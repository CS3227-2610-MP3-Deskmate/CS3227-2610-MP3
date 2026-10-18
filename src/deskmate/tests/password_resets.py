"""Browser-level reset assertions and existing limiter adapters (ACC-4)."""

import copy
from urllib.parse import urlencode, urljoin

import pytest
from django.contrib.auth import get_user_model

from deskmate.tests.demo_workspaces import ALPHABET
from deskmate.tests.helpers import cache_directives
from deskmate.tests.pages import CSRF_FIELD, ORIGIN, Page, normalise
from deskmate.tests.rate_limits import DEFAULT_SOURCE
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    SUPPORT_OFFICER,
    csrf_token,
    new_browser,
    sign_in_as,
)

RESET = "/support/reset-requester-password/"
FORM = "Reset Requester password"
BUTTON = "Reset password"
SUCCESS = "Requester password reset"
COPY = "Copy this password now. It will not be shown again."
REJECTED = "No Requester with that username was found in your workspace."
REFUSED = "Too many password resets. Wait a few minutes, then try again."


def protected(response):
    """Check the headers required on every reset response."""
    assert "no-store" in cache_directives(response), response.status_code
    assert response.get("X-Frame-Options") == "DENY"
    return response


def read_form(response, value="", *, rejected=False):
    """Check the exact form and optional generic rejection."""
    assert response.status_code == 200, response.status_code
    page = Page(protected(response))
    assert page.title == FORM
    assert page.h1s == [FORM]
    form = page.form_with_button(BUTTON)
    assert form.path == RESET and form.method == "post"
    fields = [control for control in page.controls if control.is_field()]
    assert fields == [form.field("Username")]
    assert fields[0].tag == "input" and fields[0].type == "text"
    assert fields[0].value == value
    assert page.links == [("Support Officer", urljoin(page.url, "/support/"))]
    assert page.text.count(REJECTED) == int(rejected)
    assert normalise(page.text.replace(REJECTED, "")) == (
        f"{FORM} {FORM} Username {BUTTON} Support Officer"
    )
    assert not page.tables
    return page


def read_success(response, username):
    """Check the exact one-row result and return its generated password."""
    assert response.status_code == 200, response.status_code
    page = Page(protected(response))
    assert page.title == SUCCESS and page.heading_texts == [SUCCESS]
    assert len(page.tables) == 1 and len(page.tables[0]) == 2
    assert page.tables[0][0] == [("th", "Username"), ("th", "Password")]
    row = page.tables[0][1]
    assert row[0] == ("td", username) and row[1][0] == "td"
    password = row[1][1]
    assert len(password) == 16 and set(password) <= set(ALPHABET)
    assert page.text == (
        f"{SUCCESS} {SUCCESS} {COPY} Username Password {username} {password} "
        "Support Officer"
    )
    assert page.links == [("Support Officer", urljoin(page.url, "/support/"))]
    assert not page.forms
    return password


class Resetter:
    """A signed-in officer submitting with a real CSRF token, even before GET exists."""

    def __init__(self, browser, source=DEFAULT_SOURCE):
        self.browser, self.source = browser, source
        self.token = csrf_token(browser, SUPPORT_OFFICER)

    def clone(self, source=DEFAULT_SOURCE):
        """Use another client holding this officer's authenticated cookies."""
        browser = new_browser()
        browser.cookies = copy.deepcopy(self.browser.cookies)
        return Resetter(browser, source)

    def post(self, username="nobody", *, source=None, fields=None, query=""):
        """Submit raw URL-encoded fields, retaining repeated username values."""
        data = {CSRF_FIELD: self.token, **(fields or {})}
        if username is not None:
            data["username"] = username
        return self.browser.post(
            RESET + query,
            urlencode(data, doseq=True),
            content_type="application/x-www-form-urlencoded",
            headers={
                "Origin": ORIGIN,
                **((source or self.source).options()["headers"]),
            },
            **(source or self.source).options()["environ"],
        )


@pytest.fixture(name="resetter")
def reset_fixture(make_account):
    """An officer and an eligible Requester in the existing shared workspace fixture."""
    browser, officer = sign_in_as(make_account, SUPPORT_OFFICER, "officer")
    requester = make_account("alice", PASSWORD, REQUESTER)
    return Resetter(browser), officer, requester


def accounts():
    """Return every account attribute, so a reset cannot silently change another."""
    return {row["id"]: row for row in get_user_model().objects.values()}
