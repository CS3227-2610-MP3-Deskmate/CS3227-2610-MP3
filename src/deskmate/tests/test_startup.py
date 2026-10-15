"""PLT-1.7: Deskmate refuses to start while a required variable is unset or invalid.

Each case runs `src/manage.py` in a new process with only the variables it sets,
as the TECHNICAL-SPEC Configuration table defines them.
"""

import secrets
import subprocess

import pytest

from deskmate.tests.environment import make_secret_key
from deskmate.tests.helpers import run_manage, unused_port

ALWAYS_REQUIRED = [
    "POSTGRES_HOST",
    "POSTGRES_PORT",
    "POSTGRES_DB",
    "POSTGRES_USER",
    "POSTGRES_PASSWORD",
]
REQUIRED_WITH_DEBUG_OFF = ["DJANGO_SECRET_KEY", "DJANGO_ALLOWED_HOSTS"]
REQUIRED = ALWAYS_REQUIRED + REQUIRED_WITH_DEBUG_OFF
# Local development's debug settings, as in .env.example.
DEBUG_ON = {"DJANGO_DEBUG": "true", "DJANGO_SECRET_KEY": ""}
SERVER_TIMEOUT_SECONDS = 30


def message(name):
    return f"Deskmate cannot start: {name} is not set or is invalid."


@pytest.fixture
def tag():
    """A random tag carried by the configuration's values, to spot any leak."""
    return secrets.token_hex(6)


def configuration(tag, overrides=None):
    """A valid debug-off configuration, changed by `overrides`; None unsets."""
    environment = {
        "POSTGRES_HOST": f"{tag}-host.invalid",
        "POSTGRES_PORT": "5432",
        "POSTGRES_DB": f"{tag}-db",
        "POSTGRES_USER": f"{tag}-user",
        "POSTGRES_PASSWORD": f"{tag}-password",
        "DJANGO_SECRET_KEY": make_secret_key(),
        "DJANGO_ALLOWED_HOSTS": f"{tag}.example.test",
    }
    environment.update(overrides or {})
    return {name: value for name, value in environment.items() if value is not None}


def leaked_values(output, environment, tag):
    """Return which values, or parts of them, appear in `output`."""
    leaks = [
        name
        for name, value in environment.items()
        if len(value.strip()) >= 6 and value in output
    ]
    if tag in output:
        leaks.append("the tag in the values")
    key = environment.get("DJANGO_SECRET_KEY", "")
    pieces = {key[start : start + 12] for start in range(len(key) - 11)}
    if any(piece.isalnum() and piece in output for piece in pieces):
        leaks.append("part of DJANGO_SECRET_KEY")
    return leaks


def assert_refuses_to_start(process, invalid, environment, tag):
    assert process.returncode != 0
    for name in invalid:
        assert message(name) in process.stderr
    wrongly_named = [
        name
        for name in REQUIRED
        if name not in invalid and message(name) in process.stderr
    ]
    assert wrongly_named == []
    output = process.stdout + process.stderr
    assert leaked_values(output, environment, tag) == []


def assert_starts(process):
    assert "Deskmate cannot start" not in process.stderr
    assert process.returncode == 0, process.stderr


def check(environment):
    return run_manage(["check"], environment)


# Pairwise: every variable both unset and empty, and with debug both off and on.
MISSING_DATABASE_VARIABLES = [
    pytest.param("POSTGRES_HOST", None, False, id="host-unset-debug-off"),
    pytest.param("POSTGRES_HOST", "", True, id="host-empty-debug-on"),
    pytest.param("POSTGRES_PORT", None, True, id="port-unset-debug-on"),
    pytest.param("POSTGRES_PORT", "", False, id="port-empty-debug-off"),
    pytest.param("POSTGRES_DB", None, False, id="db-unset-debug-off"),
    pytest.param("POSTGRES_DB", "", True, id="db-empty-debug-on"),
    pytest.param("POSTGRES_USER", None, True, id="user-unset-debug-on"),
    pytest.param("POSTGRES_USER", "", False, id="user-empty-debug-off"),
    pytest.param("POSTGRES_PASSWORD", None, False, id="password-unset-debug-off"),
    pytest.param("POSTGRES_PASSWORD", "", True, id="password-empty-debug-on"),
]


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize(("name", "value", "debug"), MISSING_DATABASE_VARIABLES)
def test_startup_database_variable_missing_refuses_to_start(tag, name, value, debug):
    overrides = {**(DEBUG_ON if debug else {}), name: value}
    environment = configuration(tag, overrides)
    assert_refuses_to_start(check(environment), [name], environment, tag)


@pytest.mark.ac("PLT-1.7")
def test_startup_database_variables_one_space_starts(tag):
    one_space = {
        "POSTGRES_HOST": " ",
        "POSTGRES_DB": " ",
        "POSTGRES_USER": " ",
        "POSTGRES_PASSWORD": " ",
    }
    assert_starts(check(configuration(tag, one_space)))


INVALID_PORTS = [
    pytest.param("not-a-port", id="not-a-number"),
    pytest.param("0", id="0-below-range"),
    pytest.param("65536", id="65536-above-range"),
    pytest.param("+5432", id="plus-sign"),
    pytest.param(" 5432", id="leading-space"),
    pytest.param("5_432", id="underscore"),
]


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize("port", INVALID_PORTS)
def test_startup_port_invalid_refuses_to_start(tag, port):
    environment = configuration(tag, {"POSTGRES_PORT": port})
    assert_refuses_to_start(check(environment), ["POSTGRES_PORT"], environment, tag)


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize("port", ["1", "2", "65534", "65535"])
def test_startup_port_in_range_starts(tag, port):
    assert_starts(check(configuration(tag, {"POSTGRES_PORT": port})))


INVALID_SECRET_KEYS = [
    pytest.param(lambda: None, id="unset"),
    pytest.param(lambda: "", id="empty"),
    pytest.param(lambda: make_secret_key(49), id="49-characters"),
    pytest.param(lambda: make_secret_key(64, distinct=4), id="4-different"),
    pytest.param(
        lambda: "django-insecure-" + make_secret_key(50), id="django-insecure-start"
    ),
]


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize("make_key", INVALID_SECRET_KEYS)
def test_startup_secret_key_invalid_with_debug_off_refuses_to_start(tag, make_key):
    environment = configuration(tag, {"DJANGO_SECRET_KEY": make_key()})
    process = check(environment)
    assert_refuses_to_start(process, ["DJANGO_SECRET_KEY"], environment, tag)


VALID_SECRET_KEYS = [
    pytest.param(lambda: make_secret_key(50), id="50-characters"),
    pytest.param(lambda: make_secret_key(51), id="51-characters"),
    pytest.param(lambda: make_secret_key(64, distinct=5), id="5-different"),
    pytest.param(lambda: make_secret_key(64, distinct=6), id="6-different"),
    pytest.param(
        lambda: make_secret_key(1) + "django-insecure-" + make_secret_key(49),
        id="django-insecure-not-at-start",
    ),
]


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize("make_key", VALID_SECRET_KEYS)
def test_startup_secret_key_valid_with_debug_off_starts(tag, make_key):
    assert_starts(check(configuration(tag, {"DJANGO_SECRET_KEY": make_key()})))


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize(
    "hosts",
    [
        pytest.param(None, id="unset"),
        pytest.param("", id="empty"),
        pytest.param(",", id="only-a-comma"),
        pytest.param(" , , ", id="only-spaces-and-commas"),
    ],
)
def test_startup_allowed_hosts_without_a_name_with_debug_off_refuses_to_start(
    tag, hosts
):
    environment = configuration(tag, {"DJANGO_ALLOWED_HOSTS": hosts})
    process = check(environment)
    assert_refuses_to_start(process, ["DJANGO_ALLOWED_HOSTS"], environment, tag)


@pytest.mark.ac("PLT-1.7")
def test_startup_allowed_hosts_name_among_spaces_and_empty_items_starts(tag):
    hosts = {"DJANGO_ALLOWED_HOSTS": " , localhost , "}
    assert_starts(check(configuration(tag, hosts)))


@pytest.mark.ac("PLT-1.7")
@pytest.mark.parametrize(
    ("secret_key", "hosts"),
    [
        pytest.param(None, "", id="key-unset-hosts-empty"),
        pytest.param("", None, id="key-empty-hosts-unset"),
    ],
)
def test_startup_debug_on_without_secret_key_or_hosts_starts(tag, secret_key, hosts):
    overrides = {
        "DJANGO_DEBUG": "true",
        "DJANGO_SECRET_KEY": secret_key,
        "DJANGO_ALLOWED_HOSTS": hosts,
    }
    assert_starts(check(configuration(tag, overrides)))


@pytest.mark.ac("PLT-1.7")
def test_startup_every_variable_unset_with_debug_off_names_each(tag):
    environment = configuration(tag, dict.fromkeys(REQUIRED))
    assert_refuses_to_start(check(environment), REQUIRED, environment, tag)


@pytest.mark.ac("PLT-1.7")
def test_startup_every_variable_unset_with_debug_on_names_database_ones(tag):
    environment = configuration(
        tag, {**dict.fromkeys(REQUIRED), "DJANGO_DEBUG": "true"}
    )
    assert_refuses_to_start(check(environment), ALWAYS_REQUIRED, environment, tag)


def shell_command_creating(marker):
    return ["shell", "-c", f"open({str(marker)!r}, 'w').close()"]


@pytest.mark.ac("PLT-1.7")
def test_startup_invalid_configuration_does_not_run_command(tag, tmp_path):
    marker = tmp_path / "command-ran"
    environment = configuration(tag, {"DJANGO_ALLOWED_HOSTS": None})
    process = run_manage(shell_command_creating(marker), environment)
    assert_refuses_to_start(process, ["DJANGO_ALLOWED_HOSTS"], environment, tag)
    assert not marker.exists()


@pytest.mark.ac("PLT-1.7")
def test_startup_valid_configuration_runs_command(tag, tmp_path):
    marker = tmp_path / "command-ran"
    process = run_manage(shell_command_creating(marker), configuration(tag))
    assert_starts(process)
    assert marker.exists()


@pytest.mark.ac("PLT-1.7")
def test_startup_invalid_configuration_web_server_exits_without_serving(tag):
    weak_key = "django-insecure-" + make_secret_key(50)
    environment = configuration(tag, {"DJANGO_SECRET_KEY": weak_key})
    address = f"127.0.0.1:{unused_port()}"
    arguments = ["runserver", "--noreload", address]
    try:
        process = run_manage(arguments, environment, SERVER_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        pytest.fail(f"The web server was still running after {SERVER_TIMEOUT_SECONDS}s")
    assert_refuses_to_start(process, ["DJANGO_SECRET_KEY"], environment, tag)
