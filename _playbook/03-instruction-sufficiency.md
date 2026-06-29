# 03 — Passing instruction sufficiency without killing difficulty

The sufficiency judge is a **stochastic LLM** that reads `instruction.md` and decides whether
a competent agent could know *what* is required. It is the gate most in tension with difficulty.

## The golden rule

**Document WHAT is required, never HOW to implement it.**

- ✅ "Teleport to room R is allowed iff the scan's minimum total energy cost to reach R is
  ≤ `teleport_charge`." (a behavior / requirement)
- ❌ "Use a Bellman-Ford relaxation over 20 unrolled steps with a min() over candidate costs."
  (an implementation — this hands over the answer and kills difficulty)

Documenting the *requirement* satisfies sufficiency. Withholding the *implementation* preserves
derivation difficulty (`02`). This separation is the whole game.

## What sufficiency forces you to document (and you must)

Every behavior any test checks. If a test asserts behavior X, the instruction must let the
agent know X is expected. The judge specifically hunts for "undocumented footguns" — behaviors
a test rewards/punishes that the instruction never mentions. Leaving one in = flag = fail.

This is exactly why footgun difficulty is unstable: the judge makes you surface it.

## Tactics that worked for us

1. **A complete worked example.** Concrete input → step-by-step trace → exact expected output.
   This reliably satisfies the judge that the behavior is knowable, *without* revealing an
   implementation strategy. Our §8 worked example (a sample state walked through to the final
   reachable set) was load-bearing for passing sufficiency.
2. **State the boundary rules explicitly.** Equality cases (`cost == charge` is allowed),
   exclusions (current room is never in the result set), and "missing field means X" defaults.
   These are the behaviors tests check; name every one.
3. **Field-by-field input/output contract.** A table of every input field (with "optional /
   missing means…") and the exact output shape. Ambiguity here is the #1 footgun source.
4. **Name the wrong shortcuts as out-of-scope traps, in behavior terms.** "Note: hop-count is
   not the metric; cost is" tells the agent the requirement without telling it the algorithm.
5. **Write for the worst stochastic roll.** Since the judge is non-deterministic, over-document
   the *what*. Redundant clarity costs nothing and protects against a bad sample.

## Tactics that BACKFIRED (do not repeat)

- ❌ **Adding implementation hints to "help."** We once added a "Verify via POST" style hint
  and an explicit reference to the right builtin. It made the agent clear the footgun → EASY.
  Sufficiency does **not** require hints; it requires *requirements*. Never add implementation
  guidance to chase a sufficiency pass — remove ambiguity in the *spec* instead.
- ❌ **Documenting the implementation to be safe.** Describing *how* (the algorithm, the data
  structure, the builtin to call) over-satisfies the judge and destroys difficulty. Document
  the contract, stop there.

## The reconcile move when sufficiency flags AND you need difficulty

If the judge flags an undocumented behavior:

1. Document the **requirement/behavior** in `what`-terms (satisfies the judge).
2. Make sure your difficulty does **not** rest on that behavior being secret — migrate the
   difficulty to a derivation/composition lever (`02`) that stays hard *with* the behavior
   documented.

That migration is the move that finally let us hold HARD and sufficiency PASS at the same time.

## Must not read as LLM-generated (reviewers flag this explicitly)

Three separate reviewer comments called out tasks as "fully LLM-generated" and rejected on
that basis alone — even when the task logic was otherwise sound. Reviewers pattern-match on:

- Prescriptive inline comments everywhere (`# Step 1: Install dependencies`, `# Now run tests`)
- Every requirement decomposed into a bullet point
- Identical formal tone across all milestones with no variation
- Unnecessary files left in the repo (`.gitattributes`, `scripts/`, `pyproject.toml`) — signals
  the author ran a generator and didn't clean up
- Bold markers on every key term
- Overly polished, hyper-structured prose that reads like a GPT response to "write a task spec"

**Positive markers of human-authored instructions:**
- Varied sentence length — some short, some longer
- Occasional informality ("the data lives in...", "you'll need to...")
- Focus on the problem, not the process — describes what's broken or needed, not how to fix it
- Schema or format details stated once, plainly, not in a table with headers
- No bullet-point decomposition of every sub-requirement

**Self-test before submitting:** read your instruction.md aloud. If it sounds like a ChatGPT
response to "write technical documentation for X", rewrite it. It should sound like a developer
describing a real problem to a colleague.

## Instruction styling (Edition 2 — reviewers enforce this strictly)

Reviewer feedback consistently flags instruction style as a rejection reason. The rules:

- **Prose only** — no headings, no sections, no bullet lists, no tables, no bold text, no emojis.
  Reads like an engineer writing a Slack message, not a spec document.
- **150–200 words, 1–3 paragraphs.** Longer is almost always wrong.
- **Conversational tone** — "we need to…", "the data lives in /app/data.db" style.
- **No step-by-step walkthroughs** — document the *what*, not the *how*.
- **Never reference `/tests/` or `/solution/`** — these are internal framework paths. Mentioning
  them gives agents hints about the framework and how to cheat. Reviewers flag this as HIGH severity.
  Statements like "Do not modify /tests/ or /solution/" must be removed.
- **No "validation traps"** language or internal-note phrasing — these read like LLM artifacts
  and don't constitute clear requirements.
- **No canary strings, no task name** as the first heading.
- **Absolute paths only** (e.g. `/app/output.txt` not `./output.txt`).
- **If a schema is too large**, put it in a file in the environment and reference its path.
- **Milestone instructions:** milestone 1 includes overall context; later milestones are shorter
  but fully self-contained. Each is plain prose.

## Pre-submit sufficiency self-check

- [ ] Every behavior a test checks is mentioned in the instruction (in requirement terms).
- [ ] Every input field documented, including optional fields and missing-value defaults.
- [ ] Exact output shape/format documented.
- [ ] All boundary/equality/exclusion cases stated.
- [ ] A complete worked example present (if complexity warrants it).
- [ ] No implementation/algorithm/builtin hints that would hand over the solution.
- [ ] No references to `/tests/`, `/solution/`, or internal framework paths.
- [ ] No headings, bullet lists, tables, bold markers, or heavy markdown.
- [ ] 150–200 words, 2–3 paragraphs, plain prose.
- [ ] Re-read as a hostile judge: "is any rewarded behavior a surprise?" If yes, document it
      and move difficulty off it.
