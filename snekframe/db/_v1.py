"""V1 Database Classes

Current version
"""
# pylint: disable=too-few-public-methods

from typing import Optional

from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.types import String

from .. import params
from ._base import SharedBase

class PhotoList(SharedBase):
    """Record of all photos stored and whether they're currently selected"""
    __tablename__ = "photolist_v1"

    id: Mapped[int] = mapped_column(primary_key=True)
    filename: Mapped[str] = mapped_column(String(params.MAX_FILENAME_SIZE))
    path: Mapped[str] = mapped_column(String(params.MAX_PATH_SIZE - params.MAX_FILENAME_SIZE))
    caption: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    selected: Mapped[bool] = mapped_column(insert_default=False)
