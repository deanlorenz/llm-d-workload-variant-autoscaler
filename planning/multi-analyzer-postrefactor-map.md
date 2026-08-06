# Multi-Analyzer Data-Flow Map — post-refactor (short)

**Status:** DRAFT — reviewer notes. A short, self-contained tour of the multi-analyzer engine's
data flow **after** the anchor refactor, written to orient a reviewer of this PR. Read it alongside
the diff; every claim cites the `file:line` it comes from.

**Code described:** this PR (five commits). A follow-up PR (dynamic refresh) is planned; changes
that land there — not here — are marked **[next PR]** inline so you know what's deliberately
deferred.

**What the post-refactor engine is, in one paragraph.** Analyzers no longer decide anything on their
own. Each optimize cycle, Phase I *packages a ballot* (every analyzer's result, tagged `Enabled` +
`Live`), and Phase II *derives an anchor on demand* — a single synthetic per-model result built by a
per-variant merge: **identity (a)** (`AcceleratorName/Cost/Role/ReplicaCount`) always from saturation,
**sizing (b)** (`PerReplicaCapacity/TotalDemand/Utilization/Reason`) from whichever analyzer *binds*.
The anchor is the topology/roster the optimizer iterates; the **voting subset** of the ballot is what
the quantity math (up/down/fair-share) combines. There is **no new combine engine** — the cross-analyzer
combine (MAX up, unanimous-live-veto + MIN down, score-weighted-SUM fair-share) already existed. The
refactor is about *packaging* every analyzer uniformly and deriving identity when a non-sat analyzer
binds — so `[sat]`, `[sat,TA]`, and `[TA]`-only all work through one path.

**Three configs** this must serve: **`[sat]`-only** (default; frozen byte-for-byte by the #1513
goldens), **`[sat,TA]`**, **`[TA]`-only** (sat present but non-voting, still the identity carrier).

**Enabled / Live / informative** (the ballot vocabulary):
- **Enabled** = this analyzer *votes* (config-driven).
- **Live** = informative within the staleness window (`updateLivenessAndSetLive`).
- **informative** = `ResultIsInformative` — at least one VC reason is not no-data/error.
- An analyzer **binds** iff `Enabled && Live && informative`.

---

## TOC

- [§1 Call-stack sketch (most important)](#1-call-stack-sketch-most-important) L41:104
- [§2 Dispatch](#2-dispatch) L105:112
- [§3 Generation — what each analyzer emits](#3-generation--what-each-analyzer-emits) L113:126
- [§4 Consumption — the combine](#4-consumption--the-combine) L127:149
- [§5 Paths we checked — adding TA into the mix](#5-paths-we-checked--adding-ta-into-the-mix) L150:175

## §1 Call-stack sketch (most important)

One optimize cycle, end to end, on branch `ta-anchor-refactor-v2`. **[this PR]** marks what the refactor
introduced; **[next PR]** marks what changes in the follow-up (dynamic refresh).

```
Engine.optimize()                                                       [engine.go]
  └─ switch analyzerName:
       │
       ├─ "saturation" (V2, default) ──► optimizeV2(...)
       │    for each (model, namespace) group:
       │      └─ collectV2ModelRequest(...)
       │           └─ runAnalyzersAndScore(...)   ◄── PHASE I: package ballot, no decisions   [engine_v2.go:100]  [this PR]
       │                 ├─ ballot[0] = sat entry {Enabled: satVotes}   identity(a)+sizing(b), always
       │                 ├─ for each configured non-sat analyzer (e.g. TA):
       │                 │     if effectiveEnabled → ballot[i] = {Enabled: true}
       │                 │       TA: previously-live, now-zero variant → PRC-only VC (Reason "T-sfz")   [this PR]
       │                 │            (identity(a) zero-valued — filled by the merge; never-seen → nothing)
       │                 └─ updateLivenessAndSetLive(ballot)   sets .Live on EVERY entry   [engine_v2.go:206]
       │
       │      optimizer.Optimize(...)              ◄── PHASE II: derive anchor + combine
       │        ├─ bindingAnchor(ballot)           derive anchor on demand           [analyzer_helpers.go:124-226]  [this PR]
       │        │    ├─ binding = sat iff Enabled&&Live&&informative                 [:138]
       │        │    │            else the SOLE non-sat that qualifies;
       │        │    │            >1 such → return nil [:151];  none → return nil [:158]
       │        │    │            [next PR] admits multiple non-sat voters → >1 must become a tie-break
       │        │    ├─ aCarrier = sat if present   (identity(a) source — even in [TA]-only)   [:164-166]
       │        │    └─ per-variant merge keyed by VariantName                       [:186-224]
       │        │          identity(a) ← aCarrier ;  sizing(b) ← binder
       │        │          binder-unknown variant → sat's sizing(b) iff satEnabled [:208] (no .Live) [next PR: drop]
       │        │          TotalCapacity = ReplicaCount × PerReplicaCapacity  (recomputed) [:221]
       │        │          nil anchor ⇒ per-model HOLD (every call site nil-guards)
       │        │
       │        ├─ votingResults(ballot)           prune to Enabled-only             [:234-242] (no .Live) [next PR: +&&Live]
       │        │    → this pruned slice is the quantity-combine input; the anchor build reads the FULL ballot
       │        │
       │        ├─ scale-UP   roleBottleneckReplicas = cross-analyzer MAX(ceil(demand/prc)) over raw Result  [:326-342] (NOT Live-gated)
       │        ├─ scale-DOWN needsScaleDownForRole all-live-veto [:445-457] + safeRemovalReplicasForRole MIN [:390-414] (Live-gated)
       │        ├─ fair-share fairShareValue = score-weighted SUM
       │        └─ (GreedyByScore only) applyRescale pre-pass                          [rescale.go:209-334]
       │              admit iff bindingAnchor≠nil [:225] & singleAccType; rescaleModelDecisions drives each model [:335-388]
       │
       │      buildDecisionsWithOptimizer: identity from anchor; RC/SC from anchor.RoleCapacities[role]
       │                                    else model scalars; Utilization from variant's sizing(b)   [cost_aware_optimizer.go:280-319]
       │      applyScaleToZeroEnforcement(...)     idle/TTL policy — orthogonal to the anchor
       │
       ├─ "queueing-model" ──► refuseQueueingModel(...)   explicit refusal, model holds   [engine_queueing_model.go:19]  [this PR]
       │                                                   (no silent sat-v2 fallthrough; not a ballot participant)
       │
       └─ V1 (legacy) ──► out of scope

(separate manager Runnables — NOT in optimize(), never read the anchor or ballot)
  ├─ reactive scale-from-zero engine   [cmd/main.go:551]   EPP pending>0 → wakes ALL variants (budget-blind)
  └─ (scale-to-zero handled by applyScaleToZeroEnforcement above)
```

**The one-paragraph read.** Analyzers *package* (Phase I), they don't decide; Phase II derives the anchor on
demand — **identity (a)** always from saturation, **sizing (b)** from whichever analyzer *binds* — and
combines the **voting** subset (MAX up / all-live-veto + MIN down / score-weighted SUM fair-share). There is
**no new combine engine**. Scale-**up** is *not* liveness-gated (stale enabled data can still push up);
scale-**down** is. The reactive from-zero engine and scale-to-zero enforcement bypass the anchor entirely.

[↑ TOC](#toc)

## §2 Dispatch

V1 / V2 (multi-analyzer) / QM are mutually exclusive paths. Post-refactor, **V2 is the only combine path**;
**QM is refused** (`refuseQueueingModel`, §1) rather than silently routed through sat-v2. Optimizer/limiter selection is
still name-gated (a known main-side design wart, out of scope here).

[↑ TOC](#toc)

## §3 Generation — what each analyzer emits

| Analyzer | Emits identity (a)? | Emits sizing (b)? | Votes? | Key rule |
|---|---|---|---|---|
| **sat-v2** | ✅ always | ✅ always | iff `satVotes` | topology carrier in every config; the **only** identity source |
| **TA** | ✖ (zero-value) | ✅ when enabled; **[this PR]** T-sfz PRC-only for previously-live cold variants | iff `effectiveEnabled` | never-seen variant emits nothing (PRC=0 ⇒ not selectable) |
| **QM** | — | — | ✖ **[this PR]** refused | explicit-error refusal → model holds; deferred, not a peer |

**Key rules implemented (this PR):** analyzers *package*, they don't decide (Phase I/II split); every entry is
tagged `Enabled` + `Live`; TA carries a proactive-from-zero PRC only for variants it has *seen live*; QM
refuses loudly instead of falling through to sat.

[↑ TOC](#toc)

## §4 Consumption — the combine

The combine math is **pre-existing** — the refactor only changed *what is packaged into the ballot* and
*how identity is derived*. Two ballot views: the **anchor** (full ballot, merged) carries topology/identity;
**`votingResults`** (pruned) carries the quantity votes.

| Function (`analyzer_helpers.go` unless noted) | Direction | Rule | Live-gated? |
|---|---|---|---|
| `bindingAnchor:124-226` | identity + sizing | per-variant merge; binder = `Enabled&&Live&&informative`; `>1`/none → nil → **hold** | binding needs `.Live`; the sizing-(b) fallback gate does **not** |
| `votingResults:234-242` | prune | `Enabled`-only → combine input | **no** — scale-up reads it un-liveness-gated |
| `roleBottleneckReplicas:326-342` | scale-**up** | cross-analyzer **MAX** over raw `Result` | no |
| `needsScaleDownForRole:445-457` | scale-**down** veto | all-**live** voters must see role spare | ✅ |
| `safeRemovalReplicasForRole:390-414` | scale-**down** count | **MIN** over live voters | ✅ |
| `fairShareValue` | fair-share | score-weighted **SUM** | — |

**Key rules implemented (this PR):** the anchor reads the *full* ballot (so identity survives even when sat is
non-voting in `[TA]`-only), while the quantity math reads the *pruned* voting slice; **scale-down is
`.Live`-gated, scale-up is not** (the asymmetry — safe down, hazardous up). **Design rule (→ [next PR]):** when
a non-sat analyzer binds, every *sized* variant is the binder's — a binder-unknown variant abstains (PRC=0),
never borrows sat's rejected sizing (b) (drop the fallback).

[↑ TOC](#toc)

## §5 Paths we checked — adding TA into the mix

Every autoscaling action traced end-to-end per config. **Owner** is the load-bearing split: the **analyzer
pipeline** (anchor → prune → combine → decisions/rescale) vs the **two independent Runnables the anchor never
touches** (reactive `scalefromzero`, and `applyScaleToZeroEnforcement`). "TA effect" is the focus — what
changes when TA joins sat.

| # | Action | Owner / gate | `[sat]`-only | `[sat,TA]` | `[TA]`-only | Verdict + watch-item |
|---|---|---|---|---|---|---|
| 1 | **Scale-up** | pipeline; MAX over voting slice | MAX = sat RC | **MAX(sat RC, TA RC)** per role, higher wins | MAX = TA RC (sat non-voting) | over-provision-safe. **Watch:** the voting set is gated on *Enabled* only, so a dead-but-enabled analyzer's stale count still enters the MAX (scale-down, below, is liveness-gated); a one-line `&& e.Live` on the voting set is planned for close-out |
| 2 | **Scale-down** | pipeline; all-live-veto + MIN | sat's spare governs | **both** must see spare; MIN removed | TA's spare governs | **safe** — liveness-gated. **Watch:** in a P/D (disaggregated) model, if one live analyzer lacks a role's capacity key, that map-miss reads as veto and the role can get stuck high |
| 3 | **From-zero, full** (all cold) | **reactive engine** (`cmd/main.go:551`), *not* pipeline; EPP `pending>0` | only wake path | same (config-independent) | same | **config-independent** — never reads the anchor or ballot. **Watch:** this path is budget-blind and wakes *all* variants of a model, not the cheapest — the anchor cannot govern it |
| 4 | **To-zero** | `applyScaleToZeroEnforcement`, *not* pipeline | own idle/TTL policy | same | same | **safe**, orthogonal to the anchor |
| 5 | **Partial-from-zero** (some cold) | pipeline **proactive** (T-sfz cold-start), in the anchor combine | cold variant sized by sat's zero-replica stored estimate | **TA's cold-start estimate** sizes it, metric-consistent | TA cold-start; sat non-voting | **Watch:** the per-variant sat fallback is the only place a TA-bound model can mix in a sat-derived size — the design rule is *a TA-bound model sizes cold variants from TA or abstains* (fallback removed in the follow-up). Separately, sat's `Cost=0` for a zero-replica variant can mis-rank it cheapest (pre-existing sat limitation, all configs) |
| 6 | **Rebalance** (rescale) | pipeline **rescale** (§1 pre-pass), GreedyByScore only | sat's sizing (b) | TA's sizing (b) | TA's sizing (b) | **safe** on the covered path. **Watch:** `rescaleModelDecisions` dereferences the anchor with no *local* nil-guard (safe only via the `:225` admission filter), and its sizing side can pull the sat fallback (same metric-mix concern as case 5) |

**Three cross-case rules (the outcome of the check):**
1. **Only two cases consume anchor *sizing*** — partial-from-zero (5) and rebalance (6) — which is exactly
   where metric-consistency between sat and TA matters. Scale-up *count* (1) reads each voter's raw `Result`;
   scale-down (2) is liveness-gated; the from-zero / to-zero *actuators* (3, 4) bypass the anchor entirely.
2. **Direction asymmetry holds everywhere:** scale-**up** can fire on stale data until the voting-set
   liveness gate lands; scale-**down** cannot. The fail-safe direction is over-provision.
3. **The anchor cannot govern cold-start** — reactive from-zero (3) is budget-blind; any cost/budget
   reasoning layered on from-zero has to account for that separately.

[↑ TOC](#toc)
