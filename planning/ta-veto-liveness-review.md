# ta-veto-liveness — Internal Code Review (PR D)

**Status:** DRAFT
**Reviewer session:** internal plan-vs-diff review (not `/code-review`; nothing posted to GitHub)
**Branch:** `ta-veto-liveness` @ `7e931ccf`, off `main@f5b7577c`
**Commits reviewed (round 1):** `785b5350` (state), `77be65ca` (gate), `b3b7f762` (dev-guide)
**Commits reviewed (round 2, follow-ups):** `2b0c715c` (F-B1 QM static-live + test), `5fd0a958` (F-T1a test discriminates), `7e931ccf` (F-T1b/F-Demand/F-NTH/F-Conc doc+comment)
**Plan:** [`planning/ta-veto-liveness-plan.md`](ta-veto-liveness-plan.md)
**Gates (per coder status):** make test / gofmt / lint / build / -race all green.

> **Round-2 outcome (2026-07-27): APPROVE — all six locked follow-ups (F-B1, F-T1a, F-T1b,
> F-Conc, F-Demand, F-NTH) correctly applied; no new findings; push-ready pending Dean.** See
> [§ Round-2 review](#round-2) immediately below. The round-1 sections that follow are retained
> as the finding history that drove the fixes.

---

## Verdict

Three findings, all with decisions/routing recorded (see each section):

- **B1 (blocking, coder fix):** the queueing-model optimize path reuses the shared optimizer
  (it labels its result as the `"saturation"` entry) but never sets `Live`, so the new
  safety floor silently disables QM scale-down. **Decision: option (b)** — set `Live: true`
  statically on the QM path this PR; QM liveness is deferred to the future QM-into-framework
  work. Coder fix + a QM scale-down test.
- **T1b (medium, plan-level → planner):** the PR derives liveness from saturation's *domain*
  reasons (`no-data`/`error`) rather than from a uniform engine-level error/missing/broken
  signal (which already exists via nil-result exclusion). Under Dean's (a)/(b) model,
  `no-data` is a logical omit, not a liveness failure. This diverges from the *plan's*
  framing, not the coder's execution — routed to the planner to reconcile.
- **T1a (medium, test):** the "scopes liveness per model" test does not actually exercise
  per-tuple keying (its model-a result is informative and writes its own entry, so it passes
  under a buggy name-only map too). Needs a non-informative model-a result to discriminate.
- **Concurrency (verified safe):** the new `lastGoodAnalysis` map is safe under the current
  single-goroutine `PollingExecutor`; same single-writer assumption the engine already
  relies on. **Decision: comment only, no lock.**

The core mechanics — the `Live` field, the two gated helpers, the safety floor, per-tuple
keying, the fixture updates, the dev-guide — are implemented cleanly. The V2 path is
correctly instrumented. T1b is the substantive one: it's about *which layer* liveness should
live at, and it's a design call the plan needs to settle before this lands.

**On Dean's B1 premise ("QM is not integrated; leave its path untouched"):** the second half
is right — the coder correctly did **not** touch any QM code (`engine_queueing_model.go` is
byte-identical to `main`). The first half is contradicted by the code: QM *is* wired into
the shared optimizer (labels its result `"saturation"`, calls `e.optimizer.Optimize`;
evidence in B1). So the veto change collaterally affects QM through the shared helper even
though no QM code changed — which is exactly why the static `Live: true` fix (option b) is
needed to restore QM's prior behaviour.

---

## Round-2 review — follow-ups verified (2026-07-27) {#round-2}

Three follow-up commits on top of the round-1 tip, verified against the plan's locked
[§ Review follow-ups](ta-veto-liveness-plan.md) decisions. **All six items match their locked
decision. No new findings. APPROVE, push-ready pending Dean.**

| Item | Locked decision | Delta | Verdict |
|---|---|---|---|
| **F-B1** (code+test) | static `Live: true` on QM path; no other QM code; add QM scale-down test | `engine_queueing_model.go` +6 lines only (the `Live: true` field + a prose comment, no plans-branch ids) — QM file is otherwise byte-identical to `main`. New `engine_queueing_model_test.go` asserts a QM-shaped `Live:true`, `Spare=25000`/`PRC=10000` result still scales down (3→1). | matches |
| **F-T1a** (test) | make model-a's step-2 result non-informative (`no-data`) so it discriminates per-tuple vs name-only keying | `engine_v2_liveness_test.go`: model-a switched from informative `Reason:"P1-obs"`/`now-95s` to `Reason:"no-data"`/`now`; spec + comment updated. Coder verified it now fails under a simulated name-only keying. | matches |
| **F-T1b** (doc only) | **mechanism unchanged** — reason-based `no-data`→non-live is load-bearing (broken query returns `no-data`, not an error); document the 3-case persistence window | dev-guide paragraph added (never-had-data / transient-blip / aged-out; broken query = `no-data` not error). | matches |
| **F-Demand** (doc only) | one sentence: liveness = capacity/supply signal only; demand robustness out of scope, handled upstream | dev-guide paragraph added stating exactly that. | matches |
| **F-Conc** (comment only) | field comment on `lastGoodAnalysis` mirroring `vaEventTracker`; single-goroutine safety; parallelization would need sync; no lock | comment added on `engine.go` `lastGoodAnalysis` field; no lock introduced. | matches |
| **F-NTH** (doc/comment) | (1) reword "applies uniformly" → scoped to multi-analyzer path + QM static-live exception; (2) comment `applyDeallocationForRole` as intentionally not `Live`-gated | dev-guide reworded; `analyzer_helpers.go` comment added. | matches |

**Round-2 delta is clean.** `2b0c715c` restores QM scale-down (no behavior change beyond that);
`5fd0a958` is test-only; `7e931ccf` is dev-guide prose + two code comments (0 logic, confirmed
via `--stat`: 29 doc lines, 4+4 comment lines). None of the three touches the gate logic,
`updateLivenessAndSetLive`, or the keying — so the round-1 "confirmed correct" mechanics stand
unchanged.

**On my round-1 T1b framing (now closed).** Round-1 I argued liveness sat at the wrong layer
(role-b reasons doing role-a's job). The planner + Dean ruled the reason-based `no-data`→non-live
mechanism **correct and load-bearing** — a mislabelled/broken Prometheus query returns a
well-formed `no-data` result, *not* an error, so the engine's nil/error exclusion never fires for
it and the `Reason`-based check is the only thing that detects a durably-broken analyzer. The
staleness window then separates never-had-data / transient-blip / aged-out. That is Dean's design
call; F-T1b documents the settled semantics, and it is written accurately. My round-1 §T1b
analysis below is retained as the finding that surfaced the question, not as an open objection.

**Residual (known + accepted, not blocking).** F-B1's test builds its own `Live:true`
`NamedAnalyzerResult` (via the `withQMEntry` helper) rather than driving `optimizeQueueingModel`
end-to-end, so it pins "a QM-shaped `Live:true` result scales down" but would **not** catch a
future deletion of the `Live: true` line in `engine_queueing_model.go` (that needs the heavier
`prepareModelData` fake-client fixture). The coder disclosed this in the test comment and status,
raised it via AskUserQuestion, and Dean accepted the lighter test. Recorded so it isn't
rediscovered as a surprise later.

---

## B1 — BLOCKING: queueing-model path never sets `Live` → QM scale-down silently disabled

**Where:** `internal/engines/saturation/engine_queueing_model.go:78-86` (construction);
consumed at `cost_aware_optimizer.go:447` / `greedy_score_optimizer.go:150` via
`scaleDownRoleIterated` → `needsScaleDownForRole`.

**Decisive evidence that QM reaches the veto helper (contra "QM is not integrated").**
Three independent confirmations that the QM optimize path flows through the same
`needsScaleDownForRole` the PR modified:

1. **QM labels its result as the saturation entry.** `optimizeQueueingModel` builds its
   `NamedAnalyzerResult` with `Name: domain.SaturationAnalyzerName` (=`"saturation"`), not
   `QueueingModelAnalyzerName` (engine_queueing_model.go:80). It then calls
   `e.optimizer.Optimize(ctx, requests, nil)` (:96) — the *same* `CostAwareOptimizer` /
   `GreedyByScoreOptimizer` the V2 path uses.
2. **The optimizer's scale-down gate matches on that name.** `Optimize` starts each request
   with `satEntry := saturationEntry(req.AnalyzerResults)` and `continue`s only if it is
   `nil`. `saturationEntry` (analyzer_helpers.go:66-73) returns the entry whose
   `Name == domain.SaturationAnalyzerName`. Because QM named its entry `"saturation"`, this
   is **non-nil** → no `continue` → `Optimize` proceeds to `scaleDownRoleIterated` →
   `needsScaleDownForRole`.
3. **The engine's own comments say so.** `engine.go:466` ("queueing-model paths which both
   use the optimizer pipeline") and `:481` ("Queueing model: QueueingModelAnalyzer →
   AnalyzerResult → Optimizer.Optimize → Enforcer bridge").

So QM does **not** "work alone" in the scale-down decision — it deliberately reuses the
shared optimizer by masquerading its result as the saturation entry. The coder was right to
leave QM code untouched; the break is entirely in the shared helper.

**What happens.** The engine has two optimize paths that build `NamedAnalyzerResult`
slices and feed them to `e.optimizer.Optimize` (dispatch at `engine.go:485-491`):

- **V2 / saturation** (`runAnalyzersAndScore`) — correctly instrumented: calls
  `updateLivenessAndSetLive` before the results reach the optimizer, so `Live` is set.
- **Queueing model** (`optimizeQueueingModel`) — builds `NamedAnalyzerResult{Name, Result,
  Score, Remaining, Spare}` inline at line 80 and **never sets `Live`**. There is no
  `updateLivenessAndSetLive` call on this path.

With every QM entry at `Live == false` (zero value), `needsScaleDownForRole` skips all
entries, `liveCount` stays 0, and the **safety floor returns `false` unconditionally** →
**the queueing-model path can never scale down.**

**Why it's a regression, not pre-existing dead code.** `initRoleState(s)` (called in both
optimizers before scale-down) populates `RoleSpare["both"]` from the result's `Spare`. So
**pre-PR**, a QM result with `Spare > 0` returned `true` from `needsScaleDownForRole` and
scaled down normally. Commit `77be65ca` turned that into an unconditional `false` for the
QM path.

**Active path.** Not deprecated. Selected when `analyzerName ==
domain.QueueingModelAnalyzerName`, which per the code comment (`engine.go:483`) is
"activated by presence of `wva-queueing-model-config` ConfigMap." (V1 is the one marked
for future deprecation; QM is not.)

**Why green gates didn't catch it.** There is **no** `engine_queueing_model_test.go` — the
QM optimize path has zero test coverage, so the scale-down loss is invisible to `make test`.
(V1, by contrast, uses `CalculateSaturationTargets` and never touches these helpers, so V1
is unaffected.)

**The alternatives (each is a different answer to "what is QM's relationship to the veto"):**

- **(a) Route QM through the same liveness bookkeeping** (`updateLivenessAndSetLive`, keyed
  per model), so a stale/uninformative QM analyzer is gated exactly like saturation.
  - *Pro:* uniform treatment; QM gets the same safety the PR gives saturation.
  - *Con:* QM is **not** part of the multi-analyzer framework yet — it fabricates a single
    `"saturation"`-named entry and calls the optimizer directly. Wiring it into the liveness
    machinery now bakes that temporary shape deeper. Also **couples with T1b**: QM's
    `VariantCapacity`s carry **no `Reason`** (`""`), including `errorVariantCapacity`
    (queueingmodel/analyzer.go:284), so under today's `ResultIsInformative` a QM *error*
    would read as *informative/live*. (a) is incomplete unless T1b is fixed in lockstep.
- **(b) Set `Live: true` statically at the QM construction site** (engine_queueing_model.go:80).
  - *Effect:* restores exactly the pre-PR behaviour for QM — a QM result with `Spare > 0`
    scales down as before; the new veto never applies to QM.
  - *Pro:* one line, no coupling to T1b, no new machinery on a path that isn't part of the
    framework yet. QM keeps its "works alone" semantics for the scale-down decision.
  - *Con:* QM is not liveness-gated — but that is correct **for now**, because QM has no
    per-analyzer liveness story until it is a first-class multi-analyzer participant.
- **(c) Make QM genuinely independent of the shared optimizer** (stop labelling its result
  `"saturation"`, stop routing through `needsScaleDownForRole`). Largest change; the real
  end state, but it is the "integrate QM into the multi-analyzer framework" project, not
  this PR.

**Dean's decision (2026-07-27): option (b) — statically `Live: true` for the QM path in
this PR.** Rationale: liveness for QM is out of scope here; QM's own liveness will be built
when QM is integrated into the multi-analyzer framework, in **separate future PRs** — not
this one. So the coder should add `Live: true` to the QM `NamedAnalyzerResult` construction
(engine_queueing_model.go:80-86) with a comment stating that QM is intentionally always-live
until it becomes a framework participant (forward reference, no plans-branch identifier per
CODER-CONVENTIONS §4a). This keeps the PR's veto scoped to the multi-analyzer (V2) path,
which is the only path with real per-analyzer liveness today.

- **Test:** add a minimal engine-level QM scale-down test (a plain "informative QM result
  still scales down under the new gate") so this path stops being a coverage blind spot and
  the static-live guarantee is pinned against future regressions.

**Plan-scope note (for the planner, not a coder fault in isolation).** Commit 1 step 4
said *"Locate the per-cycle path where the analyzer slice is built and the role helpers are
called (in engine_v2.go / engine.go)"* — singular "path", and Scope §scope named
`engine.go` only generically. The QM path is a **second** builder of `NamedAnalyzerResult`
that reaches the gated helpers and was not enumerated. The plan under-specified the blast
radius; the correct coder move under CONVENTIONS would have been a handoff flagging the
second path. Worth folding into the "widen the semantic-pivot grep across all construction
sites" process note already open in CURRENT.md.

---

## T1b — MEDIUM (design): liveness is derived from saturation's *domain* reasons; it should be a uniform engine-level signal, with per-analyzer reasons as logical omits

**Dean's model (2026-07-27).** Liveness has two distinct concerns that must not be
conflated, and the mechanism must be the **same for every analyzer**:

- **(a) Engine-level liveness — uniform, analyzer-agnostic.** "Global errors and a
  completely missing / broken analyzer." The *engine* decides this: did the analyzer error,
  panic, return nothing, or go missing? This has nothing to do with any analyzer's
  domain-specific output.
- **(b) Per-analyzer domain output — analyzer-specific, treated like throughput (TA).** A
  live, functioning analyzer reports per-variant results; some variants it simply can't
  speak to. Those are **logical omissions**, *not* `live=false`. Most `no-data`-style
  outcomes are omissions, not liveness failures — only a genuine error is (a).

The saturation analyzer plays **both** roles today (it is the always-present pipeline keeper
*and* a domain analyzer), and the PR's liveness mechanism mixes them.

**What the code actually does — and why it's role (b) masquerading as role (a):**

- **Role (a) already exists, separately and uniformly.** A registered analyzer that errors
  or panics is converted to `nil` by `runRegisteredAnalyzer` (engine_v2.go:264-278); the
  caller drops `nil` (`if result == nil { continue }`, :151), so a broken analyzer is simply
  **absent** from the slice and cannot veto. A saturation hard-error bails the whole cycle
  (:107-109). This is exactly the "engine treats errors / missing / broken" mechanism you
  describe, and it is already analyzer-agnostic. **The PR did not need to touch this.**
- **The PR's new machinery keys liveness on role (b).** `ResultIsInformative` inspects
  `VariantCapacity.Reason` against `{"no-data","error"}` — **saturation_v2's own domain
  vocabulary** (`satReasonNoData` = "no live replicas & no store record"; `"error"` = the
  `capacityLabel` fallback for an unmapped K2 priority, analyzer.go:667). So a *present,
  non-errored, functioning* saturation analyzer that reports `no-data` for its variants is
  driven toward `Live=false` — precisely the logical-omit case you say should **not** be a
  liveness failure.
- **The "staleness window" is really a consecutive-omit counter.** Every analyzer stamps
  `AnalyzedAt = time.Now()` on every run (saturation_v2:128, throughput:379,
  queueingmodel:142) — no analyzer ever returns an old/cached timestamp. So
  `now.Sub(lastGood) <= threshold` can only age when a **present** analyzer keeps returning
  **non-informative** (role-b `no-data`/`error`) results and thus stops refreshing its
  timestamp. In other words, the window measures "how many consecutive cycles of role-(b)
  omission," not any real data-clock staleness. It is role (b) all the way down.

**Consequence per your model.** The mechanism is at the wrong layer. Liveness (role a) is
already handled by the existing error/nil/panic exclusion — uniform and analyzer-agnostic.
The PR instead built a parallel, saturation-reason-specific path that turns a *functioning
analyzer with no data* into a vetoing-disabled one. Under your model, saturation's `no-data`
should be a **logical omit** (like throughput skipping an unresolvable variant), and only a
true error/missing/broken analyzer should be non-live — which the engine already knows how
to detect without reading `Reason` strings.

**This diverges from the *plan*, not just the code.** The plan framed liveness as
"never-had-metrics / error / stale cannot veto," which explicitly folds the *no-data*
("never-had-metrics") case into liveness. Your (a)/(b) model pulls no-data back out into
role (b). So this is a **plan-level design question for the planner to reconcile**, not a
coder mistake — the coder implemented the plan's framing faithfully. Handing to planner.

**Fix direction (for the planner, not prescriptive):** derive `Live` from the uniform
role-(a) signal the engine already has (analyzer present & non-errored this cycle, optionally
"present within the last N cycles" if a cross-cycle memory is still wanted), and treat every
analyzer's domain `no-data`/omission as a logical omit that does not clear `Live`. That would
make `ResultIsInformative`'s reason-denylist unnecessary and let saturation and throughput be
handled identically. If a cross-cycle "hasn't produced anything for N cycles → not live"
memory is desired, key it on **presence/absence in the slice** (role a), not on domain
reasons (role b).

**Secondary (test).** Because production `AnalyzedAt` is always ≈`now`, the
`"staleness boundary"` engine test fabricates a state that cannot occur in production (a
freshly-returned result with an 89s/95s-old `AnalyzedAt`). Whatever mechanism replaces the
reason-based one, that test should assert against the real signal (consecutive
omission/absence), not a hand-set old timestamp.

**Resolution / narrowing (Dean, 2026-07-27).** Role (a) and the engine-level error handling
are **agreed** — a genuine error / missing / broken analyzer is a liveness failure, and the
engine already detects it uniformly via nil-result exclusion (no change needed there). The
**only open issue is `no-data`**: is its meaning consistent across analyzers, and *when do
we actually get it?* — a question routed to the **planner**. Concrete input already gathered:

- `"no-data"` is emitted by **saturation_v2 only** (`satReasonNoData`, analyzer.go:389),
  in the branch where a variant has **no ready replicas AND no stored capacity record AND no
  compatible cross-variant record** → nothing to estimate capacity from (`PerReplicaCapacity`
  stays 0).
- **Throughput** never emits `no-data`; the equivalent "can't compute for this variant"
  condition makes it **omit the variant** entirely (`resolveITLModel` → `ok=false` →
  `continue`). **QM** sets no `Reason` at all.
- So the *concept* "analyzer has nothing to say about this variant" is represented three
  different ways (saturation: `Reason="no-data"`, PRC=0, variant present; throughput: variant
  absent; QM: n/a). It is **not** a consistent cross-analyzer signal today.

The specific question for the planner: is saturation's `no-data` a **logical omit** (role b —
this variant isn't applicable this cycle) or a genuine **never-had-metrics liveness** signal
(a model with no replicas and no store history at startup produces `no-data`, which is
exactly the "never-had-metrics" case the plan wanted to gate)? It currently conflates both.
Deciding that fixes the mechanism *and* the cross-analyzer consistency in one call.

---

## T1a — MEDIUM (test effectiveness): the per-tuple keying test does not actually exercise the keying

**Terminology (to match your framing).** Liveness state lives in one map entry per tuple
`(analyzerName, modelID, namespace)`. The map is `lastGoodAnalysis[key(ns,model)][name]`.
Below, **T_a** = `(saturation, model-a, ns)` and **T_b** = `(saturation, model-b, ns)`.
"model-a's result" is shorthand for "the `AnalyzerResult` produced when
`runAnalyzersAndScore` is called with `modelID = "model-a"`" — i.e. the result whose
liveness is stored under **T_a**. The test reuses one `Engine` and swaps its analyzer
between calls, so both calls share the same map; only the `modelID` arg differs.

**Where:** `internal/engines/saturation/engine_v2_liveness_test.go`, the
`"scopes liveness per model"` spec.

**What it intends to prove.** That because state is keyed per tuple, model-b's fresh run
writes only **T_b** and cannot make model-a's **T_a** appear live. (This is the coder's
flagged design point — per-tuple map instead of the plan's name-only map — confirmed with
you.)

**Why it doesn't discriminate.** Sequence in the test:
1. Run `modelID="model-b"` with a **fresh, informative** result → writes `T_b = now`.
2. Run `modelID="model-a"` with a **stale but still informative** result
   (`Reason:"P1-obs"`, `AnalyzedAt = now-95s`). Because that result **is informative**,
   `updateLivenessAndSetLive` **writes T_a = now-95s** this very cycle, then computes
   `Live = now - (now-95s) ≤ 90s → false`.

So `T_a` gets its `false` from **its own** freshly-written stale timestamp — model-b's run
is irrelevant to the outcome. Run the same test against a (wrong) name-only map: step 2's
informative result would overwrite the shared `"saturation"` key to `now-95s` anyway →
still `false`. **Both the correct per-tuple map and the buggy name-only map pass** → the
test cannot fail when keying breaks. It is effectively a duplicate of the
`"staleness boundary"` spec with an unused model-b run prepended.

**To make it discriminating,** step 2's model-a result must be **non-informative**
(`Reason:"no-data"`), so it does **not** write `T_a` and the outcome depends on what's
already stored:
- correct per-tuple map → `T_a` was never written → `Live == false` ✓
- buggy name-only map → step 1 wrote `"saturation" = now`; model-a reads it → `Live == true`
  ✗ (keying bug caught)

Not a code defect — the code *is* correctly per-tuple keyed — but the regression guard for
that deliberately-chosen design point is inert. (Note: this fix assumes the current
reason-based liveness; if T1b changes the mechanism, rewrite this test against the
replacement signal instead.) Relevant given the project's standing sensitivity to test-rot.

**Dean's pushback (2026-07-27):** "each tuple is either live or not; if not live, no veto —
why are T_a and T_b related?" They are **not** related under the correct code — and that is
the property the test is supposed to prove. The test exists only because the coder
deliberately deviated from the plan (plan said key by analyzer *name* alone; coder keyed by
`(name, model, ns)` tuple). Under the plan's rejected name-only keying, model-b's fresh run
*would* leak into model-a (they'd share one `"saturation"` entry). A regression guard for
"we chose per-tuple, not name-only" must therefore be built so it would **fail** under
name-only keying — i.e. construct a scenario where the two keyings give *different* answers,
then assert the per-tuple answer. The current test gives the *same* answer under both, so it
guards nothing. If the coder's per-tuple deviation is accepted as obviously-correct and not
worth a dedicated guard, the honest move is to delete the spec rather than keep an inert one.
**Routed to planner to decide** (keep+fix, or drop).

---

## Concurrency — `lastGoodAnalysis` map (verified safe under the current executor)

Dean's concern: "multiple parallel writers on the global map." Verified — **not realized
under the current code**, but the concern points at a genuine latent constraint.

**The map.** `Engine.lastGoodAnalysis map[string]map[string]time.Time` is a single
process-global map (keyed `GetNamespacedKey(ns,model)` → analyzer name → time). It is
written only in `updateLivenessAndSetLive`, including a top-level insert
`e.lastGoodAnalysis[modelKey] = make(...)` on first sight of a model — and a concurrent
top-level insert from two goroutines is exactly what triggers Go's fatal "concurrent map
writes".

**Why it's safe today.** The optimize loop is single-goroutine and cycles never overlap:
- `StartOptimizeLoop` → `e.executor.Start(ctx)`. `PollingExecutor.Start` uses
  `wait.UntilWithContext(ctx, fn, interval)` (polling.go:51) — apimachinery's helper runs
  `fn` **sequentially**, waiting for each invocation to return before the next tick. One
  goroutine; no overlap. `executeWithRetry`'s inner retry loop is also sequential.
- Inside a cycle, `optimizeV2` iterates models **sequentially**; `updateLivenessAndSetLive`
  is called once per model, in that single goroutine.
- This is the **same** single-writer assumption the engine already relies on elsewhere:
  `e.vaEventTracker = make(...)` is reassigned every cycle with **no lock**, and there is
  **no mutex on `Engine`**. If cycles could overlap, that pre-existing write would already
  race. So the new map introduces **no new concurrency risk** beyond the engine's existing
  design invariant.

**The latent constraint (worth a note, not a blocker).** The safety rests entirely on
"cycles never overlap and models are processed serially." If the engine is ever changed to
process models in parallel (a plausible future throughput optimization), `lastGoodAnalysis`,
`vaEventTracker`, and `capacityStore` would **all** need synchronization — and
`lastGoodAnalysis`'s top-level insert would be the first to panic.

**Dean's decision (2026-07-27): comment only — no lock this PR; planner handles the
documentation.** No `sync.Mutex` / `sync.Map` — not required for current correctness, and
adding one now would falsely imply the surrounding per-cycle state is already
concurrency-safe when it isn't. The single-goroutine / non-overlapping-cycle assumption
should be documented (a field comment on `lastGoodAnalysis`, mirroring the existing unguarded
`vaEventTracker`, so a future parallelization change knows to add synchronization) — the
**planner** decides how/where that documentation lands in the task plan.

---

## Confirmed correct / good work

- **Gate logic** (`needsScaleDownForRole`, `safeRemovalReplicasForRole`) matches the plan
  exactly, including the safety floor (`return liveCount > 0`) and skipping non-live
  entries in the min loop. Old `len(s)==0 → false` guard correctly subsumed.
- **V2 instrumentation** (`updateLivenessAndSetLive`): refreshes `lastGoodAnalysis` for
  informative results, sets `Live` on every entry before the helpers run, per-model keyed,
  nil-map guarded, Config-nil fallback (30s) for minimal test engines. Applied uniformly to
  saturation (no name-based exemption) — matches Dean's point 2.
- **Clock.** Plan warned against "a second time source." In practice every `AnalyzedAt` is
  `time.Now()` wall-clock (saturation_v2, throughput, queueingmodel analyzers), and the
  engine's `now := time.Now()` is the same clock; the intra-cycle skew is milliseconds
  against a ≥90s threshold. No correctness impact — verified, not a finding.
- **`ResultIsInformative`** — correct for the **saturation** analyzer this PR gates
  (real `no-data`/`error` sentinels; empty `VariantCapacities` → not informative, covering
  throughput's "no resolvable ITL model" case). See **T1b** for the cross-analyzer
  generality caveat — do not read this as "correct for all analyzers."
- **Pipeline helper tests** genuinely exercise each gate branch (never-analyzed, stale,
  safety floor, real-veto-preserved, saturation-not-exempt, safeRemoval-skips-non-live) —
  not tautological.
- **Engine tests**: recovery (two real cycles through `runAnalyzersAndScore`) and staleness
  boundary (real time, real computation) are sound (modulo T1 above for the third).
- **Fixture updates**: `Live: true` added to pre-existing scale-down fixtures across
  `cost_aware_optimizer_test.go`, `engine_v2_test.go`, plus the `makeNamed*` helper
  defaults — correct and documented in comments. Coder also widened the semantic-pivot grep
  and caught 5 extra fixtures (per the A′-review process note) — good discipline.
- **Dev-guide** (`multi-analyzer-pipeline.md`): accurate, Type-4 compliant (current code
  only, no `#1261`/plans-branch refs), self-sufficient; ASCII diagrams, field table,
  responsibility table, and the new "How results combine" prose all updated. Scale-up
  correctly documented as ungated.

## NTH / minor

- Dev-guide responsibility table attributes `Live` to "Engine (`runAnalyzersAndScore`, each
  cycle)". Once B1 is fixed by instrumenting the QM path too, reword to "the engine's
  per-cycle analysis paths" so the doc isn't V2-only. (If B1 is instead fixed with a bare
  `Live: true` on QM, the doc's "applies uniformly to every analyzer" claim becomes false —
  another reason to prefer the shared-helper fix.)
- `applyDeallocationForRole` is not `Live`-gated. Harmless today (non-live entries are
  excluded from the veto and the min, so mutating their `RoleSpare` affects nothing that's
  read), but a one-line comment noting the asymmetry would help future readers.
