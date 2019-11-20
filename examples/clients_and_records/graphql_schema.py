# GraphQL
import graphene
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType

# Project
from filters import MyFilterableConnectionField
from models import Clients, Records


class ClientsNode(SQLAlchemyObjectType):
    class Meta:
        model = Clients
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class ClientsConnection(Connection):
    class Meta:
        node = ClientsNode


class RecordsNode(SQLAlchemyObjectType):
    class Meta:
        model = Records
        interfaces = (Node,)
        connection_field_factory = MyFilterableConnectionField.factory


class RecordsConnection(Connection):
    class Meta:
        node = RecordsNode


class Query(graphene.ObjectType):
    client = graphene.relay.Node.Field(ClientsNode)
    all_clients = MyFilterableConnectionField(ClientsConnection)

    record = graphene.relay.Node.Field(RecordsNode)
    all_records = MyFilterableConnectionField(RecordsConnection)


schema = graphene.Schema(query=Query)
