"""PLT-7 source checks; rendering and hosted protections need integration checks.
Content review must also reject planned-feature claims.
"""

import re
import subprocess
import textwrap
from fnmatch import fnmatchcase
from urllib.parse import urljoin

import pytest

from deskmate.tests.helpers import REPO_ROOT
from deskmate.tests.test_release_workflow import bash_executable

REPOSITORY = "https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3"
SITE = "https://cs3227-2610-mp3-deskmate.github.io/CS3227-2610-MP3/"
MEMBERS = ("zheng-jj", "Whimsyturtle")


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


def links(markdown):
    """(text, target) of each inline, reference or HTML link in Markdown source."""
    definitions = {
        label.strip().lower(): target
        for label, target in re.findall(
            r"(?m)^ {0,3}\[([^\]]+)\]:[ \t]*<?([^\s>]+)>?", markdown
        )
    }
    found = re.findall(
        r"(?<!!)\[([^\]]+)\]\(\s*<?([^\s)>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'))?\s*\)",
        markdown,
    )
    for text, label in re.findall(
        r"(?<![!\]])\[([^\]]+)\](?:\[([^\]]*)\])?(?![(:\[])", markdown
    ):
        if target := definitions.get((label or text).strip().lower()):
            found.append((text, target))
    for target, text in re.findall(
        r"(?is)<a\s[^>]*?\bhref\s*=\s*[\"']([^\"']*)[\"'][^>]*>(.*?)</a>", markdown
    ):
        found.append((re.sub(r"<[^>]*>", "", text), target))
    return [(text.strip(), target) for text, target in found]


def front_matter(page):
    match = re.match(r"(?s)\A---\n(.*?)\n---[ \t]*(?:\n|\Z)(.*)", page)
    assert match, "Missing front matter"
    return match[1], match[2]


def excluded(config):
    block = re.search(r"(?m)^exclude:(.*)\n?((?:^[ \t]+-.*(?:\n|\Z))*)", config)
    if not block:
        return []
    inline = block[1].strip()
    items = inline.strip("[]").split(",") if inline else re.findall("-(.*)", block[2])
    return [item.strip().strip("'\"") for item in items if item.strip()]


def site_source():
    build = job(source(".github/workflows/pages.yml"), "build")
    match = re.search(r"(?mi)^\s*(?:INPUT_)?SOURCE:\s*['\"]?([^'\"\s]+)", build)
    assert match, "Missing Pages build source"
    return (REPO_ROOT / match[1]).resolve()


@pytest.mark.ac("PLT-7.7")
def test_product_website_landing_page_links_reflections_page_from_same_build():
    index = source("docs/index.md")
    targets = [target for text, target in links(index) if text == "Reflections"]
    assert targets, "Landing page has no Reflections link"
    for target in targets:
        assert urljoin(SITE, target) == f"{SITE}Reflections.html", target
    assert site_source() == (REPO_ROOT / "docs").resolve()
    front, _ = front_matter(source("docs/Reflections.md"))
    assert re.search(r"(?m)^layout:\s*default\s*$", front)
    permalink = re.search(r"(?m)^permalink:\s*['\"]?(.*?)['\"]?\s*$", front)
    assert not permalink or permalink[1] == "/Reflections.html", permalink
    for item in excluded(source("docs/_config.yml")):
        assert not fnmatchcase("Reflections.md", item), item
        assert not "Reflections.md".startswith(item), item


@pytest.mark.ac("PLT-7.8")
def test_product_website_reflections_page_titles_and_links_each_member_once():
    front, body = front_matter(source("docs/Reflections.md"))
    assert re.search(r"(?m)^title:\s*(['\"]?)Reflections\1\s*$", front)
    headings = re.findall(r"(?m)^ {0,3}#(?!#)[ \t]*(.*?)[ \t#]*$", body)
    headings += re.findall(r"(?m)^ {0,3}(\S.*?)[ \t]*\n {0,3}=+[ \t]*$", body)
    assert all(heading == "Reflections" for heading in headings), headings
    found = links(body)
    for member in MEMBERS:
        destination = f"{REPOSITORY}/blob/main/reflections/{member}/reflection.md"
        to_member = [
            (text, target)
            for text, target in found
            if re.search(rf"(?i)(?:^|/)reflections/{re.escape(member)}(?:/|$)", target)
        ]
        assert to_member == [(member, destination)], member


def assert_reflection_links_present(page, root):
    # Presence only: a stub reflection is linked like any other (PLT-7.9).
    documents = {
        path.relative_to(root).as_posix()
        for path in root.glob("reflections/*/reflection.md")
        if path.is_file()
    }
    targets = [
        target
        for _, target in links(page)
        if re.search(r"(?i)(?:^|/)reflections/", target)
    ]
    assert targets, "Reflections page has no reflection links"
    for target in targets:
        assert target.removeprefix(f"{REPOSITORY}/blob/main/") in documents, target


@pytest.mark.ac("PLT-7.9")
def test_product_website_publishes_no_reflection_and_links_present_documents():
    site = site_source()
    documents = list((REPO_ROOT / "reflections").rglob("*.md"))
    assert documents, "No reflection documents in the repository"
    for document in documents:
        assert site not in document.resolve().parents, document
    copies = {text for path in documents if (text := path.read_bytes()).strip()}
    for path in site.rglob("*"):
        relative = path.relative_to(site).as_posix()
        named = re.search(r"(?i)(?:^|/)(?:reflections/|reflection\.md$)", relative)
        assert not named, relative
        copied = path.is_file() and path.read_bytes() in copies
        assert not copied, relative
    assert_reflection_links_present(source("docs/Reflections.md"), REPO_ROOT)


@pytest.mark.ac("PLT-7.9")
@pytest.mark.parametrize("stub", [True, False], ids=["empty-stub", "missing"])
def test_product_website_reflection_link_check_accepts_stub_rejects_missing(
    tmp_path, stub
):
    target = "reflections/example-member/reflection.md"
    page = f"- [example-member]({REPOSITORY}/blob/main/{target})\n"
    (tmp_path / target).parent.mkdir(parents=True)
    if stub:
        (tmp_path / target).write_text("", "utf-8")
        assert_reflection_links_present(page, tmp_path)
    else:
        with pytest.raises(AssertionError):
            assert_reflection_links_present(page, tmp_path)


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


def assert_deployment_guard(deploy):
    # Narrow source contract for this conjunction, not a GitHub expression runner.
    condition = re.search(r"(?ms)^    if: >-\n(.*?)(?=^    \S)", deploy)
    assert condition
    assert set(" ".join(condition[1].split()).split(" && ")) == {
        "github.event_name == 'workflow_run'",
        "github.event.workflow_run.conclusion == 'success'",
        "github.event.workflow_run.event == 'push'",
        "github.event.workflow_run.head_branch == 'main'",
        "github.event.workflow_run.head_repository.full_name == github.repository",
    }


@pytest.mark.ac("PLT-7.4", "PLT-7.5", "PLT-7.6")
def test_product_website_publication_requires_success_current_main_and_serial_job():
    workflow = source(".github/workflows/pages.yml")
    deploy = job(workflow, "deploy")
    assert_deployment_guard(deploy)
    assert "github.event.workflow_run.head_sha" in deploy
    assert re.search(r"needs:\s*(?:\[\s*)?build\b", deploy)
    assert not re.search(r"continue-on-error:\s*true|always\(\)", workflow)
    assert re.search(r"environment:\s*(?:name:\s*)?production\b", deploy)
    assert "pages: write" in deploy and "id-token: write" in deploy
    assert "concurrency:" in deploy and "cancel-in-progress: false" in deploy
    group = re.search(r"group:\s*([^\n]+)", deploy)
    assert group and not re.search(r"\$\{\{|deskmate-production", group[1])
    assert re.search(r"if:.*steps\.[\w-]+\.outputs\.[\w-]+\s*==\s*'true'", deploy)
    assert "actions/deploy-pages@" in deploy


@pytest.mark.ac("PLT-7.5", "PLT-7.6")
@pytest.mark.parametrize(
    "disjunct",
    [
        "github.event_name == 'pull_request'",
        "github.event.workflow_run.head_repository.full_name != github.repository",
        "github.event.workflow_run.head_branch != 'main'",
        "github.event.workflow_run.conclusion != 'success'",
    ],
    ids=["pr", "fork", "non-main", "failed-ci"],
)
def test_product_website_deployment_guard_rejects_or_broadened_source(disjunct):
    deploy = job(source(".github/workflows/pages.yml"), "deploy")
    mutant = deploy.replace("if: >-\n", f"if: >-\n      {disjunct} ||\n", 1)
    with pytest.raises(AssertionError):
        assert_deployment_guard(mutant)


def assert_current_main_step(tmp_path, current, lookup, inverted=False):
    deploy = job(source(".github/workflows/pages.yml"), "deploy")
    run = re.search(r"(?m)^        run: \|\n((?:          .*\n)+)", deploy)
    assert run
    script = textwrap.dedent(run[1])
    if inverted:
        script = script.replace(' == "$CHECKED_SHA"', ' != "$CHECKED_SHA"')
    output = tmp_path / "output"
    fake_git = (
        'git() { if [[ "$1" == rev-parse ]]; then echo "$CHECKED_SHA"; else '
        f"printf '%s\\trefs/heads/main\\n' '{('a' if current else 'b') * 40}'; "
        f"return {lookup}; fi; }}\n"
    )
    flags = ["--noprofile", "--norc", "-e", "-o", "pipefail", "-c"]
    result = subprocess.run(
        [str(bash_executable()), *flags, fake_git + script],
        cwd=tmp_path,
        env={"CHECKED_SHA": "a" * 40, "GITHUB_OUTPUT": output.as_posix()},
        capture_output=True,
        text=True,
        timeout=20,
        check=False,
    )
    assert result.returncode == lookup, result.stdout + result.stderr
    actual = output.read_text() if output.exists() else ""
    assert actual == ("" if lookup else f"publish={str(current).lower()}\n")


@pytest.mark.ac("PLT-7.4", "PLT-7.5")
@pytest.mark.parametrize(("current", "lookup"), [(True, 0), (False, 0), (True, 2)])
def test_product_website_current_main_executes_publish_skip_or_fail(
    tmp_path, current, lookup
):
    assert_current_main_step(tmp_path, current, lookup)


@pytest.mark.ac("PLT-7.4")
@pytest.mark.parametrize("current", [True, False], ids=["matching", "stale"])
def test_product_website_current_main_detects_inverted_comparator(tmp_path, current):
    with pytest.raises(AssertionError):
        assert_current_main_step(tmp_path, current, 0, inverted=True)
