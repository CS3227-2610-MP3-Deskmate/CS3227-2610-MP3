# Run slice 38: rate limits

Slice: #38 · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-17

Cost: about 2.5 hours of wall time by commit times (17:48 to 20:10 on the container's clock), including waits for the human and for #11, which ran in parallel and has its own log. About 22 role-agent runs, counting resumes. The runs after the session's context was compacted used about 1.64M subagent tokens; the spec-writer and spec-critic runs before it, and the orchestrator's own tokens, are not counted.

## Requests

- After #44 and #45 were opened, the human asked which pull request to merge first, then said "yea do both" for #11 and #38. This branch is built on `4-demo-workspace`, because ACC-3 limits that slice's route.
- At the checkpoint, the human answered "go with recommendations": every proposed ACC-3 value, the accepted gaps (lockout of everyone, the `Retry-After` timing leak) and the operator steps. The hosting provider's firewall was asked about but never recommended, so it stays out of scope (ACC-3 "Out of scope").
- After the tests found that the clock can go backwards, the human again answered "go with recommendations", choosing option (a): `Retry-After` stays 1 to 600 and no attempt is counted earlier than one before it.
- The human chose, when asked:
  - deleting old records per kind, when timing attempts from the latest counted one made the cross-kind deletion contradict ACC-3.3;
  - recording connection exhaustion as a gap, adding the `X_Forwarded_For` probe to the operator check, and stating that the kinds never wait for each other.

## Agent runs

- **spec-writer** (`246260a`), 6 runs, all within scope:
  - ACC-3 with 8 criteria, ACC-3.8 `[manual]`, the Counted attempt row and SECURITY-SPEC "Rate limits": `1e0c647`. The critic's findings: `1b046b1`.
  - Each attempt's moment, the later of the clock and the latest counted attempt of its kind: `f43d253`. Its first draft clashed with ACC-3.3 when the clock goes backwards, so Claude sent it back to time the check, `Retry-After` and deletion from the same moment.
  - Deletion per kind: `55588fe`.
  - The review round's spec changes: `8c3d5d9`. It also extended ACC-3.8's manual check to cover the new clause, slightly beyond the one clause asked for.
- **spec-critic** (`a58461d`): findings on `1e0c647`, applied in `1b046b1`.
- **test-writer** (`3d65dbb`), 5 runs, all within scope:
  - 236 tests for ACC-3.1–3.7: `0326315`. Before the build, 223 failed for want of limits and all 703 existing tests passed. A scratch reference passed all 939, and each of 33 single-fault versions of it was caught. It found that the container's clock stepped back about 0.9 s mid-test.
  - The moment rule: `2815f73`, 18 tests; 16 failed on a copy without the rule. It held back a cross-kind test and raised the conflict that led to per-kind deletion.
  - Per-kind deletion and cross-kind moments: `a831ab2`.
  - Review fixes: `86d3586`. These cover ACC-3.5 attack inputs (non-ASCII digits, zero-width characters, CR, LF, VT, FF, a sign), the other kind not waiting, and a refused attempt deleting nothing. They also widen one timing margin.
  - The isolation level: `d5c8371`. With the test database's default set to repeatable read, 5 attempts released after 9 still allow exactly 1. A throwaway probe that skipped the pinning statement got 5 allowed. 1022 passed.
- **implementer** (`3d65dbb`), 6 runs, all within scope:
  - Plan: `fb6dec1`.
  - Task 1: `332a55e` and, after the two spec changes landed mid-run, `9eb3122`. 959 passed.
  - Task 2, the User Guide: `d4d1b3d`. It says "sign-in attempts" where the plan said "sign-ins", because failed sign-ins count too.
  - Review fixes: `bf23dfd` and `bf27014`. 1021 passed.
- **reviewer** (`246260a`), 2 rounds:
  - Round 1: nothing must-fix. Refused attempts deleted old records against TECHNICAL-SPEC's wording; the 5-second wait was not a constant; the READ COMMITTED dependency had no comment; one timing margin was narrow.
  - Round 2: nothing must-fix or nice-to-have.
- **security-reviewer** (`3d65dbb`), 2 rounds, ACC-3.8 passing in both:
  - Round 1: nothing must-fix. Medium: the lock turns a flood into connection exhaustion, and underscore header names. Low: no statement or idle timeout, one lock for both kinds, missing attack tests.
  - Round 2: nothing must-fix. Low: the isolation level was not pinned.

## Decisions and corrections

- **Claude's choices within confirmed scope:**
  - One shared lock was accepted first, as stricter than ACC-3.8 needs. Review round 1 then moved it to one lock per kind, which the spec asks for, so a flood of one kind no longer blocks the other.
  - `idle_in_transaction_session_timeout` was left out: it ended a test's deliberately held lock, and `lock_timeout` already fails waiting attempts closed. The stalled holder became a SECURITY-SPEC gap at the human's choice.
  - The clamp of `Retry-After` to 1–600 was removed, because the moment rule makes it unreachable.
  - The isolation level is pinned to READ COMMITTED inside the check (`bf27014`).
- **The size check** is measured against `4-demo-workspace`. The result is about 200 lines under `src/`, within the 400 budget and the plan's estimate of about 180, plus a 22-line generated migration.
- **Weakened tests:** the reviewers had no diffs, so Claude checked the slice's test diff itself. One assertion moved into a new helper, and the narrow timing assertion was replaced by the wider one; nothing else was removed.

## Problems

- **The shared dev container:** agents ran verify in `deskmate-dev` at the same time, overwriting each other's `/work` copy and dropping the shared test database mid-run. This caused scattered failures that didn't reproduce. Claude made the container's `verify` take a lock (`flock`), so runs queue. Runs outside `verify` still share the test database, so only `verify` results count here.
- **Spec churn mid-build:** two spec commits landed while the implementer was building, and it adapted mid-run.
- `check_scope.py` flagged other agents' parallel files several times; each agent's own files were within scope.
- **Untrusted content:** none. The only payloads seen were the escaped red-team data in the tests.
