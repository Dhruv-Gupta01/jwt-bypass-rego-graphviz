# 04 — Static checks & infra traps (Edition 2 — source of truth)

These are 100% preventable and 100% mechanical. Each one below is a real failure mode.
Build the repo right the first time using this file.

---

## Trap 1 — Test deps: bake ALL into the Dockerfile (Edition 2 rule change)

**Edition 2 hard rule:** all test/verifier dependencies (pytest, pytest-json-ctrf, requests,
playwright, etc.) must be **pre-installed in the Docker image**. `tests/test.sh` must NOT
install packages or download anything at runtime.

```dockerfile
# In environment/Dockerfile — bake pytest and test deps here
RUN pip install --no-cache-dir \
    pytest==8.4.1 \
    pytest-json-ctrf==0.3.5 \
    requests==2.32.3
```

> **⚠️ This reverses the Edition 1 / old-playbook advice about vendored wheels.** The
> old approach (vendor `.whl` files, install in `test.sh` with `--no-index`) is no longer
> correct. The CI check `check_test_sh` will fail if `test.sh` runs `pip install`.

The old vendored-wheels pattern (`tests/wheels/`, `pip install --no-index ...` in test.sh)
is now incorrect. Remove it from any task you're authoring.

---

## Trap 2 — Reward-script format and PWD guard (exact shape required)

**Cause:** `check_test_sh` matches the reward block with a regex; cosmetic differences fail it.
Reviewers also consistently flag missing PWD guards and `mkdir /logs/verifier` placed too late.

**Fix — use this exact shape in `tests/test.sh`:**
```bash
#!/bin/bash
set -uo pipefail

# PWD guard — required; reviewers flag missing this as a defect
if [ "$PWD" = "/" ]; then
    echo "Error: No working directory set. Please set a WORKDIR in your Dockerfile."
    mkdir -p /logs/verifier
    echo 0 > /logs/verifier/reward.txt
    exit 0
fi

# mkdir FIRST, before any other logic — reviewers flag if this appears later
mkdir -p /logs/verifier

python -m pytest --ctrf /logs/verifier/ctrf.json /tests/test_outputs.py -rA
rc=$?

if [ "$rc" -eq 0 ]; then
  echo 1 > /logs/verifier/reward.txt
else
  echo 0 > /logs/verifier/reward.txt
fi
```

Rules the CI enforces:
- **PWD guard first** — check `$PWD = "/"` and write reward 0 + exit if no WORKDIR set.
- **`mkdir -p /logs/verifier` immediately after the PWD guard** — before any other logic.
  Reviewers explicitly flag `/logs/verifier` written after other logic as a defect.
- Use `rc=$?` (lowercase, no braces — `${rc}` or `$RC` or `${RC}` can break the regex).
- Write reward to `/logs/verifier/reward.txt` (1 or 0 only — no partial rewards).
- **No trailing `exit` after the `fi`.** Harbor reads `reward.txt`, not the script exit code.
  Adding `exit $?` after `fi` will **fail CI**.
- Keep `test.sh` simple — just the guard, mkdir, pytest, and reward block. Do not put
  server startup, config, or build logic in `test.sh`; those go in the solution or Dockerfile.
- Always write the reward file — even on test failure or error; never exit before writing it.

---

## Trap 3 — Network calls at test time (`allow_internet = false`)

Everything at test time is offline. `curl`, `wget`, `pip install`, `npm install`, `git clone`,
`cargo fetch` — all forbidden.

**Fixes:**
- All test/verifier deps in the Dockerfile (Trap 1).
- Health checks: use pure-Python urllib, not curl:
  ```bash
  for i in $(seq 1 30); do
    python3 -c "import urllib.request; urllib.request.urlopen('http://localhost:5000/health')" \
      2>/dev/null && break
    sleep 1
  done
  ```
- Data and fixtures must be in the repo, copied into the image at build time.
- `task.toml` must set `allow_internet = false` under `[environment]`.

---

## Trap 4 — Base image not digest-pinned (`check_pinned_images`)

**Every** `FROM` line must use an immutable `@sha256:<digest>`. Tags are allowed for
readability but are not sufficient alone.

```dockerfile
# Bad — tag only
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm

# Good — tag + digest
FROM public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367a0a94ad4bc17111776fd66e3500c1d87c15bbd6055b7371d39c124fb
```

Same rule applies to `image:` lines in `docker-compose.yaml`.

---

## Trap 5 — Non-canonical base image without justification (`check_sanctioned_base_images`)

The final runtime stage must use a **canonical Terminal-Bench base image**, OR include a brief
written justification (in a Dockerfile comment or `README.md`).

**Canonical base images (use these):**

| Language | Image |
|---|---|
| Python | `public.ecr.aws/docker/library/python:3.13-slim-bookworm@sha256:01f42367...` |
| Node.js | `public.ecr.aws/docker/library/node:22-bookworm-slim@sha256:f3a68cf4...` |
| Go | `public.ecr.aws/docker/library/golang:1.24-bookworm@sha256:1a6d4452...` |
| Rust | `public.ecr.aws/docker/library/rust:1.85-slim@sha256:9f841bbe...` |
| Java | `public.ecr.aws/docker/library/eclipse-temurin:21-jdk-jammy@sha256:25d12765...` |
| C/C++ | `public.ecr.aws/docker/library/gcc:13-bookworm@sha256:930f2ebe...` |
| Ruby | `public.ecr.aws/docker/library/ruby:3.3-slim-bookworm@sha256:e76733e9...` |
| Debian base | `public.ecr.aws/docker/library/debian:bookworm-slim@sha256:4724b8cc...` |
| Ubuntu base | `public.ecr.aws/docker/library/ubuntu:24.04@sha256:0d39fcc8...` |

Non-canonical is allowed with a credible justification. Missing/vague justification → blocked.

---

## Trap 6 — Missing `tmux` and `asciinema`

The agent runtime requires both. Missing either causes **all agent runs to fail silently with no
verifier output.**

```dockerfile
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        asciinema \
        tmux \
    && rm -rf /var/lib/apt/lists/*
```

---

## Trap 7 — Solution or tests copied into Dockerfile (including via `COPY . /app`)

Never copy `solution/` or `tests/` into the image. The platform mounts them separately at
runtime. Baking them in leaks answers and will fail `tests_or_solution_in_image`.

**Watch out for `COPY . /app`** — if your build context includes the whole repo, this
copies solution/ and tests/ into the image. Use `COPY app/ /app/` or a specific path,
and ensure `.dockerignore` excludes `solution/` and `tests/`.

---

## Trap 8 — `environment/` build context too large (`check_build_context_size`)

- `environment/` must be **≤ 100 MiB total**.
- No single file over **50 MiB**.
- Non-trivial environments must include `.dockerignore`:
  ```
  .git
  **/__pycache__/
  **/*.pyc
  **/node_modules/
  **/.venv/
  solution/
  tests/
  .env
  *.log
  ```

---

## Trap 9 — AI-framework scaffolding filenames in environment (`check_no_scaffolding`)

Files named `CLAUDE.md`, `skills.md`, or similar AI-framework names must not appear anywhere
in the task environment. Remove them before submission.

---

## Trap 10 — Heredocs in Dockerfile (`check_heredoc_usage`)

Don't embed source files as heredocs; commit them as real files and `COPY` them in.

```dockerfile
# Bad
RUN cat > /app/foo.py <<'EOF'
print('hello')
EOF

# Good
COPY foo.py /app/foo.py
```

---

## Trap 11 — Recursive chmod/chown (`check_recursive_permissions`)

Avoid `chmod -R` or `chown -R` over `/app`. Use `COPY --chmod=0755` instead.

---

## Trap 12 — Line endings & formatting

- Enforce **LF** line endings (`.gitattributes`: `* text=auto eol=lf`).
- Run `ruff format` for Python before zipping.

---

## Trap 13 — Unnecessary / forbidden files in the submission

Reviewers flag these consistently. Remove before zipping:

**From the root directory (non-milestone):**
- `.gitignore`, `.gitattributes` — not required
- `scripts/` directory — not required
- `rubric.json`, `rubrics.txt` — platform rubric is the source of truth
- `pyproject.toml`, `.ruff_cache` — tooling artifacts
- The zip file of the task itself
- `wheels/` inside `tests/` — Edition 2 bakes deps in Dockerfile, not here

**In task.toml — remove these forbidden/unnecessary fields:**
```toml
# These fields do NOT belong in task.toml:
name = "..."                  # REMOVE — not in the schema
description = "..."           # REMOVE — not in the schema  
difficulty_explanation = "..."# REMOVE — not in the schema
workdir = "..."               # only valid in [environment] for milestone tasks
```
Also remove all inline comments on metadata lines (lines like `# Task metadata...` blocks);
keep only the minimal required fields.

**In milestone tasks — remove from each `steps/milestone_N/` folder:**
- `workdir/` directories — not part of the expected milestone layout
- `conftest.py` in the `steps/` root — not expected

---

## Trap 14 — task.toml forbidden/unexpected fields

Only use fields defined in the v2.0 schema (`10`). Reviewers flag:
- `name` — not a v2.0 field, remove it
- `description` — not a v2.0 field, remove it
- `difficulty_explanation` — not a v2.0 field, remove it
- `[task]` section — does not exist in v2.0
- Excessive inline comments — reviewers flag "unnecessary comments on lines 2–21"; keep
  the toml clean, no narrative comments

---

## Full CI check list (reference)

**Blocking (must pass):**
- `check_pinned_images` — every FROM has @sha256 digest
- `check_sanctioned_base_images` — canonical or justified non-canonical
- `check_build_context_size` — ≤100 MiB total, ≤50 MiB per file
- `pinned_dependencies` — all packages pinned to exact versions
- `typos` — no spelling errors
- `tests_or_solution_in_image` — solution/tests not in image
- `check_dockerfile_references` — all COPY targets exist
- `check_test_sh` — test.sh uses pre-installed deps + produces reward file
- `check_task_absolute_path` — uses absolute paths in instruction
- `ruff` — Python linting passes
- `validate_task_fields` — task.toml complete

**Warning (non-blocking, but fix if possible):**
- `check_dockerignore` — non-trivial env has .dockerignore
- `check_dockerfile_hygiene` — no clutter/secrets
- `check_offline_tests` — test.sh doesn't install or download at runtime
- `check_apt_usage` — apt usage clean and cache-friendly
- `check_reproducible_builds` — downloads are pinned/checksummed
- `check_layer_volatility` — layers ordered least-to-most volatile
- `check_no_build_tools_in_runtime` — no lingering build tools
- `check_file_extraction` — archives extracted and removed
- `check_heredoc_usage` — source files are files, not heredocs
- `check_recursive_permissions` — no broad chmod/chown

**LLMaJ checks (must pass):**
- `behavior_in_task_description` — requirements clearly stated
- `behavior_in_tests` — tests verify behavior
- `informative_test_docstrings` — every test has a docstring
- `anti_cheating_measures` — task can't be gamed
- `hardcoded_solution` — solution isn't trivially derivable
- `file_reference_mentioned` — output files specified
- `structured_data_schema` — data formats defined

---

## Trap 15 — LLMaJ: what actually triggers each check (with examples)

The names are listed above but the failure modes aren't obvious. Each check below shows
exactly what causes a pass vs. fail.

**`behavior_in_tests`** — a test asserts a behavior that the instruction never mentions.
```
# FAIL: test checks float rounding to 2dp but instruction says nothing about precision
def test_total_rounded():
    assert result["total"] == 10.55  # instruction never mentioned rounding

# PASS: instruction says "round all monetary values to 2 decimal places"
```

**`behavior_in_task_description`** — instruction describes a requirement but no test checks it.
```
# FAIL: instruction says "handle empty input gracefully" but no test for empty input exists
# PASS: every sentence in the instruction that describes expected output has a test
```

**`structured_data_schema`** — output is JSON/CSV/structured but the schema isn't in the instruction.
```
# FAIL: instruction says "write results to /app/out.json" — no schema defined
# PASS: instruction says "write results to /app/out.json with fields: id (int), name (str), score (float)"
```

**`hardcoded_solution`** — an agent could read the test assertions to derive the correct output.
```
# FAIL: assert result["answer"] == 42  (agent reads test → knows answer is 42)
# PASS: assert result["answer"] == compute_expected(input_data)  (recomputed at test time)
```

**`file_reference_mentioned`** — output file path not stated in the instruction.
```
# FAIL: test checks Path("/app/result.csv").exists() but instruction never mentions result.csv
# PASS: instruction says "write the output to /app/result.csv"
```

**`anti_cheating_measures`** — task can be trivially gamed without doing real work.
```
# FAIL: tests only check file existence — agent can touch /app/result.csv and pass
# PASS: tests check computed values using an independent verifier-side oracle
```

**`informative_test_docstrings`** — docstring is missing or too vague to describe the behavior.
```python
# FAIL
def test_output():
    """Test output."""  # too vague
    ...

# PASS
def test_output_contains_all_user_ids():
    """Verify the result CSV contains exactly one row per user_id from /app/users.db."""
    ...
```

---

## Trap 16 — Test coverage gaps (concrete audit)

After writing tests, run this 3-step audit before submitting:

**Step 1 — Map every instruction sentence to a test.**
Highlight each requirement in instruction.md. For every highlighted sentence, name the test
function that covers it. If you can't name one, you're missing a test.

**Step 2 — List implicit behaviors and check each one.**
For every task, these are almost always implicitly expected but frequently untested:
- Empty or missing input → what happens?
- Wrong file format / corrupt data → what happens?
- Boundary values (zero, negative, max) → are they handled?
- Output schema completeness — every required field present, no extras?
- Idempotency — does running the solution twice produce the same result?

**Step 3 — Red-team with the simplest wrong solution.**
Write (mentally) the laziest stub that does the minimum: creates the output file with
placeholder values, or returns a hardcoded dict. If any of your tests pass against this
stub, those tests are vacuous and need strengthening. Reviewers do exactly this check.

---

## Trap 17 — Anti-cheating: concrete techniques

Abstract "add anti-cheating measures" means nothing without specifics. Use these patterns:

**Verifier-side recompute** (strongest): tests compute expected output independently using
their own logic, not from hardcoded values the agent could read:
```python
def test_totals_correct():
    """Totals must match independent recomputation from source data."""
    import sqlite3
    conn = sqlite3.connect("/app/source.db")
    expected = sum(r[0] * r[1] for r in conn.execute("SELECT qty, price FROM orders"))
    result = json.loads(Path("/app/out.json").read_text())
    assert abs(result["total"] - expected) < 0.01
```

**Hidden seed at test time**: the instruction shows an example with seed=42; the actual
test uses seed=99 (or a file the agent has never seen). The agent must implement the logic,
not memorize the example output.

**Value tests, not existence tests**: always assert the computed value, not just that the
file exists or is valid JSON. File-exists tests are necessary but not sufficient.

**Don't put expected values as literals in test assertions**: `assert count == 1337` tells
an agent the answer. Use `assert count == len(expected_ids)` where `expected_ids` is computed.

---

## Trap 18 — Oracle flakiness

Oracle must produce reward 1.0 on every run, deterministically. Common causes of oracle
flakiness that reviewers catch:

**`set -e` + error injection**: if your task intentionally injects 429/500 errors into an
API, and your oracle uses `set -e`, the oracle exits on the first injected error before
producing output. Fix: oracle bypasses error injection (e.g. uses a direct DB path instead
of the HTTP API), or adds retry logic.

**Race conditions on service startup**: oracle tries to call a service before it's ready.
Fix: add a proper health-check loop (urllib, not curl) before any service calls in solve.sh.

**Non-deterministic output order**: if output contains a list and order isn't fixed, tests
that compare order-sensitive output will flake. Fix: sort deterministically, document the
sort order in the instruction.

**Test oracle determinism before submitting**: run the oracle 3 times consecutively in the
same container. All three must produce identical output and reward 1.0. If any run differs,
find and fix the source of non-determinism before zipping.

---

## Infra hygiene summary

- Dockerfile: ALL deps (runtime AND test), pinned, digest-pinned base, `--platform linux/amd64`.
- `test.sh`: runs pytest, writes reward.txt — no installs, no network, no trailing `exit`.
- No network at any point during test or agent run.
- `environment/` ≤100 MiB, no solution/tests in image, `.dockerignore` present.
- Know blocking vs warning: only blocking failures kill the submission.
