# GraphQL
import graphene
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType

# Project
from filters import MyFilterableConnectionField
from models import User


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
    user = graphene.relay.Node.Field(UserNode)
    all_users = MyFilterableConnectionField(UserConnection)


schema = graphene.Schema(query=Query)
