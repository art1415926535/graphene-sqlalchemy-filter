# Project
from graphene_sqlalchemy_filter import FilterableConnectionField
from tests.graphql_objects import UserConnection


def test_connection_field_without_filters():
    field = FilterableConnectionField(UserConnection)
    assert hasattr(field, 'filters') and field.filters is None


def test_connection_field_with_filters(filterable_connection_field):
    assert hasattr(filterable_connection_field, 'filters')
