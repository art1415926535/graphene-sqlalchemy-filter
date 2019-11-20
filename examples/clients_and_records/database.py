# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Project
from models import Base, Clients, Records


engine = create_engine('sqlite:///database.sqlite3', echo=True)
db_session = scoped_session(sessionmaker(bind=engine))
Base.query = db_session.query_property()


def add_clients():
    clients = [
        Clients(name='Ally'),
        Clients(name='Blayze'),
        Clients(name='Courtney'),
        Clients(name='Delmer'),
    ]
    db_session.bulk_save_objects(clients, return_defaults=True)
    return clients


def add_records(clients):
    records = [
        Records(client_id=client.id) for client in clients for _ in range(3)
    ]
    db_session.bulk_save_objects(records, return_defaults=True)
    db_session.flush()
    return records


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    clients = add_clients()
    add_records(clients)
    db_session.commit()
