# Database
# Third Party
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

from sqlalchemy import Boolean, Column, ForeignKey, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship


BulkLazyLoader.register_loader()


Base = declarative_base()


class Membership(Base):
    __tablename__ = 'member'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey('user.id'))
    group_id = Column(ForeignKey('group.id'))
    is_moderator = Column(Boolean, nullable=False, default=False)
    creator_username = Column(ForeignKey('user.username'))


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=None)
    is_active = Column(Boolean, default=True)

    memberships = relationship(
        'Membership',
        lazy='bulk',
        primaryjoin=id == Membership.user_id,
        backref=backref('user', lazy='bulk'),
    )
    created_memberships = relationship(
        'Membership',
        lazy='bulk',
        primaryjoin=username == Membership.creator_username,
        backref=backref('creator', lazy='bulk'),
    )
    groups = relationship(
        'Group',
        lazy='bulk',
        primaryjoin=id == Membership.user_id,
        secondary='member',
        backref=backref('users', lazy='bulk'),
    )


class Group(Base):
    __tablename__ = 'group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)

    memberships = relationship(
        'Membership', lazy='bulk', backref=backref('group', lazy='bulk')
    )
