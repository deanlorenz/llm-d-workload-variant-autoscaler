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

### Item 1 — RC normalization in `totalWeighted` (`engine_v2.go:140`)

**The bug is real.** The combine loop normalizes `excessFracs` and `slackFracs` by the
analyzer's own `TotalCapacity` (`t`), so those fractions are dimensionless. But
`totalWeighted` (line 140) accumulates raw `RC * score` without normalization:

```go
totalWeighted += er.result.RequiredCapacity * er.score   // ❌ raw RC, not normalized
```

`totalWeighted` flows directly into `combined.Score = priority * totalWeighted`, which
the greedy optimizer uses as the demand budget for fair-share replica allocation
([`greedy_score_optimizer.go:112`](../engine-multi-analyzer/internal/engines/pipeline/greedy_score_optimizer.go)).
If saturation (token-scale RC, e.g., 50 000 tokens) and TA (different unit scale) both
contribute, the weighted sum is dimensionally inconsistent and one analyzer dominates.

**Fix:** normalize inside the `t > 0` branch and scale back at the output:

```go
// line 140 — inside t > 0 branch:
totalWeighted += (er.result.RequiredCapacity / t) * er.score

// line 187 — output:
combined.Score = priority * totalWeighted * satTotal
```

For saturation-only (today), `t == satTotal`, so `(satRC/satTotal)*satScore*satTotal == satRC*satScore` — no behaviour change. For mixed analyzers, each RC is converted to a utilization fraction, weighted, then denormalized back to saturation's capacity scale. The optimizer always sees values in saturation-token units, which it already understands.

Cold-start case (`t == 0, RC > 0`): skip from `totalWeighted` accumulation (the cold-start
branch overrides `combined.Score` to 0 anyway via `combined.SpareCapacity = 0` — fine).

---

### Item 2 — `AnalyzerScoreConfig` thresholds: what do they mean and for whom?

**What the thresholds do in saturation:**
`ScaleUpThreshold` and `ScaleDownBoundary` are inputs to the capacity formula in
`saturation_v2/analyzer.go`:

```
RC = totalDemand / ScaleUpThreshold − totalAnticipatedSupply
SC = totalSupply − totalDemand / ScaleDownBoundary
```

This is saturation-specific math — they set headroom margins so the analyzer scales up
before hitting 100% utilisation. They are **not** a bound on the combined WVA score;
they affect how much RC/SC the saturation analyzer emits before the combine step.

**Are they meaningful for other analyzers?**
No. The ThroughputAnalyzer's scaling signal comes from ITL model degradation
(`itl_model.go`) — a completely different formula. There is no `demand/threshold` step.
Passing `ScaleUpThreshold` to TA via `input.Config` would be harmless (TA ignores it)
but also meaningless. Future analyzers (SLO, queueing model) also have their own scaling
math.

**Current engine behaviour:** only the saturation entry's per-analyzer threshold overrides
are applied (lines 206–214 of `runAnalyzersAndScore`); all other entries' overrides are
silently dropped. The struct, `Validate()`, and doc all imply they apply to every analyzer.

**Options — choose one:**

**Option A — Remove from AnalyzerScoreConfig (simplest).**
Drop `ScaleUpThreshold`/`ScaleDownBoundary` from `AnalyzerScoreConfig`. Saturation's
thresholds stay at the global `SaturationScalingConfig` level. Users who want different
per-model saturation thresholds configure them at the model config level, not inside the
`analyzers` list. Clean, no silent-drop, no broken promises. Lose the ability to override
thresholds inline in the analyzer entry — but that's fine if the only user is saturation.

**Option B — Restrict to saturation in doc + Validate (minimal).**
Keep the fields but add a doc comment: "only applies to the `saturation` analyzer; ignored
for other analyzers." Update `Validate()` to skip the pair-relationship check for
non-saturation entries (currently it validates all entries). Honest API, no code
restructuring.

**Option C — Thread to all analyzers (future-proof).**
For each enabled non-saturation analyzer, apply its entry's threshold overrides to a
local copy of `config` before building `AnalyzerInput`. Analyers that don't use them
ignore them; ones that do (e.g., a future utilization-based analyzer) get per-entry
control. Adds a config-copy loop but is mechanically consistent.

**Recommendation:** Option A is the right call for now. These thresholds are tightly
coupled to the saturation formula. No other current or near-term analyzer uses them.
Option C adds complexity for a hypothetical future use. Option B is a band-aid. Remove
them from `AnalyzerScoreConfig` and update the docs. The engine code at lines 206–214
that patches the global config from the saturation entry's overrides can be removed.

---

### Item 3 — `RegisterAnalyzer` concurrent map access (`engine.go:231`)

**The "before StartOptimizeLoop" comment:** `StartOptimizeLoop` calls
`e.executor.Start(ctx)`, which launches the goroutine that runs `optimize()` →
`runAnalyzersAndScore()`. That function iterates `e.analyzers`. If `RegisterAnalyzer`
is ever called after `Start`, the unsynchronized map write races with the concurrent
read — silently corrupting the map rather than panicking.

In practice `main.go` is sequential (New → Register → Start), so there is no real race
today. But the Go race detector will flag it, and it is one wrong call site away from
production corruption.

**Dean's observation — "initiate the operation while registrating":**
If we treat registration as a one-time initialization event, we can call any per-analyzer
setup (register metric queries, allocate state, etc.) inside `RegisterAnalyzer` rather
than lazily on first `Analyze()` call. Doing this requires that registration happens in
the right context (e.g., after metrics sources are wired up) — which is already satisfied
by the `main.go` sequence.

**Options:**

**Option A — `sync.RWMutex` (defensive, minimal change).**
Add `analyzersMu sync.RWMutex` to the Engine struct. `RegisterAnalyzer` takes a write
lock; `runAnalyzersAndScore` takes a read lock while iterating. Allows dynamic
registration at runtime (which is not intended but now safe). Standard idiom.

**Option B — Constructor injection (cleanest design).**
Add an `analyzers []NamedAnalyzer` parameter to `NewEngine`. Map is populated at
construction time before any goroutine exists; `RegisterAnalyzer` is removed. Zero race
risk. Makes the API contract explicit: "you configure analyzers at construction time."
Downside: breaks current call site in `main.go` — minor refactor.

**Option C — Snapshot on Start (enforce the contract).**
`StartOptimizeLoop` copies `analyzers` to an immutable `[]analyzerEntry` slice before
launching the goroutine. `RegisterAnalyzer` checks an `started` bool and panics on
late calls: `"RegisterAnalyzer called after StartOptimizeLoop"`. The contract is
enforced rather than documented. `RegisterAnalyzer` continues to exist for callers who
want to build the map incrementally during setup.

**Recommendation:** Option C hits the right balance — keeps the registration API, makes
the goroutine loop read from a frozen copy (no lock needed at read time), and panics
loudly if someone registers late. Combined with Dean's observation: the frozen snapshot
step in `StartOptimizeLoop` is also the natural place to call any `Init(ctx)` method on
registered analyzers before the loop runs, cleanly separating "setup" from "steady-state".

If a full refactor is in scope, Option B (constructor) is the gold standard. For a
minimal fix that satisfies the reviewer, Option A (RWMutex) is fine.
