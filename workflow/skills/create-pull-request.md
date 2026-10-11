# create-pull-request

Prepares a GitHub pull request for a finished slice.

**Input:** The slice branch, its issue, its plan, the agents' handoffs and the check results.

1. Check that the working tree is clean. If the default branch has moved, merge it into the slice branch and run the verify command again. Inspect the diff against the default branch.
2. Fill in `.github/pull_request_template.md`. Map every acceptance criterion to its test or manual check with the actual result, and list deviations and unresolved findings honestly. Leave every checkbox unticked, because only humans tick them.
3. Ask the human before pushing or creating the pull request. Without approval, give them the text and the exact commands.

**Done when:** The pull request's URL, or its ready-to-paste text, is reported with the check results.
