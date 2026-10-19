"""Account rate limits and shared admission counting (ACC-3, ACC-4.8, PLT-5).

Each attempt is checked against its kind's limits, and counted if they allow
it, in one transaction that every other attempt of its kind waits its turn
for, so counts kept only in the database hold across server instances
(ACC-3.6, 3.8).
"""

import ipaddress
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.crypto import salted_hmac

from deskmate.accounts.models import CountedAttempt, Kind

# For each kind, how many attempts counted in the window refuse the next one:
# from its client's address group, and from everyone (ACC-3.1, ACC-4.8).
LIMITS = {Kind.SIGN_IN: (10, 30), Kind.CREATION: (3, 5), Kind.RESET: (3, 5)}
WINDOW = timedelta(minutes=10)
# How long an attempt may wait to be checked, or a statement in its check
# may run, before it fails (ACC-3.7).
MAX_WAIT = timedelta(seconds=5)
# With each kind's index in `Kind`, the advisory lock key that serialises that
# kind's checks (ACC-3.8). Each kind reads and deletes only its own records,
# so the kinds need not wait for each other.
_LOCK_KEY = 3227_0038
# The group every client address that is not a valid IP address shares.
_NO_ADDRESS = "none"
_SALT = "deskmate.accounts.limits"


def client_address(meta):
    """Return the client address of a request whose `META` is `meta` (ACC-3.5).

    It is the last entry of `X-Forwarded-For`, even if that is empty, without
    the spaces and tabs around it; or, with no such header, the connection's.
    """
    if "HTTP_X_FORWARDED_FOR" in meta:
        return meta["HTTP_X_FORWARDED_FOR"].rsplit(",", 1)[-1].strip(" \t")
    return meta.get("REMOTE_ADDR", "")


def address_group(text):
    """Return the address group of client address `text` (ACC-3.5).

    An IPv4 address is its own group, an IPv6 address is grouped by its first
    64 bits, and an IPv4-mapped one as the IPv4 address it holds. Every other
    text, including one with a zone ID, which Python accepts, shares one group.
    """
    if "%" in text:
        return _NO_ADDRESS
    try:
        address = ipaddress.ip_address(text)
    except ValueError:
        return _NO_ADDRESS
    if address.version == 6 and address.ipv4_mapped:
        address = address.ipv4_mapped
    if address.version == 4:
        return f"4 {address}"
    return f"6 {int(address) >> 64:016x}"


def _stored_group(group):
    """Return `group` as stored, a hash keyed with the secret key (ACC-3.6)."""
    return salted_hmac(_SALT, group, algorithm="sha256").hexdigest()


def check_and_count(request, kind):
    """Check an attempt of `kind` against its limits, and count it if allowed.

    Returns None if it is allowed, or else its Retry-After in seconds (ACC-3.2,
    3.3), from 1 to 600 because no attempt is counted later than its moment.
    The check commits before the caller goes on, and waiting longer than
    `MAX_WAIT` for it, or a database failure, raises (ACC-3.7).
    """
    group = _stored_group(address_group(client_address(request.META)))
    return check_group_and_count(group, kind, LIMITS[kind])


def check_group_and_count(group, kind, limits):
    """Check and count `kind` for an already-keyed identity hash `group`.

    `limits` holds the allowances for this group and for everyone of this kind.
    The caller supplies the correct identity and calls outside another database
    transaction. Returns None only after counting commits, or the whole seconds
    until both allowances permit it, rounded up. Database failures propagate.
    """
    wait = f"{MAX_WAIT // timedelta(milliseconds=1)}ms"
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            # The lock serialises checks only under READ COMMITTED, where each
            # later statement sees what the lock's last holder committed, so
            # it is pinned whatever the database's default. It must come
            # before any other statement in the transaction.
            cursor.execute("SET TRANSACTION ISOLATION LEVEL READ COMMITTED")
            # Waiting for the lock, or any one statement, fails after
            # `MAX_WAIT` (ACC-3.7).
            cursor.execute(
                "SELECT set_config('lock_timeout', %s, true),"
                " set_config('statement_timeout', %s, true)",
                [wait, wait],
            )
            cursor.execute(
                "SELECT pg_advisory_xact_lock(%s, %s)",
                [_LOCK_KEY, Kind.values.index(kind)],
            )
        # The attempt's moment: the clock, read only once its turn has come,
        # but never before the latest attempt of its kind (ACC-3.8).
        moment = timezone.now()
        of_kind = CountedAttempt.objects.filter(kind=kind)
        latest = of_kind.aggregate(Max("counted_at"))["counted_at__max"]
        if latest is not None:
            moment = max(moment, latest)
        start = moment - WINDOW
        counted = of_kind.filter(counted_at__gt=start)
        refused_until = []
        for records, limit in zip(
            [counted.filter(group=group), counted], limits, strict=True
        ):
            # The limit refuses until its oldest counted attempt leaves the window.
            times = records.order_by("-counted_at").values_list("counted_at", flat=True)
            refused_until += [oldest + WINDOW for oldest in times[limit - 1 : limit]]
        if not refused_until:
            # Counting it deletes only this kind's old records (ACC-3.6).
            of_kind.filter(counted_at__lte=start).delete()
            CountedAttempt.objects.create(kind=kind, group=group, counted_at=moment)
            return None
    # In whole seconds, rounded up (ACC-3.3).
    return -(-(max(refused_until) - moment) // timedelta(seconds=1))
