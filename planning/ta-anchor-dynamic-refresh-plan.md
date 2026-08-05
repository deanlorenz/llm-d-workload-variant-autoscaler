# TA Anchor Refactor — PR-2 (dynamic refresh + multi-vote combine)

**Type:** 3 (task plan) · **Status:** STUB (deferred — do NOT start until PR-1 lands)
**Design authority:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (Type 1)
**Depends on:** [`ta-anchor-refactor-plan.md`](ta-anchor-refactor-plan.md) (PR-1) — this PR is a
**dependent** follow-up and must not begin until PR-1 is merged. Base: PR-1's merged tip.
**Branch (to cut, later):** `ta-anchor-dynamic-refresh` (not yet created).

---

## Reading Protocol

> Read this Reading Protocol + `## TOC`, then fetch sections on demand
> (`Read <file> offset:<start> limit:<end−start+1>`). Re-run `toc-refresh.sh` after structural edits.

---

## TOC

- [§0 Status — why this is a stub](#0-status--why-this-is-a-stub) L26:46
- [§1 Scope — the both-enabled dynamic case](#1-scope--the-both-enabled-dynamic-case) L47:70
- [§2 The four combine-arithmetic bugs](#2-the-four-combine-arithmetic-bugs) L71:94
- [§3 Per-iteration dynamic refresh](#3-per-iteration-dynamic-refresh) L95:116
- [§4 Ship gate & tests (to be detailed)](#4-ship-gate--tests-to-be-detailed) L117:131

## §0 Status — why this is a stub

PR-1 (`ta-anchor-refactor-plan.md`) delivers the static core: the anchor/ballot contract, the
topology-vs-vote read split, and TA-only enablement — all **single-vote** (0 or 1 enabled analyzers),
changing **zero** combine arithmetic. PR-1 guards the both-enabled (`[sat-v2, TA]`) case as
not-implemented.

This PR-2 turns on the **multi-vote** path: the per-role combine that refreshes the anchor's (b)
sizing/sort fields, the per-iteration dynamic refresh, and the four combine-arithmetic bug fixes that
only manifest with ≥2 votes. It is deferred because (a) it depends on PR-1's contract being merged and
(b) the multi-vote combine is where the real algorithmic risk lives — it deserves its own review cycle
against the design doc § anchor / § bugs, not a rushed rider on the structural PR.

**Do NOT expand this stub into a full plan until PR-1 has landed** and Dean scopes PR-2. When scoping,
first re-read the design doc § anchor, § trace, § bugs, § sort, and PR-1's §3/§12.

[↑ TOC](#toc)

---

<a id="1-scope"></a>
## §1 Scope — the both-enabled dynamic case

To be detailed at scoping. Sketch:

1. **Multi-vote refresh of the anchor's (b).** Generalize PR-1's "copy `ballot[0]`'s (b) onto the
   anchor" to the per-role binding rule from the design doc § anchor: per (role, variant), the binding
   analyzer is the `argmax_i rd_i` selection (the binding constraint), and its (b) sizing/sort fields are
   written onto the anchor. (a) is never touched; RC/SC stay per-analyzer off the ballot (unchanged from
   PR-1). All votes combine uniformly — no name-checks, per Dean's model. **The refreshed fields are
   exactly PR-1 §2's (b) sizing/sort subset:** per-variant `PerReplicaCapacity`, `TotalCapacity`,
   `TotalDemand`, `Utilization`, `Reason`; model-level `TotalSupply`, `TotalDemand`, `Utilization`.
   Nothing else moves onto the anchor.
2. **Refresh each iteration.** That binding (b) is a pure function of (immutable ballot entries,
   current+pending replicas, allocation progress); recompute it per allocation iteration rather than
   once. PR-1 does no refresh at all (single vote → the sole vote's (b) is already on the anchor, no
   drift).
3. **rescale-on multi/TA validation** — the rescale path (`rescale.go`) under ≥2 votes and TA-only,
   which PR-1 routed but did not golden-cover.

[↑ TOC](#toc)

---

<a id="2-bugs"></a>
## §2 The four combine-arithmetic bugs

All dormant with a single vote (PR-1); each manifests only when ≥2 analyzers combine. Fix here, each
with a regression test that fails pre-fix under a two-vote fixture.

- **#1 — `allocateForModelPaired` decrement unit.** The `pickerState[i][role] -= k·prc` /
  `applyAllocation` decrement applies one variant's PRC uniformly across analyzers whose per-replica
  capacity for that variant differs (`k·PRC_sat` vs `k·PRC_TA`). Per-analyzer decrement needed.
- **#2 — `roleAggRemaining` (`analyzer_helpers.go:201`).** `max_i` over raw per-analyzer RC in mixed
  units. Needs a unit-consistent aggregation (design § bugs).
- **#3 — rescale water-fill + scale-down tie-break.** `rescale.go:521` `Demand: satEntry.TotalDemand`
  (single-analyzer demand) and `sortVariantsForScaleDown:168` `Σ_e Score·PRC` tie-break under
  multi-vote.
- **#5 — `fairShareValue` uses `Σ_i` where design wants `max_i`.** Three lock-step sites that must
  change together: `fairShareValue:73`, `fairShareCap:421`, `sortVariantsForScaleDown:168`.

**#4** was downgraded (traced 2026-08-03; not an active sizing bug — residual is observability
`Utilization` only). Confirm at scoping whether any observability cleanup rides here.

[↑ TOC](#toc)

---

<a id="3-refresh"></a>
## §3 Per-iteration dynamic refresh

To be detailed. Per Dean's model, the anchor's (b) sizing/sort fields (the exact set in §1) are the
**only mutable cell**: each allocation iteration recomputes the per-role `argmax_i rd_i` binding from
the immutable ballot entries + current+pending replicas + allocation progress, and writes that
binding's (b) onto the anchor. (a) and the per-analyzer RC/SC are never touched. Whether the recompute
is memoized is an implementation detail to settle at scoping (correctness is identical either way);
the observable contract is "anchor's (b) = the current per-role binding vote's, refreshed per
iteration."

> **Forward-note (2026-08-05, after the PR-1 mechanism redesign).** PR-1
> ([`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md)) has **no stored anchor field** — the
> anchor is derived on demand by the Phase-2 getter. So "refresh per iteration" here means **re-running
> that getter** (re-select the per-role binding, re-merge) each iteration, **not** mutating a stored cell
> in place. The observable contract above is unchanged; only re-scope the mechanism to "re-invoke the
> Phase-2 getter" when this stub is expanded.

[↑ TOC](#toc)

---

<a id="4-gate"></a>
## §4 Ship gate & tests (to be detailed)

- The saturation-only characterization goldens (landed via their own PR
  [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513), not owned by PR-1)
  must **still** pass through PR-1 — the single-vote path is unchanged there.
- **Endgame for those sat-only goldens (decide at PR-2 scoping).** They are a characterization/freeze
  suite scoped to *this* refactor, not a permanent optimizer contract. Once the multi-vote goldens
  below exist, decide whether to **fold** the sat-only cases into the multi-vote suite or **relax**
  them — do not leave them silently frozen on `main` as a forever-assertion. Whichever way, capture the
  removal/fold as an explicit commit in this PR (or a same-cycle follow-up), not an implicit drop.
- New two-vote fixtures exercising each of #1/#2/#3/#5 (red before fix, green after).
- Both-enabled decisions validated against hand-worked design-doc examples.
- Full pre-push checklist incl. `-race` for the fair-share + refresh loop.

[↑ TOC](#toc)
