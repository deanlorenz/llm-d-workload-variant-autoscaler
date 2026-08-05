# ta-anchor coding-plan stack — review + redesign spec

**Status:** DRAFT
**Reviewer role:** design-review agent
**Date:** 2026-08-03 (Part 1 — review of the old plan); 2026-08-04 (Part 2 — redesign spec)
**Base code:** `main @ 9906dac5` (the plans' stated base — confirmed live).

## Document structure — read this first

This document has two clearly separated halves, per Dean's direction (2026-08-04) to *"separate the
review of the old plan from the recommended course of change"* and to make the discussion *"a spec
for the planner to create a new Type-3 coding plan to fix TA issues — explicit and clear."*

- **[Part 1 — Review of the superseded plan](#part-1--review-of-the-superseded-ta-anchor-refactor-planmd).**
  The original Type-6 review of `ta-anchor-refactor-plan.md` as drafted: verdict, correctness
  findings (F1–F12, C1), coder-executability findings (E1–E13), and the confirmed-correct list.
  **The plan reviewed here is being abandoned** — the anchor mechanism was redesigned, so the
  planner starts a *fresh* Type-3 plan (likely on a fresh branch) rather than patching the old one.
  Part 1 is retained for traceability and because several findings define what the new plan must
  **not** reintroduce.
- **[Part 2 — Recommended course of change: the spec for the new Type-3 plan](#part-2--recommended-course-of-change-spec-for-the-new-type-3-plan).**
  The corrected mechanism and every decision from the 2026-08-04 discussion, consolidated into an
  explicit, self-contained specification. **This is the authoritative input** the planner authors
  the new coding plan against; Part 1's per-finding "Fix (planner)" directions are **not** — they
  describe how to patch the abandoned plan. Where a Part-1 finding still matters, §2.2 maps it
  forward. Upon completion of the new plan doc, it gets its own review.

## Scope (Part 1 — the old plan)

Type-6 review of the concrete Type-3 coding plans for the combined-analyzer-optimizer
"binding anchor" work, plus their dev-guide-update (§8) and convention compliance:

- [`planning/ta-anchor-refactor-plan.md`](ta-anchor-refactor-plan.md) — **PR-1** (primary; the (a)/(b)/RC-SC split + TA-only enablement, ZERO combine arithmetic).
- [`planning/ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) — **PR-2 STUB** (deferred multi-vote refresh + bug fixes; cross-checked for consistency only).
- [`planning/ta-anchor-goldens-plan.md`](ta-anchor-goldens-plan.md) / [`-goldens-review.md`](ta-anchor-goldens-review.md) — the invariant-#7 ship gate (already **FINAL**; cross-checked, not re-reviewed).

**Method.** 7-agent adversarial file:line verification of every code-reference, dev-guide
specificity claim, and cross-plan-consistency claim against `Main/` at `9906dac5`, plus direct
re-confirmation of the two MAJOR findings against live code and plan text.

---

# Part 1 — Review of the superseded `ta-anchor-refactor-plan.md`

> **This part reviews a plan that Part 2 supersedes.** The findings still accurately describe gaps in
> the old plan draft *as written*; they are retained (a) for traceability, and (b) because §2.2
> ("How this redesign resolves the Part-1 findings") maps each to *resolved-by-redesign*,
> *still-applies-to-the-new-plan*, or *now-a-separate-PR*. **Do not implement against Part 1's
> per-finding "Fix (planner)" directions** — they patch the abandoned plan. Use Part 2.

## Verdict (of the old plan)

**The plan stack is highly accurate and convention-compliant.** Every domain-type enumeration,
both producer-sourcing claims, and the great majority of `file:line` read-site citations match the
code exactly — including subtle def-vs-usage line splits (e.g. `fairShareValue:61` def vs `:73`
sum-site; `sortVariantsForScaleDown:161` def vs `:168` tie-break) that a shallower review would
have wrongly flagged as stale. The (a)/(b)/RC-SC field partition is grounded in the actual
read-sites; §12 leaves no removal unclassified; the invariant-#7 decision-set-identity model is
consistent across PR-1, the goldens plan, and the goldens review; the rebase target is correctly
the moving `main` tip, not a pinned SHA.

**Two MAJOR issues block a clean PR-1 hand-off**, both in the blast radius of the
`saturationEntry(req.AnalyzerResults)` → `bindingAnchor(req)` (returns `req.Anchor`) rename:

- **F1** — a live optimizer caller the plan never inventories would silently lose *all* its
  scaling decisions after the rename.
- **F2** — an internal §9-vs-§5 contradiction that could lead a coder to preserve the exact
  special-case PR-1 exists to delete.

The remaining findings are minor doc/reference nits (F3–F12) and one borderline convention item
(C1). None of F3–C1 blocks implementation; most are backstopped by the plan's own §9 grep or
fallback clauses.

**A second lens — coder-executability (E-series, below) — is materially more blocking.** F1–C1
verify the plan's *facts*; the E-series asks whether a coder can *build* §5–§7 at the sites named.
It surfaces **five additional MAJOR blockers**: §5-1b's anchor-build site is unrealizable (E1); the
shared test builder `withSatEntry` never sets `Anchor`, so Commit 2 reddens all optimizer tests +
the #1513 goldens (E2); `copy(baseResult)` is invalid Go and the shallow alternative aliases the
stored result (E3); §6-2c reads fields off the wrong struct and drops the guard preventing an
empty-ballot panic (E4); and the new tests can't be built at the site §5/§10 name (E5). See
**§ Coder-executability findings (E-series)**.

---

## Findings

### F1 (MAJOR, missing-site) — the queueing-model optimize path is omitted; after the rename it carries a nil Anchor and every QM model is silently dropped

**Where:** [`internal/engines/saturation/engine_queueing_model.go:77-94`](../../Main/internal/engines/saturation/engine_queueing_model.go) (request builder) + `:103` (optimizer call); nil-guard at [`internal/engines/pipeline/cost_aware_optimizer.go:48-51`](../../Main/internal/engines/pipeline/cost_aware_optimizer.go). Plan gap: §5 (Commit 1 engine), §6 (Commit 2 optimizer), §9 (grep survivors), §10 (read-site inventory).

**What.** `optimizeQueueingModel` — selected at `engine.go:554` when a `wva-queueing-model-config`
ConfigMap is present — builds each `pipeline.ModelScalingRequest` with a single ballot entry
`{Name: domain.SaturationAnalyzerName, Result: qmResult, Score: 1.0, …}` and **sets no `Anchor`
field** (`engine_queueing_model.go:77-94`), then calls the *same* optimizer via
`e.optimizer.Optimize(ctx, requests, nil)` (`:103`).

PR-1 Commit 2 replaces the by-name scan `saturationEntry(req.AnalyzerResults)` with
`bindingAnchor(req)` returning `req.Anchor` (§6; §10 L467 "satEntry guard — becomes req.Anchor").
The optimizer's very first statement per request is the nil-guard
`if satEntry == nil { continue }` (`cost_aware_optimizer.go:48-51`). For QM requests `req.Anchor`
is nil → **the optimizer skips every queueing-model model → silent loss of all queueing-model
scaling decisions.** No compile error, no test failure in the pipeline package (QM lives in the
`saturation` package and has its own tests), no red golden — the behavior just vanishes.

**Why it matters.** This is the classic "commit message claims X, diff silently drops X" failure
mode the conventions warn about, except here it's the *plan* that's silent: the engine-side step
that must populate `req.Anchor` is enumerated only for the `engine_v2.go` path (§5-1a/1b/1c), and
the read-site inventory (§10) and the survivor grep (§9) both stop at `engine_v2.go` + `engine.go`.
The QM builder is a second, independent `ModelScalingRequest` producer that feeds the identical
optimizer and is invisible to the plan.

**Fix (planner, in PR-1).** The plan must make the QM path a conscious decision, not an omission.
Either:
1. **Populate `req.Anchor` in the QM builder** — set `Anchor: &result` (or a copy) on the
   `ModelScalingRequest` at `engine_queueing_model.go:77`, mirroring the `engine_v2.go` anchor
   population. This is the direct analogue and keeps the by-name scan fully retired. Add it to §5
   (or a new "Commit 1b: queueing-model request builder") and to the §10 read-site inventory; and
2. add a **backstop test** in `internal/engines/saturation/` asserting `optimizeQueueingModel`
   still produces decisions after the anchor migration (so silent loss becomes a red test).

Alternatively, if the planner prefers `bindingAnchor(req)` to *fall back* to the by-name scan when
`req.Anchor == nil`, that keeps QM working but leaves the by-name special-case alive — which
partly defeats PR-1's stated deprecation goal — so it should be an explicit, documented choice in
§6, not an accident. Either way §9's survivor list must add `engine_queueing_model.go:81` (and note
`domain/saturation_analyzer.go:33-34`, the const def, is trivially fine).

---

### F2 (MAJOR, internal contradiction) — §9 lists `engine_v2.go:141,143` as legitimate `SaturationAnalyzerName` survivors, but §5-1b removes the `:140-148` block that contains them

**Where:** plan §9 L438-440 vs §5-1b L254-255.

**What.** §9 (L439) states `SaturationAnalyzerName` "legitimately survives" at
`engine_v2.go:118,141,143`. But §5-1b (L254-255) explicitly orders: "remove the unconditional
sat-v2-first entry (`:140-148`) *and* the `entry.name == domain.SaturationAnalyzerName { continue }`
skip (`:150-152`)." Lines `:141` (`Name: domain.SaturationAnalyzerName,`) and `:143`
(`Score: scoreForAnalyzer(domain.SaturationAnalyzerName, config)`) are **inside** the `:140-148`
literal being deleted. After the refactor, sat flows through the append loop and is named via
`entry.name` / `scoreForAnalyzer(entry.name, config)` (~`:162-170`), not the deleted literals.

**Only `engine_v2.go:118`** (`resolveThresholds(domain.SaturationAnalyzerName, config)` —
recalibrates `baseResult` into the anchor) genuinely survives on the engine side.

**Why it matters.** A coder who runs the §9 grep, then consults §9's survivor list to decide which
hits are "not stale," is told to *preserve* `:141` and `:143` — i.e. to keep the always-first
hardcoded sat entry that PR-1 exists to remove. §9 directly contradicts the removal §5 mandates.

**Fix (planner).** In §9, change the survivor list from `engine_v2.go:118,141,143` to
`engine_v2.go:118` only (plus `engine.go` and `optimizer_interfaces.go:44`), and — folding in F1 —
add `engine_queueing_model.go:81` as the QM survivor to be reconciled.

---

### F3 (minor, wrong-symbol) — §2 Table 1 Reason row attributes the `ReasonNoData`/`ReasonError` gate to `prcForVariant`; it lives in `ResultIsInformative`

**Where:** plan §2 Table 1 (Reason row) vs [`analyzer_helpers.go:58`](../../Main/internal/engines/pipeline/analyzer_helpers.go) / `:102`.

`analyzer_helpers.go:58` (`if vc.Reason != ReasonNoData && vc.Reason != ReasonError {`) is inside
`func ResultIsInformative` (`:53-63`), the liveness/last-good-analysis helper — **not**
`prcForVariant`. `prcForVariant` has a single definition at `:102` and reads only
`PerReplicaCapacity`; it never touches `Reason`. The line number and the semantics (Reason gating
those two sentinels) are correct; only the attributed function name is wrong. Flagged by two
independent verifiers. **Fix:** Table 1 Reason row should cite `ResultIsInformative:58` (the §10
pairing of `prcForVariant:102` is already correct).

### F4 (minor, accurate-in-spirit) — §2 Table 1 Role row cites `cost_aware_optimizer.go:305`, which reads `state.Role`, not `vc.Role`

`cost_aware_optimizer.go:305` is `role := state.Role` (from `VariantReplicaState`), used as the
RoleCapacities lookup key — role-related, but a different struct's field than the `vc.Role`
`VariantCapacity` field being classified. The genuine `vc.Role` bucketing read is
`analyzer_helpers.go:229` (`r := vc.Role` in `variantsForRole`). Classification of `Role`=(a) is
unaffected. **Fix (optional):** point the Role row at `analyzer_helpers.go:229` for the true
`vc.Role` read (and, if desired, note the decision's own `Role` field is set at
`cost_aware_optimizer.go:285`).

### F5 (minor, self-contradiction) — §4 heading "byte-identity ship gate" contradicts its own body ("never slice/byte equality")

§4's heading (L211) reads "Invariant #7 — the byte-identity ship gate," but the body (L218) states
identity is "decision-SET-identity keyed by `VariantName`, never slice/byte equality." The ship
gate is decision-set-identity of the optimizer's *output* (order is nondeterministic via the
`cost_aware_optimizer.go:257` map range and the unstable `sortByRemainingDesc` at
`greedy_score_optimizer.go:462`). (The plan legitimately uses "byte-identical" *elsewhere* — §2
L166, §5 L268 — to mean the anchor *struct* equals the sat result field-for-field, which is fine.)
**Fix:** rename the §4 heading to "the decision-set-identity ship gate" to avoid misleading a coder
into an order-sensitive comparison.

### F6 (minor, clarity) — §3 says "four masked bugs" then enumerates #1/#2/#3/#5 with no in-plan explanation of the #4 gap

PR-1 §3 (L189) reads "All four masked bugs … deferred to PR-2:" and lists #1, #2, #3, #5 — four
items, skipping #4. This is *internally* consistent (four bugs) and *cross-plan* coherent (PR-2 §2
L87-88 documents #4 as downgraded/traced 2026-08-03 — observability `Utilization` only, not an
active sizing bug), but a reader of PR-1 alone sees an unexplained 3→5 jump. **Fix:** add a
one-line "(#4 was traced to a non-bug — see PR-2 §2)" in PR-1 §3.

### F7 (minor, wrong-symbol) — §9 greps for the literal "special role", which appears nowhere in the dev-guide

`grep -i 'special role'` over `docs/developer-guide/` returns zero hits. The conceptual framing
exists — as the exemption at `multi-analyzer-pipeline.md:164-166` ("Saturation is exempt from this
gate … the engine identifies it by name") and as "always first"/"unconditionally" (L40/L226/L237)
— but under different wording. The other grep terms ("always first", "keeper of per-variant",
"Saturation is exempt") *do* find the stale narrative, so no site is actually lost; this is a dead
search term. **Fix:** drop "special role" from the §9 grep alternation (it's the *code-comment*
TODO wording at `analyzer_helpers.go:90`, not dev-guide wording) or replace it with a term that
hits, e.g. "identifies it by name".

### F8 (minor, under-specified but backstopped) — §8's three dev-guide section names are notional; none matches an actual `##` heading, and the stale narrative is ~6 sites, not one paragraph each

The actual `##` headings in `multi-analyzer-pipeline.md` are: Architecture / Components / User
configuration / Analyzer implementor guide / Pipeline flow / How results combine / Data model /
Optimizer internals / Optimizer consumption / Observability. §8's "Engine → optimizer contract",
"variant-metadata / saturation entry paragraph", and "analyzer enablement / configuration" are
approximate. The closest real mappings: anchor concept → **Data model** (L337) / **Optimizer
consumption** (L449); keeper/always-first wording → the L330 paragraph + the L164-166 exemption;
enablement → **User configuration** (L127) *plus* Pipeline-flow step 3 (L225-227) and Components
(L107-109). The "keeper / always-first / exempt" narrative is spread across ~6 sites (L40 diagram,
L164-166, L226, L237, L330, L455), not one paragraph.

This clears the convention's "not vague" floor (names the file, gives 3 targets, states what
changes per target) and is backstopped by §9's mandatory grep + §8's explicit fallback clause
("if a section named above does not exist, the coder maps intent → actual sections and notes any
mismatch"). It is *looser* than the convention's "name specific sections" ideal. **Fix (optional,
recommended):** replace the notional names with the real headings above and note the 6-site spread
so the coder doesn't stop after the first hit.

### F9 (minor, wrong-path) — config file path drops the `internal/` prefix

§5-1b and §7 write `config/saturation_scaling.go`; the real path is
`internal/config/saturation_scaling.go` (a top-level `config/` dir does not exist). All the
`ApplyDefaults` semantics the plan describes (empty-list insert of `{saturation, Enabled:true}` at
L296-301; nil→true per-entry default at L307-310; `Enabled *bool` field) are accurate. A coder
greping the literal path would miss. **Fix:** add the `internal/` prefix.

### F10 (minor, imprecise paraphrase + PR-2 caveat) — category (a) is not "metadata only sat produces"

Throughput *also* produces `VariantName`, `Role`, `ReplicaCount`, `PendingReplicas`
(`throughput/analyzer.go:373-376`); only `AcceleratorName`/`Cost` are sat-exclusive. The plan's own
§2 text frames (a) correctly as "sat-v2's topology/identity (never overwritten)," so this is a
paraphrase imprecision, not a plan error. **Carry-forward for PR-2:** sat sets
`ReplicaCount = readyCount` (`saturation_v2/analyzer.go:446`) while throughput sets
`ReplicaCount = nKV` (`throughput/analyzer.go:375`); classifying `ReplicaCount` as (a)
never-overwritten means a TA-binding anchor reports sat's `readyCount` even if they diverge.
Immaterial to PR-1 byte-identity (single vote = sat), but PR-2's multi-vote refresh must decide
whether the anchor's `ReplicaCount` should track the binding vote — worth a line in PR-2.

### F11 (minor, imprecise classification) — `rescale.go:546` RoleCapacities is classified "off-ballot / stays per-vote," but the rescale path sources it from the single anchor

Table 2 marks `RoleCapacities` as off-ballot/per-vote, but `roleDemandGPUs` (`rescale.go:544-547`)
has no ballot iteration — it reads `satEntry.RoleCapacities[role]` off the single `satEntry`
pointer that §6-2b/§10 reroute to `req.Anchor`. So in the *rescale* path RoleCapacities comes from
the anchor, not per-vote. Mitigated: the plan defers rescale TA-only correctness to PR-2 (§6-2b
L318-319) and rescale is off in the default golden path, so it does not break PR-1 byte-identity.
The line/symbol are exact; only the per-vote label is imprecise for this one site. (Relatedly, §10's
rescale block omits the `sortVariantsForScaleDown` call at `rescale.go:397`; defensible — it's
already a flagged PR-2 combine site and its ballot arg correctly stays per-vote.) **Fix (optional):**
footnote Table 2's RoleCapacities row that the rescale read is anchor-sourced pending PR-2.

### F12 (minor, uncovered stale site) — `saturation-scaling-config.md:266` ("It always runs and drives the optimizer") is covered by neither §9's grep list nor §8's named file

§8 names only `multi-analyzer-pipeline.md`; §9's enumerated hits don't include this line. Post-PR-1,
"drives the optimizer" is conditional (TA-only disables sat's vote), so this sentence becomes stale.
**Fix:** add `saturation-scaling-config.md` to §8's dev-guide targets (or to §9's expected-hit list)
with the "always runs and drives the optimizer" → "runs by default; its vote can be disabled like
any analyzer" edit.

---

### C1 (convention, borderline) — §11 places a `git push` verb in a coder-facing plan

§11 L521-522: "ta-anchor-refactor needs a matching origin branch at creation
(`git push -u origin ta-anchor-refactor`) — subject to Dean's per-push confirmation." Per
CODER-CONVENTIONS §2 a coder never pushes, and the "no other-role actions in plan docs" convention
says a Type-3 plan should not carry action verbs a coder might wrongly execute. It *is* gated on
Dean's confirmation, so a disciplined coder hands it back — low risk — but it should be reframed as
a planner/Dean action ("the planner/Dean creates the origin branch"). PR-2 §0's planner/scoper
imperatives are correctly fenced behind its "do NOT start" STUB and are compliant.

---

## Coder-executability findings (E-series)

**Lens.** F1–F12 / C1 above verify that the plan states *true things about the code*. This section
asks the orthogonal question: **can a coder build §5–§7 at the sites the plan names, and does the
test scaffold survive Commit 2?** Method: a 4-agent coder-simulation pass (each agent walked one
commit as if implementing it), then direct re-verification of the five MAJOR blockers against
`Main/` at `9906dac5`. **Every fix below is a plan revision for the planner** — none is a coder
instruction; the coder only ever reads the revised plan.

**Headline.** The plan is accurate as documentation but **not executable as written at Commit 1/2**.
The mechanism §5-1b prescribes (`req.Anchor = copy(baseResult)` inside `runAnalyzersAndScore`)
cannot be built at that function, and the shared test builder `withSatEntry` — on which Commit 2's
reroute depends — never sets `Anchor`, so Commit 2 as specified turns ~all optimizer tests **and the
just-landed #1513 goldens** red. E1–E5 warrant the same planner pass as F1/F2.

### E1 (MAJOR, unrealizable-site) — §5-1b writes `req.Anchor = copy(baseResult)` inside `runAnalyzersAndScore`, which has no `req` and does not build the request

**Where:** plan §5-1b (L246-268), §10 (read-site inventory) vs
[`internal/engines/saturation/engine_v2.go:96-106`](../../Main/internal/engines/saturation/engine_v2.go)
(`runAnalyzersAndScore` signature) + `:110` (`baseResult`) + `:581`,`:607-610`
(`collectV2ModelRequest` request literal).

**What.** `runAnalyzersAndScore` takes **no `req`** and returns `([]pipeline.NamedAnalyzerResult,
error)` (`:96-106`); the only anchor-worthy value in scope is the *local* `baseResult` (`:110`). The
`pipeline.ModelScalingRequest` literal is assembled in a **different** function,
`collectV2ModelRequest` (`:581`; `return &pipeline.ModelScalingRequest{… AnalyzerResults:
namedResults …}` at `:607-610`), which has `namedResults` but **not** `baseResult`. So
`req.Anchor = copy(baseResult)` cannot be written at the site §5-1b names — `req` does not exist
there, and where `req` is built `baseResult` does not.

**Why it matters — two failure modes, one silent.** To set the anchor the coder must thread
`baseResult` (or the built anchor) out of `runAnalyzersAndScore` into `collectV2ModelRequest` — a
return-signature change that breaks **~19 call sites across 5 files** (1 prod call in `engine_v2.go`
+ 4 test files: `engine_v2_test.go`, `engine_v2_liveness_test.go`,
`engine_v2_demand_liveness_test.go`, `engine_v2_population_test.go`), none of which appear in §5's
Files list. The one shortcut the site *does* allow — build the anchor from `namedResults[0]` inside
`collectV2ModelRequest` — silently sources anchor-(a) [`AcceleratorName`/`Cost` + topology] from
**TA** in the TA-only path (Commit 3), while the default goldens stay green because ballot[0] is
sat there. That is a silent-correctness landmine, not a compile stall.

**Fix (planner).** §5-1b must (1) name `collectV2ModelRequest:607` as the anchor-set site (not
`runAnalyzersAndScore`); (2) specify the return-signature change that carries `baseResult`/anchor
out of `runAnalyzersAndScore`, and enumerate the ~19 call sites (incl. the 4 test files) in §5's
Files list with the mechanical fixup; and (3) **explicitly forbid** sourcing the anchor from
`namedResults[0]`, stating it must derive from the saturation `baseResult` regardless of ballot
composition. This also settles the §0 copy-mechanism deferral — the site is no longer coder's
discretion once §5 names it.

### E2 (MAJOR, test-scaffold break) — `withSatEntry` (and PD/V2 siblings) never set `Anchor`; after Commit 2's reroute all 87 fixtures + the #1513 goldens go red

**Where:** plan §6 (Commit 2 reroute) + §9 (grep) + §11 (do-not-re-signature) vs
[`internal/engines/pipeline/cost_aware_optimizer_test.go:16-27`](../../Main/internal/engines/pipeline/cost_aware_optimizer_test.go)
(`withSatEntry` body).

**What.** `withSatEntry` sets only `req.AnalyzerResults` (`:18-24`), never `req.Anchor` — its
docstring even reads "so CostAwareOptimizer can find the saturation entry," the exact by-name
lookup Commit 2 reroutes to `req.Anchor`. It is used **87 times** across four test files
(`greedy_score_optimizer_test.go` 49, `cost_aware_optimizer_test.go` 24, `rescale_optimize_test.go`
11, `optimizer_equivalence_test.go` 3). After Commit 2 makes `bindingAnchor(req)` return
`req.Anchor`, every one of those fixtures yields a nil anchor → the nil-guard skips the request →
zero decisions → ~all optimizer tests and the #1513 goldens fail.

**Why the plan actively steers past the fix.** §11 tells the coder *not* to remove or re-signature
`withSatEntry` (to keep the goldens file compiling), which discourages the exact remedy; §9's grep
is case-sensitive on `satEntry`, so it never matches `withSatEntry`; and §6's Files list
("`analyzer_helpers_test.go` + tests referencing `saturationEntry`") names neither the builder nor
these four files. **Distinct from the Confirmed-correct §11/goldens-Finding-2 note (L265-267):** that
note concerns keeping `withSatEntry`'s *signature* stable so the goldens file compiles; E2 is the
*runtime* break — a now-nil `Anchor` skipping every fixtured request.

**Fix (planner).** §6 should add an explicit step directing that `withSatEntry` and its PD/V2
siblings set `req.Anchor` from their source result **in-body** (signature unchanged — consistent
with §11's "do not re-signature" constraint, which the plan should note is *compatible* with the
in-body assignment), and add `cost_aware_optimizer_test.go` + the other three fixture files to §6's
Files list. §9's grep should be made case-insensitive (or add `withSatEntry` explicitly) so the
builder is not missed.

### E3 (MAJOR, invalid Go + latent aliasing) — `copy(baseResult)` does not compile, and a shallow struct copy aliases the stored sat result

**Where:** plan §0 / §5-1b (`copy(baseResult)`) vs
[`internal/domain/analyzer.go`](../../Main/internal/domain/analyzer.go) (`AnalyzerResult` has
`VariantCapacities []VariantCapacity` + `RoleCapacities map[…]`; no `Clone`/`DeepCopy`/`Copy`
method).

**What.** `copy` is the slice builtin; it does not compile on a struct. There is **no** clone
method on `domain.AnalyzerResult`. A plain struct assignment shares the `VariantCapacities` backing
array and the `RoleCapacities` map, so the (b)-mirror overwrite then **mutates the analyzer's
stored `baseResult`** — violating the plan's own "the anchor never mutates the stored result"
invariant (§2 L166, §5 L268).

**Why it ships silently.** In the default/goldens path ballot[0] *is* `baseResult`, so the
(b)-mirror is a self-assign no-op and no golden moves; the corruption only manifests in PR-2's
multi-vote refresh. This is exactly the "green now, wrong later" class the conventions warn about.

**Fix (planner).** §5-1b must specify explicit deep-copy code (a fresh `VariantCapacities` backing
slice + cloned `RoleCapacities`; state the required depth), and §7 should add a PR-1 unit assertion
that mutating the anchor's (b)-fields leaves the analyzer's stored sat result unchanged. If a
`Clone` helper on `domain.AnalyzerResult` is preferred, §5 should name it as a new artifact (adds a
`domain/` file to the Files list).

### E4 (MAJOR, wrong field-source + empty-ballot panic) — §6-2c routes fields that live on `VariantCapacity`, not `AnalyzerResult`, and removes the guard that today prevents an index panic

**Where:** plan §6-2c vs
[`internal/engines/pipeline/cost_aware_optimizer.go:283-284,302`](../../Main/internal/engines/pipeline/cost_aware_optimizer.go)
(assignment sites) + `:48-51` (the graceful skip).

**What (field source).** §6-2c says `AcceleratorName`/`Cost`/`Utilization` at `:283`/`:284`/`:302`
should "read from `req.Anchor`." But those are read as `vc.AcceleratorName` / `vc.Cost` /
`vc.Utilization` — fields of `domain.VariantCapacity`. `domain.AnalyzerResult` has **no**
`AcceleratorName` or `Cost` field (so `req.Anchor.AcceleratorName`/`.Cost` do not compile), and its
`Utilization` is *model-level* (`TotalDemand/TotalSupply`) whereas `vc.Utilization` is *per-variant*
(`TotalDemand/TotalCapacity`) — so that one compiles but silently substitutes the wrong ratio.
These fields already become anchor-sourced automatically once the `buildCapacityMap` input is
repointed (§6-2b); §6-2c should **leave `:283`/`:284`/`:302` reading `vc.X`** and not touch them.

**What (panic).** Today `cost_aware_optimizer.go:48-51` (`satEntry := saturationEntry(…); if
satEntry == nil { continue }`) gracefully skips a model with no ballot. After the rename
`bindingAnchor(req)` returns the engine-always-set (non-nil) `req.Anchor`, so the guard never fires
— and §6-2c's proposed RC/SC read via an unguarded `req.AnalyzerResults[0].Result` then **panics**
on an empty-ballot config. A regression from a currently-graceful path.

**Fix (planner).** §6-2c should (1) correct the field-source wording — those three fields flow via
`vcMap` and require no edit at the assignment sites; and (2) specify a length guard
(`if len(req.AnalyzerResults) > 0 && req.AnalyzerResults[0].Result != nil { … }`) plus the intended
empty-ballot RC/SC behavior, restoring the graceful skip the rename removes.

### E5 (MAJOR, untestable-as-specified) — §7's field-classification test has no observable anchor at the build site §5/§10 name, and the TA-only fixtures it needs can't be built by `withSatEntry`

**Where:** plan §7-3b (new tests) vs the E1 build-site reality + the E2 builder reality.

**What.** §7 says the field-classification test lives "in the pipeline and/or engine package," but
the only function returning a `*ModelScalingRequest` is `collectV2ModelRequest` — a pipeline-package
test can only assert a hand-built fixture, proving nothing about the *engine's* `(a)+(b)` copy
logic. Separately, the TA-only assertions require **anchor ≠ ballot[0]** fixtures (anchor-(a) from
sat, anchor-(b) from the TA vote), but the only builder (`withSatEntry`) sets ballot and (post-E2)
anchor from the *same* result → anchor == ballot, so the natural reuse makes the classification
test pass **vacuously**.

**Fix (planner).** §7 should (1) place the engine-level field-classification test in the
`saturation` package, reading the anchor from `collectV2ModelRequest`'s returned request via the
existing `fakeAnalyzerWithResult` / minimal-engine helpers (resolving the §5/§10 build-site
question from E1); and (2) specify a new fixture builder that constructs anchor-(a) and anchor-(b)
from *distinct* results, so the classification is asserted non-vacuously.

### E6–E13 (minor executability nits — plan revisions)

- **E6** — Commit 1's uniform gate reddens four **un-enumerated** engine-package suites that bypass
  `ApplyDefaults` with saturation-omitting configs: `engine_v2_test.go:375-387` & `:413-424`,
  `engine_v2_liveness_test.go:28`, `engine_v2_demand_liveness_test.go:63-66`. §7's gate wording
  ("goldens green") hides this churn. §7 should enumerate the files + the intended fixture fix.
  (Dovetails the already-tracked sat-v2 default-off gap, but names the concrete suites.)
- **E7** — §5-1b.2's reuse branch names only `satUp/satDown`, dropping `Score`/`Remaining`/`Spare`;
  a literal read fails the default goldens. §5-1b.2 should reconstruct the full 7-field
  `NamedAnalyzerResult`.
- **E8** — §5-1c's repoint must **keep** the nil→continue guard (recast as `req.Anchor == nil`),
  not drop it; and `satReq` (`engine_v2_quota_test.go:14-24`) needs `Anchor` set — add it to §5-1c's
  Files list. (The "no-entry namespace still active" test relies on the guard.)
- **E9** — §9 lists `satEntry` as a global rename target, but §6/§10 keep it as a local/field/param
  name in several helpers. §9 should state explicitly whether those ~50 non-getter hits are renamed
  to `anchor` or kept (and, if kept, excluded from §9's identifier mandate).
- **E10** — §10 flags pure consumers (`costEfficiency:234`, `fairShareCap:421`,
  `sortByCostEfficiencyAsc`, `costGreedyRolePick`) as "route to anchor," but they receive
  `VariantCapacity` by param/closure and need **no edit** — §10 should mark them "consumer, no edit;
  data flows from the repointed source arg."
- **E11** — §6-2a's "adjust signatures at the ~11 call sites" is misleading — no helper needs a new
  parameter (`req` is already in scope). §6-2a should reword to "change each getter *argument* from
  `req.AnalyzerResults` to `req`."
- **E12** — §7-3a is ambiguous on whether Commit 3 touches production; TA is already config-gated at
  `cmd/main.go:504-509`. §7-3a should state Commit 3 is test-only for enablement.
- **E13** — §13 item 3 asks the reviewer to confirm "the combine part of `fairShareCap`" unchanged,
  but `fairShareCap` (`:421`) has no Σ combine (the Σ is in `fairShareValue`); §13 should reword.
  Also §13 inserts "4a." between items 4 and 5 (14 checks under 13 numbers) — renumber.

### Extends two existing findings (same planner pass)

- **Extends F8** — the real `##` headings and the ~4-site spread for the "Engine → optimizer
  contract" content (`multi-analyzer-pipeline.md` L40/L237/L330/L455) confirm §8's bullet-1 heading
  is notional; §8 should name the real sections or defer to §9's grep as the authoritative edit set.
- **Extends F12** — beyond `saturation-scaling-config.md:266`, the same file carries a stale "not
  yet consumed … in a follow-up PR" block at **`:255-259`** that PR-1 also falsifies; neither §8
  (names only `multi-analyzer-pipeline.md`) nor §9's grep catches it. §8 should add the file and the
  `:255-259` edit.

---

## Confirmed correct (spot-checked; no action)

- **Domain types.** `VariantCapacity` (11 fields), `AnalyzerResult` (12 fields), `RoleCapacity`
  (6 sub-fields) each fully and correctly enumerated in Tables 1/2 — nothing omitted.
- **Producer sourcing.** sat-v2 (`saturation_v2/analyzer.go:441-452`, sole literal) sets all 11
  fields incl. the full topology; throughput (`throughput/analyzer.go:372-381`, sole literal) sets
  9 fields and never `AcceleratorName`/`Cost` (grep-confirmed) — the anchor is the sole source of
  those two.
- **engine_v2.go refs.** `runAnalyzersAndScore` span `:96-178`; `baseResult` `:110`; list assembly
  `:138-171`; the sat-first literal `:140-148`; the name-skip `:150-152`; the `:93-95` "keeper"
  comment (verbatim); the `:384-385` `effectiveEnabled` docstring (verbatim); `:489-506`/`:523-545`
  GPU-usage by-name scans. `optimizer_interfaces.go:41-48`/`:44` comment (verbatim).
- **Optimizer read-sites.** 13/14 cost_aware sites exact (incl. the `:303-314` RC/SC block that is
  the re-route target); greedy + analyzer_helpers sites exact incl. def-vs-usage splits
  (`applyAllocation:71`/call`:76`, `roleBottleneckReplicas:182`/call`:188`); `initRoleState:127`
  per-vote RC/SC reads `:141/142/143`; all six rescale `saturationEntry` topology reads
  (`:225,:342,:465,:486,:589,:604`) + `:521`/`:544`/`:546`.
- **Invariant #7.** Both nondeterminism sources exact: map range `cost_aware_optimizer.go:257`;
  unstable `sort.Slice` in `sortByRemainingDesc` `greedy_score_optimizer.go:462-463`. Decision-set-
  identity model consistent across PR-1 §4, goldens-plan §determinism, and goldens-review Finding 1.
- **Bug line-refs precise (not stale).** `fairShareValue:61` def vs `:73` Σᵢ sum-site;
  `sortVariantsForScaleDown:161` def vs `:168` Σₑ Score·PRC tie-break — deliberate dual-citations,
  both accurate.
- **§12 deletion classification.** Sat-first entry + name-skip = DEPRECATED; multi-vote refresh +
  bugs #1/#2/#3/#5 = DEFERRED. Nothing removed left unclassified.
- **§11 goldens Finding-2 resolution.** `withSatEntry` confirmed at `cost_aware_optimizer_test.go:16`
  (outside the goldens file, ~65 call sites); §11's "do not remove/re-signature; copy into the
  goldens file" remedy matches Finding 2 verbatim; §13 item 1 re-asserts the compile-check.
- **Rebase target.** §11/§13 correctly target the moving `main` tip, never the pinned interim
  cut-point `a2f49ccf` (which is correctly framed as the physical goldens-branch tip).
- **Bug #4 handling.** Coherent across both plans (absent from PR-1's deferral list; downgrade
  explained in PR-2 §2).

---

## Recommended disposition (of the old plan — SUPERSEDED by Part 2)

> **Superseded.** The dispositions below were written to guide *patching* `ta-anchor-refactor-plan.md`
> in place (fold F1 into §5/§9/§10, rewrite §5-1b, etc.). Since the mechanism was redesigned, the
> planner does **not** patch the old plan — it authors a fresh Type-3 plan against Part 2's spec.
> These are retained to show the state at which the old plan was abandoned; §2.2 carries the
> still-relevant findings forward.

- **F1 + F2 are blocking for PR-1 hand-off** — both are within the `saturationEntry → bindingAnchor`
  rename's blast radius and both can cause silent behavioral loss (F1 at runtime for the QM path;
  F2 by misleading the coder into preserving the always-first special-case). The planner should fold
  the QM builder into §5/§9/§10 and correct the §9 survivor list before a coder starts.
- **F3–F12 + C1 are non-blocking polish** — reference/label/path corrections and dev-guide-target
  tightening; several are backstopped by the plan's own §9 grep. Best folded in during the same
  planner pass that addresses F1/F2.
- **E1–E5 are blocking for PR-1 hand-off (executability), alongside F1/F2.** They are not
  correctness-of-facts issues — they are "the coder cannot build this at the named site, or builds
  it green-but-wrong." E1 (build site) and E2 (`withSatEntry` → red goldens at Commit 2) will stall
  or silently break a coder on the first two commits; E3/E4 add a latent aliasing bug and an
  empty-ballot panic. The planner should rewrite §5-1b (build site + return-signature + forbid the
  `namedResults[0]` shortcut), add the `withSatEntry`/sibling `Anchor` step to §6, specify the
  deep-copy in §5/§7, and correct §6-2c — in the same pass as F1/F2. E6–E13 + the F8/F12 extensions
  are polish for that pass.
- The goldens plan/review and PR-2 stub need no changes from this review.

---

# Part 2 — Recommended course of change: spec for the new Type-3 plan

This part is the **explicit, self-contained specification** for the fresh Type-3 coding plan the
planner authors. It consolidates the corrected anchor mechanism and every decision from the
2026-08-04 discussion, and supersedes the fix directions in Part 1 (F1/F2/E1–E5 and the old
Recommended disposition). It was surfaced during a parallel comprehension pass —
[`planning/multi-analyzer-dataflow-map.md`](multi-analyzer-dataflow-map.md) §8 and
[`planning/scale-from-to-zero-analysis.md`](scale-from-to-zero-analysis.md) — plus direct fact-finding
against `Main/` at `9906dac5`; it is not a re-review of the old plan text.

**How to use this part.** §2.1 is the core mechanism (the anchor build) — the heart of the change.
§2.2 maps every Part-1 finding forward (resolved / still-applies / separate-PR). §2.3 records the
surrounding decisions (QM, liveness, the standalone validation fix, scale-from-zero orthogonality).
§2.4 is the partial-zero interim recommendation (still under discussion). §2.5 is the TA-side
proactive complement. §2.6 lists the test requirements the new plan must include. §2.7 fences scope
and deferrals. The closing "Status" section records the handoff already sent to the planner and the
three closed fact-finding items. **A coder never reads this doc** — the planner turns it into a
Type-3 plan; a coder reads that plan.

**Framing — this is a fresh plan, likely a fresh branch.** The old `ta-anchor-refactor-plan.md`
mechanism ("build the anchor in Phase 1", `req.Anchor = copy(baseResult)`) is abandoned, not
patched. The new plan implements the two-phase mechanism below, in which **there is no stored
`.Anchor` field at all** — the anchor is derived on demand by the Phase-2 getter from the ballot
the engine already assembles. That single structural decision is what dissolves the bulk of the
Part-1 executability blockers (E1/E2/E3), so the new plan should state it up front.

## 2.1 The corrected two-phase mechanism

**Phase 1 (`engine_v2.go` / generation) — call every analyzer, tag status, never decide:**
1. Every registered analyzer is called unconditionally — sat included, no special-casing. Resolves
   E1: sat's failure mode becomes symmetric with every other analyzer's, not uniquely catastrophic.
2. Every call produces one ballot entry; **order does not matter.** This retracts the
   "positional binding" direction floated earlier (binding-by-ballot-position) — correctness must
   not depend on construction order.
3. Each entry carries an explicit status: enablement + error condition — replacing today's
   asymmetry (registered analyzers silently return `nil` on failure; sat's failure aborts the whole
   analyzer loop).
4. The engine may validate ("no `(a)` anywhere?", "no live+enabled `(b)` anywhere?") but makes no
   decisions from that.
5. The Phase-1 outcome carries summary status fields; the ballot itself stays a simple,
   order-independent, one-entry-per-analyzer list.

**Phase 2 (the binding/anchor getter, successor to `saturationEntry`) — interpret, decide, build:**
1. Check statuses.
2. Find the binding analyzer.
3. Generate the anchor's `VariantCapacities`, merged **per variant, matched by `VariantName`**:
   `(a)` fields (`AcceleratorName`/`Cost`/`Role`/`ReplicaCount`/`PendingReplicas`) from sat's entry
   for that name; `(b)` fields (`PerReplicaCapacity`/`TotalCapacity`/`TotalDemand`/`Utilization`/
   `Reason`) from the binding analyzer's entry for that same name. Model-level PRC/RC/SC always
   come from the binding analyzer, never blended.
4. Remove disabled/non-live results from the list before combine math runs — done here, not at
   Phase-1 packaging time (safer).
5. **No analyzer-level sort needed at this stage** — confirmed nothing in the codebase sorts the
   analyzer-ballot slice itself, only per-variant lists (`sortByCostEfficiencyAsc`,
   `sortVariantsForScaleDown`, keyed on `PerReplicaCapacity`/`Cost`) which will already read
   correctly once the anchor is built. Those existing, unchanged sort call sites are unaffected.

Refresh (subsequent calls, PR-2 territory): skip entirely if the ballot has one analyzer;
otherwise re-find the binding analyzer and update `(b)` if it changed.

**Per-variant fallback (agreed):** if the binding analyzer has no entry for a given variant (e.g.
TA skipped a zero-replica variant), fall back to sat's `(b)` for that specific variant rather than
leaving it empty. Must run *before* step 4's removal of disabled entries — if sat's own entry gets
pruned because it isn't binding, the fallback source disappears with it. Confirmed unrelated to
scale-from-zero (see decision 4 below) — it only helps the *partial*-zero case inside this engine.

## 2.2 How this redesign resolves the Part-1 findings

Each Part-1 finding maps to one of: *resolved-by-redesign* (the new mechanism removes the gap),
*still-applies* (the new plan must handle it), or *separate-PR* (tracked elsewhere). This is the
forward map the Document-structure section points at.

- **E1 (build site unrealizable)** — resolved: no anchor-building code in Phase 1 at all.
- **E2 (`withSatEntry` breaks under Commit 2, ~87 call sites + goldens)** — likely moot: there is no
  stored `.Anchor` field to separately populate; the getter derives the anchor on demand from
  `req.AnalyzerResults`, the same field `withSatEntry` already populates. Needs confirming once
  implementation starts, not asserted as certain.
- **E3 (invalid-Go copy / shallow-aliasing)** — resolved: the per-variant merge builds fresh struct
  literals field-by-field, not a shallow copy of the whole result.
- **E4 (§6-2c wrong fields + empty-ballot panic)** — field-source half resolved by the explicit
  per-field mapping above; empty-ballot half resolved by Phase 1's "no live analyzers" validation
  flag plus the failure policy below — no unguarded indexing.
- **E5 (new tests can't be built at the site)** — eased: the getter lives in the pipeline package
  with full `req` access; tests can construct `ModelScalingRequest` fixtures directly.
- **F1 (QM nil-anchor)** — decision made, see below (option b: error, not fix-the-nil-anchor).
  §9/§10 should account for `engine_queueing_model.go` as a **disabled**, non-participating path.
- **F2 (§9-vs-§5 survivor-list contradiction)** — does **not** carry to the new plan: it was an
  internal contradiction in the *old plan's own text* (its §9 survivor list vs its §5 removal
  order). The new plan writes its own grep/survivor inventory from scratch, so the contradiction
  cannot be inherited — but the *lesson* still applies: the new plan's grep-survivor list must be
  reconciled against its own removal steps, and must account for `engine_queueing_model.go` as a
  now-**disabled**, non-participating path (per §2.3 decision 1), not a live `SaturationAnalyzerName`
  survivor to preserve.
- **F3–F12, C1 (Part-1 polish)** — most were reference/label/path nits in the old plan's prose and
  are moot once that plan is discarded. Three carry a *substantive* forward note the new plan should
  fold in regardless of mechanism: **F10** (sat sets `ReplicaCount = readyCount` vs TA's `nKV` — the
  multi-vote refresh must decide whether the anchor's `ReplicaCount` tracks the binding vote;
  PR-2 territory), **F11** (the rescale path reads topology/`RoleCapacities` off the *single* anchor,
  not per-vote — a required test target once the merged anchor exists, see §2.6), and the **F8/F12
  dev-guide reality** (the real `##` headings and the ~6-site "keeper/always-first/exempt" narrative
  spread across `multi-analyzer-pipeline.md` + `saturation-scaling-config.md:255-259,266` — the new
  plan's dev-guide step must name those actual sections, not notional ones).

## 2.3 Decisions (surrounding the mechanism)

Four decisions were settled in the 2026-08-04 discussion. Decisions 1, 2, and 4 shape the new
plan's scope directly; decision 3 is explicitly carved out into a separate PR.

1. **QM: option (b) — make it an error to enable QM under the new code.** Test blast radius
   checked: `engine_queueing_model_test.go` does not call `optimizeQueueingModel` at all — it tests
   the optimizer's liveness-gate handling of a QM-*shaped* fixture (`withQMEntry`), explicitly
   avoiding the real pipeline. The QM references in `engine_scale_to_zero_enforce_test.go` and
   `mode_label_test.go` are label/enforcer tests independent of whether the real QM path runs. No
   test found that exercises `optimizeQueueingModel` end-to-end. **e2e sweep also done and clean
   (2026-08-04):** `grep -rl "queueing.model\|QueueingModel\|queueing-model" test/e2e/` finds a
   single hit, `saturation_analyzer_path_test.go`, and it's a `TODO(cleanup)` comment about
   unifying analyzer-selection config, not functional test code exercising QM. **No test carnage
   anywhere in the suite** — planner should still spot-check independently, but this item is
   closed, not deferred.
2. **Liveness/failure policy:**
   - No live analyzers for a model → "do nothing" (no scale up or down) is the base behavior, not
     a full abort.
   - **Do not kill WVA for this, for now** — confirmed no existing code does this today: a
     sat-v2 failure is already caught per-model inside `optimizeV2`'s loop (`engine.go:996-1002`),
     logged, an `OptimizationFailedEvent` recorded, and routed through the existing
     `emitSafetyNetMetrics` (`engine.go:1828+`) before `continue`-ing to the next model. No panics
     or process exits exist on this path today (the only `panic()`s in `engine.go` are
     constructor-time nil-dependency checks, unrelated to runtime analyzer failures).
   - Stale WVA (keeps running, logs the error, doesn't die) is accepted as good enough.
   - `emitSafetyNetMetrics`'s existing fallback — "Strategy 1: use the previous desired-replicas
     value if available, else current replicas" — is the right reusable primitive for the
     "no live analyzer" case; it already documents never withholding the scaling signal from
     HPA/KEDA even with incomplete data.
   - **Closed (2026-08-04) — confirmed safe, more robust than expected.** `applySaturationDecisions`
     (`engine.go:1561+`) iterates **every active VA** each cycle, not just VAs with a fresh
     decision. For a VA with none — exactly the "do nothing" case — it explicitly re-affirms
     `targetReplicas` from `Status.DesiredOptimizedAlloc.NumReplicas` if set and `>0`, else falls
     back to the deployment's actual current replica count, else (a brand-new VA with no prior
     status) resolves from the live scale target directly "to avoid unintended scaling"
     (`engine.go:1615-1645`). The code's own comment states the intent directly: "We effectively
     explicitly 'decide' to keep things as they are if no decision was made." Nothing clears the
     field on this path — it's independently reinforced by both this function and
     `emitSafetyNetMetrics`.
   - Never-alive sat (no `(a)`, ever) is probably fatal in the "do nothing forever for this model"
     sense. Stale-but-not-dead sat is probably fine to proceed on, since most of `(a)` is static.
     Dead TA in `[TA]`-alone is fatal the same way.
3. **`AnalyzerName` validation gap** (found while checking whether adding TA to the
   optimizer-selection gate carries risk — it doesn't, TA never belongs there): `AnalyzerName` is
   completely unconstrained in `Validate()`, and the dispatch switch's `default` case silently
   falls back to the deprecated V1 engine for any unrecognized value — not a no-op, a silent
   algorithm swap. **Agreed: separate, small, standalone PR. Not part of this fix, not affected by
   it, not a 0.9 requirement.**
4. **Scale-from-zero does not use the anchor, confirmed by direct grep — the per-variant fallback
   above has zero effect on it.** `internal/engines/scalefromzero/` contains no reference to
   `Anchor`, `AnalyzerResult`, `ModelScalingRequest`, or the `pipeline` package at all — it is a
   fully separate engine (`planning/scale-from-to-zero-analysis.md` §2) that never touches the
   ballot/anchor system this refactor changes. The per-variant fallback only helps the
   *partial*-zero case inside this engine (a sibling variant of a model that does have live
   replicas) — it cannot help scale-from-zero's own mechanism.

## 2.4 Partial scale-from-zero under `[TA]`-alone — rely on `scalefromzero` (interim) — STILL UNDER DISCUSSION ("almost agree," not final)

Follow-up to decision 4 above (scale-from-zero doesn't use the anchor). This subsection traces
*how* the anchor/binding mechanism handles a variant that's individually at zero replicas while
its model siblings are live (**partial**-zero, distinct from the full-zero case decision 4
addresses), and why that path is fragile under `[TA]`-alone specifically.

**Two distinct mechanisms are involved, only one of which is anchor-dependent:**

- **Mechanism A — `roleBottleneckReplicas` (quantity sizing).** Reads the *raw ballot* directly
  (`prcForVariant(e.Result, v)` per analyzer, returning `0` if that analyzer has no entry for `v`),
  not the anchor. **It is not zero-aware in any way** — confirmed via `allocateForModelPaired`
  (`analyzer_helpers.go:333-430`): the outer loop fires whenever model/role-level aggregate
  remaining demand is positive (from `initRoleState`, itself from `RequiredCapacity` — which
  aggregates `TotalDemand`/`TotalAnticipatedSupply` across *every configured variant*, correctly
  showing zero contribution from a variant with `ReplicaCount==0` regardless of any capacity
  *estimate* it might have). Only *after* `pick()` selects a candidate variant does
  `roleBottleneckReplicas` run, and only for that one variant — it is the generic
  `ceil(remaining/PRC)` sizing formula, applied identically whether the picked variant's current
  count is 0 or 50.
- **Mechanism B — candidate visibility (identity).** `costGreedyRolePick`/`fairShareRolePick` only
  ever iterate `variantsForRole(variants, role)` where `variants` is the binding entry's
  `VariantCapacities` (today: `satEntry.VariantCapacities`; under the redesign: the anchor's merged
  list). `buildCapacityMap` is keyed from the same list. **This is where the per-variant fallback
  (agreed earlier in this doc) is load-bearing, not a safety net**: without it, a variant absent
  from the binding analyzer's list (e.g. TA has no entry for a zero-replica variant, per D1) is
  invisible to `pick()` — never a candidate, regardless of what mechanism A could compute for it —
  and the decision that does get built for it defaults to `Action: NoChange` with a zero-value
  `VariantCapacity` (empty `AcceleratorName`/`Cost`/`Utilization`, not a crash).

**Realistic partial-zero scenarios are not "revival from full zero."** Today's scale-from-zero
engine has no cross-variant coordination (`scale-from-to-zero-analysis.md` §4) — when a *fully*
zero model gets revived, every variant/role comes back together as a side effect of that
coordination bug. So partial-zero actually arises from: (a) a new variant/accelerator added to an
already-live model, starting at 0 while siblings serve traffic, or (b) organic cost-optimal drain
of one variant to 0 via the *normal* scale-down path (permitted when `MinReplicas` is 0/nil,
independent of the dedicated scale-to-zero enforcer, which requires the whole model idle).

**What the picker actually sizes, precisely:** not a hardcoded RC of 1, not fake demand — the real,
measured model-level aggregate shortfall (from active siblings' actual traffic), converted into a
replica count for the specific zero-replica variant via `ceil(aggregate_remaining / PRC)`, where
`PRC` for that variant can only ever be an *estimate* (sat's capacity-store — parsed deployment
args, or borrowed from a compatible sibling), never a measurement, since there's no live replica to
measure.

**The fragility Dean flagged, confirmed as real:** cost-efficiency ranking and the estimate itself
may not be trustworthy for a zero-replica candidate. TA has no capability to estimate PRC at all
here (D1). Sat's estimate may also be unreliable or entirely absent without a compatible sibling to
borrow from — and if it lands at `PerReplicaCapacity <= 0`, the variant fails `costGreedyRolePick`'s
gate and is **permanently** invisible (no self-correction is possible, because it's never picked in
the first place — self-correction requires at least one bootstrap replica to exist so live
measurement can replace the estimate on a later cycle).

**Key finding — this appears to already be solved in production, no new code needed.** The
`scalefromzero` engine (`scale-from-to-zero-analysis.md` §2) is gated by `isInactive`
(`internal/utils/variant.go:270-272`), which checks `GetDesiredReplicas(scaleTargetAccessor) == 0`
— **that specific VA's own replica count**. Confirmed no model-level pre-filter exists anywhere in
`filterVariantsByScaleTargetAccessor` (`variant.go:97-`). So this engine already, today, revives
**any** individually-zero-replica variant/role whenever its model shows EPP-level flow-control-queue
demand, using a hardcoded `1`, with zero involvement from sat, TA, PRC estimation, or which
analyzers are configured — it's registered unconditionally in `cmd/main.go`, orthogonal to
`cfg.Analyzers`. This was not previously drawn out as an implication in
`scale-from-to-zero-analysis.md` (the per-VA fact was captured there, but not this consequence) —
being added there too.

**One timing caveat, not to be glossed over:** scale-from-zero is *reactive* — it fires only once
requests are genuinely queueing at the EPP, whereas the analyzer path's `RequiredCapacity` signal is
more *proactive* (can reflect a growing demand-vs-anticipated-supply gap before anything queues).
Relying on scale-from-zero as the safety net means the variant does come back, but only once real
queueing starts, not ahead of it.

**Checked (2026-08-04) — confirmed real, no protection exists, not just unverified.** Searched for
any cooldown/grace-period/stabilization/debounce mechanism anywhere in `internal/engines/saturation`,
`internal/engines/pipeline`, and `internal/engines/scalefromzero` — zero hits. `scalefromzero`'s
direct actuation sets no marker the normal engine could use to recognize "this replica just got
bootstrapped" — it doesn't reference `PendingReplicas`/`ReadyReplicas` at all. The only thing that
incidentally helps is the generic `PendingReplicas`-based cascade-prevention (pods not yet Ready
don't count as capacity), but that's a side effect of normal pod-startup timing (~2-7 min), not a
deliberate anti-flap design, and it stops applying the moment the pod is Ready. Once real metrics
start flowing, nothing prevents the normal engine's cost-optimal scale-down from reducing the
variant back toward 0 on the very next cycle if the (now real, measured) numbers suggest spare
capacity — no minimum-age or settling-period gate exists anywhere in this codebase. This is a
genuine, confirmed gap — document as a known limitation, not a blocker to resolve before this
redesign proceeds (the same gap exists today, independent of this refactor).

**Interim recommendation (pending Dean's final confirmation — currently "almost agree," paused to
document before continuing):** rely on the existing `scalefromzero` engine as the near-term answer
for `[TA]`-alone's zero-replica-variant revival rather than trying to make the cost-efficiency
picker trustworthy for zero-replica candidates right now. Document the analyzer-path's fragility
(untrustworthy/possibly-absent PRC estimates without a compatible sibling) as a known limitation to
fix properly later — do not attempt to fix the picker itself as part of this refactor.

## 2.5 TA-side proactive complement — reuse `lastPerReplicaSupply`/`Cost`/`AcceleratorName` as a self-fallback (agreed, 2026-08-04)

Entirely inside `internal/engines/analyzers/throughput/analyzer.go` — orthogonal to the anchor/
binding mechanism, scoped like 1.C4 (TA copying `Cost`/`AcceleratorName` from `ReplicaMetrics`): a
cheap, self-contained TA enhancement, not core anchor-refactor work, but worth bundling in because
it directly answers "make sure a variant that goes to zero can go back up when ONLY TA is enabled"
with a *proactive* path, complementing (not replacing) `scalefromzero`'s *reactive* one.

**The gap, precisely.** `Analyze()`'s only per-variant loop is `for variantName, variantMetrics :=
range byVariant`, where `byVariant := groupByVariant(input.ReplicaMetrics)` (`analyzer.go:262`) — a
variant with 0 replicas contributes 0 rows and is never a key in that map, so the loop body never
runs for it. TA emits nothing for that variant at all, not even an empty entry — confirmed, this is
D1's finding restated at the exact loop level.

**Already has the data and the precedent — just not the read-path.** `variantState` already
persists `lastPerReplicaSupply` (`analyzer.go:50`), set every cycle a per-variant computation
succeeds (`:319-322`), currently read **only** by `VariantState()` for introspection (`:475`),
never consulted by `Analyze()` itself. The exact precedent for "persist a last-good value across
cycles, distinct from workload-shape-dependent state that gets cleared" already exists in the same
struct: `lastFittedB`'s own doc comment (`:37-40`) — "the B coefficient from the most recent
successful Tier-1 OLS fit... because B reflects hardware/model characteristics rather than
workload shape... must NOT clear `lastFittedB`." This proposal applies the same pattern to
`PerReplicaCapacity`.

**The fix — a second loop, added alongside the existing one, over `input.VariantStates` (every
configured variant, live or not — already available to `Analyze()`, the same field sat-v2 uses for
its own all-variants iteration):**

```go
for _, vs := range input.VariantStates {
    if _, alreadyHandled := byVariant[vs.VariantName]; alreadyHandled {
        continue  // has live replicas — the existing loop already covered it
    }
    key := variantKey(input.Namespace, input.ModelID, vs.VariantName)
    prc := 1.0  // baseline, for a variant TA has never seen
    if state, ok := a.variantStates[key]; ok && state.lastPerReplicaSupply > 0 {
        prc = state.lastPerReplicaSupply  // was live before; reuse its last-known value
    }
    // append VariantCapacity{VariantName: vs.VariantName, PerReplicaCapacity: prc, ...}
}
```

**Two properties worth keeping precise, not just asserted:**
- **Time-bounded for free.** `variantState` entries are evicted after `2×DefaultObservationMaxAge`
  (60 min idle) — so `lastPerReplicaSupply` is only trusted for up to an hour after the variant went
  quiet; past that the entry is gone and the fallback degrades to `1` on its own, no extra logic
  needed.
- ~~`1` is a genuinely safe conservative default, not an arbitrary placeholder. With
  `PerReplicaCapacity=1`, `costEfficiency = Cost/1` makes an unknown variant look artificially
  *expensive* relative to any variant with a real (larger) PRC, so it ranks last among
  cost-efficiency picks — never preferred, never permanently excluded either. Once picked even
  once, live measurement takes over on the next cycle and corrects course.~~ **CORRECTED
  (2026-08-04) — this was wrong, and the actual failure mode is more dangerous, not just
  imprecise.**

**Correction — the `Cost` field, not just `PerReplicaCapacity`, needs a fallback, or the ranking
inverts.** `costEfficiency` (`cost_aware_optimizer.go:234-239`) is `vc.Cost / vc.PerReplicaCapacity`
(returning `math.MaxFloat64` only when `PerReplicaCapacity <= 0`). The synthesized entry above sets
`PerReplicaCapacity` but never `Cost` — and **`Cost` would be `0` from every available source**:
TA's own entry never sets it (E1), and — newly confirmed — **sat's anchor fallback doesn't either.**
`aggregateByVariant`'s `variantCost`/`variantAccel` maps (`saturation_v2/analyzer.go:353-360`) are
rebuilt **fresh every `Analyze()` call, from that cycle's `inputMetrics` only** — no persistence, no
capacity-store-derived backfill. For a variant with zero replicas *this cycle*, these maps have no
entry even in sat's own P0-store/compatible-sibling branches, which touch `perReplicaCapacity` but
never revisit `accelerator`/`cost` afterward. So the anchor's `(a)` fallback (sourced from sat) has
this identical gap — a real, previously-unflagged bug in sat-v2 itself, independent of TA or this
refactor. With `Cost=0` and `PerReplicaCapacity>0`, `costEfficiency = 0/PRC = 0.0` — **not**
`math.MaxFloat64` — ranking the variant *cheapest*, ahead of every real, paying-cost variant, every
cycle this holds. That's the opposite bias from what was claimed: artificially attractive, not
artificially unattractive.

**Corrected fix, staying inside the original scoping** (previously-live variants, per "assuming
each variant was initially started with 1 replica" — not variants that have never been observed at
all): extend the same persistence pattern to `Cost`/`AcceleratorName`, not just
`PerReplicaCapacity`. These are the `(a)`-type fields already established as static
("never overwritten" per the design doc), so persisting "last known `Cost`/`AcceleratorName`"
alongside `lastPerReplicaSupply` on `variantState` (same struct, same eviction window) is a natural,
consistent extension — same shape as `lastFittedB`. A genuinely-never-seen variant still has no
fallback for `Cost` either way (out of this fix's scope); the pre-existing, standalone bug in sat's
own `aggregateByVariant` (item worth its own small fix, not part of this refactor) should be
flagged to the planner separately.

**Relationship to the interim recommendation above: complementary, not competing.** `scalefromzero`
is reactive (fires only once EPP queueing is observed). This TA-side extension is proactive — it can
size a previously-live variant back up from `RequiredCapacity` alone, without waiting for a request
to actually queue. Recommend both: `scalefromzero` as the safety net that requires no code change,
this extension (corrected) as the proper proactive fix.

## 2.6 Test requirements for the new plan

The new Type-3 plan must enumerate (per commit) at least these tests. They translate the mechanism
and decisions above into a coder-checkable safety net, and they replace the old plan's §7 test
directions (which were unbuildable at the sites named — see E5).

1. **Merged-anchor construction (non-vacuous).** A pipeline-package fixture with a multi-analyzer
   ballot (sat entry + a distinct binding-analyzer entry for the *same* `VariantName`, with
   deliberately different `(b)` values) asserting the getter's merged anchor takes `(a)` from sat and
   `(b)` from the binding analyzer, per variant. The fixtures must make **anchor ≠ ballot[0]** so the
   classification is proven, not self-satisfied (this is the E5 vacuity trap — the old builder set
   ballot and anchor from the same result).
2. **Per-variant fallback + ordering.** Binding analyzer missing an entry for a variant → the anchor
   falls back to sat's `(b)` for that specific variant; and this fallback runs **before** the
   disabled-entry removal step (assert a case where sat's own entry is non-binding and would be
   pruned, proving the fallback source is captured first).
3. **No stored-result mutation.** Building/merging the anchor must not mutate any analyzer's stored
   result (the E3 aliasing concern) — assert the source sat/TA results are unchanged after the getter
   runs. (The redesign builds fresh per-variant literals, so this should hold by construction; the
   test locks it in.)
4. **Empty / no-live-analyzer ballot is graceful, never a panic.** A model whose ballot has no live
   analyzers produces "do nothing" (no decision), never an index panic (the E4 empty-ballot
   regression) — and `applySaturationDecisions` preserves the prior `Status.DesiredOptimizedAlloc.NumReplicas`
   and still emits the HPA/KEDA scaling metric (decision 2). Assert replicas unchanged + metric
   emitted.
5. **QM-as-error backstop.** Enabling the queueing-model path under the new code produces an explicit
   error (decision 1), not a silent nil-anchor drop and not a silent fallback to the deprecated V1
   engine. A regression test that fails loudly if QM is silently accepted.
6. **Rescale reads the merged anchor.** The rescale path's topology/`RoleCapacities` reads come from
   the single merged anchor (F11) — a test that a TA-binding anchor is what the rescale path sees.
   (The old plan deferred rescale TA-only *correctness* to PR-2; the *read-source* wiring is still
   worth a characterization test here so a later change can't silently repoint it.)
7. **TA-side self-fallback (§2.5), with the Cost/ranking guard.** A previously-live variant now at
   zero → TA emits a `VariantCapacity` whose `PerReplicaCapacity` is the persisted
   `lastPerReplicaSupply` (or the `1` baseline for a never-seen variant) **and** whose
   `Cost`/`AcceleratorName` are persisted — assert `costEfficiency` is *not* the inverted
   `Cost=0 ⇒ 0.0` value that would rank the variant cheapest (the corrected failure mode). Plus the
   eviction-window behavior: after the `2×DefaultObservationMaxAge` (~60 min) idle window the entry
   is gone and the fallback degrades to baseline on its own.
8. **Goldens (#1513) stay green.** The default sat-only path's decision-SET-identity (keyed by
   `VariantName`) is unchanged by the whole refactor — the existing characterization gate is the
   backstop; the new plan must not regress it.

## 2.7 Scope boundaries & deferred items

Explicit fences so the planner's Type-3 plan doesn't over- or under-reach.

**In scope for the new plan:**
- The corrected two-phase mechanism (§2.1): Phase-1 call-every-analyzer + status tagging;
  Phase-2 on-demand getter that finds the binding analyzer, merges the anchor per variant by
  `VariantName`, applies the per-variant fallback, then removes disabled entries. No stored
  `.Anchor` field.
- QM-as-error (§2.3 decision 1).
- Liveness/do-nothing policy reusing `emitSafetyNetMetrics` + the confirmed `applySaturationDecisions`
  last-good persistence (§2.3 decision 2).
- The TA-side proactive complement, corrected to persist `Cost`/`AcceleratorName` alongside
  `lastPerReplicaSupply` (§2.5).

**Under discussion — confirm with Dean before finalizing the plan:**
- The partial-zero interim recommendation (§2.4) — "almost agree," not final. If Dean confirms
  "rely on `scalefromzero` for now," the plan documents the analyzer-path fragility as a known
  limitation and does **not** try to make the cost-efficiency picker trustworthy for zero-replica
  candidates.

**Separate standalone PRs (NOT this plan; independent of it):**
- `AnalyzerName` validation gap — unconstrained `AnalyzerName` + silent `default`→V1 dispatch
  fallback (§2.3 decision 3). Small, standalone, not a 0.9 requirement.
- sat-v2's own `aggregateByVariant` Cost/`AcceleratorName` no-persistence bug (§2.5 correction) —
  pre-existing, present in sat independent of TA or this refactor. Flag to the planner as its own
  small fix.

**Deferred to PR-2 (multi-vote refresh territory — the `ta-anchor-dynamic-refresh` stub):**
- The refresh step (§2.1: re-find the binding analyzer and update `(b)` across cycles when the ballot
  has >1 analyzer).
- Whether the anchor's `ReplicaCount` should track the binding vote rather than sat's `readyCount`
  (F10).
- Rescale TA-only *correctness* (F11) and masked bugs #1/#2/#3/#5.

**Orthogonal / untouched:**
- The `scalefromzero` engine (§2.3 decision 4) — no `Anchor`/`AnalyzerResult`/`pipeline` reference at
  all; the per-variant fallback cannot and does not affect it.
- The flapping / no-cooldown gap (§2.4) — a confirmed, *pre-existing* codebase-wide limitation, not
  introduced by this refactor; documented, not a blocker.

## Status — handoff to the planner (2026-08-04); fact-finding items closed

Dean gave the go-ahead to trigger live, in conversation, immediately after agreeing to the
Cost/AcceleratorName correction above: *"yes and then it is time to handoff to the planner."* The
handoff was written and sent: `session/handoffs/plan__ta-anchor-refactor-mechanism-redesign.md`.
At that point the three fact-finding items below were still open and were carried into the handoff
explicitly as flagged-not-resolved, rather than treated as silently satisfied. All three have since
been checked and closed here, retroactively, so the review doc and the handoff are consistent with
what the planner actually received:

- **e2e-test check for the QM decision** — closed, clean (see item 1 above): no e2e test exercises
  the real QM path.
- **`Status.DesiredOptimizedAlloc.NumReplicas` persistence check** — closed, confirmed safe (see
  item 2 above): `applySaturationDecisions` explicitly re-affirms the last-good value every cycle
  for any VA without a fresh decision; nothing clears it.
- **Flapping-risk check** — closed, but the finding is a confirmed gap, not a clean bill of health
  (see the partial scale-from-zero subsection above): no cooldown/grace-period mechanism exists
  anywhere in this codebase to prevent a freshly-bootstrapped replica from being scaled back down
  once it starts reporting real metrics. Documented as a known, pre-existing limitation — not
  something this redesign introduces or is blocked on fixing.
- **Partial-zero interim recommendation** — still stands as "the near-term answer," now on firmer
  footing given the flapping-risk finding is fully characterized rather than an open unknown.
