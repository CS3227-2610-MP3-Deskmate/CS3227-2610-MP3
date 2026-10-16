"""PLT-2.8: process-level database transport and production host controls."""

import pytest

from deskmate.tests.environment import valid_environment
from deskmate.tests.helpers import run_manage, run_probe

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
