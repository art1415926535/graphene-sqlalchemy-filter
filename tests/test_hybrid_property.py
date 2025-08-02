import pytest
from sqlalchemy.orm import Query

from graphene_sqlalchemy_filter import FilterSet

from tests import models
from tests.graphql_objects import UserFilter


def test_hybrid_property_automatic_filter_binding():
    msg = "Unsupported field type for automatic filter binding"
    with pytest.raises(ValueError, match=msg):

        class TestFilter(FilterSet):
            class Meta:
                model = models.User
                fields = {"username_hybrid_property": [...]}


def test_sql_query(info):
    filters = {"username_hybrid_property": ["admin"]}
    user_query = Query(models.User)
    query = UserFilter.filter(info, user_query, filters)

    where_clause = str(query.whereclause)
    ok = 'lower("user".username) = :lower_1'
    assert where_clause == ok
