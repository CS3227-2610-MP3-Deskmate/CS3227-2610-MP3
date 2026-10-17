"""ACC-1.8: requests that need a CSRF token, and the Origin they may come from.

Every client here enforces Django's CSRF checks, as a browser gets them, and
debug is off. Each request that is meant to pass the checks carries
`Origin: https://testserver`, which ACC-1.8 says is accepted. The tests leave
alone what the spec leaves open: requests without an Origin, origins with a
port matching the Host header, `Origin: http://testserver`, and which origins
a `DJANGO_ALLOWED_HOSTS` name with `*` or a leading dot allows.
"""

import pytest

from deskmate.tests.pages import CSRF_FIELD, ORIGIN, Page
from deskmate.tests.signing_in import (
    FORM_EXPIRED,
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SIGN_OUT,
    SUPPORT_OFFICER,
    VISITORS,
    WRONG_PASSWORD,
    assert_forbidden,
    assert_redirects,
    assert_signed_in_as,
    assert_signed_out,
    browser_as,
    csrf_token,
    get_sign_in_page,
    new_browser,
    other_role,
    send,
    sign_in_as,
    submit_sign_in,
)

ACCOUNT = "alice"
EVIL_ORIGIN = "https://evil.example"
ROUTES = ["/", "/health/", SIGN_IN, SIGN_OUT, *ROLE_PAGES.values()]
# Methods that need a token: POST sends it in the form, the others in a
# header, and PROPFIND stands for methods that Django does not name.
UNSAFE_METHODS = ["POST", "PUT", "PATCH", "DELETE", "PROPFIND"]
# Every route with every method, cycling through visitors so each visitor
# meets each route and each method.
NO_TOKEN_CASES = [
    pytest.param(
        route,
        method,
        VISITORS[(i + j) % 3],
        id=f"{method}-{route}-{VISITORS[(i + j) % 3] or 'signed-out'}",
    )
    for i, route in enumerate(ROUTES)
    for j, method in enumerate(UNSAFE_METHODS)
]
# Ways a submission can lack a valid token: no token, an empty one, another
# browser's, or a token from a page with no CSRF cookie sent alongside it.
TOKEN_FAULTS = ["missing", "empty", "other-browser", "no-csrf-cookie"]
# Origins that are not exactly https:// or http:// and an allowed host.
REJECTED_ORIGINS = [
    pytest.param(EVIL_ORIGIN, id="other-site"),
    pytest.param("null", id="null"),
    pytest.param("https://testserver.evil.example", id="allowed-host-as-prefix"),
    pytest.param("https://testserver:8443", id="port-not-in-host-header"),
    pytest.param("ftp://testserver", id="other-scheme"),
    pytest.param("https://TESTSERVER", id="other-case"),
    pytest.param("https://testserver.", id="trailing-dot"),
    pytest.param("https://testserver/", id="trailing-slash"),
    pytest.param(f"{ORIGIN}, {EVIL_ORIGIN}", id="list-with-other-site"),
]
# How the request reached Deskmate: over HTTP or HTTPS, and with which
# forwarded-scheme header, if any.
TRANSPORTS = [
    pytest.param(secure, forwarded, id=f"{scheme}-forwarded-{forwarded or 'none'}")
    for secure, scheme in ((False, "http"), (True, "https"))
    for forwarded in (None, "http", "https")
]


def forwarded_headers(origin, forwarded):
    headers = {"Origin": origin}
    if forwarded is not None:
        headers["X-Forwarded-Proto"] = forwarded
    return headers


def token_fault_changes(fault):
    if fault == "missing":
        return {CSRF_FIELD: None}
    if fault == "empty":
        return {CSRF_FIELD: ""}
    return {CSRF_FIELD: csrf_token(new_browser())}


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("route", "method", "visitor"), NO_TOKEN_CASES)
def test_csrf_request_without_token_returns_403(make_account, route, method, visitor):
    browser, _ = browser_as(make_account, visitor)
    # Loading a form gives the browser a CSRF cookie, so only the token is missing.
    csrf_token(browser, visitor)
    assert_forbidden(send(browser, method, route), FORM_EXPIRED)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize("fault", TOKEN_FAULTS)
def test_csrf_sign_in_without_valid_token_returns_403_signs_no_one_in(
    make_account, fault
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    browser = new_browser()
    if fault == "no-csrf-cookie":
        page = get_sign_in_page(new_browser())
        response = submit_sign_in(browser, page, ACCOUNT, PASSWORD)
    else:
        page = get_sign_in_page(browser)
        changes = token_fault_changes(fault)
        response = submit_sign_in(browser, page, ACCOUNT, PASSWORD, changes=changes)
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(
    ("fault", "role"),
    [
        pytest.param(fault, ROLES[i % 2], id=fault)
        for i, fault in enumerate(["missing", "empty", "other-browser"])
    ],
)
def test_csrf_sign_out_without_valid_token_returns_403_stays_signed_in(
    make_account, fault, role
):
    browser, account = sign_in_as(make_account, role)
    form = Page(browser.get(ROLE_PAGES[role])).form_with_button("Sign out")
    response = form.submit(
        browser, button="Sign out", changes=token_fault_changes(fault)
    )
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_in_as(browser, role, account.username)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize("role", ROLES)
def test_csrf_signed_in_sign_in_without_token_keeps_account(make_account, role):
    browser, account = sign_in_as(make_account, role)
    other = make_account("other-account", WRONG_PASSWORD, other_role(role))
    form = get_sign_in_page(new_browser()).form_with_button("Sign in")
    response = form.submit(
        browser,
        {"Username": other.username, "Password": WRONG_PASSWORD},
        button="Sign in",
        changes={CSRF_FIELD: None},
    )
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_in_as(browser, role, account.username)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("secure", "forwarded"), TRANSPORTS)
def test_origin_https_allowed_host_sign_in_accepted(
    make_account, browser, secure, forwarded
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(
        browser,
        page,
        ACCOUNT,
        PASSWORD,
        headers=forwarded_headers(ORIGIN, forwarded),
        secure=secure,
    )
    assert_redirects(response, ROLE_PAGES[REQUESTER])
    assert_signed_in_as(browser, REQUESTER, ACCOUNT)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(
    ("secure", "forwarded", "role"),
    [
        pytest.param(False, None, REQUESTER, id="http-forwarded-none"),
        pytest.param(False, "http", SUPPORT_OFFICER, id="http-forwarded-http"),
        pytest.param(True, "https", REQUESTER, id="https-forwarded-https"),
    ],
)
def test_origin_https_allowed_host_sign_out_accepted(
    make_account, secure, forwarded, role
):
    browser, _ = sign_in_as(make_account, role)
    form = Page(browser.get(ROLE_PAGES[role])).form_with_button("Sign out")
    response = form.submit(
        browser,
        button="Sign out",
        headers=forwarded_headers(ORIGIN, forwarded),
        secure=secure,
    )
    assert_redirects(response, SIGN_IN)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize("origin", REJECTED_ORIGINS)
def test_origin_rejected_sign_in_returns_403_signs_no_one_in(
    make_account, browser, origin
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(
        browser, page, ACCOUNT, PASSWORD, headers={"Origin": origin}
    )
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.8")
def test_origin_matching_forwarded_host_sign_in_returns_403_signs_no_one_in(
    make_account, browser
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    headers = {"Origin": EVIL_ORIGIN, "X-Forwarded-Host": "evil.example"}
    response = submit_sign_in(browser, page, ACCOUNT, PASSWORD, headers=headers)
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(("secure", "forwarded"), TRANSPORTS)
def test_origin_other_site_sign_in_returns_403_whatever_forwarded_scheme(
    make_account, browser, secure, forwarded
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(
        browser,
        page,
        ACCOUNT,
        PASSWORD,
        headers=forwarded_headers(EVIL_ORIGIN, forwarded),
        secure=secure,
    )
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize(
    ("secure", "forwarded", "role"),
    [
        pytest.param(False, None, SUPPORT_OFFICER, id="http-forwarded-none"),
        pytest.param(False, "https", REQUESTER, id="http-forwarded-https"),
        pytest.param(True, "https", SUPPORT_OFFICER, id="https-forwarded-https"),
    ],
)
def test_origin_other_site_sign_out_returns_403_stays_signed_in(
    make_account, secure, forwarded, role
):
    browser, account = sign_in_as(make_account, role)
    form = Page(browser.get(ROLE_PAGES[role])).form_with_button("Sign out")
    response = form.submit(
        browser,
        button="Sign out",
        headers=forwarded_headers(EVIL_ORIGIN, forwarded),
        secure=secure,
    )
    assert_forbidden(response, FORM_EXPIRED)
    assert_signed_in_as(browser, role, account.username)


@pytest.mark.ac("ACC-1.8")
@pytest.mark.parametrize("route", ["/", "/health/", *ROLE_PAGES.values()])
@pytest.mark.parametrize("visitor", VISITORS, ids=["signed-out", *ROLES])
def test_origin_other_site_with_valid_token_returns_403_before_other_rules(
    make_account, route, visitor
):
    browser, _ = browser_as(make_account, visitor)
    token = csrf_token(browser, visitor)
    response = send(browser, "POST", route, token, headers={"Origin": EVIL_ORIGIN})
    assert_forbidden(response, FORM_EXPIRED)
