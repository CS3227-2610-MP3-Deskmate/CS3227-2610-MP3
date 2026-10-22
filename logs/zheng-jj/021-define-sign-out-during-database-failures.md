# Define sign-out during database failures

Slice: #115 · Tier: High · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-22

Cost: 10 role-agent runs (including 4 resumes) using about 0.7M subagent tokens. The orchestrator's own tokens, wall time and monetary cost were not measured.

## Requests

- "resolve 114 and 115". The orchestrator proposed the policy: a database failure during sign-out gives PLT-1.4's generic `500` with no redirect, leaves the session as it was, and has no retry. The human replied "make that decision".

## Agent runs

- **spec-writer** (`246260a`), 1 run and 2 resumes, within scope:
  - `8ea1544`: ACC-1.4 defines the outcome, ACC-1.2 gains the exception, SECURITY-SPEC records a `Gap:`, and the `/sign-out/` route row cites ACC-1.4.
  - `12ca524`: the spec-critic's five fixes.
  - `794e104`: review round 1's wording fixes.
- **spec-critic** (`a58461d`): five findings on `8ea1544`. The one decision, whether the `500` may clear the cookie, was settled by the orchestrator: it sets no cookie.
- **test-writer** (`3d65dbb`), 1 run and 1 resume, within scope:
  - `1d226b3`: 21 cases in `test_sign_out.py`, which all pass on current code. A failure at the session read, account read or session delete, or a full outage, gives a `500` with no cookie and leaves the session unchanged, so the same cookie still reaches the role page and a later sign-out works. A committed delete signs the cookie out. A sign-out without a session cookie still gets `302`. ACC-1.8's `403` and the `405` come first.
  - `0dcf848`: a failure at the session read inside Django's delete, and the session cookie value hidden from the `500`.
  - A scratch plugin that made Django save sessions on `500` responses failed every delete case.
- **reviewer** (`8d74e8e`), 2 rounds: `be9a06b..1d226b3` no blocking findings, with Lows on the Gap's scope, ACC-1.4 citing itself and the untested read inside delete; `1d226b3..0dcf848` all resolved.
- **security-reviewer** (`8d74e8e`), 2 rounds: `be9a06b..1d226b3` no blocking findings after tracing Django 6.1.2's `logout` and session middleware, with a Low that the Gap should say users see only a generic `500`; `1d226b3..0dcf848` resolved.

## Decisions and corrections

- Tier High, because the slice concerns sessions.
- The human made the policy decision; the orchestrator decided, under the human's earlier delegation, that the `500` sets no cookie and that no extra tests are needed for the other ways a session ends.
- No production change: Django's session middleware does not save sessions or set cookies on `5xx` responses, so the specified behaviour already holds, and the new tests pin it.

## Problems

- On this Mac, 17 tests in `test_migration.py` fail on unchanged `main` because macOS cannot bind 127.0.0.2; CI must confirm them.
- The slice ran in a separate worktree, `/Users/zheng/Desktop/mp3/worktrees/115-sign-out-db-failure`, while #114 was reviewed in the main checkout.
- Untrusted content seen: the issue text, by a repository member; treated as data.
