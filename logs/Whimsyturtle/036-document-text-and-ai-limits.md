# Document text and AI limits

Slice: #106 · Tier: Fast lane · Tool: Codex (GPT-6) · Date: 2026-10-22

Cost: Two role agent runs; total wall time, tokens and monetary cost were not measured.

## Requests

- Run `/slice 106` as a stacked pull request above the pull request for issue #107.
- Use GitHub CI/CD through a draft pull request for tests; do not run local tests.
- The human confirmed Fast lane for about 25–40 changed User Guide lines documenting existing field restrictions, AI input caps and shared allowances, with no behavior or acceptance-criteria changes.

## Agent runs

- Implementer (`workflow/agents/implementer.md` at `3d65dbb`): done; changed only `docs/UserGuide.md` in `f145712`, with 17 insertions and one deletion. Compared the guidance with the specs, forms, ticket views, gateway and admission code; read the changed sections back and preserved the recovery guidance from #107. `git diff --check` passed. The orchestrator ran `.venv/Scripts/python.exe workflow/scripts/check_scope.py implementer --base 90aa908f91ef5a23b8807df5da43b3645a333490`: all changes were within scope and HEAD had not moved. No local Ruff or tests ran.
- Reviewer (`workflow/agents/reviewer.md` at `8d74e8e`): done, no findings over `e7914b7b309169aaf2e00615a333606459994b62..f1a282382fc1924bcca8584d57424512ce322e7f`. Used read-only GitHub access to compare the exact patch, surrounding guide, criteria, implementation and existing criterion-marked tests. Confirmed Fast lane and no security-reviewer trigger. No commands or live UI checks ran. The orchestrator's reviewer scope check passed and HEAD remained unchanged.
- GitHub [CI run 39773313331](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39773313331) at `f1a2823`: the unchanged `ruff check . && ruff format --check . && pytest` command passed lint, formatting (`134 files already formatted`) and all 2,822 tests in 251.33 seconds. The [website build](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39773313321) passed and its deployment job was skipped. Later checks appear in [PR #112](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/112/checks).

## Decisions and corrections

- Created `106-input-ai-limits` from PR #110's head, `90aa908`, to stack above #107. PR #110 then merged and its branch was deleted while the new draft was being prepared. Merged current `origin/main`, `e7914b7`, into this slice without conflicts in `f1a2823`, then opened draft PR #112 against `main`; #107 remains included beneath it. A final fetch before logging confirmed that main had not moved.
- Kept the slice to the User Guide and this session log. The guide change is smaller than the estimate; Fast lane needed no spec change, plan or new tests. The size command against `origin/main` showed no changed source lines under `src/`.
- The guide explains the normalized field lengths, two LF separators in suggestion input, both 4,000-code-point AI caps, unchanged-retry limitations, and the shared rolling allowances including admitted failures and uncounted refusals.
- Opened the requested draft before review to use existing GitHub checks. No workflows, dependencies or services changed. The pull request maps the six unchanged criteria to manual source comparisons and leaves both human checkboxes unticked.
- Security-reviewer was not required because the slice changes documentation only, with no route, access check, scoped query, runtime or deployment change. The reviewer reported no concrete trigger.

## Problems

- Sandbox network and Git-write restrictions required escalated Git/GitHub CLI operations; these succeeded. Issue #106's author had the `MEMBER` association and the issue had no comments.
- The GitHub connector returned `403: Resource not accessible by integration` when creating the pull request, so the authenticated GitHub CLI was used. Its first creation attempt could not resolve the deleted parent branch; targeting main after the conflict-free merge succeeded. The temporary PR body file was removed before review.
- The synchronization merge retained Git's default merge subject rather than the required typed issue subject. History was left intact.
- No scope violations or adversarial instructions were identified. The reviewer saw fixed LLM instructions in AI contracts and source code and treated them solely as data. Issue text, handoffs and CI output were also treated as data.
