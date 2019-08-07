# GraphQL
from graphene_sqlalchemy import SQLAlchemyConnectionField, get_query
from graphene_sqlalchemy.utils import EnumValue


MYPY = False
if MYPY:
    from .filters import FilterSet  # noqa: F401; pragma: no cover


class FilterableConnectionField(SQLAlchemyConnectionField):
    filter_arg = "filters"

    def __init__(self, type_, *args, **kwargs):
        self.filters = kwargs.get(self.filter_arg)  # type: FilterSet
        super().__init__(type_, *args, **kwargs)

    def get_query(self, model, info, sort=None, **args):
        """Standard get_query with filtering."""
        query = get_query(model, info.context)
        if sort is not None:
            if isinstance(sort, EnumValue):
                query = query.order_by(sort.value)
            else:
                query = query.order_by(*(col.value for col in sort))

        request_filters = args.get(self.filter_arg)
        if self.filters is not None and request_filters:
            query = self.filters.filter(info, query, request_filters)
        return query

    def resolve_connection(self, *args, **kwargs):
        """Cast static to instance method."""
        s = super(FilterableConnectionField, self)
        func = s.resolve_connection.__func__
        return func(self, *args, **kwargs)

    def connection_resolver(self, *args, **kwargs):
        """Cast static to instance method."""
        s = super(FilterableConnectionField, self)
        func = s.connection_resolver.__func__
        return func(self, *args, **kwargs)
