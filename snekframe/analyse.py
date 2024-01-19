"""Analyse photos and add to database"""

import logging
import os.path

from .params import FILES_LOCATION, PHOTOS_LOCATION
from .db import ExistingFiles, RUNTIME_ENGINE, RUNTIME_SESSION, PERSISTENT_SESSION, PhotoList, CurrentDisplay, NumPhotos, RuntimeBase

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
            path, err, err.message)
        return False
    #except PIL.UnidentifiedImageError:
    #    logging.warning("Unidentified Image '%s'", path)
    return True
