"""The migfix_drift fixture app."""

from django.apps import AppConfig


class DriftConfig(AppConfig):
    """An app whose model has changed since its last migration."""

    name = "deskmate.tests.migration_fixtures.drift"
    label = "migfix_drift"
    default_auto_field = "django.db.models.BigAutoField"
