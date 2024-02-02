"""Functions for upgrading the database"""

import shutil

from sqlalchemy.sql.expression import select

from .version import get_database_version
from ._base import PERSISTENT_SESSION, PERSISTENT_ENGINE, DATABASE_FILE_PATH, BACKUP_DATABASE_FILE_PATH
from . import _v0 as v0, _v1 as v1

def _upgrade_v0_to_v1():
    """Upgrade the database to the latest version"""
    v1.PhotoList.__table__.create(PERSISTENT_ENGINE)

    with PERSISTENT_SESSION() as session:
        current_display = session.scalars(select(v0.CurrentDisplay)).one_or_none()
        if current_display is not None:
            all_photos = current_display.all_photos
            album = current_display.album
        else:
            all_photos = False
            album = None

        query = session.scalars(select(v0.PhotoList))
        for row in query:
            session.add(
                v1.PhotoList(
                    filename=row.filename,
                    path=row.album,
                    selected=all_photos or (album is not None and row.album == album)
                )
            )
        session.commit()

    v0.PhotoList.__table__.drop(PERSISTENT_ENGINE)
    v0.CurrentDisplay.__table__.drop(PERSISTENT_ENGINE)

def upgrade_database():
    """Upgrade the database to the latest version"""
    version_major, version_minor = get_database_version()

    upgrades_required = []

    if version_major == 0:
        if version_minor == 0:
            upgrades_required.append(_upgrade_v0_to_v1)
        else:
            raise Exception(f"Unknown database version v0.{version_minor}")
    else:
        raise Exception(f"Unknown database version v{version_major}.{version_minor}")

    shutil.copyfile(DATABASE_FILE_PATH, BACKUP_DATABASE_FILE_PATH)

    for upgrade in upgrades_required:
        upgrade()
