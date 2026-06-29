# 10 — task.toml v2.0 reference (Edition 2)

Complete schema for both non-milestone and milestone tasks.

## Non-milestone task

```toml
# Task configuration schema version — must be "2.0"
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "medium"          # "easy" | "medium" | "hard" | "unknown"
category = "software-engineering"

# Available subcategories (leave empty [] if none apply):
# "long_context" | "tool_specific" | "api_integration" | "db_interaction" | "ui_building"
subcategories = ["db_interaction"]

number_of_milestones = 0       # 0 for non-milestone tasks

# Codebase size: count files in the environment the agent operates on (not outputs)
# "minimal" = 0–20 files | "small" = 20+ files | "large" = 200+ files
codebase_size = "small"

# Primary language(s) used in the oracle solution (not test language)
# Only list C# even if you have a little Python test code
languages = ["python", "sql"]

# 3–6 descriptive keywords for tools/libraries/techniques
# For tool_specific / api_integration / db_interaction: name the specific tool
tags = ["duckdb", "terraform", "leaderboard", "sql"]

expert_time_estimate_min = 30
junior_time_estimate_min = 60

# Multi-container tasks: add these to [metadata]
# custom_docker_compose = true   # if using docker-compose.yaml
# is_multi_container = true      # if docker-compose has multiple services

[verifier]
timeout_sec = 450.0

[agent]
timeout_sec = 900.0

[environment]
build_timeout_sec = 600.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
```

## Milestone task

```toml
version = "2.0"

[metadata]
author_name = "anonymous"
author_email = "anonymous"
difficulty = "hard"
category = "software-engineering"
subcategories = ["db_interaction"]
number_of_milestones = 3       # must equal the number of [[steps]] blocks below
codebase_size = "small"
languages = ["python", "sql", "bash"]
tags = ["duckdb", "terraform", "leaderboard"]
expert_time_estimate_min = 60
junior_time_estimate_min = 120

[environment]
build_timeout_sec = 600.0
cpus = 2
memory_mb = 4096
storage_mb = 10240
allow_internet = false
workdir = "/app"               # milestone tasks: required — sets shared working directory

# No top-level [verifier] or [agent] — use per-step blocks below

[[steps]]
name = "milestone_1"           # must match steps/milestone_1/ directory name

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

## Field reference

| Field | Required | Notes |
|---|---|---|
| `version` | ✅ | Must be `"2.0"` |
| `author_name` | ✅ | `"anonymous"` is fine |
| `author_email` | ✅ | `"anonymous"` is fine |
| `difficulty` | ✅ | Based on actual agent pass rates |
| `category` | ✅ | One of the 9 task types |
| `subcategories` | ✅ | Empty list `[]` if none apply |
| `number_of_milestones` | ✅ | `0` for non-milestone; must match `[[steps]]` count |
| `codebase_size` | ✅ | `"minimal"` / `"small"` / `"large"` |
| `languages` | ✅ | Primary task language(s) — not Python just because tests use pytest |
| `tags` | ✅ | 3–6 keywords |
| `expert_time_estimate_min` | ✅ | Minutes |
| `junior_time_estimate_min` | ✅ | Minutes |
| `[verifier] timeout_sec` | ✅ non-milestone | |
| `[agent] timeout_sec` | ✅ non-milestone | |
| `[environment] build_timeout_sec` | ✅ | |
| `[environment] cpus` | ✅ | |
| `[environment] memory_mb` | ✅ | |
| `[environment] storage_mb` | ✅ | |
| `[environment] allow_internet` | ✅ | Must be `false` |
| `[environment] workdir` | ✅ milestone only | Shared working directory |
| `[[steps]] name` | ✅ milestone only | `"milestone_1"`, `"milestone_2"`, etc. |
| `[steps.agent] timeout_sec` | ✅ milestone only | Per-step |
| `[steps.verifier] timeout_sec` | ✅ milestone only | Per-step |

## Difficulty thresholds

| Level | Condition |
|---|---|
| Hard | Worst model ≤ 20% OR best model ≤ 20% |
| Medium | 20% < worst model ≤ 60% |
| Easy | 60% < worst model ≤ 80% |

Tasks where worst model > 80% are not accepted. Evaluate against both GPT-5.5 and Claude Opus 4.8,
2–3 runs each.

## Subcategory definitions

- **`long_context`** — requires reading a file ≥50k tokens that **cannot** be parsed
  programmatically or keyword-searched. The task must rely on semantic understanding of the
  document. Reviewers check: if the file is a structured format (JSON, CSV, YAML) or
  synthetically generated markdown that an agent could grep through, it does NOT qualify.
  Use real-world documents: PDFs, regulatory filings, long meeting transcripts, dense specs.
- **`tool_specific`** — targets a specific SDK/tool (Blender, FFmpeg, ImageMagick, MLFlow, etc.)
- **`api_integration`** — agent builds/interacts with an API whose source is in the environment;
  APIs must be mocked within Docker (no external deps); avoid overusing FastAPI
- **`db_interaction`** — agent must query a database engine (not just read a CSV); SQL, NoSQL,
  vector DBs, in-memory DBs all qualify; pure CSV "databases" should be minority
- **`ui_building`** — agent creates/edits a user interface (verified with Playwright Python bindings)
