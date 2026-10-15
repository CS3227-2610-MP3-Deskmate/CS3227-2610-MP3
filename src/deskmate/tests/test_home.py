"""PLT-1.1: the placeholder home page, whether or not the database answers."""

from html.parser import HTMLParser

import pytest

from deskmate.tests.helpers import media_type

HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}
# Elements whose content is not text a visitor reads.
HIDDEN_TAGS = {"script", "style", "template"}


class PageText(HTMLParser):
    """Splits a page's text into its titles, its headings and all other text."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.titles = []
        self.headings = []
        self._other = []
        self._element = None
        self._buffer = []

    def handle_starttag(self, tag, attrs):
        if self._element is None and (
            tag == "title" or tag in HEADING_TAGS or tag in HIDDEN_TAGS
        ):
            self._element = tag
            self._buffer = []

    def handle_endtag(self, tag):
        if tag != self._element:
            return
        text = normalise("".join(self._buffer))
        if tag == "title":
            self.titles.append(text)
        elif tag in HEADING_TAGS:
            self.headings.append(text)
        self._element = None

    def handle_data(self, data):
        if self._element is None:
            self._other.append(data)
        else:
            self._buffer.append(data)

    @property
    def other_text(self):
        return normalise("".join(self._other))


def normalise(text):
    return " ".join(text.split())


def page_text(response):
    parser = PageText()
    parser.feed(response.content.decode("utf-8"))
    parser.close()
    return parser


def assert_placeholder_page(response):
    assert response.status_code == 200
    assert media_type(response) == "text/html"
    text = page_text(response)
    assert text.titles == ["Deskmate"]
    assert text.headings == ["Deskmate"]
    assert text.other_text == "Deskmate is under construction."


@pytest.mark.ac("PLT-1.1")
@pytest.mark.django_db
def test_home_database_answers_returns_placeholder_page(client):
    assert_placeholder_page(client.get("/"))


@pytest.mark.ac("PLT-1.1")
@pytest.mark.usefixtures("database_refuses_connections")
def test_home_database_refuses_connections_returns_placeholder_page(client):
    assert_placeholder_page(client.get("/"))
