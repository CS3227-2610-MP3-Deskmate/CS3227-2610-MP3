"""Fixtures shared by the whole-journey tests in this folder.

The fixtures live beside the app's tests, but pytest only loads a conftest.py
for the folders above a test file. Re-export the ones these journeys use so
their behaviour stays defined in one place.
"""

from deskmate.tests.conftest import (  # noqa: F401
    browser,
    clock,
    codes,
    database_outage,
    fast_hashing,
    make_account,
    written_output,
)
from deskmate.tests.test_llm_gateway import provider  # noqa: F401
