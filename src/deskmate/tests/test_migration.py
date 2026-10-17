"""PLT-2.6, 2.8, 2.12 to 2.14: the migration entry point, drift and atomicity.

The entry point is `src/deskmate/migrate.py`, run from the repository root with no
arguments, as the build command in `vercel.json` runs it. It uses the settings
module in DJANGO_SETTINGS_MODULE, or Deskmate's own when that is unset. Each test
gives it a new throwaway database and, through DJANGO_SETTINGS_MODULE, Deskmate's
settings plus the test-only apps in `migration_fixtures`.

Its standard output and standard error are captured together, unbuffered, so the
tests see every line it writes, in order.
"""

import json
import os
import secrets
import shutil
import socket
import ssl
import struct
import subprocess
import sys
from threading import Event, Thread

import psycopg
import pytest
from django.db import connection
from django.db.migrations import Migration
from django.db.migrations.loader import MigrationLoader
from psycopg import sql

from deskmate.tests.environment import (
    DATABASE,
    is_configuration_variable,
    valid_environment,
)
from deskmate.tests.helpers import (
    REPO_ROOT,
    SRC_DIR,
    TIMEOUT_SECONDS,
    run_manage,
    run_python,
    unused_port,
)

ENTRY_POINT = "src/deskmate/migrate.py"
FIXTURES = "deskmate.tests.migration_fixtures"
ORDERED = f"{FIXTURES}.ordered_settings"
FAILING = f"{FIXTURES}.failing_settings"
DRIFT = f"{FIXTURES}.drift_settings"
NOISY = f"{FIXTURES}.noisy_settings"
UNMIGRATED = f"{FIXTURES}.unmigrated_settings"
NOISY_MIGRATION = "migfix_noisy.0001_emit"
# The only order the ordered fixture apps' dependencies allow.
ORDERED_PLAN = [
    "migfix_beta.0001_initial",
    "migfix_alpha.0001_initial",
    "migfix_beta.0002_board_pinned",
]
FAILING_PLAN = ["migfix_fail.0001_kept", "migfix_fail.0002_copy_codes"]
PASSED = "migration: passed"
FAILED = "migration: failed"
NOTHING = "migration: nothing to apply"
PUBLIC_HOST = "deskmate-synthetic.vercel.app"


def applying(name):
    return f"migration: applying {name}"


def cannot_start(name):
    return f"Deskmate cannot start: {name} is not set or is invalid."


def run_entry_point(environment, settings=None, import_path=True):
    """Run the entry point configured only by `environment`; merge its output.

    `settings` sets DJANGO_SETTINGS_MODULE. Without `import_path`, PYTHONPATH is
    unset, as in the provider's build.
    """
    env = {
        name: value
        for name, value in os.environ.items()
        if not is_configuration_variable(name) and name != "PYTHONPATH"
    }
    env.update(environment)
    if settings:
        env["DJANGO_SETTINGS_MODULE"] = settings
    if import_path:
        env["PYTHONPATH"] = str(SRC_DIR)
    env.update(PYTHONUTF8="1", PYTHONUNBUFFERED="1")
    return subprocess.run(
        [sys.executable, ENTRY_POINT],
        env=env,
        cwd=REPO_ROOT,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=TIMEOUT_SECONDS,
        check=False,
    )


def lines(process):
    return process.stdout.splitlines()


def connect(database=DATABASE["POSTGRES_DB"]):
    """Connect to the tests' database server, as its throwaway user."""
    return psycopg.connect(
        host=DATABASE["POSTGRES_HOST"],
        port=DATABASE["POSTGRES_PORT"],
        user=DATABASE["POSTGRES_USER"],
        password=DATABASE["POSTGRES_PASSWORD"],
        dbname=database,
        autocommit=True,
        connect_timeout=5,
    )


@pytest.fixture
def database():
    """Create an empty throwaway database for one test and drop it afterwards."""
    name = f"test_deskmate_migration_{secrets.token_hex(6)}"
    with connect() as server:
        server.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(name)))
    try:
        yield name
    finally:
        with connect() as server:
            server.execute(
                sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(
                    sql.Identifier(name)
                )
            )


def query(database, statement, parameters=None):
    with connect(database) as db:
        cursor = db.execute(statement, parameters)
        return cursor.fetchall() if cursor.description else []


def configured(database, overrides=None):
    return valid_environment({"POSTGRES_DB": database, **(overrides or {})})


def applied(database):
    """Return the applied migrations in order; none if Django made no history."""
    if "django_migrations" not in tables(database):
        return []
    rows = query(database, "SELECT app, name FROM django_migrations ORDER BY id")
    return [f"{app}.{name}" for app, name in rows]


def tables(database):
    rows = query(
        database,
        "SELECT table_name FROM information_schema.tables "
        "WHERE table_schema = 'public'",
    )
    return {name for (name,) in rows}


def schema(database):
    """Return the database's tables, columns, constraints, indexes and history."""
    return {
        "columns": query(
            database,
            "SELECT table_name, column_name, data_type, is_nullable "
            "FROM information_schema.columns WHERE table_schema = 'public' "
            "ORDER BY 1, 2",
        ),
        "constraints": query(
            database,
            "SELECT conrelid::regclass::text, conname, pg_get_constraintdef(oid) "
            "FROM pg_constraint WHERE connamespace = 'public'::regnamespace "
            "ORDER BY 1, 2",
        ),
        "indexes": query(
            database,
            "SELECT indexname, indexdef FROM pg_indexes "
            "WHERE schemaname = 'public' ORDER BY 1",
        ),
        "history": query(
            database, "SELECT id, app, name, applied FROM django_migrations ORDER BY id"
        ),
    }


def migrate_to(database, app, name, settings):
    """Apply migrations up to `app`.`name` with Django's own command, as setup."""
    process = run_manage(
        ["migrate", app, name, "--verbosity", "0"],
        configured(database, {"DJANGO_SETTINGS_MODULE": settings}),
    )
    assert process.returncode == 0, process.stderr


def duplicate_source_codes(database, code):
    """Make migfix_fail.0002_copy_codes fail on a duplicate of `code`."""
    query(database, "CREATE TABLE migfix_fail_source (code text NOT NULL)")
    query(
        database,
        "INSERT INTO migfix_fail_source (code) VALUES (%s), (%s)",
        (code, code),
    )


@pytest.mark.ac("PLT-2.12", "PLT-2.14")
def test_migration_empty_database_applies_all_in_dependency_order_and_passes(
    database,
):
    process = run_entry_point(configured(database), ORDERED)
    assert lines(process) == [*map(applying, ORDERED_PLAN), PASSED]
    assert process.returncode == 0
    assert applied(database) == ORDERED_PLAN
    assert {"migfix_alpha_card", "migfix_beta_board"} <= tables(database)


@pytest.mark.ac("PLT-2.12", "PLT-2.14")
@pytest.mark.parametrize(
    ("app", "name", "remaining"),
    [
        ("migfix_beta", "0001_initial", ORDERED_PLAN[1:]),
        ("migfix_alpha", "0001_initial", ORDERED_PLAN[2:]),
    ],
    ids=["two-unapplied", "one-unapplied"],
)
def test_migration_partly_migrated_database_applies_only_unapplied(
    database, app, name, remaining
):
    migrate_to(database, app, name, ORDERED)
    process = run_entry_point(configured(database), ORDERED)
    assert lines(process) == [*map(applying, remaining), PASSED]
    assert process.returncode == 0
    assert applied(database) == ORDERED_PLAN


@pytest.mark.ac("PLT-2.6", "PLT-2.12", "PLT-2.14")
def test_migration_rerun_after_success_applies_nothing_and_changes_no_schema(
    database,
):
    first = run_entry_point(configured(database), ORDERED)
    assert first.returncode == 0, first.stdout
    before = schema(database)
    process = run_entry_point(configured(database), ORDERED)
    assert lines(process) == [NOTHING, PASSED]
    assert process.returncode == 0
    assert schema(database) == before


@pytest.mark.ac("PLT-2.12", "PLT-2.14")
def test_migration_failure_stops_keeps_earlier_and_leaves_none_of_failed(database):
    row_value = f"row-{secrets.token_hex(8)}"
    duplicate_source_codes(database, row_value)
    process = run_entry_point(configured(database), FAILING)
    assert lines(process) == [*map(applying, FAILING_PLAN), FAILED]
    assert process.returncode != 0
    assert applied(database) == FAILING_PLAN[:1]
    assert "migfix_fail_kept" in tables(database)
    assert "migfix_fail_partial" not in tables(database)
    assert row_value not in process.stdout


@pytest.mark.ac("PLT-2.6", "PLT-2.14")
def test_migration_rerun_after_failure_resumes_at_first_unapplied(database):
    duplicate_source_codes(database, "code-synthetic")
    failed = run_entry_point(configured(database), FAILING)
    assert failed.returncode != 0, failed.stdout
    query(database, "DELETE FROM migfix_fail_source")
    query(database, "INSERT INTO migfix_fail_source (code) VALUES ('code-synthetic')")
    process = run_entry_point(configured(database), FAILING)
    assert lines(process) == [applying(FAILING_PLAN[1]), PASSED]
    assert process.returncode == 0
    assert applied(database) == FAILING_PLAN
    assert query(database, "SELECT code FROM migfix_fail_partial") == [
        ("code-synthetic",)
    ]


@pytest.mark.ac("PLT-2.10", "PLT-2.12", "PLT-2.14")
@pytest.mark.parametrize(
    "failure",
    ["refused", "unknown-credentials", "missing-database"],
)
def test_migration_database_error_quoting_settings_fails_without_leaking(
    database, failure
):
    tag = secrets.token_hex(8)
    overrides = {
        "refused": {
            "POSTGRES_HOST": "127.0.0.1",
            "POSTGRES_PORT": str(unused_port()),
            "POSTGRES_USER": f"user-{tag}",
            "POSTGRES_PASSWORD": f"password-{tag}",
        },
        "unknown-credentials": {
            "POSTGRES_USER": f"user-{tag}",
            "POSTGRES_PASSWORD": f"password-{tag}",
        },
        "missing-database": {"POSTGRES_DB": f"db-{tag}"},
    }[failure]
    environment = configured(database, overrides)
    process = run_entry_point(environment, ORDERED)
    assert lines(process) == [FAILED]
    assert process.returncode != 0
    assert tag not in process.stdout
    assert environment["DJANGO_SECRET_KEY"] not in process.stdout


def emit_from_migration(database, channel, value):
    """Make migfix_noisy.0001_emit send `value` through `channel`."""
    query(database, "CREATE TABLE migfix_noisy_source (channel text, value text)")
    query(
        database,
        "INSERT INTO migfix_noisy_source (channel, value) VALUES (%s, %s)",
        (channel, value),
    )


@pytest.mark.ac("PLT-2.12", "PLT-2.14")
@pytest.mark.parametrize(
    "channel",
    [
        "print",
        "stderr",
        "warning",
        "log-error",
        "log-critical",
        "database-notice",
        "stdout-descriptor",
        "stderr-descriptor",
    ],
)
def test_migration_code_writing_row_value_out_shows_only_allowed_lines(
    database, channel
):
    row_value = f"row-{secrets.token_hex(8)}"
    emit_from_migration(database, channel, row_value)
    process = run_entry_point(configured(database), NOISY)
    assert lines(process) == [applying(NOISY_MIGRATION), PASSED]
    assert process.returncode == 0
    assert applied(database) == [NOISY_MIGRATION]
    assert row_value not in process.stdout


@pytest.mark.ac("PLT-2.12", "PLT-2.14")
@pytest.mark.parametrize("channel", ["keyboard-interrupt", "base-exception"])
def test_migration_interrupted_by_base_exception_fails_without_traceback(
    database, channel
):
    row_value = f"row-{secrets.token_hex(8)}"
    emit_from_migration(database, channel, row_value)
    process = run_entry_point(configured(database), NOISY)
    assert lines(process) == [applying(NOISY_MIGRATION), FAILED]
    assert process.returncode != 0
    assert applied(database) == []
    assert "migfix_noisy_done" not in tables(database)
    assert row_value not in process.stdout


@pytest.mark.ac("PLT-1.7", "PLT-2.10", "PLT-2.12")
@pytest.mark.parametrize(
    ("overrides", "invalid"),
    [
        ({"POSTGRES_PASSWORD": None}, ["POSTGRES_PASSWORD"]),
        (
            {
                "VERCEL_ENV": "production",
                "DJANGO_DEBUG": "true",
                "DJANGO_ALLOWED_HOSTS": "*",
            },
            ["DJANGO_ALLOWED_HOSTS", "DJANGO_DEBUG"],
        ),
    ],
    ids=["one-missing", "production-two-invalid"],
)
def test_migration_invalid_configuration_names_variables_then_fails(overrides, invalid):
    tag = secrets.token_hex(8)
    environment = valid_environment(
        {
            "POSTGRES_HOST": f"ep-{tag}.ap-southeast-1.aws.neon.tech",
            "POSTGRES_USER": f"user-{tag}",
            "POSTGRES_PASSWORD": f"password-{tag}",
            **overrides,
        }
    )
    process = run_entry_point(environment)
    output = lines(process)
    assert output[-1:] == [FAILED]
    assert sorted(output[:-1]) == sorted(map(cannot_start, invalid))
    assert process.returncode != 0
    assert tag not in process.stdout
    assert environment["DJANGO_SECRET_KEY"] not in process.stdout


class FakeDatabaseServer:
    """A PostgreSQL listener at 127.0.0.2, not a loopback literal.

    Without an SSL `context`, it answers every request to encrypt with "N".
    With one, it accepts SSLRequest, presents the context's certificate and counts
    each startup message the client then sends over TLS. It always refuses
    GSSENCRequest. It counts the requests to encrypt and any plaintext startup
    message, which a client may send only by falling back.
    """

    _SSL_REQUEST = 80877103
    _GSSENC_REQUEST = 80877104

    def __init__(self, context=None):
        self._context = context
        self._socket = socket.create_server(("127.0.0.2", 0))
        self._socket.settimeout(0.1)
        self.port = self._socket.getsockname()[1]
        self.encryption_requests = 0
        self.plaintext_startups = 0
        self.tls_startups = 0
        self._stopped = Event()
        self._thread = Thread(target=self._serve, daemon=True)

    def __enter__(self):
        self._thread.start()
        return self

    def __exit__(self, *_):
        self._stopped.set()
        self._thread.join(5)
        self._socket.close()

    def _serve(self):
        while not self._stopped.is_set():
            try:
                client, _ = self._socket.accept()
            except TimeoutError:
                continue
            with client:
                client.settimeout(5)
                try:
                    self._answer(client)
                except OSError:  # Including a TLS handshake the client abandons.
                    pass

    def _answer(self, client):
        while True:
            header = b""
            while len(header) < 8:
                chunk = client.recv(8 - len(header))
                if not chunk:
                    return
                header += chunk
            length, code = struct.unpack("!ii", header)
            if length != 8 or code not in (self._SSL_REQUEST, self._GSSENC_REQUEST):
                self.plaintext_startups += 1
                return
            self.encryption_requests += 1
            if code == self._SSL_REQUEST and self._context:
                client.sendall(b"S")
                with self._context.wrap_socket(client, server_side=True) as tls:
                    if tls.recv(8):
                        self.tls_startups += 1
                return
            client.sendall(b"N")


def production_environment(port, overrides=None):
    """Configure production mode against the fake server's port at 127.0.0.2."""
    return valid_environment(
        {
            "VERCEL_ENV": "production",
            "POSTGRES_HOST": "127.0.0.2",
            "POSTGRES_PORT": str(port),
            "DJANGO_ALLOWED_HOSTS": PUBLIC_HOST,
            **(overrides or {}),
        }
    )


@pytest.mark.ac("PLT-2.8", "PLT-2.12")
def test_migration_production_database_without_tls_fails_without_plaintext():
    with FakeDatabaseServer() as server:
        process = run_entry_point(production_environment(server.port), ORDERED)
    assert lines(process) == [FAILED]
    assert process.returncode != 0
    assert server.encryption_requests >= 1
    assert server.plaintext_startups == 0


def openssl(directory, *arguments):
    """Run the OpenSSL command-line tool, which CI's runner and Git Bash include."""
    executable = shutil.which("openssl")
    assert executable, "The TLS tests make their certificates with openssl."
    subprocess.run(
        [executable, *arguments],
        cwd=directory,
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=True,
    )


def make_certificate(directory, name, subject_alt_name=None, issuer=None):
    """Write `name`.pem and `name`.key: a CA's without `issuer`, otherwise a
    server certificate for `subject_alt_name` that the CA named `issuer` signs."""
    configuration = [
        "[req]",
        "prompt = no",
        "distinguished_name = dn",
        "[dn]",
        f"CN = Deskmate synthetic {name}",
        "[ca]",
        "basicConstraints = critical, CA:TRUE",
        "keyUsage = critical, keyCertSign",
    ]
    if subject_alt_name:
        configuration += [
            "[server]",
            f"subjectAltName = {subject_alt_name}",
            "extendedKeyUsage = serverAuth",
        ]
    (directory / f"{name}.cnf").write_text(
        "".join(f"{line}\n" for line in configuration), encoding="ascii"
    )
    request = ["req", "-new", "-config", f"{name}.cnf", "-nodes"]
    request += ["-newkey", "rsa:2048", "-keyout", f"{name}.key"]
    if issuer is None:
        openssl(
            directory,
            *request,
            "-x509",
            "-days",
            "1",
            "-extensions",
            "ca",
            "-out",
            f"{name}.pem",
        )
        return
    serial = str(secrets.randbits(63))
    openssl(directory, *request, "-out", f"{name}.csr")
    openssl(
        directory,
        *["x509", "-req", "-in", f"{name}.csr", "-days", "1", "-set_serial", serial],
        *["-CA", f"{issuer}.pem", "-CAkey", f"{issuer}.key", "-out", f"{name}.pem"],
        *["-extfile", f"{name}.cnf", "-extensions", "server"],
    )


@pytest.fixture(scope="module")
def certificates(tmp_path_factory):
    """A trusted and an untrusted test CA, and server certificates they sign."""
    directory = tmp_path_factory.mktemp("certificates")
    make_certificate(directory, "trusted-ca")
    make_certificate(directory, "other-ca")
    make_certificate(directory, "trusted", "IP:127.0.0.2", "trusted-ca")
    make_certificate(directory, "untrusted-issuer", "IP:127.0.0.2", "other-ca")
    make_certificate(directory, "wrong-hostname", "DNS:db.wrong.example", "trusted-ca")
    return directory


@pytest.mark.ac("PLT-2.8", "PLT-2.12")
@pytest.mark.parametrize(
    ("certificate", "valid"),
    [("trusted", True), ("untrusted-issuer", False), ("wrong-hostname", False)],
)
def test_migration_production_database_certificate_is_verified_without_fallback(
    certificates, certificate, valid
):
    context = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
    context.load_cert_chain(
        certificates / f"{certificate}.pem", certificates / f"{certificate}.key"
    )
    # The system's CA roots are only the test CA, as OpenSSL's variable sets them.
    trust = {"SSL_CERT_FILE": str(certificates / "trusted-ca.pem")}
    with FakeDatabaseServer(context) as server:
        process = run_entry_point(production_environment(server.port, trust), ORDERED)
    # The fake server closes the connection after the startup message.
    assert lines(process) == [FAILED]
    assert process.returncode != 0
    assert server.encryption_requests >= 1
    assert (server.tls_startups > 0) is valid
    assert server.plaintext_startups == 0


def model_changes_without_migrations(database, settings):
    """Run Django's check for model changes that no migration describes."""
    return run_manage(
        ["makemigrations", "--check", "--dry-run"],
        configured(database, {"DJANGO_SETTINGS_MODULE": settings}),
    )


@pytest.mark.ac("PLT-2.13")
def test_migrations_describe_every_model_change_in_deskmate(database):
    process = model_changes_without_migrations(database, "deskmate.settings")
    assert process.returncode == 0, process.stdout + process.stderr


@pytest.mark.ac("PLT-2.13")
def test_migration_drift_check_fails_for_model_change_without_migration(database):
    process = model_changes_without_migrations(database, DRIFT)
    assert process.returncode != 0
    assert "migfix_drift" in process.stdout


@pytest.mark.ac("PLT-2.13")
def test_migration_drift_check_passes_when_migrations_match_models(database):
    process = model_changes_without_migrations(database, ORDERED)
    assert process.returncode == 0, process.stdout + process.stderr


# Prints, as JSON, the label of each installed app that has a model but no
# migrations, which `makemigrations --check` passes over.
_UNMIGRATED_APPS_WITH_MODELS = """
import json
import django
from django.apps import apps
from django.db.migrations.loader import MigrationLoader

django.setup()
unmigrated = MigrationLoader(None).unmigrated_apps
print(json.dumps(sorted(
    config.label
    for config in apps.get_app_configs()
    if config.label in unmigrated and any(config.get_models())
)))
"""


def unmigrated_apps_with_models(settings):
    """Return the installed apps of `settings` with models but no migrations."""
    process = run_python(
        ["-c", _UNMIGRATED_APPS_WITH_MODELS],
        valid_environment({"DJANGO_SETTINGS_MODULE": settings}),
    )
    assert process.returncode == 0, process.stderr
    return json.loads(process.stdout.splitlines()[-1])


@pytest.mark.ac("PLT-2.13")
def test_migrations_exist_for_every_deskmate_app_with_models():
    assert unmigrated_apps_with_models("deskmate.settings") == []


@pytest.mark.ac("PLT-2.13")
def test_migration_unmigrated_check_reports_app_with_models_without_migrations(
    database,
):
    assert unmigrated_apps_with_models(UNMIGRATED) == ["migfix_unmigrated"]
    # Django's own check passes over it, so it alone would not fail the commit.
    assert model_changes_without_migrations(database, UNMIGRATED).returncode == 0


@pytest.mark.ac("PLT-2.13")
def test_migration_unmigrated_check_passes_when_apps_with_models_have_migrations():
    assert unmigrated_apps_with_models(ORDERED) == []


def non_atomic(migrations):
    """Return the `app.name` of each of `migrations` that is not atomic."""
    return sorted(f"{m.app_label}.{m.name}" for m in migrations if not m.atomic)


@pytest.mark.ac("PLT-2.14")
def test_migrations_committed_for_deskmate_are_all_atomic():
    loader = MigrationLoader(None, ignore_no_migrations=True)
    assert non_atomic(loader.disk_migrations.values()) == []
    assert connection.features.can_rollback_ddl


@pytest.mark.ac("PLT-2.14")
def test_migration_atomic_check_reports_non_atomic_migration():
    class NonAtomic(Migration):
        atomic = False

    migrations = [Migration("0001_atomic", "app"), NonAtomic("0002_bulk", "app")]
    assert non_atomic(migrations) == ["app.0002_bulk"]
