"""Deskmate's settings plus an app whose model has a field no migration adds."""

from deskmate.settings import *

ROOT_URLCONF = "deskmate.tests.migration_fixtures"
INSTALLED_APPS = [
    "deskmate.tests.migration_fixtures.drift",
]
