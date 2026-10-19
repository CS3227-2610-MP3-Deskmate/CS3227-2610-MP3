"""The Requester's journey through the merged product, from demo workspace to
sign-out, plus the workspace boundary around tickets and articles."""

from urllib.parse import urlsplit

import pytest

from deskmate.accounts.models import Workspace
from deskmate.tests.demo_workspaces import press_create
from deskmate.tests.pages import ORIGIN, Page
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    SUPPORT_OFFICER,
    assert_redirects,
    assert_role_page,
    assert_signed_out,
    get_sign_in_page,
    new_browser,
    sign_in,
    sign_in_as,
)

pytestmark = pytest.mark.django_db
SIGN_IN = "/sign-in/"
REQUESTER_PAGE = "/requester/"
TICKETS = "/requester/tickets/"
ARTICLES = "/requester/articles/"


def demo_accounts(browser):
    """Create a demo workspace as a visitor does and return its three accounts."""
    page = get_sign_in_page(browser)
    response = press_create(browser, page)
    assert response.status_code == 200
    rows = Page(response).tables[0][1:]
    return [[text for _, text in row] for row in rows]


def role_page_for(username, password, role):
    """Sign in a fresh browser and return it, after checking its role page."""
    browser = new_browser()
    response = sign_in(browser, username, password)
    assert_redirects(response, "/requester/" if role == REQUESTER else "/support/")
    assert_role_page(
        browser.get("/requester/" if role == REQUESTER else "/support/"),
        role,
        username,
    )
    return browser


def path_of(response):
    """Return the path a successful form redirect names."""
    return urlsplit(response.url).path


@pytest.mark.ac("ACC-2.2", "ACC-1.1", "ACC-1.2", "RQ-1.1", "RQ-1.2", "RQ-1.3")
def test_requester_journey_from_demo_workspace_to_sign_out():
    creator = new_browser()
    accounts = demo_accounts(creator)
    requester_name, _, requester_password = next(
        account for account in accounts if account[0].startswith("requester1-")
    )
    officer_name, _, officer_password = next(
        account for account in accounts if account[0].startswith("support1-")
    )

    requester = role_page_for(requester_name, requester_password, REQUESTER)
    role_page = Page(requester.get(REQUESTER_PAGE, secure=True))
    assert ("Tickets", f"{ORIGIN}{TICKETS}") in role_page.links
    assert ("Knowledge base", f"{ORIGIN}{ARTICLES}") in role_page.links

    empty = Page(requester.get(TICKETS, secure=True))
    assert empty.title == "Tickets" and empty.h1s == ["Tickets"]
    assert "No tickets yet." in empty.text
    assert ("New ticket", f"{ORIGIN}{TICKETS}new/") in empty.links
    assert ("Requester", f"{ORIGIN}{REQUESTER_PAGE}") in empty.links

    form_page = Page(requester.get(f"{TICKETS}new/", secure=True))
    assert form_page.title == "New ticket" and form_page.h1s == ["New ticket"]
    form = form_page.form_with_button("Submit ticket")
    assert form.field("Title").tag == "input"
    assert form.field("Description").tag == "textarea"
    response = form.submit(
        requester,
        {
            "Title": "Printer on fire",
            "Description": "Line one\nLine two\nhttps://evil.example",
        },
        secure=True,
    )
    ticket_path = path_of(response)
    assert ticket_path.startswith(TICKETS)

    ticket = Page(requester.get(ticket_path, secure=True))
    assert ticket.title == "Ticket" and ticket.h1s == ["Ticket"]
    assert "Printer on fire" in ticket.text
    assert "Line one Line two https://evil.example" in ticket.text
    assert "Open" in ticket.text.split()
    assert ("Tickets", f"{ORIGIN}{TICKETS}") in ticket.links
    assert not any(control.is_field() for control in ticket.controls)
    assert not any("resolve" in url for _, url in ticket.links)
    assert "Reply" not in ticket.heading_texts

    listed = Page(requester.get(TICKETS, secure=True))
    assert ("Printer on fire", f"{ORIGIN}{ticket_path}") in listed.links

    officer = role_page_for(officer_name, officer_password, SUPPORT_OFFICER)
    ticket_id = ticket_path.rstrip("/").rsplit("/", 1)[1]
    support_ticket = f"/support/tickets/{ticket_id}/"
    resolve_page = Page(officer.get(f"{support_ticket}resolve/", secure=True))
    assert resolve_page.title == "Resolve ticket"
    resolution = "Restart the printer.\nThen check the paper tray."
    response = resolve_page.form_with_button("Resolve ticket").submit(
        officer, {"Reply": resolution}, secure=True
    )
    assert_redirects(response, support_ticket)

    closed = Page(requester.get(ticket_path, secure=True))
    assert "Closed" in closed.text.split()
    assert "Reply" in closed.heading_texts
    assert "Restart the printer. Then check the paper tray." in closed.text
    assert not any(control.is_field() for control in closed.controls)
    assert not any("resolve" in url for _, url in closed.links)

    authoring = Page(officer.get("/support/articles/new/", secure=True))
    article = authoring.form_with_button("Save article").submit(
        officer,
        {"Title": "Printer guide", "Body": "First check the cable.\nThen restart."},
        secure=True,
    )
    article_id = urlsplit(article.url).path.split("/")[3]
    article_path = f"{ARTICLES}{article_id}/"

    reading_list = Page(requester.get(ARTICLES, secure=True))
    assert reading_list.title == "Knowledge base"
    assert reading_list.h1s == ["Knowledge base"]
    assert ("Printer guide", f"{ORIGIN}{article_path}") in reading_list.links
    assert ("Requester", f"{ORIGIN}{REQUESTER_PAGE}") in reading_list.links
    assert not any(text == "New article" for text, _ in reading_list.links)

    article_page = Page(requester.get(article_path, secure=True))
    assert article_page.title == "Article" and article_page.h1s == ["Article"]
    assert "Printer guide" in article_page.text
    assert "First check the cable. Then restart." in article_page.text
    assert ("Knowledge base", f"{ORIGIN}{ARTICLES}") in article_page.links

    page = Page(requester.get(REQUESTER_PAGE, secure=True))
    response = page.form_with_button("Sign out").submit(
        requester, button="Sign out", secure=True
    )
    assert_redirects(response, SIGN_IN)
    assert_signed_out(requester)


@pytest.mark.ac("RQ-1.7", "KB-2.3", "RQ-1.3", "KB-2.2")
def test_requester_cannot_read_another_workspaces_ticket_or_article(make_account):
    owner, _ = sign_in_as(make_account, REQUESTER)
    officer, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    outsider_account = make_account("outsider", PASSWORD, REQUESTER)
    outsider_account.workspace = Workspace.objects.create()
    outsider_account.save()
    outsider = new_browser()
    assert_redirects(sign_in(outsider, "outsider", PASSWORD), REQUESTER_PAGE)

    ticket = (
        Page(owner.get(f"{TICKETS}new/", secure=True))
        .form_with_button("Submit ticket")
        .submit(
            owner,
            {"Title": "Owner only", "Description": "Private ticket body"},
            secure=True,
        )
    )
    ticket_path = path_of(ticket)
    article = (
        Page(officer.get("/support/articles/new/", secure=True))
        .form_with_button("Save article")
        .submit(
            officer,
            {"Title": "Owner guide", "Body": "Private article body"},
            secure=True,
        )
    )
    article_path = f"{ARTICLES}{urlsplit(article.url).path.split('/')[3]}/"

    for path in (ticket_path, article_path):
        response = outsider.get(path, secure=True)
        assert response.status_code == 404
        body = response.content
        assert b"Owner only" not in body
        assert b"Private ticket body" not in body
        assert b"Owner guide" not in body
        assert b"Private article body" not in body
