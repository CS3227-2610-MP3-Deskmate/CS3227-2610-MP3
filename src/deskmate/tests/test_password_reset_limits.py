"""ACC-4.8: reuse existing generic limiter cases with a signed-in browser."""

import inspect
import itertools
import time
from urllib.parse import unquote

import pytest
from django.db import connection

from deskmate.accounts.models import CountedAttempt
from deskmate.tests import rate_limits as limits
from deskmate.tests import signing_in as auth
from deskmate.tests import test_rate_limit_addresses as addresses
from deskmate.tests import test_rate_limit_records as records
from deskmate.tests import test_rate_limits as windows
from deskmate.tests.hashing import recording_hashes
from deskmate.tests.pages import Page
from deskmate.tests.password_resets import (
    REFUSED,
    RESET,
    accounts,
    protected,
    read_form,
    read_success,
    reset_fixture,  # noqa: F401 -- shared fixture.
)
from deskmate.tests.test_rate_limit_failures import this_threads

KIND = "reset"
pytestmark = [
    pytest.mark.ac("ACC-4.8"),
    pytest.mark.usefixtures("reset_limits", "clock"),
]


@pytest.fixture
def reset_limits(resetter, monkeypatch, settings):
    """Adapt shared browser helpers while leaving the original ACC-3 suites intact."""
    sender, _, _ = resetter
    visitor = limits.Visitor
    allowed = limits.assert_allowed
    checked = limits.check_statements
    CountedAttempt.objects.all().delete()  # Start after the fixture's officer sign-in.
    # Keep the officer authenticated while the shared secret-rotation case runs.
    settings.SECRET_KEY_FALLBACKS = [settings.SECRET_KEY]

    class ResetVisitor:
        """A reset client, delegating other kinds to a real signed-out visitor."""

        def __init__(self, source=limits.DEFAULT_SOURCE):
            self.sender = sender.clone(source)
            self.browser, self.token = self.sender.browser, self.sender.token

        def attempt(
            self,
            kind,
            username="alice",
            password=auth.WRONG_PASSWORD,
            *,
            source=None,
            changes=None,
        ):
            """Submit the chosen kind from its own appropriate authenticated state."""
            if kind != KIND:
                return visitor(source or self.sender.source).attempt(kind)
            return protected(
                self.sender.post(
                    username,
                    source=source,
                    fields={"password": password, **(changes or {})},
                )
            )

    def assert_allowed(response, kind, number=None):
        if kind != KIND:
            return allowed(response, kind, number)
        if Page(response).title == "Requester password reset":
            return read_success(response, "alice")
        return read_form(
            response, response.wsgi_request.POST.get("username", ""), rejected=True
        )

    for module in (limits, windows, records, addresses):
        monkeypatch.setattr(module, "Visitor", ResetVisitor)
        monkeypatch.setattr(module, "assert_allowed", assert_allowed)
    for mapping, value in (
        (limits.PER_GROUP, 3),
        (limits.EVERYONE, 5),
        (limits.OTHER_KIND, limits.SIGN_IN_ATTEMPT),
        (limits.REFUSALS, REFUSED),
    ):
        monkeypatch.setitem(mapping, KIND, value)
    monkeypatch.setattr(
        limits,
        "check_statements",
        lambda kind, client: checked(kind, client, after_access=kind == KIND),
    )


def shared_cases():
    """Reuse each generic kind-parameterized case, including its boundary partitions."""
    for module in (windows, records, addresses):
        for name, case in vars(module).items():
            if not name.startswith("test_"):
                continue
            marks = [
                mark
                for mark in getattr(case, "pytestmark", ())
                if mark.name == "parametrize"
            ]
            if not any(mark.args[0] == "kind" for mark in marks):
                continue
            axes = []
            for mark in marks:
                names = mark.args[0]
                names = tuple(names.split(",")) if isinstance(names, str) else names
                values = [KIND] if names == ("kind",) else mark.args[1]
                axis = []
                for value in values:
                    row = (
                        value.values
                        if hasattr(value, "values")
                        else (value,)
                        if len(names) == 1
                        else value
                    )
                    axis.append(dict(zip(names, row, strict=True)))
                axes.append(axis)
            for number, combination in enumerate(itertools.product(*axes)):
                fields = dict(
                    itertools.chain.from_iterable(part.items() for part in combination)
                )
                yield pytest.param(
                    case, fields, id=f"{module.__name__.split('.')[-1]}-{name}-{number}"
                )


@pytest.mark.parametrize(("case", "fields"), list(shared_cases()))
def test_reset_shared_limiter_contract(request, case, fields):
    values = {
        name: fields[name] if name in fields else request.getfixturevalue(name)
        for name in inspect.signature(case).parameters
    }
    case(**values)


@pytest.mark.parametrize("scope", ["address-group", "everyone"])
def test_reset_concurrent_checks_allow_only_final_place(transactional_db, clock, scope):
    count = 2 if scope == "address-group" else 4
    sources = (
        [limits.forwarded_for(limits.ADDRESS)] * 5
        if scope == "address-group"
        else [limits.numbered_source(i) for i in range(1, 6)]
    )
    for source in sources[:count]:
        limits.assert_allowed(limits.Visitor(source).attempt(KIND), KIND)
    responses = limits.attempts_together(KIND, sources)
    assert [response.status_code for response in responses].count(200) == 1
    for response in responses:
        if response.status_code == 429:
            limits.assert_refused(response, KIND)
        else:
            limits.assert_allowed(response, KIND)


@pytest.mark.parametrize(
    ("first", "second"),
    [(a, b) for other in limits.KINDS for a, b in ((KIND, other), (other, KIND))],
)
def test_reset_allowances_independent_in_both_directions(clock, first, second):
    source = limits.fill(first, "everyone")
    limits.assert_allowed(limits.Visitor(source).attempt(second), second)


@pytest.mark.parametrize("typed", [None, "", "%EF%BD%81lice", "officer", "nobody"])
def test_reset_rejected_targets_count_but_nonattempts_and_refusals_do_not(
    resetter, clock, typed, make_account
):
    sender, _, _ = resetter
    requester, _ = auth.browser_as(make_account, auth.REQUESTER)
    token = auth.csrf_token(requester, auth.REQUESTER)
    before = accounts()
    for _ in range(3):
        read_form(sender.browser.get(RESET))
        assert sender.browser.post(RESET).status_code == 403
        assert auth.send(sender.browser, "OPTIONS", RESET).status_code == 405
        assert auth.send(requester, "POST", RESET, token).status_code == 403
        assert (
            auth.send(
                sender.browser,
                "POST",
                RESET,
                sender.token,
                headers={"Origin": auth.EVIL_ORIGIN},
            ).status_code
            == 403
        )
    typed = None if typed is None else unquote(typed)
    for _ in range(3):
        read_form(sender.post(typed), typed or "", rejected=True)
    with recording_hashes() as hashed:
        limits.assert_refused(sender.post("alice"), KIND, retry_after=600)
    assert hashed == [] and accounts() == before


def test_reset_database_failure_at_each_limit_statement_fails_closed(
    transactional_db, clock
):
    statements = limits.check_statements(
        KIND, limits.Visitor(limits.numbered_source(200))
    )
    for number in range(len(statements)):
        client = limits.Visitor(limits.numbered_source(number + 1))
        client.browser.raise_request_exception = False
        failing = limits.FailingStatement(number)

        def fail(execute, sql, params, many, context, failing=failing):
            return (
                failing(execute, sql, params, many, context)
                if sql in statements
                else execute(sql, params, many, context)
            )

        before = accounts()
        with recording_hashes() as hashed, connection.execute_wrapper(fail):
            response = client.attempt(KIND)
        assert failing.failed == statements[number]
        auth.assert_server_error(response)
        assert hashed == [] and accounts() == before


@pytest.mark.parametrize(
    ("active", "held_kind"),
    [
        (KIND, KIND),
        *[(a, b) for other in limits.KINDS for a, b in ((KIND, other), (other, KIND))],
    ],
)
def test_reset_wait_timeout_and_other_kinds_do_not_wait(
    transactional_db, clock, active, held_kind
):
    statements = limits.check_statements(
        held_kind, limits.Visitor(limits.numbered_source(200))
    )
    held = limits.HeldCheck(held_kind, statements[-1], 15, limits.numbered_source(201))
    client = limits.Visitor(limits.numbered_source(202))
    client.browser.raise_request_exception = False
    with recording_hashes() as hashed, held.holding():
        before, started = accounts(), time.monotonic()
        response = client.attempt(active)
        elapsed = time.monotonic() - started
        if active == held_kind:
            auth.assert_server_error(response)
            assert this_threads(hashed) == [] and accounts() == before
        else:
            assert elapsed < limits.MAX_WAIT_SECONDS
            limits.assert_allowed(response, active)
    limits.assert_allowed(held.response, held_kind)
