"""PLT-5: durable internal AI admission, without real provider requests."""

import hashlib
import os
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import timedelta
from importlib import import_module
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from django.contrib.auth import get_user
from django.db import DatabaseError, connection, connections, transaction

from deskmate.accounts.limits import check_and_count as account_gate
from deskmate.accounts.models import CountedAttempt, Kind, Role, User, Workspace
from deskmate.knowledge.models import Article
from deskmate.tests import test_llm_probe as probe
from deskmate.tests.demo_workspaces import stored_rows
from deskmate.tests.rate_limits import FailingStatement, recording_statements
from deskmate.tests.signing_in import PASSWORD, new_browser
from deskmate.tickets.models import Ticket

pytestmark = pytest.mark.usefixtures("transactional_db", "clock", "fast_hashing")
AI = "llm_call"
TABLE = CountedAttempt._meta.db_table
ACCOUNT_KINDS = (Kind.SIGN_IN, Kind.CREATION, Kind.RESET)
provider = probe.provider


@pytest.fixture
def gate():
    return import_module("deskmate.llm_limits").check_and_count


@pytest.fixture
def users(make_account):
    accounts = [
        make_account(f"synthetic-ai-{n}", PASSWORD, Role.values[n % 2])
        for n in range(6)
    ]
    other = Workspace.objects.create()
    for user in accounts[2:]:
        user.workspace = other
        user.save(update_fields=["workspace"])
    return accounts


def population(users, scope):
    return [users[0]] * 10 if scope == "user" else users[:3] * 10


def admit(gate, accounts):
    for user in accounts:
        assert gate(user) is None


def rows():
    return list(CountedAttempt.objects.order_by("pk").values())


def together(calls):
    barrier, pids = threading.Barrier(len(calls)), []

    def run(call):
        try:
            with connections["default"].cursor() as cursor:
                cursor.execute("SELECT pg_backend_pid()")
                pids.append(cursor.fetchone()[0])
            barrier.wait(15)
            with connections["default"].execute_wrapper(slow):
                return call()
        finally:
            connections.close_all()

    def slow(execute, sql, params, many, context):
        time.sleep(0.02)
        return execute(sql, params, many, context)

    with ThreadPoolExecutor(max_workers=len(calls)) as pool:
        results = list(pool.map(run, calls))
    assert len(set(pids)) == len(calls)
    return results


@contextmanager
def holding(call):
    stopped, released = threading.Event(), threading.Event()

    def stop(execute, sql, params, many, context):
        result = execute(sql, params, many, context)
        if sql.startswith("INSERT INTO") and TABLE in sql:
            stopped.set()
            assert released.wait(20), "The test did not release the held admission."
        return result

    def run():
        try:
            with connections["default"].execute_wrapper(stop):
                return call()
        finally:
            connections.close_all()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(run)
        try:
            assert stopped.wait(10), "The held admission never inserted its count."
            yield
        finally:
            released.set()
            assert future.result(timeout=10) is None


@pytest.mark.ac("PLT-5.1", "PLT-5.2", "PLT-5.4")
@pytest.mark.parametrize("scope", ["user", "app"])
def test_llm_limits_below_limit_admits_last_then_refuses(gate, users, scope):
    accounts = population(users, scope)
    admit(gate, accounts[:-1])
    assert len(rows()) == len(accounts) - 1
    admit(gate, accounts[-1:])
    before = rows()
    for _ in range(2):
        delay = gate(users[0] if scope == "user" else users[3])
        assert type(delay) is int and delay == 600
        assert rows() == before


@pytest.mark.ac("PLT-5.2", "PLT-5.3")
@pytest.mark.parametrize("scope", ["user", "app"])
@pytest.mark.parametrize(
    "elapsed,expected", [(599.5, 1), (599.999999, 1), (600, None), (600.000001, None)]
)
def test_llm_limits_rolling_boundary_rounds_up(
    gate, users, clock, scope, elapsed, expected
):
    admit(gate, population(users, scope))
    clock.set_elapsed(timedelta(seconds=elapsed))
    assert gate(users[0] if scope == "user" else users[3]) == expected


@pytest.mark.ac("PLT-5.2", "PLT-5.3")
@pytest.mark.parametrize("scope", ["user", "app"])
def test_llm_limits_spread_attempts_free_only_one_place_at_a_time(
    gate, users, clock, scope
):
    for n, user in enumerate(population(users, scope)):
        clock.set_elapsed(timedelta(seconds=n))
        admit(gate, [user])
    target = users[0] if scope == "user" else users[3]
    clock.set_elapsed(timedelta(seconds=600))
    admit(gate, [target])
    assert gate(target) == 1


@pytest.mark.ac("PLT-5.1", "PLT-5.2", "PLT-5.3")
def test_llm_limits_retry_waits_for_both_allowances(gate, users, clock):
    admit(gate, users[1:3] * 10)
    clock.set_elapsed(timedelta(seconds=100.25))
    admit(gate, [users[0]] * 10)
    clock.set_elapsed(timedelta(seconds=200))
    assert gate(users[0]) == 501
    assert gate(users[3]) == 400
    clock.set_elapsed(timedelta(seconds=600))
    assert gate(users[0]) == 101
    admit(gate, [users[3]])
    clock.set_elapsed(timedelta(seconds=700.25))
    admit(gate, [users[0]])


@pytest.mark.ac("PLT-5.3")
@pytest.mark.parametrize("scope", ["user", "app"])
def test_llm_limits_backwards_clock_uses_latest_ai_moment(gate, users, clock, scope):
    clock.set_elapsed(timedelta(seconds=300))
    accounts = population(users, scope)
    admit(gate, accounts[:-1])
    clock.set_elapsed(timedelta(seconds=-1000))
    admit(gate, accounts[-1:])
    target = users[0] if scope == "user" else users[3]
    assert gate(target) == 600
    assert {row["counted_at"] for row in rows()} == {
        clock.start + timedelta(seconds=300)
    }
    clock.set_elapsed(timedelta(seconds=899.5))
    assert gate(target) == 1
    clock.set_elapsed(timedelta(seconds=900))
    admit(gate, [target])


@pytest.mark.ac("PLT-5.4")
def test_llm_limits_identity_survives_sessions_and_attribute_changes(gate, users):
    browsers = [new_browser(), new_browser()]
    for browser in browsers:
        browser.force_login(users[0])
    assert browsers[0].session.session_key != browsers[1].session.session_key
    for n in range(10):
        admit(gate, [get_user(SimpleNamespace(session=browsers[n % 2].session))])
    user = users[0]
    user.username, user.role, user.workspace = (
        "renamed-ai",
        Role.SUPPORT_OFFICER,
        users[2].workspace,
    )
    user.save(update_fields=["username", "role", "workspace"])
    assert gate(User.objects.get(pk=user.pk)) == 600
    admit(gate, [users[1]])


@pytest.mark.ac("PLT-5.1")
def test_llm_limits_admission_commits_before_downstream_failure(gate, users):
    for _ in range(10):
        with pytest.raises(RuntimeError, match="downstream"):
            assert gate(users[0]) is None
            with transaction.atomic():
                raise RuntimeError("synthetic downstream failure")
    connection.close()
    assert CountedAttempt.objects.filter(kind=AI).count() == 10
    assert gate(users[0]) == 600


@pytest.mark.ac("PLT-5.5")
@pytest.mark.parametrize("scope", ["user", "app"])
def test_llm_limits_five_overlapping_checks_admit_exactly_one(gate, users, scope):
    seeded = [users[0]] * 9 if scope == "user" else (users * 5)[:-1]
    admit(gate, seeded)
    contenders = [users[0]] * 5 if scope == "user" else users[1:6]
    results = together([lambda user=user: gate(user) for user in contenders])
    assert results.count(None) == 1 and results.count(600) == 4, results
    assert len(rows()) == (10 if scope == "user" else 30)


@pytest.mark.ac("PLT-5.6", "PLT-5.8")
def test_llm_limits_prunes_only_ai_and_preserves_product_data(gate, users, clock):
    Ticket.objects.create(
        workspace=users[0].workspace, title="Synthetic", description="Body"
    )
    Article.objects.create(workspace=users[0].workspace, title="Synthetic", body="Body")
    admit(gate, [users[0]])
    for kind in ACCOUNT_KINDS:
        CountedAttempt.objects.create(kind=kind, group="a" * 64, counted_at=clock.start)
    account_rows = rows()[1:]
    before = stored_rows()
    clock.set_elapsed(timedelta(seconds=600))
    admit(gate, [users[0]])
    assert (
        list(CountedAttempt.objects.exclude(kind=AI).order_by("pk").values())
        == account_rows
    )
    assert list(
        CountedAttempt.objects.filter(kind=AI).values_list("counted_at", flat=True)
    ) == [clock.now]
    after = stored_rows()
    assert {k: v for k, v in before.items() if k != TABLE} == {
        k: v for k, v in after.items() if k != TABLE
    }


@pytest.mark.ac("PLT-5.6", "PLT-5.8")
def test_llm_limits_private_keyed_identity_without_provider_or_credential_access(
    gate, users, settings, monkeypatch, written_output
):
    original = type(os.environ).__getitem__

    def guarded(environment, name):
        assert not name.startswith("SOC_LLM_"), "The gate read provider configuration."
        return original(environment, name)

    monkeypatch.setattr(type(os.environ), "__getitem__", guarded)
    no_provider = Mock(side_effect=AssertionError("The gate contacted a provider."))
    monkeypatch.setattr("deskmate.llm.urlopen", no_provider)
    settings.SECRET_KEY = "synthetic-ai-key-a"
    admit(gate, [users[0], users[0], users[1]])
    settings.SECRET_KEY = "synthetic-ai-key-b"
    admit(gate, [users[0]])
    groups = [row["group"] for row in rows()]
    assert groups[0] == groups[1] and len(set(groups)) == 3
    assert all(re.fullmatch("[0-9a-f]{64}", group) for group in groups)
    assert groups[0] != hashlib.sha256(str(users[0].pk).encode()).hexdigest()
    assert all(
        set(row) == {"id", "kind", "group", "counted_at"} and row["kind"] == AI
        for row in rows()
    )
    output = written_output.text()
    assert all(
        value not in output
        for value in [users[0].username, PASSWORD, settings.SECRET_KEY]
    )
    no_provider.assert_not_called()


@pytest.mark.ac("PLT-5.7")
def test_llm_limits_database_outage_raises_without_count(gate, users, database_outage):
    before = rows()
    with database_outage(), pytest.raises(DatabaseError):
        gate(users[0])
    assert rows() == before


@pytest.mark.ac("PLT-5.7")
def test_llm_limits_each_database_statement_failure_rolls_back(gate, users):
    with recording_statements() as statements:
        admit(gate, [users[0]])
    for number in range(len(statements)):
        before, failing = rows(), FailingStatement(number)
        with connection.execute_wrapper(failing), pytest.raises(DatabaseError):
            gate(users[1])
        assert failing.failed is not None
        assert rows() == before


@pytest.mark.ac("PLT-5.6", "PLT-5.7")
@pytest.mark.parametrize("lost_acknowledgement", [False, True])
def test_llm_limits_commit_failure_never_grants_admission(
    gate, users, clock, monkeypatch, lost_acknowledgement
):
    admit(gate, [users[0]])
    before, commit = rows(), connection._commit
    clock.set_elapsed(timedelta(seconds=600))

    def fail_commit():
        if lost_acknowledgement:
            commit()
        raise DatabaseError("synthetic commit failure")

    with monkeypatch.context() as patch:
        patch.setattr(connection, "_commit", fail_commit)
        with pytest.raises(DatabaseError):
            gate(users[1])
    if lost_acknowledgement:
        assert len(rows()) == 1 and rows()[0]["counted_at"] == clock.now
    else:
        assert rows() == before


@pytest.mark.ac("PLT-5.7")
def test_llm_limits_waiting_five_seconds_raises_without_admission(gate, users):
    with holding(lambda: gate(users[0])):
        started = time.monotonic()
        with pytest.raises(DatabaseError):
            gate(users[1])
        assert 4 <= time.monotonic() - started < 9
    assert len(rows()) == 1


@pytest.mark.ac("PLT-5.3", "PLT-5.8")
@pytest.mark.parametrize("kind", ACCOUNT_KINDS)
def test_llm_limits_account_kinds_are_independent(gate, users, clock, kind):
    request = SimpleNamespace(META={"REMOTE_ADDR": "203.0.113.7"})

    def account():
        return account_gate(request, kind)

    with holding(account):
        admit(gate, [users[0]])
    clock.set_elapsed(timedelta(seconds=300))
    with holding(lambda: gate(users[0])):
        assert account() is None
    clock.set_elapsed(timedelta(seconds=600))
    assert account() is None
    clock.set_elapsed(timedelta(seconds=0))
    # AI clamps to moment 300, while this account kind clamps to 600.
    # Their oldest attempts expire at 600 and 900: each delay is 300 seconds.
    admit(gate, [users[0]] * 8)
    assert gate(users[0]) == 300
    assert account() is None
    assert account() == (300 if kind != Kind.SIGN_IN else None)


@pytest.mark.ac("PLT-5.8", "PLT-3.5")
def test_llm_limits_exhaustion_leaves_operator_probe_database_independent(
    gate, users, client, provider, database_outage
):
    admit(gate, population(users, "app"))
    assert gate(users[3]) == 600
    before = rows()
    with database_outage():
        response = probe.get_probe(client, {"Authorization": f"Bearer {probe.TOKEN}"})
        probe.assert_probe(response, 200, {"status": "ok"})
    assert len(provider.requests) == 1 and rows() == before
