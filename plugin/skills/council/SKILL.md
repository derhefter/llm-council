---
name: council
description: Ask a council of several LLMs a hard question and get a synthesized answer with explicit dissent. Use when a decision is expensive to reverse and has no cheap ground truth - architecture and stack choices, refactoring strategy, trade-off questions, open research questions. Do NOT use for questions a test, a benchmark, or reading the code can settle.
---

# LLM Council

Several models answer independently, rank each other's answers anonymously, and a
chairman synthesizes the result. Costs ~9 API calls and 1-3 minutes per question.
That price only pays off for a narrow class of questions.

## Gatekeeper - ask this first

Run the council only if **all three** hold:

1. **Expensive to reverse.** Getting it wrong costs days, not minutes.
2. **No cheap ground truth.** No test, type check, benchmark, or 5 minutes of
   reading the code settles it.
3. **Diversity buys coverage.** The question is open enough that different models
   would genuinely explore different branches.

If any fails, answer it yourself and say why the council was not worth it. A bug,
a failing test, an API question, "does this compile" - all of these are cheaper to
verify than to deliberate.

## Picking a profile

- `decision` (default) - architecture and technical decisions. Rubric weighs
  correctness, trade-off honesty, actionability, risk. Output ends in a concrete
  recommendation.
- `research` - open questions where coverage matters more than a verdict.
- `quick` - two models, no peer review, ~30s. A cheap second opinion, not a
  deliberation. Use `council_ask` for this one.

Call `council_profiles` if unsure.

## Workflow

1. **Gather context yourself.** The council sees nothing but what you send:
   - the files that actually bear on the question (paths via `files`)
   - constraints, prior decisions, and what has already been ruled out (`context`)
   - relevant parts of CLAUDE.md, and `git diff` when the question is about a change
   Do not dump the whole repo. Pick what a senior colleague would need.
2. **State the question so it stands alone.** Name the options, the constraints,
   and what "good" means here. A vague question produces four vague answers and an
   expensive average of them.
3. **Run it.** `council_start(question, profile, context, files)` returns a
   `run_id`; poll `council_result(run_id)` until status is `complete`. Use
   `council_ask` only for the quick profile.
4. **Report back** in this order:
   - the recommendation, in one or two sentences
   - **where the council disagreed** - this is the most valuable part; a unanimous
     council is either an easy call or a shared blind spot, and say which you think
     it is
   - risks and what would have to be true
   - concrete next steps
   Note cost and duration from `run_stats` at the end.
5. **Offer the ADR.** Ask whether to record the decision:
   `council_write_adr(run_id)` writes `docs/decisions/NNNN-slug.md` in the current
   repo. Do this for decisions the team will have to remember, not for every run.

## What the council output is not

The peer ranking measures how models rate each other's writing. It is not a
correctness measure and correlates with thoroughness and style. Treat it as a
weak signal, report it as such, and never present it as a verdict.

Council members also currently rank their own answers, and the chairman sees which
model wrote what. Both bias the result toward whoever writes most confidently. Say
so when the ranking is close.
