# Build whole-word article matching

Slice: #94 · Tier: High · Tool: Codex (exact model ID not exposed) · Date: 2026-10-22

Cost: Eleven role runs. Wall time, tokens and monetary cost were not measured.

## Requests

- Run `/slice 94` for the [article suggestion matching gap](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/94).
- The human confirmed High tier and the proposed meaningful whole-word matching direction, with an estimated 50–100 changed application lines plus specs, tests and documentation.
- The human agreed to the exact criteria checkpoint, chose GitHub CI after local database authentication blocked tests, then authorized provisional commits and pushes and opening/updating the draft PR for the remaining verification and reviews.

## Agent runs

- **implementer** (`3d65dbb`), scope probe: done; refused the test-file edit and changed nothing. The refusal was role-level; the live edit hook was not exercised. Orchestrator scope check against `20d2c3d` passed.
- **spec-writer** (`246260a`): done; changed only RQ-5.3 and aligned the [AI contract](../../workflow/specs/ai/find-a-fix.md#output-and-source-matching) and [security references](../../workflow/specs/SECURITY-SPEC.md#find-a-fix), committed as `ebca977`. Writer and orchestrator scope and whitespace checks passed; changed sections were read back.
- **spec-critic** (`a58461d`): done; reviewed `20d2c3d05bf9f7ce5f40948d67247834944bed8d..ebca97700887217a2d05831dd828718b24feb6ae`, finding no material ambiguity or scope addition. Agent and orchestrator read-only scope and whitespace checks passed. Implementation, runtime behavior, live provider relevance and eventual application diff size were not checked.
- **test-writer** (`3d65dbb`), initial run: needs-decision; added matching regressions in `src/deskmate/tests/test_find_a_fix.py`, committed provisionally as `89a5508` after CI publication authorization. Updated the legacy substring test name and current-workspace expectation for `foreign printer`; no tests or criterion IDs were removed. Agent and orchestrator scope checks against `b1cde98645e194fabf54bd3d52ba506457892679` and whitespace checks passed. Ruff and formatting passed; 164 focused cases collected. Local baseline failed during database setup.
- **test-writer** (`3d65dbb`), fixture correction: done; `c552cea` replaces bulk inserts that skipped `Article.save()` with ordinary creation, preserving assertions. Scope check against `89a5508`, static checks and collection passed. Corrected red CI below established valid matching failures.
- **implementer** (`3d65dbb`), plan: done; `82d8102` adds the two-task [plan](../../workflow/plans/94-article-suggestion-matching.md). Scope check against `c552cea`, whitespace and readback passed.
- **implementer** (`3d65dbb`), matcher: handed off with CI pending; `52cfb61` changes only `src/deskmate/tickets/views.py`. Scope check against `82d8102`, static checks and collection passed. Full application CI subsequently passed.
- **implementer** (`3d65dbb`), User Guide: handed off with CI pending; `1737c74` updates the built behavior in `docs/UserGuide.md` and records task 1's successful verification. Scope check against `52cfb61`, static checks and section readback passed. Full User Guide revision CI subsequently passed.
- **reviewer** (`8d74e8e`): done; reviewed `20d2c3d05bf9f7ce5f40948d67247834944bed8d..1737c74d2a8ff553efd8fe394889fd28f3bdc405`, with no findings. Independently inspected actual diffs, source and red/green CI logs through read APIs; no commands or writes. Orchestrator read-only scope check passed.
- **security-reviewer** (`8d74e8e`): done; reviewed the same `20d2c3d05bf9f7ce5f40948d67247834944bed8d..1737c74d2a8ff553efd8fe394889fd28f3bdc405` range, with no findings or missing attack tests for touched controls. Inspected attacker-input coverage and actual head CI logs through read APIs; no commands or writes. Orchestrator read-only scope check passed.
- **implementer** (`3d65dbb`), plan completion: done; `d895b4a` records task 2's successful CI and checks its box. Scope check against `1737c74`, whitespace and readback passed. No application changes after review.

## Decisions and corrections

- Fetched origin and created `94-article-suggestion-matching` from clean `origin/main` at `20d2c3d`. GitHub API metadata confirmed the issue author association was `MEMBER`; there were no comments.
- The change is in the existing [RQ-5 requirement](../../workflow/specs/product/tickets.md#rq-5-suggest-articles-while-writing-a-ticket); no other requirement changed. Before this slice, the implementation followed the previous substring rule, so the reported miss was a spec gap rather than a regression against that rule.
- The final application diff is 64 additions and 7 deletions, 71 lines, within the confirmed 50–80-line estimate, maximum 100 and default 400-line cap. No dependencies, services, credentials, routes or operating burden were added.
- [Draft PR #97](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/97) contains the confirmed slice. The human authorized using an early draft and provisional commits so existing CI could verify each step. Both planned tasks are complete; both reviews found no issues. Later commits update only the plan and this log, outside the reviewed application change.
- [Corrected red CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39709104618) at `c552cea` passed Ruff/format, then produced 27 expected matching assertion failures and 2,611 passes in 226.30 seconds; all three printer variants reproduced the miss, with no fixture/setup errors.
- [Application CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39709409258) at `52cfb61` passed the unchanged `ruff check . && ruff format --check . && pytest`, with 2,638 tests passing in 232.55 seconds. [Reviewed code and guide CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39710013459) at `1737c74` passed the same command, with 2,638 tests passing in 210.07 seconds. These CI runs checked PR merges into unchanged `20d2c3d`; root inspected the actual job logs, and both reviewers independently inspected the reviewed-head logs. Product website builds also passed.
- `.venv/Scripts/python.exe -m unittest discover -s workflow/scripts` passed all 40 workflow tests during preparation. Focused collection passed with 164 cases. No browser manual check or real-provider relevance evaluation was performed; automated provider interactions were faked.

## Problems

- Sandbox network access and writes to the Git index were denied initially. Authorized elevated retries read the author metadata, fetched origin, created the branch and committed the specs successfully.
- Global `python3` was inaccessible; the existing virtual environment's Python ran the checks. Git also warned that its global ignore file was inaccessible.
- Docker daemon inspection failed, but a separate TCP check found `localhost:5432` reachable. A later focused baseline failed with `FATAL: password authentication failed for user "deskmate"`: 113 setup errors in 49.26 seconds, exit 1; a diagnostic run with `-x` stopped at the same first setup error. These were infrastructure errors, not valid red evidence. No local database tests were rerun after the human chose CI preparation. Database credentials, settings and services were left unchanged.
- The GitHub connector returned `403 Resource not accessible by integration` when creating the authorized PR; authenticated GitHub CLI created it successfully. Read-only GitHub APIs remained usable for source and CI inspection.
- [Initial red CI](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39708603067) had 27 expected matching failures plus one invalid fixture failure, with 2,610 passes in 170.33 seconds. Bulk creation left every article's unique title key empty; test-writer corrected that in `c552cea` before the clean red run. No production change was used to accommodate the fixture defect.
- Local evidence and PR preparation files are in ignored `test-results/94-*`. Live-provider relevance remains unverified, and the existing best-effort and workspace-scan limitations remain as documented in the AI/security specs.
- Untrusted content seen: fixed provider prompts in the AI contracts were treated as contract data. No instructions from issue text or provider prompts were followed.
