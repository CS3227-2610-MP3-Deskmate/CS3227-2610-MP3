"""Deskmate's settings plus an app whose second migration can fail.

migfix_fail.0001_kept creates a table. migfix_fail.0002_copy_codes creates
another table with a primary key and copies into it the codes in a table the test
creates, `migfix_fail_source`, so it fails, quoting the duplicated code, when that
table holds one code twice.
"""

from deskmate import settings as _deskmate
from deskmate.settings import *

INSTALLED_APPS = [
    *_deskmate.INSTALLED_APPS,
    "deskmate.tests.migration_fixtures.failing",
]
