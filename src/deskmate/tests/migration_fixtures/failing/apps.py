"""The migfix_fail fixture app, which has migrations but no models."""

from django.apps import AppConfig


class FailingConfig(AppConfig):
    """An app whose second migration fails while its source data is duplicated."""

    name = "deskmate.tests.migration_fixtures.failing"
    label = "migfix_fail"
