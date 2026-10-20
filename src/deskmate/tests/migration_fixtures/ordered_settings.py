"""Deskmate's settings plus two apps whose migrations depend on each other.

Their dependencies force one order: migfix_beta.0001_initial,
migfix_alpha.0001_initial, then migfix_beta.0002_board_pinned. Their models match
their migrations.
"""

from deskmate.settings import *

ROOT_URLCONF = "deskmate.tests.migration_fixtures"
INSTALLED_APPS = [
    "deskmate.tests.migration_fixtures.alpha",
    "deskmate.tests.migration_fixtures.beta",
]
