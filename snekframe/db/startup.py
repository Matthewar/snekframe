"""Startup Processes"""

import os

from . import _base as db, SettingsV0
from .runtime import RuntimeBase
from .version import DatabaseVersion
from .. import params

def create_database_file():
    """Generate the persistent database file and directories as required"""
    os.makedirs(params.FILES_LOCATION, exist_ok=True)

    db.PersistentBase.metadata.create_all(db.PERSISTENT_ENGINE)
    db.SharedBase.metadata.create_all(db.PERSISTENT_ENGINE)

    with db.PERSISTENT_SESSION() as session:
        session.add(DatabaseVersion())
        session.add(SettingsV0())
        session.commit()

def intialise_runtimes():
    """Setup runtime database"""
    RuntimeBase.metadata.create_all(db.RUNTIME_ENGINE)
