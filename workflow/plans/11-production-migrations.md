Goal: the Vercel production build migrates through one tested entry point, per [PLT-2.4, 2.6, 2.8–2.10 and 2.12–2.14](../specs/product/platform.md#plt-2-release-the-placeholder-site-to-production).

Estimate: about 70 lines under `src/` outside tests and migrations (budget 400). No new dependency, service or credential; `manage.py`, `settings.py` and `ci.yml` stay unchanged.

- [x] **implementer**: Add `src/deskmate/migrate.py`, run as `python src/deskmate/migrate.py` with no arguments.
  - First, if `VERCEL` is set, even empty, and `VERCEL_ENV` is not exactly `production`, print only `migration: failed` and exit 1, before loading settings or connecting (PLT-2.8, PLT-2.12).
  - Replace `sys.path[0]`, the script's own folder, with the absolute `src` folder derived from `__file__` (`wsgi.py` derives it the same way but inserts it in front), then default `DJANGO_SETTINGS_MODULE` to `deskmate.settings`.
  - Write every line to standard output and flush it, so `migration: passed` or `migration: failed` is always last. Ignore Python warnings and disable logging while it runs, so nothing else reaches either stream (PLT-2.12).
  - Call `django.setup()`. If settings raise `SystemExit`, print only the lines of its message that have the PLT-1.7 form; the text comes from `settings.py`, not a copy.
  - Connect, then replace the connection's `connect` with one that raises, so Django cannot reconnect once the connection ends. On that connection, before reading or creating any migration record, take `pg_try_advisory_lock` with a fixed key and fail if another session holds it; the lock lasts until the process exits (PLT-2.14).
  - Use Django's `MigrationExecutor` on the default connection, with the same checks as the `migrate` command: consistent history and no conflicts. Plan from the graph's leaf nodes. Print `migration: applying <app>.<name>` from the executor's `apply_start` progress callback, or `migration: nothing to apply` if the plan is empty. Apply the plan once, with no retry.
  - Then build a new plan on the same connection; print `migration: passed` and exit 0 only if it is empty. Any other exception prints `migration: failed` and exits 1, with no message or traceback.
  - Makes the 13 failing tests in `src/deskmate/tests/test_migration.py` pass.
- [x] **orchestrator**: Add `"buildCommand": "python src/deskmate/migrate.py"` to `vercel.json`, changing nothing else. Neither role's `writes` list covers `vercel.json`, so the orchestrator makes this change, as it did in [#2](2-production-deployment.md). Makes `test_vercel_build_command_runs_entry_point_once_and_fails_with_it` pass. Whether `python` resolves to the Python 3.14 that has the dependencies installed depends on hosted provider facts 1, 2 and 5 in [operator prerequisites](../specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites).
- [x] **devops**: In `.github/workflows/deploy.yml`, change only the failure guidance to follow PLT-2.4: pause automatic deployments, cancel queued deployment runs, check Vercel and reconcile any unknown outcome, confirm which migrations are applied, and confirm that no earlier operation or migration can complete later before resuming. Don't mention `migrate.py` or any `manage.py` migrate command (`test_workflows_never_migrate_outside_the_provider_build`). Makes the three `test_deployment_driver_obeys_gate_and_propagates_failure_without_retry` cases pass. The archive already includes `vercel.json` and `src/deskmate/migrate.py`.

After every task, run the unchanged [verify command](../../AGENTS.md#commands).

No User Guide task: routes and pages are unchanged. No Developer Guide note: where migration runs is documented in [Release verification](../specs/TECHNICAL-SPEC.md#release-verification), and Deskmate has no migrations of its own yet.
