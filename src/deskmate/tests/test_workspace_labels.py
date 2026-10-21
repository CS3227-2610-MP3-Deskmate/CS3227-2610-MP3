"""ACC-1.2 and ACC-4.2: common labels use current, canonical workspace accounts."""

import re

import pytest
from django.contrib.auth.models import AnonymousUser
from django.core.handlers.exception import convert_exception_to_response
from django.db import DatabaseError, connection

from deskmate.accounts.models import Role, User, Workspace
from deskmate.accounts.views import role_page, sign_in
from deskmate.knowledge.models import Article
from deskmate.tests import signing_in as auth
from deskmate.tests import test_llm_gateway as gateway
from deskmate.tests.demo_workspaces import stored_rows
from deskmate.tests.pages import Page
from deskmate.tests.password_resets import RESET, Resetter, read_form, read_success
from deskmate.tickets.models import Ticket
from deskmate.views import home, message_page

CODE = "23az9y"
pytestmark = pytest.mark.ac("ACC-1.2")
provider = gateway.provider


def assert_workspace(response, code=CODE):
    """Require one plain-text line immediately after h1, before page content."""
    assert response.status_code == 200
    html = response.content.decode()
    assert html.count("Workspace:") == 1
    line = re.search(r"</h1>\s*<([a-z][\w-]*)\b[^>]*>([^<]*)</\1>", html)
    assert line is not None, "No plain-text line directly below h1."
    assert line[2].strip() == f"Workspace: {code}"


@pytest.fixture
def trio(make_account):
    """The three accounts required for a recoverable demo code."""
    return [
        make_account(f"{name}-{CODE}", auth.PASSWORD, role)
        for name, role in (
            ("requester1", auth.REQUESTER),
            ("requester2", auth.REQUESTER),
            ("support1", auth.SUPPORT_OFFICER),
        )
    ]


def signed_browser(user):
    """Authenticate through the public sign-in form."""
    browser = auth.new_browser()
    auth.assert_redirects(
        auth.sign_in(browser, user.username, auth.PASSWORD), auth.ROLE_PAGES[user.role]
    )
    return browser


@pytest.mark.parametrize("role", auth.ROLES)
def test_workspace_label_unsaved_canonical_username_is_unavailable(rf, role):
    request = rf.get(auth.ROLE_PAGES[role])
    name = "requester1" if role == auth.REQUESTER else "support1"
    request.user = User(username=f"{name}-{CODE}", role=role)
    assert_workspace(role_page(request, Role(role)), "unavailable")


@pytest.mark.parametrize("index", [0, 1, 2])
def test_workspace_label_every_member_uses_same_code_without_writes(trio, index):
    user = trio[index]
    browser = signed_browser(user)
    before = stored_rows()
    assert_workspace(browser.get(auth.ROLE_PAGES[user.role]))
    assert stored_rows() == before


@pytest.mark.parametrize("count", [3, 19, 20, 21])
@pytest.mark.parametrize("index", [0, 2])
def test_workspace_label_contiguous_requester_extension_preserves_code_through_20(
    trio, make_account, count, index
):
    browser = signed_browser(trio[index])
    for number in range(3, count + 1):
        make_account(f"requester{number}-{CODE}", auth.PASSWORD, auth.REQUESTER)
    before = stored_rows()
    assert_workspace(
        browser.get(auth.ROLE_PAGES[trio[index].role]),
        CODE if count <= 20 else "unavailable",
    )
    assert stored_rows() == before


@pytest.mark.parametrize("number", ["0", "02", "3", "-2"])
def test_workspace_label_noncanonical_requester_number_is_unavailable(trio, number):
    browser = signed_browser(trio[0])
    User.objects.filter(pk=trio[1].pk).update(username=f"requester{number}-{CODE}")
    assert_workspace(browser.get("/requester/"), "unavailable")


def test_workspace_label_all_content_routes_and_validation(
    trio, transactional_db, provider
):
    requester, _, officer = trio
    rb, sb = signed_browser(requester), signed_browser(officer)
    ticket = Ticket.objects.create(
        workspace=requester.workspace, title="Printer", description="Jams."
    )
    article = Article.objects.create(
        workspace=requester.workspace, title="Guide", body="Read."
    )
    for browser, root in ((rb, "/requester"), (sb, "/support")):
        for path in ("", "/tickets", f"/tickets/{ticket.pk}", "/articles"):
            assert_workspace(browser.get(f"{root}{path}/"))
    assert_workspace(rb.get(f"/requester/articles/{article.pk}/"))
    assert_workspace(sb.get(RESET))
    for browser, path in [
        (rb, "/requester/tickets/new/"),
        (sb, "/support/articles/new/"),
        (sb, f"/support/articles/{article.pk}/edit/"),
        (sb, f"/support/tickets/{ticket.pk}/resolve/"),
    ]:
        assert_workspace(browser.get(path))
        assert_workspace(
            auth.send(
                browser,
                "POST",
                path,
                Page(browser.get(path)).csrf_token(),
                data={"workspace": 999999, "code": "9hkmnp"},
            )
        )
    read_form(Resetter(sb).post("unknown"), "unknown", rejected=True, workspace=CODE)
    token = auth.csrf_token(sb, auth.SUPPORT_OFFICER)
    path = f"/support/tickets/{ticket.pk}/key-sentences/"
    provider.body = gateway.probe.provider_body('{"sentences": ["Jams."]}')
    assert_workspace(auth.send(sb, "POST", path, token))


@pytest.mark.ac("ACC-4.2")
def test_workspace_label_reset_success_keeps_common_line_and_password_controls(trio):
    requester, _, officer = trio
    response = Resetter(signed_browser(officer)).post(requester.username)
    assert_workspace(response)
    read_success(response, requester.username, workspace=CODE)


@pytest.mark.parametrize("fault", ["missing", "extra", "renamed", "role", "mixed"])
def test_workspace_label_changed_membership_names_or_roles_becomes_unavailable(
    trio, make_account, fault
):
    user, second, _ = trio
    browser = signed_browser(user)
    assert_workspace(browser.get("/requester/"))
    if fault == "missing":
        second.delete()
    elif fault == "extra":
        make_account("extra", auth.PASSWORD, auth.REQUESTER)
    elif fault == "role":
        User.objects.filter(pk=second.pk).update(role=auth.SUPPORT_OFFICER)
    else:
        name = "requester2-9hkmnp" if fault == "mixed" else "other-" + CODE
        User.objects.filter(pk=second.pk).update(username=name)
    assert_workspace(browser.get("/requester/"), "unavailable")


@pytest.mark.parametrize("code", ["23456", "2345678", "234560", "23456i", "23456A"])
def test_workspace_label_common_invalid_code_is_unavailable(trio, code):
    browser = signed_browser(trio[0])
    for user in trio:
        User.objects.filter(pk=user.pk).update(
            username=user.username.split("-")[0] + "-" + code
        )
    assert_workspace(browser.get("/requester/"), "unavailable")


def test_workspace_label_current_workspace_and_client_claim_isolation(trio):
    user, _, officer = trio
    browser = signed_browser(user)
    other = Workspace.objects.create()
    browser.cookies["workspace"] = str(other.pk)
    browser.cookies["code"] = "9hkmnp"
    response = auth.send(
        browser,
        "GET",
        f"/requester/?workspace={other.pk}&code=9hkmnp",
        headers={"Workspace": str(other.pk), "X-Workspace-Code": "9hkmnp"},
    )
    assert_workspace(response)
    User.objects.filter(pk=user.pk).update(workspace=other)
    assert_workspace(browser.get("/requester/"), "unavailable")
    for member in trio:
        User.objects.filter(pk=member.pk).update(
            workspace=other, username=member.username.split("-")[0] + "-9hkmnp"
        )
    assert_workspace(browser.get("/requester/"), "9hkmnp")
    User.objects.filter(pk=user.pk).update(role=auth.SUPPORT_OFFICER)
    auth.assert_forbidden(browser.get("/requester/"), auth.NOT_FOR_YOUR_ROLE)
    officer.refresh_from_db()
    assert_workspace(signed_browser(officer).get("/support/"), "unavailable")


def test_workspace_label_excluded_responses_need_no_account_lookup(rf):
    request = rf.get("/")
    user = User(username=f"requester1-{CODE}", role=auth.REQUESTER, workspace_id=900001)
    request.user = user
    responses = [
        home(request),
        role_page(request, Role.SUPPORT_OFFICER),
        message_page(request, "Too many attempts", "Wait.", 429),
        message_page(request, "Server error", "Try later.", 500),
        sign_in(request),
    ]
    request.user = AnonymousUser()
    responses += [sign_in(request), role_page(request, Role.REQUESTER)]
    assert [r.status_code for r in responses] == [200, 403, 429, 500, 302, 200, 302]
    assert all("Workspace:" not in r.content.decode() for r in responses)


def test_workspace_label_lookup_database_error_is_generic_500_without_writes(
    trio, rf, settings
):
    settings.DEBUG = False
    request = rf.get("/requester/")
    request.user = trio[0]
    before = stored_rows()

    def fail_read(execute, sql, params, many, context):
        raise DatabaseError("synthetic workspace read failure")

    view = convert_exception_to_response(lambda req: role_page(req, Role.REQUESTER))
    with connection.execute_wrapper(fail_read):
        response = view(request)
    auth.assert_server_error(
        response, {"lookup error": "synthetic workspace read failure"}
    )
    assert "Workspace:" not in response.content.decode()
    assert stored_rows() == before
