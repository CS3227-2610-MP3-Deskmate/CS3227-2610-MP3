"""PLT-7 source checks; rendering and hosted protections need integration checks.
Content review must also reject planned-feature claims.
"""

import re

import pytest

from deskmate.tests.helpers import REPO_ROOT

REPOSITORY = "https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3"


def source(path):
    file = REPO_ROOT / path
    assert file.is_file(), f"Missing product website source: {path}"
    return "\n".join(
        line
        for line in file.read_text("utf-8").splitlines()
        if file.suffix != ".yml" or not line.lstrip().startswith("#")
    )


def job(workflow, name):
    block = re.search(rf"(?ms)^  {name}:\n(.*?)(?=^  [\w-]+:|\Z)", workflow)
    assert block, f"Missing Pages {name} job"
    return block[1]


@pytest.mark.ac("PLT-7.1", "PLT-7.2")
def test_product_website_declares_theme_title_path_and_built_features():
    config = source("docs/_config.yml")
    for key, value in {
        "title": "Deskmate",
        "theme": "jekyll-theme-cayman",
        "markdown": "kramdown",
        "url": "https://cs3227-2610-mp3-deskmate.github.io",
        "baseurl": "/CS3227-2610-MP3",
    }.items():
        assert re.search(rf"(?m)^{key}:\s*['\"]?{re.escape(value)}['\"]?\s*$", config)
    index = source("docs/index.md")
    assert re.search(r"(?s)\A---\n.*?layout:\s*default\s*\n.*?---", index)
    for feature in (
        r"Requesters?",
        r"Support Officers?",
        r"demo workspaces?",
        r"tickets?",
        r"resolution repl(?:y|ies)",
        r"knowledge[- ]base articles?",
        r"password resets?",
    ):
        assert re.search(feature, index, re.IGNORECASE), feature


@pytest.mark.ac("PLT-7.2")
def test_product_website_links_existing_guides_and_repository():
    index = source("docs/index.md")
    for label, destination in {
        "User Guide": f"{REPOSITORY}/blob/main/docs/UserGuide.md",
        "Developer Guide": f"{REPOSITORY}/blob/main/docs/DeveloperGuide.md",
        "Source code": REPOSITORY,
    }.items():
        assert f"[{label}]({destination})" in index
    assert (REPO_ROOT / "docs/UserGuide.md").is_file()
    assert (REPO_ROOT / "docs/DeveloperGuide.md").is_file()


@pytest.mark.ac("PLT-7.3")
def test_product_website_has_no_dependency_link_or_placeholder_for_reflections():
    for path in ("docs/index.md", "docs/_config.yml", ".github/workflows/pages.yml"):
        assert "reflection" not in source(path).lower()


@pytest.mark.ac("PLT-7.4", "PLT-7.6")
def test_product_website_build_is_read_only_pinned_and_uses_checked_source():
    workflow = source(".github/workflows/pages.yml")
    build = job(workflow, "build")
    assert re.search(r"^  pull_request:", workflow, re.MULTILINE)
    assert re.search(r"workflows:[\s\[\]\-\"']+CI\b", workflow)
    assert re.search(r"types:[\s\[\]\-\"']+completed\b", workflow)
    assert re.search(r"^permissions:\n  contents: read\s*\n", workflow, re.MULTILINE)
    assert "write" not in build and "environment:" not in build
    assert "pull_request_target" not in workflow and "secrets." not in workflow
    assert not re.search(r"VERCEL_|POSTGRES_|DJANGO_|SOC_LLM_", workflow)
    assert "github.event.workflow_run.head_sha" in build
    assert "persist-credentials: false" in build
    assert "actions/upload-pages-artifact@" in build
    assert re.search(
        r"ghcr.io/actions/jekyll-build-pages:v?\d+\.\d+\.\d+@sha256:[0-9a-f]{64}", build
    )
    for action in re.findall(r"uses:\s*([^\s#]+)", workflow):
        assert re.search(r"@[0-9a-f]{40}$|@sha256:[0-9a-f]{64}$", action), action
    assert "ruff check . && ruff format --check . && pytest" in source(
        ".github/workflows/ci.yml"
    )


@pytest.mark.ac("PLT-7.4", "PLT-7.5", "PLT-7.6")
def test_product_website_publication_requires_success_current_main_and_serial_job():
    workflow = source(".github/workflows/pages.yml")
    deploy = job(workflow, "deploy")
    for condition in (
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.event == 'push'",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
    ):
        assert condition in deploy
    assert re.search(r"needs:\s*(?:\[\s*)?build\b", deploy)
    assert not re.search(r"continue-on-error:\s*true|always\(\)", workflow)
    assert re.search(r"environment:\s*(?:name:\s*)?production\b", deploy)
    assert "pages: write" in deploy and "id-token: write" in deploy
    assert "concurrency:" in deploy and "cancel-in-progress: false" in deploy
    group = re.search(r"group:\s*([^\n]+)", deploy)
    assert group and not re.search(r"\$\{\{|deskmate-production", group[1])
    assert "git ls-remote" in deploy and "refs/heads/main" in deploy
    assert "github.event.workflow_run.head_sha" in deploy
    assert "GITHUB_OUTPUT" in deploy
    assert re.search(r"if:.*steps\.[\w-]+\.outputs\.[\w-]+\s*==\s*'true'", deploy)
    assert "actions/deploy-pages@" in deploy
