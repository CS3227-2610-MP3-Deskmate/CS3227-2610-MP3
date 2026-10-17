"""ACC-3.4: requests that are not attempts, which the limits neither refuse
nor count, and attempts that are counted however they end.

The rules apply in the order TECHNICAL-SPEC "Routes" gives: the 403 of
ACC-1.8, then the 405 of a method a route does not list, then a signed-in
user's redirect, then the limits, then the route's own rules. Every request
here comes from 127.0.0.1 with no X-Forwarded-For header, as every request in
the other tests does, so all of them are in one address group. The clock is
stopped, so every attempt is counted at one moment.
"""

import pytest

from deskmate.tests.demo_workspaces import (
    DEMO_WORKSPACE,
    assert_demo_form,
    assert_nothing_created,
    role_of,
    stored_state,
    usernames_for,
)
from deskmate.tests.hashing import recording_hashes
from deskmate.tests.rate_limits import (
    CREATION,
    KINDS,
    PATHS,
    PER_GROUP,
    SIGN_IN_ATTEMPT,
    Visitor,
    assert_allowed,
    assert_refused,
    make_attempts,
)
from deskmate.tests.signing_in import (
    EVIL_ORIGIN,
    FORM_EXPIRED,
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SIGN_OUT,
    TOKEN_FAULTS,
    WRONG_PASSWORD,
    assert_forbidden,
    assert_method_not_allowed,
    assert_redirects,
    assert_sign_in_page,
    assert_signed_in_as,
    assert_signed_out,
    csrf_token,
    methods_not_listed,
    new_browser,
    send,
    sign_in_as,
)

pytestmark = pytest.mark.usefixtures("fast_hashing", "clock")

# The methods each route does not list (TECHNICAL-SPEC "Routes").
UNLISTED = {
    SIGN_IN_ATTEMPT: methods_not_listed("GET", "POST"),
    CREATION: methods_not_listed("POST"),
}
UNLISTED_CASES = [
    pytest.param(kind, method, id=f"{kind}-{method}")
    for kind in KINDS
    for method in UNLISTED[kind]
]
# Ways ACC-1.8 refuses a POST: each of TOKEN_FAULTS, or an Origin from another
# site with a valid token.
CSRF_FAULTS = [*TOKEN_FAULTS, "other-site-origin"]
# Sign-in submissions, each of which is counted (ACC-3.4): (username,
# password, whether the form is sent without its Username and Password
# fields, as a script may send it).
SUBMISSIONS = [
    pytest.param("alice", PASSWORD, False, id="signs-in"),
    pytest.param("alice", WRONG_PASSWORD, False, id="wrong-password"),
    pytest.param("nobody", WRONG_PASSWORD, False, id="unknown-username"),
    pytest.param("", WRONG_PASSWORD, False, id="empty-username"),
    pytest.param("a" * 151, WRONG_PASSWORD, False, id="too-long-username"),
    pytest.param("alice", "", False, id="empty-password"),
    pytest.param("", "", False, id="both-empty"),
    pytest.param("alice", PASSWORD, True, id="fields-left-out"),
]
# Codes, from the 31 characters, for the tests to make Deskmate draw.
CODES = ("aaaaaa", "bbbbbb", "cccccc")


def reach(kind, already=0):
    """Make attempts of `kind` from 127.0.0.1 until its limit for that address
    group is reached, `already` having been counted, and check it is."""
    make_attempts(kind, PER_GROUP[kind] - already)
    assert_refused(Visitor().attempt(kind), kind)


def nearly_reach(kind, already=0):
    """Make attempts of `kind` from 127.0.0.1 until one more would reach its
    limit for that address group, `already` having been counted."""
    make_attempts(kind, PER_GROUP[kind] - 1 - already)


def assert_last_allowed_then_refused(kind):
    """Assert one more attempt of `kind` from 127.0.0.1 is allowed, and the
    one after it refused: so nothing but the attempts was counted."""
    visitor = Visitor()
    assert_allowed(visitor.attempt(kind), kind)
    assert_refused(visitor.attempt(kind), kind)


def refused_by_csrf(kind, fault):
    """Send `kind`'s POST from a signed-out browser with `fault`, one of
    CSRF_FAULTS; return the response."""
    path = PATHS[kind]
    browser = new_browser()
    if fault == "missing":
        return send(browser, "POST", path)
    if fault == "empty":
        return send(browser, "POST", path, "")
    if fault == "other-site-origin":
        token = csrf_token(browser)
        return send(browser, "POST", path, token, headers={"Origin": EVIL_ORIGIN})
    token = csrf_token(new_browser())
    if fault == "other-browser":
        csrf_token(browser)
    return send(browser, "POST", path, token)


def posts_while_signed_in(browser, role):
    """Send, from `browser` signed in with `role`, a sign-in submission with
    another account's details and a creation, and check each redirects to the
    role's page and creates nothing."""
    before = stored_state()
    token = csrf_token(browser, role)
    other = {"username": "bob", "password": PASSWORD}
    assert_redirects(
        send(browser, "POST", SIGN_IN, token, data=other), ROLE_PAGES[role]
    )
    assert_redirects(send(browser, "POST", DEMO_WORKSPACE, token), ROLE_PAGES[role])
    assert_nothing_created(before)


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_reached_signed_in_user_redirected_stays_signed_in_signs_out(
    make_account, kind, role
):
    make_account("bob", PASSWORD, REQUESTER)
    browser, account = sign_in_as(make_account, role)
    reach(kind, already=1 if kind == SIGN_IN_ATTEMPT else 0)
    with recording_hashes() as hashed:
        posts_while_signed_in(browser, role)
    assert hashed == [], "A signed-in user's submission had a password checked."
    assert_redirects(browser.get(SIGN_IN), ROLE_PAGES[role])
    assert_signed_in_as(browser, role, account.username)
    token = csrf_token(browser, role)
    assert_redirects(send(browser, "POST", SIGN_OUT, token), SIGN_IN)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_signed_in_users_posts_are_not_counted(make_account, kind):
    make_account("bob", PASSWORD, REQUESTER)
    browser, _ = sign_in_as(make_account, REQUESTER)
    nearly_reach(kind, already=1 if kind == SIGN_IN_ATTEMPT else 0)
    for _ in range(PER_GROUP[kind] + 1):
        posts_while_signed_in(browser, REQUESTER)
    assert_last_allowed_then_refused(kind)


@pytest.mark.ac("ACC-3.4")
def test_limit_reached_get_sign_in_serves_sign_in_page(db):
    for kind in KINDS:
        reach(kind)
    page = assert_sign_in_page(new_browser().get(SIGN_IN))
    assert_demo_form(page)


@pytest.mark.ac("ACC-3.4", "ACC-1.8")
@pytest.mark.parametrize("fault", CSRF_FAULTS)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_reached_request_refused_by_csrf_gets_403(db, kind, fault):
    reach(kind)
    assert_forbidden(refused_by_csrf(kind, fault), FORM_EXPIRED)


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_requests_refused_by_csrf_are_not_counted(db, kind):
    nearly_reach(kind)
    for fault in CSRF_FAULTS:
        assert_forbidden(refused_by_csrf(kind, fault), FORM_EXPIRED)
    assert_last_allowed_then_refused(kind)


@pytest.mark.ac("ACC-3.4", "ACC-1.8")
@pytest.mark.parametrize("method", ["PUT", "DELETE", "PATCH"])
@pytest.mark.parametrize("kind", KINDS)
def test_limit_reached_unlisted_method_without_token_gets_403(db, kind, method):
    reach(kind)
    assert_forbidden(send(new_browser(), method, PATHS[kind]), FORM_EXPIRED)


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize(("kind", "method"), UNLISTED_CASES)
def test_limit_reached_unlisted_method_gets_405(db, kind, method):
    reach(kind)
    browser = new_browser()
    token = csrf_token(browser)
    assert_method_not_allowed(send(browser, method, PATHS[kind], token))


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_unlisted_methods_are_not_counted(db, kind):
    nearly_reach(kind)
    browser = new_browser()
    token = csrf_token(browser)
    for _ in range(2):
        for method in UNLISTED[kind]:
            assert_method_not_allowed(send(browser, method, PATHS[kind], token))
    assert_last_allowed_then_refused(kind)


@pytest.mark.ac("ACC-3.4")
@pytest.mark.parametrize(("username", "password", "left_out"), SUBMISSIONS)
def test_limit_counts_every_allowed_sign_in_attempt_however_it_ends(
    make_account, clock, username, password, left_out
):
    make_account("alice", PASSWORD, REQUESTER)
    signs_in = username == "alice" and password == PASSWORD and not left_out
    visitor = Visitor()
    form = visitor.page.form_with_button("Sign in")
    fields = [form.field(label).name for label in ("Username", "Password")]
    changes = dict.fromkeys(fields) if left_out else None
    for number in range(1, PER_GROUP[SIGN_IN_ATTEMPT] + 1):
        if signs_in:
            visitor = Visitor()
        response = visitor.attempt(SIGN_IN_ATTEMPT, username, password, changes=changes)
        assert_allowed(response, SIGN_IN_ATTEMPT, number)
        assert (response.status_code == 302) == signs_in, response.status_code
    late = Visitor()
    with recording_hashes() as hashed:
        response = late.attempt(SIGN_IN_ATTEMPT, "alice", PASSWORD)
    assert_refused(response, SIGN_IN_ATTEMPT, retry_after=600)
    assert hashed == []
    assert_signed_out(late.browser)


@pytest.mark.ac("ACC-3.4", "ACC-2.4")
def test_limit_counts_creations_that_fail_partway(
    make_account, clock, database_fails_partway
):
    make_account("alice", PASSWORD, REQUESTER)
    visitor = Visitor()
    visitor.browser.raise_request_exception = False
    with database_fails_partway:
        for number in range(1, PER_GROUP[CREATION] + 1):
            response = visitor.attempt(CREATION)
            assert response.status_code == 500, f"Creation {number} did not fail."
    before = stored_state()
    with recording_hashes() as hashed:
        response = visitor.attempt(CREATION)
    assert_refused(response, CREATION, retry_after=600)
    assert hashed == []
    assert_nothing_created(before)


@pytest.mark.ac("ACC-3.4", "ACC-2.3")
def test_limit_counts_creations_whose_3_codes_all_clash(
    transactional_db, make_account, clock, codes
):
    for code in CODES:
        username = usernames_for(code)[0]
        make_account(username, PASSWORD, role_of(username))
    draws = codes(*CODES * PER_GROUP[CREATION])
    visitor = Visitor()
    visitor.browser.raise_request_exception = False
    for number in range(1, PER_GROUP[CREATION] + 1):
        response = visitor.attempt(CREATION)
        assert response.status_code == 500, f"Creation {number} did not fail."
    assert draws.count == len(CODES) * PER_GROUP[CREATION]
    before = stored_state()
    assert_refused(visitor.attempt(CREATION), CREATION, retry_after=600)
    assert draws.count == len(CODES) * PER_GROUP[CREATION], "A code was drawn."
    assert_nothing_created(before)
