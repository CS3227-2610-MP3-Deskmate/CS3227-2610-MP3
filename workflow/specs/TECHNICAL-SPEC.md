# Technical spec

How Deskmate is built and run. What it does is in [`PRODUCT-SPEC.md`](PRODUCT-SPEC.md).

## Architecture

- One Django project on Python 3.14 that renders HTML on the server, with no separate front end. Application code and its tests live under `src/`.
- PostgreSQL 18 is the database in every environment, including tests.
- The app ships as one Docker image.
- The app reads its configuration only from environment variables.
- Exact versions are pinned in the requirements files, the Dockerfile, the compose file and the workflows.

## Routes

| Route | Methods | Access | Purpose | Criteria |
| --- | --- | --- | --- | --- |
| `/` | GET | Public | Placeholder home page | PLT-1.1 |
| `/health/` | GET | Public | Reports whether the app can reach its database | PLT-1.2, PLT-1.3 |

A route requested without its trailing slash, such as `/health`, redirects with `301` to the route.

## Configuration

| Variable | Meaning | Criteria |
| --- | --- | --- |
| `DATABASE_URL` | The PostgreSQL database, with its user, password, host, port and name, as one URL | PLT-1.7 |
| `DJANGO_SECRET_KEY` | The key Django signs sessions and other data with | PLT-1.7 |
| `DJANGO_ALLOWED_HOSTS` | The host names the app answers to, separated by commas | PLT-1.7, PLT-1.8 |
| `DJANGO_DEBUG` | Turns on Django's debug pages | PLT-1.6 |

## Environments

| Environment | Runs | Database | Configuration |
| --- | --- | --- | --- |
| Local development | docker compose on a developer's machine runs the app, serving `http://localhost:8000/`, and PostgreSQL | A PostgreSQL container whose data survives restarts in a named volume | The developer's own `.env` file, started from `.env.example` |
| CI | GitHub Actions, on every pull request and every push to `main`, builds the image and runs the [verify command](../../AGENTS.md#commands) inside it | A PostgreSQL service container, discarded after each run | Set in the workflow, with no stored secrets ([SECURITY-SPEC](SECURITY-SPEC.md#secrets-and-settings)) |
