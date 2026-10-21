# Check progress, fix fast lane, test SoC LLM

Slice: none · Tool: Claude Code (Claude Opus 5.5) · Date: 2026-10-12

Cost: One session with no role-agent runs; wall time, tokens and monetary cost were not measured.

## Requests

- Read the local reference files and the repository, and say what is next.
- After the human added the devops role (`3d65dbb`) and excluded the local files in `.git/info/exclude`, re-read the repository. Say whether a forum answer changes the deployment question: in it, the professor approved another team's cloud hosting, with deploys run by that team's own GitHub Actions.
- The human reported that SoC LLM answered with a "missing bearer token" error from outside the NUS network, without the VPN.
- Explain the "fast-lane gap", fix it and stage the fix. The human committed it as `d1ccc61`.
- Give step-by-step instructions, from the local copies of SoC's SoCLaaS guides, to get a key and check its budget. Then help load `.env`, list the models and send a test request.
- Record the findings in a committed document for the teammate. The human decided that facts we measured may be committed.
- Corrections: drop the key setup steps, since graders will not use their own keys; title the section "Service limits"; drop the cost-estimate bullet as irrelevant.

## Agent runs

No role agents or subagents ran; Claude worked directly.

- `workflow/skills/slice.md` and `workflow/agents/devops.md`: the fast lane allows one devops run, and security-reviewer runs whenever devops changed files, in the Standard tier and the fast lane too. `python3 -m unittest discover -s workflow/scripts` passed 37 tests. The human committed it as `d1ccc61`.
- `docs/DeveloperGuide.md`: a "SoC LLM" section with the service limits seen on 12 October and the chat models' prices. Both links returned 200. The human committed it as `ac3cdd8`.
- Other checks: `check_scope.py implementer --base HEAD` failed on the seven local files before they were excluded, and `check_scope.py devops --base HEAD` passed after. An unauthenticated request to `/v1/models` from this machine returned 401. The Git Bash `.env` loader worked on a dummy file with Windows line endings.

## Decisions and corrections

- Hosting: a third-party cloud host is allowed when our GitHub Actions runs the deploys, so the team will not ask on the forum. Keep any host auto-deploy off. The host is not chosen yet.
- SoC LLM is reachable from outside NUS, so a cloud host should reach it; the skeleton's first production call will confirm it.
- From the human's tests: a $50 daily and $500 monthly allowance per key, no rate-limit headers, models served by Ollama, and model aliases that point at other models. Details are in the Developer Guide.
- Keys: Claude recommended storing the production key only as the GitHub `production` environment secret, with the teammate using their own key for development and staging. Not decided.

## Problems

- The untracked local files made the scope check fail and broke the slice skill's clean-tree rule until the human excluded them.
- The Git Bash `.env` loader failed in PowerShell. Claude gave Git Bash and PowerShell alternatives.
- The `.claude/settings.json` deny rule stopped Claude from listing `.env` to check that Git ignores it. It was not worked around.
- Unresolved: SoC LLM's request-rate limit. The portal does not show it, responses carry no rate-limit headers, and the human cannot reach `stu` to run `soclaas-portal -h`.
