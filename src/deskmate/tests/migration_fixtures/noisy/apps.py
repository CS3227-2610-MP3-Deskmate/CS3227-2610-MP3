"""The migfix_noisy fixture app, which has a migration but no models."""

from django.apps import AppConfig


class NoisyConfig(AppConfig):
    """An app whose migration writes a row value out, or raises, as the test asks."""

    name = "deskmate.tests.migration_fixtures.noisy"
    label = "migfix_noisy"
