"""Deskmate's settings plus an app whose model has a field no migration adds."""

from deskmate import settings as _deskmate
from deskmate.settings import *

INSTALLED_APPS = [
    *_deskmate.INSTALLED_APPS,
    "deskmate.tests.migration_fixtures.drift",
]
