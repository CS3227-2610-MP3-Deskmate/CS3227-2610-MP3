"""PLT-1.1: the placeholder home page, whether or not the database answers."""

import pytest
from django.utils.html import strip_tags
from pytest_django.asserts import assertInHTML

from deskmate.tests.helpers import media_type
from deskmate.tests.pages import Page
from deskmate.tests.signing_in import REQUESTER, sign_in_as


def assert_placeholder_page(response):
    assert response.status_code == 200
    assert media_type(response) == "text/html"
    html = response.content.decode("utf-8")
    assertInHTML("<title>Deskmate</title>", html, count=1)
    assertInHTML("<h1>Deskmate</h1>", html, count=1)
    assert Page(response).heading_texts == ["Deskmate"]
    assertInHTML('<a href="/sign-in/">Sign in</a>', html, count=1)
    # All the page's text: the title, heading, sentence and navigation link.
    text = " ".join(strip_tags(html).split())
    assert text == "Deskmate Deskmate Deskmate is under construction. Sign in"


@pytest.mark.ac("PLT-1.1")
def test_home_sign_in_link_opens_sign_in_form_without_query(browser):
    page = Page(browser.get("/"))
    links = [url for text, url in page.links if text == "Sign in"]
    assert len(links) == 1
    response = browser.get(links[0])
    assert response.status_code == 200
    assert response.wsgi_request.path == "/sign-in/"
    assert response.wsgi_request.META["QUERY_STRING"] == ""
    Page(response).form_with_button("Sign in")


@pytest.mark.ac("PLT-1.1")
@pytest.mark.django_db
def test_home_database_answers_returns_placeholder_page(client):
    assert_placeholder_page(client.get("/"))


@pytest.mark.ac("PLT-1.1")
@pytest.mark.usefixtures("database_refuses_connections")
def test_home_database_refuses_connections_returns_placeholder_page(client):
    assert_placeholder_page(client.get("/"))


@pytest.mark.ac("PLT-1.1")
def test_home_session_cookie_database_down_returns_placeholder_page(
    make_account, database_outage
):
    # A browser that signed in sends its session cookie with every request.
    browser, _ = sign_in_as(make_account, REQUESTER)
    with database_outage():
        response = browser.get("/")
    assert_placeholder_page(response)
