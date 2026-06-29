# 06 — Do / Don't quick checklist (Edition 2)

Skim this before every build and every submission. Each line is a scar.

## DO

- **Make difficulty survive documentation.** Base HARD on derivation/constraint/composition,
  never on a secret. (`02`)
- **Document WHAT, never HOW.** Requirements and contracts in the instruction; keep the
  implementation/algorithm to yourself. (`03`)
- **Include a complete worked example** in the instruction (input → trace → exact output).
- **Pick tasks where you can guarantee the oracle** but the agent still struggles.
- **Prefer pure-script, deterministic, offline tasks** so the only variable is difficulty. (`07`)
- **Bake ALL test deps (pytest, requests, etc.) into the Dockerfile.** `test.sh` must not
  install anything at runtime. (`04` Trap 1 — Edition 2 rule change from Edition 1)
- **Use the exact reward block** (lowercase `rc=$?`, write `/logs/verifier/reward.txt`,
  no trailing `exit`). (`04` Trap 2)
- **Digest-pin every base image** with `@sha256:<digest>`. (`04` Trap 4)
- **Use a canonical Terminal-Bench base image** or include a written justification. (`04` Trap 5)
- **Install tmux + asciinema** — agent runtime requires both. (`04` Trap 6)
- **Run oracle AND nop in Docker** before every zip. (`05`)
- **Run `harbor run -a oracle`** before submitting — this is the canonical gate check.
- **Build `--platform linux/amd64`** always.
- **Treat one difficulty reading as noise.** Act on trends, prefer cheap/reversible edits.
- **Know blocking vs warning signals.** Warnings are accepted; don't chase them.
- **Make difficulty tunable in place** — adding an interacting rule, not rebuilding infra.
- **Use python3 for JSON** in scripts (no jq on the box).
- **Include docstrings on every test** — `informative_test_docstrings` LLMaJ check requires it.
- **Author a rubric with ≥ 3 negative criteria.** (`09`)
- **Write instructions in concise, human style** — no emojis, minimal markdown, 1 sentence to
  3 paragraphs max, no step-by-step walkthroughs. (`03`, Edition 2 instruction styling)
- **Use absolute paths** in `instruction.md` (e.g. `/app/output.txt` not `./output.txt`).

## DON'T

- **Don't install test deps in test.sh.** Edition 2 requires all test deps in the Dockerfile.
  (This reverses the old "vendored wheels" advice.)
- **Don't build difficulty on an undocumented footgun.** Sufficiency forces you to document
  it and difficulty collapses. We proved this 4+ times.
- **Don't pick textbook/recall tasks for HARD** (padding oracle, nonce reuse, ROP, Dijkstra,
  topo-sort). Frontier models recall them → EASY once documented.
- **Don't add implementation hints to pass sufficiency.** It hands the agent the answer.
- **Don't document the algorithm/builtin/data-structure** to over-satisfy the judge.
- **Don't copy solution/ or tests/ in the Dockerfile** — platform mounts them separately.
- **Don't use curl or any network at test time** (`allow_internet = false`).
- **Don't add a trailing `exit` after the reward block** in test.sh — CI will fail.
- **Don't use `${RC}` or `$RC` (uppercase)** — use lowercase `rc=$?`.
- **Don't trust a local `pytest` pass** — only Docker `test.sh` → `reward.txt` counts.
- **Don't over-react to a single MEDIUM/EASY eval.** It's stochastic.
- **Don't chase non-blocking warnings.** They don't fail the task.
- **Don't optimize for "an agent can solve it."** Solvability is not a gate.
- **Don't use floating Docker tags** — always `@sha256:<digest>`.
- **Don't include CLAUDE.md, skills.md** or AI-framework files in the environment.
- **Don't use canary strings** in instruction.md (Edition 2 removed them).
- **Don't put the task name in instruction.md** (no "# my-task-name" header).
- **Don't use heredocs in the Dockerfile** to embed source files.
- **Don't use recursive chmod/chown** in the Dockerfile.
- **Don't write >3 paragraphs of instructions** — concise is 150–200 words.
- **Don't use markdown in instructions** — no headers, bullets, tables, bold, emojis.
- **Don't write step-by-step walkthroughs** in instruction.md or environment spec files.
- **Don't reference `/tests/` or `/solution/` in instructions** — HIGH severity; reveals the
  framework to agents. Remove "do not modify /tests/" style statements.
- **Don't reference `/tests/` or `/solution/` in rubrics** — HIGH severity. Same reason.
- **Don't put blank lines between rubric entries** — reviewers flag this as format violation.
- **Don't have 0 negative criteria in any milestone's rubric block** — at least 1 per block.
- **Don't exceed 40 positive points in any rubric block** — each milestone block is capped at 40.
- **Don't put implementation in solve.sh** for milestone tasks — it's a wrapper only; the
  implementation goes in `solveN.sh`.
- **Don't copy unchanged files across milestone solutions** — each milestone has only its delta.
- **Don't include `workdir/` directories inside milestone step folders.**
- **Don't use `COPY . /app`** in the Dockerfile — risks leaking solution/tests.
- **Don't include unnecessary files**: `.gitignore`, `.gitattributes`, `scripts/`, `rubric.json`,
  `pyproject.toml`, `.ruff_cache`, `wheels/` in tests/, or a zip file inside the zip.
- **Don't add `name`, `description`, or `difficulty_explanation`** fields to task.toml.
- **Don't add unnecessary inline comments** to task.toml — reviewers flag them.
- **Don't omit the PWD guard** in test.sh.
- **Don't put `mkdir -p /logs/verifier` after other logic** — it must be the first thing after
  the PWD guard.
- **Don't put server startup or build logic in test.sh** — those go in the solution or Dockerfile.
- **Don't use a synthetically-generated file for `long_context`** — it must be a real document
  ≥50k tokens that can't be keyword-searched; reviewers check this.
- **Don't make oracle solution flaky** (retries needed for injected errors, timing-sensitive).
  The oracle path must be deterministic and complete on every run.
- **Don't commit/push unless the user asks.**

## The two questions to ask before committing to a task

1. **Can I guarantee a clean oracle?** (If authoring the solution is itself research → risk on
   Gate 1.)
2. **Does the difficulty survive a perfect spec?** (If no → it'll collapse under sufficiency.)

If both are "yes," the task can pass every gate. If either is "no," pick a different task or
re-architect the difficulty lever first.
