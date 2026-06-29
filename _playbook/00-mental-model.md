# 00 — Mental model: what the platform is actually grading (Edition 2)

## Edition 2 key changes from Edition 1

- **Test deps in Dockerfile** (not vendored wheels in test.sh — see `04`)
- **Rubrics required** — you author a process-trace rubric with ≥3 negative criteria (`09`)
- **Milestones** — optional `steps/` layout for multi-stage tasks (`08`)
- **task.toml v2.0** — new fields: `version="2.0"`, `number_of_milestones`, `codebase_size`,
  `subcategories`, `[[steps]]` blocks for milestones (`10`)
- **No canary strings** in instruction.md (Edition 1 required them; Edition 2 removes them)
- **Digest-pinned base images** required with `@sha256:<digest>` on every FROM line
- **Canonical base image list** — use Terminal-Bench standard images or justify alternatives
- **Instruction style** — concise, human-sounding, 1 sentence to 3 paragraphs, no markdown
  structure, no step-by-step hints, no emojis

---

## What a Terminal-Bench 2.0 task is

You (a human expert) author a self-contained task: an environment (Docker image), an
instruction for the agent, a hidden test suite, and a reference ("oracle") solution. The
platform then:

- Runs the **oracle** solution through your tests → must score **reward 1.0**.
- Runs a **nop** (empty / do-nothing) solution → must score **reward 0.0**.
- Runs a stochastic **LLM judge** over your instruction → must rate it **sufficient**.
- Runs **static checks** over your repo structure → must all pass.
- Runs frontier agents (e.g. Opus, GPT-5.x) at the task → their pass rate is the
  **empirical difficulty**.

A task is "done" when all of these line up with your target.

## The single most important insight (cost us the most iterations)

**Difficulty and documentation are in tension, and sufficiency always wins.**

- Sufficiency *requires* you to document every behavior your tests check.
- If your difficulty came from a behavior the agent didn't know to handle (an
  **undocumented footgun**), then documenting it — which you are forced to do — hands the
  agent the answer and difficulty collapses.
- Therefore the **only stable difficulty** is difficulty that survives full documentation:
  the agent must **derive** a non-obvious solution, not **recall** a known one.

We learned this the hard way: every HARD verdict we got early was riding on a footgun
(self-teleport exclusion, output serialization shape, directed-edge asymmetry). Each time
sufficiency forced us to document it, the next eval came back MEDIUM or EASY. The pattern
only broke when difficulty became **algorithmic** (a custom fixpoint under a no-recursion
language constraint) — hard to implement correctly even when the spec is complete.

### Corollary: recall-class tasks cannot be reliably HARD

Textbook algorithms and named attacks (padding oracle, ECDSA nonce reuse, ret2libc,
Dijkstra, topological sort) are *recalled* by frontier models. Once documented, they're
easy. If you want HARD, the difficulty must be **derivation under a hostile constraint**
or **correctness density across interacting rules** — something memorization doesn't solve.

## Two independent risk axes — keep them separate in your head

1. **Will every criterion pass?** (oracle/nop/sufficiency/static/offline). This is an
   *engineering* axis. Failures here are about infra hygiene and are fully preventable with
   the checklists in `04` and `06`.
2. **Will it hit the target difficulty?** This is an *empirical* axis, measured by agent
   runs, and it's **stochastic** — the same task can read MEDIUM one run and HARD the next.
   Budget for at least one difficulty re-measurement.

Picking a task where axis 1 is structurally safe (pure-script, deterministic, offline) means
the *only* thing you're ever tuning is axis 2 — and a difficulty miss should be a cheap
in-place change, not an infra rebuild. Choose tasks with that property (see `07`).

## Difficulty is stochastic — do not over-react to one eval

We burned iterations "fixing" things in response to a single MEDIUM reading that was really
just run-to-run variance (e.g. we suspected a tag change altered difficulty; it didn't —
it was noise). Treat one difficulty reading as a noisy sample. Only act on a *consistent*
signal, and prefer difficulty changes that are cheap and reversible.
