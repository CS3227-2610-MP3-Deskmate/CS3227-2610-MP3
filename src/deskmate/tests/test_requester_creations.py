"""ACC-5.1–5.5: creation, canonical membership, quota and access boundaries.

ACC-5.2's uniform CSPRNG draws reuse ACC-2.8's manual security review.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import unquote, urlencode, urljoin

import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, identify_hasher
from django.db import connection, connections

from deskmate.accounts.models import CountedAttempt, Kind, Workspace
from deskmate.knowledge.models import Article
from deskmate.tests import demo_workspaces as demo
from deskmate.tests import signing_in as auth
from deskmate.tests.hashing import recording_hashes
from deskmate.tests.pages import Page
from deskmate.tests.password_resets import accounts, protected
from deskmate.tests.requester_creations import (
    CODE,
    CREATE,
    FORM,
    NONCANONICAL,
    QUOTA,
    SUCCESS,
    creation_fixture,  # noqa: F401 -- shared fixture.
    grow,
    read_form,
    read_success,
)
from deskmate.tests.test_workspace_labels import assert_workspace
from deskmate.tickets.models import Ticket


@pytest.mark.ac("ACC-5.1", "ACC-1.2")
def test_create_requester_officer_link_opens_only_csrf_confirmation_without_writes(
    creator,
):
    sender, _ = creator
    page = Page(sender.browser.get("/support/"))
    assert (FORM, urljoin(page.url, CREATE)) in page.links
    before = demo.stored_rows()
    read_form(sender.browser.get(CREATE))
    assert demo.stored_rows() == before


@pytest.mark.ac("ACC-5.1", "ACC-5.2", "ACC-5.5", "ACC-1.2")
@pytest.mark.parametrize("debug", demo.DEBUG_MODES)
def test_create_requester_success_hashes_once_preserves_records_and_credentials_sign_in(
    creator, settings, written_output, debug
):
    settings.DEBUG = debug
    sender, officer = creator
    Ticket.objects.create(
        workspace=officer.workspace, title="Printer", description="Jams."
    )
    Article.objects.create(workspace=officer.workspace, title="Guide", body="Read.")
    before = demo.stored_rows()
    old_accounts = accounts()
    with recording_hashes() as hashed:
        response = sender.post()
    username = f"requester3-{CODE}"
    password = read_success(response, username)
    assert len(hashed) == 1 and hashed[0].password == password
    user = get_user_model().objects.get(username=username)
    assert user.role == auth.REQUESTER and user.workspace_id == officer.workspace_id
    assert user.password == hashed[0].encoded and user.password != password
    assert identify_hasher(user.password).decode(user.password)["salt"]
    assert check_password(password, user.password)
    after_accounts = accounts()
    assert after_accounts.pop(user.pk)["username"] == username
    assert after_accounts == old_accounts
    after = demo.stored_rows()
    mutable = {get_user_model()._meta.db_table, CountedAttempt._meta.db_table}
    assert {k: v for k, v in after.items() if k not in mutable} == {
        k: v for k, v in before.items() if k not in mutable
    }
    assert demo.records_holding([password]) == demo.sessions_holding([password]) == []
    assert not demo.cookies_holding(
        [password], response.cookies, sender.browser.cookies
    )
    assert all(
        value not in written_output.text()
        for value in (username, password, user.password)
    )
    read_form(sender.browser.get(CREATE))
    for path in ("/", "/health/", auth.SIGN_IN, "/support/", "/requester/", CREATE):
        assert password not in sender.browser.get(path).content.decode()
    newcomer = auth.new_browser()
    auth.assert_redirects(auth.sign_in(newcomer, username, password), "/requester/")
    auth.assert_signed_in_as(newcomer, auth.REQUESTER, username)
    assert_workspace(newcomer.get("/requester/"))
    auth.assert_signed_in_as(sender.browser, auth.SUPPORT_OFFICER, officer.username)
    assert_workspace(sender.browser.get("/support/"))


@pytest.mark.ac("ACC-5.2", "ACC-5.7", "ACC-1.2")
@pytest.mark.parametrize("count", [1, 2, 19, 20, 21])
def test_create_requester_membership_and_quota_boundaries(creator, monkeypatch, count):
    sender, officer = creator
    if count == 1:
        get_user_model().objects.filter(username=f"requester2-{CODE}").delete()
    else:
        grow(officer, count)
    before = accounts()
    attempts = CountedAttempt.objects.filter(kind=Kind.CREATION).count()
    draws = []

    def forbidden_draw(*args, **kwargs):
        draws.append(True)
        raise AssertionError("Rejected creation must generate no password.")

    with monkeypatch.context() as patch, recording_hashes() as hashed:
        if count not in (2, 19):
            # Django also draws CSRF masks; guard only password generation.
            patch.setattr("deskmate.accounts.demo.random_password", forbidden_draw)
        response = sender.post()
    if count in (2, 19):
        read_success(response, f"requester{count + 1}-{CODE}")
        assert len(hashed) == 1
        assert (
            get_user_model()
            .objects.filter(workspace=officer.workspace, role=auth.REQUESTER)
            .count()
            == count + 1
        )
    else:
        read_form(
            response,
            error=QUOTA if count >= 20 else NONCANONICAL,
            code=CODE if count == 20 else "unavailable",
        )
        assert hashed == draws == [] and accounts() == before
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == attempts + 1


@pytest.mark.ac("ACC-5.2", "ACC-5.4")
def test_create_requester_quota_counts_only_current_workspaces_requesters(creator):
    sender, officer = creator
    grow(officer, 19)
    other = Workspace.objects.create()
    for number in range(1, 21):
        get_user_model().objects.create_user(
            username=f"requester{number}-9hkmnp",
            password=None,
            role=auth.REQUESTER,
            workspace=other,
        )
    get_user_model().objects.create_user(
        username="support1-9hkmnp",
        password=None,
        role=auth.SUPPORT_OFFICER,
        workspace=other,
    )
    before = accounts()
    read_success(sender.post(), f"requester20-{CODE}")
    user = get_user_model().objects.get(username=f"requester20-{CODE}")
    assert user.workspace_id == officer.workspace_id
    after = accounts()
    del after[user.pk]
    assert after == before


@pytest.mark.ac("ACC-5.2", "ACC-1.2")
@pytest.mark.parametrize(
    "fault",
    [
        "extra-requester",
        "extra-officer",
        "gap",
        "leading-zero",
        "mixed",
        "role",
        "support-name",
        "invalid-code",
        "markup",
    ],
)
def test_create_requester_each_noncanonical_partition_rejected_without_draw_or_write(
    creator, make_account, monkeypatch, fault
):
    sender, officer = creator
    users = get_user_model().objects
    second = users.get(username=f"requester2-{CODE}")
    if fault.startswith("extra"):
        make_account(
            "extra",
            auth.PASSWORD,
            auth.REQUESTER if fault == "extra-requester" else auth.SUPPORT_OFFICER,
        )
    elif fault == "role":
        users.filter(pk=second.pk).update(role=auth.SUPPORT_OFFICER)
    elif fault == "support-name":
        users.filter(pk=officer.pk).update(username=f"support2-{CODE}")
    elif fault == "invalid-code":
        for user in users.all():
            users.filter(pk=user.pk).update(
                username=user.username.replace(CODE, "23az9i")
            )
    else:
        name = {
            "gap": f"requester3-{CODE}",
            "leading-zero": f"requester02-{CODE}",
            "mixed": "requester2-9hkmnp",
            "markup": unquote("%3Cscript%3Ealert%281%29%3C%2Fscript%3E"),
        }[fault]
        users.filter(pk=second.pk).update(username=name)
    before = accounts()
    draws = []

    def forbidden_draw(*args, **kwargs):
        draws.append(True)
        raise AssertionError("Noncanonical creation must generate no password.")

    monkeypatch.setattr("deskmate.accounts.demo.random_password", forbidden_draw)
    with recording_hashes() as hashed:
        response = sender.post()
    read_form(response, error=NONCANONICAL, code="unavailable")
    assert "<script>" not in response.content.decode()
    assert hashed == draws == [] and accounts() == before


@pytest.mark.ac("ACC-5.3")
@pytest.mark.parametrize("overlap", [False, True])
def test_create_requester_resubmissions_create_distinct_next_numbered_accounts(
    transactional_db, creator, overlap
):
    sender, _ = creator
    clients = [sender.clone(), sender.clone()]
    barrier = threading.Barrier(2)

    def submit(client):
        try:
            if overlap:
                barrier.wait(10)
            return client.post()
        finally:
            connections.close_all()

    if overlap:
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(submit, clients))
    else:
        responses = [client.post() for client in clients]
    names = [
        Page(response).tables[0][1][0][1]
        for response in responses
        if response.status_code == 200 and Page(response).tables
    ]
    assert sorted(names) == [f"requester3-{CODE}", f"requester4-{CODE}"]
    passwords = [
        read_success(response, name)
        for response, name in zip(responses, names, strict=True)
    ]
    assert len(set(passwords)) == 2
    for name, password in zip(names, passwords, strict=True):
        assert check_password(
            password, get_user_model().objects.get(username=name).password
        )
    read_form(sender.browser.get(CREATE))


@pytest.mark.ac("ACC-5.2", "ACC-5.3")
def test_create_requester_overlapping_19_to_20_allows_and_hashes_only_one(
    transactional_db, creator
):
    sender, officer = creator
    grow(officer, 19)
    clients = [sender.clone(), sender.clone()]
    barrier = threading.Barrier(2)

    def slow(execute, sql, params, many, context):
        time.sleep(0.02)
        return execute(sql, params, many, context)

    def submit(client):
        try:
            with connections["default"].execute_wrapper(slow):
                barrier.wait(10)
                return client.post()
        finally:
            connections.close_all()

    with recording_hashes() as hashed, ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(submit, clients))
    assert sorted(Page(response).title for response in responses) == sorted(
        [FORM, SUCCESS]
    )
    for response in responses:
        if Page(response).title == SUCCESS:
            read_success(response, f"requester20-{CODE}")
        else:
            read_form(response, error=QUOTA)
    assert len(hashed) == 1
    assert (
        get_user_model()
        .objects.filter(workspace=officer.workspace, role=auth.REQUESTER)
        .count()
        == 20
    )


@pytest.mark.ac("ACC-5.4", "ACC-5.5", "ACC-5.7")
@pytest.mark.parametrize("visitor", auth.VISITORS)
@pytest.mark.parametrize("method", auth.METHODS)
@pytest.mark.parametrize("valid_token", [False, True])
def test_create_requester_csrf_method_access_order_and_all_response_headers(
    make_account, visitor, method, valid_token
):
    browser, _ = auth.browser_as(make_account, visitor)
    token = auth.csrf_token(browser, visitor) if valid_token else None
    before, attempts = accounts(), list(CountedAttempt.objects.values())
    with recording_hashes() as hashed:
        response = auth.send(browser, method, CREATE, token)
    protected(response)
    if method not in auth.SAFE_METHODS and not valid_token:
        auth.assert_forbidden(response, auth.FORM_EXPIRED)
    elif method not in {"GET", "POST"}:
        auth.assert_method_not_allowed(response)
    elif visitor is None:
        auth.assert_redirects(response, auth.SIGN_IN)
    elif visitor == auth.REQUESTER:
        auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)
    elif method == "GET":
        read_form(response, code="unavailable")
    else:
        read_form(response, error=NONCANONICAL, code="unavailable")
        assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == 1
    if not (visitor == auth.SUPPORT_OFFICER and method == "POST" and valid_token):
        assert list(CountedAttempt.objects.values()) == attempts
    if response.status_code != 200:
        assert "Workspace:" not in response.content.decode()
    assert hashed == [] and accounts() == before


@pytest.mark.ac("ACC-5.4")
@pytest.mark.parametrize(
    "change", ["role", "workspace", "expired", "deleted", "origin"]
)
def test_create_requester_next_request_uses_current_stored_access_and_session(
    creator, clock, change
):
    sender, officer = creator
    if change == "role":
        get_user_model().objects.filter(pk=officer.pk).update(role=auth.REQUESTER)
    elif change == "workspace":
        get_user_model().objects.filter(pk=officer.pk).update(
            workspace=Workspace.objects.create()
        )
    elif change == "expired":
        clock.set_elapsed(timedelta(hours=8))
    elif change == "deleted":
        officer.delete()
    before = accounts()
    with recording_hashes() as hashed:
        response = auth.send(
            sender.browser,
            "POST",
            CREATE,
            sender.token,
            headers={"Origin": auth.EVIL_ORIGIN} if change == "origin" else {},
        )
    protected(response)
    if change in {"expired", "deleted"}:
        auth.assert_redirects(response, auth.SIGN_IN)
    elif change == "role":
        auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)
    elif change == "origin":
        auth.assert_forbidden(response, auth.FORM_EXPIRED)
    else:
        read_form(response, error=NONCANONICAL, code="unavailable")
    assert hashed == [] and accounts() == before
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == int(
        change == "workspace"
    )


@pytest.mark.ac("ACC-5.4", "ACC-5.5")
def test_create_requester_forged_fields_headers_and_cookies_cannot_choose_any_attribute(
    creator,
):
    sender, officer = creator
    other = Workspace.objects.create()
    escaped = "%3Cscript%3Ealert%281%29%3C%2Fscript%3E"
    fields = {
        "username": unquote(escaped),
        "password": "chosen-password",
        "role": auth.SUPPORT_OFFICER,
        "workspace": other.pk,
        "code": "9hkmnp",
        "count": [0, 99],
        "next": unquote("https%3A%2F%2Fevil.example%2F"),
    }
    sender.browser.cookies["workspace"] = str(other.pk)
    sender.browser.cookies["role"] = auth.REQUESTER
    sender.browser.cookies["code"] = "9hkmnp"
    sender.browser.defaults["HTTP_X_WORKSPACE"] = str(other.pk)
    sender.browser.defaults["HTTP_X_ROLE"] = auth.REQUESTER
    before = accounts()
    response = sender.post(fields=fields, query="?" + urlencode(fields, doseq=True))
    password = read_success(response, f"requester3-{CODE}")
    user = get_user_model().objects.get(username=f"requester3-{CODE}")
    assert user.role == auth.REQUESTER and user.workspace_id == officer.workspace_id
    assert password != fields["password"]
    after = accounts()
    del after[user.pk]
    assert after == before
    assert not get_user_model().objects.filter(workspace=other).exists()
    assert (
        "<script>" not in response.content.decode()
        and unquote(escaped) not in Page(response).text
    )


@pytest.mark.ac("ACC-5.4")
def test_create_requester_uses_access_snapshot_if_stored_caller_changes_during_request(
    creator,
):
    sender, officer = creator
    other = Workspace.objects.create()
    table = connection.ops.quote_name(get_user_model()._meta.db_table)
    changed = []

    def change_after_access(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if (
            not changed
            and sql.lstrip().upper().startswith("SELECT")
            and table in sql
            and officer.pk in (params or ())
        ):
            changed.append(True)
            get_user_model().objects.filter(pk=officer.pk).update(
                username="moved-officer", role=auth.REQUESTER, workspace=other
            )
            # Keep the captured workspace canonical after moving the caller.
            get_user_model().objects.create_user(
                username=officer.username,
                password=None,
                role=auth.SUPPORT_OFFICER,
                workspace_id=officer.workspace_id,
            )
        return result

    with connection.execute_wrapper(change_after_access):
        response = sender.post()
    assert changed, "The stored-account access check was not reached."
    read_success(response, f"requester3-{CODE}")
    assert (
        get_user_model().objects.get(username=f"requester3-{CODE}").workspace_id
        == officer.workspace_id
    )
    auth.assert_forbidden(protected(sender.browser.get(CREATE)), auth.NOT_FOR_YOUR_ROLE)
