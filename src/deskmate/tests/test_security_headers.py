"""ACC-1.8: the headers on every response from the sign-in and role pages.

Each case makes one kind of response, checks it got the status it was meant
to, then checks the header, because ACC-1.8 covers every response from these
paths, not only the pages served with 200.
"""

import pytest

from deskmate.tests.accounts import (
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SUPPORT_OFFICER,
    WRONG_PASSWORD,
    csrf_token,
    get_sign_in_page,
    new_browser,
    other_role,
    send,
    sign_in,
    sign_in_as,
)
from deskmate.tests.pages import CSRF_FIELD

ACCOUNT = "alice"

# (case, status): responses from /sign-in/.
SIGN_IN_CASES = [
    ("page", 200),
    ("failed", 200),
    ("succeeded", 302),
    ("signed-in", 302),
    ("without-token", 403),
]
# (case, status): responses from a role's page.
ROLE_PAGE_CASES = [
    ("own-role", 200),
    ("signed-out", 302),
    ("other-role", 403),
    ("method-not-allowed", 405),
    ("without-token", 403),
]
ROLE_PAGE_PARAMS = [
    pytest.param(role, case, status, id=f"{role}-{case}")
    for role in ROLES
    for case, status in ROLE_PAGE_CASES
]


def sign_in_response(make_account, case):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    browser = new_browser()
    if case == "page":
        return browser.get(SIGN_IN)
    if case == "failed":
        return sign_in(browser, ACCOUNT, WRONG_PASSWORD)
    if case == "succeeded":
        return sign_in(browser, ACCOUNT, PASSWORD)
    if case == "signed-in":
        signed_in, _ = sign_in_as(make_account, SUPPORT_OFFICER)
        return signed_in.get(SIGN_IN)
    form = get_sign_in_page(browser).form_with_button("Sign in")
    return form.submit(
        browser,
        {"Username": ACCOUNT, "Password": PASSWORD},
        button="Sign in",
        changes={CSRF_FIELD: None},
    )


def role_page_response(make_account, role, case):
    path = ROLE_PAGES[role]
    if case == "signed-out":
        return new_browser().get(path)
    if case == "other-role":
        browser, _ = sign_in_as(make_account, other_role(role))
        return browser.get(path)
    browser, _ = sign_in_as(make_account, role)
    if case == "own-role":
        return browser.get(path)
    if case == "method-not-allowed":
        return send(browser, "POST", path, csrf_token(browser, role))
    return send(browser, "POST", path)


def cache_directives(response):
    header = response.get("Cache-Control", "")
    return {part.split("=")[0].strip().lower() for part in header.split(",")}


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("case", "status"), SIGN_IN_CASES)
def test_headers_sign_in_response_denies_framing(make_account, case, status):
    response = sign_in_response(make_account, case)
    assert response.status_code == status
    assert response.get("X-Frame-Options") == "DENY"


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("role", "case", "status"), ROLE_PAGE_PARAMS)
def test_headers_role_page_response_denies_framing(make_account, role, case, status):
    response = role_page_response(make_account, role, case)
    assert response.status_code == status
    assert response.get("X-Frame-Options") == "DENY"


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("role", "case", "status"), ROLE_PAGE_PARAMS)
def test_headers_role_page_response_is_not_stored(make_account, role, case, status):
    response = role_page_response(make_account, role, case)
    assert response.status_code == status
    assert "no-store" in cache_directives(response)
