"""PLT-1.1: the placeholder home page, whether or not the database answers."""

import pytest
from django.utils.html import strip_tags
from pytest_django.asserts import assertInHTML

from deskmate.tests.helpers import media_type


def assert_placeholder_page(response):
    assert response.status_code == 200
    assert media_type(response) == "text/html"
    html = response.content.decode("utf-8")
    assertInHTML("<title>Deskmate</title>", html, count=1)
    assertInHTML("<h1>Deskmate</h1>", html, count=1)
    # All the page's text: the title, the heading, then the one sentence.
    text = " ".join(strip_tags(html).split())
    assert text == "Deskmate Deskmate Deskmate is under construction."


@pytest.mark.ac("PLT-1.1")
@pytest.mark.django_db
def test_home_database_answers_returns_placeholder_page(client):
    assert_placeholder_page(client.get("/"))


@pytest.mark.ac("PLT-1.1")
@pytest.mark.usefixtures("database_refuses_connections")
def test_home_database_refuses_connections_returns_placeholder_page(client):
    assert_placeholder_page(client.get("/"))
