"""ACC-5.3, ACC-5.5–5.6: global collisions, atomic writes and failure privacy."""

from concurrent.futures import ThreadPoolExecutor

import pytest
from django.contrib.auth import get_user_model
from django.contrib.sessions.models import Session
from django.db import InterfaceError, OperationalError, connection, connections
from django.template.base import Template

from deskmate.accounts.models import CountedAttempt, Kind, Workspace
from deskmate.tests import demo_workspaces as demo
from deskmate.tests import signing_in as auth
from deskmate.tests.hashing import recording_hashes, reporting_hashes_to
from deskmate.tests.password_resets import accounts, protected
from deskmate.tests.requester_creations import (
    CODE,
    CREATE,
    creation_fixture,  # noqa: F401 -- shared fixture.
    read_form,
    read_success,
)
from deskmate.tests.test_demo_failures import assert_error_written


@pytest.mark.ac("ACC-5.3", "ACC-5.5", "ACC-5.6", "ACC-5.7")
@pytest.mark.parametrize("when", ["before", "meanwhile"])
@pytest.mark.parametrize("debug", demo.DEBUG_MODES)
def test_create_requester_global_collision_fails_without_retry_or_overwrite(
    transactional_db, creator, settings, written_output, when, debug
):
    settings.DEBUG = debug
    sender, _ = creator
    username = f"requester3-{CODE}"
    other = Workspace.objects.create()
    users = get_user_model().objects
    existing = []

    def take_username():
        try:
            user = users.create_user(
                username=username,
                password=None,
                role=auth.SUPPORT_OFFICER,
                workspace=other,
            )
            existing.append(user.pk)
        finally:
            connections.close_all()

    if when == "before":
        # Use the same independent commit as the simultaneous-clash case.
        with ThreadPoolExecutor(1) as pool:
            pool.submit(take_username).result(timeout=10)
    before, sessions = accounts(), list(Session.objects.values())
    table = connection.ops.quote_name(get_user_model()._meta.db_table)
    inserted = []

    def collide(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("INSERT") and table in sql:
            inserted.append(sql)
            if when == "meanwhile" and not existing:
                with ThreadPoolExecutor(1) as pool:
                    pool.submit(take_username).result(timeout=10)
        return execute(sql, params, many, context)

    sender.browser.raise_request_exception = False
    with recording_hashes() as hashed, connection.execute_wrapper(collide):
        response = sender.post()
    protected(response)
    if debug:
        assert response.status_code == 500
    else:
        auth.assert_server_error(
            response,
            {
                "next username": username,
                **{
                    f"credential {i}": value
                    for i, value in enumerate(
                        value
                        for entry in hashed
                        for value in (entry.password, entry.encoded)
                    )
                },
            },
        )
    assert existing and (when == "before" or inserted)
    after = accounts()
    collision = after[existing[0]]
    assert (
        collision["workspace_id"] == other.pk
        and collision["role"] == auth.SUPPORT_OFFICER
    )
    if when == "meanwhile":
        del after[existing[0]]
    assert after == before and list(Session.objects.values()) == sessions
    assert len(hashed) <= 1 and len(inserted) <= 1
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == 1
    hidden = [
        username,
        *(value for entry in hashed for value in (entry.password, entry.encoded)),
    ]
    assert all(value not in written_output.text() for value in hidden)
    if when == "meanwhile":
        assert_error_written(written_output.text(), "IntegrityError")


@pytest.mark.ac("ACC-5.5", "ACC-5.6")
@pytest.mark.parametrize("method", ["GET", "POST"])
def test_create_requester_database_outage_returns_generic_500_without_changes(
    creator, database_outage, method
):
    sender, _ = creator
    before = accounts(), list(Session.objects.values())
    sender.browser.raise_request_exception = False
    with recording_hashes() as hashed, database_outage():
        response = sender.browser.get(CREATE) if method == "GET" else sender.post()
    auth.assert_server_error(protected(response))
    assert "Workspace:" not in response.content.decode()
    assert hashed == [] and (accounts(), list(Session.objects.values())) == before


@pytest.mark.ac("ACC-5.5", "ACC-5.6", "ACC-5.7")
@pytest.mark.parametrize("debug", demo.DEBUG_MODES)
@pytest.mark.parametrize(
    "failure", ["random", "hash", "save", "rolled-back", "interface"]
)
def test_create_requester_failures_roll_back_accounts_and_sanitize_generated_values(
    transactional_db, creator, monkeypatch, settings, written_output, failure, debug
):
    settings.DEBUG = debug
    sender, _ = creator
    before, sessions = accounts(), list(Session.objects.values())
    sender.browser.raise_request_exception = False
    generated, failed = [], []
    username = f"requester3-{CODE}"
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
        if sql.lstrip().upper().startswith("INSERT") and table in sql:
            failed.append(True)
            if failure == "rolled-back":
                execute(sql, params, many, context)
            detail = f"Failing row contains ({username}, {generated!r})"
            error_type = InterfaceError if failure == "interface" else OperationalError
            try:
                raise RuntimeError(detail)
            except RuntimeError as cause:
                raise error_type(detail) from cause
        return execute(sql, params, many, context)

    with monkeypatch.context() as patch:
        if failure == "random":
            patch.setattr("deskmate.accounts.demo.random_password", broken_random)
        with reporting_hashes_to(hashed), connection.execute_wrapper(broken_save):
            response = sender.post()
    assert failed, "The requested failure was not reached."
    protected(response)
    hidden = {
        "next username": username,
        **{f"generated {i}": value for i, value in enumerate(generated)},
    }
    if debug:
        assert response.status_code == 500
    else:
        auth.assert_server_error(response, hidden)
    assert accounts() == before and list(Session.objects.values()) == sessions
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == 1
    assert (
        demo.records_holding(generated[:1])
        == demo.sessions_holding(generated[:1])
        == []
    )
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


@pytest.mark.ac("ACC-5.3", "ACC-5.5", "ACC-5.6", "ACC-5.7")
def test_create_requester_render_failure_keeps_account_without_password_recovery(
    transactional_db, creator, monkeypatch, written_output
):
    sender, _ = creator
    sender.browser.raise_request_exception = False
    render = Template.render
    failed = []

    def fail_success(template, context):
        # Fail at Django's render boundary only once the account is committed.
        if (
            get_user_model().objects.filter(username=f"requester3-{CODE}").exists()
            and not failed
        ):
            assert not connection.in_atomic_block, "Success was rendered before commit."
            failed.append(True)
            raise RuntimeError("synthetic success-page rendering failure")
        return render(template, context)

    with monkeypatch.context() as patch, recording_hashes() as hashed:
        patch.setattr(Template, "render", fail_success)
        response = sender.post()
    assert failed, "The post-commit rendering failure was not reached."
    auth.assert_server_error(protected(response))
    assert len(hashed) == 1
    first = get_user_model().objects.get(username=f"requester3-{CODE}")
    assert first.password == hashed[0].encoded
    read_form(sender.browser.get(CREATE))
    response = sender.post()
    password = read_success(response, f"requester4-{CODE}")
    assert password != hashed[0].password
    for path in (CREATE, "/support/", auth.SIGN_IN):
        assert hashed[0].password not in sender.browser.get(path).content.decode()
    assert hashed[0].password not in response.content.decode()
    assert (
        demo.records_holding([hashed[0].password])
        == demo.sessions_holding([hashed[0].password])
        == []
    )
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == 2
    assert all(
        value not in written_output.text()
        for value in (first.username, hashed[0].password, first.password)
    )
