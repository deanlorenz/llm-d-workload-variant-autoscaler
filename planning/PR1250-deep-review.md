# PR #1250 (TA3 / ThroughputAnalyzer) — Deep Critical Code Review

**Type:** 6 (review) · **Status:** DRAFT · **Date:** 2026-06-17
**Scope:** entire TA3 diff vs `upstream/main@04f95779` (39 commits, ~2200 LOC prod + ~2900 LOC test)
**Method:** code-only review, independent of the plan docs. Five subsystem passes (core
analyzer + ITL math read first-hand by the plan-agent; collector, wiring/gate, and test
quality by parallel review agents). Reviewers were explicitly told **not** to read any
plan/`*-plan.md`/`*-review.md` doc — findings reflect the code on its own merits.

**Purpose:** surface *every* problem for a single consolidated fix later (not incremental
patches). This is why the code went through 3+ reviewer rounds: each round fixed one
symptom; the systemic issues below were never addressed as a whole. **No code was edited
and no GitHub comment was posted** during this review.

---

## Post-merge addendum — findings superseded by ev-shindin's testing fixes (2026-06-16)

**PR #1250 merged as `efca1b4c` (squash, 2026-06-16).** Two follow-up commits by ev-shindin
landed on `main` the same day as part of the merge:

### `34c9be9b` — fix(throughput): exclude booting replicas from TotalSupply; guard A in ITL fit

**Supersedes / modifies these review findings:**

| Finding | Status after 34c9be9b |
|---|---|
| **A-B1 supply half** — booting KV=0 replicas inflated `TotalSupply` via `ReplicaCount=len(variantMetrics)` → spurious scale-down during scale-out | **FIXED** — `computeVariantSupply` now returns `nKV` (count of KV-capable replicas); `ReplicaCount = nKV` and `TotalCapacity = nKV × perReplicaSupply`. A regression test was added. |
| **A-S1** — `TotalCapacity` inert (not consumed by aggregation) | **RESOLVED differently** — `TotalCapacity = nKV × perReplicaSupply = supply`; `SumTotalSupply` computes `ReplicaCount × PerReplicaCapacity` = same value. `TotalCapacity` is now consistent with the aggregation contract and no longer cosmetic. Review recommendation to *delete* the field is superseded; the field is now load-bearing for doc contracts. |
| **B-S1** — NaN/Inf A not guarded in `FitITLModel` | **FIXED** — explicit `math.IsNaN(A) \|\| math.IsInf(A,0)` guard added before `A <= 0` check. |
| **A-S2** — EPP warm-up: `computeDemand` accumulated `ArrivalRate × AvgOutputTokens` even when `AvgOutputTokens==0` | **CLARIFIED** — guard `if m.AvgOutputTokens > 0` added inside the EPP loop (behavioral no-op per commit message; clarifies warm-up intent). |

**A-B1 demand half still open:** `computeLocalDemand` still runs on the unfiltered
`variantMetrics` slice, so a replica with `k*=NaN` or `k*>1` can reach the demand
computation. Defended by the collector at scrape time, but not at the analyzer level.

### `b2f1d7ef` — test(e2e): make multi-analyzer scale-up deterministic via fake-metrics

**Context:** The e2e "ThroughputAnalyzer scale-up signal" test was unreliable — it relied on
the simulator organically crossing the scale-up threshold under bounded load. Static
`--fake-metrics` can't drive TA inputs (they're counter rates, not gauges), so the test was
converted to drive saturation via a fake kv-cache-usage gauge instead and renamed
"multi-analyzer scale-up (saturation-driven, throughput co-registered)". A coverage honesty
comment was added: the test validates the multi-analyzer engine path, not TA-driven demand.

**Impact on review findings:**
- **E-e2** — "test never verifies TA authored the scale decision": **confirmed explicitly**.
  The commit message states: "throughput cannot be exercised end-to-end here; its scale-up
  math is covered by unit tests." The both-enabled e2e test is now documented as a
  multi-analyzer *wiring* smoke test, not a TA signal test. E-e2 stands — TA-isolated
  scale-up signal has no e2e coverage; this is now a known, documented gap.
- **E-e1/E-e3/E-e4** — e2e robustness issues (Skip-hiding, AfterAll best-effort, ObservedGeneration
  gap): still open.

**All other findings in this review remain valid as written.**

---

---

## Executive summary — the systemic story

The leaf-level numerical code (ITL OLS fit, sanity checks, window math, shape tracking) is
**solid** — tight, well-guarded, well-tested. The damage is concentrated in three seams that
were patched reactively across rounds:

1. **The analyzer's output contract is split in two** ("TA publishes Total\*; the engine
   post-step writes RC/SC"). This single decision is the root of the worst test rot: ~20
   unit assertions are `Expect(RequiredCapacity).To(Equal(0.0))` — unconditionally true —
   so the headline "scale up/down" tests assert almost nothing. The analyzer cannot be
   unit-tested for the thing it exists to produce.

2. **There is no single canonical "instance key" in the collector.** The "key-merge fix"
   landed for the 3 throughput queries vs KV, but the scheduler-dispatch loop keys on a
   *different* port label with *reversed* pod-label precedence, and the throughput loops
   `continue`-skip on any key miss with a justification copied (wrongly) from the
   cache-config block. Merge correctness depends on loop order and label uniformity that
   nothing enforces.

3. **"Off by default" and "disabled" are enforced by config-file *content*, not by code.**
   The registration gate defaults `Enabled==nil → true`; TA stays off only because the
   default YAML omits the throughput entry. A future YAML edit silently flips a production
   safety default with no test or log signal, and a runtime configmap edit to enable TA is
   silently ignored (sticky registration, no warning).

Plus a layer of **dead/placeholder code retained "for a future PR"** (`_ = anyEPP`,
`_ = anyGPSMismatch`, the always-zero RC/SC fields, the dead `FreshnessStatus=="stale"`
branch, GPS-fixture `It`s that assert nothing) that inflates apparent coverage and misleads
readers.

Severity counts (de-duplicated): **BUG/latent-BUG: 11 · DESIGN: 12 · SMELL: 14 · NIT: 9 ·
coverage GAP: 7.**

---

## A. Core analyzer — `internal/engines/analyzers/throughput/analyzer.go`

### BUGs / latent BUGs

**A-B1 — `computeLocalDemand` / `computeVariantSupply` run on *unfiltered* metrics; an
out-of-range or NaN k\* propagates into demand.** `analyzer.go:274,279,285`
`Analyze` computes supply (`:274`) and demand (`:279,:285`) from the **unfiltered**
`variantMetrics`, by design (to count booting replicas in supply). But the same unfiltered
slice contains replicas that *failed sanity* — e.g. `KvUsageInstant > 1` or `NaN`
(`SanityIssueKVOutOfRange`). `computeLocalDemand` (`:561-569`) only skips `k* <= 0`; a
`k*=1.5` glitch yields `N_dec = 1.5 × KV_max / KVreq` (inflated demand → spurious scale-up),
and a `NaN` k\* yields `NaN` demand → `NaN` `TotalDemand` → `NaN` `Utilization` on the
result, which then flows to the engine. The healthy filter exists (`filterHealthyForShape`)
but is applied only to ITL fitting and GPS, not to supply/demand. Confidence: medium — the
collector *currently* guards NaN/range on k\* at scrape time (see C-G4), so this is mostly a
defense-in-depth gap today, but the analyzer trusts an invariant it does not enforce.
*Fix direction:* compute supply/demand from a slice that includes booting (k\*=0,
cap-present) replicas but excludes sanity-failing ones; or clamp/guard k\* ∈ [0,1] and reject
NaN inside both helpers.

**A-B2 — Tier-2 ITL model skips the `A·k_sat + B > 0` guard that Tier-1 enforces.**
`analyzer.go:494-502` vs `itl_model.go:61`
`FitITLModel` rejects a fit when `A·DefaultKSat + B <= 0` (`itl_model.go:61`). The Tier-2
constrained fit in `resolveITLModel` only checks `A > 0` (`:496`) and returns
`ITLModel{A, baselineB}` with no saturation-positivity guard. With a negative pinned
`baselineB` (a valid Tier-1 B can be slightly negative) and a small refit `A`, Tier-2 can
return a model where `ITLAt(k_sat) <= 0`. It is caught downstream at `:270` (`itlSat <= 0 →
continue`), so it does not crash — but the variant is then silently dropped despite Tier-2
"succeeding," and the asymmetry between the two fit paths is a latent trap. *Fix:* apply the
same `A·k_sat+B>0` guard in Tier-2 (factor a shared `validModel(A,B)` helper).

**A-B3 — `ObservationWindow.Add` rejects NaN ITL but not NaN k; a NaN k poisons the window.**
`observation_window.go:42-47`
The range check `k < minK || k > maxK` is *false* for `k = NaN` (all NaN comparisons are
false), so a NaN k passes the gate; only ITL is NaN-checked (`:45`). A NaN k is appended and
contaminates every subsequent OLS fit (sums → NaN → fit rejected at `itl_model.go:56`) until
it ages out (30 min) or is evicted after 20 newer samples. Today `Observe` only adds from
`healthyMetrics` (NaN k is filtered as `KVOutOfRange`), so it is not reachable in the current
call path — but `Add`'s doc contract ("k ∈ [minK,maxK]") is violated and the guard is one
`math.IsNaN(k)` away. *Fix:* reject `math.IsNaN(k)` in `Add`.

### DESIGN

**A-D1 — Split output contract (TA emits Total\*; engine post-step computes RC/SC) makes the
analyzer untestable in isolation and is the root cause of the tautological test suite.**
`analyzer.go:357-379`
RC/SC are left zero by design and a separate engine post-step fills them. The *decision* the
analyzer exists to make (scale up/down) is therefore never observable from a unit test of the
analyzer — see E-B1/E-D1 for the resulting test rot. This is defensible as an architecture
but it means the analyzer + post-step must be tested *together* (integration), and that test
does not exist. *Fix direction:* either (a) have the analyzer compute RC/SC itself behind the
same helper the post-step uses, or (b) add an engine-level integration test that drives the
post-step so the end-to-end scale decision is asserted; then delete the `== 0.0` unit
assertions.

**A-D2 — `anyEPP` / `anyGPSMismatch` are computed then discarded (`_ =`); the EPP plumbing
through `computeDemand`'s `isEPP` return is entirely dead.** `analyzer.go:295-297,304-305,
365-366`
The SpareCapacity-suppression gate that consumed these was removed (deferred to #1261). The
booleans, the `isEPP` return value, and the per-variant `anyEPP` accumulation are retained as
"placeholders." This is dead code that a reader must reverse-engineer; `checkVariantGPSMismatch`
is still *called* for its window-clear side effect (`:304-316`), but its boolean *return* is
only used to set the discarded `anyGPSMismatch`. *Fix:* drop the dead aggregates and the
`isEPP` return until #1261 actually needs them (git remembers); or land #1261's gate. Keep
the window-clear path.

**A-D3 — `Analyze` acquires `a.mu` three times with gaps (role-update → Observe → main loop),
relying on an undocumented "single-flight per model" assumption that the engine boundary does
not guarantee.** `analyzer.go:214-220, 223, 227`
One analyzer instance is shared across all models. If the engine ever analyzes models
concurrently, the lock gaps allow interleaving (and the whole-map eviction in `Observe`,
`:159-163`, runs under lock but between the gaps). State is per-variant-key so corruption is
unlikely, but the safety rests on an assumption stated only in a code comment (`:211-212`),
not enforced. *Fix:* document the single-flight contract at the engine call site, or hold the
lock across the role-update+Observe+analyze sequence (Observe would need a lock-free inner
form).

**A-D4 — `Analyze` calls `time.Now()` internally (`:203`) instead of taking an injected
clock; combined with A-D1 this makes deterministic testing of time-dependent paths (pruning,
eviction, freshness) impossible.** *Fix:* thread a clock/`now` through `AnalyzerInput` or the
constructor (Observe already takes `now` — extend the same pattern up).

**A-D5 — Stale `VariantState()` snapshot fields.** `analyzer.go:289-292`
`lastITLModel`/`lastPerReplicaSupply`/`lastTotalSupply`/`lastDemand` are updated only for
variants that pass every early-`continue` (`:241,247,266,272,277`). A variant that is skipped
this cycle keeps last cycle's values; `VariantState()` then reports stale calibration as
current. Used only for tests/logging today, but misleading. *Fix:* reset or stamp these on
skip, or document that the snapshot is best-effort/last-successful.

### SMELL

**A-S1 — `TotalCapacity` field is populated (`:331`) but never read downstream.** Confirmed:
`aggregation.SumTotalSupply` computes `Σ ReplicaCount × PerReplicaCapacity` and never reads
`vc.TotalCapacity` (`aggregation.go:40-46`); `AggregateByRole` likewise. The field is
cosmetic. (This was the "F2" round-3 fix — it is correct but inert.) *Fix:* either consume it
consistently or drop it from `VariantCapacity` to avoid a "looks load-bearing but isn't"
trap.

**A-S2 — `computeDemand` returns `isEPP` with subtle "EPP present but unusable" semantics
that the only consumer (`anyEPP`, now dead) cannot distinguish.** `analyzer.go:521-544`
The F1 warm-up fix is correct (fall through to vLLM, then caller falls to local), but the
`isEPP` flag now means "EPP present" regardless of whether it produced demand, and nothing
acts on it. Folds into A-D2. *Fix:* remove the return until needed.

**A-S3 — Comment at `:347-349` asserts "`nDecodeVariants > 0` is guaranteed here" but the
guard `if nDecodeVariants > 0` immediately follows (`:350`).** Either the invariant holds and
the guard is dead, or it doesn't and the comment is wrong. (It does hold — every increment is
gated by supply>0 — so the guard is defensive-redundant.) Minor: reconcile comment and guard.

**A-S4 — Long-form design prose in the `Analyze` doc comment (`:168-194`) duplicates
`docs/developer-guide/throughput-analyzer.md` and will drift.** Acceptable as orientation,
but the two will diverge under future edits. *Fix:* trim to the contract; point to the dev
guide for the math.

### NIT

**A-N1 — `variantKey` uses a `\x00` delimiter (`:417`); fine, but the same key format is
re-derived in 3 places** (`:96,216,238`) via the helper — good — yet the eviction loop
(`:159`) iterates raw map keys, coupling eviction to the delimiter implicitly. No bug; note
for future key-format changes.

---

## B. ITL model / window / sanity / constants

The math here is the strongest part of the PR. Findings are minor.

**B-S1 — Tier-2 positivity guard missing — see A-B2** (the fix lives here: factor a shared
`func validITL(A, B float64) bool` used by both `FitITLModel` and `resolveITLModel`).

**B-S2 — `ITLModel.IsZero()` (`itl_model.go:14`) is defined but, after the changes, only the
`(model, ok bool)` return is used to signal "no model"; `IsZero` appears unused in the
analyzer path.** Verify and drop if dead.

**B-N1 — `DefaultKSat = 0.85` is duplicated as both the saturation threshold *and* the
`DefaultMaxObservableK = 0.85` upper window bound** (`constants.go:45,56`). They are
conceptually different (one is "where we evaluate capacity," the other "above this the linear
model breaks") but share a value and a `TODO: unify` (`:55`). A future change to one will
silently couple to the other if someone "DRYs" them. *Fix:* keep them distinct named
constants (already done) and add a comment that the shared 0.85 is coincidental, not a
dependency.

**B-N2 — `DefaultBaselineITLSec = 0.006` is described as "H100 SXM5-derived"
(`constants.go:60`) — a hardware-specific magic number baked into a hardware-agnostic
analyzer.** For non-H100 variants Tier-2 (before any Tier-1 fit) will mis-estimate. Acceptable
as a bootstrap default but worth a louder caveat / future per-accelerator table. (Mitigated
once `lastFittedB` is learned.)

**B-N3 — `sanity.go:53` reads `Metadata.FreshnessStatus == "stale"`, but the collector
hardcodes `FreshnessStatus: "fresh"` on every emitted metric (see C-S5/D-...) — this entire
sanity branch is dead.** Cross-subsystem; tracked under the collector findings. *Fix:* either
populate freshness in the collector or delete the dead branch + `SanityIssueStaleMetrics`.

---

## C. Collector — `internal/collector/replica_metrics.go` + `registration/throughput_analyzer.go`

*(From the collector review agent; verified against the code.)*

### BUGs

**C-B1 — The scheduler-dispatch loop keys pods differently from every other loop; ArrivalRate
silently fails to merge and fires a misleading warning every cycle.** `replica_metrics.go:
596-614` vs `:419`, `:611-614`
Every other loop keys via `buildInstanceKey` → `podName:<port-from-instance-label>`. The
scheduler loop builds `podName:<port-from-port-label>` — a different port source — and
reverses the `pod`/`pod_name` precedence (see C-N5). When the two ports differ, ArrivalRate
lands in an orphan entry (dropped at `:782`) and the KV/queue entry shows
`hasArrivalRate=false`, tripping the "possible pod/pod_name label mismatch" warning (`:865`)
every cycle. It "works" only when scrape-port == serve-port — which is exactly why it survived
review. *Fix:* route all loops through one key-derivation helper with a single defined port
source.

**C-B2 — `buildInstanceKey` produces inconsistent keys across queries when the label set
varies (`podName:port` vs bare IP:port vs bare podName), so the throughput loops' skip-unknown
silently drops real data.** `replica_metrics.go:260-277, 697-739`
Port is only parsed when `instance != "" && podName != ""`; otherwise the key falls back to
bare `instance` (IP:port) or bare `podName`. Two queries for the same pod that disagree on
which labels they carry resolve to different keys and never merge. *Fix:* one deterministic
per-pod key independent of which labels a given query happens to carry.

**C-B3 — Skip-unknown (`continue`) on the 3 throughput loops is gated on the wrong signal and
its justifying comment is factually wrong.** `replica_metrics.go:701-703,719-721,737-739`
The comment ("skip pods the KV/queue queries didn't see (scrape skew)") is copied from the
cache-config block (`:478-491`) where it is correct because that query is namespace-wide. But
the throughput queries are `model_name`-filtered (`throughput_analyzer.go:110,123,138`) — they
*cannot* return foreign pods. The only way to hit the skip is key skew (C-B1/C-B2) or a partial
KV-query failure — i.e. the skip masks a real bug instead of dropping noise. *Fix:* since these
queries are model-scoped, a miss is an anomaly — log it (with the instanceKey) or create the
entry, don't silently drop.

### DESIGN

**C-D1 — Throughput fields have no `has*` sentinel: "metric absent" and "genuine 0" are
conflated** (`replica_metrics.go:366-368` set at `:704-742`). A genuinely-absent k\*
masquerading as `k*=0` flows into the OLS observation window as a real zero point, biasing the
ITL(k)=A·k+B fit toward the intercept. This is issue #1264, unresolved for these 3 fields.
*Fix:* add `hasGenerationTokenRate`/`hasKvUsageInstant`/`hasVLLMRequestRate` or move to
`*float64`. (Pairs with A-B1: the analyzer side must then exclude absent k\* from supply/demand
*and* calibration.)

**C-D2 — `buildInstanceKey` (hence `locator.Locate`) is called per-sample in every loop — the
same pod is re-resolved 11+ times/cycle — and the locator's scale-target→scaler step is
explicitly uncached.** `replica_metrics.go:245-258` + 11 call sites. The 3 throughput loops
pay the full `Locate` cost only to throw away the returned `vaName` (`_`). Free when the
`llm_d_ai_variant` label is present (label fast-path), expensive precisely in the
Deployment/LWS layouts the owner-walk fallback was added to serve. *Fix:* resolve
`(key, podName, vaName)` once per pod per cycle and memoize; give loops that discard `vaName` a
key-only path.

**C-D3 — Map-entry creation is scattered across many loops, each seeding `podName`/`vaName`
from its own labels; correctness depends on which loop creates the entry first (loop/source
order).** `replica_metrics.go:424-678` (6 creation sites). The scheduler loop seeds an entry
with no `vaName`. Masked today by KV-loop-runs-first ordering. *Fix:* centralize a
`getOrCreate(key, labels)` that resolves attribution consistently.

**C-D4 — Per-cycle observability gauges (`SetMetricsFreshnessStatus`, `SetMetricsPodsDiscovered`)
are set per-model but keyed only by `(vaName,status)` / `(namespace)`, so multiple models in one
namespace clobber each other's gauge (last-writer-wins).** `replica_metrics.go:762,902-906`.
*Fix:* key by `(namespace, modelID)` or accumulate.

### SMELL

**C-S1 — Wrong skip-justification comment (the cache-config copy-paste) — see C-B3.**
`replica_metrics.go:702,720,738`.

**C-S2 — Shipped query comments reference closed/reversed work: "`llm_d_ai_variant` will be
dropped … once PR #1260 … and issue #1263 … land."** `throughput_analyzer.go:105-106`. #1260
and #1263 are *closed/superseded by #1267*, which *retains* the label by design. The comment
describes a reversed decision and names dead issues (and violates the no-PR/issue-refs-in-code
convention). *Fix:* delete the forward-looking sentence; the label is part of the design.

**C-S3 — The 3 throughput fields carry no freshness timestamp** (`replica_metrics.go:365-368`
vs the 9 tracked at `:373-408`), so a stale k\* (the OLS calibration input) can never be flagged
stale. Pairs with B-N3. *Fix:* track timestamps for the throughput fields or document that they
piggyback on the KV timestamp.

**C-S4 — A single 12-query `Refresh` records its duration under 3 query-type buckets and, on
error, increments 3 error counters** (`replica_metrics.go:324-332`) — arbitrary triple-counting.
*Fix:* one batch-labeled record.

**C-S5 — `Metadata.Age` / `FreshnessStatus` are hardcoded to `0` / `"fresh"` on every emitted
metric** (`replica_metrics.go:892-896`), even though real per-metric staleness was just computed
into a local map. This makes the analyzer's `FreshnessStatus=="stale"` sanity gate (B-N3) dead.
*Fix:* populate from the worst per-pod timestamp, or delete the dead branch end-to-end.

**C-S6 — `CollectSchedulerQueueMetrics` truncates float gauges via `int64(value.Value)`
(`:951,960`); 0.9 → 0 while still setting `hasData=true`.** *Fix:* round or document.

### NIT
C-N1 `LocateByVariant` (shadow-pod path) is unreachable from the collector — add a one-line
note that shadow pods ride the retained label. · C-N2 `vaEventTracker` is shared between
`UnattributedReadyPods` and `MetricsUnavailable` events, so a VA that fired one is suppressed
from the other in the same cycle (`:108-141`) — key by `(vaKey, eventType)`. · C-N3 malformed
`instance` ending in `:` leaks a trailing-colon key (`:263-265`). · C-N4 `getScaleTargetNames`
allocates per skipped pod on the info path (`:807-810`) — gate behind DEBUG. · C-N5 package doc
says precedence `pod → pod_name` (`:30-33`) but the scheduler loop reverses it (`:596-601`) —
reinforces C-B1.

---

## D. Wiring / registration gate — `cmd/main.go` + `interfaces/saturation_analyzer.go`

*(From the wiring review agent; verified.)*

### latent BUGs

**D-B1 — `RegisterThroughputAnalyzerQueries` panics on a second call (registry `.Register`
panics on dup), asymmetric with `RegisterAnalyzer` which returns an error.** `cmd/main.go:485`.
Safe today only because the enclosing `RunnableFunc` builds a fresh registry each invocation; a
runnable re-entry (leader re-acquire) or a future shared registry → hard crash. *Fix:* make
query registration return an error like `RegisterAnalyzer`; reconcile the two failure modes.

**D-B2 — `throughputAnalyzerEnabled(nil)` panics (nil-cfg deref).** `cmd/main.go:106-115`. Not
reachable today (cfg validated non-nil earlier) but the helper is a pure, testable predicate
with no guard. *Fix:* `if cfg == nil { return false }`.

### DESIGN

**D-D1 — "Off by default" is enforced by the default YAML omitting the throughput entry, not by
the gate.** `cmd/main.go:109` (`Enabled==nil → true`) +
`config/base/manager/saturation-scaling-configmap.yaml:19-21` (only `saturation`). Add
`{name: throughput}` to any base config without an explicit `enabled:false` and TA silently
turns on — two independent mechanisms must agree for the safety property. *Fix:* make the gate
require explicit `enabled:true` (true opt-in), **or** add a test asserting the default config
yields `throughputAnalyzerEnabled==false`, and say so in the doc comment.

**D-D2 — The gate ORs across *all* models/namespaces → enabling TA for one model registers the
(engine-global) analyzer for every model.** `cmd/main.go:107` over a per-model map. There is no
per-model scoping anywhere today (the per-cycle consumption gate is not landed). *Fix:* document
the global semantics explicitly; per-model en/disable is future work.

**D-D3 — Sticky registration with zero operator feedback: a runtime configmap edit to
enable/disable TA is silently ignored, and there is no log on the disabled path.** `cmd/main.go:
484-491` + `engine.go:277`. "Config changed but silently did nothing" is a worst-class operator
trap. *Fix:* (a) log in **both** branches at startup ("TA not registered; runtime edits require
restart"); (b) ideally have the configmap reconciler emit a K8s Event when live config drifts
from the frozen registration (the `K8SEventUnattributedReadyPods` precedent exists).

**D-D4 — No "disabled" startup log** (only the enabled path logs). `cmd/main.go:489`. Folds into
D-D3. *Fix:* add the `else` branch log.

### SMELL

**D-S1 — Throughput *queries* are registered in `main.go` (outside the engine) while all sibling
queries are registered inside `NewEngine` — split ownership writing to the same registry, the
asymmetry that makes D-B1's double-register reachable.** *Fix:* move throughput query
registration into the engine alongside the others, or comment why it's external.

**D-S2 — `RolePrefill` constant added but adoption is half-done: role `switch`es in
`saturation_v2/analyzer.go:625-633` and `engine.go:974-983` still use raw `"prefill"`/`"decode"`
literals, and there is no `RoleDecode` constant at all** (only `RoleBoth`, `RolePrefill`).
`engine.go:974` even mixes `interfaces.RoleBoth` (constant) with `"decode"` (literal) in one
switch. Magic strings that must match an exported constant are a drift hazard. *Fix:* add
`RoleDecode`, replace the literals.

**D-S3 — Both role `switch`es fold `"both"` and *unknown* into one `default`** (`saturation_v2/
analyzer.go:625`, `engine.go:974`) — a garbage role label is silently coerced to "both". *Fix:*
explicit `case interfaces.RoleBoth` + a `default` that logs the unexpected value.

**D-S4 — Gate name match is case-sensitive exact (`aw.Name == "throughput"`) with no
normalization** (`cmd/main.go:109`) — `Throughput` or whitespace silently disables TA. Compounds
D-D3/D-D4. *Fix:* rely on (and verify) config-load validation that rejects unknown analyzer
names, so a typo fails loudly.

### NIT
D-N1 doc comment references the internal "effectiveEnabled opt-in fix" by name (`cmd/main.go:
103-105`) — describe the mechanism in prose, not the work-item shorthand. · D-N2 the
`RegisterAnalyzer` error returns bare without the `setupLog.Error(...)` framing every other
failure in the file uses (`:486-488`). · D-N3 query registration silently skips at DEBUG if the
prometheus source is absent, yet the analyzer still registers and runs with no data
(`registration/throughput_analyzer.go:69-75`).

---

## E. Tests — unit (`analyzer_test.go`, `replica_metrics_test.go`, `itl_model_test.go`,
`sanity_test.go`) + e2e (`throughput_analyzer_test.go`)

*(From the test-quality review agent; verified against the production code.)*

### BUGs — tests that give false confidence

**E-B1 — The headline scale-up/scale-down tests are tautological.** `analyzer_test.go:302-336,
408-427, 591-619, 682-712, 765-789, 932-946, 978-1029, 1494-1509`. The pattern
`Expect(TotalDemand).To(BeNumerically(">", TotalAnticipatedSupply))` +
`Expect(RequiredCapacity).To(Equal(0.0))` asserts (a) a comparison between two numbers the
fixture itself constructed to compare that way, and (b) a field that is *unconditionally* zero
(A-D1). These — the suite's most important tests — would stay green if tiering, GPS gating, role
aggregation, or queue logic were completely broken. *Fix:* assert on values the analyzer
computed and the test did not (lock `perReplicaSupply`/`TotalSupply` against an independently
derived μ_sat with tight tolerance), and/or drive RC/SC through the engine post-step in an
integration test.

**E-B2 — `muSat` is anchored to a comment-derived magic constant with a ±10% tolerance**
(`analyzer_test.go:257-273,363,382`) — a ~10% error in `computeVariantSupply` passes. *Fix:*
recompute expected μ_sat in-test from the same constants (the `muDecG()`/`muDecW()` helpers are
the good pattern) and tighten to 1e-3.

**E-B3 — Collector "no metrics / error" tests can only ever assert the *absence* of an event;
the positive edge (available → error fires exactly one event) is untested.**
`replica_metrics_test.go:155-355`. Three near-identical tests all prove the same negative; a bug
that *never* emits would pass all three. (`_UnattributedReadyPodsEvent` at `:672` does it right —
model the others on it.) *Fix:* seed `podData`, flip to error on cycle 2, assert one event.

### Coverage GAPS (production branches with NO test)

- **E-G1 — `throughputAnalyzerEnabled` gate: zero tests.** No `cmd/*_test.go` exists. This is
  the round-2 fix for the `saturation_v2_test.go:280` CI failure, and its three branches
  (absent→false, nil→true, false→false) + multi-entry OR are untested. **Highest-value gap.**
- **E-G2 — ITL-model `NaN/Inf B` guard and `A·k_sat+B<=0` guard untested** (`itl_model.go:56-63`).
  Neither rejection path is exercised.
- **E-G3 — vLLM fallback demand path untested** (`computeDemand` vLLM branch) — every demand test
  uses EPP ArrivalRate or local k\*.
- **E-G4 — Collector skip-unknown only tested for one query; the `instanceKey==""` skip and the
  NaN/Inf/range guards on the 3 throughput fields are untested** (`replica_metrics.go:698-745`).
  (Confirms the guards exist — relevant to A-B1's "mostly defended today.")
- **E-G5 — `checkVariantGPSMismatch` never unit-tested directly** — threshold boundary, low-k
  skip, zero-GPS skip, near-k_sat diagnostic split all only reached transitively; the 5 "GPS
  scenarios" `It`s (`:1381-1510`) are pure pass-through (assert only `SC==0`).
- **E-G6 — `aggregateRoleCapacities` "both"+"decode" mix untested** (`analyzer.go:803`
  short-circuit boundary).
- **E-G7 — `observationWindow.Add` drop-bool not asserted through `Observe`** (the F4 path).

### DESIGN / SMELL (tests)

**E-D1 — The `== 0.0` assertion convention systematically hollows the suite** (~20 always-true
assertions, comment repeated ~15×). Reads like coverage, guards nothing; won't be updated when
RC/SC become real. *Fix:* delete them or convert to integration. · **E-D2 — The GPS-fixture
block (`:1381-1510`, 5 `It`s) tests nothing currently** — convert to `PIt` (pending) or extract
the fixture and delete the no-op `It`s; their names ("GPS deviates >15% …") actively mislead. ·
**E-D3 — Heavy copy-paste**: the `il/ol/kvMax/A/B` constants + 10-element `kValues` slice are
re-declared in ~9 Describe blocks (risk: B silently differing between blocks). Hoist to package
scope. · **E-S1 — `injectWindowObs` asserts readiness in some callers, not others**; a
refactor that broke window-readiness would silently fall to tier-2 and still pass via E-B1.
· **E-S2 — `VariantCapacities[0]` positional index over a map-built slice** (`:741`) — latent
flake; find by name. · **E-S3 — `Analyze` result discarded with `//nolint:errcheck`** in
state-only tests (`:376,1243`). · **E-S4 — concurrency test asserts only `ok==true`** (`:507`) —
a `-race` smoke test, not correctness; name overstates it.

### e2e specifics

- **E-e1 (BUG-ish) — `Skip()` on controller-restart failure hides the regression the suite
  exists to catch.** `throughput_analyzer_test.go:245-248,356-359,468-471`. `restartWVAController`
  returns an error for *both* "infra can't run this" *and* "rollout timed out" — and a controller
  that crash-loops because TA registration broke produces a timeout → `Skip`, green-with-skips.
  *Fix:* distinguish patch/RBAC failure (legit Skip) from rollout timeout / unhealthy pods (must
  Fail).
- **E-e2 (DESIGN) — The test never verifies TA *authored* the scale decision, only that a number
  moved.** With both analyzers enabled, saturation alone can drive the scale-up (the
  CURRENT.md-tracked "e2e wiring test is a no-op under the gate" issue). Only the TA-only suite
  isolates TA, and even it asserts only `NumReplicas > 0`. *Fix:* assert a scale-up *delta* in the
  TA-only suite; treat the both-enabled suite as a wiring smoke test (documented).
- **E-e3 (SMELL) — AfterAll restart is `Expect(...).Succeed()` in the smoke suite but best-effort
  `_ =` in the two `full` suites** (`:279` vs `:400,512`), contradicting the suite's own
  "registration is sticky → restore-then-restart is mandatory" comment. The `full` suites run load
  and are *more* likely to leave a slow/unhealthy controller → nondeterministic contamination of
  the TA-off `saturation_v2` scale-down test. *Fix:* hard-assert all three AfterAll restarts; add a
  defensive BeforeAll restart-to-saturation-only on the `saturation_v2` suite. **(Already noted as
  a known follow-up in CURRENT.md — this review confirms it and raises priority.)**
- **E-e4 (SMELL) — `restartWVAController` readiness check can pass on the *old* ReplicaSet** — no
  `ObservedGeneration >= Generation` gate, so the first poll can see the pre-restart "complete"
  status and return before the new config is read (`:127-137`). *Fix:* gate on ObservedGeneration,
  mirroring `kubectl rollout status`.
- **E-e5 (NIT) — pinned external image + wall of undocumented load-profile magic numbers**
  (`:175,181-185`); comment why workers=2/max_tokens=400 reliably saturates the simulator.

### What's genuinely good (the bar)
`itl_model_test.go`, `sanity_test.go`, the GPS *window-reset* state-machine tests (`:1578-1649`),
`lastFittedB` carry-over tests (`:1262-1378`), `averageShapeMetrics`/`estimateQueueDemand` guard
tests, and the `_UnattributedReadyPodsEvent`/`_ThroughputKeyMerge` collector tests assert
computed outputs with tight tolerances — that is the right pattern. The leaf helpers are solid;
the *system-behavior* tests are where the false confidence lives.

---

## Consolidated fix grouping (for the "bigger fix later")

Ordered by leverage. Each bundle is independently shippable.

1. **Canonical instance key (collector).** C-B1 + C-B2 + C-B3 + C-D3 + C-N5 + C-S1 are one
   defect: define the per-pod key once, route all 12 loops through it, turn silent skips into
   logged anomalies. Add E-G4 tests. *Biggest correctness win.*
2. **Kill the split-contract test rot.** A-D1 + E-B1 + E-B2 + E-D1 + E-D2: add one engine-level
   integration test that drives the post-step and asserts a real scale decision; delete the
   `== 0.0` assertions and the no-op GPS `It`s; recompute μ_sat expectations with tight tolerance.
3. **Gate hardening + observability.** D-B2 + D-D1 + D-D3 + D-D4 + D-S4 + E-G1: nil-guard, explicit
   opt-in (or a default-config test), log both branches, emit a drift Event, and unit-test the
   predicate. This is the area that caused the most reviewer churn.
4. **nil-vs-zero + freshness end-to-end.** C-D1 + C-S3 + C-S5 + B-N3 + A-B1: give the 3 throughput
   fields presence/timestamp semantics, populate `FreshnessStatus`, exclude absent k\* from
   supply/demand/calibration, and either wire or delete the dead stale branch. (Aligns with #1264.)
5. **Delete placeholder/dead code.** A-D2 + A-S1 + A-S2 + A-S3 + B-S2 + C-S2 + D-S1: drop
   `anyEPP`/`anyGPSMismatch`/`isEPP`/`TotalCapacity`/the reversed-issue comments; git remembers
   them for #1261. Reduces the "looks load-bearing but isn't" surface that misled reviewers.
6. **Math guards.** A-B2/B-S1 (shared `validITL`), A-B3 (NaN-k in `Add`), A-D3/A-D4 (lock contract
   + injected clock), E-G2 tests. Low risk, closes the defense-in-depth gaps.
7. **e2e robustness.** E-e1 + E-e3 + E-e4 + E-e2: Skip-vs-Fail split, hard AfterAll restarts +
   defensive BeforeAll, ObservedGeneration gate, TA-attribution delta assertion.

**None of these block the current CI green / merge** — they are quality debt. If #1250 must land
under the code freeze, land it as-is and schedule bundles 1–3 as the consolidated follow-up
(bundle 1 is the only one with a latent *correctness* bug, and it is config-masked today).

---

## Notes for plan reconciliation (Type 3 cleanup)
- The code confirms several items the plan tracked as done are **correct but inert** (F2/
  `TotalCapacity` — A-S1) or **dead-by-design** (anyEPP/anyGPSMismatch — A-D2); the plan should
  stop describing them as behavior and mark them placeholder/cosmetic.
- The "e2e wiring no-op under the gate" and "AfterAll best-effort restart" items are already in
  CURRENT.md — this review confirms both (E-e2, E-e3) and they should be folded into the
  consolidated-fix backlog, not left as loose next-steps.
- Issue #1261 (per-analyzer status return) is the real home for A-D2's gate and A-B1's
  demand-gating-on-sanity; #1264 is the home for C-D1's nil-vs-zero. The consolidated fix should
  reference those, not re-plan them.
