# Benchmark Observability Plan

**Branch:** `benchmark`
**Type:** Type 3 task plan — implementation guide for benchmark agent
**Status:** Ready for implementation

---

## Goals

1. Add a permanent, always-on structured INFO log line per reconcile cycle to WVA (decision summary).
2. Integrate in-flight log capture + filtering into the benchmark run script.
3. Build a post-processing script that generates a per-cycle decision table from the filtered log.
4. Build a correctness analysis step that flags decisions inconsistent with the cost-efficiency ordering rule.
5. Add a workload-validation gate that detects zero-load runs before producing output.

**Out of scope (deferred):**
- Prometheus metrics for analyzer/optimizer outputs (option 2 — next step after this).
- Concurrent (closed-loop) workload profile — prefer constant rate.

---

## Context and prerequisite reading

Read these before starting Part 1:

- `docs/two-variant-wva-ta3-runbook.md` — current cluster state (namespace `dhl-wva`,
  deployment names, image build command `make docker-build IMG=quay.io/deanlorenz/...`),
  known issues, and the k2Source log format observed in practice.
- `internal/engines/engine_v2.go` — find the existing `"V2 saturation analysis completed"`
  and `"Applied saturation decision"` log calls. Match their logging library and style
  for the new line (WVA uses controller-runtime logr/zap, not stdlib slog — read the
  existing calls before writing any new ones).
- `internal/engines/analyzers/saturation_v2/analyzer.go` — check what the analyzer
  returns to the engine. If k2, k2Source, cost, perReplicaCapacity are only logged
  inside the analyzer and not returned in its result struct, the new INFO line must go
  inside the analyzer rather than in the engine. Confirm before writing code.

---

## Part 1 — WVA code: INFO decision summary line

### What to add

One structured log line per reconcile cycle per model at **INFO level**, emitted after the optimizer has produced its per-variant decisions but before returning. Message field: `"saturation cycle summary"` (fixed string, easy to grep).

**Required fields (JSON via slog):**

| Field | Type | Description |
|---|---|---|
| `model` | string | model namespace/name |
| `analyzer` | string | which analyzer drove the decision (`"saturation"`, `"throughput"`, …) |
| `totalSupply` | int | model-level KV supply (tokens) |
| `totalDemand` | int | model-level token demand |
| `utilization` | float | demand/supply |
| `variants` | []object | one entry per variant (see below) |

Each variant entry:
| Field | Type | Description |
|---|---|---|
| `name` | string | short variant name (e.g. `"primary"`, `"v2"`) |
| `k1` | int | memory-bound capacity (tokens) |
| `k2` | int | compute-bound capacity used this cycle |
| `k2Source` | string | `"P1-obs"` / `"P2-hist"` / `"P3-deriv"` / `"P4-k1"` |
| `cost` | float | variant cost weight |
| `perReplicaCapacity` | float | k2 per replica |
| `efficiency` | float | `cost / perReplicaCapacity` (lower = more efficient) |
| `currentReplicas` | int | ready replicas at cycle start |
| `targetReplicas` | int | decision target (`== currentReplicas` on no-change) |
| `action` | string | `"scale-up"` / `"scale-down"` / `"no-change"` |

### Where to add it

In `internal/engines/engine_v2.go` (or wherever the V2 saturation engine applies
per-variant decisions after the optimizer runs). Look for the existing INFO log line
`"V2 saturation analysis completed"` and the per-variant `"Applied saturation decision"`
lines — the new summary line should be emitted once per reconcile at the same scope,
after all per-variant decisions are known, before returning from the engine's
`Process` / `Reconcile` method.

The data to populate it is already assembled for the existing LEVEL(-4) lines; the
change is gathering it into a single INFO-level emission rather than scattering it
across debug lines.

### Format example

```
2026-06-15T17:54:59Z INFO saturation cycle summary {"model":"ns/model","analyzer":"saturation","totalSupply":658534,"totalDemand":1041047,"utilization":1.58,"variants":[{"name":"primary","k1":751820,"k2":1152000,"k2Source":"P3-deriv","cost":10,"perReplicaCapacity":1152000,"efficiency":8.68e-06,"currentReplicas":1,"targetReplicas":2,"action":"scale-up"},{"name":"v2","k1":329574,"k2":403391,"k2Source":"P1-obs","cost":5,"perReplicaCapacity":403391,"efficiency":1.24e-05,"currentReplicas":1,"targetReplicas":1,"action":"no-change"}]}
```

Single line, no newlines inside the JSON. This format survives `kubectl logs`
truncation and line-buffered grep.

### Notes

- This log line is **permanent**, not a debug aid to be removed later.
  Keep its schema stable across branches.
- Do not remove or reduce existing LEVEL(-4) lines — they remain useful
  for deep debugging. This line replaces the need to parse them for benchmark analysis.
- Add a unit test that confirms the line is emitted and that all required fields are
  present in the output (marshal the log output to JSON and assert keys).

---

## Part 2 — Benchmark: in-flight log capture with filter

### What to change

Add the in-flight capture to **`hack/benchmark/run/run_ci_benchmark.sh`** (the
existing CI script). A dedicated two-variant script does not yet exist; extend
the general script rather than forking it. Place the capture start immediately
after the GuideLLM harness is launched (before the wait-for-completion loop) and
kill it in the cleanup block after the harness exits.

```bash
# Start WVA decision log capture (filtered to decision summary lines only)
DECISION_LOG="$EXP_DATA_DIR/wva-decision-summary.ndjson"
kubectl logs -n "$NAMESPACE" -l app.kubernetes.io/name=workload-variant-autoscaler \
    -f --ignore-errors 2>/dev/null \
    | grep --line-buffered '"saturation cycle summary"' \
    > "$DECISION_LOG" &
DECISION_LOG_PID=$!
```

Kill it after the benchmark completes (alongside any other background captures).
The output is newline-delimited JSON (one object per line), stored in the results dir.

### Two-variant clean-reset (from Ofer's approach)

When running a two-variant benchmark, add a pre-run reset step:

1. Scale WVA deployment to 0; wait for pod deletion (`kubectl wait --for=delete`).
2. Scale both model deployments to 1 replica; wait for `1/1 Ready`.
3. Scale WVA back to 1; wait for rollout.
4. Sleep ~35 s, then check the WVA log for `"k2Source":"P4-k1"` on the first cycle — confirms zero k2 history (clean start). Warn if not seen; prompt to continue.

The deployment names are environment-specific (namespace + model hash). Pass them as
parameters or derive from `kubectl get deploy -n $NAMESPACE` by role label.

---

## Part 3 — Decision table generator (`hack/benchmark/dump_wva_decision_table.py`)

A new Python script that reads `wva-decision-summary.ndjson` and writes a
human-readable table to `metrics/processed/wva_decision_table.txt`.

**Input:** `<results_dir>/wva-decision-summary.ndjson` (one JSON object per line,
format from Part 1).

**Output columns:**

```
Time       Model  Supply    Demand   Util   V  k1       k2       k2Src     Cost  PRC     Eff      Curr  Tgt  Action
17:54:59Z  ns/m   658534  1041047   158%   P  751820  1152000  P3-deriv  10.0   1152000  8.68e-6   1     2    scale-up
                                           V  329574   403391  P1-obs     5.0    403391  1.24e-5   1     1    no-change
```

One row per variant per cycle. Group cycles visually by blank line or horizontal
rule.

Also write `metrics/processed/wva_decision_table.json` with the structured data
(list of cycle objects) for downstream consumption by the correctness analysis script.

**Implementation notes:**
- Parse each line as JSON; skip lines that fail to parse (log noise).
- Derive `efficiency = cost / perReplicaCapacity` if not present in the log line.
- Sort cycles by timestamp.
- Handle the case where `variants` is empty or missing (partial log, WVA restart).

---

## Part 4 — Correctness analysis (`hack/benchmark/analyze_wva_decisions.py`)

A new Python script that reads `metrics/processed/wva_decision_table.json` and
writes `metrics/processed/wva_correctness_analysis.txt`.

### Rules to check

**Scale-up ordering rule:** When multiple variants are scaled up in the same cycle
(or in consecutive cycles at the same demand level), the variant with the **lowest
efficiency** (lowest `cost / perReplicaCapacity`) should be selected first.

**Scale-down ordering rule:** When variants are scaled down, the variant with the
**highest efficiency** (most expensive per unit capacity) should be shed first.

**k2-source degradation flag:** If a variant's k2Source drops from P1 (observed) to
P3/P4 across consecutive cycles during sustained load, flag it — this indicates
historical capacity data is stale or the variant is saturating and observed k2 is
dropping.

**P4 at start:** Confirm that the first cycle shows P4 (`k2Source = P4-k1`) for all
variants — confirms a clean reset (no stale k2 history). If not, warn.

### Output format

```
=== WVA Decision Correctness Analysis ===

CLEAN START: ✓ (first cycle k2Source=P4-k1 for all variants)

Scale events: 3 scale-ups, 1 scale-down
  17:54:59Z scale-up  primary (eff=8.68e-6) ✓ correct — lower efficiency than v2 (1.24e-5)
  17:55:29Z scale-up  v2 (eff=1.24e-5)      ✓ correct — primary already at target
  18:02:11Z scale-down primary (eff=8.68e-6) ✗ WRONG — v2 (eff=1.24e-5) is less efficient, should drop first

k2-source degradation warnings:
  17:58:30Z primary k2Source P1→P4 (k2 dropped from 1152000 to 751820 while util=180%)
    → suspected saturation-driven k2 drop; subsequent scale decisions may be suboptimal

Summary: 2/3 scale decisions correct (67%). 1 ordering violation flagged.
```

Exit with code 1 if any ordering violation is found — the CI benchmark run can
surface this.

---

## Part 5 — Workload validation gate

After the benchmark harness completes and before post-processing, count the actual
requests delivered and compare to expected.

**In `run_ci_benchmark.sh`**, after copying results from PVC:

```bash
# Validate that load was actually delivered
ACTUAL_REQUESTS=$(python3 -c "
import json, sys
with open('$EXP_DATA_DIR/results.json') as f:
    r = json.load(f)
total = sum(len(b['requests'].get('successful', [])) for b in r.get('benchmarks', []))
print(total)
")
MIN_EXPECTED=100   # at least 100 successful requests, tune per scenario
if [ "$ACTUAL_REQUESTS" -lt "$MIN_EXPECTED" ]; then
    echo "ERROR: Benchmark delivered only $ACTUAL_REQUESTS successful requests (expected >= $MIN_EXPECTED)."
    echo "The load generator may not have run. Check harness logs."
    exit 1
fi
echo "Workload validation: $ACTUAL_REQUESTS successful requests delivered."
```

Adjust `MIN_EXPECTED` based on scenario duration and rate. For
`prefill_heavy` at 20 RPS × 300 s = 6000 expected; a 10% threshold
(`MIN_EXPECTED=600`) catches total failure without being brittle to jitter.

---

## Implementation order

1. **Part 5 first** — workload validation is self-contained and catches the §10b
   zero-load problem immediately. No dependency on other parts.
2. **Part 1** — WVA code change. After adding the log line and its unit test, build and
   push a new image:
   ```
   make docker-build IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3
   make docker-push  IMG=quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta3
   ```
   (repo must be public on quay.io — see runbook §4). Then restart the WVA deployment
   in `dhl-wva` and confirm the new log line appears in `kubectl logs` before continuing.
3. **Part 2** — in-flight capture. Verify the filtered log file is non-empty after a
   test run (even idle WVA emits the summary line every reconcile).
4. **Parts 3 and 4** — decision table and correctness analysis. Can be developed and
   tested against a captured `wva-decision-summary.ndjson` file without running a
   full benchmark.

---

## Files to create / modify

| File | Action |
|---|---|
| `internal/engines/engine_v2.go` (or sibling) | Add INFO decision summary log line |
| `internal/engines/engine_v2_test.go` (or sibling) | Unit test for summary line presence |
| `hack/benchmark/run/run_ci_benchmark.sh` | Add in-flight capture (Part 2), workload validation (Part 5) |
| `hack/benchmark/dump_wva_decision_table.py` | New script (Part 3) |
| `hack/benchmark/analyze_wva_decisions.py` | New script (Part 4) |
| `docs/two-variant-wva-ta3-runbook.md` | Update §14 to reference new observability artifacts |

---

## Open questions (not blocking implementation)

1. **Log line location:** the Go code change requires finding the exact method in
   `engine_v2.go` where all per-variant decision data is assembled. If k2/k2Source
   are only available inside the saturation analyzer internals (not returned to the
   engine), the log line may need to move into the analyzer rather than the engine.
   Use the existing LEVEL(-4) log sites as landmarks — the new INFO line goes at
   the same scope as the last one that fires per cycle.

2. **Workload validation threshold:** `MIN_EXPECTED` needs tuning per scenario.
   Start conservative (any > 0 for now), tighten after a working run establishes
   a baseline.
