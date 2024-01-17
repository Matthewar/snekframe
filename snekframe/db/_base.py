"""Base classes required for database operation"""
# pylint: disable=too-few-public-methods

import os.path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from .. import params

class PersistentBase(DeclarativeBase):
    """Program Base DB Class"""

class SharedBase(DeclarativeBase):
    """Permanent and Runtime DB Class"""

PERSISTENT_ENGINE = create_engine("sqlite:///{}".format(os.path.join(params.FILES_LOCATION, params.DATABASE_NAME)))
PERSISTENT_SESSION = sessionmaker(PERSISTENT_ENGINE)

RUNTIME_ENGINE = create_engine("sqlite://")
RUNTIME_SESSION = sessionmaker(RUNTIME_ENGINE)

class DeprecatedPersistentOrSharedBase(DeclarativeBase):
    """Deprecated Permanent Database Definitions"""
