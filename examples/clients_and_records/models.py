# Third Party
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

# Database
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, foreign, relationship


BulkLazyLoader.register_loader()


Base = declarative_base()


class Clients(Base):
    __tablename__ = 'clients'

    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False, index=True)


class Transactions(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True)


class Records(Transactions):
    __tablename__ = 'records'

    client_id = Column('client', Integer, nullable=False, index=True)

    client = relationship(
        'Clients',
        lazy='bulk',
        primaryjoin=foreign(client_id) == Clients.id,
        backref=backref('records', lazy='bulk'),
    )
