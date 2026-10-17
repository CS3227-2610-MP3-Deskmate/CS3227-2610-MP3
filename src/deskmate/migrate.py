"""Apply Deskmate's unapplied migrations, run by the Vercel production build.

Run it as `python src/deskmate/migrate.py` with no arguments. It uses the settings
module in DJANGO_SETTINGS_MODULE, or Deskmate's own when that is unset. It writes
only the lines PLT-2.12 allows, all to standard output, ending with
`migration: passed` and status 0 once no migration remains unapplied, or
`migration: failed` and status 1. Nothing is retried (PLT-2.14).
"""

import logging
import os
import re
import sys
import warnings
from pathlib import Path

import django
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

# The line settings.py writes for each invalid variable (PLT-1.7).
_CANNOT_START = r"Deskmate cannot start: [A-Z][A-Z0-9_]* is not set or is invalid\."


def _say(line):
    print(line, flush=True)


def _report_progress(action, migration=None, fake=False):
    """Name each migration as the executor starts applying it."""
    if action == "apply_start":
        _say(f"migration: applying {migration.app_label}.{migration.name}")


def _unapplied(executor):
    """Return the executor's plan to apply every migration not yet applied."""
    return executor.migration_plan(executor.loader.graph.leaf_nodes())


def _migrate():
    """Apply the unapplied migrations once; return whether none remain."""
    executor = MigrationExecutor(connection, _report_progress)
    executor.loader.check_consistent_history(connection)
    if executor.loader.detect_conflicts():
        raise RuntimeError
    plan = _unapplied(executor)
    if not plan:
        _say("migration: nothing to apply")
    executor.migrate(executor.loader.graph.leaf_nodes(), plan=plan)
    return not _unapplied(MigrationExecutor(connection))


def main():
    """Migrate the configured database and return the exit status."""
    # Python puts this script's own folder first; Deskmate imports from src.
    sys.path[0] = str(Path(__file__).resolve().parents[1])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deskmate.settings")
    warnings.simplefilter("ignore")
    logging.disable(logging.CRITICAL)
    try:
        django.setup()
        passed = _migrate()
    except SystemExit as error:
        message = error.code if isinstance(error.code, str) else ""
        for line in message.splitlines():
            if re.fullmatch(_CANNOT_START, line):
                _say(line)
        passed = False
    except Exception:  # noqa: BLE001 -- database errors may quote secrets or rows.
        passed = False
    _say("migration: passed" if passed else "migration: failed")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
