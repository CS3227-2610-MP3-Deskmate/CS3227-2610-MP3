"""The migfix_unmigrated fixture app."""

from django.apps import AppConfig


class UnmigratedConfig(AppConfig):
    """An app with a model and no migrations package."""

    name = "deskmate.tests.migration_fixtures.unmigrated"
    label = "migfix_unmigrated"
    default_auto_field = "django.db.models.BigAutoField"
