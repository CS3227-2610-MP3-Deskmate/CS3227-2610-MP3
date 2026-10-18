"""RQ-2: Support Officers read their workspace's tickets without changing them."""

import re
from datetime import timedelta
from urllib.parse import unquote, urlsplit

import pytest
from django.contrib.sessions.models import Session
from django.db import DatabaseError, connection

from deskmate.accounts.models import User, Workspace
from deskmate.tests import signing_in as auth
from deskmate.tests.pages import ORIGIN, Page
from deskmate.tests.signing_in import REQUESTER, SUPPORT_OFFICER, VISITORS
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.django_db
LIST = "/support/tickets/"
MISSING = f"{LIST}999999999/"
ROUTES = (LIST, MISSING)
MAX_ID = 9223372036854775807


@pytest.fixture
def officer(make_account):
    """A browser authenticated through the existing sign-in form."""
    return auth.sign_in_as(make_account, SUPPORT_OFFICER)


@pytest.fixture
def records(officer):
    """A visible ticket and an unrelated workspace's private ticket."""
    own = Ticket.objects.create(
        workspace=officer[1].workspace, title="Zulu request", description="Own body"
    )
    foreign = Ticket.objects.create(
        workspace=Workspace.objects.create(),
        title="Private title",
        description="Private body",
    )
    return own, foreign


def snapshot():
    """Include every stored ticket field when detecting unintended writes."""
    return list(Ticket.objects.order_by("pk").values_list())


def security(response):
    """All ticket outcomes use the existing cache and framing controls."""
    assert "no-store" in response["Cache-Control"]
    assert response["X-Frame-Options"] == "DENY"


def checked_send(browser, method, path, token=None, *, forbid=(), **options):
    """Check read-only behavior and optionally forbid premature database reads."""
    before = snapshot()

    def guard(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("SELECT"):
            assert not any(table in sql for table in forbid), "Premature read"
        return execute(sql, params, many, context)

    with connection.execute_wrapper(guard):
        response = auth.send(browser, method, path, token, secure=True, **options)
    assert snapshot() == before
    security(response)
    return response


def page_at(browser, path=LIST):
    """Open a successful page and check its read-only navigation."""
    response = checked_send(browser, "GET", path)
    assert response.status_code == 200
    page = Page(response)
    assert all(form.path == "/sign-out/" for form in page.forms)
    assert not any(control.is_field() for control in page.controls)
    assert not any("/requester/" in url for _, url in page.links)
    assert all(
        re.fullmatch(f"{LIST}([0-9]+/)?", urlsplit(url).path)
        for _, url in page.links
        if "/tickets/" in url
    )
    forbidden = {"New ticket", "Reply", "Submit reply", "Close ticket"}
    forbidden.update({"Assign", "Edit", "Delete"})
    assert not forbidden.intersection(text for text, _ in page.links)
    assert not forbidden.intersection(control.caption for control in page.controls)
    return page


@pytest.mark.ac("RQ-2.1", "RQ-2.2", "RQ-2.3", "RQ-2.6")
def test_support_tickets_navigation_order_duplicates_and_refresh(officer):
    browser, account = officer
    assert ("Tickets", f"{ORIGIN}{LIST}") in Page(
        browser.get("/support/", secure=True)
    ).links
    page = page_at(browser)
    assert page.title == "Tickets" and page.h1s == ["Tickets"]
    assert "No tickets yet." in page.text
    assert ("Support Officer", f"{ORIGIN}/support/") in page.links
    assert not any(
        re.fullmatch(f"{LIST}[0-9]+/", urlsplit(url).path) for _, url in page.links
    )
    items = [
        Ticket.objects.create(
            workspace=account.workspace,
            title=title,
            description=f"Body {index}",
            open=is_open,
        )
        for index, (title, is_open) in enumerate(
            [("Zulu", True), ("Alpha", False), ("Zulu", False)]
        )
    ]
    Ticket.objects.create(
        workspace=Workspace.objects.create(), title="Private", description="Hidden"
    )
    for _ in range(2):
        page = page_at(browser)
        assert "No tickets yet." not in page.text
        assert [(text, url) for text, url in page.links if "/tickets/" in url] == [
            (item.title, f"{ORIGIN}{LIST}{item.pk}/") for item in items
        ]
        for item in items:
            detail = page_at(browser, f"{LIST}{item.pk}/")
            assert detail.title == "Ticket" and detail.h1s == ["Ticket"]
            assert item.title in detail.text and item.description in detail.text
            assert ("Open" if item.open else "Closed") in detail.text.split()
            assert ("Closed" if item.open else "Open") not in detail.text.split()
            assert ("Tickets", f"{ORIGIN}{LIST}") in detail.links


@pytest.mark.ac("RQ-2.2", "RQ-2.7")
@pytest.mark.parametrize(
    "encoded",
    [
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
        "%22%3E%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E",
        "%26lt%3Bb%26gt%3B%20%2A%2Abold%2A%2A%20%5Blink%5D%28https%3A%2F%2Fevil.example%29",
    ],
)
def test_support_tickets_text_and_line_breaks_are_plain(officer, encoded):
    browser, account = officer
    payload = unquote(encoded)
    item = Ticket.objects.create(
        workspace=account.workspace,
        title=payload,
        description=f"{payload}\nLine two\nhttps://evil.example",
    )
    for target in (LIST, f"{LIST}{item.pk}/"):
        response = checked_send(browser, "GET", target)
        assert response.status_code == 200
        page, html = Page(response), response.content.decode()
        assert payload in page.text
        assert all(tag not in html for tag in ("<script", "<img", "<strong", "<b>"))
        assert not any("evil.example" in url for _, url in page.links)
        if target != LIST:
            assert re.search(r"Line two<br\s*/?>\s*https://evil\.example", html)


@pytest.mark.ac("RQ-2.4", "RQ-2.6")
@pytest.mark.parametrize(
    "identifier",
    ["0", "unknown", "foreign", "zero-foreign", "zero-own", "long-zero-own"]
    + [str(MAX_ID + offset) for offset in (-1, 0, 1)]
    + ["9" * 5000, "-1", "+1", "1.0", "1e0", "\u0661", "\uff11", "new", "%3Cscript%3E"],
    ids=lambda value: value if len(value) < 30 else f"{len(value)}-digits",
)
def test_support_tickets_identifier_boundaries(officer, records, identifier):
    browser, account = officer
    own, foreign = records
    page_at(browser, f"{LIST}{own.pk}/")
    aliases = {
        "unknown": "999999999",
        "foreign": str(foreign.pk),
        "zero-foreign": f"000{foreign.pk}",
        "zero-own": f"000{own.pk}",
        "long-zero-own": f"{'0' * 5000}{own.pk}",
    }
    if identifier in (str(MAX_ID - 1), str(MAX_ID)):
        Ticket.objects.create(
            pk=int(identifier),
            workspace=account.workspace,
            title="Range boundary",
            description="Boundary body",
        )
    response = checked_send(
        browser, "GET", f"{LIST}{aliases.get(identifier, identifier)}/"
    )
    if identifier in ("zero-own", "long-zero-own", str(MAX_ID - 1), str(MAX_ID)):
        assert response.status_code == 200
        body = "Own body" if "own" in identifier else "Boundary body"
        assert body in Page(response).text
    else:
        assert response.status_code == 404
        assert response.content == checked_send(browser, "GET", MISSING).content
        assert all(text not in response.content for text in (b"Private", b"Own body"))


@pytest.mark.ac("RQ-2.5", "RQ-2.6")
@pytest.mark.parametrize("visitor", [None, REQUESTER])
@pytest.mark.parametrize("path", ROUTES)
def test_support_tickets_denial_precedes_lookup(make_account, records, visitor, path):
    browser, _ = auth.browser_as(make_account, visitor)
    own, _ = records
    browser.cookies["role"] = SUPPORT_OFFICER
    browser.cookies["workspace"] = own.workspace_id
    response = checked_send(
        browser,
        "GET",
        f"{path}?role={SUPPORT_OFFICER}&workspace={own.workspace_id}",
        data={"role": SUPPORT_OFFICER, "id": own.pk},
        headers={"Role": SUPPORT_OFFICER, "Workspace": str(own.workspace_id)},
        forbid=(Ticket._meta.db_table,),
    )
    if visitor is None:
        auth.assert_redirects(response, "/sign-in/")
    else:
        auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)


@pytest.mark.ac("RQ-2.5")
@pytest.mark.parametrize(
    "state",
    ["before", "expired", "past", "deleted", "role", "workspace"],
)
def test_support_tickets_stored_state_applies(clock, officer, records, state):
    browser, account = officer
    own, foreign = records
    if state in ("before", "expired", "past"):
        offset = {"before": -1, "expired": 0, "past": 1}[state]
        clock.set_elapsed(timedelta(hours=8, seconds=offset))
    elif state == "deleted":
        account.delete()
    elif state == "role":
        User.objects.filter(pk=account.pk).update(role=REQUESTER)
    else:
        User.objects.filter(pk=account.pk).update(workspace=foreign.workspace)
    for target in (LIST, f"{LIST}{own.pk}/"):
        response = checked_send(browser, "GET", target)
        if state in ("expired", "past", "deleted"):
            auth.assert_redirects(response, "/sign-in/")
        elif state == "role":
            auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)
        elif state == "workspace":
            assert response.status_code == (200 if target == LIST else 404)
            assert b"Zulu request" not in response.content
        else:
            assert response.status_code == 200
    if state == "workspace":
        assert "Private body" in page_at(browser, f"{LIST}{foreign.pk}/").text


@pytest.mark.ac("RQ-2.4", "RQ-2.5")
def test_support_tickets_client_overrides_have_no_authority(officer, records):
    browser, _ = officer
    own, foreign = records
    browser.cookies["workspace"] = foreign.workspace_id
    browser.cookies["role"] = REQUESTER
    query = (
        f"?workspace={foreign.workspace_id}&workspace_id={foreign.workspace_id}"
        f"&id={foreign.pk}&ticket_id={foreign.pk}&role={REQUESTER}"
    )
    for path in (LIST, f"{LIST}{own.pk}/", f"{LIST}{foreign.pk}/"):
        response = checked_send(
            browser,
            "GET",
            path + query,
            data={"workspace": foreign.workspace_id, "ticket_id": foreign.pk},
            headers={"Workspace": str(foreign.workspace_id), "Role": REQUESTER},
        )
        expected = 404 if path.endswith(f"/{foreign.pk}/") else 200
        assert response.status_code == expected
        assert all(
            text not in response.content for text in (b"Private title", b"Private body")
        )


@pytest.mark.ac("RQ-2.3", "RQ-2.5", "RQ-2.6")
@pytest.mark.parametrize(
    ("method", "visitor", "path", "fault"),
    [
        (method, visitor, ROUTES[(i + j) % 2], None)
        for i, method in enumerate(auth.methods_not_listed("GET"))
        for j, visitor in enumerate(VISITORS)
    ]
    + [
        ("POST", visitor, ROUTES[(i + j) % 2], fault)
        for i, fault in enumerate(("missing", "wrong", "origin"))
        for j, visitor in enumerate(VISITORS)
    ],
)
def test_support_tickets_csrf_method_access_precedence(
    make_account, records, method, visitor, path, fault
):
    browser, _ = auth.browser_as(make_account, visitor)
    token = auth.csrf_token(browser, visitor)
    response = checked_send(
        browser,
        method,
        path,
        None if fault == "missing" else "wrong" if fault == "wrong" else token,
        headers={"Origin": "https://evil.example"} if fault == "origin" else {},
        forbid=("",),
        data={"title": "Changed", "description": "Changed", "open": "false"},
    )
    if fault:
        auth.assert_forbidden(response, auth.FORM_EXPIRED)
    else:
        auth.assert_method_not_allowed(response)


@pytest.mark.ac("RQ-2.6", "RQ-2.8")
@pytest.mark.parametrize("path", ROUTES)
@pytest.mark.parametrize(
    "table", [Session._meta.db_table, User._meta.db_table, Ticket._meta.db_table]
)
def test_support_tickets_read_failure_is_generic(officer, records, path, table):
    browser, _ = officer
    before, reads = snapshot(), []
    browser.raise_request_exception = False

    def fail(execute, sql, params, many, context):
        if table in sql and sql.lstrip().upper().startswith("SELECT"):
            reads.append(sql)
            raise DatabaseError("Synthetic private ticket read failure")
        return execute(sql, params, many, context)

    with connection.execute_wrapper(fail):
        response = browser.get(path, secure=True)
    auth.assert_server_error(
        response,
        {
            "private title": "Private title",
            "private body": "Private body",
            "own title": "Zulu request",
            "own description": "Own body",
            "read failure": "Synthetic private ticket read failure",
        },
    )
    assert len(reads) == 1 and "Location" not in response
    assert snapshot() == before
    security(response)


@pytest.mark.ac("RQ-2.6", "RQ-2.8")
@pytest.mark.parametrize("path", ROUTES)
def test_support_tickets_outage_is_generic(officer, records, database_outage, path):
    browser, _ = officer
    before = snapshot()
    browser.raise_request_exception = False
    with database_outage():
        response = browser.get(path, secure=True)
    auth.assert_server_error(response)
    assert "Location" not in response and b"Private" not in response.content
    assert snapshot() == before
    security(response)
