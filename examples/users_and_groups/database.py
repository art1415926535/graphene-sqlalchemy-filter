# Standard Library
from random import choice

# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Project
from models import Base, Group, Membership, User


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


def add_users_to_new_groups(users):
    groups = [
        Group(name='Python'),
        Group(name='GraphQL'),
        Group(name='SQLAlchemy'),
        Group(name='PostgreSQL'),
    ]
    db_session.bulk_save_objects(groups, return_defaults=True)
    db_session.flush()

    memberships = [
        Membership(
            user_id=user.id,
            group_id=group.id,
            is_moderator=user.id == group.id,
            creator_username=choice(users).username,
        )
        for user in users
        for group in groups
    ]
    db_session.bulk_save_objects(memberships, return_defaults=True)
    db_session.flush()
    return groups


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    users = add_users()
    add_users_to_new_groups(users)
    db_session.commit()
