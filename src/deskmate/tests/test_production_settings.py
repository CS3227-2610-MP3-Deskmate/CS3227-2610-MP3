"""PLT-2: isolated production startup, database transport and host controls."""

import json
import os
import re
import subprocess
import sys

import pytest
from django.utils.html import strip_tags
from pytest_django.asserts import assertInHTML

from deskmate.tests.environment import is_configuration_variable, valid_environment
from deskmate.tests.helpers import (
    REPO_ROOT,
    SRC_DIR,
    TIMEOUT_SECONDS,
    run_manage,
    run_probe,
)

PUBLIC_HOST = "deskmate-synthetic.vercel.app"


def production_environment(overrides=None):
    return valid_environment(
        {
            "VERCEL_ENV": "production",
            "POSTGRES_HOST": "ep-synthetic.ap-southeast-1.aws.neon.tech",
            "DJANGO_ALLOWED_HOSTS": PUBLIC_HOST,
            **(overrides or {}),
        }
    )


@pytest.mark.ac("PLT-2.7", "PLT-1.1")
def test_production_wsgi_loaded_by_path_without_src_import_path_serves_home():
    probe = """
import importlib.util
import json
import sys
from contextlib import closing
from unittest.mock import patch
from wsgiref.util import setup_testing_defaults

spec = importlib.util.spec_from_file_location("vercel_wsgi", sys.argv[1])
module = importlib.util.module_from_spec(spec)
result = {}

def start_response(status, headers, exc_info=None):
    result.update(status=int(status.split()[0]), headers=dict(headers))

environ = {}
setup_testing_defaults(environ)
environ.update(HTTP_HOST=sys.argv[2], **{"wsgi.url_scheme": "https"})
with patch(
    "django.db.backends.base.base.BaseDatabaseWrapper.ensure_connection",
    side_effect=AssertionError("The home page must not connect to the database."),
):
    spec.loader.exec_module(module)
    with closing(module.application(environ, start_response)) as response:
        result["body"] = b"".join(response).decode("utf-8")
print(json.dumps(result))
"""
    environment = {
        name: value
        for name, value in os.environ.items()
        if not is_configuration_variable(name) and name != "PYTHONPATH"
    }
    environment.update(production_environment())
    process = subprocess.run(
        [
            sys.executable,
            "-I",
            "-c",
            probe,
            str(SRC_DIR / "deskmate" / "wsgi.py"),
            PUBLIC_HOST,
        ],
        env=environment,
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=TIMEOUT_SECONDS,
        check=False,
    )
    assert process.returncode == 0, process.stderr
    result = json.loads(process.stdout)
    assert result["status"] == 200
    assert result["headers"]["Content-Type"].split(";")[0] == "text/html"
    assertInHTML("<title>Deskmate</title>", result["body"], count=1)
    assertInHTML("<h1>Deskmate</h1>", result["body"], count=1)
    assertInHTML('<a href="/sign-in/">Sign in</a>', result["body"], count=1)
    visible = re.sub(
        r"<(style|script|template)\b.*?</\1>", "", result["body"], flags=re.DOTALL
    )
    assert " ".join(strip_tags(visible).split()) == (
        "Deskmate Deskmate Deskmate is a service desk: Requesters raise tickets and "
        "Support Officers resolve them. Sign in"
    )


@pytest.mark.ac("PLT-2.8")
@pytest.mark.parametrize(
    "host",
    [
        "ep-synthetic.ap-southeast-1.aws.neon.tech",
        "database.example.test",
        "192.0.2.1",
        "2001:db8::1",
        "localhost.example.test",
        "127.0.0.2",
    ],
)
def test_database_nonloopback_host_requires_verified_tls(host):
    environment = valid_environment({"POSTGRES_HOST": host})
    _, result = run_probe("/", environment)
    assert result["status"] == 200
    assert result["database_options"]["sslmode"] == "verify-full"
    assert result["database_options"]["sslrootcert"] == "system"
    assert result["database_options"]["connect_timeout"] == 5
    assert not result["database_options"]["pool"]
    assert result["connection_max_age"] == 0


@pytest.mark.ac("PLT-2.8")
@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1"])
def test_database_literal_loopback_preserves_local_startup_and_timeout(host):
    _, result = run_probe("/", valid_environment({"POSTGRES_HOST": host}))
    assert result["status"] == 200
    assert result["database_options"]["connect_timeout"] == 5


@pytest.mark.ac("PLT-2.8")
def test_database_environment_cannot_disable_remote_certificate_verification():
    environment = valid_environment(
        {
            "POSTGRES_HOST": "database.example.test",
            "PGSSLMODE": "disable",
            "PGSSLROOTCERT": "untrusted-test-certificate.pem",
            "POSTGRES_SSLMODE": "disable",
        }
    )
    _, result = run_probe("/", environment)
    assert result["database_options"]["sslmode"] == "verify-full"
    assert result["database_options"]["sslrootcert"] == "system"


@pytest.mark.ac("PLT-2.7", "PLT-2.8")
def test_production_exact_public_host_starts_with_debug_off_and_verified_tls():
    _, result = run_probe("/", production_environment(), host=PUBLIC_HOST)
    assert result["status"] == 200
    assert result["debug"] is False
    assert result["allowed_hosts"] == [PUBLIC_HOST]
    assert result["database_options"]["sslmode"] == "verify-full"
    assert result["database_options"]["sslrootcert"] == "system"
    assert result["connection_max_age"] == 0


@pytest.mark.ac("PLT-2.8")
@pytest.mark.parametrize(
    "hosts",
    [
        None,
        "",
        "*",
        ".vercel.app",
        "*.vercel.app",
        f"https://{PUBLIC_HOST}",
        f"{PUBLIC_HOST}:443",
        f"{PUBLIC_HOST}/path",
        f"{PUBLIC_HOST},other.vercel.app",
        "localhost",
        f"{PUBLIC_HOST}.example.test",
        "-bad.vercel.app",
    ],
)
def test_production_invalid_public_hostname_refuses_start_without_values(hosts):
    environment = production_environment({"DJANGO_ALLOWED_HOSTS": hosts})
    process = run_manage(["check"], environment)
    assert process.returncode != 0
    assert (
        "Deskmate cannot start: DJANGO_ALLOWED_HOSTS is not set or is invalid."
        in process.stderr
    )
    for name in ("DJANGO_SECRET_KEY", "POSTGRES_HOST", "POSTGRES_PASSWORD"):
        assert environment[name] not in process.stdout + process.stderr


@pytest.mark.ac("PLT-2.8")
def test_production_debug_true_refuses_start():
    process = run_manage(["check"], production_environment({"DJANGO_DEBUG": "true"}))
    assert process.returncode != 0
    assert (
        "Deskmate cannot start: DJANGO_DEBUG is not set or is invalid."
        in process.stderr
    )


@pytest.mark.ac("PLT-2.8")
@pytest.mark.parametrize("host", ["localhost", "127.0.0.1", "::1"])
def test_production_loopback_database_refuses_start(host):
    process = run_manage(["check"], production_environment({"POSTGRES_HOST": host}))
    assert process.returncode != 0
    assert (
        "Deskmate cannot start: POSTGRES_HOST is not set or is invalid."
        in process.stderr
    )


@pytest.mark.ac("PLT-2.8")
@pytest.mark.parametrize("host", ["other.vercel.app", "child." + PUBLIC_HOST])
def test_production_provider_metadata_does_not_expand_allowed_hosts(host):
    environment = production_environment({"VERCEL_URL": host})
    _, result = run_probe("/", environment, host=host)
    assert result["status"] == 400
    assert result["allowed_hosts"] == [PUBLIC_HOST]


@pytest.mark.ac("PLT-2.8")
def test_production_provider_environment_is_ignored_by_test_configuration(monkeypatch):
    monkeypatch.setenv("VERCEL_ENV", "production")
    monkeypatch.setenv("VERCEL_URL", "developer-state.vercel.app")
    _, result = run_probe("/", valid_environment())
    assert result["status"] == 200
