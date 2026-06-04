# PR #1052 (TA2) — Deferred Fixes Plan

> **Status: DEFERRED** — Tracking task for the follow-up PR after PR #1052
> (TA2 — `engines/analyzers/throughput`: state management, ShapeTracker,
> ObservationWindow, SanityReport) merged on 2026-05-19.
>
> 10 issues found during Claude code review of PR #1052 were deferred to a
> follow-up PR rather than landing in PR #1052. This doc tracks them so they
> are not lost and can be picked up in a single grouped fixup PR.

---

## Source

Found during Claude code review of PR #1052 (TA2) before merge. Each item is a
small, self-contained fix; together they make a single follow-up cleanup PR
sized similar to a typical doc-only PR.

PR #1052: <https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1052>
Review doc: [`PR1052-review.md`](PR1052-review.md) (FINAL).

---

## Items

### 1. `DefaultWindowMaxSize` code/doc mismatch

`internal/engines/analyzers/throughput/constants.go` defines
`DefaultWindowMaxSize = 20`; the developer-guide doc table says `100`.

**Fix:** confirm intended value with Dean and align both. Likely the doc value is
the historical pre-tuning placeholder; code value (20) is the operational
default.

### 2. Silent discard in `Analyze()`

`internal/engines/analyzers/throughput/analyzer.go`: `a.Observe(...)` return
value is silently dropped.

**Fix:** assign explicitly: `_ = a.Observe(...)`. Documents the deliberate
discard.

### 3. Misleading `CheckModelMetrics` doc

Comment says "callers should check `report.OK()` before Observe" but `Observe()`
only short-circuits on `SanityIssueNoReplicas`. Other issues are passed through.

**Fix:** reword the doc-comment to match the actual contract — `Observe()`
short-circuits on `NoReplicas` only; callers may still want to inspect the
report for non-fatal issues.

### 4. `averageShapeMetrics()` zero-count branch untested

Branch where all replicas have `IL ≤ 0` or `OL ≤ 0` is not exercised by tests.

**Fix:** add a Ginkgo spec covering the all-zero-count case. Verify downstream
`ShapeTracker` behavior (no shape update; window not advanced).

### 5. No concurrent-access test (`-race`)

Package has no `-race` test for simultaneous `Observe()` + `VariantState()`.

**Fix:** add a `-race` scenario with goroutines hitting `Observe()` and
`VariantState()` concurrently for a fixed duration; assert no data race.

### 6. `pod_name` fallback untested in collector

The collector accepts `pod_name` as a label fallback for `GenerationTokenRate`,
`KvUsageInstant`, and `VLLMRequestRate`. Not exercised in tests.

**Fix:** add collector tests using `pod_name`-only labels for each of the three
queries; verify the fallback is read.

### 7. Unbounded `variantStates` map

`internal/engines/analyzers/throughput/analyzer.go` maintains a per-variant
state map that grows monotonically. No eviction.

**Fix:** add eviction pass keyed on `lastObservedAt > 2 × DefaultObservationMaxAge`.
Also add `MaxLength` validation to `spec.modelID` in the CRD to prevent
adversarial unbounded growth.

### 8. PromQL `Build()` escaping fragility

`EscapePromQLValue` is called externally to `Build()`. Easy to forget; produces
unsafe PromQL queries.

**Fix:** either (a) move `EscapePromQLValue` inside `Build()` so it's always
applied, or (b) add explicit doc contract + a test demonstrating the escape
requirement. (a) is preferred.

### 9. `SanityReport.Has()` → `slices.Contains`

`internal/engines/analyzers/throughput/types.go` `SanityReport.Has()` is
implemented as a manual loop. Standard library `slices.Contains` works.

**Fix:** replace loop body with `return slices.Contains(r.Issues, issue)`.

### 10. `issueSet` map → `sets.Set[SanityIssue]`

`internal/engines/analyzers/throughput/sanity.go` uses
`map[SanityIssue]struct{}` as a set. Replace with
`sets.New[SanityIssue]()` from `k8s.io/apimachinery/pkg/util/sets`.

**Fix:** mechanical rewrite. Already a runtime dependency.

---

## Coordination

- All fixes target `internal/engines/analyzers/throughput/` and adjacent collector
  code on `main`. Independent of TA3 / multi-analyzer / threshold work.
- **Recommended landing:** single grouped fixup PR after TA3 merges (avoids
  rebase friction with TA3).
- Estimated PR size: ~10 commits (one per item) or 1–3 grouped commits — pick
  whichever yields cleaner review. Each item is small enough to review on its
  own.
- DCO sign-off on every commit per CONVENTIONS.

---

## References

- [`PR1052-review.md`](PR1052-review.md) — original review doc that surfaced
  these items.
- [`TA-PR3-plan.md`](TA-PR3-plan.md) — Type 3 plan for PR #1052 itself
  (state management, ShapeTracker, ObservationWindow, SanityReport).
