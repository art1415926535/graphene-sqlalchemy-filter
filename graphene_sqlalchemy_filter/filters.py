# Standard Library
import contextlib
import warnings
from copy import deepcopy
from functools import lru_cache

# GraphQL
import graphene
from graphene.types.inputobjecttype import InputObjectTypeOptions
from graphene.types.utils import get_field_as
from graphene_sqlalchemy.converter import convert_sqlalchemy_type
from graphql import ResolveInfo

# Database
from sqlalchemy import and_, not_, or_, types
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import SAWarning
from sqlalchemy.orm import aliased
from sqlalchemy.orm.query import Query


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


try:
    from sqlalchemy_utils import TSVectorType
except ImportError:
    TSVectorType = object


if MYPY:
    FilterType = Dict[str, Any]  # pragma: no cover


DELIMITER = '_'
RANGE_BEGIN = 'begin'
RANGE_END = 'end'


_range_filter_cache = {}


def _range_filter_type(type_: graphene.ObjectType, _: bool, doc: str):
    with contextlib.suppress(KeyError):
        return _range_filter_cache[type_]

    element_type = graphene.NonNull(type_)
    klass = type(
        str(type_) + 'Range',
        (graphene.InputObjectType,),
        {RANGE_BEGIN: element_type, RANGE_END: element_type},
    )
    result = klass(description=doc)
    _range_filter_cache[type_] = result
    return result


def _in_filter_type(type_: graphene.ObjectType, nullable: bool, doc: str):
    of_type = type_
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
    REGEXP = 'regexp'
    IS_NULL = 'is_null'
    IN = 'in'
    NOT_IN = 'not_in'
    LT = 'lt'
    LTE = 'lte'
    GT = 'gt'
    GTE = 'gte'
    RANGE = 'range'

    AND = 'and'
    OR = 'or'
    NOT = 'not'

    GRAPHQL_EXPRESSION_NAMES = {
        EQ: '',
        NE: NE,
        LIKE: LIKE,
        ILIKE: ILIKE,
        REGEXP: REGEXP,
        IS_NULL: IS_NULL,
        IN: IN,
        NOT_IN: NOT_IN,
        LT: LT,
        LTE: LTE,
        GT: GT,
        GTE: GTE,
        RANGE: RANGE,
        AND: AND,
        OR: OR,
        NOT: NOT,
    }

    ALLOWED_FILTERS = {
        # Boolean
        types.Boolean: [EQ, NE],
        # Date and time
        types.Date: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.Time: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.DateTime: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        # Text
        types.String: [EQ, NE, LIKE, ILIKE, REGEXP, IN, NOT_IN],
        types.Text: [EQ, NE, LIKE, ILIKE, REGEXP, IN, NOT_IN],
        types.Unicode: [EQ, NE, LIKE, ILIKE, REGEXP, IN, NOT_IN],
        types.UnicodeText: [EQ, NE, LIKE, ILIKE, REGEXP, IN, NOT_IN],
        TSVectorType: [EQ, NE, LIKE, ILIKE, REGEXP, IN, NOT_IN],
        # Number
        types.Float: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.Numeric: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.SmallInteger: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.Integer: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        types.BigInteger: [EQ, LT, LTE, GT, GTE, NE, IN, NOT_IN, RANGE],
        # PostgreSQL
        postgresql.UUID: [EQ, NE, IN, NOT_IN],
        postgresql.INET: [EQ, NE, IN, NOT_IN],
        postgresql.CIDR: [EQ, NE, IN, NOT_IN],
        postgresql.ARRAY: [EQ, NE, IN, NOT_IN],
        postgresql.JSON: [EQ, NE, IN, NOT_IN],
        postgresql.JSONB: [EQ, NE, IN, NOT_IN],
        postgresql.HSTORE: [EQ, NE, IN, NOT_IN],
    }

    ALL = [...]

    FILTER_FUNCTIONS = {
        EQ: lambda field, v: field == v,
        NE: lambda field, v: field != v,
        LIKE: lambda field, v: field.like(v),
        ILIKE: lambda field, v: field.ilike(v),
        REGEXP: lambda field, v: field == v,
        IS_NULL: lambda field, v: field.is_(None) if v else field.isnot(None),
        IN: lambda field, v: field.in_(v),
        NOT_IN: lambda field, v: field.notin_(v),
        LT: lambda field, v: field < v,
        LTE: lambda field, v: field <= v,
        GT: lambda field, v: field > v,
        GTE: lambda field, v: field >= v,
        RANGE: lambda field, v: field.between(v[RANGE_BEGIN], v[RANGE_END]),
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
        REGEXP: 'Case-sensitive regular expression match.',
        IS_NULL: 'Takes either `true` or `false`.',
        IN: 'In a given list.',
        NOT_IN: 'Not in a given list.',
        LT: 'Less than.',
        LTE: 'Less than or equal to.',
        GT: 'Greater than.',
        GTE: 'Greater than or equal to.',
        RANGE: 'Selects values within a given range.',
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
        for klass in reversed(cls.__mro__):
            with contextlib.suppress(AttributeError):
                for key, expr in klass.EXTRA_EXPRESSIONS.items():
                    extra_expressions[key] = expr

        if extra_expressions:
            cls._register_extra_expressions(extra_expressions)

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
    def _register_extra_expressions(cls, extra_expressions: dict):
        """
        Register new expressions.

        Args:
            extra_expressions: New expressions.

        """
        cls.GRAPHQL_EXPRESSION_NAMES = deepcopy(cls.GRAPHQL_EXPRESSION_NAMES)
        cls.ALLOWED_FILTERS = deepcopy(cls.ALLOWED_FILTERS)
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

                all_expr.append(key)
                cls.ALLOWED_FILTERS[sqla_type] = all_expr
                cls.FILTER_FUNCTIONS[key] = filter_

                if object_type is not None:
                    cls.FILTER_OBJECT_TYPES[key] = object_type

                cls.DESCRIPTIONS[key] = description

    @classmethod
    def aliased(
        cls,
        info,
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
            info: Graphene resolve info.

        Returns:
            Alias.

        """
        filter_aliases = info.context[cls._filter_aliases]

        key = element, name
        try:
            return filter_aliases[key]

        except KeyError:
            alias = aliased(element, alias, name, flat, adapt_on_names)
            filter_aliases[key] = alias
            return alias

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

        model_fields = {
            c.name: {'column': c, 'type': c.type, 'nullable': c.nullable}
            for c in model.__table__.columns
            if c.name in field_filters
        }

        for field_name, field_object in model_fields.items():
            column_type = field_object['type']

            expressions = field_filters[field_name]
            if expressions == cls.ALL:
                expressions = filters_map[column_type.__class__].copy()
                if field_object['nullable']:
                    expressions.append(cls.IS_NULL)

            field_type = convert_sqlalchemy_type(
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
        info.context[cls._filter_aliases] = {}

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
            clause = filter_function(getattr(cls.model, field), value)
        except AttributeError:
            raise KeyError('Field not found: ' + field)
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
