"""ACC-2.1, ACC-2.2, ACC-2.3 and ACC-2.7: creating a demo workspace from the
sign-in page, signing in with its accounts, the usernames and passwords it
generates, codes that clash, and signed-in users who send the form.

Tests where codes clash choose the codes Deskmate draws with the `codes`
fixture, and their database is not wrapped in a transaction, so what a
clashing attempt writes would really remain unless the attempt undoes it.
"""

from datetime import timedelta

import pytest

from deskmate.tests.demo_workspaces import (
    ACCOUNTS,
    CLASH_TIMES,
    DEMO_WORKSPACE,
    assert_created,
    assert_demo_form,
    assert_nothing_created,
    press_create,
    role_of,
    signed_in_account_ids,
    stored_state,
    usernames_for,
    watching,
)
from deskmate.tests.pages import Page
from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SUPPORT_OFFICER,
    WRONG_PASSWORD,
    assert_redirects,
    assert_sign_in_failed,
    assert_sign_in_page,
    assert_signed_in_as,
    assert_signed_out,
    csrf_token,
    get_sign_in_page,
    new_browser,
    send,
    session_cookie,
    sign_in,
    sign_in_as,
    submit_sign_in,
)

pytestmark = pytest.mark.usefixtures("fast_hashing")

# Codes, from the 31 characters, for the tests to make Deskmate draw (ACC-2.3).
FIRST, SECOND, THIRD = "aaaaaa", "bbbbbb", "cccccc"
TAKEN = [pytest.param(number, id=prefix) for number, (prefix, _) in enumerate(ACCOUNTS)]
# Usernames like one of a code's but not the same, so the code does not clash;
# usernames are compared case-sensitively (ACC-1.7).
NEAR_MISSES = [
    pytest.param("Requester1-{code}", id="other-case"),
    pytest.param("support2-{code}", id="other-number"),
    pytest.param("requester1-{code}2", id="longer"),
]
EIGHT_HOURS = timedelta(hours=8)
ONE_SECOND = timedelta(seconds=1)


def press_with_taken(make_account, browser, taken, when):
    """Take each username in `taken` as `when` says, then press the button.

    Returns the stored state from just before pressing, and the response.
    """
    if when == "before":
        for username in taken:
            make_account(username, PASSWORD, role_of(username))
    before = stored_state()
    page = get_sign_in_page(browser)
    with watching() as watch:
        if when == "meanwhile":
            watch.take_meanwhile(taken)
        response = press_create(browser, page)
    return before, response


@pytest.mark.ac("ACC-2.1", "ACC-1.1")
@pytest.mark.django_db
def test_demo_sign_in_page_has_demo_form_after_sign_in_form(browser):
    page = assert_sign_in_page(browser.get(SIGN_IN))
    assert_demo_form(page)


@pytest.mark.ac("ACC-2.1", "ACC-1.3")
def test_demo_failed_sign_in_page_has_demo_form_that_creates(make_account, browser):
    make_account("alice", PASSWORD, REQUESTER)
    fresh = get_sign_in_page(browser)
    response = submit_sign_in(browser, fresh, "alice", WRONG_PASSWORD)
    assert_sign_in_failed(response, "alice", fresh)
    page = Page(response)
    assert_demo_form(page)
    before = stored_state()
    assert_created(press_create(browser, page), before)


@pytest.mark.ac("ACC-2.1", "ACC-2.2", "ACC-2.3")
def test_demo_button_creates_workspace_of_3_accounts_and_shows_them(
    make_account, browser
):
    # assert_created also checks each username, code and password against
    # ACC-2.3, and that no account that existed before changes.
    make_account("alice", PASSWORD, REQUESTER)
    make_account("bob", PASSWORD, SUPPORT_OFFICER)
    before = stored_state()
    assert_created(press_create(browser), before)


@pytest.mark.ac("ACC-2.2")
def test_demo_created_accounts_sign_in_to_their_role_pages(make_account, browser):
    make_account("alice", PASSWORD, REQUESTER)
    before = stored_state()
    accounts = assert_created(press_create(browser), before)
    for account in accounts:
        signed_in = new_browser()
        response = sign_in(signed_in, account.username, account.password)
        assert_redirects(response, ROLE_PAGES[account.role])
        assert_signed_in_as(signed_in, account.role, account.username)


@pytest.mark.ac("ACC-2.2")
def test_demo_creating_signs_no_one_in(db, browser):
    before = stored_state()
    assert_created(press_create(browser), before)
    assert_signed_out(browser)
    _, accounts = stored_state()
    new_ids = {str(pk) for pk in accounts if pk not in before[1]}
    assert signed_in_account_ids().isdisjoint(new_ids)


@pytest.mark.ac("ACC-2.3")
def test_demo_no_clash_draws_one_code_and_uses_it(db, browser, codes):
    draws = codes(FIRST)
    before = stored_state()
    response = press_create(browser)
    assert draws.count == 1
    accounts = assert_created(response, before)
    assert [account.username for account in accounts] == usernames_for(FIRST)


@pytest.mark.ac("ACC-2.3")
@pytest.mark.parametrize("when", CLASH_TIMES)
@pytest.mark.parametrize("taken", TAKEN)
def test_demo_first_code_clashes_creates_with_second_code(
    transactional_db, make_account, browser, codes, taken, when
):
    draws = codes(FIRST, SECOND)
    username = usernames_for(FIRST)[taken]
    before, response = press_with_taken(make_account, browser, [username], when)
    assert draws.count == 2
    # Nothing the clashing attempt wrote remains: one new workspace, holding
    # only the second code's accounts.
    accounts = assert_created(response, before, elsewhere=[username])
    assert [account.username for account in accounts] == usernames_for(SECOND)


@pytest.mark.ac("ACC-2.3")
@pytest.mark.parametrize("when", CLASH_TIMES)
def test_demo_first_2_codes_clash_creates_with_third_code(
    transactional_db, make_account, browser, codes, when
):
    draws = codes(FIRST, SECOND, THIRD)
    taken = [usernames_for(FIRST)[1], usernames_for(SECOND)[2]]
    before, response = press_with_taken(make_account, browser, taken, when)
    assert draws.count == 3
    accounts = assert_created(response, before, elsewhere=taken)
    assert [account.username for account in accounts] == usernames_for(THIRD)


@pytest.mark.ac("ACC-2.3", "ACC-1.7")
@pytest.mark.parametrize("near_miss", NEAR_MISSES)
def test_demo_similar_username_taken_does_not_clash(
    make_account, browser, codes, near_miss
):
    make_account(near_miss.format(code=FIRST), PASSWORD, REQUESTER)
    draws = codes(FIRST, SECOND)
    before = stored_state()
    response = press_create(browser)
    assert draws.count == 1
    accounts = assert_created(response, before)
    assert [account.username for account in accounts] == usernames_for(FIRST)


@pytest.mark.ac("ACC-2.7")
@pytest.mark.parametrize("role", ROLES)
def test_demo_signed_in_post_redirects_to_own_page_creates_nothing(make_account, role):
    browser, account = sign_in_as(make_account, role)
    session = session_cookie(browser)
    token = csrf_token(browser, role)
    before = stored_state()
    response = send(browser, "POST", DEMO_WORKSPACE, token)
    assert_redirects(response, ROLE_PAGES[role])
    assert_nothing_created(before)
    assert_signed_in_as(browser, role, account.username)
    assert session_cookie(browser) == session


@pytest.mark.ac("ACC-2.7", "ACC-1.6")
def test_demo_signed_in_just_under_8_hours_post_redirects_creates_nothing(
    make_account, clock
):
    browser, account = sign_in_as(make_account, SUPPORT_OFFICER)
    token = csrf_token(browser, SUPPORT_OFFICER)
    clock.set_elapsed(EIGHT_HOURS - ONE_SECOND)
    before = stored_state()
    response = send(browser, "POST", DEMO_WORKSPACE, token)
    assert_redirects(response, ROLE_PAGES[SUPPORT_OFFICER])
    assert_nothing_created(before)
    assert_signed_in_as(browser, SUPPORT_OFFICER, account.username)


@pytest.mark.ac("ACC-2.7", "ACC-2.1", "ACC-1.6")
def test_demo_session_8_hours_after_sign_in_post_creates_as_signed_out(
    make_account, clock
):
    # At 8 hours the user is signed out (ACC-1.6), so the request is a
    # signed-out visitor's, which creates a workspace.
    browser, _ = sign_in_as(make_account, REQUESTER)
    token = csrf_token(browser, REQUESTER)
    clock.set_elapsed(EIGHT_HOURS)
    before = stored_state()
    assert_created(send(browser, "POST", DEMO_WORKSPACE, token), before)
    assert_signed_out(browser)
