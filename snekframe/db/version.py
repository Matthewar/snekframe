"""Database Versioning"""
# pylint: disable=too-few-public-methods

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.expression import select

from ._base import PersistentBase, PERSISTENT_SESSION

DATABASE_VERSION_MAJOR = 1
DATABASE_VERSION_MINOR = 0

class DatabaseVersion(PersistentBase):
    """Version"""
    __tablename__ = "database_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    major: Mapped[int] = mapped_column(insert_default=DATABASE_VERSION_MAJOR)
    minor: Mapped[int] = mapped_column(insert_default=DATABASE_VERSION_MINOR)

def get_database_version():
    """Get version of the database on the filesystem"""
    with PERSISTENT_SESSION() as session:
        version = session.scalars(select(DatabaseVersion).limit(1)).one_or_none()
    if version is None:
        raise Exception("Database version was not found")
    return (version.major, version.minor)
