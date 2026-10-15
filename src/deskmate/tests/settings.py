"""Django settings for the tests: Deskmate's own settings, configured by the tests.

Before Deskmate's settings read the environment, this replaces every variable
that configures Deskmate, Django or libpq with the values in `environment.py`.
"""

import os

from deskmate.tests.environment import use_test_configuration

use_test_configuration(os.environ)

# Imported last, so Deskmate's settings read the tests' configuration.
from deskmate.settings import *
