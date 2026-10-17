"""ACC-2.6: a demo workspace's passwords appear only in the response to the POST
that created it, which no browser or cache may store and no page may frame.

What Deskmate writes to standard output, standard error and its logs is
checked in test_demo_failures.py.
"""

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, identify_hasher

from deskmate.tests.demo_workspaces import (
    CREATE,
    DEBUG_MODES,
    DEMO_WORKSPACE,
    MAX_CODES,
    assert_created,
    cookies_holding,
    found_in,
    press_create,
    records_holding,
    role_of,
    sessions_holding,
    stored_state,
    usernames_for,
)
from deskmate.tests.helpers import cache_directives
from deskmate.tests.pages import CSRF_FIELD
from deskmate.tests.signing_in import (
    EVIL_ORIGIN,
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    SIGN_IN,
    SIGN_OUT,
    assert_redirects,
    csrf_token,
    get_sign_in_page,
    new_browser,
    send,
    sign_in,
    sign_in_as,
)

pytestmark = pytest.mark.usefixtures("fast_hashing")

# Every route, each requested by GET afterwards (TECHNICAL-SPEC "Routes").
ROUTES = ["/", "/health/", SIGN_IN, SIGN_OUT, DEMO_WORKSPACE, *ROLE_PAGES.values()]
# (case, status): responses from /demo-workspace/.
RESPONSE_CASES = [
    ("created", 200),
    ("signed-in", 302),
    ("without-token", 403),
    ("other-site-origin", 403),
    ("get", 405),
    ("head", 405),
    ("options", 405),
]
# Codes, from the 31 characters, for the tests to make Deskmate draw.
CODES = ("aaaaaa", "bbbbbb", "cccccc")


def shown_in(response, values):
    """Return the description of each of `values` that `response` holds in its
    body, headers or cookies."""
    sent = [
        response.content.decode("utf-8", "replace"),
        repr(dict(response.headers)),
        response.cookies.output(),
    ]
    return found_in("\n".join(sent), values)


def assert_not_stored_and_denies_framing(response):
    """Assert `response` carries `Cache-Control: no-store` and
    `X-Frame-Options: DENY`."""
    assert "no-store" in cache_directives(response)
    assert response.get("X-Frame-Options") == "DENY"


def demo_response(make_account, case):
    """Return a response from /demo-workspace/ of the kind `case` names."""
    browser = new_browser()
    if case == "created":
        return press_create(browser)
    if case == "signed-in":
        signed_in, _ = sign_in_as(make_account, REQUESTER)
        return send(signed_in, "POST", DEMO_WORKSPACE, csrf_token(signed_in, REQUESTER))
    if case == "without-token":
        return press_create(browser, changes={CSRF_FIELD: None})
    if case == "other-site-origin":
        return press_create(browser, headers={"Origin": EVIL_ORIGIN})
    return send(browser, case.upper(), DEMO_WORKSPACE, csrf_token(browser))


@pytest.mark.ac("ACC-2.6")
def test_demo_passwords_stored_only_as_salted_hashes(db, browser):
    before = stored_state()
    accounts = assert_created(press_create(browser), before)
    for account in accounts:
        stored = get_user_model().objects.get(username=account.username).password
        assert account.password not in stored
        # Raises ValueError unless it is a hash by a configured Django hasher.
        hasher = identify_hasher(stored)
        assert hasher.decode(stored)["salt"], "The hash has no salt."
        assert check_password(account.password, stored)


@pytest.mark.ac("ACC-2.6")
def test_demo_passwords_in_no_session_cookie_or_other_record(make_account, browser):
    make_account("alice", PASSWORD, REQUESTER)
    before = stored_state()
    response = press_create(browser)
    accounts = assert_created(response, before)
    browsers = [browser]
    for account in accounts:
        signed_in = new_browser()
        response_to_sign_in = sign_in(signed_in, account.username, account.password)
        assert_redirects(response_to_sign_in, ROLE_PAGES[account.role])
        browsers.append(signed_in)
    passwords = [account.password for account in accounts]
    assert records_holding(passwords) == []
    assert sessions_holding(passwords) == []
    jars = [response.cookies, *(each.cookies for each in browsers)]
    assert cookies_holding(passwords, *jars) == []


@pytest.mark.ac("ACC-2.6")
def test_demo_passwords_shown_by_no_route_afterwards(db, browser):
    before = stored_state()
    accounts = assert_created(press_create(browser), before)
    passwords = {f"the password of {each.username}": each.password for each in accounts}
    responses = {f"GET {path} signed out": browser.get(path) for path in ROUTES}
    for account in accounts:
        signed_in = new_browser()
        response = sign_in(signed_in, account.username, account.password)
        responses[f"signing in as {account.username}"] = response
        for path in ROUTES:
            responses[f"GET {path} as {account.username}"] = signed_in.get(path)
    shown = {name: shown_in(each, passwords) for name, each in responses.items()}
    assert {name: found for name, found in shown.items() if found} == {}


@pytest.mark.ac("ACC-2.6")
def test_demo_same_submission_sent_again_creates_another_workspace_shows_only_it(
    db, browser
):
    # A reload that resends the form sends the same data, CSRF token included.
    form = get_sign_in_page(browser).form_with_button(CREATE)
    before = stored_state()
    first = assert_created(form.submit(browser, button=CREATE), before)
    between = stored_state()
    again = form.submit(browser, button=CREATE)
    second = assert_created(again, between)
    earlier = {}
    for account in first:
        earlier[f"the first username {account.username}"] = account.username
        earlier[f"the first password of {account.username}"] = account.password
    assert shown_in(again, earlier) == []
    assert {account.username for account in first}.isdisjoint(
        account.username for account in second
    )


@pytest.mark.ac("ACC-2.6")
@pytest.mark.parametrize(("case", "status"), RESPONSE_CASES)
def test_demo_response_is_not_stored_and_denies_framing(make_account, case, status):
    response = demo_response(make_account, case)
    assert response.status_code == status
    assert_not_stored_and_denies_framing(response)


@pytest.mark.ac("ACC-2.6")
def test_demo_database_down_server_error_is_not_stored_and_denies_framing(
    transactional_db, browser, database_outage
):
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with database_outage():
        response = press_create(browser, page)
    assert response.status_code == 500
    assert_not_stored_and_denies_framing(response)


@pytest.mark.ac("ACC-2.6")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_all_3_codes_clash_server_error_is_not_stored_and_denies_framing(
    make_account, browser, settings, codes, debug
):
    settings.DEBUG = debug
    draws = codes(*CODES)
    for code in CODES:
        username = usernames_for(code)[0]
        make_account(username, PASSWORD, role_of(username))
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    response = press_create(browser, page)
    assert draws.count == MAX_CODES
    assert response.status_code == 500
    assert_not_stored_and_denies_framing(response)


@pytest.mark.ac("ACC-2.6")
@pytest.mark.parametrize("debug", DEBUG_MODES)
def test_demo_database_fails_partway_server_error_is_not_stored_and_denies_framing(
    browser, settings, database_fails_partway, debug
):
    settings.DEBUG = debug
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with database_fails_partway:
        response = press_create(browser, page)
    assert response.status_code == 500
    assert_not_stored_and_denies_framing(response)
