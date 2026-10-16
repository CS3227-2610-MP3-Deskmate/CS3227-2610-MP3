# Technical spec

How Deskmate is built and run. What it does is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md).

## Architecture

- One Django project on Python 3.14 that renders HTML on the server, with no separate front end. Application code and its tests live under `src/`: Django's commands run through `src/manage.py`, and the project package is `deskmate`, with its settings in `deskmate.settings`.
- PostgreSQL 18 is the database in every environment, including tests. Every attempt to connect to it gives up after 5 seconds.
- The app reads its configuration only from environment variables.
- Repository dependencies, CI tooling and PostgreSQL container images have exact version pins; container images also have digest pins.

**PLT-2 proposal, awaiting review:** replace app Docker packaging and its CI build/check job with Vercel's native [Python 3.14](https://vercel.com/docs/functions/runtimes/python)/[Django](https://vercel.com/docs/frameworks/full-stack/django) runtime. Docker remains for development and CI PostgreSQL only. Vercel builds from the checked source and manages Python patch updates within 3.14; CI and production are not claimed to run identical artifacts or runtimes. The proposed deployment tool is the official Vercel CLI, subject to [review](#review-decisions-and-operator-prerequisites), with no new Django dependency. No implementation or installation is authorised by this proposal.

## Routes

| Route | Methods | Access | Purpose | Criteria |
| --- | --- | --- | --- | --- |
| `/` | GET | Public | Placeholder home page | PLT-1.1 |
| `/health/` | GET | Public | Reports whether the app can reach its database | PLT-1.2, PLT-1.3 |

## Configuration

Application-supplied settings use `DJANGO_` or `POSTGRES_`; tests discard developer settings as described in [Environments](#environments). Provider credentials are protected deployment-job inputs, not app settings.

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

The existing variables and their PLT-1 validation contract stay unchanged. Proposed production configuration adds these constraints under PLT-2.8:

- `POSTGRES_HOST` is the exact Neon direct endpoint hostname; connection pooling and persistent Django database connections are disabled. The existing 5-second connection timeout remains.
- Database transport is fixed by the host: literal `localhost`, `127.0.0.1` and `::1` may use plaintext for development or isolated CI; every other host uses `sslmode=verify-full` with the system CA trust store (`sslrootcert=system`). Production requires the selected Neon hostname and verified TLS. There is no setting that permits plaintext for a remote host, disables certificate verification or falls back after TLS failure.
- `DJANGO_ALLOWED_HOSTS` contains only the exact public production hostname, without wildcards, schemes, paths or ports. No deployment URL, `VERCEL_URL` value or request header expands it.
- `DJANGO_DEBUG` is off; production database credentials and the strong `DJANGO_SECRET_KEY` are configured directly in provider production settings. They are not copied into CI settings or written into source or built artifacts.

## Environments

The app environments are development and production. Vercel Hobby and Neon Free are selected; the integration below remains proposed. CI is temporary verification; there is no Preview environment.

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | The app, serving `http://localhost:8000/`, and the [verify command](../../AGENTS.md#commands) run from the developer's `.venv`; docker compose runs only PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env`, copied from `.env.example`, which sets `DJANGO_DEBUG=true` and leaves `DJANGO_SECRET_KEY` empty. Docker compose reads it for the database, and the developer loads it into the shell that runs the app |
| Production (proposed integration) | Vercel Hobby native Python 3.14/Django in Singapore (`sin1`); a provider-generated `vercel.app` public hostname, managed HTTPS and HTTP-to-HTTPS redirects; maximum request duration 60 seconds; no background workers | Neon Free PostgreSQL 18 in AWS Singapore (`ap-southeast-1`), separate from development and CI; direct endpoint with the connection controls above | Production-only database credentials and secret key; debug off; exact public hostname |

CI validation runs in GitHub Actions on every pull request and push to `main`, using throwaway PostgreSQL containers discarded after each run and no stored secrets. The unchanged verify command and tests run on the runner. The proposed removal of the app-image job leaves production runtime verification to the public smoke test after deployment.

`pytest` needs no variables set by the developer: the tests take all their configuration from what is committed with them, except a secret key they make on each run ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)), and never from the developer's shell. Their database settings match the throwaway credentials in `.env.example` and the CI workflow.

## Release verification

PLT-2 proposes **CI → human approval → production deployment → public smoke test**, owned by GitHub Actions. The Vercel project's Git integration is unlinked. There is no container-image publication.

1. Require successful CI for the exact `main` commit. Wait for human approval of this run in the protected GitHub `production` environment. After approval, immediately before deployment, recheck current `main`; skip an outdated commit.
2. Submit only committed application/build inputs from a clean checkout of that checked commit to the fixed owner/project using the official Vercel CLI. Exclude local configuration, credentials and Git history. A normal [production deployment](https://vercel.com/docs/cli/deploy) builds the native application and automatically assigns its production domain when ready; there is no separate promotion or pre-live application probe.
3. Verify the returned deployment ID through authenticated provider responses: configured owner/project, production target and `READY` state. Confirm the fixed public hostname maps to that ID before public checks. Missing or conflicting identity/mapping fails; a healthy old site cannot establish success.
4. Smoke-test public HTTPS `/` and `/health/` against PLT-1.1 and PLT-1.2, with valid TLS and no bypass credential; do not follow redirects. Check HTTP redirects to the corresponding HTTPS URL. Record only repository/commit, GitHub run identity, owner/project/deployment IDs, hostname, stage and outcome.

The deployment job has a 15-minute execution limit after approval, including build and final checks. Mapping and public smoke checks share a two-minute window starting when deployment completes, capped by the remaining job time. Each verification request is limited to 10 seconds or the remaining applicable deadline, whichever is shorter. Provider build status may be polled until completion within the job limit. Invalid TLS and authentication failures (`401`/`403`) fail immediately. Verification retries cover transient transport failures and HTTP `429`/`5xx` before body validation; for example, health `503` with `{"status": "error"}` is retryable within the same deadline. Identity and content checks apply to otherwise successful responses; missing/wrong identity or content and other unexpected HTTP statuses fail immediately. No retry resets a deadline or repeats deployment creation.

One GitHub concurrency group spans approval through final checks, with `cancel-in-progress: false`. Pending runs may be replaced by GitHub; each run that proceeds, including a rerun of the same commit, needs fresh approval and a new deployment. This provides [job concurrency](https://docs.github.com/en/actions/how-tos/deploy/configure-and-manage-deployments/control-deployments), not a persistent lock over provider operations. Any unknown provider outcome requires an operator to check Vercel and confirm the earlier operation's outcome and that it cannot complete later before approving any subsequent run, including an already queued push. This includes timeout, cancellation, runner loss and a lost CLI/API response after Vercel may have accepted the request, even if the job exits normally as failed. Deployment is never automatically retried.

A build, deployment or smoke-test failure fails the job and identifies its stage. Once the domain switches, a runtime error can reach users before the smoke test detects it. Recovery is manual: fix and deploy again, or use Vercel Hobby's [rollback to the immediately previous production deployment](https://vercel.com/docs/instant-rollback) if available; the first release has no fallback. After rollback the operator must restore normal automatic domain assignment before another deployment. There is no automatic rollback, source-content readback/manifest, or custom persistent deployment state machine. Build, deployment and checks never run migrations or change production data.

### Free-plan operating limits

The proposal uses the selected free plans without automatic paid upgrades. Vercel Hobby is for personal, non-commercial use and does not provide paid team collaboration; the hosting account owner must be established. Its documented monthly allowances include 4 CPU-hours, 360 GB-hours of provisioned memory and one million function invocations. The proposed 60-second request limit is below the documented 300-second Hobby ceiling ([Hobby](https://vercel.com/docs/plans/hobby)). Neon Free's documented per-project monthly allowances are 1 GB storage, 100 CU-hours and 5 GB transfer; compute can sleep after five minutes idle, compute or transfer exhaustion suspends service, and the storage cap prevents further storage-growing operations ([Neon plans](https://neon.com/docs/introduction/plans)). These provider limits can change and must be checked at setup. Cold starts and quota pauses can prevent availability; the slice adds no keep-awake traffic or availability guarantee.

### Review decisions and operator prerequisites

The selected providers and development/production split are settled. These decisions remain for human review:

- Accept native Vercel Python 3.14 with managed patching, removal of app Docker packaging and its CI job, and the proposed [security tradeoffs](SECURITY-SPEC.md#release-access-and-provenance): public checks after deployment and manual recovery.
- Approve adding the official Vercel CLI as CI tooling. Devops must verify and pin its exact version before installation; no tool is installed by this proposal. Commands and provider API details belong in the later implementation plan.
- Accept the Singapore regions, generated public hostname, 60-second app-request ceiling, verified direct Neon connections and free-plan limits above. Confirm Hobby eligibility and hosting account owners.

Before enablement, operators supply non-secret owner/project IDs, public hostname, Neon endpoint/database/user identifiers and GitHub reviewer identities. They configure main-only production approval with no self-review or bypass, unlinked Vercel Git integration, public domain access, the Vercel token only in the protected GitHub job, and the database password/Django key only in provider production settings. The token's actual scope must be checked and disclosed for human acceptance; it is not assumed project-scoped. Agents never receive secret values.

Implementation must verify approval and rerun behaviour, clean committed inputs, absence of provider builds from PR edits, deployment identity/domain mapping, public smoke checks and recovery procedure before enabling deployments. These are integration checks for the implementing team, not API research delegated to the human. Provider selection does not authorise provisioning, installation, implementation, pushing or deployment enablement.
