"""The rate limits on sign-in attempts and demo workspace creations (ACC-3).

Each attempt is checked against its kind's limits, and counted if they allow
it, in one transaction that every attempt of either kind waits its turn for,
so counts kept only in the database hold across server instances (ACC-3.6,
3.8).
"""

import ipaddress
from datetime import timedelta

from django.db import connection, transaction
from django.db.models import Max
from django.utils import timezone
from django.utils.crypto import salted_hmac

from deskmate.accounts.models import CountedAttempt, Kind

# For each kind, how many attempts counted in the window refuse the next one:
# from its client's address group, and from everyone (ACC-3.1).
LIMITS = {Kind.SIGN_IN: (10, 30), Kind.CREATION: (3, 5)}
WINDOW = timedelta(minutes=10)
# The advisory lock key that serialises every check. ACC-3.8 needs only each
# kind's checks in turn, but one lock for both kinds needs only one key.
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
    The check commits before the caller goes on, and waiting more than
    5 seconds for it, or a database failure, raises (ACC-3.7).
    """
    group = _stored_group(address_group(client_address(request.META)))
    with transaction.atomic(durable=True):
        with connection.cursor() as cursor:
            # Waiting more than 5 seconds for the lock fails (ACC-3.7).
            cursor.execute("SET LOCAL lock_timeout = '5s'")
            cursor.execute("SELECT pg_advisory_xact_lock(%s)", [_LOCK_KEY])
        # The attempt's moment: the clock, read only once its turn has come,
        # but never before the latest attempt of its kind (ACC-3.8).
        moment = timezone.now()
        of_kind = CountedAttempt.objects.filter(kind=kind)
        latest = of_kind.aggregate(Max("counted_at"))["counted_at__max"]
        if latest is not None:
            moment = max(moment, latest)
        start = moment - WINDOW
        # Only this kind's old records, so the other kind's moment is kept (ACC-3.6).
        of_kind.filter(counted_at__lte=start).delete()
        counted = of_kind.filter(counted_at__gt=start)
        refused_until = []
        for records, limit in zip(
            [counted.filter(group=group), counted], LIMITS[kind], strict=True
        ):
            # The limit refuses until its oldest counted attempt leaves the window.
            times = records.order_by("-counted_at").values_list("counted_at", flat=True)
            refused_until += [oldest + WINDOW for oldest in times[limit - 1 : limit]]
        if not refused_until:
            CountedAttempt.objects.create(kind=kind, group=group, counted_at=moment)
            return None
    # In whole seconds, rounded up (ACC-3.3).
    return -(-(max(refused_until) - moment) // timedelta(seconds=1))
