# Run slice 1: Django project and CI

Slice: #1 · Tool: Claude Code (Claude Opus 5.5) · Date: 2026-10-15

Cost: up to the pull request, about 2.5 hours of wall time (commits from 14:41 to 17:07 SGT, plus earlier setup questions), with 17 role-agent runs and 1 resume using about 1.1M subagent tokens. PR review added about 1 hour 40 minutes (commits from 20:31 to 22:12 SGT) and 5 role-agent runs and 1 resume, whose tokens are not counted here. The orchestrator's own tokens are not counted.

## Requests

- Run `/slice 1` (issue #1, "Set up the Django project and CI", tier High) through the `slice` skill, from spec to pull request.
- The human answered the orchestrator's questions on scope, database, versions, dependencies, the verify command and review findings (see Decisions). Several times they asked for an explanation before choosing, for example of each dependency, of where the verify command runs, and of the PLT-1.4 options.
- At the checkpoint, the human questioned three criteria: why PLT-1.3 had its own 5-second limit, whether PLT-1.4's custom error pages were needed, and why PLT-1.8 existed.
- While reviewing PR #1, the human asked why `requirements.txt` and `requirements-dev.txt` differ. Claude explained that the dev file includes the runtime file with `-r`, and pointed out that CI only built the image. The human then asked for a simple CI check that runs the image, a minimal TECHNICAL-SPEC update, a push, and an update to this log.
- While reviewing PR #6, the human asked why `src/manage.py` imports inside `main()` and said they dislike that pattern. They then asked Claude to move it, fix every other such import, add a Ruff rule against it, push, and update this log.
- Still reviewing PR #6, the human asked why the image leaves out the tests and whether running them in the image would be more accurate. They then asked Claude to post a reminder about a smoke test of the built image on #2.
- The human asked for CI checks on Windows, macOS and Linux like MP2's, which had had an Apple Silicon bug, believing MP3 required them. Once Claude pointed out that MP3 names no operating system, they asked for the Developer Guide to cover Windows only, and then Git Bash only.
- The human asked for a prompt to check the verify command in Codex on Windows. They ran it, and a follow-up, in Codex and pasted the results. They then asked Claude to record the fix, commit, and update this log.
- Still reviewing PR #6, the human asked whether `is_configuration_variable` in `src/deskmate/tests/environment.py` was flaky, and why it worked that way. Two things worried them. A future variable with another prefix would not be dropped, and nothing recorded why the function matches `PG`. They asked where each fact belongs, then for commits, then for the Environments sentence to cover all of the tests' configuration, and then for an update to this log.
- Still reviewing PR #6, the human asked whether the `PageText` parser in `src/deskmate/tests/test_home.py` reinvented the wheel, and whether the standard library had something simpler. They then asked Claude to swap it for the simpler version Claude proposed, and to update this log.
- Still reviewing PR #6, the human asked for the cost to move from the PR description into this log, and for the template's Reflection note field to go. They then asked whether the description's verify and CI paragraph added anything, and took Claude's advice to remove it.

## Agent runs

- **spec-writer** (`a58461d`), 6 runs:
  - Founded `workflow/specs/` with PLT-1 at 8 criteria: `a893c26`.
  - Applied the spec-critic's findings and the human's choices: `262ec2a`.
  - Applied the human's checkpoint changes, which left 6 criteria (PLT-1.1–1.4, 1.6, 1.7) and retired PLT-1.5 and PLT-1.8: `589e8b8`.
  - Review fix: the TECHNICAL-SPEC Environments CI row now says CI runs Django's checks in the built image: `b49af20`.
  - Review fix: TECHNICAL-SPEC "Configuration" now requires every variable's name to start with `DJANGO_` or `POSTGRES_`: `db4090b`. All 8 variables in the table already did.
  - Review fix: the sentence below the Environments table now says the tests take all their configuration, apart from the secret key they make on each run, from committed files: `deb4dab`. The agent added the secret-key exception itself, because without it the sentence was wrong.
  - All six runs were within scope.
- **spec-critic** (`a58461d`): needs-decision, with 10 findings on `a893c26`. Three of them needed the human: database variables, the verify command and `ALLOWED_HOSTS=*`.
- **devops** (`e3b51ef`), 5 runs, all within scope:
  - Approved pins, `compose.yaml` (PostgreSQL 18.6 on loopback) and `.env.example`: `28e8e12`.
  - Indirect dependency pins: `457b956`. A clean throwaway venv matched the pins exactly.
  - `Dockerfile` and `.dockerignore`: `4b69170`. The image builds, runs as uid 999, and with no environment exits 1 with seven messages and no values.
  - `.github/workflows/ci.yml`: `1c162f3`. The action SHAs were checked against `git ls-remote`. The workflow has not run on GitHub.
  - Review fix, 1 run plus 1 resume: CI's `image` job runs `manage.py check --database default` in the built image with `.env.example`'s values: `3501d0e`. Locally the step passed. With `psycopg`, `psycopg-binary` or `sqlparse` uninstalled in the image, it failed. Plain `check` caught only a missing `asgiref`. Verify gave 106 passed.
- **test-writer** (`3d65dbb`), 3 runs, all within scope:
  - 65 tests and `pytest.ini`: `67a0102`. Before the build they failed on `ImportError: No module named 'deskmate.settings'`, the module the spec names.
  - Review fix, a `//evil.example` 404 test: `8c81741`, with 106 passed.
  - Review fix: the docstring of `is_configuration_variable` now says why it matches `DJANGO_`, `POSTGRES_` and `PG`, and links to TECHNICAL-SPEC "Configuration": `04f68d5`. Verify gave "All checks passed!", "20 files already formatted" and "106 passed".
- **implementer** (`3d65dbb`), 3 runs plus 1 resume, all within scope:
  - Plan: `4623935`. The resume changed `require_safe` to `require_GET` after the human decided.
  - Task 1, the project package: `d7bf94f`. Verify gave 102 passed, and the size check gave 174 lines.
  - Task 5, the User Guide: `07eb0ad`.
- **reviewer** (`a58461d`), 2 rounds:
  - Round 1: nothing above Low (Python 3.14.2 is old, and the Developer Guide was Windows-only).
  - Round 2: one Low, the Developer Guide's prerequisites line.
- **security-reviewer** (`3d65dbb`), 2 rounds:
  - Round 1: no Critical or High. One Medium, installs without hash checks. The Lows were deferred, apart from the `//evil.example` test.
  - Round 2: no findings.
- **Orchestrator commits:**
  - `e3b51ef`: the verify command in `AGENTS.md` and the devops wording.
  - `bf69195`, `ade3080` and `ca07a63`: the Developer Guide setup section.
  - `9229485`: the import moved to the top of `src/manage.py`, and `PLC0415` added to `pyproject.toml`. A sample file with an import inside a function failed with `PLC0415`. The file kept mode `100755`.
  - `bd21102`: the Developer Guide setup section covers Windows in Git Bash only. Claude followed its steps in Git Bash, and `manage.py check` with `.env.example`'s values reported no issues.
  - `43c832e`: `AGENTS.md` says to run the verify command in Git Bash on Windows, and `workflow/README.md` says to approve it outside Codex's sandbox. `python -m unittest discover -s workflow/scripts` ran 37 tests, OK.
  - `08ae0ed`: `src/deskmate/tests/test_home.py` checks the home page with Django's `assertInHTML` and `strip_tags` in place of its own `HTMLParser` subclass. Before the change, a scratch script, run outside pytest, compared both versions on the template and 10 edited copies of it.
  - `88af905`: the pull request template no longer has Cost or Reflection note fields, and the `log` skill asks for a Cost line under each log's header. PR #6's description was edited to match.
  - `6275099`: the `create-pull-request` skill says to leave verify and CI results out of the description. In PR #6's description, Claude removed that paragraph and the manual step that checked CI, and step 2 now expects every check to pass instead of a test count.
  - A [comment on #2](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/2#issuecomment-6192609428) suggests that its spec consider a CI check that starts the built image and requests `/health/`.
- **Platform checks (no changes):** `docker buildx imagetools inspect` showed that both pinned base images are multi-platform indexes that include `linux/arm64/v8`. PyPI lists `psycopg-binary` 3.3.6 wheels for Python 3.14 on macOS arm64 and x86_64, Windows x64 and Linux, but none for Windows on Arm. On this machine, `manage.py check --database default` passed and psycopg loaded its `binary` implementation.
- **Final verify, before committing `08ae0ed`:** `ruff check . && ruff format --check . && pytest`, in Git Bash, gave "All checks passed!", "20 files already formatted" and "106 passed".

## Decisions and corrections

- **Scope:** the app with a home page and health check, a Docker image, and CI. Pushing and deploying are left to #2.
- **Database:** Postgres everywhere, configured through separate `POSTGRES_*` variables.
- **Versions and dependencies:** Django 6.1.2 on Python 3.14. The approved dependencies are pytest, pytest-django and psycopg[binary], with their indirect dependencies pinned as well. gunicorn, whitenoise and dj-database-url were not approved.
- **Verify command:** `ruff check . && ruff format --check . && pytest`, run from `.venv` locally and on the CI runner, not inside the image. It includes the workflow's own tests.
  - The human first asked why it couldn't run only in CI. Claude explained that agents must run it before claiming a task is done.
- **Checkpoint changes:**
  - The 5-second limit became a rule for every database connection.
  - Error pages are only required to show no internals and to log server errors to standard error.
  - PLT-1.8 was dropped, and `DJANGO_ALLOWED_HOSTS=*` is allowed.
- **Order:** devops ran before test-writer, so the tests had pytest and a database to use. The image's command is `manage.py check`. The views are GET only. The Developer Guide setup section was written in this slice.
- **Review findings:**
  - Fixed now: the `//evil.example` test and the Developer Guide line.
  - Open in the PR: the Python 3.14.8 bump and CI checks of the image's controls.
  - Hash-checked installs become their own slice before #2 deploys.
  - Seven spec-level security findings go to #2's spec step.
- **Image check in CI (PR review):** Claude chose `check --database default`, the option devops recommended, over the image's plain `check` because plain `check` missed a missing database driver. The human asked for a minimal spec change, so the CI row's Configuration cell still says "Set in the workflow", even though the new step reads `.env.example`.
- **Imports inside functions (PR review):** the human doesn't want them. Claude found the import came from Django's template, whose `ImportError` hint had been removed. With the import placed before `DJANGO_SETTINGS_MODULE` was set, `check` still loaded `deskmate.settings`, then exited on unset environment variables because Claude's shell had no `.env`. `src/manage.py` held the only such import, and `PLC0415` now rejects new ones.
- **Tests stay out of the image (PR review):** SECURITY-SPEC "Container image" allows only what the app needs to run. The `verify` job runs the tests on the runner, and the `image` job runs Django's checks in the image. Claude advised against running the tests in the image and suggested a smoke test of the image once it serves. The human agreed that this belongs in #2's spec step rather than in a new issue.
- **Supported platforms (PR review):** Claude noted that MP3 names no operating system, because graders use the deployed app, but still proposed CI jobs on Windows and macOS. The human rejected them. MP3 doesn't require that support, and an untested promise in the Developer Guide could be marked as a bug. Both teammates use Windows, so setup covers Windows only, which reverses the macOS and Linux line from `ca07a63`. When Claude found that Windows PowerShell 5.1 rejects `&&`, the human chose Git Bash only over requiring PowerShell 7.
- **Codex on Windows (PR review):** Codex runs the verify command through Git Bash, approved to run outside its sandbox. Claude advised against moving pytest's temp folder into the repository, because that would change the test configuration for every tool, CI included.
- **Configuration variable prefixes (PR review):** Claude explained that the function is deterministic. It matches whole prefixes because libpq reads `PG` variables for every setting Django leaves unset, and those names have no underscore after `PG`. Building subprocess environments from scratch would be more fragile on Windows. Following "One home per fact" in `AGENTS.md`, the naming rule went into TECHNICAL-SPEC "Configuration", where anyone adding a variable must add a row, and the reason went into the function's docstring. The human chose to fix both in PR #6 rather than open an issue. Claude also noted that `.upper()` does nothing useful and that `PG` may drop unrelated variables. The human left both as they are.
- **Home page test (PR review):** Claude explained that `HTMLParser` already is the standard library's option, since nothing in it parses HTML5 into elements, and that the test extracts text because it was written from PLT-1.1 before the template existed. Claude advised against BeautifulSoup, a new dependency, and against `assertHTMLEqual` on the whole page, which would fix markup PLT-1.1 doesn't require. In the scratch comparison, the Django version failed three pages that meet PLT-1.1: a class on the heading, a heading other than `<h1>`, and an added script. It also passed an extra empty heading, which the parser rejected. Claude judged that acceptable for a placeholder page, and the human chose the swap.
- **PR description (PR review):** the cost belongs in the session log. The verify and CI paragraph repeated GitHub's checks box and this log, and was tied to `a2834dc`, which later commits had made stale. Step 2 stays because CI runs on Linux and the team develops on Windows.

## Problems

- **Claude stopped Python processes:** to stop a test server, Claude ran `taskkill /F /IM python.exe` with a window-title filter, with its output hidden. That would also stop any other windowless Python process, such as an editor's language server. Afterwards no Python processes were running, so what else it stopped, if anything, is unknown. Claude told the human.
- **Role agents ran read-only Git commands:** test-writer and implementer ran `git status` once each, and devops ran `git config core.autocrlf` once, despite "run no Git commands". Each reported it, and none changed Git state.
- **The scope hook blocked test-writer:** it stopped test-writer writing a reference implementation in the scratchpad, so the tests were not checked against an implementation before the build. Devops could not delete its scratch virtualenvs.
- **Setup waits:** the Docker daemon was off until midway through. The human had to add the database lines to `.env`, which agents may not read.
- **Not verified:** nothing has been installed or tested on Linux except the image build and the CI runs.
- **CI failed on `ca07a63`:** this log does not record that run. According to `a2834dc`'s message, Ruff's `EXE001` failed on Linux because files with a shebang were not executable, which Windows checkouts never showed. CI passed on `a2834dc`.
- **PR review follow-up:** Claude pushed `3501d0e` and `b49af20` together, and CI passed on `b49af20`. After both runs, `check_scope.py` exited 1 and listed only this log, which was untracked and existed before those runs. Claude pushed `9229485`, and CI passed on it.
- **The verify command failed in Codex, as Codex reported it:** Codex runs commands in Windows PowerShell 5.1, which could not parse the verify command's `&&`, and the execution policy blocked `Activate.ps1`. PowerShell 7 was not installed. Through Git Bash, inside the sandbox, it gave 104 passed and 2 errors: `tmp_path` raised `PermissionError` on the user's temp folder. Outside the sandbox it gave 106 passed, with exit code 0. Codex's attempt to use `bash.exe` directly as its shell failed with a WSL-style `E_ACCESSDENIED` error, for a reason it couldn't find.
- **libpq facts not checked against its documentation:** that libpq reads `PG` variables for every setting Django leaves unset, and that their names have no underscore after `PG`, came from Claude's and test-writer's memory of libpq's documentation. Nobody looked them up in this session.
- **Configuration prefix follow-up:** after each of the three runs, `check_scope.py` exited 1 and listed only this log, which was still untracked.
- **Not yet pushed:** CI passed on `43c832e`, which was pushed along with `bd21102`. It has not run on `db4090b`, `04f68d5`, `deb4dab` or `08ae0ed`.
