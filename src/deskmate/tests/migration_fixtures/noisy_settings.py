"""Deskmate's settings plus an app whose migration writes a row value out.

migfix_noisy.0001_emit creates a table, then reads `(channel, value)` rows from a
table the test creates, `migfix_noisy_source`. For each row it writes the value
through that channel: standard output or standard error, through Python or
directly to the file descriptor, a Python warning, a log record at ERROR or
CRITICAL, or a database warning; or it raises KeyboardInterrupt, or another
BaseException that is not SystemExit, carrying the value.
"""

from deskmate.settings import *

ROOT_URLCONF = "deskmate.tests.migration_fixtures"
INSTALLED_APPS = [
    "deskmate",
    "deskmate.tests.migration_fixtures.noisy",
]
