"""ACC-2.4, and the part of ACC-2.6 about standard error and logs: creations
that fail, what they leave behind, and what Deskmate writes about them.

pytest-django turns debug off when the tests start, so debug is turned on for
one test with `settings.DEBUG = True`, which Django reads on every request.
`written_output` captures what Deskmate writes to standard error and its logs.

Tests where a creation fails partway or codes clash use a database that is not
wrapped in a transaction, so what a failed attempt writes would really remain
unless the attempt undoes it. Each checks first that the database's own
errors held a generated value, so the check of what was written can find one.
"""

import pytest

from deskmate.tests.demo_workspaces import (
    ACCOUNTS,
    MAX_CODES,
    assert_created,
    assert_nothing_created,
    found_in,
    press_create,
    role_of,
    stored_state,
    usernames_for,
    watching,
)
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    assert_server_error,
    get_sign_in_page,
)

DEBUG_MODES = [pytest.param(False, id="debug-off"), pytest.param(True, id="debug-on")]
# Codes, from the 31 characters, for the tests to make Deskmate draw. The
# fourth is never taken, so drawing it would let a creation succeed.
CODES = ("aaaaaa", "bbbbbb", "cccccc", "dddddd")
CLASH_TIMES = ["before", "meanwhile"]
TRACEBACK = "Traceback (most recent call last)"


@pytest.fixture(autouse=True)
def _hash_quickly(fast_hashing):
    """Hash the generated passwords with the tests' fast hasher."""


def not_shown(watch, error_type="IntegrityError"):
    """Return, by description, what a failed creation's 500 page must not show:
    every generated value, the start of any generated username, and the type
    of the database's error."""
    return {
        **watch.generated(),
        **{f"the start of a {prefix} username": f"{prefix}-" for prefix, _ in ACCOUNTS},
        "the database error's type": error_type,
    }


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
    output = written_output.text()
    assert TRACEBACK in output
    assert "IntegrityError" in output
    assert found_in(output, generated) == []


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
    output = written_output.text()
    assert TRACEBACK in output
    assert database_fails_partway.error_type in output
    assert found_in(output, generated) == []


@pytest.mark.ac("ACC-2.6")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_created_writes_no_generated_value_to_stderr_or_logs(
    make_account, browser, settings, written_output, debug
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
