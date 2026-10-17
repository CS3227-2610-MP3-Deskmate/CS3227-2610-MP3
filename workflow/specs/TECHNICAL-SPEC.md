# Technical spec

How Deskmate is built and run. What it does is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md).

## Architecture

- One Django project on Python 3.14 that renders HTML on the server, with no separate front end. Application code and its tests live under `src/`: Django's commands run through `src/manage.py`, and the project package is `deskmate`, with its settings in `deskmate.settings`.
- PostgreSQL 18 is the database in every environment, including tests. Every attempt to connect to it gives up after 5 seconds.
- The app reads its configuration only from environment variables.
- Repository dependencies, CI tooling and PostgreSQL container images have exact version pins; container images also have digest pins.

Production uses Vercel's native [Python 3.14](https://vercel.com/docs/functions/runtimes/python)/[Django](https://vercel.com/docs/frameworks/full-stack/django) runtime. Docker is used for development and CI PostgreSQL only; there is no app image or app-image CI job. Vercel builds from the checked source and manages Python patch updates within 3.14; CI and production are not claimed to run identical artifacts or runtimes. The official Vercel CLI is pinned in the [deployment workflow](../../.github/workflows/deploy.yml), without adding a Django dependency. Runtime configuration is in [`.python-version`](../../.python-version) and [`vercel.json`](../../vercel.json); hosted setup and verification remain subject to the [operator prerequisites](#review-decisions-and-operator-prerequisites).

## Routes

| Route | Methods | Access | Purpose | Criteria |
| --- | --- | --- | --- | --- |
| `/` | GET | Public | Placeholder home page | PLT-1.1 |
| `/health/` | GET | Public | Reports whether the app can reach its database | PLT-1.2, PLT-1.3 |

## Configuration

Application-supplied settings use `DJANGO_` or `POSTGRES_`; tests discard developer settings as described in [Environments](#environments). Provider-supplied `VERCEL_ENV=production` activates production validation in [settings](../../src/deskmate/settings.py), and provider-supplied `VERCEL` with any other `VERCEL_ENV` makes the migration entry point refuse to run (PLT-2.8); Vercel's system environment variables must remain enabled. Provider credentials are protected deployment-job inputs, not app settings.

| Variable | Meaning | Required | Valid values | Criteria |
| --- | --- | --- | --- | --- |
| `POSTGRES_HOST` | The database server's host name or IP address | Always | Any but the empty string | PLT-1.7 |
| `POSTGRES_PORT` | The database server's port | Always | A whole number from 1 to 65535, written only in digits | PLT-1.7 |
| `POSTGRES_DB` | The database's name | Always | Any but the empty string | PLT-1.7 |
| `POSTGRES_USER` | The user the app connects as | Always | Any but the empty string | PLT-1.7 |
| `POSTGRES_PASSWORD` | That user's password | Always | Any but the empty string | PLT-1.7 |
| `DJANGO_SECRET_KEY` | The key Django signs sessions and other data with | With debug off | At least 50 characters, at least 5 of them different, and not starting with `django-insecure-` | PLT-1.7 |
| `DJANGO_ALLOWED_HOSTS` | The host names the app answers to, separated by commas; spaces around a name and empty items are ignored. Names match as in Django's `ALLOWED_HOSTS`, so `*` matches every host ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)) | With debug off | At least one name | PLT-1.7 |
| `DJANGO_DEBUG` | Turns on Django's debug pages | No | Any; only `true` turns debug on (PLT-1.6) | PLT-1.6 |

The existing variables and their PLT-1 validation contract stay unchanged. Production configuration adds these constraints under PLT-2.8:

- `POSTGRES_HOST` is the exact Neon direct endpoint hostname; connection pooling and persistent Django database connections are disabled. The existing 5-second connection timeout remains.
- Database transport is fixed by the host: literal `localhost`, `127.0.0.1` and `::1` may use plaintext for development or isolated CI; every other host uses `sslmode=verify-full` with the system CA trust store (`sslrootcert=system`). Production requires the selected Neon hostname and verified TLS. There is no setting that permits plaintext for a remote host, disables certificate verification or falls back after TLS failure.
- `DJANGO_ALLOWED_HOSTS` contains only the exact public production hostname, without wildcards, schemes, paths or ports. No deployment URL, `VERCEL_URL` value or request header expands it.
- `DJANGO_DEBUG` is off; production database credentials and the strong `DJANGO_SECRET_KEY` are configured directly in provider production settings. They are not copied into CI settings or written into source or built artifacts.

## Environments

The app environments are development and production, using Vercel Hobby and Neon Free for production. CI is temporary verification. There is no preview app environment: the Preview and Development environments that every Vercel project has are provider targets, which the [operator prerequisites](#review-decisions-and-operator-prerequisites) keep free of Deskmate settings. Hosted integration still requires the checks listed there.

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | The app, serving `http://localhost:8000/`, and the [verify command](../../AGENTS.md#commands) run from the developer's `.venv`; docker compose runs only PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env`, copied from `.env.example`, which sets `DJANGO_DEBUG=true` and leaves `DJANGO_SECRET_KEY` empty. Docker compose reads it for the database, and the developer loads it into the shell that runs the app |
| Production | Vercel Hobby native Python 3.14/Django in Singapore (`sin1`); a provider-generated `vercel.app` public hostname, managed HTTPS and HTTP-to-HTTPS redirects; maximum request duration 60 seconds; no background workers | Neon Free PostgreSQL 18 in AWS Singapore (`ap-southeast-1`), separate from development and CI; direct endpoint with the connection controls above | Production-only database credentials and secret key; debug off; exact public hostname |

CI validation runs in GitHub Actions on every pull request and push to `main`, using throwaway PostgreSQL containers discarded after each run and no stored secrets. The unchanged verify command and tests run on the runner. Production runtime verification uses the public smoke test after deployment.

`pytest` needs no variables set by the developer: the tests take all their configuration from what is committed with them, except a secret key they make on each run ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)), and never from the developer's shell. Their database settings match the throwaway credentials in `.env.example` and the CI workflow.

## Release verification

PLT-2 uses **reviewed PR merge → CI → automatic production deployment, whose Vercel build migrates → public smoke test**, owned by GitHub Actions. The Vercel project's Git integration must be unlinked. There is no container-image publication. Deployment commands and pins are in the [workflow](../../.github/workflows/deploy.yml); provider verification is in [`release.py`](../../src/deskmate/release.py).

The Vercel production build migrates: the build command in the committed build configuration ([`vercel.json`](../../vercel.json)) runs the single migration entry point (PLT-2.14) with the production settings that Vercel supplies, before the deployment can become `READY`. This keeps production database credentials only in provider production settings. Choosing any other placement, such as migrating from the GitHub job, would first need an explicit, marked relaxation of the database-credentials control in [Release access and provenance](SECURITY-SPEC.md#release-access-and-provenance). Build-time migration depends on the [provider facts](#review-decisions-and-operator-prerequisites) that operators must confirm, and carries the exposures marked "Relaxed (#11)" in that section.

1. Start automatically only after successful same-repository `main`-push CI for the exact commit. Approval of the PR's final revision and passing CI are enforced by main branch protection; there is no separate deployment approval. Immediately before submitting the deployment, recheck current `main`; skip an outdated commit.
2. Submit only committed application/build inputs from a clean checkout of that checked commit to the fixed owner/project using the official Vercel CLI. Exclude local configuration, credentials and Git history. A normal [production deployment](https://vercel.com/docs/cli/deploy) builds the native application, migrating under PLT-2.9, and automatically assigns its production domain when ready; there is no separate promotion or pre-live application probe.
3. Verify the returned deployment ID through authenticated provider responses: configured owner/project, production target and `READY` state. Confirm the fixed public hostname maps to that ID before public checks. Missing or conflicting identity/mapping fails; a healthy old site cannot establish success.
4. Smoke-test public HTTPS `/` and `/health/` against PLT-1.1 and PLT-1.2, with valid TLS and no bypass credential; do not follow redirects. Check HTTP redirects to the corresponding HTTPS URL. Record only repository/commit, GitHub run identity, owner/project/deployment IDs, hostname, stage and outcome. A failed migration fails the build and is recorded as `deployment: failed`; the `migration:` lines of PLT-2.12 appear only in the migration entry point's output in the provider build log.

The deployment job has a 15-minute execution limit, including the build with its migration and the final checks. Mapping and public smoke checks share a two-minute window starting when deployment completes, capped by the remaining job time. Each verification request is limited to 10 seconds or the remaining applicable deadline, whichever is shorter. Provider build status may be polled until completion within the job limit. Invalid TLS and authentication failures (`401`/`403`) fail immediately. Verification retries cover transient transport failures and HTTP `429`/`5xx` before body validation; for example, health `503` with `{"status": "error"}` is retryable within the same deadline. Identity and content checks apply to otherwise successful responses; missing/wrong identity or content and other unexpected HTTP statuses fail immediately. No retry resets a deadline or repeats deployment creation.

One GitHub concurrency group spans the deployment, including its migrating build, and final checks, with `cancel-in-progress: false`. Pending runs may be replaced by GitHub; each run that proceeds, including a rerun of the same commit, creates a new deployment whose build migrates, without fresh approval. This provides [job concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments), not a persistent lock over provider builds, and it does not cover a production build started outside the job. Separately, the migration entry point takes a fixed PostgreSQL session-level advisory lock with a try-lock that does not wait, and holds it for its whole run (PLT-2.14). A session-level lock holds only over one unpooled session, which the direct endpoint and disabled pooling in [Configuration](#configuration) provide; PostgreSQL releases it only when that session ends, not when a transaction rolls back. A killed build can therefore leave it held until the server notices the session has gone, which is why PLT-2.4 has the operator end any stale holder. The lock stops two runs migrating the same database at once, whether or not they came from the job, but it does not order builds (PLT-2.6). An unknown provider or migration outcome, including a lost CLI/API response after Vercel may have accepted the request even if the job exits normally as failed, is handled by the manual procedure in PLT-2.4.

A build (including its migration), deployment or smoke-test failure fails the job and identifies its stage as in PLT-2.4. Once the domain switches, a runtime error can reach users before the smoke test detects it. Recovery follows PLT-2.4; rollback uses Vercel Hobby's [rollback to the immediately previous production deployment](https://vercel.com/docs/instant-rollback) if available, and the first release has no fallback. After rollback the operator must restore normal automatic domain assignment before another deployment. There is no automatic rollback, source-content readback/manifest, or custom persistent deployment state machine. Migrations are never reversed, so a rollback restores code against the current schema; [migration compatibility](SECURITY-SPEC.md#release-access-and-provenance) is a review control.

### Free-plan operating limits

The selected free plans are used without automatic paid upgrades. Vercel Hobby is for personal, non-commercial use and does not provide paid team collaboration; the hosting account owner must be established. Its documented monthly allowances include 4 CPU-hours, 360 GB-hours of provisioned memory and one million function invocations. The 60-second request limit is below the documented 300-second Hobby ceiling ([Hobby](https://vercel.com/docs/plans/hobby)). Neon Free's documented per-project monthly allowances are 1 GB storage, 100 CU-hours and 5 GB transfer; compute can sleep after five minutes idle, compute or transfer exhaustion suspends service, and the storage cap prevents further storage-growing operations ([Neon plans](https://neon.com/docs/introduction/plans)). These provider limits can change and must be checked at setup. Cold starts and quota pauses can prevent availability; the slice adds no keep-awake traffic or availability guarantee.

### Review decisions and operator prerequisites

Hosted settings and integration have not been verified. Before enabling production deployments, operators must complete this setup:

- Confirm hosting account owners, eligibility for the selected plans and the current [free-plan limits](#free-plan-operating-limits).
- Configure `main` review protections under [Release access and provenance](SECURITY-SPEC.md#release-access-and-provenance). Configure the GitHub `production` environment to allow only the `main` branch, excluding tags and pull-request refs, without required reviewers or other deployment approval gates. These GitHub settings are manual operator work.
- Set non-secret GitHub environment variables `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` and `VERCEL_PUBLIC_HOSTNAME` for the fixed owner, project and exact public hostname. The only deployment secret in GitHub is `VERCEL_TOKEN`, confined to the protected job. Verify its actual scope, use the least scope available and obtain human acceptance of any broader resource access; do not assume it is project-scoped.
- Configure the Vercel project with the repository root as its root directory and the Django preset, system environment variables enabled as required by [Configuration](#configuration), Git integration unlinked, build-log and source protection enabled, and the stable production hostname publicly accessible. Use the committed [build configuration](../../vercel.json): `vercel.json` may hold the build command, which invokes the migration entry point (PLT-2.14), and no build, install or migration command is set in the Vercel project settings outside it.
- Confirm each of these provider facts, on which build-time migration depends. They are blocking: if any fails, automatic production deployment stays disabled and the slice returns to the human.
  1. A production deployment submitted by the pinned CLI is built by Vercel, not from locally prebuilt output, and that build runs the build command in the committed `vercel.json` with the Django preset.
  2. The build command runs after the committed Python dependencies are installed under Python 3.14, so the migration entry point can run.
  3. The build command receives the Vercel production environment variables, including `VERCEL_ENV=production` and the production database settings, without their being stored in GitHub.
  4. The build can reach the Neon direct endpoint over the public network and verify its certificate against the system CA trust store, as [Configuration](#configuration) requires.
  5. A non-zero exit from the build command fails the deployment, which then never becomes `READY` and never receives the production domain.
  6. The production domain is assigned only after the build command has exited successfully, and the previous production deployment keeps serving until then.
  7. The pinned CLI exits with a non-zero status when the build fails, and the provider's build-duration limit is longer than the job's 15-minute limit.
  8. Vercel never automatically retries or re-runs a failed production build.
  9. With system environment variables enabled, Vercel sets `VERCEL` and `VERCEL_ENV` while the build command runs, in preview as well as production builds, and sets `VERCEL_ENV=production` only in production builds. Provider documentation is enough to confirm this; the first production build's `migration: passed` also shows that the PLT-2.8 check does not refuse a production build.
- Record these provider facts as well. They are not blocking: whatever the answer, the operator records it and the human decides on any change.
  - Sensitive marking: whether Vercel Hobby lets environment variables be marked Sensitive, so their values cannot be read back from the project's settings once saved.
  - Concurrent builds: Vercel Hobby's concurrent-build limit and whether a build beyond it queues or runs alongside another, recorded in [Free-plan operating limits](#free-plan-operating-limits).
- Configure the required [application variables](#configuration) only in Vercel production settings: a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` matching the public hostname, and the separate production database settings. `POSTGRES_HOST` must use the direct Neon PostgreSQL 18 endpoint in AWS Singapore; the database password and Django key stay only in Vercel production settings, never GitHub. Where Vercel Hobby allows it, mark `POSTGRES_PASSWORD` and `DJANGO_SECRET_KEY` Sensitive. Vercel's Preview and Development environments have no `POSTGRES_*` or `DJANGO_*` variables at all, and no such production variable also targets Preview or Development; because Sensitive values cannot be read back, this is checked by variable name and target, not by value. Agents never receive secret values.

Hosted integration checks remain required: final-revision PR review and main branch protection, main-only production access without deployment or rerun approval, clean committed deployment inputs, absence of provider builds from PR edits, production configuration and verified database TLS, system environment variables enabled, no `POSTGRES_*` or `DJANGO_*` variable in or targeting Preview or Development, Sensitive marking of the database password and Django key where available, deployment identity and domain mapping, public HTTPS/HTTP smoke checks, the provider facts above, build-time migration ordering, failure and build-log protection, and the manual recovery procedure in PLT-2.4. Local tests do not establish these hosted controls.
