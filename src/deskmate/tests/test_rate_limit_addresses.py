"""ACC-3.5: which client address an attempt has, and which address group.

Each test uses up the limit for one address group with attempts from one
Source, then sends one more attempt from another. If the two are in one
group, it is refused; if not, it is allowed. Sources give X-Forwarded-For as
Deskmate's WSGI server gives it, with several lines already joined with
commas; one test sends several lines over HTTP to a running WSGI server.

The clock is stopped, so each refusal's Retry-After is exact whatever the
machine's clock does.

Addresses come from the documentation ranges 192.0.2.0/24, 198.51.100.0/24,
203.0.113.0/24 and 2001:db8::/32, apart from the link-local fe80::1.
"""

import http.client
from urllib.parse import urlencode, urlsplit

import pytest
from django.conf import settings

from deskmate.tests.pages import ORIGIN, SITE
from deskmate.tests.rate_limits import (
    ADDRESS,
    KINDS,
    PER_GROUP,
    SIGN_IN_ATTEMPT,
    Source,
    Visitor,
    assert_allowed,
    assert_refused,
    forwarded_for,
    make_attempts,
    running_server,
)
from deskmate.tests.signing_in import SIGN_IN, WRONG_PASSWORD

pytestmark = pytest.mark.usefixtures("db", "fast_hashing", "clock")

# An address that is not valid, whose group every such address shares.
NOT_AN_ADDRESS = forwarded_for("unknown")

# (first, second): Sources in one address group.
SAME_GROUP = [
    pytest.param(
        forwarded_for("198.51.100.1, 203.0.113.7"),
        forwarded_for("198.51.100.2, 203.0.113.7"),
        id="entries-before-last-change-nothing",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("198.51.100.1,203.0.113.7"),
        id="several-lines-joined-last-is-address",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("\t203.0.113.7 "),
        id="tab-before-space-after-ignored",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("198.51.100.1 \t,  \t203.0.113.7\t \t"),
        id="spaces-and-tabs-around-last-entry-ignored",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        Source(remote=ADDRESS),
        id="header-entry-and-connection-address",
    ),
    pytest.param(
        forwarded_for("2001:db8:0:1::1"),
        forwarded_for("2001:db8:0:1:ffff::2"),
        id="ipv6-same-first-64-bits",
    ),
    pytest.param(
        forwarded_for("2001:db8:0:1::"),
        forwarded_for("2001:db8:0:1:ffff:ffff:ffff:ffff"),
        id="ipv6-first-and-last-of-64",
    ),
    pytest.param(
        forwarded_for("2001:db8::1"),
        forwarded_for("2001:db8::1:0:0:1"),
        id="ipv6-zero-prefix-64",
    ),
    pytest.param(
        forwarded_for("2001:db8:0:1::1"),
        forwarded_for("2001:0DB8:0000:0001:0000:0000:0000:0001"),
        id="ipv6-uncompressed-uppercase-leading-zeros",
    ),
    pytest.param(
        forwarded_for("2001:db8:0:1::1"),
        forwarded_for("2001:db8:0:1::203.0.113.7"),
        id="ipv6-dotted-last-32-bits",
    ),
    pytest.param(
        Source(remote="2001:db8:0:1::1"),
        forwarded_for("2001:db8:0:1::2"),
        id="ipv6-connection-address",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("::ffff:203.0.113.7"),
        id="ipv4-mapped-dotted",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("::ffff:cb00:7107"),
        id="ipv4-mapped-hexadecimal",
    ),
    pytest.param(
        forwarded_for("::ffff:203.0.113.7"),
        forwarded_for("0:0:0:0:0:FFFF:203.0.113.7"),
        id="ipv4-mapped-uncompressed",
    ),
    pytest.param(
        Source(remote="::ffff:203.0.113.7"),
        forwarded_for(ADDRESS),
        id="ipv4-mapped-connection-address",
    ),
    *(
        pytest.param(NOT_AN_ADDRESS, forwarded_for(value), id=f"not-valid-{name}")
        for name, value in [
            ("port", "203.0.113.7:443"),
            ("empty-header", ""),
            ("empty-last-entry", "203.0.113.7,"),
            ("blank-last-entry", "203.0.113.7, \t "),
            ("last-entry-unknown", "203.0.113.7, unknown"),
            ("ipv4-leading-zero", "203.0.113.07"),
            ("ipv4-octet-over-255", "203.0.113.256"),
            ("ipv4-three-numbers", "203.0.113"),
            ("ipv4-trailing-dot", "203.0.113.7."),
            ("no-break-space-before", " 203.0.113.7"),
            ("ipv6-brackets", "[2001:db8::1]"),
            ("ipv6-brackets-port", "[2001:db8::1]:443"),
            ("ipv6-zone-id", "fe80::1%eth0"),
            ("ipv6-too-many-groups", "2001:db8:0:1:0:0:0:0:1"),
            ("ipv6-two-double-colons", "2001:db8::1::1"),
            ("ipv4-mapped-leading-zero", "::ffff:203.0.113.07"),
            ("network", "203.0.113.0/24"),
        ]
    ),
    pytest.param(
        NOT_AN_ADDRESS,
        Source(remote=""),
        id="not-valid-empty-connection-address",
    ),
    pytest.param(
        forwarded_for(""),
        forwarded_for("", remote="198.51.100.9"),
        id="not-valid-empty-header-from-other-connections",
    ),
]

# (first, second): Sources in different address groups.
DIFFERENT_GROUPS = [
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("203.0.113.7, 198.51.100.9"),
        id="last-entry-is-another-address",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("203.0.113.8"),
        id="ipv4-neighbour",
    ),
    pytest.param(
        Source(remote="198.51.100.9"),
        forwarded_for(ADDRESS, remote="198.51.100.9"),
        id="header-not-connection-address",
    ),
    pytest.param(
        Source(remote="198.51.100.9"),
        forwarded_for("", remote="198.51.100.9"),
        id="empty-header-not-connection-address",
    ),
    pytest.param(
        forwarded_for("2001:db8:0:1::1"),
        forwarded_for("2001:db8:0:2::1"),
        id="ipv6-other-64",
    ),
    pytest.param(
        forwarded_for("2001:db8:0:1::"),
        forwarded_for("2001:db8:0:0:ffff:ffff:ffff:ffff"),
        id="ipv6-adjacent-64",
    ),
    pytest.param(
        forwarded_for("::ffff:203.0.113.7"),
        forwarded_for("::ffff:203.0.113.8"),
        id="ipv4-mapped-grouped-as-ipv4-not-by-64",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("::203.0.113.7"),
        id="ipv4-compatible-is-not-ipv4-mapped",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("203.0.113.7:443"),
        id="with-port-not-the-address",
    ),
    pytest.param(
        forwarded_for(ADDRESS),
        forwarded_for("203.0.113.07"),
        id="leading-zero-not-the-address",
    ),
    pytest.param(
        forwarded_for("2001:db8::1"),
        forwarded_for("[2001:db8::1]"),
        id="brackets-not-the-address",
    ),
    pytest.param(
        forwarded_for("fe80::1"),
        forwarded_for("fe80::1%eth0"),
        id="zone-id-not-the-address",
    ),
    pytest.param(
        NOT_AN_ADDRESS,
        forwarded_for(ADDRESS),
        id="valid-address-not-in-shared-group",
    ),
    pytest.param(
        NOT_AN_ADDRESS,
        Source(),
        id="connection-address-not-in-shared-group",
    ),
]


@pytest.mark.ac("ACC-3.5")
@pytest.mark.parametrize(("first", "second"), SAME_GROUP)
@pytest.mark.parametrize("kind", KINDS)
def test_address_same_group_shares_limit(kind, first, second):
    visitor = make_attempts(kind, PER_GROUP[kind], first)
    assert_refused(visitor.attempt(kind, source=second), kind)


@pytest.mark.ac("ACC-3.5")
@pytest.mark.parametrize(("first", "second"), DIFFERENT_GROUPS)
@pytest.mark.parametrize("kind", KINDS)
def test_address_different_groups_do_not_share_limit(kind, first, second):
    visitor = make_attempts(kind, PER_GROUP[kind], first)
    assert_refused(visitor.attempt(kind), kind)
    assert_allowed(visitor.attempt(kind, source=second), kind)


def post_with_header_lines(server_url, visitor, lines):
    """Send `visitor`'s sign-in form over HTTP to the server at `server_url`,
    with one X-Forwarded-For line for each of `lines`, in order, as a browser
    on the site would send it. Returns the response's status."""
    form = visitor.page.form_with_button("Sign in")
    typed = {"Username": "nobody", "Password": WRONG_PASSWORD}
    body = urlencode(form.data(typed, button="Sign in")).encode()
    cookie = visitor.browser.cookies[settings.CSRF_COOKIE_NAME].value
    url = urlsplit(server_url)
    connection = http.client.HTTPConnection(url.hostname, url.port, timeout=30)
    try:
        connection.putrequest("POST", SIGN_IN, skip_host=True)
        connection.putheader("Host", SITE)
        connection.putheader("Origin", ORIGIN)
        connection.putheader("Cookie", f"{settings.CSRF_COOKIE_NAME}={cookie}")
        connection.putheader("Content-Type", "application/x-www-form-urlencoded")
        connection.putheader("Content-Length", str(len(body)))
        for line in lines:
            connection.putheader("X-Forwarded-For", line)
        connection.endheaders(body)
        response = connection.getresponse()
        response.read()
        return response.status
    finally:
        connection.close()


@pytest.mark.ac("ACC-3.5")
@pytest.mark.parametrize(
    ("lines", "refused"),
    [
        pytest.param(["198.51.100.1", ADDRESS], True, id="address-last"),
        pytest.param([ADDRESS, "198.51.100.1"], False, id="address-first"),
    ],
)
def test_address_several_header_lines_count_as_one_joined_in_order(
    transactional_db, lines, refused
):
    make_attempts(SIGN_IN_ATTEMPT, PER_GROUP[SIGN_IN_ATTEMPT], forwarded_for(ADDRESS))
    with running_server() as url:
        status = post_with_header_lines(url, Visitor(), lines)
    if refused:
        assert status == 429, f"Expected 429, got {status}."
    else:
        assert status == 200, f"Expected the sign-in page, got {status}."
