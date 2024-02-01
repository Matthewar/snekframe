"""Runtime databases don't persist or require versioning"""
# pylint: disable=too-few-public-methods

from typing import Optional

from sqlachemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlachemy.types import String

from .. import params

class RuntimeBase(DeclarativeBase):
    """Runtime Base DB Class"""

class ExistingFiles(RuntimeBase):
    """Compare whether files already exist"""
    __tablename__ = "existingphotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    photo_path: Mapped[str] = mapped_column(String(params.MAX_PATH_SIZE))
    found: Mapped[bool]

class PhotoOrder(RuntimeBase):
    """Ordering of photos"""
    __tablename__ = "viewing_photos"

    id : Mapped[int] = mapped_column(primary_key=True)
    photo_id : Mapped[int]

class NumPhotos(RuntimeBase):
    """Number of existing photos in each directory"""
    __tablename__ = "numphotos"

    id: Mapped[int] = mapped_column(primary_key=True)
    num_photos: Mapped[int]
    num_albums: Mapped[int]
    directory: Mapped[Optional[str]] = mapped_column(String(params.MAX_FILENAME_SIZE)) # Directory name
    prefix_path: Mapped[Optional[str]] = mapped_column(String(params.MAX_PATH_SIZE)) # Path to directory

class PhotoOrder(RuntimeBase):
    """Ordering of photos"""
    __tablename__ = "viewing_photos"

    id : Mapped[int] = mapped_column(primary_key=True)
    photo_id : Mapped[int]
