import pytest

import graphene
from graphene_sqlalchemy import get_query

from graphene_sqlalchemy_filter import FilterSet
from graphene_sqlalchemy_filter.connection_field import gqls_version

from tests import models


@pytest.mark.skipif(gqls_version < (2, 2, 0), reason="not supported")
def test_enum_filter_without_relay(session):
    """https://github.com/art1415926535/graphene-sqlalchemy-filter/issues/28"""  # noqa: D415
    online = models.StatusEnum.online
    users = [
        models.User(username="user_1", is_active=True, status=online),
        models.User(username="user_2", is_active=True),
    ]
    session.bulk_save_objects(users)

    class UserFilter(FilterSet):
        class Meta:
            model = models.User
            fields = {"status": ["eq", "in"]}

    class UserType(graphene.ObjectType):
        username = graphene.String()

    class Query(graphene.ObjectType):
        all_users = graphene.List(UserType, filters=UserFilter())

        def resolve_all_users(self, info, filters=None):
            query = get_query(models.User, info.context)
            if filters is not None:
                query = UserFilter.filter(info, query, filters)

            return query

    schema = graphene.Schema(query=Query)

    request_string = """
    {
        allUsers(filters: {status: ONLINE, statusIn: [ONLINE]}) {
            username
        }
    }"""
    execution_result = schema.execute(
        request_string, context={"session": session}
    )

    assert not execution_result.errors
    assert not execution_result.invalid

    assert execution_result.data == {"allUsers": [{"username": "user_1"}]}
