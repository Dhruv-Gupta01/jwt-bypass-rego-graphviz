# 01 — The five gates

Every task must clear all five. Know exactly what each tests and the failure mode.

---

## Gate 1 — Oracle reward = 1.0

Your reference solution, run through your hidden tests, must score a perfect 1.0.

- **What it really tests:** that the task is solvable *by you*, and that your tests agree
  with your own solution. If you can't write a clean oracle, you don't have a task.
- **Failure mode we hit:** tests that depended on a behavior the oracle didn't implement,
  or a reward script whose exit-code logic didn't actually write `1` on success.
- **Guard:** run the oracle in the real Docker image every single time before zipping
  (see `05`). Never assume — a green local `opa test` / `pytest` is not the same as the
  platform's `test.sh` writing `reward.txt`.

> **Authoring corollary:** the most reliably-HARD tasks are often the hardest for *you* to
> write a correct oracle for. Pick a task where you can *guarantee* the oracle (you fully
> understand the algorithm) but the agent still struggles (constraint/composition). If
> authoring the oracle is itself a research problem, oracle=1.0 becomes a real risk.

---

## Gate 2 — nop reward = 0.0

A do-nothing / empty solution must score 0.0.

- **What it really tests:** that your tests actually discriminate — that passing requires
  real work, not a vacuous default.
- **Failure mode to watch:** tests that pass trivially (e.g. asserting a file *can* be
  created, or a default-empty output that happens to match). If nop scores > 0, your tests
  are too lenient.
- **Guard:** run the nop in Docker and confirm it scores 0 and that a *meaningful* number
  of tests fail (we saw e.g. "82 failed, 47 passed" — the 47 passing were trivial setup
  assertions, which is fine as long as reward is 0).

---

## Gate 3 — Instruction sufficiency = PASS

A stochastic LLM judge reads `instruction.md` and decides whether a competent agent has
enough information to know *what* is required (not *how* to implement it).

- **What it really tests:** every behavior your tests check must be discoverable from the
  instruction. Undocumented "gotcha" behaviors get flagged and you're forced to document them.
- **Why it's dangerous:** documenting a footgun often kills your difficulty (see `00`).
- **It's stochastic:** the same instruction can pass once and flag once. Write defensively
  so it passes on the *worst* roll, not the average.
- Full tactics in `03`.

---

## Gate 4 — Static checks = PASS

Mechanical repo-structure checks. These are 100% preventable. Full list and fixes in `04`.
Highlights: no test dependencies baked into the Dockerfile, correct reward-script format,
no network calls at test time, minimum file count, LF line endings, zip layout.

---

## Gate 5 — Difficulty = target (HARD / MEDIUM / EASY)

Measured empirically as the frontier-agent pass rate.

- HARD ≈ agent pass rate ≤ ~1 in 5.
- MEDIUM ≈ ~40–60%.
- EASY ≈ ~80%+.
- **Stochastic** — one reading is a noisy sample. See `02` for how to reach and *hold* the
  target, and `00` for not over-reacting to a single eval.

> **Note on "solvability":** at least one agent run passing all tests is *not* required and
> is *not* a gate. Agents (even the strongest) are allowed to all fail. Do not optimize for
> solvability; optimize for the oracle passing and the difficulty target.
