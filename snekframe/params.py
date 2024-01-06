"""Common Parameters"""

import os.path

WINDOW_WIDTH : int = 1280
WINDOW_HEIGHT : int = 800

FILES_LOCATION = os.path.expanduser("~/.snekframe")
DATABASE_NAME = "photos.db"
PHOTOS_LOCATION = "files"

MAX_FILENAME_SIZE = 256

TITLE_BAR_HEIGHT = 50
TITLE_BAR_COLOUR = "red"

GIT_URL = "https://github.com"
ORGANISATION = "matthewar"
REPO_NAME = "snekframe"
REPO_URL = "/".join((GIT_URL, ORGANISATION, REPO_NAME))
