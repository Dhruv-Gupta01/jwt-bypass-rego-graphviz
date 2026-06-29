# 08 — Milestones (Edition 2)

Milestones divide a complex task into sequential, independently-verified subtasks. The Harbor
framework calls them "multi-step tasks" — the terms are interchangeable.

## When to use milestones

Use when the task naturally breaks into stages where **each stage is a prerequisite for the
next**. Milestone tasks must have **at least 2 milestones** (a single milestone = non-milestone
task). Balance: most tasks should have 2–5 milestones; don't over-segment.

## Directory layout

```
task-root/
├── task.toml                       # includes [[steps]] blocks — see below
├── environment/
│   ├── Dockerfile                  # shared container for all milestones
│   └── .dockerignore
└── steps/
    ├── milestone_1/
    │   ├── instruction.md          # prompt for milestone 1 only (include overall context)
    │   ├── tests/
    │   │   ├── test.sh             # produces /logs/verifier/reward.txt
    │   │   └── test_m1.py          # class TestMilestone1
    │   └── solution/
    │       ├── solve.sh            # wrapper — just calls solve1.sh
    │       └── solve1.sh           # oracle scoped ONLY to milestone 1
    ├── milestone_2/
    │   ├── instruction.md
    │   ├── tests/
    │   │   ├── test.sh
    │   │   └── test_m2.py          # class TestMilestone2
    │   └── solution/
    │       ├── solve.sh
    │       └── solve2.sh
    └── milestone_3/
        └── ...
```

**Critical:** no root-level `instruction.md`, `tests/`, `solution/`, or `milestone_x.md`.
Everything per-milestone lives under `steps/milestone_N/`.

## task.toml for milestone tasks

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "software-engineering"
subcategories = []
number_of_milestones = 3        # must equal the number of [[steps]] blocks
codebase_size = "small"
languages = ["python", "bash"]
tags = ["duckdb", "terraform", "sql"]
expert_time_estimate_min = 60
junior_time_estimate_min = 120

[environment]
build_timeout_sec = 600.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
workdir = "/app"                # milestone tasks: set the shared working directory here

# No top-level [agent] or [verifier] — replaced by per-milestone [[steps]] blocks

[[steps]]
name = "milestone_1"

[steps.agent]
timeout_sec = 1200.0

[steps.verifier]
timeout_sec = 450.0

[[steps]]
name = "milestone_2"

[steps.agent]
timeout_sec = 1200.0

[steps.verifier]
timeout_sec = 450.0

[[steps]]
name = "milestone_3"

[steps.agent]
timeout_sec = 1200.0

[steps.verifier]
timeout_sec = 450.0
```

## solve.sh wrapper pattern

Each milestone's `solve.sh` is a thin wrapper:

```bash
#!/bin/bash
set -euo pipefail
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
bash "$SCRIPT_DIR/solve1.sh"
```

## Per-milestone test file pattern

```python
"""Tests for milestone 1: <description of what this milestone achieves>."""
import pytest
from pathlib import Path


class TestMilestone1:
    def test_output_created(self):
        """Verify the output file from milestone 1 was created at /app/output.txt."""
        assert Path("/app/output.txt").exists()

    def test_schema_correct(self):
        """Verify the output has the expected JSON schema."""
        import json
        data = json.loads(Path("/app/output.txt").read_text())
        assert "result" in data
```

## Key rules

1. **Sequential dependency:** milestone 2 cannot pass if milestone 1 fails.
2. **Shared filesystem:** files left by milestone 1 are visible to milestone 2. Intentional —
   but if milestone 2 needs a clean slate, `solve2.sh` must reset it explicitly.
3. **Per-milestone scope:** `solveN.sh` and `test_mN.py` are scoped ONLY to that milestone.
   `solve1.sh` ↔ `test_m1.py`, `solve2.sh` ↔ `test_m2.py`, etc.
4. **`solve.sh` is ONLY a wrapper** — it must just call `solveN.sh`. Do NOT put the actual
   implementation in `solve.sh`. Reviewers flag this as a defect.
5. **Milestone 1 instruction.md** should include overall task context (the first thing the agent sees).
   Later milestones can be shorter but must be self-contained — no "see milestone 1".
6. **`number_of_milestones`** in `[metadata]` must equal the number of `[[steps]]` blocks.
7. **No `[agent]` or `[verifier]` top-level** — only per-step `[steps.agent]` and `[steps.verifier]`.
8. **No `workdir/` directories inside milestone folders** — reviewers flag these. The
   `workdir` setting belongs only in `[environment]` in task.toml, not as a directory.

## Incremental solution structure — reviewers flag this heavily

Each milestone's solution must contain **only the files introduced or modified for that
milestone**. Do not copy unchanged files forward.

```
# /app/parser.py is created in milestone 1, extended in milestone 2

# steps/milestone_1/solution/solve1.sh — creates /app/parser.py
# steps/milestone_2/solution/solve2.sh — modifies /app/parser.py (cumulative changes)
# steps/milestone_3/solution/solve3.sh — further modifies /app/parser.py (all prior + new)
```

The intended workflow: changes to `/app` persist across milestones. Each `solveN.sh` applies
**only its incremental delta**. A file that is unchanged in milestone 2 must NOT appear in
`steps/milestone_2/solution/`.

When a single file spans multiple milestones:
- `solve1.sh` writes the initial version
- `solve2.sh` applies changes to get the milestone-2 version (not a full copy of solve1's output)
- `solve3.sh` applies changes to get the milestone-3 version

Reviewers will reject if the same unmodified file is duplicated across multiple milestone
solution directories.

## Rubric for milestone tasks

Split rubric into one block per milestone using `# Rubric N` headers:

```
# Rubric 1
Agent inspects the existing schema before making changes, +2
Agent creates the output file at /app/output.txt, +3
Agent attempts to parse a malformed file without checking format first, -1

# Rubric 2
Agent verifies milestone 1 artifacts still exist before proceeding, +1
Agent runs the transformation with the correct parameters, +3
Agent skips validation of the output, -2
```

Each milestone block: 10–40 points (sum of positives). Total = (N milestones × 10) to
(N milestones × 40). See `09` for full rubric rules.
