"""ACC-2.4, and the part of ACC-2.6 about standard output, standard error and
logs: creations that fail, what they leave behind, including the sample
articles and tickets of ACC-2.9, and what Deskmate writes about them.

`written_output` captures what Deskmate writes to standard output, standard
error and its logs.

Tests where a creation fails partway or codes clash use a database that is not
wrapped in a transaction, so what a failed attempt writes would really remain
unless the attempt undoes it. Each test of what Deskmate writes when a
creation fails checks first that an error the database raised held a
generated value, so the check of what was written can find one.
"""

import re

import pytest
from django.db import DatabaseError, InterfaceError

from deskmate.knowledge.models import Article
from deskmate.tests.demo_workspaces import (
    ACCOUNTS,
    CLASH_TIMES,
    DEBUG_MODES,
    MAX_CODES,
    SAMPLE_ARTICLES,
    SAMPLE_TICKETS,
    assert_created,
    assert_nothing_created,
    found_in,
    interface_error_partway,
    press_create,
    role_of,
    stored_state,
    usernames_for,
    watching,
)
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    SUPPORT_OFFICER,
    assert_server_error,
    get_sign_in_page,
)
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.usefixtures("fast_hashing")

# Codes, from the 31 characters, for the tests to make Deskmate draw. The
# fourth is never taken, so drawing it would let a creation succeed.
CODES = ("aaaaaa", "bbbbbb", "cccccc", "dddddd")
TRACEBACK = "Traceback (most recent call last)"
# The database fails after some but not all of a creation is written (ACC-2.4):
# while it writes its last sample ticket or its last sample article of
# ACC-2.9, so every 3rd ticket row or every 2nd article row fails. The cases
# pair each table, error kind of PartwayFailure and debug mode with each value
# of the other two.
LAST_TICKET = (Ticket, len(SAMPLE_TICKETS))
LAST_ARTICLE = (Article, len(SAMPLE_ARTICLES))
LAST_SAMPLE_FAILURES = [
    pytest.param(*LAST_TICKET, "not-null", False, id="ticket-debug-off"),
    pytest.param(*LAST_TICKET, "disk-full", True, id="ticket-debug-on"),
    pytest.param(*LAST_ARTICLE, "disk-full", False, id="article-debug-off"),
    pytest.param(*LAST_ARTICLE, "not-null", True, id="article-debug-on"),
]


def not_shown(watch, error_type="IntegrityError"):
    """Return, by description, what a failed creation's 500 page must not show:
    every generated value, the start of any generated username, and the type
    of the error the creation failed with."""
    return {
        **watch.generated(),
        **{f"the start of a {prefix} username": f"{prefix}-" for prefix, _ in ACCOUNTS},
        "the failed creation's error type": error_type,
    }


def assert_error_written(written, error_type):
    """Assert `written` holds a traceback and the line that ends one, naming an
    exception of `error_type`, by its name or its dotted path (PLT-1.4)."""
    assert TRACEBACK in written, "No traceback was written."
    exception_line = rf"^(?:[\w.]+\.)?{error_type}(?::|$)"
    assert re.search(exception_line, written, re.MULTILINE), (
        f"No line written names the {error_type} raised."
    )


@pytest.mark.ac("ACC-2.4")
def test_demo_database_down_returns_500_creates_nothing(
    make_account, browser, database_outage
):
    make_account("alice", PASSWORD, REQUESTER)
    before = stored_state()
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with watching() as watch, database_outage():
        response = press_create(browser, page)
    assert_server_error(response, not_shown(watch))
    assert_nothing_created(before)


@pytest.mark.ac("ACC-2.4")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_database_fails_partway_returns_500_creates_nothing(
    make_account, browser, settings, database_fails_partway, debug
):
    settings.DEBUG = debug
    make_account("alice", PASSWORD, REQUESTER)
    before = stored_state()
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with database_fails_partway, watching() as watch:
        response = press_create(browser, page)
    assert watch.errors, "The database reported no error."
    if not debug:
        hidden = not_shown(watch, database_fails_partway.error_type)
        assert_server_error(response, hidden)
    assert_nothing_created(before)


@pytest.mark.ac("ACC-2.4", "ACC-2.9")
@pytest.mark.parametrize(("model", "every", "kind", "debug"), LAST_SAMPLE_FAILURES)
def test_demo_database_fails_on_last_sample_returns_500_creates_nothing(
    make_account, browser, settings, failing_rows, model, every, kind, debug
):
    settings.DEBUG = debug
    alice = make_account("alice", PASSWORD, SUPPORT_OFFICER)
    # An existing workspace's article and ticket, which must not change.
    workspace = alice.workspace
    Article.objects.create(workspace=workspace, title="Guide", body="Steps")
    Ticket.objects.create(workspace=workspace, title="Printer", description="Jams")
    before = stored_state()
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with failing_rows(kind, model, every) as failure, watching() as watch:
        response = press_create(browser, page)
    assert watch.errors, (
        f"The database reported no error, so sample {model._meta.model_name} "
        f"number {every} was never written."
    )
    if not debug:
        assert_server_error(response, not_shown(watch, failure.error_type))
    # Nothing from the attempt remains: no workspace, account, article or
    # ticket, and the existing ones are as they were.
    assert_nothing_created(before)


@pytest.mark.ac("ACC-2.4")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_interface_error_partway_returns_500_creates_nothing(
    transactional_db, make_account, browser, settings, debug
):
    # Django's InterfaceError is a database Error that is not a DatabaseError.
    settings.DEBUG = debug
    make_account("alice", PASSWORD, REQUESTER)
    before = stored_state()
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with watching() as watch, interface_error_partway():
        response = press_create(browser, page)
    assert any(isinstance(error, InterfaceError) for error in watch.errors), (
        "No InterfaceError was raised."
    )
    if not debug:
        assert_server_error(response, not_shown(watch, "InterfaceError"))
    assert_nothing_created(before)


@pytest.mark.ac("ACC-2.3", "ACC-2.4")
@pytest.mark.parametrize("debug", DEBUG_MODES)
@pytest.mark.parametrize("when", CLASH_TIMES)
def test_demo_all_3_codes_clash_returns_500_draws_no_4th_creates_nothing(
    transactional_db, make_account, browser, settings, codes, when, debug
):
    settings.DEBUG = debug
    draws = codes(*CODES)
    # Each code clashes on a different one of its usernames.
    taken = [usernames_for(code)[number] for number, code in enumerate(CODES[:3])]
    if when == "before":
        for username in taken:
            make_account(username, PASSWORD, role_of(username))
    before = stored_state()
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with watching() as watch:
        if when == "meanwhile":
            watch.take_meanwhile(taken)
        response = press_create(browser, page)
    assert draws.count == MAX_CODES
    if not debug:
        assert_server_error(response, not_shown(watch))
    assert_nothing_created(before, elsewhere=taken)


@pytest.mark.ac("ACC-2.6", "ACC-2.4")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_all_3_codes_clash_log_keeps_type_and_traceback_not_generated_values(
    transactional_db, browser, settings, codes, written_output, debug
):
    settings.DEBUG = debug
    codes(*CODES[:3])
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with watching() as watch:
        # Another creation saves each code's usernames while this one saves
        # its accounts, so the database reports each duplicate username.
        for code in CODES[:3]:
            watch.take_meanwhile(usernames_for(code))
        press_create(browser, page)
    generated = watch.generated()
    duplicates = [error for error in watch.errors if "already exists" in str(error)]
    assert any(found_in(str(error), generated) for error in duplicates), (
        "No database error named a generated username."
    )
    assert_error_written(written_output.standard_error(), "IntegrityError")
    assert found_in(written_output.text(), generated) == []


@pytest.mark.ac("ACC-2.6", "ACC-2.4")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_database_fails_partway_log_keeps_type_and_traceback_not_generated_values(
    browser, settings, database_fails_partway, written_output, debug
):
    settings.DEBUG = debug
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with database_fails_partway, watching() as watch:
        press_create(browser, page)
    generated = watch.generated()
    rows = [error for error in watch.errors if "Failing row contains" in str(error)]
    assert any(found_in(str(error), generated) for error in rows), (
        "No database error held the row being written."
    )
    errors = written_output.standard_error()
    assert_error_written(errors, database_fails_partway.error_type)
    assert found_in(written_output.text(), generated) == []


@pytest.mark.ac("ACC-2.6", "ACC-2.4")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_interface_error_partway_log_keeps_type_and_traceback_not_generated_values(
    transactional_db, browser, settings, written_output, debug
):
    settings.DEBUG = debug
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with watching() as watch, interface_error_partway():
        press_create(browser, page)
    generated = watch.generated()
    failures = [error for error in watch.errors if isinstance(error, InterfaceError)]
    assert failures, "No InterfaceError was raised."
    assert not any(isinstance(error, DatabaseError) for error in failures)
    held = [label for error in failures for label in found_in(str(error), generated)]
    assert any(label.startswith("generated username") for label in held), (
        "No InterfaceError named a generated username."
    )
    assert_error_written(written_output.standard_error(), "InterfaceError")
    assert found_in(written_output.text(), generated) == []


@pytest.mark.ac("ACC-2.6")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_created_writes_no_generated_value_to_stdout_stderr_or_logs(
    db, browser, settings, written_output, debug
):
    settings.DEBUG = debug
    page = get_sign_in_page(browser)
    before = stored_state()
    with watching() as watch:
        response = press_create(browser, page)
    accounts = assert_created(response, before)
    generated = watch.generated(accounts)
    assert watch.hashes, "No password was hashed with Django's configured hasher."
    assert found_in(written_output.text(), generated) == []
