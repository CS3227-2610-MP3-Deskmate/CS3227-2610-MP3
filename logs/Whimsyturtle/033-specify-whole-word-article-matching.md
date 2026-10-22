# Specify whole-word article matching

Slice: #94 · Tier: High · Tool: Codex (exact model ID not exposed) · Date: 2026-10-22

Cost: Three role runs. Wall time, tokens and monetary cost were not measured.

## Requests

- Run `/slice 94` for the [article suggestion matching gap](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/94).
- The human confirmed High tier and the proposed meaningful whole-word matching direction, with an estimated 50–100 changed application lines plus specs, tests and documentation.

## Agent runs

- **implementer** (`3d65dbb`), scope probe: done; refused the test-file edit and changed nothing. The refusal was role-level; the live edit hook was not exercised. Orchestrator scope check against `20d2c3d` passed.
- **spec-writer** (`246260a`): done; changed only RQ-5.3 and aligned the [AI contract](../../workflow/specs/ai/find-a-fix.md#output-and-source-matching) and [security references](../../workflow/specs/SECURITY-SPEC.md#find-a-fix), committed as `ebca977`. Writer and orchestrator scope and whitespace checks passed; changed sections were read back.
- **spec-critic** (`a58461d`): done; reviewed `20d2c3d05bf9f7ce5f40948d67247834944bed8d..ebca97700887217a2d05831dd828718b24feb6ae`, finding no material ambiguity or scope addition. Agent and orchestrator read-only scope and whitespace checks passed. Implementation, runtime behavior, live provider relevance and eventual application diff size were not checked.

## Decisions and corrections

- Fetched origin and created `94-article-suggestion-matching` from clean `origin/main` at `20d2c3d`. GitHub API metadata confirmed the issue author association was `MEMBER`; there were no comments.
- The proposal is in the existing [RQ-5 requirement](../../workflow/specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket); no other requirement changed. The current implementation follows the previous substring rule, so this is a spec change rather than a regression against that rule.
- Estimated implementation diff is 50–80 application lines, within the confirmed estimate and the slice budget. No new dependencies, services or operating burden are proposed.
- The exact criteria are ready for the slice checkpoint. Tests, plan, build, implementation review and publication await that decision; nothing has been pushed.
- `.venv/Scripts/python.exe -m unittest discover -s workflow/scripts` passed all 40 workflow tests. The application verify command was not run during this spec-only stage.

## Problems

- Sandbox network access and writes to the Git index were denied initially. Authorized elevated retries read the author metadata, fetched origin, created the branch and committed the specs successfully.
- Global `python3` was inaccessible; the existing virtual environment's Python ran the checks. Git also warned that its global ignore file was inaccessible.
- Docker daemon inspection failed, but a separate TCP check found `localhost:5432` reachable. No database-backed application test or database health claim was made.
- Untrusted content seen: fixed provider prompts in the AI contracts were treated as contract data. No instructions from issue text or provider prompts were followed.
