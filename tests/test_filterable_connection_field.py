# Project
from graphene_sqlalchemy_filter import FilterableConnectionField
from tests.graphql_objects import Query, UserConnection


def test_connection_field_without_filters():
    field = FilterableConnectionField(UserConnection)
    assert 'filters' not in field.args


def test_connection_field_with_filters():
    assert 'filters' in Query.field.args
