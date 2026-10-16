"""PLT-2 workflow wiring; hosted approval/access settings still need integration checks.

These source checks cover only committed workflow declarations. They do not prove
GitHub environment protections, Vercel account configuration or token scope.
"""

import re

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
