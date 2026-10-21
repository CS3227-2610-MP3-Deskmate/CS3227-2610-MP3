# Run the agent handoff experiment

Slice: none · Tier: none · Tool: Codex (orchestrator model ID not exposed), with the experiment models below; slide rewrite in Claude Code in VS Code (`claude-opus-5-5`) · Date: 2026-10-19, with the slide rewrite continuing to 2026-10-20

Cost: 85 logical scored agent runs and 110 native model calls. Their recorded call span was 16:38–18:12 SGT, about 94 minutes including gaps and pacing. This is not total active work time. Preparation, practice, excluded attempts, failed infrastructure calls, presentation work, Git operations and the orchestrator are outside that run count. Overall wall time, tokens and subscription cost were not aggregated. The slide rewrite was one Claude Code session from about 23:10 to 01:00 SGT, estimated from file and commit times and including the human's review gaps. It used no subagents, and its tokens were not counted.

## Requests

- Read the [experiment proposal](../../experiments/agent-handoff-2026-10-19/setup-original.md), assess feasibility and run a subscription-based comparison of Sol, Luna, Opus and Sonnet handoffs.
- Use the existing Claude Pro sign-in. The human accepted audited OpenAI sessions and chose Opus for the fixed coding and receiving roles.
- Explain whether the results were averages, then add two Opus coding histories and their complete paired handoff/quiz comparisons.
- Produce a minimalist presentation using the lecture notes' terminology, publish the experiment on an origin branch, switch this workspace to that branch and use the log skill.
- Rewrite the slides for an audience new to the material: plain words aligned with the lecture's terms, the proposal's flow, an explicit motivation, and diagrams instead of dense text.
- Correction: the presenter reads straight off the slides without speaker notes, so the slide text must carry the whole talk. Later points: reword the title question as "x vs y", say "next agent", replace the unclear workflow cycle, introduce the setup before naming the coding agent, clarify which token the bug concerns, use consistent box colours, state that GPT leaned free-form and Claude leaned checklist, and show only five-run totals in the backup table.
- Further review rounds asked for:
  - plainer wording, such as "all subsequent agents", "retain context", "follow all other documented rules" and "that specific run";
  - numerals for counts, the SoC LLM provider named, and a clearer name for the cut-off-reply bug;
  - labelled handoff boxes on the setup slide, the shared topic list on the question slide, and 136 shown as a five-run total;
  - a note that the stronger model in each family scored higher;
  - clearer limitations wording, an isolation and audit point on the fair-test slide, and removal of the Result 1 caveat box, the late-run mentions, the results-ZIP pointer and the "Recall first" label.
- The human asked whether the 200-word limit explained the lost success rules.
- Commit the slides and update this log, after the first rewrite and again after the final review round.

## Agent runs

The [results bundle](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Experiment_Expanded_Results.zip) is the evidence home. Paths in this section refer to its extracted contents. Its `report.html` records the method and limitations. The initial setup and first three histories are reconstructed here from retained evidence and the conversation summary; the full earlier orchestrator transcript is not in the current context.

These experiment agents use frozen experiment prompts rather than `workflow/agents/` roles, so role-file versions are N/A. No workflow reviewer or security-reviewer ran, and no formal review range applies. Coding and receiving use `claude-opus-5-5`; the handoff model varies. The final client-visible audit covers all 110 scored calls with no forbidden native events or incomplete evidence. This does not prove backend tool isolation.

- Orchestrator — role file/version N/A, done: prepared isolated inputs, harness, keys and scoring; produced the report, evidence archive and presentation; published `9cca7f1` on `experiment/agent-handoff-2026-10-19` from `47164d9`, then switched the main workspace to it. The original slide files opened and rendered in PowerPoint, with two native charts, five native tables, speaker notes and no final text-fit findings. Those checks do not cover the later restyle `e5d2342` or the rewrites `76d8ec9` and `d5b25c9`.
- Slide rewrite (Claude Code orchestrating session) — role file/version N/A, done: replaced every slide and note in [the deck](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Results.pptx) and its [PDF](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Results.pdf) in `76d8ec9`, then revised them after further review in `d5b25c9`. It kept the existing theme, master and both native charts. The result is 12 main slides and 2 backups. Checks are listed under Artifact and publication checks.

### Coding agents

Each run changed only its isolated `llm.py`; final patches and supplied histories are in `evidence/<run>/`. All use the same starting code, contract and standalone suite. The baseline produced five test failures and four errors, while the private reference passed all 30. The test environment simulated HTTP and time, without a live provider or deployment.

| Run | Status | Recorded result |
| --- | --- | --- |
| coding-01 | done | Only isolated `llm.py` changed, 6 turns, all 30 offline tests passed |
| coding-02 | done | Only isolated `llm.py` changed, 6 turns, all 30 offline tests passed |
| coding-03 | done | Only isolated `llm.py` changed, 6 turns, all 30 offline tests passed |
| coding-04 | done | Only isolated `llm.py` changed, 6 turns, all 30 offline tests passed |
| coding-05 | done | Only isolated `llm.py` changed, 6 turns, all 30 offline tests passed |

### Handoff agents

Each row is a fresh handoff run, done, with role-file version N/A. Its change is the saved `evidence/<run>/<model>/<format>/handoff.txt`. The same history and content instructions apply to both formats. Word counts include labels. Every listed run passed the final client-visible native-tool audit, including the OpenAI exception described below.

| Run / handoff model / format | Words | At most 200 |
| --- | ---: | --- |
| coding-01 / `gpt-5.6-sol` / prose | 172 | yes |
| coding-01 / `gpt-5.6-sol` / checklist | 158 | yes |
| coding-01 / `gpt-5.6-luna` / prose | 110 | yes |
| coding-01 / `gpt-5.6-luna` / checklist | 132 | yes |
| coding-01 / `claude-opus-5-5` / prose | 200 | yes |
| coding-01 / `claude-opus-5-5` / checklist | 218 | no |
| coding-01 / `claude-sonnet-5-5` / prose | 151 | yes |
| coding-01 / `claude-sonnet-5-5` / checklist | 202 | no |
| coding-02 / `gpt-5.6-sol` / prose | 170 | yes |
| coding-02 / `gpt-5.6-sol` / checklist | 156 | yes |
| coding-02 / `gpt-5.6-luna` / prose | 100 | yes |
| coding-02 / `gpt-5.6-luna` / checklist | 98 | yes |
| coding-02 / `claude-opus-5-5` / prose | 199 | yes |
| coding-02 / `claude-opus-5-5` / checklist | 241 | no |
| coding-02 / `claude-sonnet-5-5` / prose | 175 | yes |
| coding-02 / `claude-sonnet-5-5` / checklist | 212 | no |
| coding-03 / `gpt-5.6-sol` / prose | 172 | yes |
| coding-03 / `gpt-5.6-sol` / checklist | 170 | yes |
| coding-03 / `gpt-5.6-luna` / prose | 106 | yes |
| coding-03 / `gpt-5.6-luna` / checklist | 102 | yes |
| coding-03 / `claude-opus-5-5` / prose | 203 | no |
| coding-03 / `claude-opus-5-5` / checklist | 217 | no |
| coding-03 / `claude-sonnet-5-5` / prose | 175 | yes |
| coding-03 / `claude-sonnet-5-5` / checklist | 209 | no |
| coding-04 / `gpt-5.6-sol` / prose | 167 | yes |
| coding-04 / `gpt-5.6-sol` / checklist | 159 | yes |
| coding-04 / `gpt-5.6-luna` / prose | 127 | yes |
| coding-04 / `gpt-5.6-luna` / checklist | 107 | yes |
| coding-04 / `claude-opus-5-5` / prose | 202 | no |
| coding-04 / `claude-opus-5-5` / checklist | 226 | no |
| coding-04 / `claude-sonnet-5-5` / prose | 174 | yes |
| coding-04 / `claude-sonnet-5-5` / checklist | 205 | no |
| coding-05 / `gpt-5.6-sol` / prose | 171 | yes |
| coding-05 / `gpt-5.6-sol` / checklist | 160 | yes |
| coding-05 / `gpt-5.6-luna` / prose | 128 | yes |
| coding-05 / `gpt-5.6-luna` / checklist | 122 | yes |
| coding-05 / `claude-opus-5-5` / prose | 214 | no |
| coding-05 / `claude-opus-5-5` / checklist | 249 | no |
| coding-05 / `claude-sonnet-5-5` / prose | 155 | yes |
| coding-05 / `claude-sonnet-5-5` / checklist | 183 | yes |

### Receiving agents

Each row is a separate, fresh Opus receiving run, done, with role-file version N/A. Its change is `evidence/<run>/<handoff-model>/<format>/answers.json`. It saw only one handoff and the six questions. Each final client-visible audit passed. Scores below concern frozen expected facts; additional false or ambiguous claims are recorded separately in `observations.json`.

| Run / handoff model / format | Correct | Not stated | Wrong |
| --- | ---: | ---: | ---: |
| coding-01 / `gpt-5.6-sol` / prose | 14 | 13 | 0 |
| coding-01 / `gpt-5.6-sol` / checklist | 14 | 13 | 0 |
| coding-01 / `gpt-5.6-luna` / prose | 10 | 17 | 0 |
| coding-01 / `gpt-5.6-luna` / checklist | 12 | 15 | 0 |
| coding-01 / `claude-opus-5-5` / prose | 15 | 12 | 0 |
| coding-01 / `claude-opus-5-5` / checklist | 16 | 11 | 0 |
| coding-01 / `claude-sonnet-5-5` / prose | 15 | 12 | 0 |
| coding-01 / `claude-sonnet-5-5` / checklist | 14 | 13 | 0 |
| coding-02 / `gpt-5.6-sol` / prose | 16 | 11 | 0 |
| coding-02 / `gpt-5.6-sol` / checklist | 11 | 16 | 0 |
| coding-02 / `gpt-5.6-luna` / prose | 13 | 14 | 0 |
| coding-02 / `gpt-5.6-luna` / checklist | 12 | 15 | 0 |
| coding-02 / `claude-opus-5-5` / prose | 16 | 11 | 0 |
| coding-02 / `claude-opus-5-5` / checklist | 16 | 11 | 0 |
| coding-02 / `claude-sonnet-5-5` / prose | 15 | 12 | 0 |
| coding-02 / `claude-sonnet-5-5` / checklist | 15 | 12 | 0 |
| coding-03 / `gpt-5.6-sol` / prose | 17 | 11 | 0 |
| coding-03 / `gpt-5.6-sol` / checklist | 17 | 11 | 0 |
| coding-03 / `gpt-5.6-luna` / prose | 12 | 16 | 0 |
| coding-03 / `gpt-5.6-luna` / checklist | 13 | 15 | 0 |
| coding-03 / `claude-opus-5-5` / prose | 17 | 11 | 0 |
| coding-03 / `claude-opus-5-5` / checklist | 18 | 10 | 0 |
| coding-03 / `claude-sonnet-5-5` / prose | 15 | 13 | 0 |
| coding-03 / `claude-sonnet-5-5` / checklist | 16 | 12 | 0 |
| coding-04 / `gpt-5.6-sol` / prose | 16 | 11 | 0 |
| coding-04 / `gpt-5.6-sol` / checklist | 15 | 12 | 0 |
| coding-04 / `gpt-5.6-luna` / prose | 15 | 12 | 0 |
| coding-04 / `gpt-5.6-luna` / checklist | 12 | 15 | 0 |
| coding-04 / `claude-opus-5-5` / prose | 14 | 13 | 0 |
| coding-04 / `claude-opus-5-5` / checklist | 13 | 14 | 0 |
| coding-04 / `claude-sonnet-5-5` / prose | 14 | 13 | 0 |
| coding-04 / `claude-sonnet-5-5` / checklist | 14 | 13 | 0 |
| coding-05 / `gpt-5.6-sol` / prose | 15 | 12 | 0 |
| coding-05 / `gpt-5.6-sol` / checklist | 16 | 11 | 0 |
| coding-05 / `gpt-5.6-luna` / prose | 14 | 13 | 0 |
| coding-05 / `gpt-5.6-luna` / checklist | 13 | 14 | 0 |
| coding-05 / `claude-opus-5-5` / prose | 16 | 11 | 0 |
| coding-05 / `claude-opus-5-5` / checklist | 16 | 11 | 0 |
| coding-05 / `claude-sonnet-5-5` / prose | 15 | 12 | 0 |
| coding-05 / `claude-sonnet-5-5` / checklist | 16 | 11 | 0 |

### Artifact and publication checks

- `verify_expanded.py` passed: original report/ZIP and original judgments preserved, all 253 exported hashes matched, 1,088 unique fact rows, before/after totals, observations, report links, SVG parsing, ZIP CRC and temporary sign-in cleanup.
- Presentation package-integrity and layout validators passed for the originally delivered deck, and `verify_deck.py` matched chart values, embedded workbook cells, exact excerpts and notes against the source evidence. All 12 slides rendered in Microsoft PowerPoint. These checks predate the later restyling.
- For `76d8ec9` and again for `d5b25c9`: PowerPoint opened the generated package without a repair prompt, re-saved it and exported 14 PDF pages. A font-metric fit check reported no overflow, and every changed slide's render was inspected. `verify_deck.py` was not rerun. Slide figures and quotes were checked by hand against `model-format-results.json`, `question-results.json`, `word-counts.json`, `source-lengths.json`, `fact-scores.json`, `cli-audit.json` and the quoted `evidence/` files. In `d5b25c9`, the read-aloud text (titles, leads and highlighted lines) is about 630 words.
- `verify_publication.py` passed on the original publication set: five files, archive CRC, all evidence hashes, credential-path exclusions, source-identical ZIP/slides and README links. `git diff --cached --check` passed before `9cca7f1`, and the pushed origin ref matched that commit.
- No application repository code changed in this work. The application verify command was not rerun for the archive, slide, branch or log steps. Apart from the `76d8ec9` and `d5b25c9` checks above, the original checks do not cover the rewritten slides.

## Decisions and corrections

- The native ChatGPT subscription client did not accept the initially requested GPT-6.1 Sol/GPT-6 Luna IDs. The actual frozen handoff models were `gpt-5.6-sol`, `gpt-5.6-luna`, `claude-opus-5-5` and `claude-sonnet-5-5`. OpenAI throttling contributed to the human choosing fixed Opus coding and receiving roles. Providers' medium effort does not establish equal compute, and their clients did not expose temperature.
- The human accepted the explicit OpenAI exception: native tools remained exposed, models were instructed not to use them, and client events were audited. Claude native tools were disabled. The coding harness separately permitted only assigned reads, an `llm.py` write and a fixed offline test action.
- Corrected source-history rendering to preserve the coding agent's visible output faithfully, then regenerated every affected handoff. Closing handoff/finish output stayed outside the supplied history.
- Clarified full-quiz semantic grading during the original unblinded review: explicit facts anywhere in the answers or their quotes receive credit, with cross-question locations and support issues recorded. Retained that policy for the extension and left the original labels unchanged.
- The answer keys use only each supplied history. New keys were frozen before their handoffs. The added histories were requested after the initial results, so the expanded study is exploratory. Results are pooled facts across shared histories, rather than averages or repeated quizzes of one identical history.
- The comparison showed no consistent checklist advantage. Detailed results, word-budget sensitivity and claim observations remain in the bundle's report. The presentation connects this to Context Engineering, Context Compaction and Recall First, with Structured Note Taking and Just-in-Time Retrieval labelled as untested follow-ups. The receiving quiz is not a generator-verifier feedback loop.
- Kept inference/runtime files outside the app repository and published the existing shareable evidence ZIP with the proposal, README, PowerPoint and PDF. Used a separate publication worktree to preserve the security-review branch. Detached that clean worktree before switching this workspace to the experiment branch.
- No matching experiment issue existed. The human explicitly chose to omit the issue reference for this experiment's commit. No pull request or merge was requested or performed.
- Slide rewrite: speaker notes hold only background for questions and sources, without local paths or reference filenames. The slides name the models actually used. At the human's request, no slide now mentions the departures from the proposal: Opus instead of GPT-6.1 Sol for the coding and receiving roles, and runs 4 and 5 added after the first results. They remain in the speaker notes, this log and `report.html`.
- Claude proposed the motivation slide. It ties the experiment to the MP3 role-agent chain in `workflow/skills/slice.md`, whose `AGENTS.md` handoff block has the same fields as the experiment's checklist. Its goal line comes from the proposal's synopsis. The human later asked for wording changes to it and did not ask to remove it.
- At the human's request, Result 1 says GPT models leaned free-form and Claude models leaned checklist, with every gap at most 5 of 136 facts. The human then removed its caveat box. The over-length Claude checklists stay on the limitations slide, and Luna's flip appears only in the notes. A note added at the human's request says the stronger model in each family scored higher in both formats: Sol over Luna by 11 to 14 facts, and Opus over Sonnet by 4.
- On the human's question about the 200-word limit, the data do not support it as the cause. The 12 over-length handoffs kept 2 of their 108 success-rule facts, against 2 of 252 for the rest. Result 2 now gives likely reasons instead: none of the 7 prompt topics asks for these rules, and they were not among the 5 bugs.
- The limitations slide replaced the late-run item with one reader model: Claude Opus 5.5 read every handoff, which may suit Claude-written handoffs. The takeaway states the recall-first principle without naming it. Claude added "so some marks may be wrong" to the AI-grading item to say why it limits the result.
- Claude's reading of the evidence, not part of the frozen scoring or `report.html`: nearly all 20 free-form handoffs still label each requested part inline. The handoff texts almost never list the success criteria, so those facts were lost at the writing step. No handoff kept the recorded reason for a total deadline rather than a per-socket timeout, though 35 of 40 kept the 10-second limit.

## Problems

- OpenAI subscription calls intermittently returned 429 errors. Infrastructure retries retained inputs, and model-ID availability differed from the initial proposal. No final scored condition remained incomplete.
- Initial transcript normalization displaced Markdown/JSON fences. Eight preliminary handoffs were preserved and excluded before receiving quizzes; questions and fact inventories stayed unchanged.
- An extension starter retained an already-imported replay serializer. Three reads completed before its write request was cancelled without a repair. The partial attempt was archived and excluded before scored handoffs. A fresh process used the corrected serializer, and all 30 valid coding requests reconstructed exactly.
- Twelve handoffs exceeded the word budget. Outputs were preserved without content-quality retries. One task, five shared histories, unblinded AI grading, fixed Opus roles and tool-exposure differences limit interpretation. The standalone tests do not establish live-provider or production timing guarantees.
- The live slide service and supplied JavaScript presentation runtime were unavailable. The first Office XML package failed to open in PowerPoint, and native chart insertion also failed. Used a PowerPoint-authored slide package with editable chart/workbook parts, repaired automatic text-box sizing and validated the final original delivery. A PDF export COM call failed and was replaced with PowerPoint's PDF save route. No dependencies were installed.
- When the Codex part of this log was written, HEAD was the slide-restyling commit `e5d2342`, whose prompts and checks are not recorded here. The slide binaries also held the Claude Code session's first rewrite, which was revised and committed as `76d8ec9`.
- The rewrite environment had no pptxgenjs, python-pptx or markitdown. Under the no-install rule, a standard-library generator kept outside the repository wrote the deck, and PowerPoint rendered it. Arial has no non-breaking hyphen, so lines that split "65,536-byte" and "GPT-6.1" were reworded or broken by hand.
- The first rewrite put the talk's script in speaker notes. The human corrected that the slides are read directly, so the second rewrite moved the script onto the slides.
- `76d8ec9`'s backup slide and setup notes said the handoff and receiving agents had no tools. Only the Claude sessions had none. The OpenAI handoff sessions kept their built-in tools under the agreed exception, and the audit found none used. Claude found and corrected this in `d5b25c9`.
- Sandbox checks sometimes could not read the global Git ignore file, inspect background processes or access the external worktree under its owner. Scoped checks rerun with the required permissions succeeded. A GitHub CLI quoting error was corrected without changing repository settings.
- Source files, lecture notes, test payloads and model outputs were treated as data. No out-of-scope directive was followed or native forbidden tool event recorded. No secrets or private reference repair were included in the publication set.
