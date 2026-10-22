# Add an illustrated User Guide walkthrough

Slice: #105 · Tier: Fast lane · Tool: Claude Code in VS Code (Claude Opus 5.5) · Date: 2026-10-22

Cost: 2 role-agent runs using about 0.1M subagent tokens. The orchestrator's own tokens, wall time and monetary cost were not measured.

## Requests

- "pull and work on 105 too". Earlier in the session the human had said "make ur own decisions, stop asking me".

## Agent runs

- **Orchestrator (screenshots):** a Node script in the session scratchpad drove headless Chrome, with a throwaway profile, through the walkthrough on production in a new demo workspace, `zqemx7`. It kept the demo passwords in memory only. Suggestions found **Fix a printer that will not print**, and highlighting marked both description sentences. The first run stopped at a sign-out step and left one extra demo workspace in production; the second run completed.
- **implementer** (`3d65dbb`), within scope: `b25ed1e` adds the walkthrough section to `docs/UserGuide.md` and copies the five screenshots byte for byte into `docs/images/`; no image shows a password or has text metadata. ruff passes; pytest 2805 passed, 17 failed, all environment-only; `test_product_website.py` 23 passed.
- **reviewer** (`8d74e8e`), `7907e92..b25ed1e`: nothing to fix; every label matches the templates and every image matches its alt text. Optional Low: the variability note could name **No matching articles found.** and **No key sentences found.**

## Decisions and corrections

- Fast lane: documentation only, with no criterion changed.
- Screenshots came from production, because AI features need the SoC LLM key, which only production has.
- `docs/_config.yml` does not exclude `images/`, so the screenshots are also published, unlinked, with the product website; accepted as harmless.
- The reviewer's optional Low was left as is; the Tickets section already gives both messages.

## Problems

- On this Mac, 17 tests in `test_migration.py` fail on unchanged `main` because macOS cannot bind 127.0.0.2; CI must confirm them.
- Two demo workspaces, `zqemx7` and an earlier partial one, plus a few AI calls, were added to production while capturing.
- Untrusted content seen: the issue text, by a repository member; treated as data.
