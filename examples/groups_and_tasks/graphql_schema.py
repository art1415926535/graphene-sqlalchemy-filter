# GraphQL
import graphene
from graphene import Connection, relay
from graphene_sqlalchemy import SQLAlchemyObjectType

# Project
from filters import GroupFilterableConnectionField
from models import TaskModel, GroupModel


class TaskFilter(SQLAlchemyObjectType):
    class Meta:
        model = TaskModel
        interfaces = (relay.Node, )
        connection_field_factory = GroupFilterableConnectionField.factory


class TaskFilterConnection_1(Connection):
    class Meta:
        node = TaskFilter


class GroupFilterNode(SQLAlchemyObjectType):
    class Meta:
        model = GroupModel
        interfaces = (relay.Node, )
        connection_field_factory = GroupFilterableConnectionField.factory


class GroupFilterConnection(Connection):
    class Meta:
        node = GroupFilterNode


class Query(graphene.ObjectType):
    all_task = GroupFilterableConnectionField(TaskFilterConnection_1)
    all_group_filters = GroupFilterableConnectionField(
        GroupFilterConnection
    )
    filter_group = relay.Node.Field(GroupFilterNode)


schema = graphene.Schema(query=Query)
