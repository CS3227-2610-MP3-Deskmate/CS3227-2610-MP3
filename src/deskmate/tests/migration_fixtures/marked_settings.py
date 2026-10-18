"""Deskmate's settings plus the two ordered apps, recording that they were loaded.

Importing this module first creates the file named by MIGFIX_SETTINGS_MARKER, so
a test can tell whether the entry point loaded any settings.
"""

import os
from pathlib import Path

Path(os.environ["MIGFIX_SETTINGS_MARKER"]).touch()

from deskmate.tests.migration_fixtures.ordered_settings import *
