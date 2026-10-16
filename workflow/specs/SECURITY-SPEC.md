# Security spec

Threats to Deskmate and to how it is built, and the controls against them. Where a criterion implements a control, the control names it.

## Secrets and settings

Threat: a leaked secret key lets an attacker forge sessions and signed data, leaked database credentials expose every record, and debug pages show source code, settings and tracebacks to anyone.

- Secrets and personal data never go into code, logs or fixtures, and agents never read `.env` files: see [`AGENTS.md` "Safety"](../../AGENTS.md#safety).
- Configuration comes only from environment variables ([TECHNICAL-SPEC](TECHNICAL-SPEC.md#configuration)). Committed files, including `.env.example`, the compose file, the workflows and the tests' configuration, hold only the throwaway credentials of the local and CI databases, and never a secret key.
- No secret key is written in code, including the tests: with debug on and `DJANGO_SECRET_KEY` unset or empty, the app makes a random key each time it starts, and the tests make their own key on each run.
- The app fails closed: with a required variable unset or invalid, including a weak secret key or no allowed hosts when debug is off, it refuses to start, and its error names the variable but never shows a value (PLT-1.7).
- Debug is off unless explicitly turned on (PLT-1.6), and it is turned on only in local development.
- With debug off, the app answers only to the hosts in `DJANGO_ALLOWED_HOSTS`; a `*` there switches that check off. Proposed production configuration forbids wildcards and allows only its own host names (PLT-2.8); the underlying PLT-1 configuration syntax is unchanged.
- CI validation uses no stored secrets, and its databases are throwaway containers; release credentials are isolated as described in [Release access and provenance](#release-access-and-provenance).
- The local database accepts connections only from the developer's own machine.
- Proposed production configuration uses a database, credentials and Django secret key separate from development and temporary CI values; production credentials are never supplied to CI validation (PLT-2.8).
- Proposed production database access uses authenticated public-network TLS with system-CA and hostname verification, without plaintext fallback; local and CI plaintext is limited to loopback. The direct endpoint, connection lifetime and timeout are specified in [Configuration](TECHNICAL-SPEC.md#configuration). This proposal does not claim a private network or disabled external database access (PLT-2.8).

## Error pages, health check and logs

Threat: an error response reveals internals that help an attacker, or reflects attacker input into a page.

- With debug off, errors show no internal details (PLT-1.4).
- The health check reveals only `ok` or `error` (PLT-1.2, PLT-1.3).
- Server errors go to standard error with their traceback (PLT-1.4), never to the visitor. Logs never include request bodies or cookies.

## Container image

Threat: a tampered base image, a secret baked into an image layer, or a compromised app taking over its container.

- Base images are official Docker images pinned to an exact version and digest, wherever they are used.
- The image holds only what the app needs to run, never `.env` files or the Git history.
- The app runs as a non-root user.
- Django's development server never serves a deployed environment.

## CI and dependencies

Threat: a compromised action or package, or an agent's change to a workflow, runs attacker code with the repository's token, leaks secrets or lets failing code merge.

- Workflows get least-privilege permissions, SHA-pinned actions, secrets only where needed, no `pull_request_target`, and the verify command run unchanged: see [`devops.md`](../agents/devops.md), step 3.
- Dependencies are exact pins of real PyPI packages ([`devops.md`](../agents/devops.md), step 2), added only with the human's approval ([`AGENTS.md` "Safety"](../../AGENTS.md#safety)).
- Only devops may write the workflows, the Dockerfile, the compose file and the requirements files, within the limits in [`workflow/README.md` "How scope is enforced"](../README.md#how-scope-is-enforced).
- Merging needs a reviewed pull request with passing checks: see [`workflow/README.md` "GitHub settings"](../README.md#github-settings-once).

## Release access and provenance

The following controls belong to the proposed native-runtime PLT-2 design. The architecture exception and [operator proof](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites) remain for review; no hosted controls are claimed configured.

Threat: untrusted source obtains production credentials, a candidate differs from the checked source, an old approval replaces a newer release, or a healthy old deployment conceals failure.

- Pull requests and CI validation use read-only repository permissions, throwaway databases and no stored secrets. There is no container publication workflow, package-write grant or publisher credential. The designated Vercel project cannot be deployed using the repository's workflow token alone (PLT-2.1, PLT-2.5).
- Only the protected GitHub `production` job receives the Vercel token and candidate-protection automation bypass secret, after required human approval. Its environment admits only the `main` branch, excludes pull-request refs and tags, prevents self-review and forbids protection bypass. CI success is not approval. Broadening permissions in a pull-request workflow cannot grant access to these protected secrets (PLT-2.3, PLT-2.5).
- Vercel Git auto-deployment is disabled or the Git integration is unlinked: pull requests and unapproved commits cannot cause provider builds, create Preview deployments or receive production configuration. Release input is the validated repository commit; caller-selected repositories, project IDs, source refs and deployment IDs are not accepted. The fixed owner/project and public hostname are operator configuration.
- Provider credential scope is verified and disclosed during setup; a Vercel token is not assumed project-scoped. Use the least scope available, keep it within the approved production job and require the human to accept any broader resource access. Production database credentials and the Django key stay in provider production settings; the workflow does not fetch them or dump environment configuration.
- Candidate access requires deployment protection. The workflow sends the automation bypass secret only as a header to the exact verified candidate HTTPS hostname, never in a query string, log, artifact or redirected request. The stable production hostname remains public, and final public checks use no bypass secret. Host allow-list construction trusts only configured public-host and provider-owned deployment metadata, never client headers (PLT-2.7, PLT-2.8).
- Authenticated provider evidence must bind deployment ID, owner/project, production target and trusted source commit; a caller-supplied commit label or a successful health response alone is insufficient. Promotion must preserve the checked deployment ID without rebuilding, and the public-hostname mapping must be confirmed independently. Missing or conflicting identity evidence fails closed (PLT-2.2, PLT-2.3).
- Vercel builds the native artifact only from the trusted approved source. Build and deployment steps never run migrations or mutate production data; candidate health only verifies database connectivity. Production secrets must not be embedded in source, built artifacts, logs or uploaded local configuration. All retained Docker-image controls above still apply; the [managed-runtime exception](TECHNICAL-SPEC.md#architecture) does not assert control over Vercel's Python patch release.
- Release serialization spans the approval wait, candidate, promotion and final checks. Current `main` is rechecked before candidate creation and promotion. Unknown create/promote outcomes remain blocked across cancellation and runner termination until operator reconciliation; no blind repeat or automatic rollback is permitted (PLT-2.4, PLT-2.6).
- Authenticated Vercel responses may contain secrets. Logs and release records contain only the allow-listed identifiers and stage results defined in [Release verification](TECHNICAL-SPEC.md#release-verification), never full API responses, request headers, environment dumps or secret values. Setup proof must establish these controls before deployments are enabled.
