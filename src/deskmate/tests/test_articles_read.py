"""KB-2: Requesters list and read their workspace's articles."""

import re
from urllib.parse import unquote, urlsplit

import pytest
from django.contrib.auth import get_user_model

from deskmate.accounts.models import Workspace
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
LIST = '/requester/articles/'
MISSING = f'{LIST}999999999/'
LONG_ID = f'{LIST}{"9" * 5000}/'
ROUTES = (LIST, MISSING)
READ = re.compile(r'/requester/articles/[0-9]+/')


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
    form = Page(browser.get('/support/articles/new/')).form_with_button('Save article')
    response = form.submit(browser, {'Title': title, 'Body': body})
    assert response.status_code == 302
    edit = urlsplit(response.url).path
    article_id = edit.split('/')[3]
    return f'{LIST}{article_id}/'


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
    response = browser.get(path)
    assert response.status_code == 200, f'GET {path}: {response.status_code}'
    return Page(response)


def move_workspace(account, workspace):
    """Change the stored workspace, as an administrator could."""
    get_user_model().objects.filter(pk=account.pk).update(workspace=workspace)


@pytest.mark.ac('KB-2.1')
def test_articles_requester_navigation_and_empty_list(reader):
    browser, _ = reader
    role_page = Page(browser.get('/requester/', secure=True))
    assert ('Knowledge base', f'{ORIGIN}{LIST}') in role_page.links
    page = Page(browser.get(LIST, secure=True))
    assert page.title == 'Knowledge base' and page.h1s == ['Knowledge base']
    assert 'No articles yet.' in page.text
    assert ('Requester', f'{ORIGIN}/requester/') in page.links
    assert not [link for link in page.links if link[0] == 'New article']


@pytest.mark.ac('KB-2.1')
def test_articles_requester_list_shows_own_workspace_in_creation_order(reader, officer):
    author, _ = officer
    first = save(author, 'Zulu', 'First steps')
    second = save(author, 'Alpha', 'Second steps')
    browser, _ = reader
    assert article_links(browser) == [('Zulu', first), ('Alpha', second)]


@pytest.mark.ac('KB-2.2')
def test_articles_requester_reads_saved_title_and_body_as_text(reader, officer):
    author, _ = officer
    path = save(author, 'Guide', 'Line one\nLine two')
    page = article_page(reader[0], path)
    assert page.title == 'Article' and page.h1s == ['Article']
    assert 'Guide' in page.text and 'Line one Line two' in page.text
    assert ('Knowledge base', f'{ORIGIN}{LIST}') in page.links


@pytest.mark.ac('KB-2.2')
@pytest.mark.parametrize(
    'encoded',
    [
        '%3Cscript%3Ealert%281%29%3C%2Fscript%3E',
        '%3Cb%3Ebold%3C%2Fb%3E',
        '%5Blink%5D%28https%3A%2F%2Fevil.example%29',
    ],
)
def test_articles_requester_page_shows_markup_as_text(reader, officer, encoded):
    author, _ = officer
    payload = unquote(encoded)
    path = save(author, 'Guide', payload)
    page = article_page(reader[0], path)
    html = reader[0].get(path).content.decode()
    assert payload in page.text
    assert '<script>' not in html and '<b>' not in html
    assert not [url for _, url in page.links if 'evil.example' in url]


@pytest.mark.ac('KB-2.3')
def test_articles_requester_cannot_read_another_workspace(reader, officer, make_account):
    author, _ = officer
    save(author, 'Own', 'Own body')
    foreign = Workspace.objects.create()
    outsider, account = sign_in_as(make_account, SUPPORT_OFFICER)
    move_workspace(account, foreign)
    their = save(outsider, 'Foreign', 'Foreign body')
    browser, _ = reader
    response = browser.get(their)
    assert response.status_code == 404
    assert response.content == browser.get(MISSING).content
    assert b'Foreign body' not in response.content
    assert article_links(browser) == [('Own', f'{LIST}1/')]
    assert browser.get(f'{their}?workspace={foreign.pk}').status_code == 404
    assert browser.get(LONG_ID).status_code == 404


@pytest.mark.ac('KB-2.3')
def test_articles_requester_reading_never_edits(reader, officer):
    author, _ = officer
    path = save(author, 'Guide', 'Steps')
    before = list(Article.objects.values_list('title', 'body'))
    article_page(reader[0], path)
    assert list(Article.objects.values_list('title', 'body')) == before


@pytest.mark.ac('KB-2.4')
@pytest.mark.parametrize('visitor', [None, SUPPORT_OFFICER])
@pytest.mark.parametrize('path', ROUTES)
def test_articles_reading_access_denied_before_lookup(make_account, visitor, path):
    browser, _ = browser_as(make_account, visitor)
    response = send(
        browser,
        'GET',
        f'{path}?role={REQUESTER}&workspace=999',
        csrf_token(browser, visitor),
        headers={'Role': REQUESTER},
    )
    if visitor is None:
        assert_redirects(response, '/sign-in/')
    else:
        assert_forbidden(response, NOT_FOR_YOUR_ROLE)
    assert 'no-store' in response['Cache-Control']
    assert response['X-Frame-Options'] == 'DENY'


@pytest.mark.ac('KB-2.4')
@pytest.mark.parametrize(
    ('method', 'visitor', 'path'),
    [
        (method, visitor, ROUTES[(i + j) % 2])
        for i, method in enumerate(methods_not_listed('GET'))
        for j, visitor in enumerate(VISITORS)
    ],
)
def test_articles_reading_unsupported_methods_have_empty_405(
    make_account, method, visitor, path
):
    browser, _ = browser_as(make_account, visitor)
    assert_method_not_allowed(send(browser, method, path, csrf_token(browser, visitor)))


@pytest.mark.ac('KB-2.4')
@pytest.mark.parametrize('path', ROUTES)
def test_articles_reading_csrf_rejection_changes_nothing(reader, path):
    browser, _ = reader
    assert_forbidden(send(browser, 'POST', path, None), FORM_EXPIRED)


@pytest.mark.ac('KB-2.5')
@pytest.mark.parametrize('path', ROUTES)
def test_articles_reading_database_outage_returns_generic_error(
    reader, database_outage, path
):
    browser, _ = reader
    browser.raise_request_exception = False
    with database_outage():
        assert_server_error(browser.get(path))


@pytest.mark.ac('KB-2.1')
def test_articles_reading_list_uses_stored_workspace(reader, officer):
    author, _ = officer
    save(author, 'Guide', 'Steps')
    browser, account = reader
    assert article_links(browser)
    move_workspace(account, Workspace.objects.create())
    assert article_links(browser) == []
    assert 'No articles yet.' in Page(browser.get(LIST)).text