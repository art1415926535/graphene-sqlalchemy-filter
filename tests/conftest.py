# Third Party
import pytest

# GraphQL
from graphql import GraphQLResolveInfo

# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Project
from tests import models
from tests.models import Base


@pytest.fixture(scope="function")
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


@pytest.fixture(scope="function")
def info():
    db = create_engine('sqlite://')  # in-memory
    connection = db.engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(connection)

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield GraphQLResolveInfo(*[None] * 9, context={'session': session})

    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture(scope="function")
def info_and_user_query():
    db = create_engine('sqlite://')  # in-memory
    connection = db.engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(connection)

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    info = GraphQLResolveInfo(*[None] * 9, context={'session': session})
    user_query = session.query(models.User)

    yield info, user_query

    transaction.rollback()
    connection.close()
    session.remove()
