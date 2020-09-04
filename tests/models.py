# Standard Library
import enum

# Database
from sqlalchemy import (
    Boolean,
    Column,
    Enum,
    ForeignKey,
    ForeignKeyConstraint,
    Integer,
    String,
    func,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import backref, relationship

# Project
from tests import gqls_version


Base = declarative_base()


class Membership(Base):
    __tablename__ = 'member'

    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(ForeignKey('user.user_id'))
    group_id = Column(ForeignKey('group.id'))
    is_moderator = Column(Boolean, nullable=False, default=False)

    creator_username = Column(ForeignKey('user.username'))


class StatusEnum(enum.Enum):
    offline = 'offline'
    online = 'online'


class User(Base):
    __tablename__ = 'user'

    id = Column('user_id', Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=None)
    is_active = Column(Boolean, default=True)
    if gqls_version >= (2, 2, 0):
        status = Column(Enum(StatusEnum), default=StatusEnum.offline)

    @hybrid_property
    def username_hybrid_property(self):
        return func.lower(self.username)

    memberships = relationship(
        'Membership',
        primaryjoin=id == Membership.user_id,
        backref=backref('user'),
    )
    created_memberships = relationship(
        'Membership',
        primaryjoin=username == Membership.creator_username,
        backref=backref('creator'),
    )
    groups = relationship(
        'Group', primaryjoin=id == Membership.user_id, secondary='member'
    )


class Group(Base):
    __tablename__ = 'group'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(50), nullable=False, unique=True, index=True)
    parent_group_id = Column(Integer, ForeignKey('group.id'))

    memberships = relationship('Membership', backref=backref('group'))
    sub_groups = relationship(
        'Group', backref=backref('parent_group', remote_side=[id])
    )


class Author(Base):
    __tablename__ = 'author'

    first_name = Column(String(50), primary_key=True)
    last_name = Column(String(50), primary_key=True)

    articles = relationship('Article', back_populates='author')


class Article(Base):
    __tablename__ = 'article'

    id = Column(Integer, primary_key=True)
    text = Column(String(500))
    author_first_name = Column(String(50))
    author_last_name = Column(String(50))

    __table_args__ = (
        ForeignKeyConstraint(
            ('author_first_name', 'author_last_name'),
            ('author.first_name', 'author.last_name'),
        ),
    )

    author = relationship('Author', back_populates='articles')
