# Third Party
import pytest

# GraphQL
from graphene_sqlalchemy.utils import EnumValue

# Database
from sqlalchemy.sql import text

# Project
from graphene_sqlalchemy_filter import FilterSet
from tests import gqls_version, models
from tests.graphql_objects import Query, UserFilter


def test_sort(info):
    filters = None
    sort = 'username desc'
    query = Query.field.get_query(
        models.User,
        info,
        sort=EnumValue('username', text(sort)),
        filters=filters,
    )

    where_clause = query.whereclause
    assert where_clause is None

    assert str(query._order_by_clauses[0]) == sort


def test_empty_filters_query(info_and_user_query):
    info, user_query = info_and_user_query

    query = UserFilter.filter(info, user_query, {})

    where_clause = query.whereclause
    assert where_clause is None


def test_filters(info_and_user_query):
    info, user_query = info_and_user_query
    filters = {'username_ilike': '%user%', 'balance_gt': 20}
    query = UserFilter.filter(info, user_query, filters)

    ok = (
        'lower("user".username) LIKE lower(:username_1) '
        'AND "user".balance > :balance_1'
    )
    where_clause = str(query.whereclause)
    assert where_clause == ok


@pytest.mark.skipif(gqls_version < (2, 2, 0), reason='not supported')
def test_enum(info_and_user_query):
    info, user_query = info_and_user_query
    filters = {'status': models.StatusEnum.online.value}
    query = UserFilter.filter(info, user_query, filters)

    where_clause = query.whereclause
    ok = '"user".status = :status_1'
    assert str(where_clause) == ok
    assert where_clause.right.effective_value == models.StatusEnum.online


def test_custom_filter(info_and_user_query):
    info, user_query = info_and_user_query

    filters = {'is_admin': True}
    query = UserFilter.filter(info, user_query, filters)

    ok = '"user".username = :username_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok

    assert 'join' not in str(query).lower()


def test_wrong_filter(info_and_user_query):
    info, user_query = info_and_user_query

    filters = {'is_admin_true': True}
    with pytest.raises(KeyError, match='Field not found: is_admin_true'):
        UserFilter.filter(info, user_query, filters)


def test_graphql_operators_renaming(info_and_user_query):
    info, user_query = info_and_user_query

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

    filters = {'username_i_newer_asked_for_this': 'Cthulhu'}
    query = CustomUserFilter.filter(info, user_query, filters)

    ok = '"user".username != :username_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok


def test_shortcut_renaming(info_and_user_query):
    info, user_query = info_and_user_query

    class CustomUserFilter(FilterSet):
        ALL = '__all__'

        class Meta:
            model = models.User
            fields = {'username': '__all__'}

    filters = {'username': 'Guido'}
    query = CustomUserFilter.filter(info, user_query, filters)

    ok = '"user".username = :username_1'
    where_clause = str(query.whereclause)
    assert where_clause == ok


def test_error_with_not_found_operator(info_and_user_query):
    info, user_query = info_and_user_query

    class CustomUserFilter(FilterSet):
        GRAPHQL_EXPRESSION_NAMES = dict(
            FilterSet.GRAPHQL_EXPRESSION_NAMES, eq='equal'
        )

        class Meta:
            model = models.User
            fields = {'username': ['eq']}

    filters = {'username': 'Guido'}
    with pytest.raises(KeyError, match='Operator not found "username"'):
        CustomUserFilter.filter(info, user_query, filters)


def test_extra_expression(info_and_user_query):
    info, user_query = info_and_user_query

    class CustomUserFilter(UserFilter):
        class Meta:
            model = models.User
            fields = {'balance': ['zero']}

    filters = {'balance_eq_zero': True}
    query = CustomUserFilter.filter(info, user_query, filters)

    ok = '"user".balance = :balance_1'

    where_clause = str(query.whereclause)
    assert where_clause == ok


def test_complex_filters(info_and_user_query):
    info, user_query = info_and_user_query

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
    query = UserFilter.filter(info, user_query, filters)

    ok = (
        '"user".username != :username_1 AND '
        '(lower("user".username) LIKE lower(:username_2)'
        ' AND "user".balance BETWEEN :balance_1 AND :balance_2'
        ' AND is_moderator.id IS NOT NULL'
        ' OR "user".is_active != true'
        ' AND is_moderator.id IS NOT NULL'
        ' OR of_group.name = :name_1'
        ' AND ("user".username NOT IN ([POSTCOMPILE_username_3])))'
    )
    where_clause = str(query.whereclause)
    assert where_clause == ok

    str_query = str(query)
    assert str_query.lower().count('join') == 4, str_query


def test_complex_relationship_filters(info_and_user_query):
    info, user_query = info_and_user_query

    filters = {
        'not': {'is_active': True},
        'or': [
            {'is_admin': False},
            {
                'assignments': {
                    'or': [{'task': {'name': 'Write code'}}, {'active': True}]
                }
            },
        ],
    }
    query = UserFilter.filter(info, user_query, filters)

    ok = (
        '"user".is_active != true AND '
        '("user".username != :username_1 OR (EXISTS (SELECT 1'
        ' FROM "user", task_assignments'
        ' WHERE "user".user_id = task_assignments.user_id AND ((EXISTS'
        ' (SELECT 1 FROM task_assignments'
        ' WHERE "user".user_id = task_assignments.user_id AND (EXISTS'
        ' (SELECT 1 FROM task'
        ' WHERE task.id = task_assignments.task_id AND task.name = :name_1))))'
        ' OR (EXISTS (SELECT 1 FROM task_assignments WHERE '
        '"user".user_id = task_assignments.user_id AND '
        'task_assignments.active = true))))))'
    )
    where_clause = str(query.whereclause).replace('\n', '')
    assert where_clause == ok
