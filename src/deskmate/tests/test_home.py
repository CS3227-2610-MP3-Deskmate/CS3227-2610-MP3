"""PLT-1.1: the home page, whether or not the database answers."""

import re
from html.parser import HTMLParser

import pytest
from django.utils.html import strip_tags
from pytest_django.asserts import assertInHTML

from deskmate.tests.helpers import media_type
from deskmate.tests.signing_in import REQUESTER, sign_in_as


class _Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hrefs = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self.hrefs.append(dict(attrs).get("href"))


def assert_home_page(response):
    assert response.status_code == 200
    assert media_type(response) == "text/html"
    html = response.content.decode("utf-8")
    assertInHTML("<title>Deskmate</title>", html, count=1)
    assertInHTML("<h1>Deskmate</h1>", html, count=1)
    assertInHTML('<a href="/sign-in/">Sign in</a>', html, count=1)
    links = _Links()
    links.feed(html)
    assert links.hrefs == ["/sign-in/"]
    # All the page's visible text: the title, the heading, the sentence and the link.
    visible = re.sub(r"<(style|script|template)\b.*?</\1>", "", html, flags=re.DOTALL)
    text = " ".join(strip_tags(visible).split())
    assert text == (
        "Deskmate Deskmate Deskmate is a service desk: Requesters raise tickets and "
        "Support Officers resolve them. Sign in"
    )


@pytest.mark.ac("PLT-1.1")
@pytest.mark.django_db
def test_home_database_answers_returns_placeholder_page(client):
    assert_home_page(client.get("/"))


@pytest.mark.ac("PLT-1.1")
@pytest.mark.usefixtures("database_refuses_connections")
def test_home_database_refuses_connections_returns_placeholder_page(client):
    assert_home_page(client.get("/"))


@pytest.mark.ac("PLT-1.1")
def test_home_session_cookie_database_down_returns_placeholder_page(
    make_account, database_outage
):
    # A browser that signed in sends its session cookie with every request.
    browser, _ = sign_in_as(make_account, REQUESTER)
    with database_outage():
        response = browser.get("/")
    assert_home_page(response)
