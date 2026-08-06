# TA Anchor Refactor — PR-2 (dynamic refresh + multi-vote combine)

**Type:** 3 (task plan) · **Status:** Coder-ready — **stacked on PR-1; worked in parallel** (does NOT wait for PR-1 merge; starts on Dean's go-ahead)
**Design authority:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (Type 1)
**Depends on:** [`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md) (PR-1, FINAL) — this PR is a
**dependent, stacked** follow-up (Dean, 2026-08-06): its base is **PR-1's branch tip**, not merged `main`,
and the two PRs progress **in parallel**. PR-2 opens as a GitHub PR with base = the `ta-anchor-refactor-v2`
branch. Re-base onto PR-1's tip whenever PR-1's close-out (rebase-onto-`upstream/main` + F1/F3/F4 rewords)
rewrites C1–C5.
**Branch/worktree:** `ta-anchor-dynamic-refresh` — worktree CREATED 2026-08-06 off PR-1's tip
`f6485980`; **pushed to `origin/ta-anchor-dynamic-refresh` 2026-08-06** (Dean-authorized). Expect one
**force-push-after-re-base** once PR-1's close-out rewrites its C1–C5 SHAs (the current base `f6485980`
becomes orphaned). The base is a real branch base, not just a line-number convenience.
**Correctness scope:** §9 of the reviewer-owned [`multi-analyzer-dataflow-map.md`](multi-analyzer-dataflow-map.md)
(findings **N1–N9**, traced against `ta-anchor-refactor-v2 @ f6485980`).

> **Line numbers in this plan are as-of `f6485980`** and will drift after the PR-1 rebase. The coder
> **greps by symbol**, not by line — every cite below names the function/identifier so it survives the drift.

---

## Reading Protocol

> Read this Reading Protocol + `## TOC`, then fetch sections on demand
> (`Read <file> offset:<start> limit:<end−start+1>`). Re-run `toc-refresh.sh` after structural edits.

---

## TOC

- [§0 Status — scope & the indivisible-PR decision](#0-status--scope--the-indivisible-pr-decision) L43:87
- [§1 Scope — the both-enabled dynamic case + commit map](#1-scope--the-both-enabled-dynamic-case--commit-map) L88:146
  - [§1.1 Commit map (C1–C9)](#11-commit-map-c1c9) L125:146
- [§2 The four combine-arithmetic bugs](#2-the-four-combine-arithmetic-bugs) L147:199
- [§2b Live-gate the combine input (VG-up + N8 + N7) — lands in C7](#2b-live-gate-the-combine-input-vg-up--n8--n7--lands-in-c7) L200:272
- [§2c (a)/(b) → plain-prose notation cleanup — lands in C8](#2c-ab--plain-prose-notation-cleanup--lands-in-c8) L273:302
- [§3 Per-iteration dynamic refresh — lands in C2](#3-per-iteration-dynamic-refresh--lands-in-c2) L303:337
- [§4 Ship gate & tests](#4-ship-gate--tests) L338:370
- [§5 Dev-guide sections (named, per commit)](#5-dev-guide-sections-named-per-commit) L371:405
- [§6 Semantic-pivot grep steps](#6-semantic-pivot-grep-steps) L406:435
- [§7 Out of scope / deferred / separable follow-ons](#7-out-of-scope--deferred--separable-follow-ons) L436:460

## §0 Status — scope & the indivisible-PR decision

PR-1 (`ta-anchor-refactor-v2-plan.md`) delivered the static core: the anchor/ballot contract, the
topology-vs-vote read split, and TA-only enablement — all **single-vote** (0 or 1 enabled analyzers),
changing **zero** combine arithmetic. PR-1 supports `[sat]`-only and `[TA]`-only; the both-enabled
`[sat, TA]` two-vote path is what PR-2 turns on.

This PR-2 turns on the **multi-vote** path: the per-role combine that refreshes the anchor's sizing
fields, the per-iteration dynamic refresh, the four combine-arithmetic bug fixes that only manifest
with ≥2 votes, and the deferred liveness/notation hardening. This is where the real algorithmic risk
lives — it deserves its own review cycle against the design doc § anchor / § bugs / § sort / § rescale.

**Scoping decision (Dean, 2026-08-06) — this is ONE indivisible PR, not a split.** Multi-vote combine
(§1) and per-iteration dynamic re-binding (§3) do **not** separate: **multi-vote needs dynamic
re-binding** to be correct — as allocation fills within a cycle, remaining demand shifts and the
per-(role, variant) binding `argmax_i rd_i` can change, so a binding fixed at cycle start goes stale
mid-water-fill. §1 + §2 (arithmetic bugs) + §3 + §2b (liveness) ship together. The genuinely-separable
follow-ons are the standalone small PRs in PR-1 §12 (QM fold F10, the §2.4 partial scale-from-zero
picker, `AnalyzerName` validation, the sat `Cost=0`-for-zero-replica bug) — each independent, **not**
part of this stack (see §7).

**Grounding to re-read at coding start** (already read at authoring, 2026-08-06 — re-read on resume):
design doc [§ anchor](combined-analyzer-optimizer-design.md), [§ combine], [§ bugs], [§ sort],
[§ rescale]; PR-1 plan §2/§3/§12; and **§9 of `multi-analyzer-dataflow-map.md` whole** (the
authoritative correctness scope; findings N1–N9 are folded into the commits below).

**Authoring note (2026-08-06).** This doc was expanded from a STUB to coder-ready per Dean's "prepare
everything for the PR-2 coder." The commit sequence (§1 commit map) and the three scoping decisions
below were confirmed with Dean before authoring:
- **Refresh ordering:** per-iteration refresh lands **early** (C2, before the arithmetic fixes) so the
  binding is current before the bug fixtures assert numbers.
- **Sat-only goldens endgame:** **RELAX / remove** the #1513 sat-only goldens once the multi-vote
  goldens cover the single-vote path as a sub-case (explicit removal commit in C9 — see §4).
- **N3 nil-guard hardening:** **INCLUDE** it in PR-2 (rides C5, the rescale commit).

**Coding is NOT gated on PR-1 merging** (Dean, 2026-08-06) — PR-2 is **stacked on PR-1's branch and
worked in parallel**. Start C1 on Dean's explicit go-ahead (per "Discuss before implementing"); expect
to re-base onto PR-1's tip when its close-out rewrites C1–C5. The correctness dependencies PR-2 builds
on (`bindingAnchor`, `votingResults`, the `Enabled` ballot tag) are all present at the base tip.

[↑ TOC](#toc)

---

<a id="1-scope"></a>
## §1 Scope — the both-enabled dynamic case + commit map

**The three supported configs after PR-1 (unchanged framing):**
- `[sat]`-only — default; frozen by #1513 goldens; sat binds; single vote.
- `[TA]`-only — sat is a non-voting `(a)`-carrier (`Enabled=false`), TA binds; single vote.
- **`[sat, TA]`** — sat + TA both enabled; **two votes**; this is what PR-2 enables.

**The multi-vote combine model (design § anchor / § combine).** All votes combine **uniformly** — no
name-checks, per Dean's model. The anchor is derived on demand by the PR-1 Phase-2 getter
(`bindingAnchor`); PR-2 generalizes it and re-invokes it per iteration:

1. **Multi-vote refresh of the anchor's sizing fields.** Generalize PR-1's "the sole vote's sizing is
   already on the anchor" to the per-role binding rule: per (role, variant), the binding analyzer is
   `argmax_i rd_i` (the binding constraint), and its sizing/sort fields are written onto the anchor.
   Identity fields are never touched; RC/SC stay per-analyzer off the ballot (unchanged from PR-1).
   **The refreshed fields are exactly PR-1's sizing subset:** per-variant `PerReplicaCapacity`,
   `TotalCapacity`, `TotalDemand`, `Utilization`, `Reason`; model-level `TotalSupply`, `TotalDemand`,
   `Utilization`. Nothing else moves onto the anchor.
2. **Refresh each iteration.** That binding is a pure function of (immutable ballot entries,
   current+pending replicas, allocation progress); recompute per allocation iteration, not once (§3).
3. **rescale-on-multi/TA validation** — the rescale path (`rescale.go`) under ≥2 votes and TA-only,
   which PR-1 routed but did not golden-cover.
4. **Binder tie-break — dataflow-map §9 N2.** PR-1's `bindingAnchor` returns **nil** (⇒ model hold)
   whenever >1 non-saturation analyzer qualifies as a binder for a variant (`analyzer_helpers.go:150`).
   Safe under PR-1 (sat-only or TA-only ballots), but PR-2 admits ≥2 voters, so a genuine multi-binder
   tie becomes a **silent permanent hold**. The multi-vote combine must replace nil-on-ambiguity with
   a deterministic tie-break — **saturation-if-present, else lowest analyzer index** (align with design
   § anchor). Add a two-binder fixture asserting the tie-break, not a hold. (Lands in **C1**.)
5. **Abstain-vs-veto on role coverage — dataflow-map §9 N7.** The scale-down role list is
   `rolesOf(anchor.VariantCapacities)`, and `needsScaleDownForRole` (`analyzer_helpers.go:445-457`)
   requires **every** live voter to report `RoleSpare[role] > 0`; a live voter with **no opinion** on a
   role reads the map-miss as `0.0` → implicit **veto** (stuck-high). PR-1 is safe (a single binder
   defines the role set), but the multi-vote combine must decide explicitly whether a voter that does
   not size a given role **abstains** (excluded from that role's spare test) or **vetoes** (current
   behavior). **Default to abstain** (Dean-confirmed 2026-08-06) unless the design says otherwise;
   cover with a role-coverage-mismatch fixture. (Lands in **C7**.)

### §1.1 Commit map (C1–C9)

Ordered stack; each is DCO-signed, gates-green-after-every-commit in an isolated worktree. "Red-first"
= add the fixture failing before the fix, passing after.

| # | Commit scope | Red-first test | Dev-guide (§5) | Detail |
|---|---|---|---|---|
| **C1** | Admit two-vote path + **N2** deterministic binder tie-break (sat-if-present, else lowest index) — replace nil-on-ambiguity in `bindingAnchor`. Enabler. | two-binder fixture asserts tie-break, not hold | pipeline "How results combine" | §1 item 4 |
| **C2** | **Per-iteration dynamic refresh** — re-invoke the Phase-2 getter each allocation iteration so the per-(role,variant) binding re-selects as remaining demand shifts. | fixture where binding flips mid-water-fill | pipeline "Scale-up path", "Data flow per optimize cycle" | §3 |
| **C3** | **Bug #2** `roleAggRemaining` — max in replica space (`max_i rd_i`), not raw mixed-unit RC. | two-vote MAX fixture | sat-config "Shared aggregation helpers" | §2 #2 |
| **C4** | **Bug #1** `allocateForModelPaired` decrement — per-analyzer `k·PRC_i` (or replica units), not `k·PRC_sat` uniformly. Paired with C3. | two-vote allocation fixture | pipeline "Scale-up path" | §2 #1 |
| **C5** | **Bug #3** rescale water-fill + `roleDemandGPUs` combined `max_i ceil(demand_i/PRC_i)`; **+ N3** nil-guard hardening in `rescaleModelDecisions`. | two-vote rescale fixture | pipeline "Optimizer internals" | §2 #3, §7 N3 |
| **C6** | **Bug #5** fair-share — 3 lock-step sites `fairShareValue` / `fairShareCap` / `sortVariantsForScaleDown` move together (anchor combined replica-demand; GPUs→replicas convert; binding-PRC tie-break). | fair-share ordering fixture | pipeline "Fair-share iteration" | §2 #5 |
| **C7** | **Liveness** — `votingResults` `Enabled` → `Enabled && Live` (VG-up/D2); **DROP** the `bindingAnchor` sizing-fallback (N8, rewrites PR-1 Test 2 v2 110→0); **N7** abstain-vs-veto default abstain. | stale-enabled scale-up + role-coverage-mismatch fixtures | pipeline "How results combine" + "Scale-from-zero"; sat-config "How Scale-Up Triggers Work", "Saturation as the Identity Carrier" | §2b |
| **C8** | **§2c notation cleanup** — strip `(a)/(b)` letters, keep descriptive prose. Comments/docs only, byte-identical behavior. | none (green byte-for-byte) | pipeline + sat-config (see §2c line list) | §2c |
| **C9** | **Dev-guide multi-vote sections + goldens endgame** — multi-vote reference prose; **relax/remove** the #1513 sat-only goldens as an explicit commit once the multi-vote goldens cover the single-vote sub-case. | multi-vote goldens; hand-worked design examples | all touched dev-guides finalized | §4 |

[↑ TOC](#toc)

---

<a id="2-bugs"></a>
## §2 The four combine-arithmetic bugs

All **dormant with a single vote** (masked because saturation is the only PRC and unit-mixing across
analyzers can't manifest); each becomes real the moment a second analyzer votes. Fix here, each with a
regression test that is **red pre-fix** under a two-vote fixture. Source: design doc [§ bugs].
`#4` was **downgraded** (traced 2026-08-03; not an active sizing bug — residual is observability
`Utilization` only; confirm at coding whether any observability cleanup rides — default: none).

- **#1 — `allocateForModelPaired` decrement unit (`analyzer_helpers.go:366-413`) → C4.** The loop
  computes `utilByRole = n·prc/demand`, `deltaUtil = min_role`, `k = floor(deltaUtil·demand/prc)`, then
  `pickerState[i][role] -= k·prc` for **all** `i`, where `prc = prcFromVCs(variants, v)` = topology
  PRC_sat. But `roleBottleneckReplicas` reads `pickerState[i]/PRC_i`. Decrementing every analyzer's
  state by `k·PRC_sat` while dividing by `PRC_i` mixes units for `i ≠ saturation`. **Fix:** decrement
  in **replica units** (`k` replicas) or per-analyzer `k·PRC_i`, not `k·PRC_sat` uniformly.
- **#2 — `roleAggRemaining` unit-mixing (`analyzer_helpers.go:201`) → C3.** `max_i state[i][role]` maxes
  raw `RequiredCapacity` across analyzers whose units differ (saturation = tokens, throughput =
  request-rate). Maxing tokens against req/s is meaningless. **Fix:** compare in **replica space**
  (`max_i rd_i`), `roleBottleneckReplicas`-style, not raw-capacity max. (Foundational — the MAX combine
  C4 depends on; land C3 before C4.)
- **#3 — rescale water-fill weight + demand→GPU (`rescale.go`) → C5.** `roleDemandGPUs:543` uses
  `demand = satEntry.TotalDemand`, `best = cheapest PRC_sat`, `replicas = ceil(demand/best)` — the
  `i=saturation` term only; and the water-fill weight `rescaleInputsForGroup:521` `Demand:
  satEntry.TotalDemand` is incommensurable across models bound by different analyzers. **Fix:** combined
  `desired_combined[role] = max_i ceil(demand_i[role]/PRC_i[role,v*])`; keep `TotalDemand` for
  observability. Under the anchor design `roleDemandGPUs` reading the anchor gets combined demand
  automatically. `fillRole:414 → sortByCostEfficiencyAsc` efficiency PRC should be the binding
  analyzer's (collapses to today for one analyzer); `reclaimRole:387 → sortVariantsForScaleDown` is
  **already OK**. **+ N3 hardening (this commit):** `rescaleModelDecisions:342-344` dereferences the
  anchor with **no local nil-guard** (safe only via the `:225` pre-filter + `bindingAnchor` purity;
  fragile). Add the nil-guard (or compute-once-and-pass the anchor) — cheap, closes the fragility.
- **#5 — `fairShareValue` sums (`Σ_i`) where design wants (`max_i`) → C6.** Limited/fair-share mode only
  (the cost-aware unlimited path does not use fsv). Three **lock-step** sites that must change together
  or units desync:
  - **(i) `fairShareValue` (`greedy_score_optimizer.go:73`)** — replace `Σ_i Score_i × Σ_role
    ps[i][role]` with a combined replica/GPU-space quantity `Σ_role (max_i rd_i[role] − current[role])`
    (× priority; × Score only if Score is meant to weight budget). **Re-point fsv at the anchor's
    combined per-role replica-demand** instead of iterating per-analyzer `ps` — the anchor already
    holds `max_i rd_i` per role.
  - **(ii) `fairShareCap` (`greedy_score_optimizer.go:421`)** — `ceil(target / vc.PerReplicaCapacity)`
    divides the fsv-unit `target` (`= w.remaining − mean`, `:271`) by topology PRC_sat. Once `target`
    becomes replica/GPU-space (fix i), this double-converts; convert GPUs→replicas via `gpusPerReplica`
    or use replica-space `target` directly. Same commit as (i).
  - **(iii) scale-down tie-break `sortVariantsForScaleDown` (`cost_aware_optimizer.go:161-184`, weighted
    sum `:168`)** — a **second** `Σ_i Score_i × PRC_i[v]` site. Lower severity (orders scale-down
    candidates within a role, never sizes), but the same wrong-operator/mixed-unit pattern; sweep here
    — use the binding `max_i` PRC or drop the cross-analyzer weight for a topology-only tie-break.
    (Note: this site is **also** touched by C7's N7 role-coverage decision — coordinate the two edits.)

[↑ TOC](#toc)

---

<a id="2b-livegate"></a>
## §2b Live-gate the combine input (VG-up + N8 + N7) — lands in C7

Deferred from PR-1 by Dean (2026-08-06). PR-1's combine input is gated on `Enabled` **only**, not
`Enabled && Live`, at the voting site; the binder selection in `bindingAnchor` already uses
`Enabled && Live && Informative`. C7 unifies the voting site with that rule and drops the fallback.

**Scope caveat (Dean, 2026-08-06):** this is **more than a static `Enabled && Live` filter** — the gate
interacts with *when* the per-role binding is re-selected (§3), not only *which* entries vote. Keep this
work **coupled to §1/§3 inside C7-and-neighbors**, not a standalone micro-PR. The bullets below are the
floor.

- **VG-up (a.k.a. D2) — `votingResults` (`analyzer_helpers.go:234`).** Filters the combine (RC/SC)
  ballot on `e.Enabled`; change to `e.Enabled && e.Live`. Centralizes "dead = out of the combine" for
  **both** directions and establishes the clean invariant **non-nil anchor ⟹ non-empty voting set** (the
  binder itself satisfies `Enabled && Live`; an empty voting set → nil anchor → hold, never an unguarded
  scale-down). The reviewer **twice** recommended folding this into **PR-1** close-out; Dean **kept it in
  PR-2** with the rest of the liveness work (2026-08-06, re-confirmed). **Placement is decided, not
  open** — do not re-raise pulling VG-up forward.
- **N8 (supersedes the original D1) — DROP the sizing-fallback, don't `.Live`-gate it (Dean-directed
  2026-08-06, dataflow-map §9 N8).** The per-variant sizing-fallback in `bindingAnchor` (`:208`)
  currently borrows saturation's sizing for a binder-unknown variant when `satEnabled := satNR != nil &&
  satNR.Enabled` (`:169`). `.Live`-gating it (the original D1) is **nearly vacuous**: the fallback fires
  *only* when sat is already not binding (`!Live` **or** non-informative), so `&& satNR.Live` still
  admits a `Live`-but-no-data sat lending a stale stored PRC. **Instead DROP the fallback** — a
  binder-unknown variant keeps its identity fields but abstains with **PRC=0**, exactly as `[TA]`-only
  already does. Byte-identical on the #1513 + Test 9 fixtures (sat binds in both → the fallback never
  fires), makes partial-scale-from-zero metric-consistent, dissolves dataflow-map findings **N1** + the
  fallback half of **N5**, and implements Dean's rule "when TA binds, every sized entry is TA's." This
  **revises PR-1 plan decision V9** (PR-1 ships the fallback as-is — see PR-1 §12).
- **N7 abstain-vs-veto** — see §1 item 5. Default **abstain**. Coordinate with C6 (iii)
  `sortVariantsForScaleDown` — both touch the scale-down role math.

**Why it was safe to defer (PR-1 is not wrong today).** As-is, a dead analyzer causes no spurious scale
in either direction for the current analyzer set:
- **Scale-down is already enforced-Live-safe** — `needsScaleDownForRole` / `safeRemovalReplicasForRole`
  both `if !e.Live { continue }` at point of use (pre-existing base fns, untouched by PR-1); all-dead →
  no scale-down.
- **Scale-up is only *emergent*-safe** — `initRoleState` seeds the picker from every voting entry with
  no `.Live` guard (`:271-307`, skipped only by the `Result==nil` guard `:277`), so safety rests on the
  external invariant *"dead analyzer ⇒ RC=0"* — **not** enforced in the combine. A future analyzer that
  carries forward stale-but-informative `RC>0` with an aged `AnalyzedAt` breaks it. Gating `votingResults`
  on `Enabled && Live` makes scale-up robust independent of that invariant and demotes the point-of-use
  `!e.Live` guards to belt-and-suspenders.
- **Scale-from-zero is unaffected** — full scale-from-zero rides a *live* TA (`Reason:"T-sfz"` ⇒
  informative ⇒ `Live=true`), so the gate is a no-op for it.

**Caveats for the implementer:**
- Keep `bindingAnchor` reading the **FULL** ballot (do not feed it `votingResults`'s output) — it needs
  a non-voting sat's identity/topology.
- **Empty-voting ⟹ nil anchor (an invariant, not a new combination).** The binder gate
  (`Enabled && Live && Informative`) is strictly stronger than the VG-up voting gate (`Enabled && Live`),
  so binder ⊆ voters: an empty voting set forces `anchor == nil` → the existing hold path. There is no
  "empty voters + non-nil anchor" case to invent — just confirm the nil-anchor hold is exercised.
- **Ship-gate safe:** #1513 goldens + PR-1 Test 9 fixtures are all-live → the Live-filter is a no-op →
  they stay green. This is a voting-semantics change for *multi-analyzer* configs #1513 does not cover;
  add a characterization test for the stale-enabled-analyzer scale-up case.
- **N8 rewrites PR-1 Test 2** (v2 → PRC=0 instead of 110 — dropping the fallback makes v2 abstain) and
  updates the merge/fallback wording.

**Broader option Dean floated (bigger than a gate tweak, NOT in this PR):** *"there should always be
fallback sizing values, preferably to/from all analyzers."* That is upstream of the merge (how each
analyzer populates a result for every variant) and interacts with the C4 TA-PRC-only work; if pursued
it is a design-doc/plan revision. Scope separately (§7).

**Refs:** PR-1 review doc [`ta-anchor-refactor-v2-code-review.md`](ta-anchor-refactor-v2-code-review.md)
§§ D1/D2 (full verified detail); PR-1 plan §2 (merge/fallback) + §6 (`votingResults`). Relates to the
F10 "fold queueing-model into the V2 engine" combine work.

[↑ TOC](#toc)

---

<a id="2c-notation"></a>
## §2c (a)/(b) → plain-prose notation cleanup — lands in C8

The plan's `(a) identity / (b) sizing` lettering is a **plans-branch convention**. PR-1 ships it as-is
(Dean's call, review finding **F5** — self-defined at `bindingAnchor`'s doc-comment and glossed at every
use, so not a hard §4a leak), but the bare letters `(a)`/`(b)` are meaningless to a merged-code reader
(CODER-CONVENTIONS §4a). C8 **strips the letters and keeps the words** — the cleanest §4a posture. It
touches the same files the multi-vote combine edits, so it adds no extra review surface.

**Rule — replace the bare letters with plain descriptive prose, do NOT add a new legend:** `(a)` →
`identity fields` / `identity carrier`; `(b)` → `sizing fields` / `sizing binder` / `sizing fallback`.
(Adding an `(a)/(b)` legend would be the opposite of the cleanup.)

- **Production:** `analyzer_helpers.go` (~16 comment lines, incl. the `bindingAnchor` doc-comment
  legend), `optimizer_interfaces.go`, and `saturation/engine.go` / `engine_v2.go` /
  `engine_queueing_model.go`.
- **Tests:** `analyzer_helpers_test.go` (~20 comment lines) and `optimizer_scale_from_zero_test.go`.
- **Dev-guides (concrete line targets as-of `f6485980`, grep to re-locate):**
  `multi-analyzer-pipeline.md` lines **40, 166, 243, 247–248, 349, 351, 366–367, 375**;
  `saturation-scaling-config.md` "Saturation as the Identity Carrier" section (gloss inline).

Comments / docstrings / test-descriptions only — **no behavior change**; goldens and all tests stay green
byte-for-byte. **Deferred-not-deprecated:** the taxonomy is intentionally preserved for PR-1; only its
*notation* is cleaned up here, so nothing is lost. Source: review finding F5 (Dean's option-3 decision)
+ `plan__ta-anchor-ab-notation-cleanup-pr2.md`, 2026-08-06.

[↑ TOC](#toc)

---

<a id="3-refresh"></a>
## §3 Per-iteration dynamic refresh — lands in C2

Per Dean's model, the anchor's sizing/sort fields (the exact set in §1 item 1) are the **only mutable
cell**: each allocation iteration recomputes the per-role `argmax_i rd_i` binding from the immutable
ballot entries + current+pending replicas + allocation progress, and writes that binding's sizing onto
the anchor. Identity fields and the per-analyzer RC/SC are never touched.

> **No stored anchor field.** PR-1 has **no stored anchor cell** — the anchor is derived on demand by
> the Phase-2 getter `bindingAnchor`. So "refresh per iteration" means **re-running that getter**
> (re-select the per-role binding, re-merge) each iteration, **not** mutating a stored cell in place.
> Whether the recompute is memoized is an implementation detail (correctness is identical either way);
> the observable contract is "anchor's sizing = the current per-role binding vote's, refreshed per
> iteration."

**The seam already exists (design § sort, verified 2026-08-03).** The per-role sort is **already**
re-run once per (role, allocation iteration): both pick functions call `sortByCostEfficiencyAsc(roleVCs)`
*inside* the `RolePickFn` closure (`cost_aware_optimizer.go:90`, `greedy_score_optimizer.go:408`), and
that closure is invoked once per role on every turn of the `for anyRoleNeedsScaleUp` loop in
`allocateForModelPaired`. Today the key `Cost/PRC_sat` is immutable topology, so the re-sort yields the
identical order every iteration (redundant, harmless). Once the anchor's binding PRC is refreshed per
iteration, that existing re-sort automatically picks up the shifted binding — **no new loop**. The sort
needs **no** separate binding resolution; per-iteration refresh suffices.

**C2 scope:** re-invoke `bindingAnchor` (or its per-role binding computation) at the head of each
allocation iteration so the anchor consumed by `roleBottleneckReplicas` / `sortByCostEfficiencyAsc` /
`fairShareValue` reflects the current remaining demand. Add a fixture where two analyzers' relative
`rd_i` ordering **flips mid-water-fill**, asserting the binding (and thus the chosen variant) changes on
the flip — red before C2 (single cycle-start binding picks the wrong variant late in the fill), green
after. Run with `-race` (§4).

[↑ TOC](#toc)

---

<a id="4-gate"></a>
## §4 Ship gate & tests

- The saturation-only characterization goldens (landed via their own PR
  [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513)) must **still** pass
  through C1–C8 — the single-vote path is unchanged there, and every change is a no-op on all-live
  sat-only fixtures.
- **Endgame for those sat-only goldens — RELAX / REMOVE (Dean, 2026-08-06) → C9.** They are a
  characterization/freeze suite scoped to *this* refactor, not a permanent optimizer contract. Once the
  multi-vote goldens (below) cover the single-vote `[sat]`-only path **as a sub-case**, C9 **removes**
  the sat-only goldens as an **explicit commit** (not an implicit drop) — do not leave them silently
  frozen on `main` as a forever-assertion. The removal commit message states the multi-vote suite that
  now covers the sub-case.
- **New two-vote fixtures (red-before-fix) per commit:**
  - C1 — two-binder tie-break (assert deterministic binder, not hold).
  - C2 — binding flips mid-water-fill (assert variant choice changes on the flip).
  - C3 — `roleAggRemaining` MAX in replica space (mixed-unit two-vote).
  - C4 — `allocateForModelPaired` per-analyzer decrement (two-vote allocation count).
  - C5 — rescale combined demand (two-vote water-fill); + N3 nil-anchor path exercised.
  - C6 — fair-share ordering (limited mode, two votes); assert the three sites agree.
  - C7 — stale-enabled scale-up (VG-up no-longer-scales); role-coverage-mismatch (N7 abstain);
    Test 2 rewrite (v2 PRC=0 under N8).
- **Multi-vote goldens (C9):** a `[sat, TA]` golden suite that also encodes the `[sat]`-only and
  `[TA]`-only sub-cases (so the sat-only removal is covered), validated against hand-worked design-doc
  examples (§ anchor / § bugs worked numbers).
- **Full pre-push checklist incl. `-race`** for the fair-share + per-iteration refresh loop
  (`make test` / `gofmt` / `make lint` / `go build`; DCO sign-off; branch verify). See §6 for the
  semantic-pivot grep steps that must run before commit.

[↑ TOC](#toc)

---

<a id="5-devguide"></a>
## §5 Dev-guide sections (named, per commit)

Per CONVENTIONS Type-3: name specific sections, not "update the dev guide." Section titles are as-of
`f6485980`; grep the heading text if line numbers drift. `coordinator-rebalancing.md` is a **POC demo
doc** (not the combine reference) — combine-arithmetic changes go in `multi-analyzer-pipeline.md` +
`saturation-scaling-config.md`.

**`docs/developer-guide/multi-analyzer-pipeline.md`:**
- `## How results combine` (~L254) — **C1** (N2 deterministic binder tie-break replaces nil-on-ambiguity),
  **C7** (VG-up `Enabled && Live` voting semantics; N7 abstain-vs-veto). *Modify.*
- `### Scale-up path` (~L438) — **C2** (per-iteration refresh), **C4** (`allocateForModelPaired`
  per-analyzer decrement). *Modify.*
- `### Scale-down path` (~L463) — **C6** (iii) (`sortVariantsForScaleDown` binding-PRC tie-break), **C7**
  (N7). *Modify.*
- `### Fair-share iteration (GreedyByScoreOptimizer only)` (~L482) — **C6** (i)/(ii) (`fairShareValue` /
  `fairShareCap` combined replica-demand). *Modify.*
- `### Scale-from-zero and zero-replica variants` (~L358) — **C7** (N8 drop-fallback: binder-unknown ⇒
  PRC=0 abstain). *Modify.*
- `### Data flow per optimize cycle` (~L16) — **C2** (note the anchor is re-derived per allocation
  iteration). *Modify (one line).*
- `## Optimizer internals and helper composition` (~L431) — **C5** (rescale combined demand; N3
  nil-guard). *Modify.*
- `(a)/(b)` gloss lines 40/166/243/247–248/349/351/366–367/375 — **C8** notation strip. *Modify.*

**`docs/developer-guide/saturation-scaling-config.md`:**
- `#### Shared aggregation helpers` (~L431) — **C3** (`roleAggRemaining` replica-space max). *Modify.*
- `### How Scale-Up Triggers Work` (~L207) — **C7** (VG-up liveness gate on the combine input). *Modify.*
- `### Saturation as the Identity Carrier` (~L464) — **C7** (N8 drop-fallback; sat-as-non-voting-carrier
  under `[TA]`-only), **C8** (notation strip). *Modify.*

[↑ TOC](#toc)

---

<a id="6-grep"></a>
## §6 Semantic-pivot grep steps

Each behavioral-contract change below carries a grep the coder runs **after** implementing and **before**
committing, updating every stale hit in comments/docstrings/dev-guides (CONVENTIONS + CODER-CONVENTIONS
§ semantic-pivot). If a grep surfaces a hit the plan did not anticipate, write a `plan__` handoff rather
than inferring scope.

- **C1 — `bindingAnchor` return contract** (nil-on-ambiguity → deterministic binder):
  `grep -rn "bindingAnchor" internal/ docs/developer-guide/` — update every doc-comment / caller comment
  that says the getter "returns nil" or "holds" on multiple binders. Confirm all call sites
  (`cost_aware_optimizer.go`, `rescale.go`) still nil-check correctly (the getter can still return nil on
  *no* binder / empty voting set).
- **C3/C4/C6 — unit changes** (raw-capacity → replica space): `grep -rn "roleAggRemaining\|PRC_sat\|k·prc\|fairShareValue\|fairShareCap" internal/`
  and re-read every comment describing "max of RequiredCapacity" / "decrement by PRC" / "sum across
  analyzers" — reword to the replica-space / per-analyzer / max_i semantics.
- **C5 — rescale demand→GPU** (saturation-only → combined): `grep -rn "satEntry.TotalDemand\|roleDemandGPUs\|rescaleModelDecisions" internal/ docs/`
  — update comments claiming "saturation's demand" and confirm the N3 nil-guard note lands.
- **C7 — VG-up voting gate** (`Enabled` → `Enabled && Live`): `grep -rn "votingResults\|Enabled-only\|e.Enabled" internal/ docs/`
  — reword any "votes when Enabled" prose to "Enabled && Live"; verify `bindingAnchor` still reads the
  FULL ballot (must NOT be switched to `votingResults`).
- **C7 — N8 drop-fallback:** `grep -rn "satEnabled\|fallback\|(b)-fallback\|borrow" internal/ docs/`
  — remove the fallback prose; state binder-unknown ⇒ PRC=0 abstain. Update PR-1 Test 2 (v2 110→0).
- **C8 — notation strip:** `grep -rnE "\((a|b)\)" internal/ docs/developer-guide/` — zero hits in shipped
  comments/docs after C8 (the letters are gone; the words remain).

[↑ TOC](#toc)

---

<a id="7-scope"></a>
## §7 Out of scope / deferred / separable follow-ons

**In PR-2 (this stack):** §1 multi-vote combine + N2 + N7, §2 bugs #1/#2/#3/#5, §2b VG-up + N8, §2c
notation, §3 per-iteration refresh, N3 nil-guard hardening (rides C5), §4 goldens relax.

**NOT in PR-2 — separable small PRs (PR-1 §12), each independent:**
- **QM fold (F10)** — fold the queueing-model into the V2 multi-analyzer engine (PR-1 refuses QM with an
  explicit error; dataflow-map N6). Its own PR.
- **§2.4 partial scale-from-zero picker** — the cheapest-variant partial-from-zero selector (PR-1 emits
  TA PRC-only; the picker is deferred).
- **`AnalyzerName` validation** — separate validation PR.
- **sat `Cost=0`-for-zero-replica mis-ranking (N5, non-fallback half)** — reaches all three configs; a
  **separate saturation bug**, not fixed by N8 (N8 only removes the *fallback* half). File/fix
  separately.

**Pre-existing, out of anchor scope entirely:**
- **N9** — the reactive full-scale-from-zero engine (`scalefromzero/engine.go`) is budget-blind and wakes
  all variants (not cheapest). Pre-existing on `main`; the anchor never touches it. Relevant only to any
  cost/budget layer built on top of from-zero.
- **#4 observability `Utilization`** — pending-blind reporting ratio; not a scaling bug (design § bugs
  #4). Reconcile in the coordination-doc rewrite, not here.
- **Dean's "always-fallback-from-all-analyzers" idea** — a design-doc-level change to how each analyzer
  populates results for every variant (§2b). Scope separately if pursued.

[↑ TOC](#toc)
