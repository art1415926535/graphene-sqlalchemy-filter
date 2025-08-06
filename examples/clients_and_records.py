import uvicorn
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import (
    backref,
    foreign,
    relationship,
    scoped_session,
    sessionmaker,
)
from sqlalchemy.pool import StaticPool
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader
from starlette.applications import Starlette

import graphene
from graphene import Connection, Node
from graphene_sqlalchemy import SQLAlchemyObjectType
from starlette_graphene3 import GraphQLApp, make_playground_handler

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


class Clients(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)


class Transactions(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)


class Records(Transactions):
    __tablename__ = "records"

    client_id = Column("client", Integer, nullable=False, index=True)

    client = relationship(
        "Clients",
        lazy="bulk",
        primaryjoin=foreign(client_id) == Clients.id,
        backref=backref("records", lazy="bulk"),
    )


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    clients = [
        Clients(name="Ally"),
        Clients(name="Blayze"),
        Clients(name="Courtney"),
        Clients(name="Delmer"),
    ]
    session = db_session()
    session.bulk_save_objects(clients, return_defaults=True)
    records = [
        Records(client_id=client.id) for client in clients for _ in range(3)
    ]
    session.bulk_save_objects(records)
    session.commit()
    session.close()


# GraphQL schema
class ClientsFilter(FilterSet):
    class Meta:
        model = Clients
        fields = {"name": ["eq", "ne", "in", "ilike"]}


class RecordsFilter(FilterSet):
    class Meta:
        model = Records
        fields = {"id": [...]}


class MyFilterableConnectionField(FilterableConnectionField):
    filters = {Clients: ClientsFilter(), Records: RecordsFilter()}


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
    client = graphene.Node.Field(ClientsNode)
    all_clients = MyFilterableConnectionField(ClientsConnection)

    record = graphene.Node.Field(RecordsNode)
    all_records = MyFilterableConnectionField(RecordsConnection)


# Server
app = Starlette()
app.mount(
    "/",
    GraphQLApp(graphene.Schema(query=Query), on_get=make_playground_handler()),
)


if __name__ == "__main__":
    init_db()
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")
