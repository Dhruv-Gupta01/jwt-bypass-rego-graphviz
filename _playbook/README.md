# Snorkel Terminal-Bench — Task Authoring Playbook (Edition 2)

Hard-won learnings from authoring tasks end-to-end, updated for Edition 2. Drop this folder
into any task repo and read it before you start building. Every file is a checklist or a war
story with a concrete fix, not theory.

## Read order

1. **[00-mental-model.md](00-mental-model.md)** — What the platform is actually grading,
   Edition 2 key changes, and the single structural insight that took the most iterations.
2. **[01-the-five-gates.md](01-the-five-gates.md)** — The gates a task must pass
   (oracle, nop, sufficiency, static checks, difficulty) and what each one really tests.
3. **[02-difficulty-engineering.md](02-difficulty-engineering.md)** — How to reach and
   *hold* HARD. Core lesson: difficulty must survive full documentation.
4. **[03-instruction-sufficiency.md](03-instruction-sufficiency.md)** — How to pass the
   stochastic LLM sufficiency judge without collapsing difficulty.
5. **[04-static-checks-and-infra.md](04-static-checks-and-infra.md)** — Every static-check
   and infra trap with the exact fix. **Critical Edition 2 change:** all test deps baked into
   Dockerfile (NOT vendored wheels in test.sh).
6. **[05-build-and-verify-loop.md](05-build-and-verify-loop.md)** — Docker build/oracle/nop
   verification loop, Harbor CLI commands, and zip/submit mechanics.
7. **[06-do-and-dont.md](06-do-and-dont.md)** — Condensed do/don't checklist. Skim before
   every submission.
8. **[07-task-selection.md](07-task-selection.md)** — How to pick a task that can pass every
   gate with fewest iterations.
9. **[08-milestones.md](08-milestones.md)** — Edition 2 milestone task structure (`steps/`
   layout, per-milestone tests/solutions, task.toml `[[steps]]` blocks).
10. **[09-rubrics.md](09-rubrics.md)** — Edition 2 rubric authoring guide (format rules,
    negative criteria requirement, milestone rubric headers).
11. **[10-task-toml-reference.md](10-task-toml-reference.md)** — Complete task.toml v2.0
    schema reference for both non-milestone and milestone tasks.

## The one-sentence summary

> A Terminal-Bench task passes when the **oracle solution scores 1.0**, the **empty/nop
> solution scores 0.0**, **every tested behavior is documented** (sufficiency), **all
> static checks are green**, the **measured difficulty is < 80% agent pass rate**, and a
> **rubric with ≥3 negative criteria** is authored — and the only *stable* HARD comes from
> difficulty a frontier model must **derive**, not **recall**, because sufficiency forces you
> to document everything anyway.
