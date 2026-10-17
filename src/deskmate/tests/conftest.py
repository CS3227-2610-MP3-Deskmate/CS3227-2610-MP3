"""Fixtures that put Deskmate's database into the states the criteria name, make
accounts, control the clock and the codes Deskmate draws, and capture what
Deskmate writes to standard error and its logs."""

import functools
import io
import logging
import secrets
from contextlib import contextmanager

import pytest

# The shared checks are plain asserts; this makes pytest explain their failures
# as it does in test files. It must run before the modules are imported.
pytest.register_assert_rewrite(
    "deskmate.tests.signing_in",
    "deskmate.tests.pages",
    "deskmate.tests.demo_workspaces",
)

from django.contrib.auth import get_user_model
from django.db import DEFAULT_DB_ALIAS, connections
from django.utils import timezone

from deskmate.accounts.models import Workspace
from deskmate.tests.demo_workspaces import (
    RANDOM_CODE,
    RECORDING_HASHER,
    Draws,
    PartwayFailure,
)
from deskmate.tests.helpers import unused_port
from deskmate.tests.signing_in import new_browser

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


@pytest.fixture(params=["not-null", "disk-full"])
def database_fails_partway(request, transactional_db):
    """Return a PartwayFailure: inside it, the database fails partway through
    saving a workspace's accounts, with an error whose detail holds the row.

    Parametrised by the PartwayFailure's kinds, "not-null" and "disk-full".
    The database is not wrapped in a transaction, so what a request writes
    before the failure is really stored unless the request undoes it.
    """
    failure = PartwayFailure(request.param)
    try:
        yield failure
    finally:
        failure.remove()


@pytest.fixture
def fast_hashing(settings):
    """Hash passwords with a fast salted hasher that tells each Watch what it hashes."""
    settings.PASSWORD_HASHERS = [RECORDING_HASHER]


@pytest.fixture
def make_account(db, fast_hashing):
    """Return a function that makes an account and returns its user.

    `make_account(username, password, role)` makes the user through the user
    model's `create_user`, which runs no validators, with `role` one of the
    plain strings "requester" and "support_officer". Every account of a test
    belongs to one workspace made for the test.
    """
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


@pytest.fixture
def codes(monkeypatch):
    """Return a function that makes Deskmate draw the codes it is given, in order.

    `codes(*given)` replaces `deskmate.accounts.demo.random_code` with a Draws
    of `given`, which counts the draws, and returns the Draws.
    """

    def draw(*given):
        draws = Draws(given)
        monkeypatch.setattr(RANDOM_CODE, draws)
        return draws

    return draw


class WrittenOutput:
    """Everything Deskmate writes to standard error or its logs during a test."""

    def __init__(self, capsys):
        self.stream = io.StringIO()
        self._capsys = capsys
        self._stderr = []

    def text(self):
        """Return what has been written so far."""
        self._stderr.append(self._capsys.readouterr().err)
        return self.stream.getvalue() + "".join(self._stderr)


def _writes_output(handler):
    """Return whether `handler` writes log records to a stream for the app."""
    return (
        isinstance(handler, logging.StreamHandler)
        and not isinstance(handler, logging.FileHandler)
        and not type(handler).__module__.startswith("_pytest")
    )


@pytest.fixture
def written_output(capsys):
    """Return a WrittenOutput of what Deskmate writes during the test.

    Every stream handler that the logging configuration gave any logger, such
    as the one that writes server errors to standard error (PLT-1.4), writes
    to it instead of its stream. So does a handler for warnings and errors on
    the root logger, which stands in for the one Python uses when no other
    handles a record. What is written to sys.stderr is captured too.
    """
    output = WrittenOutput(capsys)
    root = logging.getLogger()
    loggers = [root, *logging.Logger.manager.loggerDict.values()]
    handlers = {
        handler
        for logger in loggers
        for handler in getattr(logger, "handlers", [])
        if _writes_output(handler)
    }
    previous = {handler: handler.setStream(output.stream) for handler in handlers}
    fallback = logging.StreamHandler(output.stream)
    fallback.setLevel(logging.WARNING)
    root.addHandler(fallback)
    try:
        yield output
    finally:
        root.removeHandler(fallback)
        for handler, stream in previous.items():
            if stream is not None:
                handler.setStream(stream)
