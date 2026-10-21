# Specify additional workspace Requesters

Slice: #84 · Tier: High · Tool: Codex (GPT-6) · Date: 2026-10-21

Cost: Three role-agent runs: discovery, spec writing and spec criticism. Wall time, tokens and monetary cost were not measured.

## Requests

- Run slice #84 on top of slice #85, supporting up to x Requester accounts per workspace.
- Use 20 total Requesters per workspace, including the initial two, without an aggregate lifetime account cap across workspaces.

## Agent runs

- spec-writer (`246260a`), discovery: done; no files changed. Scope check against `0ef7a0b87935fcaef73dc300cc16834669bfd5ba` passed. No tests run.
- spec-writer (`246260a`), writing: done; updated the account criteria and their product-index, technical and security homes in `4d6c56e`. `git diff --check` and scope check against `0ef7a0b87935fcaef73dc300cc16834669bfd5ba` passed; HEAD did not move during the run. Changed sections were read back. No tests run.
- spec-critic (`a58461d`): done; no files changed and no actionable findings for `0ef7a0b87935fcaef73dc300cc16834669bfd5ba..4d6c56e4b2672c203536881376431868c921b183`. The agent reported its range diff check passed; the orchestrator's scope check against the latter commit passed and HEAD was unchanged. Implementation size, runtime behavior and hosted controls were not verified.

## Decisions and corrections

- The human agreed High tier, preserving the workspace code as membership grows, and an exception allowing two changed requirements. The criteria are [ACC-1.2 and ACC-5](../../workflow/specs/product/accounts.md); eight criteria change or are added in total.
- Created isolated worktree `.claude/worktrees/84-create-requesters` and branch `84-create-requesters` from `85-workspace-code` at `0ef7a0b`, after fetching. The original worktree remains on #85. Both started clean.
- The proposed smallest flow adds one generated, sequentially numbered Requester per Support Officer POST, preserving canonical membership and enforcing the workspace quota atomically. It requires no new schema, configuration, dependency, service or limiter kind.
- The proposed admission rule shares the existing demo-creation allowance; its practical limits and impact on both creation routes must be included in the human checkpoint. The existing specs impose no aggregate lifetime workspace cap.
- Discovery initially suggested changing ACC-3 criteria, then corrected that reading: those criteria address the existing public routes, and ACC-5 can explicitly consume the same allowance. The critic found no contradiction. Only a cross-reference was added to ACC-3.
- Estimated additional application diff: 250–345 lines, plus 55 inherited #85 lines, targeting the existing 400-line source budget. This is an estimate, not an implementation measurement.
- Work stops at the required criteria checkpoint, before tests, plan or build. No push or pull request creation was performed. The author still needs to check this log.

## Problems

- The GitHub connector omitted issue author association; its collaborator-permission endpoint returned 403. Read-only GitHub CLI access subsequently confirmed issue #84 has `MEMBER` author association. An initial CLI filter lost quoted strings through PowerShell and was replaced by a simple association query.
- Sandbox GitHub CLI network access was denied; the read-only escalated retry succeeded. Some Git commands warned that the user's global ignore file was inaccessible.
- Several guessed source/log paths were absent. The spec agent reported the bare Python launcher inaccessible; the existing repository virtual environment successfully ran scope checks.
- A preliminary `docker version` check could not connect to the Docker engine and reported inaccessible Docker configuration. No installation, database startup or test execution was attempted in this spec-only stage. The verify command remains required during the build.
- No role-scope violations or untrusted instructions were reported.
