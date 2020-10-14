# Third Party
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

# Database
from sqlalchemy import Column, Integer, Text, ForeignKey, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, backref

BulkLazyLoader.register_loader()


Base = declarative_base()


class GroupModel(Base):
    __tablename__ = "groups"
    id = Column(Integer, primary_key=True)
    name = Column(Text, index=True)
    tasks = relationship(
        "TaskModel",
        backref=backref("circle", lazy='bulk'),
        lazy='bulk',
        cascade="all, delete-orphan",
    )


class TaskModel(Base):
    __tablename__ = "tasks"
    id = Column(Integer, primary_key=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    title = Column(Text, nullable=False)
    done = Column(Boolean, nullable=False, index=True)
    categories = Column(Text, default="General")
