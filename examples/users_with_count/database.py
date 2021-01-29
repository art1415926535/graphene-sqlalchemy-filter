# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Project
from models import Base, User


engine = create_engine('sqlite:///database.sqlite3', echo=True)  # in-memory
db_session = scoped_session(sessionmaker(bind=engine))
Base.query = db_session.query_property()


def add_users():
    users = [
        User(username='Ally', is_active=True, status='online'),
        User(username='Blayze', is_active=True, balance=0),
        User(username='Courtney', is_active=False, balance=100),
        User(username='Delmer', is_active=True, balance=9000),
    ]
    db_session.bulk_save_objects(users, return_defaults=True)
    return users


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    add_users()
    db_session.commit()
