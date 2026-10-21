"""Browser helpers for ACC-5's fixed form and one-time creation response."""

import copy
from urllib.parse import urlencode, urljoin

import pytest
from django.contrib.auth import get_user_model

from deskmate.tests import rate_limits as limits
from deskmate.tests import signing_in as auth
from deskmate.tests.demo_workspaces import ALPHABET
from deskmate.tests.pages import CSRF_FIELD, ORIGIN, Page
from deskmate.tests.password_resets import protected
from deskmate.tests.rate_limits import DEFAULT_SOURCE
from deskmate.tests.test_workspace_labels import assert_workspace

CREATE = "/support/create-requester/"
FORM = "Create Requester account"
BUTTON = "Create account"
SUCCESS = "Requester account created"
INTRO = "Create one Requester account in this workspace."
COPY = "Copy this password now. It will not be shown again."
QUOTA = "This workspace already has 20 Requester accounts."
NONCANONICAL = "Requester accounts cannot be created for this workspace."
REFUSED = "Too many account creation attempts. Wait a few minutes, then try again."
CODE = "23az9y"


def read_form(response, *, error=None, code=CODE):
    """Require the specified form, including its lack of user-selectable fields."""
    assert response.status_code == 200, response.status_code
    page = Page(protected(response))
    assert page.title == FORM and page.heading_texts == [FORM]
    assert_workspace(response, code)
    assert len(page.forms) == 1
    form = page.form_with_button(BUTTON)
    assert form.path == CREATE and form.method == "post"
    sent = [control for control in form.controls if control.is_sent()]
    assert len(sent) == 1 and sent[0].name == CSRF_FIELD
    assert sent[0].type == "hidden" and sent[0].value
    buttons = [control for control in form.controls if control.looks_like_button()]
    assert len(buttons) == 1 and buttons[0].caption == BUTTON
    assert buttons[0].is_button() and not buttons[0].name
    assert not any(control.is_field() for control in page.controls)
    assert page.links == [("Support Officer", urljoin(page.url, "/support/"))]
    assert not page.tables
    expected = f"{FORM} {FORM} Workspace: {code} {INTRO}"
    # Error placement relative to the button is not prescribed by ACC-5.2.
    text = page.text
    if error:
        assert text.count(error) == 1
        text = " ".join(text.replace(error, "").split())
    assert text == f"{expected} {BUTTON} Support Officer"
    return page


def read_success(response, username, *, code=CODE):
    """Require the entire specified success response and return its password."""
    assert response.status_code == 200, response.status_code
    page = Page(protected(response))
    assert page.title == SUCCESS and page.heading_texts == [SUCCESS]
    assert_workspace(response, code)
    assert len(page.tables) == 1 and len(page.tables[0]) == 2
    header, row = page.tables[0]
    assert header == [("th", "Username"), ("th", "Password")]
    assert len(row) == 2 and row[0] == ("td", username) and row[1][0] == "td"
    password = row[1][1]
    assert len(password) == 16 and set(password) <= set(ALPHABET)
    assert page.text == (
        f"{SUCCESS} {SUCCESS} Workspace: {code} {COPY} "
        f"Username Password {username} {password} Support Officer"
    )
    assert page.links == [("Support Officer", urljoin(page.url, "/support/"))]
    assert not page.forms
    return password


def read_refused(response, *, retry_after=600, sent=()):
    """Reuse the shared refusal checks with ACC-5's route-specific message."""
    with pytest.MonkeyPatch.context() as patch:
        patch.setitem(limits.REFUSALS, limits.CREATION, REFUSED)
        limits.assert_refused(
            protected(response), limits.CREATION, retry_after=retry_after, sent=sent
        )


class Creator:
    """An officer with a real session and CSRF token, independent of the new GET."""

    def __init__(self, browser, source=DEFAULT_SOURCE):
        self.browser, self.source = browser, source
        self.token = auth.csrf_token(browser, auth.SUPPORT_OFFICER)

    def clone(self, source=DEFAULT_SOURCE):
        """Send from an independent browser retaining this officer's session."""
        browser = auth.new_browser()
        browser.cookies = copy.deepcopy(self.browser.cookies)
        return Creator(browser, source)

    def post(self, *, source=None, fields=None, query=""):
        """Submit with a valid token and optional forged fields or address."""
        options = (source or self.source).options()
        return self.browser.post(
            CREATE + query,
            urlencode({CSRF_FIELD: self.token, **(fields or {})}, doseq=True),
            content_type="application/x-www-form-urlencoded",
            headers={"Origin": ORIGIN, **options["headers"]},
            **options["environ"],
        )


@pytest.fixture(name="creator")
def creation_fixture(make_account, clock):
    """A canonical workspace's officer, authenticated without using creation."""
    for number in (1, 2):
        make_account(f"requester{number}-{CODE}", auth.PASSWORD, auth.REQUESTER)
    officer = make_account(f"support1-{CODE}", auth.PASSWORD, auth.SUPPORT_OFFICER)
    browser = auth.new_browser()
    auth.assert_redirects(
        auth.sign_in(browser, officer.username, auth.PASSWORD), "/support/"
    )
    return Creator(browser), officer


def grow(officer, count):
    """Set up contiguous stored Requesters through count without spending attempts."""
    for number in range(3, count + 1):
        get_user_model().objects.create_user(
            username=f"requester{number}-{CODE}",
            password=None,
            role=auth.REQUESTER,
            workspace_id=officer.workspace_id,
        )
