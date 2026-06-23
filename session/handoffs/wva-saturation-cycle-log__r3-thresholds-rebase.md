from: planner
session: wva-saturation-cycle-log R3 — thresholds + remove old log line + rebase

## Your worktree

`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/wva-log-rewrite`
branch: `wva-saturation-cycle-log-r1`
current tip: `c8712fc8` (engine: fix variant reason field — R2 complete)

## Context

Two things happened since R2:
1. Upstream `main` moved 9 commits to `30b3371f`. PR #1306 (`fbbdbbb9`)
   moved the existing `"V2 saturation analysis completed"` log line into
   `runAnalyzersAndScore` (after threshold post-step) and added
   `scaleUpThreshold`/`scaleDownBoundary` fields.
2. Our `analyzer-result` line should include those threshold fields — then
   the old log line is fully superseded and must be removed.

## Steps (full spec in planning/wva-saturation-cycle-log-plan.md §§ R3, Steps 11–17)

### Commit 1 — pre-rebase fixes (Steps 11–16)

**Step 11** — Fix stale comment in `engine_v2_log_test.go:63`:
  Change `"label"` → `"reason"` in the comment text.

**Step 11b** — Guard against empty `Reason` in `saturation_v2/analyzer.go`
  `aggregateByVariant`.

  After computing `capacityLabel` via the three-branch block, add a fallback
  before building `vc` so an unmapped `K2Priority` never silently drops the
  field from the log (`json:"reason,omitempty"` makes empty string invisible):

  ```go
  if capacityLabel == "" {
      capacityLabel = "unknown"
  }
  ```

  The TA is safe by construction (only appends variants when `resolveITLModel`
  returns `ok=true`, which always produces a non-empty label), but sat_v2 can
  reach `k2SourceLabel` with K2Priority outside {1,2,3,4} in edge cases.
  `"unknown"` is explicit and operator-visible.

**Step 12** — Add to `internal/engines/pipeline/optimizer_interfaces.go`,
  `NamedAnalyzerResult` struct (after `Spare`):
  ```go
  ScaleUpThreshold  float64 // resolved scale-up threshold used to compute RC
  ScaleDownBoundary float64 // resolved scale-down boundary used to compute SC
  ```

**Step 13** — In `engine_v2.go` `runAnalyzersAndScore`:
  - Add `ScaleUpThreshold: satUp, ScaleDownBoundary: satDown` to the saturation
    `NamedAnalyzerResult` literal.
  - Add `ScaleUpThreshold: up, ScaleDownBoundary: down` to each registered
    analyzer's `NamedAnalyzerResult` in the loop.
  - (The "V2 saturation analysis completed" block does NOT exist yet on this
    branch — it arrives with the rebase. Delete it then, in Step 17.)

**Step 14** — In `logAnalyzerResult`, add after `"sc"`:
  ```go
  "scaleUpThreshold",  nr.ScaleUpThreshold,
  "scaleDownBoundary", nr.ScaleDownBoundary,
  ```

**Step 15** — In `engine_v2_log_test.go` `TestLogAnalyzerResult_EmitsRequiredFields`:
  - Set `ScaleUpThreshold: 1.2, ScaleDownBoundary: 0.7` on the fixture.
  - Add `"scaleUpThreshold"` and `"scaleDownBoundary"` to the required-keys list.

**Step 16** — Update `docs/developer-guide/cycle-log.md`:

  **16a.** In the `analyzer-result` field table, add after `sc`:
  ```
  | `scaleUpThreshold`  | float64 | resolved threshold used to compute `rc` |
  | `scaleDownBoundary` | float64 | resolved boundary used to compute `sc` |
  ```
  Remove the `cost` row if still present.

  **16b.** Update the JSON format example to include `scaleUpThreshold` and
  `scaleDownBoundary`, and show `reason` (not `label` or `cost`).

  **16c.** Rename the section `## Capacity label values (\`label\` field)` →
  `## Reason values (\`reason\` field)` and replace `label` with `reason`
  throughout that section.

  **16d.** Expand the reason-values section to cover BOTH analyzers.
  Replace the current sat_v2-only table with two subsections:

  ```markdown
  ### Saturation V2 analyzer

  | Reason | Meaning |
  |---|---|
  | `P1-obs` | k2 from **observed** tokens-in-use (queue was saturated — live signal) |
  | `P2-hist` | k2 from **historical** rolling average across saturated cycles |
  | `P3-k2`  | k2 **derived** from deployment parameters (vLLM model args, formula-based) |
  | `P4-k1`  | k2 unavailable — **fell back** to k1 (memory-bound capacity only) |
  | `P0-store` | Capacity sourced from the **capacity store** (no live replicas this cycle) |
  | `unknown` | K2 priority could not be mapped — inspect debug logs |

  ### Throughput analyzer

  | Reason | Meaning |
  |---|---|
  | `T1-ols` | ITL model fitted by **OLS from live observations** in the current window |
  | `T2-pinned` | Constrained OLS with slope **B pinned from the last successful T1 fit** (window not yet ready or fit failed) |
  | `T2-default` | Constrained OLS with **default baseline B** — cold start, no prior fit available |
  ```

  Add a note after the tables:
  ```
  Absent `reason` field: the analyzer produced a capacity estimate via a
  path not covered by the labels above. This should not occur in normal
  operation — if seen, check debug logs for the affected variant.
  ```

Commit: `git commit -s -m "engine: add scaleUpThreshold/scaleDownBoundary to analyzer-result log; update cycle-log doc"`

### Step 17 — Rebase onto upstream/main

```bash
git fetch upstream
git rebase upstream/main
```

Expected conflict in `internal/engines/saturation/engine_v2.go`:
- Upstream #1306 added a `logger.Info("V2 saturation analysis completed", ...)`
  block in `runAnalyzersAndScore` after `applyUniversalThreshold`.
- Our branch has `ScaleUpThreshold`/`ScaleDownBoundary` fields and the
  `logAnalyzerResult` loop in the same function.
- Resolution: keep our changes, **delete** the entire
  `"V2 saturation analysis completed"` logger.Info block. Our
  `logAnalyzerResult` loop supersedes it — it emits the same fields plus
  variants and thresholds.

After rebase: run all gates:
```bash
gofmt -l internal/
make test
make lint
go build ./...
```
All must be clean before writing the handoff.

## After all steps

1. Run gates (above)
2. Commit message for Step 17 is the rebase — no new commit needed.
3. Write `plans/session/handoffs/plan__wva-log-r3-done.md`
4. Mark this handoff done:
   `mv plans/session/handoffs/wva-saturation-cycle-log__r3-thresholds-rebase.md \
       plans/session/handoffs/wva-saturation-cycle-log__r3-thresholds-rebase.md.DONE`
5. Do NOT push — Dean pushes after review.
