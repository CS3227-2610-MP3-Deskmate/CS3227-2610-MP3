"""PLT-1.2 and PLT-1.3: the health check reports whether the database answers."""

import json

import pytest

from deskmate.tests.helpers import media_type


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
