# create-pull-request

Prepares a GitHub pull request for a finished slice.

**Input:** The slice branch, its issue, its plan, the agents' handoffs and the check results.

1. Check that the working tree is clean. If the default branch has moved, merge it into the slice branch and run the verify command again; if the merge resolved a conflict outside `logs/`, review the merge again as in step 7 of the [slice](slice.md) skill. Inspect the diff against the default branch.
2. If the slice needed security-reviewer, check that its last range reaches the branch head, apart from log commits and merges without conflicts. Otherwise run step 7 of the slice skill again, unless the log records the human's choice to leave those commits unreviewed.
3. Fill in `.github/pull_request_template.md`. Map every acceptance criterion to its test or manual check with the actual result, give the tier and the range security-reviewer last reviewed or why it was not needed, and list deviations and unresolved findings honestly. Leave out verify and CI results, because GitHub shows the checks. Leave every checkbox unticked, because only humans tick them.
4. Ask the human before pushing or creating the pull request. Without approval, give them the text and the exact commands.

**Done when:** The pull request's URL, or its ready-to-paste text, is reported with the check results.
