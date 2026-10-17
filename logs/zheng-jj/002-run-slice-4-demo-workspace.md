# Run slice 4: demo workspace

Slice: #4 · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-17

Cost: about 3 hours of wall time (the first spec commit was at 13:58 SGT, and this log was written at 16:50 SGT), including waits for the human. There were 15 role-agent runs and no resumes, using about 1.64M subagent tokens. The orchestrator's own tokens are not counted.

## Requests

- The human asked Claude to start #4 at once, without waiting for #3 to merge. So `4-demo-workspace` is built on `3-sign-in-by-role` and merges that branch in as it changes.
- At the checkpoint, the human answered "yse" to all of Claude's recommendations:
  - every ACC-2 value as written;
  - showing the generated passwords once, which narrows the password control;
  - accepting the gaps for the missing rate limit, storage growth, plain view and the back-forward cache;
  - merging #4 only together with or after #38 and #11;
  - keeping database text out of the error logs;
  - an estimate of 130–180 lines.
- Later, the human told Claude to remove its attribution trailers and approved rewriting both branches. Their hashes changed; the code didn't. That is recorded in `001-plan-milestones-and-run-slice-3-sign-in.md`.

## Agent runs

- **spec-writer** (`246260a`), 3 runs, all within scope. The third added the review's spec additions in `14e97b6`.
  - ACC-2 with 7 criteria, the `/demo-workspace/` route and a "Demo workspaces" section in SECURITY-SPEC: `5243080`.
  - The spec-critic's findings, which brought ACC-2 to 8 criteria with ACC-2.8 `[manual]`: `b46b57f`.
- **spec-critic** (`a58461d`): 8 findings on `5243080`. The most important: ACC-2.6 contradicted PLT-1.4 on what database errors write to standard error, and narrowing the password control needed the human.
- **test-writer** (`3d65dbb`), 2 runs, both within scope:
  - 122 tests: `d051c0b`. Before the build, 122 failed and 561 passed. A scratch reference implementation passed all 683, and each of 15 deliberate faults in it was caught.
  - Review fixes: `b3d783f`. They cover the key collision, the hasher moved to `tests/hashing.py`, the `transactional_db` guard, removed duplication and checking standard output, plus new interface-error, Origin, request-format and 500-header cases. 703 passed. The interface-error test failed on a copy that catches only `DatabaseError`.
- **implementer** (`3d65dbb`), 5 runs, all within scope. The fifth updated the plan in `57edec4`.
  - Plan: `fb4fa60`.
  - Task 1, demo workspaces: `3370a2e`. 683 passed. Against the plan, it redraws a password that matches another, as Claude asked, and splits the code loop into `_save_under_free_code`.
  - Task 2, the User Guide: `8e7ea1b`.
  - Review fixes: `b148e3a`. It now catches every `django.db.Error`, and hashes each password once before the transaction. 703 passed.
- **reviewer** (`246260a`), 2 rounds:
  - Round 1: nothing must-fix, and nine test-code findings.
  - Round 2: the code is fine. Before merge, the plan must match what was built. The tests credit ACC-2.6 with checking standard output, which it doesn't name. Two test helpers are duplicated.
- **security-reviewer** (`3d65dbb`), 2 rounds, ACC-2.8 passing in both:
  - Round 1: nothing must-fix. Findings: `InterfaceError` was not hidden; the database server's own logs; error reporters that capture local variables; dropping every database message; hashing inside the transaction; and missing attack tests.
  - Round 2: nothing must-fix. The plan is out of date, and building the hidden error could fail for `ProtectedError`, which can't happen today.
- **Orchestrator commits:** `80d23b6`, the Developer Guide's step 6, which now uses the button. In the dev container against the local database, the button appeared, `POST /demo-workspace/` returned 200 with 9 table cells, and the first Requester's credentials signed in to `/requester/`.

## Decisions and corrections

- The size check is measured against `3-sign-in-by-role`, because this branch is built on it. The result was 167 lines, within the confirmed 130–180.
- Claude asked the implementer for distinct passwords, so that ACC-2.3's "differs from the other two" holds for certain rather than by chance.
- From round 1, Claude sent the `InterfaceError` catch and hashing before the transaction to the implementer. The tests went to the test-writer. Anything needing a spec change goes to the human.
- **The human's answers after review ("yes to all"):**
  - The implementer brought the plan up to date with what was built: `57edec4`.
  - The spec-writer added standard output to ACC-2.6, a gap for the database server's own logs, and a control saying error reporting captures no local variables: `14e97b6`. 703 passed.
  - Claude pushed the branch and opened a draft PR stacked on #44.
- **Deferred:**
  - an SQLSTATE in the fixed error message;
  - a test for a concurrent creation that hasn't committed yet;
  - two duplicated test helpers;
  - a fallback for `ProtectedError` when building the hidden error.

## Problems

- Two merges of `3-sign-in-by-role` into this branch (`5768ddf` and `ac911d7`), because #3 kept changing.
- `check_scope.py` run inside the dev container lists almost every file, because of line endings. Claude ran it on the host after each agent, and every run was within scope.
- The test-writer and implementer built throwaway prototypes in the container's `/work`. None reached the repository.
- Untrusted content: none. The only payloads seen were the escaped red-team data in the tests.
