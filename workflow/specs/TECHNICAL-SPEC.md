# Technical spec

How Deskmate is built and run. What it does is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md).

## Architecture

- One Django project on Python 3.14 that renders HTML on the server, with no separate front end. Application code and its tests live under `src/`: Django's commands run through `src/manage.py`, and the project package is `deskmate`, with its settings in `deskmate.settings`.
- PostgreSQL 18 is the database in every environment, including tests. Every attempt to connect to it gives up after 5 seconds.
- The app ships as one Docker image.
- The app reads its configuration only from environment variables.
- Exact versions are pinned in the requirements files, the Dockerfile, the compose file and the workflows.

**Proposed PLT-2 architecture exception, awaiting review:** production uses Vercel's managed native [Python 3.14](https://vercel.com/docs/functions/runtimes/python)/[Django](https://vercel.com/docs/frameworks/full-stack/django) runtime, which builds a Python function artifact from validated source. The Docker image remains for CI and portability, with all existing image security controls; production would no longer ship that image. Vercel controls Python patch updates within the selected 3.14 line, while repository dependencies and the Docker base remain pinned. CI and production artifacts and runtime environments are not claimed identical. The actual production runtime is checked on the hosted candidate before promotion. No new application dependency, production server package or CLI installation is proposed. See the [review checkpoint](#review-decisions-and-operator-prerequisites).

## Routes

| Route | Methods | Access | Purpose | Criteria |
| --- | --- | --- | --- | --- |
| `/` | GET | Public | Placeholder home page | PLT-1.1 |
| `/health/` | GET | Public | Reports whether the app can reach its database | PLT-1.2, PLT-1.3 |

## Configuration

Application-supplied settings use `DJANGO_` or `POSTGRES_`; tests discard developer settings as described in [Environments](#environments). The proposed hosted integration additionally consumes only the provider-owned deployment metadata described below; provider API credentials are release-job inputs, not app settings.

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
- `DJANGO_ALLOWED_HOSTS` supplies the exact public production hostname. Hosted startup adds only the current deployment hostname from Vercel-owned [`VERCEL_URL`](https://vercel.com/docs/environment-variables/system-environment-variables#vercel_url), whose availability and match to the authenticated deployment record must be proved before enabling releases. The resulting list contains those two exact names, without wildcards, schemes, paths or ports. No host name is inferred from a request header. The provider metadata is not consulted in local development or CI, and tests discard it from the developer's environment.
- `DJANGO_DEBUG` is off; the production database credentials and strong `DJANGO_SECRET_KEY` are configured directly in the provider's production settings. They are not copied into CI settings or written into source, image layers or built artifacts. Candidate and promoted deployment use the same production settings.

## Environments

The app environments are development and production. Vercel Hobby and Neon Free are selected; the native-runtime integration below is proposed for review. CI is temporary verification. A protected production-target candidate is a deployment version using the production database, not a separate persistent environment; no Preview environment is introduced.

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | The app, serving `http://localhost:8000/`, and the [verify command](../../AGENTS.md#commands) run from the developer's `.venv`; docker compose runs only PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env`, copied from `.env.example`, which sets `DJANGO_DEBUG=true` and leaves `DJANGO_SECRET_KEY` empty. Docker compose reads it for the database, and the developer loads it into the shell that runs the app |
| Production (proposed integration) | Vercel Hobby native Python 3.14/Django in Singapore (`sin1`); a provider-generated `vercel.app` public hostname, managed HTTPS and HTTP-to-HTTPS redirects; maximum request duration 60 seconds; no background workers | Neon Free PostgreSQL 18 in AWS Singapore (`ap-southeast-1`), separate from development and CI; direct endpoint with the connection controls above | Production-only database credentials and secret key; debug off; exact public and current deployment hostnames |

CI validation runs in GitHub Actions on every pull request and push to `main`, using throwaway PostgreSQL containers discarded after each run and no stored secrets. The verify command and tests run on the runner; a separate check builds the Docker image and runs Django's checks in it, without running tests inside the app image. The image retains its existing check-and-exit command; CI does not start a new web server or claim to run Vercel's managed runtime. CI success establishes source validation only. The hosted runtime check occurs after separate human production approval and before promotion.

`pytest` needs no variables set by the developer: the tests take all their configuration from what is committed with them, except a secret key they make on each run ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)), and never from the developer's shell. Their database settings match the throwaway credentials in `.env.example` and the CI workflow.

## Release verification

PLT-2 proposes the following sequence, owned by GitHub Actions. The Vercel Git integration is unlinked or automatic deployments are disabled, including pull-request builds. There is no workflow container-image publication and no publication credential or environment.

1. Validate the trusted `main` source using PLT-2.1, then wait for the required human review in the protected GitHub `production` environment. CI success cannot substitute for this approval.
2. After approval, recheck current `main` and ask Vercel to build a production-target candidate from that exact repository commit without assigning the public hostname. This is the production-target, skip-domain behaviour described by [Vercel](https://vercel.com/docs/cli/deploying-from-cli), not a Preview deployment. The build produces a native Python artifact, independently of the CI Docker build.
3. Validate the returned deployment ID, fixed owner/project, production target, trusted repository and source commit, provider-generated hostname and `READY` state using authenticated provider evidence. Then probe the candidate's HTTPS `/health/` using the protected automation bypass header. It must satisfy PLT-1.2 against the production Neon database. Creating the candidate and these probes occur only after human approval; neither changes schema or data.
4. Recheck current `main`, then promote that same production deployment ID without rebuilding ([promotion contract](https://vercel.com/docs/deployments/promoting-a-deployment)). Confirm through provider evidence that the configured public hostname maps to that ID; successful promotion of a different ID is failure.
5. Request public HTTPS `/` and `/health/` without a bypass credential and require PLT-1.1 and PLT-1.2. Record only the source commit, owner/project/deployment identifiers, hostname, stage and outcome; never full authenticated provider responses.

One release owns the approval wait through final checks. A stale commit stops before candidate creation or promotion. Unknown creation or promotion outcomes persist across cancellation, runner loss and later runs; no further deployment is allowed until an operator reconciles the provider outcome and confirms no previous action can complete later. A request timeout does not cancel the provider operation and does not authorise a blind repeat.

| Stage | Deadline from entering the stage |
| --- | --- |
| Candidate creation, build and `READY` confirmation | 10 minutes from the creation request |
| Candidate HTTPS health | 2 minutes after confirmed identity and readiness |
| Promotion and public-hostname mapping confirmation | 2 minutes from the promotion request |
| Public `/` and `/health/` checks | 2 minutes after confirmed hostname mapping |

Each HTTP/API request is limited to 10 seconds or the remaining stage time, whichever is shorter. Retries never reset a deadline. Exact application response contracts are PLT-1.1 and PLT-1.2; smoke checks do not follow redirects.

| Observation | Retry within the original stage deadline | Terminal without another retry |
| --- | --- | --- |
| Provider status or hostname-mapping read | Transport interruption/timeout, HTTP `429` or `5xx`, or a recognised nonterminal state | `401`/`403`, other unsuccessful HTTP status, invalid TLS, terminal provider failure, unrecognised state, or missing/malformed/mismatched identity or source evidence in an otherwise successful response |
| Candidate health | Transport interruption/refusal/timeout or `503` while the native runtime or database wakes | `401`/`403`, invalid TLS, any other nonconforming completed response, including malformed JSON or wrong content type |
| Public health and home checks after hostname confirmation | Transport interruption/refusal/timeout | Any completed response violating its PLT-1 contract, including `503`, redirects or malformed JSON; invalid TLS |

The status-read rules do not permit repeating an ambiguous create or promote request. Before hostname promotion, a failed candidate leaves the previous mapping unchanged; a first failure leaves no successful live app. After a switch, any failed final check reports an unsuccessful release and requires operator recovery. No automatic rollback or continued service from the old version is promised.

### Free-plan operating limits

The proposal uses the selected free plans without automatic paid upgrades. Vercel Hobby is for personal, non-commercial use and does not provide paid team collaboration; the hosting account owner must be established. Its documented monthly allowances include 4 CPU-hours, 360 GB-hours of provisioned memory and one million function invocations. The proposed 60-second request limit is below the documented 300-second Hobby ceiling ([Hobby](https://vercel.com/docs/plans/hobby)). Neon Free's documented per-project monthly allowances are 1 GB storage, 100 CU-hours and 5 GB transfer; compute can sleep after five minutes idle, compute or transfer exhaustion suspends service, and the storage cap prevents further storage-growing operations ([Neon plans](https://neon.com/docs/introduction/plans)). These provider limits can change and must be checked at setup. Cold starts and quota pauses can prevent availability; the slice adds no keep-awake traffic or availability guarantee.

### Review decisions and operator prerequisites

The selected providers and development/production split are settled. Review the complete proposed integration before implementation:

- Accept the native-runtime architecture exception: production is a Vercel Python artifact built from validated source, not the CI Docker image; Vercel manages Python 3.14 patching. The existing Docker build/check remains, with no local claim of production-runtime equivalence. Hosted candidate checks supply that evidence. No new dependency or CLI install is proposed; any later demonstrated dependency need requires separate approval.
- Accept the production-candidate sequence, shared production database, exact-ID promotion, deadlines/retries, stale-release handling and operator recovery without automatic rollback. Candidate creation itself requires human approval.
- Accept Singapore deployment regions, the generated public domain, 60-second request ceiling, direct Neon connections, verified public-network TLS, and the free-plan cold-start/quota behaviour. Confirm eligibility for personal, non-commercial Hobby use and who owns the hosting accounts; no owner or GitHub reviewer is chosen by this proposal.
- Operators supply non-secret Vercel owner/project IDs, the exact public hostname, Neon project/endpoint/database/user identifiers and GitHub reviewer identities. They configure the Vercel token, candidate bypass secret, database password and Django key directly in the appropriate protected/provider settings, together with main-only production protection, no self-review or bypass, disabled provider auto-deploy, candidate protection and public access to the stable hostname. The agent does not read or receive secret values.
- Before enabling releases, prove that authenticated Vercel evidence binds the built artifact to the requested repository commit, production target and fixed project; that candidate protection and `VERCEL_URL` binding work; that promotion preserves the same deployment ID without rebuilding; and that the public hostname maps to that ID. **Unresolved integration question:** which authenticated source/build metadata, for the chosen native deployment submission, proves the exact source commit? Caller-supplied labels alone are insufficient. Missing proof blocks release enablement rather than substituting a healthy old URL.
- Verify and disclose the actual scope of the Vercel token at setup; it may cover resources beyond this project. Confirm the operator can reconcile uncertain operations and recover the public hostname. Provider selection is not authorization to provision, install dependencies, implement, push or enable deployment.
