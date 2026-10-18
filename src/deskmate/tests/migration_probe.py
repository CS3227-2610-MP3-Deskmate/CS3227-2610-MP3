"""Print installed apps with models but no migrations, for fresh-process tests.

Usage: python -m deskmate.tests.migration_probe

These apps are passed over by `makemigrations --check`.
"""

import json

import django
from django.apps import apps
from django.db.migrations.loader import MigrationLoader


def main():
    """Set up Django and print sorted JSON labels of unmigrated apps with models."""
    django.setup()
    unmigrated = MigrationLoader(None).unmigrated_apps
    print(
        json.dumps(
            sorted(
                config.label
                for config in apps.get_app_configs()
                if config.label in unmigrated and any(config.get_models())
            )
        )
    )


if __name__ == "__main__":
    main()
