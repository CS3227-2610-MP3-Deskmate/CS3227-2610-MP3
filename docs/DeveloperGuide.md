# Developer Guide

## Setup

Deskmate's architecture, routes, configuration and environments are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md). These steps are for Windows, run in Git Bash. You need Python 3.14, Docker Desktop and Git Bash.

1. Create the virtual environment with `python3 -m venv .venv` and activate it with `source .venv/Scripts/activate`. Then install the pinned dependencies with `pip install -r requirements-dev.txt`.

2. Copy `.env.example` to `.env`, or add its lines to an existing `.env`. Keep its database values: the tests connect with them.
3. Start PostgreSQL with `docker compose up -d db`. `docker compose down` stops it and keeps the data; `docker compose down -v` deletes the data too.
4. Run the [verify command](../AGENTS.md#commands) from the repository root.
5. Load `.env` into the shell, create or update the database tables, then start the app and open `http://localhost:8000/`:

   ```bash
   set -a; source <(tr -d '\r' < .env); set +a
   python src/manage.py migrate
   python src/manage.py runserver
   ```

6. To get accounts, open `http://localhost:8000/sign-in/` and press **Create demo workspace**. The page shows two Requesters' and one Support Officer's usernames and passwords once, as the [User Guide](UserGuide.md) describes. `createsuperuser` does not work, because it cannot set a role or a workspace.

## Development workflow

How we work, and what each file in `workflow/` is for, is in [`workflow/README.md`](../workflow/README.md).

### Why role scopes need a script

Claude Code and Codex can both make an agent read-only natively, so the critic and the reviewers get only read tools in Claude Code and `sandbox_mode = "read-only"` in Codex. Neither tool can limit which paths a writing agent may change (checked against both tools' documentation in October 2026):

- Claude Code's agent definitions have no path setting, and its path permission rules, such as `Edit(src/**)`, apply to the whole session rather than to one agent. The documented way to restrict one agent's paths is a pre-edit hook.
- Codex's sandbox lets an agent write anywhere in the workspace or nowhere. Hooks are its only per-agent control.

So [`check_scope.py`](../workflow/scripts/check_scope.py) reads each role's `writes` and `never_writes` lists and enforces them twice: as the pre-edit hook in both tools, and as a check the orchestrator runs after every role agent. This is what stops the implementer from weakening a test to make it pass. Its limits are listed under "How scope is enforced" in [`workflow/README.md`](../workflow/README.md).

## SoC LLM

Deskmate's AI features call SoC LLM (SoCLaaS), the school's OpenAI-compatible API. Keys and SoC's own guides are on [SoC DocHub](https://dochub.comp.nus.edu.sg/cf/guides/soclaas/start).

### Service limits (as of 12 October 2026)

- The API is reachable from outside the NUS network without the VPN.
- One student key had a $50 daily and $500 monthly allowance, with spend windows resetting at midnight UTC (8am SGT). The portal shows no request-rate or concurrency limit.
- Responses carry no rate-limit or `retry-after` headers, and a `429` can mean either a rate limit or a budget limit, so the app has to count its own calls.
- Models run on Ollama. Model names are aliases that SoC can repoint: `default` served `qwen3.6:35b`, and `qwen3.6:27b` served `qwen3.8:27b`. Use a concrete ID.

Chat models and their prices in US dollars per million tokens:

| Model | Input | Output | Context (tokens) |
| --- | --- | --- | --- |
| `llama3.1:8b` | 0.074 | 0.087 | 65,536 |
| `gemma4:26b` | 0.102 | 0.379 | 131,072 |
| `qwen3-vl:32b` | 0.104 | 0.416 | 80,000 |
| `qwen3.5:9b` | 0.114 | 0.200 | 65,536 |
| `ornith1.5:35b` | 0.200 | 1.700 | 262,144 |
| `qwen3-coder-next` | 0.210 | 1.040 | 262,144 |
| `qwen3.6:35b` | 0.412 | 1.457 | 262,144 |
| `qwen3.8:27b` | 0.425 | 2.550 | 262,144 |

### Production probe

The app has one operator-only probe, `GET /health/llm/` (PLT-3). It makes one fixed call to SoC LLM with the `llama3.1:8b` model and returns only `{"status": "ok"}` or `{"status": "error"}`.

1. Generate a token of at least 32 printable ASCII characters with a cryptographically secure random source.
2. In the Vercel project's production settings, set `SOC_LLM_API_KEY` to the SoC LLM key and `SOC_LLM_PROBE_TOKEN` to the token. Do not add either to Preview or Development. Where Vercel allows it, mark both Sensitive.
3. Deploy, then run `curl -i -H "Authorization: Bearer $SOC_LLM_PROBE_TOKEN" https://<hostname>/health/llm/` and expect `200` and `{"status": "ok"}`.
4. Record only the result, never the key or token. Rotate the token if it may have leaked.

The probe writes no database record, never retries and gives up after 10 seconds. A missing key makes it return `503`; a missing or wrong token makes it return `404`.

## AI features and the internal gateway

Every user AI call goes through one entry point, `deskmate.llm_gateway.call`, which
is specified in [`llm-gateway.md`](../workflow/specs/ai/llm-gateway.md) and implemented
in `src/deskmate/llm_gateway.py`. A feature never calls SoC LLM itself and never reads
`SOC_LLM_API_KEY`. One call does all of this in order:

1. checks its inputs and that no database transaction is open, then
2. admits the call through `deskmate.llm_limits.check_and_count`, which counts one
   attempt against the user's 10 and the app's 30 per rolling 10 minutes (PLT-5),
3. removes control, format, surrogate, private-use, unassigned and default-ignorable
   characters from the untrusted text, and rejects text over 4,000 code points,
4. sends one request with the fixed rules and the caller's fixed instructions, with the
   untrusted text as JSON in the user message,
5. checks the reply's size, strict JSON and the caller's schema, then
6. records one audit event (`success` or `failure`) and returns `ok`, `refused` or
   `error`.

The gateway is the only place that reads the key or talks to the provider. It writes
nothing to logs. Refusals and failures are returned as fixed values, so a caller keeps
its page usable; only invalid trusted input or a call inside a transaction raises.

Each feature's own contract lives in `workflow/specs/ai/` and fixes its `feature`
identifier, its exact instructions, its schema and which text it sends. That file is the
first place to read before changing a prompt, a schema or what a feature displays.

To add an AI feature:

1. Write or amend its contract in `workflow/specs/ai/`, and its acceptance criteria in
   the owning product spec.
2. Run its tests against the real gateway with the provider faked, as
   `src/deskmate/tests/test_key_sentences.py` does. No test contacts SoC LLM.
3. Keep the instructions and schema as developer-written constants. Put every user,
   ticket, article or workspace value in the untrusted text.
4. Treat checked output as untrusted: escape it, never render it as markup, and check any
   record it names against the user's own workspace.

The audit helper (`src/deskmate/llm_audit.py`) stores only a keyed user hash, a feature
label, an outcome and a timestamp, keeps 30 days, and has no readable user, prompt or
reply. The gateway is its only caller.

## Product website

See the [website design and operator prerequisites](../workflow/specs/TECHNICAL-SPEC.md#product-website) for publishing and manual Pages setup.

## Acknowledgements

The product site adapts [Arbiter's documentation site](https://github.com/CS3227-2610-MP2-Arbiter/CS3227-2610-MP2/tree/main/docs), using GitHub's [Cayman theme](https://github.com/pages-themes/cayman) and [Jekyll Pages builder](https://github.com/actions/jekyll-build-pages).

