# PR #1052 Review Summary

**Status: DRAFT**

**PR:** [engines/analyzers/throughput: add state management package (PR-3)](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1052)  
**Head:** `99a35b0`  
**Reviewed:** 2026-05-11

---

## CI

All checks green on `99a35b0`:
- lint-and-test ✅
- e2e-smoke ✅
- check-code-changes ✅
- check-full-tests ✅

---

## Review Status

Awaiting approval — no LGTM yet.

---

## Comment Threads

**asm582** (open, answered):
> "I would like to understand how state management is done. FYI, WVA currently runs in HA mode."

Answered in two replies: state is in-memory only (`map[string]*variantState` behind `sync.Mutex`); engine loops are already gated on leader election; on failover the new leader warms up from scratch; during warm-up (a few minutes) the TA emits no signal and the saturation analyzer covers. Documented in [State and High Availability](https://github.com/llm-d/llm-d-workload-variant-autoscaler/blob/TA2/docs/developer-guide/throughput-analyzer.md#state-and-high-availability).

No further response from asm582. No formal change requests.

---

## Code Review Findings (Claude, 2026-05-11)

Deferred to a follow-up PR after TA2 merges. See CURRENT.md § "Deferred PR-3 (#1052) Fixes" for the full list. Summary:

**Go Quality**
- `DefaultWindowMaxSize` code/doc mismatch — `constants.go` has `20`; docs table says `100`
- Silent discard of `Observe()` return in `Analyze()` — should be `_ = a.Observe(...)`
- `CheckModelMetrics` doc comment overstates the contract (says "callers should check `OK()`" but `Observe()` only short-circuits on `SanityIssueNoReplicas`)

**Test Coverage**
- `averageShapeMetrics()` count==0 branch (returns `0,0,0`) not tested
- No concurrent-access / race test for `Observe()` + `VariantState()`
- `pod_name` label fallback in collector not tested for the 3 new fields

**Security**
- `variantStates` map grows unbounded — no eviction of stale variants
- `Build()` escaping relies on all callers; fragile if non-Prometheus sources reuse templates

**Library Reuse**
- `SanityReport.Has()` → replace with `slices.Contains`
- `issueSet map[SanityIssue]struct{}` → replace with `sets.Set[SanityIssue]` from apimachinery

---

## Discussion

_[to be filled in with discussion before finalizing]_
