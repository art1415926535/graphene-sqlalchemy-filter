# GraphQL
import graphene
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType

# Project
from filters import MyFilterableConnectionField
from models import Group, Membership, User


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
    user = graphene.relay.Node.Field(UserNode)
    all_users = MyFilterableConnectionField(UserConnection)

    group = graphene.relay.Node.Field(GroupNode)
    all_groups = MyFilterableConnectionField(GroupConnection)

    membership = graphene.relay.Node.Field(MembershipNode)
    all_memberships = MyFilterableConnectionField(MembershipConnection)


schema = graphene.Schema(query=Query)
