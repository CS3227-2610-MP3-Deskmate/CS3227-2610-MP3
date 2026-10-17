# Run slice 11: production migrations

Slice: #11 · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-17

Cost: about 3 hours of wall time by commit times (17:42 to about 20:45), including waits for the human and for #38, which ran in parallel and is in `003-run-slice-38-rate-limits.md`. About 22 role-agent runs, counting resumes. The runs after the session's context was compacted used about 1.37M subagent tokens; the spec-writer and spec-critic runs before it, and the orchestrator's own tokens, are not counted.

## Requests

- The human asked which pull request to merge first and noticed there was no #11 PR. They then said "yea do both", meaning #11 and #38, and asked for the merge order. This slice is built in a separate worktree, `CS3227-2610-MP3-11`, from `main`.
- At the checkpoint, the human answered "go with recommendations":
  - the production build migrates through one entry point that `vercel.json` runs;
  - only the listed output lines are printed;
  - migrations must be atomic;
  - a drift check runs inside verify;
  - a failed migration is reported as `deployment: failed`;
  - "Relaxed (#11)" exposures go in SECURITY-SPEC;
  - the provider facts are operator prerequisites.
- After review round 1 the human again answered "go with recommendations":
  - a guard refuses non-production Vercel builds;
  - Preview and Development hold no production values, which are marked Sensitive;
  - a migration lock;
  - Django's after-migrate step stays skipped;
  - every line goes to standard output.
- After review round 2 the human chose:
  - accept the larger size;
  - add a hosted check that `POSTGRES_HOST` is not a `-pooler` hostname;
  - record the missing table-lock timeout as a gap.

## Agent runs

- **spec-writer** (`246260a`), 5 runs, all within scope:
  - PLT-2 changes: `7bc23fc`. The critic's findings: `339b2b0`.
  - The guard, the lock, the preview settings and the output stream: `ddd4118`. The critic's findings on it: `c10530d`.
  - The pooler check and the lock-timeout gap: `e2d2813`. Claude asked it to use the `Gap:` label the other slices use.
- **spec-critic** (`a58461d`), 2 runs:
  - findings on `7bc23fc`;
  - 10 findings on `ddd4118`. These were the guard's output order, the lock's lifetime, a stale lock after a killed build, an overstated exposure, Sensitive values that can't be read back, empty `VERCEL`, and repetition.
- **test-writer** (`3d65dbb`), 4 runs, all within scope:
  - Entry-point tests: `9d18b62`. Before the build, 18 failed for want of the entry point, `buildCommand` and the guidance step, and 227 passed. Against a throwaway reference, all 33 passed, and four deliberate faults were caught.
  - Round 1 tests: `7c863b5`. They cover unmigrated apps with models, a migration writing 8 ways, interrupts, bad certificates and more workflow bans. 6 failed on the old code.
  - The guard, lock and lost connection: `6b2f15f`. Exactly the 16 target tests failed, and it also made `environment.py` drop `VERCEL`.
  - The stale-lock guidance check: `4aec4ba`.
- **implementer** (`3d65dbb`), 5 runs, all within scope:
  - Plan: `61b1e00`. It reported that no role owns `vercel.json`, so Claude edits it, as in #2.
  - The entry point: `e820b6a`. 245 passed.
  - Fixes:
    - output silenced at the file-descriptor level: `d7d9df8`;
    - the guard, the lock and no reconnect: `b5065b1`. 284 passed;
    - silencing inside the guarded region, and the plan brought in line with the code: `07a80dd`.
- **devops** (`2119617`), 2 runs:
  - the guidance names applied migrations: `841f7df`;
  - the stale-lock step and the plan's new estimate: `2776f2d`. 284 passed.
- **reviewer** (`246260a`), 2 rounds:
  - Round 1: one must-fix. PLT-2.13 missed apps with models but no migrations, which would leave production without tables.
  - Round 2: one must-fix, the stale-lock step missing from the guidance. The plan was out of date and the size exceeded the estimate.
- **security-reviewer** (`3d65dbb`), 2 rounds:
  - Round 1: two must-fix. Direct writes to the output streams, and preview builds also migrating. Also two builds migrating at once, the skipped after-migrate step, and missing tests.
  - Round 2: nothing must-fix. Low: the pooler endpoint, and no table-lock timeout.
- **Orchestrator commit:** `d7ca79b`, the `vercel.json` `buildCommand`.

## Decisions and corrections

- **Claude's choices within confirmed scope:**
  - a script rather than a management command, because settings exit before a command could print `migration: failed`;
  - the stronger PLT-2.4 guidance assertion;
  - making the Sensitive and concurrent-build provider facts record-only, because the human asked for them to be confirmed, not to block releases. Fact 9 stays blocking.
- **The size check** is measured against `main`. The result is about 140 lines under `src/`, all in `migrate.py`, against the plan's first estimate of about 70 and the 400 budget. The human accepted the growth.
- Leaving out Django's pre- and post-migrate signals is recorded in `migrate.py`'s docstring.

## Problems

- **The shared dev containers:** agents running verify at the same time overwrote each other's `/work` copy. One certificate test failed once, during an overlapping run. Claude made each container's `verify` take a lock (`flock`).
- **The container's clock** steps back about 1.2 s roughly every 15 s. The certificate fixture now waits 2 s once per module.
- **Git in the worktree container:** the worktree's `.git` file points to a Windows path. So the host writes the file lists, and the container builds a throwaway Git repository to run verify.
- **Unverified hosted facts:** provider facts 1–9 are not verified. The guard depends on fact 9: Vercel sets `VERCEL` and `VERCEL_ENV` during the build. Someone with Vercel access must confirm them before release.
- **Untrusted content:** none.
