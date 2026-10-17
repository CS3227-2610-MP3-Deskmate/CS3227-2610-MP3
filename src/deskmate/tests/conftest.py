"""Fixtures that put Deskmate's database into the states the criteria name, make
accounts, and control the clock."""

import functools
import secrets
from contextlib import contextmanager

import pytest

# The shared checks are plain asserts; this makes pytest explain their failures
# as it does in test files. It must run before the modules are imported.
pytest.register_assert_rewrite("deskmate.tests.signing_in", "deskmate.tests.pages")

from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone

from deskmate.accounts.models import Workspace
from deskmate.tests.helpers import unused_port
from deskmate.tests.signing_in import new_browser

# A fast salted hasher, so tests that make many accounts stay quick.
_TEST_PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
# The two ways the database fails to answer.
_REFUSES_CONNECTIONS = "refuses-connections"
_REJECTS_CREDENTIALS = "rejects-credentials"


@contextmanager
def _outage(kind):
    """Inside it, Deskmate's database refuses connections or rejects its credentials.

    `kind` says which. It closes Deskmate's connection on entry and on exit,
    and restores the connection's settings on exit.
    """
    connection = connections[DEFAULT_DB_ALIAS]
    with pytest.MonkeyPatch.context() as patch:
        connection.close()
        if kind == _REFUSES_CONNECTIONS:
            patch.setitem(connection.settings_dict, "HOST", "127.0.0.1")
            patch.setitem(connection.settings_dict, "PORT", str(unused_port()))
        else:
            wrong_password = f"wrong-{secrets.token_hex(8)}"
            patch.setitem(connection.settings_dict, "PASSWORD", wrong_password)
        try:
            yield
        finally:
            connection.close()


@pytest.fixture
def database_refuses_connections(django_db_blocker):
    """Point Deskmate's database connection at a local port nothing listens on."""
    with django_db_blocker.unblock(), _outage(_REFUSES_CONNECTIONS):
        yield


@pytest.fixture
def database_rejects_credentials(django_db_blocker):
    """Give Deskmate a wrong password for a database server that answers.

    Connects with the right password first, so the test cannot pass merely
    because no database is running.
    """
    with django_db_blocker.unblock():
        connections[DEFAULT_DB_ALIAS].ensure_connection()
        with _outage(_REJECTS_CREDENTIALS):
            yield


@pytest.fixture(params=[_REFUSES_CONNECTIONS, _REJECTS_CREDENTIALS])
def database_outage(request, transactional_db):
    """Return a context manager inside which Deskmate's database does not answer.

    Before it is entered the database answers, so a test can make accounts and
    sign in first, and it answers again after it is left. Inside it, the
    database refuses connections or rejects the app's credentials, as the
    fixture's parameter says. The database is not wrapped in a transaction,
    so what the test wrote before the outage is really stored.
    """
    return functools.partial(_outage, request.param)


@pytest.fixture
def make_account(db, settings):
    """Return a function that makes an account and returns its user.

    `make_account(username, password, role)` makes the user through the user
    model's `create_user`, which runs no validators, with `role` one of the
    plain strings "requester" and "support_officer". Every account of a test
    belongs to one workspace made for the test.
    """
    settings.PASSWORD_HASHERS = _TEST_PASSWORD_HASHERS
    workspaces = []

    def make(username, password, role):
        if not workspaces:
            workspaces.append(Workspace.objects.create())
        return get_user_model().objects.create_user(
            username=username, password=password, role=role, workspace=workspaces[0]
        )

    return make


@pytest.fixture
def browser():
    """Return a test client that, like a browser, gets Django's CSRF checks."""
    return new_browser()


class FrozenClock:
    """Django's clock, stopped at a whole second, which a test moves forward."""

    def __init__(self, start):
        self.start = start
        self.now = start

    def set_elapsed(self, elapsed):
        """Set the clock to `elapsed`, a timedelta, after the time it stopped at."""
        self.now = self.start + elapsed


@pytest.fixture
def clock(monkeypatch):
    """Stop `django.utils.timezone.now` at the start of the test.

    Returns a FrozenClock; until the test moves it, every call returns the
    same time, so a test can sign in at an exact moment and then move the
    clock to just before, at or after a limit.
    """
    frozen = FrozenClock(timezone.now().replace(microsecond=0))
    monkeypatch.setattr(timezone, "now", lambda: frozen.now)
    return frozen
