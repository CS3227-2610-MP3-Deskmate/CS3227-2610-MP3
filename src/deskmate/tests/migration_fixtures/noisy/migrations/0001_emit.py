import logging
import os
import sys
import warnings

from django.db import migrations


class Escape(BaseException):
    """An exception that is neither an Exception nor a SystemExit."""


def emit(apps, schema_editor):
    """Send each row's value out through the row's channel, as migration code can."""
    with schema_editor.connection.cursor() as cursor:
        cursor.execute("SELECT channel, value FROM migfix_noisy_source")
        rows = cursor.fetchall()
        for channel, value in rows:
            if channel == "print":
                print(value)
            elif channel == "stderr":
                sys.stderr.write(f"{value}\n")
            elif channel == "warning":
                warnings.warn(value, stacklevel=1)
            elif channel == "log-error":
                logging.getLogger(__name__).error(value)
            elif channel == "log-critical":
                logging.getLogger(__name__).critical(value)
            elif channel == "database-notice":
                cursor.execute(
                    "DO $$ BEGIN RAISE WARNING '%', "
                    "(SELECT value FROM migfix_noisy_source LIMIT 1); END $$"
                )
            elif channel == "stdout-descriptor":
                os.write(1, f"{value}\n".encode())
            elif channel == "stderr-descriptor":
                os.write(2, f"{value}\n".encode())
            elif channel == "keyboard-interrupt":
                raise KeyboardInterrupt(value)
            elif channel == "base-exception":
                raise Escape(value)
            else:
                raise ValueError(channel)


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.RunSQL("CREATE TABLE migfix_noisy_done (id integer)"),
        migrations.RunPython(emit),
    ]
