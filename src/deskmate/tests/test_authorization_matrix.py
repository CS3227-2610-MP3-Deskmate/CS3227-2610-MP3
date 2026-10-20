"""The authorization matrix: every route against every role and workspace.

The route table in TECHNICAL-SPEC "Routes" says which roles may open each
route. This test walks the registered routes, not a hand-written list, so a
new route without an access decision fails here.
"""

import re

import pytest
from django.urls import get_resolver

from deskmate.accounts.models import Workspace
from deskmate.knowledge.models import Article
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    SUPPORT_OFFICER,
    assert_redirects,
    new_browser,
    sign_in,
    sign_in_as,
)
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.django_db

SIGN_IN = "/sign-in/"
ROLE_PAGES = {REQUESTER: "/requester/", SUPPORT_OFFICER: "/support/"}
# The deliberate alias that gives PLT-3.3's 404 (PLT-1.9).
NO_SLASH = "/health/llm"

# The access each route's table row gives it. A route not named here must be
# Public; a new route therefore has to be added here, with its decision.
ACCESS = {
    "/requester/": REQUESTER,
    "/requester/articles/": REQUESTER,
    "/requester/articles/<id>/": REQUESTER,
    "/requester/tickets/": REQUESTER,
    "/requester/tickets/new/": REQUESTER,
    "/requester/tickets/<id>/": REQUESTER,
    "/support/": SUPPORT_OFFICER,
    "/support/reset-requester-password/": SUPPORT_OFFICER,
    "/support/articles/": SUPPORT_OFFICER,
    "/support/articles/new/": SUPPORT_OFFICER,
    "/support/articles/<id>/edit/": SUPPORT_OFFICER,
    "/support/tickets/": SUPPORT_OFFICER,
    "/support/tickets/<id>/": SUPPORT_OFFICER,
    "/support/tickets/<id>/resolve/": SUPPORT_OFFICER,
}
# Routes that are not about a role's records: their answer is the same for
# every visitor, and the route's own criteria cover it.
PUBLIC = {
    "/",
    "/health/",
    "/health/llm/",
    "/sign-in/",
    "/sign-out/",
    "/demo-workspace/",
}
# What each public route answers for a signed-out visitor and for a signed-in
# one. `/sign-in/` sends a signed-in user to their own role's page (ACC-1.3).
PUBLIC_ANSWERS = {
    "/": {None: 200, REQUESTER: 200, SUPPORT_OFFICER: 200},
    "/health/": {None: 200, REQUESTER: 200, SUPPORT_OFFICER: 200},
    "/health/llm/": {None: 404, REQUESTER: 404, SUPPORT_OFFICER: 404},
    NO_SLASH: {None: 404, REQUESTER: 404, SUPPORT_OFFICER: 404},
    "/sign-in/": {None: 200, REQUESTER: 302, SUPPORT_OFFICER: 302},
    "/sign-out/": {None: 405, REQUESTER: 405, SUPPORT_OFFICER: 405},
    "/demo-workspace/": {None: 405, REQUESTER: 405, SUPPORT_OFFICER: 405},
}
NAMED_GROUP = re.compile(r"\(\?P<[^>]+>.+?\)")


def pattern_route(pattern):
    """Return `pattern` as the path a visitor requests, with `<id>` for a parameter."""
    route = NAMED_GROUP.sub("<id>", str(pattern)).removeprefix("^")
    if route.endswith("$"):
        route = route[:-1]
    elif route.endswith("\\Z"):
        route = route[:-2]
    return "/" + route


def registered_routes():
    """Return the path of every registered route, including the no-slash alias."""
    return [pattern_route(pattern.pattern) for pattern in get_resolver().url_patterns]


def ticket_id(ticket):
    """Return `ticket`'s identifier as the route uses it."""
    return str(ticket.pk)


def records(workspace):
    """Return a ticket and an article in `workspace`, for the routes that need one."""
    ticket = Ticket.objects.create(
        workspace=workspace, title="Workspace ticket", description="Ticket body"
    )
    article = Article.objects.create(
        workspace=workspace, title="Workspace article", body="Article body"
    )
    return ticket, article


def concrete(path, ticket, article):
    """Return `path` with `<id>` replaced by a record in the visitor's workspace."""
    if "tickets" in path:
        return path.replace("<id>", ticket_id(ticket))
    return path.replace("<id>", str(article.pk))


@pytest.mark.ac("ACC-1.5")
def test_every_registered_route_has_an_access_decision():
    routes = set(registered_routes())
    decided = set(ACCESS) | PUBLIC | {NO_SLASH}
    assert routes == decided, (
        f"Routes without an access decision: {sorted(routes - decided)}; "
        f"decisions without a route: {sorted(decided - routes)}"
    )


@pytest.mark.ac(
    "ACC-1.5",
    "ACC-1.4",
    "RQ-1.6",
    "RQ-2.5",
    "RQ-3.6",
    "KB-1.6",
    "KB-2.4",
    "ACC-4.5",
)
def test_a_visitor_without_the_routes_role_is_redirected_or_refused(make_account):
    requester_browser, owner = sign_in_as(make_account, REQUESTER)
    officer_browser, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    ticket, article = records(owner.workspace)

    mismatches = []
    for route, allowed_role in ACCESS.items():
        for visitor, browser in (
            (None, new_browser()),
            (REQUESTER, requester_browser),
            (SUPPORT_OFFICER, officer_browser),
        ):
            response = browser.get(concrete(route, ticket, article), secure=True)
            if visitor is None:
                if response.status_code != 302 or response["Location"] != SIGN_IN:
                    mismatches.append((route, visitor, "302 to /sign-in/", response))
                continue
            elif visitor == allowed_role:
                expected = 200
            else:
                expected = 403
            if response.status_code != expected:
                mismatches.append((route, visitor, expected, response.status_code))
    assert not mismatches, f"Route, visitor, expected, actual: {mismatches}"


@pytest.mark.ac("ACC-1.2", "ACC-1.3", "ACC-1.4", "ACC-1.5", "PLT-1.9")
def test_every_public_route_answers_each_visitor_the_same_way(make_account):
    requester_browser, _ = sign_in_as(make_account, REQUESTER)
    officer_browser, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    mismatches = []
    for route, answers in PUBLIC_ANSWERS.items():
        for visitor, browser in (
            (None, new_browser()),
            (REQUESTER, requester_browser),
            (SUPPORT_OFFICER, officer_browser),
        ):
            response = browser.get(route, secure=True)
            expected = answers[visitor]
            if response.status_code != expected:
                mismatches.append((route, visitor, expected, response.status_code))
            if expected == 302 and response["Location"] != ROLE_PAGES[visitor]:
                mismatches.append(
                    (route, visitor, ROLE_PAGES[visitor], response["Location"])
                )
    assert not mismatches, f"Route, visitor, expected, actual: {mismatches}"


@pytest.mark.ac("RQ-1.7", "RQ-2.4", "RQ-3.5", "KB-1.7", "KB-2.3")
def test_each_role_cannot_reach_another_workspaces_records(make_account):
    _, owner = sign_in_as(make_account, REQUESTER)
    officer_browser, officer = sign_in_as(make_account, SUPPORT_OFFICER)
    ticket, article = records(owner.workspace)

    foreign = Workspace.objects.create()
    outsider_requester = make_account("outsider-requester", PASSWORD, REQUESTER)
    outsider_requester.workspace = foreign
    outsider_requester.save()
    outsider_officer = make_account("outsider-officer", PASSWORD, SUPPORT_OFFICER)
    outsider_officer.workspace = foreign
    outsider_officer.save()
    requester_browser = new_browser()
    assert_redirects(
        sign_in(requester_browser, "outsider-requester", PASSWORD),
        ROLE_PAGES[REQUESTER],
    )
    officer_outside = new_browser()
    assert_redirects(
        sign_in(officer_outside, "outsider-officer", PASSWORD),
        ROLE_PAGES[SUPPORT_OFFICER],
    )

    # The owner's own officer can open both routes, so the 404s below are
    # about the workspace and not about a missing route or record.
    for path in (
        f"/support/tickets/{ticket.pk}/",
        f"/support/articles/{article.pk}/edit/",
    ):
        assert officer_browser.get(path, secure=True).status_code == 200, path
    assert officer.workspace_id == owner.workspace_id

    outside = (
        (officer_outside, f"/support/tickets/{ticket.pk}/"),
        (officer_outside, f"/support/tickets/{ticket.pk}/resolve/"),
        (officer_outside, f"/support/articles/{article.pk}/edit/"),
        (requester_browser, f"/requester/tickets/{ticket.pk}/"),
        (requester_browser, f"/requester/articles/{article.pk}/"),
    )
    for browser, path in outside:
        response = browser.get(path, secure=True)
        assert response.status_code == 404, (path, response.status_code)
        assert b"Workspace ticket" not in response.content
        assert b"Workspace article" not in response.content
        assert b"Ticket body" not in response.content
        assert b"Article body" not in response.content
