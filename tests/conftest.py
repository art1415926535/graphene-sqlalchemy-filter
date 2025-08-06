import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool

from graphene_sqlalchemy_filter.versions import graphql_version_lt_3_0_0

from tests import models
from tests.models import Base


try:
    from graphql import ResolveInfo

    class Path:
        def __init__(self):
            raise NotImplementedError(
                "Path is not implemented in this context"
            )
except ImportError:
    from graphql import GraphQLResolveInfo as ResolveInfo
    from graphql.pyutils.path import Path


@pytest.fixture
def session():
    db = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
        echo=True,
    )
    connection = db.engine.connect()
    transaction = connection.begin()
    Base.metadata.create_all(connection)

    session_factory = sessionmaker(bind=connection)
    session = scoped_session(session_factory)

    yield session

    transaction.rollback()
    connection.close()
    session.remove()


@pytest.fixture
def user_query(session):
    return session.query(models.User)


@pytest.fixture
def info_builder(session):
    """Fixture to provide a base ResolveInfo object."""

    def _builder(**kwargs):
        if graphql_version_lt_3_0_0:
            params = {
                "field_name": None,
                "field_asts": None,
                "return_type": None,
                "parent_type": None,
                "schema": None,
                "fragments": None,
                "root_value": None,
                "operation": None,
                "variable_values": None,
                "context": {"session": session},
                "path": None,
            }
            params.update(kwargs)
            return ResolveInfo(**params)

        path_array = kwargs.pop("path", None)

        path = []
        for item in path_array or []:
            if not path:
                path.append(Path(None, item, None))
            else:
                path.append(path[-1].add_key(item))

        params = {
            "field_name": None,
            "field_nodes": None,
            "return_type": None,
            "parent_type": None,
            "path": path,
            "schema": None,
            "fragments": None,
            "root_value": None,
            "operation": None,
            "variable_values": None,
            "context": {"session": session},
            "is_awaitable": None,
        }
        params.update(kwargs)

        return ResolveInfo(**params)

    return _builder


@pytest.fixture
def info(info_builder):
    return info_builder()


@pytest.fixture
def info_and_user_query(info_builder, user_query):
    return info_builder(), user_query
