"""ACC-2.5: requests to /demo-workspace/ that must create nothing, and fields,
query parameters and request bodies that must not change what a creation
makes.

Every client enforces Django's CSRF checks, as a browser gets them, and debug
is off. Each request that is meant to pass the checks carries
`Origin: https://testserver`, which ACC-1.8 says is accepted.
"""

import json

import pytest
from django.conf import settings

from deskmate.tests.demo_workspaces import (
    DEMO_WORKSPACE,
    assert_created,
    assert_nothing_created,
    press_create,
    stored_state,
)
from deskmate.tests.pages import ORIGIN
from deskmate.tests.signing_in import (
    EVIL_ORIGIN,
    FORM_EXPIRED,
    PASSWORD,
    REJECTED_ORIGINS,
    REQUESTER,
    ROLES,
    SUPPORT_OFFICER,
    TOKEN_FAULTS,
    UNSAFE_METHODS,
    VISITORS,
    assert_forbidden,
    assert_method_not_allowed,
    assert_signed_in_as,
    assert_signed_out,
    browser_as,
    csrf_token,
    get_sign_in_page,
    methods_not_listed,
    new_browser,
    send,
    token_fault_changes,
)

pytestmark = pytest.mark.usefixtures("fast_hashing")

VISITOR_IDS = ["signed-out", *ROLES]
# Methods that /demo-workspace/ does not list (TECHNICAL-SPEC "Routes").
OTHER_METHODS = methods_not_listed("POST")
# Requests with a valid token from another site, each of which another rule
# would answer if the Origin check did not come first: the signed-in
# redirect of ACC-2.7, and the 405 of a method the route does not list.
OTHER_SITE_CASES = [
    pytest.param("POST", REQUESTER, None, id="post-requester"),
    pytest.param("POST", SUPPORT_OFFICER, None, id="post-support-officer"),
    pytest.param("POST", None, "https", id="post-signed-out-forwarded-https"),
    pytest.param("PUT", None, None, id="put-signed-out"),
    pytest.param("PATCH", REQUESTER, None, id="patch-requester"),
]
# Fields a request might use to choose what is created (ACC-2.5), each sent
# alone, alternately in the form and in the query, then all in each place.
EXTRA_FIELDS = ["username", "password", "role", "workspace", "count"]
EXTRA_CASES = [
    *(
        pytest.param((name,), place, id=f"{name}-in-{place}")
        for name, place in zip(
            EXTRA_FIELDS, ["form", "query", "form", "query", "form"], strict=True
        )
    ),
    pytest.param(tuple(EXTRA_FIELDS), "form", id="all-in-form"),
    pytest.param(tuple(EXTRA_FIELDS), "query", id="all-in-query"),
]
# Bodies other than a form's that a valid POST may have, each sent with the
# token in Django's CSRF header instead of a form field.
BODY_FORMATS = ["json", "multipart"]


def assert_visitor_unchanged(browser, visitor, account):
    """Assert `browser` is still signed out, or still signed in as `account`."""
    if account is None:
        assert_signed_out(browser)
    else:
        assert_signed_in_as(browser, visitor, account.username)


@pytest.mark.ac("ACC-2.5", "ACC-1.8")
@pytest.mark.parametrize("visitor", VISITORS, ids=VISITOR_IDS)
@pytest.mark.parametrize("method", UNSAFE_METHODS)
def test_demo_request_without_token_returns_403_creates_nothing(
    make_account, method, visitor
):
    browser, account = browser_as(make_account, visitor)
    # Loading a form gives the browser a CSRF cookie, so only the token is missing.
    csrf_token(browser, visitor)
    before = stored_state()
    assert_forbidden(send(browser, method, DEMO_WORKSPACE), FORM_EXPIRED)
    assert_nothing_created(before)
    assert_visitor_unchanged(browser, visitor, account)


@pytest.mark.ac("ACC-2.5", "ACC-1.8")
@pytest.mark.parametrize("fault", TOKEN_FAULTS)
def test_demo_form_without_valid_token_returns_403_creates_nothing(db, browser, fault):
    before = stored_state()
    if fault == "no-csrf-cookie":
        response = press_create(browser, get_sign_in_page(new_browser()))
    else:
        response = press_create(browser, changes=token_fault_changes(fault))
    assert_forbidden(response, FORM_EXPIRED)
    assert_nothing_created(before)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-2.5", "ACC-1.8")
@pytest.mark.parametrize("origin", REJECTED_ORIGINS)
def test_demo_form_rejected_origin_returns_403_creates_nothing(db, browser, origin):
    assert settings.DEBUG is False
    before = stored_state()
    response = press_create(browser, headers={"Origin": origin})
    assert_forbidden(response, FORM_EXPIRED)
    assert_nothing_created(before)


@pytest.mark.ac("ACC-2.5", "ACC-1.8")
@pytest.mark.parametrize(("method", "visitor", "forwarded"), OTHER_SITE_CASES)
def test_demo_other_site_origin_with_valid_token_returns_403_before_other_rules(
    make_account, method, visitor, forwarded
):
    assert settings.DEBUG is False
    browser, account = browser_as(make_account, visitor)
    token = csrf_token(browser, visitor)
    headers = {"Origin": EVIL_ORIGIN}
    if forwarded is not None:
        headers["X-Forwarded-Proto"] = forwarded
    before = stored_state()
    response = send(
        browser,
        method,
        DEMO_WORKSPACE,
        token,
        headers=headers,
        secure=forwarded is not None,
    )
    assert_forbidden(response, FORM_EXPIRED)
    assert_nothing_created(before)
    assert_visitor_unchanged(browser, visitor, account)


@pytest.mark.ac("ACC-2.5")
@pytest.mark.parametrize("visitor", VISITORS, ids=VISITOR_IDS)
@pytest.mark.parametrize("method", OTHER_METHODS)
def test_demo_method_other_than_post_returns_405_empty_creates_nothing(
    make_account, method, visitor
):
    browser, account = browser_as(make_account, visitor)
    token = csrf_token(browser, visitor)
    before = stored_state()
    assert_method_not_allowed(send(browser, method, DEMO_WORKSPACE, token))
    assert_nothing_created(before)
    assert_visitor_unchanged(browser, visitor, account)


@pytest.mark.ac("ACC-2.5")
@pytest.mark.parametrize(("names", "place"), EXTRA_CASES)
def test_demo_extra_fields_or_query_parameters_create_the_same(
    make_account, browser, names, place
):
    alice = make_account("alice", PASSWORD, REQUESTER)
    values = {
        "username": alice.username,
        "password": PASSWORD,
        "role": SUPPORT_OFFICER,
        "workspace": str(alice.workspace_id),
        "count": "1000",
    }
    extra = {name: values[name] for name in names}
    page = get_sign_in_page(browser)
    before = stored_state()
    if place == "form":
        response = press_create(browser, page, changes=extra)
    else:
        response = press_create(browser, page, query=extra)
    # assert_created checks the new workspace holds only the three accounts
    # of ACC-2.1, with their roles, and that Alice and her workspace are as
    # they were.
    accounts = assert_created(response, before)
    assert alice.username not in [account.username for account in accounts]
    assert PASSWORD not in [account.password for account in accounts]


@pytest.mark.ac("ACC-2.5")
@pytest.mark.parametrize("body_format", BODY_FORMATS)
def test_demo_json_or_multipart_body_with_token_header_creates_the_same(
    make_account, browser, body_format
):
    alice = make_account("alice", PASSWORD, REQUESTER)
    fields = {
        "username": alice.username,
        "role": SUPPORT_OFFICER,
        "workspace": str(alice.workspace_id),
    }
    headers = {"Origin": ORIGIN, "X-CSRFToken": csrf_token(browser)}
    before = stored_state()
    if body_format == "json":
        response = browser.post(
            DEMO_WORKSPACE,
            json.dumps(fields),
            content_type="application/json",
            headers=headers,
        )
    else:
        # The test client sends a mapping as multipart/form-data by default.
        response = browser.post(DEMO_WORKSPACE, fields, headers=headers)
    # assert_created checks the new workspace holds only the three accounts
    # of ACC-2.1, with their roles, and that Alice and her workspace are as
    # they were.
    accounts = assert_created(response, before)
    assert alice.username not in [account.username for account in accounts]
