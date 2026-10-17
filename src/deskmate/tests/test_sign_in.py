"""ACC-1.1, ACC-1.3 and ACC-1.7: signing in with a username and password.

Also the sign-in parts of ACC-1.4, a database that does not answer, and of
ACC-1.5, parameters that try to choose where signing in leads.
"""

from urllib.parse import unquote, urlencode

import pytest
from django.conf import settings

from deskmate.tests.accounts import (
    NOT_FOR_YOUR_ROLE,
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SIGN_IN_ERROR,
    SUPPORT_OFFICER,
    WRONG_PASSWORD,
    assert_forbidden,
    assert_redirects,
    assert_server_error,
    assert_sign_in_failed,
    assert_sign_in_page,
    assert_signed_in_as,
    assert_signed_out,
    csrf_token,
    get_sign_in_page,
    new_browser,
    other_role,
    sign_in,
    sign_in_as,
    submit_sign_in,
)
from deskmate.tests.pages import CSRF_FIELD, Page

ACCOUNT = "alice"
LONGEST = "a" * 150
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

# Red-team usernames, stored escaped and decoded only inside the test.
MARKUP_USERNAMES = [
    pytest.param("%3Cscript%3Ealert(1)%3C%2Fscript%3E", id="script-element"),
    pytest.param(
        "%22%3E%3Cimg%20src%3Dx%20onerror%3Dalert(1)%3E", id="attribute-breakout"
    ),
    pytest.param("%26lt%3Bb%26gt%3B", id="character-reference"),
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


@pytest.mark.ac("ACC-1.1")
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
