# Security spec

Threats to Deskmate and to how it is built, and the controls against them. Where a criterion implements a control, the control names it.

## Secrets and settings

Threat: a leaked secret key lets an attacker forge sessions and signed data, leaked database credentials expose every record, and debug pages show source code, settings and tracebacks to anyone.

- Secrets and personal data never go into code, logs or fixtures, and agents never read `.env` files: see [`AGENTS.md` "Safety"](../../AGENTS.md#safety).
- Configuration comes only from environment variables ([TECHNICAL-SPEC](TECHNICAL-SPEC.md#configuration)). Committed files, including `.env.example`, the compose file and the workflows, hold only throwaway credentials for the local and CI databases, and `.env.example` leaves `DJANGO_SECRET_KEY` empty.
- No secret key is written in code. With debug on and no key set, the app makes a random key each time it starts.
- The app fails closed: without a database URL, or with debug off and without a strong secret key or its allowed hosts, it refuses to start, and its error names the variable but never shows a value (PLT-1.7).
- Debug is off unless explicitly turned on (PLT-1.6), and it is turned on only in local development.
- With debug off, the app answers only to the hosts it is configured with (PLT-1.8), so a forged `Host` header cannot poison the links it builds.
- CI uses no stored secrets: its secret key is generated for each run, and its database is a throwaway container.
- The local database accepts connections only from the developer's own machine.

## Error pages, health check and logs

Threat: an error response reveals internals that help an attacker, or reflects attacker input into a page.

- With debug off, errors show only Deskmate's own pages, which show no internal details and never repeat the requested path or host (PLT-1.4, PLT-1.5, PLT-1.8).
- The health check reveals only `ok` or `error` (PLT-1.2, PLT-1.3).
- Server errors go to standard error with their traceback (PLT-1.5), never to the visitor. Logs never include request bodies or cookies.

## Container image

Threat: a tampered base image, a secret baked into an image layer, or a compromised app taking over its container.

- Base images are official Docker images pinned to an exact version and digest, wherever they are used.
- The image holds only what the app needs to run and be tested, never `.env` files or the Git history.
- The app runs as a non-root user.
- Django's development server is used only in local development.

## CI and dependencies

Threat: a compromised action or package, or an agent's change to a workflow, runs attacker code with the repository's token, leaks secrets or lets failing code merge.

- Workflows get least-privilege permissions, SHA-pinned actions, secrets only where needed, no `pull_request_target`, and the verify command run unchanged: see [`devops.md`](../agents/devops.md), step 3.
- Dependencies are exact pins of real PyPI packages ([`devops.md`](../agents/devops.md), step 2), added only with the human's approval ([`AGENTS.md` "Safety"](../../AGENTS.md#safety)).
- Only devops may write the workflows, the Dockerfile, the compose file and the requirements files, within the limits in [`workflow/README.md` "How scope is enforced"](../README.md#how-scope-is-enforced).
- Merging needs a reviewed pull request with passing checks: see [`workflow/README.md` "GitHub settings"](../README.md#github-settings-once).
