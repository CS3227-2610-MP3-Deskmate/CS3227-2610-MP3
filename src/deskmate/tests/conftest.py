"""Fixtures that put Deskmate's database into the states the criteria name."""

import secrets

import pytest
from django.db import DEFAULT_DB_ALIAS, connections

from deskmate.tests.helpers import unused_port


@pytest.fixture
def database_refuses_connections(django_db_blocker, monkeypatch):
    """Point Deskmate's database connection at a local port nothing listens on."""
    connection = connections[DEFAULT_DB_ALIAS]
    connection.close()
    monkeypatch.setitem(connection.settings_dict, "HOST", "127.0.0.1")
    monkeypatch.setitem(connection.settings_dict, "PORT", str(unused_port()))
    with django_db_blocker.unblock():
        yield
        connection.close()


@pytest.fixture
def database_rejects_credentials(django_db_blocker, monkeypatch):
    """Give Deskmate a wrong password for a database server that answers.

    Connects with the right password first, so the test cannot pass merely
    because no database is running.
    """
    connection = connections[DEFAULT_DB_ALIAS]
    with django_db_blocker.unblock():
        connection.ensure_connection()
        connection.close()
        wrong_password = f"wrong-{secrets.token_hex(8)}"
        monkeypatch.setitem(connection.settings_dict, "PASSWORD", wrong_password)
        yield
        connection.close()
