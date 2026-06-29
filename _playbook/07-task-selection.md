# 07 — Task selection: pick one that can pass every gate with fewest iterations

The cheapest iteration is the one you avoid by picking the right task. Score candidates on
the two axes that actually fail tasks.

## The selection rubric

Score each candidate task on:

### Axis A — Can every *engineering* gate pass cleanly? (oracle/nop/sufficiency/static/offline)
- **Deterministic output?** Exact-match outputs (numbers, files, fixed strings) make
  oracle/nop trivial. Statistical thresholds ("≥95% solved", "75% of payoff", "sub-5ms")
  and RNG/timing introduce flakiness → avoid.
- **Offline & low-infra?** Pure-script tasks (read local files, write outputs) skip the
  server/wheels/health-check apparatus entirely. Server-based tasks are doable (we did Flask)
  but cost more setup.
- **Can YOU guarantee the oracle?** If you fully understand the algorithm, Gate 1 is safe.
  If authoring a correct solution is itself a research problem, that's a real risk.

### Axis B — Can it hold the target difficulty? (survives documentation)
- **Derivation, not recall?** Difficulty must come from a constraint/composition the agent
  must invent through, not a textbook algorithm it recalls. (`02`)
- **Tunable in place?** If a difficulty miss is fixed by editing oracle/tests/instruction
  (not rebuilding infra), misses are cheap. Correctness-density and rule-interaction levers
  are ideal.

> The best picks are strong on **both** axes. Many tasks trade off: the most reliably-HARD
> ones (novel coordination, hostile-constraint algorithms) are often harder to author a clean
> oracle for; the easiest-to-author ones are often recall-class → MEDIUM. Find the task where
> you can guarantee the oracle AND the difficulty survives a perfect spec.

## Red flags (skip these)

- Statistical/threshold grading: "≥X% success", "within N% of optimal", tournaments, payoffs.
- Timing attacks / performance-gated success (env-sensitive, flaky).
- RNG / procedural generation without a fixed seed (non-deterministic oracle).
- Heavy external infra: webhooks (Slack/SMTP/Jira), cloud APIs, honeypots, multi-service stacks.
- Named textbook attacks/algorithms as the *sole* difficulty (recall-class → EASY).
- Exploitation tasks where success depends on ASLR/addresses (non-deterministic).

## Green flags (favor these)

- Exact-match deterministic outputs (files, numbers, fixed structures).
- Pure-script or single-local-server, fully offline.
- A bespoke algorithm/simulator/format you can implement but the agent must derive.
- A hostile constraint (no-recursion language, resource/byte budget, memory/perf bound).
- Difficulty that's tunable by adding interacting rules in the same scaffold.

---

## How to fetch the whole task gallery (the portal is a JS SPA)

The gallery portal renders client-side; the page URL returns 404 to a fetcher. The data lives
in a public Supabase backend the page queries with a public anon key. To enumerate all tasks:

1. Fetch the SPA's JS bundle (from `index.html`'s `<script type="module" src=...>`).
2. Extract the Supabase URL, the anon JWT (`eyJ...`), and the queried table/view names
   (look for `.from("...")`). The task list view we used was `v_tasks_with_priorities`.
3. Page through the REST API with the anon key (stable sort to avoid dup/missing rows):
   ```bash
   KEY="<anon-jwt-from-bundle>"
   BASE="https://<project>.supabase.co/rest/v1"
   for r in "0-999" "1000-1999" "2000-2999" "3000-3999" "4000-4999"; do
     curl -s "$BASE/v_tasks_with_priorities?select=*&order=id.asc" \
       -H "apikey: $KEY" -H "Authorization: Bearer $KEY" \
       -H "Range-Unit: items" -H "Range: $r" -o "gallery_$r.json"
   done
   ```
   (Use `-H "Prefer: count=exact"` and read the `content-range` response header to get the
   total row count.)
4. `is_selected = true` means the task is already taken; filter those out. Parse with `python3`
   (no jq on the box).

> This is read-only enumeration via the same public key the site ships to every browser.
> Snapshot the result to a JSON file — selection state changes over time, so re-check
> availability of a specific task right before you claim it.
