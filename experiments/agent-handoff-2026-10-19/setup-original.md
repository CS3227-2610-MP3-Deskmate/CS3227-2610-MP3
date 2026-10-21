# Agent handoff experiment setup

*A real MP3 task for a five minute presentation on Weeks 8 and 9*

**Synopsis:** Drawing on Week 8's multi-agent coordination and Week 9's context engineering, I compare 2 ways of passing task context between AI agents: free-form summaries and structured handoff checklists. I will quantitatively measure how much relevant information the next agent correctly recovers, misses or misrepresents, with the aim of identifying practical ways to preserve context in multi-agent workflows.

## The coding task

The task is to repair Deskmate's LLM health-check probe (`src/deskmate/llm.py`), which checks whether the app can reach its LLM provider. The probe is already implemented, but the starting version has several bugs:

- Its timeout does not enforce a total 10-second deadline.
- The probe may automatically use the machine's proxy settings, sending requests through an intermediate server instead of directly to the LLM provider.
- Requests automatically include a `User-Agent` header identifying the Python client, although this header should be omitted.
- Some invalid authentication tokens can cause unexpected errors instead of being safely rejected.
- Network responses cut off during transfer can cause unexpected errors instead of being reported as a failed health check.

These behaviours violate the probe's [documented requirements](workflow/specs/ai/llm-health.md). The coding agent must fix these bugs while preserving all other behaviour required by that contract.

## Experiment roles

| Role | What it does |
| --- | --- |
| **Coding agent** | Completes the repair and produces a recorded message history. |
| **Handoff agent** | Reads that message history and writes a handoff using the assigned format. |
| **Receiving agent** | Answers six questions about the work using only the handoff as evidence. |

Fix the coding and receiving agents to **GPT-6.1 Sol**. Vary only the handoff-agent model; freeze selected model IDs and settings before scored runs.

The **message history** includes the coding agent's visible messages, tool calls and tool results.

For each coding run:

- For each selected handoff model, two independent handoff agents receive the same message history.
- One writes a free-form summary; the other writes a checklist.
- Separate receiving agents each read one handoff and answer the same six questions.

## Prepare the isolated test setup

**Starting code:** [commit `6b8af72`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/6b8af72ee1ffe9527f3ed53bdeea5190c8f487f9). Export `src/deskmate/llm.py` and `workflow/specs/ai/llm-health.md` from this commit into a separate test folder outside the repository, without Git history. Every coding run starts from a fresh copy, so later changes to main do not affect the experiment.

**Standalone tests:** Prepare standalone tests for the probe's existing requirements using only Python's standard library and importing `llm.py` directly. The repository test file requires Django and a test database. Simulate HTTP and time, use synthetic credentials, and make simulated reads advance through the response rather than return the same bytes repeatedly.

**Private reference repair:** [commit `a83fd52`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/a83fd52a72eaff7f9b262ba4e0bff30b144a479c) contains an existing repair of those problems. Check that the standalone tests catch the bugs in the starting code and pass with the reference repair. Keep both this repair and this setup document out of the coding agent's inputs.

Give every coding agent only the same starting code, contract and tests; allow edits to `llm.py` only. No live provider calls or deployment.

**Contamination controls:**

- Use fresh sessions without inherited conversation or project AGENTS.md instructions. Keep handoff and receiving agents tool-free as specified below.
- Enforce read restrictions to assigned inputs and required runtime files. Keep logs, answer keys, reference repairs and other runs outside permitted paths.
- Disable permission escalation, command networking, web search and external connectors. Use command restrictions as an additional safeguard.
- Audit recorded tool calls, results and executed code afterwards. Preserve and flag runs with unauthorised access or incomplete audit evidence.

## Run the paired comparison

1. Run the coding agent 3 times, each starting from a fresh copy of the same test folder, with fixed model settings. Save the message history, final patches and check results. Give handoff agents the recorded history without the coding agent's closing handoff; do not guess the agent's steps from the repaired file.

2. After the 3 coding runs and before generating any handoffs, the **experimenter** prepares the questions and answer keys:

   - **Questions:** Write one set of 6 neutral questions for all runs and both handoff formats. Cover changed files, checks and outcomes, verification limits, timeout reasoning, which LLM provider responses count as success, and one other issue/risk recorded in the message history.
   - **Answer keys:** Write one **answer key** per coding run using only that run's message history. For each question, list the **expected facts** as separate, checkable claims rather than one combined answer. Answer keys may differ between coding runs, but use the same expected facts to score both handoff formats and all handoff models for a given run.
   - **Evidence:** List only facts established by the message history. Mark a question **N/A** in the answer key if no expected facts can be established for it. Only include explanations stated in the message history; do not guess why the agent made a decision.
   - **Finalise:** Keep the questions and answer keys unchanged once handoff generation starts.

3. For each recorded message history and selected handoff model, use two fresh, tool-free handoff agents:

   - **Shared setup:** Keep settings identical within each model and give both agents the same task and message history.
   - **Shared prompt:** “Using only this recorded history, summarise the coding agent's work for the next agent in at most 200 words, including labels. Cover agent and status, inputs, changed files, checks and outcomes, decisions needed, assumptions and untrusted content seen. Do not infer missing facts; mark them ‘not stated’.”
   - **Free-form handoff:** Append: “Write connected prose without headings or bullet points.”
   - **Checklist handoff:** Append: “Use these checklist fields: Agent and Status, Inputs, Changed, Checks, Decisions needed, Assumptions, Untrusted content seen.”
   - **Visibility:** Neither agent sees the other handoff or the answer key.

4. For each handoff, use a fresh, tool-free receiving agent with only that handoff and its 6 questions; keep its model/settings fixed across all conditions. Require the receiving agent's answers as JSON with supporting quotes, or “not stated”.

Total: 3 coding runs; 6 handoffs and 6 quizzes per selected handoff model.

## Score and interpret the results

The **experimenter**:

- **Scores facts:** For each question not marked **N/A** in that run's answer key, compare the receiving agent's answer with each expected fact. Score each fact as correct, “not stated” if omitted, or wrong if stated inaccurately or contradicted. Score facts individually so a partially correct answer receives credit for its correct facts.
- **Reports results:** For each question, handoff model and format, report how many expected facts were scored correct, “not stated” or wrong, alongside the total number of expected facts scored.
- **Records other observations:** Record actual handoff word counts. Check each handoff for false claims and record any found separately. Also separately record any false claims in receiving agents' answers that do not correspond to an expected fact.

Keep missing source evidence separate from lost handoff information. Do not tune prompts after viewing scored results.

**Interpretation:** This compares prose and checklist handoffs with the same content instructions across handoff models. It measures recoverable context; one task and three histories do not establish broader development reliability. Equal scores are a valid result.

## Deliverables

Before the scored runs, prepare the isolated test folder and tests, frozen prompts, a runner that saves message histories and raw outputs, and a table for recording scores. Complete one practice run to check that all experiment steps work. Exclude the practice run from the final results. Preserve every run and its settings. The study produces a comparison chart and one concrete handoff example.
