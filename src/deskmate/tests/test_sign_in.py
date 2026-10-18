"""ACC-1.1, ACC-1.3 and ACC-1.7: signing in with a username and password.

Also the sign-in parts of ACC-1.4, a database that does not answer, and of
ACC-1.5, parameters that try to choose where signing in leads, and the methods
that /sign-in/ does not list, which sign no one in or out (ACC-1.1, ACC-1.2).
"""

from urllib.parse import unquote, urlencode

import pytest
from django.conf import settings
from django.core.exceptions import ValidationError

from deskmate.tests.pages import CSRF_FIELD, Page
from deskmate.tests.signing_in import (
    MARKUP_USERNAMES,
    NOT_FOR_YOUR_ROLE,
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SIGN_IN_ERROR,
    SUPPORT_OFFICER,
    VISITORS,
    WRONG_PASSWORD,
    assert_forbidden,
    assert_method_not_allowed,
    assert_redirects,
    assert_server_error,
    assert_sign_in_failed,
    assert_sign_in_page,
    assert_signed_in_as,
    assert_signed_out,
    browser_as,
    csrf_token,
    get_sign_in_page,
    methods_not_listed,
    new_browser,
    other_role,
    send,
    sign_in,
    sign_in_as,
    submit_sign_in,
)

ACCOUNT = "alice"
LONGEST = "a" * 150
ASCII_ALPHABET = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789@.+-_"
# Response headers whose values are the time the response was made.
TIME_HEADERS = frozenset({"date", "expires", "last-modified"})

# Each submission matches no account because of one input, then both (ACC-1.3).
NO_MATCH = [
    pytest.param("", PASSWORD, id="username-empty"),
    pytest.param(" \t\u3000", PASSWORD, id="username-only-whitespace"),
    pytest.param(LONGEST + "a", PASSWORD, id="username-151-characters"),
    pytest.param("nobody", PASSWORD, id="username-unknown"),
    pytest.param(ACCOUNT, "", id="password-empty"),
    pytest.param(ACCOUNT, WRONG_PASSWORD, id="password-wrong"),
    pytest.param("", "", id="both-empty"),
    pytest.param("nobody", WRONG_PASSWORD, id="both-wrong"),
]

# Red-team characters, stored escaped and decoded only inside the tests.
# Invisible and format characters are outside ACC-1.7's trim set and allowlist.
INVISIBLE_CHARACTERS = [
    pytest.param("%E2%80%8B", id="zero-width-space"),  # U+200B
    pytest.param("%E2%80%8D", id="zero-width-joiner"),  # U+200D
    pytest.param("%E2%81%A0", id="word-joiner"),  # U+2060
    pytest.param("%EF%BB%BF", id="zero-width-no-break-space"),  # U+FEFF
    pytest.param("%C2%AD", id="soft-hyphen"),  # U+00AD
]
INVISIBLE_PLACES = ["before", "after", "inside"]
NULL_CHARACTER = "%00"
# Every whitespace code point ACC-1.7 trims, decoded only inside the test.
TRIM_CODEPOINTS = (
    *range(0x0009, 0x000E),
    *range(0x001C, 0x0021),
    0x0085,
    0x00A0,
    0x1680,
    *range(0x2000, 0x200B),
    0x2028,
    0x2029,
    0x202F,
    0x205F,
    0x3000,
)

# Trimming does not otherwise change the ASCII username (ACC-1.7).
MATCHING_USERNAMES = [
    pytest.param("  alice  ", id="ascii-spaces"),
    pytest.param("\t\r\n alice\n", id="ascii-control-whitespace"),
    pytest.param("\u00a0\u3000alice\u2003", id="unicode-spaces"),
    pytest.param("\u0085\u2028alice\u2029", id="unicode-line-breaks"),
]

# Invalid typed usernames and a valid ASCII account with the right password.
# Compatibility forms would sign in to that account if NFKC were applied.
# Non-ASCII/red-team inputs stay escaped until each test decodes them.
INVALID_USERNAMES = [
    pytest.param("ali%21ce", ACCOUNT, id="ascii-exclamation"),
    pytest.param("ali%2Fce", ACCOUNT, id="ascii-slash"),
    pytest.param("ali%3Ace", ACCOUNT, id="ascii-colon"),
    pytest.param("ali%5Cce", ACCOUNT, id="ascii-backslash"),
    pytest.param("ali%7Fce", ACCOUNT, id="ascii-delete"),
    pytest.param("ali%09ce", ACCOUNT, id="inner-tab"),
    pytest.param("ali%0Ace", ACCOUNT, id="inner-newline"),
    pytest.param("ali%1Fce", ACCOUNT, id="inner-control-separator"),
    pytest.param("ali%20ce", ACCOUNT, id="inner-space"),
    pytest.param("ali%C2%A0ce", ACCOUNT, id="inner-nonbreaking-space"),
    pytest.param("alic%C3%A9", ACCOUNT, id="non-ascii-letter"),
    pytest.param("%D0%B0lice", ACCOUNT, id="cyrillic-lookalike"),
    pytest.param("alice%D9%A1", "alice1", id="non-ascii-digit"),
    pytest.param("alice%CC%81", ACCOUNT, id="combining-mark"),
    pytest.param(
        "%EF%BD%81%EF%BD%8C%EF%BD%89%EF%BD%83%EF%BD%85", ACCOUNT, id="fullwidth"
    ),
    pytest.param("%E3%80%80%EF%BD%81lice%20", ACCOUNT, id="fullwidth-after-trimming"),
    pytest.param("a%E2%84%93ice", ACCOUNT, id="compatibility-letter"),
    pytest.param("%E2%93%90lice", ACCOUNT, id="circled-letter"),
    pytest.param("%F0%9D%90%9Alice", ACCOUNT, id="mathematical-letter"),
    pytest.param("alice%C2%B2", "alice2", id="superscript-digit"),
    pytest.param("alice%EF%BC%91", "alice1", id="fullwidth-digit"),
    pytest.param("alice%EF%BC%8B", "alice+", id="fullwidth-punctuation"),
]

# Accepted usernames are still compared case-sensitively (ACC-1.7).
NON_MATCHING_USERNAMES = [
    pytest.param("Alice", id="capitalised"),
    pytest.param("ALICE", id="upper-case"),
]

# The username limit is measured after trimming (ACC-1.3, ACC-1.7).
USERNAME_LENGTHS = [
    pytest.param("a", "a", id="1-character"),
    pytest.param(ASCII_ALPHABET, ASCII_ALPHABET, id="entire-allowed-alphabet"),
    pytest.param("a" * 149, "a" * 149, id="149-characters"),
    pytest.param(LONGEST, LONGEST, id="150-characters"),
    pytest.param(f" {LONGEST}\u3000", LONGEST, id="150-after-trimming"),
]

# Passwords that differ from PASSWORD only in case, spaces or by NFKC.
NON_MATCHING_PASSWORDS = [
    pytest.param(PASSWORD.lower(), id="other-case"),
    pytest.param(f" {PASSWORD}", id="leading-space"),
    pytest.param(f"{PASSWORD} ", id="trailing-space"),
    pytest.param(PASSWORD.replace(" ", "  ", 1), id="extra-inner-space"),
    pytest.param("\uff33" + PASSWORD[1:], id="fullwidth-letter"),
]
SPACED_PASSWORD = "  Spaced  pass 3 "
# Unicode passwords are allowed, and normalization must not change them.
UNICODE_PASSWORD = "%20%20Synthe%CC%81tic%20%EF%BC%91%20%F0%9F%94%90%20"
# Methods that /sign-in/ does not list (TECHNICAL-SPEC "Routes").
OTHER_METHODS = methods_not_listed("GET", "POST")

# A `next` parameter on the sign-in page, in the submission's query, or in its
# form data, with values that point off the site or at the other role's page.
OTHER_ROLE_PAGE = "the other role's page"
NEXT_PLACES = ["page", "submission-query", "submission-field"]
NEXT_VALUES = ["https://evil.example/", "//evil.example/", OTHER_ROLE_PAGE]
# Every place with every value, alternating the role so each role meets each.
NEXT_CASES = [
    pytest.param(place, value, ROLES[(i + j) % 2], id=f"{place}-{value}")
    for i, place in enumerate(NEXT_PLACES)
    for j, value in enumerate(NEXT_VALUES)
]


def next_target(value, role):
    return ROLE_PAGES[other_role(role)] if value == OTHER_ROLE_PAGE else value


def assert_matches_no_account(browser, username, password):
    """Submit `username` and `password` and check the ACC-1.3 failure."""
    page = get_sign_in_page(browser)
    response = submit_sign_in(browser, page, username, password)
    assert_sign_in_failed(response, username, page)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.1", "ACC-1.3", "ACC-1.7")
@pytest.mark.django_db
def test_sign_in_page_signed_out_shows_sign_in_form(browser):
    assert_sign_in_page(browser.get(SIGN_IN))


@pytest.mark.ac("ACC-1.1")
@pytest.mark.parametrize("role", ROLES)
def test_sign_in_valid_credentials_redirects_to_role_page(make_account, browser, role):
    username = f"{role}-account"
    make_account(username, PASSWORD, role)
    assert_redirects(sign_in(browser, username, PASSWORD), ROLE_PAGES[role])
    assert_signed_in_as(browser, role, username)


@pytest.mark.ac("ACC-1.3")
@pytest.mark.parametrize(("username", "password"), NO_MATCH)
def test_sign_in_no_matching_account_shows_error_signs_no_one_in(
    make_account, browser, username, password
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    make_account(LONGEST, PASSWORD, SUPPORT_OFFICER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(browser, page, username, password)
    assert_sign_in_failed(response, username, page)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.3")
@pytest.mark.parametrize("escaped", MARKUP_USERNAMES)
def test_sign_in_failed_markup_username_kept_as_text(make_account, browser, escaped):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    typed = unquote(escaped)
    page = get_sign_in_page(browser)
    response = submit_sign_in(browser, page, typed, PASSWORD)
    assert_sign_in_failed(response, typed, page)
    assert typed not in response.content.decode("utf-8")


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("place", INVISIBLE_PLACES)
@pytest.mark.parametrize("escaped", INVISIBLE_CHARACTERS)
def test_sign_in_username_with_invisible_character_matches_no_account(
    make_account, browser, escaped, place
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    character = unquote(escaped)
    typed = {
        "before": character + ACCOUNT,
        "after": ACCOUNT + character,
        "inside": ACCOUNT[:3] + character + ACCOUNT[3:],
    }[place]
    assert_matches_no_account(browser, typed, PASSWORD)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("field", ["username", "password"])
def test_sign_in_null_character_matches_no_account(make_account, browser, field):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    null = unquote(NULL_CHARACTER)
    if field == "username":
        assert_matches_no_account(browser, ACCOUNT + null, PASSWORD)
    else:
        assert_matches_no_account(browser, ACCOUNT, PASSWORD + null)


@pytest.mark.ac("ACC-1.3")
@pytest.mark.parametrize("length", [151, 100_000], ids=["151", "100000"])
def test_sign_in_oversized_username_matches_no_account(make_account, browser, length):
    make_account(LONGEST, PASSWORD, REQUESTER)
    assert_matches_no_account(browser, f" {('a' * length)}\u3000", PASSWORD)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize(("escaped", "username"), INVALID_USERNAMES)
def test_sign_in_username_outside_allowlist_shows_generic_error(
    make_account, browser, escaped, username
):
    make_account(username, PASSWORD, REQUESTER)
    assert_matches_no_account(browser, unquote(escaped), PASSWORD)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize(("escaped", "_username"), INVALID_USERNAMES)
def test_user_validation_username_outside_allowlist_rejected(
    make_account, escaped, _username
):
    # Exercise the User rule through Django's existing model-validation API;
    # the invalid username is never saved or treated as an existing account.
    account = make_account(ACCOUNT, PASSWORD, REQUESTER)
    rejected_username = unquote(escaped)
    account.username = rejected_username
    with pytest.raises(ValidationError) as error:
        account.full_clean()
    assert "username" in error.value.message_dict
    assert account.username == rejected_username


@pytest.mark.ac("ACC-1.7")
@pytest.mark.parametrize("length", [0, 1, 150, 151])
def test_sign_in_username_all_specified_whitespace_trimmed(
    make_account, browser, length
):
    make_account("a" if length <= 1 else LONGEST, PASSWORD, REQUESTER)
    whitespace = "".join(chr(codepoint) for codepoint in TRIM_CODEPOINTS)
    typed = whitespace + "a" * length + whitespace[::-1]
    if length in (1, 150):
        assert_redirects(sign_in(browser, typed, PASSWORD), ROLE_PAGES[REQUESTER])
        assert_signed_in_as(browser, REQUESTER, "a" * length)
    else:
        assert_matches_no_account(browser, typed, PASSWORD)


@pytest.mark.ac("ACC-1.3")
def test_sign_in_existing_username_wrong_password_same_as_unknown_username(
    make_account,
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    submission = ("dana", WRONG_PASSWORD)
    unknown = sign_in(new_browser(), *submission)
    make_account("dana", PASSWORD, SUPPORT_OFFICER)
    existing = sign_in(new_browser(), *submission)
    assert SIGN_IN_ERROR in Page(existing).text
    assert comparable(existing) == comparable(unknown)


def comparable(response):
    """Return what ACC-1.3 compares: the response, apart from its CSRF token.

    The CSRF cookie is the token's other half, so it is left out. Values that
    hold the current time, such as an Expires header, are compared only for
    being there, so two responses a second apart still compare equal.
    """
    body = response.content.decode("utf-8")
    for token in Page(response).csrf_tokens():
        body = body.replace(token, "<CSRF token>")
    headers = {
        name: "<time>" if name.lower() in TIME_HEADERS else value
        for name, value in response.headers.items()
    }
    cookies = {
        name: {**morsel, "expires": "<time>" if morsel["expires"] else ""}
        for name, morsel in response.cookies.items()
        if name != settings.CSRF_COOKIE_NAME
    }
    return response.status_code, headers, body, cookies


@pytest.mark.ac("ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_sign_in_database_down_returns_500_signs_no_one_in(
    make_account, browser, database_outage, role
):
    make_account(ACCOUNT, PASSWORD, role)
    page = get_sign_in_page(browser)
    browser.raise_request_exception = False
    with database_outage():
        response = submit_sign_in(browser, page, ACCOUNT, PASSWORD)
    assert_server_error(response)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.1", "ACC-1.2")
@pytest.mark.parametrize("visitor", VISITORS, ids=["signed-out", *ROLES])
@pytest.mark.parametrize("method", OTHER_METHODS)
def test_sign_in_method_other_than_get_or_post_returns_405_empty_signs_no_one_in(
    make_account, method, visitor
):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    browser, account = browser_as(make_account, visitor)
    form = get_sign_in_page(new_browser()).form_with_button("Sign in")
    credentials = {
        form.field("Username").name: ACCOUNT,
        form.field("Password").name: PASSWORD,
    }
    token = csrf_token(browser, visitor)
    response = send(browser, method, SIGN_IN, token, data=credentials)
    assert_method_not_allowed(response)
    if account is None:
        assert_signed_out(browser)
    else:
        assert_signed_in_as(browser, visitor, account.username)


@pytest.mark.ac("ACC-1.5")
@pytest.mark.parametrize(("place", "value", "role"), NEXT_CASES)
def test_sign_in_next_parameter_does_not_change_redirect(
    make_account, browser, place, value, role
):
    username = f"{role}-account"
    make_account(username, PASSWORD, role)
    target = next_target(value, role)
    if place == "page":
        page = get_sign_in_page(browser, f"{SIGN_IN}?{urlencode({'next': target})}")
        response = submit_sign_in(browser, page, username, PASSWORD)
    elif place == "submission-query":
        page = get_sign_in_page(browser)
        response = submit_sign_in(
            browser, page, username, PASSWORD, query={"next": target}
        )
    else:
        page = get_sign_in_page(browser)
        response = submit_sign_in(
            browser, page, username, PASSWORD, changes={"next": target}
        )
    assert_redirects(response, ROLE_PAGES[role])


@pytest.mark.ac("ACC-1.5")
def test_sign_in_role_field_in_submission_does_not_change_role(make_account, browser):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(
        browser, page, ACCOUNT, PASSWORD, changes={"role": SUPPORT_OFFICER}
    )
    assert_redirects(response, ROLE_PAGES[REQUESTER])
    assert_forbidden(browser.get(ROLE_PAGES[SUPPORT_OFFICER]), NOT_FOR_YOUR_ROLE)


@pytest.mark.ac("ACC-1.7")
@pytest.mark.parametrize("role", ROLES)
def test_sign_in_signed_in_get_redirects_to_own_page(make_account, role):
    browser, account = sign_in_as(make_account, role)
    assert_redirects(browser.get(SIGN_IN), ROLE_PAGES[role])
    assert_signed_in_as(browser, role, account.username)


@pytest.mark.ac("ACC-1.5", "ACC-1.7")
@pytest.mark.parametrize(
    ("value", "role"),
    [
        pytest.param(value, ROLES[i % 2], id=value)
        for i, value in enumerate(NEXT_VALUES)
    ],
)
def test_sign_in_signed_in_get_with_next_redirects_to_own_page(
    make_account, value, role
):
    browser, _ = sign_in_as(make_account, role)
    response = browser.get(SIGN_IN, query_params={"next": next_target(value, role)})
    assert_redirects(response, ROLE_PAGES[role])


@pytest.mark.ac("ACC-1.7")
@pytest.mark.parametrize(
    ("submission", "role"),
    [
        pytest.param("other-account", REQUESTER, id="other-account-requester"),
        pytest.param("other-account", SUPPORT_OFFICER, id="other-account-officer"),
        pytest.param("wrong-password", SUPPORT_OFFICER, id="wrong-password"),
        pytest.param("empty", REQUESTER, id="empty"),
        pytest.param("invalid-username", REQUESTER, id="invalid-username"),
    ],
)
def test_sign_in_signed_in_post_redirects_to_own_page_as_same_account(
    make_account, submission, role
):
    browser, account = sign_in_as(make_account, role)
    other = make_account("other-account", WRONG_PASSWORD, other_role(role))
    typed = {
        "other-account": (other.username, WRONG_PASSWORD),
        "wrong-password": (account.username, WRONG_PASSWORD),
        "empty": ("", ""),
        "invalid-username": (unquote("%EF%BD%81lice"), PASSWORD),
    }[submission]
    # The form as the sign-in page serves it, sent with this browser's token.
    form = get_sign_in_page(new_browser()).form_with_button("Sign in")
    response = form.submit(
        browser,
        {"Username": typed[0], "Password": typed[1]},
        button="Sign in",
        changes={CSRF_FIELD: csrf_token(browser, role)},
    )
    assert_redirects(response, ROLE_PAGES[role])
    assert_signed_in_as(browser, role, account.username)


@pytest.mark.ac("ACC-1.7")
@pytest.mark.parametrize("typed", MATCHING_USERNAMES)
def test_sign_in_username_trimmed_signs_in(make_account, browser, typed):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    assert_redirects(sign_in(browser, typed, PASSWORD), ROLE_PAGES[REQUESTER])
    assert_signed_in_as(browser, REQUESTER, ACCOUNT)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("typed", NON_MATCHING_USERNAMES)
def test_sign_in_username_other_case_matches_no_account(make_account, browser, typed):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(browser, page, typed, PASSWORD)
    assert_sign_in_failed(response, typed, page)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize(("typed", "username"), USERNAME_LENGTHS)
def test_sign_in_username_up_to_150_characters_signs_in(
    make_account, browser, typed, username
):
    account = make_account(username, PASSWORD, SUPPORT_OFFICER)
    account.full_clean()
    assert account.username == username
    assert_redirects(sign_in(browser, typed, PASSWORD), ROLE_PAGES[SUPPORT_OFFICER])
    assert_signed_in_as(browser, SUPPORT_OFFICER, username)


@pytest.mark.ac("ACC-1.7")
def test_sign_in_password_with_spaces_typed_exactly_signs_in(make_account, browser):
    make_account(ACCOUNT, SPACED_PASSWORD, REQUESTER)
    response = sign_in(browser, ACCOUNT, SPACED_PASSWORD)
    assert_redirects(response, ROLE_PAGES[REQUESTER])


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("variant", ["exact", "composed", "ascii-digit", "trimmed"])
def test_sign_in_unicode_password_matches_only_exact_input(
    make_account, browser, variant
):
    password = unquote(UNICODE_PASSWORD)
    make_account(ACCOUNT, password, REQUESTER)
    typed = {
        "exact": password,
        "composed": password.replace("e\u0301", "\u00e9"),
        "ascii-digit": password.replace("\uff11", "1"),
        "trimmed": password.strip(),
    }[variant]
    if variant == "exact":
        assert_redirects(sign_in(browser, ACCOUNT, typed), ROLE_PAGES[REQUESTER])
        assert_signed_in_as(browser, REQUESTER, ACCOUNT)
    else:
        assert_matches_no_account(browser, ACCOUNT, typed)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("typed", NON_MATCHING_PASSWORDS)
def test_sign_in_password_not_exact_matches_no_account(make_account, browser, typed):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(browser, page, ACCOUNT, typed)
    assert_sign_in_failed(response, ACCOUNT, page)
    assert_signed_out(browser)
