# TA Correctness Guards — Internal Review (PR F)

**Type:** 6 (review) · **Status:** DRAFT · **Branch:** `ta-correctness-guards`, tip `8bdd8b37`
(7 commits) · **Reviewed against:** [`planning/ta-correctness-guards-plan.md`](ta-correctness-guards-plan.md)
· **Reviewer:** internal (this session) · **Date:** 2026-07-30

## Verdict

Code matches the plan closely and honestly; all gates independently re-verified green, including
after the post-rebase re-verification below. **Ready to push**, pending Dean's confirmation. One
moderate simplification finding (non-blocking) remains open; no correctness defects found in the
shipped logic.

## Change highlight

| Commit | What | Type |
|---|---|---|
| `101e64ae` | Reject NaN `k` in `ObservationWindow.Add` (I-3) | logic + test |
| `3b0b5cdf` | Collector derives real per-replica `Age`/`FreshnessStatus` from scrape timestamps instead of hardcoding `"fresh"` (I-6) | logic + test |
| `b9670047` | Extract `validITLModel`; both ITL-fit tiers now share it (I-2) | refactor + test |
| `d2618824` | Reject NaN / `>1` `KvUsageInstant` and NaN `itlAtK` in `computeLocalDemand` (I-4) | logic + test |
| `b326000b` | Dev-guide: Tier 1/2 validator, freshness note, local-demand skip condition | doc |
| `ffcdae2f` | Saturation liveness engine: clamp non-positive `OptimizationInterval()` to 30s default (DR-1); treat zero `AnalyzedAt` on an informative result as `now` (DR-2); extend prune-comment (DR-3, comment-only); adds `config.SetOptimizationIntervalForTest` | logic + test |
| `8bdd8b37` | Dev-guide: liveness interval fallback + zero-`AnalyzedAt` fail-safe | doc |

**Out of scope, as declared by the plan and confirmed unchanged:** no wiring of the throughput
sanity report into scale-down/up suppression; no change to `FreshnessThresholds`,
`DetermineStatus`, or the Prometheus freshness gauge; no gating consumer added for
`FreshnessStatus`; no restructuring of `computeLocalDemand`, the two-tier ITL strategy, or the
observation window beyond the stated guards.

## Critical section

The behavior that actually changes production output is small and isolated:

- `internal/engines/analyzers/throughput/analyzer.go:566-583` (`computeLocalDemand`'s guard
  block) — this is the only change with a **live** effect on `main` today (pre–PR-C fallback
  demand path).
- `internal/engines/saturation/engine_v2.go:196-223` (`updateLivenessAndSetLive`'s interval clamp
  + zero-`AnalyzedAt` fail-safe) — currently dormant (no live input triggers either branch, see
  Verification below) but is the safety-floor logic itself, so it is the highest-consequence
  region in the diff if a future analyzer ever hits either edge.

Everything else (I-3, I-2, I-6, DR-3) is defense-in-depth, consistency, or observability with no
behavioral effect on any input reachable today — matches the plan's own honest-severity framing,
and the commit messages do not overclaim.

## Independent verification (re-run this session, not just trusting the handoff)

- `gofmt -l ./internal ./cmd` — clean
- `go build ./...` — clean
- `make test` — full suite PASS
- `make lint` — 0 issues
- DCO — 7/7 commits signed
- §4a scan (diff content + all 7 commit messages, widened pattern including `\bDR-[0-9]\b`,
  `\bI-[0-9]\b`, `\bA[0-9]\b`, `\bB[0-9]\b`, `\bT[0-9]\b`) — clean, confirms the coder's two
  self-corrections landed cleanly
- Semantic-pivot greps (plan § grep step), re-run independently:
  - `FreshnessStatus` — only gating consumer remains `throughput/sanity.go:53`; no saturation
    consumer exists
  - `itlSlopeEpsilon|DefaultKSat|validITLModel|A <= |A > 0` — no stray inline `(A,B)` check
    survives outside `validITLModel`
  - `AnalyzedAt` in `internal/engines/saturation/` — comments read correctly post-change
  - Additionally verified the DR-2 commit's factual claim directly: grepped
    `AnalyzedAt:` set-sites in all three registered analyzers
    (`throughput/analyzer.go:379`, `saturation_v2/analyzer.go:130`,
    `queueingmodel/analyzer.go:142`) — all three unconditionally set it to `now`/`time.Now()`, so
    "no live analyzer sets a zero `AnalyzedAt` today" is true, not just asserted
- `config.SetOptimizationIntervalForTest` — confirmed it mirrors `SetLimiterForTest` exactly
  (same mutex, same file-local field access pattern) and that `OptimizationInterval()` reads the
  same `c.infrastructure.optimizationInterval` field under the same `RWMutex` — thread-safe,
  correctly scoped, justified (`Load()` always sanitizes to `MinOptimizationInterval`, so this is
  the only way to construct the test case the plan asked for)

## Findings

### 1. (Non-blocking, simplification) The freshness-rollup "cannot drift" claim is only half true

`3b0b5cdf`'s commit message says the shared `classifyTimestamp` helper means "the gauge and the
per-replica metadata cannot drift apart." That's true for the *per-timestamp classification
logic* — both `trackMetricFreshness` (`internal/collector/replica_metrics.go:441-470`) and
`worstFreshnessStatus` (`:477-506`) now call the same `classifyTimestamp`. But the **list of nine
tracked timestamp fields** (`kvTimestamp`, `queueTimestamp`, …, `avgITLTimestamp`) is still
duplicated verbatim between the two functions — I diffed them field-by-field and today they match
exactly, but nothing enforces that. If a future timestamped field is added to `podMetricData` and
only one of the two call sites is updated, the aggregate `wva_metrics_freshness_status` gauge and
the per-replica `Metadata.FreshnessStatus` (which feeds the throughput sanity check) would
silently diverge — the exact failure mode this commit's own message claims to close.

**Suggested follow-up (not blocking this PR):** factor the 9-timestamp list into one `[]time.Time`
slice (or a slice-returning method on `podMetricData`) that both functions iterate, so there is
one enumeration site instead of two.

### 2. (Readiness gap, not a code defect) Branch base is now stale — PR C merged during this session

The plan's § C-overlap section explicitly anticipated this: *"When C merges to `main`, F does one
ordinary rebase onto `main`."* PR C (`#1480`, `ta-model-level-demand`) merged to upstream `main` as
`f9f04d81` at **2026-07-30 12:14:38+03:00**. This branch's tip commit `8bdd8b37` was made at
**12:27:57+03:00** — 13 minutes *after* C's merge — but the branch is still based on
`main@f5261c8e` (the commit immediately before C landed). The coder's status file / handoff state
"PR C still OPEN at every check during this session... no rebase was ever needed," which was
accurate at check time but is now stale.

This matches `session/CURRENT.md`'s own "Next steps" item 2 (F needs its rebase onto
`main@f9f04d81`) — not a surprise to the project, but it means this branch cannot be pushed as-is;
the rebase must happen and all gates (including the §4a scan and DCO) re-verified afterward. Per
the plan's own analysis, the conflict surface should be small (C never touches
`computeLocalDemand`/`resolveITLModel` bodies, and Commit 5 touches only `engine_v2.go`, which C
never touches at all) — but this needs to actually be done and re-verified, not assumed.

## Judgment calls (from the coder's status file) — reviewed, no objection

- I-4 skip-vs-clamp for `KvUsageInstant > 1`: skip, matches plan's recommended default.
- I-6 freshness rollup basis: same 9 unconditionally-issued timestamps as the existing gauge path
  — verified above, correct.
- I-2 omitted the plan's optional Tier-2-rejects-a-previously-accepted-degenerate-A test: the
  coder's algebraic argument (Tier-2 only accepts `A>0` with both possible `B` sources always
  positive, so `A*DefaultKSat+B>0` always holds) checks out from reading `resolveITLModel` and the
  `baselineB` sources — no realistic case exists today, consistent with the plan's own "may not be
  feasible" hedge.
- DR-1 test needed a new test-only setter outside the plan's declared Commit-5 file scope
  (`internal/config/config.go`) — justified and minimal; flagged correctly rather than silently
  added.

## Open question for Dean

The coder's handoff flags that the *second* §4a history rework (fixing "I-2/I-4/I-6" in an earlier
commit message) was applied under an inferred extension of the standing approval for the *first*
rework (fixing "DR-1/DR-2/DR-3"), without asking again. Both reworks are confirmed tree-identical
via diff and the branch is unpushed, so no harm resulted — but the coder itself asked whether that
inference should have been tightened. Worth a yes/no from Dean for the record, independent of this
PR's mergeability.

## Recommendation

1. ~~Rebase `ta-correctness-guards` onto current `main` (`f9f04d81`)~~ — **DONE, independently
   re-verified 2026-07-30 (see § Post-rebase re-verification below).**
2. Optionally fold in the Finding 1 follow-up (shared timestamp-list enumeration) — small, low
   risk, but not required to unblock push; fine to defer to a forward-plan item if Dean prefers not
   to touch this branch further.
3. No other blocking issues. Ready for the push-ready plan-handoff.

## Post-rebase re-verification (2026-07-30)

New tip `abeb048f` (was `8bdd8b37`), rebased onto `upstream/main@f9f04d81` (PR C `#1480`'s merge —
the exact staleness this review flagged). Independently re-verified, not just trusting the
coder's rebase handoff:

- **The predicted silent compile-break was real and was fixed correctly.** Diffed
  `git diff f5261c8e..8bdd8b37 -- internal/engines/saturation/` against
  `git diff f9f04d81..abeb048f -- internal/engines/saturation/`: identical except for line-number
  shifts (from C's unrelated earlier edits to the same file) **and** the 3 new liveness-test calls
  in Commit 5 each gained the trailing `, 0` argument that C's own signature change
  (`runAnalyzersAndScore` gained a trailing `arrivalRate float64` param) requires. Exactly the fix
  this review anticipated — confirmed via `go build ./...` (clean) and `make test` (full suite
  PASS), not just by reading the diff.
- **Every other file's F-authored diff is line-shift-only, no semantic change**, verified the same
  way for `internal/engines/analyzers/throughput/` and `internal/collector/`+`internal/config/`+
  `docs/` (the last two: `internal/config/config.go`'s diff is byte-for-byte identical pre/post
  rebase). One dev-guide hunk (`throughput-analyzer.md`, the I-4 local-demand note) landed inside a
  section C had rewritten (renamed to "Per-Variant Demand (Introspection Only)") — read the
  resulting text directly and it's coherent: F's sentence now sits as item 3 of C's rewritten
  three-tier priority chain, in place.
- `gofmt -l ./internal ./cmd` — clean. `go build ./...` — clean. `make test` — full suite PASS.
  `make lint` — 0 issues. DCO — 7/7 (`git log f9f04d81..abeb048f`). §4a scan (widened pattern, diff
  + all 7 commit messages) — clean. Commit subjects unchanged from pre-rebase.

Finding 1 (freshness-rollup timestamp-list duplication) and the open question about the second
§4a history rework are unaffected by the rebase — both still stand as written above.

**Verdict: ready to push**, pending Dean's confirmation.

## Post-second-rebase re-verification (2026-07-30) — PR #1503

This branch is now open upstream as **PR #1503**. `upstream/main` advanced again,
`f9f04d81` → `da58c0e0` (**#1486**, "ScalingPolicy schema Phase 1"), which put #1503 into
`CONFLICTING`/`DIRTY` on GitHub (confirmed via `gh pr view 1503 -R llm-d/llm-d-workload-variant-autoscaler`
— `headRefOid` there is still the *first*-rebase tip `abeb048f`; the local second rebase below has
not been pushed). New local tip **`021b6f8d`** (was `abeb048f`), base `upstream/main@da58c0e0`.

**This rebase had a real conflict, not a mechanical replay — verified directly:**

`#1486` deleted `SetLimiterForTest`/`ReloadQuotaForTest` and the `limiterConfig` type entirely from
`internal/config/config.go` (superseded by ConfigMap-driven `EffectiveLimiterMode()`/
`EffectiveQuotaEntries()`). This branch's own `SetOptimizationIntervalForTest` (added for the DR-1
zero-interval test, unrelated to the limiter schema) sat textually adjacent to the deleted
functions. Confirmed:
- `SetOptimizationIntervalForTest` survived, unchanged in substance
  (`grep -n SetOptimizationIntervalForTest internal/config/config.go`).
- Zero dangling references anywhere in the tree to the deleted `SetLimiterForTest` /
  `ReloadQuotaForTest` (`grep -rn` across all `.go` files — none).
- The function's own doc comment, which used to say "Exported for the same reason as
  `SetLimiterForTest`," was correctly reworded to drop the now-dead cross-reference (confirmed by
  diffing this function's hunk pre- vs post-rebase) rather than left pointing at deleted code.
- `go build ./...` — clean (would have failed immediately had the merge gone wrong here).

`internal/engines/saturation/engine_v2.go`: #1486 changed `aw.Name ==` → `aw.EffectiveType() ==`
in three functions (`scoreForAnalyzer`, `resolveThresholds`, `effectiveEnabled`) — none of which
this branch's Commit 5 touches (`updateLivenessAndSetLive`, `pruneLastGoodAnalysis`). Diffed
`git diff f9f04d81..abeb048f -- internal/engines/saturation/` against
`git diff da58c0e0..021b6f8d -- internal/engines/saturation/`: identical except line-shifts and the
blob hash — auto-merged clean, no manual fix needed, confirmed rather than assumed.

Every other F-authored file (`throughput/`, `collector/`, `docs/`) diffed the same way: line-shift
only, byte-identical content.

**Full gate re-run:** `gofmt` clean, `go build ./...` clean, `make test` full-repo PASS, `make lint`
0 issues, DCO 7/7 (`git log da58c0e0..021b6f8d`), §4a scan (diff + commit messages) clean.

**Push ownership note:** this is now a live open PR (#1503); per the plan's step 0, the *planner*
force-pushes with Dean's explicit confirmation — not the coder, and not this review. Both open
findings (Finding 1, and the §4a-history-rework open question) remain unaddressed and unaffected
by either rebase.

**Verdict unchanged: ready to push** (locally) — the remaining step is the planner's force-push to
origin/upstream with Dean's confirmation, which will resolve #1503's current `CONFLICTING` state on
GitHub.
