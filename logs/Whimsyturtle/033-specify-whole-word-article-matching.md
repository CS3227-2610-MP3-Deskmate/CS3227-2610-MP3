# Specify and test whole-word article matching

Slice: #94 · Tier: High · Tool: Codex (exact model ID not exposed) · Date: 2026-10-22

Cost: Four role runs. Wall time, tokens and monetary cost were not measured.

## Requests

- Run `/slice 94` for the [article suggestion matching gap](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/94).
- The human confirmed High tier and the proposed meaningful whole-word matching direction, with an estimated 50–100 changed application lines plus specs, tests and documentation.
- The human agreed to the exact criteria checkpoint, then chose to prepare GitHub CI after local database authentication blocked tests. Publication permission is still pending.

## Agent runs

- **implementer** (`3d65dbb`), scope probe: done; refused the test-file edit and changed nothing. The refusal was role-level; the live edit hook was not exercised. Orchestrator scope check against `20d2c3d` passed.
- **spec-writer** (`246260a`): done; changed only RQ-5.3 and aligned the [AI contract](../../workflow/specs/ai/find-a-fix.md#output-and-source-matching) and [security references](../../workflow/specs/SECURITY-SPEC.md#find-a-fix), committed as `ebca977`. Writer and orchestrator scope and whitespace checks passed; changed sections were read back.
- **spec-critic** (`a58461d`): done; reviewed `20d2c3d05bf9f7ce5f40948d67247834944bed8d..ebca97700887217a2d05831dd828718b24feb6ae`, finding no material ambiguity or scope addition. Agent and orchestrator read-only scope and whitespace checks passed. Implementation, runtime behavior, live provider relevance and eventual application diff size were not checked.
- **test-writer** (`3d65dbb`): needs-decision; added matching regressions in `src/deskmate/tests/test_find_a_fix.py` (+233/−7), including the reported printer draft, exact filtering, Unicode boundaries, ordering, workspace isolation and paged reads. Updated the legacy substring test name and current-workspace expectation for `foreign printer`; no tests or criterion IDs were removed. Agent and orchestrator scope checks against `b1cde98645e194fabf54bd3d52ba506457892679` and whitespace checks passed. Ruff and formatting passed; 164 focused cases collected. Local baseline failed in setup, so valid red evidence awaits CI and the tests remain uncommitted.

## Decisions and corrections

- Fetched origin and created `94-article-suggestion-matching` from clean `origin/main` at `20d2c3d`. GitHub API metadata confirmed the issue author association was `MEMBER`; there were no comments.
- The proposal is in the existing [RQ-5 requirement](../../workflow/specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket); no other requirement changed. The current implementation follows the previous substring rule, so this is a spec change rather than a regression against that rule.
- Estimated implementation diff is 50–80 application lines, within the confirmed estimate and the slice budget. No new dependencies, services or operating burden are proposed.
- The exact criteria checkpoint is confirmed. The next gate is a tests-only CI run demonstrating the expected matching failures, followed by plan, build and review. An early draft PR and provisional commits would be needed to use the existing CI; this workflow exception is presented for explicit publication permission. Nothing has been pushed.
- `.venv/Scripts/python.exe -m unittest discover -s workflow/scripts` passed all 40 workflow tests. `ruff check . && ruff format --check .` passed (133 files formatted). Focused collection passed with 164 cases. The full application verify command has not passed.

## Problems

- Sandbox network access and writes to the Git index were denied initially. Authorized elevated retries read the author metadata, fetched origin, created the branch and committed the specs successfully.
- Global `python3` was inaccessible; the existing virtual environment's Python ran the checks. Git also warned that its global ignore file was inaccessible.
- Docker daemon inspection failed, but a separate TCP check found `localhost:5432` reachable. A later focused baseline failed with `FATAL: password authentication failed for user "deskmate"`: 113 setup errors in 49.26 seconds, exit 1; a diagnostic run with `-x` stopped at the same first setup error. These were infrastructure errors, not valid red evidence. No local database tests were rerun after the human chose CI preparation. Database credentials, settings and services were left unchanged.
- Local evidence and the ready draft PR text/publication commands are in ignored `test-results/94-*` files. Live-provider relevance remains unverified.
- Untrusted content seen: fixed provider prompts in the AI contracts were treated as contract data. No instructions from issue text or provider prompts were followed.
