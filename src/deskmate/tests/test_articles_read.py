"""KB-2: Requesters list and read their workspace's articles."""

import re
from datetime import timedelta
from html import escape
from urllib.parse import unquote, urlsplit

import pytest
from django.contrib.auth import get_user_model

from deskmate.accounts.models import User, Workspace
from deskmate.knowledge.models import Article
from deskmate.tests.pages import ORIGIN, Page
from deskmate.tests.signing_in import (
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
    send,
    sign_in_as,
)

pytestmark = pytest.mark.django_db
LIST = "/requester/articles/"
MISSING = f"{LIST}999999999/"
LONG_ID = f"{LIST}{'9' * 5000}/"
ROUTES = (LIST, MISSING)
READ = re.compile(r"/requester/articles/[0-9]+/")


@pytest.fixture
def reader(make_account):
    """A signed-in Requester and their stored account."""
    return sign_in_as(make_account, REQUESTER)


@pytest.fixture
def officer(make_account):
    """A signed-in Support Officer, who writes the articles the reader sees."""
    return sign_in_as(make_account, SUPPORT_OFFICER)


def save(browser, title, body):
    """Save an article as its author does, and return its reading path."""
    form = Page(browser.get("/support/articles/new/")).form_with_button("Save article")
    response = form.submit(browser, {"Title": title, "Body": body})
    assert response.status_code == 302
    edit = urlsplit(response.url).path
    article_id = edit.split("/")[3]
    return f"{LIST}{article_id}/"


def article_links(browser):
    """Read the ordered article titles and reading paths from the list."""
    response = browser.get(LIST)
    assert response.status_code == 200
    return [
        (text, urlsplit(url).path)
        for text, url in Page(response).links
        if READ.fullmatch(urlsplit(url).path)
    ]


def article_page(browser, path):
    """Read the reading page at `path`."""
    response = browser.get(path, secure=True)
    assert response.status_code == 200, f"GET {path}: {response.status_code}"
    return Page(response)


def move_workspace(account, workspace):
    """Change the stored workspace, as an administrator could."""
    get_user_model().objects.filter(pk=account.pk).update(workspace=workspace)


@pytest.mark.ac("KB-2.1")
def test_articles_requester_navigation_and_empty_list(reader):
    browser, _ = reader
    role_page = Page(browser.get("/requester/", secure=True))
    assert ("Knowledge base", f"{ORIGIN}{LIST}") in role_page.links
    page = Page(browser.get(LIST, secure=True))
    assert page.title == "Knowledge base" and page.h1s == ["Knowledge base"]
    assert "No articles yet." in page.text
    assert ("Requester", f"{ORIGIN}/requester/") in page.links
    assert not [link for link in page.links if link[0] == "New article"]


@pytest.mark.ac("KB-2.1")
def test_articles_requester_list_shows_own_workspace_in_creation_order(reader, officer):
    author, _ = officer
    first = save(author, "Zulu", "First steps")
    second = save(author, "Alpha", "Second steps")
    browser, _ = reader
    assert article_links(browser) == [("Zulu", first), ("Alpha", second)]


@pytest.mark.ac("KB-2.2")
def test_articles_requester_reads_saved_title_and_body_as_text(reader, officer):
    author, _ = officer
    path = save(author, "Guide", "Line one\nLine two")
    page = article_page(reader[0], path)
    assert page.title == "Article" and page.h1s == ["Article"]
    assert "Guide" in page.text and "Line one Line two" in page.text
    assert ("Knowledge base", f"{ORIGIN}{LIST}") in page.links
    html = reader[0].get(path).content.decode()
    assert re.search(r"Line one<br>\s*Line two", html), html


@pytest.mark.ac("KB-2.2")
@pytest.mark.parametrize(
    "encoded",
    [
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
        "%3Cb%3Ebold%3C%2Fb%3E",
        "%5Blink%5D%28https%3A%2F%2Fevil.example%29",
    ],
)
def test_articles_requester_page_shows_markup_as_text(reader, officer, encoded):
    author, _ = officer
    payload = unquote(encoded)
    path = save(author, "Guide", payload)
    page = article_page(reader[0], path)
    html = reader[0].get(path).content.decode()
    assert payload in page.text
    assert "<script>" not in html and "<b>" not in html
    assert not [url for _, url in page.links if "evil.example" in url]


@pytest.mark.ac("KB-2.2")
@pytest.mark.parametrize(
    "encoded",
    [
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
        "%3Cb%3Ebold%3C%2Fb%3E",
    ],
)
def test_articles_requester_list_and_page_escape_title_markup(reader, officer, encoded):
    author, _ = officer
    title = unquote(encoded)
    path = save(author, title, "Steps")
    browser, _ = reader
    for response in (browser.get(LIST), browser.get(path)):
        assert response.status_code == 200
        html = response.content.decode()
        assert "<script>" not in html and "<b>" not in html
        assert escape(title) in html
    assert (title, path) in article_links(browser)


@pytest.mark.ac("KB-2.3")
def test_articles_requester_cannot_read_another_workspace(
    reader, officer, make_account
):
    author, _ = officer
    save(author, "Own", "Own body")
    foreign = Workspace.objects.create()
    outsider, account = sign_in_as(make_account, SUPPORT_OFFICER)
    move_workspace(account, foreign)
    their = save(outsider, "Foreign", "Foreign body")
    browser, _ = reader
    response = browser.get(their)
    assert response.status_code == 404
    assert response.content == browser.get(MISSING).content
    assert b"Foreign body" not in response.content
    assert [title for title, _ in article_links(browser)] == ["Own"]
    assert browser.get(f"{their}?workspace={foreign.pk}").status_code == 404
    assert browser.get(LONG_ID).status_code == 404


@pytest.mark.ac("KB-2.3")
def test_articles_requester_query_parameters_cannot_select_article_or_workspace(
    reader, officer, make_account
):
    author, _ = officer
    own = save(author, "Own", "Own body")
    foreign = Workspace.objects.create()
    outsider, account = sign_in_as(make_account, SUPPORT_OFFICER)
    move_workspace(account, foreign)
    their = save(outsider, "Foreign", "Foreign body")
    own_id = own.strip("/").split("/")[-1]
    their_id = their.strip("/").split("/")[-1]
    browser, _ = reader
    page = article_page(browser, f"{own}?id={their_id}&role={SUPPORT_OFFICER}")
    assert "Own body" in page.text and "Foreign body" not in page.text
    for query in (f"?id={own_id}", f"?role={REQUESTER}", f"?workspace={foreign.pk}"):
        response = browser.get(f"{their}{query}")
        assert response.status_code == 404
        assert response.content == browser.get(MISSING).content
    listed = Page(
        browser.get(
            f"{LIST}?id={their_id}&role={SUPPORT_OFFICER}&workspace={foreign.pk}"
        )
    )
    assert [
        (text, urlsplit(url).path)
        for text, url in listed.links
        if READ.fullmatch(urlsplit(url).path)
    ] == [("Own", own)]


@pytest.mark.ac("KB-2.3")
@pytest.mark.django_db(reset_sequences=True)
def test_articles_requester_leading_zero_id_reads_the_same_article(reader, officer):
    author, _ = officer
    save(author, "Guide", "Steps")
    article = Article.objects.get(pk=1)
    browser, _ = reader
    page = article_page(browser, f"{LIST}0001/")
    assert page.title == "Article"
    assert article.title in page.text and article.body in page.text
    assert browser.get(f"{LIST}0001/").content == browser.get(f"{LIST}1/").content


@pytest.mark.ac("KB-2.3")
def test_articles_requester_reading_never_edits(reader, officer):
    author, _ = officer
    path = save(author, "Guide", "Steps")
    before = list(Article.objects.values_list("title", "body"))
    article_page(reader[0], path)
    assert list(Article.objects.values_list("title", "body")) == before


@pytest.mark.ac("KB-2.4")
@pytest.mark.parametrize("visitor", [None, SUPPORT_OFFICER])
@pytest.mark.parametrize("path", ROUTES)
def test_articles_reading_access_denied_before_lookup(make_account, visitor, path):
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


@pytest.mark.ac("KB-2.4")
@pytest.mark.parametrize(
    ("method", "visitor", "path"),
    [
        (method, visitor, ROUTES[(i + j) % 2])
        for i, method in enumerate(methods_not_listed("GET"))
        for j, visitor in enumerate(VISITORS)
    ],
)
def test_articles_reading_unsupported_methods_have_empty_405(
    make_account, method, visitor, path
):
    browser, _ = browser_as(make_account, visitor)
    assert_method_not_allowed(send(browser, method, path, csrf_token(browser, visitor)))


@pytest.mark.ac("KB-2.4")
@pytest.mark.parametrize("path", ROUTES)
def test_articles_reading_csrf_rejection_changes_nothing(reader, officer, path):
    author, _ = officer
    save(author, "Guide", "Steps")
    browser, _ = reader
    before = list(Article.objects.values_list("title", "body"))
    assert_forbidden(send(browser, "POST", path, None), FORM_EXPIRED)
    assert list(Article.objects.values_list("title", "body")) == before


@pytest.mark.ac("KB-2.4")
@pytest.mark.parametrize("state", ["expired", "deleted", "role-changed"])
@pytest.mark.parametrize("route", ["list", "reading"])
def test_articles_reading_current_session_and_stored_role_control_access(
    clock, reader, officer, state, route
):
    author, _ = officer
    reading = save(author, "Guide", "Steps")
    browser, account = reader
    target = LIST if route == "list" else reading
    if state == "expired":
        clock.set_elapsed(timedelta(hours=8))
    elif state == "deleted":
        account.delete()
    else:
        User.objects.filter(pk=account.pk).update(role=SUPPORT_OFFICER)
    response = browser.get(target)
    if state == "role-changed":
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
    else:
        assert_redirects(response, "/sign-in/")


@pytest.mark.ac("KB-2.4")
def test_articles_requester_successful_responses_use_cache_and_framing_controls(
    reader, officer
):
    author, _ = officer
    path = save(author, "Guide", "Steps")
    browser, _ = reader
    for target in (LIST, path):
        response = browser.get(target)
        assert response.status_code == 200
        assert "no-store" in response["Cache-Control"]
        assert response["X-Frame-Options"] == "DENY"


@pytest.mark.ac("KB-2.5")
@pytest.mark.parametrize("path", ROUTES)
def test_articles_reading_database_outage_returns_generic_error(
    reader, database_outage, path
):
    browser, _ = reader
    browser.raise_request_exception = False
    with database_outage():
        assert_server_error(browser.get(path))


@pytest.mark.ac("KB-2.1")
def test_articles_reading_list_uses_stored_workspace(reader, officer):
    author, _ = officer
    save(author, "Guide", "Steps")
    browser, account = reader
    assert article_links(browser)
    move_workspace(account, Workspace.objects.create())
    assert article_links(browser) == []
    assert "No articles yet." in Page(browser.get(LIST)).text
