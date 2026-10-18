"""The migfix_beta fixture app."""

from django.apps import AppConfig


class BetaConfig(AppConfig):
    """Boards, each of which may pin one card from migfix_alpha."""

    name = "deskmate.tests.migration_fixtures.beta"
    label = "migfix_beta"
    default_auto_field = "django.db.models.BigAutoField"
