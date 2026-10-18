"""RQ-1.3/RQ-3.7: Requesters read saved replies without resolution controls."""

import re

import pytest

from deskmate.accounts.models import Workspace
from deskmate.tests.pages import Page
from deskmate.tests.signing_in import REQUESTER, SUPPORT_OFFICER, sign_in_as
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.django_db
BASE = "/requester/tickets/"
MISSING = f"{BASE}999999999/"


@pytest.fixture
def requester_and_officer(make_account):
    """A Requester and a Support Officer in the same workspace."""
    browser, requester = sign_in_as(make_account, REQUESTER)
    _, officer = sign_in_as(make_account, SUPPORT_OFFICER)
    assert requester.workspace_id == officer.workspace_id
    return browser, requester


def ticket_page(browser, ticket):
    """Open a Requester ticket page and return its response and parsed page."""
    response = browser.get(f"{BASE}{ticket.pk}/", secure=True)
    assert response.status_code == 200
    return response, Page(response)


@pytest.mark.ac("RQ-1.3", "RQ-3.7")
def test_ticket_replies_requester_sees_closed_reply_as_plain_text(
    requester_and_officer,
):
    browser, requester = requester_and_officer
    reply = "Printer is fixed.\nPlease restart it."
    ticket = Ticket.objects.create(
        workspace=requester.workspace,
        title="Printer",
        description="It jams",
        open=False,
        reply=reply,
    )
    before = list(Ticket.objects.order_by("pk").values())

    response, page = ticket_page(browser, ticket)
    html = response.content.decode()
    assert page.title == "Ticket" and page.h1s == ["Ticket"]
    assert "Printer" in page.text and "It jams" in page.text
    assert "Closed" in page.text.split()
    assert page.heading_texts.count("Reply") == 1
    assert "Printer is fixed. Please restart it." in page.text
    rendered_reply = (
        r"<h2>Reply</h2>\s*<p>Printer is fixed\.<br>\s*Please restart it\.</p>"
    )
    assert re.search(rendered_reply, html)

    assert not any(control.is_field() for control in page.controls)
    assert not any((control.name or "").lower() == "reply" for control in page.controls)
    assert not any(control.caption == "Resolve ticket" for control in page.controls)
    assert not any(text == "Resolve ticket" for text, _ in page.links)
    assert not any("/resolve/" in url for _, url in page.links)

    ticket_page(browser, ticket)
    assert list(Ticket.objects.order_by("pk").values()) == before


@pytest.mark.ac("RQ-1.3", "RQ-3.7")
def test_ticket_replies_requester_empty_reply_has_no_heading_or_placeholder(
    requester_and_officer,
):
    browser, requester = requester_and_officer
    ticket = Ticket.objects.create(
        workspace=requester.workspace,
        title="Printer",
        description="It jams",
        open=False,
        reply="",
    )

    response, page = ticket_page(browser, ticket)
    html = response.content.decode()
    assert "Closed" in page.text.split()
    assert "Reply" not in page.heading_texts
    assert "Reply" not in page.text
    assert "No reply" not in page.text and "Not resolved" not in page.text
    assert "<h2>Reply</h2>" not in html


@pytest.mark.ac("RQ-1.3", "RQ-1.7")
def test_ticket_replies_requester_cannot_read_another_workspace(
    requester_and_officer,
):
    browser, _ = requester_and_officer
    foreign = Ticket.objects.create(
        workspace=Workspace.objects.create(),
        title="Private title",
        description="Private body",
        open=False,
        reply="Private reply\nSecond line",
    )

    response = browser.get(f"{BASE}{foreign.pk}/", secure=True)
    assert response.status_code == 404
    assert response.content == browser.get(MISSING, secure=True).content
    for text in (b"Private title", b"Private body", b"Private reply", b"Second line"):
        assert text not in response.content
