import enum

from flask import Flask
from sqlalchemy import Boolean, Column, Enum, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

import graphene
from flask_graphql import GraphQLView
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType

from graphene_sqlalchemy_filter import FilterableConnectionField, FilterSet


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
    is_active = Column(Boolean, default=True)
    status = Column(Enum(StatusEnum), default="offline")

    @hybrid_property
    def is_online(self):
        return self.status == StatusEnum.online


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    users = [
        User(username="Ally", is_active=True, status="online"),
        User(username="Blayze", is_active=True, balance=0),
        User(username="Courtney", is_active=False, balance=100),
        User(username="Delmer", is_active=True, balance=9000),
    ]
    session = db_session()
    session.bulk_save_objects(users)
    session.commit()
    session.close()


# GraphQL schema
class UserFilter(FilterSet):
    class Meta:
        model = User
        fields = {"username": ["eq"]}


class MyFilterableConnectionField(FilterableConnectionField):
    filters = {User: UserFilter()}


class TotalCount(graphene.Interface):
    total_count = graphene.Int()

    def resolve_total_count(self, info):
        return self.length


class UserNode(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class UserConnection(Connection):
    class Meta:
        node = UserNode
        interfaces = (TotalCount,)


class Query(graphene.ObjectType):
    user = graphene.Node.Field(UserNode)
    all_users = MyFilterableConnectionField(UserConnection)


# Server
app = Flask(__name__)
app.add_url_rule(
    "/graphql",
    view_func=GraphQLView.as_view(
        "graphql", schema=graphene.Schema(query=Query), graphiql=True
    ),
)


@app.teardown_appcontext
def shutdown_session(exception=None):
    db_session.remove()


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
