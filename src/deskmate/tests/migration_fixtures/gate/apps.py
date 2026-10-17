"""The migfix_gate fixture app, which has migrations but no models."""

from django.apps import AppConfig


class GateConfig(AppConfig):
    """An app whose second migration waits while the test locks its source table."""

    name = "deskmate.tests.migration_fixtures.gate"
    label = "migfix_gate"
