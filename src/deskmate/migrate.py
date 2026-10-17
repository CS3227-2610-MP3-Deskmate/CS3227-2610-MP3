"""Apply Deskmate's unapplied migrations, run by the Vercel production build.

Run it as `python src/deskmate/migrate.py` with no arguments. It uses the settings
module in DJANGO_SETTINGS_MODULE, or Deskmate's own when that is unset. It writes
only the lines PLT-2.12 allows, all to standard output, ending with
`migration: passed` and status 0 once no migration remains unapplied, or
`migration: failed` and status 1. Nothing is retried (PLT-2.14).

Unlike the `migrate` command, it sends no pre_migrate or post_migrate signal, so
no content type or permission rows are created: their handlers can write output
PLT-2.12 forbids, and no spec uses Django permissions.
"""

import logging
import os
import re
import sys
import warnings
from pathlib import Path

# The line settings.py writes for each invalid variable (PLT-1.7).
_CANNOT_START = r"Deskmate cannot start: [A-Z][A-Z0-9_]* is not set or is invalid\."


def _silence():
    """Send descriptors 1 and 2 to the null device; return a writer for real stdout.

    Redirecting the descriptors, not just sys.stdout and sys.stderr, also hides
    writes made below Python, such as by the database driver.
    """
    sys.stdout.flush()
    sys.stderr.flush()
    real_stdout = os.fdopen(os.dup(1), "w")
    null = os.open(os.devnull, os.O_WRONLY)
    os.dup2(null, 1)
    os.dup2(null, 2)
    os.close(null)

    def say(line):
        print(line, file=real_stdout, flush=True)

    return say


def _unapplied(executor):
    """Return the executor's plan to apply every migration not yet applied."""
    return executor.migration_plan(executor.loader.graph.leaf_nodes())


def _migrate(say):
    """Set Django up and apply the unapplied migrations once; return if none remain."""
    # Imported only once output is silenced and errors are caught (PLT-2.12).
    import django  # noqa: PLC0415
    from django.db import connection  # noqa: PLC0415
    from django.db.migrations.executor import MigrationExecutor  # noqa: PLC0415

    def report_progress(action, migration=None, fake=False):
        if action == "apply_start":
            say(f"migration: applying {migration.app_label}.{migration.name}")

    django.setup()
    executor = MigrationExecutor(connection, report_progress)
    executor.loader.check_consistent_history(connection)
    if executor.loader.detect_conflicts():
        raise RuntimeError
    plan = _unapplied(executor)
    if not plan:
        say("migration: nothing to apply")
    executor.migrate(executor.loader.graph.leaf_nodes(), plan=plan)
    return not _unapplied(MigrationExecutor(connection))


def main():
    """Migrate the configured database and return the exit status."""
    # Python puts this script's own folder first; Deskmate imports from src.
    sys.path[0] = str(Path(__file__).resolve().parents[1])
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "deskmate.settings")
    say = _silence()
    warnings.simplefilter("ignore")
    logging.disable(logging.CRITICAL)
    try:
        passed = _migrate(say)
    except SystemExit as error:
        message = error.code if isinstance(error.code, str) else ""
        for line in message.splitlines():
            if re.fullmatch(_CANNOT_START, line):
                say(line)
        passed = False
    except BaseException:  # noqa: BLE001 -- errors may quote secrets or rows.
        passed = False
    say("migration: passed" if passed else "migration: failed")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
