# Developer Guide

## Setup

Deskmate's architecture, routes, configuration and environments are in [`TECHNICAL-SPEC.md`](../workflow/specs/TECHNICAL-SPEC.md). To run it locally you need Python 3.14, Docker Desktop and Git Bash or PowerShell.

1. Create the virtual environment and install the pinned dependencies:

   ```bash
   python3 -m venv .venv
   source .venv/Scripts/activate      # PowerShell: .venv\Scripts\Activate.ps1
   pip install -r requirements-dev.txt
   ```

2. Copy `.env.example` to `.env`, or add its lines to an existing `.env`. Keep its database values: the tests connect with them.
3. Start PostgreSQL with `docker compose up -d db`. `docker compose down` stops it and keeps the data; `docker compose down -v` deletes the data too.
4. Run the [verify command](../AGENTS.md#commands) from the repository root.
5. Load `.env` into the shell, then start the app and open `http://localhost:8000/`:

   ```bash
   set -a; source <(tr -d '\r' < .env); set +a
   python src/manage.py runserver
   ```

   In PowerShell, load `.env` with:

   ```powershell
   Get-Content .env | ForEach-Object { if ($_ -match '^\s*([^#=\s][^=]*)=(.*)$') { Set-Item "env:$($matches[1].Trim())" $matches[2] } }
   ```

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
