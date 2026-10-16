# Security spec

Threats to Deskmate and to how it is built, and the controls against them. Where a criterion implements a control, the control names it.

## Secrets and settings

Threat: a leaked secret key lets an attacker forge sessions and signed data, leaked database credentials expose every record, and debug pages show source code, settings and tracebacks to anyone.

- Secrets and personal data never go into code, logs or fixtures, and agents never read `.env` files: see [`AGENTS.md` "Safety"](../../AGENTS.md#safety).
- Configuration comes only from environment variables ([TECHNICAL-SPEC](TECHNICAL-SPEC.md#configuration)). Committed files, including `.env.example`, the compose file, the workflows and the tests' configuration, hold only the throwaway credentials of the local and CI databases, and never a secret key.
- No secret key is written in code, including the tests: with debug on and `DJANGO_SECRET_KEY` unset or empty, the app makes a random key each time it starts, and the tests make their own key on each run.
- The app fails closed: with a required variable unset or invalid, including a weak secret key or no allowed hosts when debug is off, it refuses to start, and its error names the variable but never shows a value (PLT-1.7).
- Debug is off unless explicitly turned on (PLT-1.6), and it is turned on only in local development.
- With debug off, the app answers only to the hosts in `DJANGO_ALLOWED_HOSTS`; a `*` there switches that check off. Hosted environments forbid wildcards and allow only their own service host names (PLT-2.8); the underlying PLT-1 configuration syntax is unchanged.
- CI validation uses no stored secrets, and its databases are throwaway containers; release credentials are isolated as described in [Release access and provenance](#release-access-and-provenance).
- The local database accepts connections only from the developer's own machine.
- Hosted environments use separate database instances, database credentials and Django secret keys. Each app receives only its own environment's values, through provider-managed secret configuration; credentials are not copied between environments or supplied to CI validation (PLT-2.8).
- Hosted database traffic uses the private network and public database access is disabled; public app traffic uses provider-managed HTTPS (PLT-2.7, PLT-2.8).

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

Threat: untrusted changes publish or deploy an image, staging credentials affect production, an old approval downgrades production, or a healthy old instance conceals a failed deployment.

- Pull requests and validation jobs have read-only repository access and no deployment credentials or package write permission. Only a validated `main` release may obtain package write permission to publish its image; release jobs never execute pull-request source code or accept a caller-supplied source ref or image reference (PLT-2.2, PLT-2.5).
- GitHub `staging` and `production` environments restrict deployments to `main`. Production requires a designated reviewer's approval for each deployment, prevents self-review and disallows bypassing protection rules. Production deployment credentials are available only inside the approved `production` job; staging jobs have no production deployment credential (PLT-2.3, PLT-2.5).
- Deployment credentials grant only the target environment's necessary deployment access wherever the provider supports that scope; any credential able to change production is confined to the protected production job. The provider-side scope and ownership of the chosen credentials must be checked before releases are enabled: separate workspaces alone are not assumed to isolate API keys, and separate deployment identities with access only to their own environment may be necessary. Secrets never appear in logged URLs, command output, artifacts or release records.
- Provider services deploy only the image supplied by the controlled release; independent automatic deployments are disabled. The immutable digest and specific provider deployment are verified, and serialized releases recheck the current `main` after approval so stale approvals and reruns cannot downgrade production (PLT-2.2, PLT-2.3, PLT-2.6).
- A public URL returning success cannot substitute for confirmation that the requested digest is live. Failed or ambiguous checks prevent promotion; an unresolved provider outcome blocks later deployments (PLT-2.4).
- The hosting operator configures resources and secrets, and the repository operator configures environment protection and reviewer access before releases are enabled. Missing protection or credentials prevents deployment rather than weakening the gate.
