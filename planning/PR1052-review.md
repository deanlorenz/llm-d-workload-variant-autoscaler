<!-- cspell:ignore shindin apimachinery -->
# PR #1052 Review Summary

**Status: DRAFT**

**PR:** [engines/analyzers/throughput: add state management package (PR-3)](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1052)
**Head:** `99a35b0`
**Reviewed:** 2026-05-12

---

## CI

All checks green on `99a35b0`:
- e2e-tests-smoke ✅
- lint-and-test ✅
- check-code-changes ✅
- check-full-tests ✅
- gate ✅

---

## Review Status

**CHANGES_REQUESTED** by ev-shindin (2026-05-11) — "please address review comments"

Awaiting approval — no LGTM yet.

---

## Comment Threads

**ev-shindin** — 7 inline threads, all open and unanswered:

1. `analyzer.go:25` — `variantStates` never pruned (open, unanswered). Stale entries from deleted/recreated VAs cause false shape-change signals — a latent correctness bug, not just a memory issue. `lastObservedAt` is tracked but unused for cleanup.

2. `docs/developer-guide/throughput-analyzer.md:243` — Doc describes ShapeTracker as EWMA but `shape_tracker.go:36` does a direct overwrite (open, unanswered). The doc language is misleading.

3. `docs/developer-guide/throughput-analyzer.md:244` — Doc says window cap is `10` but `DefaultWindowMaxSize = 20`; `10` is `DefaultMinSamples` (the `Ready()` threshold) (open, unanswered). Two separate constants conflated.

4. `analyzer.go:63` — `Observe` reads wall clock directly; window-level tests use explicit timestamps but analyzer-level tests can't exercise time-based pruning (open, unanswered). Suggests injecting `clock.Clock` or accepting `now time.Time`.

5. `observation_window.go:40` — k-values outside `[0.15, 0.85]` are silently dropped; if a workload stays outside that range permanently, the window never fills and `Ready()` stays false with no log or metric (open, unanswered).

6. `analyzer.go:210` — `PrefixCacheHitRate` averaged arithmetically across replicas; during cache warm-up this understates the effective fleet hit rate (open, unanswered). Suggests request-rate-weighted average.

7. `analyzer.go:164` — `variantStates` key uses `|` as separator, but `modelID` is operator-provided and not DNS-constrained; a model ID containing `|` (e.g. `ibm/granite|instruct`) would silently collide (open, unanswered).

**asm582** (open, answered):
Asked how HA state management is handled. Dean replied twice: state is in-memory only, engine loop is gated on leader election, failover causes a warm-up gap (order of minutes) during which TA emits no signal. Documented in the [State and High Availability](https://github.com/llm-d/llm-d-workload-variant-autoscaler/blob/TA2/docs/developer-guide/throughput-analyzer.md#state-and-high-availability) section. No further follow-up from asm582.

---

## TA3 Coverage Check (2026-05-12)

Checked which pending actions are already addressed by TA3 commits (`TA2..TA3`):

| # | Item | Status in TA3 |
|---|---|---|
| 1 | `variantStates` pruning / latent VA-recreate bug | ❌ not addressed |
| 2 | Doc: ShapeTracker described as EMA/EWMA (wrong) | ✅ addressed — "Three EMA floats" text removed |
| 3 | Doc: window cap written as "≤ 10" (should be 20) | ⚠️ partial — old text removed, but config table now says `100` while `constants.go` has `20` |
| 4 | Clock injection / `now time.Time` for test coverage | ❌ not addressed |
| 5 | Log/metric for k-values dropped outside `[0.15, 0.85]` | ❌ not addressed |
| 6 | Request-rate-weighted `PrefixCacheHitRate` average | ✅ addressed — `averageShapeMetrics` uses `VLLMRequestRate`-weighted mean |
| 7 | `variantKey` separator — `modelID` may contain `\|` | ⚠️ partial — comment added saying k8s names are DNS-safe, but `modelID` is operator-provided and not DNS-constrained |

---

## Pending Actions

From ev-shindin's review:
- [ ] Fix `variantStates` pruning — evict stale entries; fix latent shape-change false positive on VA recreate
- [ ] Fix doc/code mismatch: config table says `DefaultWindowMaxSize = 100`; `constants.go` has `20` — align them
- [ ] Add clock injection or `now time.Time` param to `Observe` for time-based pruning testability
- [ ] Add log/metric when k-value is dropped (outside `[0.15, 0.85]`) to surface stuck-window failures
- [ ] Fix `variantKey` separator — `modelID` is operator-provided and not DNS-constrained; `\|` is unsafe

From Claude code review (TA2-introduced code):
- [ ] Silent discard of `Observe()` return in `Analyze()` — change to `_ = a.Observe(...)`
- [ ] `CheckModelMetrics` doc comment overstates contract — reword to match actual short-circuit behavior
- [ ] `averageShapeMetrics()` count==0 branch (`returns 0,0,0`) not tested
- [ ] No concurrent-access / race test for `Observe()` + `VariantState()`
- [ ] `pod_name` label fallback in collector not tested for the 3 new fields
- [ ] `SanityReport.Has()` → replace with `slices.Contains` (`types.go`)
- [ ] `issueSet map[SanityIssue]struct{}` → replace with `sets.Set[SanityIssue]` from apimachinery (`sanity.go`)

---

## Code Review Findings (Claude, 2026-05-11)

TA2-introduced issues are promoted to Pending Actions above.

**Deferred — pre-existing code (out of scope for TA2 PR):**
- `Build()` escaping in `internal/collector/source/query_template.go` — relies on all callers to escape; fragile. Pre-dates TA work — file last touched in #823/#984.

---

## Discussion

_[to be filled in with discussion before finalizing]_
