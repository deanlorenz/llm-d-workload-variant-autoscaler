# PR #1113 Review Summary

**Status: DRAFT**

**PR:** [engines/saturation: generic multi-analyzer pipeline with any-up/all-down combine](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1113)
**Head:** `a93bc5d`
**Reviewed:** 2026-05-20

---

## CI

- ✅ `e2e-tests-smoke` — pass (18m13s)
- ✅ `lint-and-test` — pass (2m28s)
- ✅ `DCO` — pass
- ✅ `check-code-changes` — pass
- ✅ `check-full-tests` — pass
- ✅ `gate` — pass
- ⏭ `build-image` — skipping
- ⏭ `e2e-openshift` — skipping
- ⏭ `e2e-tests-full` — skipping

---

## Review Status

CHANGES_REQUESTED by **ev-shindin** (2026-05-19). No other reviews yet.

---

## Comment Threads

### ev-shindin — CHANGES_REQUESTED

**1. `engine_v2.go:140` — RC normalization (open, unanswered)**
Reviewer says `RequiredCapacity` should be normalized w.r.t. the analyzer's own `TotalCapacity`,
not used raw. This relates directly to the dimensionless combine algorithm — RC from two analyzers
with different capacity scales aren't comparable without normalization.

**2. `engine_v2.go:206` — `AnalyzerScoreConfig` thresholds silently dropped for non-saturation analyzers (open, unanswered)**
`AnalyzerScoreConfig` exposes `ScaleUpThreshold`/`ScaleDownBoundary` for all analyzers,
`Validate()` checks both fields for all entries, and the doc says they "override global" — but
the engine only applies them to saturation. Per-entry thresholds for throughput, SLO, etc. are
silently ignored. Reviewer flags the API-behaviour mismatch.

**3. `engine.go:231` — `RegisterAnalyzer` concurrent map access (open, unanswered)**
The map is written by `RegisterAnalyzer` and read concurrently in `runAnalyzersAndScore`. The
doc comment states a "before StartOptimizeLoop" contract but nothing enforces it — a late call
would cause a data race that silently corrupts rather than panics.

---

## Pending Actions

- [ ] **`engine_v2.go:140`** — Normalize `RequiredCapacity` by the analyzer's own `TotalCapacity`
      before combining across analyzers.
- [ ] **`engine_v2.go:206`** — Resolve the `AnalyzerScoreConfig` threshold mismatch: either
      (a) restrict `ScaleUpThreshold`/`ScaleDownBoundary` fields to saturation-only in the struct
      and doc, or (b) route per-analyzer thresholds to each analyzer at call time.
- [ ] **`engine.go:231`** — Enforce the "register before StartOptimizeLoop" contract: add a
      `sync.RWMutex` around the map or gate registration with an `initialized` flag that panics
      on late calls.

---

## Discussion

_[to be filled in with discussion before finalizing]_
