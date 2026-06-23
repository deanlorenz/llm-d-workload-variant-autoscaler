from: wva-saturation-cycle-log
session: r2-label-fixes-done

## What changed

Commit c8712fc8 on wva-saturation-cycle-log-r1 (wva-log-rewrite worktree).
All gates clean (gofmt/make test/make lint/go build).

## Changes in c8712fc8

**Step 8 — Drop cost from variantEntry (engine_v2.go)**
- Removed `Cost float64 \`json:"cost"\`` from variantEntry struct
- Renamed `Label` → `Reason` with `json:"reason,omitempty"`
- Updated struct literal: `Reason: vc.Reason`
- engine_v2_log_test.go: added `"reason"` assertion, added `NotContains "cost"` assertion

**Step 9 — Sat_v2 store-path label (saturation_v2/analyzer.go)**
- `capacityStore.Get(...)` path → `reason = "P0-store"`
- `lookupCompatibleCapacity(...)` path → `reason = "P0-store"`
- saturation_v2/analyzer_test.go: new Ginkgo test verifies `VariantCapacity.Reason == "P0-store"` when no live replicas but store record exists

**Step 10 — TA tier reasons (throughput/analyzer.go)**
- `resolveITLModel` signature: `(ITLModel, string, bool)` (string before bool)
- Tier 1 → `"T1-ols"`, Tier 2 pinned → `"T2-pinned"`, Tier 2 cold → `"T2-default"`, failure → `"", false`
- Call site: `model, reason, ok := a.resolveITLModel(...)`
- `VariantCapacity.Reason = reason`
- throughput/analyzer_test.go: 3 new It blocks (T1-ols, T2-default, T2-pinned)
- Also: `tier2Replica` has `//nolint:unparam` because `k` parameter always receives 0.75

**Interface rename:**
- `interfaces.VariantCapacity.CapacityLabel` → `interfaces.VariantCapacity.Reason`

## Update CURRENT.md

Update PR Status row for wva-saturation-cycle-log:
- tip: c8712fc8 on wva-saturation-cycle-log-r1 (wva-log-rewrite)
- status: awaiting Dean push to origin/wva-saturation-cycle-log (force-push r1)
