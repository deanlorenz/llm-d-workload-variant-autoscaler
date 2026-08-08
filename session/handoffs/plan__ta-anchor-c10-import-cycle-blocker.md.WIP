# plan__ta-anchor-c10-import-cycle-blocker

from: review (PR-2 internal code reviewer)
to: planner (ta-anchor-dynamic-refresh Type-3 owner)
date: 2026-08-08
priority: **blocking C10** — please land the §2e.2 correction before the coder starts it
re: plan §2e.2 L1169-1170 clears an import cycle that is not clear. Full write-up:
`planning/ta-anchor-dynamic-refresh-review.md` § "C10 pre-registration", Finding 48.

## The defect

§2e.2 L1169-1170 says:

> New import of `internal/config` into `throughput` — **verified no cycle** (`internal/config` imports
> no `internal/engines` package).

The parenthetical is false. `internal/config/config_test.go` is **`package config`** — an in-package
test file — and it imports `internal/engines/analyzers/throughput`, using `throughput.AnalyzerName` at
`:23` as a drift guard on the literal `const throughputAnalyzerName = "throughput"`
(`config.go:341`). The comment at `config.go:338-340` states the duplication is deliberate *because
"internal/config is a lower layer than the analyzers package"*.

Consequence of adding `throughput → config`:

| build | result |
|---|---|
| `go build ./...` | acyclic, **green** |
| `go test ./internal/config/...` | **`import cycle not allowed in test`** |

An in-package test file cannot import a package that depends on the package under test. So the
clearance does not merely overstate — it points away from the cause. A coder who trusts it and builds
first sees green, then hits a cycle whose stated cause the plan has already ruled out in writing.

**Why the saturation_v2 precedent misleads.** `saturation_v2/analyzer.go` imports `internal/config` and
asserts the concrete config type exactly as §2e.2 proposes; that idiom is correct there. It fails for
`throughput` alone, for a reason unrelated to layering: config's test file points at **throughput
specifically**.

**Neither half of `resolveKSat` can dodge the import as specified** — `SaturationScalingConfig`
(`internal/config/saturation_scaling.go:12`) and `DefaultKvCacheThreshold = 0.80` (`:241`) are both in
`internal/config`.

## Option space (yours to decide; stating it because the cheapest-looking path is the harmful one)

1. **Avoid the import** *(my recommendation)*. Assert a narrow method-bearing interface —
   `cfg.(interface{ KvCacheThresholdValue() float64 })` — which needs that one method added to
   `SaturationScalingConfig` *inside* `internal/config` (no cycle), plus a home for the 0.80 fallback
   reachable without importing config. Keeps the documented layering, keeps the drift guard, no test
   surgery. Note the symmetry: duplicate-the-constant-and-guard-it-with-a-drift-test is exactly what
   `config.go:338-341` already does in the other direction.
2. Move the drift guard to external `package config_test`. Legal, but it reads unexported
   `throughputAnalyzerName`, so that must be exported or the guard rewritten — weakening the protection
   the duplication comment relies on.
3. Resolve k_sat at the engine boundary and pass a `float64` into TA. Works (pipeline already imports
   config) but is a bigger change than needed; TA already *receives* `input.Config` and simply never
   reads it.
4. **Delete the drift guard.** Please rule this out explicitly in the plan text. It is the path of least
   resistance, it silently removes real protection, and it is a §4b-classifiable deletion nobody would
   think to classify because it presents as a build fix.

## Severity, stated honestly

**Blocking C10, not a shipped-defect risk.** `make test` covers `./internal/...` and does catch it, so
the gate is sound. The cost is a mid-commit stall against plan text that argues for the wrong diagnosis,
plus the live risk of option 4.

## Not routed to the coder

I have not rung the coder's bell. The plan is its only scope authority and §2e.2 is currently wrong, so
a trigger now would send it to stale text. Suggest correcting §2e.2 and then triggering, if you want it
picked up before C10 starts.

## Also in the same review section (not blocking, no action needed from you)

Four scoreable predictions I will grade against C10 when it lands — P1 the ±10%-tolerance
discrimination trap (I re-derived §2e.3's numbers independently; 2618.93 expected, 2780.56 broken,
6.171% gap, and the ambient `muSat*0.10` window contains the broken value, so a fixture written with the
surrounding idiom proves nothing); P2 `DefaultKSat` to zero references including comments; P3 the stale
`0.85` derivation comment at `analyzer_test.go:259-264`; P4 the ~6% figure staying out of the commit
message. Recorded for scoring, not asks.
