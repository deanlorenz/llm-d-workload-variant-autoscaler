# Code review — `ta-anchor-refactor-v2` (PR-1), **incremental: C1–C5** (all coded commits)

Status: DRAFT
Reviewer: internal code-review session (plan-vs-diff)
Scope: branch `ta-anchor-refactor-v2`, commits **C1 `6cea41f2`** (§5 Phase-1 `Enabled` tag),
**C2 `4b820281`** (§6 `bindingAnchor` + per-variant merge + `votingResults` prune + repoint +
fixture migration + QM `Enabled`), **C3 `63a01e27`** (§7a QM-as-error refusal + §7b
liveness/do-nothing), **C4 `4d892cbb`** (§7b TA-side PRC-only scale-from-zero complement), and
**C5 `f6485980`** (§8 dev-guide reframing + two stale engine code-comment corrections; no behavior
change). Base `a2f49ccf` (= goldens tip, off #1513).
Against: FINAL plan `planning/ta-anchor-refactor-v2-plan.md` and the pre-staged checklist
`session/handoffs/review__ta-anchor-refactor-v2-pr1-checklist.md`.

> **This is the per-commit incremental review Dean explicitly requested**, now covering **all five
> coded commits C1–C5**. The coder's C5 handoff states PR-1 is **code-complete but not yet
> push-ready**. What still remains for the **full push-ready round** (when the coder signals via
> `review__ta-anchor-refactor-v2-ready.md`): the **definitive** #1513 golden + Test 9 combine
> characterization run green-after-every-commit **in an isolated worktree** (checklist item 8), and
> the plan §13 checklist walked end-to-end against the final tip. The §9 semantic-pivot grep and the
> named dev-guide sections (checklist item 9) are **done** as part of this C5 increment. All inspection
> here was read-only (`git -C <worktree> show/diff`); no git write-verbs in the coder's active tree.

---

## Verdict (this increment — C1–C5)

**APPROVE against the FINAL plan.** All five coded commits implement the no-stored-field two-phase
mechanism (C1/C2), the QM-as-error refusal + liveness/do-nothing (C3), the TA-side PRC-only
scale-from-zero complement (C4), and the dev-guide/code-comment reframing (C5) as the plan specifies.
**No correctness defects.** The per-commit verdicts and detail live in the increment sections below;
the residual items are all minor or non-code:

- **F1 (C2) — SHOULD-FIX, commit-hygiene, documentation-only** — C2's message misdescribes
  `ResultIsInformative` as new/exported. Reword (no code change); coder defers it to the post-#1513
  rebase-onto-main. **Bundle F3 + F4 (below) into that same reword pass.**
- **F2 (C3) — RESOLVED, no code change** — the "cheap `NumReplicas`-unchanged half" I recommended is
  **infeasible for Test 5's annotation-sourced fixture** (engine persists no CRD status → no VA to
  read; verified `engine.go:1795-1798`/`1594-1596`, `metrics.go:44`). Both halves collapse into the
  fragile package-private gauge; Dean **knowingly relaxed** F2 in favor of the existing distributed
  coverage. See the updated F2 section. Not a blocker.
- **F3 / F4 / F5 (sanitize sweep)** — see the *Sanitize sweep (§4a)* section: **F3** test-comment
  `#1513`/mission leaks (C2), **F4** commit-message schedule/mission/PR leaks (C1+C2) — both should-fix
  prose rewords bundled with F1; **F5** the `(a)/(b)` taxonomy — **DECIDED accept-as-is for PR-1,
  strip-to-plain-prose folded into PR-2**. Plus one *inherited* #1513-goldens-file leak (goldens
  branch's fix, not this branch's).
- **Two benign, justified deviations** — C3's void `refuseQueueingModel` (vs the plan's
  returns-empty signature; identical hold behavior, `unparam`-clean, plan grants the latitude); and
  the C2 fallback matching plan §2 rather than Dean's reopened `Enabled && Live` intent (see D1).
- **O1 verified safe** (no downstream anchor mutation).
- **C5 (dev-guide + comments) — no findings.** Both Type-4 files and both engine code-comment
  corrections are accurate against the C1–C4 code; the §9 semantic-pivot grep is independently
  confirmed clean (zero `saturationEntry` hits); factual claims (60-min self-expiry, the three
  nil-anchor cases, `Reason: "T-sfz"`, the `Cost=0` known-limitation) all verified. Detail in the C5
  increment section.

**Separately, Dean has reopened two plan-level design questions — D1 and D2** (whether the per-variant
(b)-fallback and `votingResults` should gate on `Enabled && Live`, not `Enabled` alone). The code
faithfully matches the *current* plan §2/§6, so these are **not code defects** — they are design
decisions handed to the planner (`session/handoffs/plan__ta-anchor-voting-liveness-gate.md`) that, if
adopted, change plan §2/§6, the merge line, `votingResults`, and Test 2. See D1/D2 below. **They do
not block this code-review verdict**, but should be resolved before the merge/voting lines are
considered final.

### Disposition update (2026-08-06, Dean) — #1513 is not a hard merge-gate

#1513 (`ta-anchor-goldens` @ `a2f49ccf`) is **OPEN, `MERGEABLE`, and fully green** — DCO,
`lint-and-test`, `e2e-tests-full`, `e2e-tests-smoke`, `kustomize-build`, signed-commits all pass;
nothing red or pending. It is a **test-only** characterization gate (+409/−0, one file).

PR-1's branch is based on `a2f49ccf`, so **the goldens already live in PR-1's own tree and pass
green there** (verified C1→C5). Therefore **merging #1513 is not a correctness prerequisite for
PR-1** — it only decides whether the goldens land as a standalone test PR or ride along in PR-1's
diff when PR-1 opens against `main`. Per Dean (2026-08-06): we do **not** wait for #1513 to merge;
we move on.

Consequence for the deferred rewords: F1 (and the bundled F3/F4) were parked "for the post-#1513
rebase-onto-main." That rebase — onto **current** `main` — can now proceed on Dean's schedule
**without** waiting for the merge. It is the same rebase, no longer gated on #1513. If #1513 has
not merged by then, the goldens commit `a2f49ccf` simply rides into PR-1's diff (fine). This
supersedes the "make it dependent / rebase on #1513" framing from earlier the same day.

---

## Findings (most-severe first)

### F1 — SHOULD-FIX (minor, commit-hygiene) — C2 message misdescribes `ResultIsInformative`

C2's commit message lists `ResultIsInformative` under **"New helpers in analyzer_helpers.go:"** and
states it is *"Exported because the saturation engine's liveness gate calls it, keeping the two
informativeness tests from drifting."*

Verified false on the diff:
- `ResultIsInformative` **pre-exists at base `a2f49ccf`** — `internal/engines/pipeline/analyzer_helpers.go:53`, already exported (capital `R`).
- It is **already called at base** — `internal/engines/saturation/engine_v2.go:215`.
- C2's `analyzer_helpers.go` diff **only calls** it (added lines 131 and 140, inside
  `bindingAnchor`'s binder-selection switch). There is **no** `+func ResultIsInformative` hunk and
  no export-changing hunk in C2.

So the helper is neither new nor exported by this commit — `bindingAnchor` merely reuses it. This
violates CONVENTIONS **"Commit messages must reflect the diff — especially after rebase"** (the
load-bearing example being the silently-dropped `Score` field). Severity is minor because the
inaccuracy is in prose, not code — but it is exactly the class of drift the rule targets.

**Recommended fix (coder, before push — `git commit --amend`/reword or during the eventual
rebase):** drop `ResultIsInformative` from the "New helpers" list and reword to reflect reuse, e.g.
> *"`bindingAnchor` reuses the existing exported `ResultIsInformative` for its binder-selection
> test, keeping it consistent with the saturation liveness gate that already calls it."*

No code change required.

---

## Confirmed correct (checklist items in scope for C1+C2)

- **Item 1 — anchor derived, never stored.** `bindingAnchor` builds a **fresh**
  `*domain.AnalyzerResult` and fresh `VariantCapacity` literals per call; no in-place mutation of
  stored ballot `Result`s. The only new struct field is `Enabled bool` on `NamedAnalyzerResult`
  (C1, §5) — that is the planned Phase-1 vote tag, **not** an anchor-storage field; no field added
  to `ModelScalingRequest`. **Test 3** (aliasing guard) mutates the returned anchor and asserts both
  source `Result`s are unchanged. **PASS.**

- **Item 2 — per-variant merge keyed by `VariantName`; (a)/(b) split + recomputed `TotalCapacity`.**
  (a) `AcceleratorName/Cost/Role/ReplicaCount/PendingReplicas` from the saturation carrier; (b)
  `PerReplicaCapacity/Reason/TotalDemand/Utilization` from the binder; `TotalCapacity` recomputed as
  `ReplicaCount × PerReplicaCapacity` (never copied). **Test 1** asserts this field-by-field
  (`TotalCapacity=400` = 2×200) and that sat's `RequiredCapacity=999` does **not** surface. **PASS.**

- **Item 3 (THE correctness item) — fallback enablement-gated; anchor is built from the FULL
  ballot, independent of `votingResults`.** `satEnabled := satNR != nil && satNR.Enabled`; the
  omitted-variant fallback is `else if satEnabled` → sat's own (b); otherwise PRC stays 0.
  **Clarification (my earlier "before the votingResults prune" wording was imprecise):**
  `votingResults` does **not** gate the fallback and there is **no ordering dependency** between
  them. They are two independent functions that happen to read the same `Enabled` bit:
  `votingResults(s)` filters the ballot for the *combine (RC/SC) math* in the optimizers;
  `bindingAnchor(s)` reads the **full, unpruned** ballot and gates the fallback with its own local
  `satEnabled` check. The invariant that matters is that `bindingAnchor` never consumes the pruned
  slice (so a non-voting sat's (a)/topology survives) — verified: every call site passes
  `req.AnalyzerResults` (full), never `votingResults(...)`. **Test 2** exercises the gated fallback
  (sat Enabled+non-Live → v2 → sat PRC=110); **Test 2b** the `[TA]`-only path (sat Enabled:false →
  omitted v2 stays **PRC=0**). Code faithfully matches plan §2 — **but see Open design question D1**,
  where Dean questions whether the gate should be `Enabled && Live` rather than `Enabled` alone.
  **PASS against the plan; D1 is a plan-level design divergence, not a code defect.**

- **Item 4 — binder selection + nil-guards.** Switch: sat binds when `Enabled && Live &&
  ResultIsInformative`; else the sole non-sat `Enabled && Live && Informative` entry; **>1 non-sat
  candidate → nil**; none → nil. Every call site nil-guards: `cost_aware_optimizer.go:48`,
  `greedy_score_optimizer.go:125`/`:159`, and the four rescale return-guards
  (`rescale.go:225`/`modelCurrentGPUs`/`roleCurrentGPUs`/`roleFloorGPUs`) all keep `if anchor == nil`;
  `buildDecisionsWithOptimizer:257` guards with `if anchor != nil`. `rescaleModelDecisions:342` derefs
  `anchor.VariantCapacities` **without** a local guard — but that is a **pure rename of the identical
  pre-existing pattern** (old `satEntry` was equally unguarded there) and the request reaching it has
  already passed the `:225` guard on the same deterministic input, so no new nil-deref surface.
  **PASS.**

- **Item 5 (C2 portion) — binder consults `.Live`.** The switch reads `satNR.Live`; the
  `updateLivenessAndSetLive` setter is unchanged by C1/C2 (still sets `.Live` on all entries incl.
  sat). Full liveness / do-nothing behavior is **C3 (§7 › 7b)** — out of scope here. **PASS (partial).**

- **Item 8 (partial) — goldens / combine identity.** The new
  `optimizer_combine_characterization_test.go` freezes the two-voting-entry `[sat,TA]` decision set
  (keyed by `VariantName`) and is **non-vacuous by construction**: sat-alone → target 3, and the test
  asserts `caTargets["v"] > 3` (actual 5), so dropping the throughput vote from `votingResults` goes
  red. Both optimizers run it. The fixture keeps every variant live so it survives the C4 proactive
  complement (honors the #1513 "withSatEntry-stability" coordination note). **I did not run the full
  suite in the live tree** (read-only discipline); the coder reports gates green through C2, and the
  #1513 saturation-only golden byte-identity is verified green-after-each-commit at the full review
  via an isolated checkout. **PASS on inspection; definitive run deferred to full review.**

- **Item 9 — rename cross-refs.** At the C2 tip: `saturationEntry` = 0 hits, `satEntry` = 0 hits
  (renamed to `satCarrier` in the saturation engine's topology-lookup helpers, with clarifying
  comments). All pipeline **selection** sites route through `bindingAnchor`; all **combine** sites
  (incl. `reclaimRole` at `rescale.go:367`) through `votingResults`. The two residual "first" grep
  hits are benign (an unrelated GreedyBySaturation comment; C1's corrected "appended first purely as
  a code artifact — order not significant" clarifier). **PASS.**

Also verified: C1 `optimizer_interfaces.go` adds the `Enabled` field + accurate docstring and
de-orders the "saturation entry is always first" comment to "order is not significant (see
bindingAnchor / votingResults)"; the `satVotes := len(config.Analyzers) == 0 ||
effectiveEnabled(SaturationAnalyzerName, config)` predicate is correct; the reuse-guard `continue`
is preserved and re-annotated ("Reuse guard, not a decision gate"). C2's QM change adds `Enabled:
true` beside the static `Live: true` (keeps QM binding through C2; the QM-as-error refusal is C3).
Fixture migrations (`withSatEntry`/`withSatEntryV2`/`withQMEntry`/`makeNamed`/`makeNamedPD` and the
greedy multi-analyzer/PD ballots) correctly add `Enabled`+`Live` — necessary because the new
liveness-gated binder requires both, whereas the old name-only `saturationEntry` did not.

---

## C3 increment — `63a01e27` (§7a QM-as-error refusal + §7b liveness/do-nothing)

**Verdict for C3: APPROVE against the FINAL plan, with one NTH coverage note (F2) and one benign,
justified signature deviation.** The QM path is refused loudly and held at last-good replicas with
no silent fall-through to V2/V1 — verified head-on. The liveness/do-nothing behavior is (as the plan
states) mostly pre-existing; the only NEW hold path (bindingAnchor→nil) is documented and tested.
No correctness defect.

### F2 — NTH (minor, test-coverage) — plan Test 4's "assert replicas unchanged + metric emitted" clause is not asserted

Plan §7c **Test 4** requires the empty/no-live-analyzer ballot to produce no decision, *"…
`applySaturationDecisions` preserves the prior `Status.DesiredOptimizedAlloc.NumReplicas`, **and**
still emits the HPA/KEDA scaling metric. **Assert replicas unchanged + metric emitted.**"*

What C3 actually asserts:
- **Test 4A** (`analyzer_helpers_test.go`, `bindingAnchor` unit) — empty ballot → nil; both-enabled +
  informative but not-live → nil; ambiguous two-non-sat → nil. Covers the *no-binder* half.
- **Test 4B** (`optimizer_hold_test.go`, NEW) — both optimizers produce **no decision** (`BeEmpty()`)
  and **never panic** on an unbindable ballot. Covers *no-decision + no-index-panic (the E4
  regression)*. Its own doc-comment concedes the hold-and-emit *"is exercised end-to-end in the
  saturation engine's queueing-model refusal test"* — i.e. relied upon there, **not asserted here**.
- **Test 5** (`engine_test.go`, envtest) — asserts `optimize()` returns nil, the refusal is logged,
  and `mockPromAPI.QueryCallCounts` is **empty** (no V2/V1 fall-through). This is a *stronger*
  no-fall-through proof than the plan asked for — but it **does not assert** `NumReplicas` unchanged
  or the metric emitted either.

So the plan's explicit *"replicas unchanged + metric emitted"* assertion is present in **neither**
test. The hold-and-emit path (`applySaturationDecisions` re-affirming last-good `NumReplicas` + the
per-cycle gauge) is pre-existing and separately covered, so this is **not a correctness gap** — but
it is a literal deviation from the Test 4 spec the plan named.

**Original recommendation (superseded — see resolution):** add a `Status.DesiredOptimizedAlloc.
NumReplicas`-unchanged assertion to Test 5 via a k8s-client VA read (not the package-private gauge).

**RESOLVED — premise corrected + Dean relaxed F2 (2026-08-06).** The coder investigated the "cheap
half" and found it **infeasible for Test 5's fixture**; I independently verified against the code:
- Test 5 lives in the *"multiple VariantAutoscalings"* Context whose `BeforeEach` creates
  Deployments + annotated HPAs only — **no `VariantAutoscaling` CRs**; the variants are
  annotation-sourced (synthesized in-memory from the HPAs).
- For annotation-sourced variants the engine **persists no CRD status** — verified at
  `engine.go:1795-1798` (*"KEDA/HPA reads `wva_desired_replicas` directly. There is no CRD status to
  patch…"*) and `engine.go:1594-1596` (`applySaturationDecisions` works on `*va.DeepCopy()`, never
  written back to the API server). So there is **no VA object to read** after `optimize()` — the
  cheap k8s-read assertion I envisioned cannot exist here.
- The **only** held-replica observable is the package-private `desiredReplicas *prometheus.GaugeVec`
  (verified `metrics.go:44`, lowercase) — exactly the fragile, parallel-Ginkgo-racy half. So both
  halves collapse into one fragile observable for this fixture. (The cheap k8s-read *would* exist for
  a model-sourced / CRD-persisted fixture — likely where the recommendation's premise came from.)

**Dean's disposition:** F2 is **knowingly relaxed** for the annotation-sourced fixture — the
distributed coverage stands (Test 4B no-decision + no-panic; the pre-existing
`applySaturationDecisions` hold tests; Test 5's `optimize()`-nil + empty `QueryCallCounts` +
logged-refusal), and the relaxation of plan Test 4's *"assert replicas unchanged + metric emitted"*
clause is to be recorded in the push-ready sync handoff. **F2 requires no code change and is not a
push blocker.** (Coder investigation: `plan__ta-anchor-v2-f2-premise-correction.md`, routed to the
planner to correct plan §14.1 F2's premise — a plan-doc edit, planner's domain, not mine.)

### Benign deviation (noted, not a finding) — `refuseQueueingModel` is void, not `allDecisions = refuse(…)`

Plan §7a shows `allDecisions = e.refuseQueueingModel(ctx, modelGroups, currentAllocations)`
(returns empty decisions). The code implements a **void** `e.refuseQueueingModel(ctx, modelGroups)`
that only logs; `allDecisions` stays `nil` and the unconditional `applySaturationDecisions` after the
switch holds. **Justified and sound:**
- Behavior is **identical** — empty/nil decisions → same `:571` hold-and-emit.
- The coder's stated reason (a function that always returns an empty slice would trip `unparam`) is
  correct — void is the lint-clean form.
- Plan §7a itself grants this latitude (L576-578): *"returning empty decisions through the existing
  `:571` path already achieves the hold + metric emission — prefer it (less new code)."* The plan
  cares that the hold flows through `:571`, not about the exact return signature.
- Dropping the `currentAllocations` param is correct — the refuse path never uses allocations.

### Confirmed correct (C3)

- **Item 6 — QM refused by explicit error, no silent fall-through.** Dispatch case
  `case domain.QueueingModelAnalyzerName:` now calls `refuseQueueingModel`, which
  `logger.Error(errors.New("queueing-model optimization path is disabled"), "refusing to dispatch the
  queueing-model path; enable the saturation and/or throughput analyzers instead", …)` and returns.
  It does **not** call `optimizeQueueingModel` and does **not** fall through to `optimizeV1`. The
  plan's single semicolon-joined message is split across the error value + log message, but carries
  the required *"refusing to dispatch"* + *"enable the saturation and/or throughput analyzers
  instead"* semantics. Test 5 proves no fall-through via an **empty `QueryCallCounts`** (refuse never
  reaches `prepareModelData`, so no Prometheus query fires). `applySaturationDecisions` after the
  switch is **unconditional** (verified at the C3 tip) → the QM cycle holds each model at last-good
  and emits the metric. The QM-vs-saturation `analyzerName` precedence (*QM ConfigMap presence >
  saturation config analyzerName*) is **PRE-EXISTING** — C3 changes only the QM branch body
  (run→refuse), not the selection, so it does not newly disable saturation. **PASS.**
- **Item 5 (full) — liveness / do-nothing.** As the plan states, mostly pre-existing
  (`optimizeV2`'s per-model `emitSafetyNetMetrics` hold; `applySaturationDecisions` re-affirming
  last-good every cycle). The **only NEW hold path** is Commit 2's `bindingAnchor`→nil → optimizer
  `if anchor == nil { continue }` → `:571` hold; C3 adds **no** new engine.go hold logic beyond that,
  matching plan §7b ("§7 only needs to document it and test it"). Tests 4A/4B document + test it.
  **PASS.**
- **§12 DEFERRED classification present + mechanism sound.** `optimizeQueueingModel`,
  `runQueueingModelAnalysis`, `buildQMConfig` are **retained in-tree** (not deleted); a blank
  reference `var _ = (*Engine).optimizeQueueingModel` keeps the parked subtree reachable so
  staticcheck U1000 does not flag it. Commit message classifies this as *"retained in-tree as a
  deferred design direction."* Matches plan §12 ("DEFERRED, not deprecated; parked until the
  multi-analyzer engine contract can host it — F10 direction"). The formal DEFERRED handoff line to
  the planner (+ the open GitHub-issue question for the QM multi-analyzer contract) rides the eventual
  push-ready sync — flagged in §12 as Dean's call, non-blocking. **PASS.**

Commit message accuracy (per CONVENTIONS): the C3 message matches the diff — void refuse, retained
helpers + blank ref, and the test summary all correspond to actual hunks. No F1-style drift.

---

## C4 increment — `4d892cbb` (§7b TA-side PRC-only scale-from-zero complement)

**Verdict for C4: APPROVE against the FINAL plan — no findings.** C4 implements plan §7b at the
near-patch level the review designed, with the Dean-2026-08-05 correction fully applied (PRC-only;
no cost sentinel; no TA-side cost/accelerator persistence). Two well-scoped tests cover both layers.

### Confirmed correct (C4 / checklist item 7)

- **Emits persisted `lastPerReplicaSupply` (PRC) ONLY.** The new second loop (`analyzer.go`,
  after the `byVariant` loop) appends `domain.VariantCapacity{VariantName, PerReplicaCapacity:
  st.lastPerReplicaSupply, Reason: itlReasonScaleFromZero}` — `Cost`/`AcceleratorName`/`Role`/
  `ReplicaCount`/`TotalCapacity`/`RequiredCapacity` all left at zero value. **Reuses the existing
  `lastPerReplicaSupply` — no new struct field** (matches plan §7b point 1). **PASS.**
- **No `fallbackVariantCost` MAX sentinel; no TA-side `lastCost`/`lastAcceleratorName`.** Grepped the
  whole `internal/` tree at the C4 tip — **zero hits** for all three identifiers. The Dean-2026-08-05
  design correction (remove the sentinel + the persisted cost/accelerator) is fully applied. **PASS.**
- **Never-seen variant emits nothing (PRC=0).** The loop `continue`s on
  `if !ok || st.lastPerReplicaSupply <= 0` — a variant TA never sized (or one whose persisted supply
  is non-positive) produces no row, so its effective PRC stays 0 and it is not proactively selectable
  (the reactive `scalefromzero` engine covers genuine cold-starts). **PASS.**
- **`alreadyLive` guard + full-variant coverage.** The loop skips any variant present in `byVariant`
  (live this cycle — the first loop already emitted its fresh capacity) and iterates
  `input.VariantStates`, which `BuildVariantStates` populates from the **full** VA list (zero-replica
  included), so the complement reaches every configured variant. **PASS.**
- **Self-expiry via entry deletion (not stale retention).** Eviction is
  `delete(a.variantStates, key)` (`analyzer.go:161`) gated on `now.Sub(lastObservedAt) >
  2*DefaultObservationMaxAge` (~60 min idle) — the **whole** `variantState` entry is dropped, so
  post-eviction the `!ok` branch fires and the variant degrades to the never-seen (no-emission) case
  with no extra logic. Test 7's eviction case asserts exactly this. **PASS.**

### Verified correctness property (not a finding — worth recording) — PRC-only row adds ZERO model-level supply

A concern the plan implies but does not spell out: does a PRC-only, `ReplicaCount=0` row inflate the
model-level `TotalAnticipatedSupply`? **It does not.** `SumTotalSupply` and
`SumTotalAnticipatedSupply` (`internal/engines/aggregation/aggregation.go`) are both
`Σ (ReplicaCount[+PendingReplicas]) × PerReplicaCapacity` — with `ReplicaCount=0` and
`PendingReplicas=0`, a scale-from-zero row contributes **0** to both. So the row is a pure
*selectability carrier*: invisible to supply/RC arithmetic, visible only to the picker (which reads
`PerReplicaCapacity` to gauge viability). This is what makes the PRC-only design safe, and it is
correctly relied upon.

### Tests (C4)

- **Test 7** (`analyzer_test.go`, analyzer layer) — (a) previously-live-now-zero → emits a row with
  `PerReplicaCapacity ≈ persisted lastPerReplicaSupply` and `Reason == itlReasonScaleFromZero`, and
  **explicitly asserts** `Cost==0.0`, `AcceleratorName==""`, `Role==""`, `ReplicaCount==0` (TA does
  not set the (a)-identity fields). (b) never-seen → no emission. (c) post-eviction → persisted state
  gone + no emission. Matches plan Test 7 head-on. **PASS.**
- **Test 10** (`optimizer_scale_from_zero_test.go`, NEW, optimizer-selection layer) — `[TA]`-only
  ballot (sat `Enabled:false, Live:false` as the (a)/identity carrier; throughput the sole
  voting+binding analyzer). The previously-live "revived" (TA PRC 12000; sat (a) `Cost 10`, H100) is
  raised above zero; the **strictly cheaper** never-seen "cold" (sat (a) `Cost 5`; TA emits no PRC →
  merged PRC 0) is skipped. Asserts `revived.TargetReplicas > 0` and `cold.TargetReplicas == 0` —
  proving selection by **viability, not cost** (the plan's Test 10 intent). Also correctly exercises
  the `[TA]`-only fallback path (sat `Enabled:false` → no (b)-fallback → cold PRC=0), which Dean
  confirmed correct — so the D1 question does **not** bear on this case. **PASS.**

Commit message accuracy (per CONVENTIONS): the C4 message matches the diff — the second loop, the
PRC-only emission with identity fields unset, the "T-sfz" `Reason`, the reused `lastPerReplicaSupply`,
and both tests all correspond to actual hunks. The `resolveITLModel` docstring update (the old
"future tier-3 scale-from-zero" note repointed to the new complement) is an accurate cross-reference
fix. No F1-style drift.

### C4 known limitation (documented, not gated — confirmed matching the plan)

Under `[TA]`-only, a previously-live-now-zero variant takes its `Cost` from sat's (a), which is **0**
for a zero-replica variant (the pre-existing sat `Cost=0` bug, §12 — *not ours*), so
`costEfficiency = 0/PRC = 0` and it ranks cheapest / is picked eagerly on scale-up. Scale-from-zero
still **functions** (selection is unaffected — only cost-*priority* is); this is the accepted,
documented known limitation (plan §7b / §7c), to be resolved by the separate sat `Cost=0` fix, **not**
by any TA-side cost plug in this PR. Test 10 deliberately hand-sets a non-zero sat (a) `Cost` because
it asserts *selection*, not the cost-priority limitation. Matches the plan — **not a finding.**

---

## C5 increment — `f6485980` (§8 dev-guide reframing + two stale engine code-comment corrections)

**Verdict: APPROVE. No findings.** C5 is docs + code-comments only — zero behavior change (confirmed:
the two `.go` edits touch only comment lines; the diff is `docs/**` + comment hunks). Diff range
`4d892cbb..f6485980`, 4 files, +112/−43. This closes checklist **item 9** (named dev-guide sections +
rename cross-refs) and the §9 semantic-pivot grep.

### Two engine code-comment corrections — both accurate

- **`engine_v2.go` `effectiveEnabled` doc comment.** Old text claimed saturation is *"exempt … before
  `effectiveEnabled` is ever called."* Corrected to: saturation is always appended as the
  identity/(a) carrier, and **whether it votes is decided by `satVotes`, which consults
  `effectiveEnabled` for the saturation name**; the per-analyzer loop's saturation-name skip is a
  reuse guard (avoid double-append), not a decision gate. **Verified accurate** — matches checklist
  item 4 (`satVotes = len(Analyzers)==0 || effectiveEnabled("saturation")`); the old "before it is
  ever called" claim was factually wrong.
- **`engine.go` `analyzersSnapshot` comment.** Dropped the stale *"other analyzers invoked but
  results not consumed yet / combine lands in follow-up PRs"* claim (pre-combine text) → now: each
  enabled analyzer's result is consumed (votes, may bind); iteration order not significant. **Verified
  accurate** against the C1–C4 combine behavior.

### Dev-guide accuracy — verified against code, not against the plan

- **`multi-analyzer-pipeline.md`** — the anchor-merge description (step 7), the nil-anchor
  hold-unchanged case, the liveness-over-`votingResults` reframing, and the QM-refused-and-parked
  paragraph all match the C2/C3 code. Three specific factual claims independently checked:
  - the three **nil-anchor cases** ("empty ballot / no enabled-and-live-and-informative analyzer /
    ambiguous set of binding candidates") map exactly to `bindingAnchor`'s three `return nil` paths
    (`analyzer_helpers.go:151` ambiguous-candidate; `:158` no-binder incl. empty) — **accurate**;
  - the scale-from-zero **`Reason: "T-sfz"`** and PRC-only emission match C4 — **accurate**;
  - the **~60-min self-expiry** matches `DefaultObservationMaxAge = 30*time.Minute` × 2 — **accurate**.
- **`saturation-scaling-config.md`** — the three-config Scope note (default / `[sat,throughput]` /
  `[throughput]`-only) and the "Saturation Always Runs" → "**Saturation as the Identity Carrier**"
  rename match the code; the old "not yet consumed / follow-up PR" scope note is properly retired.
- **`(a)/(b)` notation in Type-4 prose is acceptable** — it is defined inline at pipeline step 7
  ("(a) identity fields … (b) sizing fields") and everywhere else paired with its gloss
  ("(a)/identity", "(b)/sizing"). It is a labeled shorthand carrying its own meaning, **not** an
  opaque plans-branch section identifier — so **no §4a violation**. No `Fnn`/`Ann`/`§`-style
  plans-branch tokens leaked into either doc or the comments (grep-checked).
- **Coder's flagged doc-accuracy call is resolved correctly.** Plan §8 wording said TA emits
  "per-replica capacity / cost / accelerator"; C4 code emits **PRC-only** (Cost/AcceleratorName/Role
  stay saturation's (a) via the merge). The coder documented the code, not the stale plan prose — the
  correct Type-4 discipline, and consistent with the C4-increment finding. This is the same benign
  plan-vs-code deviation noted for C4, resolved in favor of code.

### §9 semantic-pivot grep — independently confirmed clean

Ran `git -C <wt> grep saturationEntry` across `internal/**`, `docs/**`, `cmd/**`: **zero hits**. The
`saturationEntry`→`bindingAnchor` rename left no stale comment/docstring/identifier references — checklist
item 9's rename half is satisfied.

### Deletion/deferred classification (C5 makes it visible)

The dev-guide now states the queueing-model optimize path is "retained but parked; re-enabling it is
a separate follow-up." This surfaces the C3 **DEFERRED** classification in the shipped Type-4 doc —
the generic "separate follow-up" phrasing (no "PR-N" reference) satisfies both the deletion-documentation
rule and the Type-4 "no PR-schedule references" rule.

---

## Checklist verification — both checklists + plan §13, tip `f6485980` (2026-08-06)

Consolidated pass across the **coder quick-checklist** (`ta-anchor-refactor-v2-coder-checklist.md`, 10
items → plan §13), the **reviewer blast-radius checklist**
(`review__ta-anchor-refactor-v2-pr1-checklist.md`, 9 items), and the canonical **plan §13 gate**
(L1047:1074). Static items verified by read-only `git -C <worktree> show/grep` + `Read` against the
coder's tree; test/lint gates run in an **isolated detached worktree I own** (`/tmp`, removed after —
the coder's tree was never touched, no git write-verbs in it). Line refs are the tip.

**Reviewer checklist (9 items) — all PASS:**

| # | Item | Verdict | Evidence |
|---|------|---------|----------|
| 1 | Anchor derived, never stored | ✅ PASS | No `Anchor` field on `NamedAnalyzerResult` (optimizer_interfaces.go:21-45) or `ModelScalingRequest` (:49-56); `bindingAnchor` builds a fresh `*domain.AnalyzerResult` per call (analyzer_helpers.go:124,172,193) — comment L122-123 "never mutates the source Results". |
| 2 | Per-variant merge keyed by `VariantName`, (a)/(b) split | ✅ PASS | (a) AcceleratorName/Cost/Role/ReplicaCount/PendingReplicas from `aCarrier` (:195-202); (b) PerReplicaCapacity/Reason/TotalDemand/Utilization from `binding` via `bByName` (:189-191,203-207); `TotalCapacity` **recomputed** `ReplicaCount×PerReplicaCapacity` (:221), not copied. |
| 3 | Fallback enablement-gated (**V9 correctness gate**) | ✅ PASS — **not a BLOCKER** | Fallback is `else if satEnabled` (:208), `satEnabled := satNR != nil && satNR.Enabled` (:169) — follows §2 (gated), not §6's ungated wording. `[TA]`-only omitted variant → PRC stays 0 (:216-217). No ordering dep on the prune: `bindingAnchor` reads the full ballot `s`; `votingResults` is a separate combine-input filter. |
| 4 | Binding selection + `satVotes` rule | ✅ PASS | Sat binds when `satNR.Enabled && satNR.Live && ResultIsInformative` (:138-140); else sole non-sat enabled+live+informative binds (:141-155); >1 non-sat → nil (:148-151); none → nil (:157-159). `satVotes := len(config.Analyzers)==0 || effectiveEnabled("saturation")` (engine_v2.go:147). |
| 5 | Liveness set on every entry incl. sat; rule reads it | ✅ PASS | `updateLivenessAndSetLive` iterates all `namedResults` (sat is index 0, engine_v2.go:154) setting `.Live` in place (:232-233), "no name-based exemption" (:203-204); rule reads `satNR.Live` / `s[i].Live` (analyzer_helpers.go:138,147). |
| 6 | QM refused by explicit error, no V2 fallthrough | ✅ PASS | Dispatch `case QueueingModelAnalyzerName → e.refuseQueueingModel` (engine.go:554-558); `refuseQueueingModel` logs `logger.Error("queueing-model optimization path is disabled")` + emits no decisions (engine_queueing_model.go:30-40) → models held. **DEFERRED classification present in-code** (L19-29, L42-49). |
| 7 | TA §7b emits PRC only; never-seen → nothing | ✅ PASS | Loop over `input.VariantStates` (analyzer.go:400); `!ok \|\| lastPerReplicaSupply<=0 → continue` (:406-407, never-seen emits nothing); emits `{VariantName, PerReplicaCapacity: lastPerReplicaSupply, Reason: itlReasonScaleFromZero}` only (:409-413); Cost/Accel/Role/ReplicaCount deliberately unset (:393-395). `itlReasonScaleFromZero = "T-sfz"` (constants.go:123). No MAX sentinel, no TA-side lastCost/lastAcceleratorName. |
| 8 | Goldens (#1513) stay green **after every commit** | ✅ PASS (definitive) | Isolated worktree: `go test ./internal/engines/pipeline/...` = `ok` (all 308 specs) at **each** of C1 `6cea41f2` / C2 `4b820281` / C3 `63a01e27` / C4 `4d892cbb` / C5 `f6485980`. Focused run confirms the characterization goldens + combine (Test 9) specs pass. |
| 9 | Rename cross-refs + named dev-guide sections | ✅ PASS | `saturationEntry` grep = **0 hits** tree-wide; both Type-4 files (multi-analyzer-pipeline.md, saturation-scaling-config.md) verified accurate against code in the C5 increment above; two stale engine comments corrected. |

**Plan §13 gate (12 checkbox items) — all satisfied.** Beyond the 9 above (which cover Enabled+satVotes,
fresh-literals+fallback, TotalCapacity recompute, selection-via-`bindingAnchor` + combine-via-`votingResults`,
QM-Error+hold, TA-PRC-only+eviction, goldens, grep, dev-guide), the remaining §13 items are the gate battery,
verified in the isolated worktree at tip `f6485980`:

- **gofmt** `./internal/... ./cmd/...` — clean (`pkg/` is absent past this tip, matching the known dir change).
- **`make test` / full tree** `go test ./internal/... ./cmd/...` — **0 FAIL**, every package `ok`
  (throughput, saturation, pipeline, scalefromzero, controller, all others).
- **`make lint`** (golangci-lint 2.8.0) — **0 issues**.
- **`go build ./...`** — clean.
- Empty-ballot no-panic / NumReplicas / metric: covered by C3 Test 4B (no-decision + no-panic) — see F2 for
  the one unasserted NTH sub-clause (metric + replicas-unchanged), non-blocking.
- Fixture 3 builders + DCO sign-off + branch: DCO/branch are push-gate items the coder confirms at
  push-ready; commits are on `ta-anchor-refactor-v2` (verified) — DCO trailer check belongs to the final
  push-ready battery.

**Coder quick-checklist (10 items)** is a TOC-indexed view onto the same plan sections (§5/§6/§7a/§7b/§8/§9/§13);
every item maps onto a reviewer-checklist row or §13 gate row above and carries the same ✅.

**Net:** both checklists **PASS** at tip `f6485980`. The single flagged correctness item (reviewer #3 / V9
enablement-gated fallback) is confirmed **correctly gated** (§2, not the ungated §6 wording) — **not the
BLOCKER the checklist warned about.** Residual items F1 (C2 commit-message hygiene, prose-only) and F2 (C3
NTH test sub-clause) remain non-blocking; D1/D2 are plan-level design questions with the planner, not code
defects.

---

## Out of scope for this increment (now essentially closed)

C5 closed the two doc items (item 9 dev-guide + §9 grep). This verification pass closed the last deferred
gate (**item 8 definitive** — goldens green after every commit, run in isolation above). What remains is
**not review work** — it is coder push-prep:

- **Push-ready sync handoff** must carry the formal DEFERRED/DEPRECATED classifications (QM path DEFERRED
  §12) — the coder writes this on Dean's OK; the classification is already visible in-code (item 6 evidence).
- **DCO sign-off** verification on all five commits + the origin push are push-gate steps, done at push time.

A separate full push-ready review round is no longer strictly needed for correctness (this pass covered it);
it fires only if the coder rebases onto `main` post-#1513-merge and the diff materially changes.

---

## Open design question raised by Dean (2026-08-05)

### D1 — should the per-variant (b)-fallback gate on `Enabled && Live`, not `Enabled` alone?

**What the code does (verified against the full `bindingAnchor` body).** Terminology first, since it
is easy to conflate: `bindingAnchor` is the **function**; the **binding analyzer** (`binding`) is the
ballot entry selected to supply (b) sizing; the **anchor** is the fresh merged `*domain.AnalyzerResult`
returned. Three distinct things.

- **Binder selection is already `Enabled && Live && Informative`** for both branches (sat, and the
  sole non-sat) — this matches Dean's *"binding analyzer should only be picked from alive and
  enabled."* ✅
- **The per-variant fallback gates on `Enabled` only** (`satEnabled := satNR != nil && satNR.Enabled`),
  **not Live.** Consequences, enumerated over the only case where the fallback can fire (a **non-sat**
  analyzer binds and omits a variant that sat's (a) list contains):
  - sat **Enabled + not-Live** (stale `[sat,TA]`, TA binds): current code **falls back to sat's stale
    (b)**. → **Diverges from Dean's** *"values … used by the optimizer only if enabled AND live."*
  - sat **Live + not-Enabled** (Dean's *"live but non-enabled sat if TA is alive"*): `satEnabled`
    is false → **no fallback** → PRC=0. → **Already matches Dean's intent.** ✅
  - sat **not-Enabled** (`[TA]`-only, Test 2b): no fallback → PRC=0. Matches.

So the **only** behavioral gap between the code and Dean's stated model is the **Enabled-but-stale**
case: the code trusts a stale-but-enabled sat's (b); Dean wants (b) used only from an
**enabled *and* live** source. The one-line change is to gate the fallback on
`satNR.Enabled && satNR.Live`. **Impact:** flips **Test 2**'s assertion (v2 would become PRC=0 instead
of 110) and requires a plan §2 wording update and a test rewrite.

**This is a code-matches-plan situation, not a code defect.** The FINAL plan §2 specifies the
Enabled-only gate; the coder implemented it faithfully. Changing it is a **plan/design decision** — the
planner's domain (I will not edit the plan; the coder must not infer it from this review). Options for
Dean:
1. **Adopt `Enabled && Live` fallback gate** (closes the stale-sat case; rewrites Test 2 + plan §2).
2. **Keep `Enabled`-only** (current plan) and accept stale-but-enabled sat as a fallback source.
3. **Broader model** — Dean's *"there should always be fallback (b) values, preferably to/from all
   analyzers."* That is upstream of the merge (how each analyzer populates its result for every
   variant) and interacts with the C4 TA-PRC-only work; it is bigger than a gate tweak and, if
   pursued, belongs in a design-doc/plan revision rather than PR-1.

**Routing:** once Dean picks (1) or (3), it needs a `plan__` handoff to the planner to update plan §2
(and, for (3), the design doc) before the coder touches the merge/tests. Recorded here so the decision
is not lost.

### D2 — should `votingResults` gate `Enabled && Live` (not `Enabled` alone)? (2026-08-05, verified)

Dean's principle: *"voting math should only be live+enabled. live was added to prevent veto of a dead
analyzer — this is important."* My initial framing was **half-wrong**; corrected picture, verified
against C2 tip `4b820281` and base `a2f49ccf`:

- **`votingResults(s)` (NEW in C2, `analyzer_helpers.go:234`) filters the combine input on `Enabled`
  ONLY, not `Live`.** Base passed the **full ballot** (`req.AnalyzerResults`, no filter) to
  `initRoleState`; the refactor **added an `Enabled` filter but no `Live` filter**. (`bindingAnchor`
  deliberately still reads the FULL ballot — correct, keep it.)
- **Scale-DOWN veto/removal is ALREADY Live-gated** — `needsScaleDownForRole` and
  `safeRemovalReplicasForRole` **pre-exist at base** (base:301 / base:246), both `if !e.Live
  { continue }` at point of use, and **C2 left them untouched**. So a dead-but-enabled analyzer
  **already cannot veto a scale-down**; empty-live → no scale-down (safety floor). **Dean's "critical"
  concern is already structurally met on the scale-down side.** ✅
- **Scale-UP is NOT Live-gated** — `initRoleState`→`pickerState[i][role]=RequiredCapacity`,
  `anyRoleNeedsScaleUp`, `roleBottleneckReplicas`, `roleAggRemaining` (all pre-existing) act on every
  voting entry with no `.Live` check. A dead-but-enabled entry whose retained `Result` carries RC>0
  **would force a scale-up**. Safety here rests entirely on the external invariant *"dead analyzer →
  RC=0"* — a ballot-construction property tied to the not-yet-landed **C3** liveness/do-nothing work,
  not enforced in the combine. (Dean invoked exactly this invariant: *"force case is empty, dead
  analyzers don't create RC."*)

**So the principle is only half-enforced today:** veto (down) enforced at point-of-use; force (up)
relies on an unenforced invariant. **Clean fix (planner's call):** gate `votingResults` on
`Enabled && Live` — centralizes the invariant for both directions, makes scale-up robust independent
of "dead→RC=0", and demotes the point-of-use `!e.Live` gates to belt-and-suspenders. Caveats: keep
`bindingAnchor` on the FULL ballot; handle empty-voting (no live+enabled) as "do nothing"; goldens
#1513 (sat-only, sat-Live) unaffected.

**This is not a code defect** (code matches the current plan, and the veto path is safe) — it is the
plan-level design decision Dean directed be surfaced to the planner, together with D1. Same `plan__`
handoff.

## Observations (not findings)

- **O1 — VERIFIED SAFE — no downstream mutation of the anchor.** `bindingAnchor` copies
  `binding.Result.RoleCapacities` (a `map`) by reference into the fresh anchor (all other fields are
  scalar copies or freshly-built `VariantCapacity` literals). I grepped the whole pipeline package
  (non-test): **`.RoleCapacities` is never written** (no `RoleCapacities[..] =`, no `.RoleCapacities =`,
  no `delete`), and the only `anchor.X =` write is inside `bindingAnchor` itself
  (`analyzer_helpers.go:224`, assigning the fresh `merged` slice). All 10 call sites read the anchor
  only. Test 3 additionally proves the `VariantCapacity` literals don't alias. So the map alias is
  benign **today by verification**, not just by assumption. Only risk is a *future* writer of
  `anchor.RoleCapacities`; a one-line copy there (or a guard test) would make it robust to that.

---

## Sanitize sweep (§4a) + dev-doc correctness re-check (2026-08-06, tip `f6485980`)

Dean asked for a dedicated pass: (i) §4a — plans-branch / PR-schedule / plan-section terms that
leaked into code-side artifacts (comments, docstrings, identifiers, dev-guide, test descriptions,
commit messages); (ii) re-confirm the Type-4 dev-guides were updated correctly. Scope of the scan:
the full `a2f49ccf..f6485980` (C1–C5) diff — 13 production files, 10 test files, 2 dev-guides, 5
commit messages. **These are findings for the coder to fix; the reviewer does not edit code.**

### Production code — CLEAN of hard tokens ✅ (one taxonomy caveat: see F5)
Every added non-test `.go` comment/identifier was scanned for `#1NNN`, `planning/`, `-plan.md`,
`PR N`, `Phase N`, `Commit N`, `anchor refactor`, `ship gate`, `§`, plan-section IDs (`F#`/`V#`/`D#`).
**Zero hits.** New identifiers (`bindingAnchor`, `refuseQueueingModel`, `itlReasonScaleFromZero="T-sfz"`)
are descriptive prose, no plans-branch shorthand. `T1-ols`/`T2-default`/`T-sfz` Reason strings are
legitimate code data (not plan tokens). **Caveat (corrects an earlier over-claim):** this token scan
did NOT cover the `(a)/(b)` field taxonomy, which IS plan-inherited notation and appears pervasively
in production comments, test comments, and both dev-guides — see **F5** for the full assessment.

### F5 — JUDGMENT CALL (Dean's fork), §4a-borderline — the `(a)/(b)` field taxonomy
The plan (`ta-anchor-refactor-v2-plan.md`) labels the anchor-merge field groups "(a)" (identity) and
"(b)" (sizing). That lettering flows through the code: `analyzer_helpers.go` (~16 comment lines),
`optimizer_interfaces.go`, `engine.go`, `engine_v2.go`, `engine_queueing_model.go`; test comments in
`analyzer_helpers_test.go` (~20) and `optimizer_scale_from_zero_test.go`; and both dev-guides.

**Is it a §4a leak?** Borderline, and it turns on self-containment:
- **Argument it is NOT a leak (why it's defensible as-is):** the code *defines the taxonomy at its
  primary site* — `bindingAnchor`'s doc comment (`analyzer_helpers.go:87–97`) enumerates exactly which
  fields are `identity/(a)` (`AcceleratorName, Cost, Role, ReplicaCount, PendingReplicas`; model-level
  `ModelID, Namespace, AnalyzedAt`) and which are `sizing/(b)` (`PerReplicaCapacity, Reason, TotalDemand,
  Utilization`; model-level `TotalSupply, …`). Every subsequent use pairs the letter with its word
  (`identity/(a)`, `sizing/(b)`, `(a) carrier`). The dev-guides gloss inline the same way
  (`(a)/identity fields (Cost, AcceleratorName, Role)`). A merged-code reader who reads `bindingAnchor`
  resolves the notation without ever opening the plan — functionally identical to naming two field
  groups "group A / group B" and defining them once. Under that reading it is **not** a §4a violation.
- **Argument it IS a soft leak (why it's worth reconsidering):** the letters coincide with the plan's
  notation and carry **no meaning independent of the paired word** — "identity fields" and "sizing
  fields" read identically without "(a)"/"(b)", and dropping the letters removes any appearance of
  referencing an external lettered list. §4a's spirit is "a token that means nothing to a merged-code
  reader → replace with prose"; the bare letters are exactly such redundant residue.

**This is Dean's fork** (a notation/naming decision — per doc-accuracy discipline, forks belong to
Dean, not the reviewer or coder). Options, in ascending churn:
1. **Accept as-is** — defensible; the taxonomy is code-defined and glossed everywhere. Zero churn.
2. **Keep letters, ensure one explicit legend per artifact** — already effectively true (code:
   `bindingAnchor` doc comment; dev-guides: inline glosses). Near-zero churn; maybe tighten the two
   dev-guides to state the legend once up front rather than re-gloss.
3. **Strip the bare letters, keep the words** — `identity fields` / `sizing fields`, `identity carrier`,
   `sizing binder`, `sizing fallback`. Cleanest §4a posture; mechanical find/replace across ~5
   production files, 2 test files, 2 dev-guides. A coder task, not the reviewer's.

Not a correctness defect and not a hard leak — recorded as a should-decide so it isn't silently shipped
as "clean." My recommendation: acceptable as-is (option 1/2) because the code self-defines it; escalate
to option 3 only if you want zero plan-inherited notation in shipped code.

**DECIDED (Dean, 2026-08-06): option 1 for PR-1 — accept the `(a)/(b)` taxonomy as-is; ships unchanged.
Option 3 (strip bare letters → plain "identity/sizing" prose across production comments, tests, and both
dev-guides) is folded into PR-2 (`ta-anchor-dynamic-refresh`).** F5 is therefore **not** a PR-1 finding.
The PR-2 cleanup item is handed to the planner via `plan__ta-anchor-ab-notation-cleanup-pr2.md` so it
lands in the PR-2 plan stub and isn't lost.

### F3 — SHOULD-FIX, §4a, test-comment leak (introduced by C2) — `optimizer_combine_characterization_test.go`
The C2-added file header comment (L3–L20) leaks PR-number and mission-schedule terms invisible to a
merged-code reader:
- L3 `// Anchor-refactor combine characterization golden …` — mission name.
- L5 `// The #1513 goldens (optimizer_characterization_test.go) …` — PR number.
- L9 `// … same shape as the #1513 goldens …` — PR number.
- L10 `// anchor refactor's combine arithmetic …` — mission name.
- L14 `// … the same method used for the #1513 goldens …` — PR number.
- L19 `// … the later throughput-side proactive-capacity complement …` — commit-schedule ref.
- (softer) L15–16 `// the refactor changed …` / `// the design's single-vote-equivalence invariant …`
  — reword to self-contained prose (e.g. reference "the sibling single-analyzer golden file
  `optimizer_characterization_test.go`" instead of "#1513 goldens"; "the two-phase combine behavior on
  `main@9906dac5`" instead of "anchor refactor"). Keep the concrete `main@9906dac5` anchor SHA — that
  *is* meaningful to a code reader.

### F4 — SHOULD-FIX, §4a, commit-message leaks (C1, C2) — permanent code-side history
Per §4a, commit messages are code-side history. Two carry leaks:
- **C1 `6cea41f2`** — subject `… (Phase 1 of anchor refactor)` (mission name); body `votingResults
  (a later commit) prunes …` (commit-schedule ref); body `The #1513 characterization …` (PR number).
- **C2 `4b820281`** — subject `… (Phase 2 of anchor refactor)` (mission name); body `… the later
  proactive-capacity complement stays a no-op …` (commit-schedule ref).
- C3 / C4 / C5 messages are clean.

Reword to describe the *mechanism* not the *plan schedule* — "the two-phase anchor mechanism; this
commit adds the Enabled tag" is fine (the mechanism genuinely has two phases); "Phase 1 of anchor
refactor", "a later commit", "#1513" are not. Practical note: **bundle F4 with the F1 reword** — the
coder is already amending a commit message (F1), so all commit-message hygiene lands together. If PR-1
is squash-merged the individual messages are discarded and F4 self-resolves; if rebase-merged they
persist and F4 must be fixed. (Applies regardless: fix now, cheap.)

### Inherited (NOT introduced by this branch) — `optimizer_characterization_test.go` (the #1513 goldens)
This file is **at base `a2f49ccf`, unchanged by C1–C5** — it is the #1513 characterization goldens
that ride in when PR #1513 merges. Its header comment leaks too (`invariant #7 of the anchor
refactor`; `rides unchanged onto the anchor-refactor branch as its ship gate`). **Provenance: PR #1513,
not `ta-anchor-refactor-v2`.** The fix belongs on the `ta-anchor-goldens` branch (or Dean accepts it);
recording here only so the merged-code leak is tracked. Not a finding against this branch's diff.

### Dev-doc correctness — RE-CONFIRMED ✅
Both Type-4 files re-verified at tip against the C1–C5 code (fresh pass, not relying on the C5
increment review):
- **`multi-analyzer-pipeline.md`** (C5 +97): every claim checked against code — sat always-run/(a)-carrier
  (`engine_v2.go` unconditional prepend, `Enabled: satVotes`); vote opt-in (`satVotes = len(Analyzers)==0
  || effectiveEnabled(...)`); `votingResults` prune; on-demand `bindingAnchor` per-variant merge with
  (a)-from-sat / (b)-from-binder; three nil-anchor cases (empty ballot / none enabled-live-informative /
  ambiguous >1) map to `bindingAnchor`'s `return nil`s; `Reason:"T-sfz"` PRC-only fallback; never-seen →
  PRC=0 not selectable; ~60-min self-expiry (`DefaultObservationMaxAge 30m`×2); QM refusal + parked path;
  `Cost=0` zero-replica known-limitation framed as pre-existing saturation behavior, out of scope. **All
  accurate.**
- **`saturation-scaling-config.md`** (C5 +43): three-config scope note (default / `[sat,thpt]` /
  `[thpt]`-only) matches the binder rule; "always runs, voting is opt-in" matches; `interfaces.Saturation
  AnalyzerName` is a real identifier. **Accurate.**
- **No forward-looking / pending-PR content** in either file (scanned for `pending PR`/`will be`/`future
  PR`/`once … lands`/`TODO` — zero hits). Reflects current code only, per Type-4 discipline.
- **§4a-clean:** the `(a)/(b)` notation is glossed inline ("(a)/identity fields (Cost, AcceleratorName,
  Role)", "(b)/sizing fields (PerReplicaCapacity, demand)") so both docs read standalone; the only `#NNNN`
  / `V1`/`V2` / "Phase 1" tokens are legitimate public upstream references (ScalingPolicy proposal #1245,
  quota-caps #1003) and engine-version labels — not plans-branch or mission terms.

### Net
Production code + dev-guides: correct, no forward-looking content, no hard-token leaks. Three
items for the coder / Dean: **F3** (test-comment `#1513`/mission leaks, introduced by C2 — should-fix),
**F4** (commit-message schedule/mission/PR leaks in C1+C2 — should-fix, bundle with the F1 amend),
and **F5** (the `(a)/(b)` field taxonomy — **DECIDED: accept as-is for PR-1; strip-to-plain-prose folded
into PR-2**, so not a PR-1 finding). F3/F4 are cheap prose rewords with no behavior change. One further
**inherited** leak sits in the #1513 goldens file (fix on the goldens branch or accept). No correctness
or design findings.

---

## Provenance

Reverse-read of C1 (`6cea41f2`) and C2 (`4b820281`) diffs against plan §2/§5/§6/§10/§13 and the
pre-staged blast-radius checklist. Findings ranked by blast radius. This doc is the incremental
companion to the plan-review `planning/ta-anchor-refactor-review.md`; it will be extended (or a full
`*-code-review.md` verdict appended) when C3–C5 land and the coder signals push-ready.

---

## Definitive push-ready review (post-rebase, tip `075a208e`) — 2026-08-06

**Trigger:** `session/handoffs/review__ta-anchor-refactor-v2-ready.md` (`reason: PR-1 rebased; tip
moved`). The coder rebased the 5-commit stack onto **current** `upstream/main` (`aadaa596`, #1509;
merge-base was `9906dac5`), producing a 10-commit stack (5 characterization goldens + C1–C5) at new
tip `075a208e`. #1513 is still unmerged, so the goldens ride into PR-1's diff — expected per the
2026-08-06 disposition, not a defect.

**Scope of THIS pass is git-/read-verifiable only.** Per Dean (2026-08-06), the coder's post-rebase
test/lint/build battery is **not re-run here** — those rows are accepted from the coder's documented
results (`session/status/ta-anchor-refactor-v2.md` § Rebase + § Verified). The isolated-worktree run
recorded in the *Checklist verification* section above was against the **pre-rebase** tip `f6485980`;
since the C1–C5 code is **byte-identical across the rebase** (proven below), those green results carry
forward to the post-rebase stack unchanged.

**Verdict: APPROVE — push-ready.** No new findings. All prior-increment verdicts (C1–C5 APPROVE, no
correctness defects) stand; the rebase introduced no code change to the stack beyond the intended F3
rewrap and the 3 files genuinely new on the #1509 base.

### Rebase integrity — PASS (no silent hunk loss)

`git diff --stat pre-rebase-f6485980 075a208e` = exactly **4 files**:

| File | Δ | Provenance |
|---|---|---|
| `cmd/main.go` | +42 | #1509 (`aadaa596`, new on base) |
| `internal/utils/crd/watcher.go` | +94 (new) | #1509 |
| `internal/utils/crd/watcher_test.go` | +166 (new) | #1509 |
| `internal/engines/pipeline/optimizer_combine_characterization_test.go` | 12 (6 ins/6 del) | **F3 comment rewrap** (intended) |

306 ins / 8 del total. The **other 22 C1–C5 stack files + all 5 goldens are byte-identical** across the
rebase. This satisfies the CONVENTIONS "Score field silently dropped during cross-rebase" discipline:
the only content delta is (a) the 3 files genuinely new on the #1509 base and (b) the one intended F3
rewrap. Merge-base = `upstream/main` tip `aadaa596` → clean linear rebase, no divergence. Recovery tags
`pre-rebase-f6485980` and `post-rebase-clean` both present.

### DCO — PASS

All 10 commits (`aadaa596..HEAD`) carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Zero missing.

### Deferred rewords F1 / F3 / F4 — APPLIED in the rebase, verified

- **F1 (C2 commit message) — APPLIED.** C2 `a0795e36` now reads: *"bindingAnchor's binder-selection
  test reuses the existing exported ResultIsInformative (added earlier for the saturation engine's
  liveness gate) rather than introducing a second informativeness check."* — the exact recommended
  reword; `ResultIsInformative` is correctly described as **reused/pre-existing**, no longer as
  new/exported. The prior misdescription (the F1 defect) is gone.
- **F3 (combine-test header §4a strip) — APPLIED.** Header comment
  (`optimizer_combine_characterization_test.go` L3–L21) now reads "Two-analyzer combine
  characterization golden" / "single-analyzer goldens" — the `#1513` PR numbers and the "anchor
  refactor" mission token are stripped from the **comment**; the meaningful `main@9906dac5` anchor SHA
  is retained. **Residual (Dean-accepted 2026-08-06, outside F3's scope):** the `Describe(...)` string
  at L32 still reads "Anchor refactor combine characterization goldens" — accepted as descriptive
  prose, not a PR/plans identifier.
- **F4 (C1/C2 commit-message §4a strip) — APPLIED.** C1 `387d69ac` and C2 `a0795e36` subjects are
  clean; the mission-name schedule tokens ("Phase N of anchor refactor") and PR numbers (`#1513`) are
  removed from both bodies. What remains — "Phase 1 of the two-phase anchor mechanism", "votingResults
  (a later commit)", "the later proactive-capacity complement" — is **mechanism-descriptive within-PR
  prose**, exactly the form F4 blessed ("describe the mechanism, not the plan schedule"); the mechanism
  genuinely has two phases and these are not plans-branch/PR-schedule identifiers. **F4 is satisfied.**

### §4a — PR-1's own production code CLEAN

Hard-token scan (`#1NNN`, `planning/`, `-plan.md`, `-review.md`, `PR-N`, `Phase N`, `Commit N`, `ship
gate`, `§`, `F#`/`V#`/`D#`) across **added lines** of all 11 touched production `.go` files
(`aadaa596..HEAD`): **zero hits** (the `T1-ols`/`T2-default`/`T-sfz` Reason strings and `V1`/`V2`
engine-version labels are legitimate code data, excluded). Consistent with the C5-increment §4a sweep.
The `(a)/(b)` taxonomy is the Dean-decided accept-as-is (F5, PR-1) / strip-in-PR-2 item — not
re-litigated.

**Two pre-existing pointers confirmed NOT PR-1 regressions** (on unchanged lines, absent from the
added-line scan): `// Design § Architecture/D:` in `analyzer_helpers.go` (introduced by #1246
`09e1c386`) and `TA-supply.md §3.1` in `throughput/constants.go` (introduced by #1250 `efca1b4c`).
Both byte-identical at the base — inherited, not this PR's to fix.

**Inherited #1513-goldens §4a tokens now ride in PR-1's diff.** Because the coder rebased onto current
`main` **before** #1513 merged, the 5 goldens commits are folded into PR-1's own 10-commit history. The
goldens file `optimizer_characterization_test.go` carries its own header tokens ("invariant #7 of the
anchor refactor", "ship gate", "Commit 2/3/4" Describe labels) — **provenance #1513, not
`ta-anchor-refactor-v2`**. PR-1 must **not** rewrite those commits (it would diverge from
`origin/ta-anchor-goldens`). Disposition for Dean: either they land as-is when the goldens ride into
PR-1's diff, or #1513 merges first as a standalone test PR and the tokens stay a goldens-branch concern.
Neither blocks PR-1.

### Test / lint / build gates — accepted from the coder's documented battery (not re-run this window)

Per Dean's instruction, not re-executed here. The coder documents (status file, post-rebase): per-commit
goldens + Test 9 combine characterization green C1→C5 (`-count=1`); `gofmt` clean; `go build ./...`
clean; `make lint` 0 issues; `make test` all-green including the upstream-changed `internal/utils/crd`;
§9 semantic-pivot grep zero stale hits; §10 backstop clean; plan §13 checklist all rows pass. The
static/structural rows of the 9-item reviewer checklist + §13 were independently walked at pre-rebase
tip `f6485980` (recorded above, all PASS) and carry forward unchanged to `075a208e` on the
byte-identical C1–C5 code.

### Residual items for Dean (none blocking the push-ready verdict)

1. **Origin push** `git push -u origin ta-anchor-refactor-v2` — awaits Dean's OK (matching-origin
   convention). Not a review blocker.
2. **#1513-owned goldens §4a tokens** now exposed in PR-1's diff — Dean's disposition (accept, or merge
   #1513 first). Coder must not rewrite the goldens commits.
3. **Push-ready `sync__` handoff** carrying the DEFERRED (QM optimize path, §12) / DEPRECATED
   (`saturationEntry` getter) classifications + the F1-done / F2-relaxed records — the coder writes this
   on Dean's OK.
4. **Open plan-level design questions D1/D2** (voting/fallback `Enabled && Live` gating) remain with the
   planner (`plan__ta-anchor-voting-liveness-gate.md`) — not code defects, do not block this verdict.
