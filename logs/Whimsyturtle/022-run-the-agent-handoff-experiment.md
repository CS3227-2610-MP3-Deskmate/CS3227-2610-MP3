# Run the agent handoff experiment

Slice: none · Tier: none · Tool: Codex (orchestrator model ID not exposed), with the experiment models below · Date: 2026-10-19

Cost: 85 logical scored agent runs and 110 native model calls. Their recorded call span was 16:38–18:12 SGT, about 94 minutes including gaps and pacing. This is not total active work time. Preparation, practice, excluded attempts, failed infrastructure calls, presentation work, Git operations and the orchestrator are outside that run count. Overall wall time, tokens and subscription cost were not aggregated.

## Requests

- Read the [experiment proposal](../../experiments/agent-handoff-2026-10-19/setup-original.md), assess feasibility and run a subscription-based comparison of Sol, Luna, Opus and Sonnet handoffs.
- Use the existing Claude Pro sign-in. The human accepted audited OpenAI sessions and chose Opus for the fixed coding and receiving roles.
- Explain whether the results were averages, then add two Opus coding histories and their complete paired handoff/quiz comparisons.
- Produce a minimalist presentation using `CS3227 Notes.md` terminology, publish the experiment on an origin branch, switch this workspace to that branch and use the log skill.

## Agent runs

The [results bundle](../../experiments/agent-handoff-2026-10-19/Agent_Handoff_Experiment_Expanded_Results.zip) is the evidence home. Paths in this section refer to its extracted contents. Its `report.html` records the method and limitations. The initial setup and first three histories are reconstructed here from retained evidence and the conversation summary; the full earlier orchestrator transcript is not in the current context.

These experiment agents use frozen experiment prompts rather than `workflow/agents/` roles, so role-file versions are N/A. No workflow reviewer or security-reviewer ran, and no formal review range applies. Coding and receiving use `claude-opus-5-5`; the handoff model varies. The final client-visible audit covers all 110 scored calls with no forbidden native events or incomplete evidence. This does not prove backend tool isolation.

- Orchestrator — role file/version N/A, done: prepared isolated inputs, harness, keys and scoring; produced the report, evidence archive and presentation; published `9cca7f1` on `experiment/agent-handoff-2026-10-19` from `47164d9`, then switched the main workspace to it. The original slide files opened and rendered in PowerPoint, with two native charts, five native tables, speaker notes and no final text-fit findings. Later slide edits described under Problems were not covered by those checks.

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
- `verify_publication.py` passed on the original publication set: five files, archive CRC, all evidence hashes, credential-path exclusions, source-identical ZIP/slides and README links. `git diff --cached --check` passed before `9cca7f1`, and the pushed origin ref matched that commit.
- No application repository code changed in this work. The application verify command was not rerun for the archive, slide, branch or log steps. This log records prior observed checks rather than asserting the currently edited slides passed them.

## Decisions and corrections

- The native ChatGPT subscription client did not accept the initially requested GPT-6.1 Sol/GPT-6 Luna IDs. The actual frozen handoff models were `gpt-5.6-sol`, `gpt-5.6-luna`, `claude-opus-5-5` and `claude-sonnet-5-5`. OpenAI throttling contributed to the human choosing fixed Opus coding and receiving roles. Providers' medium effort does not establish equal compute, and their clients did not expose temperature.
- The human accepted the explicit OpenAI exception: native tools remained exposed, models were instructed not to use them, and client events were audited. Claude native tools were disabled. The coding harness separately permitted only assigned reads, an `llm.py` write and a fixed offline test action.
- Corrected source-history rendering to preserve the coding agent's visible output faithfully, then regenerated every affected handoff. Closing handoff/finish output stayed outside the supplied history.
- Clarified full-quiz semantic grading during the original unblinded review: explicit facts anywhere in the answers or their quotes receive credit, with cross-question locations and support issues recorded. Retained that policy for the extension and left the original labels unchanged.
- The answer keys use only each supplied history. New keys were frozen before their handoffs. The added histories were requested after the initial results, so the expanded study is exploratory. Results are pooled facts across shared histories, rather than averages or repeated quizzes of one identical history.
- The comparison showed no consistent checklist advantage. Detailed results, word-budget sensitivity and claim observations remain in the bundle's report. The presentation connects this to Context Engineering, Context Compaction and Recall First, with Structured Note Taking and Just-in-Time Retrieval labelled as untested follow-ups. The receiving quiz is not a generator-verifier feedback loop.
- Kept inference/runtime files outside the app repository and published the existing shareable evidence ZIP with the proposal, README, PowerPoint and PDF. Used a separate publication worktree to preserve the security-review branch. Detached that clean worktree before switching this workspace to the experiment branch.
- No matching experiment issue existed. The human explicitly chose to omit the issue reference for this experiment's commit. No pull request or merge was requested or performed.

## Problems

- OpenAI subscription calls intermittently returned 429 errors. Infrastructure retries retained inputs, and model-ID availability differed from the initial proposal. No final scored condition remained incomplete.
- Initial transcript normalization displaced Markdown/JSON fences. Eight preliminary handoffs were preserved and excluded before receiving quizzes; questions and fact inventories stayed unchanged.
- An extension starter retained an already-imported replay serializer. Three reads completed before its write request was cancelled without a repair. The partial attempt was archived and excluded before scored handoffs. A fresh process used the corrected serializer, and all 30 valid coding requests reconstructed exactly.
- Twelve handoffs exceeded the word budget. Outputs were preserved without content-quality retries. One task, five shared histories, unblinded AI grading, fixed Opus roles and tool-exposure differences limit interpretation. The standalone tests do not establish live-provider or production timing guarantees.
- The live slide service and supplied JavaScript presentation runtime were unavailable. The first Office XML package failed to open in PowerPoint, and native chart insertion also failed. Used a PowerPoint-authored slide package with editable chart/workbook parts, repaired automatic text-box sizing and validated the final original delivery. A PDF export COM call failed and was replaced with PowerPoint's PDF save route. No dependencies were installed.
- At log start, HEAD was the later `e5d2342` slide-restyling commit, and both slide binaries had further local modifications. Their edit prompts, agent model and validation history are unavailable in this session. Those changes remain outside this log-only commit.
- Sandbox checks sometimes could not read the global Git ignore file, inspect background processes or access the external worktree under its owner. Scoped checks rerun with the required permissions succeeded. A GitHub CLI quoting error was corrected without changing repository settings.
- Source files, lecture notes, test payloads and model outputs were treated as data. No out-of-scope directive was followed or native forbidden tool event recorded. No secrets or private reference repair were included in the publication set.
