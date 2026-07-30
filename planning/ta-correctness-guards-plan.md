# TA Correctness Guards — Type 3 Task Plan (PR F)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-correctness-guards` cut from the current tip of `main`
(the moving ref — `git worktree add … main`, never a pinned SHA). Anchors verified against `main`
`f5261c8e` on 2026-07-30 (the merge of D `#1481`). Any SHA here is informational-as-of-authoring only.
**Size:** 4 small guard/wiring commits + tests + dev-guide · **Reviewer session:** yes (correctness-adjacent)
**Depends on:** nothing at build time. **Overlaps PR C `#1480`** (still OPEN) in `analyzer.go` — see
§ C-overlap. Independent of PR E `#1497`/`ta-gate-observability`.

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L28:56
- [Scope, non-goals, honest severity {#scope}](#scope-non-goals-honest-severity-scope) L57:85
- [C-overlap and commit ordering {#c-overlap}](#c-overlap-and-commit-ordering-c-overlap) L86:114
- [Commit 1 — I-3: reject NaN k in ObservationWindow.Add {#commit-1}](#commit-1--i-3-reject-nan-k-in-observationwindowadd-commit-1) L115:145
- [Commit 2 — I-6: wire real per-replica freshness in the collector {#commit-2}](#commit-2--i-6-wire-real-per-replica-freshness-in-the-collector-commit-2) L146:189
- [Commit 3 — I-2: shared validITLModel across both fit tiers {#commit-3}](#commit-3--i-2-shared-validitlmodel-across-both-fit-tiers-commit-3) L190:226
- [Commit 4 — I-4: NaN/out-of-range guard in computeLocalDemand {#commit-4}](#commit-4--i-4-nanout-of-range-guard-in-computelocaldemand-commit-4) L227:278
- [Semantic-pivot grep step {#grep}](#semantic-pivot-grep-step-grep) L279:299
- [Tests {#tests}](#tests-tests) L300:327
- [Developer guide {#devguide}](#developer-guide-devguide) L328:350
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L351:367

## Overview {#overview}

This PR lands four small, independent correctness/robustness guards in the ThroughputAnalyzer and
its collector, drawn from the TA forward plan (internal issues I-2, I-3, I-4, I-6). None changes a
public contract; each is a localized guard or a wiring fix. They are grouped because they are all
"defensive hardening of numeric/freshness paths that a single bad metric could poison."

The items, by honest current severity (see § Scope for the full derivation — do **not** overclaim
these in commit messages or the dev-guide):

- **I-4** — `computeLocalDemand` does not reject a NaN `KvUsageInstant` (or a NaN `ITLAt`), so one
  bad replica metric poisons the summed local-demand term. **Live on this PR's base (`main`)**,
  where `computeLocalDemand` is the fallback demand contributor; narrows to introspection-only once
  PR C merges. Real guard either way.
- **I-6** — the collector computes real per-timestamp freshness (for the Prometheus gauge) but
  **hardcodes** the per-replica `Metadata.FreshnessStatus` to `"fresh"`, so the throughput sanity
  check's stale-metrics detection can never fire. **Observability/prep value only today** — the
  sanity report does not yet gate scaling (`TODO(#1261)`). Makes detection truthful; does not
  change scaling.
- **I-2** — the two ITL-fit tiers validate their output differently: `FitITLModel` (Tier 1) has
  NaN/Inf-A, epsilon-slope, NaN/Inf-B, and positivity guards; `resolveITLModel`'s Tier-2 path only
  checks `A > 0`. Input pre-filtering makes a bad Tier-2 model unlikely today — this is
  consistency/defense-in-depth, not a live bug.
- **I-3** — `ObservationWindow.Add` already rejects NaN/≤0 `itl` but a **NaN `k`** slips the
  range check (`k < minK || k > maxK` are both false for NaN). Narrow defense-in-depth; `Add` is
  reached behind `report.OK()`.

[↑ TOC](#toc)

## Scope, non-goals, honest severity {#scope}

**In scope:** the four guards above, their unit tests, and dev-guide updates that describe the
*current* behavior (Type 4 rule — no forward-looking "pending PR" text).

**Non-goals (do NOT do in this PR):**
- **Do not** wire the throughput sanity report into scale-down/scale-up suppression. That is the
  `#1261` per-analyzer status-return work. I-6 makes the *stale* signal real; consuming it to gate
  a decision stays out of scope. State this in the dev-guide.
- **Do not** change `FreshnessThresholds`, `DetermineStatus`, or the Prometheus freshness gauge
  (`wva_metrics_freshness_status`) — I-6 only populates the per-replica metadata that already
  exists in the struct.
- **Do not** touch the saturation analyzer. `domain.ReplicaMetricsMetadata.FreshnessStatus` is
  defined shared, but the **only** gating consumer of `== "stale"` is the throughput sanity check
  (`internal/engines/analyzers/throughput/sanity.go`). Confirm this with the § grep before relying
  on it; if a saturation consumer has appeared, hand it back via a planner handoff (widens blast
  radius beyond this PR's "throughput" framing).
- **Do not** remove or restructure `computeLocalDemand`, the two-tier ITL strategy, or the
  observation window. Guards only.

**Honest-severity discipline (per doc-accuracy convention):** the forward plan's one-line labels
overstate two of these. When you write commit messages and dev-guide prose, describe what the code
does *today*: I-6 is "detection becomes truthful, gating still deferred," and I-2 is "harmonize the
two validators so Tier-2 can't drift," **not** "fixes a live scaling bug." I-4 is a live guard on
this branch's base; if C has merged by the time you reach Commit 4, reframe it as introspection-value
+ deferred-fallback protection (see § C-overlap). Only I-3 and I-4 (pre-C) touch a live numeric total.

[↑ TOC](#toc)

## C-overlap and commit ordering {#c-overlap}

PR C (`ta-model-level-demand`, `#1480`, tip `b2acffd6`, still OPEN) rewrites `analyzer.go`
(`Analyze`, `computeDemand`, `aggregateRoleCapacities`, `distributeDemandByRole`) but changes
**neither** `computeLocalDemand`'s body **nor** `resolveITLModel`'s body (verified 2026-07-30 —
C only adds comments adjacent to `computeLocalDemand`). C also adds a helper to
`collector/replica_metrics.go` inside `CollectSchedulerQueueMetrics` (~L1091), **not** near the
freshness set-site (~L1004). So the real conflict surface between F and C is small and confined to
`analyzer.go`.

**Base decision:** cut F from `main`, **not** stacked on C. Rationale: (a) open PRs don't chase a
live PR branch — if C force-pushes during review, a stacked F would have to re-rebase repeatedly;
(b) three of the four items (I-3, I-6, and the `itl_model.go` half of I-2) are in files C never
touches. When C merges to `main`, F does one ordinary rebase onto `main`.

**Commit ordering** puts the two `analyzer.go`-touching commits **last**, so if C merges mid-work
the coder rebases onto `main` before doing them:

1. **Commit 1 — I-3** — `observation_window.go` (conflict-free with C).
2. **Commit 2 — I-6** — `collector/replica_metrics.go` freshness set-site (conflict-free with C).
3. **Commit 3 — I-2** — `itl_model.go` (conflict-free) + one small `resolveITLModel` edit in
   `analyzer.go`.
4. **Commit 4 — I-4** — `computeLocalDemand` in `analyzer.go`.

If C merges before you start Commit 3 or 4: rebase onto `main` first, re-verify the two `analyzer.go`
anchors, and reframe I-4's severity per § Scope.

[↑ TOC](#toc)

## Commit 1 — I-3: reject NaN k in ObservationWindow.Add {#commit-1}

**File:** `internal/engines/analyzers/throughput/observation_window.go`, `func (w *ObservationWindow) Add`
(anchor L41). Current body range-checks `k` and separately guards `itl`:

```go
if k < w.minK || k > w.maxK {
    return true // dropped: out of range
}
if itl <= 0 || math.IsNaN(itl) {
    return true // dropped: invalid
}
```

**Gap:** a NaN `k` passes the range check — `NaN < minK` and `NaN > maxK` are both false — so a NaN
`k` is appended and later poisons `KSpread()` / the OLS sums.

**Fix:** reject NaN `k` in the range guard. Mirror the existing `itl` guard's style:

```go
if math.IsNaN(k) || k < w.minK || k > w.maxK {
    return true // dropped: NaN or out of range
}
```

`math` is already imported. Keep the return contract (`true` = dropped) unchanged.

**Deletion classification:** none (pure addition).

[↑ TOC](#toc)

## Commit 2 — I-6: wire real per-replica freshness in the collector {#commit-2}

**File:** `internal/collector/replica_metrics.go`. The per-replica metadata is hardcoded at the
metric-assembly site (anchor ~L1002-1006):

```go
Metadata: &domain.ReplicaMetricsMetadata{
    CollectedAt:     collectedAt,
    Age:             0, // Fresh
    FreshnessStatus: "fresh",
},
```

The collector already has the machinery to compute real freshness: `trackMetricFreshness`
(anchor ~L428) and `config.FreshnessThresholds.DetermineStatus(age)` /
`config.DefaultFreshnessThresholds()` (`internal/config/prometheus.go:46,56`) which return
`"fresh"`, `"stale"`, or `"unavailable"`/`"missing"`. Today `trackMetricFreshness` only feeds the
aggregate Prometheus gauge (`SetMetricsFreshnessStatus`, ~L1012-1014); the per-replica metadata is
thrown away.

**Fix:** derive the per-replica `Age` and `FreshnessStatus` from the same timestamps
`trackMetricFreshness` uses (`data.*Timestamp` on `podMetricData`) and set them on the metadata,
instead of the hardcoded literals. Design for the coder to settle from the code:

1. Determine, per pod's `podMetricData`, an overall freshness: the **oldest** (worst) status across
   the tracked timestamps is the safe rollup (if any driving metric is stale, the replica is stale).
   Reuse `DetermineStatus` — do **not** reimplement the thresholds. `Age` = `collectedAt.Sub(oldest
   non-zero timestamp)`; a zero timestamp → treat as `"missing"`/`"unavailable"` per existing
   `trackTimestamp` semantics.
2. Set `Age` and `FreshnessStatus` from that rollup at the assembly site.
3. Factor the per-timestamp status logic so `trackMetricFreshness` (gauge) and the per-replica
   rollup share one helper rather than duplicating the threshold calls — check whether a small
   `worstStatus(data, collectedAt, thresholds)` helper cleanly serves both. If the two genuinely
   need different granularity, keep them separate but do not fork the threshold source.

**Blast radius (must confirm with § grep):** the only gating consumer of `FreshnessStatus == "stale"`
is `throughput/sanity.go:53`. So this makes the throughput stale-metrics **sanity issue** real —
but that issue is **not yet consumed to gate scaling** (`TODO(#1261)` at `analyzer.go:249`). Do not
claim this changes scaling behavior.

**Deletion classification:** none (replaces two hardcoded literals with computed values).

[↑ TOC](#toc)

## Commit 3 — I-2: shared validITLModel across both fit tiers {#commit-3}

**Files:** `internal/engines/analyzers/throughput/itl_model.go` (`FitITLModel`, anchor L36) and
`internal/engines/analyzers/throughput/analyzer.go` (`resolveITLModel` Tier-2, anchor L464).

`FitITLModel` currently validates its `(A, B)` inline with four guards: NaN/Inf-A;
`A <= itlSlopeEpsilon` (flat/inverted); NaN/Inf-B; `A*DefaultKSat + B <= 0` (positivity).
`resolveITLModel`'s Tier-2 constructs `ITLModel{A: A, B: baselineB}` after only `A > 0`.

**Fix:** extract the shared predicate and call it from both:

```go
// validITLModel reports whether an (A, B) pair is a usable ITL model:
// finite, meaningfully-positive slope, finite intercept, and positive ITL at
// saturation. Shared by the Tier-1 OLS fit and the Tier-2 constrained fit so
// the two validation paths cannot drift.
func validITLModel(a, b float64) bool { … }
```

Body = the exact four checks currently in `FitITLModel` (NaN/Inf-A; `a <= itlSlopeEpsilon`;
NaN/Inf-B; `a*DefaultKSat + b <= 0`). Then:

- In `FitITLModel`: replace the four inline guards with `if !validITLModel(A, B) { return ITLModel{}, false }`.
  Keep the explanatory comments (move the load-bearing ones — the epsilon-slope and positivity
  rationale — onto `validITLModel`; do not lose the arm64/amd64 noise note).
- In `resolveITLModel` Tier-2: after computing `A`, replace `if A > 0 {` with
  `if validITLModel(A, baselineB) {` (baselineB is `DefaultBaselineITLSec` or `state.lastFittedB`).

**Behavior note (state honestly):** because Tier-2's inputs are pre-filtered (`AvgITL > 0`,
`KvUsageInstant > 0`) and `baselineB > 0`, this rarely changes Tier-2's accept/reject outcome today
— its value is preventing future drift between the two validators. Frame the commit that way.

**Deletion classification:** none (refactor — the inline `FitITLModel` guards move into the shared
helper with identical semantics; classify as such in the handoff).

[↑ TOC](#toc)

## Commit 4 — I-4: NaN/out-of-range guard in computeLocalDemand {#commit-4}

**File:** `internal/engines/analyzers/throughput/analyzer.go`, `func computeLocalDemand` (anchor
L567). Current per-replica loop:

```go
for _, m := range metrics {
    if m.KvUsageInstant <= 0 || m.TotalKvCapacityTokens <= 0 {
        continue
    }
    itlAtK := model.ITLAt(m.KvUsageInstant)
    if itlAtK <= 0 {
        continue
    }
    total += m.KvUsageInstant * float64(m.TotalKvCapacityTokens) / shape.KVreq / itlAtK
}
```

**Gap:** a NaN `KvUsageInstant` passes `<= 0` (NaN comparisons are false), and a NaN `itlAtK`
passes `itlAtK <= 0`, so either poisons `total` into NaN. There is also no upper bound on
`KvUsageInstant` (k*); a spurious `> 1` value inflates the term.

**Fix:** add NaN rejection to both existing skip guards; decide k*>1 handling explicitly:

```go
if math.IsNaN(m.KvUsageInstant) || m.KvUsageInstant <= 0 || m.TotalKvCapacityTokens <= 0 {
    continue
}
// KvUsageInstant is a KV-utilization fraction; values > 1 indicate a bad/over-committed
// metric. Skip rather than clamp — a single over-range replica shouldn't inflate demand.
if m.KvUsageInstant > 1 {
    continue
}
itlAtK := model.ITLAt(m.KvUsageInstant)
if math.IsNaN(itlAtK) || itlAtK <= 0 {
    continue
}
```

Confirm `math` is imported in `analyzer.go` (it is used elsewhere; verify). For k*>1, **skip** is the
recommended default (documented above); if the coder finds a strong reason to clamp to 1 instead,
that is a judgment call to raise, not to silently choose — note it in the status file.

**Severity framing (per § Scope / § C-overlap):** on this branch's base (`main`, pre-C),
`computeLocalDemand` is a live fallback demand contributor, so this guard protects a real
`TotalDemand`. After C merges it feeds per-variant introspection + the deferred fallback only —
still worth guarding, but reframe the commit message to the state at commit time.

**Deletion classification:** none (pure addition).

[↑ TOC](#toc)

## Semantic-pivot grep step {#grep}

Two behavioral-adjacent changes need a cross-reference scan after implementation:

```bash
# I-6: confirm the ONLY gating consumer of stale freshness is the throughput sanity check.
grep -rn 'FreshnessStatus' internal/ --include=*.go | grep -v '_test.go'
# I-2: confirm both fit tiers now route through the shared validator; no stray inline (A,B) checks.
grep -rn 'itlSlopeEpsilon\|DefaultKSat\|validITLModel\|A <= \|A > 0' internal/engines/analyzers/throughput/ --include=*.go
```

Required action:
- If any consumer other than `throughput/sanity.go` gates on `FreshnessStatus == "stale"`
  (especially in the saturation analyzer), **stop** — I-6's blast radius exceeds this PR's scope;
  write a planner handoff rather than proceeding.
- Confirm no second inline `(A, B)` validity check survives outside `validITLModel` after Commit 3.
- Update the `types.go:109` comment near the throughput `FreshnessStatus` reference if I-6 changes
  how the field is populated.

[↑ TOC](#toc)

## Tests {#tests}

Add per commit; run `make test` after each.

1. **I-3** — `observation_window_test.go`: `Add(math.NaN(), validITL, ts)` returns `true` (dropped)
   and does not append (assert `Len()` unchanged). Keep the existing in-range/out-of-range cases.
2. **I-6** — collector test (`internal/collector/replica_metrics_test.go` or the freshness-focused
   test file): a pod whose driving timestamp is older than the stale threshold yields a metric with
   `Metadata.FreshnessStatus == "stale"` and a non-zero `Age`; a fresh pod yields `"fresh"`. If the
   existing collector tests construct `podMetricData` directly, reuse that fixture idiom.
   Additionally, a throughput sanity test (`sanity_test.go` already has the `"stale"`/`"fresh"`
   cases at L60-70) confirms the gate now fires on a collector-produced stale metric end-to-end if
   feasible without heavy wiring — otherwise the collector-level test suffices.
3. **I-2** — `itl_model_test.go`: keep all existing `FitITLModel` accept/reject cases (they now
   exercise `validITLModel` transitively). Add a direct `validITLModel` table test covering each
   reject branch (NaN A, Inf A, flat A≈0, NaN B, non-positive ITL-at-sat). If practical, a
   `resolveITLModel` Tier-2 test that would previously have accepted a degenerate `A` and now
   rejects it — only if a realistic degenerate input exists (see the honest-severity note; may not).
4. **I-4** — `analyzer_test.go`: `computeLocalDemand` with one replica having
   `KvUsageInstant = math.NaN()` returns a finite total (the NaN replica is skipped, others count);
   a replica with `KvUsageInstant > 1` is skipped; a NaN-producing model (if constructible) is
   skipped via the `itlAtK` guard.

Match existing table/Ginkgo idioms in each file; do not introduce a new assertion helper if one
exists.

[↑ TOC](#toc)

## Developer guide {#devguide}

Edit `docs/developer-guide/throughput-analyzer.md` (Type 4 — current behavior only):

- **§ ITL Model Calibration → Tier 1 / Tier 2** (headings at L393/L398/L405): note that both tiers
  validate their fitted `(A, B)` through the **same** predicate (finite, positive slope, positive
  ITL at saturation), so Tier-2 cannot accept a model Tier-1 would reject. (I-2)
- **§ Demand Estimation → Priority Chain** (L449/L451): note that the local (k*-based) demand term
  skips replicas with missing, NaN, or out-of-range (`> 1`) KV-utilization so a single bad metric
  cannot poison the total. (I-4)
- **§ Metrics → Shared Fields from Collector** (L179) **or** the sanity/staleness prose: note that
  per-replica metric freshness (`Age`, `FreshnessStatus`) is now computed by the collector from the
  metric scrape timestamps (previously always reported fresh), and that the throughput sanity check
  flags stale metrics accordingly. **State the limitation explicitly:** the stale-metrics sanity
  issue is currently detection/observability — it is reported but does not by itself suppress a
  scaling decision. Do **not** reference a future PR for the gating; a neutral "not currently used to
  gate scaling" phrasing is correct and not forward-looking. (I-6)
- I-3 is an internal invariant of the observation window — no dev-guide change unless the guide
  already documents `Add`'s drop conditions (grep `observation window` / `Add`); if it does, add the
  NaN-k case.

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

Run in order (per CONVENTIONS pre-push checklist):
1. `git branch --show-current` — confirm `ta-correctness-guards`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass (new I-2/I-3/I-4/I-6 tests included).
4. `make lint` — clean (required gate; not caught by build/test).
5. DCO — every commit `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
6. `go build ./...` — clean.
7. **§4a scan** (per the 2026-07-29 PR-C incident): grep the diff's added comment/test lines for
   `decision #|review finding|\bF[0-9]\b|plan §|TA-[a-z]+ §|planning/|-plan\.md|-review\.md` — no
   plans-branch identifiers in code comments, `It(...)`/`Describe(...)` strings, or commit messages.

Then write the `review__ta-correctness-guards-ready.md` trigger (per CODER-CONVENTIONS §5.4) before
the push-ready plan handoff. No push without Dean's explicit confirmation.

[↑ TOC](#toc)
