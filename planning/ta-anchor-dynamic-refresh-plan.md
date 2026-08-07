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

**Setup — first action, before C1 (Dean, 2026-08-06).** The worktree was cut off `f6485980`, but PR-1's
tip may have advanced since. **Re-base this branch once onto the current `ta-anchor-refactor-v2` tip
before writing any code** — target the *moving branch ref*, not the pinned `f6485980` SHA — so PR-2
starts stacked on the latest PR-1 state:
```
# from the ta-anchor-dynamic-refresh worktree, after verifying pwd + branch
git rebase ta-anchor-refactor-v2      # PR-1's local branch tip (not pushed to origin)
```
Resolve any conflicts, run the full pre-push battery (`make test` / `gofmt` / `make lint` / `go build`),
then begin C1. Do **not** push after this rebase (coders never push; `origin/ta-anchor-dynamic-refresh`
gets force-updated later by the planner/Dean). This one-time pre-C1 rebase is **separate** from the
later force-push-after-re-base tied to PR-1's close-out — that second re-base happens whenever PR-1
rewrites C1–C5, and is coordinated then.
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

- [§0 Status — scope & the indivisible-PR decision](#0-status--scope--the-indivisible-pr-decision) L69:133
- [§1 Scope — the both-enabled dynamic case + commit map](#1-scope--the-both-enabled-dynamic-case--commit-map) L134:196
  - [§1.1 Commit map (C1–C10)](#11-commit-map-c1c10) L171:196
- [§2 The four combine-arithmetic bugs](#2-the-four-combine-arithmetic-bugs) L197:293
- [§2b Live-gate the combine input (VG-up + N8 + N7) — lands in C7](#2b-live-gate-the-combine-input-vg-up--n8--n7--lands-in-c7) L294:366
- [§2c (a)/(b) → plain-prose notation cleanup — lands in C8](#2c-ab--plain-prose-notation-cleanup--lands-in-c8) L367:396
- [§2d Score semantics — the dominance rule, one combine helper, four call sites — lands in C6a–C6d](#2d-score-semantics--the-dominance-rule-one-combine-helper-four-call-sites--lands-in-c6ac6d) L397:705
  - [§2d.1 What Score means (decided)](#2d1-what-score-means-decided) L404:423
  - [§2d.2 The combine rule (dominance weighting)](#2d2-the-combine-rule-dominance-weighting) L424:471
  - [§2d.3 The helper — one function, and the duplicate loop that must die](#2d3-the-helper--one-function-and-the-duplicate-loop-that-must-die) L472:534
  - [§2d.4 Missing / non-participating entries](#2d4-missing--non-participating-entries) L535:601
  - [§2d.5 Fair share (Bug #5) — currency](#2d5-fair-share-bug-5--currency) L602:659
  - [§2d.6 T1.4 — the existing Score test (rewrite; do not retire)](#2d6-t14--the-existing-score-test-rewrite-do-not-retire) L660:686
  - [§2d.7 Why this is safe to land here](#2d7-why-this-is-safe-to-land-here) L687:705
- [§2e k_sat is not a threshold — TA must use saturation's target — lands in C10](#2e-ksat-is-not-a-threshold--ta-must-use-saturations-target--lands-in-c10) L706:848
  - [§2e.1 Three constants; TA mirrored the wrong one](#2e1-three-constants-ta-mirrored-the-wrong-one) L715:750
  - [§2e.2 The fix — resolve once, thread to four sites](#2e2-the-fix--resolve-once-thread-to-four-sites) L751:787
  - [§2e.3 Effect, churn, ordering](#2e3-effect-churn-ordering) L788:848
- [§3 Per-iteration dynamic refresh — lands in C2](#3-per-iteration-dynamic-refresh--lands-in-c2) L849:883
- [§4 Ship gate & tests](#4-ship-gate--tests) L884:994
- [§5 Dev-guide sections (named, per commit)](#5-dev-guide-sections-named-per-commit) L995:1080
- [§6 Semantic-pivot grep steps](#6-semantic-pivot-grep-steps) L1081:1155
- [§7 Out of scope / deferred / separable follow-ons](#7-out-of-scope--deferred--separable-follow-ons) L1156:1206

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
- **Score semantics + the combine helper (Dean, 2026-08-06 — "Lets fix the score logic… The logic needs
  fixing for multi-analyzers, so do it"):** analyzer `Score` is a **belief weight over votes**, applied in
  the combine (stage 1) and nowhere else; model `priority` is the only fair-share weight (stage 2). The
  combine collapses into **one helper**, and `Score` leaves `fairShareValue` and the `sortVariantsForScaleDown`
  tie-break. Full spec: **§2d**. This expands the old single C6 into **C6a–C6d**.

- **k_sat is not a threshold — TA must use saturation's target (Dean, 2026-08-07: "*Use the same target as
  sat. This looks like a small trivial bug. Fold it in. Too many small PRs already*"):** the throughput
  analyzer evaluates per-replica capacity at a hard-coded `DefaultKSat = 0.85`, which mirrors
  `DefaultScaleUpThreshold` — a **watermark** — instead of saturation's k_sat `KvCacheThreshold` (0.80).
  Folded in here rather than split into its own PR. Full spec: **§2e**. Adds **C10**.

**Stack order note (2026-08-06, revised 2026-08-07).** C1–C5, C7 and C8 have **already landed** on the
branch; C6 was paused on the Score question (coder handoff `plan__ta-anchor-c6-fairsharevalue-score.md`,
answered in §2d). So the git order is **C1–C5 → C7 → C8 → C6a–C6d → C10 → C9** — the C-labels are stable
identifiers, not the commit sequence. Do not renumber landed commits. C10 is deliberately late: see §2e
§ Ordering.

**Coding is NOT gated on PR-1 merging** (Dean, 2026-08-06) — PR-2 is **stacked on PR-1's branch and
worked in parallel**. Start C1 on Dean's explicit go-ahead (per "Discuss before implementing"). **First
action before C1: the one-time pre-C1 rebase onto the current `ta-anchor-refactor-v2` tip** (see the
Setup step in the header) — the worktree was cut off `f6485980` and PR-1's tip may have moved since.
Then expect a *second* re-base onto PR-1's tip when its close-out rewrites C1–C5. The correctness
dependencies PR-2 builds on (`bindingAnchor`, `votingResults`, the `Enabled` ballot tag) are all present
at the base tip.

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

### §1.1 Commit map (C1–C10)

Ordered stack; each is DCO-signed, gates-green-after-every-commit in an isolated worktree. "Red-first"
= add the fixture failing before the fix, passing after.

| # | Commit scope | Red-first test | Dev-guide (§5) | Detail |
|---|---|---|---|---|
| **C1** | Admit two-vote path + **N2** deterministic binder tie-break (sat-if-present, else lowest index) — replace nil-on-ambiguity in `bindingAnchor`. Enabler. | two-binder fixture asserts tie-break, not hold | pipeline "How results combine" | §1 item 4 |
| **C2** | **Per-iteration dynamic refresh** — re-invoke the Phase-2 getter each allocation iteration so the per-(role,variant) binding re-selects as remaining demand shifts. | fixture where binding flips mid-water-fill | pipeline "Scale-up path", "Data flow per optimize cycle" | §3 |
| **C3** | **Bug #2** `roleAggRemaining` — max in replica space (`max_i rd_i`), not raw mixed-unit RC. | two-vote MAX fixture | sat-config "Shared aggregation helpers" | §2 #2 |
| **C4** | **Bug #1** `allocateForModelPaired` decrement — per-analyzer `k·PRC_i` (or replica units), not `k·PRC_sat` uniformly. Paired with C3. | two-vote allocation fixture | pipeline "Scale-up path" | §2 #1 |
| **C5** | **Bug #3** rescale water-fill + `roleDemandGPUs` combined `max_i ceil(demand_i/PRC_i)`; **+ N3** nil-guard hardening in `rescaleModelDecisions`. | two-vote rescale fixture | pipeline "Optimizer internals" | §2 #3, §7 N3 |
| **C6a** | **`combineVotes` helper + collectors** — one combine core; **merge** `roleBottleneckReplicas` + `bindingIndexForRole` (delete the duplicate loop); retrofit `roleAggRemaining` / `roleDemandGPUs` / `safeRemovalReplicasForRole` onto it. Uniform scores ⇒ **byte-identical**. | helper unit table (uniform / dominant / bounded / single / empty); 3-analyzer non-participant fixture (finding (a)) | pipeline "How results combine" | §2d.3 |
| **C6b** | **Score dominance weighting on** — the `(sᵢ − s_bind)⁺` term; rounding **once** at the call site (`ceil` up, `floor` down). | 10-vs-5 @ scores 1/2 ⇒ 9 up, 6 down | pipeline "How results combine"; sat-config score semantics | §2d.2 |
| **C6c** | **Bug #5** fair-share — **5** lock-step sites (i) `fairShareValue` (+ signature: it must receive the picker's variant slice) / (ii) `fairShareCap` (`prcRef` rescale, not bare `ceil(target)`) / (iii) `sortVariantsForScaleDown` / (iv) `allocateForModel`'s picker-state clamp / (v) `fairShareValue`'s raw-unit fallback; **Score out** of fsv and the scale-down tie-break; finding **(b)** participation filter. | fsv ordering + `mean` fixtures; multi-role cap fixture; **fall-through cap** fixture (two variants, one role, cheaper one infeasible); fallback-currency fixture; **T1.4 rewrite**; goldens re-run | pipeline "Fair-share iteration", "Scale-down path"; **quota-limiter "Fair-share interaction"** (3rd copy of the fsv formula) | §2 #5, §2d.5, §2d.6 |
| **C6d** | Finding **(c)** — **per-variant** veto re-check in `safeRemovalReplicasForRole`: a **live** analyzer with `RoleSpare[role] <= 0` (key *present*) blocks removal, PRC-blind **and** score-blind. The entry gate already covers role *entry*; the reachable defect is **mid-loop**, after `applyDeallocationForRole` drives a spare to 0. **Not** a synthetic 0-vote — post-C6b a vote cannot encode a veto. (Distinct from C7's N7 *abstain*.) | **end-to-end** via `scaleDownRoleIterated`: one role, **two** variants, live objector sizing only the first-shed one (red: 2nd variant's replicas removed; green: held) + outscored-objector variant + N7 control | pipeline "Scale-down path" | §2d.4 (c) |
| **C7** | **Liveness** — `votingResults` `Enabled` → `Enabled && Live` (VG-up/D2); **DROP** the `bindingAnchor` sizing-fallback (N8, rewrites PR-1 Test 2 v2 110→0); **N7** abstain-vs-veto default abstain. | stale-enabled scale-up + role-coverage-mismatch fixtures | pipeline "How results combine" + "Scale-from-zero"; sat-config "How Scale-Up Triggers Work", "Saturation as the Identity Carrier" | §2b |
| **C8** | **§2c notation cleanup** — strip `(a)/(b)` letters, keep descriptive prose. Comments/docs only, byte-identical behavior. | none (green byte-for-byte) | pipeline + sat-config (see §2c line list) | §2c |
| **C10** | **k_sat is configuration, not a constant** — TA evaluates per-replica capacity at saturation's configured k_sat (`KvCacheThreshold`, default 0.80) instead of the hard-coded `DefaultKSat = 0.85`, which mirrored a *watermark*. Resolver + 4 threaded sites; `DefaultKSat` **deleted**. Not a combine bug; a correctness/configurability fix — the numeric shift is sub-1% at default config, *not* the ~6% an early draft claimed (§2e.3). | `resolveKSat` unit table; TA `Analyze` fixture with `KvCacheThreshold: 0.5` asserting PRC tracks config (red: pinned at 0.85), expected **2618.9**, **tolerance ≤1% relative** — the file's `muSat*0.10` idiom is *above* the 6.17% bound and stays green at 0.85 (§4) | throughput-analyzer (5 named locations) | §2e |
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
- **#5 — `fairShareValue` sums (`Σ_i`) where design wants (`max_i`) → C6c.** Limited/fair-share mode only
  (the cost-aware unlimited path does not use fsv). **Five** **lock-step** sites that must change together
  or units desync — sites (iv) and (v) are not in the design doc's list: (iv) was found while verifying
  §2d.5, (v) by the reviewer 2026-08-07 (verified against source, plan-spec corrected before C6c was
  written; §2d.5 *Reference PRC*).
  The Score decision that this bug's fix depended on is **settled in §2d** (Score leaves fsv entirely);
  the old "× Score only if Score is meant to weight budget" hedge is **withdrawn**.
  - **(i) `fairShareValue` (`greedy_score_optimizer.go:73`)** — replace `Σ_i Score_i × Σ_role
    ps[i][role]` with the combined **replica-space** per-role demand
    `Σ_role combineVotes(votesFromPickerState(…, role, v_role), up=true)`, × `priority`, **no Score**.
    `v_role` = the role's first `sortByCostEfficiencyAsc` candidate with `PRC > 0` (§2d.5 (i)).
    **Signature change required:** today's `fairShareValue(priority, s, ps, roles)` receives no variant
    list, so it cannot reach `v_role`. Hand it the **same** `[]domain.VariantCapacity` the picker
    iterates (`w.anchor.VariantCapacities`) — not a separately-sourced copy — so both sides select an
    identical `v_role`; see §2d.5 *Reference PRC*. All three call sites change together (`:133` initial,
    `:348` / `:350` recompute).
  - **(ii) `fairShareCap` (`greedy_score_optimizer.go:423`)** — `ceil(target / vc.PerReplicaCapacity)`
    divides the fsv-unit `target` (`= w.remaining − mean`, `:273`) by **that candidate's own** PRC, on
    every loop iteration. Once `target` is replica-space (fix i) the divide is the second half of a
    double-conversion — but **`ceil(target)` is correct only when the candidate the loop lands on *is*
    `v_role`**, and the picker skips candidates on two conditions `v_role` selection does not model
    (`gpusAvail < gpusPR` — the cheaper accelerator pool is dry, `:420`; `headroom <= 0` — the cheaper
    variant is at `MaxReplicas`, `:427`). Both `continue`, and the cap is then measured in `v_role`'s
    capacity but applied to a variant with different capacity. **Fix:** rescale per candidate —
    `capN_candidate = ceil(target × prcRef / vc.PerReplicaCapacity)` with `prcRef` = `v_role`'s PRC. For
    `vc == v_role` the ratio is exactly 1 and this **is** `ceil(target)`, so §2d.5's neutrality
    arithmetic and (i)'s double-conversion reasoning stand unchanged; the ratio only bites on
    fall-through. `prcRef` needs **no new closure parameter** — the closure already computes
    `sortByCostEfficiencyAsc(roleVCs)`, and `prcRef` is that sorted slice's first `PRC > 0` entry, i.e.
    `v_role` by construction (§2d.5 *Reference PRC*).
  - **(iii) scale-down tie-break `sortVariantsForScaleDown` (`cost_aware_optimizer.go:161-184`, weighted
    sum `:168`)** — a **second** `Σ_i Score_i × PRC_i[v]` site. Lower severity (orders scale-down
    candidates within a role, never sizes), but the same wrong-operator/mixed-unit pattern; sweep here
    — drop the Score factor and tie-break on the **binding** analyzer's PRC (`combineVotes` binder,
    `up=false`), then name ascending. (Note: this site is **also** touched by C7's landed N7 role-coverage
    decision — coordinate both edits. C6d lands in the same scale-down path but in a *different* function,
    `safeRemovalReplicasForRole`; it does not touch this tie-break.)
  - **(iv) `allocateForModel`'s picker-state clamp (`greedy_score_optimizer.go`, the
    `if ps[i][role] > target { ps[i][role] = target }` loop, ~`:285-291`) — NEW.** It clamps
    **raw-capacity** `ps` against `target`. The moment `target` becomes replica-space the clamp truncates
    every role to a handful of capacity units. Convert the clamp to replica space (or clamp the combined
    per-role replica count instead) in the same commit. **This is the site that makes #5 a units bug and
    not merely a shape bug** — it is inert today only because `target` is the *sum over roles*, so each
    individual role's value is already ≤ it.
  - **(v) `fairShareValue`'s own fallback (`greedy_score_optimizer.go:78-92`) — NEW.** Taken when
    `priority × weighted <= 0`, it returns `max_role ps[i][role]` in **raw demand units**. After (i) the
    function would return replica-space on its primary path and demand-space on its fallback — the exact
    desync this bug is about, inside the very function being rewritten — and that raw value then flows
    into (ii)'s cap and (iv)'s clamp, mis-sizing by a factor of PRC. **Fix:** make the fallback the
    primary expression with the `priority` factor dropped:
    `Σ_role combineVotes(votesFromPickerState(…, role, v_role), up=true)`. That fixes the currency and
    incidentally removes a pre-existing asymmetry — the fallback **maxes** over roles where the primary
    **sums**, so a P/D model's fallback is systematically smaller than its primary value (pre-existing,
    not caused by C6c). **Keep the fallback; do not delete it** — deletion would need a §4b DEPRECATED
    classification and would change the `fsv > 0` admission at `:134` for hand-built zero-priority
    fixtures. Post-C6c reachability is effectively **nil in production**: `ApplyDefaults` rewrites
    `Priority == 0` to `DefaultPriority = 1.0` (`config/saturation_scaling.go:275-276`) and validation
    rejects negatives, and Score has left fsv — so the guard can only trip on all-zero remaining demand,
    where both paths return 0. No golden can move on this site; fix it for honesty, not for behavior.
    Also **rewrite the doc comment at `:53-60`**, which states
    `fsv = priority × Σᵢ Score_i × Σ_role pickerState[i][role]` — it names Score.

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

<a id="2d-score"></a>
## §2d Score semantics — the dominance rule, one combine helper, four call sites — lands in C6a–C6d

Origin: Dean's directive 2026-08-06 ("*Lets fix the score logic. We already did all the work. The logic
needs fixing for multi-analyzers, so do it*"), triggered by the coder's blocking question in
`plan__ta-anchor-c6-fairsharevalue-score.md`. That handoff asked which of three formulas to implement;
this section is the answer (**option 1 — drop Score from fsv — with the T1.4 fixture rewritten**, §2d.6).

### §2d.1 What Score means (decided)

`analyzers[].score` (public YAML, default `1.0`, `0` coerced to `1.0` in `config/saturation_scaling.go`)
is a **belief weight over votes** — how much to trust one analyzer's replica opinion against another's.
It is **not** a budget multiplier and **not** a priority. Model `priority` (default `1.0`) is the only
fair-share weight. `K2Priority` is an unrelated name collision — **do not touch it**.

Two stages, per Dean: **(1) combine analyzers with scores** → one replica number per (variant, role);
**(2) fair-share models with priorities.** Score appears only in stage 1; `priority` only in stage 2.

Consequences:
- **Score is REMOVED from `fairShareValue` and from the `sortVariantsForScaleDown` tie-break.** Both are
  stage-2 / ordering sites that today multiply by Score, double- and triple-counting a stage-1 quantity.
- **Rejected — "Score as an aggregate budget multiplier"** (`fsv = priority × (Σᵢ Scoreᵢ) × …`, the coder's
  option 3). It reproduces T1.4's existing expectation, but it makes a model's GPU claim grow with the
  *number of analyzers configured for it*, which is not a property of the workload. Rejected 2026-08-06;
  do not re-raise without a design-doc change.

[↑ TOC](#toc)

### §2d.2 The combine rule (dominance weighting)

Per (variant, role), over **participating votes only** (§2d.4):

```
vᵢ  = replicas analyzer i implies    (demandᵢ/PRCᵢ scale-up;  spareᵢ/PRCᵢ scale-down)
sᵢ  = analyzer i's Score  (> 0)
e   = max vᵢ (scale-up)  |  min vᵢ (scale-down)      ← the binder's vote
s_e = the binder's Score

v* = e  −  Σᵢ (e − vᵢ)·(sᵢ − s_e)⁺ / Σⱼ sⱼ            (x⁺ = max(x, 0))
```

Then round **once**, at the call site: `ceil(v*)` scale-up, `floor(v*)` scale-down — **never per element**
(Dean, 2026-08-06: "*ceil belongs after the weighting, not per element*").

**One expression serves both directions.** For scale-down `e` is the *min*, so `(e − vᵢ) ≤ 0` and the
subtraction *adds*. `up` selects only the extremum and the rounding — there is no second formula and no
sign flip in the body.

Invariants (the helper's unit table asserts each):
1. **Uniform scores ⇒ plain extremum.** Every `(sᵢ − s_e)⁺ = 0` ⇒ `v* = e` — *exactly* today's `maxᵢ` /
   `minᵢ`. This is why C6a is behavior-preserving and why the #1513 goldens cannot move on it.
2. **Dominant score ⇒ that analyzer's own number.** `s_k → ∞` ⇒ `v* → v_k`.
3. **Bounded: `v* ∈ [min vᵢ, max vᵢ]`, always.** Because `s_e ≥ 0`, `Σᵢ(sᵢ − s_e)⁺ ≤ Σⱼ sⱼ`, so the
   correction can never exceed `|e − v_opposite|`. The combine can never invent a number no analyzer asked
   for.
4. **Monotone in each `sᵢ`** — raising a dissenter's score pulls the result toward its vote.
5. Single vote ⇒ `v* = v₀`. No participating vote ⇒ `(0, −1)` ⇒ the caller holds.

**Worked example (Dean's, 2026-08-06).** TA wants 10 replicas (score 1), saturation wants 5 (score 2).
`e = 10` (TA binds), `s_e = 1`, `Σs = 3`. Correction `= (10−5)·(2−1)/3 = 5/3 = 1.667`.
`v* = 8.333` → **ceil ⇒ 9 replicas**. Reproduces Dean's 8.33 exactly.
A plain weighted average would give **6.67** — rejected, because it lands *below every analyzer's own
lower bound reasoning* in cases where the binding constraint genuinely needs more than the trusted
analyzer noticed. (Dean's literal phrasing, "max − weighted average of the deltas", is algebraically
identical to that plain weighted average: `e − Σwᵢ(e−vᵢ)/Σwᵢ ≡ Σwᵢvᵢ/Σwᵢ`. Weighting the deltas by
**score excess over the binder** rather than by raw score is what produces 8.33 and satisfies 1–3 above.)

**Scale-down mirror** (scores swapped so the correction is visible): TA says 10 replicas are removable
(score 2), saturation says 5 (score 1). `e = 5` (saturation binds — the conservative vote), `s_e = 1`,
`Σs = 3`, correction `= (5−10)·(2−1)/3 = −1.667` ⇒ `v* = 6.667` → **floor ⇒ 6 removable**. Still ≤ TA's
own 10 and ≥ saturation's 5. When the *conservative* analyzer is also the higher-scored one, every
`(sᵢ − s_e)⁺ = 0` and the result stays at the safe extremum — the direction that matters for safety needs
no special case.

[↑ TOC](#toc)

### §2d.3 The helper — one function, and the duplicate loop that must die

The same combine loop is written out **six times** today, and two of them —
`roleBottleneckReplicas` and `bindingIndexForRole` — are the *identical* loop with the *identical*
tie-break, one returning the count and the other the argmax, **maintained independently**. That is a
latent desync now and a guaranteed one once the score term lands. Extract one core:

```go
// replicaVote is one analyzer's opinion in a single (variant, role) combine,
// already converted to replica space. Value is real-valued — rounding happens
// once, at the caller, after the weighting.
type replicaVote struct {
	Index int     // ballot index — binder identity and deterministic tie-break
	Value float64 // replicas: demand/PRC (scale-up) or spare/PRC (scale-down)
	Score float64 // belief weight; > 0 (config coerces 0 → 1.0)
}

// combineVotes reduces one (variant, role) ballot to a single real-valued replica
// count plus the index of the binding analyzer. up=true takes the max (scale-up
// demand), up=false the min (scale-down safe removal). Higher-scored analyzers pull
// the result toward their own vote without it ever leaving [min, max]; uniform
// scores collapse to the plain extremum. Ties keep the lowest index. Returns
// (0, -1) when no vote participates.
func combineVotes(votes []replicaVote, up bool) (value float64, binder int)
```

Returning **both** the value and the binder from one evaluation is the load-bearing part: the count and
"which analyzer is binding" can no longer disagree, and the binder identity is what §3's per-iteration
refresh writes onto the anchor.

Collectors — one thin function per state source, each applying the **same** participation filter
(`e.Result != nil`, `prcForVariant(e.Result, variant) > 0`, its own state present):

```go
func votesFromPickerState(s []NamedAnalyzerResult, st RolePairedState, role, variant string) []replicaVote // scale-up (picker)
func votesFromTotalDemand(s []NamedAnalyzerResult, role, variant string) []replicaVote                     // rescale
func votesFromRoleSpare(s []NamedAnalyzerResult, role, variant string) []replicaVote                       // scale-down
```

Because the filter lives in the collectors, `Σⱼ sⱼ` runs over participating votes only **structurally**,
not by comment — finding (a) below is then unrepresentable.

**Retrofit map** (grep by symbol — line numbers drift):

| Site | Today | After |
|---|---|---|
| `roleBottleneckReplicas` (`analyzer_helpers.go`) | own `max ceil(state/prc)` loop | `ceil(combineVotes(votesFromPickerState(…), true))` |
| `bindingIndexForRole` (`analyzer_helpers.go`) | the **same** loop, returns argmax | **DELETED** — callers take `combineVotes`' second return |
| `roleAggRemaining` | binder's raw remaining via `bindingIndexForRole` | binder from `combineVotes`; **Bug #2** ⇒ replica space |
| `roleDemandGPUs` (`rescale.go`) | own `maxᵢ ceil(demandᵢ/PRCᵢ)` loop | `ceil(combineVotes(votesFromTotalDemand(…), true))` (**Bug #3**) |
| `safeRemovalReplicasForRole` | own `minᵢ floor(spareᵢ/PRCᵢ)` loop | `floor(combineVotes(votesFromRoleSpare(…), false))` |
| `sortVariantsForScaleDown` (`cost_aware_optimizer.go`) | `Σᵢ Scoreᵢ·prcForVariant(…)` tie-break | Score dropped; binder's PRC (§2d.5 (iii)) |

`needsScaleDownForRole` keeps its own all-agree **boolean** shape (it is a veto, not a magnitude) but must
use the same participation filter — see finding (c).

Bugs #1–#3 (C3/C4/C5, already landed) each fixed one of these loops in place. C6a does **not** re-open
those fixes: it hoists their now-agreeing arithmetic into the shared core and deletes the duplicate. If a
landed fix turns out to disagree with the extracted core, that is a finding — stop and write a `plan__`
handoff rather than quietly re-deciding it inside C6a.

[↑ TOC](#toc)

### §2d.4 Missing / non-participating entries

Analyzer *i* **does not participate** in a (variant, role) combine when it has no `Result`, no
`VariantCapacities` entry for the variant (`prcForVariant` returns `0` — note it returns `0` both for
"absent" and for a genuine zero), or no state for that role. A non-participant is excluded from the
extremum, from the correction sum, **and from `Σⱼ sⱼ`**.

Walking this (2026-08-06) produced three findings. Dean approved acting on **(b)** and **(c)**.

- **(a) `Σⱼ sⱼ` over participating votes only — handled structurally, assert it.** If non-participants
  counted in the denominator, a configured-but-silent analyzer would dilute every correction toward the
  binder: an analyzer that says *nothing* would make the system trust the binder *more*. The collector-side
  filter makes this automatic. Pin it: a 3-analyzer fixture whose third entry has no PRC for the variant
  must produce the **same** number as the equivalent 2-analyzer fixture.
- **(b) `fairShareValue` counts demand the pipeline cannot act on — FIX (participation filter), Dean-approved.**
  `fairShareValue` skips only `e.Result == nil`; it has **no PRC filter**, so an analyzer with
  `RequiredCapacity > 0` and no usable PRC for any variant still inflates the model's fsv. Full traced
  consequence: the model sorts to the front of the fair-share queue on an unactionable claim →
  `allocateForModel` can allocate nothing against it (`fairShareRolePick` skips `PerReplicaCapacity <= 0`)
  → `allocated == false` → the model is **dropped for the rest of the cycle** at `fairShareScaleUp`'s
  `w.remaining = -1`. Not a spin, but the model is **under-served**, and every other model's `mean` was
  distorted for the iterations it was in the running. **Fix:** fsv counts only demand that has a PRC to
  convert it — the same participation filter as the combine. (T1.4's fixture is exactly this shape — §2d.6.)
- **(c) A live analyzer can be over-ridden on scale-down — FIX, and the trigger is *mid-loop*, not at role
  entry (re-derived 2026-08-07 on a reviewer finding; the original wording described an unreachable state).**

  **What is already enforced.** `needsScaleDownForRole` (`analyzer_helpers.go:683-702`) *already* implements
  the PRC-blind role-level veto, at role granularity: it skips non-live entries, abstains on
  `Result == nil || RoleSpare == nil` and on a missing key, and returns **false** for a live entry whose
  `RoleSpare[role] <= 0` — **without ever consulting PRC**. `scaleDownRoleIterated:439` turns that into
  `continue`, skipping the role in full. So a fixture that merely *constructs* `RoleSpare[role] = 0` and
  runs the pipeline is held **by the gate**, not by anything C6d adds, and a unit test calling
  `safeRemovalReplicasForRole` directly with that state exercises a state the pipeline cannot deliver at
  role entry. **A green test of that shape would pass for the wrong reason** — this is the trap to avoid.

  **What is reachable.** `scaleDownVariantSet` (`cost_aware_optimizer.go:124-155`) walks **all** of the
  role's variants, calling `maxRemovable(vc)` per variant and `applyDeallocationForRole` after each
  removal — which **decrements** every analyzer's `RoleSpare[role]` by `n × PRC_i[v]`, clamping at 0
  (`:658-661`). The gate runs **once per role, before the loop**, and is never re-checked. So a role spare
  that was positive at entry can reach 0 *during* the loop, and from that moment the objection is silently
  discardable in **two** ways:

  1. **PRC absence.** Role R, variants v1/v2; live analyzer X has `RoleSpare[R] = S > 0` (gate passes) and
     PRC for **v1 only**. v1 sheds first ⇒ X's role spare hits 0. On v2, `votesFromRoleSpare` drops X at
     `:499-501` (`prc <= 0`), so X's now-explicit *"no spare left in this role"* is excluded from the
     combine, the others' spare wins, and v2's replicas come off **over X's objection**. Realistic: a
     variant with no observed metrics yet is absent from that analyzer's `VariantCapacities` while still
     present in the anchor.
  2. **Being outscored — new with C6b, and it does not need partial PRC.** Even when X *does* size the
     variant and therefore votes `0`, a `0` vote is no longer absolute under dominance weighting: with
     `e = min vᵢ = 0`, `s_e = s_X`, and another voter at `10` with `s_Y > s_X`, the correction is
     `(0−10)(s_Y−s_X)/(s_X+s_Y) < 0`, so `v* = +10(s_Y−s_X)/(s_X+s_Y) > 0` and `floor(v*)` can be ≥ 1.
     **A vote cannot encode a veto.** (Only `s_Y ≤ s_X` leaves `v* = 0`.)

  **Fix — a per-variant veto re-check, PRC-blind *and* score-blind.** `safeRemovalReplicasForRole` returns
  **0**, before combining, if any live entry with `Result != nil`, `RoleSpare != nil` and the key **present**
  has `RoleSpare[role] <= 0`. Do **not** express this as a synthetic 0-vote inside `votesFromRoleSpare` —
  per (2) above a vote is not a veto after C6b. Using the *same predicate* as the entry gate makes the gate
  a cheap early-out for the whole role and this the actual enforcement point; say so in the doc comment so
  the duplication reads as intentional rather than as a copy to be de-duplicated later.

  This stays **distinct from N7** (landed in C7), which reads a *missing* `RoleSpare[role]` as an
  **abstain**: (c) is a *present, zero* role-level opinion. N7's abstain is unchanged —
  `RoleSpare == nil` or key missing ⇒ **abstain**; key present and `<= 0` ⇒ **veto**.

[↑ TOC](#toc)

### §2d.5 Fair share (Bug #5) — currency

fsv's currency must match every consumer of `target`. See §2 #5 for the four sites (i)–(iv) and their
edits; (iv) is new, found while verifying this section, and is the one that turns #5 from a shape bug into
a units bug.

**Why the #1513 goldens stay green — verified 2026-08-06, not assumed.** For a single analyzer with one
PRC per variant, `Σ_role RC[role] / PRC ≡ Σ_role (RC[role]/PRC)`: the currency change is an exact monotone
rescale of fsv by `1/PRC`, and `fairShareCap` divides that rescale straight back out, so the cap number is
unchanged. The only quota-constrained golden (`optimizer_characterization_test.go`, "Commit 4 —
quota-constrained optimizer golden", scenario C1) is **single-model, single-role, single-variant,
priority 1, Score 1**: fsv `50000 → 5`, cap `ceil(50000/10000)=5 → ceil(5)=5`, and the namespace budget
still binds at 2 replicas. Unchanged. Every other golden runs either `CostAwareOptimizer` (never touches
fsv) or `unlimitedConstraints` with one active model, where fsv's magnitude only has to stay `> 0`.

**What the currency fix genuinely does change:** multi-model, quota-constrained allocation where models
have different PRCs — `computeMean` / `sortByRemainingDesc` compare tokens/s against req/s today. That is
the bug being fixed, and #1513 does not cover it. Add fixtures for it (§4). **Run the goldens per commit
and report; if one moves, stop and write a `plan__` handoff — do not rewrite a golden to accommodate this
change.**

**Reference PRC — one selection rule, one slice (added 2026-08-07).** Sites (i) and (ii) both need
`v_role`, and they must agree *exactly*. The rule is identical on both sides — the role's first
`sortByCostEfficiencyAsc` candidate with `PRC > 0`, which is simply `sorted[0]`, because
`costEfficiency` returns `math.MaxFloat64` for `PRC <= 0` (`cost_aware_optimizer.go:238-243`) and so
sorts those last. Feed both sides the **same** `w.anchor.VariantCapacities` slice: `sort.Slice` is
deterministic for a given input, so identical input ⇒ identical `sorted[0]` ⇒ `prcRef` bit-identical to
`v_role.PerReplicaCapacity` ⇒ (ii)'s ratio is exactly `1.0` and `ceil(target × 1.0)` reproduces
`ceil(target)` with no float drift. A separately-sourced copy, or a different role filter, re-opens the
mismatch through a second door. (`sort.Slice` is not *stable*, so equal-efficiency ties resolve
deterministically-but-arbitrarily; same-slice-same-rule makes that harmless. A name-ascending tie-break
would be more robust — optional hardening, not required here.)

**The fall-through case (ii) must survive.** `v_role` is the *cheapest-efficiency* candidate, and the
picker does not always allocate it. One role; `v1` PRC 10000 (cheapest efficiency), `v2` PRC 2000;
`target` 50000 demand ⇒ 5 replicas of `v1`. Now exhaust `v1`'s GPU pool (or put `v1` at `MaxReplicas`):

| | cap computed for `v2` |
|---|---|
| today | **25** = `ceil(50000/2000)` |
| (i)+(ii) without the rescale | **5** = `ceil(5)` |
| (i)+(ii) with the `prcRef` rescale | **25** = `ceil(5 × 10000/2000)` ✓ |

A silent 5× under-allocation, on exactly the path the cost-aware optimizer exists to serve — two
accelerator types per role, fall through to the pricier one when the cheap pool runs dry — and
`headroom <= 0` is the *normal* late state of a scale-up loop, not an edge case. **Why the existing
suite misses it:** every #1513 golden and this section's worked example above are
single-variant-per-role, where `v_role` is the only candidate and the error is identically zero; §4's
other requested fsv fixtures vary PRC **across models**, not across variants within one role. §4 adds
the fixture that catches it.

The blunter alternative — keep fsv in demand space and fix only the `Σᵢ`→combine shape — is
**rejected**: the combine has to be in replica space for a `max` across analyzers with different
capacity units to mean anything (§2d.3). The currency change is right; it just has to survive contact
with the second candidate.

[↑ TOC](#toc)

### §2d.6 T1.4 — the existing Score test (rewrite; do not retire)

`greedy_score_optimizer_test.go` T1.4 ("non-uniform Score across two analyzers drives fair-share ordering",
~L881) asserts Model A (fsv 60000; saturation Score 1.0 + throughput Score 2.0) out-prioritizes Model B
(fsv 20000; saturation only). Its throughput entry has an **empty `VariantCapacities`** while its comment
claims it "shares rA's variant capacity" — the comment describes a fixture that was never built. The test
therefore pins **exactly the two behaviors this section removes**: Score inflating fsv, and unactionable
demand counting toward fsv (finding (b)).

**Rewrite it** — the *premise* (non-uniform Score changes the outcome) stays valid; the *mechanism* moves
from stage 2 to stage 1. Dean-approved shape:
- Give the throughput entry a **real** `PerReplicaCapacity` for `a-v1`, consistent with the anchor data
  contract (a voting analyzer sizes the variants it votes on).
- Choose demands and PRCs so the two analyzers **disagree on the replica count** and the dominance
  correction lands where `ceil` cannot swallow it — e.g. votes of 10 and 5 with scores 1 and 2 ⇒ 8.33 ⇒ 9,
  distinguishable from both 10 and 5. **Counts in the low single digits round the whole effect away**; use
  ≥ ~10 replicas of spread.
- Assert the **combine** outcome (the replica number *and* the binder index), and keep a fair-share
  ordering assertion driven by **priority**, not Score.
- Add the uniform-score control asserting the plain extremum.

Under the rewritten fixture the old expectation (A ≻ B *by Score*) no longer holds, and is not supposed
to: with equal priorities and equal demands two models tie regardless of how many analyzers each has.
State that in the commit message (CODER-CONVENTIONS §4a — describe it in prose, no plan-doc identifiers).

[↑ TOC](#toc)

### §2d.7 Why this is safe to land here

- Both shipped configs set `score: 1.0`. The **only** non-unit Score in the tree is T1.4's fixture, so
  non-uniform Score is **unreachable in production today** (Dean, 2026-08-06: "*we don't expect any non
  default scores… this lowers the risk*").
- Uniform scores collapse the new arithmetic to the old extremum exactly (§2d.2 invariant 1) ⇒ **C6a is a
  behavior-preserving refactor** and **C6b turns on arithmetic no shipped config reaches**.
- The user-visible risk concentrates in **C6c** (fsv currency + Score removal), which is why it is its own
  commit, with the goldens re-run and dedicated `mean`/ordering fixtures.
- Scope discipline: this is the "correct calculation" for multi-analyzer combine, not new functionality —
  Dean, 2026-08-06: "*we should change the plan back to what was unless we know we had a math/logic bug
  earlier… The correct calculation is always the same.*" Recomputation savings when the binder is unchanged
  are **not** a goal (§3 refreshes unconditionally; memoization stays an implementation detail).

[↑ TOC](#toc)

---

<a id="2e-ksat"></a>
## §2e k_sat is not a threshold — TA must use saturation's target — lands in C10

Folded in by Dean 2026-08-07 ("*Use the same target as sat. This looks like a small trivial bug. Fold it
in. Too many small PRs already*"). Not a combine-arithmetic bug — a **capacity-definition** bug inside the
throughput analyzer — but it belongs here because PR-2 is the PR that makes TA's vote count *against
saturation's*, and a shared definition of "full" is the precondition for comparing the two. The numeric
shift is small (§2e.3, sub-1% at default config); the reason to fix it is correctness and configurability,
not magnitude.

### §2e.1 Three constants; TA mirrored the wrong one

| Constant | Value | Role | Lands on |
|---|---|---|---|
| `config.DefaultKvCacheThreshold` (field `KvCacheThreshold`) | **0.80** | saturation's **k_sat** — the definition of "full" per replica | `k1 = TotalKvCapacityTokens × KvCacheThreshold` (saturation_v2 `analyzer.go:168`, `:243`; also passed to `aggregateByVariant`) ⇒ shapes **PerReplicaCapacity** |
| `config.DefaultScaleUpThreshold` | 0.85 | scale-**up** watermark | **RC only** |
| `config.DefaultScaleDownBoundary` | 0.70 | scale-**down** watermark | **SC only** |

`scaleUpThreshold` / `scaleDownBoundary` are **margins around the steady state** — the HPA-style no-op band
(`RC>0` needs `demand/0.85 > anticipated`; `SC>0` needs `supply > demand/0.70`; between them both are zero).
Validation enforces `scaleUp > scaleDown`, and `resolveSaturationConfig` resets an inverted pair to the
defaults, so the band is a first-class invariant. They are **not** utilization targets, and they are not
interchangeable with k_sat.

`throughput/constants.go:52-56` conflates the two:

> `DefaultKSat = 0.85` — *"Mirrors DefaultScaleUpThreshold in saturation config so that the throughput
> analyzer and saturation analyzer agree on the definition of 'full'. TODO: unify with the system-wide
> k_sat used by the EPP and saturation analyzer."*

It mirrors the **watermark**, not the k_sat. Net effect: saturation says full = 80% KV, TA says 85% — the
two analyzers do **not** agree on the definition of full, which is the one property that comment exists to
guarantee. And the value is a compile-time constant: TA receives `input.Config` and never reads it (zero
`KvCacheThreshold` and zero `ScaleUpThreshold` hits in the whole `throughput/` package), so an operator's
configured k_sat never reaches TA at all. By the "config not used to set the value" test, that is a bug.

**The engine's threshold post-step is correct and is not the bug.** `applyUniversalThreshold`
(`engine_v2.go:468-505`) is invoked once per analyzer with that analyzer's *resolved* thresholds
(`resolveThresholds` → `EffectiveScaleUpThreshold(global)`, per-analyzer override with global fallback,
plumbed for both directions and for the `parameters:` plugin-envelope form via `Normalize()`), and it
writes **RC/SC only** — model-level and each `RoleCapacity` — leaving `VariantCapacities` (PRC, TotalDemand,
Utilization) raw. That is exactly where the margins belong; do not "fix" it, and do not push margins into
the PRC math. Recorded because the opposite conclusion was reached once and abandoned.

[↑ TOC](#toc)

### §2e.2 The fix — resolve once, thread to four sites

```go
// resolveKSat returns the KV-utilization fraction at which per-replica capacity is
// evaluated. It is saturation's configured k_sat, so both analyzers agree on what
// "full" means. It is NOT a scale-up/scale-down watermark — those are margins the
// engine applies to RC/SC after Analyze() returns.
func resolveKSat(cfg domain.AnalyzerConfig) float64 {
	if sc, ok := cfg.(*config.SaturationScalingConfig); ok && sc.KvCacheThreshold > 0 {
		return sc.KvCacheThreshold
	}
	return config.DefaultKvCacheThreshold
}
```

Called once at the top of `Analyze`; the value threads down. New import of `internal/config` into
`throughput` — **verified no cycle** (`internal/config` imports no `internal/engines` package).

| Site | Today | Change |
|---|---|---|
| `analyzer.go:295`, inside `Analyze` | `itlSat := model.ITLAt(DefaultKSat)` | `model.ITLAt(kSat)` — local variable, no signature change |
| `analyzer.go:711-727` `computeVariantSupply` | `nSat := DefaultKSat * kvMax / shape.KVreq` | add `kSat float64` param — **1** production caller (`:300`), no direct test |
| `itl_model.go:33-57` `validITLModel` | `a*DefaultKSat+b <= 0` | add `kSat float64` param; callers `FitITLModel:88` and `resolveITLModel:602` thread it — `FitITLModel` is **exported**, so its signature grows too |
| `analyzer.go:801-845` `checkVariantGPSMismatch` | `m.KvUsageInstant < DefaultKSat-DefaultNearKSatMargin` | add `kSat float64` param — diagnostic gate; "near saturation" must mean near the *same* k |

**Fallback is `config.DefaultKvCacheThreshold` (0.80), not 0.85.** A 0.85 nil-config fallback would keep a
second definition of "full" alive in exactly the path the TA unit tests exercise (no TA test sets
`input.Config`), so the tests would keep validating the old basis. One value, every path.

**`DefaultKSat` is DELETED**, not retained as an alias. §4b classification: **DEPRECATED** — the value is
now configuration; no future work planned; keeping a `0.85` constant named `KSat` is precisely the trap that
produced this bug. `DefaultNearKSatMargin` (0.10) **stays** — it is a genuine margin — with its doc prose
re-anchored to "the resolved k_sat" rather than to the deleted constant. The `TODO: unify with the
system-wide k_sat used by the EPP` moves onto `resolveKSat` (still open — see §7).

[↑ TOC](#toc)

### §2e.3 Effect, churn, ordering

**Effect — much smaller than it looks, and model-dependent.** `kSat` enters per-replica capacity
**twice**, not once: `computeVariantSupply` forms `N_sat = kSat × KV_max / KVreq` and divides it by
`itlSat = ITLAt(kSat) = A·kSat + B` (computed at `analyzer.go:295`, consumed at `:719`). So

```
μ_dec_sat(k) = (k · KV_max / KVreq) / (A·k + B)

μ(0.80)/μ(0.85) = (0.80/0.85) · (A·0.85 + B)/(A·0.80 + B)
                   └ 0.9412 ┘   └────── > 1 whenever A > 0 ──────┘
```

Lowering `k` shrinks numerator and denominator together and they largely cancel. Writing `r = B/A`, the
drop is `1 − (0.80/0.85)·(0.85 + r)/(0.80 + r)`: **0% at `r = 0`** (pure-slope ITL — `μ = KV_max/(KVreq·A)`,
independent of `k` entirely), rising monotonically toward 5.88% only as `r → ∞`. `validITLModel` requires
`a > itlSlopeEpsilon` (`1e-12`), so `A > 0` always holds and the `r → ∞` end is structurally unreachable.
With `B ≈ DefaultBaselineITLSec = 0.006` and slopes of order `1e-2`, the realistic band is **0.4%–2.5%**.

Against the shipped fixture (`analyzer_test.go:266-274` — `A=0.073 B=0.006 KV_max=1024000 KVreq=4600`,
i.e. `r = 0.0822`):

| | `N_sat` | `ITL_sat` | `μ_sat` |
|---|---|---|---|
| k=0.85 (today) | 189.2174 | 0.06805 | **2780.56** |
| k=0.80 (post-C10) | 178.0870 | 0.06440 | **2765.33** |

⇒ **−0.548%**. An earlier draft of this section claimed ~5.9% — that was `1 − 0.80/0.85`, the **numerator
alone**, off by ~11×; corrected 2026-08-07 on a reviewer finding. The *direction* is still the intended one
(PRC down ⇒ TA's replica vote up, conservative on saturation's basis), but at sub-1% under defaulted config
the integer vote moves only where `ceil` happens to straddle. **Justify C10 as a correctness and
configurability fix, not as a systematic ~6% correction — and keep the 6% figure out of the commit
message.**

**Test churn** (all inside `internal/engines/analyzers/throughput/`; no other package constructs TA):
- `itl_model_test.go` — 10 `FitITLModel(...)` + 6 `validITLModel(...)` call sites take a new arg
  (mechanical); the comment at `:136` names `DefaultKSat`.
- `analyzer_test.go` — **expect little or no numeric churn; do not go hunting for it.** It is the only file
  calling `NewThroughputAnalyzer` and no TA test sets `input.Config`, so every one takes the fallback — but
  all three `TotalSupply` assertions (`:367`, `:405`, `:425`) read
  `BeNumerically("~", muSat, muSat*0.10)` against `muSat = 2782.0` (`:273`), a **±10% tolerance**. A 0.55%
  shift stays far inside it, so nothing goes red. Two things are nonetheless required: **(i)** the
  derivation comment at `:259-264` spells `0.85` into the `N_sat` and `ITL_sat` lines — rewrite it against
  the resolved k_sat and re-derive the numbers it prints; **(ii)** if an expectation *does* move, re-derive
  it from the **full two-place ratio above** — numerator `N_sat = kSat × KV_max / KVreq` **and** denominator
  `itlSat = A·kSat + B`. Scaling by `0.80/0.85 = 0.9412` alone lands ~5% off, and the ±10% tolerance will
  not catch it: wrong expectation, green gate.
- **#1513 goldens are saturation-only ⇒ unaffected.** Re-run anyway (§4).

**Ordering — C10 lands after C6a–C6d and before C9.** The combine fixtures in C1–C6 build
`NamedAnalyzerResult` values directly from synthetic RC/PRC and are immune to TA's k_sat; only TA's own
package tests are touched at all. Landing C10 late keeps the analyzer-internal change out of the combine
commits, so any TA-package test movement is attributable to one commit rather than smeared across the
arithmetic fixes — a separation-of-concerns argument, which stands even though the expected movement turns
out to be near-zero (above).

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
  - C6a — `combineVotes` **unit table** (the invariants of §2d.2 one row each: uniform ⇒ extremum both
    directions · dominant score ⇒ that vote · bounded in `[min,max]` · monotone in `sᵢ` · single vote ⇒
    itself · no vote ⇒ `(0,−1)` · tie ⇒ lowest index), plus a **3-analyzer non-participant fixture**
    (third entry has no PRC for the variant) that must produce the **same** number as the equivalent
    2-analyzer fixture — this is finding (a)'s pin. Plus a byte-identity check: with uniform scores every
    retrofitted site returns exactly what it returned before C6a.
  - C6b — the two worked examples of §2d.2 as fixtures: votes 10/5 @ scores 1/2 ⇒ **9** scale-up; votes
    10/5 @ scores 2/1 ⇒ **6** scale-down. Assert the number **and** the binder index. Add the
    conservative-analyzer-is-higher-scored case asserting the result stays at the safe extremum.
  - C6c — fsv **ordering** fixtures (two models, differing PRCs, quota-constrained: the model whose demand
    is larger *in replicas* wins, not the one whose demand is larger in tokens/s) · a `computeMean`
    fixture in replica space · a **multi-role** fixture pinning site (iv)'s clamp (a two-role model must
    not have either role truncated to a handful of units) · finding (b): a model whose only demand has no
    usable PRC must **not** sort ahead of an actionable model, and must not be dropped for the cycle ·
    a **fall-through cap** fixture for site (ii): one role, two variants with different PRCs **and**
    different costs, the cheaper-efficiency one made infeasible via `MaxReplicas` headroom, asserting the
    cap the **pricier** variant receives — red without the `prcRef` rescale (5 instead of 25 on §2d.5's
    numbers), and note this is the one fsv fixture that varies PRC *within* a role rather than across
    models · a **fallback-currency** fixture for site (v): a hand-built request with `Priority = 0`
    (constructed directly, bypassing `ApplyDefaults`, which would rewrite it to 1.0) asserting fsv comes
    back in replicas, not raw demand ·
    **T1.4 rewritten** per §2d.6 · **goldens re-run**.
  - C6d — finding (c). **Every fixture here must drive `scaleDownRoleIterated` end-to-end** — a direct
    `safeRemovalReplicasForRole` unit call with `RoleSpare[role] = 0` exercises a state the pipeline cannot
    deliver at role entry (`needsScaleDownForRole` vetoes the role first), so it would be **green for the
    wrong reason** both before and after the change. Three cases, per §2d.4 (c):
    - **PRC-absence (the primary red).** One role, **two** variants v1/v2 with costs ordered so `v1` sheds
      first; live objector X with `RoleSpare[R] > 0` at entry (so the gate passes) and a
      `VariantCapacities` entry for **v1 only**; a second live analyzer sizing both with ample spare. Size
      X's spare so v1's removal decrements it to exactly 0. Red: v2 loses replicas. Green: v2 held.
    - **Outscored objector** — X sizes *both* variants but carries a lower `Score` than the other voter;
      after C6b its `0` vote is pulled positive by dominance weighting, so removal proceeds without the
      veto. Red today *even with* full PRC coverage; this is the case that proves the fix must be a veto
      rather than a vote.
    - **N7 control** — key *missing* ⇒ abstain, removal proceeds. Pins (c) and N7 as distinct.
  - C7 — stale-enabled scale-up (VG-up no-longer-scales); role-coverage-mismatch (N7 abstain);
    Test 2 rewrite (v2 PRC=0 under N8).
  - C10 — `resolveKSat` **unit table** (config sets `KvCacheThreshold` ⇒ that value · field zero ⇒
    `DefaultKvCacheThreshold` · non-saturation config type ⇒ default · nil config ⇒ default), plus a TA
    `Analyze` fixture whose `Config` carries `KvCacheThreshold: 0.5` asserting per-replica capacity tracks
    it (red before: PRC pinned at 0.85 whatever the config says). **That fixture needs a tight tolerance,
    ~1%, and must not copy the neighbours' `muSat*0.10` idiom** — on the shipped fixture model
    `μ(0.5) = (0.5·1024000/4600)/(0.073·0.5+0.006) = 111.30/0.0425 = 2618.9`, against the k=0.85 value of
    2780.56. **The bound, stated the way the assertion consumes it:** `BeNumerically("~", 2618.9, tol)`
    takes `tol` *relative to the expected value*, and `2780.56 − 2618.9 = 161.6` is **6.17% of 2618.9** —
    so any `tol ≥ 6.17%` stays green at k=0.85 and pins nothing. (The same gap is 5.8% of 2780.56; that
    framing is the one that does *not* bound the assertion — do not use it to size `tol`.) Use
    **±1% ⇒ band `[2592.7, 2645.1]`**, which excludes 2780.56 with room. Existing `analyzer_test.go`
    expectations are **not** expected to move (0.55% shift vs ±10% tolerance — do not manufacture churn);
    if one does, re-derive it from the **two-place** ratio, numerator `N_sat = kSat × KV_max / KVreq` *and*
    denominator `itlSat = A·kSat + B`, never by scaling `0.80/0.85` (§2e.3). Also rewrite the derivation
    comment at `analyzer_test.go:259-264`, which spells `0.85` into both lines.
- **Goldens are run per commit, not just at the end.** C6a and C6b must leave them byte-identical (uniform
  scores ⇒ old arithmetic). C6c is the only commit where a golden *could* plausibly move — the verified
  analysis in §2d.5 says it does not. **If a golden moves at any point: stop, and write a `plan__` handoff
  with the diff. Do not rewrite a golden to accommodate this change.**
- **Multi-vote goldens (C9):** a `[sat, TA]` golden suite that also encodes the `[sat]`-only and
  `[TA]`-only sub-cases (so the sat-only removal is covered), validated against hand-worked design-doc
  examples (§ anchor / § bugs worked numbers).
- **Full pre-push checklist incl. `-race`** for the fair-share + per-iteration refresh loop
  (`make test` / `gofmt` / `make lint` / `go build`; DCO sign-off; branch verify). See §6 for the
  semantic-pivot grep steps that must run before commit.

**Plans-branch token hygiene (CODER-CONVENTIONS §4a) — two halves, only one of which a commit can fix.**
A full-branch sweep (reviewer, 2026-08-07) found **32 code/doc locations plus a token in all nine commit
messages** — 6 of 9 subject lines (`(N2)`, `(Bug #2)`, `(Bug #1)`, `(Bug #3)`, `(C6a)`, `(C6b)`) and 8 of 9
bodies. None are inherited: the same grep at the base (`075a208e`) returns nothing, so this is entirely
PR-2's. Notes for whoever actions it:

- **The 32 code/doc locations ride one sweep commit.** C9 already touches the dev-guide, so it is the
  natural host. Two of the 32 are in the shipped Type 4 `multi-analyzer-pipeline.md` (`:338` `N7`, `:472`
  `N8`) — the most reader-visible surface on the branch. `analyzer_helpers.go:550` cites
  `combined-analyzer-optimizer-design.md`, which is **not in the repo** — a dangling pointer; the
  surrounding prose is self-sufficient, so delete the citation rather than repointing it. Note the
  `Bug #n` form is worse than the `Nn` form: `Nn` is merely opaque, whereas `Bug #2` reads as a tracker
  reference and sends a reader to an unrelated issue #2. Keep `#1513` in the golden's comment — that is a
  real GitHub PR number and is legitimate.
- **The nine commit *messages* are not reachable by any later commit.** A tenth commit cannot clean subject
  lines that `git log --oneline` and the GitHub commit list show permanently; only `rebase -i` + reword ×9
  reaches them. **This is a decision for Dean, and it is schedule-bound rather than work-bound:** the branch
  needs a force-push regardless (`origin/ta-anchor-dynamic-refresh@f6485980` is already orphaned by PR-1's
  reword), so folding the reword into that unavoidable force-push costs ~nothing — whereas the identical
  reword *after* a GitHub PR is opened becomes a history rewrite on a live PR branch, which the project's
  "no rebase of live PR branches" rule exists to prevent. So the cheap window closes the instant the PR
  opens. **"Not worth it" is a legitimate answer** and should be recorded as accepted; what should not
  happen is the default-by-omission where the PR gets opened first and the choice is made for us.
  Requires Dean's explicit go-ahead like any force-push.

[↑ TOC](#toc)

---

<a id="5-devguide"></a>
## §5 Dev-guide sections (named, per commit)

Per CONVENTIONS Type-3: name specific sections, not "update the dev guide." Section titles are as-of
`f6485980`; grep the heading text if line numbers drift. `coordinator-rebalancing.md` is a **POC demo
doc** (not the combine reference) — combine-arithmetic changes go in `multi-analyzer-pipeline.md` +
`saturation-scaling-config.md`, **plus `quota-limiter.md` for the fsv formula specifically** (added
2026-08-07 — it holds a third copy; see its block below). The fsv formula appears in **three** places
across two files: `multi-analyzer-pipeline.md:622` and `:675`, and `quota-limiter.md:284`. C6c must
update all three; a `grep -rn "Score_i\|score × unmet\|priority × score" docs/developer-guide/` is the
cheap check (see §6).

**`docs/developer-guide/multi-analyzer-pipeline.md`:**
- `## How results combine` (~L254) — **C1** (N2 deterministic binder tie-break replaces nil-on-ambiguity),
  **C6a** (the single `combineVotes` helper is now *the* combine — describe it once here and have the
  per-path sections refer back; name the collectors and the participation filter), **C6b** (the dominance
  rule: what `score` means, the formula, rounding once at the caller, "uniform scores ⇒ plain max/min" as
  the reader's anchor, and the 10-vs-5 @ 1/2 ⇒ 9 worked example), **C7** (VG-up `Enabled && Live` voting
  semantics; N7 abstain-vs-veto). *Modify — this is the largest single dev-guide edit in PR-2.*
- `### Scale-up path` (~L438) — **C2** (per-iteration refresh), **C4** (`allocateForModelPaired`
  per-analyzer decrement). *Modify.*
- `### Scale-down path` (~L463) — **C6c** (iii) (`sortVariantsForScaleDown` tie-break: Score dropped, uses
  the binder's PRC), **C6d** (the veto is checked **per variant**, not only once per role: a live
  analyzer's role-level "no spare" blocks removal regardless of whether it sizes that variant and
  regardless of its Score — say *why* the role-entry gate is not sufficient on its own, namely that
  deallocating one variant can exhaust a spare the gate already passed; and how a *present* zero differs
  from an absent key abstaining), **C7** (N7). *Modify.*
- `### Fair-share iteration (GreedyByScoreOptimizer only)` (~L482) — **C6c** (i)/(ii) `fairShareValue` /
  `fairShareCap` in **replica space**; state explicitly that `score` does **not** appear in fair share
  (it is consumed upstream in the combine) and that `priority` is the only fair-share weight; note the
  participation filter (demand with no usable PRC does not inflate a model's claim). *Modify.*
- `### Scale-from-zero and zero-replica variants` (~L358) — **C7** (N8 drop-fallback: binder-unknown ⇒
  PRC=0 abstain). *Modify.*
- `### Data flow per optimize cycle` (~L16) — **C2** (note the anchor is re-derived per allocation
  iteration). *Modify (one line).*
- `## Optimizer internals and helper composition` (~L431) — **C5** (rescale combined demand; N3
  nil-guard). *Modify.*
- `(a)/(b)` gloss lines 40/166/243/247–248/349/351/366–367/375 — **C8** notation strip. *Modify.*

**`docs/developer-guide/saturation-scaling-config.md`:**
- `### AnalyzerScoreConfig Fields` (~L313) — **C6b**. The `score` field's documented meaning becomes
  operative for the first time: a **belief weight over analyzer votes**, applied per (variant, role) inside
  the combine, *not* a budget or priority multiplier. State that `1.0` for all analyzers (the default, and
  what every shipped config uses) reproduces the plain max/min exactly, that raising one analyzer's score
  pulls the combined number toward that analyzer's own vote without ever leaving the
  `[min vote, max vote]` range, and that model `priority` — not `score` — is what weights fair share.
  Add a short "when would I change this?" note. Explicitly disambiguate the unrelated `K2Priority`.
  *Modify (substantial — the field is currently documented as little more than a default).*
- `#### Shared aggregation helpers` (~L431) — **C3** (`roleAggRemaining` replica-space max), **C6a** (the
  helpers now delegate to the one `combineVotes` core; `bindingIndexForRole` is gone — the binder comes
  back from the same call that produces the count). *Modify.*
- `### How Scale-Up Triggers Work` (~L207) — **C7** (VG-up liveness gate on the combine input). *Modify.*
- `### Saturation as the Identity Carrier` (~L464) — **C7** (N8 drop-fallback; sat-as-non-voting-carrier
  under `[TA]`-only), **C8** (notation strip). *Modify.*

**`docs/developer-guide/throughput-analyzer.md`** — **C10**, five locations:
- the `## Supply Estimation` block (~L458-459) — **both** lines read against the **resolved** k_sat:
  `N_dec_sat = k_sat × KV_max / KVreq` *and* `μ_dec_sat = N_dec_sat / ITL(k_sat)`. The doc is already
  correct that k_sat appears twice; keep it that way, since that is exactly why the change moves the number
  far less than the numerator alone suggests (§2e.3). *Modify.*
- the `DefaultKSat = 0.85` gloss (~L470) — replace with saturation's configured `kvCacheThreshold`
  (default **0.80**), and say *why*: one definition of "full" shared across analyzers. State explicitly that
  this is **not** `scaleUpThreshold` — that is a watermark the engine applies to RC/SC afterwards.
  *Modify.*
- near-saturation diagnostics `k* ≥ DefaultKSat − 0.10` (~L639) — the literal 0.75 becomes
  `k_sat − DefaultNearKSatMargin` (0.70 at the default). *Modify.*
- constants table row (~L675) — **remove** the `DefaultKSat` row (constant deleted), add a config-sourced
  k_sat line pointing at `kvCacheThreshold`; keep the `DefaultNearKSatMargin` row. *Modify.*
- known-limitations line (~L692) — currently "`DefaultKSat = 0.85` is per-analyzer; needs alignment with
  EPP system-wide k_sat". The *per-analyzer* half is now fixed; **keep the EPP half** as still-open (§7).
  *Modify.*

**`docs/developer-guide/quota-limiter.md`** — **C6c**, one location (added 2026-08-07; this file was
missing from the list above, and it carries a **third** copy of the Score-bearing fsv formula):
- `### Fair-share interaction`, first bullet (~L283-285) — "the average of the active models' remaining
  fair-share metric (**priority × score × unmet demand** — see the worked-example caveat below)". Drop
  `score` (it is consumed upstream in the combine, not in fsv) and put the unmet demand in **replica**
  space, matching (i). *Modify.* Note while there: the worked example just below (~L309-325) reasons in
  replicas already ("Wants" 3/4/4, mean ≈ 3.67), which today is a simplification of a demand-space
  metric — after C6c it is **literally** what fsv computes, so the "worked-example caveat" hedge can go.
  No numbers in that example change.

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
- **C3/C4/C6c — unit changes** (raw-capacity → replica space): `grep -rn "roleAggRemaining\|PRC_sat\|k·prc\|fairShareValue\|fairShareCap" internal/`
  and re-read every comment describing "max of RequiredCapacity" / "decrement by PRC" / "sum across
  analyzers" — reword to the replica-space / per-analyzer / max_i semantics.
- **C6a — `bindingIndexForRole` deleted:** `grep -rn "bindingIndexForRole" internal/ docs/` — must return
  **zero** hits after C6a, including in comments and dev-guide prose that describes "a second pass to find
  the binding analyzer." Any remaining reference means a caller was left on the old two-call pattern.
- **C6a — the combine is one helper:** `grep -rn "roleBottleneckReplicas\|safeRemovalReplicasForRole\|roleDemandGPUs\|needsScaleDownForRole" internal/ docs/`
  — every doc-comment that spells the loop out ("takes the max over analyzers of ceil(...)") now describes
  *delegation* to the shared combine, and every one of them must name the **same** participation filter.
  A comment that still describes its own private loop is a stale hit even though the code compiles.
- **C6b — `score` is a combine weight** (`Enabled`-list ordering → belief weight): `grep -rni "score" internal/ docs/developer-guide/ config/`
  — this is a wide grep; read every hit and classify. Fix any comment calling `score` a priority, a weight
  on capacity/budget, or an ordering key. **Leave `K2Priority` and every `k2*` identifier untouched** (name
  collision, unrelated mechanism) — if a hit makes that confusion in prose, fix the prose.
- **C6c — `score` no longer reaches fair share:** `grep -rn "Score" internal/engines/pipeline/` — after
  C6c there must be **no** `Score` reference in `fairShareValue` (**both** its primary path *and* its
  fallback, site (v)), `fairShareCap`, `computeMean`, `sortByRemainingDesc`, `allocateForModel`, or
  `sortVariantsForScaleDown`. Any survivor is either a double-count or a units desync. **The doc half of
  this pivot is a separate grep, because the formula is written out in three places:**
  `grep -rn "Score_i\|priority × score\|Priority × Σ" docs/developer-guide/` must return **zero** hits —
  expect `multi-analyzer-pipeline.md:622`, `:675`, and `quota-limiter.md:284` before the fix (§5). A
  surviving copy is a dev-guide that contradicts the code.
- **C6c — fsv currency is replicas, not demand:** `grep -rn "fairShareValue\|w.remaining\|fsv\|remaining demand\|unmet demand" internal/engines/pipeline/ docs/developer-guide/`
  — every comment or prose line that calls the fair-share metric "demand", "tokens", "capacity" or
  "unmet demand" is a stale hit once (i) lands; it is a **replica count**. This is the grep that catches
  site (v)'s stale doc-comment (`greedy_score_optimizer.go:53-60`) and the `modelWork.remaining` field
  comment (`:49`, "fair-share priority metric"), which should now name the unit.
- **C6d — role-level objection blocks removal** (skip-on-no-PRC → veto): `grep -rn "RoleSpare\|prc <= 0\|prcForVariant" internal/ docs/`
  — update every comment that says an analyzer without per-variant capacity "is skipped" on the scale-down
  path; it now still objects at role granularity. Verify the *abstain* prose for a genuinely missing
  `RoleSpare` key (landed in C7) is still accurate and is stated as the distinct case.
  **Two specific comments assert the property C6d changes and will be wrong afterwards:**
  `safeRemovalReplicasForRole`'s own doc comment (`analyzer_helpers.go:626-631`) says it *"Returns 0 when no
  live analyzer sizes v"* — after C6d it also returns 0 when a live analyzer that does **not** size `v`
  objects at role level; and `applyDeallocationForRole`'s (`:643-648`) justifies not Live-gating on the
  premise that non-live entries are *"already excluded from … the safe-removal minimum"* — still true for
  non-**live** entries, but re-read it against the new PRC-blind path and make sure the reasoning it states
  is the reasoning that now holds. Also re-check `:233`'s "point of use" note, which names both functions.
- **C5 — rescale demand→GPU** (saturation-only → combined): `grep -rn "satEntry.TotalDemand\|roleDemandGPUs\|rescaleModelDecisions" internal/ docs/`
  — update comments claiming "saturation's demand" and confirm the N3 nil-guard note lands.
- **C7 — VG-up voting gate** (`Enabled` → `Enabled && Live`): `grep -rn "votingResults\|Enabled-only\|e.Enabled" internal/ docs/`
  — reword any "votes when Enabled" prose to "Enabled && Live"; verify `bindingAnchor` still reads the
  FULL ballot (must NOT be switched to `votingResults`).
- **C7 — N8 drop-fallback:** `grep -rn "satEnabled\|fallback\|(b)-fallback\|borrow" internal/ docs/`
  — remove the fallback prose; state binder-unknown ⇒ PRC=0 abstain. Update PR-1 Test 2 (v2 110→0).
- **C8 — notation strip:** `grep -rnE "\((a|b)\)" internal/ docs/developer-guide/` — zero hits in shipped
  comments/docs after C8 (the letters are gone; the words remain).
- **C10 — k_sat is configuration, not a constant:** `grep -rn "DefaultKSat" internal/ docs/` must return
  **zero** hits after C10 (constant deleted, four call sites threaded, dev-guide prose reworded). Then
  `grep -rni "0\.85\|k_sat\|ksat" internal/engines/analyzers/throughput/ docs/developer-guide/throughput-analyzer.md`
  — every surviving `0.85` must be a *watermark* reference, never a capacity basis. Leave
  `DefaultNearKSatMargin` in place and confirm its doc prose no longer anchors to the deleted constant.
- **C7/C10 — the stale engine comment:** rewrite `engine_v2.go:126-131`. Both halves are defective: there
  is no config-mutating loop (`resolveThresholds` returns values and `config` is passed by value), and
  "*their results are discarded*" is precisely what PR-2 falsifies. Keep or repoint the
  [#1228](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1228) reference rather than
  dropping it.

[↑ TOC](#toc)

---

<a id="7-scope"></a>
## §7 Out of scope / deferred / separable follow-ons

**In PR-2 (this stack):** §1 multi-vote combine + N2 + N7, §2 bugs #1/#2/#3/#5, §2b VG-up + N8, §2c
notation, **§2d Score semantics — the `combineVotes` extraction, the dominance rule, the missing-entry
findings (a)/(b)/(c), the fair-share currency fix and the T1.4 rewrite**, **§2e TA's k_sat — resolved from
saturation's configured `kvCacheThreshold` instead of the hard-coded 0.85 watermark mirror**, §3
per-iteration refresh, N3 nil-guard hardening (rides C5), §4 goldens relax.

**Considered and REJECTED (do not re-implement without a design-doc change):**
- **Score as an aggregate budget multiplier** — `fsv = priority × (Σᵢ Scoreᵢ) × …` (the coder's option 3 in
  `plan__ta-anchor-c6-fairsharevalue-score.md`). It has the appeal of reproducing T1.4's existing
  expectation with the existing fixture, but it makes a model's claim on GPUs grow with the *number of
  analyzers configured for it*, which is not a property of the workload. Rejected by the planner
  2026-08-06; §2d.1.
- **Plain weighted average across votes** — `Σ sᵢvᵢ / Σ sⱼ`. Rejected by Dean 2026-08-06 ("*Weighted
  average as is gives 6.67. not the right call*"): it can land below every analyzer's own lower-bound
  reasoning. The shipped rule weights the *deltas from the extremum by score excess over the binder*,
  which keeps the result inside `[min, max]` and reproduces Dean's 8.33 (§2d.2).
- **Weighting each vote by Score before the extremum** — `maxᵢ (Scoreᵢ × ceil(vᵢ))` (the coder's option 2).
  Not sign-coherent for scale-down, and it can exceed `max vᵢ`, i.e. invent a replica count no analyzer
  asked for. Also rounds per element, which Dean ruled out.

**Not deferred out of PR-2 by the Score work.** The fair-share currency fix (§2 #5) was briefly considered
for a follow-up PR on the theory that it would move the #1513 goldens; that was **verified false**
(§2d.5) and it stays here. Nothing new left PR-2's scope as a result of §2d.

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
- **EPP system-wide k_sat unification** — `throughput-analyzer.md`'s standing note that k_sat "needs
  alignment with EPP system-wide k_sat" is only **half** closed by C10: TA now tracks *saturation's*
  configured k_sat, but neither tracks whatever the EPP uses for its own saturation notion. Still open;
  the `TODO: unify with the system-wide k_sat used by the EPP` moves onto `resolveKSat` rather than being
  deleted with the constant (§2e.2).

[↑ TOC](#toc)
