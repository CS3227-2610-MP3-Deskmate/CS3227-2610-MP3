"""Signing in and out, and the checks the ACC-1 tests share (accounts.md).

The tests sign in as a browser does: they load the sign-in page, type into the
fields labelled Username and Password and press Sign in, with Django's CSRF
checks enforced. Every account is made by the `make_account` fixture.
"""

import itertools
from urllib.parse import urlencode, urljoin, urlsplit

from django.conf import settings
from django.test import Client

from deskmate.tests.helpers import internal_details
from deskmate.tests.pages import CSRF_FIELD, ORIGIN, SITE, Page, normalise

# The stored values of the two roles.
REQUESTER = "requester"
SUPPORT_OFFICER = "support_officer"
ROLES = (REQUESTER, SUPPORT_OFFICER)
ROLE_PAGES = {REQUESTER: "/requester/", SUPPORT_OFFICER: "/support/"}
ROLE_TITLES = {REQUESTER: "Requester", SUPPORT_OFFICER: "Support Officer"}
SIGN_IN = "/sign-in/"
SIGN_OUT = "/sign-out/"
# Synthetic passwords; nothing outside the tests uses them.
PASSWORD = "Synthetic pass 1"
WRONG_PASSWORD = "Wrong pass 2"
# The fixed texts of ACC-1.3, ACC-1.5 and ACC-1.8.
SIGN_IN_ERROR = "Incorrect username or password."
NOT_FOR_YOUR_ROLE = "This page is not for your role."
FORM_EXPIRED = "This form has expired. Go back, reload the page and try again."
# The methods that need no CSRF token (ACC-1.8).
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS", "TRACE"})

_numbers = itertools.count(1)


def other_role(role):
    """Return the role that is not `role`."""
    return SUPPORT_OFFICER if role == REQUESTER else REQUESTER


def new_browser():
    """Return a test client that, like a browser, gets Django's CSRF checks."""
    return Client(enforce_csrf_checks=True)


def session_cookie(browser):
    """Return the value of the session cookie `browser` holds, or None."""
    morsel = browser.cookies.get(settings.SESSION_COOKIE_NAME)
    return morsel.value if morsel is not None else None


def get_sign_in_page(browser, path=SIGN_IN):
    """Load the sign-in page at `path` in `browser`, check it is served, return it."""
    response = browser.get(path)
    assert response.status_code == 200, f"GET {path} returned {response.status_code}."
    return Page(response)


def submit_sign_in(browser, page, username, password, **options):
    """Type `username` and `password` into `page`'s form and press Sign in.

    `options` are those of `Form.submit`. Returns the response.
    """
    form = page.form_with_button("Sign in")
    typed = {"Username": username, "Password": password}
    return form.submit(browser, typed, button="Sign in", **options)


def sign_in(browser, username, password, **options):
    """Load the sign-in page in `browser` and sign in; return the response."""
    page = get_sign_in_page(browser)
    return submit_sign_in(browser, page, username, password, **options)


def sign_in_as(make_account, role, username=None):
    """Make an account with `role`, sign it in in a new browser, and check it.

    Returns the browser and the account.
    """
    username = username or f"{role}{next(_numbers)}"
    account = make_account(username, PASSWORD, role)
    browser = new_browser()
    assert_redirects(sign_in(browser, username, PASSWORD), ROLE_PAGES[role])
    return browser, account


def csrf_token(browser, role=None):
    """Return a CSRF token from a form that `browser` was served.

    For a signed-out browser it comes from the sign-in page; for one signed in
    with `role`, from the Sign out form on that role's page.
    """
    if role is None:
        return get_sign_in_page(browser).csrf_token()
    response = browser.get(ROLE_PAGES[role])
    assert response.status_code == 200, f"GET {ROLE_PAGES[role]} failed."
    return Page(response).csrf_token()


def send(browser, method, path, token=None, *, headers=None, secure=False):
    """Send a `method` request for `path` from `browser`; return the response.

    A `token` goes in the form data of a POST and in Django's CSRF header for
    other methods. A request by a method that needs a token carries
    `Origin: https://testserver`, as a browser's would, unless `headers`
    replaces it.
    """
    body = ""
    extra = {}
    if token is not None:
        if method == "POST":
            body = urlencode({CSRF_FIELD: token})
        else:
            extra[settings.CSRF_HEADER_NAME] = token
    sent_headers = {} if method in SAFE_METHODS else {"Origin": ORIGIN}
    sent_headers.update(headers or {})
    return browser.generic(
        method,
        path,
        body,
        content_type="application/x-www-form-urlencoded",
        secure=secure,
        headers=sent_headers,
        **extra,
    )


def assert_redirects(response, path):
    """Assert `response` is a 302 to exactly `path` on this site, with no query."""
    assert response.status_code == 302, (
        f"Expected a 302 redirect to {path}, got {response.status_code}."
    )
    base = response.wsgi_request.build_absolute_uri()
    target = urlsplit(urljoin(base, response["Location"]))
    assert (target.netloc, target.path, target.query, target.fragment) == (
        SITE,
        path,
        "",
        "",
    ), f"Redirected to {response['Location']!r}, not {path!r}."


def assert_sign_in_page(response):
    """Assert `response` is the sign-in page of ACC-1.1, and return it."""
    assert response.status_code == 200
    page = Page(response)
    assert page.title == "Sign in"
    assert page.h1s == ["Sign in"]
    form = page.form_with_button("Sign in")
    assert form.method == "post"
    assert form.path == SIGN_IN
    assert form.field("Username").type == "text"
    assert form.field("Password").type == "password"
    return page


def assert_sign_in_failed(response, typed_username, fresh_page):
    """Assert `response` is the sign-in page with only the ACC-1.3 error.

    `fresh_page` is the sign-in page the user typed into; apart from the one
    error, the response must have the same text. The Username field must keep
    exactly `typed_username`, and the Password field must be empty.
    """
    page = assert_sign_in_page(response)
    assert page.text.count(SIGN_IN_ERROR) == 1, page.text
    assert normalise(page.text.replace(SIGN_IN_ERROR, " ")) == fresh_page.text
    form = page.form_with_button("Sign in")
    assert (form.field("Username").value or "") == typed_username
    assert not form.field("Password").value


def assert_role_page(response, role, username):
    """Assert `response` is `role`'s page of ACC-1.2, for `username`."""
    assert response.status_code == 200, (
        f"Expected the {ROLE_TITLES[role]} page, got {response.status_code}."
    )
    page = Page(response)
    assert page.title == ROLE_TITLES[role]
    assert page.h1s == [ROLE_TITLES[role]]
    assert f"Signed in as {username}." in page.text, page.text
    form = page.form_with_button("Sign out")
    assert form.method == "post"
    assert form.path == SIGN_OUT


def assert_signed_in_as(browser, role, username):
    """Assert `browser` is signed in as `username`, who has `role`."""
    assert_role_page(browser.get(ROLE_PAGES[role]), role, username)


def assert_signed_out(browser):
    """Assert both role pages send `browser` to the sign-in page (ACC-1.4)."""
    for path in ROLE_PAGES.values():
        assert_redirects(browser.get(path), SIGN_IN)


def assert_forbidden(response, message):
    """Assert `response` is a 403 page titled and headed Forbidden.

    Its only other text must be `message`, and it must show none of the
    internal details of PLT-1.4.
    """
    assert response.status_code == 403, f"Expected 403, got {response.status_code}."
    page = Page(response)
    assert page.title == "Forbidden"
    assert page.heading_texts == ["Forbidden"]
    assert page.text == f"Forbidden Forbidden {message}"
    body = response.content.decode("utf-8", "replace")
    assert internal_details(body, {"the secret key": settings.SECRET_KEY}) == []


def assert_method_not_allowed(response):
    """Assert `response` is a 405 with an empty body."""
    assert response.status_code == 405, f"Expected 405, got {response.status_code}."
    assert response.content == b""


def assert_server_error(response):
    """Assert `response` is a 500 that shows no internal details (PLT-1.4)."""
    assert response.status_code == 500, f"Expected 500, got {response.status_code}."
    body = response.content.decode("utf-8", "replace")
    details = {
        "the secret key": settings.SECRET_KEY,
        "the database's name": settings.DATABASES["default"]["NAME"],
        "the database error's type": "OperationalError",
        "the database error's message": "connection to server",
    }
    assert internal_details(body, details) == []
