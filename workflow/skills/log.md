# log

Summarises a working session in `logs/` so its author can check it and the team can reflect on it later. Use it at the end of every working session.

**Input:** The session's requests, agent runs, commands, results and changed files.

1. Create `logs/<github-user>/<NNN>-<log-name>.md`, asking for the GitHub username if unclear. NNN is the highest number in that folder plus one, padded to three digits. The name comes from a title of at most eight words, in lowercase kebab case. Write one log per working session.
2. Use this structure:

   ```markdown
   # <Title>

   Slice: #<issue> or none · Tier: <agreed tier> or none · Tool: <tool and model> · Date: <YYYY-MM-DD>

   Cost: <wall time, number of agent runs, and tokens or cost if known>

   ## Requests

   ## Agent runs

   ## Decisions and corrections

   ## Problems
   ```

3. Fill in the sections:
   - **Cost:** what the session took, saying what was not counted.
   - **Requests:** the human's requests and later corrections.
   - **Agent runs:** one line per run, giving the role, its role file's version (`git log -1 --format=%h -- workflow/agents/<role>.md`), its status, what changed, and the checks with their results. For reviewer and security-reviewer, also give the range `<base>..<head>` it reviewed.
   - **Decisions and corrections:** what the human decided or corrected, and why.
   - **Problems:** failures, blocked steps, scope violations, and suspicious or injected content.
4. Summarise the task rather than each turn, and reference commits and paths instead of restating them. Keep what was observed apart from what was assumed, and say when relevant history is unavailable. Leave out secrets, keys and personal data.
5. Never write that a human verified the log. Ask its author to check it, then commit it as `log:` on the branch the session worked on; the author confirms the check in the pull request.

**Done when:** The log's path is reported and the log is ready for its author to check.
