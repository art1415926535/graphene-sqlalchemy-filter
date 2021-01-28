# Standard Library
import contextlib
import inspect
import warnings
from copy import deepcopy
from functools import lru_cache

# GraphQL
import graphene
from graphene.types.generic import GenericScalar
from graphene.types.inputobjecttype import InputObjectTypeOptions
from graphene.types.utils import get_field_as
from graphene_sqlalchemy import __version__ as gqls_version
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphql import ResolveInfo

# Database
from sqlalchemy import and_, cast, inspection, not_, or_, types
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SAWarning
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import aliased
from sqlalchemy.orm.attributes import InstrumentedAttribute
from sqlalchemy.orm.query import Query
from sqlalchemy.sql import sqltypes


MYPY = False
if MYPY:
    from typing import (  # noqa: F401; pragma: no cover
        Any,
        Callable,
        Dict,
        Iterable,
        List,
        Type,
        Tuple,
        Union,
    )
    from sqlalchemy import Column  # noqa: F401; pragma: no cover
    from sqlalchemy.orm.query import (  # noqa: F401; pragma: no cover
        _MapperEntity,
    )

    FilterType = 'Dict[str, Any]'  # pragma: no cover

    GRAPHENE_OBJECT_OR_CLASS = Union[  # pragma: no cover
        graphene.ObjectType, Type[graphene.ObjectType]
    ]


try:
    from sqlalchemy_utils import TSVectorType
except ImportError:
    TSVectorType = object


gqls_version = tuple([int(x) for x in gqls_version.split('.')])


def _get_class(obj: 'GRAPHENE_OBJECT_OR_CLASS') -> 'Type[graphene.ObjectType]':
    if inspect.isclass(obj):
        return obj

    return obj.__class__  # only graphene-sqlalchemy<=2.2.0; pragma: no cover


def _eq_filter(field: 'Column', value: 'Any') -> 'Any':
    column_type = getattr(field, 'type', None)
    if isinstance(column_type, postgresql.ARRAY):
        value = cast(value, column_type)

    return field == value


DELIMITER = '_'
RANGE_BEGIN = 'begin'
RANGE_END = 'end'


_range_filter_cache = {}


def _range_filter_type(
    type_: 'GRAPHENE_OBJECT_OR_CLASS', _: bool, doc: str
) -> graphene.InputObjectType:
    of_type = _get_class(type_)

    with contextlib.suppress(KeyError):
        return _range_filter_cache[of_type]

    element_type = graphene.NonNull(of_type)
    klass = type(
        str(of_type) + 'Range',
        (graphene.InputObjectType,),
        {RANGE_BEGIN: element_type, RANGE_END: element_type},
    )
    result = klass(description=doc)
    _range_filter_cache[of_type] = result
    return result


def _in_filter_type(
    type_: 'GRAPHENE_OBJECT_OR_CLASS', nullable: bool, doc: str
) -> graphene.List:
    of_type = type_

    if not isinstance(of_type, graphene.List):
        of_type = _get_class(type_)

    if not nullable:
        of_type = graphene.NonNull(of_type)

    filter_field = graphene.List(of_type, description=doc)
    return filter_field


class FilterSetOptions(InputObjectTypeOptions):
    model = None
    fields = None  # type: Dict[str, List[str]]


class FilterSet(graphene.InputObjectType):
    """Filter set for connection field."""

    _custom_filters = set()
    _filter_aliases = '_filter_aliases'
    model = None

    EQ = 'eq'
    NE = 'ne'
    LIKE = 'like'
    ILIKE = 'ilike'
    IS_NULL = 'is_null'
    IN = 'in'
    NOT_IN = 'not_in'
    LT = 'lt'
    LTE = 'lte'
    GT = 'gt'
    GTE = 'gte'
    RANGE = 'range'
    CONTAINS = 'contains'
    CONTAINED_BY = 'contained_by'
    OVERLAP = 'overlap'

    AND = 'and'
    OR = 'or'
    NOT = 'not'

    GRAPHQL_EXPRESSION_NAMES = {
        EQ: '',
        NE: NE,
        LIKE: LIKE,
        ILIKE: ILIKE,
        IS_NULL: IS_NULL,
        IN: IN,
        NOT_IN: NOT_IN,
        LT: LT,
        LTE: LTE,
        GT: GT,
        GTE: GTE,
        RANGE: RANGE,
        CONTAINS: CONTAINS,
        CONTAINED_BY: CONTAINED_BY,
        OVERLAP: OVERLAP,
        AND: AND,
        OR: OR,
        NOT: NOT,
    }

    ALLOWED_FILTERS = {
        types.Boolean: [EQ, NE],
        types.Date: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.Time: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.DateTime: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.String: [EQ, NE, LIKE, ILIKE, IN, NOT_IN],
        TSVectorType: [EQ, NE, LIKE, ILIKE, IN, NOT_IN],
        types.Integer: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.Numeric: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        postgresql.UUID: [EQ, NE, IN, NOT_IN],
        postgresql.INET: [EQ, NE, IN, NOT_IN],
        postgresql.CIDR: [EQ, NE, IN, NOT_IN],
        postgresql.JSON: [EQ, NE, IN, NOT_IN],
        postgresql.HSTORE: [EQ, NE, IN, NOT_IN],
        postgresql.ARRAY: [
            EQ,
            NE,
            IN,
            NOT_IN,
            LT,
            LTE,
            GT,
            GTE,
            CONTAINS,
            CONTAINED_BY,
            OVERLAP,
        ],
    }

    ALL = [...]

    FILTER_FUNCTIONS = {
        EQ: lambda field, v: _eq_filter(field, v),
        NE: lambda field, v: not_(_eq_filter(field, v)),
        LIKE: lambda field, v: field.like(v),
        ILIKE: lambda field, v: field.ilike(v),
        IS_NULL: lambda field, v: field.is_(None) if v else field.isnot(None),
        IN: lambda field, v: field.in_(v),
        NOT_IN: lambda field, v: field.notin_(v),
        LT: lambda field, v: field < v,
        LTE: lambda field, v: field <= v,
        GT: lambda field, v: field > v,
        GTE: lambda field, v: field >= v,
        RANGE: lambda field, v: field.between(v[RANGE_BEGIN], v[RANGE_END]),
        CONTAINS: lambda field, v: field.contains(cast(v, field.type)),
        CONTAINED_BY: lambda field, v: field.contained_by(cast(v, field.type)),
        OVERLAP: lambda field, v: field.overlap(cast(v, field.type)),
    }

    FILTER_OBJECT_TYPES = {
        AND: lambda type_, _, doc: graphene.List(graphene.NonNull(type_)),
        OR: lambda type_, _, doc: graphene.List(graphene.NonNull(type_)),
        NOT: lambda type_, _, doc: type_,
        IS_NULL: lambda *x: graphene.Boolean(description=x[2]),
        RANGE: _range_filter_type,
        IN: _in_filter_type,
        NOT_IN: _in_filter_type,
    }

    DESCRIPTIONS = {
        EQ: 'Exact match.',
        NE: 'Not match.',
        LIKE: 'Case-sensitive containment test.',
        ILIKE: 'Case-insensitive containment test.',
        IS_NULL: 'Takes either `true` or `false`.',
        IN: 'In a given list.',
        NOT_IN: 'Not in a given list.',
        LT: 'Less than.',
        LTE: 'Less than or equal to.',
        GT: 'Greater than.',
        GTE: 'Greater than or equal to.',
        RANGE: 'Selects values within a given range.',
        CONTAINS: (
            'Elements are a superset of the elements '
            'of the argument array expression.'
        ),
        CONTAINED_BY: (
            'Elements are a proper subset of the elements '
            'of the argument array expression.'
        ),
        OVERLAP: (
            'Array has elements in common with an argument array expression.'
        ),
        AND: 'Conjunction of filters joined by ``AND``.',
        OR: 'Conjunction of filters joined by ``OR``.',
        NOT: 'Negation of filters.',
    }

    class Meta:
        abstract = True

    @classmethod
    def __init_subclass_with_meta__(
        cls, model=None, fields=None, _meta=None, **options
    ):
        if model is None and fields:
            raise AttributeError('Model not specified')

        if not _meta:
            _meta = FilterSetOptions(cls)

        cls.model = model
        _meta.model = model

        extra_expressions = {}
        extra_allowed_filters = {}
        for klass in reversed(cls.__mro__):
            with contextlib.suppress(AttributeError):
                for key, expr in klass.EXTRA_EXPRESSIONS.items():
                    extra_expressions[key] = expr

            with contextlib.suppress(AttributeError):
                for key, exprs in klass.EXTRA_ALLOWED_FILTERS.items():
                    extra_allowed_filters[key] = exprs

        if extra_expressions or extra_allowed_filters:
            cls._register_extra(extra_expressions, extra_allowed_filters)

        filters_fields = {}
        if model is not None:
            # Add default filter objects.
            filters_fields = cls._generate_default_filters(model, fields)

        for op in [cls.AND, cls.OR, cls.NOT]:
            doc = cls.DESCRIPTIONS.get(op)
            graphql_name = cls.GRAPHQL_EXPRESSION_NAMES[op]
            filters_fields[graphql_name] = graphene.InputField(
                cls.FILTER_OBJECT_TYPES[op](cls, False, doc), description=doc
            )

        if not _meta.fields:
            _meta.fields = {}

        _meta.fields.update(filters_fields)

        default_filter_keys = set(filters_fields.keys())

        # Add custom filter objects.
        super().__init_subclass_with_meta__(_meta=_meta, **options)

        # Save set of custom filter names.
        cls._custom_filters = set()
        meta_fields = set(_meta.fields.keys())
        if meta_fields:
            cls._custom_filters = meta_fields.difference(default_filter_keys)

    @classmethod
    def _register_extra(
        cls, extra_expressions: dict, extra_allowed_filters: dict
    ):
        """
        Register new expressions and allowed filters.

        Args:
            extra_expressions: New expressions.
            extra_allowed_filters: New allowed filters.

        """
        cls.GRAPHQL_EXPRESSION_NAMES = deepcopy(cls.GRAPHQL_EXPRESSION_NAMES)
        cls.ALLOWED_FILTERS = deepcopy(cls.ALLOWED_FILTERS)
        cls.ALLOWED_FILTERS.update(extra_allowed_filters)
        cls.FILTER_FUNCTIONS = deepcopy(cls.FILTER_FUNCTIONS)
        cls.FILTER_OBJECT_TYPES = deepcopy(cls.FILTER_OBJECT_TYPES)
        cls.DESCRIPTIONS = deepcopy(cls.DESCRIPTIONS)

        for key, data in extra_expressions.items():
            graphql_name = data['graphql_name']
            for_types = data.get('for_types', [])
            filter_ = data['filter']
            object_type = data.get('input_type')
            description = data.get('description')

            cls.GRAPHQL_EXPRESSION_NAMES.update({key: graphql_name})

            for sqla_type in for_types:
                try:
                    all_expr = cls.ALLOWED_FILTERS[sqla_type]
                except KeyError:
                    all_expr = []

                if key not in all_expr:
                    all_expr.append(key)
                cls.ALLOWED_FILTERS[sqla_type] = all_expr
                cls.FILTER_FUNCTIONS[key] = filter_

                if object_type is not None:
                    cls.FILTER_OBJECT_TYPES[key] = object_type

                cls.DESCRIPTIONS[key] = description

    @classmethod
    def aliased(
        cls,
        query,
        element,
        alias=None,
        name=None,
        flat=False,
        adapt_on_names=False,
    ):
        """
        Get an alias of the given element.

        Notes:
            Other arguments are the same as sqlalchemy.orm.aliased.

        Args:
            query: SQLAlchemy query (Deprecated: Graphene resolve info).

        Returns:
            Alias.

        """
        if isinstance(query, Query):
            filter_aliases = cls._aliases_from_query(query)
        else:
            example = cls._build_example_for_deprecation_warning(
                element, alias, name, flat, adapt_on_names
            )
            warnings.warn(
                'Graphene resolve info is deprecated, use SQLAlchemy query. '
                + example,
                DeprecationWarning,
                stacklevel=2,
            )
            filter_aliases = cls._aliases_from_info(query)

        key = element, name

        try:
            return filter_aliases[key]
        except KeyError:
            alias = aliased(element, alias, name, flat, adapt_on_names)

            if not isinstance(query, Query):
                filter_aliases[key] = alias

            return alias

    @classmethod
    def _build_example_for_deprecation_warning(
        cls, element, alias, name, flat, adapt_on_names
    ) -> str:
        """
        Build message for deprecation warning.

        Returns:
            Example code.

        """
        example = 'Example: cls.aliased(query, Model)'
        with contextlib.suppress(Exception):
            args = {
                'alias': alias,
                'name': name,
                'flat': flat,
                'adapt_on_names': adapt_on_names,
            }
            args_list = []
            for k, v in args.items():
                if not v:
                    continue

                if isinstance(v, str):
                    v = '"{}"'.format(v)
                args_list.append(k + '=' + v)

            example = 'Hint: cls.aliased(query, {}, {})'.format(
                element.__name__, ', '.join(args_list)
            )

        return example

    @classmethod
    def _aliases_from_info(
        cls, info: graphene.ResolveInfo
    ) -> 'Dict[str, _MapperEntity]':
        """
        Get cached aliases from graphene ResolveInfo object.

        Notes:
            Deprecated.

        Args:
            info: Graphene ResolveInfo object.

        Returns:
            Dictionary of model aliases.

        """
        context = info.context

        if isinstance(context, dict):
            filter_aliases = context[cls._filter_aliases]
        elif '__dict__' in context.__dir__():
            filter_aliases = getattr(context, cls._filter_aliases)
        else:
            raise RuntimeError(
                'Not supported with info.context type {}'.format(type(context))
            )

        return filter_aliases

    @classmethod
    def _aliases_from_query(cls, query: Query) -> 'Dict[str, _MapperEntity]':
        """
        Get aliases from SQLAlchemy query.

        Args:
            query: SQLAlchemy query.

        Returns:
            Dictionary of model aliases.

        """
        aliases = {
            (mapper._target, mapper.name): mapper.entity
            for mapper in query._join_entities
        }

        return aliases

    @classmethod
    def _generate_default_filters(
        cls, model, field_filters: 'Dict[str, Union[Iterable[str], Any]]'
    ) -> dict:
        """
        Generate GraphQL fields from SQLAlchemy model columns.

        Args:
            model: SQLAlchemy model.
            field_filters: Filters for fields.

        Returns:
            GraphQL fields dictionary:
            field name (key) - field instance (value).

        """
        graphql_filters = {}
        filters_map = cls.ALLOWED_FILTERS
        model_fields = cls._get_model_fields_data(model, field_filters.keys())

        for field_name, field_object in model_fields.items():
            column_type = field_object['type']

            expressions = field_filters[field_name]
            if expressions == cls.ALL:
                if column_type is None:
                    raise ValueError(
                        'Unsupported field type for automatic filter binding'
                    )

                type_class = column_type.__class__
                try:
                    expressions = filters_map[type_class].copy()
                except KeyError:
                    for type_, exprs in filters_map.items():
                        if issubclass(type_class, type_):
                            expressions = exprs.copy()
                            break
                    else:
                        raise KeyError(
                            'Unsupported column type. '
                            'Hint: use EXTRA_ALLOWED_FILTERS.'
                        )

                if field_object['nullable']:
                    expressions.append(cls.IS_NULL)

            field_type = cls._get_gql_type_from_sqla_type(
                column_type, field_object['column']
            )

            fields = cls._generate_filter_fields(
                expressions, field_name, field_type, field_object['nullable']
            )
            for name, field in fields.items():
                graphql_filters[name] = get_field_as(
                    field, graphene.InputField
                )

        return graphql_filters

    @classmethod
    def _get_gql_type_from_sqla_type(
        cls, column_type, sqla_column
    ) -> 'Union[Type[graphene.ObjectType], Type[GenericScalar]]':
        """
        Get GraphQL type from SQLAlchemy column.

        Args:
            column_type: SQLAlchemy column type.
            sqla_column: SQLAlchemy column or hybrid attribute.

        Returns:
            GraphQL type.

        """
        if column_type is None:
            return GenericScalar
        else:
            return convert_sqlalchemy_type(column_type, sqla_column)

    @classmethod
    def _get_model_fields_data(cls, model, only_fields: 'Iterable[str]'):
        """
        Get model columns.

        Args:
            model: SQLAlchemy model.
            only_fields: Filter of fields.

        Returns:
            Fields info.

        """
        model_fields = {}

        inspected = inspection.inspect(model)
        for descr in inspected.all_orm_descriptors:
            if isinstance(descr, hybrid_property):
                attr = descr
                name = attr.__name__
                if name not in only_fields:
                    continue

                model_fields[name] = {
                    'column': attr,
                    'type': None,
                    'nullable': True,
                }

            elif isinstance(descr, InstrumentedAttribute):
                attr = descr.property
                name = attr.key
                if name not in only_fields:
                    continue

                column = attr.columns[0]
                model_fields[name] = {
                    'column': column,
                    'type': column.type,
                    'nullable': column.nullable,
                }

        return model_fields

    @staticmethod
    def _is_graphene_enum(obj: 'Any') -> bool:
        """
        Return whether 'obj' is a enum.

        Args:
            obj: lambda or graphene.Field

        Returns:
            boolean

        """
        if gqls_version < (2, 2, 0):
            # https://github.com/graphql-python/graphene-sqlalchemy/blob/v2.1.2/graphene_sqlalchemy/converter.py#L147
            return isinstance(
                obj, graphene.Field
            ) and isinstance(  # pragma: no cover
                obj._type, graphene.types.enum.EnumMeta
            )
        elif gqls_version == (2, 2, 0):
            # https://github.com/graphql-python/graphene-sqlalchemy/blob/db3e9f4c3baad3e62c113d4a9ddd2e3983d324f2/graphene_sqlalchemy/converter.py#L150
            return isinstance(obj, graphene.Field) and callable(
                obj._type
            )  # pragma: no cover
        else:
            # https://github.com/graphql-python/graphene-sqlalchemy/blob/17d535efba03070cbc505d915673e0f24d9ca60c/graphene_sqlalchemy/converter.py#L216
            return callable(obj) and obj.__name__ == '<lambda>'

    @staticmethod
    def _get_enum_from_field(
        enum: 'Union[Callable, graphene.Field]',
    ) -> graphene.Enum:
        """
        Get graphene enum.

        Args:
            enum: lambda or graphene.Field

        Returns:
            Graphene enum.

        """
        if gqls_version < (2, 2, 0):
            # AssertionError: Found different types
            # with the same name in the schema: ...
            raise AssertionError(  # pragma: no cover
                'Enum is not supported. '
                'Requires graphene-sqlalchemy 2.2.0 or higher.'
            )
        elif gqls_version == (2, 2, 0):
            # https://github.com/graphql-python/graphene-sqlalchemy/compare/2.1.2...2.2.0#diff-9202780f6bf4790a0d960de553c086f1L155
            return enum._type()()  # pragma: no cover
        else:
            # https://github.com/graphql-python/graphene-sqlalchemy/compare/2.2.0...2.2.1#diff-9202780f6bf4790a0d960de553c086f1L150
            return enum()()

    @classmethod
    def _generate_filter_fields(
        cls,
        expressions: 'List[str]',
        field_name: str,
        field_type: 'Type[graphene.ObjectType]',
        nullable: bool,
    ) -> 'Dict[str, graphene.ObjectType]':
        """
        Generate all available filters for model column.

        Args:
            expressions: Allowed expressions. Example: ['eq', 'lt', 'gt'].
            field_name: Model column name.
            field_type: GraphQL field type.
            nullable: Can field be is null.

        Returns:
            GraphQL fields dictionary.

        """
        filters = {}

        for op in expressions:
            key = field_name
            graphql_name = cls.GRAPHQL_EXPRESSION_NAMES[op]
            if graphql_name:
                key += DELIMITER + graphql_name

            doc = cls.DESCRIPTIONS.get(op)
            try:
                filter_field = cls.FILTER_OBJECT_TYPES[op](
                    field_type, nullable, doc
                )
            except KeyError:
                if isinstance(field_type, graphene.List):
                    filter_field = field_type
                elif cls._is_graphene_enum(field_type):
                    filter_field = cls._get_enum_from_field(field_type)
                else:
                    field_type = _get_class(field_type)
                    filter_field = field_type(description=doc)

            filters[key] = filter_field

        return filters

    @classmethod
    def filter(
        cls, info: ResolveInfo, query: Query, filters: 'FilterType'
    ) -> Query:
        """
        Return a new query instance with the args ANDed to the existing set.

        Args:
            info: GraphQL execution info.
            query: SQLAlchemy query.
            filters: Filters dictionary.

        Returns:
            Filtered query instance.

        """
        context = info.context

        if isinstance(context, dict):
            context[cls._filter_aliases] = {}
        elif '__dict__' in context.__dir__():
            setattr(context, cls._filter_aliases, {})
        else:
            msg = (
                'Graphene-SQLAlchemy-Filter: '
                'info.context has an unsupported type {}. '
                'Now cls.aliased(info, ...) is not supported. '
                'Allowed types: dict and object with __dict__ attribute.'
            ).format(type(context))
            warnings.warn(msg, RuntimeWarning)

        query, sqla_filters = cls._translate_many_filter(info, query, filters)
        if sqla_filters is not None:
            query = query.filter(*sqla_filters)

        return query

    @classmethod
    @lru_cache(maxsize=500)
    def _split_graphql_field(cls, graphql_field: str) -> 'Tuple[str, str]':
        """
        Get model field name and expression.

        Args:
            graphql_field: Field name.

        Returns:
            Model field name and expression name.

        """
        empty_expr = None

        expression_to_name = sorted(
            cls.GRAPHQL_EXPRESSION_NAMES.items(), key=lambda x: -len(x[1])
        )

        for expression, name in expression_to_name:
            if name == '':
                empty_expr = expression
                continue

            key = DELIMITER + name
            if graphql_field.endswith(key):
                return graphql_field[: -len(key)], expression

        if empty_expr is not None:
            return graphql_field, empty_expr

        raise KeyError('Operator not found "{}"'.format(graphql_field))

    @classmethod
    def _translate_filter(
        cls, info: ResolveInfo, query: Query, key: str, value: 'Any'
    ) -> 'Tuple[Query, Any]':
        """
        Translate GraphQL to SQLAlchemy filters.

        Args:
            info: GraphQL resolve info.
            query: SQLAlchemy query.
            key: Filter key: model field, 'or', 'and', 'not', custom filter.
            value: Filter value.

        Returns:
            SQLAlchemy clause.

        """
        if key in cls._custom_filters:
            filter_name = key + '_filter'
            with warnings.catch_warnings():
                warnings.simplefilter('ignore', SAWarning)
                clause = getattr(cls, filter_name)(info, query, value)
                if isinstance(clause, tuple):
                    query, clause = clause

            return query, clause

        if key == cls.GRAPHQL_EXPRESSION_NAMES[cls.AND]:
            return cls._translate_many_filter(info, query, value, and_)

        if key == cls.GRAPHQL_EXPRESSION_NAMES[cls.OR]:
            return cls._translate_many_filter(info, query, value, or_)

        if key == cls.GRAPHQL_EXPRESSION_NAMES[cls.NOT]:
            return cls._translate_many_filter(
                info, query, value, lambda *x: not_(and_(*x))
            )

        field, expression = cls._split_graphql_field(key)
        filter_function = cls.FILTER_FUNCTIONS[expression]

        try:
            model_field = getattr(cls.model, field)
        except AttributeError:
            raise KeyError('Field not found: ' + field)

        model_field_type = getattr(model_field, 'type', None)
        if isinstance(model_field_type, sqltypes.Enum):
            value = model_field_type.enum_class(value)

        clause = filter_function(model_field, value)
        return query, clause

    @classmethod
    def _translate_many_filter(
        cls,
        info: ResolveInfo,
        query: Query,
        filters: 'Union[List[FilterType], FilterType]',
        join_by: 'Callable' = None,
    ) -> 'Tuple[Query, Any]':
        """
        Translate several filters.

        Args:
            info: GraphQL resolve info.
            query: SQLAlchemy query.
            filters: GraphQL filters.
            join_by: Join translated filters.

        Returns:
            SQLAlchemy clause.

        """
        result = []

        # Filters from 'and', 'or', 'not'.
        if isinstance(filters, list):
            for f in filters:
                query, local_filters = cls._translate_many_filter(
                    info, query, f, and_
                )
                if local_filters is not None:
                    result.append(local_filters)

        else:
            for k, v in filters.items():
                query, r = cls._translate_filter(info, query, k, v)
                if r is not None:
                    result.append(r)

        if not result:
            return query, None

        if join_by is None:
            return query, result

        return query, join_by(*result)
