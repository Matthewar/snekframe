"""Base classes required for database operation"""
# pylint: disable=too-few-public-methods

import os.path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import StaticPool

from .. import params

class PersistentBase(DeclarativeBase):
    """Program Base DB Class"""

class SharedBase(DeclarativeBase):
    """Permanent and Runtime DB Class"""

DATABASE_FILE_PATH = os.path.join(params.FILES_LOCATION, params.DATABASE_NAME)
BACKUP_DATABASE_FILE_PATH = f"{DATABASE_FILE_PATH}.bak"

PERSISTENT_ENGINE = create_engine(f"sqlite:///{DATABASE_FILE_PATH}")
PERSISTENT_SESSION = sessionmaker(PERSISTENT_ENGINE)

RUNTIME_ENGINE = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool
)
RUNTIME_SESSION = sessionmaker(RUNTIME_ENGINE)

class DeprecatedPersistentOrSharedBase(DeclarativeBase):
    """Deprecated Permanent Database Definitions"""
