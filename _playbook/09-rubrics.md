# 09 — Rubrics (Edition 2)

Every submission must include a rubric. Rubrics evaluate the **process trace** (what the agent
did in the terminal), not just the final pytest result.

## Workflow

1. Submit your task ZIP on the Snorkel Platform **with the rubric checkbox checked**.
2. After CI runs, your submission returns with an auto-generated rubric in the textbox.
3. **Edit the rubric** for accuracy and completeness — the generated one is a starting point.
4. **Uncheck the checkbox** before you send to reviewer. (Submitting with it checked
   overwrites your edited rubric.)

## Format rules (strict — CI validates these AND reviewers enforce them)

Every criterion line must:
- **Start with "Agent"** — no exceptions
- **End with `, +N` or `, -N`** (comma then space then score) — exactly this format
- Use **only values ±1, ±2, ±3, or ±5** — never ±4, never ±6/7/8, never decimals
- Be a **single line**
- Have **no blank lines between entries** — reviewers explicitly flag blank-line-separated
  rubrics as incorrectly formatted

Example (correct — no blank lines):
```
Agent reads the Terraform state file before making changes, +2
Agent runs terraform plan before terraform apply, +3
Agent applies changes without reviewing the plan output, -3
Agent runs terraform destroy on the wrong workspace, -5
Agent verifies the output file was created at /app/result.json, +1
```

## Score scale

| Importance | Values |
|---|---|
| Critical — safety, core correctness | ±5 |
| Major — reliability, verification, error recovery | ±3 |
| Minor — inspection hygiene, tool flags | ±1 to ±2 |

## Negative criteria requirements

**Non-milestone tasks:** at least **3 negative criteria** total.

**Milestone tasks:** at least **1 negative criterion per milestone** (in addition to the
overall 3-total minimum).

Reviewers flag tasks with 0 negatives in any milestone block as a defect.

## Cumulative score range

**Non-milestone tasks:** 10–40 points total (sum of all positive criteria).

**Milestone tasks:** 10–40 points per milestone. The sum of positives within each `# Rubric N`
block must independently fall in this range. A total of 56 positive points in one block is
rejected; each block must be ≤40.

- 1 milestone → 10–40 pts total
- 2 milestones → 20–80 pts total
- 3 milestones → 30–120 pts total

## Milestone rubric format

Use `# Rubric N` headers (exact format) to split by milestone, followed immediately by that
milestone's criterion lines with **no blank lines** between entries:

```
# Rubric 1
Agent inspects existing files before modifying them, +2
Agent creates the required schema at /app/schema.sql, +3
Agent runs SQL queries to validate the output, +2
Agent drops the entire database instead of a single table, -5
Agent repeats the same failing query 3 or more times, -1

# Rubric 2
Agent verifies milestone 1 artifacts still exist, +1
Agent runs the migration with the correct flags, +3
Agent skips rollback testing, -2
```

**Non-milestone tasks:** flat list, no `# Rubric N` headers needed (one optional `# Rubric 1`
is tolerated but not required; `# Rubric 2+` is only for milestone tasks).

## What NOT to include — HIGH SEVERITY failures

These are the most common reviewer rejections:

- **Never reference `/tests/` or `/solution/`** — HIGH severity. Referencing these paths
  reveals the framework's internal layout to agents. Reviewers will reject on this alone.
- **Never reference testing logic** — No "Agent runs the unit tests", no "Agent checks
  test results", no "Agent reads test_outputs.py". Tests run automatically; don't rubric them.
- **Never reference `task.toml` or `instruction.md`** — The agent has no context about
  these files and should not be rubric'd on them.
- **Never reference oracle/nop runs** — "Oracle passes consistently" is not a valid criterion.

## Phrasing rules

All criteria must be **positively phrased** (a statement of what the agent did), even when
assigning a negative score:

```
# Bad phrasing — negatively framed
Agent does not validate output format, -2

# Good phrasing — positive statement, negative score
Agent skips output format validation, -2

# Bad — references internal files
Agent reads the /solution/solve.sh for reference, -3

# Bad — references tests
Agent runs pytest on the /tests/ directory, -2
```

## Examples of good vs bad criteria

| | Good | Bad |
|---|---|---|
| Specific | `Agent runs terraform init before terraform plan, +1` | `Agent sets up correctly, +1` |
| Binary | `Agent reads /app/config.json before editing, +2` | `Agent handles config files well, +2` |
| Value | `Agent corrupts the database schema, -5` | `Agent makes errors, -4` (forbidden 4!) |
| No /tests/ | `Agent validates the output at /app/result.json, +2` | `Agent passes all unit tests, +3` |
| No blanks | entries flow continuously | blank line between every entry |

## Quick self-check before submitting

- [ ] Every line starts with "Agent".
- [ ] Every line ends with `, +N` or `, -N`.
- [ ] Only values ±1, ±2, ±3, ±5 used (no ±4, no ±6/7/8).
- [ ] **No blank lines between criterion entries.**
- [ ] At least 3 negative criteria in total.
- [ ] At least 1 negative criterion per milestone (if milestone task).
- [ ] No references to `/tests/`, `/solution/`, test files, or testing logic.
- [ ] No references to `task.toml`, `instruction.md`, or oracle/nop runs.
- [ ] Criteria are positively phrased (negative scores for bad behaviors, not negative sentences).
- [ ] Milestone tasks: each milestone has a `# Rubric N` header.
- [ ] Score range: 10–40 per milestone block (or 10–40 total for non-milestone).
- [ ] Rubric checkbox is **unchecked** before sending to reviewer.
