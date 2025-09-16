import enum
from random import choice

from flask import Flask
from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    Integer,
    String,
    and_,
    create_engine,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship, scoped_session, sessionmaker
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


class Membership(Base):
    __tablename__ = "member"

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey("user.id"))
    group_id = Column(ForeignKey("group.id"))
    is_moderator = Column(Boolean, nullable=False, default=False)
    creator_username = Column(ForeignKey("user.username"))


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

    memberships = relationship(
        "Membership",
        lazy="bulk",
        primaryjoin=id == Membership.user_id,
        backref=backref("user", lazy="bulk"),
    )
    created_memberships = relationship(
        "Membership",
        lazy="bulk",
        primaryjoin=username == Membership.creator_username,
        backref=backref("creator", lazy="bulk"),
    )
    groups = relationship(
        "Group",
        lazy="bulk",
        primaryjoin=id == Membership.user_id,
        secondary="member",
        backref=backref("users", lazy="bulk"),
    )


class Group(Base):
    __tablename__ = "group"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)

    memberships = relationship(
        "Membership", lazy="bulk", backref=backref("group", lazy="bulk")
    )


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    users = [
        User(username="Ally", is_active=True, status="online"),
        User(username="Blayze", is_active=True, balance=0),
        User(username="Courtney", is_active=False, balance=100),
        User(username="Delmer", is_active=True, balance=9000),
    ]
    groups = [
        Group(name="Python"),
        Group(name="GraphQL"),
        Group(name="SQLAlchemy"),
        Group(name="PostgreSQL"),
    ]
    session = db_session()
    session.bulk_save_objects(users, return_defaults=True)
    session.bulk_save_objects(groups, return_defaults=True)
    memberships = [
        Membership(
            user_id=user.id,
            group_id=group.id,
            is_moderator=user.id == group.id,
            creator_username=choice(users).username,  # noqa: S311
        )
        for user in users
        for group in groups
    ]
    session.bulk_save_objects(memberships)
    session.commit()
    session.close()


# GraphQL schema
class BaseFilter(FilterSet):
    EXTRA_EXPRESSIONS = {
        "zero": {
            "graphql_name": "eq_zero",
            "for_types": [Integer],
            "filter": lambda f, v: f == 0 if v else f != 0,
            "input_type": (lambda t, n, d: graphene.Boolean(nullable=False)),
            "description": "Equal to zero.",
        }
    }

    class Meta:
        abstract = True


class UserFilter(BaseFilter):
    is_admin = graphene.Boolean(description="username = admin")
    is_moderator = graphene.Boolean(description="User is a moderator")
    member_of_group = graphene.String(
        description="Member of the group that is named"
    )

    @staticmethod
    def _default_filter(info, query):
        return User.is_active.is_(True)

    @staticmethod
    def is_admin_filter(info, query, value):
        """Simple filter return only clause."""
        if value:
            return User.username == "admin"

        return User.username != "admin"

    @classmethod
    def is_moderator_filter(cls, info, query, value):
        membership = cls.aliased(query, Membership, name="is_moderator")

        query = query.join(
            membership,
            and_(
                User.id == membership.user_id,
                membership.is_moderator.is_(True),
            ),
        )

        if value:
            filter_ = membership.id.isnot(None)
        else:
            filter_ = membership.id.is_(None)
        return query, filter_

    @classmethod
    def member_of_group_filter(cls, info, query, value):
        membership = cls.aliased(query, Membership, name="member_of")
        group = cls.aliased(query, Group, name="of_group")

        query = query.join(membership, User.memberships).join(
            group, membership.group
        )

        return query, group.name == value

    class Meta:
        model = User
        fields = {
            "username": ["eq", "ne", "in", "ilike"],
            "balance": [...],
            "status": ["eq"],
            "is_online": ["eq", "ne"],
        }


class MembershipFilter(BaseFilter):
    class Meta:
        model = Membership
        fields = {"is_moderator": [...]}


class GroupFilter(BaseFilter):
    class Meta:
        model = Group
        fields = {"name": [...]}


class MyFilterableConnectionField(FilterableConnectionField):
    filters = {
        User: UserFilter(),
        Membership: MembershipFilter(),
        Group: GroupFilter(),
    }


class UserNode(SQLAlchemyObjectType):
    class Meta:
        model = User
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class UserConnection(Connection):
    class Meta:
        node = UserNode


class MembershipNode(SQLAlchemyObjectType):
    class Meta:
        model = Membership
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class MembershipConnection(Connection):
    class Meta:
        node = MembershipNode


class GroupNode(SQLAlchemyObjectType):
    class Meta:
        model = Group
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class GroupConnection(Connection):
    class Meta:
        node = GroupNode


class Query(graphene.ObjectType):
    user = graphene.Node.Field(UserNode)
    all_users = MyFilterableConnectionField(UserConnection)

    group = graphene.Node.Field(GroupNode)
    all_groups = MyFilterableConnectionField(GroupConnection)

    membership = graphene.Node.Field(MembershipNode)
    all_memberships = MyFilterableConnectionField(MembershipConnection)


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
