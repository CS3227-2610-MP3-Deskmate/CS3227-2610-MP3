# Cover ticket-creation database failures

Slice: #114 · Tier: Standard · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-22

Cost: 2 role-agent runs using about 0.15M subagent tokens. The orchestrator's own tokens, wall time and monetary cost were not measured.

## Requests

- "resolve 114 and 115". Earlier in the session the human had said "make ur own decisions, stop asking me".

## Agent runs

- **test-writer** (`3d65dbb`), within scope: `9e46aac` adds five RQ-1.8 tests to `test_tickets.py` for a Requester's New ticket POST when the ticket INSERT is rejected (two database errors), when the connection is lost at the INSERT, and during a database outage (two cases). Each expects PLT-1.4's generic `500`, no redirect and no new ticket. All pass on current code; on a scratch copy, four ways of swallowing or exposing the error each failed them. pytest: 2810 passed, 17 failed, all environment-only.
- **reviewer** (`8d74e8e`), `be9a06b..9e46aac`: no blocking findings; security-reviewer not needed, since only a test file changed. Informational: the outage cases fail before the INSERT, which the other three tests cover.

## Decisions and corrections

- Standard tier, as the issue proposed; a tests-only change for an existing criterion, so no spec change, plan or build step.
- No product bug was found, so the slice adds regression coverage only.

## Problems

- On this Mac, 17 tests in `test_migration.py` fail on unchanged `main` because macOS cannot bind 127.0.0.2; CI must confirm them.
- Untrusted content seen: the issue text, by a repository member; treated as data.
