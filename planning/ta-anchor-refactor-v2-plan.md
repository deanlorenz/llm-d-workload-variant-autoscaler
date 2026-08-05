# TA Anchor Refactor v2 — TA-0.9 critical enablement (self-contained)

**Type:** 3 (task plan) · **Status:** DRAFT
**Design authority:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (Type 1)
**Spec source:** [`ta-anchor-refactor-review.md`](ta-anchor-refactor-review.md) **Part 2** (§2.1–§2.7) — the corrected two-phase mechanism
**Current-code map:** [`multi-analyzer-dataflow-map.md`](multi-analyzer-dataflow-map.md) (base `9906dac5`; §8 = reviewer annotations)
**Base (interim):** `ta-anchor-goldens@a2f49ccf` — rebases onto `main` after goldens PR #1513 merges (see §11)
**Branch (to cut):** `ta-anchor-refactor-v2` (not yet created — git op described in §11, executed by Dean/coder, not the planner)
**Supersedes:** [`ta-anchor-refactor-plan.md`](ta-anchor-refactor-plan.md) (stored-`.Anchor`-field design; now `Status: SUPERSEDED`) and the abandoned commit `ta-anchor-refactor@34055d77`
**Companion:** [`ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) (PR-2, dependent — waits until this PR lands)
**Ship gate:** the characterization goldens from [`ta-anchor-goldens-plan.md`](ta-anchor-goldens-plan.md) must stay green at every commit (decision-SET-identity, keyed by VariantName).

---

## Reading Protocol

> **Agents:** do **not** read this file top-to-bottom. Read this Reading Protocol + the `## TOC`
> below, then fetch only the sections you need via `Read <file> offset:<start> limit:<end−start+1>`.
> Re-read the TOC after any structural edit (run `bash plans/scripts/toc-refresh.sh <file>`).

---

## TOC

- [§0 Deferred coder decisions (non-blocking)](#0-deferred-coder-decisions-non-blocking) L70:101
- [§1 Mission & the corrected model](#1-mission--the-corrected-model) L102:138
- [§2 The (a)/(b) split + the per-variant merge](#2-the-ab-split--the-per-variant-merge) L139:225
  - [Table 1 — per-variant fields (`VariantCapacity`)](#table-1--per-variant-fields-variantcapacity) L145:167
  - [Table 2 — model-level fields (`AnalyzerResult`)](#table-2--model-level-fields-analyzerresult) L168:186
  - [The per-variant merge + fallback ordering (the load-bearing correctness point)](#the-per-variant-merge--fallback-ordering-the-load-bearing-correctness-point) L187:225
- [§3 Scope & non-goals — what this PR does NOT touch](#3-scope--non-goals--what-this-pr-does-not-touch) L226:278
- [§4 Invariant #7 — the decision-set-identity ship gate](#4-invariant-7--the-decision-set-identity-ship-gate) L279:294
- [§5 Commit 1 — Phase 1: uniform generation + `Enabled` tag](#5-commit-1--phase-1-uniform-generation--enabled-tag) L295:374
  - [1a. Add the enablement tag to `NamedAnalyzerResult`](#1a-add-the-enablement-tag-to-namedanalyzerresult) L302:322
  - [1b. Uniform generation loop in `runAnalyzersAndScore`](#1b-uniform-generation-loop-in-runanalyzersandscore) L323:362
  - [1c. QM — no change in this commit](#1c-qm--no-change-in-this-commit) L363:374
- [§6 Commit 2 — Phase 2: `bindingAnchor` getter + `votingResults` + repoint](#6-commit-2--phase-2-bindinganchor-getter--votingresults--repoint) L375:531
  - [2a. Rename `saturationEntry` → `bindingAnchor`; new body](#2a-rename-saturationentry--bindinganchor-new-body) L385:421
  - [2b. New `votingResults` combine-ballot prune](#2b-new-votingresults-combine-ballot-prune) L422:439
  - [2c. Repoint the SELECTION sites (anchor)](#2c-repoint-the-selection-sites-anchor) L440:459
  - [2d. Repoint the COMBINE-BALLOT sites (`votingResults`)](#2d-repoint-the-combine-ballot-sites-votingresults) L460:473
  - [2e. Fixture updates (bounded — this is the E2 "likely moot" resolution)](#2e-fixture-updates-bounded--this-is-the-e2-likely-moot-resolution) L474:493
  - [2f. Tests (this commit)](#2f-tests-this-commit) L494:531
- [§7 Commit 3 — QM-as-error + liveness/do-nothing](#7-commit-3--qm-as-error--livenessdo-nothing) L532:608
  - [7a. QM-as-error (decision 1)](#7a-qm-as-error-decision-1) L538:577
  - [7b. Liveness / do-nothing (decision 2)](#7b-liveness--do-nothing-decision-2) L578:593
  - [7c-tests (this commit)](#7c-tests-this-commit) L594:608
- [§7b Commit 4 — TA-side proactive complement](#7b-commit-4--ta-side-proactive-complement) L609:728
  - [The gap](#the-gap) L616:624
  - [The fix — a second loop over `input.VariantStates`](#the-fix--a-second-loop-over-inputvariantstates) L625:676
  - [Why TA emits PRC only (and the resulting known limitation)](#why-ta-emits-prc-only-and-the-resulting-known-limitation) L677:692
  - [Interaction with the `[sat,TA]` bit-identity gate (Test 9)](#interaction-with-the-satta-bit-identity-gate-test-9) L693:707
  - [Test (this commit)](#test-this-commit) L708:728
- [§7c Partial scale-from-zero under `[TA]`-only / `[sat,TA]` — covered via §7b; sat-only deferred](#7c-partial-scale-from-zero-under-ta-only--satta--covered-via-7b-sat-only-deferred) L729:784
- [§8 Commit 5 — developer-guide](#8-commit-5--developer-guide) L785:827
- [§9 Semantic-pivot grep (mandatory)](#9-semantic-pivot-grep-mandatory) L828:854
- [§10 Read-site inventory — code-change areas from main](#10-read-site-inventory--code-change-areas-from-main) L855:943
  - [Struct / field](#struct--field) L861:869
  - [Phase 1 (`engine_v2.go: runAnalyzersAndScore`, ~:96-178)](#phase-1-enginev2go-runanalyzersandscore-96-178) L870:880
  - [Phase 2 (`analyzer_helpers.go`)](#phase-2-analyzerhelpersgo) L881:889
  - [Selection sites (→ `anchor := bindingAnchor(...)`)](#selection-sites--anchor--bindinganchor) L890:899
  - [Combine-ballot sites (→ `s := votingResults(req.AnalyzerResults)`)](#combine-ballot-sites--s--votingresultsreqanalyzerresults) L900:909
  - [QM / liveness (`engine.go`)](#qm--liveness-enginego) L910:920
  - [TA complement (`throughput/analyzer.go`)](#ta-complement-throughputanalyzergo) L921:930
  - [Fixtures (test-only, bounded)](#fixtures-test-only-bounded) L931:943
- [§11 Coordination — branch, goldens gate, PR-2 dependency](#11-coordination--branch-goldens-gate-pr-2-dependency) L944:975
- [§12 Deferrals & deletion classification](#12-deferrals--deletion-classification) L976:1020
- [§13 Reviewer verification checklist](#13-reviewer-verification-checklist) L1021:1048

## §0 Deferred coder decisions (non-blocking)

The old plan had a long §0 pinning a "copy mechanism" (variant (i)/(ii)) and a build-site. **All of
that is gone by construction** — this redesign has no stored `.Anchor` field, no clone helper, and
no engine-side build site. The anchor is derived on demand by the Phase-2 getter (§6). Only two real
discretion points remain:

1. **memoize-or-recompute.** The Phase-2 getter (`bindingAnchor`, §6) is called at every optimizer
   selection read-site (~10+ per model per cycle: `buildCapacityMap`, `allocateForModelPaired`,
   the six `rescale.go` sites, etc. — full list in §10). Recomputing the per-variant merge fresh at
   each call is O(variants) map-join — cheap, and the recommended default. **Assumption:** recompute
   each call. Memoizing once per `Optimize()` invocation is permitted as coder discretion *only if*
   the `-race`/perf pass shows it matters — but it must not change observable behavior, and it must
   not reintroduce a stored field on `ModelScalingRequest`.

2. **enablement-tag polarity (`Enabled` vs `Disabled`).** §5 specifies a new `Enabled bool` field on
   `NamedAnalyzerResult`, matching the review's language. This is fail-**closed**: a fixture that
   forgets to set it drops out of the combine ballot. The coder MUST therefore update the three
   central fixture builders + audit inline literals (§6 fixture step, §9 grep). If that fixture
   churn proves larger than the three helpers + a handful of literals, an equivalent fail-**safe**
   inversion (`Disabled bool`, default-false = voting) is acceptable as long as the Phase-1 loop sets
   the tag with the same truth table (§5) and `votingResults` prunes the correct entries. Pick one;
   do not ship both. Recommended: `Enabled bool` (matches spec + is self-documenting at read sites).

Everything else — the (a)/(b) field partition, the binding-selection rule, the QM disposition, the
liveness policy, the TA-side complement — is pinned below. Do NOT re-derive; implement as written and
assert in the tests (§5–§7b test blocks).

[↑ TOC](#toc)

---

## §1 Mission & the corrected model

**Goal (Dean, verbatim intent):** make WVA's saturation-v2 analyzer cleanly *disable-able* and make
ThroughputAnalyzer (TA) *enable-able* as a standalone or second analyzer **"with no special voting
code."** The three target configurations must all emerge from the enablement list alone, with **zero
change to the combine arithmetic**:

| Config (`analyzers:` list) | Behavior |
|---|---|
| *(empty / default)* → `[saturation]` | today's behavior, byte-identical decisions (goldens, §4) |
| `[saturation, throughput]` | both vote (pre-existing 2-entry combine, unchanged); sat is the single **anchor-binder**. Expected bit-identical to **main's `[sat,TA]`**, not to `[sat]` — see §3 / §2f Test 9. |
| `[throughput]` only | TA binds the anchor; sat present only as the identity/(a) carrier, does **not** vote |

**The corrected model (supersedes the stored-`.Anchor` design).** There is **no stored anchor field**.
Instead:

- **Phase 1 — generation** (`engine_v2.go: runAnalyzersAndScore`). Call every registered analyzer
  (saturation included, no name-special-casing at decision time). Each call yields one ballot entry
  tagged with its **enablement** (new `Enabled bool`) and **liveness** (existing `Live bool`). The
  engine makes **no** decisions here and builds no anchor.
- **Phase 2 — the binding/anchor getter** (`bindingAnchor`, successor to `saturationEntry`). Called
  on demand by the optimizers. It (1) finds saturation's entry as the **(a)/identity carrier**,
  (2) selects the **binding** analyzer (the (b)/sizing source), (3) builds a **fresh, per-variant
  merged** `*domain.AnalyzerResult` keyed by `VariantName`, (4) returns `nil` when nothing can bind
  (→ the optimizer holds for that model). Nothing is stored; the merge is recomputed on demand.

Why an anchor at all: the optimizers consume two *different* views of the ballot (§2). The selection
view (topology, per-variant capacity, cost-efficiency ranking) needs a single coherent per-variant
record with **both** identity (a) and sizing (b) fields populated. Saturation is the only analyzer
that always populates (a) for **every** configured variant (even zero-replica ones); TA may leave (a)
fields empty. The anchor merges sat's (a) with the binding analyzer's (b) so the selection view is
always complete regardless of which analyzer binds.

[↑ TOC](#toc)

---

## §2 The (a)/(b) split + the per-variant merge

The field partition is grounded in the real types: `domain.AnalyzerResult` and `domain.VariantCapacity`
([`internal/domain/analyzer.go:88-162`](../../Main/internal/domain/analyzer.go)). Implement these two
tables **verbatim** and assert every row in the §6 tests (test 1/2). Do not re-derive.

### Table 1 — per-variant fields (`VariantCapacity`)

| Field | Class | Source in the merge |
|---|---|---|
| `VariantName` | **key** | merge key (must match on both sides) |
| `AcceleratorName` | (a) identity | **saturation** |
| `Cost` | (a) identity | **saturation** |
| `Role` | (a) identity | **saturation** |
| `ReplicaCount` | (a) identity | **saturation** |
| `PendingReplicas` | (a) identity | **saturation** |
| `PerReplicaCapacity` | (b) sizing | **binding analyzer** |
| `Reason` | (b) sizing | **binding analyzer** |
| `TotalCapacity` | (b) derived | **recompute** = `ReplicaCount`(a) × `PerReplicaCapacity`(b) |
| `TotalDemand` | (b) sizing | **binding analyzer** |
| `Utilization` | (b) sizing | **binding analyzer** |

`TotalCapacity` is **recomputed** in the merge (not copied) so the consistency invariant
`anchor.TotalCapacity == anchor.ReplicaCount × anchor.PerReplicaCapacity` holds by construction. It
does hold across analyzers today (all analyzers derive `ReplicaCount` from the same `VariantStates`),
but recomputing removes any dependence on that coincidence. Assert this invariant in test 1.

[↑ TOC](#toc)

### Table 2 — model-level fields (`AnalyzerResult`)

| Field | Class | Source in the merge |
|---|---|---|
| `AnalyzerName` | identity | **binding analyzer** (recommended). **VERIFY** no behavioral read keys off `anchor.AnalyzerName` before finalizing — if any does, revisit; there is no known one. |
| `ModelID` | identity | saturation (== binding; same model) |
| `Namespace` | identity | saturation (== binding) |
| `AnalyzedAt` | identity | saturation |
| `VariantCapacities` | merged | the per-variant merge below |
| `TotalSupply` | (b) | binding analyzer |
| `TotalDemand` | (b) | binding analyzer |
| `Utilization` | (b) | binding analyzer |
| `TotalAnticipatedSupply` | (b) | binding analyzer |
| `RequiredCapacity` | (b) RC | binding analyzer (engine-written post-threshold; carried through) |
| `SpareCapacity` | (b) SC | binding analyzer |
| `RoleCapacities` | (b) | binding analyzer (nil when not disaggregated) |

[↑ TOC](#toc)

### The per-variant merge + fallback ordering (the load-bearing correctness point)

Build `anchor.VariantCapacities` by iterating **saturation's** variant list (the complete set — sat
emits every configured variant) and, for each `VariantName`:

1. take (a) fields from sat's entry for that name;
2. look up the **binding** analyzer's entry for the *same* `VariantName`;
   - if found → take (b) fields from it, recompute `TotalCapacity`;
   - **if not found → enablement-gated (b) fallback** (see the consistency rule below).

**(b)-fallback consistency rule (Dean 2026-08-05).** The (demand, PRC) pair for a variant must come
from a **single source** — never TA's demand paired with sat's PRC. sat's own (b) is therefore a valid
fallback **sizing** source **only when saturation is enabled** (it is then both the demand *and* the PRC
source, so the pair stays self-consistent). Per config:

| Config | (a) identity | (b) sizing | Fallback when the binding analyzer misses a variant |
|---|---|---|---|
| `[saturation]`-only | sat | sat | **trivial** — sat is both (a) and (b); the "merge" is sat's own result |
| `[sat,TA]` | sat | anchor/combine | **sat's own (b)** — valid (sat enabled); demand+PRC both from sat → consistent (this is the "anchor's PRC", never TA-demand×sat-PRC) |
| `[TA]`-only | sat | TA | **suppressed** — sat is the (a) carrier but **not** a (b) source; a variant with no TA (b) entry and no persisted TA PRC gets **PRC = 0 → not proactively selectable**; genuine cold-starts fall to the reactive `scalefromzero` engine |

§7b's persisted `lastPerReplicaSupply` gives a **previously-live-now-zero** variant a real TA (b) entry,
so under `[TA]`-only the fallback never fires for it — TA's own PRC is used, consistent. The fallback is
only "suppressed" for a **never-seen** variant (no TA history at all), which is exactly the cold-start
case the reactive net owns.

**Ordering rule (must not be violated):** where the fallback *does* fire (saturation enabled), it reads
sat's own entry, so it must run **before** any step that removes saturation from the voting set. When sat
is non-voting (`[TA]`-only) it is still the (a) carrier — pruning it first would make (a) vanish.
Concretely: `bindingAnchor` captures sat's entry up front (§6), then does the merge, and the
combine-ballot prune (`votingResults`, §6) is a **separate** operation on a **separate** slice — the
anchor build never consults the pruned slice. Test 2 asserts a case where sat is non-binding *and*
the binding analyzer is missing a variant, proving the fallback behaves per the table above (resolves
from sat when sat is enabled; yields PRC=0 under `[TA]`-only).

[↑ TOC](#toc)

---

## §3 Scope & non-goals — what this PR does NOT touch

**In scope (this PR):**

- Phase-1 uniform generation + the `Enabled` tag (Commit 1, §5).
- Phase-2 `bindingAnchor` getter + per-variant merge + `votingResults` combine-ballot prune +
  repointing every read site (Commit 2, §6).
- QM-as-error dispatch refusal + liveness/do-nothing policy (Commit 3, §7).
- TA-side proactive complement — emit the already-persisted `lastPerReplicaSupply` (real TA PRC) for a
  **previously-live-now-zero** variant so it stays a selectable scale-from-zero candidate. Cost /
  AcceleratorName are (a)-identity fields from saturation, **not** TA's to emit — TA emits PRC only. A
  **never-seen** variant gets no TA (b) entry (PRC=0, not proactively selectable under `[TA]`-only); the
  reactive `scalefromzero` engine covers genuine cold-starts (Commit 4, §7b).
- Developer-guide updates (Commit 5, §8).

**Explicitly NOT in scope (deferred / separate — do not design into a commit):**

- **The combine arithmetic is unchanged.** `initRoleState`, `fairShareValue`, `applyAllocation`,
  `scaleDownRoleIterated` keep their exact math. The only thing that changes for combine is *which
  entries are in the ballot* (pruned to voting via `votingResults`), not how they combine.
  - **Default (`[saturation]`) path:** `votingResults` returns the same single entry as today and the
    combine math is untouched → decisions are bit-identical, and **this is what the #1513 goldens
    prove** (§4). The goldens cover the default path *only*.
  - **`[sat,TA]` path:** both analyzers already vote today (this is the **pre-existing 2-entry
    combine**, unchanged). "PR-1 single-vote" in the §1 table refers to a single **anchor-binder**
    (sat binds the anchor's (b)), **not** a single combine entry — the ballot genuinely has two voting
    entries and `votingResults` returns both. So `[sat,TA]` decisions are expected bit-identical to
    **main's `[sat,TA]`** (not to `[sat]`), because the refactor changes zero combine arithmetic and
    `votingResults` returns the same set. **The goldens do NOT prove this** — they are sat-only. The
    regression backstop for `[sat,TA]` is the dedicated characterization test added in §2f (Test 9),
    not the goldens.
  - **`[TA]`-only path:** the only config where the combine *set* differs from main (sat is pruned out
    of the ballot) — new capability, not a goldens regression.
- **Partial scale-from-zero for `[saturation]`-only (TA absent)** — the pre-existing sat-v2 gap (sat's
  own `aggregateByVariant` not backfilling a per-variant cost for zero-replica variants) is NOT fixed
  here (Dean 2026-08-05: fix `[TA]`-only / `[sat,TA]` now, open an issue on sat-only later — §12). The
  TA-enabled configs **are** handled in this PR via §7b (all-variants fallback), without any picker code
  change; only the TA-absent path is deferred. See §7c.
- **`AnalyzerName` validation gap** (§2.3-3) — the unconstrained `AnalyzerName` field + the silent
  `default:`→`optimizeV1` dispatch fallback ([engine.go:557](../../Main/internal/engines/saturation/engine.go#L557)).
  Separate small standalone PR, not a 0.9 requirement. Recorded in §12.
- **sat-v2's own `aggregateByVariant` Cost/`AcceleratorName` no-persistence bug** — pre-existing,
  present in sat independent of TA or this refactor. Separate small fix. Recorded in §12.
- **Multi-vote refresh / dynamic re-binding across cycles, `ReplicaCount`-tracks-binding (F10),
  rescale TA-only *correctness* (F11 beyond the read-source wiring), masked bugs #1/#2/#3/#5** —
  all PR-2 (`ta-anchor-dynamic-refresh`).
- **The `scalefromzero` engine** — orthogonal; has no `Anchor`/`AnalyzerResult`/`pipeline` reference;
  untouched.

[↑ TOC](#toc)

---

## §4 Invariant #7 — the decision-set-identity ship gate

The characterization goldens shipped in **PR #1513** ([`ta-anchor-goldens-plan.md`](ta-anchor-goldens-plan.md))
freeze the default sat-only path's **decision SET identity, keyed by `VariantName`**. Every commit in
this PR must keep those goldens green **independently** — run them after each commit, not just at the
end. This is the backstop that proves "zero combine-arithmetic change" for the default path is real,
not asserted. Test 8 (§6) is this gate.

The goldens key by `VariantName` (not slice order) precisely because this refactor makes ballot order
irrelevant — a positional golden would break spuriously. If a commit turns a golden red, the refactor
changed observable default-path behavior and the commit is wrong; do not "re-bless" the golden.

[↑ TOC](#toc)

---

## §5 Commit 1 — Phase 1: uniform generation + `Enabled` tag

**Files:** `internal/engines/pipeline/optimizer_interfaces.go`,
`internal/engines/saturation/engine_v2.go`.
**Goal:** every analyzer produces one status-tagged ballot entry; the engine makes no decisions and
builds no anchor. Default path stays a single `[sat(Enabled)]` ballot → goldens green.

### 1a. Add the enablement tag to `NamedAnalyzerResult`

- [`optimizer_interfaces.go:36`](../../Main/internal/engines/pipeline/optimizer_interfaces.go#L36) —
  add a field immediately after `Live bool`:
  ```go
  // Enabled indicates the analyzer votes in the combine (RC/SC) math for this cycle.
  // Saturation is present as the identity/(a) carrier even when it does not vote
  // (e.g. an [throughput]-only config), so "present in the ballot" ≠ "votes".
  // Set by the engine each cycle (Phase 1). votingResults() prunes the ballot to
  // Enabled entries before combine math; the anchor build (bindingAnchor) reads the
  // full ballot so a non-voting saturation entry can still supply (a)/fallback (b).
  Enabled bool
  ```
- [`optimizer_interfaces.go:44`](../../Main/internal/engines/pipeline/optimizer_interfaces.go#L44) —
  the field comment on `AnalyzerResults` says `// per-analyzer slice; saturation entry is always
  first`. **Behavioral-contract change:** order is no longer load-bearing. Replace with
  `// per-analyzer slice; order is not significant (see bindingAnchor / votingResults)`. This is a
  semantic-pivot cross-reference — §9 lists the grep that catches its siblings.

[↑ TOC](#toc)

### 1b. Uniform generation loop in `runAnalyzersAndScore`

Current shape ([`engine_v2.go:96-178`](../../Main/internal/engines/saturation/engine_v2.go)): sat is
run via `runV2AnalysisOnly`, appended first unconditionally (~:140-148, no `Enabled`), then a non-sat
loop (~:149-171) with three `continue` guards — sat-name reuse-guard (~:150-152), `!effectiveEnabled`
(~:153-155), nil-result (~:157-159) — then `updateLivenessAndSetLive` (~:172).

Changes:

- Before the sat append, compute the saturation-votes predicate:
  ```go
  satVotes := len(config.Analyzers) == 0 || effectiveEnabled(domain.SaturationAnalyzerName, config)
  ```
  Rationale (verified against `ApplyDefaults` + `effectiveEnabled`): `ApplyDefaults`
  ([`config/saturation_scaling.go:296-301`](../../Main/internal/config/saturation_scaling.go#L296))
  injects `[{saturation,1.0,Enabled:true}]` when the list is empty, so the defaulted runtime config
  yields `satVotes=true`. But unit/test configs frequently skip `ApplyDefaults` and leave the list
  empty — the `len(...)==0` disjunct keeps those defaulting to sat-votes too. `effectiveEnabled`
  returns `false` for a name **absent** from a non-empty list, so `[throughput]`-only correctly gives
  `satVotes=false`.
- The saturation entry is **still always appended** (it is the (a) carrier), now tagged
  `Enabled: satVotes`.
- **Keep** the sat-name reuse-guard `continue` in the non-sat loop — it prevents double-appending sat
  and re-running its analysis; it is a reuse guard, **not** a decision gate. (Do not delete it: that
  was the load-bearing name-skip. Its docstring says it is a reuse guard, keep that framing.)
- **Keep** the nil-result `continue` (a dead analyzer contributes no ballot entry — see the
  liveness discussion in §7; an entry that never ran has no (b) to offer).
- Enabled non-sat entries get `Enabled: true`. Disabled non-sat entries: **coder discretion** whether
  to append-with-`Enabled:false` or skip via the existing `!effectiveEnabled` `continue`. Skipping is
  simpler and safe *for non-sat analyzers* — the only entry that must survive-when-non-voting is
  **saturation** (the (a) carrier). A disabled non-sat analyzer has no (a) role, so omitting it is
  fine. Recommended: keep the `!effectiveEnabled` skip for non-sat; only sat is special-cased to
  survive as the carrier.
- The sat-error path is unchanged: `runV2AnalysisOnly` error → `return nil, err`
  (~:113) → routed to per-model hold upstream (§7). Do not convert this to a tagged entry.
- Update the `runAnalyzersAndScore` docstring (~:90-95) to describe the tag semantics and drop any
  "saturation is always first / special" language (semantic-pivot; §9).

[↑ TOC](#toc)

### 1c. QM — no change in this commit

The QM refusal lives in `engine.go`'s dispatch switch (§7), outside `engine_v2.go`. Nothing to do here.

**Test (goldens):** after this commit the default path is still a one-entry `[sat(Enabled:true)]`
ballot; run the #1513 goldens — must be green (test 8). No new unit test is required for Commit 1
alone; the tag is exercised by Commit 2's tests.

[↑ TOC](#toc)

---

## §6 Commit 2 — Phase 2: `bindingAnchor` getter + `votingResults` + repoint

**Files:** `internal/engines/pipeline/analyzer_helpers.go`,
`internal/engines/pipeline/cost_aware_optimizer.go`,
`internal/engines/pipeline/greedy_score_optimizer.go`,
`internal/engines/pipeline/rescale.go`, plus test fixtures
(`cost_aware_optimizer_test.go`, `analyzer_helpers_test.go`).
**Goal:** derive the anchor on demand, prune the combine ballot to voting entries, and repoint every
read site. This is the largest commit; the read-site inventory is §10.

### 2a. Rename `saturationEntry` → `bindingAnchor`; new body

- [`analyzer_helpers.go:87-98`](../../Main/internal/engines/pipeline/analyzer_helpers.go#L87) —
  rename `saturationEntry(s []NamedAnalyzerResult) *domain.AnalyzerResult` →
  `bindingAnchor(s []NamedAnalyzerResult) *domain.AnalyzerResult` (**same signature**, so call-site
  churn is limited to the name + variable rename). New body:

  1. **Find the (a) carrier:** scan `s` for `e.Name == domain.SaturationAnalyzerName` with a non-nil
     `Result`; call it `satNR`. (May be present even when `!satNR.Enabled`.) **Reader-note:** `satNR.Live`
     is populated for *every* ballot entry (sat included) by the existing `updateLivenessAndSetLive`
     pass at the end of Phase 1 (`engine_v2.go:~172`, §5 1b) — sat is **not** exempt from liveness
     tagging, so the `satNR.Live` read in step 2 is always meaningful. (The default-path goldens
     enforce this indirectly: sat binds only because its `Live` is set true.)
  2. **Select the binding analyzer** (the (b)/sizing source), by this rule:
     - if `satNR != nil && satNR.Enabled && satNR.Live && ResultIsInformative(satNR)` → **binding = sat**
       (this is the default and `[sat,TA]` case — sat binds whenever it votes, which is why the
       goldens hold: merging sat-with-itself is the identity);
     - else scan for an enabled + live + informative **non-sat** entry → **binding = that entry**
       (the `[TA]`-only case). PR-1 supports exactly one binding candidate here; if the config somehow
       yields more than one enabled+live+informative non-sat analyzer (not a PR-1 config — see §3),
       that is PR-2 territory: pick deterministically is NOT specified — instead treat it as unbindable
       and return nil (hold) rather than guess. Log at a level the coder deems appropriate. Record in
       §12 as a PR-2 item.
     - else → **return nil** (no binding vote → the optimizer holds for this model; §7 liveness).
  3. **Build the merged anchor** per §2: fresh `*domain.AnalyzerResult`, model-level fields per
     Table 2, `VariantCapacities` by iterating `satNR`'s variant list and merging (a) from sat + (b)
     from binding per `VariantName`, with the per-variant fallback to sat's own (b) when binding lacks
     that variant. Recompute `TotalCapacity`. **Build fresh literals — never mutate `satNR.Result`,
     `binding.Result`, or their `VariantCapacities` slices/elements** (the aliasing guard; test 3).
  4. Return the fresh anchor.

  Delete the old docstring's "keeper of per-variant metadata / TODO: remove the sat_v2 special role"
  framing (the special role is now gone). Replace with a docstring describing the merge + fallback +
  ordering rule.

[↑ TOC](#toc)

### 2b. New `votingResults` combine-ballot prune

- In `analyzer_helpers.go`, add:
  ```go
  // votingResults returns the sub-slice of the ballot whose analyzers vote in the
  // combine (RC/SC) math this cycle. Non-voting entries (e.g. a saturation entry that
  // is present only as the (a) carrier in an [throughput]-only config) are excluded.
  // The anchor build (bindingAnchor) reads the FULL ballot, not this pruned view.
  func votingResults(s []NamedAnalyzerResult) []NamedAnalyzerResult { /* filter e.Enabled */ }
  ```
  In the default and `[sat,TA]` configs this returns the same entries as `s` (all Enabled) → the
  combine input set is unchanged from main. In the default path that identity is proven by the #1513
  goldens (§4); in `[sat,TA]` it is an argument-from-unchanged-code (goldens do **not** cover
  `[sat,TA]`), backstopped by the §2f Test 9 characterization test. In `[TA]`-only it drops the
  non-voting sat entry (the one config where the combine set differs — new capability).

[↑ TOC](#toc)

### 2c. Repoint the SELECTION sites (anchor)

Every current `satEntry := saturationEntry(...)` becomes `anchor := bindingAnchor(...)`, and every
`satEntry.VariantCapacities` / `satEntry.TotalDemand` / `satEntry.RoleCapacities` read becomes the
`anchor.*` equivalent. The full site list is §10. Notable:

- `cost_aware_optimizer.go` — `:48` getter, `:49-51` nil-guard (`if anchor == nil { continue }` —
  this is the per-model hold, §7), `:54` `buildCapacityMap(anchor.VariantCapacities)`, `:62`
  `allocateForModelPaired(..., anchor.VariantCapacities, ...)`, `:65` `scaleDownRoleIterated(...,
  anchor.VariantCapacities, ...)`, `:256` (second selection use).
- `greedy_score_optimizer.go` — the `modelWork.satEntry` field (`:46`) → `anchor`; getters at
  `:125`/`:158`; `buildCapacityMap` at `:149`/`:164`; `scaleDownRoleIterated` at `:170`.
- `rescale.go` — six sites, all selection-source (topology / `RoleCapacities` / `TotalDemand`):
  `:225`, `:342-371`, `:465-471`, `:486-521`, `:589-595`, `:604-610`. Helpers `modelDemandGPUs` /
  `roleDemandGPUs` take a `satEntry *domain.AnalyzerResult` parameter — rename the parameter to
  `anchor` for clarity (cosmetic, but do it so no "sat" naming survives that would mislead a later
  reader; §9 grep enforces).

[↑ TOC](#toc)

### 2d. Repoint the COMBINE-BALLOT sites (`votingResults`)

Every `s := req.AnalyzerResults` that feeds combine math becomes `s := votingResults(req.AnalyzerResults)`:

- `cost_aware_optimizer.go:59`.
- `greedy_score_optimizer.go:130`, `:168`.
- `rescale.go:365` — `reclaimRole(ctx, req.AnalyzerResults, ...)` passes the raw ballot as a combine
  input → `reclaimRole(ctx, votingResults(req.AnalyzerResults), ...)`.
- **Exhaustiveness:** the coder MUST `grep -rn "AnalyzerResults" internal/engines/pipeline/` and
  confirm every combine-consuming site is repointed and every selection-consuming site goes through
  `bindingAnchor`. Do not rely on this list being complete — the grep is the backstop (§9).

[↑ TOC](#toc)

### 2e. Fixture updates (bounded — this is the E2 "likely moot" resolution)

The old fold-in touched ~87 sites because the stored-`.Anchor` design forced every fixture to populate
a new field threaded through `collectV2ModelRequest`. **This redesign has no stored field**, so the
getter reads the same `req.AnalyzerResults` slice the fixtures already build. The only fixture change
is the `Enabled` tag (§0 item 2), and it is concentrated in **three central builders**:

- [`cost_aware_optimizer_test.go:16`](../../Main/internal/engines/pipeline/cost_aware_optimizer_test.go#L16)
  `withSatEntry` — add `Enabled: true` to the constructed `NamedAnalyzerResult` (1 line).
- [`analyzer_helpers_test.go:14`](../../Main/internal/engines/pipeline/analyzer_helpers_test.go#L14)
  `makeNamed` — add `Enabled: true` (1 line).
- [`analyzer_helpers_test.go:117`](../../Main/internal/engines/pipeline/analyzer_helpers_test.go#L117)
  `makeNamedPD` — add `Enabled: true` (1 line).

Then `grep -rn "NamedAnalyzerResult{" internal/engines/pipeline/*_test.go` for **inline literals**
that construct entries directly (not via the three helpers); add `Enabled: true` to each that the
test intends to vote. This is the complete fixture scope — a handful of lines, not 87.

[↑ TOC](#toc)

### 2f. Tests (this commit)

- **Test 1 — merged-anchor construction (non-vacuous).** Pipeline-package fixture with a two-entry
  ballot: a sat entry + a distinct binding-analyzer entry for the **same** `VariantName`, with
  deliberately different (b) values. Assert the merged anchor takes (a) from sat and (b) from the
  binding analyzer per variant, and that `anchor.TotalCapacity == ReplicaCount × PerReplicaCapacity`.
  **Fixtures must make anchor ≠ ballot[0]** (the E5 vacuity trap — prove the classification, don't
  self-satisfy it).
- **Test 2 — per-variant fallback + ordering.** Binding analyzer missing an entry for one variant →
  anchor falls back to sat's (b) for that variant; and construct the case so sat's own entry is
  **non-binding** (would be pruned by `votingResults`) yet the fallback still resolves — proving the
  fallback source is captured before any prune.
- **Test 3 — no stored-result mutation.** Assert the source sat/binding `Result` structs and their
  `VariantCapacities` are unchanged after `bindingAnchor` runs (aliasing guard). Holds by construction
  (fresh literals); the test locks it in.
- **Test 6 — rescale reads the merged anchor (F11 read-source).** A `[TA]`-binding anchor with rescale
  enabled: assert the rescale path resolves `AcceleratorName` via the anchor even though TA's own
  result leaves it empty (it comes from sat's (a) through the merge). This is a characterization test
  of the read-source wiring so a later change can't silently repoint it; rescale TA-only *correctness*
  stays PR-2.
- **Test 9 — `[sat,TA]` combine characterization (the V5 backstop; goldens do NOT cover this).**
  A two-voting-entry ballot (`saturation` + `throughput`, both `Enabled`), exercised through the full
  combine path (`votingResults` → `initRoleState`/`fairShareValue`/`applyAllocation`). Freeze the
  resulting decision SET (keyed by `VariantName`, same shape as the #1513 goldens) as this test's
  expectation. Purpose: the #1513 goldens prove only the sat-only default path is unchanged; nothing
  else proves the `[sat,TA]` path is bit-identical to main. This test is that proof — it must stay
  green at every commit, and if a later change perturbs the `[sat,TA]` combine it fails loudly. Build
  the expectation from the **current (pre-refactor) main** behavior for the same fixture so it is a
  true characterization, not a re-blessing of the refactored output. **Fixture constraint: every
  variant must be live (≥1 replica)** so the §7b all-variants fallback (Commit 4) is a no-op for this
  fixture — otherwise Commit 4 legitimately adds zero-replica candidates to TA's ballot and would break
  the bit-identity this test freezes (see §7b "Interaction with the `[sat,TA]` bit-identity gate").
- **Test 8 — goldens (#1513) green.** Run after this commit.

[↑ TOC](#toc)

---

## §7 Commit 3 — QM-as-error + liveness/do-nothing

**File:** `internal/engines/saturation/engine.go`.
**Goal:** enabling the queueing-model path is an explicit refusal (never a silent sat-v2 or V1
fallback); and "no analyzer can bind for a model" holds that model at its last-good replicas.

### 7a. QM-as-error (decision 1)

**When this case fires (verify before writing).** The QM path is **not** activated by the `analyzers:`
list — it is activated by the *presence* of a queueing-model ConfigMap. `analyzerName` is set to
`domain.QueueingModelAnalyzerName` at [`engine.go:522-524`](../../Main/internal/engines/saturation/engine.go#L522)
guarded by `hasQMAnalyzerConfig` ("ConfigMap takes priority over saturation analyzerName"), and that
name then routes the dispatch switch below. So the refusal must sit in the **dispatch case body** (it
fires whenever the ConfigMap selects QM); it must **not** be gated on the `analyzers:` list, or a
QM-ConfigMap deployment would slip past the refusal. Confirm `hasQMAnalyzerConfig` is still the sole
activation trigger before finalizing.

- [`engine.go:553-554`](../../Main/internal/engines/saturation/engine.go#L553) — the dispatch switch
  case:
  ```go
  case domain.QueueingModelAnalyzerName:
      allDecisions = e.optimizeQueueingModel(ctx, modelGroups, currentAllocations)
  ```
  Replace the body with a call to a **new** `refuseQueueingModel`:
  ```go
  case domain.QueueingModelAnalyzerName:
      allDecisions = e.refuseQueueingModel(ctx, modelGroups, currentAllocations)
  ```
  `refuseQueueingModel` logs an **Error** ("queueing-model optimization path is disabled; refusing to
  dispatch — enable the saturation and/or throughput analyzers instead") and returns **empty
  decisions**. It does NOT call `optimizeQueueingModel` and does NOT fall through to `optimizeV1`. The
  existing unconditional `applySaturationDecisions(ctx, allDecisions, ...)` at
  [`engine.go:571`](../../Main/internal/engines/saturation/engine.go#L571) then runs with zero
  decisions → preserves each VA's last-good `Status.DesiredOptimizedAlloc.NumReplicas` and still emits
  the HPA/KEDA metric every cycle. (This is the same hold mechanism as decision 2; no new plumbing.)
  - `emitSafetyNetMetrics` is an alternative idiom, but returning empty decisions through the existing
    `:571` path already achieves the hold + metric emission — prefer it (less new code). Coder may use
    `emitSafetyNetMetrics` instead if it reads cleaner, but must not do both.
- **Do NOT touch** `modeLabelForAnalyzer` at [`engine.go:586`](../../Main/internal/engines/saturation/engine.go#L586)
  — that switch only produces a log label and is benign under refusal.
- **Classification:** DEFERRED (not deprecated). The QM analyzer is a real design intent parked until
  the multi-analyzer engine contract can host it (F10). §12 records this and flags the GitHub-issue
  question for Dean.

[↑ TOC](#toc)

### 7b. Liveness / do-nothing (decision 2)

Mostly **pre-existing** — verify and lean on it, don't reinvent:

- `optimizeV2`'s per-model loop already catches a sat-analysis error and holds that model via
  `emitSafetyNetMetrics` ([`engine.go:~1002`](../../Main/internal/engines/saturation/engine.go#L1002),
  "Strategy 1: use previous desired-replicas value if available").
- `applySaturationDecisions` re-affirms the last-good `NumReplicas` every cycle for any VA without a
  fresh decision (confirmed).
- **The only NEW hold path** is the one introduced in Commit 2: `bindingAnchor` returns `nil` (no
  enabled+live+informative binding vote) → the optimizer's `if anchor == nil { continue }` skips that
  model → no decision → the `:571` path holds it. No engine.go change is needed for this beyond what
  Commit 2 already did; §7 only needs to *document* it and test it.

[↑ TOC](#toc)

### 7c-tests (this commit)

- **Test 4 — empty / no-live-analyzer ballot is graceful.** A model whose ballot has no
  enabled+live+informative analyzer produces **no decision** (never an index panic — the E4
  empty-ballot regression), `applySaturationDecisions` preserves the prior
  `Status.DesiredOptimizedAlloc.NumReplicas`, **and** still emits the HPA/KEDA scaling metric. Assert
  replicas unchanged + metric emitted.
- **Test 5 — QM-as-error backstop.** Enabling the QM path produces the explicit refusal (Error +
  hold), **not** a silent nil-anchor drop and **not** a silent fall-through to `optimizeV1`. A
  regression test that fails loudly if QM is silently accepted or routed to V1.

[↑ TOC](#toc)

---

## §7b Commit 4 — TA-side proactive complement

**File:** `internal/engines/analyzers/throughput/analyzer.go`. Orthogonal to the anchor mechanism;
bundled into this PR per Dean's decision. This is the *proactive* answer to "a variant that went to
zero can scale back up under `[TA]`-only" (complementing `scalefromzero`'s *reactive* path). The review
designed this to near-patch level (Part 2 §2.5); implement as written.

### The gap

`Analyze()`'s only per-variant loop is `for variantName, variantMetrics := range byVariant` where
`byVariant := groupByVariant(input.ReplicaMetrics)` (~`analyzer.go:262`). A variant with 0 replicas
contributes 0 rows and is never a key → the loop never runs for it → TA emits **nothing** for that
variant.

[↑ TOC](#toc)

### The fix — a second loop over `input.VariantStates`

`variantState` already persists `lastPerReplicaSupply` (~`analyzer.go:50`), set every cycle a
per-variant computation succeeds (~:319-322), currently read only by `VariantState()` introspection.
The precedent for "persist a last-good value across cycles, distinct from workload-shape state that
gets cleared" is `lastFittedB` (~:37-40). **No new struct field is needed** — this commit *reuses* the
existing `lastPerReplicaSupply`.

> **Design correction (Dean 2026-08-05).** The earlier design added persisted `lastCost` /
> `lastAcceleratorName` and a `fallbackVariantCost` MAX sentinel. **Both are removed.** `Cost` and
> `AcceleratorName` are **(a)-identity fields sourced from saturation** in the merge (§2 Table 1) — not
> TA's to emit or persist. "lastPRC is real"; a last-cost persisted by TA is not. TA emits **PRC only**
> for its scale-from-zero complement; (a) (including `Cost`) comes from sat's entry via the anchor merge.

1. **Struct change — none.** Reuse `lastPerReplicaSupply`, already set at the success site (~:319-322).
2. **Second loop** — after the existing `byVariant` loop, iterate `input.VariantStates` and emit a
   **PRC-only** capacity for a previously-live variant now at zero replicas:
   ```go
   for _, vs := range input.VariantStates {
       if _, alreadyHandled := byVariant[vs.VariantName]; alreadyHandled {
           continue // has live replicas — the existing loop covered it
       }
       key := variantKey(input.Namespace, input.ModelID, vs.VariantName)
       st, ok := a.variantStates[key]
       if !ok || st.lastPerReplicaSupply <= 0 {
           continue // NEVER-SEEN: no TA history → emit nothing.
                    // PRC=0 ⇒ not proactively selectable under [TA]-only;
                    // the reactive scalefromzero engine covers genuine cold-starts.
       }
       // PREVIOUSLY-LIVE: emit the persisted last-good PRC so the variant stays a
       // selectable scale-from-zero candidate. Emit PRC ONLY — Cost / AcceleratorName /
       // Role / ReplicaCount are (a)-identity fields the anchor merge (§2) takes from
       // saturation's entry for this variant, not TA's to set.
       // append VariantCapacity{VariantName: vs.VariantName,
       //                        PerReplicaCapacity: st.lastPerReplicaSupply, ...}
   }
   ```
3. **No cost sentinel.** The earlier design plugged a large `fallbackVariantCost` constant so a
   never-seen variant would rank last while staying selectable. That is **removed**: a never-seen
   variant is not something TA can size or price, so TA emits nothing for it and it is not proactively
   selectable — the honest outcome, and it avoids fabricating a cost (the "hack to bypass an existing
   bug" Dean rejected). The real per-variant CRD-spec cost is deliberately not plumbed here (see §12).
4. **Coverage.** `input.VariantStates` is built by `BuildVariantStates`
   ([`saturation/engine.go:1064`](../../Main/internal/engines/saturation/engine.go#L1064)), which
   enumerates the **full** VA list — zero-replica variants included. So this second loop reaches every
   variant, and emits a real-PRC (b) for exactly those that were previously live (have a persisted
   `lastPerReplicaSupply`). Same eviction window as `lastFittedB` / `lastPerReplicaSupply` (entries
   evicted after `2×DefaultObservationMaxAge`, ~60 min idle) — so a long-idle variant's persisted PRC
   self-expires and it degrades to the never-seen (not-selectable) case with no extra logic.

[↑ TOC](#toc)

### Why TA emits PRC only (and the resulting known limitation)

`Cost` and `AcceleratorName` are **(a)-identity fields the merge takes from saturation** (§2 Table 1) —
not TA's to emit. So TA's scale-from-zero emission carries a real PRC and leaves (a) to sat. The
consequence, under `[TA]`-only: for a previously-live-now-zero variant, `Cost` comes from sat's (a),
which is **0** for a zero-replica variant (the pre-existing sat `Cost=0` bug — §12, *not ours*). Then
`costEfficiency = Cost / PRC = 0 / PRC = 0`
([`cost_aware_optimizer.go:234-239`](../../Main/internal/engines/pipeline/cost_aware_optimizer.go)),
so the returning variant ranks **cheapest** and is picked first on scale-up. **This is an accepted,
documented known limitation, not something PR-1 gates on** (Dean 2026-08-05: "`[TA]`-only now behaves
like `[sat]`-only — same limit until the bug is fixed. Document, don't gate. We fix it by fixing the sat
`Cost=0` bug"). Scale-from-zero still *functions* (the variant is selected — if anything, eagerly); only
cost-*priority* is affected. Full net-effect analysis and disposition are in §7c.

[↑ TOC](#toc)

### Interaction with the `[sat,TA]` bit-identity gate (Test 9)

The second loop only emits for variants **absent from `byVariant`** — i.e. variants at **zero live
replicas** this cycle. Under `[sat,TA]`, those emissions enter TA's ballot entry and thus the combine.
To keep Test 9 (§2f — `[sat,TA]` bit-identical to main) valid, **Test 9's fixture must have every
variant live (≥1 replica)**, so this loop `continue`s all of them and emits nothing extra → the combine
ballot is unchanged → bit-identity holds. The new scale-from-zero behavior (a previously-live
zero-replica variant entering the ballot with its persisted real PRC) is exercised by the dedicated
scale-from-zero test below
(Test 10), **not** by Test 9. **Coder gate:** run Test 9 after this commit — if it goes red, the fixture
has a zero-replica variant and either the fixture must be made all-live or the perturbation investigated;
it must not silently change the frozen `[sat,TA]` decisions.

[↑ TOC](#toc)

### Test (this commit)

- **Test 7 — TA-side PRC-only self-fallback + eviction.** (a) a **previously-live** variant now at
  zero → TA emits a `VariantCapacity` whose `PerReplicaCapacity` is the persisted `lastPerReplicaSupply`
  and which carries **no** TA-sourced `Cost`/`AcceleratorName` (those are (a) from sat via the merge —
  assert TA does not set them). (b) a **never-seen** variant (no persisted PRC) → TA emits **nothing**
  for it (assert no capacity is produced; under `[TA]`-only its effective PRC is 0 → not selectable).
  Plus eviction: after the `2×DefaultObservationMaxAge` (~60 min) idle window the persisted entry is
  gone and a previously-live variant degrades to the never-seen (no-emission) case on its own.
- **Test 10 — scale-from-zero selection under `[TA]`-only.** End-to-end proof that scale-from-zero
  *functions*: a model with unmet demand and a **previously-live-now-zero** variant (persisted
  `lastPerReplicaSupply` > 0) as the viable capacity source → the optimizer selects it and raises its
  replica count above zero (PRC > 0 keeps it a candidate). Complements Test 7 (which proves the
  *emission*); Test 10 proves the *picker acts on it*. Note the §7c cost-priority caveat (the returning
  variant may be picked *eagerly* because sat's (a) gives it `Cost=0`) — Test 10 asserts *selection*,
  not cost-optimal ranking. Distinct from Test 9 (all-live, no scale-from-zero event).

[↑ TOC](#toc)

---

## §7c Partial scale-from-zero under `[TA]`-only / `[sat,TA]` — covered via §7b; sat-only deferred

Scale-from-zero and partial scale-from-zero **are addressed in this PR for the configs that enable TA**
(`[TA]`-only and `[sat,TA]`), per Dean (2026-08-05) — via the §7b complement, **not** via any picker
code change (the picker is unmodified; the fix is upstream — TA now emits a complete, non-inverting
(PRC, cost) for every variant).

- **Previously-live variants get a real-PRC fallback.** §7b's second loop iterates
  `input.VariantStates` (the full VA list from `BuildVariantStates`, zero-replica variants included) and
  emits the persisted `lastPerReplicaSupply` (real TA (b)) for every variant that was previously live —
  keeping it a selectable scale-from-zero candidate. `Cost`/`AcceleratorName` are **not** TA-emitted;
  they are (a)-identity from saturation via the merge (§2). A **never-seen** variant gets no TA (b)
  entry → PRC=0 → not proactively selectable under `[TA]`-only.
- **Known limitation — `[TA]`-only now behaves like `[sat]`-only (accepted; document, don't gate).**
  Because `Cost` is sat's (a) and sat emits `Cost=0` for a zero-replica variant (the pre-existing sat
  `Cost=0` bug — §12, *not ours*), a returning previously-live variant has
  `costEfficiency = 0/PRC = 0` and ranks **cheapest**, so the picker chooses it first on scale-up. This
  is the *same* mis-ranking `[sat]`-only already has (Dean 2026-08-05: "same limit until the bug is
  fixed"). Net effect:
  - **Scale-from-zero still functions** — the variant *is* selected (in fact eagerly). §7b's core value
    (proactive return of a previously-live variant) is intact; only cost-*priority* is affected.
  - **Flap** — if load then dips to create spare, scale-down sheds the most-expensive first (now the
    returned variant, once its real cost is revealed) → back to zero → `Cost=0` again → next rise
    re-picks it. Sustains only while load oscillates across the up/down boundary; no damping exists in
    the cost optimizer to suppress it.
  - **Stuck-suboptimal** — if load stays high enough that the extra replica is genuinely needed, it is
    never shed (`safeRemovalReplicasForRole` returns 0 with no spare) → a persistent costlier
    allocation, silent, no self-correction.
  Both are the **sat `Cost=0` bug's** effect and are resolved when the separate sat fix lands — **not** a
  hard dependency of PR-1 (Dean: "we fix by fixing the sat cost=0 bug").
- **`scalefromzero` remains the reactive net.** The existing `scalefromzero` engine still covers
  scale-from-zero *reactively* today (per-VA `isInactive` check, no model-level pre-filter); it is
  orthogonal to the anchor mechanism and unchanged. §7b is the *proactive* complement, and it is the
  **only** proactive path for a never-seen variant under `[TA]`-only (which §7b leaves unselectable).
- **The sat `Cost=0` bug is out of scope (separate PR — "not ours").** sat's own `aggregateByVariant`
  never backfills a per-variant `Cost`/`AcceleratorName` for a zero-replica variant, so `[saturation]`-only
  has always mis-ranked returning variants — and, per the known limitation above, `[TA]`-only now inherits
  the same behavior (since `Cost` is sat's (a)). Dean (2026-08-05): "the satv2 cost=0 bug seems completely
  separate to this TA work. It pops here too but it is unchanged. A separate PR — small, but not ours."
  Neither fixed nor worked-around here; recorded in §12 for a separate small plan.

**Tracked follow-ups (visible, not silently dropped — Dean: "proceed now, track as follow-ups"):**

1. **e2e-test sweep for the QM refusal** — unit sweep confirmed no test exercises the real
   `optimizeQueueingModel`; the e2e sweep is still owed. Non-blocking.
2. **`Status.DesiredOptimizedAlloc.NumReplicas` persistence** — confirmed safe by code reading
   (`applySaturationDecisions` re-affirms last-good every cycle); test 4 locks it in. Closed, but
   recorded here for traceability.
3. **Flapping risk** — no cooldown/grace-period mechanism exists anywhere in this codebase to prevent
   a freshly-bootstrapped replica from being scaled back down once it reports real metrics. Confirmed
   **pre-existing** gap, not introduced by this refactor; documented as a known limitation.

[↑ TOC](#toc)

---

## §8 Commit 5 — developer-guide

**Files:** `docs/developer-guide/multi-analyzer-pipeline.md`,
`docs/developer-guide/saturation-scaling-config.md`.
**Framing shift:** from "saturation is always first / always runs / drives every decision / keeps
per-variant metadata" → "the engine calls every enabled analyzer; the anchor is a per-variant merge
derived on demand ((a) identity from saturation, (b) sizing from the binding analyzer); saturation is
the (a) carrier but no longer has a voting exemption; the queueing-model path is refused."

Per CONVENTIONS (name specific sections, and no plans-branch identifiers in code-side text). Update
these specific passages — the coder greps each (they are also caught by §9):

**`multi-analyzer-pipeline.md`:**
- The pipeline **diagram** annotation "Saturation V2 (always first)" → describe saturation as the
  identity/(a) carrier that is called like any other analyzer; order not significant.
- The "**exempt from this gate**" text (saturation-vote-exemption) → saturation votes only when
  enabled (opt-in); an `[throughput]`-only config makes it a non-voting carrier.
- The "**always first … carry Cost**" text → the anchor is a per-variant merge; (a) fields (incl.
  `Cost`, `AcceleratorName`) come from saturation, (b) fields from the binding analyzer.
- The "**no name-based exemption**" text → align with the opt-in `satVotes` predicate.
- The "**keeper of per-variant metadata**" text (the old `saturationEntry` framing) → replace with the
  `bindingAnchor` derived-on-demand description.

**`saturation-scaling-config.md`:**
- "**Saturation drives every scaling decision**" → saturation drives decisions only when enabled;
  describe the three configs (§1 table).
- "**always runs and drives**" → always *runs* (as the (a) carrier); *drives* only when it votes.
- The "**### Saturation Always Runs**" subsection heading/body → rewrite to "Saturation as the
  identity carrier" (or similar): it always runs to supply (a), but voting is opt-in.

**Add** (either file, whichever has the natural home — check during writing): a short note on the
TA-side persistence behavior (§7b) — TA now emits a fallback `VariantCapacity` for a previously-live
variant that dropped to zero, using its last-known per-replica capacity / cost / accelerator, within
the ~60-min eviction window — and the §7c documentation-only note on scale-from-zero reliance +
tracked follow-ups.

**Constraint:** Type-4 docs reflect *current code on this branch* only — no "pending PR" / forward
references, no `Fnn`/`Ann`/`planning/` identifiers. Use descriptive prose.

[↑ TOC](#toc)

---

## §9 Semantic-pivot grep (mandatory)

Two behavioral contracts change: `saturationEntry` → `bindingAnchor` (getter shape + "sat is special"
framing), and QM-silent-dispatch → QM-error. After implementation, run this grep across code **and**
docs and update every stale hit (comments, docstrings, dev-guide prose, test names):

```bash
grep -rni \
  -e "saturationEntry" -e "satEntry" \
  -e "saturation entry is always first" -e "always first" \
  -e "keeper of per-variant" \
  -e "Saturation is exempt" -e "no name-based exemption" \
  -e "before effectiveEnabled is ever called" \
  -e "always runs" -e "drives every scaling decision" \
  -e "optimizeQueueingModel" \
  internal/ docs/developer-guide/
```

Every hit must either be updated to the new framing or, if it is a genuine reuse-guard comment that
still applies (the `engine_v2.go` sat-name reuse-guard `continue`, §5), left with a clarified comment
that says "reuse guard, not a decision gate." Do not leave any "saturation is always first / special /
exempt" language that implies ordering or a voting exemption. Zero stale hits before commit.

[↑ TOC](#toc)

---

## §10 Read-site inventory — code-change areas from main

This is the "highlight the changes and code change areas from main" map (Dean's request). Line numbers
are as-of base `9906dac5`; treat them as anchors, re-confirm with the grep (§9) since the interim base
is the goldens tip.

### Struct / field

| Site | From | To |
|---|---|---|
| `optimizer_interfaces.go:36` | (no enablement field) | add `Enabled bool` after `Live bool` |
| `optimizer_interfaces.go:44` | `// saturation entry is always first` | `// order is not significant (see bindingAnchor/votingResults)` |

[↑ TOC](#toc)

### Phase 1 (`engine_v2.go: runAnalyzersAndScore`, ~:96-178)

| Site | From | To |
|---|---|---|
| before sat append (~:140) | — | compute `satVotes` |
| sat append (~:140-148) | `{Name: sat, ...}` (no `Enabled`) | add `Enabled: satVotes` |
| non-sat loop (~:149-171) | 3 `continue` guards, no tag | keep guards; enabled entries get `Enabled: true` |
| docstring (~:90-95) | "always first / special" | tag semantics; drop ordering language |

[↑ TOC](#toc)

### Phase 2 (`analyzer_helpers.go`)

| Site | From | To |
|---|---|---|
| `:87-98` | `saturationEntry` (scan sat, return `e.Result`) | `bindingAnchor` (find sat carrier, select binding, per-variant merge, nil→hold) |
| new | — | `votingResults(s)` — filter to `Enabled` |

[↑ TOC](#toc)

### Selection sites (→ `anchor := bindingAnchor(...)`)

| File | Sites |
|---|---|
| `cost_aware_optimizer.go` | `:48` getter, `:49-51` nil-guard→hold, `:54` buildCapacityMap, `:62` allocateForModelPaired, `:65` scaleDownRoleIterated, `:256` |
| `greedy_score_optimizer.go` | `modelWork.satEntry` field `:46`→`anchor`; `:125`/`:158` getters; `:149`/`:164` buildCapacityMap; `:170` scaleDownRoleIterated |
| `rescale.go` | `:225`, `:342-371`, `:465-471`, `:486-521`, `:589-595`, `:604-610` (+ rename `modelDemandGPUs`/`roleDemandGPUs` param `satEntry`→`anchor`) |

[↑ TOC](#toc)

### Combine-ballot sites (→ `s := votingResults(req.AnalyzerResults)`)

| File | Sites |
|---|---|
| `cost_aware_optimizer.go` | `:59` |
| `greedy_score_optimizer.go` | `:130`, `:168` |
| `rescale.go` | `:365` (`reclaimRole(ctx, req.AnalyzerResults, ...)`) |

[↑ TOC](#toc)

### QM / liveness (`engine.go`)

| Site | From | To |
|---|---|---|
| `:553-554` | `optimizeQueueingModel(...)` | `refuseQueueingModel(...)` (new: Error + empty decisions) |
| `:557` `default:` | `optimizeV1(...)` | **unchanged** (AnalyzerName-validation gap → separate PR, §12) |
| `:571` | `applySaturationDecisions` (unconditional) | **unchanged** (the hold + metric mechanism) |
| `:1002`, `:1828+` | `emitSafetyNetMetrics` per-model catch / defn | **unchanged** (pre-existing hold precedent) |

[↑ TOC](#toc)

### TA complement (`throughput/analyzer.go`)

| Site | From | To |
|---|---|---|
| `variantState` (~:50) | `lastPerReplicaSupply` (already persisted) | **no new field** — reuse it |
| success site (~:319-322) | already sets `lastPerReplicaSupply` | **unchanged** |
| after `byVariant` loop (~:262) | — | second loop over `input.VariantStates` — emit PRC-only from `lastPerReplicaSupply` for previously-live-now-zero variants (never-seen → no emission) |

[↑ TOC](#toc)

### Fixtures (test-only, bounded)

| Site | Change |
|---|---|
| `cost_aware_optimizer_test.go:16` `withSatEntry` | add `Enabled: true` |
| `analyzer_helpers_test.go:14` `makeNamed` | add `Enabled: true` |
| `analyzer_helpers_test.go:117` `makeNamedPD` | add `Enabled: true` |
| inline `NamedAnalyzerResult{` literals in `*_test.go` | add `Enabled: true` where voting (grep) |

[↑ TOC](#toc)

---

## §11 Coordination — branch, goldens gate, PR-2 dependency

**Branch decision.** Cut a **fresh** branch `ta-anchor-refactor-v2` off the **goldens tip**
`ta-anchor-goldens@a2f49ccf` (interim base). Reasoning: `main` is still `9906dac5` (the goldens PR
#1513 is open, not merged), and the goldens must be present on this branch to run as the ship gate
(§4). After #1513 merges into `main`, **rebase `ta-anchor-refactor-v2` onto `main`** (the goldens
arrive via that merge; the interim base disappears cleanly). This mirrors the interim-base reasoning
the superseded plan used — only the branch name changes.

- The abandoned `ta-anchor-refactor@34055d77` (Dean's stored-`.Anchor` commit) and the Aug-4 fold-in
  commits (`68bda1a1`/`192ae06b`, on the *plans* branch — plan-doc edits, not code) are **superseded**
  by the no-stored-field design. Leave `34055d77` in place, unpushed, until Dean archives it with
  `git boidem ta-anchor-refactor` at his convenience — not urgent, no PR, no risk sitting there.
- **This is a git operation outside the planner's write scope.** The planner does not create the
  branch/worktree; it describes the ask in a handoff (see §"handoffs" in the task log) for Dean/the
  coder to execute. Every code branch needs a matching origin branch — pushing `ta-anchor-refactor-v2`
  to origin is subject to the "no push without explicit confirmation" rule.

**Goldens gate (hard dependency).** #1513 must be green and its goldens present. Run them after every
commit (§4, test 8). If #1513's `withSatEntry`-stability note (goldens review Finding 2) surfaces a
fixture-stability issue, resolve it here as part of §6's fixture step — the `Enabled: true` addition to
`withSatEntry` is the coordination point.

**PR-2 dependency.** `ta-anchor-dynamic-refresh` (multi-vote combine + per-iteration dynamic re-binding
+ masked bugs #1/#2/#3/#5 + F10/F11-correctness) is **deferred until this PR lands**. Do not start it.
Its stub carries a one-line forward-note that "refresh = re-run the Phase-2 getter each cycle," not
"mutate a stored field."

[↑ TOC](#toc)

---

## §12 Deferrals & deletion classification

Per the deletion-documentation rule — nothing is silently dropped; each removed/parked behavior is
classified so a future session can recover the intent.

- **Queueing-model optimize path → DEFERRED (not deprecated).** `optimizeQueueingModel` is no longer
  dispatched (§7a `refuseQueueingModel`). The analyzer and its optimize path remain in the tree; the
  design intent (a queueing-model-driven analyzer) is real but parked until the multi-analyzer engine
  contract can host it as a first-class voting analyzer (the F10 "fold queueing-model into the V2
  engine" direction). **Open for Dean:** file a GitHub issue for the queueing-model multi-analyzer
  contract work? (Flagged, not blocking this PR.)
- **The stored-`.Anchor`-field mechanism → superseded (not a code deletion).** It never merged
  (`34055d77` unpushed). No code-level classification needed; recorded here for traceability so a
  reader of the old plan understands why it was abandoned (a structurally simpler, more correct
  no-stored-field design replaced it).
- **AnalyzerName validation gap → separate standalone PR.** Unconstrained `AnalyzerName` +
  silent `default:`→`optimizeV1` fallback ([engine.go:557](../../Main/internal/engines/saturation/engine.go#L557)).
  Not a 0.9 requirement. File as its own small PR/issue.
- **sat `Cost=0`-for-zero-replica bug → separate PR (pre-existing, "not ours").** sat's
  `aggregateByVariant` rebuilds `variantCost`/`variantAccel` fresh each cycle from that cycle's live
  metrics, so a zero-replica variant gets `Cost=0` / `AcceleratorName=""`
  ([`saturation_v2/analyzer.go` ~:353-373](../../Main/internal/engines/analyzers/saturation_v2/analyzer.go))
  even though the correct spec cost already exists one call up in `prepareModelData`'s `variantCosts` map
  ([`saturation/engine.go` ~:1490-1520](../../Main/internal/engines/saturation/engine.go)). Because
  `Cost` is the anchor's (a) from sat, this bug surfaces under **every** config with a returning
  zero-replica variant — `[saturation]`-only always, and now `[TA]`-only too (§7c known limitation).
  This PR neither fixes nor works around it (no sentinel, no TA-side cost plug — that would be the "hack
  to bypass an existing bug" Dean rejected). Dean (2026-08-05): "completely separate … pops here too but
  unchanged. A separate PR — small, but not ours. Create a separate plan for it later." File as its own
  small plan/issue; do not fix in this PR.
- **Real per-variant CRD-spec cost NOT plumbed into `VariantReplicaState` → decided against (2026-08-05).**
  One way to give a returning zero-replica variant a real cost would be to add `Cost`/`AcceleratorName`
  to `domain.VariantReplicaState` and fill them in `BuildVariantStates` from `va.Spec.VariantCost`.
  **Rejected by Dean:** the VA CRD is being deprecated, cost sourcing is unrelated to TA support, and
  accelerator-type config lookup already supplies the value when config populates it — so no new plumbing
  mechanism in this PR. The correct home for a real fix is the sat `Cost=0` bug (bullet above), not TA.
  Recorded so a future session doesn't re-propose it without the deprecation context.
- **Partial-scale-from-zero picker trustworthiness → deferred (documented in §7c).** Under discussion
  in the review (§2.4); this PR relies on `scalefromzero` (reactive) + §7b (proactive) and does not
  change the picker for never-seen zero-replica candidates.

[↑ TOC](#toc)

---

## §13 Reviewer verification checklist

Internal plan-vs-diff review before push (this is the internal review, not the GitHub-posting skill):

- [ ] **Goldens green after every commit** (§4/test 8) — not just at the end.
- [ ] `Enabled bool` added; `satVotes` predicate matches the truth table (§1 table): default & `[sat,TA]`
      → sat votes; `[TA]`-only → sat is a non-voting carrier.
- [ ] `bindingAnchor` builds **fresh** literals — no mutation of source `Result`/`VariantCapacities`
      (test 3); per-variant fallback runs **before** `votingResults` prune (test 2).
- [ ] `TotalCapacity` recomputed as `ReplicaCount × PerReplicaCapacity` (test 1 invariant).
- [ ] Every selection site goes through `bindingAnchor`; every combine site through `votingResults`
      (§10 + the `grep AnalyzerResults` backstop). No raw `req.AnalyzerResults` feeding combine math.
- [ ] Empty/no-live ballot → no panic, no decision, `NumReplicas` preserved, metric emitted (test 4).
- [ ] QM enabled → explicit Error + hold, never silent V1 fallback (test 5).
- [ ] TA complement: a previously-live-now-zero variant emits its persisted `lastPerReplicaSupply` as
      **PRC only** (real TA (b)); `Cost`/`AcceleratorName` are **not** TA-emitted (they are sat's (a) via
      the merge); a never-seen variant emits nothing (PRC=0, not proactively selectable under `[TA]`-only)
      (test 7); a previously-live zero-replica variant is still selectable when scale-from-zero is
      warranted (test 10); eviction degrades a long-idle variant to the never-seen (no-emission) case. No
      `fallbackVariantCost` sentinel, no TA-side cost plug (§7c known limitation is documented, not gated).
- [ ] Fixture scope is the 3 central builders + audited inline literals — **not** an 87-site churn
      (E2 confirmed moot).
- [ ] Semantic-pivot grep (§9) returns zero stale hits in code **and** dev-guide.
- [ ] Dev-guide (§8) reflects current branch code only — no forward refs, no plans-branch identifiers.
- [ ] gofmt clean; `make test` pass; `make lint` clean; `go build ./...` clean; DCO sign-off on every
      commit; correct branch (`ta-anchor-refactor-v2`) verified before each commit.

[↑ TOC](#toc)
