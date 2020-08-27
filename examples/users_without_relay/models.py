# Third Party
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

# Database
from sqlalchemy import Column, Integer, String
from sqlalchemy.ext.declarative import declarative_base


BulkLazyLoader.register_loader()


Base = declarative_base()


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=None)
    type = Column(String, nullable=True)
