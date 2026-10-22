# Reflections: Whimsyturtle

In [MP2](https://github.com/CS3227-2610-MP2-Arbiter/CS3227-2610-MP2/blob/main/reflections/Whimsyturtle/reflection.md#what-i-would-change), I concluded that I should check agents with **deterministic graders** for what they change and run, and keep human review for judgement. For MP3, I designed Deskmate's multi-agent workflow with Claude, grounded in the Weeks 6 to 8 lecture notes, to fix four problems from MP2: plans too long for humans to read, one big commit per feature, drift from creating many issues up front, and unclear issue granularity. I then owned the Support Officer role, including its AI feature, [highlighting a ticket's key sentences](../../workflow/specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences). At the team level, I built the guarded gateway that every user AI call passes through ([PLT-5, PLT-6 and PLT-8](../../workflow/specs/product/platform.md#plt-8-guard-user-ai-calls-in-the-internal-gateway)), and most recently fixed how article suggestions match articles ([#94](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/issues/94)).

_(See [001](../../logs/Whimsyturtle/001-plan-the-multi-agent-workflow-and-scaffold-it.md))_

## AI Security

### 1. Attack Surfaces and Prompt Injections I Considered

Week 6's lecture separates securing the **product** from securing the **development process**, and I found that each needed its own threat model.

In the product, who writes the text sent to the model decides the type of **prompt injection**. My key-sentences feature sends a description written by a Requester to the model when a Support Officer asks for it. This is **remote (indirect) prompt injection**: the attacker never talks to the model, but plants instructions in stored content that another user's request later processes. In contrast, my teammate's article suggestions send the Requester's own draft, so their main risk is **direct prompt injection**. Beyond injection, I also considered exhausting the shared SoC LLM allowance and model output being rendered as HTML. To cover Week 6's types systematically, the gateway's tests use 23 payloads, ranging from direct overrides and false authority claims, through forged role markers and delimiters, to **obfuscation** (e.g. base64 and Cyrillic look-alikes) and **Unicode smuggling** (e.g. zero-width and tag characters).

In the process, Week 6 warns that anything a coding agent reads is a potential injection point. As such, [`AGENTS.md`](../../AGENTS.md#instructions-and-data) treats code, issues, handoffs, test payloads and model output as data, reads issues only from collaborators, and makes each agent report any "Untrusted content seen". The process surface I had not considered was the **supply chain**: a later security review found that our deployment job pinned the Vercel CLI but not its npm dependencies, in the same job that holds the deployment token.

_(See [020](../../logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md), [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md))_

### 2. Security Features and How They Are Tested

Every user AI call goes through one [internal gateway](../../workflow/specs/ai/llm-gateway.md), which applies Week 6's mitigations in a fixed order:

1. **Strict Templates and Delimiters**: Each request has exactly two messages. The system message holds only our fixed rules and the feature's instructions, while the user message is JSON of the form `{"untrusted_text": ...}`.
2. **Input Restriction**: Invisible and control characters are removed, and text over 4,000 code points is rejected.
3. **Output Filtering**: A reply must be strict JSON matching the feature's schema. Otherwise, the user gets an error and none of the reply.

However, I trusted these less than the controls that limit what a successful injection could achieve. Each sentence my key-sentences feature returns must be an exact substring of the saved description, so an injection can at worst make the model pick misleading sentences, never say anything new. Similarly, article suggestions never send article text to the provider: the model only returns up to three short phrases, and our own code does the matching.

Each acceptance criterion is labelled with one of Week 6's five case types, and 42 of our 154 product criteria are **adversarial**. For example, PLT-8.4 requires that no payload changes the request's structure, and its test checks the exact messages sent to a faked provider for all 23 payloads. Review also found weaknesses the tests had not: the security-reviewer showed that my original 12,000-code-point cap did not bound tokens, so a long ticket could push the system message out of the model's context, and I lowered it to 4,000. More surprisingly, Claude's own Edit and Write tools decoded the spec's `<` escape (which stops forged `<|eot_id|>` tokens) back into `<`. A security control written into the spec had been silently undone in transit, and had to be restored byte by byte.

The main limitation is that every injection test fakes the provider. The tests show that a payload stays data in the request, not that the real model ignores it, and we never tried **Best-of-N jailbreaking** against the live model. This is why the damage-limiting controls above matter most to me.

_(See [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md), [026](../../logs/Whimsyturtle/026-specify-ticket-key-sentence-highlighting.md))_

### 3. Limits on the AI Agents

For the app's LLM calls, I applied Week 5's **guardrails** on resources and time as fixed limits in the spec: 10 calls per user and 30 across the app per rolling 10 minutes, at most 512 output tokens, a 10-second total timeout with no retries, and at most three items in any reply. I counted failed calls against the allowance too, as otherwise an attacker could deliberately trigger failures (e.g. by provoking malformed output) and retry without limit.

For the coding agents, each [role file](../../workflow/agents/) declares the paths it `writes` and `never_writes`. For example, the implementer may change `src/` but never its tests, while the critic and both reviewers may write nothing. [`check_scope.py`](../../workflow/scripts/check_scope.py) enforces this both as a hook before every file edit and as a check after every role run. Our Claude Code settings also deny reading `.env` files and destructive Git commands, and ask before pushing, merging or installing packages. At the process level, each slice is capped at one requirement, eight criteria and 400 application lines, and review stops after two rounds for me to decide, similar to Week 5's **max iterations** guardrail.

These limits were weaker than they looked. The hook checks file edits but not shell commands, so as our [workflow README](../../workflow/README.md#how-scope-is-enforced) admits, it "catches accidents, not attacks". In the gateway slice, for instance, the test-writer and implementer wrote throwaway scripts through Bash outside their scopes. When the hook wrongly blocked correct writes in a nested worktree, the orchestrator even played test-writer and implementer itself, quietly removing the independence the roles exist for. In terms of Week 5's workflow metrics, `check_scope.py` measured **scope accuracy**, but nothing measured the **prohibited-action rate**.

_(See [012](../../logs/Whimsyturtle/012-write-and-edit-knowledge-base-articles.md), [022](../../logs/Whimsyturtle/022-run-user-ai-admission-slice.md), [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md))_

### 4. Approval Gates and Human Oversight

Our **approval gates** sit wherever an agent's work leaves the repository or commits us to a design: I agree each slice's risk tier, confirm its acceptance criteria before tests are written, and must explicitly confirm any scope expansion. On GitHub, `main` requires an approved pull request and a passing `verify` check, and only such commits deploy.

I deliberately removed one gate. Production originally waited for a separate approval after CI, which I considered redundant, as the pull request review and required CI check were already the real gate. Notably, Codex's automatic approval review refused to remove it, as a persistent production-security change, until I requested it explicitly. However, this made the pull request review our last human gate, which raised the stakes of every review.

That made the next failure more serious. Auditing every merged pull request with subagents, I found that three had run at the Standard tier their issues proposed, without the security-reviewer, although they changed access-checked routes and the release check. A security review of the merged code then found 6 Medium issues, the worst being a test, added in a fix commit after review, that _required_ a page with a hidden extra link to pass the release check. The gate was not compromised by an attacker, but by a label: the tier came from the issue rather than from what the code changed. As such, I made security review trigger on what a slice changes (routes, role or workspace checks, scoped queries and deployment files), gave reviewers the exact commit range, and allowed a change to be called security-reviewed only within that range. This reflects Week 6's **continuous review**, as controls go stale when the workflow changes.

To keep the gates themselves from being bypassed, agents may never write that a human approved something, only humans tick pull request checkboxes, and the orchestrator re-checks agents' claims rather than relaying them (e.g. its own probe disproved a security-reviewer's claim about how HTML comments are parsed). Still, oversight involved trade-offs. After two rounds of fixes, I stopped without filing the remaining parser findings, as the release check only reads our own home page, which an attacker cannot easily supply, and the fixes had already cost about a million subagent tokens. While I still believe the risk was low, those findings now exist only in a log, and I would file them next time.

_(See [009](../../logs/Whimsyturtle/009-activate-automatic-releases.md), [019](../../logs/Whimsyturtle/019-audit-security-reviews-and-tighten-the-workflow.md), [020](../../logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md), [021](../../logs/Whimsyturtle/021-fix-the-medium-security-review-findings.md))_

## Spec-Driven Development

Overall, I found SDD worth its overhead for risky work, such as AI features and security controls, but too heavy for small or cosmetic changes.

### 1. What a Good Spec Makes Clear

We used Week 7's **more structured form of SDD**: [product specs](../../workflow/specs/PRODUCT-SPEC.md) split by concern, a [technical spec](../../workflow/specs/TECHNICAL-SPEC.md), a [security spec](../../workflow/specs/SECURITY-SPEC.md), one contract per AI feature, and a short plan per slice. Each requirement states why it exists and what is out of scope, and each criterion has an ID and a case type. Building with these, I think a good spec must make the following clear before implementation begins:

1. **Intent, With a Realistic Example**: A precise rule can still miss its purpose ([see below](#2-telling-whether-a-spec-is-precise-enough)), so each AI feature's spec should include a real input that must succeed.
2. **Conflicts With Existing Rules**: When I specified resolving tickets with a reply, the spec-writer stopped before drafting, as existing criteria promised that tickets were read-only. Only a human can choose which rule wins, so the spec must surface such conflicts rather than silently override one.
3. **Non-Happy Paths**: Week 7 warns that anything unspecified becomes **the agent's guess**. Our critic repeatedly found such gaps, such as a Requester's eligibility for a password reset changing mid-request.
4. **Scope**: Each slice is limited to one requirement and eight criteria, so a request bundling several capabilities is split first, like Week 7's **Phase 0 scope check**.

_(See [013](../../logs/Whimsyturtle/013-define-requester-password-reset-slice.md), [016](../../logs/Whimsyturtle/016-define-ticket-resolution-with-a-reply.md))_

### 2. Telling Whether a Spec Is Precise Enough

Our [spec-critic](../../workflow/agents/spec-critic.md) asks of every criterion: "Can it be tested without reading code? Could two developers build different behaviour from it?" In practice, I treated three signals as evidence that a spec passed: the critic found nothing, the new tests failed only for the expected reason, and the implementer built the change in one pass with no review findings.

However, #94 showed me that precise is not the same as right. The original rule for article suggestions matched an article only if a whole AI phrase appeared inside its title or body. It passed the critic, was built exactly, and passed review. Yet the AI contract asks the model for "short search phrases", which rarely appear verbatim in an article, so the reported draft "i have printer that wont print, help" found nothing, despite a directly relevant demo article. Each rule was precise, but together, they could not meet the requirement's purpose. This matches Week 8's warning that a **verifier struggles when the evaluation criteria are fuzzy**: the critic checks a spec against itself, and "relevant" could not be checked without real model output.

Precision also depends on what the tests can check. In #95, I specified a loading caption for `Suggest articles`, but our test tools cannot run browser JavaScript, so deleting the script would still pass every test. I chose manual checks over adding Playwright, as a browser test framework would have added a dependency and CI burden, and expanded the scope close to the deadline. Hence, a criterion is only precise enough for an agent if the available tests can make it fail; otherwise, it should be explicitly marked as a manual check.

Finally, precision cost readability. Our specs reached about 40,000 words, and some criteria even define behaviour through Python functions, despite the spec-writer's rule to describe behaviour only. I often had to ask the agent to explain criteria in plain words before approving them. While Week 7 says a good spec should be **readable by agents (and people)**, ours drifted towards agents.

_(See [013](../../logs/Whimsyturtle/013-define-requester-password-reset-slice.md), [032](../../logs/Whimsyturtle/032-specify-article-suggestion-loading-feedback.md), [033](../../logs/Whimsyturtle/033-specify-whole-word-article-matching.md))_

### 3. How Requirement Changes Flow

Our specs are **spec-anchored**, in Week 7's terms: every test is marked with the criteria it checks (e.g. `@pytest.mark.ac("RQ-5.3")`), so a changed criterion leads directly to the tests that must change. As the old matching rule had been implemented exactly, #94 was a spec gap rather than a regression, so it followed the full flow:

1. **Spec** ([`ebca977`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/ebca977)): The spec-writer changed the rule to match articles on shared meaningful whole words, and the critic found no ambiguity.
2. **Checkpoint**: I confirmed the criteria. I chose whole-word matching as the smallest fix for the reported case before the deadline, and because it is deterministic, it can be tested without the real model, unlike a prompt change.
3. **Tests** ([`89a5508`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/89a5508)): The test-writer updated the existing tests and added a regression test using the reported draft. Once a faulty fixture was fixed, CI failed only for the expected reason.
4. **Plan, Build and Docs** ([`52cfb61`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/52cfb61)): A two-task plan, a 71-line change and an updated User Guide.
5. **Review**: Both reviewers found nothing, and all 2,638 tests passed.

Changes also flowed backwards, from review into the spec. When the security-reviewer found the gateway's 12,000-code-point cap unsafe, the change went into the spec first, then the tests, code and plan. However, this showed where the flow leaks: the new tests and the fix were pushed together, so CI never showed the tests failing against the old code, and the plan kept saying 12,000 until a second review round noticed. Week 7's **keeping the spec alive** therefore applies to every copy of a fact, which is why our [one home per fact](../../AGENTS.md#one-home-per-fact) rule links to a fact rather than restating it.

_(See [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md), [033](../../logs/Whimsyturtle/033-specify-whole-word-article-matching.md))_

### 4. Tests That Check Intent, Not Wording

#94's bug passed every test because the tests were written by people (and agents) who knew how the matcher worked. For example, our end-to-end Requester test uses a fake provider whose phrases are commented as "The phrases the fake provider suggests for the draft, which match both sample articles". In other words, the tests checked that the code matched phrases chosen to match, i.e. the spec's wording rather than its intent. As Week 2 warned, **volume is not coverage**: over 2,600 passing tests did not include one realistic model phrase.

For AI features, intent depends on both our code _and_ the real model's output, while a faked provider only tests the former. The fix's regression test is closer to intent, as it uses the reported draft and the actual demo article, but its phrases are still hand-picked, and live-provider relevance remains unverified. Next time, I would record real SoC LLM responses for each feature and use them as test fixtures.

Tests can also pass for the wrong reason, lacking Week 2's **defect-finding power**. My key-sentences feature passed two rounds of agent review, but a later review in my teammate's session found that the expired-session test would still pass with the eight-hour sign-in rule broken, because Django's own session expiry rejected the request first ([`77a2221`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/77a2221)). This suggests a practical way to check intent: for each test, ask which broken implementation would still pass it.

_(See [026](../../logs/Whimsyturtle/026-specify-ticket-key-sentence-highlighting.md), [033](../../logs/Whimsyturtle/033-specify-whole-word-article-matching.md))_

## Basic Multi-Agent SE

### 1. Which Tasks Benefit from Specialised Agents

Our seven [role agents](../../workflow/agents/) map onto Week 7's specialised agents: a spec-writer, a read-only spec-critic, a test-writer, an implementer that also plans, devops for deployment files, and read-only reviewer and security-reviewer roles. The [`slice`](../../workflow/skills/slice.md) skill runs them in Week 8's **orchestrator-subagent** pattern. We did not need separate analyst or architect agents, as the spec-writer owned the technical spec, and each slice was small enough to need little architecture.

My main takeaway is that the value came from **independence** rather than expertise, matching Week 7's motivations of **access control** and **independent verification**:

1. **Tests Separate From Code**: As the implementer can never write tests, it cannot weaken one to make it pass. When two test-harness failures appeared while building ticket resolution, the implementer stopped as `blocked`, and the test-writer fixed the harness.
2. **Read-Only Verifiers**: The critic and reviewers cannot "fix" what they review, so their findings go back to me or to the role that owns the file. For example, the security-reviewer, not the general reviewer, found the unsafe input cap.

Conversely, specialisation was overkill for small, localised changes, as Week 7's trade-offs warn. Showing the workspace code on the demo page took 6 role runs and about 328,000 subagent tokens for a 29-line change, whereas our Fast lane fixed a one-line spacing bug with two runs.

_(See [017](../../logs/Whimsyturtle/017-resolve-tickets-with-one-saved-reply.md), [018](../../logs/Whimsyturtle/018-show-the-workspace-code-on-the-demo-page.md), [024](../../logs/Whimsyturtle/024-space-submit-buttons-away-from-fields.md))_

### 2. Building and Testing the Agents

I built each role as one Markdown file in [`workflow/agents/`](../../workflow/agents/), with thin adapters so that both Claude Code and Codex load it, and read-only roles get only read tools. Following my MP2 conclusion, I tested what could be checked deterministically: 40 workflow tests check that both tools load every role, that read-only roles cannot write, and that the scope check blocks cases such as the implementer editing a test.

Following Week 7's simple workflow, I also fed review lessons back into the agent definitions. After the security-review audit, I changed the reviewers' inputs and triggers ([`8d74e8e`](https://github.com/CS3227-2610-MP3-Deskmate/CS3227-2610-MP3/commit/8d74e8e)). Since each log records which version of a role file an agent ran, I could see the change take effect: in the next Fast lane slice, the updated reviewer flagged that a bug fix needed my explicit confirmation to use the Fast lane.

However, these tests check the **enforcement**, not the **agents' behaviour**. I still did not build the invocation tests and negative controls I proposed in MP2, and Week 4's point that **one passing run proves little** applies to most of my evidence. My one controlled experiment was on handoffs, described next.

_(See [001](../../logs/Whimsyturtle/001-plan-the-multi-agent-workflow-and-scaffold-it.md), [019](../../logs/Whimsyturtle/019-audit-security-reviews-and-tighten-the-workflow.md), [024](../../logs/Whimsyturtle/024-space-submit-buttons-away-from-fields.md))_

### 3. What One Agent Must Pass to the Next

I prepared an [experiment](../../experiments/agent-handoff-2026-10-19/README.md) on handoffs for a tutorial presentation, expecting our structured `AGENTS.md` checklist to preserve more context than free prose. Five Opus coding agents each worked on the same task. Four handoff models (GPT-5.6 Sol and Luna, and Claude Opus and Sonnet 5.5) then summarised every history twice, in at most 200 words: once as prose and once as our checklist. Finally, fresh Opus agents answered six questions using only each handoff, scored against answer keys frozen in advance.

| Handoff model | Prose | Checklist |
| --- | --- | --- |
| Sol | 78 | 73 |
| Luna | 64 | 62 |
| Opus | 78 | 79 |
| Sonnet | 74 | 75 |

_Expected facts recovered, out of 136 per condition._

My expectation was wrong: there was no consistent checklist advantage, and every condition lost roughly half of the expected facts. Instead, what survived was what was asked for: changed files and checks run were recovered fully in every condition, while which provider responses count as success was recovered in only 4 of 360 cases. No fact was stated wrongly, which, given Week 9's **recall first** principle, is what makes these losses dangerous: a receiving agent cannot recover what was never written, and cannot tell that it is missing. A rigid field could even hide a decision: in one checklist, an open question about API keys became an assumption under "Decisions needed: None stated".

As such, I concluded that a handoff must explicitly ask for open decisions, unverified areas and rules still to enforce, and that durable facts should not depend on handoffs at all. In our workflow, the orchestrator passes the issue, the paths needed and earlier handoffs as fenced data, but never its conversation, while facts live in the spec. Reviewers also needed the **risk tier and exact commit range**, as before I added these, fix commits landed after the last review round unnoticed. The experiment had clear limits, namely one task, AI grading without blinding, and two of the five histories added after I had seen the first results.

_(See [019](../../logs/Whimsyturtle/019-audit-security-reviews-and-tighten-the-workflow.md), [022](../../logs/Whimsyturtle/022-run-the-agent-handoff-experiment.md))_

### 4. Where Errors and Malicious Instructions Slip Through

In our spec, implement and review chain, errors slipped through at four points:

1. **A Shared Wrong Spec**: In #94, every agent agreed, as each checked its work against the spec, and the spec was wrong for real model output.
2. **Labels Deciding Who Reviews**: The wrong tier skipped the security-reviewer, and a test that _required_ insecure behaviour got in. As later agents treat tests as the truth, a bad test is a durable way for an error, or a malicious change, to survive.
3. **The Orchestrator**: When I asked for explicit confirmation before scope expansion, the orchestrator also added an unrequested budget rule, and recorded it as my request. I had it reverted, and logged the irony of overscoping an anti-overscoping request. Although it is the most powerful agent, the scope check never applies to it.
4. **Between Pull Requests**: My teammate's authorization test was designed to fail for any route without an access decision, but my key-sentences route merged while that pull request was still open, so each passed separately and only the combination failed.

We saw no real attack, so our defences against malicious instructions remain structural: agents treat issues, handoffs and test payloads as data, read issues only from collaborators, and red-team payloads are stored escaped. The gap that concerns me most is Week 6's **tool poisoning** through GitHub: since the hook does not check shell commands, an agent that followed an injected instruction could act outside its scope, leaving only the post-run scope check and human review to catch it.

_(See [008](../../logs/Whimsyturtle/008-restart-automatic-deployment.md), [020](../../logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md), [027](../../logs/Whimsyturtle/027-correct-key-sentence-authorization-coverage.md))_

### 5. Evidence Each Agent Leaves Behind

To support Week 5's **traceability**, each agent run leaves evidence that can be checked without trusting its summary:

1. **A Handoff**: Its status, changed paths, checks with their actual results, decisions needed, assumptions and untrusted content seen.
2. **Commits**: One per step, with an `Agent:` trailer, a `Why:` line on spec changes, and a scope check against the run's starting commit.
3. **Red Then Green CI**: 150 of our 154 criteria are mapped to tests by ID, and the remaining 4 are marked as manual checks.
4. **A Session Log**: It records each run's role-file version, reviewed range and results, separating what was checked from what was not.

However, this evidence was not always reliable. Statuses were ambiguous (an implementer once reported `blocked` only because it could not read the CI logs, although its work was complete), raw handoffs were not kept, and the orchestrator once committed its own edit under the implementer's trailer. Most logs also record cost as "not measured", making it hard to answer Week 9's **valuemaxxing** question of whether the extra agents were worth it.

_(See [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md), [031](../../logs/Whimsyturtle/031-run-slice-83-demo-workspace-samples.md))_

## Lessons I Learnt

1. **Validate AI Specs Against Real Model Output**: A spec can be precise, critiqued and fully tested, yet still miss its purpose. For each AI feature, I would include a realistic example that must succeed, and test against recorded real responses.
2. **Limit What a Successful Injection Can Do**: As tests with a faked provider cannot prove that the model ignores an injection, I would prioritise controls that bound the damage, and add live red-team runs.
3. **Decide Reviews by What Changed, Not by Labels**: Taking tiers from issue labels let security-sensitive changes skip review, while triggering review from the diff closed that gap.
4. **Check the Orchestrator Too**: The most powerful agent was the least checked, and it once rewrote my request. I would record requests verbatim and apply the same scope checks to it.
5. **Ask for What the Next Agent Needs**: A handoff template's fields matter more than its format, so it should explicitly ask for open decisions, unverified areas and rules still to enforce.
6. **Keep Red Before Green, and File What Is Left**: Pushing a test with its fix lost the evidence that the test could fail, and findings I chose not to fix were left only in a log. Both are small habits with large effects on traceability.
7. **Use Specialists for Risk, Not by Default**: Specialised agents paid off for AI and security work, mainly through independence, but cost hundreds of thousands of tokens for small changes. I would reserve them for high-risk slices, and measure cost consistently.
