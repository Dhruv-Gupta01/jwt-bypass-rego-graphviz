# 05 — Build & verify loop (Edition 2 commands, oracle/nop, zip & submit)

Run this loop every time before you submit. It's the cheapest insurance against a failed gate.

## Repo shapes (reference layouts)

### Non-milestone task
```
task-root/
├── task.toml                      # metadata, v2.0 schema, agent/verifier timeouts
├── instruction.md                 # agent-facing spec (sufficiency target)
├── environment/
│   ├── Dockerfile                 # ALL deps (runtime + test), digest-pinned base
│   ├── .dockerignore
│   └── [data/, schemas/, app/, etc.]
├── solution/
│   └── solve.sh                   # oracle solution
└── tests/
    ├── test.sh                    # runs pytest, writes reward.txt (no installs)
    └── test_outputs.py            # pytest assertions with docstrings
```

### Milestone task
```
task-root/
├── task.toml                      # version="2.0", number_of_milestones=N, [[steps]] per milestone
├── environment/
│   ├── Dockerfile
│   └── .dockerignore
└── steps/
    ├── milestone_1/
    │   ├── instruction.md
    │   ├── tests/
    │   │   ├── test.sh
    │   │   └── test_m1.py         # class TestMilestone1
    │   └── solution/
    │       ├── solve.sh           # wrapper — calls solve1.sh
    │       └── solve1.sh          # oracle scoped to milestone 1 only
    └── milestone_2/
        └── ...                    # same structure
```

**No** root-level `instruction.md`, `tests/`, `solution/`, or `milestone_x.md` in milestone tasks.

---

## The verification loop

### 1. Build the environment image
```bash
docker build --platform linux/amd64 -t mytask ./environment 2>&1 | tail -5
```

### 2. Oracle run — MUST be reward 1.0
```bash
CID=$(docker run -d --platform linux/amd64 mytask)
docker cp solution "$CID":/oracle
docker cp tests    "$CID":/tests
docker exec "$CID" bash -c "bash /oracle/solve.sh && bash /tests/test.sh" 2>&1 | tail -20
echo "oracle reward: $(docker exec "$CID" cat /logs/verifier/reward.txt)"   # expect 1
docker rm -f "$CID"
```

### 3. Nop run — MUST be reward 0.0
```bash
CID=$(docker run -d --platform linux/amd64 mytask)
docker cp tests "$CID":/tests          # NOTE: do NOT copy solution
docker exec "$CID" bash /tests/test.sh 2>&1 | tail -5
echo "nop reward: $(docker exec "$CID" cat /logs/verifier/reward.txt)"       # expect 0
docker rm -f "$CID"
```

A healthy nop shows many substantive tests failing; reward = 0. Some trivial setup
assertions passing is fine as long as reward is 0.

### 4. Offline smoke test

```bash
CID=$(docker run -d --platform linux/amd64 --network none mytask)
docker cp solution "$CID":/oracle
docker cp tests    "$CID":/tests
docker exec "$CID" bash -c "bash /oracle/solve.sh && bash /tests/test.sh"
echo "offline reward: $(docker exec "$CID" cat /logs/verifier/reward.txt)"   # expect 1
docker rm -f "$CID"
```

### 5. Use Harbor CLI when available

```bash
# Oracle agent (must PASS)
harbor run -a oracle -p <task-folder>

# LLMaJ/static checks
harbor tasks check -p <task-folder>

# Real agents (run 2–3 times each to gauge pass rate)
stb harbor run -m @openai/gpt-5.5 -p <task-folder>
stb harbor run -m @anthropic/claude-opus-4-8 -p <task-folder>
```

---

## Only when both oracle=1 and nop=0 — rebuild the zip

**Non-milestone tasks:** zip the files inside the folder, not the folder itself.
Select: `instruction.md`, `task.toml`, `environment/`, `solution/`, `tests/`

**Milestone tasks:** zip: `task.toml`, `environment/`, `steps/`
No root-level `instruction.md`, `tests/`, `solution/`.

Using git archive (guarantees clean tree, respects .gitignore):
```bash
rm -f ../mytask.zip
git archive --format=zip -o ../mytask.zip HEAD
unzip -l ../mytask.zip | tail -3       # sanity: entry count, no nested top-folder
```

**Critical:** the zip must have files at the root, not nested inside a folder. On macOS:
open the task folder → select all files → Compress. Do NOT right-click the folder itself.

---

## Environment notes

- Always `--platform linux/amd64` even on Apple Silicon.
- No `jq` on the authoring machine — use `python3` for JSON parsing.
- Re-run oracle AND nop after **every** change to tests, solution, or Dockerfile.
- The solution folder is mounted at `/oracle/` at runtime (not `/solution/`).
- Special container paths: `/logs/verifier/` (reward + CTRF), `/logs/agent/`, `/oracle/`, `/tests/`.

---

## Pre-submission gate checklist

- [ ] `docker build --platform linux/amd64` clean.
- [ ] Oracle reward = 1.0 (in Docker, via test.sh — not just local pytest).
- [ ] Nop reward = 0.0 (substantive tests fail).
- [ ] Offline run passes (oracle with `--network none`).
- [ ] `harbor tasks check` passes (all CI blocking checks green).
- [ ] Oracle agent: `harbor run -a oracle -p <task-folder>` PASSES.
- [ ] Static-check items from `04` satisfied.
- [ ] Sufficiency self-check from `03` done.
- [ ] Zip has files at root (not in subfolder).
- [ ] Rubric drafted (at least 3 negative criteria — see `09`).
