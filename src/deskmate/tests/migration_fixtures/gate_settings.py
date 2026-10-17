"""Deskmate's settings plus an app whose middle migration waits for the test.

migfix_gate.0001_before creates a table. migfix_gate.0002_wait creates another,
then reads a table the test creates, `migfix_gate_source`, so it waits for as long
as the test holds a lock on that table. migfix_gate.0003_after creates a third.
"""

from deskmate import settings as _deskmate
from deskmate.settings import *

INSTALLED_APPS = [
    *_deskmate.INSTALLED_APPS,
    "deskmate.tests.migration_fixtures.gate",
]
