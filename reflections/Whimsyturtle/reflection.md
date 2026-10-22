# Reflections: Whimsyturtle

In [MP2](https://github.com/CS3227-2610-MP2-Arbiter/CS3227-2610-MP2/blob/main/reflections/Whimsyturtle/reflection.md#what-i-would-change), I concluded that agents' work should be checked by **deterministic graders** wherever possible (e.g. which files they changed and which commands they ran), with human review kept for matters of judgement. For MP3, I designed Deskmate's multi-agent workflow with Claude, based on the Weeks 6 to 8 lecture notes, to fix four problems from MP2: plans too long for humans to read, one large commit per feature, issues drifting out of date because they were all created up front, and unclear issue sizes. I then owned the Support Officer role, including its AI feature, [highlighting a ticket's key sentences](../../workflow/specs/product/tickets.md#rq-4-highlight-a-tickets-key-sentences). At the team level, I built the [guarded gateway](../../workflow/specs/ai/llm-gateway.md): the single internal entry point that every AI feature must use to call the LLM.

_(See [001](../../logs/Whimsyturtle/001-plan-the-multi-agent-workflow-and-scaffold-it.md))_

## AI Security

### 1. Attack Surfaces and Prompt Injections I Considered

Week 6's lecture separates securing the **product** from securing the **development process**, and I found that each needed its own threat model.

For the product, the type of **prompt injection** depends on who writes the text that is sent to the model. My key-sentences feature sends a ticket description, written by a Requester, to the model when a Support Officer asks for it. This is **remote (indirect) prompt injection**: the attacker never talks to the model directly, but plants instructions in a ticket that another user's request later sends to it. In contrast, my teammate's article suggestions send the Requester's own draft, so their main risk is **direct prompt injection**. Besides injection, I also considered attackers using up our shared SoC LLM allowance, and model output being displayed as HTML, which could run scripts in a user's browser. To test each type of injection from Week 6, the gateway's tests include sample attacks: direct commands, false claims of authority, fake role markers, and instructions disguised through **obfuscation** or **Unicode smuggling**.

For the process, Week 6 warns that anything a coding agent reads is a potential injection point. As such, [`AGENTS.md`](../../AGENTS.md#instructions-and-data) tells every agent to treat code, issues, handoffs, test payloads and model output as data, never as instructions, to read issues only from collaborators, and to report any "Untrusted content seen". One risk I had missed was the **supply chain**. A later security review found that our deployment job installed a tool whose own dependencies were not pinned to exact versions. As the same job also holds our deployment token, a compromised dependency could have stolen it.

_(See [020](../../logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md), [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md))_

### 2. Security Features and How They Are Tested

Every AI feature must call the LLM through one internal gateway, which applies Week 6's mitigations in a fixed order:

1. **Strict Templates and Delimiters**: Each request has exactly two messages: a system message containing only our fixed rules and the feature's instructions, and a user message containing only the untrusted text, wrapped in JSON so that the model can tell it apart from the instructions.
2. **Input Restriction**: Invisible and control characters are removed, and overly long text is rejected.
3. **Output Filtering**: A reply must be valid JSON in the exact shape the feature expects. Otherwise, the user gets an error and none of the reply.

However, these mitigations only make injection harder, so I relied more on controls that limit the damage if an injection succeeds. Each sentence my key-sentences feature returns must appear word for word in the saved description. At worst, an injection could make the model highlight misleading sentences, but never add text of its own. Similarly, article suggestions never send article text to the model: the model only returns a few short search phrases, and our own code uses them to find matching articles.

To test these features, we labelled each acceptance criterion with one of Week 6's five case types (happy, boundary, ambiguous, failure and adversarial). Over a quarter of our product criteria are **adversarial**, e.g. one requires that no injected text can change the structure of the request sent to the model. Reviews also found weaknesses that the tests had missed. For example, the security-reviewer showed that my original length limit was too generous: a long enough ticket could overflow the model's context window and push out the system message, so I lowered the limit. More surprisingly, the agent's own editing tools broke a control. The spec requires every `<` in user text to be escaped, so that attackers cannot forge the special tokens that mark the start of a new message. When Claude edited the spec, its tools silently converted the written escape back into `<`, and it had to be restored.

The main limitation is that every injection test uses a fake model instead of the real one. The tests show that an attack stays in the data part of the request, but not that the real model would ignore it. We also never tried **Best-of-N jailbreaking** (trying many variants of an attack until one works) against the real model. This is why I value the damage-limiting controls most.

_(See [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md), [026](../../logs/Whimsyturtle/026-specify-ticket-key-sentence-highlighting.md))_

### 3. Limits on the AI Agents

For the app's own LLM calls, I wrote Week 5's resource and time **guardrails** into the spec as fixed limits: a maximum number of calls per user and across the whole app, a cap on the length of each reply, a total timeout with no retries, and a maximum number of items per reply. Failed calls also count towards the limit, since otherwise an attacker could deliberately cause failures and retry as often as they liked.

For the coding agents, each [role file](../../workflow/agents/) lists the paths that agent may and may not write. For example, the implementer may change `src/` but never its tests, while the critic and both reviewers may write nothing at all. [`check_scope.py`](../../workflow/scripts/check_scope.py) enforces these lists twice: as a hook that blocks an edit before it happens, and as a check after each agent finishes. Our Claude Code settings also forbid reading `.env` files and running destructive Git commands, and ask me first before pushing, merging or installing packages. For the process as a whole, each slice has a size limit, and after two rounds of review, the agents stop and I decide what happens next, similar to Week 5's **max iterations** guardrail.

However, these limits were weaker than they looked. The hook only checks file edits, not shell commands, so as our [workflow README](../../workflow/README.md#how-scope-is-enforced) admits, it "catches accidents, not attacks". In practice, agents did occasionally write files outside their scope through the shell. When the hook wrongly blocked a valid edit, the orchestrator even did the test-writer's and implementer's work itself, quietly removing the independence that separate roles exist to provide. In terms of Week 5's workflow metrics, `check_scope.py` measured **scope accuracy** (whether edits stayed within the allowed files), but nothing measured the **prohibited-action rate** (how often agents attempted forbidden actions).

_(See [012](../../logs/Whimsyturtle/012-write-and-edit-knowledge-base-articles.md), [022](../../logs/Whimsyturtle/022-run-user-ai-admission-slice.md), [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md))_

### 4. Approval Gates and Human Oversight

We placed **approval gates** at the points where an agent's work leaves the repository or commits us to a design. I agree each slice's risk tier, approve its acceptance criteria before any tests are written, and must explicitly approve any expansion of scope. On GitHub, a change reaches `main` only through an approved pull request with passing CI, and only `main` is deployed.

I deliberately removed one gate. Each production deployment originally waited for a separate approval after CI. I considered this redundant, since the pull request review and the required CI check already formed the real gate. Notably, Codex's built-in approval check refused to remove the gate, treating it as a lasting change to production security, until I asked for it explicitly. However, this made the pull request review our last human gate, which raised the stakes of every review.

This made the next failure more serious. When I used subagents to audit every merged pull request, I found that several had skipped the security-reviewer. Their issues had proposed a lower risk tier, even though the changes touched code that controls who may access what. A security review of the merged code then found several medium-severity problems, including a test, added after review, that only passed if the code behaved insecurely. In other words, the gate failed not because of an attacker, but because of a label: the risk tier came from the issue's description, not from what the code actually changed. As such, I changed the workflow so that:

1. Security review is triggered by what a slice actually changes (e.g. routes and access checks).
2. Reviewers are told exactly which commits to review.
3. A change counts as security-reviewed only if a security-reviewer actually checked its commits.

This reflects Week 6's **continuous review**: controls go stale as the workflow changes, so they must be revisited.

To stop the gates themselves from being bypassed, agents may never claim that a human approved something, only humans tick pull request checkboxes, and the orchestrator re-checks agents' claims rather than passing them on (e.g. it once tested and disproved a security-reviewer's claim). Still, oversight involved trade-offs. After two rounds of fixes, I stopped without filing issues for the remaining edge cases, for two reasons: the affected check only reads our own web pages, which an attacker cannot easily control, and further rounds were costly in tokens and time. While I still believe the risk was low, those findings now exist only in a log, and I would file them next time.

_(See [009](../../logs/Whimsyturtle/009-activate-automatic-releases.md), [019](../../logs/Whimsyturtle/019-audit-security-reviews-and-tighten-the-workflow.md), [020](../../logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md), [021](../../logs/Whimsyturtle/021-fix-the-medium-security-review-findings.md))_

## Spec-Driven Development

Overall, I found SDD worth its overhead for risky work, such as AI features and security controls, but too heavy for small or cosmetic changes.

### 1. What a Good Spec Makes Clear

We used Week 7's **more structured form of SDD**: [product specs](../../workflow/specs/PRODUCT-SPEC.md) split by area, a [technical spec](../../workflow/specs/TECHNICAL-SPEC.md), a [security spec](../../workflow/specs/SECURITY-SPEC.md), one contract per AI feature, and a short plan per slice. Each requirement states why it exists and what is out of scope, and each criterion has an ID and a case type. From building with these, I think a good spec must make the following clear before implementation begins:

1. **Intent, With a Realistic Example**: A rule can be precise yet still miss its purpose ([see below](#2-telling-whether-a-spec-is-precise-enough)), so each AI feature's spec should include a realistic input that it must handle correctly.
2. **Conflicts With Existing Rules**: A new requirement can contradict an old one. For example, adding replies to tickets conflicted with criteria promising that tickets could not be changed, and the spec-writer stopped before drafting. Only a human can decide which rule should win, so the spec must raise such conflicts rather than silently override the old rule.
3. **Non-Happy Paths**: Week 7 warns that anything unspecified becomes **the agent's guess**. Our critic repeatedly found such gaps, e.g. what should happen if data changes while a request is being processed.
4. **Scope**: Each slice may change only one requirement and a handful of criteria, so a request that bundles several features is split up first, like Week 7's **Phase 0 scope check**.

_(See [013](../../logs/Whimsyturtle/013-define-requester-password-reset-slice.md), [016](../../logs/Whimsyturtle/016-define-ticket-resolution-with-a-reply.md))_

### 2. Telling Whether a Spec Is Precise Enough

Our [spec-critic](../../workflow/agents/spec-critic.md) asks of every criterion: "Can it be tested without reading code? Could two developers build different behaviour from it?" In practice, I took three signals as evidence that a spec was precise enough: the critic found no problems, the new tests failed only for the expected reason before implementation, and the implementer built the change in one attempt without review findings.

However, article suggestions showed me that a precise spec is not necessarily a correct one. The original rule only matched an article if it contained one of the model's suggested phrases exactly. This rule passed the critic, was implemented exactly as written, and passed review. Yet the model is asked for short search phrases (e.g. "printer not printing"), which rarely appear word for word in an article. As a result, a realistic ticket about a broken printer found nothing, even though a demo article covered exactly that problem. Each part of the spec was precise on its own, but together, they could not achieve what the requirement was for. This matches Week 8's warning that a **verifier struggles when the evaluation criteria are fuzzy**. Our critic checks a spec for internal consistency, but whether suggestions are "relevant" could only be judged against the real model's output.

Precision also depends on what the tests are able to check. When I specified a loading indicator for article suggestions, our test tools could not run browser JavaScript, so the tests would still pass even if the script were deleted. I chose manual checks over adding a browser test framework, since that would have added a new dependency, made CI heavier, and expanded the scope close to the deadline. Hence, a criterion is only precise enough for an agent if the available tests would fail when it is broken; otherwise, it should be explicitly marked as a manual check.

Finally, precision came at the cost of readability. Our specs grew to tens of thousands of words, and some criteria even describe behaviour in terms of specific Python functions, despite the spec-writer's rule to describe only behaviour, not implementation. I often had to ask the agent to explain criteria in plain words before approving them. While Week 7 says a good spec should be **readable by agents (and people)**, ours became easier for agents to read than for people.

_(See [013](../../logs/Whimsyturtle/013-define-requester-password-reset-slice.md), [032](../../logs/Whimsyturtle/032-specify-article-suggestion-loading-feedback.md), [033](../../logs/Whimsyturtle/033-specify-whole-word-article-matching.md))_

### 3. How Requirement Changes Flow

In Week 7's terms, our specs are **spec-anchored**: each test is tagged with the IDs of the criteria it checks, so when a criterion changes, we can find exactly which tests must change too. A requirement change therefore follows the same steps as new work:

1. **Spec**: The spec-writer changes the criteria and records why, and the critic checks the change.
2. **Checkpoint**: I confirm the criteria, the approach and the size before any tests are written.
3. **Tests**: The test-writer updates the tests, which must fail, for the expected reason, before any code changes.
4. **Plan and Build**: The implementer plans and makes the change, and updates the User Guide.
5. **Review**: The reviewers check the final change against the spec.

Only a bug that breaks an existing criterion may skip the spec step. The article matching problem was not such a bug, since the code did exactly what the old spec said, so the fix had to start from the spec and go through every step. For that fix, I chose to match articles that share whole words with the model's phrases. It was the smallest fix possible before the deadline, and unlike changing the model's prompt, its results could be tested without calling the real model.

Changes can also start from a review. When the security-reviewer found the gateway's length limit unsafe, we changed the spec first, then the tests, code and plan. However, this also showed where the flow can break down. The new tests and the fix were pushed together, so CI never showed the tests failing on the old code, and the plan still stated the old limit until a second review noticed. Week 7's advice on **keeping the spec alive** therefore applies to every copy of a fact, which is why our [one home per fact](../../AGENTS.md#one-home-per-fact) rule says to link to a fact rather than repeat it.

_(See [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md), [033](../../logs/Whimsyturtle/033-specify-whole-word-article-matching.md))_

### 4. Tests That Check Intent, Not Wording

The article suggestion problem passed every test because the tests were written by people (and agents) who knew how the matching worked. For example, our end-to-end test used a fake model that returned phrases deliberately chosen to match the sample articles. In other words, the tests checked that the code followed the spec's wording, not that it achieved the spec's intent. As Week 2 warned, **volume is not coverage**: thousands of passing tests did not include a single realistic phrase from the model.

For AI features, whether the intent is met depends on both our code _and_ the real model's output, but tests with a fake model only check our code. The fix's new test is closer to the intent, as it uses a realistic ticket and the actual demo article, but we still have not checked how relevant the suggestions are with the real model. Next time, I would record real SoC LLM responses for each feature and use them as test data.

Tests can also pass for the wrong reason, meaning they lack Week 2's **defect-finding power**. My key-sentences feature passed two rounds of agent review, but a later review found that its test for expired sign-ins would still pass even if our sign-in time limit were broken, because a different rule rejected the request first. This suggests a practical way to check intent: for each test, ask what broken code would still pass it.

_(See [026](../../logs/Whimsyturtle/026-specify-ticket-key-sentence-highlighting.md), [033](../../logs/Whimsyturtle/033-specify-whole-word-article-matching.md))_

## Basic Multi-Agent SE

### 1. Which Tasks Benefit from Specialised Agents

Our seven [role agents](../../workflow/agents/) map onto Week 7's specialised agents: a spec-writer, a read-only spec-critic, a test-writer, an implementer that also plans, devops for deployment files, and read-only reviewer and security-reviewer roles. The [`slice`](../../workflow/skills/slice.md) skill coordinates them in Week 8's **orchestrator-subagent** pattern: one orchestrating session hands each task to the right agent and checks its result. We did not need separate analyst or architect agents, as the spec-writer owned the technical spec, and each slice was small enough to need little architecture.

My main takeaway is that the value came from keeping agents **independent**, rather than from their specialised expertise. This matches two of Week 7's motivations, **access control** and **independent verification**:

1. **Tests Separate From Code**: As the implementer can never write tests, it cannot weaken a test to make it pass. When a test harness failed, the implementer stopped and reported itself as `blocked` rather than editing the test, and the test-writer fixed it.
2. **Read-Only Verifiers**: The critic and reviewers cannot change what they review, so they must report problems to me or to the agent responsible, instead of quietly fixing them. A separate security-reviewer also caught problems the general reviewer missed, such as the unsafe length limit.

On the other hand, as Week 7's trade-offs warn, specialisation was overkill for small, self-contained changes. A small display change took six agent runs and hundreds of thousands of tokens, whereas our Fast lane, a shorter path for low-risk changes, handled a one-line fix with just two.

_(See [017](../../logs/Whimsyturtle/017-resolve-tickets-with-one-saved-reply.md), [018](../../logs/Whimsyturtle/018-show-the-workspace-code-on-the-demo-page.md), [024](../../logs/Whimsyturtle/024-space-submit-buttons-away-from-fields.md))_

### 2. Building and Testing the Agents

I defined each role in a single Markdown file in [`workflow/agents/`](../../workflow/agents/), with small adapter files so that both Claude Code and Codex can load it, and gave read-only roles no tools that can write. Following my MP2 conclusion, I tested what could be checked deterministically: our workflow tests check that both tools load every role, that read-only roles cannot write, and that the scope check blocks cases such as the implementer editing a test.

Following Week 7's simple workflow, I also updated the agent definitions with lessons from reviews. For example, after the security-review audit, I changed what reviewers receive and when security review runs. Since each log records which version of a role file an agent used, I could see the change take effect: the updated reviewer soon caught a process problem that its earlier version did not check for.

However, these tests only check that the restrictions are **enforced**, not how well the agents **behave**. I still did not build the invocation tests and negative controls I proposed in MP2, and Week 4's point that **one passing run proves little** applies to most of my evidence. My one controlled experiment was on handoffs, described next.

_(See [001](../../logs/Whimsyturtle/001-plan-the-multi-agent-workflow-and-scaffold-it.md), [019](../../logs/Whimsyturtle/019-audit-security-reviews-and-tighten-the-workflow.md), [024](../../logs/Whimsyturtle/024-space-submit-buttons-away-from-fields.md))_

### 3. What One Agent Must Pass to the Next

For a tutorial presentation, I ran an [experiment](../../experiments/agent-handoff-2026-10-19/README.md) on handoffs, expecting the structured checklist in `AGENTS.md` to preserve more context than free-form prose. Several coding agents worked on the same task. Four different models then wrote two handoffs for each coding session, one in each format, within a word limit. Finally, new agents answered questions about the work using only one handoff each, and their answers were scored against answer keys fixed in advance.

My expectation was wrong: neither format consistently did better, and every combination lost roughly half of the expected facts. Instead, the facts that survived were the ones the handoff instructions asked for. The changed files and checks run were always passed on, while details nobody asked for, such as which responses from the model provider count as successful, almost never were. No fact was stated wrongly; facts were simply left out. Week 9's **recall first** principle explains why this is dangerous: the next agent cannot recover information that was never written down, and cannot even tell that it is missing. A fixed template could even hide a decision: in one checklist handoff, an unresolved question was listed as an assumption, while the "Decisions needed" field said there were none.

As such, I concluded that a handoff template must explicitly ask for open decisions, anything not yet verified, and rules the next agent must still follow, and that important long-term facts should not rely on handoffs at all. In our workflow, the orchestrator gives each agent the issue, the relevant file paths and earlier handoffs, clearly marked as data, but never its own conversation, while lasting facts are kept in the spec. Reviewers also needed to know the risk tier and exactly which commits to review: before I added these, fixes committed after the last review round went unreviewed without anyone noticing. The experiment had clear limits: it used only one task, the AI grader knew which format it was grading, and two coding sessions were added after I had seen the first results.

_(See [019](../../logs/Whimsyturtle/019-audit-security-reviews-and-tighten-the-workflow.md), [022](../../logs/Whimsyturtle/022-run-the-agent-handoff-experiment.md))_

### 4. Where Errors and Malicious Instructions Slip Through

In our chain of writing the spec, implementing it and reviewing it, errors slipped through at four points:

1. **A Shared Wrong Spec**: With article suggestions, every agent's work was consistent with the spec, so none of them flagged a problem. The spec itself was what failed against real model output.
2. **Labels Deciding Who Reviews**: A wrong risk tier skipped the security-reviewer, which let in a test that only passed if the code behaved insecurely. Since later agents treat tests as correct, a bad test is a lasting way for an error, or a malicious change, to survive.
3. **The Orchestrator**: When I asked for a rule requiring my confirmation before any scope expansion, the orchestrator also added a size rule I had not asked for, and recorded it as my request. I had it reverted, and had the irony of overscoping a request against overscoping noted in the log. The orchestrator is the most powerful agent, yet the scope check never applies to it.
4. **Between Pull Requests**: My teammate's authorization test was designed to fail if any route (URL) in the app had no access rule. However, my key-sentences route was merged while that test's pull request was still open, so each passed on its own, and the problem only appeared once both were combined.

We did not see any real attack, so our defences against malicious instructions are untested in practice and rely on the workflow's design: agents treat issues, handoffs and test payloads as data, read issues only from collaborators, and store attack payloads in an escaped form. The gap that concerns me most is Week 6's **tool poisoning** through GitHub, where an instruction hidden in an issue or pull request hijacks an agent. Since the hook does not check shell commands, such an agent could act outside its scope, and only the check after its run and human review would catch it.

_(See [008](../../logs/Whimsyturtle/008-restart-automatic-deployment.md), [020](../../logs/Whimsyturtle/020-security-review-the-merged-code-that-skipped-it.md), [027](../../logs/Whimsyturtle/027-correct-key-sentence-authorization-coverage.md))_

### 5. Evidence Each Agent Leaves Behind

To support Week 5's **traceability**, each agent run leaves evidence that a person can check without having to trust the agent's own summary:

1. **A Handoff**: Its status, the files it changed, the checks it ran with their actual results, decisions needed, assumptions, and any untrusted content seen.
2. **Commits**: One commit per step, labelled with the agent that made it, with the reason for every spec change, and checked against the agent's allowed paths.
3. **CI Results**: Tests failing before the change and passing after it. Almost every criterion is linked to tests by its ID, and the rest are marked as manual checks.
4. **A Session Log**: A summary of each working session, recording which version of each role file ran, which commits were reviewed and the results, and separating what was checked from what was not.

However, this evidence was not always reliable. Statuses could be misleading (an implementer once reported `blocked` only because it could not read the CI logs, although its work was complete), the original handoffs were not kept, only summaries of them, and the orchestrator once labelled its own edit as the implementer's. Most logs also record cost as "not measured", making it hard to answer Week 9's **valuemaxxing** question of whether the extra agents were worth their cost.

_(See [025](../../logs/Whimsyturtle/025-run-the-guarded-ai-gateway-slice.md), [031](../../logs/Whimsyturtle/031-run-slice-83-demo-workspace-samples.md))_

## Lessons I Learnt

1. **Validate AI Specs Against Real Model Output**: A spec can be precise, critiqued and fully tested, yet still miss its purpose. For each AI feature, I would include a realistic example that must succeed, and test it against real responses recorded from the model.
2. **Limit What a Successful Injection Can Do**: Since tests with a fake model cannot prove that the real model will ignore an injection, I would prioritise controls that limit the damage, and add attack tests against the real model.
3. **Decide Reviews by What Changed, Not by Labels**: Setting risk tiers from issue labels let security-sensitive changes skip security review; deciding based on what the code actually changes closed that gap.
4. **Check the Orchestrator Too**: The most powerful agent was the least checked, and it once rewrote my request. I would record my requests word for word, and apply the same scope checks to the orchestrator as to other agents.
5. **Ask for What the Next Agent Needs**: What a handoff template asks for matters more than its format, so it should explicitly ask for open decisions, anything not yet verified, and rules the next agent must still follow.
6. **Show Tests Failing First, and File What Is Left**: Pushing a new test together with its fix lost the evidence that the test could catch the problem, and findings I chose not to fix were left only in a log. Both are small habits with a large effect on traceability.
7. **Use Specialists for Risk, Not by Default**: Specialised agents paid off for AI and security work, mainly because they were independent of each other, but cost hundreds of thousands of tokens even for small changes. I would reserve them for high-risk work, and measure cost consistently.
