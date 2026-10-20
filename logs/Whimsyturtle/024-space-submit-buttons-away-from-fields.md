# Space submit buttons away from fields

Slice: #72 · Tier: Fast lane · Tool: Claude Code (cloud session; model not recorded) · Date: 2026-10-20

Cost: Two role-agent runs, about 67,500 subagent tokens and 7 minutes of agent time, as the tool reported them. The orchestrating session's own tokens and total wall time were not measured.

## Requests

- Set up the cloud container (start PostgreSQL, copy `.env.example` to `.env`, create `.venv` with Python 3.14 and install `requirements-dev.txt`), then run the `slice` skill for issue #72, which reports that the submit buttons on `/sign-in/` and `/support/reset-requester-password/` touch the field above them (PLT-4.2, no criterion change).

## Agent runs

- **implementer**, fast-lane change (`3d65dbb`): done; `d8e3441` adds one rule to the shared style in `src/deskmate/templates/deskmate/base.html`, giving a button directly after a visible input or textarea a 0.75rem top margin, the labels' top margin. Hidden inputs are excluded so the CSRF-only "Create demo workspace" and "Sign out" forms keep their layout. Writer verify: Ruff/format clean, 2,011 passed. Root scope check passed; root verify: Ruff/format clean, 2,011 passed.
- **reviewer** (`8d74e8e`): needs-decision; reviewed `abcdbc2..d8e3441`. No code findings. Medium (process): bug fixes sit in the Standard row of the tier table, so Fast lane needed the human's explicit confirmation. Low: PLT-4.2 and PLT-4.3 are manual and unchecked. Low, no change recommended: buttons on `form.as_p` pages sit about 16px below the field, against 12px here, the same difference that already existed between field and label gaps. Note: `textarea + button` matches no current template. It ran no commands and relied on the recorded check results. It agreed that step 7 does not require security-reviewer.

## Decisions and corrections

- The human chose the Fast lane, as the issue proposed. After the reviewer's tier finding, which the first question had not raised, the human confirmed the Fast lane for this presentation-only fix, with PLT-4.2 and PLT-4.3 listed as manual checks.
- The human chose the branch `72-button-spacing`, following the slice skill, over the branch the cloud session was preset to.
- Security-reviewer was not run: the slice changes no route, role or workspace check, scoped query or devops file.
- The counted `src/` diff is 1 insertion, within the 400-line budget.
- Root rendered both pages in headless Chromium at 1280px on the local dev server: "Sign in" and "Reset password" each sit 12px below their field, and "Create demo workspace" keeps a 0px top margin. This is root's observation, not the manual check; narrow windows and the `form.as_p` pages were not rendered.

## Problems

- The local PostgreSQL had no `deskmate` role, so the baseline verify failed with 1,684 errors and 1 failure, all `password authentication failed`. Root created the throwaway role and database with the `.env.example` credentials, and the baseline then passed: 2,011 tests.
- Root's `pkill -f` to stop the dev server matched its own shell, ending the command before the commit ran. Root checked that nothing was committed and committed again.
- Root's verify run on the change added `-p no:cacheprovider` to pytest; the implementer's run used the plain command.
- No suspicious or injected content was seen.
