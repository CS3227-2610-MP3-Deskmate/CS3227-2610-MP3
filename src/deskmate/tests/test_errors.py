"""PLT-1.4: with debug off, errors get bare responses and server errors are logged."""

from urllib.parse import unquote

import pytest
from django.test import Client

from deskmate.tests.environment import valid_environment
from deskmate.tests.failing_urls import (
    FAILING_PATH,
    FAILURE_MESSAGE,
    SyntheticFailureError,
)
from deskmate.tests.helpers import internal_details, run_probe

# PLT-1.4's examples, stored escaped as the spec writes them.
ADMIN_PATH = "/admin"
INJECTED_PATH = "/%3Cscript%3Ealert(1)%3C/script%3E/"
UNMATCHED_PATHS = [ADMIN_PATH, ADMIN_PATH + "/", INJECTED_PATH]
# Unmatched paths that a browser would read as another site's address if it
# were sent there, with and without the trailing slash.
OFFSITE_PATH = "//evil.example"
OFFSITE_PATHS = [OFFSITE_PATH, OFFSITE_PATH + "/"]
FAILING_URLCONF = "deskmate.tests.failing_urls"


def failure_details():
    return {
        "the exception's message": FAILURE_MESSAGE,
        "the exception's type": SyntheticFailureError.__name__,
    }


def get_path_as_sent(client, path):
    """GET `path` exactly as a server receives it.

    The test client reads a leading "//" as a host name and would request "/",
    so the path is set directly and checked to be the one requested.
    """
    response = client.get("/", PATH_INFO=path)
    assert response.wsgi_request.path_info == path
    return response


@pytest.fixture
def debug_off(settings):
    settings.DEBUG = False
    return settings


@pytest.mark.ac("PLT-1.4")
@pytest.mark.parametrize("path", UNMATCHED_PATHS)
def test_errors_unmatched_path_returns_404(client, debug_off, path):
    assert client.get(path).status_code == 404


@pytest.mark.ac("PLT-1.4")
@pytest.mark.parametrize("path", UNMATCHED_PATHS)
def test_errors_unmatched_path_shows_no_internal_details(client, debug_off, path):
    body = client.get(path).content.decode("utf-8", "replace")
    secret_key = {"the secret key": debug_off.SECRET_KEY}
    assert internal_details(body, secret_key) == []


@pytest.mark.ac("PLT-1.4")
def test_errors_injected_path_is_not_reflected(client, debug_off):
    body = client.get(INJECTED_PATH).content.decode("utf-8", "replace")
    injected_markup = unquote(INJECTED_PATH).strip("/")
    assert injected_markup not in body


@pytest.mark.ac("PLT-1.4")
@pytest.mark.parametrize("path", OFFSITE_PATHS)
def test_errors_offsite_path_returns_404(client, debug_off, path):
    assert get_path_as_sent(client, path).status_code == 404


@pytest.mark.ac("PLT-1.4")
@pytest.mark.parametrize("path", OFFSITE_PATHS)
def test_errors_offsite_path_does_not_redirect(client, debug_off, path):
    response = get_path_as_sent(client, path)
    assert not 300 <= response.status_code < 400
    assert "Location" not in response


@pytest.mark.ac("PLT-1.4")
@pytest.mark.urls(FAILING_URLCONF)
def test_errors_unexpected_error_returns_500(debug_off):
    client = Client(raise_request_exception=False)
    assert client.get(FAILING_PATH).status_code == 500


@pytest.mark.ac("PLT-1.4")
@pytest.mark.urls(FAILING_URLCONF)
def test_errors_unexpected_error_shows_no_internal_details(debug_off):
    client = Client(raise_request_exception=False)
    body = client.get(FAILING_PATH).content.decode("utf-8", "replace")
    details = {**failure_details(), "the secret key": debug_off.SECRET_KEY}
    assert internal_details(body, details) == []


@pytest.mark.ac("PLT-1.4")
def test_errors_unexpected_error_writes_traceback_to_stderr():
    environment = valid_environment()
    process, result = run_probe(FAILING_PATH, environment, urlconf=FAILING_URLCONF)
    assert result["debug"] is False
    assert result["status"] == 500
    assert "Traceback (most recent call last)" in process.stderr
    assert f"{SyntheticFailureError.__name__}: {FAILURE_MESSAGE}" in process.stderr
    details = {
        **failure_details(),
        "the secret key": environment["DJANGO_SECRET_KEY"],
    }
    assert internal_details(result["body"], details) == []
