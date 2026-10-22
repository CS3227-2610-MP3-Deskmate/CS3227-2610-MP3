# Add Ruff as the Python style checker

Slice: none · Tool: Claude Code (Claude Opus 5.5) · Date: 2026-10-15

Cost: One session; the log records no role-agent runs, and wall time, tokens and monetary cost were not measured.

## Requests

- Add a style check like MP2's Checkstyle, using a standard Python style rather than porting the Java config.
- Explain how MP2's Javadoc exceptions, unit tests and Django boilerplate would fit.
- Add Ruff alone, without Django. Keep Ruff's defaults, apart from MP2's exceptions for non-public code, `@Override` and test files, and anything that clashes with Django.
- Corrections: turn on the line limit, and exclude Markdown.
- The human will commit the change; log the session.

## Agent runs

No role agents or subagents ran; Claude worked directly.

- `requirements-dev.txt` pins `ruff==0.17.0`, released on 2026-10-09. It is installed in the gitignored `.venv`.
- `pyproject.toml` holds the Ruff config.
- `workflow/scripts/`: the three scripts were run through `ruff format`, `check_scope.py` gained six one-line docstrings, a test helper gained an explicit `check=False`, and four long strings were split without changing their text.
- Checks: `ruff check .` and `ruff format --check .` passed, and `python3 -m unittest discover -s workflow/scripts` passed 37 tests.

## Decisions and corrections

- The style is PEP 8, checked by Ruff. MP2's config came from the SE-EDU Java standard; Claude found no SE-EDU Python guide, as its conventions pages returned 404.
- Lines are at most 88 characters, Ruff's default, rather than MP2's 120. Ruff does not check line length by default, so the human asked for `E501` to be turned on.
- Ruff 0.17's defaults require no docstrings, so `D101`–`D103` require them on public classes, methods and functions, as in MP2. Ruff skips names starting with `_` and methods marked `@typing.override`, and test files are exempt. MP2's other exemptions (getters and setters, short methods, parameter tags) were left to Ruff's behaviour.
- Ruff was run on hand-written Django-style files. Three exceptions came from what clashed: migrations are excluded, `RUF012` is off because Django puts lists on classes, and `settings.py` is exempt from the line limit for its generated validator path.
- Claude found that Ruff 0.17 formats Python code blocks in Markdown by default. The human excluded `*.md` so frozen plans and logs are left alone.
- The config sits in `pyproject.toml`, which the implementer's `never_writes` already protects, and the pin in `requirements-dev.txt`, which devops owns.
- The verify command in `AGENTS.md`, CI and the Developer Guide are unchanged; the verify command waits for the Django skeleton.

## Problems

- The human declined a download of Django's `startproject` and `startapp` templates, so real Django output is untested. On the hand-written samples, the generated `AppConfig` class needed a docstring and `manage.py` needed one `ruff format` run.
- Ruff changes its default rules between releases (0.17.0 dropped seven `DTZ` rules and added `F406`), so the version is pinned exactly.
