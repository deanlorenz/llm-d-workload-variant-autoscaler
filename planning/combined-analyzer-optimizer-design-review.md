# Review — combined-analyzer-optimizer-design

**Status:** DRAFT
**Type:** 6 (review)
**Reviewer:** plan/review agent (independent code-grounded pass)
**Date:** 2026-08-03 (original pass) · **Reconciled:** 2026-08-03 (post-revision pass — see [Reconciliation](#reconciliation))
**Target:** [`planning/combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (Type 1 DRAFT) + derived Type 3 stack: [`ta-anchor-goldens-plan.md`](ta-anchor-goldens-plan.md), [`ta-anchor-refactor-plan.md`](ta-anchor-refactor-plan.md) (PR-1), [`ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) (PR-2, STUB)
**Code baseline:** `Main/` worktree = local `main` tip (verified against working tree 2026-08-03)
**Method:** independent — I formed my own view of the code first, then compared it to the design's claims. Not a line-ref audit of the design's citations. Every code claim below was checked against the current `Main/` source; file:line refs are mine.
**Reconciliation method:** after the planner revised the design doc and authored the Type 3 stack, I re-checked each finding against the *current* text of all four docs + code, via an adversarial 4-auditor pass (design-text / plan-text / code-reconfirm / decomposition). Every "ADDRESSED" below is backed by a confirmed quote from the live doc, not recollection.

---

## Reading Protocol

**Current state first:** read the **Verdict** and the **Reconciliation** table — they tell you what
survives after the planner's revisions (one doc-hygiene fix). §1–§6 are the *original pass*,
preserved verbatim with inline `Update (post-revision):` notes so the code-grounded analysis is not
lost; read them only if you need the supporting detail behind a reconciliation row.

## TOC

- [Verdict (bottom line up front)](#verdict)
- [Reconciliation — post-revision pass (2026-08-03)](#reconciliation)
- [§1 — Priority: can TA be enabled *replacing* satv2?](#s1)
- [§2 — Corrections (1 refuted, 4 imprecise)](#s2)
- [§3 — Bug assessment (independent reachability)](#s3)
- [§4 — Confirmed-correct claims](#s4)
- [§5 — Cross-doc tension: F1 abandonment vs. the rejection handoff](#s5)
- [§6 — Recommendations before locking](#s6)

---

<a name="verdict"></a>
## Verdict

The design is **substantially accurate and well-reasoned.** Its central thesis — that today's code
uses saturation's per-replica capacity as a stand-in proxy in sizing/sort/utilization, so turning on
a second analyzer with a different PRC silently corrupts the composite math — is **confirmed** in
code. The anchor refactor (separate saturation's metadata-carrier role from its vote role) is the
right shape and correctly resolves the veto/liveness hazard that sank the earlier zero-signal design.

**Post-revision bottom line:** the planner's revisions to the design doc plus the new Type 3 stack
(`ta-anchor-goldens` → `ta-anchor-refactor` PR-1 → `ta-anchor-dynamic-refresh` PR-2) **address five of
the six recommendations** from the original pass. The three "needs attention" items I raised are now
resolved in the docs, and the config-trap / enablement-mechanism gap I flagged as unspecified is
specified concretely in the PR-1 plan (skip removal + `effectiveEnabled` default-on gate + anchor
re-pointing + STOP→handoff boundary with the lifecycle plan). **One substantive finding survives**,
and it is doc-hygiene only:

> **§2.1 (LIVE) — the refuted "TA consumes sat-v2's outputs / sat-v2 must run before TA in analyzer
> order" claim still stands verbatim in the design doc** (§anchor L273-275, with a partial echo of
> the "consumes" half at Open-Q #2 L619-620). It states a *wrong reason* for a *correct conclusion*.
> **Impact is confined to the Type 1 doc — the false claim did NOT leak to the coder:** the derived
> PR-1 plan (§1/§2) gives the *correct* reason (sat-v2 is the sole source of the (a) common metadata
> Cost/AcceleratorName) and explicitly repudiates any analyzer-ordering constraint. So the fix is a
> one-paragraph edit in the design doc, not an implementation concern.

The 0.9 ship posture (do not enable TA on the current code; land it behind the anchor refactor) is
**sound** — see §3. **What changed since the original pass** — item by item, with the doc refs that
resolve each — is in the [Reconciliation](#reconciliation) table below; the original findings are
preserved beneath it with inline `Update (post-revision):` notes.

---

<a name="reconciliation"></a>
## Reconciliation — post-revision pass (2026-08-03)

The planner revised the Type 1 design doc and authored the Type 3 plan stack after the original pass.
I re-checked every finding against the *current* text of all four docs + code (adversarial 4-auditor
pass: design-text / plan-text / code-reconfirm / decomposition; all verdicts CONFIRM except the one
noted). Result: **5 of 6 recommendations addressed; 1 doc-hygiene finding live.**

| Original finding / rec | Status | Resolved by (live ref) |
|---|---|---|
| **§1** — priority question needs a sharper answer + config-trap is a silent no-op + enablement mechanism unspecified | **ADDRESSED** | Design §anchor "Anchor population by active-vote set" (three explicit cases: sat-only / TA-only / both). PR-1 plan §5 1b removes the `entry.name == SaturationAnalyzerName { continue }` skip and gates saturation via the **same `effectiveEnabled(name,config)`** as every other analyzer (default-on) → `saturation:{enabled:false}` becomes truthful; §5 1c re-points `computeCurrentGPUUsage`/`ByNamespace` to `req.Anchor` (sat-v2 may be off-ballot in TA-only). §7 3a + boundary: STOP→handoff to `wva-analyzer-lifecycle-plan.md` if the config surface can't disable saturation yet. |
| **§2.1** — REFUTED "TA consumes sat-v2's outputs / sat must run before TA" | **LIVE (doc-hygiene)** | **Still present** in design §anchor L273-275 (+ partial echo Open-Q #2 L619-620). Code re-confirmed: TA imports no saturation pkg, reads no sat output; `AnalyzerInput` has no field carrying another analyzer's result. **Did not leak:** PR-1 plan §1/§2 states the correct metadata-sourcing reason and repudiates ordering ("any order", "no forced sat-first entry", "ordering not significant to correctness"). Fix = design-doc edit only (see §2.1). |
| **§2.2** — "cannot be enabled in any form" conflates alongside vs. replacing | **ADDRESSED** | Design now separates the two (§anchor active-vote breakdown; "Both 'TA alongside' and 'TA replacing the sat-v2 *vote*' are in scope; neither removes the sat-v2 *run*"). "cannot be enabled today" is scoped to the pre-change state. |
| **§2.3** — mis-attributed limited-mode selector (`LimitedModeEnabled()`/`WVA_LIMITED_MODE`) | **ADDRESSED** | Whole-doc grep finds no flag-name assertion; the limited section + bug #5 now reference only code identifiers (`fairShareValue`/`fairShareCap`). |
| **§2.4** — sort-feed mechanism attribution (`buildCapacityMap` vs. param) | **ADDRESSED** | PR-1 plan §10 routes **both** `buildCapacityMap` (`:54`) and `allocateForModelPaired` (`:62`) to `req.Anchor.VariantCapacities`; both feed the same anchor, so the original nit is moot. |
| **§2.5** — `modelDemandGPUs` grouping nit | **ADDRESSED (moot)** | Subsumed by the anchor re-point in PR-1 §10; no standalone action. |
| **§3 / bug #4** — keep downgraded, add observability note | **ADDRESSED** | Design §bugs #4 fully traces + downgrades ("NOT an active *sizing* bug"); Open-Q #6 recommends **no code change**, doc/comment note only — matching my recommendation. |
| **§5** — F1 reversal + coordination-doc thread must be surfaced, not silent | **ADDRESSED** | F1 reversal is explicit at three spots (header "this doc is its missing design"; §anchor L271-277; Open-Q #2 "F1 … is not a prerequisite"). Coordination-doc follow-up kept as a separate tracked thread (bug #4 net + Open-Q #3 "update coordination-doc D1/#2"). |

**Decomposition check (new — not in the original pass).** The planner split the work three ways; I
confirmed each Type 3 doc matches its role:
- **`ta-anchor-goldens`** — invariant-#7 ship gate: characterization goldens over sat-v2-only
  behavior captured from `main`, additive / test-only / near-zero risk. (Nuance: the goldens plan
  says "same decisions as today"; "byte-identity" is the refactor plan's phrasing — substantively
  equivalent.)
- **`ta-anchor-refactor` (PR-1)** — static single-vote (a)/(b) split + TA-only enablement,
  **zero combine arithmetic, no refresh machinery**; the four masked bugs (#1/#2/#3/#5) are
  combine-only and deferred to PR-2.
- **`ta-anchor-dynamic-refresh` (PR-2)** — deferred **STUB** (do not start until PR-1 lands): turns
  on the multi-vote per-iteration (b) refresh and fixes the four combine-arithmetic bugs.

This is a sound decomposition: the risk gradient (static single-vote first, dynamic multi-vote
second) matches the design's own "clean risk gradient" framing, and the goldens gate makes the
byte-identity invariant enforceable rather than aspirational.

---

<a name="s1"></a>
## §1 — Priority: can TA be enabled *replacing* satv2?

> **Update (post-revision 2026-08-03): ADDRESSED.** The gap this section flagged — target named but
> mechanism unspecified, and the `saturation:{enabled:false}` silent no-op — is now specified in
> **`ta-anchor-refactor-plan.md`**: §5 1b removes the name-based `continue` skip and gates saturation
> through the **same `effectiveEnabled(name,config)`** default-on path as every other analyzer (so
> the parsed `enabled:false` finally takes effect — the trap becomes truthful, exactly the
> "honor the existing field" fix I recommended); §5 1c re-points `computeCurrentGPUUsage`/
> `…ByNamespace` to `req.Anchor` so GPU accounting survives sat-v2 being off-ballot in TA-only; §7 3a
> keeps default = saturation-enabled and drops the vote off-ballot on disable, with an explicit
> **STOP→handoff** to `wva-analyzer-lifecycle-plan.md` if the config surface can't disable saturation
> yet. The design side adds the three-case active-vote breakdown (sat-only / TA-only / both) in
> §anchor. The original trace below stands as the *why*; the mechanism is now on record.

Dean's request was specifically: *"Check all initialization/configuration paths to make sure TA can
be enabled **replacing** satv2."* This is the load-bearing question, so I traced every init/config
path independently.

### Two meanings of "replacing," and the answer to each

**(A) TA is the sole *vote*; satv2 still *runs* as the metadata carrier** (this is the design's
model — case (b) in §anchor). **Not reachable today.** No config, flag, or env var produces it.

**(B) satv2 does not run at all.** The design explicitly rejects this as the model (satv2 *must* run
to populate anchor topology). Also not reachable, and correctly out of scope.

So under the design's own intended meaning (A), **the answer is: not achievable in current code, and
the design describes the target without specifying the mechanism that would get there.**

### The init/config trace (why (A) is unreachable)

1. **`cmd/main.go:391,504-509`** — `taRegistered := cfg.ThroughputAnalyzerEnabled()`; if true,
   `engine.RegisterAnalyzer(throughput.AnalyzerName, …)`. This is the *only* knob that admits TA.
   It is purely **additive** — it appends TA to the analyzer set. There is no corresponding path
   that *removes* saturation.

2. **`config.go:355-364`** (`ThroughputAnalyzerEnabled`) + **`saturation_scaling.go:222-227,296-301`**
   (`ApplyDefaults`/`GetAnalyzerName`) — config is **fundamentally saturation-rooted**. When the
   `Analyzers` list is empty it is auto-seeded with `{Name:"saturation", Score:1.0, Enabled:true}`;
   when populated, `GetAnalyzerName` still returns `"saturation"`. The `Analyzers` list *adds*
   analyzers; it is not a replacement set.

3. **`engine.go:284-286`** (`NewEngine`) pre-registers **only** saturation into `analyzers`.
   **`engine_v2.go:106-178`** (`runAnalyzersAndScore`) then, every cycle:
   - computes saturation's `baseResult` unconditionally and makes it **`namedResults[0]`**
     (L~110-149) — before any enable check;
   - loops the snapshot, **`continue`-ing past saturation by name** (L~150-151) so it never reaches
     the `effectiveEnabled` gate;
   - gates every *other* analyzer on `effectiveEnabled` (L~153).

4. **`engine_v2.go:386`** (`effectiveEnabled`) — docstring states saturation is **exempt**. Its
   `Enabled` field is never consulted on the consumption side.

**Consequence — the config trap.** Setting `saturation: {enabled: false}` in the ConfigMap is a
**silent no-op**: the field parses and stores correctly (`saturation_scaling.go`), but the consumer
never reads it for saturation. A user trying to "replace satv2 with TA" would write exactly this
config, get no error, and observe saturation still driving decisions. This is the origin bug in
[`plan__sat-v2-disable-not-working-f1-gap.md`](../session/handoffs/plan__sat-v2-disable-not-working-f1-gap.md)
and Dean's rejection of the zero-signal shortcut in
[`wva-analyzer-lifecycle-plan.md`](wva-analyzer-lifecycle-plan.md) (Commit 2c, REJECTED 2026-07-31).

### What *is* reachable today

**TA *alongside* saturation** (both vote) is mechanically wireable via `ThroughputAnalyzerEnabled()`
→ TA appended as `namedResults[1]`. But this is the exact configuration the design's bugs #1/#2
corrupt (see §3) — reachable-but-wrong on the default cost-aware path.

### Gap the design should close

The design names the target (case (b): TA sole vote, saturation silent carrier) but does **not**
specify the concrete mechanism. To make (A) reachable and correct, the implementation needs, at
minimum:

- a **config knob** that means "saturation's vote is suppressed" (and, ideally, honoring the
  already-parsed `saturation.Enabled=false` so the existing trap becomes truthful rather than adding
  a second knob);
- a **conditional prepend** in `runAnalyzersAndScore` — the anchor still gets built from saturation's
  `baseResult` (metadata), but saturation's *entry* is omitted from the vote slice when suppressed;
- explicit **veto/liveness handling** for the suppressed case (the design gets this right
  conceptually — true removal drops saturation from the all-live-agree set, unlike the rejected
  Spare=0 approach — but the mechanism section should state it as a requirement, not leave it
  implicit).

**Recommendation:** add an explicit "§enablement mechanism" to the design covering these three
points, and state plainly: *replacing satv2 (TA sole vote) is not reachable today; here is the
change that makes it reachable.*

---

<a name="s2"></a>
## §2 — Corrections

### 2.1 REFUTED — "TA consumes sat-v2's outputs" (design §anchor L273-275) — **LIVE**

> **Update (post-revision 2026-08-03): LIVE — the single surviving substantive finding.** The claim
> still stands verbatim in the current design doc at **§anchor L273-275** ("TA **consumes some of
> sat-v2's outputs for its own analyzer calculation**, *upstream* of anchor construction — so sat-v2
> must run before TA in analyzer order, and TA-alone still relies on sat-v2 running"), with a
> **partial echo of the "consumes" half only** at Open-Q #2 L619-620 ("TA even consumes some sat-v2
> outputs for its own calculation" — no ordering clause there). Code was re-confirmed adversarially:
> TA imports no saturation package, reads no shared capacity store, and `domain.AnalyzerInput` has no
> field that can carry another analyzer's result — so there is no data path and no ordering
> requirement. **Impact confined to the Type 1 doc:** the derived PR-1 plan (`ta-anchor-refactor-
> plan.md` §1/§2) already states the *correct* reason (sat-v2 is the sole source of the (a) common
> metadata `Cost`/`AcceleratorName`, which a non-saturation vote cannot supply) and explicitly
> repudiates ordering ("any order", "no forced sat-first entry", "ordering is not significant to
> correctness"). So the false claim **did not leak to the implementer** — the fix is the
> one-paragraph doc edit spelled out at the end of this subsection (now hitting L273-275 + L619-620,
> not the stale ~L213-221 the original pass cited).

The design states TA "additionally consumes some of sat-v2's outputs for its own analyzer
calculation, upstream of anchor construction — so sat-v2 must run before TA in analyzer order, and
TA-alone still relies on sat-v2 running."

**This is wrong on the mechanism.** I verified `throughput/analyzer.go`:
- imports (L3-13) are `context, math, sync, time, ctrl, domain, aggregation, logging` — **no
  saturation package**;
- `Analyze(ctx, input)` reads only the raw `input.ReplicaMetrics`; it never reads saturation's
  produced `AnalyzerResult` or a shared capacity store populated by saturation.

TA and sat-v2 are **independent producers** consuming the same raw `AnalyzerInput`. There is no data
path from sat-v2's output into TA, and **no analyzer-ordering requirement** for TA's own calculation.

**The conclusion still holds, for a different reason:** TA-alone *does* rely on sat-v2 running —
because sat-v2's `Result` is the **carrier** that populates the anchor's topology metadata
(accel/cost/role/replica-count), which originates in the engine's capacity store and is copied into
`VariantCapacities`. That is exactly the design's §why point #1 (metadata-carrier role).

**Fix (the one remaining action for this review):**
- **§anchor L273-275** — replace "TA **consumes some of sat-v2's outputs** for its own analyzer
  calculation … so sat-v2 must run before TA in analyzer order" with: "TA is an **independent
  producer** consuming the same raw `AnalyzerInput`; sat-v2 must still run because its `Result` is
  the **carrier** of the anchor's topology metadata (accel/cost/role/replica-count) — not because TA
  reads sat-v2's output. There is **no analyzer-ordering constraint**." (This is the reason the
  derived PR-1 plan §2 already states correctly — just import it back into the design doc.)
- **Open-Q #2 L619-620** — delete the parenthetical "(TA even consumes some sat-v2 outputs for its
  own calculation)"; it repeats the same wrong mechanism.

### 2.2 IMPRECISE — "cannot be enabled in any form" (design ship-decision framing)

> **Update (post-revision): ADDRESSED.** Design §anchor now separates the two meanings explicitly
> ("Both 'TA alongside' and 'TA replacing the sat-v2 *vote*' are in scope; neither removes the sat-v2
> *run*"), and "cannot be enabled today" is scoped to the pre-change state rather than conflating the
> cases.

Conflates two facts that Dean's question needs kept apart:
- **alongside** = mechanically wireable but math-corrupting (bugs #1/#2, default path);
- **replacing** = not wireable at all.

The ship decision (don't enable TA in 0.9) is correct either way, but the *reason* differs per case.
Recommend splitting the statement.

### 2.3 IMPRECISE — limited-mode selector is `EnableLimiter`, not `LimitedModeEnabled()`

> **Update (post-revision): ADDRESSED.** A whole-doc grep now finds no `LimitedMode*`/`WVA_LIMITED*`
> flag-name assertion anywhere; the limited section and bug #5 reference only real code identifiers
> (`fairShareValue`/`fairShareCap`). The mis-attributed selector name is gone.

The design attributes bug #5's reachability to `LimitedModeEnabled()` / `WVA_LIMITED_MODE`. The
actual optimizer selector is the saturation ConfigMap's **`EnableLimiter`** field
(`engine.go:~527-535` chooses `GreedyByScoreOptimizer` vs `CostAwareOptimizer`). The **headline is
correct** — bug #5 is off the default path (limited mode is opt-in) — only the flag name/location is
wrong. Fix the attribution.

### 2.4 IMPRECISE — sort/feed mechanism attribution (`buildCapacityMap`)

> **Update (post-revision): ADDRESSED (moot).** PR-1 plan §10 routes **both** `buildCapacityMap`
> (`cost_aware_optimizer.go:54`) and `allocateForModelPaired` (`:62`) to `req.Anchor.VariantCapacities`.
> Since both now feed the same anchor, which one feeds the sort is no longer load-bearing — the
> original attribution nit dissolves.

The design's conclusion (sort/sizing consume the saturation PRC proxy) is **correct**. The mechanism
attribution is slightly off: the sort reads `satEntry.VariantCapacities` **directly** via the
`variants` parameter threaded into `allocateForModelPaired` (`cost_aware_optimizer.go:62`), not via
`buildCapacityMap`. Cosmetic — fix the reference so the implementer looks in the right place.

### 2.5 IMPRECISE — topology iterator grouping (`modelDemandGPUs`)

> **Update (post-revision): ADDRESSED (moot).** Subsumed by the anchor re-point in PR-1 §10; no
> standalone action remains.

Minor: `modelDemandGPUs` is mis-grouped among the topology iterators in the design's list.
Conclusion unaffected; correct the grouping for accuracy.

---

<a name="s3"></a>
## §3 — Bug assessment (independent reachability)

I re-derived each bug's reachability from the callers, because reachability — not just existence —
determines the 0.9 ship posture.

| Bug | What | Path | Reachable when | Severity |
|---|---|---|---|---|
| **#1** | `allocateForModelPaired` unit mismatch (demand-in-replicas vs PRC-in-tokens) | `cost_aware_optimizer.go:62` (**default**) + `greedy_score_optimizer.go:309` (limited) | ≥2 votes with differing PRC → **TA alongside, default optimizer** | **HIGH** — corrupts the live scale-up decision |
| **#2** | `roleAggRemaining` mixed-unit `max` | `analyzer_helpers.go:370,391`, **inside** `allocateForModelPaired` (default scale-up loop) | same as #1 | **HIGH** — same live path |
| **#3** | rescale water-fill weight uses sat PRC | `engine.go:931` via `RescaleFlags`, `EnableRescale`-gated | ≥2 votes **and** rescale enabled | MEDIUM — opt-in surface |
| **#4** | (design's candidate) RC uses sat PRC as denominator | — | — | **NOT A BUG** — confirmed downgrade (see below) |
| **#5** | `fsv` / fair-share uses sat PRC | greedy/limited optimizer, `EnableLimiter`-gated | ≥2 votes **and** limited mode | MEDIUM — opt-in surface |

> **Update (post-revision): ADDRESSED.** The design now carries the full bug-#4 trace and downgrade
> ("NOT an active *sizing* bug"), and Open-Q #6 lands exactly where I recommended: **no code change**,
> a doc/comment note that the observability `Utilization` remains saturation-proxy-based (harmless).

**Bug #4 downgrade — CONFIRMED (design is right to drop it).** RC =
`max(0, TotalDemand/scaleUp − TotalAnticipatedSupply)`, with pending replicas counted once. The
saturation PRC never appears in a denominator in the RC path. The only residual saturation-PRC use
in that vicinity is the **observability** `Utilization = demand/current-supply`, which does not feed a
scaling decision. Downgrading #4 from bug to non-bug is correct; I'd keep a one-line note that the
observability utilization is still saturation-proxy-based (harmless, but worth stating so a future
reader doesn't "re-discover" it as a bug).

**Ship-posture implication.** The two HIGH bugs (#1, #2) are exactly on the **default cost-aware
scale-up path** and fire the moment a second analyzer with a different PRC is active — i.e. the only
thing a user *can* do today (TA alongside) is also corrupting. That fully justifies the design's
"do not enable TA in 0.9; document it" posture. #3/#5 are additional opt-in surfaces, not the
gating concern.

---

<a name="s4"></a>
## §4 — Confirmed-correct claims

Independently verified and correct (brief — these need no action):

- **§why metadata-carrier role** — saturation's `Result` carries variant identity
  (Cost/AcceleratorName/Role/KV/replica-count) that other analyzers and the optimizer read; nothing
  else supplies it today. Matches `engine_v2.go` + the F1 note in `multi-analyzer-design.md:506-511`.
- **§abstraction / §combine** — replica-demand `rd_i = demand_i/PRC_i`, `desired = max_i ceil(rd_i)`,
  `coverage = min_i cov_i`, `safeRemoval = min_i floor(spare_i/PRC_i)`, veto = all-live-agree. The
  combine rules are internally consistent and match the pipeline helpers.
- **§anchor byte-identity invariant (#7)** — single-vote must be byte-for-byte identical to today.
  Reachable: single-vote keeps saturation as `namedResults[0]` with no second entry, so the anchor is
  a pass-through. Sound.
- **Veto hazard resolution** — `needsScaleDownForRole` (`analyzer_helpers.go:301-313`) iterates the
  live vote list and requires all live analyzers' `RoleSpare>0`; a **truly removed** saturation drops
  out of the veto set, whereas the rejected zero-signal design left `Spare=0` → a permanent veto. The
  design's true-removal choice is the correct fix for this hazard. Confirmed against the rejection in
  `wva-analyzer-lifecycle-plan.md` Commit 2c.
- **Bugs #1/#2/#3/#5 exist and are latent today** — masked only because saturation is the sole
  analyzer (PRC_sat == PRC_i, so the unit mismatch is a no-op at 1 vote).

---

<a name="s5"></a>
## §5 — Cross-doc tension: F1 abandonment vs. the rejection handoff

> **Update (post-revision): ADDRESSED.** The F1 reversal is now surfaced explicitly, not folded in
> silently — at three spots: the design header ("this doc is its missing design"), §anchor L271-277,
> and Open-Q #2 ("F1 'pre-analysis extraction' is **not a prerequisite and not a cost saver**").
> The coordination-doc follow-up (the suspected anticipated-supply-in-denominator issue) is kept as a
> **separate tracked thread**: bug #4's net + Open-Q #3 both route it to `optimizer-coordination-design.md`
> D1/#2, so the anchor refactor does not appear to close it. Both halves of this finding are resolved.

The originating handoff
[`plan__sat-v2-disable-not-working-f1-gap.md`](../session/handoffs/plan__sat-v2-disable-not-working-f1-gap.md)
(lines 76-79, 107-109) records Dean's steer: the real fix is "true removal from `namedResults` (not
zero-signal), **most likely shaped by F1 'Pre-analysis extraction'**" — F1 being the deferred design
to extract variant metadata into a common pre-analysis stack so saturation is "no longer always
first" (`multi-analyzer-design.md:506-511`).

The combined-analyzer design **explicitly abandons F1** ("F1 not needed"): it solves the
`VariantCapacities` sourcing problem via the **anchor** (saturation still runs and populates the
anchor's topology; the anchor carries metadata forward) rather than by extracting a pre-analysis
stack.

**This is a defensible engineering call** — the anchor *does* solve the metadata-sourcing problem the
rejection handoff was worried about, without the larger F1 refactor. But it is a **direction reversal**
of the recorded plan, not a detail. It should be surfaced to Dean explicitly:

> The design supersedes the "F1-shaped fix" direction from the disable-bug handoff. The anchor
> replaces F1 as the metadata-sourcing solution. F1 (pre-analysis extraction) is no longer on the
> critical path for disabling saturation's vote — it reverts to pure future-cleanup.

Also flag the still-open **coordination-doc follow-up** (`optimizer-coordination-design.md` § Open
issues #2): the suspected "anticipated-supply-in-denominator" bug is a *separate* thread from these
five and is not addressed by this design — keep it tracked independently so the anchor refactor
doesn't appear to close it.

---

<a name="s6"></a>
## §6 — Recommendations before locking

**Post-revision status — 5 of 6 addressed by the design revisions + the Type 3 stack; 1 live.**
The strikethroughs below are done; only the first item remains.

1. **[LIVE — §2.1 doc-hygiene] Fix the "TA consumes sat-v2's outputs" claim in the design doc.**
   Two edits, both spelled out in [§2.1](#s2)'s **Fix**: (a) §anchor **L273-275** — swap the
   "consumes … so sat-v2 must run before TA in analyzer order" wording for the independent-producer /
   metadata-carrier reason (the reason PR-1 plan §2 already states correctly); (b) Open-Q #2
   **L619-620** — delete the "(TA even consumes some sat-v2 outputs …)" parenthetical. No
   implementation impact — the false claim never reached the coder.
2. ~~Add §enablement mechanism / resolve the `saturation.Enabled=false` silent-no-op trap.~~
   **DONE** — specified in `ta-anchor-refactor-plan.md` §5 1b/1c + §7 3a (skip removal +
   `effectiveEnabled` default-on gate + anchor re-point + STOP→handoff boundary). See §1 Update.
3. ~~Split "cannot be enabled in any form" into alongside vs. replacing.~~ **DONE** — §2.2 Update.
4. ~~Correct the three imprecise mechanism refs (`EnableLimiter`, sort-feed, `modelDemandGPUs`).~~
   **DONE** — §2.3/§2.4/§2.5 Updates (the last two are now moot via the PR-1 anchor re-point).
5. ~~Keep bug #4 downgraded with an observability note.~~ **DONE** — design §bugs #4 + Open-Q #6
   (doc-note, no code change). See §3 Update.
6. ~~Surface the F1 reversal; keep the coordination-doc anticipated-supply issue tracked separately.~~
   **DONE** — surfaced at three spots; coordination follow-up routed to `optimizer-coordination-design.md`
   D1/#2. See §5 Update.

**Net:** the anchor refactor is the right shape, the 0.9 posture is correct, the enablement mechanism
is now concretely specified, and the decomposition (goldens gate → static PR-1 → dynamic PR-2) is
sound. The design is lockable once the single §2.1 doc-paragraph edit lands.
