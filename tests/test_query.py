# GraphQL
from graphene_sqlalchemy.utils import EnumValue

# Project
import pytest
from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet
from tests import models
from tests.graphql_objects import UserConnection, UserFilter


def test_empty_filters_query(info, filterable_connection_field):
    filters = None
    sort = 'username desc'
    query = filterable_connection_field.get_query(
        models.User, info, sort=EnumValue('username', sort), filters=filters
    )

    where_clause = query.whereclause
    assert where_clause is None

    assert str(query._order_by[0]) == sort


def test_filters(info, filterable_connection_field):
    filters = {'username_ilike': '%user%', 'balance_gt': 20}
    sort = 'username desc'
    query = filterable_connection_field.get_query(
        models.User, info, sort=EnumValue('username', sort), filters=filters
    )

    ok = (
        'lower("user".username) LIKE lower(:username_1) '
        'AND "user".balance > :balance_1'
    )
    where_clause = str(query.whereclause)
    assert where_clause == ok

    assert str(query._order_by[0]) == sort


def test_custom_filter(info, filterable_connection_field):
    filters = {'is_admin': True}
    query = filterable_connection_field.get_query(
        models.User, info, filters=filters
    )

    ok = '"user".username = :username_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok

    assert 'join' not in str(query).lower()


def test_wrong_filter(info, filterable_connection_field):
    filters = {'is_admin_true': True}
    with pytest.raises(KeyError, match='Field not found: is_admin_true'):
        filterable_connection_field.get_query(
            models.User, info, filters=filters
        )


def test_graphql_operators_renaming(info):
    class CustomBaseFilter(FilterSet):
        GRAPHQL_EXPRESSION_NAMES = dict(
            FilterSet.GRAPHQL_EXPRESSION_NAMES, ne='i_newer_asked_for_this'
        )

        class Meta:
            abstract = True

    class CustomUserFilter(CustomBaseFilter):
        class Meta:
            model = models.User
            fields = {'username': ['eq', 'ne']}

    user_filters = CustomUserFilter()
    field = FilterableConnectionField(UserConnection, filters=user_filters)

    filters = {'username_i_newer_asked_for_this': 'Cthulhu'}
    query = field.get_query(models.User, info, filters=filters)

    ok = '"user".username != :username_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok


def test_shortcut_renaming(info):
    class CustomUserFilter(FilterSet):
        ALL = '__all__'

        class Meta:
            model = models.User
            fields = {'username': '__all__'}

    user_filters = CustomUserFilter()
    field = FilterableConnectionField(UserConnection, filters=user_filters)

    filters = {'username': 'Guido'}
    query = field.get_query(models.User, info, filters=filters)

    ok = '"user".username = :username_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok


def test_error_with_not_found_operator(info):
    class CustomUserFilter(FilterSet):
        GRAPHQL_EXPRESSION_NAMES = dict(
            FilterSet.GRAPHQL_EXPRESSION_NAMES, eq='equal'
        )

        class Meta:
            model = models.User
            fields = {'username': ['eq']}

    user_filters = CustomUserFilter()
    field = FilterableConnectionField(UserConnection, filters=user_filters)

    filters = {'username': 'Guido'}
    with pytest.raises(KeyError, match='Operator not found "username"'):
        field.get_query(models.User, info, filters=filters)


def test_extra_expression(info):
    class CustomUserFilter(UserFilter):
        class Meta:
            model = models.User
            fields = {'balance': ['zero']}

    user_filters = CustomUserFilter()
    field = FilterableConnectionField(UserConnection, filters=user_filters)
    query = field.get_query(
        models.User, info, filters={'balance_eq_zero': True}
    )
    ok = '"user".balance = :balance_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok


def test_complex_filters(info, filterable_connection_field):
    assert hasattr(filterable_connection_field, 'filters')

    filters = {
        'is_admin': False,
        'or': [
            {
                'and': [
                    {'username_ilike': '%loki%'},
                    {'balance_range': {'begin': 500, 'end': 1000}},
                    {'is_moderator': True},
                ]
            },
            {
                'or': [
                    {'not': {'is_active': True}, 'is_moderator': True},
                    {'member_of_group': 'Valgalla', 'username_not_in': ['1']},
                    {},
                ]
            },
        ],
    }
    query = filterable_connection_field.get_query(
        models.User, info, filters=filters
    )

    ok = (
        '"user".username != :username_1 AND '
        '(lower("user".username) LIKE lower(:username_2)'
        ' AND "user".balance BETWEEN :balance_1 AND :balance_2'
        ' AND is_moderator.id IS NOT NULL'
        ' OR "user".is_active != true'
        ' AND is_moderator.id IS NOT NULL'
        ' OR of_group.name = :name_1'
        ' AND "user".username NOT IN (:username_3))'
    )
    where_clause = str(query.whereclause)
    assert where_clause == ok

    str_query = str(query)
    assert str_query.lower().count('join') == 4, str_query
