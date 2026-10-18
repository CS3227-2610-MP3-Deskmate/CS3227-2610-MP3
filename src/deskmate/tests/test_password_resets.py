"""ACC-4.1–4.7: reset form, target selection, sessions and failure privacy.

CSPRNG uniformity is the manual ACC-2.8 security review reused by ACC-4.2.
"""

import threading
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import unquote

import pytest
from django.conf import settings as django_settings
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password, identify_hasher
from django.contrib.sessions.models import Session
from django.db import InterfaceError, OperationalError, connection, connections

from deskmate.accounts.models import Workspace
from deskmate.tests import demo_workspaces as demo
from deskmate.tests import signing_in as auth
from deskmate.tests.hashing import recording_hashes, reporting_hashes_to
from deskmate.tests.pages import Page
from deskmate.tests.password_resets import (
    FORM,
    RESET,
    accounts,
    protected,
    read_form,
    read_success,
    reset_fixture,  # noqa: F401 -- shared fixture.
)
from deskmate.tests.test_demo_failures import assert_error_written
from deskmate.tests.test_sign_in import (
    INVALID_USERNAMES,
    TRIM_CODEPOINTS,
    USERNAME_LENGTHS,
)


@pytest.mark.ac("ACC-4.1")
def test_reset_officer_link_opens_empty_form_without_accounts(resetter):
    sender, officer, requester = resetter
    page = Page(sender.browser.get(auth.ROLE_PAGES[auth.SUPPORT_OFFICER]))
    assert (FORM, page.url + "reset-requester-password/") in page.links
    response = sender.browser.get(RESET)
    read_form(response)
    body = response.content.decode()
    assert officer.username not in body and requester.username not in body
    assert "<datalist" not in body.lower()


@pytest.mark.ac("ACC-4.2", "ACC-4.6", "ACC-4.8")
@pytest.mark.parametrize("debug", demo.DEBUG_MODES)
def test_reset_success_changes_only_target_hash_shows_once_and_signs_in(
    resetter, settings, written_output, debug
):
    settings.DEBUG = debug
    sender, officer, target = resetter
    before, sessions = accounts(), demo.signed_in_account_ids()
    with recording_hashes() as hashed:
        response = sender.post(target.username)
    password = read_success(response, target.username)
    assert len(hashed) == 1 and hashed[0].password == password
    target.refresh_from_db()
    assert target.password != before[target.pk]["password"]
    assert identify_hasher(target.password).decode(target.password)["salt"]
    assert check_password(password, target.password)
    before[target.pk]["password"] = target.password
    assert accounts() == before and demo.signed_in_account_ids() == sessions
    assert demo.records_holding([password]) == demo.sessions_holding([password]) == []
    assert not demo.cookies_holding(
        [password], response.cookies, sender.browser.cookies
    )
    sensitive = (target.username, password, target.password)
    assert all(value not in written_output.text() for value in sensitive)
    read_form(sender.browser.get(RESET))
    for path in ("/", "/health/", auth.SIGN_IN, *auth.ROLE_PAGES.values(), RESET):
        assert password not in sender.browser.get(path).content.decode()
    newcomer = auth.new_browser()
    auth.assert_redirects(
        auth.sign_in(newcomer, target.username, password),
        auth.ROLE_PAGES[auth.REQUESTER],
    )
    auth.assert_signed_in_as(newcomer, auth.REQUESTER, target.username)
    auth.assert_signed_in_as(sender.browser, auth.SUPPORT_OFFICER, officer.username)


@pytest.mark.ac("ACC-4.3")
@pytest.mark.parametrize(("typed", "stored"), USERNAME_LENGTHS)
def test_reset_valid_username_boundaries_select_exact_stored_account(
    resetter, make_account, typed, stored
):
    sender, _, _ = resetter
    make_account(stored, auth.PASSWORD, auth.REQUESTER)
    read_success(sender.post(typed), stored)


@pytest.mark.ac("ACC-4.3")
@pytest.mark.parametrize("codepoint", TRIM_CODEPOINTS)
def test_reset_every_specified_whitespace_character_is_trimmed(resetter, codepoint):
    sender, _, target = resetter
    read_success(
        sender.post(chr(codepoint) + target.username + chr(codepoint)), target.username
    )


@pytest.mark.ac("ACC-4.3", "ACC-4.6")
@pytest.mark.parametrize(("escaped", "ascii_name"), INVALID_USERNAMES)
def test_reset_malformed_and_compatibility_usernames_rejected_without_normalising(
    resetter, make_account, escaped, ascii_name
):
    sender, _, target = resetter
    if ascii_name != target.username:
        make_account(ascii_name, auth.PASSWORD, auth.REQUESTER)
    typed = unquote(escaped)
    before = accounts()
    with recording_hashes() as hashed:
        read_form(sender.post(typed), typed.replace("\n", " "), rejected=True)
    assert hashed == [] and accounts() == before


@pytest.mark.ac("ACC-4.3", "ACC-4.6")
@pytest.mark.parametrize(
    "escaped",
    [
        None,
        "",
        "%20%09%E3%80%80",
        "a" * 151,
        "Alice",
        "unknown",
        "ali%E2%80%8Bce",
        "%3Cscript%3Ealert%281%29%3C%2Fscript%3E",
        "%22%3E%3Cimg%20src%3Dx%20onerror%3Dalert%281%29%3E",
        "a%0D%0Ab%0Dc%0Ad%00",
    ],
)
def test_reset_missing_invalid_and_raw_markup_values_have_only_generic_error(
    resetter, escaped
):
    sender, _, _ = resetter
    typed = None if escaped is None else unquote(escaped)
    shown = (
        (typed or "")
        .replace("\r\n", " ")
        .replace("\r", " ")
        .replace("\n", " ")
        .replace("\0", "\ufffd")
    )
    before = accounts(), list(Session.objects.values())
    with recording_hashes() as hashed:
        response = sender.post(typed)
    read_form(response, shown, rejected=True)
    assert (
        "<script>" not in response.content.decode()
        and "<img " not in response.content.decode()
    )
    assert hashed == [] and (accounts(), list(Session.objects.values())) == before


@pytest.mark.ac("ACC-4.3")
@pytest.mark.parametrize(
    "partition", ["unknown", "caller", "other-officer", "other-workspace"]
)
def test_reset_target_ineligible_partitions_share_identical_rejection(
    resetter, make_account, partition
):
    sender, officer, _ = resetter
    name = "officer" if partition == "caller" else "classified"
    baseline = sender.post("classified") if partition != "caller" else None
    if partition == "other-officer":
        make_account(name, auth.PASSWORD, auth.SUPPORT_OFFICER)
    elif partition == "other-workspace":
        user = make_account(name, auth.PASSWORD, auth.REQUESTER)
        user.workspace = Workspace.objects.create()
        user.save(update_fields=["workspace"])
    before = accounts(), list(Session.objects.values())
    response = sender.post(name)
    page = read_form(response, name, rejected=True)
    if baseline is not None:
        expected = baseline.content.decode().replace(
            Page(baseline).csrf_token(), "TOKEN"
        )
        actual = response.content.decode().replace(page.csrf_token(), "TOKEN")
        assert expected == actual
    assert (accounts(), list(Session.objects.values())) == before
    auth.assert_signed_in_as(sender.browser, auth.SUPPORT_OFFICER, officer.username)


@pytest.mark.ac("ACC-4.3", "ACC-4.5")
@pytest.mark.parametrize("last_valid", [False, True])
def test_reset_last_form_value_alone_selects_target_ignoring_query_and_extra_fields(
    resetter, make_account, last_valid
):
    sender, officer, target = resetter
    other = make_account("bob", auth.PASSWORD, auth.REQUESTER)
    before = accounts()
    values = (
        [other.username, target.username]
        if last_valid
        else [target.username, "unknown"]
    )
    fields = {
        "password": auth.PASSWORD,
        "role": auth.SUPPORT_OFFICER,
        "workspace": 9999,
        "user_id": other.pk,
        "next": unquote("https%3A%2F%2Fevil.example%2F"),
    }
    response = sender.post(
        values,
        fields=fields,
        query=unquote(
            "?username=bob&password=chosen&role=requester&workspace=9999&next=%2F%2Fevil.example%2F"
        ),
    )
    if last_valid:
        password = read_success(response, target.username)
        assert password != auth.PASSWORD
        target.refresh_from_db()
        before[target.pk]["password"] = target.password
    else:
        read_form(response, "unknown", rejected=True)
    assert accounts() == before
    auth.assert_signed_in_as(sender.browser, auth.SUPPORT_OFFICER, officer.username)


@pytest.mark.ac("ACC-4.4")
def test_reset_invalidates_all_target_sessions_and_cookie_replays_only(
    resetter, make_account
):
    sender, officer, target = resetter
    browsers = [auth.new_browser(), auth.new_browser()]
    for browser in browsers:
        auth.assert_redirects(
            auth.sign_in(browser, target.username, auth.PASSWORD),
            auth.ROLE_PAGES[auth.REQUESTER],
        )
    cookies = [auth.session_cookie(browser) for browser in browsers]
    other = make_account("bob", auth.PASSWORD, auth.REQUESTER)
    unaffected = auth.new_browser()
    auth.assert_redirects(
        auth.sign_in(unaffected, other.username, auth.PASSWORD),
        auth.ROLE_PAGES[auth.REQUESTER],
    )
    read_success(sender.post(target.username), target.username)
    for browser, cookie in zip(browsers, cookies, strict=True):
        auth.assert_signed_out(browser)
        replay = auth.new_browser()
        replay.cookies[django_settings.SESSION_COOKIE_NAME] = cookie
        auth.assert_signed_out(replay)
    auth.assert_signed_in_as(sender.browser, auth.SUPPORT_OFFICER, officer.username)
    auth.assert_signed_in_as(unaffected, auth.REQUESTER, other.username)
    assert (
        auth.sign_in(auth.new_browser(), target.username, auth.PASSWORD).status_code
        == 200
    )


@pytest.mark.ac("ACC-4.4")
@pytest.mark.parametrize("overlap", [False, True])
def test_reset_resubmissions_each_generate_password_only_last_commit_remains(
    transactional_db, resetter, overlap
):
    sender, _, target = resetter
    clients = [sender.clone(), sender.clone()]
    barrier = threading.Barrier(2)

    def reset(client):
        try:
            if overlap:
                barrier.wait(10)
            return client.post(target.username)
        finally:
            connections.close_all()

    if overlap:
        with ThreadPoolExecutor(2) as pool:
            responses = list(pool.map(reset, clients))
    else:
        responses = [client.post(target.username) for client in clients]
    passwords = [read_success(response, target.username) for response in responses]
    assert len(set(passwords)) == 2
    target.refresh_from_db()
    matches = [check_password(password, target.password) for password in passwords]
    assert matches == [False, True] if not overlap else sum(matches) == 1


@pytest.mark.ac("ACC-4.5", "ACC-4.6")
@pytest.mark.parametrize("visitor", auth.VISITORS)
@pytest.mark.parametrize("method", auth.METHODS)
@pytest.mark.parametrize("valid_token", [False, True])
def test_reset_csrf_method_and_access_checks_precede_target_and_hashing(
    make_account, visitor, method, valid_token
):
    browser, _ = auth.browser_as(make_account, visitor)
    token = auth.csrf_token(browser, visitor) if valid_token else None
    before = accounts()
    with recording_hashes() as hashed:
        response = protected(
            auth.send(browser, method, RESET, token, data={"username": "alice"})
        )
    if method not in {"GET", "HEAD", "OPTIONS", "TRACE"} and not valid_token:
        auth.assert_forbidden(response, auth.FORM_EXPIRED)
    elif method not in {"GET", "POST"}:
        auth.assert_method_not_allowed(response)
    elif visitor is None:
        auth.assert_redirects(response, auth.SIGN_IN)
    elif visitor == auth.REQUESTER:
        auth.assert_forbidden(response, auth.NOT_FOR_YOUR_ROLE)
    elif method == "GET":
        read_form(response)
    else:
        read_form(response, "alice", rejected=True)
    assert hashed == [] and accounts() == before


@pytest.mark.ac("ACC-4.5")
@pytest.mark.parametrize(
    "change", ["role", "workspace", "expired", "deleted", "origin"]
)
def test_reset_next_request_uses_stored_caller_access_and_expiry(
    resetter, settings, clock, change
):
    sender, officer, target = resetter
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
            RESET,
            sender.token,
            data={"username": target.username},
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
        read_form(response, target.username, rejected=True)
    assert hashed == [] and accounts() == before


@pytest.mark.ac("ACC-4.5")
@pytest.mark.parametrize("change", ["deleted", "role", "workspace", "caller"])
def test_reset_target_rechecked_at_update_and_caller_snapshot_kept(resetter, change):
    sender, officer, target = resetter
    table = connection.ops.quote_name(get_user_model()._meta.db_table)
    changed = []

    def mutate(execute, sql, params, many, context):
        selecting_target = sql.lstrip().upper().startswith(
            "SELECT"
        ) and target.username in (params or ())
        updating_target = (
            sql.lstrip().upper().startswith("UPDATE")
            and table in sql
            and '"password"' in sql
        )
        already_executed = False
        result = None
        if not changed and (
            selecting_target if change == "caller" else updating_target
        ):
            changed.append(True)
            if change == "caller":
                result = execute(sql, params, many, context)
                already_executed = True
                get_user_model().objects.filter(pk=officer.pk).update(
                    role=auth.REQUESTER, workspace=Workspace.objects.create()
                )
            elif change == "deleted":
                get_user_model().objects.filter(pk=target.pk).delete()
            elif change == "role":
                get_user_model().objects.filter(pk=target.pk).update(
                    role=auth.SUPPORT_OFFICER
                )
            else:
                get_user_model().objects.filter(pk=target.pk).update(
                    workspace=Workspace.objects.create()
                )
        return result if already_executed else execute(sql, params, many, context)

    sessions = list(Session.objects.values())
    with connection.execute_wrapper(mutate):
        response = sender.post(target.username)
    assert changed, "The target lookup/update was not reached."
    if change == "caller":
        read_success(response, target.username)
        auth.assert_forbidden(sender.browser.get(RESET), auth.NOT_FOR_YOUR_ROLE)
    else:
        read_form(response, target.username, rejected=True)
        if change != "deleted":
            old_hash = target.password
            target.refresh_from_db()
            assert target.password == old_hash
        assert list(Session.objects.values()) == sessions


@pytest.mark.ac("ACC-4.7", "ACC-4.6")
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_reset_database_outage_returns_generic_error_and_preserves_password(
    resetter, database_outage, method
):
    sender, _, target = resetter
    before = accounts(), list(Session.objects.values())
    sender.browser.raise_request_exception = False
    with recording_hashes() as hashed, database_outage():
        response = (
            sender.browser.get(RESET)
            if method == "GET"
            else sender.post(target.username)
        )
    auth.assert_server_error(protected(response))
    assert hashed == [] and (accounts(), list(Session.objects.values())) == before


@pytest.mark.ac("ACC-4.6", "ACC-4.7")
@pytest.mark.parametrize("debug", demo.DEBUG_MODES)
@pytest.mark.parametrize(
    "failure", ["random", "hash", "save", "rolled-back", "interface"]
)
def test_reset_failures_preserve_old_hash_sessions_and_hide_sensitive_logs(
    transactional_db, resetter, monkeypatch, settings, written_output, failure, debug
):
    settings.DEBUG = debug
    sender, _, target = resetter
    previous = auth.new_browser()
    auth.assert_redirects(
        auth.sign_in(previous, target.username, auth.PASSWORD),
        auth.ROLE_PAGES[auth.REQUESTER],
    )
    before = accounts(), list(Session.objects.values())
    sender.browser.raise_request_exception = False
    generated, failed = [], []
    table = connection.ops.quote_name(get_user_model()._meta.db_table)

    def broken_random(*args, **kwargs):
        failed.append(True)
        raise RuntimeError("synthetic random source failure")

    def hashed(password, encoded):
        generated.extend([password, encoded])
        if failure == "hash":
            failed.append(True)
            raise RuntimeError("synthetic hashing failure")

    def broken_save(execute, sql, params, many, context):
        if (
            sql.lstrip().upper().startswith("UPDATE")
            and table in sql
            and '"password"' in sql
        ):
            failed.append(True)
            if failure == "rolled-back":
                execute(sql, params, many, context)
            if failure in {"save", "rolled-back", "interface"}:
                detail = f"Failing row contains ({target.username}, {generated!r})"
                error_type = (
                    InterfaceError if failure == "interface" else OperationalError
                )
                try:
                    raise RuntimeError(detail)
                except RuntimeError as cause:
                    raise error_type(detail) from cause
        return execute(sql, params, many, context)

    with monkeypatch.context() as patch:
        if failure == "random":
            patch.setattr("secrets.choice", broken_random)
        with reporting_hashes_to(hashed), connection.execute_wrapper(broken_save):
            response = sender.post(target.username)
    assert failed, "The requested failure was not reached."
    protected(response)
    hidden = {
        "target username": target.username,
        **{f"generated {n}": value for n, value in enumerate(generated)},
    }
    if not debug:
        auth.assert_server_error(response, hidden)
    else:
        assert response.status_code == 500
    assert (accounts(), list(Session.objects.values())) == before
    auth.assert_signed_in_as(previous, auth.REQUESTER, target.username)
    written = written_output.text()
    assert all(value not in written for value in hidden.values())
    assert_error_written(
        written,
        "InterfaceError"
        if failure == "interface"
        else "OperationalError"
        if failure in {"save", "rolled-back"}
        else "RuntimeError",
    )
