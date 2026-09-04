---
description: Ask the LLM Council a hard question (architecture decision or open research question)
argument-hint: <die Frage>
---

Run the LLM Council on this question: $ARGUMENTS

Follow the `council` skill:

1. Apply the gatekeeper first. If a test, a benchmark, or reading the code settles
   this question, say so and answer it directly instead of spending ~9 API calls.
2. Gather the context that actually bears on the question from this repository -
   the relevant files, the constraints, what has already been ruled out.
3. Pick a profile (`decision` for technical decisions, `research` for open
   questions) and run `council_start`, then poll `council_result`.
4. Report: recommendation, then where the council disagreed, then risks, then next
   steps, then cost and duration.
5. Offer to record it with `council_write_adr`.
