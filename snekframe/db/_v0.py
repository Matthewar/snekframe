"""V0 classes

Many classes have been replaced by V1

Settings has not been removed in V1
"""
# pylint: disable=too-few-public-methods

import datetime
from typing import Optional

from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy.types import String, Time

from ._base import PersistentBase, DeprecatedPersistentOrSharedBase as DeprecatedBase
from .. import params

class Settings(PersistentBase):
    """All saved settings"""
    __tablename__ = "settings"

    id: Mapped[int] = mapped_column(primary_key=True)
    shuffle_photos: Mapped[bool] = mapped_column(insert_default=False)
    # TODO:
    sleep_start_time: Mapped[Optional[datetime.time]] = mapped_column(Time(), nullable=True, insert_default=None)
    sleep_end_time: Mapped[Optional[datetime.time]] = mapped_column(Time(), nullable=True, insert_default=None)
    photo_change_time: Mapped[int] = mapped_column(insert_default=10)

### DEPRECATED

class CurrentDisplay(DeprecatedBase):
    """Currently Displayed Album

    Removed due to selecting photos across albums
    """
    __tablename__ = "displayed_album"

    id: Mapped[int] = mapped_column(primary_key=True)
    album: Mapped[Optional[str]] = mapped_column(String(params.MAX_FILENAME_SIZE), nullable=True)
    all_photos: Mapped[bool]

class PhotoList(DeprecatedBase):
    """Record of all photos stored"""
    __tablename__ = "photolist"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(params.MAX_FILENAME_SIZE))
    album: Mapped[str] = mapped_column(String(params.MAX_FILENAME_SIZE))
