# Standard Library
import enum

# Third Party
from sqlalchemy_bulk_lazy_loader import BulkLazyLoader

# Database
from sqlalchemy import Boolean, Column, Enum, Integer, String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.ext.hybrid import hybrid_property


BulkLazyLoader.register_loader()


Base = declarative_base()


class StatusEnum(enum.Enum):
    offline = 'offline'
    online = 'online'


class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True, autoincrement=True)
    username = Column(String(50), nullable=False, unique=True, index=True)
    balance = Column(Integer, default=None)
    is_active = Column(Boolean, default=True)
    status = Column(Enum(StatusEnum), default='offline')

    @hybrid_property
    def is_online(self):
        return self.status == StatusEnum.online
