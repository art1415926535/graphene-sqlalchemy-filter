from flask import Flask
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker
from sqlalchemy.pool import StaticPool
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

import graphene
from flask_graphql import GraphQLView

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


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=None)
    type = Column(String, nullable=True)


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    users = [
        User(username="Ally", type="human"),
        User(username="Blayze", balance=0),
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
