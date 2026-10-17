"""Making attempts, and the checks the ACC-3 tests share (accounts.md).

An attempt is a signed-out visitor's `POST /sign-in/` or `POST /demo-workspace/`
that ACC-1.8 does not refuse (ACC-3.1). The tests send attempts as a script
does: a `Visitor` loads the sign-in page once, then sends its forms again and
again with the same CSRF token, with Django's CSRF checks enforced.

Where an attempt comes from reaches Deskmate as its WSGI server gives it: the
connection's address as `REMOTE_ADDR`, which the test client sets to
127.0.0.1 unless a test changes it, and an `X-Forwarded-For` header as
`HTTP_X_FORWARDED_FOR`, in which the server has already joined several lines
with commas. Every test outside the ACC-3 tests sends from 127.0.0.1 with no
such header.

The limits' clock is `django.utils.timezone.now`, which the `clock` fixture
stops. Whether a password was checked or hashed is seen through the tests'
hasher in `deskmate.tests.hashing`, which `fast_hashing` configures. Nothing
here names how Deskmate stores what it counts: the limits' records are found
as the rows that counting an attempt adds to tables other than those of
accounts and workspaces, and the statements that check and count an attempt
as those it runs before it first reads or writes an account or a workspace.
"""

import json
import threading
import time
from collections import namedtuple
from contextlib import contextmanager

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.handlers.wsgi import WSGIHandler
from django.core.servers.basehttp import ThreadedWSGIServer, WSGIRequestHandler
from django.db import DEFAULT_DB_ALIAS, connection, connections

from deskmate.accounts.models import Workspace
from deskmate.tests.demo_workspaces import (
    DEMO_WORKSPACE,
    press_create,
    read_created_page,
    stored_rows,
)
from deskmate.tests.environment import valid_environment
from deskmate.tests.helpers import internal_details, media_type, run_python
from deskmate.tests.pages import Page
from deskmate.tests.signing_in import (
    SIGN_IN,
    WRONG_PASSWORD,
    get_sign_in_page,
    new_browser,
    submit_sign_in,
)

# The two kinds of attempt, and the route each is sent to.
SIGN_IN_ATTEMPT = "sign-in"
CREATION = "creation"
KINDS = (SIGN_IN_ATTEMPT, CREATION)
PATHS = {SIGN_IN_ATTEMPT: SIGN_IN, CREATION: DEMO_WORKSPACE}
# The limits of ACC-3.1: for each kind, how many attempts counted in the
# 10 minutes before an attempt refuse it, from one address group and from
# everyone, and the longest Retry-After (ACC-3.3).
PER_GROUP = {SIGN_IN_ATTEMPT: 10, CREATION: 3}
EVERYONE = {SIGN_IN_ATTEMPT: 30, CREATION: 5}
WINDOW_SECONDS = 600
# The fixed texts of ACC-3.2.
REFUSED = "Too many attempts"
REFUSALS = {
    SIGN_IN_ATTEMPT: "Too many sign-in attempts. Wait a few minutes, then try again.",
    CREATION: (
        "Too many demo workspaces have been created. "
        "Wait a few minutes, then try again."
    ),
}
# A synthetic username no account has; signing in with it hashes the password
# once, as Django does to take as long as for a known username.
UNKNOWN_USERNAME = "nobody"
# The client address most tests send from, from a documentation range.
ADDRESS = "203.0.113.7"
# How long Deskmate may make an attempt wait to be checked (ACC-3.7).
MAX_WAIT_SECONDS = 5
# How long a thread may take before a test gives up on it.
_THREAD_SECONDS = 60


class Source(namedtuple("Source", ["forwarded", "remote"], defaults=(None, None))):
    """Where an attempt comes from, as Deskmate's WSGI server gives it.

    `forwarded` is the value of its `X-Forwarded-For` header, with several
    lines joined with commas, or None if it has no such header. `remote` is
    the address its connection came from, or None for the test client's
    127.0.0.1.
    """

    def options(self):
        """Return the `headers` and `environ` that send a form from here."""
        headers = {} if self.forwarded is None else {"X-Forwarded-For": self.forwarded}
        environ = {} if self.remote is None else {"REMOTE_ADDR": self.remote}
        return {"headers": headers, "environ": environ}


# Where an attempt with no options comes from: 127.0.0.1, with no header.
DEFAULT_SOURCE = Source()


def forwarded_for(value, remote=None):
    """Return a Source whose X-Forwarded-For is `value`."""
    return Source(value, remote)


def numbered_source(number):
    """Return a Source whose X-Forwarded-For is IPv4 address `number`, from 1
    to 254 of 192.0.2.0/24, each a different address group."""
    assert 1 <= number <= 254, number
    return forwarded_for(f"192.0.2.{number}")


class Visitor:
    """A signed-out visitor's browser that has loaded the sign-in page once,
    and sends its forms again with the same CSRF token, as a script does."""

    def __init__(self, source=DEFAULT_SOURCE):
        self.source = source
        self.browser = new_browser()
        self.page = get_sign_in_page(self.browser)

    @property
    def token(self):
        """Return the CSRF token the page gave the browser."""
        return self.page.csrf_token()

    def attempt(
        self,
        kind,
        username=UNKNOWN_USERNAME,
        password=WRONG_PASSWORD,
        *,
        source=None,
        changes=None,
    ):
        """Send an attempt of `kind` from `source`, or this visitor's Source.

        A sign-in attempt types `username` and `password`; `changes` are
        those of `Form.submit`. Returns the response.
        """
        options = {**(source or self.source).options(), "changes": changes}
        if kind == SIGN_IN_ATTEMPT:
            return submit_sign_in(
                self.browser, self.page, username, password, **options
            )
        return press_create(self.browser, self.page, **options)


def make_attempts(kind, count, source=DEFAULT_SOURCE, **fields):
    """Send `count` attempts of `kind` from `source`, each of which must be
    allowed, and return the Visitor that sent them.

    `fields` are those of `Visitor.attempt`.
    """
    visitor = Visitor(source)
    for number in range(1, count + 1):
        assert_allowed(visitor.attempt(kind, **fields), kind, number)
    return visitor


def make_attempts_from_many(kind, count, first=1):
    """Send `count` attempts of `kind`, each allowed and each from its own
    address group: `numbered_source(first)`, then the next, and so on."""
    visitor = Visitor()
    for number in range(first, first + count):
        response = visitor.attempt(kind, source=numbered_source(number))
        assert_allowed(response, kind, number)


def fill(kind, scope):
    """Use up one limit of `kind`, as ACC-3.3's examples do, and return the
    Source whose next attempt that limit alone refuses.

    For `scope` "address-group", ADDRESS sends PER_GROUP attempts; for
    "everyone", EVERYONE attempts come from as many address groups, and the
    Source returned is another one.
    """
    if scope == "address-group":
        source = forwarded_for(ADDRESS)
        make_attempts(kind, PER_GROUP[kind], source)
        return source
    make_attempts_from_many(kind, EVERYONE[kind])
    return forwarded_for(ADDRESS)


def limit_of(kind, scope):
    """Return the number of `kind`'s limit for `scope`, as `fill` names it."""
    return (PER_GROUP if scope == "address-group" else EVERYONE)[kind]


def assert_allowed(response, kind, number=None):
    """Assert `response` is not a refusal but what ACC-1 or ACC-2 says for an
    attempt of `kind` from a signed-out visitor.

    A sign-in attempt gets the sign-in page or, if it signed someone in, a
    redirect; a creation gets the page of ACC-2.1. `number` names the attempt
    in the message.
    """
    which = f"Attempt {number}" if number is not None else "The attempt"
    assert response.status_code != 429, f"{which} of kind {kind!r} was refused."
    if kind == CREATION:
        read_created_page(response)
        return
    assert response.status_code in (200, 302), (
        f"{which} got {response.status_code}, not the sign-in page or a redirect."
    )
    if response.status_code == 200:
        assert Page(response).title == "Sign in"


def assert_refused(response, kind, retry_after=None, sent=()):
    """Assert `response` is the refusal of ACC-3.2 for an attempt of `kind`,
    and return its Retry-After as a number of seconds.

    `retry_after`, if given, is the exact number of seconds its Retry-After
    must give; otherwise it must be a whole number from 1 to 600 (ACC-3.3).
    `sent` are values the request sent, none of which the page may show.
    """
    assert response.status_code == 429, (
        f"Expected the 429 of ACC-3.2, got {response.status_code}."
    )
    header = response.get("Retry-After")
    assert header is not None, "The 429 has no Retry-After header."
    assert header.isascii() and header.isdigit(), f"Retry-After is {header!r}."
    seconds = int(header)
    if retry_after is None:
        assert 1 <= seconds <= WINDOW_SECONDS, f"Retry-After is {header}."
    else:
        assert header == str(retry_after), (
            f"Expected Retry-After: {retry_after}, got {header!r}."
        )
    assert media_type(response) == "text/html"
    page = Page(response)
    assert page.title == REFUSED
    assert page.heading_texts == [REFUSED]
    assert page.text == f"{REFUSED} {REFUSED} {REFUSALS[kind]}"
    body = response.content.decode("utf-8", "replace")
    assert internal_details(body, {"the secret key": settings.SECRET_KEY}) == []
    shown = [value for value in sent if value and value in body]
    assert not shown, f"The page shows what the request sent: {shown}"
    return seconds


def account_tables():
    """Return the names of the tables that hold accounts and workspaces."""
    return {get_user_model()._meta.db_table, Workspace._meta.db_table}


def added_rows(before):
    """Return each row stored now but not in `before`, a stored_rows, as a
    `(table, text)` pair, leaving out accounts and workspaces."""
    left_out = account_tables()
    return [
        (table, text)
        for table, texts in stored_rows().items()
        if table not in left_out
        for text in texts
        if text not in set(before.get(table, ()))
    ]


def table_records(table):
    """Return each row of `table` as a dict from its columns' names to values."""
    with connection.cursor() as cursor:
        cursor.execute(f"SELECT * FROM {connection.ops.quote_name(table)}")
        names = [column.name for column in cursor.description]
        return [dict(zip(names, row, strict=True)) for row in cursor.fetchall()]


def touches_accounts(sql):
    """Return whether `sql` reads or writes accounts or workspaces."""
    return any(connection.ops.quote_name(table) in sql for table in account_tables())


@contextmanager
def recording_statements():
    """Inside it, return a list of the SQL of each statement Deskmate's
    connection, in this thread, runs."""
    statements = []

    def record(execute, sql, params, many, context):
        statements.append(sql)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(record):
        yield statements


def check_statements(kind, visitor):
    """Send an allowed attempt of `kind` from `visitor`, and return the SQL of
    each statement it ran before it first read or wrote an account or a
    workspace, in order: those that check it against the limits and count it.

    Fails if it ran none, because then the limits could keep no count in the
    database (ACC-3.6).
    """
    with recording_statements() as statements:
        response = visitor.attempt(kind)
    assert_allowed(response, kind)
    before = []
    for sql in statements:
        if touches_accounts(sql):
            break
        before.append(sql)
    assert before, (
        "The attempt ran no database statement before it read or wrote an "
        "account or a workspace, so nothing was checked or counted in the "
        "database first."
    )
    return before


class FailingStatement:
    """A database execute wrapper that makes one statement fail as the database
    would: the statement numbered `number`, from 0, of those it sees, raises
    Django's OperationalError instead of running."""

    def __init__(self, number):
        self.number = number
        self.seen = 0
        self.failed = None

    def __call__(self, execute, sql, params, many, context):
        """Run one statement for Deskmate, unless it is the one that fails."""
        number, self.seen = self.seen, self.seen + 1
        if number == self.number:
            self.failed = sql
            database = context["connection"]
            with database.wrap_database_errors:
                raise database.Database.OperationalError(
                    "server closed the connection unexpectedly (synthetic)"
                )
        return execute(sql, params, many, context)


def _in_thread(target, name):
    """Return a started thread running `target`, which closes its own
    database connections when it ends."""

    def run():
        try:
            target()
        finally:
            connections.close_all()

    thread = threading.Thread(target=run, name=name, daemon=True)
    thread.start()
    return thread


def attempts_together(kind, sources, statement_seconds=0.02):
    """Send one attempt of `kind` from each of `sources` at once, and return
    their responses in order.

    Each comes from its own thread and database connection, as from separate
    server instances. Each thread first loads the sign-in page, then waits at
    a barrier until every thread is ready, so all the attempts are released
    together. Every statement each attempt runs waits `statement_seconds`
    first, so attempts that are not made to wait for each other overlap.
    Needs the `transactional_db` fixture.
    """
    assert not connection.in_atomic_block, "attempts_together needs transactional_db."
    barrier = threading.Barrier(len(sources))
    responses = [None] * len(sources)
    problems = []

    def slow(execute, sql, params, many, context):
        time.sleep(statement_seconds)
        return execute(sql, params, many, context)

    def attempt(number, source):
        def run():
            try:
                visitor = Visitor(source)
                visitor.browser.raise_request_exception = False
                with connections[DEFAULT_DB_ALIAS].execute_wrapper(slow):
                    barrier.wait(_THREAD_SECONDS)
                    responses[number] = visitor.attempt(kind)
            except Exception as error:  # noqa: BLE001 -- reported below.
                barrier.abort()
                problems.append(f"Attempt {number + 1}: {type(error).__name__}")

        return run

    threads = [
        _in_thread(attempt(number, source), f"attempt-{number + 1}")
        for number, source in enumerate(sources)
    ]
    for thread in threads:
        thread.join(_THREAD_SECONDS)
    assert not any(thread.is_alive() for thread in threads), "An attempt hung."
    assert not problems, problems
    return responses


class HeldCheck:
    """Another attempt of `kind`, sent from `source` in another thread and
    database connection, that stops partway through its check.

    It stops just after it first runs `sql`, the last statement that checks
    and counts it, before its check ends; so, inside `holding`, it is still
    being checked, and attempts of its kind must wait for it (ACC-3.6). It
    goes on after `seconds`, or when `holding` ends if that is sooner. After
    `holding` ends, `response` is its response.
    """

    def __init__(self, kind, sql, seconds, source):
        self.kind = kind
        self.sql = sql
        self.seconds = seconds
        self.source = source
        self.response = None
        self.problems = []
        self._stopped = threading.Event()
        self._released = threading.Event()

    def _stop_after(self, execute, sql, params, many, context):
        """Run one statement; after the first that is `sql`, stop for a while."""
        result = execute(sql, params, many, context)
        if sql == self.sql and not self._stopped.is_set():
            self._stopped.set()
            self._released.wait(self.seconds)
        return result

    def _run(self):
        """Send the attempt, stopping partway through its check."""
        try:
            visitor = Visitor(self.source)
            visitor.browser.raise_request_exception = False
            with connections[DEFAULT_DB_ALIAS].execute_wrapper(self._stop_after):
                self.response = visitor.attempt(self.kind)
        except Exception as error:  # noqa: BLE001 -- reported by holding.
            self.problems.append(f"{type(error).__name__}: {error}")
        finally:
            self._stopped.set()

    @contextmanager
    def holding(self):
        """Inside it, the other attempt is stopped partway through its check."""
        assert not connection.in_atomic_block, "HeldCheck needs transactional_db."
        thread = _in_thread(self._run, "held-attempt")
        assert self._stopped.wait(_THREAD_SECONDS), "The other attempt never ran."
        assert not self.problems, self.problems
        try:
            yield self
        finally:
            self._released.set()
            thread.join(_THREAD_SECONDS)
            assert not thread.is_alive(), "The other attempt hung."
        assert not self.problems, self.problems


def sign_in_attempts_in_new_process(count, forwarded):
    """Send `count` sign-in attempts with an empty password, each with
    X-Forwarded-For `forwarded`, from Deskmate started in a new process, as
    another server instance, using this test's database and secret key.

    Returns the status of each. Needs the `transactional_db` fixture, so the
    new process sees what this one counted.
    """
    environment = valid_environment(
        {
            "POSTGRES_DB": connection.settings_dict["NAME"],
            "DJANGO_SECRET_KEY": settings.SECRET_KEY,
        }
    )
    environment["DJANGO_SETTINGS_MODULE"] = "deskmate.settings"
    arguments = ["-m", "deskmate.tests.attempts_probe", str(count), forwarded]
    process = run_python(arguments, environment)
    if process.returncode != 0 or not process.stdout.strip():
        raise AssertionError(
            f"The other instance exited with {process.returncode}.\n{process.stderr}"
        )
    return json.loads(process.stdout.strip().splitlines()[-1])


@contextmanager
def running_server():
    """Inside it, Deskmate is served over HTTP by Django's own threaded WSGI
    server on a free local port, whose URL it returns.

    Like other WSGI servers, it gives Deskmate several lines of one header as
    one value, joined with commas in the order they arrived. Each request runs
    in its own thread and database connection, so the test needs the
    `transactional_db` fixture.
    """
    assert not connection.in_atomic_block, "running_server needs transactional_db."
    server = ThreadedWSGIServer(("127.0.0.1", 0), WSGIRequestHandler)
    server.set_app(WSGIHandler())
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        host, port = server.server_address[:2]
        yield f"http://{host}:{port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(_THREAD_SECONDS)
