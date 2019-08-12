# GraphQL
from graphene_sqlalchemy import SQLAlchemyConnectionField, get_query
from graphene_sqlalchemy.utils import EnumValue
from graphql import ResolveInfo


MYPY = False
if MYPY:
    from .filters import FilterSet  # noqa: F401; pragma: no cover


class FilterableConnectionField(SQLAlchemyConnectionField):
    filter_arg = "filters"

    @classmethod
    def get_query(cls, model, info: ResolveInfo, sort=None, **args):
        """Standard get_query with filtering."""
        query = get_query(model, info.context)
        if sort is not None:
            if isinstance(sort, EnumValue):
                query = query.order_by(sort.value)
            else:
                query = query.order_by(*(col.value for col in sort))

        request_filters = args.get(cls.filter_arg)
        if request_filters:
            filter_set = cls.get_filter_set(info)
            query = filter_set.filter(info, query, request_filters)

        return query

    @classmethod
    def get_filter_set(cls, info):
        """
        Get field filter set.

        Args:
            info: Graphene resolve info object.

        Returns:
            FilterSet class from field args.

        """
        field_name = info.field_asts[0].name.value
        schema_field = info.parent_type.fields.get(field_name)
        filters = schema_field.args[cls.filter_arg].type
        filters = filters.graphene_type  # type: FilterSet
        return filters
