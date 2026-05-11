# PR #1051 Review Summary

**Status: DRAFT**

**PR:** [collector/registration: register throughput analyzer queries (PR-1, PR-2)](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1051)  
**Head:** `c405e8d` (rebased 2026-05-11; previous tip `900c94c`)  
**Reviewed:** 2026-05-11

---

## CI

All checks green on `900c94c`:
- lint-and-test ✅
- e2e-smoke ✅
- check-code-changes ✅
- check-full-tests ✅

---

## Review Status

**APPROVED** by `ev-shindin` (2026-05-09):
> "Thanks @deanlorenz. Please rebase again, then merge."

---

## Comment Threads

All inline comments resolved. Two rounds:

**Round 1** (ev-shindin, 2026-04-28) — fixed in `04f6571` / `e84207d`:
1. `docs/developer-guide/throughput-analyzer.md:1` — doc was in wrong directory → moved to `docs/developer-guide/`
2. `docs/developer-guide/throughput-analyzer.md:19` — PR-3 content not scoped → added Status callout and pending markers
3. `docs/developer-guide/throughput-analyzer.md:161` — Architecture section described non-existent types → marked pending
4. `throughput_analyzer_test.go:36` — redundant "no-panic" test → replaced with duplicate-registration panic test
5. `replica_metrics.go:403` — pod-label fallback pattern undocumented → added package-level doc comment

**Round 2** (ev-shindin, 2026-05-04) — fixed in `900c94c`:
1. `throughput_analyzer.go:27,60,90,128` — `sum(rate) × avg(tokens)` vs `Σ_{r∈V}(rate_r × tokens_r)` (4 instances); the two diverge when OL varies across replicas → corrected to per-replica notation; developer guide updated to match
2. `docs/developer-guide/throughput-analyzer.md:274` — wrong constant `QueryFlowControlQueueSize` → corrected to `QuerySchedulerQueueSize`
3. `throughput_analyzer.go:73` — list column alignment → fixed
4. `replica_metrics.go:140` — error message "failed to refresh saturation metrics" stale after query scope widened → updated to "failed to refresh replica metrics"

---

## Pending Action

- [ ] Rebase onto current main tip (ev-shindin's merge instruction)
- [ ] Merge

---

## Discussion

_[to be filled in with discussion before finalizing]_
