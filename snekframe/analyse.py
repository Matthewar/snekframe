"""Analyse photos and add to database"""

import logging
import os.path

from .params import FILES_LOCATION, PHOTOS_LOCATION
from .db import (
    ExistingFiles,
    RUNTIME_ENGINE,
    RUNTIME_SESSION,
    PERSISTENT_SESSION,
    PhotoList,
    CurrentDisplay,
    NumPhotos,
    RuntimeBase,
)

import filetype.helpers
import PIL.Image

from sqlalchemy.sql.expression import select, func, update, delete


def is_file_image(path):
    """Verify if an image is a file and if it can be parsed"""
    if not filetype.helpers.is_image(path):
        logging.info("File '%s' is not an image according to filetype checker", path)
        return False
    image = PIL.Image.open(path)
    try:
        image.verify()
    except Exception as err:
        logging.warning(
            "File '%s' failed to be verified as an image '%s': '%s'",
            path,
            err,
            err.message,
        )
        return False
    # except PIL.UnidentifiedImageError:
    #    logging.warning("Unidentified Image '%s'", path)
    return True


def setup_viewed_photos(shuffle=False, album=None):
    """Returns True if found photos"""
    with PERSISTENT_SESSION() as persistent_session, RUNTIME_SESSION() as runtime_session:
        runtime_session.execute(delete(PhotoList))

        query = select(PhotoList)
        if album is not None:
            query = query.where(PhotoList.album == album)
        if shuffle:
            query = query.order_by(func.random())
        found_photos = False
        for row in persistent_session.scalars(query):
            found_photos = True
            runtime_session.merge(row)
        runtime_session.commit()

        if not found_photos:
            persistent_session.execute(delete(CurrentDisplay))
            return False
        else:
            updated = persistent_session.execute(
                update(CurrentDisplay)
                .values(album=album, all_photos=album is None)
                .returning(CurrentDisplay.id)
            ).one_or_none()
            if updated is None:
                persistent_session.add(
                    CurrentDisplay(album=album, all_photos=album is None)
                )

        persistent_session.commit()
        return True


def load_photo_files():
    """Load existing photos on startup"""
    RuntimeBase.metadata.create_all(RUNTIME_ENGINE)
    with PERSISTENT_SESSION() as persistent_session, RUNTIME_SESSION() as runtime_session:
        existing_photos = persistent_session.scalars(
            select(PhotoList.filename, PhotoList.album)
        )
        for row in runtime_session:
            runtime_session.add(
                ExistingFiles(photo_path=os.path.join(*row), found=False)
            )

        persistent_session.execute(delete(PhotoList))

        albums = []
        for direntry in os.scandir(os.path.join(FILES_LOCATION, PHOTOS_LOCATION)):
            if direntry.is_dir():
                logging.info("Found album '%s'", direntry.name)
                albums.append(direntry.name)
            elif direntry.is_file():
                logging.warning(
                    "Found potential photo without album '%s'", direntry.name
                )
            else:
                logging.error("Found unknown file '%s'", direntry.name)

        num_photos = 0
        for album in albums:
            for direntry in os.scandir(
                os.path.join(FILES_LOCATION, PHOTOS_LOCATION, album)
            ):
                if direntry.is_dir():
                    logging.warning(
                        "Ignoring directory '%s' in album '%s'", direntry.name, album
                    )
                elif direntry.is_file():
                    if is_file_image(direntry.path):
                        num_photos += 1
                        persistent_session.add(
                            PhotoList(filename=direntry.name, album=album)
                        )
                        found_image = runtime_session.execute(
                            update(ExistingFiles)
                            .where(ExistingFiles.photo_path == direntry.path)
                            .values(found=True)
                            .returning(ExistingFiles.id)
                        ).first()
                        if found_image is None:
                            logging.info(
                                "Found new image '%s' in album '%s'",
                                direntry.name,
                                album,
                            )
                        else:
                            logging.info(
                                "Rediscovered image '%s' in album '%s'",
                                direntry.name,
                                album,
                            )
                else:
                    logging.error(
                        "Found unknown file '%s' in album '%s'", direntry.name, album
                    )

        persistent_session.commit()

        lost_files = runtime_session.execute(
            select(ExistingFiles.photo_path).where(ExistingFiles.found == True)
        )
        for row in lost_files:
            logging.warning("Cannot find photo '%s'", row)

        runtime_session.rollback()

        runtime_session.add(NumPhotos(num_photos=num_photos, num_albums=len(albums)))
        runtime_session.commit()
