# TA Anchor Refactor — PR-2 (dynamic refresh + multi-vote combine)

**Type:** 3 (task plan) · **Status: FROZEN 2026-08-08** — the coding batch is applied and this plan is
the authoritative scope for the remainder of PR-2. **Read §0.0 first**: the branch is *code-complete at
`a9afb740`*, so most of what follows below is a **record of what landed**, not a forward instruction, and
§0.0 names the short list that is genuinely left plus the two decisions the freeze deliberately does
**not** make.
**Design authority:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md)
(Type 1, FINAL @ `8c2a9b04`) **plus
[`combined-analyzer-optimizer-design-addendum-1.md`](combined-analyzer-optimizer-design-addendum-1.md)
(Addendum 1, Rev 6 @ `423eb2a8`, approved by Dean 2026-08-08)**. The addendum is additive and the parent
is deliberately unedited; **where the two overlap the addendum is later and governs**. The addendum is
reachable only by name from the parent, which is why this line carries it — see its § discoverability.
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
**Correctness scope:** [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md)
**§ findings** (`N1`–`N9`, `VG-up`, `VG-fallback`, `FZ-admission`), **§ units** (the per-site unit table,
the integral-replica rule, the three constants), **§ invariants** (1–11) and **§ limited** (the end-state
formulas). The Type 1 is the **only** authority for *what* is correct; this plan decides only *how* and
*when*. Its **§ open** decision queue is **EMPTY** as of the freeze — `W1`–`W5` are all answered, and §7.1
here records the answers rather than pointing at open questions.

> **The data-flow map is a source trace, not an authority** (Dean, 2026-08-07). §9 of the
> reviewer-owned [`multi-analyzer-dataflow-map.md`](multi-analyzer-dataflow-map.md) is where these
> findings were first traced, and it remains the best **per-site line evidence** — but it was a
> discussion summary plus review findings, and its content has since been **migrated into the Type 1**.
> Cite it for evidence, never for authority. If the map and the Type 1 disagree, **the Type 1 governs**
> and the map is stale.

> **Revision marker — refreshed against the FROZEN Type 1, 2026-08-07.** This plan is now derived from
> [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) at **`8c2a9b04`**
> (`Status: FINAL`, frozen 2026-08-07; content commit `52bfb59f`, status marking `8c2a9b04`). Pin that
> SHA — the Type 1 was uncommitted while its decision queue was being drained, so anything read from it
> before `8c2a9b04` is partial state. **Where the two disagree, the Type 1 governs and this plan is
> refreshed from it, never the reverse.** Post-freeze changes to the Type 1 go through Dean.
>
> **The commit map DID change in this refresh** (it did not in the previous one): the four remaining
> commits became **seven** — bug #5's currency pivot targets **GPU space, not replica space**, and the two
> behavior changes it surfaced (`W1` joint-role budget, `W4` abstain rule) plus `FZ-admission` are now
> their own commits so they cannot ride inside the status-quo-preserving conversion. See §1.1.
>
> ⚠️ **That revision marker is superseded by the freeze — read it as history.** It was written while the
> branch stood at `d9f3b97e` with C6c unimplemented, and it says so ("C6c has zero edits … safe to
> re-specify"). **C6c through C9e have since landed.** The branch is code-complete at **`a9afb740`**
> (25 commits on base `075a208e`, working tree clean, nothing pushed). Every forward-looking sentence in
> §2, §2b–§2f, §3 and §4 below therefore describes work that is **done**; the specification remains the
> record of *what was required*, and §0.0 is the only place that states what is still *owed*.

> **Line numbers in this plan are as-of `d9f3b97e` and are up to 25 commits stale**; the freeze did not
> re-derive them, because the rule that makes them survivable has not changed. The coder **greps by
> symbol**, not by line — every cite names the function/identifier. They will drift again at the PR-1
> rebase, which is now onto plain **`main`** (PR-1 merged as `57f3fe64`, so PR-2's base is no longer a
> sibling branch tip).

---

## Reading Protocol

> Read this Reading Protocol + `## TOC`, then fetch sections on demand
> (`Read <file> offset:<start> limit:<end−start+1>`). Re-run `toc-refresh.sh` after structural edits.

---

## TOC

- [§0.0 FREEZE RECORD — 2026-08-08 {#freeze}](#00-freeze-record--2026-08-08-freeze) L129:351
  - [Where the branch actually is](#where-the-branch-actually-is) L138:161
  - [What is genuinely left](#what-is-genuinely-left) L162:190
  - [What this freeze deliberately does NOT decide](#what-this-freeze-deliberately-does-not-decide) L191:212
  - [`AD5`/`AD8` — the disposition the freeze carries](#ad5ad8--the-disposition-the-freeze-carries) L213:321
  - [Premises to stop carrying](#premises-to-stop-carrying) L322:338
  - [Latent, not live — recorded without an ask](#latent-not-live--recorded-without-an-ask) L339:351
- [§0 Status — scope & the indivisible-PR decision](#0-status--scope--the-indivisible-pr-decision) L352:457
- [§1 Scope — the both-enabled dynamic case + commit map](#1-scope--the-both-enabled-dynamic-case--commit-map) L458:658
  - [§1.1 Commit map (C1–C11)](#11-commit-map-c1c11) L500:658
    - [§1.1.0 LANDED LEDGER — what git actually contains (freeze, 2026-08-08)](#110-landed-ledger--what-git-actually-contains-freeze-2026-08-08) L505:564
    - [§1.1.1 C11 (D-a) — DEFERRED, and why it is not a missed feature](#111-c11-d-a--deferred-and-why-it-is-not-a-missed-feature) L565:615
    - [§1.1.2 Original intent table (the spec each commit was written against)](#112-original-intent-table-the-spec-each-commit-was-written-against) L616:658
- [§2 The four combine-arithmetic bugs](#2-the-four-combine-arithmetic-bugs) L659:970
- [§2b Live-gate the combine input (VG-up + N8 + N7) — lands in C7](#2b-live-gate-the-combine-input-vg-up--n8--n7--lands-in-c7) L971:1057
- [§2c (a)/(b) → plain-prose notation cleanup — lands in C8](#2c-ab--plain-prose-notation-cleanup--lands-in-c8) L1058:1087
- [§2d Score semantics — the dominance rule, one combine helper, four call sites — lands in C6a–C6d](#2d-score-semantics--the-dominance-rule-one-combine-helper-four-call-sites--lands-in-c6ac6d) L1088:1484
  - [§2d.1 What Score means (decided)](#2d1-what-score-means-decided) L1095:1114
  - [§2d.2 The combine rule (dominance weighting)](#2d2-the-combine-rule-dominance-weighting) L1115:1162
  - [§2d.3 The helper — one function, and the duplicate loop that must die](#2d3-the-helper--one-function-and-the-duplicate-loop-that-must-die) L1163:1225
  - [§2d.4 Missing / non-participating entries](#2d4-missing--non-participating-entries) L1226:1299
  - [§2d.5 Fair share (Bug #5) — currency](#2d5-fair-share-bug-5--currency) L1300:1426
    - [Sat-only invariance](#sat-only-invariance) L1365:1406
    - [Goldens](#goldens) L1407:1426
  - [§2d.6 T1.4 — the existing Score test (rewrite; do not retire)](#2d6-t14--the-existing-score-test-rewrite-do-not-retire) L1427:1465
  - [§2d.7 Why this is safe to land here](#2d7-why-this-is-safe-to-land-here) L1466:1484
- [§2e k_sat is not a threshold — TA must use saturation's target — lands in C10](#2e-ksat-is-not-a-threshold--ta-must-use-saturations-target--lands-in-c10) L1485:1646
  - [§2e.1 Three constants; TA mirrored the wrong one](#2e1-three-constants-ta-mirrored-the-wrong-one) L1494:1529
  - [§2e.2 The fix — resolve once, thread to four sites](#2e2-the-fix--resolve-once-thread-to-four-sites) L1530:1585
  - [§2e.3 Effect, churn, ordering](#2e3-effect-churn-ordering) L1586:1646
- [§2f Proactive from-zero admission — lands in C11](#2f-proactive-from-zero-admission--lands-in-c11) L1647:1802
  - [The gap](#the-gap) L1670:1692
  - [(D-a) Mechanism — the sentinel lives in `PerReplicaCapacity`, tagged by its own `Reason`](#d-a-mechanism--the-sentinel-lives-in-perreplicacapacity-tagged-by-its-own-reason) L1693:1735
  - [(D-b) Cap — a one-replica ceiling on the variant's *target*, at the three sites that grant](#d-b-cap--a-one-replica-ceiling-on-the-variants-target-at-the-three-sites-that-grant) L1736:1778
  - [Scope](#scope) L1779:1802
- [§3 Per-iteration dynamic refresh — lands in C2](#3-per-iteration-dynamic-refresh--lands-in-c2) L1803:1837
- [§4 Ship gate & tests](#4-ship-gate--tests) L1838:2127
- [§5 Dev-guide sections (named, per commit)](#5-dev-guide-sections-named-per-commit) L2128:2391
- [§6 Semantic-pivot grep steps](#6-semantic-pivot-grep-steps) L2392:2625
- [§7 Out of scope / deferred / separable follow-ons](#7-out-of-scope--deferred--separable-follow-ons) L2626:2826
  - [§7.1 Design-level "what" questions surfaced by the currency fix (W1–W5) — all answered](#71-design-level-what-questions-surfaced-by-the-currency-fix-w1w5--all-answered) L2767:2826

## §0.0 FREEZE RECORD — 2026-08-08 {#freeze}

[↑ TOC](#toc)

**Read this section before any other.** Dean, 2026-08-08 (relayed by the coder): *"stop running anymore
tests and check. We freeze the plan then finish coding."* And to this role: *"when analyzer finalizes
addenum you finalize PR-2 type 3 doc."* Addendum 1 reached Rev 6 (`423eb2a8`) and Dean approved it, so
both gates fired and this is the resulting freeze.

### Where the branch actually is

**Code-complete at `a9afb740`** — 25 commits on base `075a208e`, working tree clean, **nothing pushed**,
gates green as of C9e. The labelled commit map in §1.1 reads C1–C11; the *git* history is longer because
C6 and C9 each decomposed while being coded (C6a–C6f, C9a–C9e). **Where the two disagree, the git history
is the fact and the map is the intent.**

⚠️ **One map row did not ship as written: C11's (D-a) admission sentinel is DEFERRED** — a *proven*
regression, verified by mutation, not a skipped step. C11 ships as the (D-b) ceiling only, i.e. **built,
not enabled**. §1.1.1 carries the full classification and the reason the sentinel cannot work
anchor-only. That deferral needs a backlog entry outside this plan; it is not a coder action.

Two consequences the freeze fixes rather than restates:

- **`origin/ta-anchor-dynamic-refresh@f6485980` is orphaned** by PR-1's reword and needs a force-push
  (`--force-with-lease`) to reach `a9afb740`. Dean's, not the coder's.
- **The rebase target changed.** This plan's setup step targets PR-1's *branch tip*; PR-1 **merged** as
  squash `57f3fe64`, so the target is now plain **`main`**, and PR-2's diff will no longer carry PR-1's
  commits. Re-run **`make lint`** after that rebase regardless of its result here: `main` moved
  golangci-lint **2.8.0 → 2.10.0** (PR #1512), so a green run from before that bump does not carry
  forward, and new findings are the bump's, not a regression.

[↑ TOC](#toc)

### What is genuinely left

⚠️ **The coder's stand-down list was stale by the time it was written — re-verified at `a9afb740` for this
freeze, not adopted as written.** `A29`, `A30`, and `A28` are **already landed**: `k_sat_test.go:163` now
reads *"scale-up watermark is 0.85"* (the token gone), `rescale_test.go:239,:248` already read
`maxRep := 3` / `maxRep := 8` (`a9afb740`'s own commit body records the rename, from Finding 50), and
`analyzer_helpers.go:88`/`:642` carry no token. **Re-verify any line number in this document before acting
on it** — the C9 sweep moved every one.

| Item | Work | Status at the freeze (verified at `a9afb740`) |
|---|---|---|
| `A29` | Two §4a token edits — `k_sat_test.go:163`, `rescale_test.go:186` | ✅ **DONE**; sites clean |
| `A30` | `max :=` shadows the builtin at `rescale_test.go:239,:248` → `maxRep` | ✅ **DONE**; renamed |
| `A28` | Two claimed §4a violations at `analyzer_helpers.go:88`, `:642` | ✅ **DONE**; no token at either line |
| **§4a residual** | `docs/developer-guide/multi-analyzer-pipeline.md:858` — *"open with the **Type-1** owner"* | ✅ **DONE** — `6d55fbd7`, reworded to *"analyzer-design owner"*, no token |
| `B2` | Discriminating `fairShareRolePick` spec | **Planner's to write; not coder latitude** — still outstanding |
| `AD8` (b) | Three-site per-role pricing repair | ⛔ **Dean places it** — see below |

⚠️ **The "rounding — `ceil` vs `floor`, Dean holds it" row above earlier revisions carried is RETRACTED
(designer correction, 2026-08-08) — it mis-scoped two different quantities as one fork.** `capN =
min(replicasToCover(share, gpusPR), gpusAvail/gpusPR)` rounds its two terms in **opposite directions on
purpose**, per the shipped comment at `greedy_score_optimizer.go:695-700`: the **entitlement**
(`replicasToCover`, `ceil`) — a replica is the indivisible unit allocation happens in, so a fractional
GPU claim rounds *up* to the replica it needs; the **pool** (`gpusAvail/gpusPR`, integer division ≡
`floor`) — a GPU either exists or it doesn't, so availability rounds *down*. The frozen Type 1's `floor`
mandate (row 6 of the GPU-space unit table, *"no per-role reference PRC, so it's a floor by
construction"*) is about the **pool** term only — `fairShareCap`'s own name for the same quantity — and
it is satisfied exactly as specified. There is **no** discrepancy between the shipped code and the
frozen Type 1 to hold open. Addendum 1's own out-of-scope note (*"the ceil → floor conversion … Dean:
'we discuss later'"*) refers to this same pool-term conversion, already landed at C6c (`34b18bc5`) and
carried faithfully into this plan — the *"discuss later"* was Dean reserving a retrospective
conversation about that choice, not a live fork blocking anything. **Nothing about rounding is open.**

**§4a is otherwise closed.** A class-based sweep of `internal/` and `docs/` at `a9afb740` finds 8 token
lines across 4 Go files and 3 lines across 1 markdown file that are byte-identical at base `075a208e` —
inherited from `main`, not this branch's to fix (`greedy_score_optimizer_test.go`, `analyzer_test.go`,
`analyzer_helpers.go:411,:419`, `constants.go:85`, `throughput-analyzer.md:614,:646,:714`). Dismissed as
false positives: the goldens' own `A1`–`C1`/`B1`/`B2` scenario labels and their `M1`–`M7` mirrors (which
`a9afb740` deliberately made resolvable in-file), `Pro-B60-Graphics` (an Intel product name), and
`grep -A5` in `controller-behavior.md`.

[↑ TOC](#toc)

### What this freeze deliberately does NOT decide

Naming these is the point of the block: **plan §7.1's rule is that a site list is a plan step, not coder
latitude**, so silence here would read as permission. Two items are Dean's and are not resolved:

1. **The rounding decision** (`ceil` vs `floor` in `replicasToCover`). Dean: *"the ceil/floor we discuss
   later."* It is **three sites**, not one — the indivisible-unit floor now exists at
   `greedy_score_optimizer.go:458-460` (`bound = prc`), `:694` (`firstDraw && capN < 1`) and `:822`
   (`math.Ceil` in `replicasToCover`), each citing the others. A "floor everywhere" mandate applied
   literally means reverting three sites, not changing one expression. **Do not implement either
   direction until Dean rules.**
2. **Placement of the approved `AD8` pricing repair** — in PR-2, or a follow-up. Addendum 1 Rev 6 ask 2 is
   explicit: *"do not schedule it into PR-2 on the strength of the old severity, and do not retire it
   either. Ask him."* The severity that justified PR-2 placement was withdrawn (see §0.0's `AD8` note
   below); the repair itself is still approved. It is three sites on a code-complete branch, which is why
   it is a placement question and not a coding one.

Neither is a defect in the freeze. A design or scheduling choice this plan declines to make is Dean's to
make — what would be a defect is leaving it unnamed.

[↑ TOC](#toc)

### `AD5`/`AD8` — the disposition the freeze carries

Addendum 1 `AD8` is **DECIDED: repair the pricing** (Dean, 2026-08-08). The mechanism question is closed;
only placement is open.

- **Approved — option (b), the per-role pricing repair, three sites:** per-role sizing; `CapGPUs`/`Demand`
  in `rescaleInputsForGroup:540-546` (fixing only the role split leaves the model hard-capped at its
  understated demand); `cost_aware_optimizer.go:350-367` observability.
- **Rejected — option (a), a liveness-aware refusal.** Dean: *"PD not SAT — DONT."* The rule stays keyed
  on the **enabled** set; no second refusal predicate is wanted. Anything that reads as a liveness special
  case in the combine is in this family and is out.
- **Additive — option (c), interim documentation.** Not an alternative to (b).
- **`MinReplicas` is not a fourth option.** It is an operator-set **per-variant** field, unset by default,
  fails correlated with the defect, **cannot reach regime (i) at all** (it can preserve a scale-up, never
  originate one — `greedy_saturation_algorithm.go:52-63` + `:80-83`), and is not free: any variant with
  `minReplicas > 0` makes `applyScaleToZeroEnforcement` skip the enforcer **model-wide**
  (`saturation/engine.go:1362`). It survives only as a documented severity floor for regime (ii), cost
  attached.

**`AD5` — a distinct backlog item, not one of `AD8`'s three letters.** `AD5` is the *hold predicate*
question (when the binding analyzer is not role-complete for a role, hold that role rather than let it
drain or freeze) — related to `AD8` by sharing a cause (`VG-up`, `952d2fff`) but a different mitigation
shape, and it does **not** fix `AD8` route (A) (demand vs. `RoleSpare` — a hold predicate addresses a
role never being granted anything, not a role being priced away). **Recommendation, unchanged across
every round of analysis: defer to a follow-up, not PR-2.** Reasons: the placement exists in **no
document** (the anchor no longer sizes a role, so the predicate's insertion point — ballot construction
vs. `binder < 0` handling — is undesigned); it needs its own trigger-state sub-decision (which state
holds — "nobody priced this role" vs. "the analyzers agree on zero" are different states); and per
*"don't leave design decisions to coder"* a mitigation that presupposes a modeling decision (how prefill
demand is denominated, §7.1 `W2`-adjacent) cannot be correctly scoped on a code-complete branch. File the
follow-up naming **both** halves — the mitigation (hold predicate) and the actual fix (demand
denomination) — so it is not closed by the cheaper half alone.

**Two regimes from one cause — they reach the backlog as two items, never one, because a fix verified on
one says nothing about the other.** Dispatch is a global OR over roles
(`analyzer_helpers.go:709-718`) with mutually exclusive arms (`cost_aware_optimizer.go:62-67`), which is
why one role captures the model:

- **Regime (i), the freeze** — decode `RC > 0` ⇒ scale-**up** arm ⇒ prefill **freezes at its current
  count, including 0**. **No floor of any kind reaches it.**
- **Regime (ii), the drain** — decode `RC == 0` with spare ⇒ scale-**down** arm ⇒ prefill **drains to 1**.

**Severity: dropped, and the drop is global.** Addendum 1 Rev 6 closes the `[sat, TA]`-with-saturation-
non-live cell, and the internal reviewer's counter-example search (Rev 6's own settling test for that row)
came back **empty** across four single-fault stories — write-up in
`planning/ta-anchor-dynamic-refresh-review.md` **Finding 75**, `cbb17457`, a source read at `a9afb740`
with no build or test behind it. `[TA]`-only is what remains, and Dean's guard (*on a disaggregated model
with TA and no saturation, do nothing*) makes that configuration **hold** rather than act, which
*enforces* `AD2` rather than documenting it.

⚠️ **Take the closure, not Rev 6's stated reason for it — and this is now settled upstream, not a plan-side
caveat.** Rev 6 argued from a retention asymmetry (saturation's capacity store kept **7 days** against TA's
**1-hour** idle expiry). The designer has **withdrawn that argument** in **Rev 7** (`43f20c65`, § withdrawn
item 9) while keeping the conclusion, so cite the addendum rather than re-deriving here. Three mechanisms
under Rev 6's argument do not hold: the eviction constants are **dormant** (`EvictStale` /
`EvictStaleHistory` have **zero callers tree-wide, tests included** — records live for the process
lifetime); the TA side conflated **two fields** (`lastObservedAt`, `throughput/analyzer.go:99`, is assigned
*before* the `SanityIssueNoReplicas` `continue` at `:101-108`, so the 1-hour clock keys on a variant merely
**appearing** in the metrics slice, whereas the field the cell depends on is `lastPerReplicaSupply`, which
needs usable rows); and the `NoData` stamp is governed by **row count**, `len(replicas) > 0`
(`saturation_v2/analyzer.go:390`), not by arithmetic. The replacement needs **no time constant at all**:
both memories are written by **the same event** — a usable replica-metric row writes saturation a
`learnedFromLive` record keyed on the same `rm.VariantName` on the same cycle
(`saturation_v2/analyzer.go:198-207`), protected from weaker sources by `capacity_store.go:98-101`, and
saturation is warm over a **strictly broader** set because the store is also pre-populated from
scale-target objects on step 1 of every cycle (`saturation/engine_v2.go:38-53`). Containment, not a race.
**No duration is load-bearing**, and the conclusion is *stronger* than Rev 6 claimed. Rev 6's own stated
residual ("a fresh process where every scale-target fetch fails") is **retired** by two closures it did not
cite: the failed-fetch `continue` at `saturation/engine.go:1506` precedes both `scaleTargets[key] = …`
(`:1520`) and `variantAutoscalings[…] = va` (`:1523`), and `:1540-1545` returns early on
`len(replicaMetrics) == 0` before `BuildVariantStates` (`:1547`) — that state is **no model on the ballot**,
not an all-`NoData` model, so there is nothing for TA to be sole voter on.

**"Closed" is not "closed by exhaustive proof."** One residual is explicitly not closed: for the cell to
open, **every** variant must reach `satReasonNoData`, which needs `EffectiveCapacity = min(k1, k2) <= 0`
(`saturation_v2/analyzer.go:185-188`) on every variant's last live cycle while TA computed a positive
supply from those same rows, with `lookupCompatibleCapacity` also missing everywhere. Reading could not
rule that out. It is **not** being claimed reachable — recording it so the file is not mistaken for a
proof. It needs a **k1/k2 fixture, not a liveness fixture**.

⚠️ **This role recorded a scoped exception to that drop and has withdrawn it.** The claim was that route
(A) (`scaleDownRoleIterated → scaleDownVariantSet`) drains prefill in a compliant `[sat, TA]` P/D model
with **no** liveness gap, because TA's prefill `SpareCapacity` is the entire live prefill fleet (TA's
prefill `TotalDemand` being structurally 0). **It is wrong, verified at `a9afb740`:** route (A)'s
magnitude is `combineVotes(votesFromRoleSpare(…), false)` and `up == false` makes the binder the **MIN**
over participating live entries, so TA's inflated spare cannot carry the vote by itself — a live
saturation that sizes prefill bounds the count to its own, smaller figure; and `roleSpareVetoed` blocks
the **entire role** the moment any live analyzer carries an explicit `RoleSpare[role] <= 0`, deliberately
PRC-blind and score-blind so the objection cannot be diluted. The drain needs saturation to abstain on
prefill or be non-live, and non-live is the cell Rev 6 closed.

**One bounded residual survives, and the addendum does not name it for route (A).** Rev 6's reachability
bound is stated *under uniform scores* and derived on the demand (**max**) path. Route (A) runs the same
core in the **min** direction, where the correction term has the opposite sign: with `e = min`,
`(e − v_i) ≤ 0`, so a **higher-scored** entry with a **larger** spare pulls the combined removable count
**above** the min. Under default config this is exactly inert — `voteScore` returns `1.0` for any
`Score <= 0` and the config layer coerces zero to `1.0`, so all scores are uniform and the correction is
0. The residual therefore needs an operator to set per-analyzer scores with **TA above saturation**, is
bounded by the weighting rather than unbounded, and remains fully blocked by `roleSpareVetoed`. Record it
as a bounded known limitation of non-uniform scoring — **not** as a reachable drain, and not as a revival
of the withdrawn claim.

**Sequencing precondition, to travel with wherever the `#1237` tidy-up is tracked:** *if the positional
rule is ever tidied, floor every variant in the role first* — tidy-first re-opens this at every height on
both scale-down paths (measured: prefill → 0). It **governs regime (ii) only**; everything it protects
lives inside `scaleDownVariantSet`, which regime (i) never enters.

[↑ TOC](#toc)

### Premises to stop carrying

Delete these from any inherited text rather than softening them:

- **Addendum § withdrawn items 6/7/8** — including *"the cell is reachable by the most ordinary path there
  is (a cold start)"* and *"reachable by cold start or sustained metrics gap"*. Both wrong.
- **Review finding `V6`'s (b)-fallback domain** — inverted; superseded by `N1`.
- **`applyAllocation` as a sentinel sizing hazard** — it reads the ballot, never the anchor. The real
  unbounded grant is `fillRole`.
- **C10's effect as "~6%"** — numerator-only arithmetic. `k_sat` enters per-replica capacity **twice**;
  the realistic band is **0.4%–2.5%** and it is **−0.548%** on the shipped fixture. The justification is
  correctness and configurability, never a systematic correction.
- **`W2` with `U4` as an open question** — it was answered and then deferred on Dean's own criticality
  test. Record it as settled-deferred.

[↑ TOC](#toc)

### Latent, not live — recorded without an ask

The reviewer's seam is real and survives Rev 6: informativeness reads per-variant `Reason`
(`ResultIsInformative`, `analyzer_helpers.go:53-63`) while the `RC` reaching the optimizer comes from
`RoleCapacities`, and `applyUniversalThreshold` (`saturation/engine_v2.go:476-513`) never mentions
`VariantCapacities`. Aligning the two predicates is a **Type-1 design question, not PR-2 work**, and it is
**not** a revival of rejected option (a) — different site (the liveness computation, not a second refusal
predicate in the optimizer). No ask attached.

[↑ TOC](#toc)

---

## §0 Status — scope & the indivisible-PR decision

PR-1 (`ta-anchor-refactor-v2-plan.md`) delivered the static core: the anchor/ballot contract, the
topology-vs-vote read split, and TA-only enablement — all **single-vote** (0 or 1 enabled analyzers),
changing **zero** combine arithmetic. PR-1 supports `[sat]`-only and `[TA]`-only; the both-enabled
`[sat, TA]` two-vote path is what PR-2 turns on.

This PR-2 turns on the **multi-vote** path: the per-role combine that refreshes the anchor's sizing
fields, the per-iteration dynamic refresh, the four combine-arithmetic bug fixes that only manifest
with ≥2 votes, and the deferred liveness/notation hardening. This is where the real algorithmic risk
lives — it deserves its own review cycle against the design doc § anchor / § bugs / § sort / § rescale.

**Everything folds into PR-2 (Dean, 2026-08-07).** The frozen Type 1 rolls this up in a table at
[`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) § limited. It sweeps in,
beyond the four arithmetic bugs and the per-iteration re-binding: the **currency pivot** (bug #5 → GPU
space, `W5`'s per-site unit table), **`W1`** (one fair-share entitlement per *model*, spent jointly across
roles), **`W4`** (no conversion factor ⇒ no spend), **`FZ-admission`** (the scale-from-zero admission
sentinel + its one-replica cap), and **`VG-up`**. Explicitly **not** in PR-2: `W2` with `U4`, `U5`'s new
metric series, `N9`, `AnalyzerName` validation, and the saturation `Cost = 0` zero-replica bug (`N5`).
`W3` needs **documentation only**. See §7/§7.1 for the full in/out split.

**Scoping decision (Dean, 2026-08-06) — this is ONE indivisible PR, not a split.** Multi-vote combine
(§1) and per-iteration dynamic re-binding (§3) do **not** separate: **multi-vote needs dynamic
re-binding** to be correct — as allocation fills within a cycle, remaining demand shifts and the
per-(role, variant) binding `argmax_i rd_i` can change, so a binding fixed at cycle start goes stale
mid-water-fill. §1 + §2 (arithmetic bugs) + §3 + §2b (liveness) ship together. The genuinely-separable
follow-ons are the standalone small PRs in PR-1 §12 (QM fold F10, the §2.4 partial scale-from-zero
picker, `AnalyzerName` validation, the sat `Cost=0`-for-zero-replica bug) — each independent, **not**
part of this stack (see §7).

**Grounding to re-read at coding start** (re-read on resume; the Type 1 froze *after* this plan's first
authoring, so a pre-freeze reading is stale). In the design doc
[`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) **at `8c2a9b04`**, read in
this order:

1. **§ units** — the one contract, the per-analyzer currencies, the **integral-replica rule**, the three
   constants, and the observability note. Load-bearing for C6c/C6e/C6f/C11 and for C7.
2. **§ units** *per-site unit table* (`W5`, in § open's answered block) — the nine rows are the
   specification C6c implements; §2 #5 and §2d.5 here are its derived detail, not a substitute.
3. **§ invariants** — 1–11, especially **7** (sat-v2-only ⇒ anchor byte-identical, with a required direct
   test), **8** (a one-analyzer ballot is a pass-through *algebraically*, so a saturation-only golden
   moving is never the combine's fault and those goldens do **not** cover combine arithmetic), **10**
   (`Σ_role` legal in GPUs only) and **11** (priority orders, never scales).
4. **§ limited** — the end-state formulas and the everything-folds-into-PR-2 table.
5. **§ findings** — `N1`–`N9`, `VG-up`, `VG-fallback`, **`FZ-admission`** (mechanism *and* cap, both
   decided — transcribed here in §2f; do not re-open).
6. **§ configs**, then **§ combine**, **§ anchor**, **§ bugs**, **§ sort**, **§ rescale**.

**§ open is EMPTY** — every `W` question is answered; §7.1 here records the answers. Then PR-1 plan
§2/§3/§12. The data-flow map's §9 is **optional supporting evidence** — read it when you want the per-site
line trace behind a finding, not to establish what the finding *is*.

**Two things the Type 1 says not to carry forward** (both were in earlier review rounds and are
superseded — do not resurrect them from a stale trigger or review doc):
- Review finding **V6**'s claim about the (b)-fallback's domain is **inverted**; `N1` supersedes it.
- An earlier pass listed `applyAllocation` as a sentinel sizing hazard. That was **wrong**:
  `applyAllocation` reads the **ballot**, never the anchor, so the sentinel cannot reach it. The real
  unbounded grant is **`fillRole`** (§2f).

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

- **Currency, `W1`, `W4`, `FZ-admission` (post-freeze refresh, 2026-08-07).** The Type 1's answered
  `W` block redirected bug #5's pivot from replica space to **GPU space**, and separated out two
  behavior changes (`W1`, `W4`) that the earlier plan had folded into the conversion. Three new commits
  (C6e, C6f, C11) exist so that **the conversion commit contains neither** — that separation is the
  load-bearing part, because per-commit goldens are what distinguish "conversion was value-neutral" from
  "behavior moved."

**Stack order note (2026-08-06, revised 2026-08-07 twice).** C1–C5, C7, C8, C6a and C6b have **already
landed** on the branch (tip `d9f3b97e`); **C6c has zero edits**. So the git order is
**C1–C5 → C7 → C8 → C6a–C6b → C6c → C6d → C6e → C6f → C11 → C10 → C9** — the C-labels are stable
identifiers, not the commit sequence. Do not renumber landed commits. C10 is deliberately late: see §2e
§ Ordering. C6e-before-C6f is convenience, not a dependency; what **is** load-bearing is that C6c precedes
both and contains neither.

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
4. **Binder tie-break — design § findings `N2`.** PR-1's `bindingAnchor` returns **nil** (⇒ model hold)
   whenever >1 non-saturation analyzer qualifies as a binder for a variant (`analyzer_helpers.go:150`).
   Safe under PR-1 (sat-only or TA-only ballots), but PR-2 admits ≥2 voters, so a genuine multi-binder
   tie becomes a **silent permanent hold**. The multi-vote combine must replace nil-on-ambiguity with
   a deterministic tie-break — **lowest analyzer index, with no saturation-first special case**
   (Dean-confirmed 2026-08-07; stated as the design rule in § anchor "Multi-vote semantics"). The tie is
   rare, its scope is one analysis, and the ballot is fixed within an analysis — C2's per-iteration
   refresh re-reads each entry's values, not the analyzer list, so index order cannot shift and the
   binding cannot oscillate mid-water-fill. Add a two-binder fixture asserting the tie-break, not a
   hold. (Lands in **C1**.)
5. **Abstain-vs-veto on role coverage — design § findings `N7`.** The scale-down role list is
   `rolesOf(anchor.VariantCapacities)`, and `needsScaleDownForRole` (`analyzer_helpers.go:683-702`
   at C6b's tip `d9f3b97e`; the `:445-457` this doc cited was pre-C7/C6a)
   requires **every** live voter to report `RoleSpare[role] > 0`; a live voter with **no opinion** on a
   role reads the map-miss as `0.0` → implicit **veto** (stuck-high). PR-1 is safe (a single binder
   defines the role set), but the multi-vote combine must decide explicitly whether a voter that does
   not size a given role **abstains** (excluded from that role's spare test) or **vetoes** (current
   behavior). **Default to abstain** (Dean-confirmed 2026-08-06) unless the design says otherwise;
   cover with a role-coverage-mismatch fixture. (Lands in **C7**.)

### §1.1 Commit map (C1–C11)

Ordered stack; each is DCO-signed, gates-green-after-every-commit in an isolated worktree. "Red-first"
= add the fixture failing before the fix, passing after.

#### §1.1.0 LANDED LEDGER — what git actually contains (freeze, 2026-08-08)

**This ledger is the fact; the intent table below it is the spec.** 25 commits on base `075a208e`, head
`a9afb740`, tree clean, nothing pushed. Git order, oldest first. Sub-labels are taken from the commit
bodies' own self-identification, not assigned here.

| # | SHA | Label | Subject |
|---|---|---|---|
| 1 | `680bebdb` | C1 | deterministic binder tie-break for multi-vote ballots (N2) |
| 2 | `b106b929` | C2 | per-iteration dynamic refresh of the anchor's binder |
| 3 | `50034d15` | C3 | compare `roleAggRemaining` in replica space, not raw units (Bug #2) |
| 4 | `07b8fdb7` | C4 | decrement each analyzer by its own PRC, not the anchor's (Bug #1) |
| 5 | `3c9d45bb` | C5 | combine rescale's demand-to-GPU conversion across voters (Bug #3) |
| 6 | `952d2fff` | C7 | liveness-gate the voting set and drop the sizing fallback |
| 7 | `1140a4c2` | C8 | strip (a)/(b) notation, keep the descriptive prose |
| 8 | `8eb6ee2d` | C6a | hoist the cross-analyzer combine into one helper |
| 9 | `d9f3b97e` | C6b | let a configured analyzer score weigh its vote |
| 10 | `34b18bc5` | C6c | convert the fair-share claim to GPUs before comparing models |
| 11 | `330fcd26` | C6d | re-check the role veto per variant; shed by coverage/GPU |
| 12 | `784c2b5c` | C6e | one fair-share entitlement per model, drawn in sequence |
| 13 | `a679f2ad` | C6f | abstain is not exempt — make `W4` a tested property |
| 14 | `537b0153` | — | pin the claim-pricing distortion as a dormant spec |
| 15 | `4fb49ac6` | — | drop plans-branch paths from shipped comments; fix the mean claim |
| 16 | `a46c7eea` | — | pin the fair-share shared balance, not just the per-role clamp |
| 17 | `eb12089a` | — | drop the mis-routed role label from a shipped comment |
| 18 | `b6bb525c` | **C11 (D-b only)** | bound a from-zero-admitted variant at the grant sites |
| 19 | `1a50b418` | C10 | read `k_sat` from config instead of hard-coding it |
| 20 | `79a590d6` | C11 follow-up | test the admission ceiling at `fillRole` |
| 21 | `757fc6f5` | C9a | document the capacity-gauge currency gap and the deprioritize idiom |
| 22 | `2ae440e3` | C9b | write from-zero admission as deferred and fix four false premises |
| 23 | `209e148f` | C9c | pin the multi-vote decision goldens and invariant 7 directly |
| 24 | `4e369f10` | C9d | remove the sat-only characterization goldens, scenario by scenario |
| 25 | `a9afb740` | C9e | make every reference in shipped comments resolvable from `main` |

**Four deviations from the map, all deliberate and all recorded in the commits themselves:**

1. **Git order ≠ label order** — `C1–C5 → C7 → C8 → C6a…C6f → C11 → C10 → C9a…C9e`. C6c-before-
   C6e/C6f/C11 was load-bearing, not convenience: C6c is the only behavior-preserving one of the four, so
   keeping the behavior changes after it is what makes a per-commit golden re-run attributable.
2. **Rows 14–17 are unlabelled in the map** — two are `§4a`/comment-accuracy repairs pulled forward, two
   pin a spec that had no commit of its own. They are part of the freeze's record even though no map row
   predicted them.
3. ⚠️ **C11 shipped as (D-b) only. (D-a), the `PRC = 1` admission sentinel, is DEFERRED as a proven
   regression** — see §1.1.1. The intent table's row for C11 still says "both already decided in the
   Type 1 — transcribe, do not re-open"; **that instruction is spent**, and the reason is not a coder
   deviation.
4. **The one-replica ceiling reads through a new `maxTargetReplicas` helper** rather than being folded
   into each site's existing `MaxReplicas`-headroom branch as (D-b) literally instructed. The literal
   form does not work: at all three granting sites that computation sits behind a nil-guard on
   `MaxReplicas` whose fall-through treats *unset* as unbounded (`costGreedyRolePick` returns
   `math.MaxInt`; `fillRole`'s loop is bounded by nothing else; `fairShareRolePick` applies no clamp), so
   a ceiling folded into the guarded branch **would not exist on any variant without `MaxReplicas`** —
   which is exactly the never-measured population the ceiling is for. For an untagged variant the helper
   is the `MaxReplicas` check verbatim, so nothing else moved. Each site **skips** an exhausted ceiling
   instead of returning a cap of 0 (a returned 0 makes the caller compute `deltaUtil == 0` and break out
   of the whole model's allocation, taking every variant behind it down too), and in `fairShareRolePick`
   the clamp must stay **after** the `firstDraw` floor, which raises `capN`.

[↑ TOC](#toc)

#### §1.1.1 C11 (D-a) — DEFERRED, and why it is not a missed feature

Classification per the deletion rule: **DEFERRED**, reason recorded in-code at
`ReasonFromZeroAdmission`.

**What it would have done.** Tag a never-measured variant with a `Reason`-marked `PRC = 1` sentinel at the
anchor's no-variant branch — gated on `ReplicaCount == 0` **and** binder-omitted — so the non-positive-
capacity gates stop excluding it and a model at zero replicas can be *proactively* admitted onto it.

**Why it was removed now.** An anchor-only sentinel makes a variant **selectable without making it
sizable**. Selection reads the anchor, but the replica count comes from the **ballot**, via
`votesFromPickerState → combineVotes → roleBottleneckReplicas`, which **abstains** for a variant no voting
entry prices and returns 0. Then `n = min(0, cap) = 0`, `deltaUtil == 0`, and `allocateForModelPaired`
**breaks** — costing the model every variant behind the admitted one. **Verified by mutation:** with the
sentinel written the measured variant stays at its current replicas; with it disabled the same fixture
scales. That is a regression, not a missed feature. (The previously-live variant in
`optimizer_scale_from_zero_test.go` works precisely because the throughput analyzer emits its PRC into the
**ballot** rather than the anchor.)

**Where the future version lands.** Whether the sentinel may enter the **voting set** is an `N8` question,
so it is the **Type-1 owner's** — raised to the designer by handoff, not resolved here. Do not re-attempt
(D-a) inside PR-2 on the strength of the map row.

**Consequence for the shipped tree, stated so the dev guide and the plan agree:** C11 is **built, not
enabled** — nothing in production code writes the tag, the write site is reachable only from tests, and
for an untagged variant `maxTargetReplicas` is the `MaxReplicas` check verbatim. C9b's dev-guide
subsection says exactly that; prose calling the ceiling an active guard would be false on the merged tree.

**Owed, not blocking: `fillRole`'s clamp is untested at the one site a tagged variant can actually reach
it through.** Of the three grant sites, `costGreedyRolePick` has three behavioral specs and
`fairShareRolePick` is legitimately excused (a tagged variant's empty `AcceleratorName` fails its
`available[...]` gate first, disclosed in that test's own comment) — but `fillRole` has neither an excuse
nor a spec, despite the commit's own prose naming it the worst case (*"this loop is otherwise unbounded
whenever MaxReplicas is unset"*). Because nothing in production writes the tag, this is dormant today and
becomes live at the exact moment a future (D-a) lands — so it travels with that backlog item rather than
needing a PR-2 amendment: whoever revisits (D-a) should land a `fillRole` fixture
(`VariantCapacity{PerReplicaCapacity: 1, Reason: ReasonFromZeroAdmission}`, `GPUsPerReplica: 1`,
`MaxReplicas` nil, `wantGPUs: 10` ⇒ assert `spent == 1`) alongside it — the four `maxTargetReplicas` unit
specs prove the helper returns the right number, not that the loop honors it.

⚠️ **(D-b)'s ranking premise was also wrong and is corrected in the shipped tests.** An admitted variant
does **not** sort behind every measured option: `PRC = 1` degenerates cost efficiency to `Cost`, but a
never-measured variant's `Cost` arrives as **0** from the same zero-replica lookup that leaves its
accelerator empty, so the ratio is `0/1` and **it sorts first**, tying with every never-measured peer
under an unstable sort. No sentinel value repairs that; the root is the sat-v2 zero-replica `Cost = 0` bug
(`N5`), out of scope. The tests state the ranking the code actually has, and the ceiling is documented as
**the only** guard on an admitted variant rather than one of several. The intent table's C11 "ranking"
assertion is therefore **superseded** — do not restore it.

[↑ TOC](#toc)

#### §1.1.2 Original intent table (the spec each commit was written against)

**Refreshed 2026-08-07 against the frozen Type 1.** The four remaining commits became **seven**. The split
is not cosmetic: **C6c is a currency conversion that preserves current behavior** (with exactly one flagged
exception, the `floor` boundary), while **C6e and C6f are behavior changes** and **C11 adds a new
capability**. Keeping them apart is what makes the per-commit golden re-run a signal instead of noise — a
golden that moves at C6c is a bug or the `floor` boundary; a golden that moves at C6e/C6f/C11 is the
intended change, and one that moves at both is unattributable.

**Per-commit TA-exposure class** (from the Type 1's classification; it decides which fixtures can possibly
cover the change):

| Commit | Class | What that means for coverage |
|---|---|---|
| C6c currency | **TA-CREATED** for the mixing itself, but the conversion touches `[sat]`-only arithmetic too — value-neutral there **except at the `floor`/`ceil` boundary** | needs a `[sat]`-only fixture that **varies `GPUsPerReplica`** across models, plus a mid-replica boundary fixture |
| C6e `W1` | **TA-AMPLIFIED** — pre-existing: `[sat]`-only P/D already draws the full budget twice (once per role); TA makes it `\|analyzers\| × \|roles\|` = 4 | needs a `[sat]`-only **P/D** fixture as well as a `[sat,TA]` one |
| C6f `W4` | **TA-CREATED** (a single analyzer is always its own conversion factor) | `[sat]`-only goldens cannot cover it either way |
| C11 `FZ-admission` | **TA-CREATED** | `[sat]`-only goldens cannot cover it either way |

| # | Commit scope | Red-first test | Dev-guide (§5) | Detail |
|---|---|---|---|---|
| **C1** | Admit two-vote path + **N2** deterministic binder tie-break (**lowest analyzer index**, no sat-first case) — replace nil-on-ambiguity in `bindingAnchor`. Enabler. | two-binder fixture asserts tie-break, not hold | pipeline "How results combine" | §1 item 4 |
| **C2** | **Per-iteration dynamic refresh** — re-invoke the Phase-2 getter each allocation iteration so the per-(role,variant) binding re-selects as remaining demand shifts. | fixture where binding flips mid-water-fill | pipeline "Scale-up path", "Data flow per optimize cycle" | §3 |
| **C3** | **Bug #2** `roleAggRemaining` — max in replica space (`max_i rd_i`), not raw mixed-unit RC. | two-vote MAX fixture | pipeline "Optimizer internals and helper composition" (**corrected 2026-08-07** — this cell used to say sat-config "Shared aggregation helpers", which §5 re-pointed; that section documents one analyzer's own aggregation, not the cross-analyzer combine) | §2 #2 |
| **C4** | **Bug #1** `allocateForModelPaired` decrement — per-analyzer `k·PRC_i` (or replica units), not `k·PRC_sat` uniformly. Paired with C3. | two-vote allocation fixture | pipeline "Scale-up path" | §2 #1 |
| **C5** | **Bug #3** rescale water-fill + `roleDemandGPUs` combined `max_i ceil(demand_i/PRC_i)`; **+ N3** nil-guard hardening in `rescaleModelDecisions`. | two-vote rescale fixture | pipeline "Optimizer internals" | §2 #3, §7 N3 |
| **C6a** | **`combineVotes` helper + collectors** — one combine core; **merge** `roleBottleneckReplicas` + `bindingIndexForRole` (delete the duplicate loop); retrofit `roleAggRemaining` / `roleDemandGPUs` / `safeRemovalReplicasForRole` onto it. Uniform scores ⇒ **byte-identical**. | helper unit table (uniform / dominant / bounded / single / empty); 3-analyzer non-participant fixture (finding (a)) | pipeline "How results combine" | §2d.3 |
| **C6b** | **Score dominance weighting on** — the `(sᵢ − s_bind)⁺` term; rounding **once** at the call site (`ceil` up, `floor` down). | 10-vs-5 @ scores 1/2 ⇒ 9 up, 6 down | pipeline "How results combine"; sat-config score semantics | §2d.2 |
| **C6c** | **Bug #5 — the currency pivot to GPU space.** 5 lock-step sites, unit-table rows 0/1/2/3/4/6/8: (i) `fairShareValue` **converts each ballot entry's metric to GPUs at row 0** (+ signature: it must receive the picker's variant slice) / (ii) `fairShareCap` becomes a whole-replica **`floor` fill** / (iii) `sortVariantsForScaleDown` tie-break → **moved to C6d** / (iv) `allocateForModel`'s picker-state clamp converts the GPU bound down through **that analyzer's own** PRC (row 8) / (v) `fairShareValue`'s raw-unit fallback is **converted, not deleted**. **Score out** of fsv; finding **(b)** participation filter. Status-quo-preserving **except** the `ceil → floor` boundary, which must be called out in the commit message. | mid-replica **`floor` boundary** fixture (direct closure call); `[sat]`-only ordering fixture **varying `GPUsPerReplica`**; fsv ordering + `mean` fixtures; multi-role cap fixture; fallback-currency fixture; **T1.4 rewrite** (re-denominated, asserts ordering); invariant-7 direct anchor-equality test; goldens re-run | pipeline "Fair-share iteration"; **quota-limiter "Fair-share interaction"** (**two** of the formula's copies, not one — the file was missed entirely in the original plan; **six** copies total across four doc locations + two code doc comments, see §5) | §2 #5, §2d.5, §2d.6 |
| **C6d** | Finding **(c)** — **per-variant** veto re-check in `safeRemovalReplicasForRole`: a **live** analyzer with `RoleSpare[role] <= 0` (key *present*) blocks removal, PRC-blind **and** score-blind. The entry gate already covers role *entry*; the reachable defect is **mid-loop**, after `applyDeallocationForRole` drives a spare to 0. **Not** a synthetic 0-vote — post-C6b a vote cannot encode a veto. (Distinct from C7's N7 *abstain*.) **Plus bug #5 site (iii)** — `sortVariantsForScaleDown`'s tie-break becomes unit-table **row 7**: *dimensionless coverage per GPU freed*, `max_i` not `Σ_i`, Score out. Moved here from C6c because it is the one bug-#5 site on the **scale-down** path, and `U2`'s negative test belongs beside it. | **end-to-end** via `scaleDownRoleIterated`: one role, **two** variants, live objector sizing only the first-shed one (red: 2nd variant's replicas removed; green: held) + outscored-objector variant + N7 control; **`U2` zero-invocation** test (the scale-down iteration never invokes the per-variant sizing refresh); site-(iii) ordering fixture | pipeline "Scale-down path" | §2d.4 (c), §2 #5 (iii) |
| **C6e** | **`W1` — one fair-share entitlement per *model*, spent jointly across roles** (**behavior change**, TA-AMPLIFIED). Two defects, both real: site (ii) hands **every role** the same whole-model `target`, and site (iv) lets each `(analyzer, role)` pair clamp against the **full** `target` — a **double-spend** in P/D. `fairShareRolePick`'s `_ = roles` becomes a **sequenced draw** against a shared balance, not a static per-role split. What prevents real over-allocation today is only the downstream pool check: *the pool is enforced, the fair share is not.* | `Σ_role spend ≤ target` assertion on a P/D model, **in both a `[sat,TA]` and a `[sat]`-only fixture** (the `[sat]`-only one is the TA-AMPLIFIED proof); fixture must **not** give prefill and decode the same PRC *or* the same `GPUsPerReplica` (invariant 10 — it could not distinguish correct from role-mixing) | pipeline "Fair-share iteration" | §2 #5 (ii)/(iv), §7.1 `W1` |
| **C6f** | **`W4` — no conversion factor ⇒ no spend** (**behavior change**, TA-CREATED). An analyzer that cannot price a variant (no PRC for it) **abstains**: it contributes nothing to the claim and draws nothing from the budget. It is *not* budget-exempt — the distinction is the whole finding. Applies at unit-table rows 0 and 8. | `[sat,TA]` fixture where one analyzer has **no PRC for the reference variant** must produce the **same allocation** as the identical fixture with that analyzer **absent from the ballot** | pipeline "How results combine", "Fair-share iteration" | §7.1 `W4` |
| **C7** | **Liveness** — `votingResults` `Enabled` → `Enabled && Live` (VG-up/D2); **DROP** the `bindingAnchor` sizing-fallback (N8, rewrites PR-1 Test 2 v2 110→0); **N7** abstain-vs-veto default abstain. | stale-enabled scale-up + role-coverage-mismatch fixtures | pipeline "How results combine" + "Scale-from-zero"; sat-config "How Scale-Up Triggers Work", "Saturation as the Identity Carrier" | §2b |
| **C8** | **§2c notation cleanup** — strip `(a)/(b)` letters, keep descriptive prose. Comments/docs only, byte-identical behavior. | none (green byte-for-byte) | pipeline + sat-config (see §2c line list) | §2c |
| **C11** | **`FZ-admission`** — a never-measured variant is currently invisible to the optimizer (`PRC <= 0` ⇒ ineligible), so a model at zero replicas can never be *proactively* admitted onto it. Two parts, **both already decided in the Type 1** — transcribe, do not re-open: **(D-a)** a `Reason`-tagged **`PRC = 1` admission sentinel** at the anchor's no-variant branch, gated on `ReplicaCount == 0` **and** binder-omitted; **(D-b)** a **one-replica ceiling on the variant's target** at the three sites that can grant replicas (`costGreedyRolePick`, `fairShareRolePick`, `fillRole`), folded into each one's existing `MaxReplicas`-headroom mechanism, **skip-not-zero-cap**. The cap is what makes the sentinel legal under `W4`. Retires the deferred *partial* scale-from-zero picker as a separate scope item. | four assertions as originally specified: eligibility (a never-measured variant becomes pickable at 0 replicas) · ranking (⚠️ **written as "sorts behind every measured option" — false; corrected below and in §1.1.1/§2f: it sorts *first*, at `Cost = 0`, and safety comes from the cap plus one-cycle self-healing, not from rank**) · the one-replica ceiling holds across iterations · **skip-not-zero-cap regression** (a capped variant must not zero out the model's allocation loop) | pipeline "Scale-from-zero" | §2f |
| **C10** | **k_sat is configuration, not a constant** — TA evaluates per-replica capacity at saturation's configured k_sat (`KvCacheThreshold`, default 0.80) instead of the hard-coded `DefaultKSat = 0.85`, which mirrored a *watermark*. Resolver + 4 threaded sites; `DefaultKSat` **deleted**. Not a combine bug; a correctness/configurability fix — the numeric shift is sub-1% at default config, *not* the ~6% an early draft claimed (§2e.3). | `resolveKSat` unit table; TA `Analyze` fixture with `KvCacheThreshold: 0.5` asserting PRC tracks config (red: pinned at 0.85), expected **2618.9**, **tolerance ≤1% relative** — the file's `muSat*0.10` idiom is *above* the 6.17% bound and stays green at 0.85 (§4) | throughput-analyzer (5 named locations) | §2e |
| **C9** | **Dev-guide multi-vote sections + goldens endgame** — multi-vote reference prose; **relax/remove** the #1513 sat-only goldens as an explicit commit once the multi-vote goldens cover the single-vote sub-case. | multi-vote goldens; hand-worked design examples | all touched dev-guides finalized, **plus two documentation-only items that have no code commit of their own** and would otherwise be homeless: the `U5` capacity-gauge limitation (pipeline "Observability") and the `W3` priority-idiom prose (sat-config "V2 Analyzer Parameters" + "Validation Rules") — see §5 | §4 |

[↑ TOC](#toc)

---

<a id="2-bugs"></a>
## §2 The four combine-arithmetic bugs

All **dormant with a single vote** (masked because saturation is the only PRC and unit-mixing across
analyzers can't manifest); each becomes real the moment a second analyzer votes. Fix here, each with a
regression test that is **red pre-fix** under a two-vote fixture. Source: design doc [§ bugs].
`#4` was **downgraded** (traced 2026-08-03; not an active sizing bug — residual is observability
`Utilization` only; confirm at coding whether any observability cleanup rides — default: none).

> **Line numbers in this doc are informational-as-of-authoring; function names are authoritative.**
> C1–C5/C7/C8/C6a/C6b have landed and moved the pipeline files by hundreds of lines, so any `file.go:N`
> written before a given commit may now point into a different function. Navigate by
> `grep -n "func <name>"`, not by the cited line. Citations were re-verified against C6b's tip
> `d9f3b97e` on 2026-08-07 and the stale ones corrected (two in this section, one in §2 #5 (iii), one
> in item 5 above); citations added after that date are as-of-then. Same principle as the rebase-target
> rule — a pinned number is a snapshot, the named symbol is the moving ref.

> **Item 5's five *what* questions are ANSWERED** (refreshed 2026-08-07 against the frozen Type 1;
> supersedes the earlier "five open questions / C6c is status-quo-preserving on every one of them" box).
> The Type 1's § open queue is empty. Summary, with the full record in [§7.1](#7-1-what):
> - **`W5`** — the currency is **GPUs**, not replicas, and the Type 1 fixes the unit **per site** in a
>   nine-row table. `fairShareCap` becomes a whole-replica **`floor` fill**. → **C6c**.
> - **`W1`** — one entitlement per **model**, spent jointly across roles. **Behavior change.** → **C6e**.
> - **`W2`** — priority **orders** but never **scales** an entitlement. **Deferred out of PR-2**
>   (TA-neutral; Dean's criticality test). Consequence for C6c: site (v) is **converted, not deleted**.
> - **`W3`** — **documentation only**, no API change. → **C9** (§5).
> - **`W4`** — no conversion factor ⇒ **no spend** (abstain, not budget-exempt). **Behavior change.**
>   → **C6f**.
>
> **So C6c is no longer status-quo-preserving "on every one of them" — it is status-quo-preserving
> because the two behavior changes were moved out of it** (into C6e and C6f) and one was deferred
> entirely. C6c's own single behavioral exception is the `ceil → floor` boundary at `fairShareCap`
> (§2 #5 (ii)). If a site still cannot be converted without picking a side, that is a `plan__` handoff,
> not a coding judgement call.

- **#1 — `allocateForModelPaired` decrement unit (`analyzer_helpers.go:724-833` at `d9f3b97e`; this doc
  cited `:366-413`, which is now `combineVotes`) → C4.** The loop
  computes `utilByRole = n·prc/demand`, `deltaUtil = min_role`, `k = floor(deltaUtil·demand/prc)`, then
  `pickerState[i][role] -= k·prc` for **all** `i`, where `prc = prcFromVCs(variants, v)` = topology
  PRC_sat. But `roleBottleneckReplicas` reads `pickerState[i]/PRC_i`. Decrementing every analyzer's
  state by `k·PRC_sat` while dividing by `PRC_i` mixes units for `i ≠ saturation`. **Fix:** decrement
  in **replica units** (`k` replicas) or per-analyzer `k·PRC_i`, not `k·PRC_sat` uniformly.
- **#2 — `roleAggRemaining` unit-mixing (`analyzer_helpers.go:589` at `d9f3b97e`; this doc cited
  `:201`) → C3.** `max_i state[i][role]` maxes
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
- **#5 — `fairShareValue` sums (`Σ_i`) where design wants (`max_i`), in a currency that cannot be summed
  → C6c.** Limited/fair-share mode only (the cost-aware unlimited path does not use fsv). **Five**
  **lock-step** sites that must change together or units desync — sites (iv) and (v) are not in the design
  doc's original list: (iv) was found while verifying §2d.5, (v) by the reviewer 2026-08-07.
  The Score decision that this bug's fix depended on is **settled in §2d** (Score leaves fsv entirely);
  the old "× Score only if Score is meant to weight budget" hedge is **withdrawn**.

  > **The currency is GPUs (refreshed 2026-08-07 — this section previously said *replica space*).** The
  > frozen Type 1's `W5` fixes the unit **per site** in a nine-row table (§ open's answered block; derived
  > detail in §2d.5 here). Read the table; this section is its implementation, not its definition.
  >
  > **Row 0 is the only conversion in and row 8 the only conversion out.** Each ballot entry's own metric
  > is converted once, at entry to the combine:
  > ```
  > toGPUs(metric, PRC, GPUsPerReplica) = (metric / PRC) × GPUsPerReplica
  > ```
  > An entry with **no PRC for the reference variant has no conversion factor and therefore contributes
  > nothing** (`W4` → C6f). Rows 1–6 are then **all GPUs**, so nothing inside the combine needs to know
  > which analyzer a number came from. Row 8 converts the resulting GPU bound back down into *that
  > analyzer's own* metric.
  >
  > **What this makes possible:** `Σ_role` is legal in GPUs and only in GPUs (invariant 10), which is what
  > lets `W1`'s single per-model entitlement be spent jointly across roles at all (C6e).
  >
  > **Mechanical reviewer check, carried verbatim from the Type 1:** *if a number has no unit, it must not
  > appear on the left of an assignment that reduces a budget.* Exactly two rows are dimensionless — row 5
  > (`sortByRemainingDesc`'s ordering key) and row 7 (the scale-down tie-break) — and **neither is ever
  > spent**. Any other unitless quantity reaching a subtraction is the bug reappearing.

  - **(i) `fairShareValue` (`greedy_score_optimizer.go:73`) — rows 0, 1, 2.** Replace
    `Σ_i Score_i × Σ_role ps[i][role]` with the **GPU-space** claim:
    - **row 0** — convert each participating entry's `ps[i][role]` to GPUs via
      `toGPUs(ps[i][role], PRC_i[v_role], GPUsPerReplica[v_role])`;
    - **row 1** — across analyzers within one role, take **`max_i`, never `Σ_i`** (this is the wrong
      operator half of the bug);
    - **row 2** — across roles within one model, **`Σ_role`** (legal here, and only here);

    then × `priority` for **ordering only** (row 5) — **no Score**. `v_role` = the role's first
    `sortByCostEfficiencyAsc` candidate with `PRC > 0` (§2d.5).
    **Signature change required:** today's `fairShareValue(priority, s, ps, roles)` receives no variant
    list, so it cannot reach `v_role` — and in GPU space it now also needs `GPUsPerReplica`, which lives
    on the same `VariantCapacity`. Hand it the **same** `[]domain.VariantCapacity` the picker iterates
    (`w.anchor.VariantCapacities`) — not a separately-sourced copy — so both sides select an identical
    `v_role`. All three call sites change together (`:133` initial, `:348` / `:350` recompute).

    **Signature — DECIDED 2026-08-07: option (a).** `fairShareValue(priority, s, ps, roles, variants)`
    with `variants []domain.VariantCapacity`. Smallest surface, keeps fsv a free function over explicit
    inputs, and — the reason that matters more than surface area — passing the *same slice* the picker
    iterates is what makes both sides select a bit-identical `v_role`.

    **The `v_role` selection rule may live in a small local helper** used by (i) and (iv)'s bound — both
    are the *same* rule evaluated at the *same* instant (fsv time), so one function is right. Suggested
    name `referenceVariantForRole(vcs, role) (domain.VariantCapacity, bool)` — "reference", not
    "cheapest", because its job is to *denominate the claim*, not to pick what gets allocated.

    **Extraction guidance (answers the coder's Q1).** **Do** extract two small helpers, because C11 makes
    three grant sites share one ceiling and lock-step is the entire point of this item: (1) the row-0
    `toGPUs` conversion, and (2) the row-6 whole-replica `floor` fill. **Do not** extract a cross-site
    `cheapestSizedVariantForRole` over the four picker loops — see the box below.

    > **DECIDED — do NOT unify `referenceVariantForRole` with the picker loops.** A three-way extraction
    > over `fairShareRolePick`, `costGreedyRolePick` / `fillRole` and `roleDemandGPUs` was proposed and is
    > **declined**, for a reason that is load-bearing rather than stylistic: those loops take the first
    > **feasible** candidate, and they *must* fall through past the reference variant when the cheap
    > accelerator pool is dry (`greedy_score_optimizer.go:420`) or the cheap variant is at `MaxReplicas`
    > (`:427`). fsv's reference and the picker's landing variant are **allowed and expected to disagree**.
    > In GPU space that disagreement no longer needs a compensating ratio at the cap — the cap divides by
    > the candidate's own `GPUsPerReplica`, which is exactly right for whichever candidate the loop lands
    > on — but the loops still differ from each other in **skip semantics**, so unifying them is scope
    > creep with a correctness edge. Two supporting facts, verified at `d9f3b97e`: there are **four** such
    > loops, not three (`fairShareRolePick:410`, `costGreedyRolePick` `cost_aware_optimizer.go:94`,
    > `fillRole` `rescale.go:439`, `roleDemandGPUs` `rescale.go:572`), and **none is a
    > cheapest-sized-variant selector** — `roleDemandGPUs` additionally scopes to one accelerator via
    > `variantsOnType`, so its notion of "cheapest" differs by construction. Keep `rescale.go` out of C6c.
    >
    > **What survives the pivot:** the **reference-variant approximation in the numerator**. fsv still
    > denominates the claim using one representative variant per role, which is an approximation whenever
    > the role's variants have different PRCs. GPU space does not fix that and is not meant to.
  - **(ii) `fairShareCap` (`greedy_score_optimizer.go:423`) — row 6: a whole-replica `floor` fill.**
    > ⚠️ **The entire `prcRef` design is GONE (refreshed 2026-08-07).** This item previously specified
    > `capN = ceil(target × prcRef[role] / vc.PerReplicaCapacity)`, with a threaded per-role `prcRef`
    > value map, a capture-before-refresh ordering requirement, and a grep step forbidding in-closure
    > derivation. **None of that exists in GPU space.** If you are working from a trigger, review note, or
    > pre-freeze reading that mentions `prcRef`, it is superseded — see §2d.5 *What stops existing*.

    **The replacement, verbatim from the Type 1:**
    ```
    fairShareCap = floor( remaining_GPUs / GPUsPerReplica[vc] )
    capN         = min( fairShareCap, gpusAvail / GPUsPerReplica[vc] )
    ```
    The budget arrives already in GPUs (rows 2–4), so the cap divides by the **landing candidate's own**
    `GPUsPerReplica` — no reference ratio, because there is nothing left to compensate for. This is the
    integral-replica rule from the Type 1's § units: *never round a GPU share into replicas; commit whole
    replicas while a whole replica's worth of the resource remains, and return the remainder to the pool.*

    > ⚠️ **`floor`, not `ceil` — this is the one place the conversion is NOT value-neutral, and it must be
    > called out in the commit message.** `ceil` is the pre-existing rounding and **over-grants by up to
    > one replica at every boundary** where the remaining share is not an exact multiple of
    > `GPUsPerReplica`. The correction is a **one-replica behavior change at the boundary**, in the
    > conservative direction. It needs its own **mid-replica fixture** (§4) — a case where the remaining
    > share is strictly between two whole replicas — and it is the reason C6c can legitimately move a
    > golden.

    **Correction to this plan's earlier claim that C6c cannot move a golden.** That claim was verified
    against the **replica-space** pivot and does **not** survive `ceil → floor`: the #1513 sat-only goldens
    *do* reach `fairShareRolePick`'s cap at `sorted[0]` (with one active model `allocationMean = 0`, so
    `target = fsv` and the fair-share path is exercised), and `target` is generally fractional. So a golden
    **may** move at C6c. If one does, the coder must **prove** the delta is exactly the `floor` boundary —
    one replica, on a variant whose remaining share was mid-replica — and take it to Dean before adjusting
    the golden. Any other delta is a bug, not a boundary.

    **What made `ceil(target / vc.PerReplicaCapacity)` wrong in the first place** (kept because it explains
    why the site is in the lock-step set at all): it divided the fsv-unit `target` by **that candidate's
    own** PRC on every loop iteration, while `target` was denominated in the *reference* candidate's PRC.
    The picker skips candidates on two conditions the reference selection does not model
    (`gpusAvail < gpusPR` — the cheaper accelerator pool is dry, `:420`; `headroom <= 0` — the cheaper
    variant is at `MaxReplicas`, `:427`), so the cap was measured in one variant's capacity and applied to
    another's. GPU space removes the mismatch by construction rather than compensating for it.

    **Signature:** `fairShareRolePick(target, s, roles)` — unchanged from today apart from `target`'s unit.
    The two currently-dead parameters (`_ = s`, `_ = roles`, `:399-400`, commented "available for future
    multi-analyzer demand inspection") stay dead **in C6c**; `roles` becomes live in **C6e**, where `W1`
    turns the per-role split into a sequenced draw against a shared balance.
  - **(iii) scale-down tie-break `sortVariantsForScaleDown` (`cost_aware_optimizer.go:165-188`, weighted
    sum `:172` inside the `weighted` closure `:166-175`) — row 7. MOVED TO C6d.** A **second**
    `Σ_i Score_i × PRC_i[v]` site. Lower severity (orders scale-down candidates within a role, never
    sizes), but the same wrong-operator/mixed-unit pattern — drop the Score factor and tie-break on the
    **binding** analyzer's PRC (`combineVotes` binder, `up=false`), then name ascending.

    **Row 7's unit is *dimensionless coverage per GPU freed*, and the operator is `max_i`, never `Σ_i`.**
    It is one of exactly two dimensionless rows in the table (the other is row 5's ordering key), and —
    per the mechanical reviewer check — **neither is ever spent**: a ranking key does not reduce a budget,
    so it needs no currency.

    **Why it moved out of C6c:** it is the one bug-#5 site on the **scale-down** path, and `U2`'s negative
    test (the scale-down iteration never invokes the per-variant sizing refresh) belongs beside it. C6d
    already owns the scale-down path via finding (c) in `safeRemovalReplicasForRole` — a *different*
    function, which does not touch this tie-break. This site is **also** touched by C7's landed N7
    role-coverage decision; coordinate both edits.
  - **(iv) `allocateForModel`'s picker-state clamp (`greedy_score_optimizer.go`, the
    `if ps[i][role] > target { ps[i][role] = target }` loop, ~`:285-291`) — row 8: the only conversion
    **out** of GPU space.** It clamps **raw-capacity** `ps` against `target`. The moment `target` leaves
    raw capacity the clamp truncates every role to a handful of capacity units. **This is the site that
    makes #5 a units bug and not merely a shape bug** — it is inert today only because `target` is the
    *sum over roles*, so each individual role's value is already ≤ it.

    **Shape: convert the GPU bound down into *that analyzer's own* metric; leave `ps` raw.** Row 8's unit
    is *that analyzer's own metric*, reached by dividing out `GPUsPerReplica` and multiplying by **its
    own** PRC — GPUs → replicas → metric:
    ```go
    for _, role := range w.roles {
        vc, ok := referenceVariantForRole(w.anchor.VariantCapacities, role) // same rule as v_role, site (i)
        if !ok {
            continue
        }
        g := gpusPerReplica(vc) // topology, immutable within the cycle
        if g <= 0 {
            continue
        }
        for i := range ps {
            prc := prcForVariant(w.s[i].Result, vc.VariantName) // nil-safe
            if prc <= 0 {
                continue // no conversion factor ⇒ no spend — see W4 below
            }
            if bound := (target / g) * prc; ps[i][role] > bound {
                ps[i][role] = bound
            }
        }
    }
    ```
    Rationale, and why moving `ps` itself is worse: `ps` is raw capacity to **every** downstream consumer
    — `roleBottleneckReplicas` divides it by `PRC_i` (`analyzer_helpers.go:511`), `allocateForModelPaired`
    decrements it in capacity (`:816`), `applyDeallocationForRole` likewise. Re-denominating `ps` ripples
    into `initRoleState`, `roleBottleneckReplicas`, `allocateForModelPaired` and
    `applyDeallocationForRole` — far beyond #5's scope. Clamping "the combined per-role replica count"
    instead has no landing site: `ps` is per-analyzer and the combine is downstream of it. Converting only
    the bound keeps the comparison commensurable at one line, and keeps `ps` commensurable with `prc` so
    `allocateForModelPaired`'s `k = max(floor(deltaUtil·demand/prc), min(1, n))`
    (`analyzer_helpers.go:788`) is untouched.

    > ⚠️ **Inertness in `[sat]`-only holds for the SINGLE-ROLE case only** (correction the Type 1
    > records). `ps[i][role] = d_role` and `bound = (target / g) × prc`, and `target` is the sum over
    > roles, so a single-role model's bound is `≥ d_role` for the same reason the clamp is inert today.
    > **Do not extend that argument to `[sat]`-only P/D** — see the multi-role divergence below.

    **Multi-role (P/D) divergence — why C6e exists.** `target` is a **scalar** summed over roles, while
    the cap is applied **per role**. Today's per-role bound reduces to `ceil((Σ_role' d_role') / PRC_vc)`;
    after the conversion it is `ceil((Σ_role' d_role' · PRC_ref[role] / PRC_ref[role']) / PRC_vc)`. The two
    agree **iff all per-role reference PRCs are equal** — so a fixture where prefill and decode share the
    same PRC *or* the same `GPUsPerReplica` **cannot distinguish** correct from role-mixing (invariant
    10). Letting each `(analyzer, role)` pair clamp against the **full** `target` is a **double-spend**;
    fixing it is `W1`, which is a **behavior change** and therefore lands in **C6e**, not here.

    **The no-PRC analyzer — `W4` is ANSWERED: no conversion factor ⇒ no spend.** An entry with no PRC for
    the role's reference variant cannot price the variant, so it **abstains** — it is *not* budget-exempt.
    The `continue` above is the abstention. Zeroing it would delete its vote; clamping raw capacity
    against a GPU number is the bug itself. This is harmless in the same cycle because the same
    `prc <= 0` filter in `votesFromPickerState` (`analyzer_helpers.go:441-443`) already excludes the entry
    from `roleBottleneckReplicas` for that variant, so it cannot drive allocation of the variant whose
    budget it escaped. **Making the abstention a tested property is `W4` → C6f**, with an equality
    fixture: a `[sat,TA]` ballot in which one analyzer has no PRC for the reference variant must produce
    the **same allocation** as the same fixture with that analyzer absent from the ballot.
  - **(v) `fairShareValue`'s own fallback (`greedy_score_optimizer.go:78-92`) — row 9. CONVERTED, NOT
    DELETED.** Taken when `priority × weighted <= 0`, it returns `max_role ps[i][role]` in **raw demand
    units**. After (i) the function would return GPUs on its primary path and demand-space on its
    fallback — the exact desync this bug is about, inside the very function being rewritten — and that raw
    value then flows into (ii)'s cap and (iv)'s clamp, mis-sizing by a factor of PRC. **Fix:** make the
    fallback the primary expression with the `priority` factor dropped, in GPUs:
    `Σ_role toGPUs( combineVotes(votesFromPickerState(…, role, v_role), up=true), PRC_ref[role], GPUsPerReplica[v_role] )`.
    That fixes the currency and incidentally removes a pre-existing asymmetry — the fallback **maxes** over
    roles where the primary **sums**, so a P/D model's fallback is systematically smaller than its primary
    value (pre-existing, not caused by C6c).

    > ⚠️ **PR-2 converts this site; PR-2 does not delete it.** The Type 1's `W5` row 9 calls row 9 *dead*
    > — that is the **end state after `W2` lands**, not this PR. `W2` (priority orders but never scales)
    > is **deferred**, so the branch is still reachable and must keep working in the new currency. When
    > `W2` eventually lands, the deletion is classified **DEPRECATED** with this wording, supplied
    > verbatim by the Type 1 and reserved for that commit — do **not** use it in PR-2:
    > *"priority-zero fallback in `fairShareValue` — removed; `priority` no longer scales the claim, so
    > the branch is unreachable, and a zero claim is the correct output rather than a condition to
    > substitute a manufactured one for."*

    Deleting it in PR-2 would additionally change the `fsv > 0` admission at `:134` for hand-built
    zero-priority fixtures. Post-C6c reachability is effectively **nil in production**: `ApplyDefaults`
    rewrites `Priority == 0` to `DefaultPriority = 1.0` (`config/saturation_scaling.go:275-276`) and
    validation rejects negatives, and Score has left fsv — so the guard can only trip on all-zero
    remaining demand, where both paths return 0. No golden can move on this site; convert it for honesty,
    not for behavior. Also **rewrite the doc comment at `:53-60`**, which states
    `fsv = priority × Σᵢ Score_i × Σ_role pickerState[i][role]` — it names Score.

  **Units bookkeeping — `target` is priority-scaled GPUs, and the comment must say so.**
  `target = w.remaining − mean` and `w.remaining` is fsv, which carries the `× priority` factor. So after
  (i) the honest name for `target`'s unit is **priority-scaled GPUs**, not GPUs. Three points, in the
  order they matter:
  1. **The conversion does not change this.** Today `target / PRC` is equally priority-scaled, so every
     cap and clamp number moves identically. It is not a regression introduced by C6c.
  2. **It becomes newly misleading, and the comment is the deliverable.** Post-fix the expression *reads*
     like a resource count. Write "priority-scaled GPUs" in the doc comment at (ii) and at (iv); do
     **not** write "GPUs".
  3. **Dividing `priority` back out is `W2` — SETTLED as deferred, not open.** The Type 1's end-state
     formulas are `claim = Σ_role (desired[role] − current[role]) × gpusPerReplica` with **no**
     `priority`, and `ordering key = priority × claim` used for the **sort only** (invariant 11: priority
     orders, never scales). `W2` is TA-neutral, so it failed Dean's *"is this critical for TA
     integration"* test and became a future TODO — **do not re-open it, do not route it to Dean, and do
     not hold this refresh on it.** Note the asymmetry it interacts with: site (v)'s fixed fallback
     **deliberately drops** `priority` (it would otherwise be `≤ 0` exactly when it fires), so post-C6c
     the primary path is priority-scaled and the fallback is not. Site (v)'s "fixes the currency" means
     *fixes the metric→GPU conversion*, not *makes the two paths numerically equal*.

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
  2026-08-06; design § findings `N8`).** The per-variant sizing-fallback in `bindingAnchor` (`:208`)
  currently borrows saturation's sizing for a binder-unknown variant when `satEnabled := satNR != nil &&
  satNR.Enabled` (`:169`). `.Live`-gating it (the original D1) is **nearly vacuous**: the fallback fires
  *only* when sat is already not binding (`!Live` **or** non-informative), so `&& satNR.Live` still
  admits a `Live`-but-no-data sat lending a stale stored PRC. **Instead DROP the fallback** — a
  binder-unknown variant keeps its identity fields but abstains with **PRC=0**, exactly as `[TA]`-only
  already does. Byte-identical on the #1513 + Test 9 fixtures (sat binds in both → the fallback never
  fires), makes partial-scale-from-zero metric-consistent, dissolves findings **N1** + the
  fallback half of **N5**, and implements Dean's rule "when TA binds, every sized entry is TA's." This
  **revises PR-1 plan decision V9** (PR-1 ships the fallback as-is — see PR-1 §12).
  ⚠️ **LANDED in `952d2fff`, but the reasoning above is superseded — keep the conclusion, replace the
  argument** (the shipped comment was rewritten accordingly in `2ae440e3`). The premise *"the fallback
  fires only when sat is already not binding"* — i.e. that a binder omits a variant only when it is
  enabled-but-not-binding — is **false about the binder**: `ResultIsInformative` is an **any-variant**
  predicate, so a perfectly healthy binder can price **nothing** for one particular variant. Same family as
  review finding `V6`'s inverted (b)-fallback-domain claim; **do not carry either forward.** The real
  argument is **structural**: when saturation binds it is both identity carrier *and* binder, so the sizing
  map is built from the very slice the merge iterates and every lookup hits — the else branch is
  **unreachable**. It can be reached only with a saturation entry present as *carrier* but not binding,
  `!(Enabled && Live && Informative)`, which is exactly when saturation's own sizing is the least
  trustworthy thing to borrow: stale, no-data, or not even asked for. The **disabled** case belongs in that
  set, because the carrier is located **by name, not by vote** — an earlier draft wrote the narrower
  `Enabled && !(Live && Informative)`, inherited from the very claim it was replacing. The byte-identical
  ship-gate claim below survives on this structural ground, not on the old premise.
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
  **This holds only because the *fixed* fallback carries the same filter (added 2026-08-07).** The claim
  "(b) falls out of the participation filter" is true of the primary path by construction, but a model
  whose demand is *entirely* unactionable computes `0` on the primary path and would then drop into
  `fairShareValue`'s fallback — which, **unfixed**, returns the raw unactionable number and re-inflates
  exactly the value (b) forbids. §2 #5 site (v) rewrites the fallback as the primary expression minus
  `priority`, so it inherits the filter and returns `0` too. (b) and (v) must land together; neither is
  complete alone. A fixture must pin **both** halves — see §4.
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

> **REWRITTEN 2026-08-07 from the frozen Type 1.** This section previously specified a **replica-space**
> pivot with a threaded per-role `prcRef` reference ratio. The frozen design pivots to **GPU space**
> instead, and that removes the entire `prcRef` construction rather than refining it. See *What stops
> existing* below before reading any pre-freeze note, review comment, or trigger that mentions `prcRef`.

fsv's currency must match every consumer of `target`. See §2 #5 for the five sites (i)–(v), their edits,
and the per-site unit assignments; this section is the **derivation and the sat-only argument**.

**The currency is GPUs.** One conversion function, applied once per ballot entry:

```
toGPUs(metric, PRC, GPUsPerReplica) = (metric / PRC) × GPUsPerReplica
```

**The nine rows of the Type 1's per-site unit table**, reproduced here as the derived detail C6c/C6d/C6e
implement (the Type 1's `W5` is the authority; if this table and it ever disagree, the Type 1 governs):

| row | site | unit | rule |
|---|---|---|---|
| 0 | ballot entry → claim | **GPUs** | `toGPUs(metric, PRC, GPUsPerReplica)`; **no PRC ⇒ contributes nothing** (`W4`) |
| 1 | across analyzers, one role | GPUs | `max_i` — **never** `Σ_i` |
| 2 | across roles, one model | GPUs | `Σ_role` — legal here **and only here** (invariant 10) |
| 3 | `computeMean` | GPUs | mean of **unweighted** claims (`W2`) |
| 4 | `target = claim − mean` | GPUs | **one per model**; `Σ_role spend ≤ target` (`W1`) |
| 5 | `sortByRemainingDesc` | **dimensionless rank** | `priority × claim`; **never spent** |
| 6 | `fairShareCap` | **replicas (integral)** | `floor(remaining_GPUs / GPUsPerReplica)`, then `min` with the real pool |
| 7 | site (iii) tie-break | **dimensionless** coverage per GPU freed | `max_i`, not `Σ_i`; **never spent** |
| 8 | site (iv) clamp | **that analyzer's own metric** | convert the GPU bound down through **its own** PRC and `GPUsPerReplica`; `ps` stays raw |
| 9 | site (v) fallback | **dead** — after `W2` | converted in PR-2 (`W2` deferred), deleted later |

**Three closure properties**, and they are what make the pivot verifiable rather than merely different:

1. **One conversion boundary.** Row 0 is the only conversion *in*; row 8 the only conversion *out*. Rows
   1–6 are all GPUs, so no intermediate step needs a compensating factor.
2. **The round-trip hazard is GONE, not solved.** The old design's failure mode was dividing by one
   PRC and multiplying by another (or by the same PRC re-read at a different instant). In GPU space the
   cap divides by `GPUsPerReplica`, which is **immutable topology** — invariant 9's drift hazard cannot
   arise for the cap at all. There is nothing to capture and nothing to keep in sync.
3. **Only rows 5 and 7 are dimensionless, and neither is ever spent.** Mechanical reviewer check, carried
   verbatim from the Type 1: *if a number has no unit, it must not appear on the left of an assignment
   that reduces a budget.*

**What stops existing** (delete on sight; do not port forward):
- the `prcRef` per-role reference-PRC parameter and its threaded signature;
- the **copied value map** requirement (`map[string]float64` sourced from the pre-refresh
  `w.anchor.VariantCapacities`);
- the **capture-before-refresh ordering** requirement at `greedy_score_optimizer.go:310`;
- the grep step forbidding in-closure derivation of the reference PRC;
- the 5× fall-through cap table and the value-drift / identity-drift failure-mode pair.

**What survives the pivot:** the **reference-variant approximation in the numerator**. Rows 0–2 still
price a role's claim using `referenceVariantForRole`'s candidate, so the claim is exact only if the picker
lands on that variant. GPU space removes the *round-trip* error, not the *approximation*.

**One standing fact worth keeping from the old measurement work** (it is load-bearing for §2f's cap and
for reading the picker at all): **site (ii)'s cap bounds only per-iteration progress; site (iv)'s `ps`
bounds the allocation total.** `allocateForModelPaired` (`analyzer_helpers.go:736-832`) loops on
`anyRoleNeedsScaleUp` and re-picks every iteration; the cap enters only at
`n = min(bottleneckReplicas, capN)` (`:760`), while `k = max(floor(deltaUtil·demand/prc), min(1, n))`
(`:788`) carries a `min(1, n)` forward-progress floor and termination/pool-drain are driven by `k`
(`:816`, `:819`). An understated cap therefore costs iterations, not replicas — which is exactly why a
cap of **`0`** is a different animal, and why §2f requires **skip, not zero-cap**.

#### Sat-only invariance

Dean's governing constraint: **do not break current behaviour when saturation is the only analyzer.**
Two invariants from the frozen Type 1 carry the argument.

**Invariant 8 — a one-analyzer ballot is a pass-through *algebraically*.** Verified at source: with one
vote `combineVotes` has `b = 0`, `e = votes[0].Value`, and the correction loop's only term has
`excess = Score₀ − Score₀ = 0`, so it returns `votes[0].Value` exactly, binder `0`
(`analyzer_helpers.go:369-406`). Score cannot influence a one-analyzer ballot even *before* C6c removes
it. **Consequence:** a saturation-only golden moving is never the combine's fault — and those goldens do
**not** cover combine arithmetic. Claiming they do is a **category error**.

**Invariant 7 — sat-v2-only ⇒ the anchor is byte-for-byte identical, always.** This needs a **direct
test**, not an inference from goldens: assert `anchor == saturationEntry` field-for-field before, during
and after allocation, and assert the per-iteration sizing refresh is **not invoked**. Observe the
`withSatEntry`-stability rule when writing it (carried from the #1513 review, Finding 2).

Per-site, in GPU space:

| site | `[sat]`-only effect | why |
|---|---|---|
| (i) fsv, **single model** | no change to decisions | `allocationMean = 0` with one active model (`greedy_score_optimizer.go:239-240`), so `target = fsv` |
| (i) fsv, **≥2 models** | **changes ordering** — intended | claims priced in GPUs are comparable across models; tokens/s vs req/s were not |
| (ii) cap | **value-neutral EXCEPT at the `ceil → floor` boundary** | the GPU budget divided by `GPUsPerReplica` reproduces today's replica count whenever the share is an exact multiple; `floor` differs from `ceil` by one replica when it is not |
| (iii) tie-break | exactly identical | one analyzer ⇒ `weighted(v) = 1.0 × PRC_sat[v]`, and the replacement reads the `combineVotes(up=false)` binder's PRC, which with one vote **is** `PRC_sat[v]` |
| (iv) clamp | **inert — SINGLE-ROLE ONLY** | `ps[i][role] = d_role` and the bound is `≥ d_role` because `target` sums over roles. ⚠️ **Do not assert this for `[sat]`-only P/D** — see §2 #5 (iv)'s multi-role divergence |
| (v) fallback | unreachable | `ApplyDefaults` rewrites `Priority == 0 → 1.0`; every #1513 case is `Priority: 1` |

**Two `[sat]`-only behavior changes, and they are deliberate**, which is why they are *not* in C6c:
- **`W1` (C6e)** changes `[sat]`-only **P/D** whenever the fair-share budget binds. `[sat]`-only P/D
  already makes **two independent full-budget draws**; TA makes it `|analyzers| × |roles|` — the finding is
  **TA-AMPLIFIED**, not TA-created.
- **`W2`** would change `computeMean` for any multi-model contended cycle with unequal priorities. It is
  **deferred**, so it changes nothing in PR-2.

**Fixture requirement — the `[sat]`-only ordering fixture must vary `GPUsPerReplica` across the two
models.** If both models share a `GPUsPerReplica`, the new factor cancels and the fixture **cannot detect
the pivot at all**. Same trap in the multi-role direction: a fixture where prefill and decode share the
same PRC *or* the same `GPUsPerReplica` cannot distinguish correct from role-mixing (invariant 10).

[↑ TOC](#toc)

#### Goldens

**Correction to this plan's earlier verified claim.** This section previously argued, with worked
arithmetic, that C6c **cannot** move a #1513 golden. That verification was performed against the
**replica-space** pivot, where the cap divided the rescale straight back out; it does **not** survive
`ceil → floor`. The sat-only goldens *do* reach `fairShareRolePick`'s cap at `sorted[0]` — with one active
model `allocationMean = 0`, so `target = fsv` and the fair-share path is exercised — and `target` is
generally fractional.

So the rule for C6c is: **run the goldens per commit and report.** If one moves, the coder must **prove**
the delta is exactly the `floor` boundary — one replica, on a variant whose remaining share was
mid-replica — and take it to Dean via a `plan__` handoff before adjusting the golden. **Any other delta is
a bug, not a boundary.** Do not rewrite a golden to accommodate the change on your own judgement.

The blunter alternative — keep fsv in demand space and fix only the `Σᵢ`→combine shape — remains
**rejected**: the combine has to be in a shared resource currency for a `max` across analyzers with
different capacity units to mean anything (§2d.3).

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

**Shape — DECIDED 2026-08-07: split it into two tests.** The bullet above asks one test to assert a
**binder index**, which is not observable from `Optimize()`'s output. So:
- a **unit** assertion on `combineVotes` for the 10-vs-5-at-scores-1-and-2 ⇒ 8.33 case, asserting the
  value *and* the returned binder index. This is where the dominance arithmetic belongs; it is also
  where a wrong binder is visible at all;
- an **end-to-end** `Optimize()` ordering assertion driven by **unequal priority**. It must be unequal:
  under the currency fix equal-priority equal-demand models tie, which is the old expectation this
  section already retires — an equal-priority ordering assertion would be asserting a coin flip.

Keep the uniform-score control at whichever level it reads more clearly; it is a one-line assertion
either way.

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

⚠️ **FREEZE CORRECTION — the shipped shape is not the one this section specified, and is the reference
now.** The code block below was written before C10 landed and type-asserted directly against
`*config.SaturationScalingConfig`, clearing itself with *"verified no cycle (`internal/config` imports no
`internal/engines` package)"*. **That clearance is wrong even for the code as specified**: `internal/config`'s
own in-package tests import `throughput`, so a direct import the other way is a **test-binary** import
cycle, not a production one — the earlier check looked at the wrong binary. The coder took a fifth shape
that avoids the coupling rather than clearing it (verified read-only at `1a50b418`,
`throughput/analyzer.go:217-223`):

```go
// resolveKSat resolves saturation's configured k_sat from an analyzer-agnostic
// interface rather than importing *config.SaturationScalingConfig: this package
// cannot import internal/config (that package's in-package tests import this
// one, so the edge is a test-binary import cycle). Any config exposing KSat()
// satisfies it.
func resolveKSat(cfg domain.AnalyzerConfig) float64 {
	if p, ok := cfg.(interface{ KSat() float64 }); ok {
		if k := p.KSat(); k > 0 {
			return k
		}
	}
	return fallbackKSat
}
```

**The layering property holds by construction, not by a cleared cycle check:** production `throughput`
imports **nothing** from `internal/config` — `KSat()` was added *inside* `internal/config`
(`saturation_scaling.go:243`) as the concrete method the self-declared interface binds to, so the
assertion is against TA's own already-injected config parameter, not a new dependency. `fallbackKSat`
(0.80, `constants.go`) duplicates `config.DefaultKvCacheThreshold` rather than importing it, guarded
against drift from both sides: `k_sat_test.go`'s `TestFallbackKSatMatchesConfigDefault` pins
`fallbackKSat == config.DefaultKvCacheThreshold`, symmetric with `config.go`'s existing guard in the
opposite direction (the same duplication pattern `throughputAnalyzerName` already uses). Called once at
the top of `Analyze`; the value threads down to the three remaining sites below.

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

<a id="2f-fromzero"></a>
## §2f Proactive from-zero admission — lands in C11

> ⚠️ **HALF-SUPERSEDED BY THE FREEZE (2026-08-08). Read §1.1.1 before this section.**
> **(D-b), the one-replica ceiling, LANDED** — `b6bb525c` plus the `fillRole` coverage in `79a590d6`, via a
> new `maxTargetReplicas` helper rather than the per-site fold this section instructs (§1.1.0 deviation 4
> gives the reason the literal form does not work). **(D-a), the sentinel, is DEFERRED** — a regression
> proven by mutation, not a skipped step: an anchor-only sentinel makes a variant selectable without making
> it *sizable*, so `roleBottleneckReplicas` abstains, `n = 0`, and `allocateForModelPaired` breaks out of
> the model's whole allocation loop. Whether the sentinel may enter the **voting set** is an `N8` question
> and therefore the **Type-1 owner's**, raised by handoff. The net shipped state is **built, not enabled**.
> Everything below is preserved as the specification the commits were written against — the (D-a)
> subsection is now a *record of an attempt*, not an instruction, and its "transcribe, do not re-open"
> framing is spent. **Do not re-attempt (D-a) inside PR-2 on the strength of this section.**

**Added by the 2026-08-07 refresh.** The frozen Type 1 answers Dean's own follow-up
(*"the anchor no-variant fallback sets PRC=1 for unknown never seen if TA is binding? sat remains as
is?"*) and **decides both the mechanism and the cap** — per *"don't leave design decsions to coder."*
This section **transcribes** those decisions; it does not re-open them. The Type 1's `FZ-admission` row
and its decision block are the authority.

**Line numbers below are as of `ta-anchor-dynamic-refresh@d9f3b97e`, now up to 16 commits stale — grep by
symbol, not by line.**

### The gap

`bindingAnchor`'s merge takes identity from the (a) carrier (always saturation, located **by name, not by
vote**) and `PerReplicaCapacity` **only** from the binder's map. When the binder omits a variant, the
`else` branch at `analyzer_helpers.go:213` leaves `PerReplicaCapacity` at its zero value, and at
`PRC == 0` **every** eligibility gate filters the variant out — `cost_aware_optimizer.go:95`, `:125`,
`:239`; `greedy_score_optimizer.go:411`; `rescale.go:443`, `:573`.

The defect is a **vocabulary** gap, not a lost number: *abstain* is the only thing the anchor can say, and
"no opinion about a variant we know" and "a variant nobody has measured yet" are different states.
Saturation *has* computed a positive PRC for the never-seen variant, and it correctly reaches nothing (the
anchor merge does not read it; the `Live`-filtered vote prune drops it) — importing it would be exactly
the KV-tokens-sizing-a-req/s-anchor borrow that N8 rejects. **The sentinel supplies the missing
vocabulary; it does not revive the discarded number.**

Under a TA binder the only remaining admission path is the reactive `scalefromzero` engine, which tests
inactivity **per variant** but triggers **per model** and then brings up *every* inactive variant at 1
replica, unranked by cost — so a brand-new variant is admitted only *after the model backs up*. That
coarseness is `N9` and stays **out of scope**; what C11 fixes is that under a TA binder it stops being a
backstop and becomes the only path.

[↑ TOC](#toc)

### (D-a) Mechanism — the sentinel lives in `PerReplicaCapacity`, tagged by its own `Reason`

At the `else` branch (`analyzer_helpers.go:213`): when the binder omitted the variant **and** the (a)
identity shows `ReplicaCount == 0`, set `PerReplicaCapacity = 1` and set `Reason` to a dedicated constant.

- **`ReplicaCount == 0` is a required guard, not a refinement.** The binder also omits variants that *are*
  running but have no usable metric this cycle, and there abstain remains right — the variant is already
  up, so admission is moot and sizing must not be fabricated. TA's own scale-from-zero complement already
  covers *previously-live* zero-replica variants from persisted supply, so "binder omitted it **and**
  `ReplicaCount == 0`" is precisely "never seen". `ReplicaCount` comes from the (a) identity, so it is
  **already in hand at the merge site** (`:204`) — no new plumbing.
- **Saturation is untouched.** When saturation binds, nothing changes at all.
- **The sentinel is in the binder's own currency**, so it is a *declared minimum*, not a borrowed
  measurement. N8 stays intact.
- **The `Reason` tag:** a pipeline-side sibling of the `satReason*` family. **The exact spelling is the
  coder's; the existence of the tag is not.** It reuses existing plumbing, so it adds **no new metric
  series**, and it is what the cap keys on.
- **Why keying the cap on `Reason` is safe:** `Reason` and `PerReplicaCapacity` move as a **set** at every
  site that writes them — the build-time merge (`analyzer_helpers.go:207-212`) and the per-iteration
  refresh (`refreshAnchorSizing:569-572`) copy the pair together. The tag therefore cannot outlive the
  sentinel: the first cycle a voting entry actually sizes the variant, the real PRC and the real reason
  replace both at once. The refresh's two `continue` branches (`:562`, `:566`) leave the sentinel standing,
  which is correct — nothing has measured it yet.

**Rejected: a separate `admissible` predicate** leaving `PRC = 0`. It would have to be threaded through
all **six** `PRC <= 0` gates listed above, and it splits eligibility from ranking across two fields that
must then be kept in agreement. Writing into the field those gates already read costs one branch and keeps
both properties on one value.

**Rejected: the self-clamping `PRC = TotalDemand` seed** (so that `ceil(demand / PRC) = 1`). It makes the
never-seen variant rank *best* precisely when scale-up is needed. The explicit cap states the intent —
*one bite, then measure* — instead of leaning on an arithmetic coincidence.

**What `PRC = 1` gets right on its own, and what it does not:**

| concern | effect | |
|---|---|---|
| eligibility | clears every `PRC <= 0` gate — the whole point, riding gates that already exist | ✅ |
| ranking | `costEfficiency = Cost / PRC` degenerates to `Cost` ⚠️ **this row is false and was never buildable — see §1.1.1.** A never-seen variant's `Cost` is **0** (saturation prices `variantCost` only from live `inputMetrics`, `saturation_v2/analyzer.go:352-360`, and a zero-replica variant contributes none), so `costEfficiency = 0/1 = 0` and it ranks **first**, tying every other never-measured peer, not last. Measured PRCs being ≫ 1 was never the operative condition — ranking behind a priced peer needs a *cost-ratio* inequality the sentinel does not satisfy. Safety comes from the (D-b) cap plus one-cycle self-healing once real metrics arrive, not from rank. | ❌ |
| sizing | in the binder's currency `PRC = 1` reads as *"one replica serves 1 req/s"*, so `target / PRC` and `fillRole`'s `targets[v]++` loop treat it as real capacity. **Unclamped, one never-seen variant can absorb the whole budget one request-per-second at a time** | ⚠ needs (D-b) |

[↑ TOC](#toc)

### (D-b) Cap — a one-replica ceiling on the variant's *target*, at the three sites that grant

The bound is on the variant's **target**, expressed in **replicas**, **not** per-iteration — so a repeated
allocation loop cannot buy a second replica by going round again. All three grant sites already contain
the exact mechanism:

| grant site | grants by | where the ceiling binds |
|---|---|---|
| `costGreedyRolePick` (`cost_aware_optimizer.go:85-109`) | returns `(variant, cap)`; `cap` = `MaxReplicas − targets[v]`, else `MaxInt` | fold into that same `headroom` computation (`:100-104`), **including its `headroom <= 0 → continue`** |
| `fairShareRolePick` (`greedy_score_optimizer.go:398-437`) | same `(variant, cap)` slot; `capN` clamped by `headroom` (`:425-431`), then the `capN > 0` guard (`:432`) | same clamp, same skip |
| `fillRole` (`rescale.go:431-460`) | `targets[v]++` in a loop bounded only by `MaxReplicas` (`:452`) | add the ceiling to that same `break` condition |

> ⚠️ **SKIP the variant — do NOT return `cap = 0`.** This is not decoration. A picker that *returns*
> `cap = 0` sets `n = 0` → `utilByRole = 0` → `deltaUtil = 0` → `break`, **killing the whole model's
> allocation loop** instead of moving to the next variant. The ceiling must skip, exactly as `MaxReplicas`
> exhaustion already does.

**The cap is what makes the sentinel legal under `W4`.** `W4` says a voter that cannot price a variant may
not thereby escape the budget. Here the sentinel deliberately does *not* price capacity; the cap prices
the **spend** — exactly one replica, `GPUsPerReplica` GPUs, charged to the budget like any other.
*Unpriced capacity, bounded spend.*

**Five consumers that need no change** (transcribed with the Type 1's reason for each — do not re-derive):

- `allocateForModelPaired`'s `k` (`analyzer_helpers.go:750`, `:766`, `:788`) **inherits** the bound: with
  `prc = 1`, `deltaUtil ≤ n·1/demand`, so `k = floor(deltaUtil·demand/1) ≤ n`, and `n = min(bottleneck,
  cap)` is already capped. ⚠️ **This is a consequence, not the mechanism — do not implement the cap by
  leaning on it.**
- `applyAllocation` (`analyzer_helpers.go:71-85`) decrements each analyzer's `Remaining` from
  `prcForVariant(s[i].Result, …)` — the **ballot**, never the anchor — so the sentinel never reaches it.
  (An earlier reviewer pass named this as a sizing hazard; **that was wrong**. The real unbounded grant is
  `fillRole`.)
- `roleDemandGPUs` (`rescale.go:569-590`) takes only topology and the cost sort from the anchor; the
  replica count comes from `votesFromTotalDemand`, where no voter carries the variant ⇒ no binder ⇒ `0` ⇒
  hold.
- every scale-down and reclaim path (`scaleDownVariantSet:125`, `reclaimRole`, `rescale.go:488`, `:511`)
  computes `removable = current − minReplicas`, which is `≤ 0` at zero replicas. Skipped.
- `TotalCapacity = ReplicaCount × PerReplicaCapacity` (`analyzer_helpers.go:220`, `:573`) is `0 × 1 = 0`,
  so the sentinel never inflates aggregate capacity — it moves eligibility and the cost ordering, nothing
  else.

[↑ TOC](#toc)

### Scope

**TA-CREATED** by the Type 1's exposure test: under `[sat]`-only it cannot occur, because saturation always
binds and always seeds — so the `[sat]`-only goldens **cannot cover it in either direction**, and deferring
it would ship `[TA]`-only and TA-binding `[sat,TA]` with no proactive from-zero admission at all. That is
why it folds into PR-2 rather than waiting.

- **Retires** the deferred *partial* scale-from-zero picker as a separate scope item: its trigger is now
  named (the abstain gate cannot express *new*) and its mechanism is decided above.
- **`N9` stays out** — the reactive path remains model-triggered and unranked; that is outside anchor
  scope.
- **No new metric series** (`U5` is deferred; see §7).
- The dev-guide note beside the sibling saturation `Cost = 0` limitation is **no longer a substitute for
  the fix**, but that bug itself stays out of PR-2.

**Deletion/behavior classification for the coder's handoff:** C11 adds behavior and deletes nothing, so no
DEPRECATED/DEFERRED entry is due. State in the handoff that the `Reason` constant is **new pipeline-side
vocabulary** and name the spelling chosen, so the dev-guide and any future grep can find it.

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

> **FREEZE RECORD (2026-08-08) — the gate ran and the goldens endgame executed.** Pipeline suite at
> `a9afb740`: **386 passed / 0 failed / 1 pending** (base was 308 specs). **No golden moved anywhere in the
> stack**, including at C6c — the `ceil → floor` boundary this section warned about turned out
> value-neutral on every existing fixture, so the anticipated legitimate move never materialized. C6e's
> commit states the same result and, correctly, *"that is not evidence the fix is inert"* — the existing
> golden is single-model and demand-bound with a generous pool, i.e. blind to the double-spend by
> construction. **Invariant 7's direct test landed** in `209e148f` (both halves: field-for-field anchor
> equality and the not-invoked assertion). **The endgame executed** in `4e369f10` — the sat-only goldens
> were removed as an **explicit** commit, scenario by scenario, with a one-line mapping per removed spec.
>
> **Two gates remain and are NOT satisfied by the above**, because both post-date the runs: (1) **re-run
> `make lint`** after the rebase — `main` moved golangci-lint **2.8.0 → 2.10.0** (PR #1512), so a green run
> from before that bump does not carry forward and any new finding is the bump's, not a regression;
> (2) the rebase itself now targets plain **`main`** (PR-1 merged as `57f3fe64`), not a sibling branch tip.
> Everything below is the specification the suite was written against.

- The saturation-only characterization goldens (landed via their own PR
  [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513)) must **still** pass
  through C1–C5, C7, C8, C6a and C6b — the single-vote path is unchanged there, and every change is a
  no-op on all-live sat-only fixtures. **From C6c onward the claim weakens** (refreshed 2026-08-07):
  the currency pivot replaces `ceil` with `floor` at the fair-share cap (§2 site (ii)), a one-replica
  change at every mid-replica boundary, so a golden *may* legitimately move there. See the *Goldens*
  rule below for what to do when one does.
- **Invariant 7 needs a direct test, not just green goldens** (added 2026-08-07, from the frozen
  Type 1). "sat-v2-only ⇒ the anchor is byte-for-byte the saturation entry, always" is asserted today
  only *transitively*, through decision goldens that would stay green even if the anchor were subtly
  different but the decisions happened to coincide. Assert it **directly**: a one-analyzer `[sat]`
  ballot, anchor equal to the saturation entry **field-for-field, before / during / after**
  allocation — **plus** that the per-variant sizing refresh is **not invoked at all** on a
  one-analyzer ballot. Both halves matter: the equality is the invariant, the not-invoked assertion is
  what stops a future refactor from satisfying the equality by round-tripping through a refresh that
  merely happens to be idempotent today. Honour the `withSatEntry` stability rule when building the
  fixture (#1513's review Finding 2) or the test pins the helper instead of the anchor.
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
  - C6c — **the currency conversion and nothing else** (rewritten 2026-08-07 for the GPU pivot). Every
    fixture below asserts *status-quo-preserving re-denomination into GPUs*, with one deliberate
    exception called out as such. The two behaviour changes the frozen design also wants — `W1` joint
    spend and `W4` abstain-without-a-conversion-factor — are **C6e and C6f**, with their own fixtures;
    keeping them out of C6c is what makes "goldens green at C6c" a meaningful signal at all.
    - **fsv ordering — saturation as the *only* analyzer, and the fixture must vary
      `GPUsPerReplica` across the two models.** Two models, differing PRCs, quota-constrained: the
      model whose demand is larger *in GPUs* wins, not the one whose demand is larger in tokens/s.
      §2d.5's per-site table shows the ordering key is the **single** sat-only-observable change in
      all of C6c, and #1513 cannot see it because every golden case builds one `ModelScalingRequest`.
      A two-analyzer ordering fixture would confound the currency change with the combine change and
      would *not* discharge Dean's "do not break sat-only" constraint. ⚠ **Varying `GPUsPerReplica`
      is load-bearing under the GPU pivot** (added 2026-08-07): with both models on the same
      `GPUsPerReplica` the new factor cancels out of the comparison and the fixture is green against
      replica space *and* GPU space — it cannot detect the pivot it exists to pin. Write it **before**
      C6c's code so the change reads red-to-green, and assert the *ordering* (which model
      `sortByRemainingDesc` puts first / which gets the larger share), not a magnitude — fsv's
      magnitude is not a contract. Optionally add the two-analyzer variant as a **separate** `It()`,
      labelled as covering the combine, not the currency.
    - **`computeMean` in GPU space** — the mean of **unweighted** claims (row 3 of §2d.5's table).
      Under the deferred `W2` this site loses its priority factor; at C6c it keeps whatever it has
      today, re-denominated. Assert the arithmetic, not the presence or absence of priority.
    - **A multi-role fixture pinning site (iv)'s clamp** — a two-role model must not have either role
      truncated. ⚠ **Do not build it with prefill and decode sharing the same PRC *or* the same
      `GPUsPerReplica`** (invariant 10, added 2026-08-07): such a fixture cannot distinguish the
      correct per-role conversion from a role-mixing one, so it reads as a guard while guarding
      nothing. Vary both.
    - **Site (v)'s fallback in GPU space** — a hand-built request with `Priority = 0` (constructed
      directly; `ApplyDefaults` would rewrite it to 1.0) asserting fsv comes back in **GPUs**, not
      raw demand. Site (v) is **converted, not deleted**, at C6c — its deletion belongs to the
      deferred `W2` commit (§2 site (v)), so this fixture is expected to be *retired*, not *changed*,
      when that lands.
    - **Finding (b), both halves in one fixture** (per §2d.4 (b)): a model whose only demand has no
      usable PRC must **not** sort ahead of an actionable model, and must **not** be dropped for the
      cycle. Give it a `Priority` such that the primary path yields 0 **and** it therefore traverses
      the *fixed* site-(v) fallback, and assert fsv comes back **0**, not the raw unactionable
      demand. A fixture that only exercises the primary path is green against the unfixed fallback
      and so does not guard (b).
    - **The `floor` boundary — the one fixture here that is deliberately *not* value-neutral** (added
      2026-08-07). §2 site (ii) replaces `ceil(...)` with
      `floor(remaining_GPUs / GPUsPerReplica[vc])`, which moves the granted cap by one replica at
      every mid-replica boundary. Build a fixture whose remaining GPU budget is deliberately **not**
      an integral multiple of `GPUsPerReplica` — e.g. 5 GPUs remaining against `GPUsPerReplica = 2`
      ⇒ `floor` gives **2** where the old `ceil` gave 3 — and assert the 2. **This is a unit test,
      not an `Optimize()` scenario** (level established by measurement at `d9f3b97e`): call the
      closure `fairShareRolePick` returns **directly** and assert the returned `capN`. At
      `Optimize()` level the difference is usually invisible — site (iv)'s `ps` bounds the allocation
      *total* while site (ii) bounds only *per-iteration progress*, and `allocateForModelPaired`
      re-picks each iteration, so an understated cap costs iterations rather than replicas. Measured:
      `map[v1:1 v2:26]` single-role and `map[d1:6 p1:1 p2:26]` P/D came out identical either way; the
      direct closure call was the only probe that discriminated. **Say in the `It()` that this is the
      one place the conversion changes behaviour**, so a reader does not file it as a
      re-denomination check — and see the *Goldens* rule below, because this is also the reason a
      #1513 golden may legitimately move at C6c.
    - **T1.4 rewritten** per §2d.6 — which **splits** it: the unit `combineVotes` assertion (value
      *and* binder index) belongs with the combine at C6a/C6b, and the **end-to-end `Optimize()`
      ordering** assertion stays here, re-denominated into GPUs and driven by **unequal** priority.
      Unequal is required: under the currency fix equal-priority equal-demand models tie, so an
      equal-priority ordering assertion would be asserting a coin flip. The ordering key is
      `priority × claim` both before and after the deferred `W2`, so this half survives `W2`
      unchanged · **goldens re-run**.
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
    - **`U2` — the refresh is never invoked on the scale-down path** (added 2026-08-07, from the
      frozen Type 1; lands here because C6d is the scale-down commit). A **negative** assertion:
      instrument the per-variant sizing refresh with a counting or fake hook and assert **zero**
      invocations across a **multi-variant, multi-iteration** scale-down. Single-variant or
      single-iteration fixtures are green whether or not the property holds. This is the companion to
      invariant 7's not-invoked half — that one pins the one-analyzer case, this one pins the
      scale-down direction.
  - C6e — **`W1`: one fair-share entitlement per *model*, spent jointly across roles** (new commit,
    2026-08-07). This is a **behaviour change**, not a re-denomination, which is why it is not in
    C6c. Two defects to pin, and today's only real protection is the downstream pool check — *the
    pool is enforced, the fair share is not*:
    - **Site (ii)'s per-role budget** — a P/D model must not have each role handed the whole-model
      `target` independently. Assert `Σ_role spend ≤ target` over a full `Optimize()`, with roles
      that would each individually fit but jointly overrun. `fairShareRolePick`'s `_ = roles` goes
      live here as a **sequenced draw against a shared balance**, so the fixture must also pin that
      the draw order is deterministic.
    - **Site (iv)'s per-`(analyzer, role)` clamp** — each pair must not clamp against the *full*
      `target`. With `|analyzers| = 2` and `|roles| = 2` the unfixed code permits four full-budget
      draws.
    - ⚠ **Include a `[sat]`-only P/D fixture as well as `[sat,TA]`.** The frozen Type 1 corrects an
      earlier claim here: the site-(iv) inertness argument for `[sat]`-only holds for
      **single-role only** — a `[sat]`-only *P/D* model already makes two independent full-budget
      draws today, so `W1` is **TA-amplified, not TA-created**, and a sat-only fixture is expected
      to move. That is a deliberate sat-only behaviour change; state it in the commit message and in
      the `It()`.
  - C6f — **`W4`: no conversion factor ⇒ abstain, not budget-exempt** (new commit, 2026-08-07). Also
    a behaviour change, also therefore out of C6c. **The fixture is an equality, not a magnitude:**
    a `[sat,TA]` fixture in which one analyzer has no PRC for the reference variant must produce the
    **same allocation** as the same fixture with that analyzer **absent** from the ballot entirely.
    Anything weaker (asserting a number) pins today's arithmetic rather than the property. Pair it
    with the C6a 3-analyzer non-participant fixture — that one pins the same property inside
    `combineVotes`; this one pins it at the spend sites.
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
  - C11 — **proactive from-zero admission** (new commit, 2026-08-07; mechanism and cap decided in §2f —
    transcribe, do not re-open). **Four assertions, and they are four because each one fails
    independently:**
    1. **Eligibility.** A variant at `ReplicaCount == 0` that no analyzer has ever measured, and that
       the binder omits, becomes eligible: the model that holds today scales, and to **exactly one**
       replica. Red before the sentinel exists.
    2. **The ceiling is on the target, not the iteration.** A **multi-iteration** fixture must still
       end at one replica — a repeated allocation loop must not buy a second by going round again.
       A per-iteration cap is green on a single-iteration fixture, which is exactly the wrong
       implementation passing the wrong test.
    3. **Skip, do not zero-cap.** A role holding the sentinel variant **and** a separately actionable
       variant must still allocate the actionable one. This is the fixture that catches
       `return cap = 0`, which sets `n = 0` → `deltaUtil = 0` → `break` and kills the whole model's
       allocation loop (§2f's ⚠). Assert the *other* variant's replicas, not the sentinel's.
    4. **Ranking.** With `PRC = 1` the cost ordering `Cost/PRC` degenerates to `Cost`, and measured
       PRCs are ≫ 1, so the never-measured variant must rank **behind** every measured option: when a
       measured variant is feasible, assert it is the one chosen. (This is why the rejected
       `PRC = TotalDemand` self-clamping variant would have been wrong — it ranks the unmeasured
       variant *best* exactly when scale-up is needed.)

    **Controls (negative, cheap, and they document §2f's five harmless consumers):** `TotalCapacity`
    stays `0` for the sentinel variant (`0 × 1`), and no scale-down or reclaim path acts on it.
    **Build the fixture so `Reason` and `PerReplicaCapacity` are set as a *set*** — that is the
    property (D-a) leans on for keying the cap on `Reason`; a fixture that sets one without the other
    tests a state the code cannot produce.
- **Goldens are run per commit, not just at the end.** C6a and C6b must leave them byte-identical (uniform
  scores ⇒ old arithmetic). **C6c can now legitimately move a golden** (corrected 2026-08-07): the earlier
  "verified: it does not" analysis in §2d.5 was verified against the *replica-space* pivot, and the frozen
  design's GPU pivot additionally replaces `ceil` with `floor` at the fair-share cap — a one-replica change
  at every mid-replica boundary. So the rule is now conditional, not absolute:
  - **C1–C5, C7, C8, C6a, C6b, C6d, C10 — a moving golden is a bug.** Stop and write a `plan__` handoff
    with the diff.
  - **C6c — a moving golden must be *proved* to be exactly the `floor` boundary** before it is accepted:
    show the remaining-GPU budget, `GPUsPerReplica`, and that `ceil` and `floor` differ by one there.
    Then take it to Dean. A golden that moves for any other reason at C6c, or by more than one replica,
    is a bug.
  - **C6e, C6f, C11 — goldens are *expected* to move** (they are behaviour changes; C6e moves even
    `[sat]`-only P/D). Each move still gets the same treatment: named in the commit message, and the
    reason stated.
  - **In no case is a golden rewritten to accommodate a change** without that written justification.
    The blunter alternative — relaxing the sat-only goldens early to stop them tripping — stays
    **rejected**; their relax/remove is C9's explicit commit, after the multi-vote suite covers the
    sub-case.
- **Multi-vote goldens (C9):** a `[sat, TA]` golden suite that also encodes the `[sat]`-only and
  `[TA]`-only sub-cases (so the sat-only removal is covered), validated against the hand-worked numbers
  in the **frozen** `planning/combined-analyzer-optimizer-design.md` (`Status: FINAL`, `8c2a9b04`) —
  its § anchor and § bugs worked examples. Pin that SHA when transcribing: anything read from an
  earlier revision of that doc is partial state.
- **Full pre-push checklist incl. `-race`** for the fair-share + per-iteration refresh loop
  (`make test` / `gofmt` / `make lint` / `go build`; DCO sign-off; branch verify). See §6 for the
  semantic-pivot grep steps that must run before commit.

⚠️ **FREEZE RECOUNT (2026-08-08) — every count below (32/48/31/17) is superseded; do not re-quote them.**
This passage tracked a moving target through C6a→C9 and was rewritten several times mid-flight (each
revision below records its own "corrected" date). It is now closed: the actual, final numbers are in
§0.0's *"What is genuinely left"* table — **0 PR-2-introduced Go-file violations, 1 PR-2-introduced
markdown violation** (`multi-analyzer-pipeline.md:858`, missed by C9e's own sweep, now authorized for a
follow-up edit), **8 Go-file + 3 markdown lines inherited from base** (`governance-follow-ups.md`'s, not
PR-2's). The commit-*message* half is separately recounted just above (§4 note): **22 of 25 commits**
carry a token. Read the rest of this passage as **historical narration of how the count was tracked
down**, not as a current figure — kept for the reasoning, not the numbers.

**Plans-branch token hygiene (CODER-CONVENTIONS §4a) — two halves, only one of which a commit can fix.**
A full-branch sweep (reviewer, 2026-08-07) found **32 code/doc locations plus a token in all nine commit
messages** — 6 of 9 subject lines (`(N2)`, `(Bug #2)`, `(Bug #1)`, `(Bug #3)`, `(C6a)`, `(C6b)`) and 8 of 9
bodies. For the `Nn` / `Bug #n` / `Cn` families that count is right and is entirely PR-2's. **But "none are
inherited" is only true of those families** (corrected 2026-08-07 after a wider re-measure — see §6's
cross-cutting token-sweep bullet): widening the grep to the full §4a token set (`PR-n`, `Fn`, `Commit n`,
`§n`) gives **48 in-tree lines at `d9f3b97e`, of which 31 are PR-2's and 17 are already present at the
PR-1 base `075a208e`**. The inherited 17 are **out of scope for this PR** — they belong to the pre-existing
`main`-side §4a cleanup tracked in `planning/governance-follow-ups.md`, and 8 of them are the #1513
goldens' own `Commit 2/3/4` scenario labels, which PR-2 must not churn. Any "grep to zero" criterion has to
be scoped to the PR-2 delta or it is unachievable by construction. Notes for whoever actioned it (landed):

- **The 32 code/doc locations ride one sweep commit.** C9 already touches the dev-guide, so it is the
  natural host. Two of the 32 are in the shipped Type 4 `multi-analyzer-pipeline.md` (`:338` `N7`, `:472`
  `N8`) — the most reader-visible surface on the branch. `analyzer_helpers.go:550` cites
  `combined-analyzer-optimizer-design.md`, which is **not in the repo** — a dangling pointer; the
  surrounding prose is self-sufficient, so delete the citation rather than repointing it. Note the
  `Bug #n` form is worse than the `Nn` form: `Nn` is merely opaque, whereas `Bug #2` reads as a tracker
  reference and sends a reader to an unrelated issue #2. Keep `#1513` in the golden's comment — that is a
  real GitHub PR number and is legitimate.
- **⚠️ FREEZE RECOUNT (2026-08-08) — the "nine" figure is stale; the branch is code-complete and the
  count is now final, not a moving target.** Measured directly against the shipped tip `a9afb740`
  (`git log --format='%s'` / `%b` over `075a208e..a9afb740`, all 25 commits): **9** subjects carry a
  plans-branch token; **22 of 25 commits** carry one in the subject *or* body — only `34b18bc5` and
  `757fc6f5` are fully clean. `a9afb740` itself (C9e, the final comment sweep) is the largest single body,
  13 lines, because it is the commit that *removed* most in-tree tokens and had to explain the removal in
  branch-history terms. **The reword count and the token-removal count are two different numbers and this
  plan previously conflated their trajectory** — §4a's *code/doc* token count went **down** over the
  branch's life (C9's sweep is what did it), while the *commit-message* count only ever goes **up**,
  because messages are permanent once committed. The "9 now vs 16 later" framing measured the wrong
  quantity against a moving target; there is no more "later" to project — the batch is 22 either way,
  and rewording is now a fixed one-time cost. **The commit *messages* are not reachable by any later
  commit.** A further commit cannot clean subject or body text that `git log --oneline` and the GitHub
  commit list show permanently; only `rebase -i` + reword ×22 reaches them (as bodies, not all as
  subjects — 13 of the 22 are body-only, a smaller edit than a subject reword). **This is a decision for
  Dean, and it is schedule-bound rather than work-bound:** the branch needs a force-push regardless
  (`origin/ta-anchor-dynamic-refresh@f6485980` is already orphaned by PR-1's reword), so folding the
  reword into that unavoidable force-push costs ~nothing — whereas the identical reword *after* a GitHub
  PR is opened becomes a history rewrite on a live PR branch, which the project's "no rebase of live PR
  branches" rule exists to prevent. So the cheap window closes the instant the PR opens. **"Not worth it"
  is a legitimate answer** and should be recorded as accepted; what should not happen is the
  default-by-omission where the PR gets opened first and the choice is made for us. Requires Dean's
  explicit go-ahead like any force-push.

[↑ TOC](#toc)

---

<a id="5-devguide"></a>
## §5 Dev-guide sections (named, per commit)

> **FREEZE RECORD (2026-08-08) — all four named dev-guides shipped.** Measured at `a9afb740`:
> `multi-analyzer-pipeline.md` **+548/−**, `saturation-scaling-config.md` **+65/−**,
> `throughput-analyzer.md` **+28/−**, `quota-limiter.md` **+15/−** (572 insertions, 84 deletions across the
> four). The two homeless documentation-only items this section adopted both landed in `757fc6f5` — the
> `U5` capacity-gauge limitation and the `W3` priority-idiom prose — and the prose half of C9 landed in
> `2ae440e3`. **One shipped section says the opposite of what this plan specified, deliberately:** the
> from-zero admission subsection is written as *built, not enabled*, because C11 (D-a) is deferred
> (§1.1.1), and it corrects the ranking claim rather than repeating it. Treat the per-commit rows below as
> the specification, and `2ae440e3` as the authority on what the merged prose actually asserts. **Every
> `~L` hint in this section is now up to 25 commits stale — grep the heading text.**

Per CONVENTIONS Type-3: name specific sections, not "update the dev guide." Section titles are as-of
`f6485980`; grep the heading text if line numbers drift. **They have drifted — do not trust the `~L`
hints in this section** (measured 2026-08-07 at `d9f3b97e`): C6a/C6b grew `multi-analyzer-pipeline.md`
by ~100 lines, so every `~L` for that file is low by roughly that much (`## How results combine` 254→258,
`## Optimizer internals and helper composition` 431→534, `### Scale-up path` 438→541, `### Scale-down
path` 463→589, `### Fair-share iteration` 482→608, `### Scale-from-zero and zero-replica variants`
358→457). The **heading text is authoritative**; the numbers are navigation hints that will drift again as
C6c–C10 land. Same caveat as §2's. `coordinator-rebalancing.md` is a **POC demo
doc** (not the combine reference) — combine-arithmetic changes go in `multi-analyzer-pipeline.md` +
`saturation-scaling-config.md`, **plus `quota-limiter.md` for the fsv formula specifically** (added
2026-08-07 — it holds **two** copies; see its block below). The fsv formula appears in **four** places
across two doc files: `multi-analyzer-pipeline.md:622` and `:675`, and `quota-limiter.md:284` and
`:328`. C6c must update all four; a
`grep -rn "Score_i\|score × unmet\|priority × score" docs/developer-guide/` is the cheap check (see §6).

**Two further copies live in code doc comments, and are caught by §6's *currency* grep rather than this
one** (corrected 2026-08-07): the exported `GreedyByScoreOptimizer` **type** doc comment
(`greedy_score_optimizer.go:15-18`, "*ordered by fair-share priority value (priority × Σᵢ(Remainingᵢ ×
Scoreᵢ) across analyzers)*") and `fairShareValue`'s own (`:53-60`). **Six copies total.** The type doc
comment is the easiest of the six to miss: it asserts *both* halves of this pivot (Score in fsv, and
demand units) yet sits outside every function C6c edits, so a coder checking §6's code-grep criterion
literally — "no `Score` in [six named functions]" — passes with it stale. §6's criterion now names it.

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
- `### Fair-share iteration (GreedyByScoreOptimizer only)` (~L482) — the single largest *conceptual*
  edit in this file, because three separate commits land in it. Take them in order:
  - **C6c** (i)/(ii) — `fairShareValue` and the site-(ii)/(iv) budget arithmetic move into **GPU
    space**, *not* replica space (this supersedes the earlier revision of this bullet, which said
    replica space — the frozen design puts the shared currency at GPUs). Give the reader the one
    conversion — a claim in some analyzer's own metric becomes GPUs by dividing by **that analyzer's
    own** per-replica capacity and multiplying by the variant's `GPUsPerReplica` — and then say that
    every number between the ballot and the final clamp is a GPU count: the per-role claim, the
    cross-role sum, the mean, and the target. Two things a reader will otherwise get wrong and both
    are worth one sentence each: the cross-analyzer combine within a role is a **max**, never a sum
    (a role's need is the most demanding analyzer's, not the total of their opinions), while the sum
    **across roles** of one model is legitimate and is the only place a sum appears. Say explicitly
    that `score` does **not** appear in fair share (it is consumed upstream in the combine) and that
    `priority` is the only fair-share weight.
  - **C6c**, `fairShareCap` — the cap is now a whole-replica **`floor`** fill of the GPU budget:
    `floor(remaining_GPUs / GPUsPerReplica)`, then `min` with the real replica headroom. State the
    rule behind it — commit whole replicas while a whole replica's worth of the budget remains, and
    return the remainder to the pool — and state plainly that this is a **behavior change** from
    today's `ceil`: at any mid-replica boundary the optimizer now commits one replica fewer per
    iteration. That is the one sentence in this whole file that a reviewer diffing behavior needs to
    find, so do not bury it in a formula.
  - **C6e** — one fair-share entitlement per **model**, spent **jointly** across its roles. Today's
    doc reads as though each role gets the model's target; after C6e the target is a single balance
    that prefill and decode draw down in sequence, so the sum of what the roles spend is bounded by
    the model's target. Name the consequence for a P/D model concretely (two roles no longer make two
    full-budget draws), and note that the downstream pool check is what has been masking this — the
    pool was enforced, the fair share was not.
  - **C6f** — an analyzer with no usable per-replica capacity for the variant it is being clamped
    against **abstains**: it contributes no claim and spends nothing. Say why the alternative reading
    is wrong: leaving it unclamped is not "harmless", it is an unpriced draw on a shared budget that
    happens to be invisible today because a second, independent filter also excludes it.
  - The participation filter (demand with no usable PRC does not inflate a model's claim) is the same
    property from the claim side; keep that sentence and cross-reference the C6f paragraph rather
    than restating it. *Modify.*
- `### Scale-from-zero and zero-replica variants` (~L358) — **C7** (N8 drop-fallback: binder-unknown ⇒
  PRC=0 abstain) **and C11** (the from-zero admission sentinel). C11 is the substantial half: this
  section currently explains why a variant nobody can size gets no replicas, and C11 makes a narrow
  exception to that, so the section has to hold both rules without the reader concluding they conflict.
  Write it as three claims. (1) A zero-replica variant that no analyzer can price is **admitted** with a
  per-replica capacity of one, tagged by its own reason constant, so that the eligibility gates the
  optimizers already apply — every one of which rejects a non-positive per-replica capacity — stop
  excluding it. (2) That admission is **not** a capacity estimate and must never be spent as one, so its
  target is ceilinged at a single replica; the phrase to give the reader is *unpriced capacity, bounded
  spend*. (3) The ceiling is on the **variant's target**, not on one iteration, and a picker that cannot
  grant the replica **skips the variant** rather than returning a zero cap — say why, because it is the
  non-obvious part: a zero cap collapses the model's utilization delta and breaks out of the whole
  allocation loop, denying the *other* variants too. ⚠️ **The ranking line this row originally asked for
  is FALSE and must not be written** — it claimed that with a per-replica capacity of one the cost-per-unit
  ordering degenerates to raw cost, so an unpriced variant *sorts behind* every priced one as intended
  last-resort behavior. It sorts **first**: a never-measured variant's `Cost` arrives as **0** from the same
  zero-replica lookup that leaves its accelerator empty, so the ratio is `0/1` and it ties with every other
  never-measured peer under an unstable sort. The shipped C9b prose says that instead, names the root as the
  sat-v2 zero-replica `Cost = 0` bug (out of scope), and documents the one-replica ceiling as **the only**
  guard rather than one of two. Also state that claim (1) — the sentinel itself — **does not ship**: C11
  (D-a) is deferred (§1.1.1), so the section is titled as *built, not enabled*. *Modify (substantial) —
  LANDED in `2ae440e3`.*
- `### Data flow per optimize cycle` (~L16) — **C2** (note the anchor is re-derived per allocation
  iteration). *Modify (one line).*
- `## Optimizer internals and helper composition` (~L534) — **C5** (rescale combined demand; N3
  nil-guard), and — *added 2026-08-07, re-pointed out of `saturation-scaling-config.md`* — **C3**
  (`roleAggRemaining` returns a replica-space max, not a raw-capacity one). C3's two hits are the
  composition list's `roleAggRemaining → the binding entry's own raw demand (same combine, second return
  value)` line (~L551) and the collector table row in `## How results combine` (~L284) that names
  `roleAggRemaining` as a `votesFromPickerState` consumer. Both must state the unit. *Modify.*
- `## Observability` (~L684, currently four lines pointing at `cycle-log.md`) — **C9**, a short
  **documented limitation** on the emitted capacity gauges. *Added 2026-08-07 from the frozen design's
  `U5`; the decision there was explicitly **rename nothing, add nothing** — no new series, no new label,
  no renamed field — so this is the entire deliverable for that item and there is no code change to pair
  it with.* The limitation, verified at `d9f3b97e`: the decision's `RequiredCapacity` / `SpareCapacity`
  are copied from **whichever analyzer bound the anchor** (`cost_aware_optimizer.go:307-318` — per-role
  when the binder has an entry for the variant's role, model-level otherwise), while the `unit` label on
  those gauges is stamped unconditionally as the continuous/token unit for every V2 decision
  (`enrichDecisionsWithKvTokenData`, `engine.go:1297`). So on a multi-analyzer model the value's real
  currency is the binder's, the label always says tokens, and a binding change between cycles moves the
  series' meaning **with no label change to signal it**. Say the operational consequence in one sentence
  — treat these two gauges as a scaling-pressure indicator, not a token measurement, on any model with
  more than one enabled analyzer — and say what is *not* affected: the per-analyzer `analyzer-result` log
  line carries each analyzer's own `rc`/`sc` under its own name, so it stays unambiguous and
  `cycle-log.md` needs **no** edit. Do not propose a fix here; the fix is out of PR-2 by decision. *Modify
  (add a short paragraph).*
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
  **Also in this table, one cell beyond what this row originally named — accepted retroactively
  2026-08-07:** the `enabled` field's description still read "*Reserved — placeholder for future combine
  logic*" after C7 made it operative (it is now the `Enabled` half of the VG-up `Enabled && Live` voting
  gate). The coder fixed it inside C6b, in a table it was already rewriting, and said so in the commit
  message — correct call, and the alternative (a separate one-cell commit, or leaving a Type 4 doc calling
  a live gate "reserved") is worse. Recorded here so §5 and the branch agree.
- `#### Shared aggregation helpers` (~L443) — **cross-reference only.** *Re-pointed 2026-08-07 — the
  original assignment here was wrong.* This section documents `internal/engines/aggregation`
  (`SumTotalSupply` / `SumTotalAnticipatedSupply` / `SumTotalDemand` / `AggregateByRole`), which fold **one
  analyzer's own** `VariantCapacities` into that analyzer's own result. Neither `roleAggRemaining` nor
  `bindingIndexForRole` was ever documented here, so C3's and C6a's prose has **no home in this file** —
  their home is `multi-analyzer-pipeline.md` (see below: `## How results combine` for C6a, `## Optimizer
  internals and helper composition` for C3). The right edit here is the one the coder already made in C6a:
  a one-line disambiguation saying these helpers are **not** the cross-analyzer combine and linking to
  `multi-analyzer-pipeline.md#how-results-combine`. Landed at `saturation-scaling-config.md:459`; **verify
  it survives, do not re-do it.** *No further modification.*
- `### V2 Analyzer Parameters` (~L159) — the `priority` row (~L166, currently "*Multiplier for this
  model's scaling urgency in fair-share GPU allocation*") **and** `### Validation Rules` item 6 (~L812,
  "*Priority: Must be ≥ 0*") — **C9**, documentation only. *Added 2026-08-07 from the frozen design's
  `W3`, where the decision was explicitly **no API change**: the gap is documentation, not the schema, so
  this bullet is the whole of that item and there is no code change to pair with it.* What the docs must
  say, and it is counter-intuitive enough that it needs stating rather than implying: writing
  `priority: 0` does **not** deprioritize the model — defaults rewrite exactly `0` to `1.0`, so an
  explicit zero silently becomes *normal* priority, the opposite of the intent. The way to express "last
  in line, take what you need, I will use the leftovers" is a **small positive** value such as
  `0.00001`: it survives defaulting, passes validation, applies as an override, and orders the model
  behind every other while leaving it eligible for whatever the others do not take. Say plainly that this
  idiom is the feature's only spelling, not a workaround, so nobody files it as a bug and nobody
  "fixes" the defaulting. Keep the validation rule's `≥ 0` wording as-is — it is accurate — and add a
  parenthetical there pointing at the field row so the two places agree. *Modify (two small edits, one
  file).*
  **One adjacent cell in the same table, and it should ride the same commit:** the note under the table
  (~L169) still reads "*`scaleUpThreshold` and `scaleDownBoundary` are honored only for saturation on
  this branch; see the `multi-analyzer-threshold` PR for the universal post-step…*". Both halves are now
  wrong for a Type-4 doc on this branch: the universal post-step **is** here
  (`applyUniversalThreshold`, `engine_v2.go:456`, which recalibrates model-level and per-role RC/SC for
  every analyzer), and a shipped reference doc must not point readers at an internal branch or an
  unmerged PR. Replace it with a statement of current behavior and drop the forward reference. Same
  judgment as the `enabled` cell accepted above — a reference doc that describes a live mechanism as
  pending is worse than a one-cell scope stretch in a table the commit is already editing.
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

**`docs/developer-guide/quota-limiter.md`** — **C6c**, **two locations** (added 2026-08-07; this file was
missing from the list above, and it carries **two** copies of the Score-bearing fsv formula — count
corrected 2026-08-07). Both are inside the same `### Fair-share interaction` section (spans ~L278-330),
so this is one edit in one place, not two hunts:
- `### Fair-share interaction`, first bullet (~L283-285) — "the average of the active models' remaining
  fair-share metric (**priority × score × unmet demand** — see the worked-example caveat below)". Drop
  `score` (it is consumed upstream in the combine, not in fsv) and put the unmet demand in **GPU**
  space, matching (i). *Modify.*
- the worked example's closing parenthetical (~L327-329) — "*(The exact per-round means come from the
  fair-share metric — **priority × score × demand** — so treat the numbers here as an illustration of the
  path, not an exact trace.)*" This is the **second formula copy**, not merely a hedge: it names `score`
  *and* calls the currency "demand", so it asserts both halves of what C6c changes. **Rewrite it; do not
  delete it, and do not upgrade it into a claim of exactness.** *(Corrected 2026-08-07 — an earlier
  revision of this bullet said to delete the parenthetical outright on the grounds that after C6c the
  worked example above it (~L309-325, "Wants" 3/4/4, mean ≈ 3.67) would be *literally* what fsv computes.
  That was written against the replica-space pivot. In GPU space it holds only when every variant in the
  example has `GPUsPerReplica = 1` — which the example does not state, so the claim is not available.)*
  The replacement keeps a hedge but drops the stale formula: say that the per-round means are computed
  from the fair-share metric in **GPU** space, that the numbers below read as replica counts only because
  this illustration assumes one GPU per replica, and that the example shows the path rather than an exact
  trace. No numbers in the example change. *Modify.*
  **The `score` token must not survive in either location** — §6's doc-grep is a grep-to-zero criterion,
  and one survivor fails it mid-commit and costs a round-trip. Rewriting the sentence satisfies that;
  softening it in place (keeping the formula and adding words around it) does not.

**Coverage check — every commit has a named home, and three commits deliberately have none.** Read this
table before the first dev-guide edit and again before the last: this section is the only thing standing
between PR-2 and a merged branch whose reference docs describe the previous arithmetic.

| Commit | Dev-guide home(s) |
|---|---|
| C1 | `multi-analyzer-pipeline.md` `## How results combine` |
| C2 | `multi-analyzer-pipeline.md` `### Scale-up path`, `### Data flow per optimize cycle` |
| C3 | `multi-analyzer-pipeline.md` `## Optimizer internals and helper composition` (+ the collector row in `## How results combine`) |
| C4 | `multi-analyzer-pipeline.md` `### Scale-up path` |
| C5 | `multi-analyzer-pipeline.md` `## Optimizer internals and helper composition` |
| C6a | `multi-analyzer-pipeline.md` `## How results combine`; `saturation-scaling-config.md` `#### Shared aggregation helpers` (one-line disambiguation — **already landed, verify only**) |
| C6b | `multi-analyzer-pipeline.md` `## How results combine`; `saturation-scaling-config.md` `### AnalyzerScoreConfig Fields` |
| C6c | `multi-analyzer-pipeline.md` `### Fair-share iteration`, `### Scale-down path`; `quota-limiter.md` `### Fair-share interaction` (both copies) |
| C6d | `multi-analyzer-pipeline.md` `### Scale-down path` |
| C6e | `multi-analyzer-pipeline.md` `### Fair-share iteration` |
| C6f | `multi-analyzer-pipeline.md` `### Fair-share iteration` |
| C7 | `multi-analyzer-pipeline.md` `## How results combine`, `### Scale-down path`, `### Scale-from-zero and zero-replica variants`; `saturation-scaling-config.md` `### How Scale-Up Triggers Work`, `### Saturation as the Identity Carrier` |
| C8 | `multi-analyzer-pipeline.md` `(a)/(b)` gloss lines; `saturation-scaling-config.md` `### Saturation as the Identity Carrier` |
| C10 | `throughput-analyzer.md` — five locations |
| C11 | `multi-analyzer-pipeline.md` `### Scale-from-zero and zero-replica variants` |
| C9 | `multi-analyzer-pipeline.md` `## Observability` (`U5` limitation); `saturation-scaling-config.md` `### V2 Analyzer Parameters` + `### Validation Rules` (`W3`) + the stale post-step note; and the sat-only goldens work, which is code, not docs |

Three things are deliberately absent and a coder should not go looking for them: `coordinator-rebalancing.md`
is a POC demo doc and is **not** a combine reference, so it takes no edit from any commit here;
`cycle-log.md` takes none either (its per-analyzer line names the analyzer, so it does not inherit the
`U5` ambiguity); and there is no user-facing doc change for the deferred priority-does-not-scale work,
because that work is not in PR-2 — `W3`'s prose is written against the arithmetic that ships here, which
is why it says "small positive value" rather than explaining a weighting rule the branch does not yet
have.

[↑ TOC](#toc)

---

<a id="6-grep"></a>
## §6 Semantic-pivot grep steps

> **FREEZE RECORD (2026-08-08) — the greps ran and their fallout landed.** The comment-accuracy repairs
> they surfaced are commits `4fb49ac6`, `eb12089a`, `2ae440e3` and `a9afb740` (the last one titled for
> exactly this: *"make every reference in shipped comments resolvable from `main`"*). Four premises the
> greps exposed as false were rewritten rather than reworded — see §2b's N8 note and §1.1.1's ranking
> correction.
>
> **The §4a token sweep is NOT closed, and it is the freeze's only remaining mechanical work.** Still owed,
> all authorized by this freeze and all in the coder's scope: two production doc comments at
> `analyzer_helpers.go:88` and `:642`, two test tokens at `k_sat_test.go:163` and `rescale_test.go:186`,
> and the `max :=` builtin shadowing at `rescale_test.go:239,:248` (rename `maxRep`). Note `2ae440e3`
> already removed four tokens that the final ledger had counted, so the remaining ledger is **smaller than
> any earlier count in this document** — re-grep rather than trusting a number written here.
>
> ⚠️ **Separately and still unresolved: the commit-message half.** A plans-branch token appears in the
> *messages* of the landed commits, and a further commit cannot fix a message — only `rebase -i` + reword.
> The branch needs a force-push anyway (`origin/…@f6485980` is orphaned), so it is nearly free now and
> becomes a live-PR history rewrite once PR-2 opens. **Re-count against `a9afb740` before acting**: the
> figure this document carried was measured at an earlier tip and every commit since then may add one.
> *"Not worth it" is a legitimate answer; silence is not.* **Dean's call, and the window closes when PR-2
> opens.**

Each behavioral-contract change below carries a grep the coder runs **after** implementing and **before**
committing, updating every stale hit in comments/docstrings/dev-guides (CONVENTIONS + CODER-CONVENTIONS
§ semantic-pivot). If a grep surfaces a hit the plan did not anticipate, write a `plan__` handoff rather
than inferring scope.

- **C1 — `bindingAnchor` return contract** (nil-on-ambiguity → deterministic binder):
  `grep -rn "bindingAnchor" internal/ docs/developer-guide/` — update every doc-comment / caller comment
  that says the getter "returns nil" or "holds" on multiple binders. Confirm all call sites
  (`cost_aware_optimizer.go`, `rescale.go`) still nil-check correctly (the getter can still return nil on
  *no* binder / empty voting set).
- **C3/C4 — unit changes into replica space** (raw mixed-unit capacity → replicas):
  `grep -rn "roleAggRemaining\|PRC_sat\|k·prc" internal/` and re-read every comment describing "max of
  RequiredCapacity" / "decrement by PRC" / "sum across analyzers" — reword to the replica-space /
  per-analyzer / max_i semantics.
  **This bullet was split from a single C3/C4/C6c one, 2026-08-07, and the split is the point.** The
  frozen design puts the *fair-share* currency in **GPUs** and `roleAggRemaining`'s in **replicas**; they
  are analogous sites, not the same site, so a coder re-denominating all three together would convert
  `roleAggRemaining` a second time and land it in the wrong unit. C3 has already landed correctly in
  replica space — **do not revisit it**, and do not read the GPU pivot below as retroactively applying to
  it. The distinguishing question, if a hit is ambiguous: is this number ever compared or summed against
  a *different analyzer's* metric across a *model's* roles (⇒ GPUs), or is it a replica count consumed by
  one role's own bottleneck arithmetic (⇒ replicas)?
- **C6c — the fair-share currency pivot into GPU space:**
  `grep -rn "fairShareValue\|fairShareCap\|computeMean\|sortByRemainingDesc" internal/` — every comment
  on these four must name **GPUs** as the unit afterwards, and each must be explicit about the shape of
  the aggregation it performs: a max across analyzers within a role, a sum across a model's roles, an
  unweighted mean across models, or a dimensionless ordering key that is never spent. A comment that
  names a unit but not the shape is what let today's mixing survive review, so the criterion is both.
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
  `sortVariantsForScaleDown`, **or in `greedy_score_optimizer.go`'s file- and type-level doc comments**
  (criterion extended 2026-08-07). That last clause is load-bearing: the exported
  `GreedyByScoreOptimizer` **type** doc comment (`:15-18`) states the fsv formula as
  "*priority × Σᵢ(Remainingᵢ × Scoreᵢ) across analyzers*" — both halves of this pivot — but is inside
  **none** of the six functions above, so the six-function phrasing on its own lets it through while the
  file's most prominent prose contradicts the code it heads. Any survivor is either a double-count or a
  units desync. **The doc half of this pivot is a separate grep, because the formula is written out in
  four places:** `grep -rn "Score_i\|priority × score\|Priority × Σ" docs/developer-guide/` must return
  **zero** hits — expect `multi-analyzer-pipeline.md:622`, `:675`, and `quota-limiter.md:284` **and
  `:328`** before the fix (§5; `:328` added 2026-08-07 — it is the worked-example parenthetical). A
  surviving copy is a dev-guide that contradicts the code.
  **Disposition differs between the three formula sites and the parenthetical, corrected 2026-08-07:**
  an earlier revision of this bullet said §5 wants `:328` *deleted rather than softened*. §5 now says
  **rewrite it** — do not delete it, and do not upgrade it into a claim of exactness. That instruction was
  written against the replica-space pivot, under which the worked example's numbers happened to be
  *literally* what fsv computes; in GPU space that identity holds only when every variant in the example
  has `GPUsPerReplica = 1`, which the example never states, so the exactness claim is simply not available
  any more. The grep target is unchanged — **zero** hits either way — but "zero hits" is reached by
  rewriting the sentence around the example, not by removing the example. Deleting it would cost the file
  its only concrete illustration to satisfy a grep, which is the wrong trade.
- **C6c — fsv currency is GPUs, not demand and not replicas** *(header and unit corrected 2026-08-07;
  the prior revision of this bullet said "replicas, not demand", which was the earlier pivot and is
  wrong under the frozen design — see the split note on the C3/C4 bullet above for why the two are not
  the same site):* `grep -rn "fairShareValue\|w.remaining\|fsv\|remaining demand\|unmet demand" internal/engines/pipeline/ docs/developer-guide/`
  — every comment or prose line that calls the fair-share metric "demand", "tokens", "capacity",
  "unmet demand" **or "replicas"** is a stale hit once (i) lands; it is a **GPU count**. This is the grep that catches
  site (v)'s stale doc-comment (`greedy_score_optimizer.go:53-60`), the `modelWork.remaining` field
  comment (`:49`, "fair-share priority metric"), and — added 2026-08-07 — the **type** doc comment at
  `:15-18`, whose "*fair-share priority value*" phrasing matches none of this grep's tokens either. So
  `:15-18` is invisible to *both* C6c greps as they were originally worded, and is reached only because
  the code-grep criterion above now names it explicitly. All three should end up naming the unit.
  **Coder-inventoried target list, as-of `d9f3b97e`** (folded in 2026-08-07 — the coder swept these while
  writing C6b and deliberately held them out of it "*so no commit documents behaviour that does not exist
  yet*", which is right; C6c owns them, and they are *accurate today* and *false the instant C6c lands*):
  `cost_aware_optimizer.go:160/163/172` · `rescale.go:380` · `greedy_score_optimizer.go` L18/54/58/73/78 ·
  `multi-analyzer-pipeline.md` L599/605-606/618/622-623/675-677 · `quota-limiter.md` L284/328. Treat this
  as a **checklist, not a substitute for the grep** — it is a snapshot at one tip, and C6c's own edits move
  lines. Note the overlap with the doc-formula grep above (`multi-analyzer-pipeline.md:622`, `:675`,
  `quota-limiter.md:284`, `:328` are the four formula copies); the rest are unit/currency prose.
- **C6c — the round-trip hazard is gone, so there is nothing to grep for** *(this bullet replaces a
  `prcRef`-capture grep, removed 2026-08-07)*. The earlier plan revision carried a check that
  `sortByCostEfficiencyAsc` never appears inside `fairShareRolePick`'s closure, because a reference PRC
  re-derived in-closure would read a value the per-iteration refresh had already rewritten. **The frozen
  design removes the mechanism that hazard needed:** the conversion multiplies by `GPUsPerReplica`, which
  is immutable variant topology and cannot be rewritten by a refresh, so there is no captured-vs-derived
  distinction left to police and no per-role `prcRef` parameter to thread. Recorded rather than silently
  dropped because the deleted grep looks like a coverage regression if you diff plan revisions — it is
  not; the property became unfalsifiable by construction, which is strictly better than checking it.
  **One check does survive the deletion, and it survives on its own terms:**
  `grep -n "fairShareRolePick(" internal/engines/pipeline/*_test.go` — the cap fixtures (§4, including the
  `floor`-boundary one) must appear here, i.e. call the returned closure **directly** and assert `capN`.
  Measured at `d9f3b97e`, an `Optimize()`-level fixture on §2d.5's numbers is green with *and* without the
  intended behavior, because site (ii)'s cap bounds only per-iteration progress while site (iv)'s `ps`
  bounds the allocation total and `allocateForModelPaired` re-picks every iteration. A test that cannot go
  red is worse than no test — it reads as coverage.
- **C6c — no `ceil` survives on the fair-share fill path** (added 2026-08-07, and this is the grep that
  pins the one behavior change inside C6c):
  `grep -rn "ceil(" internal/engines/pipeline/` — classify every hit. `fairShareCap`'s must be **gone**,
  replaced by the whole-replica `floor` fill. The others are legitimate and must **stay**: converting a
  demand into a replica count needs `ceil` (partial replicas cannot serve), and C5's
  `max_i ceil(demand_i/PRC_i)` is exactly that. The rule that separates them in one sentence — **round up
  when asking how many replicas a demand needs, round down when asking how many replicas a budget can
  afford** — belongs in the commit message, because the diff alone makes the change look like an
  inconsistency.
- **C6e — one budget per model, drawn in sequence** (added 2026-08-07):
  `grep -rn "for .*range roles\|_ = roles\|rolesFor\|RoleCapacities\[" internal/engines/pipeline/` — read
  every loop over a model's roles and answer one question per hit: does this loop give each role a fresh
  copy of a model-level budget? Any hit that does is the `W1` defect, whether or not it is one of the two
  sites §2 names — the two named sites are what a review found, not a proof there are only two. Also
  confirm `_ = roles` no longer appears in `fairShareRolePick`; while it does, the signature is advertising
  a parameter the body ignores, which is how the defect stayed invisible.
- **C6f — abstain is not the same as exempt** (added 2026-08-07):
  `grep -rn "prc <= 0\|prc == 0\|PerReplicaCapacity <= 0\|PerReplicaCapacity == 0" internal/` — there are
  **six** such gates in the optimizers (`cost_aware_optimizer.go:95`, `:125`, `:239`;
  `greedy_score_optimizer.go:411`; `rescale.go:443`, `:573`, as-of `d9f3b97e`) and after C6f every comment
  on them must say the analyzer **abstains** — contributes no claim and spends nothing — rather than that
  it "is skipped" or "is excluded". The wording matters beyond style: "skipped" is what made the unpriced
  draw read as harmless, since two independent filters happened to agree. C11 then makes one of these
  gates deliberately passable via the admission sentinel, so whatever prose lands here must still be true
  after C11 — write it as a rule about *pricing*, not about zero.
- **C6c/C6e — comments that still say "replicas" where the number is now GPUs** (added 2026-08-07):
  `grep -rni "replica" internal/engines/pipeline/analyzer_helpers.go internal/engines/pipeline/greedy_score_optimizer.go`
  — a wide grep with many legitimate hits (replica counts are real and everywhere). The stale ones are
  specifically comments on the fair-share path that describe the *budget*, the *mean*, or the *target* as
  a replica count. This grep exists because the pivot changes what a number means without changing its
  type: nothing fails to compile, no test goes red, and the only artifact left describing the old unit is
  prose. It is the highest-yield grep in this section and the easiest to skip.
- **C11 — the sentinel's tag and its cap are never separated** (added 2026-08-07):
  `grep -rn "<the new Reason constant>" internal/` — spelling is the coder's (§2f (D-a)), so grep for
  whatever constant lands. Every hit must be in one of exactly **two** kinds of place: the **write** site
  that sets `PerReplicaCapacity` and `Reason` together, or a **read** site that applies the one-replica
  ceiling. A hit that reads the tag for any other purpose — logging a decision, choosing a message,
  branching on eligibility — is a new coupling to the sentinel that the design did not sanction, and it is
  how a tag starts drifting away from the value it is supposed to describe. The property that makes
  keying on `Reason` safe at all is that the tag and the capacity are copied **as a set** at both write
  sites; a third reader is not unsafe by itself, but it is the first step to someone copying one without
  the other.
  **Second grep, and this one has a hard answer:** `grep -rn "PerReplicaCapacity = 1\|prc = 1\|= 1 //" internal/engines/pipeline/`
  — the literal `1` must appear **once**, at the admission branch, and must be tagged on the same
  statement group. An untagged `PRC = 1` anywhere on the anchor path is an unpriced variant that no cap
  will ever find, because the cap keys on the tag: it would be admitted and then allowed to draw like a
  measured variant. That is the one C11 failure mode that is silent — it passes every gate, moves no
  golden, and shows up only as a model over-allocating onto hardware nobody has measured.
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
- **C8 — notation strip:** `grep -rnE "\((a|b)\)" internal/ docs/developer-guide/` — zero hits **that denote
  the (a)/(b) sizing notation** after C8 (the letters are gone; the words remain). *Criterion corrected
  2026-08-07:* a literal "zero hits" is unachievable — the pattern also matches `math.Abs(a)`,
  `string(b)`, `cmp.Compare(b.Priority, a.Priority)` and ordinary English "(a)… (b)…" enumerations in
  unrelated files. **17 hits remain at `d9f3b97e` and all 17 are false positives** (each read), so C8 did
  its real job; the reword exists so the next reader does not re-chase them and so a genuine hit is not
  lost in the noise.
- **Cross-cutting — §4a plans-branch token sweep (run before the final push, not per commit)** (added
  2026-08-07):
  `grep -rnE '\bN[0-9]\b|\bBug #[0-9]|\bPR-[0-9]\b|\bC[0-9]+[a-d]?\b|\bF[0-9]+\b|§[0-9]|\bCommit [0-9]' internal/ docs/developer-guide/`
  — **the criterion is zero *PR-2-introduced* hits, not zero hits.** Measured at `d9f3b97e`: **48 in-tree
  lines, 31 PR-2's, 17 inherited from the PR-1 base `075a208e`.** Per-file PR-2 delta, which is the actual
  target list: `analyzer_helpers.go` 8 · `analyzer_helpers_test.go` 7 · `rescale.go` 4 ·
  `optimizer_liveness_test.go` 3 · `optimizer_dynamic_refresh_test.go` 3 ·
  `optimizer_combine_characterization_test.go` 2 · `multi-analyzer-pipeline.md` 2 ·
  `optimizer_interfaces.go` 1 · `rescale_test.go` 1. By class: **13** shipped non-test code, **16** tests,
  **2** dev-guide. Confirm provenance per file with
  `git show 075a208e:<path> | grep -cE '<same regex>'` before editing — the **17 inherited** hits
  (`optimizer_characterization_test.go` 8 = the #1513 goldens' own `Commit 2/3/4` labels ·
  `analyzer_test.go` 4 · `throughput-analyzer.md` 2 · `constants.go` 1 · `throughput_analyzer.go` 1 ·
  `greedy_score_optimizer_test.go` 1) are **out of scope**: they belong to the `main`-side cleanup in
  `planning/governance-follow-ups.md`, and churning the goldens' labels would dirty a diff PR-2 is
  supposed to leave alone. Replace each PR-2 hit with the prose the token stands for — §4a's own
  example: "abstains rather than vetoing (N7)" → "abstains rather than vetoing — a coarser voter has no
  basis to veto a role it never sized". **Why this bullet exists:** §6 previously had exactly one
  §4a-flavoured grep (C8's), so the `Nn` / `Bug #n` / `PR-n` families were outside every stated criterion
  and a coder following the plan literally had no scope to infer one — and the C6d bullet actively points
  *at* three `N7` hits (`analyzer_helpers.go:671`, `:682`, `:694`) asking that their prose stay accurate
  without saying to strip the token. Two of the 31 are in the shipped Type 4 `multi-analyzer-pipeline.md`
  (`:338` `N7`, `:472` `N8`) — the most reader-visible surface on the branch, and Type 4 must be
  self-sufficient for a reviewer reading only the diff. Real GitHub numbers (`#1228`, `#1513`) are
  legitimate and stay. Commit messages are **not** reachable by this or any later commit — see §4.
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
saturation's configured `kvCacheThreshold` instead of the hard-coded 0.85 watermark mirror**, **§2f
proactive from-zero admission (`FZ-admission`, both the sentinel and its one-replica cap)**, §3
per-iteration refresh, N3 nil-guard hardening (rides C5), §4 goldens relax.

**Plus three design answers that became PR-2 work when the Type 1 froze** (2026-08-07 — see
[§7.1](#7-1-what)): `W1` one fair-share entitlement per **model** spent jointly across roles (→ C6e), `W4`
an analyzer that cannot price a variant **abstains** rather than being budget-exempt (→ C6f), and `W5` the
per-site unit table putting the fair-share path in **GPU space** with `fairShareCap` as a whole-replica
`floor` fill (→ C6c). Two more are answered without code: `W3` and `U5` are **documentation only** and ride
C9. The scope of this PR grew when the design froze; it did not shrink.

**Superseded framing, recorded so a stale read is recognisable (2026-08-07).** An earlier revision of this
section said the `W1`–`W5` questions were *"not in PR-2"*, that *"C6c must not decide them"*, and that they
were **open** rather than settled. All three statements were true when written and are now false: the Type
1's decision queue is **empty**, and the answers are what C6c/C6e/C6f implement. If you are reading a copy
of this plan that still frames the W items as open, it predates the freeze — the frozen Type 1 governs.

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
for a follow-up PR on the theory that it would move the #1513 goldens, and it stays here regardless.
**The reason has changed, corrected 2026-08-07:** this paragraph used to say a moving golden was *"verified
false"*. That verification was done against the replica-space pivot and does **not** survive
`ceil → floor` — a `[sat]`-only golden **may** legitimately move at C6c, at any model whose fair share
lands strictly between two whole replicas (§2 #5 (ii), §4). What keeps the work here is not that goldens
cannot move; it is that a move is now *diagnosable*: C6c is the only commit in the stack whose golden delta
must be **proved** to be exactly the `floor` boundary, and the behavior changes that would muddy that proof
were deliberately moved into C6e/C6f/C11. Nothing new left PR-2's scope as a result of §2d.

**NOT in PR-2 — separable small PRs (PR-1 §12), each independent:**
- **QM fold (F10)** — fold the queueing-model into the V2 multi-analyzer engine (PR-1 refuses QM with an
  explicit error; design § findings `N6`). Its own PR.
- **§2.4 partial scale-from-zero picker** — ⚠️ **the 2026-08-07 "RETIRED as a separate scope item" ruling
  is REVERSED by the freeze; it is DEFERRED again.** The retirement rested on two claims that both turned
  out false. It argued that §2f's admission sentinel plus its one-replica cap makes the choice exist, so
  the existing cost/fair-share ranking *is* the picker — *"a sentinel variant prices at raw cost and sorts
  behind every measured option."* But **the sentinel does not ship** (C11 (D-a) deferred as a proven
  regression, §1.1.1), so a never-measured variant is still invisible to the optimizer and there is still
  nothing for a picker to choose between; and **the ranking claim is inverted** — a sentinel variant sorts
  **first**, not last, because its `Cost` is 0. Neither half survives. Track it as deferred work alongside
  the (D-a) sentinel it depends on: the picker cannot be revisited before the sentinel question (an `N8`
  question, the Type-1 owner's) is answered. PR-1 §12's listing of it as deferred is therefore **correct
  as written** and needs no reconciliation.
- **`AnalyzerName` validation** — separate validation PR.
- **sat `Cost=0`-for-zero-replica mis-ranking (`N5`/`AD7`, non-fallback half)** — reaches all three
  configs; a **separate saturation bug**, not fixed by N8 (N8 only removes the *fallback* half).
  **Decided (Dean, via Addendum 1): fix.** Root cause is **sourcing, not arithmetic** — cost is a spec
  property (`VariantCost` is set on the spec, the same precedent `AcceleratorName` follows) but the
  pipeline reads it from `ReplicaMetrics.Cost` (`saturation_analyzer.go:59`), a live-pod-derived type a
  cold variant has no entry in. **Sizing/placement is the planner's call, and the recommendation is: a
  follow-up, not a PR-2 growth** — `VariantReplicaState` (`:386-409`) is spec/deployment-derived and
  already exists for a zero-replica variant, but carries neither `AcceleratorName` nor `Cost`; adding
  that field pair there fixes this bug, the `AD6` retention-hazard identity question, and the
  `fairShareRolePick`-unreachable-via-`available[AcceleratorName]` gap (§1.1.1's fillRole note above) in
  one change — one root cause, three symptoms, so the follow-up should be scoped as *the field pair*,
  not as three separate patches. **File/fix as that follow-up, not inside this PR.** ⚠️ **Reverses
  CURRENT.md, which lists `N5` under this PR's *out* set — needs a `sync__` line recording this
  disposition change**, not a silent carry-forward.

**NOT in PR-2 — genuinely unanswered, not decided-and-deferred: the claim-pricing distortion
(`537b0153`).** `referenceVariantForRole` prices a role's claim through one variant's `GPUsPerReplica`
while `fairShareRolePick` spends the entitlement through whichever candidate it lands on, using *that*
variant's `GPUsPerReplica` — reference selection filters only on `PerReplicaCapacity > 0`, never checks
headroom, so it can price a whole role through a variant the picker cannot buy, inflating that model's
claim (and ranking) by the ratio between the two `GPUsPerReplica` values. **Cross-model, not intra-model**
— the pool is honoured in both directions (it is a pure redistribution between contending models), so no
pool check and no single-model golden can see it. The coder deliberately left this **undecided** rather
than picking a fix: a `PIt` pending spec (`537b0153`, +88, asserting the honest even split) is pinned as a
dormant characterization, verified red when temporarily enabled, isolated in its own revertable commit.
**Disposition is the Type-1 owner's** (three shapes on the table, none chosen: accept-and-document /
headroom-partial / `min(gpusPR / PRC)` over feasible candidates — the last changes the **ranking key**
for any unequal-PRC role and no golden covers that either) — route by handoff, not decided here. If the
ruling is "current pricing is correct as designed," the pending spec is deleted; otherwise it goes green
when the fix lands. The dev-guide sentence naming this (`multi-analyzer-pipeline.md`, "Fair-share
iteration") must say *"open with the analyzer-design owner"* or equivalent — not "Type-1 owner" verbatim,
which is the one §4a residual this freeze already authorizes fixing (§0.0 table).

**NOT in PR-2 — deferred design work, decided-and-deferred rather than unanswered (added 2026-08-07):**
- **`W2` with `U4` — priority orders but never scales an entitlement.** Answered in the frozen Type 1 and
  then **deferred as a future TODO**, on Dean's own criticality test (*"is this critical for TA
  integration. If not then it becomes a future TODO"*): the coupling is **TA-neutral**, so nothing about
  multi-analyzer integration depends on breaking it. **This is settled, not open** — do not re-open it in
  the Type 3, do not route it to Dean as a question, and do not let it hold the rest of the work. Two
  consequences bind PR-2 and both are already carried: site (v) is **converted, not deleted** (§2 #5),
  and `W3`'s dev-guide prose is written against the arithmetic that **ships today**, not against the
  deferred rule (§5).
- **`U5`'s new metric series** — emitting the anchor's RC/SC with a unit that follows the binder would need
  either a relabel or a new series. Decided: **rename nothing, add nothing now.** What PR-2 ships instead
  is the *documented limitation* (C9, §5 `## Observability`), which is the whole deliverable for that item
  — there is no paired code change to look for.
- **C11 (D-a) — the from-zero admission sentinel.** DEFERRED as a proven regression; full classification and
  the reason an anchor-only sentinel cannot work are in §1.1.1. The open question is **whether the sentinel
  may enter the voting set**, which is an `N8` question and therefore the **Type-1 owner's** — raised by
  handoff, not answerable here. The **§2.4 partial from-zero picker** depends on it and is deferred with it
  (see the separable-PRs list above, where the 2026-08-07 retirement is reversed).

**NOT in PR-2 unless Dean places it there — `AD8`, the P/D prefill collapse. TWO items, never one:**

Addendum 1 `AD8` is **DECIDED: repair the pricing** (Dean, 2026-08-08) — option (b), three sites; option
(a) a liveness-aware refusal **rejected** (*"PD not SAT — DONT"*); option (c) documentation is additive;
`MinReplicas` is not a fourth option. §0.0 carries the disposition, the severity history, and the
withdrawn scoped exception. **Placement is Dean's open call** (Rev-6 ask 2: *"do not schedule it into PR-2
on the strength of the old severity, and do not retire it either. Ask him."*).

The one thing this plan fixes rather than leaves to judgment: **the two regimes are tracked as two
items.** They share a cause but not a code path, so a fix verified on one says **nothing** about the
other. Dispatch is a global OR over roles (`analyzer_helpers.go:709-718`) with mutually exclusive arms
(`cost_aware_optimizer.go:62-67`), which is why one role captures the model.

- **`AD8`-i — the freeze.** Decode `RC > 0` ⇒ `anyRoleNeedsScaleUp` ⇒ the scale-**up** arm ⇒ prefill
  **freezes at its current count, including 0**. **No floor of any kind reaches this regime** — in
  particular `MinReplicas` can preserve a scale-up but cannot originate one
  (`greedy_saturation_algorithm.go:52-63`, `:80-83`). Verification is a scale-up fixture; the scale-down
  fixtures cannot see it.
- **`AD8`-ii — the drain.** Decode `RC == 0` with spare ⇒ the scale-**down** arm ⇒ prefill **drains to
  1**. Two routes reach it: (A) `scaleDownRoleIterated → scaleDownVariantSet` (both role gates apply) and
  (B) `reclaimRole → scaleDownVariantSet` (neither gate; needs rescale plus a contended group).
  Verification is a scale-down fixture, and route (B) needs the rescale path specifically.
  **Precondition to travel with the `#1237` positional-rule tidy-up wherever that is tracked:** *if the
  positional rule is ever tidied, **floor every variant in the role first**.* Tidy-first re-opens this at
  every height on **both** scale-down routes (measured: prefill → 0). It governs **regime (ii) only** —
  everything it protects lives inside `scaleDownVariantSet`, which regime (i) never enters.

<a id="7-1-what"></a>
### §7.1 Design-level "what" questions surfaced by the currency fix (W1–W5) — all answered

**Status changed 2026-08-07: these are answered and frozen, not open.** The five questions were raised by
C6c's discussion, moved to the Type 1 because a Type-3 task plan is the wrong instrument for a *"what do we
want"* question, and then **decided there** — the design doc's decision queue is now empty. Their full
statements and reasoning live in
[`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) **§ open** and its
`§ findings` rows, at frozen commit **`8c2a9b04`**. Read them there. They are still deliberately **not**
restated in full here — a task plan that carries its own copy of a design decision becomes a second
authority for it, and the answers below are pointers plus the landing commit, not the argument.

What each one is and where it lands, so this plan stays navigable without the design doc open:

| ID | Question | Answer (frozen Type 1) | Lands in |
|---|---|---|---|
| `W1` | Is the fair-share budget one scalar per *model*, or one per *(model, role)*? | **One per model, spent jointly across roles.** Both current spend sites are defects, not merely mis-united: site (ii) hands every role the whole-model target and site (iv) lets each `(analyzer, role)` clamp against the full target. **Behavior change.** | **C6e** |
| `W2` | Should the budget be priority-scaled where it is *spent*, or only where models are *ordered*? | **Ordered only — priority must never scale an entitlement.** Answered, then **deferred** as a future TODO (TA-neutral, so not critical for TA integration). Consequence carried here: site (v) is **converted, not deleted**. | *deferred, not PR-2* |
| `W3` | What does `priority: 0` mean? | **Last in line, still eligible, takes the leftovers, claim unweighted.** Reachable only as a small positive value (`0.00001`) because `ApplyDefaults` rewrites exactly `0` to `1.0` — and that is **accepted, not a defect**. **Documentation only, no API change.** | **C9** (docs) |
| `W4` | Is a voter that cannot size the reference variant exempt from the budget? | **No — it abstains.** No conversion factor ⇒ no claim *and* no spend. "Exempt" and "abstains" differ exactly where it matters: an exempt voter draws on a budget it never contributed to. **Behavior change.** | **C6f** |
| `W5` | Is the cross-model mean a meaningful reference, and in what unit (replicas vs GPUs)? | **GPU space**, fixed per site by a nine-row unit table rather than one global declaration; `fairShareCap` becomes a whole-replica **`floor` fill**. Rows 1–6 are all GPUs, with one conversion in at row 0 and one out at row 8. | **C6c** |

**Two things this table replaces, called out because a stale read of either is actively harmful:**

1. **The old "What C6c does about it" column** said C6c *preserves* `W1`'s scalar, *preserves* `W2`'s
   coupling, takes *no position* on `W3`, leaves `W4` *unclamped*, and fixes `W5`'s unit to **replicas**.
   Every one of those was the correct status-quo answer before the freeze and is wrong now — the unit is
   GPUs, and `W1`/`W4` are implemented rather than preserved.
2. **The old rule that "every W item is status-quo-preserving"** is deleted. It is replaced by a narrower
   one that survives the freeze: **C6c alone is status-quo-preserving** — and even C6c has the one flagged
   `ceil → floor` exception — *because the behavior changes were moved out of it* into C6e and C6f and one
   was deferred entirely. The separation is the point: it is what lets a moving golden be diagnosed rather
   than argued about (§1.1, §4).

**What a coder may still not do.** The prohibition survives, with its reason inverted. Before the freeze a
coder must not resolve a W item because it was undecided; now a coder must not *re-decide* one because it is
decided — including by "improving" an answer while implementing it. If a site cannot be built as specified,
that is a `plan__` handoff, not a judgment call, and post-freeze changes to the Type 1 go through Dean.

---

**Pre-existing, out of anchor scope entirely:**
- **N9** — the reactive full-scale-from-zero engine (`scalefromzero/engine.go`) is budget-blind and wakes
  all variants (not cheapest). Pre-existing on `main`; the anchor never touches it. Relevant only to any
  cost/budget layer built on top of from-zero. **Still out of scope after C11, and the boundary is worth
  stating** (added 2026-08-07): C11 makes the *proactive* path able to admit a never-measured variant under
  a one-replica cap, so the two paths now coexist and can look like duplicates of each other. They are not
  — N9 is the reactive cold-start that fires when traffic arrives at a zero-replica model, and its
  coarseness is its own bug. Fixing C11 does not fix it, and a reader should not treat §2f as having
  narrowed N9's scope.
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
