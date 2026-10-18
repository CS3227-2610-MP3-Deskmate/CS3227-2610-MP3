"""RQ-3: one atomic workspace resolution, shared by both readers."""

from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from types import SimpleNamespace
from urllib.parse import unquote

import pytest
from django.contrib.sessions.models import Session
from django.db import DatabaseError, connection, connections
from django.db.migrations.executor import MigrationExecutor

from deskmate.accounts.models import User, Workspace
from deskmate.tests import signing_in as auth
from deskmate.tests.pages import ORIGIN, Page
from deskmate.tests.test_support_tickets import checked_send, security, snapshot
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.django_db
BASE = "/support/tickets/"
ERROR = "Enter a valid reply (1 to 10000 characters)."


@pytest.fixture
def c(make_account):
    """Browser, stored user, own ticket, foreign ticket and request metadata."""
    b, u = auth.sign_in_as(make_account, auth.SUPPORT_OFFICER)
    t = Ticket.objects.create(workspace=u.workspace, title="Own", description="Body")
    f = Ticket.objects.create(
        workspace=Workspace.objects.create(), title="Private", description="Hidden"
    )
    return SimpleNamespace(
        b=b,
        u=u,
        t=t,
        f=f,
        path=f"{BASE}{t.pk}/resolve/",
        detail=f"{BASE}{t.pk}/",
        token=auth.csrf_token(b, auth.SUPPORT_OFFICER),
    )


def read(c, method="GET", path=None, **options):
    """Check headers and no mutations on a request expected to be read-only."""
    return checked_send(c.b, method, path or c.path, c.token, **options)


def form_at(c):
    """Fail at the missing route before setting up later request partitions."""
    response = read(c)
    assert response.status_code == 200
    return Page(response).form_with_button("Resolve ticket")


def submit(c, form, raw, **options):
    """Submit the real labelled field, including browser CSRF and Origin."""
    response = form.submit(c.b, {"Reply": raw}, secure=True, **options)
    security(response)
    return response


def require_reply():
    """Fail clearly before constructing states that need the new column."""
    assert "reply" in {f.name for f in Ticket._meta.fields}, "Missing reply column."


@pytest.mark.ac("RQ-3.1", "RQ-3.2", "RQ-3.3", "RQ-3.7", "RQ-1.3", "RQ-2.2")
@pytest.mark.parametrize(
    "kind",
    ["minimum", "above-min", "below-max", "maximum", "unicode", "crlf", "markup"],
)
def test_resolution_form_save_plaintext_and_readers_refresh(c, make_account, kind):
    payload = unquote(
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E%22%3E%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E%20%26lt%3Bb%26gt%3B%20%2A%2Abold%2A%2A%20%5Blink%5D%28https%3A%2F%2Fevil.example%29"
    )
    raw = {
        "minimum": "a",
        "above-min": "ab",
        "below-max": "\U0001f642" * 9999,
        "maximum": "\U0001f642" * 10000,
        "crlf": "x\r\n" + "y" * 9998,
        "unicode": "\u3000 e\u0301  \uff21\tinside\r\nnext\rend\u200b \u00a0",
        "markup": payload + "\nLine two\nhttps://evil.example",
    }[kind]
    Ticket.objects.filter(pk=c.t.pk).update(
        title=payload, description="Body\nSecond line"
    )
    form, page = form_at(c), Page(read(c))
    assert page.title == "Resolve ticket" and page.h1s == ["Resolve ticket"]
    assert payload in page.text and ("Ticket", ORIGIN + c.detail) in page.links
    assert "Body Second line" in page.text
    html = read(c).content.decode()
    assert "Body<br>" in html and "<script" not in html and "<img" not in html
    assert form.field("Reply").tag == "textarea" and not form.field("Reply").value
    before = list(Ticket.objects.values())
    auth.assert_redirects(submit(c, form, raw), c.detail)
    reply = raw.replace("\r\n", "\n").replace("\r", "\n").strip()
    before[0].update(reply=reply, open=False)
    assert list(Ticket.objects.values()) == before
    requester, _ = auth.sign_in_as(make_account, auth.REQUESTER)
    paths = ((c.b, c.detail), (requester, f"/requester/tickets/{c.t.pk}/"))
    for browser, path in paths:
        for _ in range(2):
            response = checked_send(browser, "GET", path)
            html, page = response.content.decode(), Page(response)
            assert "Closed" in page.text and "Reply" in page.heading_texts
            assert " ".join(reply.split()) in page.text
            assert not any(x.is_field() for x in page.controls)
            assert not any("resolve" in url for _, url in page.links)
            assert not any("evil.example" in url for _, url in page.links)
            assert all(tag not in html for tag in ("<script", "<img", "<strong"))
            if kind == "markup":
                assert "Line two<br>" in html


@pytest.mark.ac("RQ-3.3", "RQ-3.7")
@pytest.mark.parametrize("kind", ["missing", "empty", "space", "long", "null", "raw"])
def test_resolution_invalid_reply_retains_raw_text(c, kind):
    attack = unquote("%3C%2Ftextarea%3E%3Cscript%3Ealert%281%29%3C%2Fscript%3E")
    raw = {
        "missing": None,
        "empty": "",
        "space": " \u3000\t\r\n",
        "long": "x" * 10001,
        "null": "a\x00b",
        "raw": " \n" + attack + "\r\nline\rend\x00 ",
    }[kind]
    form, before = form_at(c), snapshot()
    response = form.submit(c.b, changes={form.field("Reply").name: raw}, secure=True)
    assert response.status_code == 200
    security(response)
    page = Page(response)
    assert page.title == "Resolve ticket" and page.h1s == ["Resolve ticket"]
    assert page.text.count(ERROR) == 1 and "valid title" not in page.text
    assert (
        "valid description" not in page.text
        and "<script" not in response.content.decode()
    )
    retained = page.form_with_button("Resolve ticket").field("Reply").value
    expected = (raw or "").replace("\r\n", "\n").replace("\r", "\n")
    assert retained == expected.replace("\x00", "\ufffd")
    assert "Own" in page.text and "Body" in page.text and snapshot() == before


@pytest.mark.ac("RQ-3.4", "RQ-3.7", "RQ-2.3", "RQ-1.3")
@pytest.mark.parametrize("reply", ["", "Existing answer"])
def test_resolution_closed_legacy_and_stale_requests_keep_reply(c, make_account, reply):
    form_at(c)
    require_reply()
    Ticket.objects.filter(pk=c.t.pk).update(open=False, reply=reply)
    for method in ("GET", "POST"):
        for raw in ("Replacement", "a\x00b"):
            auth.assert_redirects(read(c, method, data={"reply": raw}), c.detail)
    requester, _ = auth.sign_in_as(make_account, auth.REQUESTER)
    for browser, path in (
        (c.b, c.detail),
        (requester, f"/requester/tickets/{c.t.pk}/"),
    ):
        page = Page(checked_send(browser, "GET", path))
        assert ("Reply" in page.heading_texts) == bool(reply)
        assert "Closed" in page.text and not any("resolve" in u for _, u in page.links)
        assert not reply or reply in page.text


@pytest.mark.ac("RQ-3.5", "RQ-3.7")
@pytest.mark.parametrize(
    "key",
    [
        "0",
        "999999999",
        "foreign",
        "alias",
        "long-alias",
        "low",
        "max",
        "overflow",
        "huge",
        "",
        "-1",
        "1.0",
        "\u0661",
        "\uff11",
    ],
)
def test_resolution_identifier_partitions_precede_validation(c, key):
    form_at(c)
    ids = dict(
        foreign=f"000{c.f.pk}",
        alias=f"000{c.t.pk}",
        huge="9" * 5000,
        low=str(2**63 - 2),
        max=str(2**63 - 1),
        overflow=str(2**63),
        **{"long-alias": "0" * 5000 + str(c.t.pk)},
    )
    if key in ("low", "max"):
        Ticket.objects.create(
            pk=int(ids[key]), workspace=c.u.workspace, title="Bound", description="Body"
        )
    path = f"{BASE}{ids.get(key, key)}/resolve/"
    missing = read(c, path=f"{BASE}999999999/resolve/")
    for method in ("GET", "POST"):
        response = read(c, method, path, data={"reply": "invalid\x00"})
        if key in ("alias", "long-alias", "low", "max"):
            assert (
                response.status_code == 200 and Page(response).title == "Resolve ticket"
            )
        else:
            assert response.status_code == 404 and response.content == missing.content
            assert all(
                text not in response.content for text in (b"Own", b"Body", b"Private")
            )


@pytest.mark.ac("RQ-3.6", "RQ-3.7")
@pytest.mark.parametrize(
    "method,visitor,fault",
    [
        (m, auth.VISITORS[i % 3], None)
        for i, m in enumerate(auth.methods_not_listed("GET", "POST"))
    ]
    + [
        ("POST", v, f)
        for v, f in zip(auth.VISITORS, ("missing", "wrong", "origin"), strict=True)
    ]
    + [(m, v, None) for m in ("GET", "POST") for v in (None, auth.REQUESTER)]
    + [("PUT", None, "missing"), ("DELETE", auth.REQUESTER, "origin")],
)
def test_resolution_csrf_method_access_precedence(
    c, make_account, method, visitor, fault
):
    form_at(c)
    browser, _ = auth.browser_as(make_account, visitor)
    token = auth.csrf_token(browser, visitor)
    browser.cookies["role"] = auth.SUPPORT_OFFICER
    early = fault or method not in ("GET", "POST")
    response = checked_send(
        browser,
        method,
        f"{BASE}999999999/resolve/?role=support_officer",
        None if fault == "missing" else "wrong" if fault == "wrong" else token,
        headers={"Origin": auth.EVIL_ORIGIN} if fault == "origin" else {},
        data={"reply": "invalid\x00", "workspace": c.t.workspace_id},
        forbid=("",) if early else (Ticket._meta.db_table,),
    )
    if fault:
        auth.assert_forbidden(response, auth.FORM_EXPIRED)
    elif early:
        auth.assert_method_not_allowed(response)
    elif visitor is None:
        auth.assert_redirects(response, "/sign-in/")
    else:
        auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)


@pytest.mark.ac("RQ-3.6")
@pytest.mark.parametrize(
    "state", ["before", "expired", "past", "deleted", "role", "workspace"]
)
def test_resolution_next_request_uses_current_account(c, clock, state):
    form_at(c)
    if state in ("before", "expired", "past"):
        clock.set_elapsed(
            timedelta(hours=8, seconds={"before": -1, "expired": 0, "past": 1}[state])
        )
    elif state == "deleted":
        c.u.delete()
    elif state == "role":
        User.objects.filter(pk=c.u.pk).update(role=auth.REQUESTER)
    else:
        User.objects.filter(pk=c.u.pk).update(workspace=c.f.workspace)
    response = read(c, "POST", data={"reply": ""})
    if state in ("expired", "past", "deleted"):
        auth.assert_redirects(response, "/sign-in/")
    elif state == "role":
        auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)
    else:
        assert response.status_code == (404 if state == "workspace" else 200)
        if state == "workspace":
            assert read(c, path=f"{BASE}{c.f.pk}/resolve/").status_code == 200


@pytest.mark.ac("RQ-3.2", "RQ-3.6")
def test_resolution_overrides_cannot_change_target_or_other_fields(c):
    form, before = form_at(c), list(Ticket.objects.values())
    extra = {
        "id": c.f.pk,
        "ticket_id": c.f.pk,
        "workspace": c.f.workspace_id,
        "workspace_id": c.f.workspace_id,
        "role": auth.REQUESTER,
        "open": "true",
        "title": "Changed",
        "description": "Changed",
    }
    c.b.cookies.update({"workspace": str(c.f.workspace_id), "role": auth.REQUESTER})
    headers = {"Role": auth.REQUESTER, "Workspace": str(c.f.workspace_id)}
    response = submit(c, form, "Answer", changes=extra, query=extra, headers=headers)
    auth.assert_redirects(response, c.detail)
    before[0].update(reply="Answer", open=False)
    assert list(Ticket.objects.values()) == before


@pytest.mark.ac("RQ-3.8", "RQ-3.7")
@pytest.mark.parametrize(
    "table", [Session._meta.db_table, User._meta.db_table, Ticket._meta.db_table]
)
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_resolution_read_failure_is_generic_without_retry(c, table, method):
    form_at(c)
    before, reads = snapshot(), []
    c.b.raise_request_exception = False

    def fail(execute, sql, params, many, context):
        if table in sql and sql.lstrip().upper().startswith("SELECT"):
            reads.append(sql)
            raise DatabaseError("Synthetic private resolution failure")
        return execute(sql, params, many, context)

    with connection.execute_wrapper(fail):
        response = auth.send(
            c.b, method, c.path, c.token, data={"reply": "Private answer"}, secure=True
        )
    auth.assert_server_error(
        response, {"title": "Own", "body": "Body", "reply": "Private answer"}
    )
    assert len(reads) == 1 and "Location" not in response and snapshot() == before
    security(response)


@pytest.mark.ac("RQ-3.8", "RQ-3.7")
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_resolution_outage_changes_nothing(c, database_outage, method):
    form_at(c)
    before = snapshot()
    c.b.raise_request_exception = False
    with database_outage():
        response = auth.send(
            c.b, method, c.path, c.token, data={"reply": "Private answer"}, secure=True
        )
    auth.assert_server_error(response, {"reply": "Private answer"})
    assert "Location" not in response and snapshot() == before
    security(response)


@pytest.mark.ac("RQ-3.2", "RQ-3.8")
@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("rejected", ["open", "reply"])
def test_resolution_rejected_write_never_saves_half_the_pair(c, rejected):
    form = form_at(c)
    require_reply()
    before, table = snapshot(), connection.ops.quote_name(Ticket._meta.db_table)
    rule = '"open"' if rejected == "open" else "\"reply\" = ''"
    with connection.cursor() as cursor:
        cursor.execute(
            f"ALTER TABLE {table} ADD CONSTRAINT resolution_test CHECK ({rule})"
        )
    c.b.raise_request_exception = False
    try:
        response = submit(c, form, "Private rejected reply")
        auth.assert_server_error(response, {"reply": "Private rejected reply"})
        assert "Location" not in response and snapshot() == before
    finally:
        with connection.cursor() as cursor:
            cursor.execute(f"ALTER TABLE {table} DROP CONSTRAINT resolution_test")


@pytest.mark.ac("RQ-3.2", "RQ-3.4")
@pytest.mark.django_db(transaction=True)
def test_resolution_overtaken_post_cannot_overwrite_winner(c):
    form, rival = form_at(c), auth.new_browser()
    rival.cookies = c.b.cookies.copy()
    raced = []

    def win():
        try:
            with connection.cursor() as cursor:
                cursor.execute("SET lock_timeout = '2s'")
            auth.assert_redirects(
                form.submit(rival, {"Reply": "Winner"}, secure=True), c.detail
            )
        finally:
            connections.close_all()

    def overtake(execute, sql, params, many, context):
        if not raced and sql.startswith("UPDATE") and Ticket._meta.db_table in sql:
            raced.append(True)
            with ThreadPoolExecutor(max_workers=1) as pool:
                pool.submit(win).result(timeout=10)
        return execute(sql, params, many, context)

    with connection.execute_wrapper(overtake):
        auth.assert_redirects(submit(c, form, "Overtaken"), c.detail)
    c.t.refresh_from_db()
    assert raced == [True] and c.t.reply == "Winner" and not c.t.open


@pytest.mark.ac("RQ-3.7", "RQ-3.2")
@pytest.mark.django_db(transaction=True)
def test_resolution_migration_preserves_rows_and_preceding_version_inserts():
    require_reply()
    workspace, executor = Workspace.objects.create(), MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes("tickets")
    previous = [("tickets", "0001_initial")]
    assert latest != previous, "Missing reply migration."
    executor.migrate(previous)
    try:
        old = executor.loader.project_state(previous).apps.get_model(
            "tickets", "Ticket"
        )
        for is_open in (True, False):
            old.objects.create(
                workspace_id=workspace.pk,
                title="Legacy",
                description="Body",
                open=is_open,
            )
        before = list(old.objects.order_by("pk").values())
        MigrationExecutor(connection).migrate(latest)
        assert list(Ticket.objects.order_by("pk").values()) == [
            dict(row, reply="") for row in before
        ]
        table = connection.ops.quote_name(Ticket._meta.db_table)
        with connection.cursor() as cursor:
            cursor.execute(
                f'INSERT INTO {table} (workspace_id, title, description, "open") '
                "VALUES (%s, %s, %s, %s) RETURNING id",
                [workspace.pk, "Old version", "Body", True],
            )
            inserted = cursor.fetchone()[0]
        assert Ticket.objects.get(pk=inserted).reply == ""
        assert (
            Ticket.objects.create(
                workspace=workspace, title="New", description="Body"
            ).reply
            == ""
        )
    finally:
        MigrationExecutor(connection).migrate(latest)
