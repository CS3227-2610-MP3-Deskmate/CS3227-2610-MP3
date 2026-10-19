"""RQ-1: Requesters submit tickets and read them in their workspace."""

import re
from datetime import timedelta
from urllib.parse import unquote, urlsplit

import pytest
from django.apps import apps
from django.contrib.auth import get_user_model

from deskmate.accounts.models import Workspace
from deskmate.tests.pages import CSRF_FIELD, ORIGIN, Page
from deskmate.tests.signing_in import (
    EVIL_ORIGIN,
    FORM_EXPIRED,
    NOT_FOR_YOUR_ROLE,
    REQUESTER,
    SUPPORT_OFFICER,
    VISITORS,
    assert_forbidden,
    assert_method_not_allowed,
    assert_redirects,
    assert_server_error,
    browser_as,
    csrf_token,
    methods_not_listed,
    new_browser,
    send,
    sign_in_as,
)

pytestmark = pytest.mark.django_db
LIST = "/requester/tickets/"
NEW = f"{LIST}new/"
MISSING = f"{LIST}999999999/"
LONG_ID = f"{LIST}{'9' * 5000}/"
ROUTES = (LIST, NEW, MISSING)
TICKET = re.compile(r"/requester/tickets/[0-9]+/")
TITLE_ERROR = "Enter a valid title (1 to 200 characters)."
DESCRIPTION_ERROR = "Enter a valid description (1 to 10000 characters)."
VALID = {"Title": "Printer", "Description": "It jams"}
# An identifier no ticket in the tests has, for a forged `pk` to choose.
UNUSED_ID = 1999999999
# Ticket fields and identifiers a forged creation request may name, sent in the
# form or the query string. `id` names an existing ticket in another workspace.
FORGED_CREATION = [
    *[("form", name) for name in ("open", "reply", "id", "pk")],
    *[
        ("query", name)
        for name in ("open", "reply", "id", "pk", "workspace", "workspace_id", "role")
    ],
]
# Reasons RQ-1.6 rejects a creation request that carries valid ticket fields.
REJECTED_CREATIONS = [
    "signed-out",
    "support-officer",
    "role-changed",
    "deleted",
    "expired",
    "missing-csrf",
    "other-origin",
]


@pytest.fixture
def requester(make_account):
    """A signed-in Requester and their stored account."""
    return sign_in_as(make_account, REQUESTER)


@pytest.fixture
def tickets():
    """Find the Ticket record specified by the technical data model."""
    matches = [m for m in apps.get_models() if m._meta.object_name == "Ticket"]
    assert len(matches) == 1, "The specified Ticket record is missing."
    return matches[0].objects


def form_at(browser, path=NEW):
    """Open the creation form as a browser does."""
    response = browser.get(path, secure=True)
    assert response.status_code == 200, f"GET {path}: {response.status_code}"
    return Page(response).form_with_button("Submit ticket")


def submit(browser, title="Printer", description="It jams", **changes):
    """Submit a ticket and return its page path."""
    response = form_at(browser).submit(
        browser, {"Title": title, "Description": description}, changes=changes
    )
    assert response.status_code == 302
    return urlsplit(response.url).path


def ticket_links(browser):
    """Read the ordered ticket titles and page paths from the list."""
    response = browser.get(LIST, secure=True)
    assert response.status_code == 200
    return [
        (text, urlsplit(url).path)
        for text, url in Page(response).links
        if TICKET.fullmatch(urlsplit(url).path)
    ]


def ticket_page(browser, path):
    """Read the ticket page at `path`."""
    response = browser.get(path, secure=True)
    assert response.status_code == 200, f"GET {path}: {response.status_code}"
    return Page(response)


def move_workspace(account, workspace):
    """Change the stored workspace, as an administrator could."""
    get_user_model().objects.filter(pk=account.pk).update(workspace=workspace)


@pytest.mark.ac("RQ-1.1", "RQ-1.2", "RQ-1.3")
def test_tickets_navigation_creation_and_reopening(requester, tickets):
    browser, account = requester
    role_page = Page(browser.get("/requester/", secure=True))
    assert ("Tickets", f"{ORIGIN}{LIST}") in role_page.links
    page = Page(browser.get(LIST, secure=True))
    assert page.title == "Tickets" and page.h1s == ["Tickets"]
    assert "No tickets yet." in page.text
    assert ("New ticket", f"{ORIGIN}{NEW}") in page.links
    assert ("Requester", f"{ORIGIN}/requester/") in page.links
    page = Page(browser.get(NEW, secure=True))
    assert page.title == "New ticket" and page.h1s == ["New ticket"]
    form = page.form_with_button("Submit ticket")
    assert form.field("Title").tag == "input"
    assert form.field("Description").tag == "textarea"
    assert [form.field(label).value for label in ("Title", "Description")] == ["", ""]
    assert ("Tickets", f"{ORIGIN}{LIST}") in page.links
    first = submit(browser, "Printer", "It jams")
    second = submit(browser, "Email", "No mail")
    assert ticket_links(browser) == [("Printer", first), ("Email", second)]
    page = ticket_page(browser, first)
    assert page.title == "Ticket" and page.h1s == ["Ticket"]
    assert "Printer" in page.text and "It jams" in page.text
    assert "Open" in page.text
    assert ("Tickets", f"{ORIGIN}{LIST}") in page.links
    assert (
        tickets.count() == 2
        and tickets.filter(workspace=account.workspace).count() == 2
    )


@pytest.mark.ac("RQ-1.3")
def test_tickets_description_line_breaks_are_shown(requester):
    browser, _ = requester
    path = submit(browser, "Printer", "Line one\nLine two")
    html = browser.get(path, secure=True).content.decode()
    assert re.search(r"Line one<br>\s*Line two", html)


@pytest.mark.ac("RQ-1.4")
@pytest.mark.parametrize(
    ("title", "description"),
    [
        ("a", "b"),
        ("x" * 200, "y" * 10000),
        ("  \u3000Title\t ", " \u3000Body\r\nline\rline "),
    ],
    ids=["minimum", "maximum", "whitespace-and-crlf"],
)
def test_tickets_valid_boundaries_and_normalisation(
    requester, tickets, title, description
):
    browser, _ = requester
    path = submit(browser, title, description)
    page = ticket_page(browser, path)
    assert title.strip() in page.text
    normalised = description.replace("\r\n", "\n").replace("\r", "\n").strip()
    assert all(
        part.strip() in page.text for part in normalised.split("\n") if part.strip()
    )


@pytest.mark.ac("RQ-1.4")
@pytest.mark.parametrize(
    ("field", "invalid"),
    [
        ("Title", None),
        ("Title", ""),
        ("Title", " \u3000\t"),
        ("Title", "x" * 201),
        ("Title", "a\rb"),
        ("Title", "a\nb"),
        ("Title", "a\r\nb"),
        ("Title", "a\x00b"),
        ("Description", None),
        ("Description", ""),
        ("Description", " \u3000\t"),
        ("Description", "x" * 10001),
        ("Description", "a\x00b"),
    ],
    ids=lambda value: (
        f"{len(value)}-chars"
        if isinstance(value, str) and len(value) > 24
        else repr(value)
    ),
)
def test_tickets_invalid_field_retains_input_and_saves_nothing(
    requester, tickets, field, invalid
):
    browser, _ = requester
    form = form_at(browser)
    typed = {"Title": " Raw title ", "Description": " Raw\r\nbody "}
    response = form.submit(browser, typed, changes={form.field(field).name: invalid})
    assert response.status_code == 200
    page = Page(response)
    assert (TITLE_ERROR in page.text) == (field == "Title")
    assert (DESCRIPTION_ERROR in page.text) == (field == "Description")
    retained = page.form_with_button("Submit ticket")
    typed[field] = invalid or ""
    for label, value in typed.items():
        value = (
            value.replace("\r\n", "\n").replace("\r", "\n").replace("\x00", "\ufffd")
        )
        assert retained.field(label).value == (
            value.replace("\n", " ") if label == "Title" else value
        )
    assert tickets.count() == 0


@pytest.mark.ac("RQ-1.5")
def test_tickets_same_title_and_resend_each_create_a_ticket(requester, tickets):
    browser, _ = requester
    first = submit(browser, "Same", "One")
    second = submit(browser, "Same", "Two")
    assert first != second
    assert [title for title, _ in ticket_links(browser)] == ["Same", "Same"]
    assert tickets.count() == 2


@pytest.mark.ac("RQ-1.6")
@pytest.mark.parametrize("visitor", [None, SUPPORT_OFFICER])
@pytest.mark.parametrize("path", ROUTES)
def test_tickets_access_denied_before_lookup(make_account, tickets, visitor, path):
    browser, _ = browser_as(make_account, visitor)
    response = send(
        browser,
        "GET",
        f"{path}?role={REQUESTER}&workspace=999",
        csrf_token(browser, visitor),
        headers={"Role": REQUESTER},
    )
    if visitor is None:
        assert_redirects(response, "/sign-in/")
    else:
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
    assert "no-store" in response["Cache-Control"]
    assert response["X-Frame-Options"] == "DENY"
    assert tickets.count() == 0


@pytest.mark.ac("RQ-1.6")
@pytest.mark.parametrize(
    ("method", "visitor", "path"),
    [
        (method, visitor, ROUTES[(i + j) % 3])
        for i, method in enumerate(methods_not_listed("GET", "POST"))
        for j, visitor in enumerate(VISITORS)
    ]
    + [("POST", visitor, LIST) for visitor in VISITORS],
)
def test_tickets_unsupported_methods_have_empty_405(
    make_account, tickets, method, visitor, path
):
    browser, _ = browser_as(make_account, visitor)
    assert_method_not_allowed(send(browser, method, path, csrf_token(browser, visitor)))
    assert tickets.count() == 0


@pytest.mark.ac("RQ-1.6")
@pytest.mark.parametrize("fault", ["missing", "wrong", "origin"])
def test_tickets_csrf_and_origin_rejection_creates_nothing(requester, tickets, fault):
    browser, _ = requester
    token = csrf_token(browser, REQUESTER)
    headers = {"Origin": "https://evil.example"} if fault == "origin" else None
    token = None if fault == "missing" else "wrong" if fault == "wrong" else token
    assert_forbidden(send(browser, "POST", NEW, token, headers=headers), FORM_EXPIRED)
    assert tickets.count() == 0


@pytest.mark.ac("RQ-1.6")
@pytest.mark.parametrize("reason", REJECTED_CREATIONS)
def test_tickets_rejected_valid_creation_creates_nothing(
    clock, requester, make_account, tickets, settings, reason
):
    browser, account = requester
    # A Requester's form, filled in with valid values before the rejection.
    form = form_at(browser)
    changes, headers = {}, None
    if reason == "signed-out":
        browser = new_browser()
        changes[CSRF_FIELD] = csrf_token(browser)
    elif reason == "support-officer":
        browser, _ = sign_in_as(make_account, SUPPORT_OFFICER)
        changes[CSRF_FIELD] = csrf_token(browser, SUPPORT_OFFICER)
    elif reason == "role-changed":
        get_user_model().objects.filter(pk=account.pk).update(role=SUPPORT_OFFICER)
    elif reason == "deleted":
        account.delete()
    elif reason == "expired":
        clock.set_elapsed(timedelta(hours=8))
    elif reason == "missing-csrf":
        changes[CSRF_FIELD] = None
    else:
        settings.DEBUG = False
        headers = {"Origin": EVIL_ORIGIN}
    response = form.submit(
        browser, VALID, button="Submit ticket", changes=changes, headers=headers
    )
    if reason in ("missing-csrf", "other-origin"):
        assert_forbidden(response, FORM_EXPIRED)
    elif reason in ("support-officer", "role-changed"):
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
    else:
        assert_redirects(response, "/sign-in/")
    assert tickets.count() == 0


@pytest.mark.ac("RQ-1.6")
@pytest.mark.parametrize("state", ["expired", "deleted", "role-changed"])
def test_tickets_current_session_and_stored_role_control_access(
    clock, requester, state
):
    browser, account = requester
    path = submit(browser, "Printer", "It jams")
    if state == "expired":
        clock.set_elapsed(__import__("datetime").timedelta(hours=8))
    elif state == "deleted":
        account.delete()
    else:
        get_user_model().objects.filter(pk=account.pk).update(role=SUPPORT_OFFICER)
    for target in (LIST, path):
        response = browser.get(target, secure=True)
        if state == "role-changed":
            assert_forbidden(response, NOT_FOR_YOUR_ROLE)
        else:
            assert_redirects(response, "/sign-in/")


@pytest.mark.ac("RQ-1.6")
def test_tickets_successful_responses_use_cache_and_framing_controls(requester):
    browser, _ = requester
    path = submit(browser, "Printer", "It jams")
    for target in (LIST, path):
        response = browser.get(target, secure=True)
        assert response.status_code == 200
        assert "no-store" in response["Cache-Control"]
        assert response["X-Frame-Options"] == "DENY"


@pytest.mark.ac("RQ-1.7")
def test_tickets_cannot_read_another_workspace(requester, make_account, tickets):
    browser, _ = requester
    own = submit(browser, "Own", "Own body")
    foreign = Workspace.objects.create()
    outsider, account = sign_in_as(make_account, REQUESTER)
    move_workspace(account, foreign)
    their = submit(outsider, "Foreign", "Foreign body")
    response = browser.get(their, secure=True)
    assert response.status_code == 404
    assert response.content == browser.get(MISSING).content
    assert b"Foreign body" not in response.content
    assert ticket_links(browser) == [("Own", own)]
    for query in (f"?id={own}", f"?role={REQUESTER}", f"?workspace={foreign.pk}"):
        assert browser.get(f"{their}{query}", secure=True).status_code == 404
    assert browser.get(LONG_ID, secure=True).status_code == 404
    overflow = f"{LIST}9999999999999999999/"
    assert browser.get(overflow, secure=True).status_code == 404


@pytest.mark.ac("RQ-1.7")
def test_tickets_forged_fields_cannot_change_workspace(requester, tickets):
    browser, account = requester
    foreign = Workspace.objects.create()
    path = submit(
        browser,
        "Own",
        "Own body",
        workspace=foreign.pk,
        workspace_id=foreign.pk,
        role=SUPPORT_OFFICER,
    )
    ticket = tickets.get(pk=int(path.strip("/").split("/")[-1]))
    assert ticket.workspace_id == account.workspace_id
    assert tickets.count() == 1


@pytest.mark.ac("RQ-1.2", "RQ-1.7")
@pytest.mark.parametrize(("place", "name"), FORGED_CREATION)
def test_tickets_forged_creation_fields_create_one_open_ticket_and_change_none(
    requester, tickets, place, name
):
    browser, account = requester
    own = tickets.create(workspace=account.workspace, title="Own", description="Body")
    foreign = tickets.create(
        workspace=Workspace.objects.create(),
        title="Foreign",
        description="Foreign body",
        open=False,
        reply="Foreign answer",
    )
    existing = list(tickets.values())
    forged = {
        name: {
            "open": "false",
            "reply": "Forged reply",
            "id": str(foreign.pk),
            "pk": str(UNUSED_ID),
            "workspace": str(foreign.workspace_id),
            "workspace_id": str(foreign.workspace_id),
            "role": SUPPORT_OFFICER,
        }[name]
    }
    response = form_at(browser).submit(
        browser,
        VALID,
        button="Submit ticket",
        changes=forged if place == "form" else None,
        query=forged if place == "query" else None,
    )
    assert response.status_code == 302
    created = list(tickets.exclude(pk__in=[own.pk, foreign.pk]).values())
    assert len(created) == 1, created
    ticket = created[0]
    assert ticket["id"] != UNUSED_ID
    assert urlsplit(response.url).path == f"{LIST}{ticket['id']}/"
    assert ticket == {
        "id": ticket["id"],
        "workspace_id": account.workspace_id,
        "title": "Printer",
        "description": "It jams",
        "open": True,
        "reply": "",
    }
    assert list(tickets.filter(pk__in=[own.pk, foreign.pk]).values()) == existing


@pytest.mark.ac("RQ-1.7")
@pytest.mark.parametrize(
    "encoded",
    [
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
        "%22%3E%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E",
        "%5Blink%5D%28https%3A%2F%2Fevil.example%29",
    ],
)
def test_tickets_saved_markup_is_text(requester, encoded):
    browser, _ = requester
    payload = unquote(encoded)
    path = submit(browser, payload, payload)
    for target in (path, LIST):
        response = browser.get(target, secure=True)
        html = response.content.decode()
        assert payload in Page(response).text
        assert "<script>" not in html and "<img" not in html
        assert not [url for _, url in Page(response).links if "evil.example" in url]


@pytest.mark.ac("RQ-1.8")
@pytest.mark.parametrize("path", ROUTES)
def test_tickets_database_outage_returns_generic_error(
    requester, database_outage, path
):
    browser, _ = requester
    browser.raise_request_exception = False
    with database_outage():
        assert_server_error(browser.get(path, secure=True))


@pytest.mark.ac("RQ-1.7")
def test_tickets_list_uses_stored_workspace(requester):
    browser, account = requester
    submit(browser, "Printer", "It jams")
    assert ticket_links(browser)
    move_workspace(account, Workspace.objects.create())
    assert ticket_links(browser) == []
    assert "No tickets yet." in Page(browser.get(LIST, secure=True)).text
