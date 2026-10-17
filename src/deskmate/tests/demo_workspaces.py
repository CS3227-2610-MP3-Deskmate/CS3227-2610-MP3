"""Creating demo workspaces, and the checks the ACC-2 tests share (accounts.md).

The tests create a workspace as a visitor does: they load the sign-in page and
press Create demo workspace, with Django's CSRF checks enforced. Everything
they expect comes from ACC-2. The one thing they need from Deskmate's code is
a way to choose the codes it draws, so that codes can clash (ACC-2.3): each
time Deskmate draws a code it calls `deskmate.accounts.demo.random_code()`,
which the `codes` fixture replaces with a `Draws`.

A `Watch` records what a creation generates and what the database reports, so
a test can look for those values where they must not appear, and it can make
another creation take a code's usernames while the accounts are being saved.
It learns each password hashed and its hash from the tests' hasher in
`deskmate.tests.hashing`, which the `fast_hashing` fixture configures.
"""

import re
import threading
import zlib
from collections import namedtuple
from contextlib import contextmanager
from importlib import import_module
from urllib.parse import unquote, urlsplit

import pytest
from django.conf import settings
from django.contrib.auth import SESSION_KEY, get_user_model
from django.contrib.auth.hashers import check_password
from django.core import signing
from django.db import DatabaseError, connection, connections, transaction

from deskmate.accounts.models import Workspace
from deskmate.tests.hashing import reporting_hashes_to
from deskmate.tests.pages import CSRF_FIELD, SITE, Page
from deskmate.tests.signing_in import (
    REQUESTER,
    ROLE_TITLES,
    SIGN_IN,
    SUPPORT_OFFICER,
    get_sign_in_page,
)

DEMO_WORKSPACE = "/demo-workspace/"
# The fixed texts of ACC-2.1.
CREATE = "Create demo workspace"
INVITATION = (
    "No account? Create a demo workspace with 2 Requesters and 1 Support Officer."
)
CREATED = "Demo workspace created"
COPY_NOW = "Copy these passwords now. They will not be shown again."
COLUMNS = ["Username", "Role", "Password"]
SIGN_IN_LINK = "Sign in"
# What ACC-2.3 generates: each account's username before its code, and its
# role, in the order the page lists them, and the codes' and passwords'
# lengths and characters. A creation draws at most MAX_CODES codes.
ACCOUNTS = (
    ("requester1", REQUESTER),
    ("requester2", REQUESTER),
    ("support1", SUPPORT_OFFICER),
)
ALPHABET = "23456789abcdefghjkmnpqrstuvwxyz"
CODE_LENGTH = 6
PASSWORD_LENGTH = 16
MAX_CODES = 3
# The function the tests replace to choose the codes Deskmate draws.
RANDOM_CODE = "deskmate.accounts.demo.random_code"
# When a clashing username is taken: before the visitor presses the button, or
# by another creation that finishes while the accounts are being saved.
CLASH_TIMES = ["before", "meanwhile"]
# Both debug modes, for what ACC-2.4 and ACC-2.6 require in either. A test
# turns debug on with `settings.DEBUG = True`, which Django reads per request.
DEBUG_MODES = [pytest.param(False, id="debug-off"), pytest.param(True, id="debug-on")]

# An account the created page shows, with its stored role.
Account = namedtuple("Account", ["username", "role", "password"])

# A generated username, wherever it appears in a statement or its parameters.
_GENERATED_USERNAME = re.compile(r"(?:requester1|requester2|support1)-[0-9a-z]+")
# How long another connection may take to save accounts while a request waits.
_MEANWHILE_SECONDS = 30


def usernames_for(code):
    """Return the three usernames ACC-2.3 makes from `code`, in the page's order."""
    return [f"{prefix}-{code}" for prefix, _ in ACCOUNTS]


def role_of(username):
    """Return the role of the generated account whose username is `username`."""
    return dict(ACCOUNTS)[username.split("-", 1)[0]]


def press_create(browser, page=None, **options):
    """Press Create demo workspace on `page`, or on a sign-in page `browser` loads.

    `options` are those of `Form.submit`. Returns the response.
    """
    page = page or get_sign_in_page(browser)
    return page.form_with_button(CREATE).submit(browser, button=CREATE, **options)


def assert_demo_form(page):
    """Assert the sign-in `page` has, after its sign-in form, the text and the
    form of ACC-2.1, and return that form."""
    sign_in_form = page.form_with_button("Sign in")
    form = page.form_with_button(CREATE)
    assert page.forms == [sign_in_form, form], (
        "Expected the sign-in form, then the demo workspace form, and no other."
    )
    assert INVITATION in sign_in_form.text_after, page.text
    assert page.text.count(INVITATION) == 1, page.text
    assert form.method == "post"
    url = urlsplit(form.url)
    assert (url.netloc, url.path, url.query) == (SITE, DEMO_WORKSPACE, ""), form.url
    buttons = [control for control in form.controls if control.looks_like_button()]
    assert [button.caption for button in buttons] == [CREATE]
    assert buttons[0].is_button() and not buttons[0].name, "The button sends a field."
    sent = [control for control in form.controls if control.is_sent()]
    assert [control.name for control in sent] == [CSRF_FIELD]
    assert sent[0].type == "hidden" and sent[0].value
    return form


def stored_state():
    """Return every workspace's id, and every account's stored fields by its id."""
    workspaces = frozenset(Workspace.objects.values_list("pk", flat=True))
    accounts = {row["id"]: row for row in get_user_model().objects.values()}
    return workspaces, accounts


def _saved_since(before, elsewhere=()):
    """Return the workspaces and accounts saved since `before`, a stored_state.

    Leaves out the accounts whose usernames are in `elsewhere`, which another
    creation saved meanwhile, and their workspaces. Checks that every
    workspace and account in `before` is still there, unchanged.
    """
    workspaces, accounts = stored_state()
    old_workspaces, old_accounts = before
    unchanged = {pk: accounts.get(pk) for pk in old_accounts}
    assert unchanged == old_accounts, "An account that existed before changed."
    assert old_workspaces <= workspaces, "A workspace that existed before is gone."
    others = {
        pk
        for pk, account in accounts.items()
        if pk not in old_accounts and account["username"] in elsewhere
    }
    other_workspaces = {accounts[pk]["workspace_id"] for pk in others}
    new_accounts = [
        account
        for pk, account in accounts.items()
        if pk not in old_accounts and pk not in others
    ]
    return workspaces - old_workspaces - other_workspaces, new_accounts


def assert_nothing_created(before, elsewhere=()):
    """Assert no workspace or account was saved since `before`, a stored_state,
    and none that existed then changed, apart from the accounts in `elsewhere`
    that another creation saved meanwhile."""
    workspaces, accounts = _saved_since(before, elsewhere)
    usernames = sorted(account["username"] for account in accounts)
    assert not workspaces and not accounts, (
        f"{len(workspaces)} workspaces and these accounts remain: {usernames}"
    )


def read_created_page(response):
    """Assert `response` is the page of ACC-2.1, showing accounts generated as
    ACC-2.3 says, and return its accounts in order."""
    assert response.status_code == 200, (
        f"Expected the {CREATED} page, got {response.status_code}."
    )
    page = Page(response)
    assert page.title == CREATED
    assert page.heading_texts == [CREATED]
    assert len(page.tables) == 1, f"Expected one table, got {len(page.tables)}."
    header, *rows = page.tables[0]
    assert header == [("th", column) for column in COLUMNS], header
    cells = [[text for _, text in row] for row in rows]
    assert len(cells) == len(ACCOUNTS), f"Expected 3 accounts' rows, got {cells}."
    assert all(len(row) == len(COLUMNS) for row in cells), cells
    shown = " ".join(" ".join(row) for row in cells)
    expected = f"{CREATED} {CREATED} {COPY_NOW} {' '.join(COLUMNS)} {shown}"
    assert page.text == f"{expected} {SIGN_IN_LINK}"
    assert len(page.links) == 1, page.links
    text, url = page.links[0]
    parts = urlsplit(url)
    assert (text, parts.netloc, parts.path, parts.query, parts.fragment) == (
        SIGN_IN_LINK,
        SITE,
        SIGN_IN,
        "",
        "",
    ), page.links
    titles = [row[1] for row in cells]
    assert titles == [ROLE_TITLES[role] for _, role in ACCOUNTS], titles
    accounts = [
        Account(username, role, password)
        for (username, _, password), (_, role) in zip(cells, ACCOUNTS, strict=True)
    ]
    assert_generated(accounts)
    return accounts


def assert_generated(accounts):
    """Assert `accounts`, in the page's order, are named and given passwords as
    ACC-2.3 says."""
    codes = set()
    pattern = f"([{ALPHABET}]{{{CODE_LENGTH}}})"
    for account, (prefix, _) in zip(accounts, ACCOUNTS, strict=True):
        match = re.fullmatch(f"{prefix}-{pattern}", account.username)
        assert match, (
            f"{account.username!r} is not {prefix}- and a code of "
            f"{CODE_LENGTH} of the {len(ALPHABET)} characters."
        )
        codes.add(match[1])
        password = account.password
        assert len(password) == PASSWORD_LENGTH, f"{password!r} is not 16 long."
        assert set(password) <= set(ALPHABET), f"{password!r} has other characters."
    assert len(codes) == 1, f"The usernames do not share one code: {codes}"
    passwords = {account.password for account in accounts}
    assert len(passwords) == len(accounts), "Two accounts have the same password."


def assert_created(response, before, elsewhere=()):
    """Assert `response` is the page of ACC-2.1 for one workspace created since
    `before`, a stored_state, and return the accounts it shows.

    The new workspace must hold exactly those accounts, with their roles and
    passwords, and nothing that existed before may change (ACC-2.2). Accounts
    whose usernames are in `elsewhere`, which another creation saved
    meanwhile, and their workspaces are left out.
    """
    accounts = read_created_page(response)
    workspaces, saved = _saved_since(before, elsewhere)
    assert len(workspaces) == 1, f"Expected 1 new workspace, got {len(workspaces)}."
    by_username = {account["username"]: account for account in saved}
    shown = sorted(account.username for account in accounts)
    assert sorted(by_username) == shown, "The new accounts are not those shown."
    for account in accounts:
        stored = by_username[account.username]
        assert stored["workspace_id"] in workspaces
        assert stored["role"] == account.role, f"{account.username} has another role."
        assert check_password(account.password, stored["password"]), (
            f"The password shown for {account.username} is not its password."
        )
    return accounts


def _session_store():
    """Return the SessionStore class of the session engine Deskmate uses."""
    return import_module(settings.SESSION_ENGINE).SessionStore


def signed_in_account_ids():
    """Return the id, as a string, of each account a stored session signs in."""
    store = _session_store()
    sessions = store.get_model_class().objects.all()
    signed_in = {
        store().decode(session.session_data).get(SESSION_KEY) for session in sessions
    }
    return signed_in - {None}


def records_holding(values):
    """Return where a database row's text holds one of `values`, as
    `<table> row <number>`, for every table."""
    found = []
    with connection.cursor() as cursor:
        for table in connection.introspection.table_names(cursor):
            name = connection.ops.quote_name(table)
            cursor.execute(f"SELECT CAST(t AS text) FROM {name} AS t")
            for number, (text,) in enumerate(cursor.fetchall(), 1):
                if any(value in text for value in values):
                    found.append(f"{table} row {number}")
    return found


def sessions_holding(values):
    """Return the number of each stored session whose data holds one of `values`."""
    store = _session_store()
    sessions = store.get_model_class().objects.all()
    return [
        number
        for number, session in enumerate(sessions, 1)
        if any(value in repr(store().decode(session.session_data)) for value in values)
    ]


def cookies_holding(values, *jars):
    """Return the name of each cookie in `jars` that holds one of `values`.

    `jars` are cookie collections, such as a response's or a browser's. A
    cookie's value is read as sent, URL-decoded, and decoded as Django's
    signed values are; the session cookie is also read as the session it
    names.
    """
    found = []
    for jar in jars:
        for name, morsel in jar.items():
            readings = _readings(morsel.value)
            if name == settings.SESSION_COOKIE_NAME:
                store = _session_store()
                readings.append(repr(store(session_key=morsel.value).load()))
            if any(value in reading for value in values for reading in readings):
                found.append(name)
    return found


def _readings(value):
    """Return `value` as sent, URL-decoded, and decoded as signing.dumps encodes."""
    readings = [value, unquote(value)]
    payload = unquote(value).split(":")[0]
    try:
        data = signing.b64_decode(payload.lstrip(".").encode())
        if payload.startswith("."):
            data = zlib.decompress(data)
    except (ValueError, zlib.error):
        return readings
    return [*readings, data.decode("utf-8", "replace")]


def found_in(text, values):
    """Return the description of each of `values`, a mapping, found in `text`."""
    return [label for label, value in values.items() if value in text]


class Draws:
    """Stands in for `deskmate.accounts.demo.random_code`.

    Returns the test's codes in order and counts how many were drawn. Drawing
    more codes than the test gave fails.
    """

    def __init__(self, codes):
        self.codes = list(codes)
        self.count = 0

    def __call__(self, *args, **kwargs):
        """Return the next code."""
        self.count += 1
        assert self.count <= len(self.codes), (
            f"Code {self.count} was drawn; the test gave {len(self.codes)}."
        )
        return self.codes[self.count - 1]


class Watch:
    """What Deskmate generates, and what its database reports, inside `watching`.

    It records each password the tests' hasher hashes and the hash, each
    generated username sent to the database, and each database error.
    """

    def __init__(self):
        self.passwords = []
        self.hashes = []
        self.usernames = set()
        self.errors = []
        self.problems = []
        self._meanwhile = {}

    def hashed(self, password, encoded):
        """Record that `password` was hashed as `encoded`."""
        self.passwords.append(password)
        self.hashes.append(encoded)

    def take_meanwhile(self, usernames):
        """Have another creation take `usernames` while the accounts are saved.

        Just before the request first saves an account whose username has the
        code of one of `usernames`, accounts with those usernames are saved in
        a new workspace from another database connection, and committed. So
        the code clashes because a creation finished meanwhile (ACC-2.3), and
        the clash is found only when the accounts are saved.

        It needs the `transactional_db` fixture, whose database is emptied
        after the test, because the other connection commits those accounts,
        and rolling back a test's transaction would leave them in place.
        """
        assert not connection.in_atomic_block, (
            "take_meanwhile needs transactional_db, not a database wrapped in a "
            "transaction."
        )
        for username in usernames:
            code = username.split("-", 1)[1]
            self._meanwhile.setdefault(code, []).append(username)

    def __call__(self, execute, sql, params, many, context):
        """Run one statement for Deskmate, recording what it sends and its errors."""
        texts = [sql, *_strings(params)]
        for text in texts:
            self.usernames.update(_GENERATED_USERNAME.findall(text))
        if _saves_account(sql):
            for code in list(self._meanwhile):
                if any(text.endswith(f"-{code}") for text in texts):
                    self._save_elsewhere(self._meanwhile.pop(code))
        try:
            return execute(sql, params, many, context)
        except Exception as error:
            self.errors.append(error)
            raise

    def _save_elsewhere(self, usernames):
        """Save and commit accounts with `usernames` from another connection."""
        failures = []

        def save():
            try:
                with transaction.atomic():
                    workspace = Workspace.objects.create()
                    for username in usernames:
                        get_user_model().objects.create_user(
                            username=username,
                            password=None,
                            role=role_of(username),
                            workspace=workspace,
                        )
            except DatabaseError as error:
                failures.append(f"{type(error).__name__}: {error}")
            finally:
                connections.close_all()

        thread = threading.Thread(target=save)
        thread.start()
        thread.join(_MEANWHILE_SECONDS)
        if thread.is_alive():
            failures.append("Another connection could not save accounts in time.")
        self.problems += failures

    def generated(self, accounts=()):
        """Return, by description, each generated username, password and hash.

        Each hash's salt and digest are included too, because PostgreSQL
        shortens long values in the rows its errors show. `accounts` adds the
        accounts a page showed.
        """
        values = {}
        usernames = {*self.usernames, *(account.username for account in accounts)}
        passwords = {*self.passwords, *(account.password for account in accounts)}
        for number, username in enumerate(sorted(usernames), 1):
            values[f"generated username {number}"] = username
        for number, password in enumerate(sorted(passwords), 1):
            values[f"generated password {number}"] = password
        for number, encoded in enumerate(sorted(set(self.hashes)), 1):
            values[f"password hash {number}"] = encoded
            secret_parts = [part for part in encoded.split("$") if len(part) >= 16]
            for part_number, part in enumerate(secret_parts, 1):
                values[f"password hash {number}, part {part_number}"] = part
        return values


@contextmanager
def watching():
    """Return a Watch of Deskmate's database connection and hasher inside it.

    Fails on leaving if the Watch could not save accounts meanwhile.
    """
    watch = Watch()
    with reporting_hashes_to(watch.hashed), connection.execute_wrapper(watch):
        yield watch
    assert not watch.problems, watch.problems


def _strings(params):
    """Yield every string among a statement's parameters, however nested."""
    if isinstance(params, str):
        yield params
    elif isinstance(params, dict):
        for value in params.values():
            yield from _strings(value)
    elif isinstance(params, (list, tuple)):
        for value in params:
            yield from _strings(value)


def _saves_account(sql):
    """Return whether `sql` inserts rows into the accounts table."""
    table = re.escape(get_user_model()._meta.db_table)
    pattern = rf'\s*INSERT\s+INTO\s+"?{table}"?[\s(]'
    return re.match(pattern, sql, re.IGNORECASE) is not None


class PartwayFailure:
    """Inside it, every third account row the database is asked to insert fails
    with an error whose detail holds that row, password hash included.

    So a creation fails after its workspace and two of its accounts are
    written, and so does every attempt it makes again. `kind` chooses the
    error: "not-null" is PostgreSQL's own not-null violation, which Django
    raises as IntegrityError, and "disk-full" is raised as a full disk is,
    which Django raises as OperationalError. `error_type` is that name.
    """

    _ERROR_TYPES = {"not-null": "IntegrityError", "disk-full": "OperationalError"}
    _FAILURES = {
        "not-null": "NEW.workspace_id := NULL;",
        "disk-full": (
            "RAISE EXCEPTION 'could not extend relation: No space left on device' "
            "USING ERRCODE = 'disk_full', "
            "DETAIL = format('Failing row contains %s.', NEW);"
        ),
    }
    _NAME = "deskmate_test_fail_third_account"
    _COUNTER = "deskmate_test_account_inserts"

    def __init__(self, kind):
        self.kind = kind
        self.error_type = self._ERROR_TYPES[kind]

    def __enter__(self):
        """Make the database fail every third account row from now on."""
        table = connection.ops.quote_name(get_user_model()._meta.db_table)
        function = f"""
            CREATE FUNCTION {self._NAME}() RETURNS trigger LANGUAGE plpgsql AS $$
            BEGIN
                IF nextval('{self._COUNTER}') % 3 = 0 THEN
                    {self._FAILURES[self.kind]}
                END IF;
                RETURN NEW;
            END
            $$
        """
        with connection.cursor() as cursor:
            cursor.execute(f"CREATE SEQUENCE {self._COUNTER}")
            cursor.execute(function)
            cursor.execute(
                f"CREATE TRIGGER {self._NAME} BEFORE INSERT ON {table} "
                f"FOR EACH ROW EXECUTE FUNCTION {self._NAME}()"
            )
        return self

    def __exit__(self, *exc_info):
        """Let the database insert accounts again."""
        self.remove()

    def remove(self):
        """Remove the failure, if it is there."""
        table = connection.ops.quote_name(get_user_model()._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(f"DROP TRIGGER IF EXISTS {self._NAME} ON {table}")
            cursor.execute(f"DROP FUNCTION IF EXISTS {self._NAME}()")
            cursor.execute(f"DROP SEQUENCE IF EXISTS {self._COUNTER}")


class _InterfaceErrorOnThirdRow:
    """A database execute wrapper that makes the statement inserting every third
    account row fail with Django's InterfaceError, whose message holds the
    statement's text values."""

    def __init__(self):
        self.rows = 0

    def __call__(self, execute, sql, params, many, context):
        """Run one statement for Deskmate, unless it inserts a third account row."""
        if _saves_account(sql):
            texts = list(_strings(params))
            generated = [text for text in texts if _GENERATED_USERNAME.fullmatch(text)]
            before, self.rows = self.rows, self.rows + max(1, len(generated))
            if before // 3 != self.rows // 3:
                database = context["connection"]
                # As the driver's errors are: Django raises the driver's
                # InterfaceError as its own, chained to it.
                with database.wrap_database_errors:
                    raise database.Database.InterfaceError(
                        f"the connection was lost while sending ({', '.join(texts)})"
                    )
        return execute(sql, params, many, context)


@contextmanager
def interface_error_partway():
    """Inside it, every third account row Deskmate's connection is asked to insert
    fails with Django's InterfaceError, as when the driver loses its connection.

    InterfaceError is a Django database `Error` but not a `DatabaseError`. Its
    message holds the row's text, generated username and password hash
    included. So a creation fails after its workspace and two of its accounts
    are written, and so does every attempt it makes again. The connection stays
    usable, so what was written remains unless the creation undoes it. Enter it
    inside `watching`, so that the Watch sees each statement and the error.
    """
    with connection.execute_wrapper(_InterfaceErrorOnThirdRow()):
        yield
