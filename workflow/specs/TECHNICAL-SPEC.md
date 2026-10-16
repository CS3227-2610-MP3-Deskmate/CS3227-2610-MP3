# Technical spec

How Deskmate is built and run. What it does is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md).

## Architecture

- One Django project on Python 3.14 that renders HTML on the server, with no separate front end. Application code and its tests live under `src/`: Django's commands run through `src/manage.py`, and the project package is `deskmate`, with its settings in `deskmate.settings`.
- PostgreSQL 18 is the database in every environment, including tests. Every attempt to connect to it gives up after 5 seconds.
- The app ships as one `linux/amd64` Docker image whose default command runs a production WSGI server on `0.0.0.0:8000`; the server package requires separate dependency approval before implementation.
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

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | The app, serving `http://localhost:8000/`, and the [verify command](../../AGENTS.md#commands) run from the developer's `.venv`; docker compose runs only PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env`, copied from `.env.example`, which sets `DJANGO_DEBUG=true` and leaves `DJANGO_SECRET_KEY` empty. Docker compose reads it for the database, and the developer loads it into the shell that runs the app |
| CI validation | GitHub Actions, on every pull request and every push to `main`, runs the verify command on the runner; a separate image check builds the image, runs Django's checks in it and starts its default production server for PLT-2.1; tests still run on the runner | Throwaway PostgreSQL containers, discarded after each run | Debug off for image checks, explicit test host names, a fresh secret key generated for that run and throwaway database credentials; no stored secrets ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)) |
| Staging | A paid, always-on Render web service in Singapore, using an image from the GitHub Container Registry (GHCR), with a provider-assigned `onrender.com` host name | Its own paid managed PostgreSQL 18 instance in Singapore, using its internal connection address | Existing app variables injected by the provider; debug off, only this service's host name allowed, and this environment's own database credentials and secret key |
| Production | A separate paid, always-on Render web service in Singapore, using the same image digest as staging, with its own provider-assigned `onrender.com` host name | A separate paid managed PostgreSQL 18 instance in Singapore, using its internal connection address | Existing app variables injected by the provider; debug off, only this service's host name allowed, and this environment's own database credentials and secret key |

`pytest` needs no variables set by the developer: the tests take all their configuration from what is committed with them, except a secret key they make on each run ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)), and never from the developer's shell. Their database settings match the throwaway credentials in `.env.example` and the CI workflow.

Render terminates TLS and redirects HTTP to HTTPS for both public service host names ([managed TLS](https://render.com/docs/tls)). Its router forwards requests to the container's HTTP port; the database is reached through the provider's private network, with external database access disabled ([database connections](https://render.com/docs/postgresql-creating-connecting)). Both services use `/health/` as their provider readiness path.

## Release verification

PLT-2 defines release behaviour; these are its runtime limits and deployment identities.

- A candidate is identified by its `main` commit and the digest of the image built and validated for that commit. GHCR holds the public release image; deployments use a complete `sha256` digest reference, never a mutable tag ([image deployment](https://render.com/docs/deploying-an-image)).
- CI allows 60 seconds from starting the image for its smoke check to succeed. Each hosted deployment allows 20 minutes from its deployment request for provider confirmation and the subsequent smoke check; an individual HTTP or provider API request times out after 10 seconds. Health checks do not follow redirects and require the exact status, content type and JSON object in PLT-1.2.
- A provider deployment ID is tied to the target service and requested image digest. Success requires that deployment's live status and matching image identity, followed by the HTTPS smoke check. A service's currently healthy URL alone cannot establish success. Render's own readiness check accepts more responses than PLT-1.2, so it cannot replace the smoke check ([provider health checks](https://render.com/docs/health-checks)).
- One release owns both environments through the production approval wait; later candidates wait and may be superseded before they start. The current-`main` check in PLT-2.6 also applies after approval and on reruns. A deployment with unknown outcome must be resolved before ownership passes to another release.
- The release result records the source commit, image digest, environment, provider deployment ID and validation outcome without secret values. It distinguishes a provider readiness failure before traffic switches from a failed smoke check after the deployment becomes live.

Hosting resources, environment configuration and the protected GitHub environments are operator prerequisites; no workflow silently creates paid resources. The required access controls are in [SECURITY-SPEC](SECURITY-SPEC.md#release-access-and-provenance).
