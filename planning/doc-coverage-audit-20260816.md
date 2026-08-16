# Doc coverage audit — Type 2 / Type 4 / call-stack docs, 2026-08-16

**Kind:** analysis (per `doc-and-session-model.md`'s "Kinds the audit found" table — output of an
investigation, proposes nothing, judges nothing). **Status: state capture only — no doc edits made
as part of producing this report**, per Dean's explicit instruction for this pass.

**Scope:** three questions, asked across every mission with a Type 1 (design) doc:
1. Does a Type 2 (roadmap) exist, and is it current against actual PR/code state?
2. Do Type 4 (reference, `docs/developer-guide/` on code branches) docs exist and match current code?
3. Does a call-stack/data-flow doc exist — either a standalone reference, or embedded inline in a
   Type 3 (as `sync-watchers-spec.md`'s `## Intent` section does)?

**Method:** six parallel Explore-agent audits (one per mission or mission-pair), each independently
reading the relevant `planning/` docs, the relevant `docs/developer-guide/` files on the relevant code
worktree, and the actual Go/script source — cross-checked against `session/CURRENT.md` and
`session/status/*.md` for ground truth on what has actually landed. Two additional findings made by
direct read, not delegated. `planning/planning-map.md` (itself DRAFT) was used as the starting index,
not as ground truth — it turned out to have its own drift, noted below.

---

## The call-stack-doc question is already answered — a decision of Dean's is half-finished, not a new question

Dean's two named examples turned out to be **two different mechanisms that happen to rhyme**, not one
mechanism at two granularities:

1. **`sync-watchers-spec.md`'s embedded stack** is a **named, fixed field** in the atomic-step-protocol
   Type-3 template. `atomic-step-protocol-design.md:242-243`: `## Intent` has fixed fields `intent`,
   `current call stack`, `planned call stack`, `new components`, `new conventions` — explicitly to make
   review *bounded rather than diligence-dependent*. Not informal; already spec'd, and correctly
   spreading — 11 Type-3 docs in that cluster now carry it (`checkpoint-capture-spec.md`,
   `doc-tooling-spec.md`, `role-skills-spec.md`, `conventions-authoring-spec.md`, and others).

2. **`multi-analyzer-postrefactor-map.md`'s shape** — standalone, reviewer-facing, file:line citations,
   TOC — is a **different kind**, and **Dean already ruled on it**: `doc-and-session-model.md:114`
   names it **"source trace"** (with `multi-analyzer-dataflow-map.md` as the sibling example), records
   his 2026-08-07 ruling that these are **"traces, not authorities — cite for per-site line evidence
   only; the design governs on disagreement,"** and flags **"deserves its own type name."** That
   promotion never happened.

So the open work here isn't "decide whether these are new" — it's (a) finish promoting *source trace*
to a real, named type, and (b) separately decide whether the atomic-step-protocol's `current call
stack` field should be back-ported as a convention for non-atomic-step Type 3s.

---

## Type 2 (roadmaps) — per mission

| Mission | Type 2 exists? | Current? |
|---|---|---|
| TA | 3 docs (`TA-Plan.md`, `TA-forward-plan.md`, `TA-e2e-plan.md`) | **All three stale.** `TA-Plan.md` still describes pre-merge PRs from long before TA 0.9 merged. `TA-forward-plan.md`'s own header still says `Status: ACTIVE` with no note that all P0 items are done — a reader can't tell without cross-checking CURRENT.md. `TA-e2e-plan.md` still frames around the long-merged PR-5 wiring PR. |
| Multi-analyzer engine | 2 docs, both effectively dead | `ENGINE-multi-analyzer-plan.md` self-flags SUPERSEDED (correct, not a problem). `multi-analyzer-addendum-plan.md` is a **finished Type 3 mislabeled as Type 2** in `planning-map.md` — the mission has no live roadmap at all, silently. |
| Anchor-refactor | **None** | Confirmed absent by grep; `planning-map.md` doesn't even flag this as a gap for this mission (it flags the same gap for three other missions but misses this one). |
| Optimizer/cost-allocation | None | Confirmed absent — matches `planning-map.md`'s own claim. |
| pokprod | 2 current docs | **Current — and the map is wrong about it.** `ta-pokprod-roadmap.md` is Dean's **first-ever** Type 2 for this mission (created 2026-08-15), but `planning-map.md:170` calls it "(early)" as if superseded by `ta-pokprod-testing-plan.md` — backwards. The newest doc is described as the oldest. |
| autoscaling-viz | 1 doc | **Stale in the map's summary, less stale in the doc itself.** The map says "6 items, most still open." The doc actually has **12 items** now; of the original 6, half are done or superseded. The doc updates itself reasonably; the map lags behind it. |
| Benchmark harness/observability | `benchmark-observability-plan.md` | **Mislabeled and superseded.** It's a Type 3, not Type 1/2 (the map flagged its own uncertainty here — resolved: it's a Type 3). Its main content (Parts 1-4, the INFO log schema) was superseded by `wva-saturation-cycle-log-plan.md`, which shipped a different schema and is confirmed live in `docs/developer-guide/cycle-log.md`. |
| atomic-step-protocol (internal tooling) | `atomic-step-protocol-roadmap.md` | **Real, functioning roadmap** — genuinely tracks phases/scripts/defects. One concrete gap: it lists `single-instance-guard.sh` as "not started," but the file exists on disk, fully written, modified same day. One step behind. |

## Type 4 (dev-guide references) — per mission

| Mission | Coverage | Currency |
|---|---|---|
| TA | `throughput-analyzer.md` | **Stale.** The anchor refactor (#1516, merged) added scale-from-zero behavior and `bindingAnchor`/`Enabled` participation to TA, and #1516's own doc-update commit touched `multi-analyzer-pipeline.md` and `saturation-scaling-config.md` — **but not this file**. Confirmed via `git show 57f3fe64 --name-only`. |
| Multi-analyzer engine | `multi-analyzer-pipeline.md` | **Current on the mechanism, one internal inconsistency**: its own "Optimizer consumption" section (~lines 502-511) still says the optimizer reads the saturation entry's `VariantCapacities` directly — contradicted by its *own* earlier "How results combine" section, which correctly describes the `bindingAnchor` merge. Not updated when the anchor mechanism landed. |
| Anchor-refactor (PR-2 specifically) | same file | **Current and accurate** — three specific claims cross-checked against `analyzer_helpers.go` line-by-line, all matched, including a verbatim-matching comment. The one mission where Type 4 is unambiguously good. |
| Optimizer/cost-allocation | same file, uncommitted diff | Uncommitted addition (rationale + worked example + edge-case table, all citing real test names) is **complete and polished**, not WIP — blocked behind the Phase-2 clean-design discussion before it can commit. |
| pokprod | none | `benchmark-guide.md` has **zero mentions of pokprod**. Arguable whether it owes one; flagged either way. |
| autoscaling-viz | `COVERAGE-CHECKS.md` | **Genuinely good Type-4-equivalent** for a non-code-branch mission — but isn't labeled as Type 4 anywhere, and the followon-plan still says "not yet written" for an item that's actually landed. |
| Benchmark harness | `benchmark-guide.md`, `two-variant-wva-benchmark.md` | **Stale, confirmed concretely.** Both describe the old flat results layout, not the current `runs/<id>/{config,raw,viz}/` tree (code-complete since 2026-08-11/12). Neither mentions the env-guard contract or T9/gateway-log-follower — both real, both heavily used per `session/status/benchmark.md`. |
| atomic-step-protocol | split | `plans-tooling/README.md` covers the conventions sub-cluster well. **No equivalent exists for the checkpoint/sync script family** — the Type-3 specs are doing double duty as the only reference, fragile if they go stale post-fix. |

## Call-stack docs — per mission

| Mission | Exists? |
|---|---|
| TA | **No** — confirmed no TA-scoped doc in either shape. The two engine-level map docs mention TA only in passing. Flagged by its own auditor as notable given TA is "the oldest and largest mission." |
| Multi-analyzer engine (base) | **No**, and a genuine gap distinct from the anchor overlay: `multi-analyzer-dataflow-map.md` is pinned to `9906dac5` — **one commit before** the anchor refactor merged — and describes the now-superseded pre-refactor identity model. Nothing describes the base engine's dispatch/registration/lifecycle independent of the anchor overlay, current as of today. |
| Anchor-refactor | Partial, and **confirmed stale**: `multi-analyzer-postrefactor-map.md` explicitly deferred three items as `[next PR]` — all three have now **landed** in PR-2's actual code (verified against `analyzer_helpers.go` line-by-line: the tie-break logic, the dropped sat-sizing fallback, the `&& e.Live` gate on `votingResults`). The doc describes PR-1's world as if it were still current. |
| Optimizer/cost-allocation | No | `optimizer-coordination-design.md` has adjacent content (a code-mapping table, a deviations list) but not the dispatch-tree shape. |
| pokprod | N/A | Correctly not applicable — cluster experimentation, no call stack to document. |
| autoscaling-viz | No | Flagged as a real gap given `extract_real_trace.py`/`render_real_trace.py` are 65-70KB each with genuine architectural complexity. |
| Benchmark harness | No | Correctly not applicable in the strict sense (shell/Makefile orchestration), but a "how the harness actually flows" doc (standup → env-guard → run_cell → results-tree → viz) was flagged as would-be-useful and doesn't exist. |
| atomic-step-protocol | Yes, systematically | Every Type 3 in this cluster has one via the `## Intent` field — **except one script**: `sync-current-watch.sh`, explicitly named in `sync-watchers-spec.md` itself as needing its own spec, still absent, and still on the pre-Addendum-7 guard pattern (the most behind *and* the least documented, at once). |

## Two findings beyond the three questions, made by direct check (not delegated)

1. **`combined-analyzer-optimizer-design-addendum-1.md:18`** still reads: *"`AD8`'s placement in PR-2
   remains the single open question with Dean."* `session/CURRENT.md` records this as **already decided
   and landed** (`AD8` (b) → `C12`, at both line 130 and line 460). The addendum's own headline open
   question is stale.

2. **`planning-map.md` itself has drifted** in at least three places found across the six audits: the
   pokprod roadmap relationship is inverted (newest doc described as oldest/superseded), the
   atomic-step-protocol addenda count is wrong (says 8, there are 10 — two landed the same day as this
   audit), and the anchor-refactor mission's missing Type 2 isn't flagged as a gap even though the map
   flags the same gap for three other missions. The map is itself `Status: DRAFT` with no refresh
   mechanism (a gap it names about itself), so this is expected, not alarming — but means don't treat
   the map as ground truth for a future pass either, including this doc's own eventual refresh.

## Decisions made after this report (2026-08-16, same day)

Dean reviewed this audit and ruled on scope and process. Recorded here as a pointer — the decisions
themselves live in the handoff, not duplicated:

- **Do not touch active-owner docs.** Every Type 1/2/3/4/6 with a live owner needs coordination with
  that owner first — this audit surfaced staleness, it did not authorize fixing it.
- **Process fix ownership: atomic-step-protocol planner, not this session.** Two asks routed via
  [`plan__call-stack-process-two-asks.md`](../session/handoffs/plan__call-stack-process-two-asks.md):
  (1) generalize the `current call stack` field to non-atomic-step Type 3s, scoped to *only the
  stacks that specific Type 3 touches* — narrower than `multi-analyzer-postrefactor-map.md`'s
  whole-mission tour shape; (2) Type 6 may add a similarly-scoped stack per review; the *aggregate*
  stack (many Type 3/6 stacks merged into one picture of what actually exists) gets an **interim** home
  inside Type 2 — not Type 4, since Type 4 ships in the PR and must never run ahead of code — with
  Dean explicit that this is temporary ("we move it later").
- **Cleanup authorized only for ownerless docs**, and narrowly: merged/abandoned Type 3 gets a PR
  pointer only, no rewrite (done: [`benchmark-observability-plan.md`](benchmark-observability-plan.md)
  now points at its superseding doc and PR #1277). Type 4 and its call-stacks are explicitly **out of
  scope** — production-touching, needs its own PR-based mission, left alone. Type 2 shortening (a
  checklist of merged PRs / open items / roadmap items, no call-stack content) applies only to
  ownerless missions — from this audit's set, `ENGINE-multi-analyzer-plan.md` already self-flags
  SUPERSEDED and needs nothing further; no other Type 2 in the audited set was found ownerless.

## Not decided (still open, deliberately)

- Whether to promote *source trace* to a named type, and where it lives in the taxonomy — flagged to
  the atomic-step planner as related but not folded into their two asks.
- Which stale *active-owner* doc to prioritize fixing — not this session's call; needs coordination
  with each doc's owner.
- Whether `planning-map.md` itself should be corrected now or left until a broader refresh.

## Sources

Six parallel Explore-agent audits (2026-08-16), each reading: the mission's `planning-map.md` section,
its Type 1/2/3 docs in full, the relevant `docs/developer-guide/` files on the relevant code worktree,
the actual Go/script source the docs describe, and cross-checks against `session/CURRENT.md` /
`session/status/*.md`. Plus two direct reads: `atomic-step-protocol-design.md:225-259` (the `## Intent`
fixed-field spec) and `doc-and-session-model.md:105-124` (the "Kinds the audit found" table, including
the 2026-08-07 source-trace ruling), and `combined-analyzer-optimizer-design-addendum-1.md:15-18` cross-
checked against `session/CURRENT.md:130,460`.
