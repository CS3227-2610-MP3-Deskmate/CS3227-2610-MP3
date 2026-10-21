"""ACC-5.7: route integration with ACC-3's existing creation mechanism.

The existing ACC-3 suites cover the shared clock, address, storage/privacy,
cleanup and serialization contract; these cases check the new route joins it.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta

import pytest
from django.db import OperationalError, connection, connections

from deskmate.accounts.models import CountedAttempt, Kind
from deskmate.tests import rate_limits as limits
from deskmate.tests import signing_in as auth
from deskmate.tests.hashing import recording_hashes, reporting_hashes_to
from deskmate.tests.password_resets import accounts, protected
from deskmate.tests.requester_creations import (
    CODE,
    NONCANONICAL,
    QUOTA,
    creation_fixture,  # noqa: F401 -- shared fixture.
    grow,
    read_form,
    read_refused,
    read_success,
)
from deskmate.tests.test_rate_limit_failures import this_threads

pytestmark = pytest.mark.ac("ACC-5.7")


@pytest.mark.parametrize("first", ["demo", "requester"])
@pytest.mark.parametrize("scope", ["address-group", "everyone"])
def test_create_requester_and_demo_share_address_and_global_counts_in_both_directions(
    creator, first, scope
):
    sender, _ = creator
    maximum = 3 if scope == "address-group" else 5
    sources = [
        limits.numbered_source(1 if scope == "address-group" else n + 1)
        for n in range(maximum + 1)
    ]
    for number, source in enumerate(sources[:-1], 3):
        if first == "demo":
            limits.assert_allowed(
                limits.Visitor(source).attempt(limits.CREATION), limits.CREATION
            )
        else:
            read_success(sender.post(source=source), f"requester{number}-{CODE}")
    before = accounts()
    attempts = list(CountedAttempt.objects.values())
    with recording_hashes() as hashed:
        if first == "demo":
            read_refused(
                sender.post(
                    source=sources[-1], fields={"username": "private-request-data"}
                ),
                sent=["private-request-data"],
            )
        else:
            limits.assert_refused(
                limits.Visitor(sources[-1]).attempt(limits.CREATION),
                limits.CREATION,
                retry_after=600,
            )
    assert hashed == [] and accounts() == before
    assert list(CountedAttempt.objects.values()) == attempts


@pytest.mark.parametrize("state", ["quota", "noncanonical"])
def test_create_requester_rejections_count_and_refusals_do_not_delay_window(
    creator, clock, state
):
    sender, officer = creator
    if state == "quota":
        grow(officer, 20)
    else:
        officer.username = "noncanonical-officer"
        officer.save(update_fields=["username"])
    before = accounts()
    error, code = (QUOTA, CODE) if state == "quota" else (NONCANONICAL, "unavailable")
    for _ in range(3):
        read_form(sender.post(), error=error, code=code)
    records = list(CountedAttempt.objects.values())
    clock.set_elapsed(timedelta(seconds=599.5))
    with recording_hashes() as hashed:
        read_refused(sender.post(), retry_after=1)
    assert hashed == [] and accounts() == before
    assert list(CountedAttempt.objects.values()) == records
    clock.set_elapsed(timedelta(seconds=600))
    read_form(sender.post(), error=error, code=code)
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == 1


def test_create_requester_count_is_committed_before_hashing_and_other_kinds_unchanged(
    transactional_db, creator
):
    sender, _ = creator
    old = list(CountedAttempt.objects.exclude(kind=Kind.CREATION).values())
    seen = []

    def read_count():
        try:
            return CountedAttempt.objects.filter(kind=Kind.CREATION).count()
        finally:
            connections.close_all()

    def at_hash(password, encoded):
        with ThreadPoolExecutor(1) as pool:
            seen.append(pool.submit(read_count).result(timeout=10))

    with reporting_hashes_to(at_hash):
        read_success(sender.post(), f"requester3-{CODE}")
    assert seen == [1]
    assert list(CountedAttempt.objects.exclude(kind=Kind.CREATION).values()) == old
    assert CountedAttempt.objects.filter(kind=Kind.CREATION).count() == 1


def test_create_requester_counter_database_failure_fails_closed_before_generation(
    transactional_db, creator, monkeypatch
):
    sender, _ = creator
    sender.browser.raise_request_exception = False
    table = connection.ops.quote_name(CountedAttempt._meta.db_table)
    failed, draws = [], []

    def fail_count(execute, sql, params, many, context):
        if sql.lstrip().upper().startswith("INSERT") and table in sql:
            failed.append(True)
            raise OperationalError("synthetic count failure")
        return execute(sql, params, many, context)

    def forbidden_draw(*args, **kwargs):
        draws.append(True)
        raise AssertionError("Failed admission must generate no password.")

    monkeypatch.setattr("secrets.choice", forbidden_draw)
    before = accounts()
    with recording_hashes() as hashed, connection.execute_wrapper(fail_count):
        response = sender.post()
    assert failed, "Creation admission never inserted its counted attempt."
    auth.assert_server_error(protected(response))
    assert hashed == draws == [] and accounts() == before
    assert not CountedAttempt.objects.filter(kind=Kind.CREATION).exists()


def test_create_requester_waiting_on_demo_creation_limit_fails_closed_after_5_seconds(
    transactional_db, creator
):
    sender, _ = creator
    statements = limits.check_statements(
        limits.CREATION, limits.Visitor(limits.numbered_source(200))
    )
    held = limits.HeldCheck(
        limits.CREATION, statements[-1], 15, limits.numbered_source(201)
    )
    before = accounts()
    sender.browser.raise_request_exception = False
    with recording_hashes() as hashed, held.holding():
        started = time.monotonic()
        response = sender.post()
        elapsed = time.monotonic() - started
        auth.assert_server_error(protected(response))
        assert this_threads(hashed) == [] and accounts() == before
        # As in the existing ACC-3 timeout cases, allow scheduling overhead.
        assert elapsed < 10, f"Admission waited {elapsed:.1f}s instead of timing out."
    limits.assert_allowed(held.response, limits.CREATION)


@pytest.mark.parametrize("scope", ["address-group", "everyone"])
def test_create_requester_and_demo_concurrent_admission_share_final_place(
    transactional_db, creator, scope
):
    sender, _ = creator
    count = 2 if scope == "address-group" else 4
    source = limits.numbered_source(1)
    for number in range(count):
        limits.assert_allowed(
            limits.Visitor(
                source
                if scope == "address-group"
                else limits.numbered_source(number + 1)
            ).attempt(limits.CREATION),
            limits.CREATION,
        )
    barrier = threading.Barrier(2)
    client = sender.clone(
        source if scope == "address-group" else limits.numbered_source(10)
    )
    visitor = limits.Visitor(
        source if scope == "address-group" else limits.numbered_source(11)
    )

    def submit(which):
        try:
            barrier.wait(10)
            return (
                client.post()
                if which == "requester"
                else visitor.attempt(limits.CREATION)
            )
        finally:
            connections.close_all()

    with ThreadPoolExecutor(2) as pool:
        responses = list(pool.map(submit, ["requester", "demo"]))
    assert sorted(response.status_code for response in responses) == [200, 429]
    for which, response in zip(["requester", "demo"], responses, strict=True):
        if which == "demo":
            (
                limits.assert_refused
                if response.status_code == 429
                else limits.assert_allowed
            )(response, limits.CREATION)
        elif response.status_code == 429:
            read_refused(response)
        else:
            read_success(response, f"requester3-{CODE}")
