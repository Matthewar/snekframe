import datetime
import os
from typing import Optional

from sqlalchemy import String, Time, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, sessionmaker

from . import params
from .params import MAX_FILENAME_SIZE

class PersistentBase(DeclarativeBase):
    """Program Base DB Class"""
    pass

class DatabaseVersion(PersistentBase):
    """Version"""
    __tablename__ = "application_version"

    id: Mapped[int] = mapped_column(primary_key=True)
    major: Mapped[int] = mapped_column(insert_default=0)
    minor: Mapped[int] = mapped_column(insert_default=0)

class CurrentDisplay(PersistentBase):
    """Currently Displayed Album"""
    __tablename__ = "displayed_album"

    id: Mapped[int] = mapped_column(primary_key=True)
    album: Mapped[Optional[str]] = mapped_column(String(MAX_FILENAME_SIZE), nullable=True)
    all_photos: Mapped[bool]

class Settings(PersistentBase):
    """All saved settings"""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    shuffle_photos: Mapped[bool] = mapped_column(insert_default=False)
    # TODO:
    sleep_start_time: Mapped[Optional[datetime.time]] = mapped_column(Time(), nullable=True, insert_default=None)
    sleep_end_time: Mapped[Optional[datetime.time]] = mapped_column(Time(), nullable=True, insert_default=None)
    photo_change_time: Mapped[int] = mapped_column(insert_default=10)

PERSISTENT_ENGINE = create_engine("sqlite:///{}".format(os.path.join(params.FILES_LOCATION, params.DATABASE_NAME)))
PERSISTENT_SESSION = sessionmaker(PERSISTENT_ENGINE)

class SharedBase(DeclarativeBase):
    """Permanent and Runtime DB Class"""
    pass

class PhotoList(SharedBase):
    """Record of all photos stored"""
    __tablename__ = "photolist"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(MAX_FILENAME_SIZE))
    album: Mapped[str] = mapped_column(String(MAX_FILENAME_SIZE))
    #caption: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)

RUNTIME_ENGINE = create_engine("sqlite://")
RUNTIME_SESSION = sessionmaker(RUNTIME_ENGINE)

class RuntimeBase(DeclarativeBase):
    """Runtime Base DB Class"""
    pass

class ExistingFiles(RuntimeBase):
    """Compare whether files already exist"""
    __tablename__ = "existingphotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_path: Mapped[str] = mapped_column(String(MAX_FILENAME_SIZE*2))
    found: Mapped[bool]

class NumPhotos(RuntimeBase):
    """Number of existing photos"""
    __tablename__ = "numphotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    num_photos: Mapped[int]
    num_albums: Mapped[int]
