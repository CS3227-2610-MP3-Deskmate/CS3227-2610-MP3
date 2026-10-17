# Security spec

Threats to Deskmate and to how it is built, and the controls against them. Where a criterion implements a control, the control names it.

## Secrets and settings

Threat: a leaked secret key lets an attacker forge sessions and signed data, leaked database credentials expose every record, and debug pages show source code, settings and tracebacks to anyone.

- Secrets and personal data never go into code, logs or fixtures, and agents never read `.env` files: see [`AGENTS.md` "Safety"](../../AGENTS.md#safety).
- Configuration comes only from environment variables ([TECHNICAL-SPEC](TECHNICAL-SPEC.md#configuration)). Committed files, including `.env.example`, the compose file, the workflows and the tests' configuration, hold only the throwaway credentials of the local and CI databases, and never a secret key.
- No secret key is written in code, including the tests: with debug on and `DJANGO_SECRET_KEY` unset or empty, the app makes a random key each time it starts, and the tests make their own key on each run.
- The app fails closed: with a required variable unset or invalid, including a weak secret key or no allowed hosts when debug is off, it refuses to start, and its error names the variable but never shows a value (PLT-1.7).
- Debug is off unless explicitly turned on (PLT-1.6), and it is turned on only in local development.
- With debug off, the app answers only to the hosts in `DJANGO_ALLOWED_HOSTS`; a `*` there switches that check off. Production configuration permits only the exact public hostname, without expansion from provider metadata or request headers (PLT-2.8); the underlying PLT-1 configuration syntax is unchanged.
- CI validation uses no stored secrets, and its databases are throwaway containers; release credentials are isolated as described in [Release access and provenance](#release-access-and-provenance).
- The local database accepts connections only from the developer's own machine.
- Production configuration uses a database, credentials and Django secret key separate from development and temporary CI values; production credentials are never supplied to CI validation (PLT-2.8).
- Production database access uses authenticated public-network TLS with system-CA and hostname verification, without plaintext fallback; local and CI plaintext is limited to loopback. The production-mode signal, direct endpoint, connection lifetime and timeout are specified in [Configuration](TECHNICAL-SPEC.md#configuration). No private network or disabled external database access is claimed (PLT-2.8).

## Error pages, health check and logs

Threat: an error response reveals internals that help an attacker, or reflects attacker input into a page.

- With debug off, errors show no internal details (PLT-1.4).
- The health check reveals only `ok` or `error` (PLT-1.2, PLT-1.3).
- Server errors go to standard error with their traceback (PLT-1.4), never to the visitor. Logs never include request bodies or cookies.

## Container image

Threat: a tampered base image, a secret baked into an image layer, or a compromised app taking over its container.

- Base images are official Docker images pinned to an exact version and digest, wherever they are used, including development and CI PostgreSQL.
- There is no app image; the [native-runtime architecture](TECHNICAL-SPEC.md#architecture) trusts Vercel's runtime isolation and patch management. App-image minimisation and non-root controls are inapplicable to this managed runtime.
- Django's development server never serves a deployed environment.

## CI and dependencies

Threat: a compromised action or package, or an agent's change to a workflow, runs attacker code with the repository's token, leaks secrets or lets failing code merge.

- Workflows get least-privilege permissions, SHA-pinned actions, secrets only where needed, no `pull_request_target`, and the verify command run unchanged: see [`devops.md`](../agents/devops.md), step 3.
- Python dependencies are exact pins of real PyPI packages ([`devops.md`](../agents/devops.md), step 2), added only with the human's approval ([`AGENTS.md` "Safety"](../../AGENTS.md#safety)). The official Vercel CLI has an exact version pin in the [deployment workflow](../../.github/workflows/deploy.yml).
- Only devops may write the workflows, the Dockerfile, the compose file and the requirements files, within the limits in [`workflow/README.md` "How scope is enforced"](../README.md#how-scope-is-enforced).
- Merging needs a reviewed pull request with passing checks: see [`workflow/README.md` "GitHub settings"](../README.md#github-settings-once).

## Release access and provenance

The PLT-2 design trusts the protected job's committed deployment inputs and Vercel's build, without independent source-content readback, pre-live runtime checks or separate promotion. A runtime failure can reach users before the public smoke test detects it. GitHub concurrency does not guarantee exclusion after runner loss; recovery relies on the operator procedure in [PLT-2.4](product/platform.md#plt-2-release-the-placeholder-site-to-production). Hosted controls still require the [setup and integration checks](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites); none are claimed configured or verified.

Threat: untrusted source obtains production credentials, unchecked source is deployed, an earlier provider operation replaces a newer deployment, a healthy old site conceals failure, a migration leaves live code against a schema it cannot use, or migration output leaks credentials or row data.

- Pull requests and CI validation use read-only repository permissions, throwaway databases and no stored secrets. There is no container publication, package-write grant or publisher credential. The repository's workflow token alone cannot deploy to the designated Vercel project (PLT-2.1, PLT-2.5).
- Only the protected GitHub `production` job receives the Vercel token, automatically after successful same-repository `main`-push CI. Main branch protection requires a pull request approved at its final revision (stale approvals dismissed) and passing CI, without bypass or force pushes. Its environment admits only `main`, excludes pull-request refs and tags, and requires no separate deployment or rerun approval; editable PR workflow permissions cannot grant these secrets (PLT-2.1, PLT-2.3, PLT-2.5).
- The Vercel project's Git integration must be unlinked. PR changes to deployment configuration must cause no provider build or exposure of production configuration. The protected job submits only committed inputs from a clean checkout of the exact CI-checked current-`main` commit; caller-selected repositories, project IDs, source refs and deployment IDs are not accepted. Owner/project and public hostname are fixed operator configuration (PLT-2.2, PLT-2.5).
- Verify and disclose actual Vercel token scope during setup, use the least scope available and require human acceptance of access beyond this project. Production database credentials and the Django key stay in provider production settings; the job does not fetch them or dump environment configuration. There is no deployment-protection bypass secret (PLT-2.7, PLT-2.8).
- Verify the returned deployment ID, fixed owner/project, production target, `READY` state and authenticated public-hostname mapping before public smoke checks. This detects a wrong deployment or healthy old site; it does not independently prove source content or artifact equivalence (PLT-2.2, PLT-2.3).
- Production schema and data change only through the committed migration entry point, which the Vercel production build runs from the committed build configuration before the new version goes live; pull requests, CI validation and untrusted runs cannot migrate production, and production database credentials stay in provider production settings. Health checks only verify database connectivity. Submitted inputs exclude local configuration and Git history. Production secrets must not be embedded in source, artifacts or logs (PLT-2.5, PLT-2.8, PLT-2.9, PLT-2.14).
- Relaxed (#11): build-time migration adds these exposures. Committed Django code runs at build time with write access to the production database. Vercel build logs carry the migration entry point's output, limited by PLT-2.12. Any Vercel production build migrates, including a dashboard Redeploy or a use of the Vercel token outside the job, which bypasses the current-`main` check and the GitHub concurrency group; the migration lock still keeps a build of committed code from migrating alongside another run (PLT-2.14). Vercel also runs the build command, and so the migration entry point, in every preview build. In a preview build of committed code, the entry point fails without connecting to a database (PLT-2.8). A preview build of modified source, such as one submitted with the Vercel token outside the job, can drop that check, so it is stopped only by Vercel's Preview and Development environments having no `POSTGRES_*` or `DJANGO_*` variables ([operator prerequisites](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites)). Build-log and source protection must be enabled, and the [provider facts](TECHNICAL-SPEC.md#review-decisions-and-operator-prerequisites) confirmed, before deployment enablement.
- Migration compatibility is a review control: because the version in production keeps serving while and after migrating, after a failed release and after a rollback, and the schema is never rolled back, a pull request's migrations may only add tables, add nullable columns, add columns with a database default, or add indexes. Any other change is split across releases: first code that no longer needs the old shape, then a later migration. Every committed migration is atomic (PLT-2.14). Nothing checks compatibility automatically; an incompatible migration that is merged is still applied, the running version can fail until a fix is live, and rollback restores code but not schema.
- GitHub concurrency, the immediate current-`main` check and a new migrating deployment on each rerun follow [Release verification](TECHNICAL-SPEC.md#release-verification). Unknown provider or migration outcomes follow the manual procedure in [PLT-2.4](product/platform.md#plt-2-release-the-placeholder-site-to-production); the migration lock (PLT-2.14) prevents concurrent migration but does not order builds (PLT-2.6), no automatic recovery block acts before intervention, and neither automatic deployment or migration retries nor automatic rollback are allowed (PLT-2.4, PLT-2.6, PLT-2.10).
- Authenticated provider responses may contain secrets. Job logs contain only the identifiers and stage results listed in [Release verification](TECHNICAL-SPEC.md#release-verification), never full API responses, request headers, environment dumps or secret values. The migration entry point's output in the provider build log is limited to the lines in PLT-2.12 and never includes SQL, database error messages or row data. Integration verification must establish these controls before deployment enablement.
