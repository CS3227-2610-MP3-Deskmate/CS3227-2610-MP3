# Technical spec

How Deskmate is built and run. What it does is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md).

## Architecture

- One Django project on Python 3.14 that renders HTML on the server, with no separate front end. Application code and its tests live under `src/`: Django's commands run through `src/manage.py`, and the project package is `deskmate`, with its settings in `deskmate.settings`.
- PostgreSQL 18 is the database in every environment, including tests. Every attempt to connect to it gives up after 5 seconds.
- The app ships as one Docker image.
- The app reads its configuration only from environment variables.
- Exact versions are pinned in the requirements files, the Dockerfile, the compose file and the workflows.

## Routes

| Route | Methods | Access | Purpose | Criteria |
| --- | --- | --- | --- | --- |
| `/` | GET | Public | Placeholder home page | PLT-1.1 |
| `/health/` | GET | Public | Reports whether the app can reach its database | PLT-1.2, PLT-1.3 |

## Configuration

Every app configuration variable's name starts with `DJANGO_` or `POSTGRES_`, so the tests can drop all of them from the developer's shell ([Environments](#environments)); provider identifiers and release credentials belong to the deployment environment, not to the app's configuration.

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

## Environments

The intended app environments are development and production. Production hosting remains a proposal; CI is temporary verification, not another persistent app environment.

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | The app, serving `http://localhost:8000/`, and the [verify command](../../AGENTS.md#commands) run from the developer's `.venv`; docker compose runs only PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env`, copied from `.env.example`, which sets `DJANGO_DEBUG=true` and leaves `DJANGO_SECRET_KEY` empty. Docker compose reads it for the database, and the developer loads it into the shell that runs the app |
| Production (proposed) | Host, plan and deployment integration pending selection; Python 3.14 and the Docker image baseline remain unchanged | PostgreSQL 18, separate from development and CI; provider and connection controls pending selection | Existing app variables supplied securely; debug off, explicit production hosts, and production-only database credentials and secret key |

CI validation runs in GitHub Actions on every pull request and push to `main`, using throwaway PostgreSQL containers discarded after each run and no stored secrets. The verify command and tests run on the runner; a separate check builds the Docker image and runs Django's checks in it, without running tests inside the app image. The proposed PLT-2.1 image smoke check supplements these checks: debug is off, host names are explicit, and a fresh key is generated for the run. CI success establishes validation only; production deployment needs separate human approval.

`pytest` needs no variables set by the developer: the tests take all their configuration from what is committed with them, except a secret key they make on each run ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)), and never from the developer's shell. Their database settings match the throwaway credentials in `.env.example` and the CI workflow.

## Release verification

PLT-2 proposes CI validation, publication, human approval and production deployment. Its provider-dependent contract must be settled before implementation.

- A candidate is identified by its `main` commit and the digest of the image built and validated for that commit. The proposed release image repository is one operator-selected public GitHub Container Registry (GHCR) package, with a fixed registry, namespace and package name; a workflow caller cannot substitute another package. Deployment of its complete `sha256` digest without rebuilding is the proposed contract, subject to host compatibility.
- The proposed CI image readiness deadline is 60 seconds. Hosted deployment and individual request deadlines remain pending the selected provider's startup behaviour. Health checks do not follow redirects and require the exact status, content type and JSON object in PLT-1.2.
- Retry eligibility is defined below. Every retry is bounded by the original overall deadline; a retry never resets that deadline or permits success without the exact required health response.

| Check | May retry within its deadline | Terminal failure without another retry |
| --- | --- | --- |
| CI image startup health | Connection refusal, transport timeout or interruption, or a completed response other than an authentication or permission rejection that does not yet satisfy PLT-1.2, including `503` or malformed JSON | Authentication or permission rejection (`401` or `403`), the server exits, or the readiness deadline expires |
| Provider deployment status | Transport timeout or interruption; HTTP `429` or `5xx`; a valid nonterminal deployment state | Authentication or permission rejection; any other unsuccessful HTTP status; invalid TLS certificate; a terminal deployment failure; an otherwise successful response with missing, malformed or mismatched service, deployment or image identity, including the wrong digest; an unrecognised state; or the deployment deadline expires |
| Hosted health, after the requested deployment is confirmed live | Connection refusal, transport timeout or interruption | Any completed HTTP response that does not satisfy PLT-1.2, including a redirect, `503`, wrong content type or malformed JSON; invalid TLS certificate; or the deployment deadline expires |

- A deployment request whose outcome is uncertain does not authorise a replacement request. In particular, a timeout while requesting deployment leaves the outcome unknown; the status and health retry rules do not permit blindly triggering another deployment.
- The proposed deployment identity check ties a provider deployment ID to production and the requested image digest, followed by an HTTPS smoke check. A currently healthy URL alone cannot establish that the requested release is live. How the selected provider proves this identity and readiness remains pending.
- One release owns the production approval wait and deployment; later candidates wait and may be superseded before they start. The current-`main` check in PLT-2.6 also applies after approval and on reruns. Unknown deployment outcomes remain blocked across job cancellation, runner termination and later workflow runs; ownership cannot pass to another release until the operator confirms the provider outcome and that no deployment remains pending or in progress.
- The proposed release result records the source commit, image digest, provider deployment identity and validation outcome without secret values.

Hosting resources, the designated registry package's access controls, environment configuration and protected GitHub publication and deployment environments are operator prerequisites; no workflow silently creates paid resources. The required access controls and proof before enabling releases are in [SECURITY-SPEC](SECURITY-SPEC.md#release-access-and-provenance).

### Pending hosting and deployment decisions

- Select hosting and a database after evaluating free options, their limits and cold-start behaviour. No provider or paid plan is selected.
- Confirm support for the existing Docker, Python 3.14 and PostgreSQL 18 baseline, then agree the production server dependency, image runtime configuration, deployment identity/readiness checks, deadlines and previous-release/first-deployment failure behaviour. A runtime change requires a separate human decision.
- Agree the production host name, HTTPS provision, database network exposure and transport controls, and provider credential scope. Private networking and disabled public database access are not assumed to be available on an unselected provider.
