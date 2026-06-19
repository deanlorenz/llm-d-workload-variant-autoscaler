from: wva-saturation-cycle-log
session: redesign-rewrite

## What changed

The PR #1277 log design was redesigned after review. The old 2-commit stack
(`e92e26ba`, `01bfe940`) is being replaced entirely. Do NOT rebase it.

## Your task

Implement the redesigned logging from scratch on top of `upstream/main`.
Full spec is in `planning/wva-saturation-cycle-log-plan.md` (read it first).

Summary of the new design:
- Two log lines per reconcile cycle per model (not one):
  - `"analyzer-result"` — one per analyzer, emitted in `runAnalyzersAndScore`
  - `"scaling-decision"` — one per model, emitted after optimizer returns
- One generic field added to `VariantCapacity`: `CapacityLabel string`
- `SaturationVariantCapacity` struct is GONE — do not add it
- `K2Priority` stays internal to `saturation_v2` package only

## Rewrite procedure

1. Create a fresh worktree from `upstream/main` (tip `02d06eb2`):
   ```
   git -C /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/repo fetch upstream
   git -C /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/repo worktree add \
     /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/wva-log-rewrite \
     -b wva-saturation-cycle-log-r1 upstream/main
   ```
2. Implement Steps 1–7 from the plan.
3. Run all gates (gofmt / make test / make lint / go build).
4. Write your status file and a `plan__wva-log-rewrite-ready.md` handoff.
   Dean will force-push `wva-saturation-cycle-log-r1` to
   `origin/wva-saturation-cycle-log` to update PR #1277.

## Do not

- Rebase `e92e26ba` or `01bfe940` — replace them entirely.
- Push anything — Dean pushes after reviewing.
- Add `MedianK1`, `MedianK2`, `K2SourceLabel`, `SaturationVariantCapacity`.
- Add optimizer-internal logging (Log B is deferred).
