from: planner
session: wva-saturation-cycle-log R2 reason field fixes

## Your worktree

`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/wva-log-rewrite`
branch: `wva-saturation-cycle-log-r1`
current tip: `69ba4d8b` (docs: add observability pointer to multi-analyzer-pipeline doc)

## Task

Implement R2 amendments from the plan. Steps 1–7 are already done. You are
adding one commit on top of the current tip covering Steps 8, 9, and 10.

Full step-by-step instructions are in:
`planning/wva-saturation-cycle-log-plan.md` — section "R2 amendments"

## Summary of the three changes

**Step 8 — Drop `cost` from `variantEntry` (`engine_v2.go`, `logAnalyzerResult`)**
- Remove `Cost float64 \`json:"cost"\`` from struct definition
- Remove `Cost: vc.Cost,` from struct literal
- Update tests: remove any `cost` assertions

**Step 9 — Sat_v2 store-path label (`saturation_v2/analyzer.go`, `aggregateByVariant`)**
- Introduce `var reason string` tracked through the three branches:
  - `len(replicas) > 0` → `reason = k2SourceLabel(replicas)`
  - `capacityStore.Get(...)` path → `reason = "P0-store"`
  - `lookupCompatibleCapacity(...)` path → `reason = "P0-store"`
- Replace `k2SourceLabel(replicas)` in the `vc` struct with `reason`
- Add a test: no live replicas + store record present → `Reason == "P0-store"`

**Step 10 — TA tier reasons (`throughput/analyzer.go`, `resolveITLModel`)**
- Change return type from `(ITLModel, bool)` to `(ITLModel, string, bool)`
- Tier 1 success → reason `"T1-ols"`
- Tier 2 with prior fit (`state.hasFittedB == true`) → `"T2-pinned"`
- Tier 2 cold start → `"T2-default"`
- Failure → `"", false`
- Capture at call site: `model, reason, ok := a.resolveITLModel(...)`
- Add `Reason: reason` to the `VariantCapacity` struct literal
- Add tests for all three tier reasons

## After implementing

1. Run gates: `gofmt -l internal/`, `make test`, `make lint`, `go build ./...` — all clean
2. Single commit with DCO sign-off:
   `git commit -s -m "engine: fix variant reason field — drop cost from log, add store/TA tier reasons"`
3. Write `plans/session/handoffs/plan__wva-log-r2-done.md`
4. Mark this trigger done:
   `mv plans/session/handoffs/wva-saturation-cycle-log__r2-label-fixes.md \
       plans/session/handoffs/wva-saturation-cycle-log__r2-label-fixes.md.DONE`
5. Do NOT push — Dean pushes after review.
