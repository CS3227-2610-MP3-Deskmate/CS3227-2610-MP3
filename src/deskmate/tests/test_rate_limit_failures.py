"""ACC-3.7: attempts whose check against the limits cannot finish fail closed.

The database either does not answer, fails at one of the statements that
check and count an attempt, or keeps an attempt waiting while another attempt
of its kind is being checked. Each attempt sends an account's username and
password, so it would sign in, or check or hash a password, if it got past
the limits. The statements that check and count an attempt are found as those
an allowed attempt runs before it first reads or writes an account or a
workspace (`check_statements`).
"""

import threading
import time

import pytest
from django.db import connection

from deskmate.tests.demo_workspaces import (
    DEBUG_MODES,
    assert_created,
    assert_nothing_created,
    signed_in_account_ids,
    stored_state,
)
from deskmate.tests.hashing import recording_hashes
from deskmate.tests.rate_limits import (
    CREATION,
    KINDS,
    MAX_WAIT_SECONDS,
    SIGN_IN_ATTEMPT,
    FailingStatement,
    HeldCheck,
    Visitor,
    assert_allowed,
    check_statements,
    numbered_source,
)
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    assert_redirects,
    assert_server_error,
    assert_signed_in_as,
    assert_signed_out,
)

pytestmark = pytest.mark.usefixtures("fast_hashing")

ACCOUNT = "alice"
# How long another attempt keeps its check going at most: far more than an
# attempt may wait, so the waiting attempt answers first, and less.
LONGER = 3 * MAX_WAIT_SECONDS
SHORTER = MAX_WAIT_SECONDS - 1


def this_threads(hashed):
    """Return the passwords in `hashed`, a recording_hashes list, that this
    thread checked or hashed."""
    name = threading.current_thread().name
    return [entry.password for entry in hashed if entry.thread == name]


def assert_failed_closed(response, visitor, before, hashed, debug=False):
    """Assert the attempt that got `response` from `visitor` failed as ACC-3.7
    says: a 500 with debug off, no password checked or hashed in this thread,
    no one signed in and nothing created since `before`, a stored_state."""
    if debug:
        assert response.status_code == 500, response.status_code
    else:
        assert_server_error(response, {"the account's password": PASSWORD})
    assert this_threads(hashed) == [], "A password was checked or hashed."
    assert_signed_out(visitor.browser)
    assert signed_in_account_ids() == set()
    assert_nothing_created(before)


@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_database_down_attempt_returns_500_checks_and_hashes_nothing(
    make_account, database_outage, kind
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    before = stored_state()
    visitor = Visitor()
    visitor.browser.raise_request_exception = False
    with recording_hashes() as hashed, database_outage():
        response = visitor.attempt(kind, ACCOUNT, PASSWORD)
    assert_failed_closed(response, visitor, before, hashed)


@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("debug", DEBUG_MODES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_database_fails_while_checking_or_counting_returns_500(
    transactional_db, make_account, settings, kind, debug
):
    settings.DEBUG = debug
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    statements = check_statements(kind, Visitor(numbered_source(200)))
    for number, sql in enumerate(statements):
        before = stored_state()
        visitor = Visitor(numbered_source(number + 1))
        visitor.browser.raise_request_exception = False
        failing = FailingStatement(number)
        with recording_hashes() as hashed, connection.execute_wrapper(failing):
            response = visitor.attempt(kind, ACCOUNT, PASSWORD)
        assert failing.failed == sql, f"Statement {number + 1} was not the same."
        assert_failed_closed(response, visitor, before, hashed, debug)


@pytest.mark.ac("ACC-3.7")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_attempt_waiting_over_5_seconds_to_be_checked_returns_500(
    transactional_db, make_account, kind
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    statements = check_statements(kind, Visitor(numbered_source(200)))
    held = HeldCheck(kind, statements[-1], LONGER, numbered_source(201))
    before = stored_state()
    visitor = Visitor(numbered_source(202))
    visitor.browser.raise_request_exception = False
    with recording_hashes() as hashed, held.holding():
        started = time.monotonic()
        response = visitor.attempt(kind, ACCOUNT, PASSWORD)
        waited = time.monotonic() - started
    # The other attempt was still being checked when this one answered.
    assert response.status_code == 500, (
        f"After waiting {waited:.1f}s, the attempt got {response.status_code}."
    )
    assert_server_error(response, {"the account's password": PASSWORD})
    assert this_threads(hashed) == [], "A password was checked or hashed."
    assert_signed_out(visitor.browser)
    if kind == CREATION:
        # The only workspace created is the other attempt's.
        assert_created(held.response, before)
    else:
        assert_allowed(held.response, kind)
        assert signed_in_account_ids() == set()


@pytest.mark.ac("ACC-3.7", "ACC-3.6")
def test_limit_attempt_waiting_under_5_seconds_is_checked_after_the_other(
    transactional_db, make_account
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    kind = SIGN_IN_ATTEMPT
    statements = check_statements(kind, Visitor(numbered_source(200)))
    held = HeldCheck(kind, statements[-1], SHORTER, numbered_source(201))
    visitor = Visitor(numbered_source(202))
    with held.holding():
        started = time.monotonic()
        response = visitor.attempt(kind, ACCOUNT, PASSWORD)
        waited = time.monotonic() - started
    assert waited > SHORTER - 0.5, (
        f"The attempt was checked after {waited:.1f}s, while the other attempt "
        "of its kind was still being checked."
    )
    assert_redirects(response, ROLE_PAGES[REQUESTER])
    assert_signed_in_as(visitor.browser, REQUESTER, ACCOUNT)
    assert_allowed(held.response, kind)
