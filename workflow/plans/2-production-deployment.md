Release the existing placeholder site through the protected Vercel deployment and verification flow in [PLT-2](../specs/product/platform.md#plt-2-release-the-placeholder-site-to-production).

Dependency: the root orchestrator supplies minimal root `.python-version` and `vercel.json` hosting configuration separately; neither role owns those paths.

- [x] **implementer** — Change `src/deskmate/settings.py`; add `src/deskmate/wsgi.py` and `src/deskmate/release.py`.
  Reuse startup validation for production host/debug/database constraints and fixed database TLS options; expose standard WSGI.
  Build a small standard-library verifier and CLI entry point: resolve the returned URL through authenticated deployment lookup, validate identity and alias mapping, then check public pages and redirects under shared deadlines with safe stage-only failures.
  Use `/v13/deployments/{idOrUrl}` and `/v4/aliases/{host}`, default TLS, no redirects, bounded transient retries before body validation, and no raw provider output.
  Make `src/deskmate/tests/test_production_settings.py` and `src/deskmate/tests/test_release.py` pass; retain PLT-1 behaviour. Keep all non-test `src/` changes below 400 inserted/deleted lines, aiming below 350.
- [x] **devops** — Change `.github/workflows/ci.yml`; add `.github/workflows/deploy.yml`; remove `Dockerfile` and obsolete `.dockerignore`.
  Keep the unchanged verify command and temporary PostgreSQL; gate the serial 15-minute production job on successful same-repository main-push CI, protected approval, exact-SHA checkout without persisted credentials, and a final current-main check.
  Archive only committed deployment inputs from that checkout, including root hosting configuration, `requirements.txt` and `src/`; exclude local configuration and Git history.
  Pin official Vercel CLI `64.3.1`, Python `3.14.2`, a verified exact Node version and action SHAs; run one normal `vercel deploy --prod --force` against the fixed project with raw streams suppressed.
  Capture the monotonic job deadline early and deployment completion immediately; invoke the verifier within the shared completion-plus-120-seconds/job deadline. Add no environment pull, promotion, deployment retry, rollback or migration.
  Make `src/deskmate/tests/test_release_workflow.py` pass; run the full unchanged [verify command](../../AGENTS.md#commands) after both tasks and report hosted steps that cannot run locally.

Operator setup, recovery and integration evidence belong in [TECHNICAL-SPEC](../specs/TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites), updated separately by spec-writer; provider controls remain unverified until configured and exercised.
The public routes and wording stay unchanged, so no User Guide edit is needed.
