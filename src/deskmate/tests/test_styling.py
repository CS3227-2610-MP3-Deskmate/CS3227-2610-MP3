"""PLT-4: one inline presentation shared by every common-layout page."""

import re

import pytest

from deskmate.tests.helpers import REPO_ROOT
from deskmate.tests.pages import Page
from deskmate.tests.signing_in import (
    REQUESTER,
    SUPPORT_OFFICER,
    new_browser,
    sign_in_as,
)
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.django_db
STYLE = re.compile(r"<style>(.*?)</style>", re.DOTALL)
EXTERNAL = re.compile(
    r"""(?:<link\b[^>]*\brel\s*=\s*["']?stylesheet|<script\b[^>]*\bsrc\s*=|<img\b|<iframe\b|@import\b|url\s*\()""",
    re.IGNORECASE,
)


def style_of(response):
    """Return the single inline style block in `response`, or fail."""
    styles = STYLE.findall(response.content.decode("utf-8"))
    assert len(styles) == 1, "The page does not have exactly one inline style block."
    return styles[0]


def assert_common_layout(response):
    """Assert `response` uses the shared layout and its inline presentation."""
    assert response.status_code == 200
    html = response.content.decode("utf-8")
    assert html.count("<main>") == 1 and html.count("</main>") == 1
    style = style_of(response)
    assert "max-width" in style or "width: min(" in style
    assert "box-sizing" in style and "@media" in style
    assert not EXTERNAL.search(html), "The page fetches a separate resource."
    return Page(response), style


def common_pages(make_account):
    """Return representative pages that use the common layout."""
    requester_browser, requester = sign_in_as(make_account, REQUESTER)
    officer_browser, officer = sign_in_as(make_account, SUPPORT_OFFICER)
    ticket = Ticket.objects.create(
        workspace=requester.workspace, title="Printer", description="It jams"
    )
    foreign = Ticket.objects.create(
        workspace=officer.workspace, title="Mail", description="No mail"
    )
    pages = {
        "home": new_browser().get("/"),
        "sign-in": new_browser().get("/sign-in/"),
        "requester": requester_browser.get("/requester/", secure=True),
        "support": officer_browser.get("/support/", secure=True),
        "requester-tickets": requester_browser.get("/requester/tickets/", secure=True),
        "requester-ticket": requester_browser.get(
            f"/requester/tickets/{ticket.pk}/", secure=True
        ),
        "requester-ticket-new": requester_browser.get(
            "/requester/tickets/new/", secure=True
        ),
        "support-tickets": officer_browser.get("/support/tickets/", secure=True),
        "support-ticket": officer_browser.get(
            f"/support/tickets/{foreign.pk}/", secure=True
        ),
        "support-ticket-resolve": officer_browser.get(
            f"/support/tickets/{foreign.pk}/resolve/", secure=True
        ),
        "requester-articles": requester_browser.get(
            "/requester/articles/", secure=True
        ),
        "support-articles": officer_browser.get("/support/articles/", secure=True),
        "support-article-new": officer_browser.get(
            "/support/articles/new/", secure=True
        ),
        "support-reset": officer_browser.get(
            "/support/reset-requester-password/", secure=True
        ),
    }
    return pages


@pytest.mark.ac("PLT-4.1", "PLT-4.4")
def test_styling_every_common_page_has_the_same_inline_presentation(make_account):
    pages = common_pages(make_account)
    styles = set()
    for name, response in pages.items():
        page, style = assert_common_layout(response)
        assert page.title, name
        scripts = re.findall(r"<script\b", response.content.decode(), re.IGNORECASE)
        if name in {"support-ticket", "requester-ticket-new"}:
            assert len(scripts) == 1, name
        else:
            assert not scripts, name
        styles.add(style)
    assert len(styles) == 1, "Common pages do not share one presentation."


@pytest.mark.ac("PLT-4.5")
def test_styling_adds_no_visible_content_or_control(make_account):
    for name, response in common_pages(make_account).items():
        page = Page(response)
        body = re.search(r"<body>(.*)</body>", response.content.decode(), re.DOTALL)
        assert body is not None, name
        visible = re.sub(r"<style>.*?</style>", "", body.group(1), flags=re.DOTALL)
        assert "@media" not in visible and "font:" not in visible, name
        assert all(control.name != "style" for control in page.controls), name


@pytest.mark.ac("PLT-4.6")
def test_styling_preserves_text_and_ticket_line_breaks(make_account):
    browser, account = sign_in_as(make_account, REQUESTER)
    ticket = Ticket.objects.create(
        workspace=account.workspace,
        title="Printer",
        description="Line one\nLine two",
    )
    response = browser.get(f"/requester/tickets/{ticket.pk}/", secure=True)
    html = response.content.decode("utf-8")
    page = Page(response)
    assert "Printer" in page.text and "Line one Line two" in page.text
    assert re.search(r"Line one<br>\s*Line two", html)
    assert not re.search(r"display\s*:\s*none", style_of(response))


@pytest.mark.ac("PLT-4.4")
def test_styling_adds_no_asset_pipeline_or_dependency():
    assert not (REPO_ROOT / "static").exists()
    assert not (REPO_ROOT / "assets").exists()
    assert not (REPO_ROOT / "package.json").exists()
