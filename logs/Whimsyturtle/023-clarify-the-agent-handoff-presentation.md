# Clarify the agent handoff presentation

Slice: none · Tier: none · Tool: Codex (exact model ID not exposed) · Date: 2026-10-20

Cost: One orchestrating session, with no subagents or new experiment runs. Artifact timestamps place slide editing at approximately 22:06–22:47 SGT, including the human's review gaps. Earlier discussion and the final log and commit work are outside that estimate. Total active time, tokens and subscription cost were not aggregated.

## Requests

- Read the experiment branch without changing the active `20-llm-guards` branch, and explain why the presentation emphasises which provider replies count as a success.
- Reconsider the finding because the handoff prompt requested changes and checks but did not explicitly request those response rules. Keep the example while correcting its interpretation.
- Edit only the necessary slide text, preserve the design, and use the same plain English as the other slides.
- Remove the confusing sentence about not testing why agents left out the rules; restore the stronger takeaway about a handoff covering its requested topics while leaving out facts the next agent is asked about.
- Make slide 9's explanation box smaller, call it `Likely reason`, and label slide 12's proposed experiments `POTENTIAL FOLLOW-UP EXPERIMENTS`.
- Check what `fresh copy` meant in the runner, clarify slide 14, then commit the updated slides and session log together.

## Agent runs

- Codex orchestrator — role file/version N/A, done: inspected the [experiment evidence](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Experiment_Expanded_Results.zip), revised the [PowerPoint](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Results.pptx) and [PDF](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Results.pdf), and wrote this log in a separate worktree on `experiment/agent-handoff-2026-10-19`, based on `4ec53f0`. No role agents, reviewers or security-reviewers ran; no review range applies.

Checks actually run:

- The installed PowerPoint opened the edited deck, rendered all 14 slides and exported the matching PDF. The Windows PDF renderer opened and rendered all 14 exported pages. Each edited page was inspected visually after its final change.
- Standard-library ZIP and XML checks verified each targeted edit. Final package comparison against `4ec53f0`'s saved deck found changes only in slides 9, 12 and 14 and the notes for slides 9 and 12; all other 95 parts were byte-identical. Final PDF page renders differed from the starting PDF only on pages 9, 12 and 14.
- `inspect_presentation_package_integrity.py --fail-on-findings` passed on the saved final deck: 14 slides, 2 charts and no findings.
- `inspect_presentation_layout_geometry.py --expected-slide-count 14 --expected-slide-size-emu 12192000,6858000 --validate-heading-fit --validate-bullet-geometry --fail-on-findings` passed on the saved final deck, with no findings or warnings.
- PowerPoint's text-bound measurements showed no overflow in the edited boxes. Two small horizontal overhangs on unchanged slides 11 and 13 were already present; they were left outside this request's scope.
- `git diff --check` passed after saving the revisions. The application verify command was not run because no application code changed. The experiment, its grading and the earlier `verify_deck.py` and `verify_publication.py` scripts were not rerun.

## Decisions and corrections

- The [earlier experiment log](022-run-the-agent-handoff-experiment.md) remains the record of the original runs and previous slide rewrites. This session changed the presentation, not the evidence archive, prompts, answer keys, scores or recorded model outputs.
- Kept the success-response example and its figures. The slides now distinguish the missing information from an explanation for its absence: changes and checks were requested, while the rules tested by the quiz were not explicitly requested. This does not establish that handoff writers generally prefer changed information over unchanged requirements. The word-budget observations also do not isolate what caused the omissions.
- The quiz tested what the receiving agent could recover, and the experiment compared two formats. It did not compare prompts that asked for these response rules or test whether their absence harmed later coding. The broad sentence `We didn’t test why the agents left them out` was removed from slide 9; the takeaway retains the relevant limit on later coding.
- The first rewrite was too abstract. After the human's correction, restored the original takeaway title and used shorter, spoken sentences. A further correction restored the main finding as slide 12's highlighted point instead of leaving only generic advice about what to request.
- Retained the example on slide 10 unchanged. Slide 9's box now fits its shorter text, and slide 12 identifies adding a field and looking up the contract as potential follow-up experiments rather than tested improvements.
- Checked `coding()` in the archived `runner-source/run.py`: a new coding run creates its own `workspaces/<run_id>` folder and copies `llm.py`, `llm-health.md` and `test_probe.py` from the same baseline. Slide 14 now states that each coding run had its own folder with the same starting code, requirements and tests.
- All tracked changes stayed in the experiment branch's separate worktree. The active workspace remained on `20-llm-guards` with no tracked edits. The human requested one local commit containing this log and both slide files; no push, pull request or merge was requested.

## Problems

- The bundled JavaScript presentation package was unavailable. Used targeted edits to the existing Office XML package, preserving its theme, masters, fonts, charts and other existing objects; rendered with the installed PowerPoint. No dependency was installed.
- The first draft introduced stiff wording and displaced the stronger finding with generic advice. Both were corrected after the human's feedback.
- Git worktree creation and PowerPoint startup initially failed inside the sandbox. Scoped escalations succeeded without changing the active branch. A first PDF save failed with a forward-slash output path; using a native Windows path succeeded.
- The Windows PDF helper initially stayed alive after writing its rendered pages. Only those completed helper sessions were stopped; the helper was then corrected to exit after rendering.
- Read-only network attempts were unavailable, so source inspection used the local experiment ref and the evidence bundle. Git also warned that it could not read the global ignore file; repository operations otherwise completed.
- Archived runner prompts, code and model outputs were treated as evidence, not new instructions. No embedded directive was followed. No secrets or private reference repair were read or added to the commit.
