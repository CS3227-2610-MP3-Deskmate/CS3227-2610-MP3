"""ACC-2.9, with ACC-2.2: the sample articles and tickets that a new demo
workspace holds, how both roles' lists and pages show them, and that they are
then ordinary records of that workspace alone.

Every expected title, body, description, open value and reply is ACC-2.9's,
as SAMPLE_ARTICLES and SAMPLE_TICKETS in demo_workspaces.py hold them.
`assert_created` checks that each creation stores exactly those, in order, in
its new workspace and nowhere else.
"""

from unittest.mock import Mock

import pytest

from deskmate.knowledge.models import Article
from deskmate.tests import test_llm_gateway as llm
from deskmate.tests.demo_workspaces import (
    SAMPLE_ARTICLES,
    SAMPLE_TICKETS,
    assert_created,
    found_in,
    listed_items,
    press_create,
    stored_state,
    workspace_of,
)
from deskmate.tests.pages import ORIGIN, Page
from deskmate.tests.signing_in import (
    REQUESTER,
    ROLE_PAGES,
    SUPPORT_OFFICER,
    assert_redirects,
    new_browser,
    send,
    sign_in,
    sign_in_as,
)
from deskmate.tests.test_support_tickets import page_at
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.usefixtures("fast_hashing")
# The gateway tests' fake provider, which records every request sent to it.
provider = llm.provider

# Each role's knowledge-base and ticket lists (KB-1.1, KB-2.1, RQ-1.1, RQ-2.1):
# the list's path, and a pattern of the paths its items link to whose group is
# the item's id.
ARTICLE_LISTS = {
    SUPPORT_OFFICER: ("/support/articles/", r"/support/articles/([0-9]+)/edit/"),
    REQUESTER: ("/requester/articles/", r"/requester/articles/([0-9]+)/"),
}
TICKET_LISTS = {
    SUPPORT_OFFICER: ("/support/tickets/", r"/support/tickets/([0-9]+)/"),
    REQUESTER: ("/requester/tickets/", r"/requester/tickets/([0-9]+)/"),
}
# What a list shows when it has no items, and KB-1.5's duplicate-title error.
NO_ARTICLES = "No articles yet."
NO_TICKETS = "No tickets yet."
DUPLICATE = "An article with this title already exists."
# Titles that a new article in a demo workspace duplicates under KB-1.5's
# rule: ACC-2.9's example, and the other sample's title in another case.
SAMPLE_DUPLICATES = [
    pytest.param("connect to the office wi-fi", id="acc-2.9-example"),
    pytest.param("FIX A PRINTER THAT WILL NOT PRINT", id="other-sample-upper-case"),
]
ARTICLE_TITLES = [sample.title for sample in SAMPLE_ARTICLES]
TICKET_TITLES = [sample.title for sample in SAMPLE_TICKETS]
# What a Support Officer writes when resolving a sample ticket or editing a
# sample article.
REPLY = "Forget the office network on your laptop, then connect again."
EDITED_BODY = "Choose the office network and enter the password on the board."
# Every text of ACC-2.9's samples, by the sample's number and the field.
SAMPLE_TEXTS = {
    f"sample {number} {field}": text
    for number, sample in enumerate((*SAMPLE_ARTICLES, *SAMPLE_TICKETS), 1)
    for field, text in sample._asdict().items()
    if isinstance(text, str) and text
}
# An id no article or ticket has, whose generic 404 a request for another
# workspace's record must match (RQ-1.7, RQ-2.4, RQ-3.5, KB-1.7, KB-2.3).
UNKNOWN = 999999999


def create_workspace(browser):
    """Press Create demo workspace in `browser`, and check with assert_created
    that the new workspace holds exactly the samples of ACC-2.9.

    Returns the accounts the page shows and their workspace's id.
    """
    before = stored_state()
    accounts = assert_created(press_create(browser), before)
    return accounts, workspace_of(accounts[0])


def signed_in(account):
    """Return a new browser signed in as `account`, an Account the page showed."""
    browser = new_browser()
    response = sign_in(browser, account.username, account.password)
    assert_redirects(response, ROLE_PAGES[account.role])
    return browser


def open_page(browser, path):
    """Open `path` in `browser`, check it is served, and return the page."""
    response = browser.get(path, secure=True)
    assert response.status_code == 200, f"GET {path}: {response.status_code}"
    return Page(response)


def ids_in(workspace):
    """Return the ids of `workspace`'s articles and of its tickets, each in
    creation order."""
    return tuple(
        list(
            model.objects.filter(workspace_id=workspace)
            .order_by("pk")
            .values_list("pk", flat=True)
        )
        for model in (Article, Ticket)
    )


def assert_lists(browser, role, articles, tickets):
    """Assert `browser`, signed in with `role`, sees exactly `articles` on its
    knowledge-base list and `tickets` on its ticket list, each a list of the
    titles and ids of the items in the order shown, and the empty list's text
    only when there are none."""
    for (path, pattern), items, empty in (
        (ARTICLE_LISTS[role], articles, NO_ARTICLES),
        (TICKET_LISTS[role], tickets, NO_TICKETS),
    ):
        page = open_page(browser, path)
        assert listed_items(page, pattern) == items, f"{path} lists other items."
        assert (empty in page.text) == (not items), page.text


def titles_with(titles, ids):
    """Return each of `titles` with the id in `ids` at the same place."""
    return list(zip(titles, ids, strict=True))


def sample_ids(browser, role):
    """Return the ids of the sample articles and of the sample tickets that
    `browser`, signed in with `role`, sees on its lists, after checking each
    list shows exactly ACC-2.9's samples, in order."""
    ids = []
    for (path, pattern), titles in (
        (ARTICLE_LISTS[role], ARTICLE_TITLES),
        (TICKET_LISTS[role], TICKET_TITLES),
    ):
        items = listed_items(open_page(browser, path), pattern)
        assert [title for title, _ in items] == titles, f"{path} lists other items."
        ids.append([pk for _, pk in items])
    return ids


@pytest.mark.ac("ACC-2.9")
def test_demo_samples_listed_in_creation_order_on_every_users_lists(db, browser):
    accounts, workspace = create_workspace(browser)
    article_ids, ticket_ids = ids_in(workspace)
    articles = titles_with(ARTICLE_TITLES, article_ids)
    tickets = titles_with(TICKET_TITLES, ticket_ids)
    # Both Requesters and the Support Officer: articles 1, 2 and tickets 3, 4,
    # 5, earliest first.
    for account in accounts:
        assert_lists(signed_in(account), account.role, articles, tickets)


@pytest.mark.ac("ACC-2.9")
def test_demo_samples_pages_show_exact_text_and_closed_tickets_reply(db, browser):
    accounts, workspace = create_workspace(browser)
    article_ids, ticket_ids = ids_in(workspace)
    requester, officer = signed_in(accounts[0]), signed_in(accounts[2])
    for sample, pk in zip(SAMPLE_ARTICLES, article_ids, strict=True):
        page = open_page(requester, f"/requester/articles/{pk}/")
        assert page.title == "Article" and page.h1s == ["Article"]
        assert sample.title in page.text and sample.body in page.text
        edit = open_page(officer, f"/support/articles/{pk}/edit/")
        form = edit.form_with_button("Save article")
        assert form.field("Title").value == sample.title
        assert form.field("Body").value == sample.body
    for sample, pk in zip(SAMPLE_TICKETS, ticket_ids, strict=True):
        shown, not_shown = ("Open", "Closed") if sample.open else ("Closed", "Open")
        detail = f"/support/tickets/{pk}/"
        # page_at also checks the Support Officer's page offers highlighting
        # its key sentences and changes no ticket.
        support = page_at(officer, detail)
        for page in (open_page(requester, f"/requester/tickets/{pk}/"), support):
            assert page.title == "Ticket" and page.h1s == ["Ticket"]
            assert sample.title in page.text and sample.description in page.text
            words = page.text.split()
            assert shown in words and not_shown not in words, page.text
            assert ("Reply" in page.heading_texts) == bool(sample.reply)
            assert not sample.reply or sample.reply in page.text
        resolve = ("Resolve ticket", f"{ORIGIN}{detail}resolve/")
        assert (resolve in support.links) == sample.open


@pytest.mark.ac("ACC-2.9", "ACC-2.2")
def test_demo_samples_each_workspace_has_own_copies_changed_independently(db, browser):
    first, first_workspace = create_workspace(browser)
    # assert_created also checks the second creation adds its own copies and
    # leaves the first workspace's copies as they were.
    second, second_workspace = create_workspace(new_browser())
    first_articles, first_tickets = ids_in(first_workspace)
    second_articles, second_tickets = ids_in(second_workspace)
    officer = signed_in(second[2])
    before = stored_state()
    # The second workspace's Support Officer resolves its copy of ticket 4 and
    # edits the body of its copy of article 2.
    ticket = second_tickets[1]
    detail = f"/support/tickets/{ticket}/"
    form = open_page(officer, f"{detail}resolve/").form_with_button("Resolve ticket")
    assert_redirects(form.submit(officer, {"Reply": REPLY}, secure=True), detail)
    article = second_articles[1]
    edit = f"/support/articles/{article}/edit/"
    form = open_page(officer, edit).form_with_button("Save article")
    typed = {"Title": SAMPLE_ARTICLES[1].title, "Body": EDITED_BODY}
    assert_redirects(form.submit(officer, typed, secure=True), edit)
    # Only those two records changed; the first workspace's copies did not.
    after = stored_state()
    tickets = dict(before.tickets)
    tickets[ticket] = {**tickets[ticket], "open": False, "reply": REPLY}
    articles = dict(before.articles)
    articles[article] = {**articles[article], "body": EDITED_BODY}
    assert after.tickets == tickets
    assert after.articles == articles
    other = signed_in(first[2])
    page = page_at(other, f"/support/tickets/{first_tickets[1]}/")
    assert "Open" in page.text.split() and "Reply" not in page.heading_texts
    edit = open_page(other, f"/support/articles/{first_articles[1]}/edit/")
    form = edit.form_with_button("Save article")
    assert form.field("Body").value == SAMPLE_ARTICLES[1].body


@pytest.mark.ac(
    "ACC-2.9", "ACC-2.2", "RQ-1.7", "RQ-2.4", "RQ-3.5", "RQ-4.5", "KB-1.7", "KB-2.3"
)
def test_demo_samples_other_workspaces_copies_by_id_get_generic_404(
    db, browser, provider, monkeypatch
):
    first, _ = create_workspace(browser)
    second, _ = create_workspace(new_browser())
    # The first workspace's sample ids, as its own Support Officer's lists show.
    articles, tickets = sample_ids(signed_in(first[2]), SUPPORT_OFFICER)
    officer, requester = signed_in(second[2]), signed_in(second[0])
    # The second workspace's Support Officer fills in the forms for its own
    # copies of ticket 4 and article 2, each with a valid CSRF token, and sends
    # them to the first workspace's copies instead.
    own_articles, own_tickets = sample_ids(officer, SUPPORT_OFFICER)
    detail = f"/support/tickets/{own_tickets[1]}/"
    page = open_page(officer, f"{detail}resolve/")
    reply = page.form_with_button("Resolve ticket").data({"Reply": REPLY})
    highlight = open_page(officer, detail).form_with_button("Highlight key sentences")
    page = open_page(officer, f"/support/articles/{own_articles[1]}/edit/")
    save = page.form_with_button("Save article").data({"Body": EDITED_BODY})
    # Each request: who sends it, its method and route, with {} for the id, its
    # form data, and the first workspace's ids it is sent for.
    ticket, article = "/support/tickets/{}/", "/support/articles/{}/edit/"
    attacks = (
        (officer, "GET", ticket, None, tickets),
        (officer, "GET", f"{ticket}resolve/", None, tickets),
        (officer, "POST", f"{ticket}resolve/", reply, tickets),
        (officer, "POST", f"{ticket}key-sentences/", highlight.data(), tickets),
        (officer, "GET", article, None, articles),
        (officer, "POST", article, save, articles),
        (requester, "GET", "/requester/tickets/{}/", None, tickets),
        (requester, "GET", "/requester/articles/{}/", None, articles),
    )
    gateway = Mock(side_effect=AssertionError("A foreign ticket reached the gateway."))
    monkeypatch.setattr("deskmate.tickets.views.llm_gateway.call", gateway)
    before = stored_state()
    for user, method, route, data, ids in attacks:
        # The generic 404 of an id that does not exist, which each must match.
        missing = send(user, method, route.format(UNKNOWN), data=data, secure=True)
        for pk in ids:
            response = send(user, method, route.format(pk), data=data, secure=True)
            request = f"{method} {route.format(pk)}"
            assert response.status_code == missing.status_code == 404, request
            assert response.content == missing.content, request
            assert not found_in(response.content.decode(), SAMPLE_TEXTS), request
    assert stored_state() == before
    gateway.assert_not_called()
    assert provider.requests == [] and llm.attempts() == 0 and llm.events() == []


@pytest.mark.ac("ACC-2.9")
def test_demo_samples_records_created_later_list_after_them(db, browser):
    accounts, workspace = create_workspace(browser)
    requester, officer = signed_in(accounts[1]), signed_in(accounts[2])
    # Titles that sort before every sample's, so a list in title order fails.
    ticket = {"Title": "Access card stopped working", "Description": "It beeps."}
    form = open_page(requester, "/requester/tickets/new/").form_with_button(
        "Submit ticket"
    )
    response = form.submit(requester, ticket, secure=True)
    assert response.status_code == 302, response.status_code
    article = {"Title": "Add a shared calendar", "Body": "Ask the help desk."}
    form = open_page(officer, "/support/articles/new/").form_with_button("Save article")
    response = form.submit(officer, article, secure=True)
    assert response.status_code == 302, response.status_code
    article_ids, ticket_ids = ids_in(workspace)
    articles = titles_with([*ARTICLE_TITLES, article["Title"]], article_ids)
    tickets = titles_with([*TICKET_TITLES, ticket["Title"]], ticket_ids)
    for role, user in ((REQUESTER, requester), (SUPPORT_OFFICER, officer)):
        assert_lists(user, role, articles, tickets)


@pytest.mark.ac("ACC-2.9")
@pytest.mark.parametrize("title", SAMPLE_DUPLICATES)
def test_demo_samples_new_article_with_sample_title_gets_duplicate_error(
    db, browser, title
):
    accounts, _ = create_workspace(browser)
    officer = signed_in(accounts[2])
    before = stored_state()
    form = open_page(officer, "/support/articles/new/").form_with_button("Save article")
    typed = {"Title": title, "Body": "Ask the help desk."}
    response = form.submit(officer, typed, secure=True)
    assert response.status_code == 200, response.status_code
    page = Page(response)
    assert page.text.count(DUPLICATE) == 1, page.text
    assert page.form_with_button("Save article").field("Title").value == title
    assert stored_state() == before


@pytest.mark.ac("ACC-2.9", "ACC-2.2")
def test_demo_samples_not_added_to_workspace_without_them_lists_stay_empty(
    make_account, browser
):
    # A workspace made before the creation, as one from before new workspaces
    # got samples was, holding no articles or tickets.
    requester, _ = sign_in_as(make_account, REQUESTER)
    officer, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    create_workspace(browser)
    for role, user in ((REQUESTER, requester), (SUPPORT_OFFICER, officer)):
        assert_lists(user, role, [], [])
