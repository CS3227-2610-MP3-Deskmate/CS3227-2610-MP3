"""Create a Requester through the UI and share their first workspace ticket."""

from urllib.parse import urlsplit

import pytest

from deskmate.tests.demo_workspaces import press_create, read_created_page
from deskmate.tests.pages import Page
from deskmate.tests.requester_creations import BUTTON, FORM, read_form, read_success
from deskmate.tests.signing_in import (
    REQUESTER,
    SUPPORT_OFFICER,
    assert_redirects,
    assert_role_page,
    new_browser,
    session_cookie,
    sign_in,
)
from deskmate.tests.test_workspace_labels import assert_workspace
from e2e.test_support_officer_journey import officer_browser, support_path


def follow_link(browser, page, caption):
    """Follow the page's single rendered link with this caption."""
    urls = [url for text, url in page.links if text == caption]
    assert len(urls) == 1, (caption, page.links)
    return browser.get(urls[0], secure=True)


@pytest.mark.ac(
    "ACC-1.1",
    "ACC-1.2",
    "ACC-2.1",
    "ACC-2.2",
    "ACC-5.1",
    "ACC-5.2",
    "RQ-1.1",
    "RQ-1.2",
    "RQ-1.3",
    "RQ-2.1",
    "RQ-2.2",
)
@pytest.mark.django_db(transaction=True)
def test_requester_creation_journey_preserves_code_and_shares_new_requesters_ticket(
    fast_hashing, clock
):
    accounts = read_created_page(press_create(new_browser(), secure=True))
    account = next(user for user in accounts if user.role == SUPPORT_OFFICER)
    code = account.username.split("-", 1)[1]
    officer = officer_browser(account.username, account.password)
    officer_session = session_cookie(officer)
    landing = officer.get("/support/", secure=True)
    assert_workspace(landing, code)

    creation = follow_link(officer, Page(landing), FORM)
    form_page = read_form(creation, code=code)
    created = form_page.form_with_button(BUTTON).submit(
        officer, button=BUTTON, secure=True
    )
    username = f"requester3-{code}"
    password = read_success(created, username, code=code)
    officer_landing = follow_link(officer, Page(created), "Support Officer")
    assert_workspace(officer_landing, code)
    assert_role_page(officer_landing, SUPPORT_OFFICER, account.username)
    assert officer_session and session_cookie(officer) == officer_session

    requester = new_browser()
    signed_in = sign_in(requester, username, password)
    assert_redirects(signed_in, "/requester/")
    requester_landing = requester.get(signed_in.url, secure=True)
    assert_role_page(requester_landing, REQUESTER, username)
    assert_workspace(requester_landing, code)
    listed = follow_link(requester, Page(requester_landing), "Tickets")
    assert_workspace(listed, code)
    new_ticket = follow_link(requester, Page(listed), "New ticket")
    assert_workspace(new_ticket, code)
    title = "Monitor for the new teammate"
    description = "The new desk monitor does not turn on."
    submitted = (
        Page(new_ticket)
        .form_with_button("Submit ticket")
        .submit(
            requester,
            {"Title": title, "Description": description},
            button="Submit ticket",
            secure=True,
        )
    )
    assert submitted.status_code == 302
    requester_ticket = requester.get(submitted.url, secure=True)
    assert_workspace(requester_ticket, code)
    assert Page(requester_ticket).h1s == ["Ticket"]
    assert title in Page(requester_ticket).text
    assert description in Page(requester_ticket).text

    officer_list = follow_link(officer, Page(officer_landing), "Tickets")
    assert_workspace(officer_list, code)
    ticket_urls = [url for text, url in Page(officer_list).links if text == title]
    assert len(ticket_urls) == 1
    assert urlsplit(ticket_urls[0]).path == support_path(submitted.url)
    officer_ticket = follow_link(officer, Page(officer_list), title)
    assert_workspace(officer_ticket, code)
    assert Page(officer_ticket).h1s == ["Ticket"]
    assert title in Page(officer_ticket).text
    assert description in Page(officer_ticket).text
    assert "Open" in Page(officer_ticket).text.split()
    assert session_cookie(officer) == officer_session
    final_landing = officer.get("/support/", secure=True)
    assert_role_page(final_landing, SUPPORT_OFFICER, account.username)
    assert_workspace(final_landing, code)
