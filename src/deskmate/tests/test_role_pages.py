"""ACC-1.2, ACC-1.4 and ACC-1.5: who may open the Requester and Support Officer
pages, and what those pages show."""

from urllib.parse import unquote

import pytest
from django.conf import settings
from django.contrib.auth import get_user_model

from deskmate.tests.signing_in import (
    MARKUP_USERNAMES,
    NOT_FOR_YOUR_ROLE,
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SUPPORT_OFFICER,
    UNKNOWN_SESSION_KEY,
    VISITORS,
    assert_forbidden,
    assert_method_not_allowed,
    assert_redirects,
    assert_role_page,
    assert_server_error,
    browser_as,
    csrf_token,
    other_role,
    send,
    sign_in_as,
)

# Usernames with a non-ASCII letter and every punctuation mark the data model
# allows, written escaped: zoë.r+1-2_x@desk and Ünal.s+3-4_y@desk.
DISPLAYED_USERNAMES = {
    REQUESTER: "zo\u00eb.r+1-2_x@desk",
    SUPPORT_OFFICER: "\u00dcnal.s+3-4_y@desk",
}

# Every method but GET, with each kind of visitor, alternating the page so each
# page meets each method and each visitor (ACC-1.4).
OTHER_METHODS = ["POST", "PUT", "PATCH", "DELETE", "HEAD", "OPTIONS", "TRACE"]
METHOD_CASES = [
    pytest.param(
        method,
        visitor,
        list(ROLE_PAGES.values())[(i + j) % 2],
        id=f"{method}-{visitor or 'signed-out'}",
    )
    for i, method in enumerate(OTHER_METHODS)
    for j, visitor in enumerate(VISITORS)
]

# What a client might send to claim a role it does not have (ACC-1.5).
CLAIMS = ["query", "role-header", "remote-user-header", "role-cookie"]


@pytest.mark.ac("ACC-1.2")
@pytest.mark.parametrize("role", ROLES)
def test_role_page_signed_in_shows_username_and_sign_out(make_account, role):
    username = DISPLAYED_USERNAMES[role]
    browser, _ = sign_in_as(make_account, role, username)
    assert_role_page(browser.get(ROLE_PAGES[role]), role, username)


@pytest.mark.ac("ACC-1.2")
@pytest.mark.parametrize("role", ROLES)
@pytest.mark.parametrize("escaped", MARKUP_USERNAMES)
def test_role_page_markup_username_shown_as_text(make_account, role, escaped):
    # make_account uses create_user, which runs no validators, so the account
    # can have a username that the data model's rules would refuse.
    username = unquote(escaped)
    browser, _ = sign_in_as(make_account, role, username)
    response = browser.get(ROLE_PAGES[role])
    assert_role_page(response, role, username)
    assert username not in response.content.decode("utf-8")


@pytest.mark.ac("ACC-1.4")
@pytest.mark.django_db
@pytest.mark.parametrize("path", ROLE_PAGES.values())
def test_role_page_signed_out_redirects_to_sign_in(browser, path):
    assert_redirects(browser.get(path), SIGN_IN)


@pytest.mark.ac("ACC-1.4")
@pytest.mark.django_db
@pytest.mark.parametrize("path", ROLE_PAGES.values())
def test_role_page_unknown_session_cookie_redirects_to_sign_in(browser, path):
    browser.cookies[settings.SESSION_COOKIE_NAME] = UNKNOWN_SESSION_KEY
    assert_redirects(browser.get(path), SIGN_IN)


@pytest.mark.ac("ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_role_page_account_deleted_redirects_to_sign_in(make_account, role):
    browser, account = sign_in_as(make_account, role)
    get_user_model().objects.filter(pk=account.pk).delete()
    assert_redirects(browser.get(ROLE_PAGES[role]), SIGN_IN)


@pytest.mark.ac("ACC-1.4")
@pytest.mark.parametrize(("method", "visitor", "path"), METHOD_CASES)
def test_role_page_method_other_than_get_returns_405_empty(
    make_account, method, visitor, path
):
    browser, _ = browser_as(make_account, visitor)
    token = csrf_token(browser, visitor)
    assert_method_not_allowed(send(browser, method, path, token))


@pytest.mark.ac("ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_role_page_database_down_returns_500(make_account, database_outage, role):
    browser, _ = sign_in_as(make_account, role)
    browser.raise_request_exception = False
    with database_outage():
        response = browser.get(ROLE_PAGES[role])
    assert_server_error(response)


@pytest.mark.ac("ACC-1.5")
@pytest.mark.parametrize("role", ROLES)
def test_role_page_other_role_returns_403(make_account, role):
    browser, _ = sign_in_as(make_account, role)
    response = browser.get(ROLE_PAGES[other_role(role)])
    assert_forbidden(response, NOT_FOR_YOUR_ROLE)


@pytest.mark.ac("ACC-1.5", "ACC-1.7")
@pytest.mark.parametrize("role", ROLES)
def test_role_page_stored_role_changed_applies_from_next_request(make_account, role):
    browser, account = sign_in_as(make_account, role)
    assert browser.get(ROLE_PAGES[role]).status_code == 200
    new_role = other_role(role)
    get_user_model().objects.filter(pk=account.pk).update(role=new_role)
    assert_forbidden(browser.get(ROLE_PAGES[role]), NOT_FOR_YOUR_ROLE)
    assert_role_page(browser.get(ROLE_PAGES[new_role]), new_role, account.username)
    assert_redirects(browser.get(SIGN_IN), ROLE_PAGES[new_role])


@pytest.mark.ac("ACC-1.5")
@pytest.mark.parametrize("claim", CLAIMS)
@pytest.mark.parametrize("visitor", VISITORS, ids=["signed-out", *ROLES])
def test_role_page_client_claims_do_not_change_access(make_account, claim, visitor):
    claimed_role = REQUESTER if visitor is None else other_role(visitor)
    owner = make_account(f"{claimed_role}-owner", PASSWORD, claimed_role)
    browser, _ = browser_as(make_account, visitor)
    request = {}
    if claim == "query":
        request["query_params"] = {"role": claimed_role, "username": owner.username}
    elif claim == "role-header":
        request["headers"] = {"X-Role": claimed_role}
    elif claim == "remote-user-header":
        request["headers"] = {"Remote-User": owner.username}
    else:
        browser.cookies["role"] = claimed_role
    response = browser.get(ROLE_PAGES[claimed_role], **request)
    if visitor is None:
        assert_redirects(response, SIGN_IN)
    else:
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
