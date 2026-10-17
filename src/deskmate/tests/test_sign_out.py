"""ACC-1.2: signing out with the Sign out button, only by POST /sign-out/."""

import pytest
from django.conf import settings

from deskmate.tests.accounts import (
    ROLE_PAGES,
    ROLES,
    SIGN_IN,
    SIGN_OUT,
    assert_method_not_allowed,
    assert_redirects,
    assert_signed_in_as,
    assert_signed_out,
    csrf_token,
    new_browser,
    send,
    session_cookie,
    sign_in_as,
)
from deskmate.tests.pages import Page


def press_sign_out(browser, role):
    """Press the Sign out button on `role`'s page in `browser`."""
    response = browser.get(ROLE_PAGES[role])
    assert response.status_code == 200, f"GET {ROLE_PAGES[role]} failed."
    form = Page(response).form_with_button("Sign out")
    return form.submit(browser, button="Sign out")


@pytest.mark.ac("ACC-1.2", "ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_button_signs_out_and_redirects_to_sign_in(make_account, role):
    browser, _ = sign_in_as(make_account, role)
    assert_redirects(press_sign_out(browser, role), SIGN_IN)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.2", "ACC-1.4")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_old_session_cookie_sent_again_is_signed_out(make_account, role):
    browser, _ = sign_in_as(make_account, role)
    old_cookie = session_cookie(browser)
    assert old_cookie
    press_sign_out(browser, role)
    replay = new_browser()
    replay.cookies[settings.SESSION_COOKIE_NAME] = old_cookie
    assert_signed_out(replay)


@pytest.mark.ac("ACC-1.2")
@pytest.mark.django_db
def test_sign_out_signed_out_visitor_redirects_to_sign_in(browser):
    response = send(browser, "POST", SIGN_OUT, csrf_token(browser))
    assert_redirects(response, SIGN_IN)


@pytest.mark.ac("ACC-1.2")
@pytest.mark.parametrize("role", ROLES)
def test_sign_out_get_returns_405_empty_stays_signed_in(make_account, role):
    browser, account = sign_in_as(make_account, role)
    assert_method_not_allowed(browser.get(SIGN_OUT))
    assert_signed_in_as(browser, role, account.username)
