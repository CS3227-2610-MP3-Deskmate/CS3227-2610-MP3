"""ACC-1.2: signing out with the Sign out button, only by POST /sign-out/.

`/sign-out/` lists only POST, so other methods get 405 with an empty body
(TECHNICAL-SPEC "Routes"). ACC-1.4: a sign-out that a database failure
interrupts gets PLT-1.4's 500, sets no cookie and leaves an uncommitted
session signed in.
"""

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import DatabaseError, connection, transaction

from deskmate.tests.pages import Page
from deskmate.tests.signing_in import (
    EVIL_ORIGIN,
    FORM_EXPIRED,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SIGN_OUT,
    VISITORS,
    assert_forbidden,
    assert_method_not_allowed,
    assert_redirects,
    assert_server_error,
    assert_signed_in_as,
    assert_signed_out,
    browser_as,
    csrf_token,
    methods_not_listed,
    new_browser,
    send,
    session_cookie,
    sign_in_as,
)

# Every method but POST, GET included, each sent with a valid CSRF token, and
# each with every kind of visitor.
OTHER_METHODS = methods_not_listed("POST")
METHOD_CASES = [
    pytest.param(method, visitor, id=f"{method}-{visitor or 'signed-out'}")
    for method in OTHER_METHODS
    for visitor in VISITORS
]


def press_sign_out(browser, role):
    """Press the Sign out button on `role`'s page in `browser`."""
    return sign_out_form(browser, role).submit(browser, button="Sign out")


def sign_out_form(browser, role):
    """Return the Sign out form on `role`'s page in `browser`."""
    response = browser.get(ROLE_PAGES[role])
    assert response.status_code == 200, f"GET {ROLE_PAGES[role]} failed."
    return Page(response).form_with_button("Sign out")


@pytest.mark.ac("ACC-1.2", "ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_button_signs_out_and_redirects_to_sign_in(make_account, role):
    browser, _ = sign_in_as(make_account, role)
    assert_redirects(press_sign_out(browser, role), SIGN_IN)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.2", "ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_old_session_cookie_sent_again_is_signed_out(make_account, role):
    browser, _ = sign_in_as(make_account, role)
    old_cookie = session_cookie(browser)
    assert old_cookie
    press_sign_out(browser, role)
    replay = new_browser()
    replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
    assert_signed_out(replay)


@pytest.mark.ac("ACC-1.2")
@pytest.mark.django_db
def test_sign_out_signed_out_visitor_redirects_to_sign_in(browser):
    response = send(browser, "POST", SIGN_OUT, csrf_token(browser))
    assert_redirects(response, SIGN_IN)


@pytest.mark.ac("ACC-1.2")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_get_returns_405_empty_stays_signed_in(make_account, role):
    browser, account = sign_in_as(make_account, role)
    assert_method_not_allowed(browser.get(SIGN_OUT))
    assert_signed_in_as(browser, role, account.username)


@pytest.mark.ac("ACC-1.2")
@pytest.mark.parametrize(("method", "visitor"), METHOD_CASES)
def test_sign_out_method_other_than_post_returns_405_empty_signs_no_one_out(
    make_account, method, visitor
):
    browser, account = browser_as(make_account, visitor)
    token = csrf_token(browser, visitor)
    assert_method_not_allowed(send(browser, method, SIGN_OUT, token))
    if account is None:
        assert_signed_out(browser)
    else:
        assert_signed_in_as(browser, visitor, account.username)


# ACC-1.4: a sign-out that a database failure interrupts. Each failure point
# is a statement on a table: loading the session, loading its stored account
# and deleting the session.
SESSION_TABLE = f'"{Session._meta.db_table}"'
ACCOUNT_TABLE = f'"{get_user_model()._meta.db_table}"'
FAILURE_POINTS = {
    "session-read": ("SELECT", SESSION_TABLE),
    "account-read": ("SELECT", ACCOUNT_TABLE),
    "session-delete": ("DELETE", SESSION_TABLE),
}
SYNTHETIC_ERROR = "Synthetic private sign-out failure"
HIDDEN = {"the synthetic error": SYNTHETIC_ERROR}


@pytest.fixture
def debug_off(settings):
    """Turn debug off, as ACC-1.4's sign-out failure requires."""
    settings.DEBUG = False
    return settings


def statement_is(sql, verb, table):
    """Return whether `sql` is a `verb` statement that names `table`."""
    return sql.lstrip().upper().startswith(verb) and table in sql


def stored_session(key):
    """Return the stored session with `key` as a dict of its columns, or None."""
    return Session.objects.filter(session_key=key).values().first()


def assert_interrupted_sign_out(response):
    """Assert `response` is PLT-1.4's generic 500, with no redirect or cookie."""
    assert_server_error(response, HIDDEN)
    assert "Location" not in response
    assert not response.cookies, f"The 500 set cookies: {list(response.cookies)}"


def assert_still_signed_in_until_signed_out(browser, role, account, cookie):
    """Assert `browser`, holding `cookie`, is still signed in as `account`, and
    that a new sign-out then signs it out (ACC-1.2, ACC-1.4)."""
    assert session_cookie(browser) == cookie
    assert_signed_in_as(browser, role, account.username)
    assert_redirects(press_sign_out(browser, role), SIGN_IN)
    assert_signed_out(browser)
    replay = new_browser()
    replay.cookies[settings.SESSION_COOKIE_NAME] = cookie
    assert_signed_out(replay)


@pytest.mark.ac("ACC-1.4", "ACC-1.2")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("point", FAILURE_POINTS)
def test_sign_out_failure_point_returns_500_no_cookie_keeps_session(
    make_account, debug_off, role, point
):
    browser, account = sign_in_as(make_account, role)
    form, cookie = sign_out_form(browser, role), session_cookie(browser)
    before = stored_session(cookie)
    assert before is not None
    verb, table = FAILURE_POINTS[point]
    attempts = []

    def fail(execute, sql, params, many, context):
        if statement_is(sql, verb, table):
            attempts.append(sql)
            raise DatabaseError(SYNTHETIC_ERROR)
        return execute(sql, params, many, context)

    browser.raise_request_exception = False
    with connection.execute_wrapper(fail):
        response = form.submit(browser, button="Sign out")
    assert_interrupted_sign_out(response)
    # Nothing retries the failed operation.
    assert len(attempts) == 1, attempts
    assert stored_session(cookie) == before
    assert_still_signed_in_until_signed_out(browser, role, account, cookie)


@pytest.mark.ac("ACC-1.4", "ACC-1.2")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_database_outage_returns_500_no_cookie_keeps_session(
    make_account, database_outage, debug_off, role
):
    browser, account = sign_in_as(make_account, role)
    form, cookie = sign_out_form(browser, role), session_cookie(browser)
    before = stored_session(cookie)
    assert before is not None
    browser.raise_request_exception = False
    with database_outage():
        response = form.submit(browser, button="Sign out")
    assert_interrupted_sign_out(response)
    assert stored_session(cookie) == before
    assert_still_signed_in_until_signed_out(browser, role, account, cookie)


@pytest.mark.ac("ACC-1.4")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_failure_after_committed_delete_leaves_cookie_signed_out(
    make_account, debug_off, role
):
    browser, _ = sign_in_as(make_account, role)
    form, cookie = sign_out_form(browser, role), session_cookie(browser)
    deletes = []

    def committed_then_failed():
        raise DatabaseError(SYNTHETIC_ERROR)

    def fail_after_delete(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if not deletes and statement_is(sql, "DELETE", SESSION_TABLE):
            deletes.append(sql)
            # The step after the deletion fails once the deletion has
            # committed: at once in autocommit, or after the transaction's
            # commit otherwise.
            alias = context["connection"].alias
            if context["connection"].in_atomic_block:
                transaction.on_commit(committed_then_failed, using=alias)
            else:
                committed_then_failed()
        return result

    browser.raise_request_exception = False
    with connection.execute_wrapper(fail_after_delete):
        form.submit(browser, button="Sign out")
    assert deletes, "The sign-out never deleted the session."
    assert stored_session(cookie) is None
    replay = new_browser()
    replay.cookies[settings.SESSION_COOKIE_NAME] = cookie
    assert_signed_out(replay)


@pytest.mark.ac("ACC-1.4", "ACC-1.2")
@pytest.mark.django_db(transaction=True)
def test_sign_out_without_session_cookie_needs_no_database_redirects(debug_off):
    browser = new_browser()
    token = csrf_token(browser)
    assert session_cookie(browser) is None
    statements = []

    def fail(execute, sql, params, many, context):
        statements.append(sql)
        raise DatabaseError(SYNTHETIC_ERROR)

    browser.raise_request_exception = False
    with connection.execute_wrapper(fail):
        response = send(browser, "POST", SIGN_OUT, token)
    assert_redirects(response, SIGN_IN)
    assert statements == []


@pytest.mark.ac("ACC-1.4", "ACC-1.2")
def test_sign_out_without_session_cookie_during_outage_redirects(
    database_outage, debug_off
):
    browser = new_browser()
    token = csrf_token(browser)
    browser.raise_request_exception = False
    with database_outage():
        response = send(browser, "POST", SIGN_OUT, token)
    assert_redirects(response, SIGN_IN)


@pytest.mark.ac("ACC-1.8", "ACC-1.4")
@pytest.mark.parametrize("refusal", ["missing-token", "other-origin"])
def test_sign_out_csrf_refusal_comes_before_database_failure(
    make_account, database_outage, debug_off, refusal
):
    browser, account = sign_in_as(make_account, REQUESTER)
    token = csrf_token(browser, REQUESTER)
    if refusal == "missing-token":
        token, headers = None, None
    else:
        headers = {"Origin": EVIL_ORIGIN}
    browser.raise_request_exception = False
    with database_outage():
        response = send(browser, "POST", SIGN_OUT, token, headers=headers)
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_in_as(browser, REQUESTER, account.username)


@pytest.mark.ac("ACC-1.2", "ACC-1.4")
def test_sign_out_get_during_outage_returns_405_stays_signed_in(
    make_account, database_outage, debug_off
):
    browser, account = sign_in_as(make_account, REQUESTER)
    browser.raise_request_exception = False
    with database_outage():
        assert_method_not_allowed(browser.get(SIGN_OUT))
    assert_signed_in_as(browser, REQUESTER, account.username)
