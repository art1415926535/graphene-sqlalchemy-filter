from graphene_sqlalchemy_filter import FilterableConnectionField

from tests.graphql_objects import UserConnection, UserFilter
from tests.models import User


def test_connection_field_without_filters():
    field = FilterableConnectionField(UserConnection)
    assert "filters" not in field.args


def test_connection_field_with_filters():
    field = FilterableConnectionField(UserConnection, filters=UserFilter())
    assert "filters" in field.args


def test_connection_field_with_custom_field():
    class CustomField(FilterableConnectionField):
        filters = {User: UserFilter()}

    field = CustomField(UserConnection)
    assert "filters" in field.args


def test_connection_field_with_custom_field_and_arg():
    class CustomField(FilterableConnectionField):
        filter_arg = "where"
        filters = {User: UserFilter()}

    field = CustomField(UserConnection)
    assert "where" in field.args
