# ta-model-level-demand — Review

**Status:** FINAL — 2 blocking findings; both routed to coder via planner handoff
**Scope:** `652307bd` (Commit 1), `6f161a5a` (Commit 2) on branch `ta-model-level-demand` (off
`main@f5b7577c`). Reviewed against
[`planning/ta-model-level-demand-plan.md`](ta-model-level-demand-plan.md). Both commits match the
plan's declared boundaries (1 = query + plumbing, no behavior change; 2 = TA demand rewire).

**Gates:** coder's trigger (`review__ta-model-level-demand-ready.md`) reports `make test`,
`gofmt`, `go vet`, `make lint`, `go build ./...` all green, DCO present on both commits.
Independently spot-checked: `go build ./...` clean; `go test
./internal/engines/analyzers/throughput/... ./internal/collector/... ./internal/engines/saturation/...`
all pass; `gofmt -l` on every changed `.go` file — clean. Did not re-run `make lint` or the full
suite (coder already confirmed).

---

## Verified correct

1. **Decision 2a respected — `queueing_model.go` untouched.** `git diff` against
   `internal/collector/registration/queueing_model.go` is empty. The new
   `QueryModelArrivalRate` query is registered exclusively in
   `throughput_analyzer.go`'s `RegisterThroughputAnalyzerQueries`, with a header-comment update
   (three → four queries) and a doc-comment explaining why it doesn't belong in QM's file.

2. **No `model_name` fallback clause on the new query**, per the EPP-metric fact-find
   (`inference_extension_scheduler_attempts_total` never carries `model_name`, only
   `target_model_name`) — matches the plan's explicit instruction not to copy that pattern from
   the flow-control queue metric.

3. **Both `AnalyzerInput` construction sites plumb `ArrivalRate`.** Grepped
   `ArrivalRate:` / `SchedulerQueue:` across non-test code: `engine_v2.go:60` (V2
   `runV2AnalysisOnly`) and `engine_v2.go:125` (V2 `runAnalyzersAndScore`'s per-analyzer input)
   both set it from the same `arrivalRate` value collected once in `prepareModelData`. The third
   `AnalyzerInput{}` site, `engine_queueing_model.go:130` (QM's own path), correctly does **not**
   set it — QM never consumed `SchedulerQueue` either, and per decision 2 continues to read its
   own per-pod `ArrivalRate` from `ReplicaMetrics` directly. Not a missed site.

4. **Per-pod `ReplicaMetrics.ArrivalRate` collection is untouched and regression-tested.**
   `TestCollectReplicaMetrics_ArrivalRatePerPodRetained` pins that the existing
   `scheduler_dispatch_rate` → `ArrivalRate` merge still populates per-pod, which
   `queueingmodel`/`internal/utils/allocation.go` depend on (decision 2).

5. **Model-level combination matches decision #3.** `arrivalDecodeDemand` and `queueDemand` are
   computed independently and both added to `totalDemand` (not folded into each other), then both
   distributed via the same renamed `distributeDemandByRole` helper (was
   `distributeQueueDemandByRole` — generalized, not duplicated, per the plan's explicit
   instruction). `RoleCapacities[role].TotalDemand = arrivalDemandByRole[role] +
   queueDemandByRole[role]`; the "queue term added once, role-distributed" test confirms
   `Σ RoleCapacities[*].TotalDemand == result.TotalDemand` exactly.

6. **Decision #4 (no served-rate floor) is correctly implemented and tested.** `ArrivalRate: 0`
   with `RequestRate: 20` (still draining) yields `TotalDemand == 0` — the per-variant
   engine-rate fallback no longer reaches model-level `TotalDemand` at all now that the arrival
   term is model-level-only.

7. **Warm-up regression correctly avoided, and the fix is well-reasoned.** `avgOL` is accumulated
   from each variant's *tracked* `state.shapeTracker.Current().AvgOutputTokens`, not a fresh
   average over live `input.ReplicaMetrics` — the coder's status file documents catching this
   during implementation (a first draft using live data reintroduced the EPP-warm-up
   spurious-scale-down bug because `averageShapeMetrics` excludes zero-OL replicas). Both
   pre-existing "EPP warm-up" tests still pass with this fix and were extended to also cover the
   model-level path.

8. **Deferred item (k\*-local no longer backfills model-level `TotalDemand`) is exactly the
   plan's documented deferral, not a silent behavior change.** The rewritten "k\*-based local
   demand (no EPP)" test asserts the new, intended split: per-variant `VariantCapacity.TotalDemand`
   still populates (introspection), model-level `TotalDemand` is `0` by design when there's no
   EPP signal and no queue. Coder's status file flags this explicitly as "worth a second look,"
   which is the correct level of transparency for a deferred-but-real behavior change — see
   Findings below for the one related question.

9. **Dev-guide (`throughput-analyzer.md`, Demand Estimation section) accurately reflects the new
   code**, including the exact (unweighted) `avgOL` formula, the Warm-Up Safety rationale, the
   retained-per-variant-introspection-only framing, and the deferred k\*-local note — all Type 4
   compliant (describes current code only, no forward `k_knee` implementation claim). No
   plans-branch identifiers leaked into the doc text.

10. **`CollectModelArrivalRate` mirrors `CollectSchedulerQueueMetrics`'s existing shape**
    (NaN/Inf/negative filtering, debug-level unavailable-metric logging, scalar sum over
    `result.Values`) — consistent style, no new pattern introduced.

---

## Findings

### F1 — BLOCKING (Dean's ruling 2026-07-27): model-level `avgOL` silently diverges from the plan's specified weighting; must be fixed, not accepted

The plan specifies (Overview / Commit 2): *"avgOL is the model-level average output length (the
`averageShapeMetrics` OL, [analyzer.go:637], already **RequestRate-weighted**)."* The intent was
one call to `averageShapeMetrics` across all replicas of the model — a single RequestRate-weighted
average.

The implementation (`analyzer.go:322-326`, `:379-382`) instead computes:

```go
if state.role != domain.RolePrefill {
    totalDecodeITLSat += itlSat
    totalDecodeOL += shape.AvgOutputTokens   // per-variant tracked shape, already weighted *within* that variant
    nDecodeVariants++
}
...
avgOL := totalDecodeOL / float64(nDecodeVariants)   // simple mean *across* variants
```

`shape.AvgOutputTokens` is each variant's own tracked, RequestRate-weighted average over that
variant's replicas (`averageShapeMetrics(healthyMetrics)` at line 130, fed through
`state.shapeTracker`). But the cross-variant combination is an **unweighted mean of per-variant
means** — every non-prefill variant contributes equally to `avgOL` regardless of how many
replicas it has or what share of traffic it carries.

This is a deliberate, well-documented substitution — not an oversight. The coder's status file
and the dev-guide both explain *why*: calling `averageShapeMetrics` fresh on live
`input.ReplicaMetrics` (the plan's literal instruction) would reintroduce the EPP-warm-up
zero-OL regression, since that helper excludes zero-OL replicas from its live average. Using the
tracked per-variant shape avoids that. The substitution of *source* (tracked vs. live) is
correct and necessary. What changed *along with it*, apparently as a side effect rather than a
separate decision, is the *weighting scheme* (per-variant-equal vs. per-replica/request-weighted
across the whole model).

For a model with a single non-prefill variant — the only scenario any test exercises, and
apparently the benchmark's current no-scale-up scenario — `nDecodeVariants == 1` and this
distinction is invisible: `avgOL` is just that one variant's tracked OL either way. It only
diverges when a model has **2+ non-prefill variants with different output-length profiles and/or
different traffic shares** (e.g. two decode-role variants, or a canary/blue-green pair) —
squarely within scope for the multi-analyzer / multi-variant mission this codebase otherwise
supports. In that case the two weighting schemes can produce materially different `avgOL` values,
and hence different `arrivalDecodeDemand` and downstream RC/SC.

No test exercises this: every "two variant" fixture in `analyzer_test.go` uses the same `olA`/`olM`
value for both variants (e.g. the "TotalSupply equals..." fixture at line 1202-1219, and the
role-split "queue term added once" fixture at line 1403-1442 uses one prefill + one decode
variant, not two decode variants). The cross-variant averaging behavior for *heterogeneous*
decode-variant OLs is unverified in either direction.

**Dean's ruling (2026-07-27): the simplification is unacceptable.** Nothing in the plan or the
design docs (TA-demand.md §3.3/§3.5, TA-overview.md) suggests or assumes a model ever has only
one non-prefill variant — multi-variant support (canary, blue/green, multiple GPU tiers) is a
standing capability this codebase otherwise supports throughout (`byVariant`, `RoleCapacities`,
the entire multi-analyzer mission). The plan's literal instruction (RequestRate-weighted average
across all replicas) stands; the coder's fix for the warm-up bug should have preserved that
weighting — e.g. weighting each variant's tracked OL by that variant's `nKV`/replica count
(already in hand in the same loop) — instead of silently dropping to an equal-weight mean.

**Required fix:** re-derive `avgOL` as a weighted combination across non-prefill variants
(weight by replica count or tracked request-rate share — coder's implementation choice, but it
must not be equal-per-variant), and add a test with 2+ non-prefill variants carrying different
`AvgOutputTokens` and different weights (replica counts and/or request rates) that pins the
weighted result — not just that *some* demand is produced.

**Process point, separate from the code fix:** the coder should never have decided this
divergence silently. A behavioral change from the plan's specified formula — even one made for a
good reason, in the course of fixing an unrelated bug — is a decision fork that belongs to Dean
or the planner (see `feedback_doc_accuracy_discipline` — "design evolution is normal, but elevate
forks early"). Burying the weighting-scheme change inside the "bug found and fixed" note in the
status file, framed only as a source change (tracked vs. live data) and not also as a *weighting*
change, meant it surfaced only because this review happened to derive the formula by hand and
diff it against the plan's literal wording — not because it was called out. This should be
captured as a CODER-CONVENTIONS gap alongside the existing semantic-pivot-grep rule: implementing
a fix that changes a plan-specified formula's semantics (not just its data source) must be
flagged as an explicit open question, not folded into a same-paragraph bug-fix note.

### F2 — BLOCKING (Dean's ruling 2026-07-27: needs fix): `docs/developer-guide/multi-analyzer-pipeline.md`'s `AnalyzerInput` field table omits the new `ArrivalRate` field

This PR adds `ArrivalRate float64` to `domain.AnalyzerInput` (`analyzer.go:32` region). The
generic "how to write a new analyzer" contract reference at `multi-analyzer-pipeline.md:171-180`
lists `ModelID`, `Namespace`, `ReplicaMetrics`, `VariantStates`, `Config`, `SchedulerQueue` as the
"key `AnalyzerInput` fields" — `ArrivalRate` is not in that table. This doc wasn't in the plan's
named dev-guide scope (only `throughput-analyzer.md`'s Demand Estimation section was named), so
this isn't a coder process failure — it's a plan gap: `multi-analyzer-pipeline.md` should have
been named too, since it's the canonical `AnalyzerInput` field reference and this PR changed that
struct. Low severity (one missing table row), but worth a one-line fix so a future analyzer
author doesn't miss that the field exists.

---

## Verdict

**NOT ready to push.** Commit 1's plumbing is exactly the plan's mirror-the-queue-pattern
instruction, decision 2a is respected, and Commit 2's demand rewire is otherwise well-tested
against every explicitly-planned invariant (model-level R×L, orphan-merge backstop,
queue-combination linearity, no served-rate floor) with a genuinely-caught warm-up regression
fixed correctly along the way. But **F1 is blocking**: Dean ruled the equal-weight-across-variants
simplification unacceptable — nothing in the plan or design docs assumes single-decode-variant
models, and the coder should have surfaced the weighting-scheme change as an explicit question
rather than deciding it silently while fixing the warm-up bug. **F2 is also blocking** (small doc
fix). Both routed to the planner for coder follow-up; re-review required once landed.

## Update — F1 and F2 landed, both confirmed correct

Two follow-up commits on top of the previously-reviewed two (tip now `4a816dde`):

- **`e800ff87`** (F1) — `avgOL` is now `Σ(nKV_v × shape_v.AvgOutputTokens) / Σ(nKV_v)` across
  non-prefill variants (`totalDecodeOL`/`totalDecodeKV` accumulators, weighted by each variant's
  replica count, already in hand in the loop as `nKV` from `computeVariantSupply`). Confirmed the
  weight is safe from division-by-zero: `computeVariantSupply`'s doc comment states supply and
  `nKV` are both zero together ("All are zero when no replica has KV capacity data"), and the
  `supply == 0 { continue }` check above already guarantees `nKV ≥ 1` for any variant that reaches
  the accumulator — so `nDecodeVariants > 0 ⟹ totalDecodeKV ≥ 1`, same guarantee the pre-fix code
  relied on for `nDecodeVariants`. New test (1 replica @ OL=100, 3 replicas @ OL=300) asserts
  `TotalDemand == ArrivalRate × 250` (the weighted answer) — verified by hand: `(1×100+3×300)/4 =
  250`, correctly distinct from the unweighted `(100+300)/2 = 200` the test explicitly guards
  against regressing to. Dev-guide (`throughput-analyzer.md`, "Warm-Up Safety and Weighting")
  states the weighted formula and explains why single-non-prefill-variant models never see the
  distinction — matches the fixed code exactly.
- **`4a816dde`** (F2) — adds the missing `ArrivalRate` row to `multi-analyzer-pipeline.md`'s
  `AnalyzerInput` field table, correctly typed and described (model-level req/s, no per-pod
  labels, zero when EPP absent/no traffic). Matches the domain struct's own field comment.

Independently re-verified (not just re-trusting the status file): `go build ./...` clean; fresh
(`-count=1`, no cache) `go test` on
`internal/engines/analyzers/throughput/... internal/collector/... internal/engines/saturation/...`
all pass; `gofmt -l` on the two changed `.go` files — clean. Both commits DCO-signed.

**Final verdict: ready to push.** No outstanding findings. F1's process point (surfacing
formula-semantics divergences as their own decision, not folded into a bug-fix note) remains an
open CODER-CONVENTIONS gap for the planner/Dean to close — not something either fix commit needed
to address.
