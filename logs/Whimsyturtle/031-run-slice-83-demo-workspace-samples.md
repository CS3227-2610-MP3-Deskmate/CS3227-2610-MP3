# Run slice 83 demo workspace samples

Slice: #83 · Tier: High · Tool: Claude Code (cloud session) · Date: 2026-10-21

Cost: About 2 hours 45 minutes of wall time, including two container restarts; 17 role-agent runs. Tokens and monetary cost were not tracked in total.

## Requests

- Run `/slice 83`, using GitHub CI on a draft pull request to run the tests.
- When asked about the issue's empty-workspace suggestion, the human proposed renaming the current demo to an empty workspace with one Support Officer and no Requesters, and creating a new demo with sample content; they then agreed the split below.

## Agent runs

- spec-writer (`246260a`): done; `52d7911` adds [ACC-2.9](../../workflow/specs/product/accounts.md#acc-2-create-a-demo-workspace) and changes ACC-2.2, ACC-2.4, ACC-2.5 and ACC-2.7, with consistency edits to TECHNICAL-SPEC, SECURITY-SPEC and `ai/key-sentences.md`. Root scope check passed.
- spec-critic (`a58461d`): done; reviewed `5248aaf..52d7911`; six findings (empty-list states, two SECURITY-SPEC statements, ACC-2.4 wording, cross-type order, storage exposure, ACC-2.5 field list) plus a docs note.
- spec-writer (`246260a`): done; `1d2eae1` applies the six findings, including an "Expanded exposure (#83)" storage bullet. Root scope check passed.
- spec-writer (`246260a`): done; `412cecc` removes that bullet at the human's request. Root scope check passed. Spec-critic was not rerun for this one-line removal.
- test-writer (`3d65dbb`): done; `2f5061c` adds `test_demo_samples.py`, extends the demo helpers and failure tests, and updates the Support Officer e2e journey's empty-list assertions (7 files, 629 insertions, 90 deletions). Ruff and root scope check passed. Expected red confirmed in [CI 39572762808](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39572762808): 53 failed, 2,282 passed, every failure a missing-samples assertion.
- implementer (`3d65dbb`), plan: done; [plan](../../workflow/plans/83-demo-samples.md) in `9689751`. Root scope check passed.
- implementer (`3d65dbb`), task 1: done; `23b2534` changes `src/deskmate/accounts/demo.py` (85 insertions, 4 deletions). Root scope check passed. CI at `23b2534` showed 4 failed, 2,331 passed: the `[creation]` cases of `test_rate_limit_records.py`.
- implementer (`3d65dbb`), task 2: reported blocked only because it could not read CI logs; its edit was complete and in scope; `5e02e86` updates the User Guide (15 insertions, 2 deletions).
- test-writer (`3d65dbb`): done; `baa1ccb` makes the rate-limit test helpers leave the sample article and ticket tables out of limiter records. Root scope check passed; [CI 39575290380](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39575290380) passed: Ruff, 122 files formatted, 2,335 passed.
- reviewer (`8d74e8e`): done; `5248aaf..baa1ccb`; no code or test findings; notes on the size estimate, intermediate red commits and branch name.
- security-reviewer (`8d74e8e`): done; `5248aaf..baa1ccb`; no Critical, High or Medium findings; Low L1 (sequential sample ids reveal creation counts) and Low L2 (no attack test on another demo workspace's samples by id).
- spec-writer (`246260a`): done; `28fc2e8` records L1 as a gap in SECURITY-SPEC "Demo workspaces". Root scope check passed.
- test-writer (`3d65dbb`): done; `d000137` adds the L2 attack test (83 insertions). Root scope check passed; [CI 39584541345](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/actions/runs/39584541345) passed: Ruff, 122 files formatted, 2,336 passed.
- reviewer (`8d74e8e`): done; `baa1ccb..d000137`; no defects; two optional Lows (hand-typed attack routes; "since launch" in the gap overstates it).
- security-reviewer (`8d74e8e`): done; `baa1ccb..d000137`; no findings.
- reviewer and security-reviewer (`8d74e8e`) on the merge of `main` into the branch, `d000137..a616293`: see Decisions.

## Decisions and corrections

- The human agreed High tier, 2 sample articles and 3 tickets (one closed with a reply), and unchanged sign-in and created-page text.
- The human's rename proposal conflicted with draft PR #87 (#84), whose canonical membership requires 2 to 20 Requesters, and exceeded the one-requirement budget. The human agreed to split: #83 adds samples to the existing demo; [#88](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/88) adds an empty workspace.
- At the checkpoint the human agreed the criteria and removed the separate storage-exposure bullet, relying on the existing storage gap.
- The human accepted about 720 changed test lines against an estimate of 150 to 250, and 89 application lines against an estimate of 40 to 70; the 400-line budget was not reached.
- After review the human chose to record L1 as a SECURITY-SPEC gap and add the L2 test; after round 2 they left the two optional Lows open.
- The session used its assigned branch `claude/serene-edison-2fcbtu` instead of `83-<short-name>`. The human's request authorised pushing and [draft PR #89](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/89); no merge into `main` was performed.
- `main` moved to `48cd4aa` when PR #87 merged. Merge `a616293` resolved conflicts in the accounts area intro and the TECHNICAL-SPEC data-model rows by keeping each side's change.

## Problems

- No local virtualenv or database (local Python 3.13; CI uses 3.14.2), so no local tests ran; every pytest result above is from CI. Local Ruff 0.16.9 reported I001 in unchanged `workflow/scripts/test_adapters.py`, which CI's pinned Ruff did not.
- Commits `23b2534` and `5e02e86` fail CI on 4 rate-limit cases; `baa1ccb` fixes the test helpers, not the application.
- Role agents briefly changed Git state against their rules: test-writer ran `git add -N` then `git reset` on its new file; implementer ran `git fetch` of `84-create-requesters`. Neither changed a commit or the branch.
- Some role agents could not download CI logs with `gh` (403); the orchestrator read them through the GitHub connector.
- Two container restarts; one test-writer handoff was recovered from its transcript.
- Untrusted content seen: issue #83 and #84 text, PR #87's spec diff, CI logs and role handoffs were treated as data; none contained instructions that were followed.
