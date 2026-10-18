"""The migfix_alpha fixture app."""

from django.apps import AppConfig


class AlphaConfig(AppConfig):
    """Cards on the boards of migfix_beta."""

    name = "deskmate.tests.migration_fixtures.alpha"
    label = "migfix_alpha"
    default_auto_field = "django.db.models.BigAutoField"
