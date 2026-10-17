"""PLT-2 workflow wiring; hosted branch/environment controls need integration checks.

These source checks cover only committed workflow and build declarations, such as
the build command in `vercel.json` that migrates. They do not prove
GitHub environment protections, Vercel account configuration or token scope.
"""

import json
import os
import re
import secrets
import shlex
import shutil
import subprocess
import sys
import textwrap
import time
from fnmatch import fnmatch
from pathlib import Path

import pytest

from deskmate.tests.helpers import REPO_ROOT


def workflow(name):
    path = REPO_ROOT / ".github" / "workflows" / name
    assert path.is_file(), f"Missing release workflow: {path.name}"
    return "\n".join(
        line
        for line in path.read_text(encoding="utf-8").splitlines()
        if not line.lstrip().startswith("#")
    )


@pytest.mark.ac("PLT-2.1", "PLT-2.5")
def test_ci_runs_exact_verification_with_postgres_and_without_stored_secrets():
    source = workflow("ci.yml")
    assert re.search(r"^\s+pull_request:", source, re.MULTILINE)
    assert re.search(r"^\s+push:\s+branches:\s+- main\s", source, re.MULTILINE)
    assert "ruff check . && ruff format --check . && pytest" in source
    assert re.search(r"image: postgres:18\.\d+[^\s]*@sha256:[0-9a-f]{64}", source)
    assert "secrets." not in source
    assert "pull_request_target" not in source
    assert not re.search(r"docker\s+(?:build|push|login)\b", source)
    assert not re.search(r"^  image:", source, re.MULTILINE)


@pytest.mark.ac("PLT-2.1", "PLT-2.5")
def test_release_packaging_removes_application_docker_image():
    assert not (REPO_ROOT / "Dockerfile").exists()


@pytest.mark.ac("PLT-2.1", "PLT-2.2", "PLT-2.3", "PLT-2.5")
def test_deployment_workflow_requires_successful_main_ci_and_production_environment():
    source = workflow("deploy.yml")
    assert "workflow_run:" in source
    assert re.search(r"workflows:[\s\[\]\-\"']+CI\b", source)
    assert re.search(r"types:[\s\[\]\-\"']+completed\b", source)
    for condition in (
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.event == 'push'",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
    ):
        assert condition in source
    assert re.search(r"environment:\s*(?:name:\s*)?production\b", source)
    assert "pull_request_target" not in source
    assert "POSTGRES_PASSWORD" not in source
    assert "DJANGO_SECRET_KEY" not in source
    assert "VERCEL_TOKEN" in source


@pytest.mark.ac("PLT-2.2", "PLT-2.4", "PLT-2.6")
def test_deployment_uses_checked_source_serial_job_and_official_cli_once():
    source = workflow("deploy.yml")
    assert re.search(r"timeout-minutes:\s*15\b", source)
    assert "concurrency:" in source
    assert "cancel-in-progress: false" in source
    group = re.search(r"group:\s*([^\n]+)", source)
    assert group
    assert not any(
        name in group[1] for name in ("head_sha", "run_id", "run_attempt", "github.sha")
    )
    assert re.search(
        r"ref:\s*\$\{\{\s*github.event.workflow_run.head_sha\s*\}\}", source
    )
    assert "persist-credentials: false" in source
    assert "refs/heads/main" in source
    assert re.search(r"vercel(?:@|==)\d+\.\d+\.\d+", source)
    assert len(re.findall(r"\bvercel deploy\b", source)) == 1
    assert "--prod" in source
    assert not re.search(r"\bvercel (?:promote|rollback)\b", source)
    assert not re.search(r"\bmanage.py\s+migrate\b", source)
    assert not re.search(r"docker\s+(?:build|push|login)\b", source)


def deployment_script():
    source = (REPO_ROOT / ".github/workflows/deploy.yml").read_text(encoding="utf-8")
    step = source.split(
        "      - name: Deploy current main and verify the public release\n", 1
    )[1]
    body = step.split("        run: |\n", 1)[1]
    lines = []
    for line in body.splitlines():
        if line.strip() and not line.startswith("          "):
            break
        lines.append(line[10:])
    return "\n".join(lines)


def bash_executable():
    bash = (
        Path("C:/Program Files/Git/bin/bash.exe")
        if os.name == "nt"
        else shutil.which("bash")
    )
    assert bash and Path(bash).is_file(), (
        "The deployment tests require Git Bash or Bash"
    )
    return bash


def run_deployment_script(
    script, tmp_path, current=True, git=0, deploy=0, verify=0, build_log=""
):
    """Run `script` with fakes; the fake CLI writes `build_log` to both streams."""
    bash = bash_executable()
    environment = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    token = secrets.token_urlsafe(24)
    environment.update(
        RUNNER_TEMP=tmp_path.as_posix(),
        RELEASE_SOURCE=tmp_path.as_posix(),
        RELEASE_JOB_DEADLINE=str(time.monotonic() + 60),
        VERCEL_TOKEN=token,
        CHECKED_SHA="a" * 40,
        TEST_CURRENT_SHA=("a" if current else "b") * 40,
        TEST_GIT_STATUS=str(git),
        TEST_DEPLOY_STATUS=str(deploy),
        TEST_VERIFY_STATUS=str(verify),
        TEST_BUILD_LOG=build_log,
        TEST_PYTHON=Path(sys.executable).as_posix(),
    )
    # Functions intercept external effects; Python still runs the real timing code.
    fakes = textwrap.dedent("""\
        git() {
          printf 'lookup\n' >> events
          printf '%s\trefs/heads/main\n' "$TEST_CURRENT_SHA"
          printf '%s\n' "$VERCEL_TOKEN" >&2
          return "$TEST_GIT_STATUS"
        }
        vercel() {
          printf 'deploy\n' >> events
          if [[ -n "$TEST_BUILD_LOG" ]]; then
            printf '%s\n' "$TEST_BUILD_LOG"
            printf '%s\n' "$TEST_BUILD_LOG" >&2
          fi
          printf 'https://deployment-synthetic.vercel.app\n'
          printf '%s\n' "$VERCEL_TOKEN" >&2
          return "$TEST_DEPLOY_STATUS"
        }
        python() {
          if [[ "$1" == src/deskmate/release.py ]]; then
            printf 'verify\n' >> events
            cat > verifier-input
            return "$TEST_VERIFY_STATUS"
          fi
          "$TEST_PYTHON" "$@"
        }
        timeout() { shift 2; "$@"; }
        """)
    process = subprocess.run(
        [
            str(bash),
            "--noprofile",
            "--norc",
            "-e",
            "-o",
            "pipefail",
            "-c",
            fakes + script,
        ],
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert token not in process.stdout + process.stderr
    events = (tmp_path / "events").read_text().splitlines()
    if "verify" in events:
        assert (tmp_path / "verifier-input").read_text().strip() == (
            "https://deployment-synthetic.vercel.app"
        )
    return process, events


def assert_deployment_outcome(result, succeeds, events, stage):
    process, actual_events = result
    assert (process.returncode == 0) is succeeds, process.stdout + process.stderr
    assert actual_events == events
    if stage:
        assert stage in process.stdout


@pytest.mark.ac("PLT-2.2", "PLT-2.4", "PLT-2.6")
@pytest.mark.parametrize(
    ("options", "succeeds", "events", "stage"),
    [
        ({}, True, ["lookup", "deploy", "verify"], None),
        ({"current": False}, True, ["lookup"], "current-main: skipped outdated commit"),
        ({"git": 2}, False, ["lookup"], "current-main: failed"),
        ({"deploy": 3}, False, ["lookup", "deploy"], "deployment: failed"),
        ({"verify": 4}, False, ["lookup", "deploy", "verify"], "verification: failed"),
    ],
    ids=["current", "stale", "lookup-fails", "deploy-fails", "verification-fails"],
)
def test_deployment_driver_obeys_gate_and_propagates_failure_without_retry(
    tmp_path, options, succeeds, events, stage
):
    result = run_deployment_script(deployment_script(), tmp_path, **options)
    assert_deployment_outcome(result, succeeds, events, stage)
    if not succeeds:
        guidance = result[0].stdout.lower()
        assert "pause automatic deployments" in guidance
        assert "cancel queued deployment runs" in guidance
        assert re.search(r"(check|reconcile) vercel", guidance)
        assert "before resuming" in guidance
        assert re.search(r"which migrations (?:are|were|have been) applied", guidance)
        assert "before approving" not in guidance


@pytest.mark.ac("PLT-2.4", "PLT-2.10")
def test_deployment_driver_failed_migration_reports_deployment_failed_only(tmp_path):
    build_log = "migration: applying deskmate.0001_initial\nmigration: failed"
    process, events = run_deployment_script(
        deployment_script(), tmp_path, deploy=1, build_log=build_log
    )
    assert process.returncode != 0
    assert events == ["lookup", "deploy"]
    assert "deployment: failed" in process.stdout
    assert "migration:" not in process.stdout + process.stderr


ENTRY_POINT = "src/deskmate/migrate.py"


def run_build_command(command, tmp_path, status):
    """Run `command` from the repository root as the provider's build would.

    `python` and `python3` are fakes that record their arguments and exit with
    `status`. Returns the finished process and the recorded calls.
    """
    calls = tmp_path / "calls"
    environment = {
        name: value
        for name, value in os.environ.items()
        if name.upper() in {"PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP"}
    }
    environment.update(TEST_CALLS=calls.as_posix(), TEST_STATUS=str(status))
    fakes = textwrap.dedent("""\
        python() { printf '%s\n' "$*" >> "$TEST_CALLS"; return "$TEST_STATUS"; }
        python3() { python "$@"; }
        """)
    process = subprocess.run(
        [str(bash_executable()), "--noprofile", "--norc", "-c", fakes + command],
        cwd=REPO_ROOT,
        env=environment,
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    recorded = calls.read_text().splitlines() if calls.exists() else []
    return process, recorded


@pytest.mark.ac("PLT-2.9", "PLT-2.10", "PLT-2.14")
@pytest.mark.parametrize("status", [0, 1], ids=["migration-passes", "migration-fails"])
def test_vercel_build_command_runs_entry_point_once_and_fails_with_it(tmp_path, status):
    configuration = json.loads((REPO_ROOT / "vercel.json").read_text("utf-8"))
    assert configuration.get("framework") == "django"
    command = configuration.get("buildCommand")
    assert isinstance(command, str) and command.strip(), "vercel.json: buildCommand"
    process, calls = run_build_command(command, tmp_path, status)
    assert calls.count(ENTRY_POINT) == 1
    assert [call for call in calls if "migrat" in call] == [ENTRY_POINT]
    assert (process.returncode == 0) is (status == 0)
    del configuration["buildCommand"]
    assert "migrat" not in json.dumps(configuration)


@pytest.mark.ac("PLT-2.9", "PLT-2.14")
def test_deployment_inputs_include_build_configuration_and_entry_point():
    source = workflow("deploy.yml")
    archive = re.search(r'git archive "\$CHECKED_SHA"(.*?)\|', source, re.DOTALL)
    assert archive
    pathspecs = shlex.split(archive[1].replace("\\\n", " "))
    included = [spec for spec in pathspecs if not spec.startswith(":(")]
    excluded = [
        spec.split(")", 1)[1]
        for spec in pathspecs
        if spec.startswith(":(") and "exclude" in spec.split(")", 1)[0]
    ]
    assert "vercel.json" in included
    assert any(
        ENTRY_POINT == path or ENTRY_POINT.startswith(path.rstrip("/") + "/")
        for path in included
    )
    for pattern in excluded:
        assert not ENTRY_POINT.startswith(pattern.rstrip("/") + "/")
        assert not fnmatch(ENTRY_POINT, pattern)


@pytest.mark.ac("PLT-2.5", "PLT-2.8", "PLT-2.14")
@pytest.mark.parametrize("name", ["ci.yml", "deploy.yml"])
def test_workflows_never_migrate_outside_the_provider_build(name):
    source = workflow(name)
    assert "migrate.py" not in source
    assert not re.search(r"manage\.py\s+\S*migrat", source)
    assert "call_command" not in source
