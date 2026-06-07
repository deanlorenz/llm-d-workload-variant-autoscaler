# TA-PR5 — Code Review

**Status: DRAFT**
**Reviewer:** plan-agent (reviewer role), 2026-06-07
**Branch reviewed:** `TA3` @ `3b1c5ad2` (18 commits above optimizer base
`multi-analyzer-optimizer@4bfac2fa`).
PR-5 specific commits (top 5 of the 18): `87633e84`, `2e47d9fb`,
`f8d92506`, `a06617e3`, `3b1c5ad2`. Earlier 13 are PR-4 / pre-rebase
work that survived the rebase.
**Compared against:** [`TA-PR5-plan.md`](TA-PR5-plan.md) §§ 2–3 and
[`multi-analyzer-design.md`](multi-analyzer-design.md) §§ A–H.

> Method: read each PR-5 commit + the post-PR-5 file states; diff
> against optimizer base; compare with plan §3 by item. No code
> modifications. Coder reported all gates green; not re-run.

---

## What the code does (independent reading)

### Wiring (`87633e84`)
Two new lines in `cmd/main.go`:
```go
registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer())
```
Calls match the optimizer-base `RegisterAnalyzer(name, analyzer)`
signature (no error return; panic on duplicate / late registration —
plan-anticipated error-return form lands when optimizer rebases onto
post-#1225 main).

### Rebase cleanup (`2e47d9fb`)
Mechanical fixups: `Observe(ctx, modelID, ...)` → `Observe(ctx, now,
modelID, ...)` (PR-3's signature on optimizer base);
`llm_d_ai_variant` removed from query templates; e2e fixture
signature; unused `fmt` import dropped. No behavior change.

### Analyzer contract migration (`f8d92506`)
The substantive PR-5 commit. `analyzer.go`:
- Drops local `totalSupply / totalDemand / totalAnticipated`
  accumulation in the per-variant loop. Uses
  `aggregation.SumTotalSupply / SumTotalAnticipatedSupply /
  SumTotalDemand` after the loop.
- Drops model-level `RequiredCapacity` / `SpareCapacity` writes
  (including the EPP/GPS-mismatch SC gate).
- Adds `TotalAnticipatedSupply` to the result struct literal.
- New `distributeQueueDemandByRole(queueDemand, vcs)` splits queue
  demand evenly across active **non-prefill** roles (plan §3.3 d).
- `aggregateRoleCapacities` simplified: no longer takes
  `isEPPByVariant`; takes `queueDemandByRole` instead. Uses
  `aggregation.AggregateByRole` for per-role `Total*`. Drops in-loop
  RC/SC writes and prefill-role RC suppression.
- `anyEPP` and `anyGPSMismatch` still computed but discarded with
  `_ = anyEPP; _ = anyGPSMismatch`.

### Test migration (`a06617e3`)
55 RC/SC assertions migrated:
- `RC > 0` → `result.TotalDemand > result.TotalAnticipatedSupply` +
  `RequiredCapacity == 0`.
- `SC > 0` → `result.TotalSupply > result.TotalDemand` +
  `SpareCapacity == 0`.
- `RC == 0` → `result.TotalDemand <= result.TotalAnticipatedSupply` +
  `RequiredCapacity == 0`.
- EPP/GPS-gated SC tests: assert `SpareCapacity == 0` (always true
  now) plus a comment noting the regression.
- Prefill-role RC test: assert `prefillRC.RequiredCapacity == 0` plus
  a comment about the OL guard.

### Docs (`3b1c5ad2`)
`docs/developer-guide/throughput-analyzer.md`:
- Scaling Signal section: TA publishes `Total*`; engine post-step
  writes RC/SC. Reference to `saturation-scaling-config.md` for the
  formula.
- New Known Regression subsection: PR-5 drops the EPP/GPS-mismatch SC
  gate, restoration deferred.
- GPS Verification: SC-suppression claim removed; consecutive-mismatch
  observation-window-clearing behavior preserved.
- Role-Aware Aggregation: TA publishes raw `Total*` per role; prefill
  RC≈0 falls out of OL guard; queue-demand-per-role described.
- Data flow diagrams refreshed.

---

## Plan-vs-code matrix

| Plan item | In code? |
|---|---|
| §3.1 — `cmd/main.go` wiring with `RegisterAnalyzer` | ✅ (panic API form per current optimizer base; error-return deferred to final rebase per H1 below) |
| §3.2 — drop obsolete engine.go plumbing during rebase | ✅ (no engine.go change in PR-5 commits — production impl already on optimizer base) |
| §3.3 (a) — stop writing model-level RC/SC | ✅ |
| §3.3 (b) — replace local accumulation with `aggregation.Sum*` | ✅ |
| §3.3 (c) — populate `TotalAnticipatedSupply` on result | ✅ |
| §3.3 (d) — lift queue demand to per-role attribution | ✅ (`distributeQueueDemandByRole` evenly across non-prefill roles) |
| §3.3 (e) — drop in-`aggregateRoleCapacities` RC/SC writes | ✅ |
| §3.3 (f) — drop prefill-role RC suppression | ✅ (no per-role RC computation at all now) |
| §3.3 (g) — drop EPP/GPS-mismatch SC gate | ✅ |
| §3.3 (h) — confirm `ReplicaCount = len(variantMetrics)` | ✅ (unchanged) |
| §3.4 (i) — RC>0 / SC>0 inline migration to inequality+0 | ✅ |
| §3.4 (ii) — EPP/GPS SC tests: ~~delete and replace with single regression spec~~ | Revised per discussion: preserve scenarios as-is for future SC-gate PR; rename for clarity. See T1. |
| §3.4 (iii) — prefill-role RC=0 test migration | ✅ |
| §3.4 — **new test specs** asserting `result.TotalSupply == aggregation.SumTotalSupply(...)`, role-level Total*, queue-demand attribution | ❌ (none added; see T2) |
| §3.5 — dev-guide updated with new contract + Known Regression | ✅ |

---

## Findings

### D1 — Stale doc-comment on `Analyze` (correctness/clarity)

`internal/engines/analyzers/throughput/analyzer.go:180-188` (the
function header for `Analyze`):

```go
// RequiredCapacity and SpareCapacity are computed from model-level totals, not
// per-variant deficits. This prevents conflicting signals when one variant is
// overloaded while another has spare capacity. PendingReplicas is included in
// anticipated supply to suppress scale-up thrashing while pods are starting.
// SpareCapacity is only emitted when EPP is deployed (ArrivalRate > 0).
//
// For P/D disaggregated models, RoleCapacities provides per-role breakdowns.
// No role is excluded from supply/demand computation. RequiredCapacity is
// suppressed for the prefill role: decode rate is never the prefill bottleneck.
```

After PR-5 none of this is true:
- TA does **not** compute RC/SC; the engine post-step does.
- SC is no longer EPP-gated (gate dropped).
- Per-role RC suppression for prefill is no longer explicit (relies
  on the OL guard making prefill `TotalDemand ≈ 0` upstream).

This is exactly the kind of stale cross-reference CONVENTIONS Type 3
guidance flags ("any step that changes a function's behavioral
contract … must include a companion verification step: the exact
`grep` search term and the files to scan for stale cross-references
in comments and docstrings"). Plan §3 didn't list this comment as a
target, but a `grep "EPP" / "suppress" / "RequiredCapacity"` over
`analyzer.go` would have caught it.

**Fix:** rewrite the function header to match the new contract: TA
publishes `Total*` (model + per-role); engine post-step writes RC/SC;
queue demand split across non-prefill roles by
`distributeQueueDemandByRole`; prefill `TotalDemand ≈ 0` falls out of
the OL guard.

### D2 — Stale comment on `estimateQueueDemand` use site

`analyzer.go:527`:

```go
// This estimate is used for scale-up only; SpareCapacity still requires EPP.
```

The "SpareCapacity still requires EPP" claim is stale — the EPP gate
on SC was dropped in PR-5. Drop or rewrite to point at the engine
post-step.

### T1 — GPS-verification test block is stale and pass-by-coincidence

`internal/engines/analyzers/throughput/analyzer_test.go:1153-1276`
(the `Describe("Analyze — GPS verification suppresses SpareCapacity",
…)` block).

After PR-5 the SC gate is gone, so TA always emits `SpareCapacity = 0`.
Every test in this block now asserts `SpareCapacity == 0` regardless
of GPS state — there is no GPS-driven branch to exercise. The
test names still suggest the gate exists:

- L1153 `Describe("Analyze — GPS verification suppresses SpareCapacity", …)`
- L1216 `It("suppresses SpareCapacity when GPS deviates > 15% …", …)`
- L1229 `It("does not suppress SpareCapacity when GPS deviates but k* < …", …)`
- L1245 `It("does not suppress SpareCapacity when GenerationTokenRate is zero …", …)`
- L1260 `It("preserves RequiredCapacity when GPS mismatch suppresses SpareCapacity", …)`

The `It`s at L1216, L1229, L1245 all assert `SpareCapacity == 0`.
That assertion passes for the wrong reason now (TA always leaves
SC=0; nothing to do with GPS). The variation in setup (different GPS
values, different k*) doesn't drive different code paths in TA's
output — the GPS branch isn't observable in `result.SpareCapacity`
anymore, only via internal state (observation-window clearing).

Plan §3.4 (ii) originally recommended **delete and replace with a
single spec**. Per discussion with Dean, that recommendation is
**revised**: the gate restoration is deferred to a broader future PR
(see § Gate restoration deferred below), and the GPS-deviation test
**scenarios** (input data: ITL coefficients, k* values, GPS values)
should be **preserved as-is** so they can be re-armed when the gate
returns. Wholesale deletion would force the F3 PR to reconstruct the
scenarios from scratch.

GPS-driven observation-window clearing **is** still observable
(internal state). The current tests don't assert that, but the
scenarios that drive a mismatch are right here — the future PR can
either reapply the SC-suppression assertions or, if window-clearing
needs separate coverage, lift the same scenarios into a new
`Describe("GPS-mismatch observation-window clearing", …)` block.

**Fix (in PR-5):**

- Rename the `Describe` and each `It` so the names reflect what's
  actually being tested *today* (TA leaves SC=0 unconditionally; the
  GPS variations exercise observation-window behavior, not SC).
  Suggested renames:
  - `Describe("Analyze — GPS-mismatch scenarios (preserved fixtures for future SC gate)", …)`
  - L1216: `It("GPS deviates > 15% at k* ≥ DefaultGPSMinKForVerification — fixture for future SC suppression", …)`
  - L1229: `It("GPS deviates but k* < DefaultGPSMinKForVerification — fixture for future SC pass-through", …)`
  - L1245: `It("GenerationTokenRate is zero (metric absent) — fixture for future SC pass-through", …)`
  - L1260: `It("RC remains nonzero under GPS mismatch — fixture for future SC suppression", …)`
- Keep all existing scenario data and `SpareCapacity == 0`
  assertions as-is. Add a one-line comment at the top of the
  `Describe` noting the fixtures are preserved for future SC-gate
  restoration; current assertions are pass-through.

This preserves the F3 PR's test surface with zero data loss and makes
the deferred-gate state explicit in the names.

### T2 — Plan §3.4 "new test specs" are missing

Plan §3.4 listed six new specs to add for aggregation-helper
correctness:

1. `result.TotalSupply == aggregation.SumTotalSupply(result.VariantCapacities)`
2. `result.TotalAnticipatedSupply == aggregation.SumTotalAnticipatedSupply(result.VariantCapacities)`
3. `result.TotalDemand == aggregation.SumTotalDemand(result.VariantCapacities) + queueDemand` (when queue is configured)
4. `result.RoleCapacities[role].TotalAnticipatedSupply` matches per-role aggregation
5. `result.RoleCapacities[role].TotalDemand` includes the queue-demand share for that role
6. `result.RequiredCapacity == 0 && result.SpareCapacity == 0` on `Analyze` return

Item (6) is present (33 instances). Items (1)–(5) — the
linearity/consistency invariants the engine post-step depends on —
were **not added**. `grep "aggregation\.Sum"` in `analyzer_test.go`
returns nothing.

If TA's aggregation drifts (a future refactor inadvertently
double-counts a variant, or skips a role, or fails to add queue
demand), only downstream effects (engine post-step producing wrong
RC/SC) would catch it — and not directly in TA's own test suite.

**Fix:** add the five missing specs in
`internal/engines/analyzers/throughput/analyzer_test.go`. They are
small (one assertion each on existing fixtures) and lock the
contract.

### N1 — `anyEPP` / `anyGPSMismatch` computed-and-discarded (deliberate placeholder)

`analyzer.go:222-300` still computes `anyEPP` and `anyGPSMismatch`
across the per-variant loop, then discards them with
`_ = anyEPP; _ = anyGPSMismatch` after the loop. Reading these as
"dead code" was wrong: per the deferral decision (see § Gate
restoration deferred below), the computation is a deliberate
placeholder for the future per-analyzer status-return PR. The flags
will be needed when the gate is restored. Keep as-is.

### Gate restoration deferred to a broader future PR

PR-5 dropped TA's pre-existing SC gate (`!anyEPP || anyGPSMismatch →
SpareCapacity = 0`). Restoration is **deferred** to a broader PR
that adds a per-analyzer status-return state to the analyzer→engine
contract — applicable to any analyzer (sat_v2, TA, QM, future), not
TA-specific. Tracked in the design doc § Future direction (the
unified F3 entry).

The dropped gate has three underlying conditions; only two need
gating once the contract supports it:

- **Per-replica EPP arrival rate missing** — `ReplicaMetrics.ArrivalRate
  == 0` for all replicas. **Has a fallback** (vLLM `RequestsRate ×
  AvgOutputTokens`); SC suppression not needed for this case alone.
  The pre-PR-5 `anyEPP` proxy was over-conservative — it suppressed
  SC in the legitimately quiet case.

- **EPP scheduler queue signal missing** — `AnalyzerInput.SchedulerQueue
  == nil`. **No fallback**: queue depth is orchestration-layer state.
  Queued-but-not-yet-on-pod demand silently contributes 0 →
  `TotalDemand` under-estimated → engine SC over-estimated → unsafe
  scale-down. Genuinely needs SC suppression.

- **GPS mismatch** — measured `GenerationTokenRate` deviates from ITL
  model's predicted `μ_dec` by > 15% at `k* ≥ 0.30`. Already triggers
  observation-window-clear (recovery via re-fit); SC suppression
  during the mismatch window is additional safety.

Refined gate (for the future PR): `Suppress = (input.SchedulerQueue
== nil) || anyGPSMismatch`. Strictly more accurate than the old
`anyEPP` proxy.

| State | Old `anyEPP` gate | Refined future gate |
|---|---|---|
| Queue + arrival rate present, GPS OK | not suppressed | not suppressed |
| Queue + arrival rate present, GPS mismatch | suppressed | **suppressed** |
| Queue present, arrival rate 0 (genuinely quiet) | suppressed (false positive) | not suppressed |
| Queue absent, arrival rate via vLLM fallback | suppressed | **suppressed** |
| Queue absent, GPS mismatch | suppressed | **suppressed** |

**No in-PR-5 warning log on missing queue.** Adding a `WARN` log when
`input.SchedulerQueue == nil` was considered and rejected: today the
engine collector returns nil in three legitimate states (flow control
disabled, queue empty, genuinely missing), so the log would fire
forever in the legitimate cases. The "genuinely missing" case is
already detectable via EPP's own queue-depth metric exported to
Prometheus — that out-of-band observability is sufficient for
detection in the meantime. Correct gating waits for the future PR,
where `*SchedulerQueueMetrics` gains discriminators for the three
states and analyzers can suppress SC.

`anyEPP` and `anyGPSMismatch` continue to be computed in `Analyze`
(via `_ = ...` placeholders) so that the future PR has minimal
analyzer-side change — flip the discards into status-return writes.
GPS-deviation test scenarios are preserved in
`analyzer_test.go` (see T1) so the future PR can re-arm the
SC-suppression assertions without reconstructing fixtures.

### H1 — Harness state: `RegisterAnalyzer` error-return deferred

`cmd/main.go:455-460` calls
`engine.RegisterAnalyzer(throughput.AnalyzerName,
throughput.NewThroughputAnalyzer())` without checking a return value.
Optimizer base (`4bfac2fa`) still has the panic-API form
`RegisterAnalyzer(name, a) []`; post-#1225-merge `main` has the
error-return form `RegisterAnalyzer(name, a) error`. Coder noted in
the handoff that the error-return wiring is deferred to the final
rebase onto post-#1225 main. This is correct given the current base.

**Track at rebase time:** §3.1's expected form
```go
if err := engine.RegisterAnalyzer(throughput.AnalyzerName,
        throughput.NewThroughputAnalyzer()); err != nil {
    return err
}
```
must land in the same commit that does the final main-rebase.
Optimizer rebase plan (in optimizer-plan.md § Phase 2) doesn't yet
list this — recommend adding to the post-#1228-merge rebase notes.

---

## Confirmed correct

- §3.1 wiring: matches optimizer base contract (panic API).
- §3.2 obsolete engine.go plumbing: dropped during rebase; production
  RegisterAnalyzer is on optimizer base.
- §3.3 (a)–(g): all done. The behavioral migration is faithful to
  plan and design § B/D.
- Linearity invariant at the aggregate level:
  `Σ_role TotalDemand_role = SumTotalDemand(vcs) + queueDemand`,
  preserved through `distributeQueueDemandByRole` (queue demand
  shared across non-prefill roles; per-role variants summed by
  `AggregateByRole`).
- Edge cases for `distributeQueueDemandByRole`:
  - Non-prefill role count = 0 (model is prefill-only): returns nil;
    queue demand goes to model-level only. ✅
  - "both" model: queue demand shared with the single "both" role. ✅
  - P/D model: queue demand all flows to "decode" (matches plan's
    "decode-rate-denominated" framing). ✅
- Disaggregation detection in `aggregateRoleCapacities` (returns
  `nil` for all-empty/all-"both"): equivalent to old
  `hasDisaggregation` check, cleaner. ✅
- Dev-guide § Known Regression: PR-5 SC-gate drop documented;
  follow-up restoration referenced. ✅
- Cross-references in dev-guide updated to new contract; data-flow
  diagrams refreshed. ✅
- Engine-side reads: per design § B, RC/SC at every scope are
  written by the engine post-step (`applyUniversalThreshold`)
  uniformly across analyzers. TA's `TotalAnticipatedSupply` is the
  exact field the post-step formula reads
  (`RC = max(0, TD/scaleUp − Anticipated)`). ✅

---

## Recommendation

Implementation matches plan §3.3 precisely. Test migration covers
the inline assertions but **deviates from plan §3.4 in two specific
ways** (T1: GPS-verification names stale, scenarios preserved; T2:
missing aggregation-helper specs) and **leaves two stale
doc-references** in `analyzer.go` (D1, D2 — the function header and
one comment).

None of D1, D2, T1, T2 is a behavioral bug. T2 is a real
test-coverage gap relative to plan; T1 is naming/clarity (scenarios
preserved by design). D1 and D2 are doc-quality. N1 is a deliberate
placeholder for the future per-analyzer status-return PR. H1 is a
future-tracking note.

Suggested follow-up commits on TA3 (small, focused):

1. **Doc fixes (D1+D2).** Rewrite the `Analyze` function header
   comment + the `estimateQueueDemand` comment to match the new
   contract.
2. **Test rename (T1).** Rename the GPS-verification `Describe` and
   each `It` so names reflect what's tested today (preserved
   fixtures for future SC gate). No assertion changes; data
   preserved.
3. **Aggregation-helper specs (T2).** Add the five missing specs
   from plan §3.4 (`result.TotalSupply ==
   aggregation.SumTotalSupply(...)` and four siblings).
4. **Rebase tracker (H1).** Update optimizer-plan § Post-#1237 (or
   wherever final-rebase notes live) to include the
   `RegisterAnalyzer` error-return migration.

N1 is intentionally not in the follow-up list — the placeholders
stay.

The PR is close to merge-ready. Items 1–3 are all small and
contained to TA3.

---

## References

- [`TA-PR5-plan.md`](TA-PR5-plan.md) — PR-5 plan reviewed against.
- [`TA-Plan.md`](TA-Plan.md) — TA mission roadmap.
- [`multi-analyzer-design.md`](multi-analyzer-design.md) — engine
  contract (§§ B, D, H).
- [`multi-analyzer-optimizer-plan.md`](multi-analyzer-optimizer-plan.md)
  § Phase 2 — sibling fix plan (engine post-step is the dependency
  TA-PR5 builds on).
