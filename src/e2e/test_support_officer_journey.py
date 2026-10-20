"""The Support Officer's journey through the merged product, from demo workspace
to sign-out, plus the workspace boundary around tickets and articles."""

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
SUPPORT_PAGE = "/support/"
TICKETS = "/support/tickets/"
ARTICLES = "/support/articles/"
RESET = "/support/reset-requester-password/"


def demo_accounts(browser):
    """Create a demo workspace as a visitor does and return its three accounts."""
    page = get_sign_in_page(browser)
    response = press_create(browser, page)
    assert response.status_code == 200
    rows = Page(response).tables[0][1:]
    return [[text for _, text in row] for row in rows]


def officer_browser(username, password):
    """Sign in a fresh browser as a Support Officer and return it."""
    browser = new_browser()
    assert_redirects(sign_in(browser, username, password), SUPPORT_PAGE)
    assert_role_page(browser.get(SUPPORT_PAGE), SUPPORT_OFFICER, username)
    return browser


def path_of(response):
    """Return the path a successful form redirect names."""
    return urlsplit(response.url).path


def submit_ticket(requester, title, description):
    """Submit a ticket through the Requester's form and return its path."""
    form_page = Page(requester.get("/requester/tickets/new/", secure=True))
    response = form_page.form_with_button("Submit ticket").submit(
        requester,
        {"Title": title, "Description": description},
        secure=True,
    )
    return path_of(response)


def support_path(requester_path):
    """Return the Support Officer path for a Requester ticket path."""
    ticket_id = requester_path.rstrip("/").rsplit("/", 1)[1]
    return f"{TICKETS}{ticket_id}/"


@pytest.mark.ac(
    "ACC-2.2",
    "ACC-1.1",
    "ACC-1.2",
    "ACC-4.1",
    "ACC-4.2",
    "RQ-2.1",
    "RQ-2.2",
    "RQ-2.3",
    "RQ-3.1",
    "RQ-3.2",
    "RQ-3.7",
    "KB-1.1",
    "KB-1.2",
    "KB-1.3",
)
def test_support_officer_journey_from_demo_workspace_to_sign_out():
    creator = new_browser()
    accounts = demo_accounts(creator)
    officer_name, _, officer_password = next(
        account for account in accounts if account[0].startswith("support1-")
    )
    requester_name, _, requester_password = next(
        account for account in accounts if account[0].startswith("requester1-")
    )

    officer = officer_browser(officer_name, officer_password)
    role_page = Page(officer.get(SUPPORT_PAGE, secure=True))
    assert ("Tickets", f"{ORIGIN}{TICKETS}") in role_page.links
    assert ("Knowledge base", f"{ORIGIN}{ARTICLES}") in role_page.links
    assert ("Reset Requester password", f"{ORIGIN}{RESET}") in role_page.links

    empty = Page(officer.get(TICKETS, secure=True))
    assert empty.title == "Tickets" and empty.h1s == ["Tickets"]
    assert "No tickets yet." in empty.text
    assert ("Support Officer", f"{ORIGIN}{SUPPORT_PAGE}") in empty.links
    assert not any(text == "New ticket" for text, _ in empty.links)

    requester = new_browser()
    assert_redirects(
        sign_in(requester, requester_name, requester_password), "/requester/"
    )
    requester_path = submit_ticket(
        requester,
        "Printer on fire",
        "Line one\nLine two\nhttps://evil.example",
    )
    ticket_path = support_path(requester_path)

    listed = Page(officer.get(TICKETS, secure=True))
    assert ("Printer on fire", f"{ORIGIN}{ticket_path}") in listed.links

    ticket = Page(officer.get(ticket_path, secure=True))
    assert ticket.title == "Ticket" and ticket.h1s == ["Ticket"]
    assert "Printer on fire" in ticket.text
    assert "Line one Line two https://evil.example" in ticket.text
    assert "Open" in ticket.text.split()
    assert "Reply" not in ticket.heading_texts
    assert ("Tickets", f"{ORIGIN}{TICKETS}") in ticket.links
    assert ("Resolve ticket", f"{ORIGIN}{ticket_path}resolve/") in ticket.links
    assert not any(control.is_field() for control in ticket.controls)

    resolve_page = Page(officer.get(f"{ticket_path}resolve/", secure=True))
    assert resolve_page.title == "Resolve ticket"
    assert resolve_page.h1s == ["Resolve ticket"]
    assert "Printer on fire" in resolve_page.text
    form = resolve_page.form_with_button("Resolve ticket")
    assert form.field("Reply").tag == "textarea"
    assert form.field("Reply").value == ""
    assert ("Ticket", f"{ORIGIN}{ticket_path}") in resolve_page.links
    response = form.submit(
        officer,
        {"Reply": "Restart the printer.\nThen check the paper tray."},
        secure=True,
    )
    assert_redirects(response, ticket_path)

    closed = Page(officer.get(ticket_path, secure=True))
    assert "Closed" in closed.text.split()
    assert "Reply" in closed.heading_texts
    assert "Restart the printer. Then check the paper tray." in closed.text
    assert not any("resolve" in url for _, url in closed.links)

    article_list = Page(officer.get(ARTICLES, secure=True))
    assert article_list.title == "Knowledge base"
    assert article_list.h1s == ["Knowledge base"]
    assert "No articles yet." in article_list.text
    assert ("New article", f"{ORIGIN}{ARTICLES}new/") in article_list.links
    assert ("Support Officer", f"{ORIGIN}{SUPPORT_PAGE}") in article_list.links

    creation = Page(officer.get(f"{ARTICLES}new/", secure=True))
    assert creation.title == "New article" and creation.h1s == ["New article"]
    assert creation.form_with_button("Save article").field("Title").value == ""
    created = creation.form_with_button("Save article").submit(
        officer,
        {"Title": "Printer guide", "Body": "First check the cable.\nThen restart."},
        secure=True,
    )
    edit_path = path_of(created)
    assert edit_path.startswith(ARTICLES) and edit_path.endswith("/edit/")

    edit = Page(officer.get(edit_path, secure=True))
    assert edit.title == "Edit article" and edit.h1s == ["Edit article"]
    form = edit.form_with_button("Save article")
    assert form.field("Title").value == "Printer guide"
    assert form.field("Body").value == "First check the cable.\nThen restart."
    assert_redirects(
        form.submit(
            officer,
            {"Title": "Printer guide", "Body": "Check the cable.\nThen restart twice."},
            secure=True,
        ),
        edit_path,
    )

    edit_list = Page(officer.get(ARTICLES, secure=True))
    assert ("Printer guide", f"{ORIGIN}{edit_path}") in edit_list.links
    edited = Page(officer.get(edit_path, secure=True))
    assert edited.form_with_button("Save article").field("Body").value == (
        "Check the cable.\nThen restart twice."
    )

    reset = Page(officer.get(RESET, secure=True))
    assert reset.title == "Reset Requester password"
    assert reset.h1s == ["Reset Requester password"]
    assert reset.form_with_button("Reset password").field("Username").value == ""
    assert ("Support Officer", f"{ORIGIN}{SUPPORT_PAGE}") in reset.links
    success = Page(
        reset.form_with_button("Reset password").submit(
            officer, {"Username": requester_name}, secure=True
        )
    )
    assert success.title == "Requester password reset"
    assert success.h1s == ["Requester password reset"]
    assert success.tables[0][0] == [("th", "Username"), ("th", "Password")]
    assert success.tables[0][1][0] == ("td", requester_name)
    new_password = success.tables[0][1][1][1]
    assert len(new_password) == 16

    reset_requester = new_browser()
    assert_redirects(
        sign_in(reset_requester, requester_name, new_password), "/requester/"
    )

    page = Page(officer.get(SUPPORT_PAGE, secure=True))
    response = page.form_with_button("Sign out").submit(
        officer, button="Sign out", secure=True
    )
    assert_redirects(response, SIGN_IN)
    assert_signed_out(officer)


@pytest.mark.ac("RQ-2.4", "RQ-3.5", "KB-1.7")
def test_support_officer_cannot_reach_another_workspaces_records(make_account):
    officer, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    outsider_account = make_account("outsider", PASSWORD, SUPPORT_OFFICER)
    outsider_account.workspace = Workspace.objects.create()
    outsider_account.save()
    outsider = new_browser()
    assert_redirects(sign_in(outsider, "outsider", PASSWORD), SUPPORT_PAGE)

    owner, _ = sign_in_as(make_account, REQUESTER)
    ticket_path = submit_ticket(owner, "Owner only", "Private ticket body")
    article = (
        Page(officer.get(f"{ARTICLES}new/", secure=True))
        .form_with_button("Save article")
        .submit(
            officer,
            {"Title": "Owner guide", "Body": "Private article body"},
            secure=True,
        )
    )
    article_path = path_of(article)

    for path in (support_path(ticket_path), f"{support_path(ticket_path)}resolve/"):
        response = outsider.get(path, secure=True)
        assert response.status_code == 404
        assert b"Owner only" not in response.content
        assert b"Private ticket body" not in response.content
    response = outsider.get(article_path, secure=True)
    assert response.status_code == 404
    assert b"Owner guide" not in response.content
    assert b"Private article body" not in response.content
