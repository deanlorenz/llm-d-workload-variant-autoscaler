# Open Items Roadmap

**Status:** DRAFT — scoring in progress (multi-analyzer area complete; TA + D52 in progress)
**Last updated:** 2026-06-11
**Scope:** Open items + recently-closed tail (~2 weeks). Includes operational backlog *only when not already-captured in `session/CURRENT.md` § Next-steps* (those are transient and live there). This roadmap is the **strategic backlog**: things that *can* be done after the in-flight PRs land, scored for triage.

This is a Type-2 living roadmap (per `session/CONVENTIONS.md`). Source-of-truth for backlog priorities; transient/operational state continues to live in `session/CURRENT.md`. When CURRENT's "Issues to Open" list is next refreshed, it should point at this doc as the canonical backlog.

---

## Methodology

**Scoring rubric** (Eisenhower × effort, agreed 2026-06-09):

- **Quadrant** — Eisenhower 2×2 over (Urgent? × Important?):
  - **Q1 — Do** (urgent + important): block-or-soon-after the next merge cycle.
  - **Q2 — Schedule** (not urgent + important): plan a slot; don't drop.
  - **Q3 — Delegate** (urgent + not important): mechanical / hand off / file as standalone issue without claiming attention.
  - **Q4 — Drop** (neither): keep for record but don't fund.
- **Effort** — S (≤1 day) / M (1–3 days) / L (>3 days).
- **Deps** — `blocked-by [ID]` and/or `blocks [ID]`. Cross-area deps explicitly named.

**Scoring is deferred** to a follow-up pass; the columns are placeholders (`?`) below. Bulk-score in batches per area, then refine the dependency graph.

**Item format**: `ID — Title — Source ref — Gating — Q ? — Eff ? — Deps ?`

ID format: `<area>-<seq>` for stable cross-reference (e.g., `MA-F4`, `TA-R-1`, `D52-3`). IDs are never reused; if an item is dropped or absorbed, mark it superseded but keep the slot.

---

## Recently closed (≥ 2026-05-26)

| Date | Item | Evidence |
|---|---|---|
| 2026-05-29 | TA2 review items 2/6 (ShapeTracker EWMA doc; PrefixCacheHitRate weighted) | PR1052-review.md TA3 coverage table |
| 2026-06-07 | **#1225** `multi-analyzer-registration` MERGED | `f664a470` on main |
| 2026-06-08 | **#1228** `multi-analyzer-threshold` MERGED | `d9e4ae1f` on main |
| 2026-06-08 | **#1237** upstream role-aware scale-down MERGED | `badc48be` on main |
| 2026-06-08 | `engine-queue-fix` SchedulerQueue wiring absorbed into optimizer commit `3fe287fe` | TA-PR5-plan.md §2.7 |
| 2026-06-08 | Optimizer **B1** (Score never populated) — fixed | optimizer-review.md Phase 2 |
| 2026-06-08 | Optimizer **B2** (paired-scale-up AND-guard) — fixed | optimizer-review.md Phase 4 |
| 2026-06-08 | Optimizer **P3.1/P3.2/P3.3** Phase 3 cleanup — closed via `2711bdc1` | optimizer-review.md Phase 4 |
| 2026-06-09 | **#1246** `multi-analyzer-optimizer` opened; rebased onto `main@badc48be` (`ad1a8e1e`) | CURRENT.md |
| 2026-06-09 | Design doc **F6** (sat_v2 in-analyzer formula simplification) — completed via #1228 | design.md §F6 (listed for completeness only) |
| 2026-06-10 | **#1246** `multi-analyzer-optimizer` MERGED (`09e1c386` on main) | CURRENT.md |
| 2026-06-10 | **MA-1113-A** per-analyzer threshold override resolution — DONE in #1246 (`resolveThresholds`, `applyUniversalThreshold`, `EffectiveScaleUpThreshold`) | engine_v2.go; config/saturation_scaling.go |
| 2026-06-10 | **MA-F5** model-level RC/SC for disaggregated — operationally resolved; `initRoleState` uses `RoleCapacities` for disagg, model-level scalars only for `"both"` | engine_v2.go; analyzer_helpers.go |
| 2026-06-10 | **MA-1225-A** stale "panic" docstrings — CLOSED; all 4 fixes present on main@2a0c3a7c | grep confirms |
| 2026-06-10 | **TA-R-1..R-4** (D1/D2/T1/T2 from TA-PR5 review) — all committed on TA3 branch (`26394354`, `ea218f6d`, `24917288`); in PR #1250 | TA3.1-plan.md §1 |
| 2026-06-11 | main updated to `2a0c3a7c` (+6 commits: #1107 events, #1230 benchmark doc, #1243 agents doc, #1242 Coordinator, #1255 sat_v2 gpuCount key fix) | git merge --ff-only upstream/main |

---

## Multi-analyzer

### Design futures (`planning/multi-analyzer-design.md` § Future direction)

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| MA-F1 | Pre-analysis extraction — extract variant identity (Cost, AcceleratorName, Role, replica counts) from saturation V2 into a common pre-analysis stack so saturation is a peer, not always-first. Eliminates `saturationEntry()` helper dependency. | design.md §F1; PR1113-review.md "variant identity" caveat | post multi-analyzer stack merge | Q2 | L | ? |
| MA-F2 | Vector α / analyzer-published `D(p)` — analyzer publishes α directly on `RoleCapacities`, or `D(p)` as a function. Supports vector demands and non-linear couplings. | design.md §F2 | post multi-analyzer stack merge | Q4 | L | blocked-by `MA-F1` |
| MA-F3 | Per-analyzer status-return state (`AnalyzerStatus`: SuppressSC / SuppressRC / SuppressBoth / Fail). Restores TA's EPP-queue + GPS-mismatch SC gating; subsumes F9 and the deferred `ThresholdApplied` flag (PR1113 Appendix B); also fixes SchedulerQueueMetrics discriminators. | design.md §F3, §F9; TA-PR5-plan.md §7; TA-PR5-plan.md §8 (TA-F-8) | post #1246 + #1250 merges | Q2 | M | ? |
| MA-F4 | Per-analyzer observability — Prometheus gauges (`wva_analyzer_required_capacity`, `_spare_capacity`, `_utilization`) labeled by `analyzer_name`; generalize `enrichDecisionsWithKvTokenData` to per-analyzer decision-enrichment hook. | design.md §F4; CURRENT § Issues to Open | post #1246 merge | Q2 | M | blocked-by `MA-F1` (helps but not strict) |
| ~~MA-F5~~ | ~~Engine model-level RC/SC for disaggregated models — latent bug.~~ **CLOSED** — `initRoleState` in #1246 uses `RoleCapacities` for disagg; model-level scalars never read by optimizer for disaggregated path. Fields still exist but are unused. | design.md §F5 | resolved by #1246 | — | — | — |
| MA-F7 | `enabled:false` analyzer veto fix — `runAnalyzersAndScore` appends all registered analyzers unconditionally; disabled analyzer with Spare>0 vetoes scale-down. Fix: skip-the-run for disabled entries. **In PR-A** (`multi-analyzer-addendum-plan.md`). | design.md §A8 / §F7 | post #1246 merge; unblocked | Q1 | S | — |
| MA-F8 | Replica-count accounting consistency — TA uses `len(variantMetrics)`; sat_v2 uses `readyCount`. Reconcile to canonical engine source. | design.md §F8; TA-PR5-plan.md §7 | post #1250 merge | Q2 | S | ? |
| MA-F10 | Fold queueing-model into V2 multi-analyzer engine (Option A: register QM as saturation-slot analyzer). Fixes 4 pre-existing QM oversights: threshold post-step skipped, SchedulerQueue not threaded, disaggregation dispatch missing, GPU limiter not enforced. | design.md §F10; CURRENT § Issues to Open | post #1246 merge | Q2 | L | own design doc needed first |
| MA-F11 | Joint-allocation generalization beyond P/D — >2 roles, mixed role/non-role within a model, multi-model joint demand, multi-location replication. | design.md §F11 | post multi-analyzer stack stable | Q4 | L | blocked-by `MA-F2` |
| MA-F12 | Per-role RC/SC canonical end-to-end — engine/analyzer always populates `RoleCapacities` including `"both"` for non-disaggregated; drop model-level RC/SC scalars. | design.md §F12; CURRENT § Issues to Open | deferred — ripples into #1228 contract and TA analyzer | Q2 | L | ? |
| MA-F13 | Cost picker integer-rounding suboptimality — `cost/PRC` ascending mis-picks at the tail when `RC < PRC`; pragmatic fix is residual-RC tail re-rank. | design.md §F13; optimizer-plan.md Phase 3 note | out of scope for Phase 3 | Q3 | S | ? |
| MA-A9 | Engine package rename `internal/engines/saturation/` → `internal/engines/` — historical naming artifact. | design.md §A9 | long-term cleanup | Q4 | M | ? |
| MA-A10 | `RoleRemaining map[string]float64` field on `NamedAnalyzerResult` — symmetric to `RoleSpare`; first-class per-role demand bookkeeping. | design.md §A10 | future PR if load-bearing | Q3 | S | enables `MA-F4`, `MA-F11` |

### Multi-analyzer review residue (not yet addressed)

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| MA-H-1 | Engine config-bridge tests — assert `runAnalyzersAndScore` correctly populates `Score`, `Disaggregated`, per-analyzer threshold overrides. **In PR-A** (`multi-analyzer-addendum-plan.md` §Item 2). | optimizer-review.md Phase 4 | post #1246; unblocked | Q1 | S | — |
| MA-OPT-4 | Greedy fair-share with non-uniform `Score` — multi-model integration test, non-uniform Score across analyzers (T1.3 covers uniform case only). **In PR-A** (`multi-analyzer-addendum-plan.md` §Item 2). | optimizer-review.md Phase 4 | post #1246; unblocked | Q1 | S | subset of `MA-H-1` |
| MA-OPT-5 | QM path consistency — `engine_queueing_model.go` hardcodes `Score: 1.0`; low impact (single-analyzer path, 1.0 is correct default). | optimizer-review.md Phase 2 | post #1246 | Q3 | S | absorbed by `MA-F10` if Option-A lands |

### Threshold-design open items

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| ~~MA-1113-A~~ | ~~Per-analyzer threshold override resolution.~~ **CLOSED** — done in #1246: `resolveThresholds` + `applyUniversalThreshold` per analyzer; `EffectiveScaleUpThreshold`/`EffectiveScaleDownBoundary` helpers in config. | PR1113-review.md | resolved by #1246 | — | — | — |
| MA-1113-B | Threshold via `AnalyzerInput` — thread resolved per-analyzer thresholds into `AnalyzerInput` so analyzers can use them for in-analyzer calibration/logging. `AnalyzerInput` has no threshold fields today. Unblocked (MA-1113-A done; F3 dependency was a specific design variant, not a hard gate). | PR1113-review.md | unblocked (was blocked-by MA-1113-A, now done) | Q2 | S | — |
| MA-1113-C | Threshold abstraction — auto-derive thresholds from observed variance or expose "target utilization" knob. Long-term. | PR1113-review.md | long-term | Q4 | L | — |
| MA-1113-D | Smart Greedy scale-down with multi-model foresight — choose scale-down variants to free scarce accelerators competing models need. | PR1113-review.md Future directions | post multi-analyzer stack stable | Q4 | L | ? |
| MA-CAV-2 | RoleCapacities multi-analyzer aggregation strategy for P/D — undefined today; optimizer reads from saturation's entry by convention. No crash today (saturationEntry is a hard precondition). Design pass needed before multi-analyzer P/D is meaningful. | PR1113-review.md Caveats | deferred to follow-up | Q2 | M | blocked-by `MA-F1`; pre-req for `MA-F11` |
| TA-F-9 | Per-analyzer threshold CRD surface — wire the API field through CRD reconciliation (config-side already in place via MA-1113-A). | TA-PR5-plan.md §8 | out of scope for PR-5 | Q3 | S | MA-1113-A done; CRD plumbing only |

### Docs / mechanical

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| MA-OPT-1 | Multi-analyzer dev-guide expansion — stub exists on main (`docs/developer-guide/multi-analyzer-pipeline.md`); expand with user config, analyzer implementor guide, pipeline flow, veto semantics. **In PR-A** (`multi-analyzer-addendum-plan.md` §Item 3). Note: ev-shindin #1223 adds `optimizers.md` (algorithms); PR-A doc covers pipeline flow — complementary. | optimizer-plan.md Open items | unblocked (#1246 merged) | Q1 | M | — |
| MA-OPT-2 | Doc fork-URL fix — `multi-analyzer-pipeline.md:46` links to personal fork. **In PR-A** (absorbed by MA-OPT-1). | optimizer-plan.md Open items | unblocked | Q1 | S | absorbed by `MA-OPT-1` |
| MA-REG-1 | Registration dev-guide note — surface `RegisterAnalyzer` error string + `analyzersSnapshot` mechanism. Absorbed by MA-OPT-1. | registration-plan.md Open items | unblocked | Q2 | S | absorbed by `MA-OPT-1` |
| ~~MA-1225-A~~ | ~~Stale "panic" docstrings.~~ **CLOSED** — all 4 fixes present on main@2a0c3a7c; confirmed via grep. | PR1225-review.md | closed | — | — | — |

---

## Throughput-Analyzer

### TA roadmap (long-term)

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| TA-F-1 | Mixed-workload PR — multiple workload bins via weighted average of A. Does NOT block μ_dec (single-workload μ_dec works in TA3). Extension only. | TA-Plan.md Phase 3 | post-#1250 + Step 2f validated | Q2 | L | blocked-by TA3 merge + Step 2f |
| TA-F-2 | μ_RPS supply model — request-rate-based supply. | TA-Plan.md Phase 3 | requires TA-F-1 stable | Q4 | L | ? |
| TA-F-3 | Saturation detection — TTFT knee prediction. | TA-Plan.md Phase 3 | post PR-3+PR-4 stable | Q4 | L | ? |
| TA-F-4 | TA API extension — `ThroughputAnalyzerConfig`, gRPC/REST recalibration. | TA-Plan.md Phase 3 | only if required | Q4 | M | ? |
| TA-F-5 | Tier-3 ITL knowledge store wiring — wire `itlKnowledgeStore` into `Analyze()`. | TA-Plan.md PR-4 OOS | out of scope for PR-5 | Q2 | M | ? |
| TA-F-6 | Unify `DefaultKSat` with EPP system-wide k_sat. | TA-Plan.md PR-4 OOS | out of scope for PR-5 | Q3 | S | ? |
| TA-F-10 | Prefill-specific rate signals for dedicated prefill pods. | TA-PR5-plan.md §8 | out of scope for PR-5 | Q3 | S | ? |
| TA-F-12 | Additional TA e2e scenarios — cold-start, multi-variant, P/D disagg. Parallel track; does NOT fix TA-OBS-3 smoke failures (different harness). | TA-PR5-plan.md §8 | post-#1250 merge | Q2 | M | ? |

### TA-PR5 review follow-ups (post-#1250 merge)

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| ~~TA-R-1~~ | ~~D1 — rewrite stale Analyze doc-comment.~~ **IN PR #1250** — commit `26394354` on TA3 branch. | TA-PR5-review.md D1 | in #1250 | — | — | — |
| ~~TA-R-2~~ | ~~D2 — drop stale computeLocalDemand comment.~~ **IN PR #1250** — commit `26394354` on TA3 branch. | TA-PR5-review.md D2 | in #1250 | — | — | — |
| ~~TA-R-3~~ | ~~T1 — rename GPS-suppression test blocks.~~ **IN PR #1250** — commits `ea218f6d` + `24917288` on TA3 branch. | TA-PR5-review.md T1 | in #1250 | — | — | — |
| ~~TA-R-4~~ | ~~T2 — add 5 aggregation-helper linearity specs.~~ **IN PR #1250** — commit `ea218f6d` on TA3 branch. | TA-PR5-review.md T2 | in #1250 | — | — | — |

### TA observability + e2e + misc

| ID | Title | Source | Gating | Q | Eff | Deps |
|---|---|---|---|---|---|---|
| TA-OBS-1 | ArrivalRate staleness check in `computeDemand` (Bob review 1.3) — observability PR. | CURRENT § Issues to Open | post-#1250 merge | Q2 | S | ? |
| TA-OBS-2 | E2E Step 2f — full TA scenarios (TA-driven scale-up + TA-only mode). Pending Dean's go-ahead. | CURRENT TA3 section | gated on Dean's green-light | Q2 | M | ? |
| TA-OBS-3 | Triage 3 pre-existing smoke failures: `smoke_test.go:339, :542, :1724`. Cannot be fixed by benchmark infrastructure (different harness). Must be triaged post-#1250 merge. | CURRENT § Next steps | post-#1250 merge | Q2 | S | ? |
| TA-OBS-4 | ndots fix — `test/e2e/fixtures/workload_builder.go` commit `3c838547` sets `ndots:2` for musl DNS. **IN PR #1250** as-is (option A per TA3.1-plan.md §4); decision to extract deferred to Dean. | CURRENT § Issues to Open | in #1250; extraction optional | Q1 | S | before #1250 merge if extracted |
| TA-OBS-5 | ITL model Prometheus gauges — `wva_throughput_analyzer_itl_model_{a,b}` labeled by namespace/model/variant/tier. | TA-PR5-plan.md §7 item 4 | post-#1250 merge | Q2 | S | ? |

---

## Deferred TA2 / PR-3 fixes (grouped fixup PR after #1250 merges)

### From `planning/PR1052-deferred-fixes.md` (10 itemized fixes)

| ID | Title | Source | Q | Eff | Deps |
|---|---|---|---|---|---|
| D52-1 | `DefaultWindowMaxSize` doc/code mismatch — `constants.go=20` vs developer-guide `100`. | PR1052-deferred-fixes.md | post-#1250 merge | Q3 | S | ? |
| D52-2 | `Analyze()` silently drops `a.Observe(...)` return → `_ = a.Observe(...)`. | PR1052-deferred-fixes.md | post-#1250 merge | Q2 | S | ? |
| D52-3 | `CheckModelMetrics` doc-comment overstates contract. | PR1052-deferred-fixes.md | post-#1250 merge | Q2 | S | ? |
| D52-4 | `averageShapeMetrics()` zero-count branch untested. | PR1052-deferred-fixes.md | post-#1250 merge | Q2 | S | ? |
| D52-5 | No `-race` test for simultaneous `Observe()` + `VariantState()`. | PR1052-deferred-fixes.md | post-#1250 merge | Q2 | S | ? |
| D52-6 | `pod_name` label fallback untested for 3 metrics. | PR1052-deferred-fixes.md | post-#1250 merge | Q2 | S | ? |
| D52-7 | Unbounded `variantStates` map — no eviction; stale VA entries produce false shape-change signals. *Latent correctness bug.* | PR1052-deferred-fixes.md; PR1052-review.md ev-shindin thread 1 | post-#1250 merge | Q1 | M | EV52-2 enables testing |
| D52-8 | `EscapePromQLValue` ergonomics — easy to forget. | PR1052-deferred-fixes.md | post-#1250 merge | Q3 | S | ? |
| D52-9 | `SanityReport.Has()` → `slices.Contains`. | PR1052-deferred-fixes.md | post-#1250 merge | Q3 | S | ? |
| D52-10 | `issueSet map[SanityIssue]struct{}` → `sets.New[SanityIssue]()`. | PR1052-deferred-fixes.md | post-#1250 merge | Q3 | S | ? |

### From PR1052-review.md ev-shindin threads (additional, not in deferred-fixes.md)

| ID | Title | Source | Q | Eff | Deps |
|---|---|---|---|---|---|
| EV52-2 | Inject `clock.Clock` (or `now time.Time` param) into `Observe` — make time-based pruning testable. Prerequisite for properly testing D52-7. | PR1052-review.md thread 4 | post-#1250 merge | Q1 | S | pre-req for D52-7 testing |
| EV52-3 | Log/metric when k-values fall outside `[0.15, 0.85]` — `Ready()` stays false permanently with no signal if workload is outside range. | PR1052-review.md thread 5 | post-#1250 merge | Q2 | S | ? |
| EV52-4 | `variantKey` separator collision — `|` separator collides with operator-provided `modelID` containing `|`. Data-integrity risk; comment added in TA3 but root not fixed. | PR1052-review.md thread 7 | post-#1250 merge | Q1 | S | ? |

---

## Infra

| ID | Title | Source | Q | Eff | Deps |
|---|---|---|---|---|---|
| INF-1 | EPP image version mismatch — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0. | CURRENT § Issues to Open | anytime | Q3 | S | ? |
| INF-2 | Gateway prompt bug — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true`. | CURRENT § Issues to Open | anytime | Q3 | S | ? |
| INF-3 | Makefile `IMG` always set — `deploy-e2e-infra` registry-image path unreachable. | CURRENT § Issues to Open | anytime | Q3 | S | ? |

---

## Process / cleanup

| ID | Title | Source | Q | Eff | Deps |
|---|---|---|---|---|---|
| PROC-2 | Close PR #1113 (`engine-multi-analyzer`) — superseded by 3-PR split; coordinate with ev-shindin first. | CURRENT PR Status | post-coordination | Q2 | S | ? |
| PROC-3 | Close `engine-queue-fix` branch + remove worktree — content absorbed into optimizer commit `3fe287fe`. | CURRENT § Next steps | unblocked | Q1 | S | ? |
| PROC-4 | Drop `backup/multi-analyzer-optimizer-pre-rebase@ae456aa0` ref. | CURRENT § Next steps | unblocked (#1246 merged) | Q1 | S | ? |
| PROC-5 | Remove `engine-multi-analyzer` worktree. | CURRENT § Next steps | at discretion | Q1 | S | ? |
| PROC-6 | PR #1092 (VA CRD removal) — short review comment ready (`scratch/PR1092-short-draft.md`); counter-proposal pending integration before posting. | CURRENT § Pending handoffs | awaiting Dean integration | Q2 | ? | ? |

---

## Dependency graph (updated 2026-06-11)

```
   #1246 MERGED ──► MA-F4, MA-F7 (Q1), MA-F10, MA-H-1 (Q1), MA-OPT-4 (Q1)
                 ── MA-1113-A CLOSED (done in #1246)
                 ── MA-F5 CLOSED (resolved in #1246)
                 ── MA-OPT-1/2 unblocked (PR-A scope)
                 ── PROC-3/4/5 unblocked

   PR-A (multi-analyzer-cleanup) ──► closes MA-F7, MA-H-1, MA-OPT-4, MA-OPT-1/2
     Watch: #1252 (cheaper-variant overflow fix) — if merged before PR-A, rebase
     Watch: #1223 (ev-shindin optimizer doc) — if merged, link from MA-OPT-1 doc

   #1250 merges ──┬─► TA-R-1..R-4 land on main (already in #1250)
                  ├─► TA-OBS-3, TA-OBS-5, TA-F-1, TA-F-12
                  ├─► MA-F8 (replica-count consistency, TA-side)
                  └─► D52-1..D52-10 + EV52-2..EV52-4 (fixup PR-A2, split into correctness+polish)

   MA-F1 ─────────► MA-F2 ─► MA-F11
                  └─► MA-F4 (strict dep relaxed; helps but not required)
                  └─► MA-CAV-2 (P/D multi-analyzer RoleCapacities aggregation)

   MA-F3 ─────────► subsumes TA-F-8 (ThresholdApplied flag)
   MA-1113-A DONE ─► MA-1113-B unblocked (F3 dep was design-variant only)
   MA-1113-A DONE ─► TA-F-9 unblocked (CRD plumbing only)

   MA-A10 ────────► load-bearing for MA-F4 (per-role obs) and MA-F11

   EV52-2 (clock injection) ─► enables D52-7 (eviction) testability
   EV52-4 (variantKey collision) ─► standalone fix, no hard dep
```

---

## Open questions (updated 2026-06-11)

- **MA-F3 vs F12 ordering.** F3 lands per-analyzer status flags; F12 makes `RoleCapacities` canonical. Either can come first; no hard dep between them. Both Q2/M or Q2/L; score together in next pass.
- **Mass close vs. selective issue filing.** Q1+Q2 items should be filed on GitHub post-#1246 merge. Q3/Q4 can stay roadmap-only. File in priority order after PR-A lands.
- **TA-R-1..R-4 RESOLVED** — all four are already in PR #1250 (`26394354`, `ea218f6d`, `24917288`). Lands with #1250. No separate action.
- **ndots (TA-OBS-4)** — currently in PR #1250. Leave in or extract as standalone PR? Decision pending Dean. Recommendation: leave in #1250 (option A in TA3.1-plan.md §4).
- **D52 split** — proposed two-PR split: PR-A1 correctness (D52-7+EV52-2+EV52-4+D52-2+D52-5) + PR-A2 polish (D52-1/3/4/6/8/9/10+EV52-3). Gate: post-#1250 merge.
- **#1223 (ev-shindin optimizer dev guide)** — no reviews yet; could merge anytime. MA-OPT-1 (PR-A) is complementary (pipeline flow, not optimizer algorithms). If #1223 merges first, PR-A links to it; no rework needed.
- **#1252 (biranofer cheaper-variant overflow fix)** — open, touches `cost_aware_optimizer.go`. If merges before PR-A is pushed, rebase PR-A onto updated main.

---

## Coverage notes

- **Sources surveyed:** `TA-Plan.md`, `TA-PR5-plan.md`, `TA-PR5-review.md`, `PR1052-deferred-fixes.md`, `PR1052-review.md`, `PR1051-review.md`, `PR1113-review.md`, `PR1225-review.md`, `multi-analyzer-design.md` (§Future direction + §Alternatives), `multi-analyzer-registration-plan.md`, `multi-analyzer-threshold-plan.md`, `multi-analyzer-optimizer-plan.md`, `multi-analyzer-optimizer-review.md`, `session/CURRENT.md`.
- **Excluded (out of scope):** `benchmark-wva-vs-keda{,-plan}.md` (NOT-AUTHORIZED gate keeps benchmark separate); `autoscaling-evaluation-framework.md` (separate eval-framework discussion track); `multi-analyzer-coder-rules.md` (process/agent-rule, not work backlog); historical TA-{notation,supply,demand,overview}.md (frozen design docs).
- **Deduplication:** when source A and source B describe the same underlying work (e.g., `multi-analyzer-design.md §F5` = `multi-analyzer-threshold-plan.md` "Open items" first bullet), one consolidated entry with both sources cited. Items merged: TA-F-8 → MA-F3; TA-F-11 → MA-A9; MA-CAV-1 → MA-F1; EV52-1 → D52-7; MA-TH-1 → MA-F5. Items dropped (already done): TA-F-X around saturation simplification (= MA-F6 done), MA-OPT-3 (rebase done in `ad1a8e1e`).
- **Item count:** ~58 open items + ~10 recently-closed.

---

## Next steps for this doc

1. ~~Score multi-analyzer area~~ — DONE (2026-06-11).
2. ~~Score TA area~~ — DONE (2026-06-11).
3. ~~Score D52/EV52 area~~ — DONE (2026-06-11).
4. CURRENT.md § Issues to Open — replace current bullet list with a pointer to this roadmap. Do in next sync.
5. Per-quadrant Q1/Q2 items: file as GitHub issues after PR-A lands, in priority order.
6. Add new upstream items to roadmap as they emerge (#1252 cheaper-variant fix, Coordinator follow-ons, etc.).
