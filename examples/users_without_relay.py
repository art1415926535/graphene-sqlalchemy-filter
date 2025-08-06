import enum

import uvicorn
from sqlalchemy import Column, Enum, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader
from starlette.applications import Starlette

import graphene
from starlette_graphene3 import GraphQLApp, make_playground_handler

from graphene_sqlalchemy_filter import FilterSet


BulkLazyLoader.register_loader()


# Database and models
engine = create_engine(
    "sqlite:///:memory:",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=True,
)
db_session = scoped_session(sessionmaker(bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class StatusEnum(enum.Enum):
    offline = "offline"
    online = "online"


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=None)
    type = Column(String, nullable=True)
    status = Column(Enum(StatusEnum), default=None, nullable=True)


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    users = [
        User(username="Ally", type="human", status=StatusEnum.online),
        User(username="Blayze", balance=0, status=StatusEnum.offline),
        User(username="Courtney", balance=100),
        User(username="Delmer", balance=9000),
    ]
    session = db_session()
    session.bulk_save_objects(users)
    session.commit()
    session.close()


# GraphQL schema
class UserFilter(FilterSet):
    is_admin = graphene.Boolean(description="username = admin")

    @staticmethod
    def is_admin_filter(info, query, value):
        """Simple filter return only clause."""
        if value:
            return User.username == "admin"

        return User.username != "admin"

    class Meta:
        model = User
        fields = {
            "username": ["eq", "ne", "in", "ilike"],
            "balance": [...],
            "type": [...],
            "status": [...],
        }


class UserType(graphene.ObjectType):
    id = graphene.Int()
    username = graphene.String()
    balance = graphene.Int()


class Query(graphene.ObjectType):
    all_users = graphene.List(UserType, filters=UserFilter())

    def resolve_all_users(self, info, filters=None):
        query = User.query
        if filters is not None:
            query = UserFilter.filter(info, query, filters)

        return query


# Server
app = Starlette()
app.mount(
    "/",
    GraphQLApp(graphene.Schema(query=Query), on_get=make_playground_handler()),
)


if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
