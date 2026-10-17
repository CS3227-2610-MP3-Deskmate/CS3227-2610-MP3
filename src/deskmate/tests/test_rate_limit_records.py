"""ACC-3.6: attempts that arrive together, limits that every server instance
shares, and what the limits store.

Attempts that arrive together come from threads, each with its own database
connection, as from separate server instances; another instance is also
started as a new process. The limits' records are found without naming them:
they are the rows that counting an attempt adds to tables other than those of
accounts and workspaces. The clock is stopped unless a test moves it, so
attempts released together are all counted at one moment; a test that moves it
backwards checks the moment of ACC-3.8 at which an attempt is counted.
"""

import base64
import ipaddress
from datetime import timedelta

import pytest
from django.conf import settings as django_settings

from deskmate.tests.demo_workspaces import stored_rows
from deskmate.tests.environment import make_secret_key
from deskmate.tests.rate_limits import (
    ADDRESS,
    CREATION,
    EVERYONE,
    KINDS,
    OTHER_KIND,
    PER_GROUP,
    SIGN_IN_ATTEMPT,
    Visitor,
    added_rows,
    assert_allowed,
    assert_refused,
    attempts_together,
    forwarded_for,
    make_attempts,
    make_attempts_from_many,
    numbered_source,
    sign_in_attempts_in_new_process,
    table_records,
)

pytestmark = pytest.mark.usefixtures("fast_hashing", "clock")

TOGETHER = 5
# Synthetic values a request sends, which no record may hold.
USERNAME = "probe-user-5e1c"
PASSWORD = "Probe pass 7f3a"
# Client addresses, each with the address before it in X-Forwarded-For.
STORED_ADDRESSES = [
    pytest.param("203.0.113.7", id="ipv4"),
    pytest.param("2001:db8:0:1::1", id="ipv6"),
    pytest.param("::ffff:203.0.113.7", id="ipv4-mapped"),
    pytest.param("probe-host-9f2", id="not-valid"),
]
EARLIER_ADDRESS = "198.51.100.23"


def encodings(label, value):
    """Return, by description, `value`, a string, as text and as its UTF-8
    bytes in hexadecimal and base64."""
    data = value.encode()
    return {
        f"{label} as text": value,
        f"{label} in hexadecimal": data.hex(),
        f"{label} in base64": base64.b64encode(data).decode().rstrip("="),
    }


def packed_encodings(label, data):
    """Return, by description, the bytes `data` in hexadecimal, base64 and
    URL-safe base64, and as a decimal number."""
    return {
        f"{label} packed, in hexadecimal": data.hex(),
        f"{label} packed, in base64": base64.b64encode(data).decode().rstrip("="),
        f"{label} packed, in URL-safe base64": (
            base64.urlsafe_b64encode(data).decode().rstrip("=")
        ),
        f"{label} packed, as a number": str(int.from_bytes(data)),
    }


def address_encodings(label, text):
    """Return, by description, the client address `text` and its address
    group in every encoding the tests look for."""
    values = encodings(label, text)
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return values
    values.update(packed_encodings(label, address.packed))
    if isinstance(address, ipaddress.IPv4Address):
        return values
    values[f"{label}, exploded"] = address.exploded
    if address.ipv4_mapped:
        # Its group is that of the IPv4 address it holds (ACC-3.5).
        mapped = address_encodings(f"{label}'s IPv4", str(address.ipv4_mapped))
        return {**values, **mapped}
    group = ipaddress.IPv6Network((int(address) >> 64 << 64, 64)).network_address
    values.update(encodings(f"{label}'s group", str(group)))
    values[f"{label}'s group, exploded"] = group.exploded[:19]
    values.update(packed_encodings(f"{label}'s group", group.packed[:8]))
    return values


def found(rows, values):
    """Return each `(table, description)` for which a row of `rows`, pairs of
    a table and a row's text, holds a value of `values`, ignoring case for
    every encoding but base64."""
    hits = []
    for table, text in rows:
        for label, value in values.items():
            exact = "base64" in label
            if (value in text) if exact else (value.lower() in text.lower()):
                hits.append((table, label))
    return hits


def limit_tables(kind):
    """Count one allowed attempt of `kind` from a new address group, and return
    the tables it added rows to, apart from accounts and workspaces."""
    before = stored_rows()
    assert_allowed(Visitor(numbered_source(254)).attempt(kind), kind)
    tables = {table for table, _ in added_rows(before)}
    assert tables, "Counting an attempt stored no record."
    return tables


def records(tables):
    """Return every row of `tables`, as a sorted tuple of (column, value)."""
    return {
        (table, tuple(sorted(row.items(), key=lambda item: item[0])))
        for table in tables
        for row in table_records(table)
    }


def counted_record(tables, kind, source):
    """Count an allowed attempt of `kind` from `source`, and return the one
    record of `tables` it added, as a dict from columns' names to values."""
    before = records(tables)
    assert_allowed(Visitor(source).attempt(kind), kind)
    added = records(tables) - before
    assert len(added) == 1, f"Counting an attempt added {len(added)} records."
    return dict(next(iter(added))[1])


@pytest.mark.ac("ACC-3.6")
def test_limit_5_sign_in_attempts_together_after_9_allow_exactly_1(transactional_db):
    source = forwarded_for(ADDRESS)
    make_attempts(SIGN_IN_ATTEMPT, PER_GROUP[SIGN_IN_ATTEMPT] - 1, source)
    responses = attempts_together(SIGN_IN_ATTEMPT, [source] * TOGETHER)
    statuses = [response.status_code for response in responses]
    assert statuses.count(429) == TOGETHER - 1, statuses
    for response in responses:
        if response.status_code == 429:
            assert_refused(response, SIGN_IN_ATTEMPT)
        else:
            assert_allowed(response, SIGN_IN_ATTEMPT)


@pytest.mark.ac("ACC-3.6")
def test_limit_5_creations_together_from_new_groups_after_4_allow_exactly_1(
    transactional_db,
):
    make_attempts_from_many(CREATION, EVERYONE[CREATION] - 1)
    sources = [numbered_source(100 + number) for number in range(TOGETHER)]
    responses = attempts_together(CREATION, sources)
    statuses = [response.status_code for response in responses]
    assert statuses.count(429) == TOGETHER - 1, statuses
    for response in responses:
        if response.status_code == 429:
            assert_refused(response, CREATION)
        else:
            assert_allowed(response, CREATION)


@pytest.mark.ac("ACC-3.6")
def test_limit_counts_shared_with_another_server_instance(transactional_db):
    source = forwarded_for(ADDRESS)
    visitor = make_attempts(SIGN_IN_ATTEMPT, PER_GROUP[SIGN_IN_ATTEMPT] - 1, source)
    assert sign_in_attempts_in_new_process(2, ADDRESS) == [200, 429]
    assert_refused(visitor.attempt(SIGN_IN_ATTEMPT), SIGN_IN_ATTEMPT)


@pytest.mark.ac("ACC-3.6")
@pytest.mark.parametrize("address", STORED_ADDRESSES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_records_hold_nothing_the_request_sent(db, kind, address):
    visitor = Visitor(forwarded_for(f"{EARLIER_ADDRESS}, {address}"))
    before = stored_rows()
    assert_allowed(visitor.attempt(kind, USERNAME, PASSWORD), kind)
    added = added_rows(before)
    assert added, "Counting the attempt stored no record."
    values = {
        **address_encodings("the client address", address),
        **address_encodings("the earlier address", EARLIER_ADDRESS),
        **encodings("the username", USERNAME),
        **encodings("the password", PASSWORD),
        **encodings("the CSRF token", visitor.token),
        **encodings(
            "the CSRF cookie",
            visitor.browser.cookies[django_settings.CSRF_COOKIE_NAME].value,
        ),
    }
    assert found(added, values) == []


@pytest.mark.ac("ACC-3.6")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_records_of_same_group_change_with_secret_key(db, clock, settings, kind):
    tables = limit_tables(kind)
    source = forwarded_for(ADDRESS)
    first = counted_record(tables, kind, source)
    second = counted_record(tables, kind, source)
    settings.SECRET_KEY = make_secret_key()
    third = counted_record(tables, kind, source)
    # The columns that two attempts from one group, at one moment, share.
    shared = [name for name in first if first[name] == second[name]]
    assert any(third[name] != first[name] for name in shared), (
        "What is stored for the address group did not change with the key."
    )


@pytest.mark.ac("ACC-3.6")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_counting_deletes_own_kind_records_counted_10_minutes_before(
    db, clock, kind
):
    tables = limit_tables(kind)
    make_attempts(kind, 1, forwarded_for(ADDRESS))
    old = records(tables)
    clock.set_elapsed(timedelta(minutes=10))
    assert_allowed(Visitor(forwarded_for("198.51.100.30")).attempt(kind), kind)
    remaining = old & records(tables)
    assert not remaining, f"{len(remaining)} records 10 minutes old remain."


@pytest.mark.ac("ACC-3.6")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_counting_leaves_other_kind_records_counted_10_minutes_before(
    db, clock, kind
):
    other = OTHER_KIND[kind]
    tables = limit_tables(other)
    make_attempts(other, 1, forwarded_for(ADDRESS))
    old = records(tables)
    clock.set_elapsed(timedelta(minutes=10))
    assert_allowed(Visitor(forwarded_for("198.51.100.30")).attempt(kind), kind)
    gone = old - records(tables)
    assert not gone, f"{len(gone)} records of the other kind were changed or deleted."


@pytest.mark.ac("ACC-3.6")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_records_kept_under_10_minutes_still_count(db, clock, kind):
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    clock.set_elapsed(timedelta(minutes=10) - timedelta(microseconds=1))
    assert_allowed(Visitor(forwarded_for("198.51.100.30")).attempt(kind), kind)
    assert_refused(visitor.attempt(kind), kind, retry_after=1)


@pytest.mark.ac("ACC-3.6", "ACC-3.8")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_clock_back_attempt_stored_at_latest_counted_time(db, clock, kind):
    tables = limit_tables(kind)
    early = counted_record(tables, kind, numbered_source(1))
    clock.set_elapsed(timedelta(seconds=100))
    latest = counted_record(tables, kind, numbered_source(2))
    alike = counted_record(tables, kind, numbered_source(3))
    # The columns that two attempts at one moment share, and that differ from
    # an attempt's at another moment: when an attempt was counted.
    timed = [name for name in latest if latest[name] == alike[name] != early[name]]
    assert timed, "No record says when its attempt was counted."
    clock.set_elapsed(timedelta(seconds=40))
    after = counted_record(tables, kind, numbered_source(4))
    assert {name: after[name] for name in timed} == {
        name: latest[name] for name in timed
    }, "The attempt was counted at the clock's earlier time, not the latest's."


@pytest.mark.ac("ACC-3.3", "ACC-3.6", "ACC-3.8")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_clock_back_after_10_minutes_records_gone_attempts_uncounted(
    db, clock, kind
):
    tables = limit_tables(kind)
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    old = records(tables)
    clock.set_elapsed(timedelta(seconds=601))
    assert_allowed(Visitor(forwarded_for("198.51.100.30")).attempt(kind), kind)
    clock.set_elapsed(timedelta(seconds=500))
    # Its moment is 601 s, 10 minutes or more after ADDRESS's attempts, so
    # they neither remain nor count, though the clock says 500 s.
    assert_allowed(visitor.attempt(kind), kind)
    remaining = old & records(tables)
    assert not remaining, f"{len(remaining)} records 10 minutes old remain."


@pytest.mark.ac("ACC-3.3", "ACC-3.6", "ACC-3.8")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_clock_back_other_kind_moment_leaves_records_that_still_count(
    db, clock, kind
):
    other = OTHER_KIND[kind]
    clock.set_elapsed(timedelta(seconds=601))
    assert_allowed(Visitor(numbered_source(1)).attempt(other), other)
    clock.set_elapsed(timedelta(seconds=0))
    tables = limit_tables(kind)
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    old = records(tables)
    clock.set_elapsed(timedelta(seconds=500))
    # The other kind's moment is 601 s, 10 minutes after this kind's records,
    # but it deletes none of them.
    assert_allowed(Visitor(numbered_source(2)).attempt(other), other)
    gone = old - records(tables)
    assert not gone, f"The other kind's attempt changed or deleted {len(gone)} records."
    # This kind's moment is the clock's 500 s, so the attempts at 0 s count.
    assert_refused(visitor.attempt(kind), kind, retry_after=100)
