"""Container for photo database modification and reading"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum, auto
import logging
import os.path
import pathlib
import threading
import time
from typing import Optional, List
import queue

import tkinter as tk

from sqlalchemy.sql.expression import select, delete, update, func, and_, or_, not_

from PIL import Image as PIL_Image, ImageTk as PIL_ImageTk

from ..analyse import is_file_image
from ..db import RUNTIME_SESSION, PERSISTENT_SESSION, PhotoListV1
from ..db.runtime import ExistingFiles, NumPhotos, PhotoOrder
from .. import params
from ..params import WINDOW_HEIGHT, TITLE_BAR_HEIGHT
from . import display

class PageDirection(Enum):
    Up = auto()
    Previous = auto()
    Next = auto()

@dataclass
class GoToPage:
    """Switch directory page"""
    current_page_id : int
    direction : PageDirection

@dataclass
class GoIntoPage:
    """Go into a directory or view a full image"""
    current_page_id : int
    into_index : int

@dataclass
class SelectItem:
    current_page_id : int
    index : int
    select : bool

@dataclass
class SelectAll:
    current_page_id : int
    select : bool

@dataclass
class StartExplorer:
    pass

@dataclass
class CloseExplorer:
    pass

@dataclass
class CommitChanges:
    save : int

RequestType = GoToPage | GoIntoPage | StartExplorer | CloseExplorer | CommitChanges

######

@dataclass
class DisplayNewPage:
    """Display a new page

    Title shows the new title element
    - Str to append a name to the path
    - None to remove the head of the path
    Directory:
    - True if the displayed page is a directory
    - False if the displayed page should be a full image
    """
    title : Optional[str]
    directory : bool
    new_page_id : int

@dataclass
class ViewUpdate:
    current_page_id : int

@dataclass
class ItemViewUpdate(ViewUpdate):
    index : int

@dataclass
class NameViewUpdate(ItemViewUpdate):
    name : str
    directory : bool

class PhotoDirectorySelection(Enum):
    Not = 0
    Partial = 1
    All = 2

    @classmethod
    def value_to_enum(cls, value):
        for option in (cls.Not, cls.Partial, cls.All):
            if value == option.value:
                return option
        raise KeyError()

@dataclass
class SelectViewUpdate(ItemViewUpdate):
    selection : PhotoDirectorySelection

#@dataclass
#class ThumbnailViewUpdate(ItemViewUpdate):
#    image : tk.PhotoImage

@dataclass
class DirectionsUpdate(ViewUpdate):
    backwards : Optional[bool]
    forwards : Optional[bool]
    up : Optional[bool]
    selection : Optional[PhotoDirectorySelection]

@dataclass
class FullImageViewUpdate(ViewUpdate):
    image : PIL_ImageTk.PhotoImage

class _FileSystemExplorer:
    def __init__(self):
        self._request_queue = queue.Queue()
        self._return_data_queue = queue.Queue()
        self._thread = None

        # Viewing side
        self._opening_page = False
        self._current_displayed_page_id = None

    def request_go_into_page(self, current_page_id : int, index : int):
        """Open the page at the index shown on the current page"""
        if self._opening_page:
            raise Exception()
        if self._current_displayed_page_id is None or self._current_displayed_page_id != current_page_id:
            raise Exception()

        self._opening_page = True
        self._request_queue.put(
            GoIntoPage(
                current_page_id=current_page_id,
                into_index=index
            )
        )

    def request_goto_page(self, current_page_id : int, direction : PageDirection):
        if self._opening_page:
            raise Exception()
        if self._current_displayed_page_id is None or self._current_displayed_page_id != current_page_id:
            raise Exception()

        self._opening_page = True
        self._request_queue.put(
            GoToPage(
                current_page_id=current_page_id,
                direction=direction
            )
        )

    def request_selection(self, current_page_id : int, index : int, select : bool):
        if self._opening_page:
            raise Exception()
        if self._current_displayed_page_id is None or self._current_displayed_page_id != current_page_id:
            raise Exception()

        self._request_queue.put(
            SelectItem(
                current_page_id=current_page_id,
                index=index,
                select=select
            )
        )

    def request_select_all(self, current_page_id : int, select : bool):
        if self._opening_page:
            raise Exception()
        if self._current_displayed_page_id is None or self._current_displayed_page_id != current_page_id:
            raise Exception()

        self._request_queue.put(
            SelectAll(
                current_page_id=current_page_id,
                select=select
            )
        )

    def get_page(self):
        """Wait for page change"""
        if not self._opening_page or self._current_displayed_page_id is None:
            raise Exception()

        while True:
            result = self._return_data_queue.get()
            self._return_data_queue.task_done()
            if not isinstance(result, DisplayNewPage):
                continue
            if self._current_displayed_page_id >= result.new_page_id:
                raise Exception()
            self._current_displayed_page_id = result.new_page_id
            self._opening_page = False

            return result

    def get_view_update(self):
        """Non-blocking check for updates to the view"""
        if self._opening_page or self._current_displayed_page_id is None:
            raise Exception()

        while True:
            try:
                result = self._return_data_queue.get_nowait()
            except queue.Empty:
                return
            if isinstance(result, DisplayNewPage):
                raise Exception()
            if result.current_page_id < self._current_displayed_page_id:
                continue
            if result.current_page_id > self._current_displayed_page_id:
                raise Exception()
            return result

    def start_explorer(self):
        if self._current_displayed_page_id is not None:
            raise Exception()
        if not self._request_queue.empty():
            raise Exception()
        if not self._return_data_queue.empty():
            raise Exception()
        if self._thread is not None:
            raise Exception()

        self._thread = threading.Thread(target=self._explorer_thread)
        self._thread.start()

        self._opening_page = True
        self._request_queue.put(
            StartExplorer()
        )
        result = self._return_data_queue.get()
        self._return_data_queue.task_done()
        self._current_displayed_page_id = result.new_page_id
        self._opening_page = False
        return result

    def save_or_cancel_changes(self, save):
        if self._current_displayed_page_id is None:
            raise Exception()
        # What happens if save or rollback while opening a page, need to potentially adjust ID to avoid in progress
        # updates about selections
        self._request_queue.put(
            CommitChanges(
                save=save
            )
        )

    def close_explorer(self, save=False):
        if self._current_displayed_page_id is None:
            raise Exception()

        self.save_or_cancel_changes(save) # TODO only if selection mode
        self._request_queue.put(
            CloseExplorer()
        )
        self._thread.join()

    def __del__(self):
        self.close_explorer(False)

    class _PageDisplayStage(Enum):
        Directions = auto()
        Name = auto()
        Selection = auto()
        Image = auto()
        SelectDirection = auto()

    def _explorer_thread(self) -> None:
        directory_info : List[CurrentDirectoryInfo | PhotoInfo] = []
        page_number : List[int] = []
        current_page_id : Optional[int] = None
        next_pages : Optional[List[CurrentDirectoryInfo | PhotoInfo]] = None # Potential next pages

        current_display_index : int = 0
        current_display_stage : List[_FileSystemExplorer._PageDisplayStage] = []

        with RUNTIME_SESSION() as runtime_session, PERSISTENT_SESSION() as persistent_session:
            finished = False
            while not finished:
                try:
                    item = self._request_queue.get_nowait()
                except queue.Empty:
                    if not current_display_stage:
                        time.sleep(0.1)
                    elif current_display_stage[0] == self._PageDisplayStage.Directions:
                        if isinstance(directory_info[-1], CurrentDirectoryInfo):
                            backwards = page_number[-1] > 0
                            forwards = page_number[-1] < (directory_info[-1].num_pages - 1)
                        else:
                            backwards = False
                            forwards = False
                        self._return_data_queue.put(
                            DirectionsUpdate(
                                current_page_id=current_page_id,
                                backwards=backwards,
                                forwards=forwards,
                                up=len(directory_info) > 1,
                                selection=None
                            )
                        )
                        current_display_stage.pop(0)
                    elif current_display_stage[0] == self._PageDisplayStage.Name:
                        if next_pages is None:
                            raise Exception()

                        self._return_data_queue.put(
                            NameViewUpdate(
                                current_page_id=current_page_id,
                                index=current_display_index,
                                name=next_pages[current_display_index].name,
                                directory=isinstance(next_pages[current_display_index], CurrentDirectoryInfo)
                            )
                        )

                        current_display_index += 1
                        if current_display_index == len(next_pages):
                            current_display_index = 0
                            current_display_stage.pop(0)
                    elif current_display_stage[0] == self._PageDisplayStage.Selection:
                        if isinstance(directory_info[-1], CurrentDirectoryInfo):
                            if next_pages is None:
                                raise Exception()

                            selection = next_pages[current_display_index].selected
                        else:
                            if directory_info[-1].selected:
                                selection = PhotoDirectorySelection.All
                            else:
                                selection = PhotoDirectorySelection.Not

                        self._return_data_queue.put(
                            SelectViewUpdate(
                                current_page_id=current_page_id,
                                index=current_display_index,
                                selection=selection
                            )
                        )

                        current_display_index += 1
                        if next_pages is None or current_display_index == len(next_pages):
                            current_display_index = 0
                            current_display_stage.pop(0)
                    elif current_display_stage[0] == self._PageDisplayStage.Image:
                        if not isinstance(directory_info[-1], CurrentDirectoryInfo):
                            # TODO: Thumbnails for directories
                            # For now only output normal image
                            image = PIL_ImageTk.PhotoImage(display._resize_image(directory_info[-1].generate_image, max_height=WINDOW_HEIGHT-TITLE_BAR_HEIGHT*2))
                            self._return_data_queue.put(
                                FullImageViewUpdate(
                                    current_page_id=current_page_id,
                                    image=image
                                )
                            )

                        current_display_stage.pop(0)
                    elif current_display_stage[0] == self._PageDisplayStage.SelectDirection:
                        # Searching for select all settings
                        total_selection = None
                        for page_id in range(directory_info[0].num_pages):
                            for page in directory_info[0].get_page(page_id):
                                if isinstance(page, CurrentDirectoryInfo):
                                    page_selection = page.selected
                                elif page.selected:
                                    page_selection = PhotoDirectorySelection.All
                                else:
                                    page_selection = PhotoDirectorySelection.Not

                                if page_selection == PhotoDirectorySelection.Partial:
                                    total_selection = page_selection
                                    break
                                if total_selection is None:
                                    total_selection = page_selection
                                elif total_selection == PhotoDirectorySelection.Not and page_selection == PhotoDirectorySelection.All:
                                    total_selection = PhotoDirectorySelection.Partial
                                    break
                                elif total_selection == PhotoDirectorySelection.All and page_selection == PhotoDirectorySelection.Not:
                                    total_selection = PhotoDirectorySelection.Partial
                                    break
                        self._return_data_queue.put(
                            DirectionsUpdate(
                                current_page_id=current_page_id,
                                backwards=None,
                                forwards=None,
                                up=None,
                                selection=total_selection
                            )
                        )

                        current_display_index = 0
                        current_display_stage.pop(0)
                    else:
                        raise TypeError()
                else:
                    if isinstance(item, GoIntoPage):
                        if current_page_id != item.current_page_id:
                            raise Exception()
                        if not directory_info:
                            raise Exception()
                        if next_pages is None:
                            raise Exception()

                        directory_info.append(next_pages[item.into_index])
                        page_number.append(0)
                        directory = isinstance(directory_info[-1], CurrentDirectoryInfo)
                        if directory:
                            next_pages = directory_info[-1].get_page(page_number[-1])
                        else:
                            next_pages = None

                        current_page_id += 1
                        self._return_data_queue.put(
                            DisplayNewPage(
                                title=directory_info[-1].name,
                                directory=directory,
                                new_page_id=current_page_id
                            )
                        )

                        current_display_stage = [self._PageDisplayStage.Directions]
                        if directory:
                            current_display_stage.append(self._PageDisplayStage.Name)
                        current_display_stage += [
                            self._PageDisplayStage.Selection,
                            self._PageDisplayStage.Image,
                            self._PageDisplayStage.SelectDirection
                        ]
                        current_display_index = 0
                    elif isinstance(item, GoToPage):
                        if current_page_id != item.current_page_id:
                            raise Exception()
                        if isinstance(directory_info[-1], CurrentDirectoryInfo):
                            raise Exception()

                        if item.direction == PageDirection.Up:
                            if len(directory_info) < 2:
                                raise Exception()

                            directory_info.pop()
                            page_number.pop()

                            new_title = None
                        else:
                            if not directory_info:
                                raise Exception()

                            # TODO Check for forward/back?
                            if item.direction == PageDirection.Previous:
                                page_number[-1] -= 1
                            elif item.direction == PageDirection.Next:
                                page_number[-1] += 1

                            new_title = directory_info[-1].name

                        current_page_id += 1
                        self._return_data_queue.put(
                            DisplayNewPage(
                                title=new_title,
                                directory=True,
                                new_page_id=current_page_id
                            )
                        )

                        next_pages = directory_info[-1].get_page(page_number[-1])

                        current_display_stage = [self._PageDisplayStage.Directions]
                        if directory:
                            current_display_stage.append(self._PageDisplayStage.Name)
                        current_display_stage += [
                            self._PageDisplayStage.Selection,
                            self._PageDisplayStage.Image,
                            self._PageDisplayStage.SelectDirection
                        ]
                        current_display_index = 0
                    elif isinstance(item, SelectItem):
                        if current_page_id != item.current_page_id:
                            raise Exception()

                        if isinstance(directory_info[-1], CurrentDirectoryInfo):
                            next_pages[item.index].selected = item.select
                        else:
                            directory_info[-1].selected = item.select

                        self._return_data_queue.put( # This seems potentially unnecessary
                            SelectViewUpdate(
                                current_page_id=current_page_id,
                                index=item.index,
                                selection=PhotoDirectorySelection.All if item.select else PhotoDirectorySelection.Not
                            )
                        )
                    elif isinstance(item, SelectAll):
                        if current_page_id != item.current_page_id:
                            raise Exception()

                        for page_id in range(directory_info[0].num_pages):
                            for page in directory_info[0].get_page(page_id):
                                page.selected = item.select

                        self._return_data_queue.put(
                            DirectionsUpdate(
                                current_page_id=current_page_id,
                                backwards=None,
                                forwards=None,
                                up=None,
                                selection=PhotoDirectorySelection.All if item.select else PhotoDirectorySelection.Not
                            )
                        )
                        if current_display_stage[0] == self._PageDisplayStage.Selection:
                            current_display_index = 0
                        else:
                            current_display_stage.append(self._PageDisplayStage.Selection)
                    elif isinstance(item, StartExplorer):
                        if current_page_id is not None or directory_info:
                            raise Exception()
                        directory_info.append(CurrentDirectoryInfo(runtime_session, persistent_session, None, None))
                        page_number.append(0)
                        next_pages = directory_info[0].get_page(page_number[0])
                        current_page_id = 0

                        self._return_data_queue.put(
                            DisplayNewPage(
                                title=directory_info[0].name,
                                directory=True,
                                new_page_id=current_page_id
                            )
                        )

                        current_display_stage = [self._PageDisplayStage.Directions]
                        if directory:
                            current_display_stage.append(self._PageDisplayStage.Name)
                        current_display_stage += [
                            self._PageDisplayStage.Selection,
                            self._PageDisplayStage.Image,
                            self._PageDisplayStage.SelectDirection
                        ]
                        current_display_index = 0
                    elif isinstance(item, CommitChanges):
                        for session in (runtime_session, persistent_session):
                            if item.save:
                                session.commit()
                            else:
                                session.rollback()
                    elif isinstance(item, CloseExplorer):
                        finished = True
                    else:
                        raise TypeError()
                    self._request_queue.task_done()


class PhotoInfo:
    """File Info"""
    def __init__(self, path : str, filename : str, parent : CurrentDirectoryInfo, persistent_session, selection, row_id):
        self._path = path
        self._filename = filename
        self._directory_info = parent

        self._persistent_session = persistent_session
        if row_id is None:
            self._id = self._persistent_session.scalars(
                select(PhotoListV1.id).where(and_(PhotoListV1.path == self._path, PhotoListV1.filename == self._filename))
            ).one()
        else:
            self._id = row_id

        self._selection = selection

    @property
    def name(self):
        return self._filename

    @property
    def selected(self):
        """Whether the file is selected"""
        if self._selection is None:
            self._selection = self._persistent_session.scalars(
                select(PhotoListV1.selected).where(PhotoListV1.id == self._id)
            ).one()
        return self._selection

    @selected.setter
    def selected(self, selection : bool):
        self._set_selected(selection)

    def _set_selected(self, selection : bool, propagate_up : bool = True):
        if selection != self.selected:
            self._persistent_session.execute(
                update(PhotoListV1).where(PhotoListV1.id == self._id).values(selected=selection)
            )
            if propagate_up:
                self._directory_info._child_changed(selection)

    def generate_image(self):
        return PIL_Image.open(os.path.join(params.FILES_LOCATION, params.PHOTOS_LOCATION, self._path, self._filename))

class CurrentDirectoryInfo:
    """Directory Info"""
    def __init__(self, runtime_session, persistent_session, prefix_path : Optional[str], directory : Optional[str], parent=None, num_photos=None, num_albums=None, selection=None, num_items_per_page=params.NUM_ITEMS_PER_GALLERY_PAGE):
        self._path = prefix_path
        self._name = directory
        self._runtime_session = runtime_session
        self._persistent_session = persistent_session
        if prefix_path is None:
            if directory is None:
                self._full_path = ""
            else:
                self._full_path = directory
        elif directory is None:
            raise TypeError()
        else:
            self._full_path = os.path.join(prefix_path, directory)

        if parent is None and not (prefix_path is None and directory is None):
            raise TypeError()
        self._parent = parent

        self._num_photos = num_photos
        self._num_albums = num_albums
        if (num_photos is None) != (num_albums is None):
            raise TypeError()
        self._selection = selection

        self._pages = None
        self._num_items_per_page = num_items_per_page

    def _load_pages(self):
        self._pages = []

        if self._num_photos is None:
            result = self._runtime_session.scalars(
                select(NumPhotos).where(and_(NumPhotos.prefix_path == self._path, NumPhotos.directory == self._name))
            ).one()
            self._num_photos = result.num_photos
            self._num_albums = result.num_albums
            if self._selection is None:
                self._selection = PhotoDirectorySelection.value_to_enum(result.selected)

        self._pages.append([])
        page_number = 0

        if self._num_albums != 0:
            result = self._runtime_session.scalars(
                select(NumPhotos).where(NumPhotos.prefix_path == self._full_path)
            )
            for row in result:
                if len(self._pages[page_number]) == self._num_items_per_page:
                    self._pages.append([])
                    page_number += 1

                self._pages[page_number].append(
                    self.__class__(
                        self._runtime_session, self._persistent_session, self._full_path, row.directory, parent=self, num_photos=row.num_photos, num_albums=row.num_albums, selection=PhotoDirectorySelection.value_to_enum(row.selected)
                    )
                )
        if self._num_photos != 0:
            image_path = "" if self._path is None else self._path
            if self._name is not None:
                image_path = os.path.join(image_path, self._name)
            result = self._persistent_session.scalars(
                select(PhotoListV1).where(PhotoListV1.path == image_path)
            )
            for row in result:
                if len(self._pages[page_number]) == self._num_items_per_page:
                    self._pages.append([])
                    page_number += 1
                self._pages[page_number].append(
                    PhotoInfo(row.path, row.filename, self, self._persistent_session, row.selected, row.id)
                )

    @property
    def name(self):
        return self._name

    @property
    def selected(self):
        """Whether the entire directory is selected"""
        if self._selection is None:
            self._selection = PhotoDirectorySelection.value_to_enum(
                self._runtime_session.scalars(
                    select(NumPhotos.selected).where(and_(NumPhotos.prefix_path == self._path, NumPhotos.directory == self._name))
                ).one()
            )

    @selected.setter
    def selected(self, selection): # Wrong?
        self._set_selected(selection)

    def _set_selected(self, selection : bool, propagate_up : bool = True, propagate_down : bool = True):
        if (selection and self.selected != PhotoDirectorySelection.All) or (not selection and self.selected != PhotoDirectorySelection.Not):
            self._runtime_session.execute(
                update(NumPhotos).where(and_(NumPhotos.prefix_path == self._path, NumPhotos.directory == self._name)).values(selected=PhotoDirectorySelection.All.value if selection else PhotoDirectorySelection.Not.value)
            )
            if propagate_up and self._parent is not None:
                self._parent._child_changed(selection)
            if propagate_down:
                for page_index in range(self.num_pages):
                    for item in self.get_page(page_index):
                        item._set_selected(selection, propagate_up=False)

    def _child_changed(self, selection):
        if selection == PhotoDirectorySelection.Partial:
            self._selection = selection
            self._runtime_session.execute(
                update(NumPhotos).where(and_(NumPhotos.prefix_path == self._path, NumPhotos.directory == self._name)).values(selected=selection.value)
            )
            if self._parent is not None:
                self._parent._child_changed(selection)
        else:
            if selection:
                total_selection = PhotoDirectorySelection.All
            else:
                total_selection = PhotoDirectorySelection.Not
            selection_discovered = False
            for page_index in range(self.num_pages):
                for item in self.get_page(page_index):
                    if item.selected == PhotoDirectorySelection.Partial:
                        # We'll already be in partial, stop propagating
                        return
                    if isinstance(item.selected, bool):
                        item_selection = PhotoDirectorySelection.All if item.selected else PhotoDirectorySelection.Not
                    else:
                        item_selection = item.selected
                    if item_selection != total_selection:
                        total_selection = PhotoDirectorySelection.Partial
                        selection_discovered = True
                        break
                if selection_discovered:
                    break
            if total_selection != self._selection:
                self._runtime_session.execute(
                    update(NumPhotos).where(and_(NumPhotos.prefix_path == self._path, NumPhotos.directory == self._name)).values(selected=total_selection.value)
                )
                if self._parent is not None:
                    self._parent._child_changed(total_selection)

    @property
    def num_pages(self):
        """Number of pages directory takes"""
        if self._pages is None:
            self._load_pages()

        return len(self._pages)

    def get_page(self, page_number):
        """Get a particular pages info"""
        if self._pages is None:
            self._load_pages()

        return self._pages[page_number]

class PhotoContainer:
    """Runtime access to photos and selection"""
    def __init__(self, shuffle):
        #self._all_photos_selected = False
        self._total_num_photos = 0
        self._total_num_albums = 0
        self.rescan(shuffle=shuffle)

    def rescan(self, shuffle=False):
        """Load existing photos from filesystem

        Then sets up runtime ordering according to shuffle parameter

        Assumes that runtime database is already setup

        Will log errors if any files are missing
        """
        with PERSISTENT_SESSION() as persistent_session, RUNTIME_SESSION() as runtime_session:
            # Delete num photos list, will rebuild while rescanning
            runtime_session.execute(delete(NumPhotos))
            runtime_session.commit()

            existing_photos = persistent_session.execute(
                select(PhotoListV1.path, PhotoListV1.filename)
            )
            for row in existing_photos:
                runtime_session.add(ExistingFiles(photo_path=os.path.join(*row), found=False))

            PHOTOS_PATH = pathlib.Path(os.path.join(params.FILES_LOCATION, params.PHOTOS_LOCATION))

            def scan_directory(directory : Optional[pathlib.Path]):
                directory_relative_path = "." if directory is None else directory

                num_photos = 0
                num_albums = 0

                directory_selected = None

                for path in PHOTOS_PATH.joinpath(directory_relative_path).iterdir():
                    relative_path = path.relative_to(PHOTOS_PATH)
                    if path.is_dir():
                        logging.debug("Found directory '%s' in '%s'", path.name, relative_path)
                        found_photos, internal_directory_selected = scan_directory(relative_path)
                        if found_photos:
                            num_albums += 1
                            self._total_num_albums += 1

                            if directory_selected is None:
                                directory_selected = internal_directory_selected
                            elif internal_directory_selected == PhotoDirectorySelection.Partial:
                                directory_selected = internal_directory_selected
                            elif internal_directory_selected != directory_selected:
                                # If one selection is all and one is none
                                directory_selected = PhotoDirectorySelection.Partial
                    elif path.is_file():
                        if is_file_image(path):
                            num_photos += 1
                            self._total_num_photos += 1
                            found_image = runtime_session.execute(
                                update(ExistingFiles).where(ExistingFiles.photo_path == str(relative_path)).values(found=True).returning(ExistingFiles.id)
                            ).one_or_none()
                            if found_image is None:
                                persistent_session.add(PhotoListV1(filename=path.name, path=str(relative_path.parent)))
                                logging.info("Found new image '%s' in '%s'", path.name, relative_path)
                                photo_selected = False
                            else:
                                logging.info("Rediscovered image '%s' in '%s'", path.name, relative_path)
                                photo_selected = persistent_session.scalars(
                                    select(PhotoListV1.selected).where(
                                        and_(
                                            PhotoListV1.path == str(relative_path.parent),
                                            PhotoListV1.filename == str(relative_path.name)
                                        )
                                    )
                                ).one()

                            if directory_selected is None:
                                if photo_selected:
                                    directory_selected = PhotoDirectorySelection.All
                                else:
                                    directory_selected = PhotoDirectorySelection.Not
                            elif directory_selected != PhotoDirectorySelection.Partial:
                                if directory_selected == PhotoDirectorySelection.All and not photo_selected:
                                    directory_selected = PhotoDirectorySelection.Partial
                                elif directory_selected == PhotoDirectorySelection.Not and photo_selected:
                                    directory_selected = PhotoDirectorySelection.Partial
                        else:
                            logging.error("Found unknown file '%s' in '%s'", path.name, relative_path)

                if num_photos != 0 or num_albums != 0:
                    if directory is None:
                        prefix_path = None
                        directory_name = None
                    else:
                        prefix_path = str(directory.parent) if directory.parent != pathlib.Path(".") else None
                        directory_name = directory.name
                    runtime_session.add(NumPhotos(num_photos=num_photos, num_albums=num_albums, directory=directory_name, prefix_path=prefix_path, selected=directory_selected.value))
                    return True, directory_selected
                return False, None

            self._total_num_photos = 0
            self._total_num_albums = 0

            scan_directory(None)

            persistent_session.commit()

            lost_files = runtime_session.execute(
                select(ExistingFiles.photo_path).where(ExistingFiles.found == False)
            )
            for filepath in lost_files:
                logging.warning("Cannot find photo '%s'", filepath)

            runtime_session.execute(delete(ExistingFiles))
            runtime_session.commit()

            #result = persistent_session.scalars(
            #    select(func.count(PhotoListV1.id)).where(PhotoListV1.selected == False)
            #).scalar_one()

            #self._all_photos_selected = result == 0

        self.reorder(shuffle=shuffle)


    @property
    def num_photos(self):
        """Get the number of photos stored"""
        return self._total_num_photos

    @property
    def num_directories(self):
        """Get the total number of directories with photos in"""
        return self._total_num_albums

    def reorder(self, shuffle=False):
        """Setup the viewable (selected) photos

        Ordering them according to shuffle parameter

        This doesn't affect the persistent DB
        """
        with RUNTIME_SESSION() as runtime_session, PERSISTENT_SESSION() as persistent_session:
            runtime_session.execute(delete(PhotoOrder))

            query = select(PhotoListV1.id).where(PhotoListV1.selected == True)
            if shuffle:
                query.order_by(func.random())

            for row in persistent_session.execute(query):
                runtime_session.add(PhotoOrder(photo_id=row))
            runtime_session.commit()

    @property
    def num_selected_photos(self):
        """Get the number of selected photos"""
        with RUNTIME_SESSION() as session:
            return session.scalars(
                select(func.count(PhotoOrder.id))
            ).scalar_one()

    @property
    def photos_selected(self):
        """Return whether any photos are selected"""
        with RUNTIME_SESSION() as session:
            result = session.scalars(
                select(PhotoOrder.id).limit(1)
            ).one_or_none()
            return result is not None

    @property
    def all_photos_selected(self):
        """Whether all photos are selected"""
        return self.num_photos == self.num_selected_photos
