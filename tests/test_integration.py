# Project
from tests.models import User


def test_empty_response(schema, session):
    session.add(User(username='user_1', is_active=True, balance=0))
    session.add(User(username='user_2', is_active=True))
    session.commit()

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


def test_data_response_and_filtration(schema, session):
    session.add(User(username='user_1', is_active=True, balance=0))
    session.add(User(username='user_2', is_active=True))
    session.commit()

    execution_result = schema.execute(
        '{field(filters:{username: "user_1"}){edges{node{username balance}}}}',
        context={'session': session},
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
