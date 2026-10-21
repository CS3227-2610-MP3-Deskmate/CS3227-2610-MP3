# Build bounded workspace Requester accounts

Slice: #84 · Tier: High · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: Seven role-agent runs. Wall time, token use and monetary cost were not measured.

## Requests

- Continue after agreement with the [criteria checkpoint](030-specify-additional-workspace-requesters.md).
- Run tests only through GitHub CI/CD on a draft pull request; do not run local tests. This authorized publishing the branch and opening draft [PR #87](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/87).

## Agent runs

- test-writer (`3d65dbb`), initial tests: done; six test/helper paths committed in `a8b4d2c`. Parent scope check against `14f96dc`, Ruff lint, 125-file format check and diff check passed; HEAD stayed unchanged during the run. The expected failing CI baseline is recorded below.
- implementer (`3d65dbb`), plan: done; [two-task plan](../../workflow/plans/84-create-requesters.md) committed in `bdd54e8`. Parent scope check against `310ceef` and diff check passed; HEAD unchanged.
- implementer (`3d65dbb`), application: done; seven source paths plus the task checkbox committed in `6ab9c01`. Parent scope check against `bdd54e8`, Ruff lint, 127-file format check and diff check passed; HEAD unchanged. Source diff: 143 insertions plus 18 deletions, 161 changed lines against `5248aaf`, within the confirmed 400-line budget.
- test-writer (`3d65dbb`), test correction: done; four random-generation patches in three test modules narrowed in `8a8c9f6`. Parent scope and diff checks against `6ab9c01` passed; HEAD unchanged. Agent explicit-path Ruff checks passed. Password-generation, hashing and write assertions were retained.
- implementer (`3d65dbb`), User Guide: done; `docs/UserGuide.md` and task checkbox committed in `165eab2`. Parent scope and diff checks against `8a8c9f6` passed; HEAD unchanged. Changed sections were read back against the built templates with no duplicate headings, orphaned fragments or lost rules reported. No source lines added.
- reviewer (`8d74e8e`): done, no actionable findings for `5248aafe9b1e3ce40fc89e97ce77020116b1846d..165eab292c8b85a76d612f267e580897385c8bf9`. Independently inspected final-head CI logs, test corrections, code, scope and guide. Parent scope check against `165eab2` passed; no files changed and HEAD unchanged.
- security-reviewer (`8d74e8e`): done, no actionable findings for `5248aafe9b1e3ce40fc89e97ce77020116b1846d..165eab292c8b85a76d612f267e580897385c8bf9`. ACC-5.2's reused ACC-2.8 CSPRNG draws passed code inspection. Parent scope check against `165eab2` passed; no files changed and HEAD unchanged. This reviewer did not independently reproduce CI outcomes or verify hosted/browser controls.

## Decisions and corrections

- Built the agreed [ACC-1.2 and ACC-5 behavior](../../workflow/specs/product/accounts.md) and its User Guide instructions, with no schema, setting, dependency, service or limiter-kind addition.
- Slice #85 merged through #86 and its remote branch was deleted while this session was preparing the draft PR. Fetch confirmed its `0ef7a0b` tip was an ancestor of new `main` at `5248aaf`. Integrated that merge without conflicts in `310ceef`; #84 still builds on #85 and PR #87 targets `main`. Final pre-delivery fetch found `main` unchanged.
- The existing CI workflow already runs on draft PRs against any base; no workflow changes were needed. The human's CI-only instruction required committing and pushing before remote verification. No local pytest, unittest or manual UI tests ran; only static lint/format, scope and diff checks ran locally.
- [CI 39569820035](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39569820035) at `8a8c9f6`: actual logs showed lint/format passed and 2,447 tests passed in 213.97 seconds.
- [CI 39570687249](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39570687249) at final reviewed source head `165eab2`: actual logs showed lint/format passed and 2,447 tests passed in 205.33 seconds. Its Product website run also succeeded; deployment was skipped for the PR. Both review reports cover this source head; delivery adds only this log.
- Draft PR metadata maps every changed criterion to tests and the CSPRNG code inspection. Human checkboxes remain unticked; no human GitHub approval, manual testing or log verification is claimed. The author still needs to check this log.

## Problems

- Expected red [CI 39567769147](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39567769147) at `310ceef`: lint/format passed; 127 tests failed and 2,320 passed in 194.86 seconds. The parent inspected failures: absent creation route/link, old label behavior and route-table/access registration; no collection or environment errors.
- Initial application [CI 39569073964](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39569073964): 12 failed and 2,435 passed in 210.78 seconds. Negative-generation tests patched global `secrets.choice`, unintentionally blocking Django's CSRF-mask randomness while redisplaying rejected forms. The test writer narrowed the patches to the existing password generator; app code and rejection assertions were unchanged. Subsequent full runs passed.
- GitHub connector PR creation and editing returned 403. Authenticated GitHub CLI was the fallback. Its first creation attempt failed because the requested #85 base branch had just been deleted after merging; refreshing refs and targeting `main` resolved it. A temporary PR-body patch was rejected for targeting one file twice and was corrected to a single update; no repository file was affected.
- A synthetic implementer edit event aimed at a test file was refused by `check_scope.py --hook` with exit 2; no test file was changed by that probe. This checks the hook script, not whether a particular client has enabled its runtime hook.
- Git sometimes warned that the global ignore file was inaccessible. One PowerShell `rg` invocation used an unexpanded wildcard path and was unnecessary to the fix. Neither affected verification.
- No scope violation or HEAD movement occurred during role runs. Security review treated plan/log directives and escaped XSS/redirect fixtures only as data; no injected instructions were followed.
