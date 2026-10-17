"""ACC-1.1, ACC-1.3 and ACC-1.7: signing in with a username and password.

Also the sign-in parts of ACC-1.4, a database that does not answer, and of
ACC-1.5, parameters that try to choose where signing in leads, and the methods
that /sign-in/ does not list, which sign no one in or out (ACC-1.1, ACC-1.2).
"""

from urllib.parse import unquote, urlencode

import pytest
from django.conf import settings
from django.contrib.auth import forms as auth_forms

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
# Four characters that NFKC turns into one, U+1F8F: Greek capital alpha with
# dasia, perispomeni and prosgegrammeni.
DECOMPOSED_ALPHA = "\u0391\u0314\u0342\u0345"
COMPOSED_ALPHA = "\u1f8f"
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
# Invisible and format characters are not Unicode whitespace and NFKC keeps
# them, so a username with one anywhere in it is not `alice` (ACC-1.7).
INVISIBLE_CHARACTERS = [
    pytest.param("%E2%80%8B", id="zero-width-space"),  # U+200B
    pytest.param("%E2%80%8D", id="zero-width-joiner"),  # U+200D
    pytest.param("%E2%81%A0", id="word-joiner"),  # U+2060
    pytest.param("%EF%BB%BF", id="zero-width-no-break-space"),  # U+FEFF
    pytest.param("%C2%AD", id="soft-hyphen"),  # U+00AD
]
INVISIBLE_PLACES = ["before", "after", "inside"]
NULL_CHARACTER = "%00"
# Usernames far over the limit (ACC-1.3), as an escaped character and how many
# times it is typed. NFKC turns U+FDFA into 18 characters.
OVERSIZED_USERNAMES = [
    pytest.param("a", 100_000, id="100000-characters"),
    pytest.param("%EF%B7%BA", 9, id="9-characters-162-after-nfkc"),
    pytest.param("%EF%B7%BA", 100_000, id="100000-characters-nfkc-expands"),
]

# Typed usernames that sign in as `alice` (ACC-1.7): Unicode whitespace around
# them is ignored, and they are compared after NFKC normalisation.
MATCHING_USERNAMES = [
    pytest.param("  alice  ", id="ascii-spaces"),
    pytest.param("\t\r\n alice\n", id="ascii-control-whitespace"),
    pytest.param("\u00a0\u3000alice\u2003", id="unicode-spaces"),
    pytest.param("\u0085\u2028alice\u2029", id="unicode-line-breaks"),
    pytest.param("\uff41\uff4c\uff49\uff43\uff45", id="fullwidth"),
    pytest.param("\u3000\uff41\uff4c\uff49\uff43\uff45 ", id="fullwidth-and-spaces"),
]

# Typed usernames that do not sign in as `alice`: comparison is case-sensitive,
# and only whitespace around the username is ignored (ACC-1.7).
NON_MATCHING_USERNAMES = [
    pytest.param("Alice", id="capitalised"),
    pytest.param("ALICE", id="upper-case"),
    pytest.param("ali ce", id="inner-space"),
]

# The username limit is 150 characters after trimming and NFKC normalisation
# (ACC-1.3): (typed, the account's username).
USERNAME_LENGTHS = [
    pytest.param("a", "a", id="1-character"),
    pytest.param(LONGEST, LONGEST, id="150-characters"),
    pytest.param(f" {LONGEST}\u3000", LONGEST, id="150-after-trimming"),
    pytest.param("e\u0301" * 150, "\u00e9" * 150, id="150-after-nfkc"),
    pytest.param(
        DECOMPOSED_ALPHA * 150, COMPOSED_ALPHA * 150, id="600-typed-150-after-nfkc"
    ),
    pytest.param(
        f"{DECOMPOSED_ALPHA * 150} ",
        COMPOSED_ALPHA * 150,
        id="601-typed-150-after-trimming-and-nfkc",
    ),
]
# Typed usernames 151 characters long after trimming and NFKC, each with the
# account whose username they would be if cut to 150 characters (ACC-1.3).
TOO_LONG_USERNAMES = [
    pytest.param("e\u0301" * 151, "\u00e9" * 150, id="151-after-nfkc"),
    pytest.param(
        DECOMPOSED_ALPHA * 150 + "\u0391",
        COMPOSED_ALPHA * 150,
        id="601-typed-151-after-nfkc",
    ),
    pytest.param("a" * 601, LONGEST, id="601-characters"),
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
# Methods that /sign-in/ does not list (TECHNICAL-SPEC "Routes").
OTHER_METHODS = methods_not_listed("GET", "POST")
# NFKC turns at most 4 characters into 1, so no typed username longer than 4
# times the 150-character limit can be 150 characters after NFKC (ACC-1.3).
# Longer input is refused without being normalised, because NFKC is slow on
# huge input.
LONGEST_NORMALISED = 4 * len(LONGEST)
OVER_LONGEST_NORMALISED = [
    pytest.param(LONGEST_NORMALISED + 1, id="601-characters"),
    pytest.param(100_000, id="100000-characters"),
]

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


@pytest.fixture
def normalised_lengths(monkeypatch):
    """Return a list of the length of each string normalised during the test.

    It patches `unicodedata.normalize` as `django.contrib.auth.forms` reaches
    it, so the list grows each time anything calls it, and the string is
    still normalised.
    """
    lengths = []
    normalize = auth_forms.unicodedata.normalize

    def recording_normalize(form, text):
        lengths.append(len(text))
        return normalize(form, text)

    monkeypatch.setattr(auth_forms.unicodedata, "normalize", recording_normalize)
    return lengths


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
@pytest.mark.parametrize(("escaped", "count"), OVERSIZED_USERNAMES)
def test_sign_in_oversized_username_matches_no_account(
    make_account, browser, escaped, count
):
    make_account(LONGEST, PASSWORD, REQUESTER)
    assert_matches_no_account(browser, unquote(escaped) * count, PASSWORD)


@pytest.mark.ac("ACC-1.3")
@pytest.mark.parametrize("length", OVER_LONGEST_NORMALISED)
def test_sign_in_username_over_600_characters_never_normalised_matches_no_account(
    make_account, browser, normalised_lengths, length
):
    make_account(LONGEST, PASSWORD, REQUESTER)
    assert_matches_no_account(browser, "a" * length, PASSWORD)
    assert max(normalised_lengths, default=0) <= LONGEST_NORMALISED, (
        f"NFKC was applied to {max(normalised_lengths)} characters."
    )


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
def test_sign_in_username_600_characters_normalised_signs_in(
    make_account, browser, normalised_lengths
):
    username = COMPOSED_ALPHA * 150
    make_account(username, PASSWORD, SUPPORT_OFFICER)
    typed = DECOMPOSED_ALPHA * 150
    assert len(typed) == LONGEST_NORMALISED
    response = sign_in(browser, typed, PASSWORD)
    assert LONGEST_NORMALISED in normalised_lengths
    assert_redirects(response, ROLE_PAGES[SUPPORT_OFFICER])
    assert_signed_in_as(browser, SUPPORT_OFFICER, username)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize(("typed", "username"), TOO_LONG_USERNAMES)
def test_sign_in_username_151_after_nfkc_matches_no_account(
    make_account, browser, typed, username
):
    make_account(username, PASSWORD, SUPPORT_OFFICER)
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
def test_sign_in_username_trimmed_and_normalised_signs_in(make_account, browser, typed):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    assert_redirects(sign_in(browser, typed, PASSWORD), ROLE_PAGES[REQUESTER])
    assert_signed_in_as(browser, REQUESTER, ACCOUNT)


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("typed", NON_MATCHING_USERNAMES)
def test_sign_in_username_other_case_or_inner_space_matches_no_account(
    make_account, browser, typed
):
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
    make_account(username, PASSWORD, SUPPORT_OFFICER)
    assert_redirects(sign_in(browser, typed, PASSWORD), ROLE_PAGES[SUPPORT_OFFICER])
    assert_signed_in_as(browser, SUPPORT_OFFICER, username)


@pytest.mark.ac("ACC-1.7")
def test_sign_in_password_with_spaces_typed_exactly_signs_in(make_account, browser):
    make_account(ACCOUNT, SPACED_PASSWORD, REQUESTER)
    response = sign_in(browser, ACCOUNT, SPACED_PASSWORD)
    assert_redirects(response, ROLE_PAGES[REQUESTER])


@pytest.mark.ac("ACC-1.3", "ACC-1.7")
@pytest.mark.parametrize("typed", NON_MATCHING_PASSWORDS)
def test_sign_in_password_not_exact_matches_no_account(make_account, browser, typed):
    make_account(ACCOUNT, PASSWORD, REQUESTER)
    page = get_sign_in_page(browser)
    response = submit_sign_in(browser, page, ACCOUNT, typed)
    assert_sign_in_failed(response, ACCOUNT, page)
    assert_signed_out(browser)
