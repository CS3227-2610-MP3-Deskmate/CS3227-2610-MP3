"""PLT-1.2 and PLT-1.3: the health check reports whether the database answers,
whether or not the visitor sends a signed-in session cookie."""

import json

import pytest

from deskmate.tests.helpers import media_type
from deskmate.tests.signing_in import REQUESTER, SUPPORT_OFFICER, sign_in_as


def assert_health(response, status, body):
    assert response.status_code == status
    assert media_type(response) == "application/json"
    assert json.loads(response.content) == body


@pytest.mark.ac("PLT-1.2")
@pytest.mark.django_db
def test_health_database_answers_returns_200_ok(client):
    assert_health(client.get("/health/"), 200, {"status": "ok"})


@pytest.mark.ac("PLT-1.3")
@pytest.mark.usefixtures("database_refuses_connections")
def test_health_database_refuses_connections_returns_503_error(client):
    assert_health(client.get("/health/"), 503, {"status": "error"})


@pytest.mark.ac("PLT-1.3")
@pytest.mark.usefixtures("database_rejects_credentials")
def test_health_database_rejects_credentials_returns_503_error(client):
    assert_health(client.get("/health/"), 503, {"status": "error"})


@pytest.mark.ac("PLT-1.2")
def test_health_signed_in_database_answers_returns_200_ok(make_account):
    browser, _ = sign_in_as(make_account, REQUESTER)
    assert_health(browser.get("/health/"), 200, {"status": "ok"})


@pytest.mark.ac("PLT-1.3")
def test_health_signed_in_database_down_returns_503_error(
    make_account, database_outage
):
    # A browser that signed in sends its session cookie with every request.
    browser, _ = sign_in_as(make_account, SUPPORT_OFFICER)
    with database_outage():
        response = browser.get("/health/")
    assert_health(response, 503, {"status": "error"})
