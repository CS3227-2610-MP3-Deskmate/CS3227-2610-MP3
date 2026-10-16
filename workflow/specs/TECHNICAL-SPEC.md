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

Application-supplied settings use `DJANGO_` or `POSTGRES_`; tests discard developer settings as described in [Environments](#environments). Provider-supplied `VERCEL_ENV=production` activates production validation in [settings](../../src/deskmate/settings.py); Vercel's system environment variables must remain enabled. Provider credentials are protected deployment-job inputs, not app settings.

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

The app environments are development and production, using Vercel Hobby and Neon Free for production. CI is temporary verification; there is no Preview environment. Hosted integration still requires the checks in [Operator prerequisites](#review-decisions-and-operator-prerequisites).

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | The app, serving `http://localhost:8000/`, and the [verify command](../../AGENTS.md#commands) run from the developer's `.venv`; docker compose runs only PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env`, copied from `.env.example`, which sets `DJANGO_DEBUG=true` and leaves `DJANGO_SECRET_KEY` empty. Docker compose reads it for the database, and the developer loads it into the shell that runs the app |
| Production | Vercel Hobby native Python 3.14/Django in Singapore (`sin1`); a provider-generated `vercel.app` public hostname, managed HTTPS and HTTP-to-HTTPS redirects; maximum request duration 60 seconds; no background workers | Neon Free PostgreSQL 18 in AWS Singapore (`ap-southeast-1`), separate from development and CI; direct endpoint with the connection controls above | Production-only database credentials and secret key; debug off; exact public hostname |

CI validation runs in GitHub Actions on every pull request and push to `main`, using throwaway PostgreSQL containers discarded after each run and no stored secrets. The unchanged verify command and tests run on the runner. Production runtime verification uses the public smoke test after deployment.

`pytest` needs no variables set by the developer: the tests take all their configuration from what is committed with them, except a secret key they make on each run ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)), and never from the developer's shell. Their database settings match the throwaway credentials in `.env.example` and the CI workflow.

## Release verification

PLT-2 uses **reviewed pull-request merge → successful main CI → automatic production deployment → public smoke test**, owned by GitHub Actions. The Vercel project's Git integration must be unlinked. There is no container-image publication. Deployment commands and pins are in the [workflow](../../.github/workflows/deploy.yml); provider verification is in [`release.py`](../../src/deskmate/release.py).

1. Require successful CI from a push to this repository for the exact current `main` commit admitted through the [reviewed-merge controls](SECURITY-SPEC.md#release-access-and-provenance). There is no per-deployment approval pause. Before submission, establish that earlier deployment-capable runs have no unsettled provider operation; unavailable or inconclusive evidence fails closed without deployment. Immediately before deployment, recheck current `main`; skip an outdated commit.
2. Submit only committed application/build inputs from a clean checkout of that checked commit to the fixed owner/project using the official Vercel CLI. Exclude local configuration, credentials and Git history. A normal [production deployment](https://vercel.com/docs/cli/deploy) builds the native application and automatically assigns its production domain when ready; there is no separate promotion or pre-live application probe.
3. Verify the returned deployment ID through authenticated provider responses: configured owner/project, production target and `READY` state. Confirm the fixed public hostname maps to that ID before public checks. Missing or conflicting identity/mapping fails; a healthy old site cannot establish success.
4. Smoke-test public HTTPS `/` and `/health/` against PLT-1.1 and PLT-1.2, with valid TLS and no bypass credential; do not follow redirects. Check HTTP redirects to the corresponding HTTPS URL. Record only repository/commit, GitHub run identity, owner/project/deployment IDs, hostname, stage and outcome.

The deployment job has a 15-minute execution limit from execution start, including preparation, build and final checks. Mapping and public smoke checks share a two-minute window starting when deployment completes, capped by the remaining job time. Each verification request is limited to 10 seconds or the remaining applicable deadline, whichever is shorter. Provider build status may be polled until completion within the job limit. Invalid TLS and authentication failures (`401`/`403`) fail immediately. Verification retries cover transient transport failures and HTTP `429`/`5xx` before body validation; for example, health `503` with `{"status": "error"}` is retryable within the same deadline. Identity and content checks apply to otherwise successful responses; missing/wrong identity or content and other unexpected HTTP statuses fail immediately. No retry resets a deadline or repeats deployment creation.

One GitHub concurrency group spans deployment execution through final checks, with `cancel-in-progress: false`. Pending runs may be replaced by GitHub. Each run that proceeds, including an explicitly requested rerun of the same commit, must satisfy the exact-CI, current-main and recovery checks and creates a new deployment. This is [job concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments), not a persistent lock over provider operations. If an earlier run may have submitted a deployment but its provider outcome is unknown, subsequent submissions are automatically blocked, including already queued pushes and reruns; missing reconciliation evidence also blocks submission. This includes timeout, cancellation, runner loss and a lost CLI/API response after Vercel may have accepted the request, even if the job exits normally as failed. Only a repository administrator may record the recovery acknowledgement in production configuration, identifying all reconciled run attempts after checking Vercel and confirming that no earlier operation can complete later. Before the first automatic release, the administrator must establish an explicit recovery baseline by reconciling all earlier deployment-capable attempts; missing baseline or history fails with `recovery: blocked`. The acknowledgement survives runner loss and cannot be written by deployment jobs or pull requests. Recovery does not bypass successful CI or the current-main check. Deployment is never automatically retried.

A build, deployment or smoke-test failure fails the job and identifies its stage. Once the domain switches, a runtime error can reach users before the smoke test detects it. Recovery is manual: fix and deploy again, or use Vercel Hobby's [rollback to the immediately previous production deployment](https://vercel.com/docs/instant-rollback) if available; the first release has no fallback. After rollback the operator must restore normal automatic domain assignment before another deployment. There is no automatic rollback, source-content readback/manifest, or custom persistent deployment state machine. Build, deployment and checks never run migrations or change production data.

### Free-plan operating limits

The selected free plans are used without automatic paid upgrades. Vercel Hobby is for personal, non-commercial use and does not provide paid team collaboration; the hosting account owner must be established. Its documented monthly allowances include 4 CPU-hours, 360 GB-hours of provisioned memory and one million function invocations. The 60-second request limit is below the documented 300-second Hobby ceiling ([Hobby](https://vercel.com/docs/plans/hobby)). Neon Free's documented per-project monthly allowances are 1 GB storage, 100 CU-hours and 5 GB transfer; compute can sleep after five minutes idle, compute or transfer exhaustion suspends service, and the storage cap prevents further storage-growing operations ([Neon plans](https://neon.com/docs/introduction/plans)). These provider limits can change and must be checked at setup. Cold starts and quota pauses can prevent availability; the slice adds no keep-awake traffic or availability guarantee.

### Review decisions and operator prerequisites

Hosted settings and integration have not been verified. Before enabling production deployments, operators must complete this setup:

- Confirm hosting account owners, eligibility for the selected plans and the current [free-plan limits](#free-plan-operating-limits).
- Configure the GitHub `production` environment to admit only the `main` branch, excluding tags and pull-request refs, with no required deployment reviewer. Preserve the [reviewed-merge controls](SECURITY-SPEC.md#release-access-and-provenance) on `main` and verify the automatic recovery block before enabling deployments.
- Set non-secret GitHub environment variables `VERCEL_ORG_ID`, `VERCEL_PROJECT_ID` and `VERCEL_PUBLIC_HOSTNAME` for the fixed owner, project and exact public hostname. The only deployment secret in GitHub is `VERCEL_TOKEN`, confined to the protected job. Verify its actual scope, use the least scope available and obtain human acceptance of any broader resource access; do not assume it is project-scoped.
- Configure the Vercel project with the repository root as its root directory and the Django preset, system environment variables enabled as required by [Configuration](#configuration), Git integration unlinked, and the stable production hostname publicly accessible. Use the committed [runtime configuration](../../vercel.json), without custom build or migration commands.
- Configure the required [application variables](#configuration) only in Vercel production settings: a strong `DJANGO_SECRET_KEY`, `DJANGO_DEBUG=false`, `DJANGO_ALLOWED_HOSTS` matching the public hostname, and the separate production database settings. `POSTGRES_HOST` must use the direct Neon PostgreSQL 18 endpoint in AWS Singapore; the database password and Django key stay only in Vercel production settings, never GitHub. Agents never receive secret values.

Hosted integration checks remain required: reviewed-merge and production-environment restrictions, automatic deployment after successful main CI, stale-run and rerun checks, automatic blocking after unknown provider outcomes and explicit operator recovery, clean committed deployment inputs, absence of provider builds from PR edits, production configuration and verified database TLS, deployment identity and domain mapping, public HTTPS/HTTP smoke checks, and the manual recovery procedure above. Local tests do not establish these hosted controls.
