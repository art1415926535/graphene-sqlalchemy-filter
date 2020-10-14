# Database
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Project
from models import GroupModel, TaskModel, Base


engine = create_engine('sqlite:///database.sqlite3', echo=True)  # in-memory
db_session = scoped_session(sessionmaker(bind=engine))
Base.query = db_session.query_property()


def add_groups():
    groups = [
        GroupModel(name='Ally'),
        GroupModel(name='Blayze'),
        GroupModel(name='Courtney'),
        GroupModel(name='Delmer'),
    ]
    db_session.bulk_save_objects(groups, return_defaults=True)
    return groups


def add_tasks(groups):
    tasks = [
        TaskModel(
            group_id=group.id,
            title="Title: " + group.name,
            done=bool(i % 2),
            categories="Category: " + group.name,
        )
        for i, group in enumerate(groups)
    ]
    db_session.bulk_save_objects(tasks, return_defaults=True)
    db_session.flush()
    return tasks


def init_db():
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    groups = add_groups()
    add_tasks(groups)
    db_session.commit()
