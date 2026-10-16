Deploy reviewed current-main commits automatically after CI, with fail-closed recovery admission under [PLT-2](../specs/product/platform.md#plt-2-release-the-placeholder-site-to-production).

- [x] **implementer** — Add `src/deskmate/release_gate.py`; reuse `src/deskmate/release.py`'s bounded, TLS-validating, no-redirect request transport without a new dependency.
  Implement the environment-driven `main()` interface fixed by `src/deskmate/tests/test_release_gate.py`; validate inputs before authenticated reads, re-fetch exact eligible CI, and bind reads to the fixed repository's Actions API.
  Establish complete paginated Deploy run, attempt and job history; validate identities, counters, gaps, duplicates and completion evidence under the existing shared job deadline, with safe `recovery: blocked` failures.
  Apply the administrator baseline, strict per-attempt last-job completion boundary, successful/all-production-skipped settlement and held-lock exclusions exactly as [Recovery admission](../specs/TECHNICAL-SPEC.md#recovery-admission) specifies; inspect prior and older-run reruns.
  Make `src/deskmate/tests/test_release_gate.py` pass and preserve `src/deskmate/tests/test_release.py`; keep total production-source insertions plus deletions within 400 lines, aiming for a gate of 300–350 lines to leave repair room.
  Run the unchanged full [verify command](../../AGENTS.md#commands); report pending `test_deployment_gate_precedes_submit_with_baseline_and_read_only_token` and `test_deployment_gate_and_other_steps_do_not_receive_provider_credentials` failures precisely, without changing tests or claiming full verification passed.
- [x] **devops** — Change `.github/workflows/deploy.yml` to run one separate recovery-admission step before Vercel submission, while holding the existing shared concurrency lock.
  Grant only required read permissions, pass the gate `GITHUB_TOKEN`, triggering `RELEASE_CI_RUN_ID` and protected `RELEASE_RECOVERY_BASELINE`, and keep `VERCEL_TOKEN` confined to the submission/verification step.
  Preserve successful same-repository main-push provenance, exact-SHA committed-input checkout, CLI-once submission, the shared early deadline, immediate current-main recheck, verification and fail-stop propagation; remove stale per-run approval/recovery wording.
  Make `src/deskmate/tests/test_release_workflow.py` pass; run the unchanged full [verify command](../../AGENTS.md#commands) and require the entire suite to pass, reporting hosted steps that cannot run locally.

Operator setup, baseline administration and hosted integration checks already belong in [TECHNICAL-SPEC](../specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites); GitHub settings remain operator work.
Public routes and wording are unchanged, so no User Guide task is needed.
