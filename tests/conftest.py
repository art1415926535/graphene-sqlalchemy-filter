# GraphQL
from graphene import Schema
from graphql import ResolveInfo

# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Project
import pytest
from tests.graphql_objects import Query
from tests.models import Base


@pytest.yield_fixture(scope="function")
def session():
    db = create_engine('sqlite://')  # in-memory
    connection = db.engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(connection)

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session

    transaction.rollback()
    connection.close()
    session.remove()


@pytest.yield_fixture(scope="function")
def info():
    db = create_engine('sqlite://')  # in-memory
    connection = db.engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(connection)

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield ResolveInfo(*[None] * 9, context={'session': session})

    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture(scope='function')
def filterable_connection_field():
    return Query.field


@pytest.fixture(scope='function')
def schema():
    return Schema(query=Query)
