from: review (plan-reviewer)
to: review
session: ta-anchor-refactor-v2 PR-1 internal code-review checklist (pre-staged)

## Purpose

Pre-staged verification checklist for the **internal code-review round of PR-1** (branch
`ta-anchor-refactor-v2`, the anchor-refactor static core). Dean will launch a fresh internal
reviewer against the coder's diff once it is push-ready. This handoff is that reviewer's brief.

**Start clean — do NOT read the whole plan or the review doc.** Every item below cites the exact
plan section by its TOC entry + line range. Fetch only those ranges on demand
(`Read planning/ta-anchor-refactor-v2-plan.md offset:<start> limit:<end-start+1>`). The plan's TOC
is at `planning/ta-anchor-refactor-v2-plan.md` L23:68 if you need to navigate further. You should
never need to open `planning/ta-anchor-refactor-review.md` — its conclusions are already distilled
here.

## Preconditions — run this review ONLY when all hold

- The coder has signalled push-ready via `session/handoffs/review__ta-anchor-refactor-v2-ready.md`.
- All 5 commits are present on `ta-anchor-refactor-v2` (C1 §5 / C2 §6 / C3 §7 / C4 §7b / C5 §8).
- The coder's gates are green: `make test`, `gofmt -l ./internal/...`, `make lint`, `go build ./...`.
- **Do not review a mid-work tree.** If the worktree has uncommitted changes or fewer than 5
  commits, the coder is still working — stop and wait. (Read-only inspection only; never `git`
  write-verbs in the coder's worktree per CONVENTIONS.)

## Canonical coder gate — run first

The plan's own reviewer checklist is authoritative and comes first:
**§13 Reviewer verification checklist — L1047:1074.** Run every item there. The list below is the
**blast-radius-ordered complement** (my own prep, not duplicated into §13): the correctness-critical
invariants, each mapped to the plan section that specifies the intended behavior.

## Blast-radius checklist (verify diff against plan)

> Note on the confusing `7b`: the plan has TWO. `§7 › 7b. Liveness / do-nothing` (L587:602) is item 5.
> The top-level `§7b Commit 4 — TA-side proactive complement` (L618:742) is item 7. Titles + ranges
> below disambiguate.

1. **Anchor is derived, never stored.** No new field on `ModelScalingRequest`/`NamedAnalyzerResult`;
   `bindingAnchor` (rename of `saturationEntry`) builds a **fresh** `*domain.AnalyzerResult` per call;
   stored ballot `Result`s are not mutated in place.
   - Plan: §6 › 2a `bindingAnchor` new body **L389:430**; §2 merge rule **L187:225**; §10 struct/field
     **L884:892** (confirms no new field); test in §6 › 2f **L503:540**.
   - Guards: no-stored-mutation invariant.

2. **Per-variant merge keyed by `VariantName`; the (a)/(b) field split is correct.** Per variant:
   (a) `AcceleratorName/Cost/Role/ReplicaCount/PendingReplicas` from **sat**; (b)
   `PerReplicaCapacity/Reason/TotalDemand/Utilization` from the **binding analyzer**; `TotalCapacity`
   **recomputed** (`ReplicaCount × PerReplicaCapacity`), never copied.
   - Plan: §2 Table 1 (per-variant `VariantCapacity`) **L145:167**; §2 Table 2 (model-level
     `AnalyzerResult`) **L168:186**; §2 merge/fallback **L187:225**.
   - Guards: silent (a)/(b) crossover; stale `TotalCapacity`.

3. **Per-variant fallback fires *before* the non-voting-sat prune AND is enablement-gated.** Fallback
   to sat's (b) only when saturation is enabled; under `[TA]`-only a missing binding (b) → **PRC=0**
   (not sat's (b)). The fallback must run **before** `votingResults` prunes the non-voting sat entry.
   - Plan: §2 merge/fallback ordering **L187:225** (the gated rule — AUTHORITATIVE); §6 › 2b
     `votingResults` prune **L431:448**; test 2 in §6 › 2f **L503:540**.
   - ⚠️ **Known plan inconsistency (my finding V9, should-fix-before-coding):** §6 prose read as
     *ungated* while §2 gates it. **§2 is authoritative.** Confirm the coder implemented the
     **enablement-gated** fallback, not the ungated §6 wording. If the diff shows ungated fallback,
     that is a BLOCKER.
   - Guards: `[TA]`-only cold variant silently inheriting sat's (b); ordering bug that prunes before
     fallback.

4. **Binding selection matches the decided rule.** default & `[sat,TA]` → **sat** binds; `[TA]`-only
   → sat is a non-voting (a)-carrier + **TA** binds; nothing binds → getter returns **nil** → the
   call-site nil-guard holds (zero decisions, no crash). `satVotes` =
   `len(Analyzers)==0 || effectiveEnabled("saturation")`.
   - Plan: §6 › 2a `bindingAnchor` body **L389:430**.
   - Guards: wrong binder under `[TA]`-only; missing nil-guard → panic on empty ballot.

5. **Liveness is set on every entry incl. sat, and the binding rule reads it.**
   `updateLivenessAndSetLive` sets `.Live` on index 0; the binding rule consults `satNR.Live`.
   - Plan: §7 › 7b Liveness / do-nothing **L587:602**; the read in §6 › 2a **L389:430**.
   - Guards: stale-sat cycle binds stale (a) instead of holding.

6. **QM refused by explicit error — no silent sat-v2 fallback.** QM dispatch returns an error; no path
   lets a present QM ConfigMap fall through to V2. Deletion/deferral classification present.
   - Plan: §7 › 7a QM-as-error **L547:586**; §12 deferrals & deletion classification **L1000:1046**;
     test 5 in §7 › 7c **L603:617**.
   - Guards: silent QM→V2 fallthrough (drops every QM model); undocumented deletion.

7. **TA (Commit 4 §7b) emits PRC only.** A **previously-live-now-zero** variant emits its persisted
   `lastPerReplicaSupply` (real TA PRC) **only**; `Cost`/`AcceleratorName` are sat's (a) via the merge,
   **not** TA-emitted; a **never-seen** variant emits **nothing** (PRC=0, not selectable under
   `[TA]`-only). There must be **no** `fallbackVariantCost` MAX sentinel and **no** TA-side
   `lastCost`/`lastAcceleratorName` (that pre-redesign design was removed in `2e83c7fe`).
   - Plan: §7b › "Why TA emits PRC only (and the resulting known limitation)" **L686:701**; the fix
     loop **L634:685**; test in §7b **L717:742**; selectability effect (cost picker /
     `cost_aware_optimizer`) verified by test 10 in §6 › 2f **L503:540**.
   - Guards: TA re-emitting cost/accel (re-introducing the removed sentinel); never-seen variant
     fabricating a baseline PRC.

8. **Goldens (#1513) stay green.** The saturation-only decision-set identity (keyed by `VariantName`)
   is byte-for-byte unchanged — `optimizer_characterization_test.go` green **after every commit**, not
   just at the tip.
   - Plan: §4 Invariant #7 ship gate **L283:298**; §11 coordination / goldens gate **L967:999**.
   - Guards: any behavior change to the default (sat-only) config.

9. **Rename cross-refs + named dev-guide sections updated.** The `saturationEntry`→`bindingAnchor`
   semantic-pivot grep (§9) is clean across comments/docstrings; the enumerated dev-guide sections
   match the new behavior; any stale combine comment is corrected if in scope.
   - Plan: §9 semantic-pivot grep (mandatory) **L851:877**; §8 Commit 5 developer-guide **L808:850**.
   - Guards: doc drift; stale `saturationEntry` references surviving in prose.

## After the review

- Report findings ranked most-severe first. Item 3 (V9 gating) is the single correctness item to
  confirm explicitly; the rest are structure/behavior checks against the cited sections.
- Blocking findings → the coder addresses before push; non-blocking → note for Dean's call.
- This handoff supersedes the stale `review__ta-anchor-refactor-criteria.md` (it pointed at the
  SUPERSEDED `ta-anchor-refactor-plan.md` and the abandoned `ta-anchor-refactor/` worktree).

Provenance: distilled from my §0–§7 reverse-read walkthrough and Review Round 2 (findings V8–V11,
all folded into the FINAL plan `c279bdeb`). Items 3 & 7 reflect the `2e83c7fe` PRC-only redesign.
