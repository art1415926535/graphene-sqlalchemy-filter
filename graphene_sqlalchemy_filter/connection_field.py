from __future__ import annotations

import importlib.metadata
import re
from contextlib import suppress
from functools import partial
from typing import TYPE_CHECKING, Any, ClassVar, Union, cast

from sqlalchemy import inspect, inspection, tuple_
from sqlalchemy.orm import (
    DeclarativeMeta,
    Query,
    aliased,
    contains_eager,
    defaultload,
)

import graphene_sqlalchemy
from graphene.utils.str_converters import to_snake_case
from promise import Promise, dataloader


if TYPE_CHECKING:
    from collections.abc import Callable

    from graphene.relay import Connection
    from graphql import ResolveInfo

    from .filters import FilterSet

_gqls_version_match = re.match(
    r"(\d+)\.(\d+)\.(\d+)", importlib.metadata.version("graphene-sqlalchemy")
)
gqls_version = ()
if _gqls_version_match:
    gqls_version: tuple[int, ...] = tuple(
        int(x) for x in _gqls_version_match.groups()
    )


graphene_sqlalchemy_version_lt_2_1_2 = gqls_version < (2, 1, 2)
if graphene_sqlalchemy_version_lt_2_1_2:
    default_connection_field_factory = None
else:
    from graphene_sqlalchemy.fields import default_connection_field_factory


SqlaModel = Union[DeclarativeMeta, type[DeclarativeMeta]]

DEFAULT_FILTER_ARG: str = "filters"


class FilterableConnectionField(graphene_sqlalchemy.SQLAlchemyConnectionField):
    filter_arg: ClassVar[str] = DEFAULT_FILTER_ARG

    factory: ClassVar[FilterableFieldFactory | Callable | None] = None
    filters: ClassVar[dict] = {}

    def __init_subclass__(cls) -> None:
        if graphene_sqlalchemy_version_lt_2_1_2:
            return

        if cls.filters and cls.factory is None:
            cls.factory = FilterableFieldFactory(cls.filters)

            if cls.filter_arg != DEFAULT_FILTER_ARG:
                # Update filter arg for nested fields.
                cls.factory.model_loader_class = type(
                    "CustomModelLoader",
                    (ModelLoader,),
                    {"filter_arg": cls.filter_arg},
                )
        elif cls.factory is None:
            cls.factory = default_connection_field_factory

    def __init__(
        self, connection: type[Connection], *args: Any, **kwargs: Any
    ) -> None:
        if self.filter_arg not in kwargs:
            model = connection._meta.node._meta.model

            with suppress(KeyError):
                kwargs[self.filter_arg] = self.filters[model]

        super().__init__(connection, *args, **kwargs)

    @classmethod
    def get_query(
        cls, model: SqlaModel, info: ResolveInfo, sort: Any = None, **args: Any
    ) -> Query:
        """Standard get_query with filtering."""
        query = super().get_query(model, info, sort, **args)

        request_filters = args.get(cls.filter_arg)
        filter_set = cls.get_filter_set(info)
        return filter_set.filter(info, query, request_filters)

    @classmethod
    def get_filter_set(cls, info: ResolveInfo) -> FilterSet:
        """Get field filter set.

        Args:
            info: Graphene resolve info object.

        Returns:
            FilterSet class from field args.

        """
        field_name = info.field_asts[0].name.value
        schema_field = info.parent_type.fields.get(field_name)
        filters_type = schema_field.args[cls.filter_arg].type
        filters: FilterSet = filters_type.graphene_type
        return filters


class ModelLoader(dataloader.DataLoader):
    filter_arg: str = DEFAULT_FILTER_ARG

    def __init__(
        self,
        parent_model: Any,
        model: SqlaModel,
        info: ResolveInfo,
        graphql_args: dict,
    ) -> None:
        """Dataloader for SQLAlchemy model relations.

        Args:
            parent_model: Parent SQLAlchemy model.
            model: SQLAlchemy model.
            info: Graphene resolve info object.
            graphql_args: Request args: filters, sort, ...

        """
        super().__init__()
        self.info: ResolveInfo = info
        self.graphql_args: dict = graphql_args

        self.model: SqlaModel = model
        self.parent_model: Any = parent_model
        self.parent_model_pks: tuple[str, ...] = self._get_model_pks(
            self.parent_model
        )
        self.parent_model_pk_fields: tuple = tuple(
            getattr(self.parent_model, pk) for pk in self.parent_model_pks
        )

        self.model_relation_field: str = to_snake_case(self.info.field_name)

        self.relation: Any = getattr(
            self.parent_model, self.model_relation_field
        )

    def batch_load_fn(self, keys: list[tuple[Any]]) -> Promise:
        """Load related objects.

        Args:
            keys: Primary key values of parent model.

        Returns:
            Lists of related orm objects.

        """
        if len(self.parent_model_pk_fields) == 1:
            left_hand_side = self.parent_model_pk_fields[0]
            right_hand_side = [k[0] for k in keys]
        else:
            left_hand_side = tuple_(*self.parent_model_pk_fields)
            right_hand_side = keys

        query: Query = self._get_query().filter(
            left_hand_side.in_(right_hand_side)
        )

        objects: dict[tuple[Any], Any] = {
            self.parent_model_object_to_key(parent_object): getattr(
                parent_object, self.model_relation_field
            )
            for parent_object in query
        }
        return Promise.resolve(
            [objects.get(object_id, []) for object_id in keys]
        )

    @staticmethod
    def _get_model_pks(model: SqlaModel) -> tuple[str, ...]:
        """Get primary key field name.

        Args:
            model: SQLAlchemy model.

        Returns:
            Field name.

        """
        model_pk_fields: tuple[str, ...] = tuple(
            (
                cast("str", name)
                for name, c in inspection.inspect(model).columns.items()
                if c.primary_key
            )
        )
        return model_pk_fields

    def parent_model_object_to_key(self, parent_object: Any) -> Any:
        """Get primary key value from SQLAlchemy orm object.

        Args:
            parent_object: SQLAlchemy orm object.

        Returns:
            Primary key value.

        """
        key: tuple[Any, ...] = tuple(
            getattr(parent_object, pk) for pk in self.parent_model_pks
        )
        return key

    @classmethod
    def _get_filter_set(cls, info: ResolveInfo) -> FilterSet:
        """Get field filter set.

        Args:
            info: Graphene resolve info object.

        Returns:
            FilterSet class from field args.

        """
        field_name = info.field_asts[0].name.value
        schema_field = info.parent_type.fields.get(field_name)
        filters_type = schema_field.args[cls.filter_arg].type
        filters: FilterSet = filters_type.graphene_type
        return filters

    def _get_query(self) -> Query:
        """Build, filter and sort the query.

        Returns:
            SQLAlchemy query.

        """
        subquery = graphene_sqlalchemy.get_query(self.model, self.info.context)

        request_filters = self.graphql_args.get(self.filter_arg)
        filter_set = self._get_filter_set(self.info)
        subquery = filter_set.filter(self.info, subquery, request_filters)

        aliased_model = aliased(
            self.model, subquery.subquery(with_labels=True)
        )

        query = (
            graphene_sqlalchemy.get_query(self.parent_model, self.info.context)
            .join(aliased_model, self.relation)
            .options(
                contains_eager(self.relation, alias=aliased_model),
                defaultload(self.parent_model).load_only(
                    *self.parent_model_pk_fields
                ),
            )
        )
        return self._sorted_query(
            query, self.graphql_args.get("sort"), aliased_model
        )

    def _sorted_query(
        self, query: Query, sort: list | None, by_model: Any
    ) -> Query:
        """Sort query."""
        order = []
        if sort:
            for s in sort:
                ai = inspect(by_model)
                prop = ai.mapper.get_property_by_column(s.value.element)
                col = getattr(by_model, prop.key)
                order.append(s.value.modifier(col))

        return query.order_by(*order)


class NestedFilterableConnectionField(FilterableConnectionField):
    dataloaders_field: str = "_sqla_filter_dataloaders"

    @classmethod
    def _get_or_create_data_loader(
        cls, root: Any, model: SqlaModel, info: ResolveInfo, args: dict
    ) -> ModelLoader:
        """Get or create (and save) dataloader from ResolveInfo.

        Args:
            root: Parent model orm object.
            model: SQLAlchemy model.
            info: Graphene resolve info object.
            args: Request args: filters, sort, ...

        Returns:
            Dataloader for SQLAlchemy model.

        """
        context: dict | object = info.context

        if isinstance(context, dict):
            try:
                data_loaders = context[cls.dataloaders_field]
            except KeyError:
                data_loaders = {}
                context[cls.dataloaders_field] = data_loaders

        else:
            data_loaders = getattr(context, cls.dataloaders_field, None)
            if data_loaders is None:
                data_loaders = {}
                setattr(info.context, cls.dataloaders_field, data_loaders)

        # Unique dataloader key for context.
        data_loader_key = tuple(p for p in info.path if isinstance(p, str))

        try:
            current_data_loader: ModelLoader = data_loaders[data_loader_key]
        except KeyError:
            current_data_loader = ModelLoader(type(root), model, info, args)
            data_loaders[data_loader_key] = current_data_loader

        return current_data_loader

    @classmethod
    def connection_resolver(
        cls,
        resolver: Any,  # noqa: ARG003
        connection_type: Any,
        model: SqlaModel,
        root: Any,
        info: ResolveInfo,
        **kwargs: dict,
    ) -> Promise | Connection:
        """Resolve nested connection.

        Args:
            resolver: Default resolver.
            connection_type: Connection class.
            model: SQLAlchemy model.
            root: Parent SQLAlchemy object.
            info: Graphene resolve info object.
            **kwargs: Request args: filters, sort, ...

        Returns:
            Connection object.

        """
        data_loader: ModelLoader = cls._get_or_create_data_loader(
            root, model, info, kwargs
        )
        root_pk_value: tuple = data_loader.parent_model_object_to_key(root)
        resolved: Promise = data_loader.load(root_pk_value)

        on_resolve = partial(
            cls.resolve_connection, connection_type, model, info, kwargs
        )
        return Promise.resolve(resolved).then(on_resolve)


class FilterableFieldFactory:
    model_loader_class: type[ModelLoader] = ModelLoader
    field_class: type[NestedFilterableConnectionField] = (
        NestedFilterableConnectionField
    )

    def __init__(self, model_filters: dict) -> None:
        self.model_filters: dict = model_filters

    def __call__(
        self, relationship: Any, registry: Any = None, **field_kwargs: dict
    ) -> NestedFilterableConnectionField:
        """Get field for relation.

        Args:
            relationship: SQLAlchemy relation.
            registry: graphene-sqlalchemy registry.
            **field_kwargs: Field args.

        Returns:
            Filed object.

        """
        model = relationship.mapper.entity
        model_type = registry.get_type_for_model(model)

        filters: FilterSet | None = self.model_filters.get(model)

        if filters is not None:
            field_kwargs.setdefault(
                self.model_loader_class.filter_arg, filters
            )

        return self.field_class(model_type._meta.connection, **field_kwargs)
