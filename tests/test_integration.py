# Third Party
import pytest

# Project
from graphene_sqlalchemy_filter.connection_field import (
    graphene_sqlalchemy_version_lt_2_1_2,
)
from tests.graphql_objects import schema
from tests.models import Assignment, Group, Membership, Task, User
from tests.utils import SQLAlchemyQueryCounter


def add_users(session):
    users = [
        User(username='user_1', is_active=True, balance=0),
        User(username='user_2', is_active=True),
    ]
    session.bulk_save_objects(users, return_defaults=True)
    return users


def add_groups(session, with_parent_group=False):
    parent_group_id = None

    if with_parent_group:
        parent_group = Group(name='parent')
        session.add(parent_group)
        session.flush()

        parent_group_id = parent_group.id

    groups = [
        Group(name='group_1', parent_group_id=parent_group_id),
        Group(name='group_2', parent_group_id=parent_group_id),
        Group(name='group_3', parent_group_id=parent_group_id),
    ]
    session.bulk_save_objects(groups, return_defaults=True)
    session.flush()

    return groups


def add_users_to_new_groups(session, users):
    groups = add_groups(session)

    memberships = [
        Membership(
            user_id=users[0].id,
            creator_username=users[0].username,
            group_id=groups[0].id,
        ),
        Membership(
            user_id=users[0].id,
            creator_username=users[0].username,
            group_id=groups[1].id,
            is_moderator=True,
        ),
        Membership(
            user_id=users[0].id,
            creator_username=users[0].username,
            group_id=groups[2].id,
        ),
        Membership(
            user_id=users[1].id,
            creator_username=users[0].username,
            group_id=groups[0].id,
            is_moderator=True,
        ),
        Membership(
            user_id=users[1].id,
            creator_username=users[1].username,
            group_id=groups[1].id,
        ),
        Membership(
            user_id=users[1].id,
            creator_username=users[1].username,
            group_id=groups[2].id,
        ),
    ]
    session.bulk_save_objects(memberships, return_defaults=True)
    session.flush()
    return groups


def add_tasks(session):
    tasks = [
        Task(name='Write code'),
        Task(name='Write documentation'),
        Task(name='Make breakfast'),
    ]
    session.bulk_save_objects(tasks, return_defaults=True)
    session.flush()

    return tasks


def assign_users_to_tasks(session, users):
    tasks = add_tasks(session)

    assignments = [
        Assignment(user_id=users[0].id, task_id=tasks[0].id, active=True),
        Assignment(user_id=users[0].id, task_id=tasks[1].id, active=False),
        Assignment(user_id=users[1].id, task_id=tasks[2].id, active=True),
    ]
    session.bulk_save_objects(assignments, return_defaults=True)
    session.flush()
    return assignments


def test_response_without_filters(session):
    add_users(session)
    session.commit()

    with SQLAlchemyQueryCounter(session, 2):
        execution_result = schema.execute(
            '{field{edges{node{username}}}}', context={'session': session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert 'field' in execution_result.data

    field = execution_result.data['field']
    assert 'edges' in field

    edges = field['edges']
    assert len(edges) == 2

    node = edges[0]['node']
    assert node == {'username': 'user_1'}

    node = edges[1]['node']
    assert node == {'username': 'user_2'}


def test_response_with_filters(session):
    add_users(session)
    session.commit()

    request_string = (
        '{field(filters:{username: "user_1"}){edges{node{username balance}}}}'
    )
    with SQLAlchemyQueryCounter(session, 2):
        execution_result = schema.execute(
            request_string, context={'session': session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert 'field' in execution_result.data

    field = execution_result.data['field']
    assert 'edges' in field

    edges = field['edges']
    assert len(edges) == 1

    node = edges[0]['node']
    assert node == {'username': 'user_1', 'balance': 0}


def test_nested_response_without_filters(session):
    users = add_users(session)
    add_users_to_new_groups(session, users)
    session.commit()

    request_string = """{
            field{
                edges{
                    node{
                        username
                        groups{
                            edges{
                                node{
                                    name
                                }
                            }
                        }
                        SomeMemberships: memberships{
                            edges{
                                node{
                                    isModerator
                                }
                            }
                        }
                        createdMemberships{
                            edges{
                                node{
                                    isModerator
                                }
                            }
                        }
                    }
                }
            }
        }"""
    if graphene_sqlalchemy_version_lt_2_1_2:
        query_count = 8  # default
    else:
        query_count = 5  # graphene_sqlalchemy_filter.ModelLoader

    with SQLAlchemyQueryCounter(session, query_count):
        execution_result = schema.execute(
            request_string, context={'session': session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert 'field' in execution_result.data

    field = execution_result.data['field']
    assert 'edges' in field

    edges = field['edges']
    assert len(edges) == 2
    user_0 = edges[0]['node']
    user_1 = edges[1]['node']

    user_0_memberships_edges = user_0['SomeMemberships']['edges']
    is_moderator_values_1 = [
        e['node']['isModerator'] for e in user_0_memberships_edges
    ]
    assert is_moderator_values_1 == [False, True, False]

    user_0_created_memberships_edges = user_0['createdMemberships']['edges']
    is_moderator_values_2 = [
        e['node']['isModerator'] for e in user_0_created_memberships_edges
    ]
    assert is_moderator_values_2 == [False, True, False, True]

    user_0_groups_edges = user_0['groups']['edges']
    groups = [e['node']['name'] for e in user_0_groups_edges]
    assert groups == ['group_1', 'group_2', 'group_3']

    user_1_memberships_edges = user_1['SomeMemberships']['edges']
    is_moderator_values = [
        e['node']['isModerator'] for e in user_1_memberships_edges
    ]
    assert is_moderator_values == [True, False, False]


@pytest.mark.skipif(
    graphene_sqlalchemy_version_lt_2_1_2, reason='not supported'
)
def test_nested_response_with_filters(session):
    users = add_users(session)
    add_users_to_new_groups(session, users)
    session.commit()

    request_string = """{
            field(filters:{username: "user_1"}){
                edges{
                    node{
                        username
                        memberships(filters:{isModerator: true}){
                            edges{
                                node{
                                    isModerator
                                }
                            }
                        }
                    }
                }
            }
        }"""
    with SQLAlchemyQueryCounter(session, 3):
        execution_result = schema.execute(
            request_string, context={'session': session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert 'field' in execution_result.data

    field = execution_result.data['field']
    assert 'edges' in field

    edges = field['edges']
    assert len(edges) == 1
    user_0 = edges[0]['node']

    user_0_memberships_edges = user_0['memberships']['edges']
    assert len(user_0_memberships_edges) == 1
    is_moderator_value = user_0_memberships_edges[0]['node']['isModerator']
    assert is_moderator_value is True


@pytest.mark.skipif(
    graphene_sqlalchemy_version_lt_2_1_2, reason='not supported'
)
def test_nested_response_with_recursive_model(session):
    add_groups(session, with_parent_group=True)
    session.commit()

    request_string = """{
            allGroups(filters:{parentGroupIdIsNull: true}){
                edges{
                    node{
                        subGroups(
                            filters: {
                                or: [{name: "group_1"}, {name: "group_2"}]
                            },
                            sort: NAME_DESC
                        ){
                            edges{
                                node{
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }"""
    with SQLAlchemyQueryCounter(session, 3):
        execution_result = schema.execute(
            request_string, context={'session': session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert 'allGroups' in execution_result.data

    field = execution_result.data['allGroups']
    assert 'edges' in field

    edges = field['edges']
    assert len(edges) == 1
    group_0 = edges[0]['node']

    group_0_sub_groups_edges = group_0['subGroups']['edges']
    assert len(group_0_sub_groups_edges) == 2
    sub_group_name = group_0_sub_groups_edges[0]['node']['name']
    assert sub_group_name == 'group_2'


def test_relationship_filtering(session):
    users = add_users(session)
    assign_users_to_tasks(session, users)
    session.commit()

    request_string = """{
        field(filters: {
            assignments: {
                 and: [
                    {
                         task: {
                            name: "Write code",
                        }
                    },
                    {
                        active: true
                    }
                ]
            }
        }){
            edges{
                node{
                    username
                    assignments{
                        edges{
                            node{
                                active
                                task {
                                    name
                                }
                            }
                        }
                    }
                }
            }
        }
    }"""

    execution_result = schema.execute(
        request_string, context={'session': session}
    )
    edges = execution_result.data["field"]["edges"]
    assert len(execution_result.data["field"]["edges"]) == 1
    assert edges[0]["node"]["username"] == "user_1"
    assert len(edges[0]["node"]["assignments"]["edges"]) == 2
