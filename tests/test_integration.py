import pytest

from graphene_sqlalchemy_filter.connection_field import (
    graphene_sqlalchemy_version_lt_2_1_2,
)

from .graphql_objects import schema
from .models import Article, Author, Group, Membership, User
from .utils import SQLAlchemyQueryCounter


def add_users(session):
    users = [
        User(username="user_1", is_active=True, balance=0),
        User(username="user_2", is_active=True),
    ]
    session.bulk_save_objects(users, return_defaults=True)
    return users


def add_groups(session, with_parent_group=False):
    parent_group_id = None

    if with_parent_group:
        parent_group = Group(name="parent")
        session.add(parent_group)
        session.flush()

        parent_group_id = parent_group.id

    groups = [
        Group(name="group_1", parent_group_id=parent_group_id),
        Group(name="group_2", parent_group_id=parent_group_id),
        Group(name="group_3", parent_group_id=parent_group_id),
    ]
    session.bulk_save_objects(groups, return_defaults=True)
    session.flush()

    return groups


def add_authors(session):
    authors = [
        Author(first_name="John", last_name="Doe", is_active=True),
        Author(first_name="Alice", last_name="Smith", is_active=False),
    ]
    session.bulk_save_objects(authors, return_defaults=True)
    session.flush()
    return authors


def add_articles(session, authors):
    articles = [
        Article(
            author_first_name=author.first_name,
            author_last_name=author.last_name,
            text="Text",
        )
        for author in authors
    ]
    session.bulk_save_objects(articles, return_defaults=True)
    session.flush()
    return articles


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


def test_response_without_filters(session):
    add_users(session)
    session.commit()

    with SQLAlchemyQueryCounter(session, 2):
        execution_result = schema.execute(
            "{field{edges{node{username}}}}", context={"session": session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert "field" in execution_result.data

    field = execution_result.data["field"]
    assert "edges" in field

    edges = field["edges"]
    expected_edges_count = 2
    assert len(edges) == expected_edges_count

    node = edges[0]["node"]
    assert node == {"username": "user_1"}

    node = edges[1]["node"]
    assert node == {"username": "user_2"}


def test_response_with_default_filter(session):
    authors = add_authors(session)
    add_articles(session, authors)
    session.commit()

    with SQLAlchemyQueryCounter(session, 4):
        execution_result = schema.execute(
            """{
                allAuthors{edges{node{firstName lastName}}}
                allArticles{edges{node{authorFirstName}}}
            }""",
            context={"session": session},
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert "allAuthors" in execution_result.data

    all_authors = execution_result.data["allAuthors"]
    assert "edges" in all_authors

    authors_edges = all_authors["edges"]
    expected_authors_edges_count = 1
    assert len(authors_edges) == expected_authors_edges_count

    author_node = authors_edges[0]["node"]
    assert author_node == {"firstName": "John", "lastName": "Doe"}

    assert "allArticles" in execution_result.data
    all_articles = execution_result.data["allArticles"]
    assert "edges" in all_articles
    articles_edges = all_articles["edges"]
    expected_articles_edges_count = 1
    assert len(articles_edges) == expected_articles_edges_count

    article_node = articles_edges[0]["node"]
    assert article_node == {"authorFirstName": "John"}


def test_response_with_filters(session):
    add_users(session)
    session.commit()

    request_string = (
        '{field(filters:{username: "user_1"}){edges{node{username balance}}}}'
    )
    with SQLAlchemyQueryCounter(session, 2):
        execution_result = schema.execute(
            request_string, context={"session": session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert "field" in execution_result.data

    field = execution_result.data["field"]
    assert "edges" in field

    edges = field["edges"]
    assert len(edges) == 1

    node = edges[0]["node"]
    assert node == {"username": "user_1", "balance": 0}


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
    # 5 - if graphene_sqlalchemy_filter.ModelLoader used
    query_count = 8 if graphene_sqlalchemy_version_lt_2_1_2 else 5

    with SQLAlchemyQueryCounter(session, query_count):
        execution_result = schema.execute(
            request_string, context={"session": session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert "field" in execution_result.data

    field = execution_result.data["field"]
    assert "edges" in field

    edges = field["edges"]
    expected_edges_count = 2
    assert len(edges) == expected_edges_count
    user_0 = edges[0]["node"]
    user_1 = edges[1]["node"]

    user_0_memberships_edges = user_0["SomeMemberships"]["edges"]
    is_moderator_values_1 = [
        e["node"]["isModerator"] for e in user_0_memberships_edges
    ]
    assert is_moderator_values_1 == [False, True, False]

    user_0_created_memberships_edges = user_0["createdMemberships"]["edges"]
    is_moderator_values_2 = [
        e["node"]["isModerator"] for e in user_0_created_memberships_edges
    ]
    assert is_moderator_values_2 == [False, True, False, True]

    user_0_groups_edges = user_0["groups"]["edges"]
    groups = [e["node"]["name"] for e in user_0_groups_edges]
    assert groups == ["group_1", "group_2", "group_3"]

    user_1_memberships_edges = user_1["SomeMemberships"]["edges"]
    is_moderator_values = [
        e["node"]["isModerator"] for e in user_1_memberships_edges
    ]
    assert is_moderator_values == [True, False, False]


@pytest.mark.skipif(
    graphene_sqlalchemy_version_lt_2_1_2, reason="not supported"
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
            request_string, context={"session": session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert "field" in execution_result.data

    field = execution_result.data["field"]
    assert "edges" in field

    edges = field["edges"]
    assert len(edges) == 1
    user_0 = edges[0]["node"]

    user_0_memberships_edges = user_0["memberships"]["edges"]
    assert len(user_0_memberships_edges) == 1
    is_moderator_value = user_0_memberships_edges[0]["node"]["isModerator"]
    assert is_moderator_value is True


@pytest.mark.skipif(
    graphene_sqlalchemy_version_lt_2_1_2, reason="not supported"
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
                            sort: ID_DESC
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
            request_string, context={"session": session}
        )

        assert not execution_result.errors
        assert not execution_result.invalid

        assert execution_result.data

    assert "allGroups" in execution_result.data

    field = execution_result.data["allGroups"]
    assert "edges" in field

    edges = field["edges"]
    assert len(edges) == 1
    group_0 = edges[0]["node"]

    group_0_sub_groups_edges = group_0["subGroups"]["edges"]
    sub_groups_expected_count = 2
    assert len(group_0_sub_groups_edges) == sub_groups_expected_count
    sub_group_name = group_0_sub_groups_edges[0]["node"]["name"]
    assert sub_group_name == "group_2"
