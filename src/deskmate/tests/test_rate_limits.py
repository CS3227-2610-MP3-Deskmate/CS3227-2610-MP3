"""ACC-3.1 to ACC-3.3: the limits on sign-in attempts and creations, the 429
that refuses an attempt, and the 10 minutes an attempt counts for.

Every test stops the clock, so each attempt is counted at the moment the test
chooses; tests that move it backwards check ACC-3.8's moment, the later of the
clock and the latest attempt of its kind already counted. Unless a test says
otherwise, attempts come from ADDRESS, as the last entry of X-Forwarded-For,
and sign-in attempts use an unknown username.
"""

from datetime import timedelta
from urllib.parse import unquote

import pytest

from deskmate.tests.demo_workspaces import (
    assert_created,
    assert_nothing_created,
    signed_in_account_ids,
    stored_state,
)
from deskmate.tests.hashing import recording_hashes, reporting_hashes_to
from deskmate.tests.helpers import cache_directives
from deskmate.tests.rate_limits import (
    ADDRESS,
    CREATION,
    EVERYONE,
    KINDS,
    PER_GROUP,
    SIGN_IN_ATTEMPT,
    Visitor,
    assert_allowed,
    assert_refused,
    fill,
    forwarded_for,
    limit_of,
    make_attempts,
    make_attempts_from_many,
    numbered_source,
)
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    assert_redirects,
    assert_signed_in_as,
    assert_signed_out,
)

pytestmark = pytest.mark.usefixtures("db", "fast_hashing")

SCOPES = ["address-group", "everyone"]
OTHER_KIND = {SIGN_IN_ATTEMPT: CREATION, CREATION: SIGN_IN_ATTEMPT}
# (seconds after the limit was reached, Retry-After or None if allowed), at
# and around the end of the 10 minutes (ACC-3.3).
WINDOW_EDGES = [
    pytest.param(0, 600, id="at-once"),
    pytest.param(1, 599, id="1s-later"),
    pytest.param(599.5, 1, id="599.5s-later"),
    pytest.param(599.999999, 1, id="1us-before-10-minutes"),
    pytest.param(600, None, id="10-minutes-later"),
    pytest.param(600.000001, None, id="1us-after-10-minutes"),
]
# Where the clock goes back to, in seconds, after the limit is reached at 300
# seconds: just before then, and more than 10 minutes before then.
CLOCK_BACK = [
    pytest.param(299.999999, id="1us-back"),
    pytest.param(-1000, id="1300s-back"),
]


def seconds(value):
    """Return a timedelta of `value` seconds."""
    return timedelta(seconds=value)


@pytest.mark.ac("ACC-3.1", "ACC-3.3")
@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_one_below_allows_last_then_refuses_next(clock, kind, scope):
    # Just below the limit, at it, and just above it.
    limit = limit_of(kind, scope)
    if scope == "address-group":
        visitor = make_attempts(kind, limit - 1, forwarded_for(ADDRESS))
    else:
        make_attempts_from_many(kind, limit - 1)
        visitor = Visitor(forwarded_for(ADDRESS))
    assert_allowed(visitor.attempt(kind), kind, limit)
    assert_refused(visitor.attempt(kind), kind, retry_after=600)


@pytest.mark.ac("ACC-3.3", "ACC-3.2")
@pytest.mark.parametrize(("elapsed", "retry_after"), WINDOW_EDGES)
@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_reached_refuses_until_10_minutes_after_with_retry_after(
    clock, kind, scope, elapsed, retry_after
):
    source = fill(kind, scope)
    clock.set_elapsed(seconds(elapsed))
    response = Visitor(source).attempt(kind)
    if retry_after is None:
        assert_allowed(response, kind)
    else:
        assert_refused(response, kind, retry_after=retry_after)


@pytest.mark.ac("ACC-3.3")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_retry_after_rounds_up_to_whole_seconds(clock, kind):
    clock.set_elapsed(seconds(0.25))
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    clock.set_elapsed(seconds(100))
    assert_refused(visitor.attempt(kind), kind, retry_after=501)
    clock.set_elapsed(seconds(100.25))
    assert_refused(visitor.attempt(kind), kind, retry_after=500)
    clock.set_elapsed(seconds(100.250001))
    assert_refused(visitor.attempt(kind), kind, retry_after=500)


@pytest.mark.ac("ACC-3.3")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_spread_attempts_free_one_place_as_earliest_turns_10_minutes(clock, kind):
    # One attempt every 10 seconds: the earliest stops counting first.
    visitor = Visitor(forwarded_for(ADDRESS))
    limit = PER_GROUP[kind]
    for number in range(limit):
        clock.set_elapsed(seconds(10 * number))
        assert_allowed(visitor.attempt(kind), kind, number + 1)
    last = 10 * (limit - 1)
    clock.set_elapsed(seconds(last + 5))
    assert_refused(visitor.attempt(kind), kind, retry_after=600 - last - 5)
    clock.set_elapsed(seconds(600))
    assert_allowed(visitor.attempt(kind), kind)
    # The second attempt now counts for 10 seconds more.
    assert_refused(visitor.attempt(kind), kind, retry_after=10)
    clock.set_elapsed(seconds(610))
    assert_allowed(visitor.attempt(kind), kind)


@pytest.mark.ac("ACC-3.3", "ACC-3.8")
@pytest.mark.parametrize("back_to", CLOCK_BACK)
@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_clock_back_after_limit_reached_refuses_with_retry_after_600(
    clock, kind, scope, back_to
):
    # The refused attempt's moment is 300 s, the latest counted attempt's
    # time, so Retry-After is from then, not from the earlier clock.
    clock.set_elapsed(seconds(300))
    source = fill(kind, scope)
    clock.set_elapsed(seconds(back_to))
    assert_refused(Visitor(source).attempt(kind), kind, retry_after=600)


@pytest.mark.ac("ACC-3.3", "ACC-3.8")
@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_clock_back_attempt_counts_until_10_minutes_after_latest(
    clock, kind, scope
):
    limit = limit_of(kind, scope)
    clock.set_elapsed(seconds(300))
    if scope == "address-group":
        visitor = make_attempts(kind, limit - 1, forwarded_for(ADDRESS))
    else:
        make_attempts_from_many(kind, limit - 1)
        visitor = Visitor(forwarded_for(ADDRESS))
    clock.set_elapsed(seconds(0))
    # Counted at its moment, 300 s, not at the clock's 0 s.
    assert_allowed(visitor.attempt(kind), kind, limit)
    assert_refused(visitor.attempt(kind), kind, retry_after=600)
    clock.set_elapsed(seconds(600))
    assert_refused(visitor.attempt(kind), kind, retry_after=300)
    clock.set_elapsed(seconds(900))
    assert_allowed(visitor.attempt(kind), kind)


@pytest.mark.ac("ACC-3.1", "ACC-3.3")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_attempts_count_toward_both_limits_retry_after_is_longest(clock, kind):
    # Other groups' attempts at T, then ADDRESS's at T+100, reach both limits.
    others = EVERYONE[kind] - PER_GROUP[kind]
    make_attempts_from_many(kind, others)
    clock.set_elapsed(seconds(100))
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    clock.set_elapsed(seconds(200))
    # Both limits refuse ADDRESS: its group's until T+700, everyone's until
    # T+600. Only the limit for everyone refuses another group.
    assert_refused(visitor.attempt(kind), kind, retry_after=500)
    other_group = numbered_source(others + 1)
    assert_refused(visitor.attempt(kind, source=other_group), kind, retry_after=400)
    clock.set_elapsed(seconds(600))
    assert_refused(visitor.attempt(kind), kind, retry_after=100)
    assert_allowed(visitor.attempt(kind, source=other_group), kind)


@pytest.mark.ac("ACC-3.1")
@pytest.mark.parametrize("scope", SCOPES)
@pytest.mark.parametrize("kind", KINDS)
def test_limit_other_kind_used_up_does_not_limit_this_kind(clock, kind, scope):
    source = fill(OTHER_KIND[kind], scope)
    visitor = Visitor(source)
    assert_refused(visitor.attempt(OTHER_KIND[kind]), OTHER_KIND[kind])
    assert_allowed(visitor.attempt(kind), kind)


@pytest.mark.ac("ACC-3.1")
def test_limit_tenth_sign_in_attempt_with_account_password_signs_in(
    clock, make_account
):
    make_account("alice", PASSWORD, REQUESTER)
    make_attempts(SIGN_IN_ATTEMPT, 9, forwarded_for(ADDRESS), username="alice")
    visitor = Visitor(forwarded_for(ADDRESS))
    response = visitor.attempt(SIGN_IN_ATTEMPT, "alice", PASSWORD)
    assert_redirects(response, ROLE_PAGES[REQUESTER])
    assert_signed_in_as(visitor.browser, REQUESTER, "alice")


@pytest.mark.ac("ACC-3.1")
def test_limit_third_creation_from_group_creates_workspace(clock):
    make_attempts(CREATION, 2, forwarded_for(ADDRESS))
    before = stored_state()
    assert_created(Visitor(forwarded_for(ADDRESS)).attempt(CREATION), before)


@pytest.mark.ac("ACC-3.1", "ACC-3.4")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_attempt_whose_hashing_fails_is_still_counted(clock, kind):
    # Counted before any password is hashed, so a failure while hashing
    # leaves it counted.
    def fail(password, encoded):
        raise RuntimeError("synthetic failure while hashing")

    visitor = Visitor(forwarded_for(ADDRESS))
    visitor.browser.raise_request_exception = False
    with reporting_hashes_to(fail):
        for number in range(1, PER_GROUP[kind] + 1):
            response = visitor.attempt(kind)
            assert response.status_code == 500, (
                f"Attempt {number} got {response.status_code}; hashing did not fail."
            )
    assert_refused(visitor.attempt(kind), kind, retry_after=600)


@pytest.mark.ac("ACC-3.2")
def test_limit_refused_sign_in_with_account_password_checks_nothing_signs_in_no_one(
    clock, make_account
):
    make_account("alice", PASSWORD, REQUESTER)
    fill(SIGN_IN_ATTEMPT, "address-group")
    visitor = Visitor(forwarded_for(ADDRESS))
    with recording_hashes() as hashed:
        response = visitor.attempt(SIGN_IN_ATTEMPT, "alice", PASSWORD)
    assert_refused(response, SIGN_IN_ATTEMPT, retry_after=600)
    assert hashed == [], "A password was checked or hashed."
    assert_signed_out(visitor.browser)
    assert signed_in_account_ids() == set()


@pytest.mark.ac("ACC-3.2")
@pytest.mark.parametrize("scope", SCOPES)
def test_limit_refused_creation_hashes_nothing_creates_nothing(clock, scope):
    source = fill(CREATION, scope)
    before = stored_state()
    with recording_hashes() as hashed:
        response = Visitor(source).attempt(CREATION)
    assert_refused(response, CREATION, retry_after=600)
    assert hashed == [], "A password was hashed."
    assert_nothing_created(before)


@pytest.mark.ac("ACC-3.2")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_refused_page_shows_nothing_the_request_sent(clock, kind):
    # Red-team values, stored escaped and decoded only here.
    username = "%3Cscript%3Ealert(%22probe-4c1d%22)%3C%2Fscript%3E"
    password = "probe-pass-8e2b"
    forwarded = "198.51.100.77, 203.0.113.7"
    source = forwarded_for(forwarded)
    visitor = make_attempts(kind, PER_GROUP[kind], source)
    response = visitor.attempt(kind, unquote(username), password)
    sent = [
        unquote(username),
        "probe-4c1d",
        password,
        "198.51.100.77",
        ADDRESS,
        visitor.token,
    ]
    assert_refused(response, kind, retry_after=600, sent=sent)


@pytest.mark.ac("ACC-3.2", "ACC-1.8", "ACC-2.6")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_refused_response_carries_framing_and_cache_headers(clock, kind):
    source = fill(kind, "address-group")
    response = Visitor(source).attempt(kind)
    assert_refused(response, kind)
    assert response.get("X-Frame-Options") == "DENY"
    if kind == CREATION:
        assert "no-store" in cache_directives(response)


@pytest.mark.ac("ACC-3.2", "ACC-3.3")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_refused_attempts_do_not_delay_next_allowed(clock, kind):
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    for elapsed in (300, 450, 599):
        clock.set_elapsed(seconds(elapsed))
        for _ in range(3):
            response = visitor.attempt(kind)
            assert_refused(response, kind, retry_after=600 - elapsed)
    clock.set_elapsed(seconds(600))
    assert_allowed(visitor.attempt(kind), kind)


@pytest.mark.ac("ACC-3.2", "ACC-3.1")
@pytest.mark.parametrize("kind", KINDS)
def test_limit_refused_attempts_count_toward_no_limit_for_everyone(clock, kind):
    visitor = make_attempts(kind, PER_GROUP[kind], forwarded_for(ADDRESS))
    for _ in range(EVERYONE[kind]):
        assert_refused(visitor.attempt(kind), kind, retry_after=600)
    others = EVERYONE[kind] - PER_GROUP[kind]
    make_attempts_from_many(kind, others)
    response = visitor.attempt(kind, source=numbered_source(others + 1))
    assert_refused(response, kind, retry_after=600)
