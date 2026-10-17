"""ACC-1.6: sessions last 8 hours from signing in, and their cookies.

The `clock` fixture stops Django's clock, so each test signs in at an exact
moment and then moves the clock to just before, at or after the limit.
"""

from datetime import timedelta
from importlib import import_module

import pytest
from django.conf import settings

from deskmate.tests.signing_in import (
    PASSWORD,
    REQUESTER,
    ROLE_PAGES,
    SIGN_IN,
    SUPPORT_OFFICER,
    UNKNOWN_SESSION_KEY,
    assert_redirects,
    assert_sign_in_page,
    assert_signed_in_as,
    assert_signed_out,
    new_browser,
    session_cookie,
    sign_in,
    sign_in_as,
)

EIGHT_HOURS = timedelta(hours=8)
ONE_SECOND = timedelta(seconds=1)


def session_store():
    """Return the session store class of Django's configured session engine."""
    return import_module(settings.SESSION_ENGINE).SessionStore


@pytest.mark.ac("ACC-1.6")
def test_session_just_under_8_hours_serves_role_page(make_account, clock):
    browser, account = sign_in_as(make_account, REQUESTER)
    clock.set_elapsed(EIGHT_HOURS - ONE_SECOND)
    assert_signed_in_as(browser, REQUESTER, account.username)


@pytest.mark.ac("ACC-1.6", "ACC-1.4")
@pytest.mark.parametrize(
    ("elapsed", "role"),
    [
        pytest.param(EIGHT_HOURS, SUPPORT_OFFICER, id="at-8-hours"),
        pytest.param(EIGHT_HOURS + ONE_SECOND, REQUESTER, id="over-8-hours"),
    ],
)
def test_session_8_hours_or_more_after_sign_in_signs_out(
    make_account, clock, elapsed, role
):
    browser, _ = sign_in_as(make_account, role)
    clock.set_elapsed(elapsed)
    assert_redirects(browser.get(ROLE_PAGES[role]), SIGN_IN)
    assert_sign_in_page(browser.get(SIGN_IN))


@pytest.mark.ac("ACC-1.6")
def test_session_activity_does_not_extend_8_hours(make_account, clock):
    browser, account = sign_in_as(make_account, SUPPORT_OFFICER)
    moments = [timedelta(hours=hours) for hours in range(1, 8)]
    for elapsed in [*moments, EIGHT_HOURS - ONE_SECOND]:
        clock.set_elapsed(elapsed)
        assert_signed_in_as(browser, SUPPORT_OFFICER, account.username)
        assert_redirects(browser.get(SIGN_IN), ROLE_PAGES[SUPPORT_OFFICER])
    clock.set_elapsed(EIGHT_HOURS)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.6", "ACC-1.4")
def test_session_saved_again_after_sign_in_still_ends_at_8_hours(make_account, clock):
    browser, account = sign_in_as(make_account, REQUESTER)
    clock.set_elapsed(EIGHT_HOURS - ONE_SECOND)
    # A later feature writes to the session, so Django saves it again and sets
    # its database expiry 8 hours from now.
    session = browser.session
    session["synthetic"] = "written by a later feature"
    session.save()
    stored = session.get_model_class().objects.get(session_key=session.session_key)
    assert stored.expire_date > clock.start + EIGHT_HOURS
    assert_signed_in_as(browser, REQUESTER, account.username)
    clock.set_elapsed(EIGHT_HOURS)
    assert_signed_out(browser)
    assert_sign_in_page(browser.get(SIGN_IN))


@pytest.mark.ac("ACC-1.6")
def test_session_signed_out_by_time_sign_in_again_starts_new_8_hours(
    make_account, clock
):
    browser, account = sign_in_as(make_account, REQUESTER)
    clock.set_elapsed(EIGHT_HOURS)
    assert_signed_out(browser)
    response = sign_in(browser, account.username, PASSWORD)
    assert_redirects(response, ROLE_PAGES[REQUESTER])
    clock.set_elapsed(2 * EIGHT_HOURS - ONE_SECOND)
    assert_signed_in_as(browser, REQUESTER, account.username)
    clock.set_elapsed(2 * EIGHT_HOURS)
    assert_signed_out(browser)


@pytest.mark.ac("ACC-1.6")
def test_session_cookie_set_at_sign_in_has_no_expires_or_max_age(make_account, browser):
    make_account("rhea", PASSWORD, REQUESTER)
    response = sign_in(browser, "rhea", PASSWORD)
    morsel = response.cookies[settings.SESSION_COOKIE_NAME]
    assert morsel.value
    assert morsel["expires"] == ""
    assert morsel["max-age"] == ""


@pytest.mark.ac("ACC-1.6")
def test_session_cookie_set_at_sign_in_is_secure_lax_httponly(make_account, browser):
    make_account("rhea", PASSWORD, REQUESTER)
    response = sign_in(browser, "rhea", PASSWORD)
    assert settings.DEBUG is False
    morsel = response.cookies[settings.SESSION_COOKIE_NAME]
    assert morsel["secure"]
    assert morsel["samesite"].lower() == "lax"
    assert morsel["httponly"]


@pytest.mark.ac("ACC-1.6")
def test_session_csrf_cookies_are_secure_lax(make_account, browser):
    make_account("rhea", PASSWORD, REQUESTER)
    page_response = browser.get(SIGN_IN)
    sign_in_response = sign_in(browser, "rhea", PASSWORD)
    assert settings.DEBUG is False
    assert page_response.cookies[settings.CSRF_COOKIE_NAME].value
    for response in (page_response, sign_in_response):
        morsel = response.cookies.get(settings.CSRF_COOKIE_NAME)
        if morsel is not None and morsel.value:
            assert morsel["secure"]
            assert morsel["samesite"].lower() == "lax"


@pytest.mark.ac("ACC-1.6")
@pytest.mark.parametrize("held", ["anonymous-session", "unknown-key"])
def test_session_cookie_held_before_sign_in_identifies_no_session_after(
    make_account, held
):
    make_account("rhea", PASSWORD, REQUESTER)
    if held == "anonymous-session":
        planted = session_store()()
        planted["synthetic"] = "held before signing in"
        planted.save()
        old_key = planted.session_key
    else:
        old_key = UNKNOWN_SESSION_KEY
    browser = new_browser()
    browser.cookies[settings.SESSION_COOKIE_NAME] = old_key
    assert_redirects(sign_in(browser, "rhea", PASSWORD), ROLE_PAGES[REQUESTER])
    assert session_cookie(browser) not in (None, "", old_key)
    assert not session_store()().exists(old_key)
    replay = new_browser()
    replay.cookies[settings.SESSION_COOKIE_NAME] = old_key
    assert_signed_out(replay)
    assert_signed_in_as(browser, REQUESTER, "rhea")
