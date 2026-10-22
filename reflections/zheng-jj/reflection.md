# Reflections: zheng-jj

I planned Deskmate's initial milestones and high-level issues, then ran most of the Requester-facing slices: sign-in and demo workspaces, ticket submission, article reading, article suggestions and their loading feedback, the Requester and Support Officer journeys, the route inventory, and the authorization matrix. I also worked on rate limits, production migrations, and the audit of our session logs. My main conclusion is that specification is not paperwork that precedes development; it is the coordination mechanism that decides whether several agents, tests and reviews are checking the same thing. When that mechanism was precise, the workflow was powerful. When it was only precise-looking, it made everyone confidently build the wrong thing.

## AI Security

### 1. Attack Surfaces and Prompt Injections I Considered

I treated AI security as two problems: securing the product and securing the process that builds it. For the product, the most useful question was who writes the text that reaches the model. In the article-suggestion feature I built, the Requester writes the draft, so the realistic risk is **direct prompt injection** by the person using the feature. In the key-sentences feature, a Requester writes a ticket description and a Support Officer later causes that description to be sent to the model, so the risk is **indirect, cross-user prompt injection**. The attacker does not need access to the model; they only need to plant instructions in text another user will submit.

I also considered attack surfaces beyond injection:

- **Data over-sharing**: article bodies, user identities and workspace identifiers must not be sent to the provider. My feature sends only the Requester's normalised title and description, and the model returns only short search phrases.
- **Resource exhaustion**: an authenticated user could spend the shared SoC LLM allowance, or cause repeated expensive requests. This is why admission limits, audit records, one-call semantics and the separate sign-in rate limits mattered.
- **Output handling**: a model reply could contain HTML, misleading article titles or forged markup. Provider output had to remain data, and stored article titles had to be escaped when displayed.
- **Authorization and forged input**: extra form fields, query parameters or headers must not select another workspace, article or ticket. The request's stored role and workspace have to win every time.
- **Process injection**: issues, handoffs, code comments and test payloads are all text an agent reads. I followed the rule that these are data, never instructions, and recorded untrusted content in the session logs.

These surfaces appear in different slices. The article-suggestion work is logged in [008](../../logs/zheng-jj/008-specify-article-suggestions.md) and [012](../../logs/zheng-jj/012-build-article-suggestions.md); the rate-limit work is in [003](../../logs/zheng-jj/003-run-slice-38-rate-limits.md); the sign-in controls and their review are in [001](../../logs/zheng-jj/001-plan-milestones-and-run-slice-3-sign-in.md).

### 2. Security Features and How They Are Tested

The product's central AI control is the guarded gateway, which every user-facing AI feature must call. My article-suggestion feature did not reimplement that boundary; it relied on the gateway's fixed instructions, schema, input guard, output guard, admission and audit behaviour. The feature added three controls of its own:

1. **Only the attacker-relevant data is sent.** The joined text is exactly the normalised title, two line feeds and the normalised description. No article body, article identifier or workspace value reaches the provider.
2. **Matching is local and deterministic.** The provider returns at most three phrases of at most 100 code points. The application then matches those phrases against the current workspace's saved articles, using casefolding and explicit word rules. A manipulated reply can choose phrases, but it cannot cause the app to fetch or display an article from another workspace.
3. **The feature keeps no suggestion state.** Suggestions are not stored in the session, cookies, cache or database. Only the gateway's existing admission and audit records change.

The tests are deliberately adversarial rather than only happy-path. In [012](../../logs/zheng-jj/012-build-article-suggestions.md), the new tests first failed for the missing route and button, then covered 24 RQ-5 cases. They check that a hostile draft and hostile reply stay data, that submitted values and article titles are escaped, that extra inputs cannot choose a workspace or article, that an `error` or `refused` result reads no article, and that no article is read before an accepted gateway call. The current test suite also has cases such as `test_find_a_fix_adversarial_draft_and_reply_stay_data` and `test_find_a_fix_extra_inputs_cannot_choose_workspace_article_or_ticket`.

The independent security review still found a Medium that the tests had not encoded: the first version loaded the whole workspace's articles before admission. A refused or over-length request therefore paid a database cost it did not need. The fix moved the read after an `ok` result and changed it to bounded keyset pages, stopping at three matches. This is the value of a separate reviewer: the tests proved the behaviour they specified, but the review found an availability and cost problem outside that specification.

The same pattern held in other slices. The sign-in tests were checked against a scratch reference implementation and 30 deliberately injected defects; the demo-workspace tests caught 15 deliberate faults; the rate-limit tests covered non-ASCII digits, zero-width characters, control characters, signs and a clock that moved backwards. Those mutation-style checks matter more to me than a large green count, because they show that a test can actually fail when the defence is removed.

### 3. Limits on the AI Agents and on AI Features

The AI feature limits are layered. The gateway rejects text over 4,000 Unicode code points, makes at most one provider request, has no retry or fallback, and accepts only a reply that passes a 4,096-code-point cap, strict JSON parsing and the caller's schema. The article-suggestion schema further limits the reply to three phrases of at most 100 code points. Each admitted call is counted and audited, and the provider call runs outside a database transaction. The rate-limit slice adds separate limits for sign-in and other counted actions, with per-kind locks and a recorded gap for connection exhaustion ([003](../../logs/zheng-jj/003-run-slice-38-rate-limits.md)).

The agents that build the product are limited in a different way. A slice may change criteria in at most one requirement, at most eight criteria, and at most 400 lines under `src/` outside tests and migrations. Role agents have explicit `writes` and `never_writes` lists. Reviewers are read-only. A role agent gets two review rounds before I must decide what remains. The plan, spec and pull request all expose the scope before and after the work.

Those limits are not equivalent in strength. The code limits are measured by commands; the agent limits depend on the orchestrator noticing that a limit was crossed. The pre-edit hook catches an agent trying to edit outside its role, but shell commands are not checked, and the hook fails open if `python3` is unavailable. On one machine that failure actually happened ([001](../../logs/zheng-jj/001-plan-milestones-and-run-slice-3-sign-in.md)), so the orchestrator had to run `check_scope.py` manually. I would not describe that as a security boundary. It is an accident detector with a useful audit trail.

### 4. Approval Gates and Human Oversight

We used human gates at the points that mattered most: the tier decision, the spec checkpoint before tests, explicit approval for a scope expansion, pull-request review, and deployment approval. The gates did catch real problems. In [007](../../logs/zheng-jj/007-lead-home-page-visitors-to-sign-in.md), review found that the production release verifier still expected the old exact home-page text, so the home-page link would have broken a production release after deployment. The session stopped and asked whether to expand the slice to fix the verifier; I approved that expansion, and the slice then added regression cases.

The weakness was not the existence of gates but the quality of the approval. In [001](../../logs/zheng-jj/001-plan-milestones-and-run-slice-3-sign-in.md), I replied `yea do it` to a checkpoint that bundled paths, wording, response codes, session length and security headers. In [002](../../logs/zheng-jj/002-run-slice-4-demo-workspace.md), I replied `yse` to every recommendation for the demo workspace. In [003](../../logs/zheng-jj/003-run-slice-38-rate-limits.md) and [004](../../logs/zheng-jj/004-run-slice-11-production-migrations.md), I repeatedly replied `go with recommendations`. Those answers were convenient, but they were not informed approval of each security-relevant choice. A recommendation list produced by the same agent that will implement it, followed by a one-word acceptance, turns oversight into a formality.

There was a second, more serious problem: when an independent reviewer was unavailable, I sometimes completed the review myself. In [013](../../logs/zheng-jj/013-requester-end-to-end.md), the reviewer stalled and produced no handoff; the orchestrator completed the review. In [009](../../logs/zheng-jj/009-route-inventory.md), [011](../../logs/zheng-jj/011-authorization-matrix.md) and [015](../../logs/zheng-jj/015-check-every-session-log.md), the orchestrator also played the test-writer or reviewer role. That keeps the work moving, but it destroys the independence the gate was supposed to provide. If the same session writes the test, runs the test and decides that the test is adequate, there is no credible second opinion.

My conclusion is that an approval gate must be **specific, attributable and independent**. A checkpoint should list numbered decisions, each with the exact behaviour and the files or tests it changes, and I should approve or reject each one. A review with no handoff should be marked incomplete and rerun, not silently replaced by the orchestrator's own judgement. An agent should never be able to approve its own production change.

## Spec-Driven Development

### 1. What a Good Specification Makes Clear

A good specification makes the intended user-visible behaviour unambiguous before implementation begins. In our best slices it stated:

1. **Why the requirement exists.** Every product requirement has a `Why:` line. That line let the critic and the implementer distinguish a real requirement from an accidental detail.
2. **The exact observable contract.** For article suggestions, this included the joined text, the exact field limits, the exact response messages, the order of validation and AI work, and the exact HTML structure of the results area.
3. **Boundary behaviour.** The spec had to say what happens at 4,000 code points, what happens when a draft is valid under the ticket limits but too long for the gateway, and whether that case is a validation error or an unavailable result. Those distinctions are not cosmetic; they change the user's path.
4. **Failure behaviour before the happy path is built.** The spec named what happens for `error`, `refused`, an empty phrase list, a database failure before the gateway call and a database failure after an `ok` result.
5. **Scope and exclusions.** The article-suggestion requirement explicitly excluded ranking, synonyms, stemming, fuzzy matching, saved suggestions, background work and new limits. Without that list, each agent could have invented a different feature.
6. **How the requirement will be checked.** Criteria were tagged as happy, boundary, ambiguous, failure or adversarial. A timing behaviour that the Django test client could not observe was marked `[manual]` rather than being given a test that could not fail for the right reason.

The loading-feedback slice is a useful small example. The spec had to carve out exactly one inline script from the general no-script rule, define the pending caption and paragraph, say what happens without scripting, and say that the script reads no ticket, user or provider value. The spec-critic found ten issues, including a duplicated sentence, a dangling reference to RQ-5, a contradiction with the existing plain-text requirement, and an unspecified no-script fallback. Those were specification defects, not implementation defects, and finding them before code saved a much more expensive review round ([014](../../logs/zheng-jj/014-highlight-loading-feedback.md)).

### 2. Telling Whether a Spec Is Precise Enough

I used four signals: the spec-critic found no material ambiguity; two independent implementers could build the same observable behaviour from the text; the new tests failed for the expected reason before implementation; and the tests would fail if the behaviour were removed. The last signal is the one I trust most, because a test can be precise and still be unable to detect the defect it claims to cover.

But article suggestions taught me that precision is not the same as correctness. The original specification was very precise about matching: casefold each phrase and each article title and body, then match when a phrase is a substring. The feature was implemented exactly as written, the critic accepted it, and the tests passed. Yet the model was asked for short search phrases, and a short phrase will often not occur verbatim in an article that covers the same problem. A realistic ticket about a printer that will not print might produce `printer not printing`, while the article says `the printer is offline`; the exact-match rule returns nothing. The rule was testable, deterministic and internally consistent, but it did not serve the requirement's purpose. The later whole-word matching change addressed the recall problem by retaining meaningful words after filtering stopwords.

That is why I now want a realistic example in every AI requirement, not only a set of boundary cases. The example should be an actual ticket and an actual article that a user would expect to match, and it should be tested against recorded or real model output. A spec that cannot pass its own purpose example is not precise enough, however exact its language is.

There is a second limit: precision cannot exceed what the tests can observe. For the pending-state timing in [014](../../logs/zheng-jj/014-highlight-loading-feedback.md), the Django test client renders one response and cannot see the browser between submission and response. The static tests can prove that the fixed script and template exist, but they cannot prove that the pending state appears at the right moment. We marked the timing as manual instead of pretending otherwise. That is more honest than a test that passes whether or not the browser behaviour works.

### 3. How Requirement Changes Flow

The flow that worked was: change the spec and record `Why:`, run the spec-critic for a High-risk slice, present a checkpoint to me, write tests that fail for the intended reason, write or update the plan, implement, verify, review, log, and open the pull request. Requirement changes were supposed to move in both directions: a reviewer finding that needs a spec change goes back to me and the spec-writer, not into a quiet code fix.

Two examples show why that matters. In [007](../../logs/zheng-jj/007-lead-home-page-visitors-to-sign-in.md), a review finding exposed a contradiction between the new home page and the production release verifier. The correct response was to stop and ask whether the slice should expand, not to change the verifier silently. I approved the expansion, and the specification and tests then moved together. In [014](../../logs/zheng-jj/014-highlight-loading-feedback.md), the spec-critic found that the new pending text conflicted with the existing plain-text rules. The resolution was an explicit exception in the specification, not an unexplained special case in the template.

The flow broke when a plan or test was treated as a separate source of truth. In [012](../../logs/zheng-jj/012-build-article-suggestions.md), four later CI runs failed because of test defects: the form was posted under the wrong field names, a fixture was missing, fixtures reused the same text as both a title and a body, and `make_account` shared one workspace per test. The feature was not failing; the tests were. In [005](../../logs/zheng-jj/005-read-knowledge-base-articles.md), a second review found that a test assertion had been weakened while fixing earlier gaps. If the tests are allowed to drift from the spec, later agents will treat the tests as the source of truth and preserve the drift.

### 4. Tests That Check Intent, Not Only Wording

The strongest tests in the project checked a rule against several kinds of evidence:

- **Criterion-linked tests.** Each acceptance criterion had an ID, and tests referenced that ID. A reviewer could ask which test would fail if a criterion were removed.
- **Deliberately broken copies.** The sign-in slice checked 30 injected defects, the demo-workspace slice checked 15, and the rate-limit slice checked 33 single-fault versions of a reference implementation. This is mutation testing in a small, practical form: it tests the tests.
- **Adversarial cases in the product suite.** Article suggestions tests covered hostile drafts, hostile replies, forged inputs, escaped output and workspace boundaries. The authorization matrix walked Django's registered routes, so a new route without an access decision would fail instead of being missed by a hand-written list ([011](../../logs/zheng-jj/011-authorization-matrix.md)).
- **End-to-end journeys.** The Requester and Support Officer journeys exercised demo-workspace creation, sign-in, ticket submission, resolution, article reading and sign-out across roles ([010](../../logs/zheng-jj/010-support-officer-end-to-end.md), [013](../../logs/zheng-jj/013-requester-end-to-end.md)).

The limits are equally important. The original suggestion tests confirmed the exact substring rule and therefore confirmed the wrong recall behaviour. The loading-feedback tests could not observe browser timing. And a test suite that contains defects can produce a red build that looks like a product failure: in [012](../../logs/zheng-jj/012-build-article-suggestions.md), the first red run was useful because it failed on the missing route and button, but four later red runs were test-side errors. I now use three questions: did the test fail for the right reason, did it pass for the right reason, and would it fail if the intended behaviour were removed?

## Basic Multi-Agent Software Engineering

### 1. Which Tasks Benefit from Specialised Agents

Specialisation paid off most where independence mattered. The spec-writer and spec-critic separated drafting from challenge. The test-writer could not modify production code, so it could not weaken a test to make an implementation pass. The implementer could not rewrite the spec to match its code. The reviewer and security-reviewer were read-only, so their findings had to be reported rather than quietly fixed. The devops role kept deployment and migration changes away from the general implementer. These separations caught defects that a single agent would plausibly have missed, including the full-workspace article read, the `InterfaceError` handling gap and the release-verifier contradiction.

Specialisation did not pay off for every task. The route-inventory slice needed one specification change and three focused tests, with no production change; I did that work directly ([009](../../logs/zheng-jj/009-route-inventory.md)). The log check was mechanical and faster as one scripted pass ([015](../../logs/zheng-jj/015-check-every-session-log.md)). The Support Officer end-to-end slice was also mostly test writing and review ([010](../../logs/zheng-jj/010-support-officer-end-to-end.md)). Running six agents on those tasks would add cost and handoff risk without adding much independent judgement. My rule now is: use specialists when the work needs a different permission, a different kind of expertise, or a genuinely independent check. Do not use them merely because the workflow diagram has a box for them.

### 2. Building and Testing the Agents Themselves

We treated the agents as part of the software. Each role file defines its inputs, allowed writes and forbidden writes; `.claude/` and `.codex/` adapters load those files; `check_scope.py` checks a role's changes against its scope; the pre-edit hook blocks an out-of-scope edit; and unit tests cover the hook and adapters. This was the right direction. It made the rules executable instead of relying on an agent to remember them.

The operational failures were revealing. The hook failed open when `python3` was missing ([001](../../logs/zheng-jj/001-plan-milestones-and-run-slice-3-sign-in.md)). It does not inspect shell commands, so it catches accidents rather than deliberate circumvention. Parallel agents sharing the development container overwrote each other's `/work` copy and dropped the shared test database mid-run; we fixed verification by making the container's `verify` use `flock` ([002](../../logs/zheng-jj/002-run-slice-4-demo-workspace.md), [003](../../logs/zheng-jj/003-run-slice-38-rate-limits.md)). The worktree's `.git` file pointed to a Windows path, so the container needed a throwaway repository for verification ([004](../../logs/zheng-jj/004-run-slice-11-production-migrations.md)).

Those are agent-infrastructure bugs, and they should be tested like any other code. Useful cases include: an out-of-scope edit through the editor, an out-of-scope write through the shell, two agents verifying at once, a missing runtime dependency, a stale base commit, and a handoff that is missing a required field. We tested some of these; we did not test all of them.

### 3. What One Agent Must Pass to the Next

The minimum useful handoff is not a summary of what the agent did. It is enough context for the next agent to continue without guessing:

- the issue and the exact specification IDs;
- the base commit and the files in scope;
- the commands run and their actual results;
- what changed, with commit hashes;
- decisions that still need a human, separated from decisions already taken;
- assumptions and anything not yet verified;
- any untrusted content seen.

Our handoff block asked for those fields, and the specification and plan held the lasting facts. That was better than passing a conversation transcript. But the evidence was often weaker than the template suggested. In [013](../../logs/zheng-jj/013-requester-end-to-end.md), the reviewer stalled and produced no handoff, so there was no independent report to check. In [012](../../logs/zheng-jj/012-build-article-suggestions.md), an implementer's status was `blocked` in one case only because it could not read CI, even though the work was complete. In [004](../../logs/zheng-jj/004-run-slice-11-production-migrations.md), the plan's estimate and the review's stale-lock finding were both correct, but the plan had fallen behind the code. A handoff can be complete in form and still hide the one fact the next agent needs.

The information that was most often lost was the reason for a decision. A commit hash and a passing test tell the next agent what happened, not why an alternative was rejected. The `Why:` line on spec commits helped, and the session logs helped more when they recorded corrections as corrections rather than folding them into a clean narrative. I would make the `Why:` and the rejected alternatives mandatory in every handoff that changes behaviour.

### 4. Where Errors and Malicious Instructions Slip Through

Our chain was spec-writer, spec-critic, test-writer, implementer, reviewer, security-reviewer and human. I saw errors slip through at six points:

1. **A shared wrong specification.** Article suggestions were precise, reviewed and implemented correctly, but the matching rule did not achieve the requirement's purpose. Every agent checked the same wrong assumption.
2. **A bundled approval.** The orchestrator turned a request into a list of recommendations, and a reply from me such as `go with recommendations` approved the whole list. That is efficient, but it makes a specific security decision easy to miss.
3. **A self-review.** When a reviewer stalled, the orchestrator completed the review. The work was checked, but not independently.
4. **A bad test.** A test can encode the wrong intent, be weakened during a fix, or strip the very markup it is supposed to inspect. The loading-feedback review found that a helper stripped every script and template, which could have hidden an injected script ([014](../../logs/zheng-jj/014-highlight-loading-feedback.md)).
5. **A cross-branch integration.** The Requester journey initially claimed to cover the Requester's features but did not exercise the article-suggestion flow. I had to extend it and stack it on the suggestion branch ([013](../../logs/zheng-jj/013-requester-end-to-end.md)). The route inventory and authorization matrix were valuable because they checked the assembled route table rather than a hand-maintained list.
6. **An unverified environment fact.** The production migration slice depended on Vercel setting `VERCEL` and `VERCEL_ENV`, but the provider facts were not verified. The guard was correct only if that fact was true ([004](../../logs/zheng-jj/004-run-slice-11-production-migrations.md)).

Malicious instructions were a different kind of risk. We did not observe a real injection in a session, and our tests used escaped attack payloads. The workflow's design was sensible: agents treat issue text, handoffs and test payloads as data, read issues only from collaborators, and report untrusted content. But the design is not a proof. The hook does not inspect shell commands, and a sufficiently persuasive instruction in an issue or pull request could still influence an agent that reads it. The honest statement is that our process defences were reviewed and tested in small ways, not red-teamed end to end.

### 5. Evidence Each Agent Should Leave Behind

The evidence I want from every run is:

- a handoff with status, inputs, changed paths, commands and actual results, decisions, assumptions and untrusted content;
- small commits labelled with the responsible agent and the issue;
- the base and head of every review range;
- the verification command and its real exit status;
- a plan that matches what was built;
- a session log that separates observed facts from assumptions and records cost.

I do not think the lesson is "collect more documents". It is "make the evidence falsifiable". A status of `done` is not evidence; a command and its output are. A sentence saying the tests pass is not evidence; the CI job and the commit are. A review with no findings is not evidence unless the reviewer names the range it read and the checks it ran. Our evidence often had the right shape but the wrong strength: several logs said cost was not measured, one review had no handoff, and I once briefly reported a green build when the CI job was red ([012](../../logs/zheng-jj/012-build-article-suggestions.md)). Those are exactly the failures a later agent cannot detect unless the record is honest about them.

## Lessons I Learnt

1. **Approve decisions, not bundles.** A checkpoint should enumerate each behaviour, scope expansion and security trade-off separately. `Yes to all` is not informed consent when the list was written by the agent that will implement it.
2. **Never let the producer be the only reviewer.** A stalled reviewer should leave the review incomplete, not hand the decision back to the orchestrator. If independence is unavailable, the pull request should say so.
3. **Test the purpose, not just the wording.** Every AI feature needs a realistic input that a user would expect to work, tested against recorded or real model output. Exact-match tests can confirm a rule that fails the product's intent.
4. **Treat tests as code under review.** Test defects, weakened assertions and helpers that hide the thing under test can create false confidence or a misleading red build. Mutation checks and independent test review are worth the extra time.
5. **Put the orchestrator under the same rules as everyone else.** The orchestrator is the most powerful agent, yet it is also the one that writes recommendations, decides when a review is finished and can edit outside any role's scope. Its actions need their own scope record and its approvals need a human, not itself.
6. **Preserve integration evidence.** A slice that passes alone can fail when combined with another route, migration or test. The authorization matrix, route inventory and end-to-end journeys were valuable because they checked the assembled system; I would make a combined-branch verification part of every stacked pull request.
7. **Write down what was not verified.** Hosted provider facts, browser timing, real-model behaviour and review independence were the places where our evidence was weakest. Naming them in the spec, the log and the pull request is better than letting a green test suite imply more than it proves.

If I ran this project again, I would keep the small slices, the fixed specifications and the separate test-writer and security-reviewer. I would change the approval mechanism, keep reviewers independent even when that means waiting, and make every AI feature prove one realistic end-to-end example before the team treats its specification as ready.
