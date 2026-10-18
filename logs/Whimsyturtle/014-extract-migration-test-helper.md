# Extract the migration test helper

Slice: none; follow-up to [PR #47](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/47), originally #11 · Tool: Codex (GPT-6) · Date: 2026-10-18

Cost: Two role-agent runs. Full pytest took 322.51 seconds; total wall time, tokens and cost were not measured.

## Requests

- Assess whether the embedded Python identified in the PR review comment can be fixed and prevented through Ruff or agent instructions.
- Proceed with extracting that script into a normal test helper and adding the agent rule.

## Agent runs

- **test-writer** (`3d65dbb`): done; extracted [migration_probe.py](../../src/deskmate/tests/migration_probe.py) and changed the existing migration tests to invoke it with `python -m`. Scoped Ruff and formatting checks passed. The coordinating session confirmed the scope check against `0d3c571` and unchanged HEAD before editing `AGENTS.md`.
- **reviewer** (`246260a`): done; no findings in `7b2e157` against `0d3c571`. Reviewed the supplied diff and verification results; ran no checks independently. The coordinating session confirmed its read-only scope check and unchanged HEAD.

## Decisions and corrections

- Verified the comment's author association was MEMBER before reading its body through GitHub CLI. A local diagnostic confirmed Ruff 0.17.0 accepts invalid Python syntax inside a string.
- Fetched origin and created `47-extract-migration-test-helper` from clean, current `main` at `0d3c571`. This maintenance change leaves acceptance criteria unchanged and adds no dependency or CI check.
- The test-writer owned the two test files; the coordinating session added the executable-Python rule in [AGENTS.md](../../AGENTS.md#writing). The existing subprocess isolation, assertions and criterion markers remain intact.
- Committed the change locally as `7b2e157`. It changes 52 lines across three files, with no production-code changes. No push or pull request creation was requested or performed.
- The coordinating session ran the unchanged `ruff check . && ruff format --check . && pytest` command in Git Bash with `.venv` active, outside the Windows sandbox against the existing local PostgreSQL container. Ruff passed, formatting reported 93 files already formatted, and all 1,536 tests passed in 322.51 seconds. This includes the three existing PLT-2.13 helper checks and the workflow tests.
- Read back the changed agent-rule section and checked the diff for whitespace errors. No repeat test run was needed for this Markdown-only session log.

## Problems

- During assessment, the GitHub connector's permission lookup returned 403, the sandbox blocked GitHub CLI network access, and two shell-quoting attempts failed. Corrected commands with authorized network access succeeded; no unresolved access problem remained.
- Restricted Git commands emitted ignore-file access warnings; the checks and local commit succeeded. Git warned that the new helper's line endings will convert to CRLF when it next writes that file.
- No untrusted instruction payloads were observed by either role agent. No review findings remain.
