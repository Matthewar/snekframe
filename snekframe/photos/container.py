"""Container for photo database modification and reading"""

from __future__ import annotations
from enum import Enum
import logging
import os.path
import pathlib
from typing import Optional, Any

from sqlalchemy.sql.expression import select, delete, update, func, and_, or_, not_

from ..analyse import is_file_image
from ..db import RUNTIME_SESSION, PERSISTENT_SESSION, PhotoListV1
from ..db.runtime import ExistingFiles, NumPhotos, PhotoOrder
from .. import params

class PageDirection(Enum):
    Up = auto()
    Into = auto()
    Previous = auto()
    Next = auto()

@dataclass
class GoToPage:
    direction : PageDirection
    into_index : Optional[int]

@dataclass
class SelectItem:
    index : Optional[int] # None = select all

@dataclass
class CommitChanges:
    pass

class ItemType(Enum):
    Name = auto()
    Selection = auto()
    Image = auto()

@dataclass
class ReturnData:
    page_iteration : int
    item_index : int
    item_data : Any
    last_item : bool

class _FileSystemExplorer:
    def __init__(self):
        self._request_queue = queue.Queue()
        self._return_data_queue = queue.Queue()
        self._page_iteration = 0

    #def open_page(self, 
    #def set_selection
    #def get_page

    def explorer_thread(self):
        self._current_page = None
        self._reading_page = None
        self._item_index = 0

        while True:
            try:
                item = self._request_queue.get_nowait()
            except queue.Empty:
                # Can do a get operation
            else:
                # Either something needs updating or switching page
                if item.priority = Priorities.GetPage.value:
                    self._reading_page = 
                self._database_queue.task_done()

            if item.priority == Priorities.GetPage()

            #if current_page_iteration is None:
            #    item.page_iteration = current_page_iteration

            #if isistance


class PhotoDirectorySelection(Enum):
    Not = 0
    Partial = 1
    All = 2

class PhotoInfo:
    """File Info"""
    def __init__(self, path : str, filename : str, parent : CurrentDirectoryInfo, selection : Optional[bool] = None, modified : bool =True):
        self._path = path
        self._filename = filename
        self._directory_info = parent

        self._selection = selection
        if selection is not None:
            self._modified = modified
        else:
            self._modified = False

    def _get_where_clause(self):
        return and_(PhotoListV1.path == self._path, PhotoListV1.filename == self._filename)

    @property
    def selected(self):
        """Whether the file is selected"""
        if self._selection is None:
            query = select(PhotoListV1.selected).where(self._get_where_clause())
            with PERSISTENT_SESSION() as persistent_session:
                self._selection = persistent_session.scalars(query).first()
            self._modified = False
        return self._selection

    @selected.setter
    def selected(self, selection : bool):
        self._selection = selection
        self._modified = True

    def commit_change(self):
        if not self._modified:
            return

        with PERSISTENT_SESSION() as session:
            session.execute(
                update(PhotoListV1).where(self._get_where_clause()).value(selected=self._selection)
            )
            session.commit()

class CurrentDirectoryInfo:
    """Directory Info"""
    def __init__(self, prefix_path : Optional[str], directory : Optional[str], parent=None, num_photos=None, num_albums=None, num_items_per_page=params.NUM_ITEMS_PER_GALLERY_PAGE):
        self._path = prefix_path
        self._name = directory
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

        self._pages = None
        self._num_items_per_page = num_items_per_page

    def _load_pages(self):
        self._pages = []

        if self._num_photos is None:
            with RUNTIME_SESSION() as session:
                result = session.scalars(
                    select(NumPhotos).where(and_(NumPhotos.prefix_path == self._path, NumPhotos.directory == self._name))
                ).first()
                self._num_photos = result.num_photos
                self._num_albums = result.num_albums

        self._pages.append([])
        page_number = 0

        if self._num_albums != 0:
            with RUNTIME_SESSION() as session:
                result = session.scalars(
                    select(NumPhotos).where(NumPhotos.prefix_path == self._full_path)
                )
                for row in result:
                    if len(self._pages[page_number]) == self._num_items_per_page:
                        self._pages.append([])
                        page_number += 1
                    self._pages[page_number].append(
                        self.__class__(
                            self._full_path, row.directory, parent=self._parent, num_photos=row.num_photos, num_albums=row.num_albums
                        )
                    )
        if self._num_photos != 0:
            image_path = "" if self._path is None else self._path
            if self._name is not None:
                image_path = os.path.join(image_path, self._name)
            with RUNTIME_SESSION() as session:
                result = session.scalars(
                    select(PhotoListV1).where(PhotoListV1.path == image_path)
                )
                for row in result:
                    if len(self._pages[page_number]) == self._num_items_per_page:
                        self._pages.append([])
                        page_number += 1
                    self._pages[page_number].append(
                        PhotoInfo(row.path, row.filename)
                    )

    @property
    def selected(self): # TODO: Go into directories
        """Whether the entire directory is selected"""
        with PERSISTENT_SESSION() as persistent_session, RUNTIME_SESSION() as runtime_session:
            none_selected = True
            all_selected = True

            modified_rows = runtime_session.execute(
                select(PhotoListV1.filename, PhotoListV1.selected).where(PhotoListV1.path == self._full_path)
            )

            where_clauses = []

            for filename, path, selected in modified_rows:
                if selected:
                    none_selected = False
                else:
                    all_selected = False
                where_clauses.append(and_(PhotoListV1.filename == filename, PhotoListV1.path == self._full_path))

            original_rows = persistent_session.execute(
                select(PhotoListV1.selected).where(not_(or_(*where_clauses)))
            )
            for selected in original_rows:
                if selected:
                    none_selected = False
                else:
                    all_selected = False

            if none_selected:
                return self.DirectorySelection.Not
            if all_selected:
                return self.DirectorySelection.All
            return self.DirectorySelection.Partial

    @selected.setter
    def selected(self, selection): # Wrong?
        if not isinstance(selection, self.DirectorySelection):
            raise TypeError()
        if selection == self.DirectorySelection.Partial:
            raise TypeError()

        with RUNTIME_SESSION() as runtime_session, PERSISTENT_SESSION() as persistent_session:
            runtime_session.execute(
                delete(PhotoListV1).where(PhotoListV1.path == self._full_path)
            )
            rows = persistent_session.scalars(
                select(PhotoListV1).where(PhotoListV1.path == self._full_path)
            )
            for row in rows:
                runtime_session.merge(row)
            runtime_session.execute(
                update(PhotoListV1).where(PhotoListV1.path == self._full_path).values(selected=selection == self.DirectorySelection.All)
            )
            runtime_session.commit()

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

def commit_photo_selections(self):
    """Commit changes made to photo selections (update persistent database)"""
def rollback_photo_selections(self):
    """Remove changes made to photo selections (delete runtime change database)"""
    #with

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

            existing_photos = persistent_session.scalars(
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
                                persistent_session.add(PhotoListV1(filename=path.name, path=relative_path.parent))
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
                        prefix_path = directory.parent if directory.parent != pathlib.Path(".") else None
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

        return self.reorder(shuffle=shuffle)


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
        with PERSISTENT_SESSION() as persistent_session, RUNTIME_SESSION() as runtime_session:
            runtime_session.execute(delete(PhotoOrder))

            query = select(PhotoListV1.id).where(PhotoListV1.selected == True)
            if shuffle:
                query.order_by(func.random())

            for row in persistent_session.execute(query):
                runtime_session.add(PhotoOrder(photo_id=row))
            runtime_session.commit()

            return persistent_session.scalars(
                select(func.count(PhotoOrder.id))
            ).scalar_one()

    #@property
    #def all_photos_selected(self):
    #    """Whether all photos are selected"""
    #    return self._all_photos_selected
