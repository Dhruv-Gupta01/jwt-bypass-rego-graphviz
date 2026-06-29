# 02 — Difficulty engineering: reaching and HOLDING the target

This is the file that took the most iterations to learn. Read it twice.

## The core law

> **Stable difficulty = difficulty that survives full documentation.**

Sufficiency (Gate 3) forces you to document every tested behavior. So any difficulty that
depends on the agent *not knowing* something evaporates the moment you document it. Plan
your difficulty as if the agent has read a perfect, complete spec — because it effectively has.

## The difficulty taxonomy

### ❌ Footgun difficulty (UNSTABLE — avoid as your primary lever)

Difficulty from an undocumented surprise: an output must be serialized a specific way; a
node must be excluded from a set; an edge is directed not undirected. These give a HARD
reading *only while undocumented*. Sufficiency then forces you to document them → EASY.

War story: we got HARD four separate times on footguns (self-teleport exclusion, output
object-vs-string shape, directed wormhole asymmetry). Every single time, documenting the
footgun (required) dropped us to MEDIUM/EASY on the next eval. We chased this loop for many
iterations before accepting it can't work.

### ❌ Recall difficulty (UNSTABLE — looks hard, isn't)

Difficulty from a "hard" but *well-known* algorithm or attack. Frontier models have these
memorized. Examples: CBC padding oracle (Cryptopals 3.17), ECDSA nonce reuse, ret2libc/ROP,
Dijkstra, A*, topo-sort. Documented or not, the model recalls the solution → EASY/MEDIUM.

### ✅ Derivation difficulty (STABLE — your primary lever)

The agent must *invent* a non-obvious solution that no documentation can hand it:

- **Hostile constraint that breaks the obvious approach.** E.g. the algorithm everyone
  knows uses recursion, but the language forbids recursion (our winning Rego lever: a
  fixpoint that must be manually unrolled into N bounded steps). The model knows the
  *concept* but must derive the *implementation* under the constraint.
- **Information-theoretic / resource constraint.** E.g. coordinate two agents through a
  16-byte-per-turn channel — no textbook protocol exists, the agent must design an encoding.
- **Novel composite algorithm.** A bespoke combination with no reference implementation,
  e.g. a joint fixpoint over *two interacting quantities at once* (cost AND collected items),
  where neither a connectivity builtin nor a single-pass shortest path is sufficient.

### ✅ Correctness-density difficulty (SEMI-STABLE — good secondary lever)

Many individually-documentable rules whose *interaction* is what trips the agent. Each rule
is simple; getting all of them simultaneously right is not. Tends to land MEDIUM–HARD, and
crucially it's **cheap to tune in place** (add more interacting rules without changing infra).
Example: monorepo version-bump propagation where a package bumps for its own commit AND a
transitive dependency major at once, with diamond-dedup and version-range-aware republish sets.

## How our winning Rego difficulty was built (concrete template)

The final HARD lever — an "energy-budget joint fixpoint" — combined three stable sources:

1. **Hostile constraint:** OPA/Rego forbids recursive rules → the fixpoint must be unrolled
   into a bounded chain of relaxation steps by hand.
2. **Novel composite:** the scan relaxes *minimum cost* and grows an *effective item set*
   simultaneously; collecting an item opens a door that lowers a cost that brings a new room
   (and its items) into reach. Neither `graph.reachable` (connectivity, no distance) nor a
   one-pass shortest path computes this.
3. **Correctness density:** directed conduits (asymmetric), per-edge costs, a charge cutoff
   where `cost == charge` is allowed, and en-route loot that's collected-but-still-unaffordable.

All of it fully documented in the instruction (with a worked example) — and *still* hard,
because implementing a recursion-free Bellman-Ford-with-item-unlocks is derivation work.

## A practical recipe for "engineer it to HARD on purpose"

1. Start from an algorithm you can implement correctly as the oracle (protects Gate 1).
2. Add a **hostile constraint** that forbids the obvious implementation (language limit,
   resource budget, no-recursion, tight performance/memory bound).
3. Add **2–3 interacting rules** whose combination has a non-obvious correct behavior.
4. Make at least one trap a **plausible-but-wrong shortcut** the agent will reach for
   (e.g. "count hops" when the answer needs "sum costs"; "symmetrize edges"; "collect all
   loot up front"). Add tests that specifically catch each wrong shortcut.
5. Document all of it completely. If it's still hard with a perfect spec, you have stable HARD.

## Tuning without re-churning infra

Pick tasks where a difficulty miss is fixed by **editing the oracle/tests/instruction**, not
rebuilding the harness. Correctness-density and rule-interaction levers are ideal: if the
first eval reads MEDIUM, you add another interacting rule and a few test cases — same scaffold,
same day. Avoid tasks where raising difficulty means re-architecting the environment.

## Don't over-react to one difficulty reading

Difficulty is a noisy measurement. We once attributed a MEDIUM reading to an unrelated tag
change; it was just variance. Confirm a trend across readings before making structural changes,
and prefer cheap/reversible difficulty edits.
