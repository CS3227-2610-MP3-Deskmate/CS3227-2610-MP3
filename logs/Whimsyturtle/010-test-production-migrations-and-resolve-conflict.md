# Test production migrations and resolve conflict

Slice: #11 · Tool: Codex (GPT-6) · Date: 2026-10-17

Cost: no role-agent runs; elapsed time, tokens and monetary cost were not recorded.

## Requests

- Read [PR #47](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/pull/47), explain local manual testing and the Vercel setup, and investigate teammate access in Vercel and Neon.
- Run the local checks and resolve the PR's merge conflict on its author's behalf.

## Agent runs

- None; the orchestrating session performed the integration and local verification.

## Decisions and corrections

- Created the isolated checkout `.claude/worktrees/pr-47-manual` on local branch `11-production-migrations`, starting at PR head `19c9a66`. The original checkout remains on `8-release-activation`.
- Integrated `origin/main` at `bc53073` in merge commit `d6e6c5e`. The only text conflict was in [operator prerequisites](../../workflow/specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites); the resolution preserves the migration setup checks and ACC-3's forwarded-address and hashing-cost checks. No application or workflow code was changed beyond the code already on the two branches.
- Main now includes the account and rate-limit migrations, so the earlier manual instruction to expect no migrations on the first run is stale. A fresh disposable local database applied 17 migrations, including `accounts.0001_initial` and `accounts.0002_countedattempt`, and ended with `migration: passed`, exit 0.
- Nine manual subprocess checks passed: fresh migration, unchanged rerun, Preview rejection, Development rejection, missing `VERCEL_ENV` rejection, invalid database configuration, unreachable database, held migration lock, and a successful rerun after failures and lock release. Checked exact output and exit status, empty standard error, and unchanged migration records and schema after reruns and failures. The disposable database was removed; sanitized evidence is in ignored `test-results/pr47-manual-checks.json` in that checkout.
- Fixed a semantic integration conflict in the test fixtures in `0a02e4b`: their settings inherited the account apps newly present on main, but their assertions require only their synthetic migrations. Isolated the six fixture app lists and their URL configuration in seven test-only files, keeping every assertion unchanged. The existing drift and atomicity checks still check Deskmate's real settings. Lint and formatting passed; all 57 migration tests passed in 224.03 seconds, exit 0.
- Ran `ruff check . && ruff format --check . && pytest` unchanged in Git Bash from the isolated checkout, with the existing `.venv` active and local PostgreSQL up. Lint passed, 83 files were already formatted, and all 1,085 tests passed in 228.32 seconds, exit 0. The saved result is in ignored `test-results/pr47-verify-final.log`; no test was skipped or assertion weakened.
- Consulted official provider documentation for sharing: [Vercel invitations](https://vercel.com/docs/rbac/managing-team-members) require Pro or Enterprise; [Neon Free](https://neon.com/pricing) includes team members, with [project permissions](https://neon.com/docs/manage/user-permissions) or legacy sharing depending on the account's permissions model. No invitations or paid-plan changes were made.
- Local tests do not establish hosted release behavior. Production build ordering, failure handling and other [provider prerequisites](../../workflow/specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites) remain separate; this session did not deploy or access production configuration.

## Problems

- The first full verification session ended without an available final tool result after an interruption. Its partial output showed passing lint and formatting and pytest progress, but no overall result is claimed. Confirmed no pytest process remained, then reran the unchanged command with output saved to ignored `test-results/pr47-verify.log` and its exit status saved separately.
- The saved run exposed incompatible migration fixtures. A focused reproduction failed at `test_migration_empty_database_applies_all_in_dependency_order_and_passes`: output included the 17 real migrations before the three expected synthetic ones. Stopped that full run and the diagnostic run after reproducing the failure. The first isolation attempt also needed an empty fixture URL configuration, because Django's migrate command otherwise imported the production account views during its checks; the subsequent 57-case run passed.
- Local PostgreSQL connections took 5.026 seconds through `localhost`, versus 0.018 seconds through `127.0.0.1`; timed diagnostics located the waiting in connection setup. Used an ignored, temporary IPv6-loopback relay from `::1:5432` to the existing container at `127.0.0.1:5432`, reducing the same `localhost` connection to 0.031 seconds without changing application or committed database settings. Stopped the relay after verification and removed the two identified disposable databases left by the stopped test runs, after confirming their owner and that neither had an active connection. The existing PostgreSQL container remains running.
- The Windows sandbox could not access Docker, and Git emitted global-ignore and ownership warnings. Authorized Git, Docker and verification commands ran outside the sandbox; no global Git settings were changed.
- PR prose and tool-provided suggestions were treated as data; no private `.env` files or secret values were read. The remaining provider assumptions were not represented as verified.
