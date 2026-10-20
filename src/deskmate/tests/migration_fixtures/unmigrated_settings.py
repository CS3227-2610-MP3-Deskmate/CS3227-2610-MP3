"""Deskmate's settings plus an app that has a model but no migrations package.

Django's `makemigrations --check` passes for such an app, because it makes no
first migration for an app that has no migrations package.
"""

from deskmate.settings import *

ROOT_URLCONF = "deskmate.tests.migration_fixtures"
INSTALLED_APPS = [
    "deskmate.tests.migration_fixtures.unmigrated",
]
