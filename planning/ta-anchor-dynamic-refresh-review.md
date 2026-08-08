# ta-anchor-dynamic-refresh (PR-2) — Internal Review

**Type:** 6 (review) · **Status:** DRAFT — **coverage complete**, findings not yet finalized. All **25**
commits reviewed (C1–C5, C7, C8, C6a–C6f, C11, C10, C9a–C9e); PR-2 is code-complete. DRAFT persists per
Type-6 convention until Dean finalizes the findings in discussion — it is not a statement about coverage.
· **Branch:** `ta-anchor-dynamic-refresh`, tip **`a9afb740`** (25 commits, verified by
`rev-list --count`, not a subject compare; base `ta-anchor-refactor-v2@075a208e`, stacked/parallel per §0)
· **Reviewed against:**
[`planning/ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) **at plan revision
`1a116e7a`** §1.1 commit map, §2d score semantics, §4 ship gate, §5 dev-guide map, §6 semantic-pivot
grep · **Reviewer:** internal (this session) · **Date:** 2026-08-06 → 2026-08-08 (rolling).

> **Open at the top level, for Dean, not for the coder:** the **T1-1 `ceil`/`floor` fork** — the frozen
> Type 1 mandates `floor`, the tree ships `math.Ceil` with a written justification. See
> [Finding 64](#finding-64--the-forks-price-was-measured-two-commits-before-the-mitigation-that-narrows-it)
> (the fork was priced on a C6c measurement taken **two commits before C6e shipped the mitigation**) and
> **[Finding 65](#finding-65--the-refresh-landed-mechanism-confirmed-price-narrower-than-either-of-us-said)
> — the refresh has since landed**: re-measured at HEAD, the price is **5 failures of 386 with zero
> eviction rows and a worst delta of −2**, and on the split in Finding 65 that is **2 behavioral specs plus
> 3 seam-expectation updates**, not 9-of-334-with-a-−4. The decision is current now, and it is still Dean's
> — I do not make the call, and the failure counts are the coder's measurement, not mine.

> ⚠️ **C6c was redesigned on 2026-08-07 (plan `1a116e7a`): replica space → GPU space, and `prcRef`
> is gone entirely.** Everything in this review that reasons about `prcRef` is **historical**, and one
> earlier verified claim of mine is now **void and under-warning** (goldens *can* move on site (ii)).
> Read [§ C6c design pivot to GPU space](#c6c-design-pivot-to-gpu-space-plan-1a116e7a--what-in-this-review-is-now-historical)
> **before** using any pre-pivot C6c material here as guidance. Findings 19, 20 and 21 are unaffected;
> Finding 20 was *promoted* into the plan.

**Plan-revision trail.** This review spans plan revisions `62c37c46` → `1a116e7a` (20 revisions
total, 12 of them inside one ~17-hour window on 2026-08-07). Findings are raised against whichever
revision was current when written, and each finding that has since been folded into the plan names
its closing revision inline in its own section. **Re-point this header on every future pass** —
it was itself stale at `62c37c46` by 8 commits until 2026-08-07, the same failure mode Finding 21
documents in the coder. Doc-structure findings about the mission's Type 1/3/6 layering are **out of
reviewer scope** and were handed to the planner in
`session/handoffs/plan__ta-anchor-doc-taxonomy-findings.md`, not recorded here.

## Scope of this pass

Dean authorized a partial review after C1 landed, extended commit-by-commit as the stack progresses
(reviewer owns this file). Sections below are in **landing order**, which is the plan's git order
`C1–C5 → C7 → C8 → C6a–C6b → C6c → C6d → C6e → C6f → C11 → C10 → C9` — the C-labels are stable
identifiers, not a sequence.

Reviewed so far: C1 `680bebdb`, C2 `b106b929`, C3 `50034d15`, C4 `07b8fdb7`, C5 `3c9d45bb`,
C7 `952d2fff`, C8 `1140a4c2`, C6a `8eb6ee2d`, C6b `d9f3b97e`, C6c `34b18bc5`, C6d `330fcd26`.
Still to come: C6e (`W1` fair-share double-spend), C6f (`W4` abstain-when-unpriced), C11
(`FZ-admission`), C10 (`resolveKSat`), C9 (dev-guide + goldens endgame). Each commit is diffed against
**PR-1's tip `075a208e`**, not `main`, and every gate is re-run by me on a clean `git archive` extract
rather than taken from the coder's report.

Three **pre-emptive** sections review the *plan spec* for commits that have not been written yet
(C10 → Finding 6, C6c → Findings 9/10, C6d → Findings 11/12). Each states the checklist I will hold
the commit to when it lands. This is deliberate: a spec error costs a comment now and a rewrite
later, and Finding 6 — already accepted and corrected by the planner in plan tip `62c37c46` — is the
precedent for the pattern paying off.

## Verdict (C1 only)

C1 implements the N2 deterministic binder tie-break correctly and matches the plan's description
exactly (saturation-if-present, else lowest ballot index; later qualifying non-saturation entries
vote without binding). Gates are green, DCO is present, the two-binder fixture is well-constructed
(goes beyond the plan's minimum bar by asserting the tie-break flips when ballot order reverses,
proving the pick is index-driven and not name-driven). One **should-fix** finding: plans-branch
identifiers (`N2`, `PR-2`) leaked into shipped code comments, a test comment, and the commit
subject line, violating CONVENTIONS §4a. Not a correctness defect — recommend fixing before this
commit is pushed to origin (amend, since it hasn't been pushed yet).

## Independently re-verified

- `git branch --show-current` → `ta-anchor-dynamic-refresh`; `git merge-base HEAD
  ta-anchor-refactor-v2` → `075a208e` — confirms C1 is stacked on PR-1's tip, not on `main`, per §0.
- `gofmt -l` over `internal/`, `cmd/` — clean.
- `go build ./...` — clean.
- `go test ./internal/engines/pipeline/... -count=1 -v` — 308 passed, 0 failed (includes the
  existing `[sat]`-only characterization goldens — untouched, still green per §4's "no-op on
  all-live sat-only fixtures" requirement).
- `make test` (full suite) — all packages green.
- `make lint` — 0 issues.
- DCO — commit carries `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
- `grep -rn "bindingAnchor" internal/ docs/developer-guide/` (plan §6 C1 grep) — no stale
  "returns nil on ambiguity" / "sole enabled" wording remains outside the one still-accurate Test 4
  comment (genuine no-binder-at-all hold, unaffected by C1).
- Dev-guide edit lands in `## Pipeline flow` (intro binder-selection sentence) and `## How results
  combine` (~L257) in `multi-analyzer-pipeline.md`, matching plan §5's C1 section assignment
  exactly.
- Red-before-fix logic check (via diff, not re-execution): the old code returned `nil` on
  encountering a second qualifying non-saturation candidate (`if binding != nil { return nil }`);
  the new Test 5 fixture supplies exactly two such candidates, so the pre-fix code would have failed
  the `NotTo(BeNil())` assertion — confirms red-before-fix without needing a working-tree checkout
  on this shared worktree.

## Findings

### Finding 1 (should-fix) — §4a plans-branch token leak into shipped code/commit message

CONVENTIONS §4a requires descriptive prose in shipped code, comments, and commit messages — no
plans-branch section identifiers (the doc's own examples are `Fnn`/`Ann`/etc.; the dataflow-map's
`N1`–`N9` finding labels are the same class of identifier). C1 leaks `N2` (the dataflow-map finding
label) and `PR-2` (the internal stack-position label, not a real GitHub PR number) into:

- `internal/engines/pipeline/analyzer_helpers.go:146` — `"(N2 deterministic tie-break): once PR-2 admits..."`
- `internal/engines/pipeline/analyzer_helpers_test.go:328` — `"...remain after N2's deterministic tie-break..."`
- `internal/engines/pipeline/analyzer_helpers_test.go:365` — `"Test 5 — N2 deterministic binder tie-break..."` / `"PR-2 admits multiple..."`
- `internal/engines/pipeline/optimizer_interfaces.go:54` — `"...the lowest ballot index binds (N2)."`
- Commit subject: `pipeline: deterministic binder tie-break for multi-vote ballots (N2)`

The dev-guide edit in `multi-analyzer-pipeline.md` is clean (uses "the deterministic tie-break"
prose throughout, no leaked labels) — the leak is confined to code/test comments and the commit
subject.

**Suggested reword** (descriptive prose, no identifier): replace `"(N2 deterministic tie-break)"` /
`"(N2)"` with `"(deterministic tie-break)"`, and `"once PR-2 admits multiple non-saturation
voters"` / `"PR-2 admits multiple non-saturation voters"` with `"once multiple non-saturation
voters are enabled"`. Commit subject → `pipeline: deterministic binder tie-break for multi-vote
ballots`.

**Fix mechanism:** this commit hasn't been pushed to origin yet (worktree is 12 commits ahead / 10
behind `origin/ta-anchor-dynamic-refresh`, i.e. locally rewritten already), so amending `680bebdb`
in place is available and is the cleanest fix — no separate "fixup" commit needed. Coder's call to
apply before continuing to C2, or batch with other rewording; either way it should land before this
reaches origin.

## Verified-correct (not a finding — confirms a pre-existing, already-tracked item)

`rescale.go:342` (`rescaleModelDecisions`) dereferences `anchor.VariantCapacities` immediately after
`bindingAnchor(...)` with no local nil-guard. This matches dataflow-map **N3** exactly (line
`:342-344`, "confirmed / fragile") and the commit map's own note that N3's nil-guard hardening
**rides C5**, not C1. C1 does not change whether this call site is reachable on a nil anchor — it
only removes one of the three nil-return branches (the ambiguous-tie case), which was never on this
call site's reachable path under either PR-1 or C1's ballots — so this is pre-existing, already
scoped, and not a C1 regression. No action needed now; will re-check when C5 lands.

Two other call sites (`cost_aware_optimizer.go:257`, inside `buildDecisionsWithOptimizer`) dereference
`anchor` without an *adjacent* nil-check, but the actual field access (`anchor.RequiredCapacity` /
`anchor.RoleCapacities`) is correctly guarded by `if anchor != nil` a few lines later inside the loop
body (line 304) — pre-existing PR-1 pattern, untouched by C1, no bug.

## Outstanding for this branch (not blocking C1)

- C2–C9 not yet reviewed (plan §1.1); will extend this doc per commit as they land.
- Finding 1 should be resolved before push; re-verify the grep list in plan §6 is clean after the
  reword.

---

## C2 — `pipeline: per-iteration dynamic refresh of the anchor's binder` (`b106b929`)

**Verdict:** Correct, and matches plan §3's "re-run the getter each iteration" contract via the
plan's own explicitly-sanctioned alternative ("mutating a stored cell in place" as an
implementation detail — plan §3 says correctness is identical either way). `refreshAnchorSizing`'s
per-(role,variant) argmax (`bindingIndexForRole`) is a deliberate mirror of `roleBottleneckReplicas`
— same `max_i ceil(state[i][role]/PRC_i[v])` computation, so the two can never disagree on which
entry wins. Hooks into the existing `for anyRoleNeedsScaleUp` loop head and the pre-existing
`sortByCostEfficiencyAsc`-in-closure seam exactly as plan §3 describes — no new outer loop. Found
and fixed a real pre-existing bug along the way (`CostAwareOptimizer.Optimize`'s `vcMap` snapshot
taken before the allocation loop, so the refresh's mutations never reached the decisions —
`GreedyByScoreOptimizer` already snapshotted after). One **repeat** should-fix finding (Finding 2,
same class as Finding 1).

**Design-ambiguity note (resolved via AskUserQuestion with Dean before coding, per the coder's
outbox):** C1's tie-break (sat-if-present else lowest index) and C2's per-iteration refresh
(magnitude-based `argmax_i rd_i`) are two distinct, composable mechanisms — C1 governs the anchor's
*initial* single (b)-source pick and genuine ties; C2 overrides sizing every iteration for
`len(voting)>1` based on current remaining demand, independent of ballot position except as its own
tie-break. Confirmed by reading both functions: identical max-finding loop, `bindingIndexForRole`
tracks the winning index with a strict `>` so ties resolve to the lowest index, exactly like
`roleBottleneckReplicas`' `max` never needing tie-break tracking of its own.

### Independently re-verified

Since the working tree was already mid-edit on C3 when this review ran, verification used
`git archive b106b929 | tar -x` into a scratch directory rather than touching the shared worktree
(no `checkout`/`stash` on a live coder session):

- `go build ./...` on the isolated C2 snapshot — clean (the working tree's live `go build` failure
  at the time was C3-in-progress's `roleAggRemaining` signature change, not a C2 defect — confirmed
  by diffing against the isolated snapshot).
- `gofmt -l` — clean. `make lint` equivalent (`golangci-lint run`) — 0 issues.
- `go test -race -count=1 ./internal/engines/pipeline/...` — PASS.
- Full `go test ./internal/... ./cmd/...` — all packages green.
- DCO — `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` present.
- Traced Test 9's updated numbers by hand: sat `Remaining=5000`/PRC=10000 → `ceil=1`; throughput
  `Remaining=25000`/PRC=10000 → `ceil=3`; throughput wins the (role,v) argmax and becomes the sizing
  binder, so `Utilization` comes from throughput's zero-value field → `0`, matching the golden's
  updated `want`. Replicas/RC/SC unaffected (per-analyzer, not part of the (b) refresh) — correctly
  left at the pre-C2 values.
- Confirmed `refreshAnchorSizing`'s `len(s) <= 1` no-op check operates on `votingResults(...)`'s
  Enabled-only filter (current, pre-C7 semantics) — consistent with the rest of the pre-C7 codebase;
  not a new gap (C7's VG-up already covers tightening this to `Enabled && Live`).
- Confirmed the `variants` slice threaded into `refreshAnchorSizing` and into each role's `pick(...)`
  call within the same `allocateForModelPaired` iteration is the same backing array (`anchor.VariantCapacities`), so `pick`'s `sortByCostEfficiencyAsc` sees the refreshed values immediately, not one
  iteration stale.
- Confirmed no §6 grep step is specified for C2 (plan §6 lists C1/C3/C4/C6/C5/C7/C8 only) — matches
  the coder's note; a bounded sanity grep for stale "static/one-time anchor" language turned up
  nothing.
- Dev-guide touches land exactly where plan §5 assigns C2: the "Data flow per optimize cycle" ASCII
  box (one line) and "### Scale-up path" (pseudocode + new paragraph) in `multi-analyzer-pipeline.md`.

### Finding 2 (should-fix, repeat of Finding 1) — more §4a leaks

Same class as Finding 1, now in a second commit — `N2`, `PR-2`, and `C2` (planning-stack labels)
leaked into shipped code/test comments:

- `internal/engines/pipeline/analyzer_helpers.go:351` — `bindingIndexForRole` doc-comment: `"...mirroring bindingAnchor's own tie-break (N2). Returns -1..."`
- `internal/engines/pipeline/optimizer_dynamic_refresh_test.go:3` — package comment: `"Per-iteration dynamic refresh (PR-2 C2): refreshAnchorSizing recomputes the..."`
- `internal/engines/pipeline/optimizer_dynamic_refresh_test.go:14,17` — `"Before C2, refreshAnchorSizing does not exist..."` / `"...is red before C2... and green after."`
- `internal/engines/pipeline/optimizer_combine_characterization_test.go:42,104` — `"...saturation's (PR-2 per-iteration refresh; ...)"` / `"Utilization=0 is PR-2's per-variant sizing refresh..."`

Dev-guide again stays clean (no leaked labels) — confirms the leak is specifically a code/test-comment
habit, not a documentation one. Given this is now 2-for-2 commits, recommend the coder add a standing
pre-commit check — `grep -rnE "\bN[0-9]+\b|\bPR-[12]\b|\bC[1-9]\b" internal/ docs/developer-guide/` (hand-filter `C[1-9]` hits against legitimate uses like "C100" GPU counts) — rather than relying on
catching it commit-by-commit in review. Same fix mechanism as Finding 1: both commits are still
unpushed local history, so amending in place remains available.

## Outstanding for this branch (not blocking C1/C2)

- C3–C9 not yet reviewed.
- Findings 1 and 2 (§4a leaks, 7 locations across 2 commits) should be resolved before push —
  recommend batching the reword into one pass across both commits (or squash-fixup) rather than two
  separate amends, since Dean/coder may prefer to defer the whole cleanup to right before push.

---

## C3 — `pipeline: compare roleAggRemaining in replica space, not raw units (Bug #2)` (`50034d15`)

**Verdict:** Correct, and a clean §4a pass (zero leaked plans-branch identifiers — first commit on
this branch without a Finding-1/2-class hit). Reuses C2's `bindingIndexForRole` rather than
duplicating the argmax loop — one source of truth for "who's the (role,v) bottleneck," and it
guarantees `roleAggRemaining`'s selected entry is always the *same* entry `roleBottleneckReplicas`
and the anchor's own `refreshAnchorSizing` (C2) pick for the same `(role, v, pickerState)` snapshot,
since all three now route through the identical max-finding loop.

**Design nuance worth recording (not a defect):** the plan/design-doc shorthand for this bug
("compare in replica space, `max_i rd_i`, `roleBottleneckReplicas`-style") could be read as "return
a replica-count," but the commit instead returns the *winning entry's own raw remaining* (native
units — tokens or req/s) rather than a converted replica count. Traced why this is still correct:
the caller's `utilByRole = n·prc/demand` and `k = floor(deltaUtil·demand/prc)` need `demand`
commensurable with `prc`, and `prc` is `prcFromVCs(variants, v)` — the anchor's own PRC field, which
C2's `refreshAnchorSizing` already set from the *same* winning entry (same `bindingIndexForRole`
call, same `pickerState` snapshot, no decrement happens between the two calls within one iteration).
So `demand/prc` = `state[idx][role]/PRC_idx[v]` exactly — the unceiled replica-space ratio for the
winning entry — without introducing an extra rounding step that pre-computing `ceil(...)` and
reusing it would have. This is arguably more numerically precise than the literal "return
`max_i rd_i`" reading, not a deviation from intent.

### Independently re-verified

Working tree was mid-edit on C4 again; used the same `git archive 50034d15 | tar -x` isolation
approach.

- `go build ./...`, `gofmt -l`, `golangci-lint run` — all clean on the isolated snapshot.
- `go test -race -count=1 ./internal/engines/pipeline/...` — PASS.
- DCO — present (checked via `git -C ta-anchor-dynamic-refresh log`, since the archived snapshot has
  no `.git`).
- `grep -rn "roleAggRemaining\|PRC_sat\|k·prc\|fairShareValue\|fairShareCap"` (plan §6 C3/C4/C6 grep)
  — the only hits are `fairShareValue`/`fairShareCap` (C6's still-unfixed scope, correctly untouched
  by this commit) and the new `roleAggRemaining` call sites/tests themselves; no stale "raw max"
  language remains.
- Confirmed single-voter byte-identity: with `len(s)==1`, `bindingIndexForRole` always resolves to
  index 0 (when PRC>0), so `roleAggRemaining` returns `state[0][role]` — the same value the old
  `max` loop produced over one element. Covered by its own test.
- The two-vote MAX fixture (sat Remaining=100/PRC=1 vs. throughput Remaining=5000/PRC=1000) correctly
  asserts the replica-space winner (sat, rd=100) over the raw-value-larger loser (throughput,
  rd=5) — this is the red-before-fix case the old code got backwards.

**Process note (not a finding — confirms correct handling of a plan gap):** the coder found that the
plan's §5 dev-guide target for C3 (`saturation-scaling-config.md` "#### Shared aggregation helpers")
documents the unrelated single-analyzer `internal/engines/aggregation` package, not the optimizer's
cross-analyzer `roleAggRemaining`. Swept the doc for a better-fitting section, found none, and
correctly declined to force an edit into the wrong place — landing only the accurate
`multi-analyzer-pipeline.md` pseudocode-line fix instead. This is the right call per
CODER-CONVENTIONS §3's semantic-pivot-grep spirit (don't infer scope, flag the gap) — recommend the
planner correct plan §5's C3 citation (either point at `multi-analyzer-pipeline.md` only, or note
that `saturation-scaling-config.md` has no home for this content yet).

## Outstanding for this branch (not blocking C1/C2/C3)

- C4–C9 not yet reviewed (C4 in progress in the working tree as of this pass).
- Findings 1 and 2 (§4a leaks, C1+C2 only) still outstanding — recommend one batched reword pass.
- Plan §5's C3 dev-guide citation should be corrected (see process note above) — a planner-side fix,
  not something to block the coder on.

---

## C4 — `pipeline: decrement each analyzer by its own PRC, not the anchor's (Bug #1)` (`07b8fdb7`)

**Verdict:** Correct, clean §4a pass (second in a row), and the narrowest possible fix — touches only
the decrement loop, leaves the (correct, binder-PRC-based) `k`-sizing computation above it untouched.
Mirrors the pre-existing `applyAllocation` per-analyzer-PRC pattern exactly (`prcForVariant` lookup,
skip on `Result == nil` or `prc <= 0`, `math.Max(0, ...)` floor) — same helper, same defensive
shape, zero new patterns introduced.

### Independently re-verified

- `go build ./...`, `gofmt -l`, `golangci-lint run`, `go test -race -count=1 ./internal/engines/pipeline/...` on an isolated `git archive 07b8fdb7` snapshot — all clean/PASS.
- DCO present; zero leaked plans-branch identifiers in the diff.
- Hand-traced the new fixture's numbers against the fixed code: sat (remaining=100, PRC=10) vs.
  throughput (remaining=500, PRC=100) for variant "v". Binder: `rd_sat=ceil(100/10)=10` beats
  `rd_ta=ceil(500/100)=5`, so the anchor's PRC for "v" is sat's (10). `n=min(roleBottleneckReplicas=10,
  capN=MaxInt)=10`; `demand=roleAggRemaining(...)=100` (sat's own remaining, per C3); `utilByRole =
  10*10/100 = 1.0`; single role so `deltaUtil=1.0`; `k=floor(1.0*100/10)=10`. Decrement: sat
  `100-10*10=0`; throughput `500-10*100=-500→clamped 0`. Both clear in one iteration, `targets["v"]=10`
  — matches the fixture's assertions exactly.
- Confirmed the pre-fix failure mode algebraically: with the old uniform-PRC decrement, throughput
  would have been decremented by `10*10=100` (the anchor's PRC, not its own), leaving
  `500-100=400 > 0` — the loop would keep iterating and over-allocate. This is the "spurious extra
  iterations" the commit message and fixture comment both describe; confirms red-before-fix without
  needing to check out the parent commit.
- Dev-guide addition (`multi-analyzer-pipeline.md`, one pseudocode line + one paragraph under
  "Scale-up path") matches plan §5's C4 assignment.

No findings for C4.

## Outstanding for this branch (not blocking C1–C4)

- C5–C9 not yet reviewed.
- Findings 1 and 2 (§4a leaks, C1+C2 only — C3 and C4 both clean) still outstanding; recommend one
  batched reword pass before push.
- Plan §5's C3 dev-guide citation should be corrected (planner-side, not blocking).

---

## C5 — `pipeline: combine rescale's demand-to-GPU conversion across voters (Bug #3)` (`3c9d45bb`)

**Verdict:** Correct, and lands exactly the three things plan §2 #3 + §7 N3 called for in one
coherent commit: (1) `roleDemandGPUs` now takes `max_i ceil(demand_i[role]/PRC_i[v*])` over the
voting entries instead of reading only the anchor's (binder's) demand; (2) the water-fill weight
(`rescaleInput.Demand`) switches from the anchor's native-unit `TotalDemand` to the already-computed
GPU-unit `modelDemandGPUs` result — same number now feeds both `CapGPUs` and the weight, so there's
no second incommensurable quantity to drift; (3) the N3 nil-guard lands on `rescaleModelDecisions`,
closing the fragile-pre-filter-only gap I flagged as verified-correct-but-tracked back in the C1
review. `fillRole`'s cost-efficiency sort and `sortVariantsForScaleDown` are correctly left
untouched — plan §2 #3 says the variant-selection sort stays binder-based (collapses to today for
one analyzer), only the demand *aggregation* needed the multi-voter fix.

### Independently re-verified

- `go build ./...`, `gofmt -l`, `golangci-lint run`, `go test -race -count=1 ./internal/engines/pipeline/...` on an isolated `git archive 3c9d45bb` snapshot — all clean/PASS.
- DCO present.
- Hand-traced the new two-vote fixture: `v*="A-v"` (only variant on A100, PRC=1000 for both entries).
  sat demand=8500 → `ceil(8500/1000)=9`; throughput demand=25000 → `ceil(25000/1000)=25`. `max(9,25)=25`
  matches the fixture's expectation — confirms the old anchor-only code would have wrongly returned 9
  (sat's own value, since sat is passed as `anchor` directly in this test), understating the true GPU
  need by more than half.
- Confirmed single-voter byte-identity holds: with one voter, that voter *is* the anchor's binder, so
  `anchor.VariantCapacities[v*].PerReplicaCapacity` and `prcForVariant(soleVoter.Result, v*)` are the
  same value by construction (`bindingAnchor`'s own merge) — the pre-existing test (now updated to
  pass `s` explicitly) still asserts the unchanged `9` result for the single-voter case.
- `roleCapacities`-role branch (non-`"both"`) correctly `continue`s past a voting entry with no data
  for that role rather than treating a map-miss as zero demand — consistent with
  `roleBottleneckReplicas` skipping a zero/absent PRC elsewhere.
- Plan §6 C5 grep (`satEntry.TotalDemand|roleDemandGPUs|rescaleModelDecisions`) — no stale
  "saturation's demand"-only language remains; every touched call site and comment now describes the
  combined, multi-voter semantics.
- Dev-guide gains a new "### Rescale pre-pass" subsection under "Fair-share iteration" — matches plan
  §5's C5 assignment ("Optimizer internals" / rescale combined demand + N3 nil-guard), and explicitly
  documents both fixes plus the nil-guard rationale.

### Finding 3 (should-fix, repeat of Findings 1/2) — one more §4a leak

`internal/engines/pipeline/rescale.go:348` — `// N3: every sibling topology helper (...)`. Same class
as Findings 1/2 (a dataflow-map finding label leaked into a shipped code comment); the dev-guide's
own N3 explanation (multi-analyzer-pipeline.md, "Rescale pre-pass" section) is clean prose with no
leaked label, so — as with C1/C2 — this is purely a code-comment habit. Suggested reword: drop the
`"N3: "` prefix and let the sentence stand on its own ("Every sibling topology helper... already
nil-guards its own call; this one was safe only via `applyRescale`'s pre-filter — a fragile coupling
this closes."). Now 3 commits with a leak (C1, C2, C5) vs. 2 clean (C3, C4) — the standing
pre-commit grep suggested after Finding 2 would have caught this one too.

## Outstanding for this branch (not blocking C1–C5)

- C6–C9 not yet reviewed.
- Findings 1–3 (§4a leaks, 8 locations across C1/C2/C5) outstanding — still recommend one batched
  reword pass (plus adding the standing grep to the coder's own pre-commit routine) before push.
- Plan §5's C3 dev-guide citation should be corrected (planner-side, not blocking).

---

## C7 — `pipeline: liveness-gate the voting set and drop the sizing fallback` (`952d2fff`)

C6 (fair-share) is paused on an open design question (Score's treatment — coder's `plan__` handoff,
relayed separately); the coder moved to C7 in the meantime, per plan §0's "not a standalone
micro-PR" framing this is independent of C6's fair-share formula question.

**Verdict:** The three §2b fixes (VG-up, N8, N7) are each implemented correctly and match the plan's
literal scope exactly — single-gate centralization in `votingResults` (`Enabled` → `Enabled && Live`),
full removal (not a `.Live`-gating) of the `bindingAnchor` sizing-fallback branch, and an
abstain/veto distinction in `needsScaleDownForRole` via `RoleSpare[role]`'s comma-ok form. PR-1 Test
2 rewritten exactly as the plan anticipated (v2 110→0). Found and correctly handled a **second**
dev-guide citation mismatch (sat-config "How Scale-Up Triggers Work" is explicitly V1-only,
unrelated to V2's `votingResults`) — I independently confirmed the section header and its "Applies
to V1 only" callout; the coder's redirect to "Saturation as the Identity Carrier" (which the plan
*did* cite correctly) is the right fix. Also caught and fixed a dev-guide passage that was **actively
wrong** post-VG-up (the old "liveness gate does not apply to scale-up" claim, resting on an
invariant this exact commit stops relying on) — good catch, verified against the diff.

However, this is also the first commit with two real gaps: a plausible correctness bug in a sibling
function N7 didn't touch, and by far the largest §4a leak batch so far (the first to reach the
dev-guide, not just code/test comments).

### Independently re-verified

- `go build ./...`, `gofmt -l`, `golangci-lint run`, `go test -race -count=1 ./internal/engines/pipeline/...` on an isolated `git archive 952d2fff` snapshot — all clean/PASS. DCO present.
- Hand-traced the new VG-up fixture: saturation (RC=0, live) + throughput (RC=100000, **Enabled but
  not Live**). Confirmed `roleBottleneckReplicas`/`roleAggRemaining`/`initRoleState` have no `.Live`
  check of their own — they trust whatever `votingResults` hands them — so pre-fix, the stale
  throughput entry would size a `ceil(100000/PRC)`-replica scale-up; post-fix, `votingResults`
  excludes it before `initRoleState` ever sees it. Confirms VG-up is a genuine single-point fix, not
  cosmetic.
- Hand-traced both `needsScaleDownForRole` fixtures (mixed P/D + non-disaggregated ballot): a
  non-disaggregated live voter's `RoleSpare` map, after `initRoleState`, has only a `RoleBoth` key —
  asking it about `"prefill"` now correctly abstains (comma-ok `false`) rather than reading the
  zero-value as `Spare == 0` and vetoing.
- Confirmed the "non-nil anchor ⟹ non-empty voting set" invariant holds structurally: `bindingAnchor`'s
  binder gate (`Enabled && Live && Informative`) is strictly stronger than `votingResults`' new
  `Enabled && Live` — no code path can produce a non-nil anchor from an empty voting set.
- Confirmed `bindingAnchor`'s call sites still pass the **full** `req.AnalyzerResults`, never
  `votingResults`' pruned output (the plan's explicit caveat) — unchanged from prior commits.
- Ran both plan §6 C7 greps; the second (`satEnabled|fallback|(b)-fallback|borrow`) is extremely
  broad (matches the generic English word "fallback" used unrelatedly ~150+ times across the
  codebase) — filtered to the `bindingAnchor`-sizing-fallback-specific hits only, all of which
  correctly describe the post-N8 state (no stale "borrows saturation's own (b)" claims remain).

### Finding 4 (should-fix, plausible bug) — `safeRemovalReplicasForRole` has the same map-miss-as-veto pattern N7 just fixed in its sibling, unaddressed

N7 fixed `needsScaleDownForRole` (`analyzer_helpers.go`) so a live voter with no opinion on a role
abstains instead of reading `RoleSpare[role]`'s map-miss as `0` and vetoing. `safeRemovalReplicasForRole`
(`analyzer_helpers.go:488-511`) — the MIN-computation used to size *how many* replicas are safe to
remove once scale-down is already gated "yes" — has the identical bug, unfixed:

```go
n := int(math.Floor(e.RoleSpare[role] / prc))  // map-miss on `role` silently reads as 0.0
if n < smallest {
    smallest = n  // caps the safe-removal count to 0 for a role this voter never sized
}
```

Concrete failure scenario (the same mixed-ballot shape the new N7 test already exercises): saturation
is disaggregated (`RoleSpare[prefill]=20000`), throughput is non-disaggregated (only
`RoleSpare[RoleBoth]` after `initRoleState`, no `"prefill"` key) and *does* carry a positive PRC for
the variant being sized. `needsScaleDownForRole(s, "prefill")` now correctly returns `true` (throughput
abstains, saturation alone decides). But `safeRemovalReplicasForRole(s, v, "prefill")` still includes
throughput in the MIN: `e.RoleSpare["prefill"]` map-misses to `0.0`, `floor(0/prc)=0`, and since
`found=true` gets set anyway, the function returns `0` — capping the safe-removal count to zero even
though the gate that was supposed to authorize this removal already excluded this exact voter's
opinion. Net effect: scale-down is gated "safe" but then sized to remove nothing, in the same
manner N7 fixed the boolean gate against.

Checked `safeRemovalReplicasForRole`'s existing 4 tests (`analyzer_helpers_test.go:570-597`) — none
covers a **live** second voter with `RoleSpare` non-nil but missing the queried role's key (the
existing "non-live" test is excluded before reaching this code path; the "RoleSpare is nil" test
hits a different guard). This exact scenario is genuinely untested.

This is outside C7's literal scope — plan §1 item 5 / §2b's N7 text cites only
`needsScaleDownForRole:445-457` by name and line, not this sibling — so it isn't a regression in
this commit, but it's the same bug class, in the same file, in the function this commit's own
`needsScaleDownForRole` fix is paired with at every call site. Recommend folding into a follow-up
commit (natural fit: same shape as N7's fix, `if ok, spare := e.RoleSpare[role]; !ok { continue }`)
rather than filing separately, given how directly it parallels what C7 just did next door.

### Finding 5 (should-fix, larger repeat of Findings 1–3) — §4a leaks, now including the dev-guide

11 new leaked plans-branch labels (`N7`, `N8`, `PR-2 C7`) — and for the first time, 2 of them are in
the **dev-guide**, not just code/test comments (Findings 1–3 were all code-only):

- `internal/engines/pipeline/analyzer_helpers.go:119,214,542,560`
- `internal/engines/pipeline/analyzer_helpers_test.go:147,187`
- `internal/engines/pipeline/optimizer_liveness_test.go:3,10,75`
- `docs/developer-guide/multi-analyzer-pipeline.md:265,395`

Combined with Findings 1–3, that's **19 leaked-label locations across 4 of 7 landed commits** (C1,
C2, C5, C7 — C3, C4 clean). The standing-grep suggestion from Finding 2 clearly hasn't been adopted
yet; recommend actually wiring it in before C8 (which is comment-heavy and touches these same files,
so it's the natural place to sweep everything at once — see below) or before push at the latest.

**Silver lining:** C8 (in progress as of this pass, per the coder's outbox) is a comment-only
notation-cleanup commit scoped to exactly the files carrying most of these leaks
(`analyzer_helpers.go`, `optimizer_interfaces.go`, both dev-guides, `analyzer_helpers_test.go`) —
but its plan §2c scope is specifically the `(a)/(b)` letters, not the `N`/`F`/`PR-n` finding-label
class of leak. Worth explicitly asking the coder to fold Findings 1–5's reword into the same pass
rather than assuming C8 covers it incidentally.

## Outstanding for this branch (not blocking C1–C7)

- C6 paused on the fairShareValue/Score design question (separate thread).
- C8–C9 not yet reviewed.
- Finding 4 (safeRemovalReplicasForRole map-miss gap) — recommend a follow-up commit near C7/N7.
- Findings 1–5 (§4a leaks, 19 locations across C1/C2/C5/C7) — recommend one batched reword pass,
  explicitly including it in C8's scope rather than assuming C8 covers it.
- Plan §5's C3 dev-guide citation should be corrected (planner-side, not blocking).

---

## C8 — `docs: strip (a)/(b) notation, keep the descriptive prose` (`1140a4c2`)

**Verdict:** Correct, and exactly as advertised — comment/doc-comment/test-description-only,
byte-identical behavior. Confirmed by grepping every changed line in `internal/` and rejecting the
diff unless each hunk is either a full comment line or a comment/description fragment attached to
an unchanged code statement — every hit matched that shape, none touched an executable statement,
struct field value, or assertion. `grep -rnE "\((a|b)\)" internal/ docs/developer-guide/` now
returns zero hits for the anchor-refactor's `(a)/(b)` notation (the handful of remaining `(a)`/`(b)`
matches elsewhere in the repo — `quota-limiter.md`, `gpurebalance/plugin.go`, math variable names —
are pre-existing, unrelated enumerations, not this notation).

**As anticipated:** this did **not** sweep up Findings 1–5's leaked `N`/`PR-n` labels — confirmed
still present at every location listed above, byte-for-byte unchanged. C8's plan §2c scope was
always specifically the `(a)/(b)` letters, a different (though adjacent) cleanup; flagging again
since C8 was the natural place it could have ridden along for free and didn't.

### Independently re-verified

- `go build ./...`, `gofmt -l`, `golangci-lint run`, `go test -race -count=1 ./internal/engines/pipeline/...` on isolated `git archive 1140a4c2` snapshot — clean/PASS. DCO present.
- One unrelated pre-existing `N2` hit noticed in `greedy_score_optimizer_test.go:1303` while re-running
  the leak grep — `git blame` traces it to `09e1c386` (2026-06-10, pre-dates this PR-2 branch and even
  the anchor-refactor mission). Not a Finding-5 instance; excluded from the count.

No new findings for C8 itself.

## Outstanding for this branch (not blocking C1–C8)

**Scope grew after C8** (plan tip `588e3020`, 2026-08-07): the paused C6 was answered as new plan §2d
and split into **C6a–C6d**, and a new **C10** (§2e, TA k_sat) was folded in. Remaining commits, in git
order: **C6a → C6b → C6c → C6d → C10 → C9**. C-labels are identifiers, not sequence.

- **Finding 4 is now in-scope, not a follow-up.** Plan §2d.3's `votesFromRoleSpare` collector applies a
  participation filter that includes *"its own state present"*, and §2d.4 (c) states the intended rule
  outright — `RoleSpare == nil` or key missing ⇒ **abstain**; key present and `<= 0` ⇒ **veto**. That is
  exactly the map-miss-as-veto gap I flagged. Verify it in C6a/C6d rather than re-raising it; if the
  collector lands without the missing-key exclusion, Finding 4 survives and becomes blocking for C6d.
  Note the two are adjacent but *opposite* directions and both must hold: absent-key + PRC ⇒ abstain
  (my Finding 4), present-zero + no PRC ⇒ veto (plan finding (c)).
- **Findings 1–5 (§4a leaks, 19 locations) still unswept** after 8 commits. Five more commits are
  coming, three of them comment- and doc-heavy (C6a's helper doc-comments, C10's re-anchored prose,
  C9's dev-guide). Re-run the leak grep on each; the batch reword still needs an explicit pass before
  push.
- Plan §5's C3 dev-guide citation should be corrected (planner-side, not blocking).

### What each remaining commit must be checked against

- **C6a** (`combineVotes` + collectors) — the load-bearing claim is *uniform scores ⇒ byte-identical*.
  Check by re-deriving, not by trusting green tests: with all `Score` equal every `(sᵢ − s_e)⁺` is 0, so
  `v*` must reduce to the plain extremum. `bindingIndexForRole` must be **deleted** (not left as a
  wrapper) and its callers take `combineVotes`' second return. Plan §2d.3 has a standing instruction
  that if a landed C3/C4/C5 fix disagrees with the extracted core, the coder must **stop and write a
  `plan__` handoff** rather than re-decide inside C6a — so a silent expectation change in a C3/C4/C5
  fixture here is a finding, not a cleanup.
- **C6b** (dominance weighting) — verify the formula as written, the four listed invariants
  (uniform ⇒ extremum; dominant score ⇒ that analyzer's vote; bounded to `[min, max]`; monotone), and
  that rounding happens **once at the call site** (`ceil` up / `floor` down), never per element. The
  plan's own worked examples are the fixtures to reproduce by hand: 10-vs-5 @ scores 1/2 ⇒ 8.33 ⇒ **9**
  up, and the mirror ⇒ 6.67 ⇒ **6** down.
- **C6c** (Bug #5 fair share) — the highest-risk commit of the five. Four sites must move in lock step
  (`fairShareValue` / `fairShareCap` / `sortVariantsForScaleDown` / `allocateForModel`'s picker-state
  clamp); Score must leave fsv *and* the scale-down tie-break; finding (b)'s PRC participation filter
  must be present. T1.4 is a **rewrite, not a retirement**. Plan §2d.5 forbids rewriting a golden to
  accommodate this change — if a #1513 golden moves, that is a stop-and-handoff, so check the goldens
  independently rather than accepting a "goldens updated" hunk.
- **C6d** (finding (c)) — role-level objection with no per-variant PRC blocks removal; must not
  regress C7's N7 abstain for the genuinely-absent case. This is where Finding 4 gets confirmed or not.
- **C10** (TA k_sat) — `resolveKSat` + 4 threaded sites, `DefaultKSat` **deleted** (grep to zero),
  fallback `DefaultKvCacheThreshold` (0.80, deliberately *not* 0.85), `DefaultNearKSatMargin` retained.
  The moved TA expectations are the real check: plan §2e.3 says **re-derive from
  `N_dec_sat = kSat × KV_max / KVreq`, do not re-baseline to what the code now prints** — so verify a
  sample of the ~6% shifts arithmetically by hand. Also verify the new `internal/config` import into
  `throughput` introduces no cycle, and that the `TODO: unify with the system-wide k_sat used by the
  EPP` moved onto `resolveKSat` rather than being deleted with the constant.
- **C9** (dev-guide + goldens endgame) — the #1513 sat-only goldens may only be relaxed/removed *after*
  multi-vote goldens demonstrably cover the single-vote sub-case. Check that coverage claim directly;
  this is the commit where a real regression could hide behind a deleted test.

---

## Pre-emptive — C10 not yet written

### Finding 6 (should-fix, plan-side arithmetic error that will propagate into C10) — §2e.3's "~5.9%" is numerator-only; the real shift is ~0.5%, and the re-derivation instruction as written produces wrong expectations

Plan §2e.3 states: *"TA now evaluates capacity at 0.80 instead of 0.85 ⇒ PRC **↓ ~5.9%** ⇒ TA's replica
vote **↑ ~6%**"*, and instructs the coder to *"**Re-derive each moved expectation** from
`N_dec_sat = kSat × KV_max / KVreq`; do not re-baseline to whatever the code now prints."*

`5.9%` is exactly `1 − 0.80/0.85`, i.e. the change in the **numerator alone**. But `kSat` enters the
per-replica capacity **twice**, not once — `computeVariantSupply` divides by `itlSat`, which is
`model.ITLAt(kSat) = A·kSat + B`, computed at the same `kSat` (`analyzer.go:295` feeds `:719`):

```
μ_dec_sat(k) = (k · KV_max / KVreq) / (A·k + B)

μ(0.80)/μ(0.85) = (0.80/0.85) · (A·0.85 + B)/(A·0.80 + B)
                   └ 0.9412 ┘   └────── > 1 whenever A > 0 ──────┘
```

Lowering `k` shrinks the numerator **and** the ITL denominator, so the two effects largely cancel.
`validITLModel` requires `a > itlSlopeEpsilon` (`itl_model.go:9`, `1e-12`), so `A > 0` always holds for a
model that reaches this code — the `A → 0` case where 5.9% would be correct is *structurally rejected*.

**Against the shipped fixture** (`analyzer_test.go:264-273`: `A=0.073`, `B=0.006`, `KV_max=1024000`,
`KVreq=4600`):

| | `N_sat` | `ITL_sat` | `μ_sat` |
|---|---|---|---|
| k=0.85 (today) | 189.2174 | 0.06805 | **2780.56** |
| k=0.80 (post-C10) | 178.0870 | 0.06440 | **2765.33** |

Actual shift: **−0.548%**, not −5.9% — off by a factor of ~11. Sensitivity in `r = B/A`: the drop rises
monotonically from **0%** at `r=0` (pure-slope ITL: `μ = KV_max/(KVreq·A)`, wholly independent of `k`) to
5.882% only as `r → ∞` (flat ITL, rejected). With `B ≈ DefaultBaselineITLSec = 0.006` and slopes "order
1e-2" (the code's own characterization), `r ≈ 0.06–0.6` ⇒ a realistic **0.4%–2.5%** drop. The fixture sits
at `r = 0.0822`.

**Two consequences, both live:**

1. **The re-derivation instruction is a trap as written.** It names only
   `N_dec_sat = kSat × KV_max / KVreq` — the numerator. A coder following it literally scales expectations
   by `0.9412` and lands ~5.4% away from what the code actually produces. Worse, that error is
   *invisible*: the three `muSat` assertions (`analyzer_test.go:367,405,425`) carry a **±10% tolerance**
   (`BeNumerically("~", muSat, muSat*0.10)`), so wrong-by-5.4% expectations still pass. Silently-wrong
   fixtures, green suite. The correct re-derivation must use the full ratio above.
2. **`muSat = 2782.0` will not go red at all.** A 0.55% shift is well inside ±10%, so plan §2e.3's
   premise that `analyzer_test.go`'s "expected supply/PRC numbers move ~6%" and need updating is largely
   false — most of the predicted churn does not exist. The red-first fixture the plan *does* specify
   (a `KvCacheThreshold: 0.5` case asserting PRC tracks config) is the one that carries real signal,
   because 0.5 vs 0.85 is a big enough move to escape the tolerance. Verify that fixture exists and that
   its expected value is derived with the **denominator included**: at `k=0.5`,
   `μ = (0.5·1024000/4600)/(0.073·0.5+0.006) = 111.3043/0.0425 = 2618.93`.

   **Sharpened 2026-08-07 — the exact threshold, because "tight tolerance" is not a number and the
   default here is on the wrong side of it.** The gap the fixture must resolve is
   `2780.56 / 2618.93 = 1.06172`, i.e. **6.17%**. A Gomega `BeNumerically("~", 2618.93, tol)` therefore
   stays **green at k=0.85** — the very state it is supposed to catch — for any relative `tol ≥ 6.17%`.
   The conventional tolerance in this exact file is `muSat*0.10` = **±10%**, used at all three existing
   `TotalSupply` sites. So the single most likely way to write this fixture — copy the neighbouring
   assertion's shape — produces a test that passes before *and* after C10 and pins nothing. Plan §1.1
   asks for "**tight tolerance**" and §2e.3 for red-before-green, but neither states the bound, and the
   local idiom violates it.

   > **Correction 2026-08-07 — this was already in the plan, and I should have found it.** Plan **§4**
   > (ship gate) has carried the requirement since tip `62c37c46` (03:15): *"That fixture needs a tight
   > tolerance, ~1%, and must not copy the neighbours' `muSat*0.10` idiom"*, with the μ(0.5) derivation
   > and the "at ±10% it passes either way and asserts nothing" rationale spelled out. So the gap I
   > describe above **did not exist** when I wrote it up, and the handoff I sent at 04:42 asked the
   > planner to add a clause the planner had already added 87 minutes earlier. Withdrawn — see that
   > handoff's header.
   >
   > Cause worth recording, because it is not just carelessness: I checked §1.1 and §2e.3 and never
   > opened §4, where ship-gate *test* requirements actually live. Finding 14 is the aggravating factor
   > — §4's TOC range points at §3, so a TOC-driven fetch would have landed me in the wrong section
   > anyway. That explains the miss; it does not excuse it, since the fix was to read the section that
   > owns test requirements before asserting the plan omitted one.
   >
   > One residual precision note, **not** an ask: §4 states the gap as **5.8%**, which is
   > `161.66/2780.56` — relative to the k=0.85 value. A Gomega `BeNumerically("~", expected, tol)`
   > compares an absolute `tol` against `expected = 2618.93`, so the bound expressed the way a tolerance
   > is actually written is `161.63/2618.93` = **6.17%**. Both numbers are correct about different
   > denominators, and since §4 prescribes ~1% the distinction never bites. Recording it only so the two
   > figures in these docs are not read as a contradiction.

   Required: relative tolerance **< 6.17%**, and materially so — **±1%** gives the band
   `[2592.7, 2645.1]`, which excludes 2780.56 with room to spare. I will check this by flipping the
   resolver back to 0.85 on a scratch extract and confirming the fixture actually goes red; a fixture
   asserted as red-before-green in the commit message but green at both values is the same
   passes-for-the-wrong-reason failure as Finding 11's, and neither the ±10% idiom nor a green suite
   will surface it.

   One reassurance in the other direction: at `k=0.5` the numerator-only error would give
   `2782.0 × (0.5/0.85) = 1636.5` against a correct 2618.93 — a 60% miss that any sane tolerance
   catches. So this fixture is self-protecting against the 0.9412-class error and vulnerable only to the
   too-loose-tolerance one. The `k=0.80` default-config expectations are the reverse: immune to
   looseness (they barely move) and fully exposed to the numerator-only error.

**What this does *not* undermine:** the fix itself is still correct and worth landing. The two real
defects §2e.1 identifies stand independently of magnitude — saturation and TA genuinely disagree on the
definition of "full" (0.80 vs 0.85), and TA genuinely receives `input.Config` and never reads it, so a
configured k_sat never reaches it. What changes is the *justification's weight*: this is a correctness /
configurability fix, not a "fixed ~6% thumb on the scale that biases the binder `argmax`". Under default
config the binder bias it removes is sub-1%. Worth saying plainly in the commit message rather than
repeating the 6% figure, and worth correcting in §2e.3 (planner-side) so the number does not outlive this
review as received wisdom.

**Recommended verification when C10 lands** (I will run these):
- Re-derive every moved TA expectation with the full two-place ratio; flag any that match the
  numerator-only 0.9412 scaling instead.
- Confirm the `KvCacheThreshold: 0.5` fixture asserts **2618.93** with relative tolerance **< 6.17%**
  (±1% recommended) — not the file's ±10% idiom, which would leave it green at 0.85. Verified by
  flipping the resolver back to 0.85 on a scratch extract and watching it go red, not by reading it.
- Confirm `DefaultKSat` greps to zero and `DefaultNearKSatMargin` survives with re-anchored prose.
- Confirm the `TODO: unify with the system-wide k_sat used by the EPP` moved onto `resolveKSat`.

### Pre-check — §2d.2's combine formula is sound (verified algebraically, no finding)

Done ahead of C6a/C6b so that a failing fixture there can be attributed to the implementation rather than
re-litigating the formula. With `wᵢ = (sᵢ − s_e)⁺`, `S = Σⱼ sⱼ`, `C = Σᵢ (e − vᵢ)·wᵢ / S`, `v* = e − C`:

- **Invariant 1 (uniform ⇒ extremum).** All `sᵢ` equal ⇒ every `wᵢ = 0` ⇒ `C = 0` ⇒ `v* = e`. Exact, not
  approximate — so C6a's byte-identical claim is arithmetically justified and the #1513 goldens genuinely
  cannot move on it.
- **Invariant 3 (bounded to `[min, max]`).** Upper: each `(e − vᵢ) ≥ 0` for scale-up ⇒ `C ≥ 0` ⇒ `v* ≤ e`.
  Lower: `(sᵢ − s_e)⁺ ≤ sᵢ` for `s_e ≥ 0` ⇒ `Σwᵢ ≤ S` ⇒ `C ≤ (e − v_min)` ⇒ `v* ≥ v_min`. Holds. The plan's
  one-line justification is correct as written.
- **Invariant 2 (dominant score ⇒ its own vote).** `s_k → ∞` with `k` a dissenter: `w_k = s_k − s_e`,
  `C → (e − v_k)` ⇒ `v* → v_k`. And when the dominant analyzer *is* the binder, all `wᵢ = 0` ⇒ `v* = e = v_k`.
  Holds in both directions — no special case needed.
- **Scale-down sign.** For `up=false`, `e = min vᵢ` ⇒ `(e − vᵢ) ≤ 0` ⇒ `C ≤ 0` ⇒ `v*` rises above the
  conservative extremum, bounded by `max vᵢ`. Confirms the plan's "one expression, no sign flip" claim.
  Reproduced both worked examples by hand: up 10-vs-5 @ 1/2 ⇒ `10 − 5·1/3 = 8.333` ⇒ ceil **9**; down
  10-vs-5 @ 2/1 ⇒ `5 − (−5)·1/3 = 6.667` ⇒ floor **6**. Both match.
- **Invariant 4 (monotone in each `sᵢ`)** is the one stated loosely: raising `sᵢ` also raises the shared
  denominator `S`, diluting *other* dissenters' pull, so `dC/ds_i` is not sign-definite in the
  3+-analyzer case. Every case I worked still moved `v*` toward `vᵢ`, so the claim's *intent* holds; but
  it is not the one-line consequence the others are. Not a defect — just the invariant whose unit-table
  assertion I will read closely rather than assume.

## Outstanding — pre-C6a

- **Finding 6 above is the one item worth raising before C10 is written** rather than after; it changes
  how the coder computes the new expectations, and the ±10% tolerances mean a wrong answer will not be
  caught by the suite.
- Findings 1–5 (§4a leaks, 19 locations) still unswept after 8 commits.
- Finding 4 folded into the C6a/C6d verification list (see above) — no longer a standalone follow-up ask.

**Resolution of Finding 6 (2026-08-07).** Routed via `session/handoffs/plan__ta-anchor-pr2-c10-ksat-effect-arithmetic.md`;
the planner verified it independently and corrected plan §2e.3 in `62c37c46` (plan tip moved
`588e3020` → `62c37c46`), with a sibling sync handoff retracting the "~5.9% / ~6%" figure in favour of
"sub-1% at default config, 0.4%–2.5% depending on the fitted ITL model". C10's justification is
restated as correctness + configurability rather than a systematic ~6% correction. The two-place ratio
is now stated in the plan and a tight tolerance is called for on the new fixture. **Accepted — closed.**
The C10 verification item below still stands: re-derive the moved expectations myself and flag any that
match numerator-only `0.9412` scaling.

---

## C6a — `pipeline: hoist the cross-analyzer combine into one helper` (`8eb6ee2d`)

Amended once in place (`ab4f0838` → `8eb6ee2d`); reviewed at the final SHA. Diffed against `1140a4c2`.
6 files, +392/−110: `analyzer_helpers.go` (+251/−?), `analyzer_helpers_test.go` (+134),
`rescale.go` (−39 net), the combine golden (comment only), and two dev-guide files.

**Verdict: APPROVE with one finding.** The hoist is real and the arithmetic is sound. One undeclared
behavioral change rides along (Finding 7) — in the right direction, but contradicting the commit
message's own byte-identity claim and untested.

### Gates (run by me at `8eb6ee2d`, in a `git archive` extract — never in the coder's live tree)

- `gofmt -l internal cmd` — clean
- `go build ./...` — clean
- `go vet ./internal/engines/pipeline/...` — clean
- `go test -race ./internal/engines/pipeline/...` — PASS
- `go test ./internal/... ./cmd/...` — PASS (full suite)
- `golangci-lint run` — **0 issues**
- DCO — `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` present

### Independently re-verified

**The magnitude claim holds at all four sites.** The commit rests on `max_i ceil(x_i) == ceil(max_i x_i)`
and `min_i floor(x_i) == floor(min_i x_i)`. Both are just monotonicity of `ceil`/`floor` plus the
extremum being attained, so rounding once at the caller is exact, not approximate. Checked per site
against the removed code:

| site | old | new | equal? |
|---|---|---|---|
| `roleBottleneckReplicas` | `max` seeded at `0`, `max_i ceil(state[i][role]/prc)` | `ceil(combine)` then `>0` clamp | ✓ (clamp shapes agree: old floors at 0 via the seed) |
| `safeRemovalReplicasForRole` | `min_i floor(RoleSpare/prc)`, `!found ‖ smallest<0 → 0` | `floor(combine)` then `>0` clamp | ✓ (participation filter copied verbatim: `Live`, `Result≠nil`, `RoleSpare≠nil`, `prc>0`) |
| `roleDemandGPUs` (rescale) | `replicas` seeded `0`, `max_i ceil(demand/prc)` | `ceil(combine)` then `>0` clamp | ✓ (filter identical, incl. `RoleCapacities[role]` presence for non-`both`) |
| `roleAggRemaining` | `state[bindingIndexForRole()][role]` | `state[combine-binder][role]` | ✗ — see Finding 7 |

**`combineVotes` collapses correctly under uniform scores.** With all `Score` equal, every
`(sᵢ − s_e)⁺` is `0`, so `correction == 0` and `v* == e`. Every collector hard-codes `Score: 1.0`, so the
dominance term is genuinely unreachable from the pipeline at this commit — the claim is structural, not
an empirical observation about the current fixtures.

**`bindingIndexForRole` is deleted, not wrapped.** Confirmed: the symbol is gone from the tree; both
former callers (`refreshAnchorSizing`, `roleAggRemaining`) now call `combineVotes(votesFromPickerState(…), true)`
and discard the value. This was the specific thing I said I would check rather than trust.

**No silent expectation change in a landed C3/C4/C5 fixture.** The only test-side edits are additive
(+134 lines of new `combineVotes`/collector specs) plus two comment-only touches — the C3 fixture at
`analyzer_helpers_test.go:642` (prose reworded, the `100` expectation and the whole `s` slice untouched)
and the combine golden's comment. No assertion value moved anywhere in the diff. Plan §2d's "must not
re-decide a landed fix" instruction is respected.

**The five new `combineVotes` specs are arithmetically right.** I re-derived every asserted number from
the §2d.2 formula by hand rather than trusting the suite: `10 − 11/6 = 8.1667` (up, 3 analyzers),
`5 + 1/3 = 5.333` (down — confirms the single expression handles both directions with no sign flip),
`10 − 5/3 = 8.333` (the design's worked example), `7.0` (score 1 vs 4), and `10 − 4995/1001 = 5.00999`
against the `~5.0 ± 0.02` dominance-convergence assertion. All five match. Boundedness is asserted
directly and follows from `Σᵢ(sᵢ − s_e)⁺ ≤ Σⱼ sⱼ`.

**The tie-break spec earns its keep.** I had expected the `Value == && Index <` switch arm to be dead,
since collectors append in ascending index order so `b` starts lowest and only strict `>` advances it.
The second half of the tie-break spec passes a hand-built out-of-order ballot, which is the one shape
that reaches it. Good instinct on the coder's part; the arm is not dead code.

**The participation-filter-in-the-collectors argument is correct and the test pins it.** Because
`Σⱼ sⱼ` runs over participating votes only, an analyzer with no PRC for the variant is structurally
absent rather than a zero-weight participant. The spec's counterfactual is right: counting `lat` would
make the denominator `4` instead of `3` and pull `10 − 5/3 = 8.333` to `10 − 5/4 = 8.75` — i.e. silence
would *increase* trust in the binder. This is a genuine design property, not decoration.

**Finding 4 is correctly parked, not dropped.** `votesFromRoleSpare`'s doc comment states the retained
behavior explicitly ("a live entry whose `RoleSpare` map exists but carries no key for `role` still
votes, reading the map-miss as 0.0"), and `needsScaleDownForRole`'s comment records that it deliberately
does *not* delegate because it is a veto with stricter participation rules. That is the honest framing of
the asymmetry I flagged, and it defers the behavioral question to C6d rather than silently resolving it.
**Finding 4 remains open, now explicitly owned by C6d.**

### Finding 7 (should-fix — undeclared behavioral change; the commit message claims the opposite)

**Claim.** The commit message says `bindingIndexForRole` "was `roleBottleneckReplicas`' loop with the
value discarded, which is now just the second return value", and that the commit "cannot move a number".
The first statement is not accurate, and the second is true only of the *magnitudes*.

**The change.** The deleted `bindingIndexForRole` selected the binder as the argmax of the **rounded**
value:

```go
n := int(math.Ceil(state[i][role] / prc))
if best == -1 || n > bestN { bestN = n; best = i }
```

`combineVotes` selects it as the argmax of the **raw** value. Whenever two participating analyzers'
raw replica-demands differ but `ceil` to the same integer, the old code saw a tie and kept the lowest
ballot index; the new code discriminates and picks the true argmax. Different binder, same magnitude.

**Reachability — verified empirically**, not argued. I copied the parent commit's `bindingIndexForRole`
verbatim into a scratch test in my extract (never the coder's tree) and drove both through the real
helpers with `sat: 100/48 = 2.0833` and `ta: 50/20 = 2.5` (both `ceil` to 3):

```
magnitude: roleBottleneckReplicas = 3          <- unchanged, as claimed
binder index: old = 0, new = 1                 <- changed
roleAggRemaining (new) = 50 ; old binder = 100  <- 2x
anchor PRC after refreshAnchorSizing = 20      <- old would be 48, 2.4x
```

So the binder identity reaches two consumers with real numeric effect: `roleAggRemaining`'s return value
(which feeds the caller's `n*prc/demand` and `k` formulas) and `refreshAnchorSizing`'s copied sizing
fields (`PerReplicaCapacity`, `Reason`, `TotalDemand`, `Utilization`). Unreachable with a single voter —
which is why the #1513 goldens and the whole suite stay green — and reachable exactly under the
multi-vote ballots PR-2 exists to enable.

**Direction.** The new behavior is the better one. `combined-analyzer-optimizer-design.md`'s anchor
refresh is specified as `argmax_i rd_i` over raw replica demand, so argmaxing the rounded value was a
latent loss of discrimination. I am **not** asking for the old behavior back.

**Why it is still a finding.** This is a correctness improvement riding silently inside a commit that
asserts byte-identity — the exact pattern the project's doc-accuracy discipline names ("a bug fix can
silently ride a semantic change — name it separately"). Concretely: no fixture pins argmax-of-raw over
argmax-of-ceil, so a future refactor can revert it and every gate stays green; and a reader who trusts
the commit message will not know the anchor's binder selection got finer.

**Suggested resolution** (coder's call on form; both are cheap):
1. Name it in the commit message and in `combineVotes`' doc comment — one sentence: the binder is the
   argmax of the *unrounded* vote, which is finer than the pre-hoist argmax-of-`ceil` and matches the
   design's `argmax_i rd_i`.
2. Add one fixture with a `ceil`-tie and differing raw values (the numbers above suffice), asserting
   both the magnitude (`3`) *and* the binder index (`1`), so the discrimination is pinned.

**Secondary note, same mechanism, lower reachability.** `votesFromPickerState` adds a guard the old
loops did not have — `i >= len(state) || state[i] == nil` — which excludes an entry that previously
participated with a `0.0` vote (indexing a nil map yields `0.0`, it does not panic). For the three
magnitudes this is inert: a `0.0` vote cannot change a `max` that is already clamped at `0`. For the
binder it can matter, but only in the degenerate all-zero-demand case, where the old code would pick
the first participant and the new code picks the first *non-nil-state* participant. Worth a clause in
the collector's comment; not worth a fixture.

### Developer guide (Type 4) — C6a

`multi-analyzer-pipeline.md` (+74/−?) and `saturation-scaling-config.md` (+2). Good work, and it does
the harder thing: **it documents Finding 4's asymmetry in the shipped doc instead of hiding it** — "its
opinion filter is weaker than the gate's: a live voter whose `RoleSpare` doesn't decompose the role
abstains from the *gate* and still votes `0.0` on the *count* … safe, but the two filters do not yet
agree." That is the honest description of current code state, and "not yet" is the phrasing Type 4
explicitly sanctions for a genuine absence, so it is not a forward-looking violation.

Also correct: the new `combineVotes` subsection, the three-collector table, the reasoning for keeping the
filter in the collectors, the `needsScaleDownForRole` veto-not-magnitude note, the two flow-diagram
updates, and the cross-link added to `saturation-scaling-config.md` distinguishing one analyzer's own
`AggregateByRole` from the cross-analyzer combine (a genuinely useful disambiguation — those two are easy
to conflate).

**Minor accuracy nit (no finding raised, but worth a one-line fix if C6c/C6d touches this text).** The
collector table's blanket sentence — "All three apply the same filter: the entry must have a `Result`, a
positive `PerReplicaCapacity` for that variant, and its own state **for that role**" — overstates
uniformity on exactly the axis Finding 4 is about. In code, only `votesFromTotalDemand` checks the *role
key* (`RoleCapacities[role]` absent ⇒ skip). `votesFromPickerState` checks `state[i] != nil` and
`votesFromRoleSpare` checks `RoleSpare != nil` — map *presence*, not the role key — so a missing role key
yields a participating `0.0` vote in both. The doc corrects itself for `votesFromRoleSpare` three
paragraphs later, but the table's sentence contradicts that correction. Suggest "…and its own state map
for that source (see the scale-down note for how a missing role *key* differs per collector)".

The `up`/`down` in the ASCII flow diagrams stand in for `up=true`/`up=false` rather than real
identifiers — fine as diagram shorthand.

### §4a leak sweep — C6a

Two new instances, on added lines:

| location | token | note |
|---|---|---|
| commit subject `…one helper (C6a)` | `C6a` | **first commit on this branch to put a plan commit-map label in a subject line** — maximally visible in merged history |
| `analyzer_helpers.go` `needsScaleDownForRole` comment: "abstains here (N7)" | `N7` | newly introduced |

Two pre-existing instances were **re-touched without being cleaned**, i.e. the coder rewrote the line
and carried the token across: `analyzer_helpers.go` `roleAggRemaining` ("Bug #2") and
`allocateForModelPaired` ("Bug #1"), plus `rescale.go` `roleDemandGPUs` ("Bug #3"). Editing a line is the
cheapest possible moment to drop the token, so these three now read as deliberate retention.

`#1513` in the golden's comment is **not** a leak — a GitHub PR number is code-side-visible and
legitimate. `PR-2` survives on an untouched context line in the combine golden (already in Finding 5's
inventory). Running total: **21 locations** across C1/C2/C5/C7/C8/C6a, still unswept.

### Outstanding for this branch (not blocking C1–C6a)

- Finding 7 — name the binder-selection change + pin it with one fixture.
- Findings 1–5 + C6a's two new instances — §4a leaks, **21 locations**, still unswept after 9 commits.
  Worth one sweep commit near the end rather than 21 amendments.
- Finding 4 — open, owned by C6d.
- Plan §5's C3 dev-guide citation correction — planner-side, not blocking.

---

## C6b — `pipeline: let a configured analyzer score weigh its vote` (`d9f3b97e`)

7 files, +198/−23. This is the commit that makes `score` mean something: C6a hoisted the
dominance formula into `combineVotes`, but every collector still hard-coded a weight of `1.0`, so an
operator's configured score reached the optimizer and was discarded there.

### Verdict (C6b)

**APPROVE.** The implementation is correct, the arithmetic matches plan §2d.2 in both directions, and
every claim in a long commit message checks out — including the ones I tried hardest to break. One
finding, and it is not a defect: the scale-down direction silently trades a hard safety bound for a
trust-weighted one, and the shipped operator doc states that consequence in a clause that cancels
itself out. That needs Dean's eyes, not the coder's.

### Gates (re-run by me on a clean extract of `d9f3b97e`)

| gate | result |
|---|---|
| `gofmt -l` | clean |
| `go build ./...` | clean |
| `go vet ./internal/...` | clean |
| `go test -race ./internal/engines/pipeline/...` | PASS |
| `go test ./internal/... ./cmd/...` (full) | PASS, `TEST_RC=0`, 0 FAIL lines |
| `golangci-lint run` | **0 issues** |
| DCO | `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` present |

### Independently re-verified

- **`voteScore`'s coercion claim is exactly true, not approximately.** The new helper is
  `if e.Score > 0 { return e.Score }; return 1.0`. I read both places the commit message says it
  matches: `saturation/engine_v2.go` `scoreForAnalyzer` (identical `> 0` test, identical `1.0`
  fallback) and `config/saturation_scaling.go:307-308` (`if …Score == 0 { …Score = 1.0 }`). The config
  layer coerces **zero only**; negatives survive load and are caught downstream by `scoreForAnalyzer`.
  `voteScore`'s `> 0` covers both, so it is the stricter of the two and cannot disagree with either.
- **`scoreForAnalyzer`'s body is unchanged** — `git show` of the hunk is comment-only. So C6b changes
  no saturation behavior; the corrected comment there is a doc fix riding a code commit, which is the
  right place for it.
- **All five new fixture values re-derived by hand from the formula**, not accepted from a green suite:

  | fixture | ballot | derivation | asserted |
  |---|---|---|---|
  | `pulls scale-up sizing toward the better-trusted dissenter…` | TA 10 @ 1, sat 5 @ 2 | `e=10`, `s_e=1`, `Σs=3`, corr `=(10−5)(2−1)/3=1.667` | `8.3333`, binder `1`, `roleBottleneckReplicas == 9` ✓ |
  | `pulls scale-down removal toward the better-trusted dissenter…` | TA 10 @ 2, sat 5 @ 1 | `e=5` (min), `s_e=1`, `Σs=3`, corr `=(5−10)(2−1)/3=−1.667` | `6.6667`, binder `0`, `safeRemovalReplicasForRole == 6` ✓ |
  | `holds scale-down at the safe extremum when the conservative analyzer is the better-trusted one` | sat 5 @ 2, TA 10 @ 1 | every `(sᵢ−s_e)⁺ = 0` | `5.0`, binder `0`, `== 5` ✓ |
  | `holds scale-up at the binder's vote when the binder is also the better-trusted one` | — | same, up direction | `10.0`, binder `1`, `== 10` ✓ |
  | `treats an unset score as the 1.0 default…` | one entry with `Score` unset | `voteScore → 1.0` | `votes[0].Score == 1.0`, `value == 10.0` ✓ |

  Both non-trivial values land on a number that is **neither analyzer's vote and neither analyzer's
  rounding** (9 from ceil(8.33) where the voters said 10 and 5; 6 from floor(6.67) where they said 10
  and 5), so these fixtures cannot pass by accident against a stubbed combine.
- **The coercion is load-bearing, and more so than the commit message claims.** The message says an
  uncoerced hand-built entry "would quietly over-correct." I computed the actual counterfactual on the
  shipped scale-up shape: with TA's score left at `0` and no coercion, TA still binds (`e=10`) but
  `s_e=0` and `Σs=2`, so saturation's *excess* becomes its *full* score — corr `=(10−5)·2/2=5` and
  `v* = 5.0 → 5 replicas` instead of `8.33 → 9`. The correction consumes the entire gap and the result
  collapses onto the dissenter's vote. Not a rounding nudge — a 9-vs-5 replica difference. The guard
  earns its place.
- **The new `enabled` row's parenthetical is accurate.** It now claims an enabled-but-stale analyzer is
  also excluded; verified against the VG-up filter landed in C7 (`analyzer_helpers.go:248`,
  `if e.Enabled && e.Live`), which is the set the collectors read.
- **"All shipped configs leave score at 1.0" is true.** Both shipped configmaps —
  `config/base/manager/saturation-scaling-configmap.yaml:34` and
  `deploy/configmap-saturation-scaling.yaml:38` — set `score: 1.0` explicitly. Uniform scores zero
  every correction, so C6b is inert on every shipped path and the goldens are byte-identical, as
  claimed. (Note for later: `saturation_scaling.go:171` accepts a second source, `Parameters["score"]`,
  applied only when `Score == 0`. Harmless here — the `:307` coercion runs after — but it means "score"
  has two spellings in config. Not C6b's problem; flagging so it isn't discovered as a surprise.)

### Findings

### Finding 8 (design question for Dean — not a defect, and fully declared) — on scale-down the combine may now remove more replicas than the most conservative live analyzer considers safe; the shipped operator doc states this in a self-cancelling clause

**What changes.** Before C6b, `safeRemovalReplicasForRole` was `minᵢ floor(spareᵢ/PRCᵢ)` — a hard
bound: no analyzer's own safe-removal count could be exceeded, whatever the config said. After C6b the
dominance rule applies in the down direction too, so the result is bounded only by the **most
aggressive** voter and positioned by relative trust. The shipped fixture pins exactly this:
`safeRemovalReplicasForRole(…) == 6` when saturation — the conservative voter — says only **5** are
safely removable.

**Why this is not a defect.** It is declared everywhere it should be: plan §2d.2 derives the scale-down
mirror and states the result "Still ≤ TA's own 10 and ≥ saturation's 5"; the commit message spells out
the 6.67 → 6 outcome; and the fixture title says "without exceeding its vote" — accurate, since the
bound that survives is the aggressive voter's. `needsScaleDownForRole` also remains a strict
all-live-must-agree veto, so only the *magnitude* of a permitted scale-down moved, never the decision
to scale down at all. The coder implemented the plan faithfully.

**Why it still needs Dean.** Plan §2d.2's justification is *"When the conservative analyzer is also the
higher-scored one … the direction that matters for safety needs no special case."* That argument holds
only under one score ordering — and the operator controls the ordering and can invert it. Nothing in
the code, config validation, or docs constrains it. Many voting schemes deliberately keep this
asymmetry (weighted on the way up, hard `min` on the way down) precisely because the cost of the two
errors is not symmetric: over-provisioning burns GPU-hours, under-provisioning drops requests. Whether
WVA wants the symmetric rule or a clamped one is a design call, and the plan reaches it by mirroring an
example rather than by weighing that asymmetry. It should be an explicit decision, not an inherited
one.

**The doc problem is separate and concrete.** `saturation-scaling-config.md` currently ends the score
explanation with:

> Trust the conservative voter more on scale-down and the result simply stays at the safe end; there is
> no configuration that makes the combine less safe than the most conservative live analyzer's vote
> plus the pull of a better-trusted dissenter.

The first clause describes only the favourable ordering. The second reads as a safety guarantee but is
vacuous — "no less safe than [the conservative vote] plus [the correction]" is just a restatement of
the formula; the trailing clause gives back exactly what the sentence appears to promise. An operator
reading this table would not learn the one thing they need to know before touching the field: **if you
score an aggressive analyzer above a conservative one, scale-down can remove more replicas than the
conservative analyzer considers safe.** That is the actionable consequence and it is the shipped
fixture's own number.

**Recommendation.** (1) Dean decides whether the down direction stays symmetric or gets clamped at the
min. (2) Independent of that decision, replace the vacuous clause with the consequence stated plainly,
in the same voice as the rest of that (genuinely good) section — it already tells operators "prefer
fixing the mis-calibrated analyzer first"; this is the same kind of warning and belongs next to it.
No code change is requested by this finding as it stands.

### Developer guide (Type 4) — C6b

Strong, and the strongest operator-facing writing on this branch so far. `multi-analyzer-pipeline.md`
gains the formula and its properties; `saturation-scaling-config.md` gains a "What `score` means"
section that leads with what the field is *not* (not a priority, not a budget multiplier), states that
`1.0` everywhere reproduces the plain max/min exactly, works the 10-vs-5 example through to 9, answers
"When would I change it?", and warns that raising every score together changes nothing. Two of the
three field-table rows it rewrites were previously wrong-by-staleness, and it fixes the neighbouring
`enabled` row rather than leaving a knowingly-false line inside a table it was already editing — the
right call, and the commit message says so out loud.

The only defect is the sentence quoted in Finding 8.

### §4a leak sweep — C6b

Clean in the added code and doc lines. The only new instance is the **commit subject's `(C6b)`** — the
second subject-line label on this branch after C6a's, and subject lines are the most visible place a
plans-branch token can land in merged history. Running total: **22 locations**, still unswept.

### Outstanding for this branch (not blocking C1–C6b)

- **Finding 8 — Dean's call** on scale-down symmetry, plus the one-sentence doc fix (independent of the
  decision).
- Finding 7 — name C6a's binder-selection change + pin it with one fixture.
- Findings 1–5 + C6a/C6b's new instances — §4a leaks, **22 locations**, unswept after 10 commits.
  Still best handled as one sweep commit near the end. **→ Superseded: see Finding 13** — a full-branch
  re-grep found **32** code/doc locations plus all 9 commit messages, and the commit-message half is not
  fixable by a sweep commit. Use Finding 13's inventory, not this count.
- Finding 4 — open, owned by C6d (C6a's own comments now say so explicitly).
- Plan §5's C3 dev-guide citation correction — planner-side, not blocking.
- Finding 6 — closed (planner corrected plan §2e.3 in `62c37c46`); the C10 re-derivation check it
  called for is still owed when C10 lands.

---

## Pre-emptive — C6c not yet written

C6c is the highest-risk commit on the branch (plan §6: "the user-visible risk concentrates in C6c").
Same method as the pre-emptive C10 pass that produced Finding 6: check the plan's own load-bearing
arithmetic *before* code exists, because a wrong expectation encoded into a fixture is invisible
afterwards. I pinned the pre-C6c state of all four named sites from `d9f3b97e` and worked the currency
change through them.

### Verified-correct in the plan (no action)

- **§2d.5's golden-neutrality argument holds.** `Σ_role RC[role]/PRC ≡ Σ_role (RC[role]/PRC)` is
  distributivity; and for the one quota-constrained golden (single-model / single-role /
  single-variant / priority 1 / Score 1) the numbers work as written: fsv `50000 → 5`, and with (ii)'s
  divide removed the cap is `ceil(5) = 5` against today's `ceil(50000/10000) = 5`. Unchanged, and the
  namespace budget still binds at 2. The claim is verified, not assumed.
- **Site (iv) is characterized correctly.** `allocateForModel:274-291` sets `target = w.remaining − mean`
  and then clamps raw per-analyzer per-role demand with `if ps[i][role] > target { ps[i][role] = target }`.
  It is inert today for the stated reason (`target` is the sum over roles, so each role's value is
  already ≤ it) and becomes a hard truncation the moment `target` is replica-space. Real, and the plan is
  right that it is what turns #5 from a shape bug into a units bug.
- **`v_role` is well-defined.** `costEfficiency` returns `math.MaxFloat64` for `PRC <= 0`
  (`cost_aware_optimizer.go:238-243`), so "first `sortByCostEfficiencyAsc` candidate with `PRC > 0`" is
  just `sorted[0]` whenever any variant is sizable, and it is the same ordering `fairShareRolePick`
  iterates. Deterministic.

### Finding 9 (should-fix, pre-emptive — cheap now, invisible later) — moving fsv to replica space turns `fairShareCap`'s per-candidate PRC division into a cross-variant unit mismatch whenever the picker falls through to a second variant

**Today's code is unit-correct across variants by construction.** `fairShareRolePick` iterates
`sortByCostEfficiencyAsc(roleVCs)` and computes `fairShareCap := ceil(target / vc.PerReplicaCapacity)`
using **that candidate's own** PRC, every iteration. `target` is demand-space, so each candidate
converts the same budget with its own capacity — correct for whichever variant the picker lands on.

**After (i)+(ii) it is correct only for the first candidate.** `target` becomes replica-space, converted
per §2d.5 (i) against `v_role` = the cheapest-efficiency candidate; (ii) then reduces the cap to
`ceil(target)`. That is exact **iff** the variant the picker allocates to is `v_role`. But the picker
skips a candidate on two conditions that `v_role` selection does not model:

- `gpusAvail < gpusPR` — the cheaper accelerator pool is exhausted;
- `headroom <= 0` — the cheaper variant is at `MaxReplicas`.

Either one makes the loop fall through to a later candidate, and `ceil(target)` is then "replicas
measured in `v_role`'s capacity" applied to a variant with a different capacity. Concretely: one role,
`v1` PRC 10000 (cheapest efficiency) and `v2` PRC 2000, `target` = 50000 demand ⇒ 5 replicas of `v1`.
With `v1`'s GPUs exhausted, today's cap for `v2` is `ceil(50000/2000) = 25`; after the change it is
`ceil(5) = 5` — a **5× under-allocation**, silently, on the path the cost-aware design exists to
serve (two accelerator types per role, fall through to the pricier one when the cheap pool runs dry).
Neither condition is exotic; `headroom <= 0` is the *normal* late state of a scale-up loop.

**Why it will not be caught.** Every #1513 golden and the plan's worked example are
single-variant-per-role, where `v_role` is the only candidate and the mismatch is identically zero. The
fixtures §4 asks for ("two models, differing PRCs") differ *across models*, not across variants within
one role. So the whole finding lives in a gap the planned test set does not cover.

**Remedy (reduces to the plan's (ii) in the ordinary case).** Carry the reference PRC used for the fsv
conversion into the pick and rescale per candidate:
`ceil(target × prcRef / vc.PerReplicaCapacity)`. When `vc == v_role` the ratio is 1 and this *is*
`ceil(target)`, so §2d.5's arithmetic, the golden neutrality, and (ii)'s "double conversion" reasoning
all stand unchanged — the ratio only bites in exactly the fall-through case that is wrong today's
successor. The natural `prcRef` is the `combineVotes` **binder's** PRC for `v_role`, which is also what
the C2-refreshed anchor already carries, so it is available without new plumbing. (A blunter
alternative — keep fsv in demand space and fix only the `Σᵢ`→combine shape — is *not* recommended: the
combine has to be in replica space for a max across analyzers with different capacity units to mean
anything at all. The currency change is right; it just needs to survive contact with the second
candidate.)

### Finding 10 (should-fix, pre-emptive) — `fairShareValue`'s `maxDemand` fallback is an unnamed **fifth** lock-step site; it returns raw demand where every caller will read replicas

Plan §2 #5 names four lock-step sites. There is a fifth inside site (i)'s own function:
`greedy_score_optimizer.go:78-92`, the fallback taken when `priority × weighted <= 0`:

```go
// Fallback: max remaining demand across roles when Score=0 or priority=0.
maxDemand := 0.0
… if ps[i][role] > maxDemand { maxDemand = ps[i][role] } …
return maxDemand
```

It returns **raw `ps` demand units**, so once (i) lands, `fairShareValue` returns replica-space on its
primary path and demand-space on its fallback — the exact currency desync §2d.5 warns about, inside the
function being rewritten. It is reachable (`priority == 0`, or all-zero remaining), and after (ii)/(iv)
a raw-unit fsv flowing into `ceil(target)` and the `ps` clamp mis-sizes by a factor of PRC.

Two secondary points in the same function: the fallback maxes **over roles** while the primary path
**sums** over roles, so a P/D model's fallback is systematically smaller than its primary value (a
pre-existing inconsistency, not caused by C6c, but this is the moment it is cheap to settle); and the
doc comment at `:58` states the formula as `fsv = priority × Σᵢ Score_i × Σ_role pickerState[i][role]`,
which C6c must rewrite since it names Score.

**Also worth stating in the plan:** `fairShareValue(priority, s, ps, roles)` does not currently receive
the variant list, so (i) needs a signature change to reach `v_role` — and it must be handed the *same*
`variants` slice `fairShareRolePick` iterates, or the reference candidate and the picker's first
candidate can diverge (which is Finding 9's mismatch arriving through a second door).

### Outstanding — pre-C6c

- Findings 9 and 10 → routed to the planner (both are plan-spec corrections, not code review of
  something written). Cheap before C6c exists; near-invisible after.
- The C6c checklist I will hold the commit to: Score gone from all six names in plan §6's grep
  (`fairShareValue`, `fairShareCap`, `computeMean`, `sortByRemainingDesc`, `allocateForModel`,
  `sortVariantsForScaleDown`); all five sites converted in lock-step; T1.4 rewritten per §2d.6 with
  ≥ ~10 replicas of spread and both the replica number **and** binder index asserted; finding (b)'s
  participation filter present; goldens **re-run and unmoved** (plan: if one moves, stop — do not
  rewrite a golden to accommodate this change), which I will verify by re-running them myself rather
  than reading the report.

## Pre-emptive — C6d not yet written

Same rationale as the C6c pass above: C6d's spec is plan §2d.4 finding **(c)**, and walking the actual
call graph before the commit exists turned up a problem with the spec itself. Cheap to fix now.

**What checks out.** `votesFromRoleSpare` at HEAD is Live-gated at the top (`if !e.Live { continue }`),
treats `Result == nil || RoleSpare == nil` as an abstain, and its doc comment is honest about the one
case it deliberately leaves alone. `needsScaleDownForRole` implements N7 correctly with a two-value
lookup (`spare, ok := e.RoleSpare[role]; if !ok { continue }`) and carries a safety floor
(`liveCount > 0`, so "nobody has an opinion on this role" does not authorise removal). The two
functions' divergent participation rules are documented at both ends rather than left implicit.

### Finding 11 (should-fix, plan defect — C6d as specified is unreachable code) — the scenario finding (c) describes is already prevented by the `needsScaleDownForRole` gate, one frame up the call stack

Plan §2d.4 (c) states the bug as: a **live** analyzer reporting `RoleSpare[role] = 0` — "an explicit
*there is no spare here*" — but carrying no per-variant PRC "is dropped from the `min`; the other
analyzers' spare wins and replicas come off **over its objection**." The proposed fix is that such an
analyzer "blocks removal for every variant of that role, whether or not it sizes the variant."

That outcome cannot occur on the production path, because the objection is already honoured — and
honoured at a coarser granularity than the proposed fix would achieve. The sole non-test caller of
`safeRemovalReplicasForRole` is inside a loop guarded by the veto
([cost_aware_optimizer.go:437-450](../../ta-anchor-dynamic-refresh/internal/engines/pipeline/cost_aware_optimizer.go#L437-L450)):

```go
for _, role := range roles {
    if !needsScaleDownForRole(s, role) {
        continue                    // whole role skipped — no variant of it is considered
    }
    ...
    sorted := sortVariantsForScaleDown(s, roleVCs)
    scaleDownVariantSet(ctx, sorted, targets, states,
        func(vc domain.VariantCapacity) int {
            return safeRemovalReplicasForRole(s, vc.VariantName, role)   // only reached past the gate
        }, ...)
}
```

and `needsScaleDownForRole` vetoes on a present, non-positive spare **without consulting PRC at all**
([analyzer_helpers.go:683-703](../../ta-anchor-dynamic-refresh/internal/engines/pipeline/analyzer_helpers.go#L683-L703)):

```go
spare, ok := e.RoleSpare[role]
if !ok { continue }              // abstain (N7)
if spare <= 0 { return false }   // veto — PRC never enters this decision
```

So for (c)'s exact stipulation — live, `RoleSpare[role]` present and `== 0`, no PRC for the variant —
the gate returns `false`, the role is skipped in full, and `safeRemovalReplicasForRole` is never
called for *any* variant of that role. Verified: `git grep` finds exactly one non-test caller of each
function, the veto at `:439` and the magnitude at `:449`, in that nesting. The abstain branch cannot
smuggle (c) past the gate either, since (c) stipulates the key is present, and `initRoleState` never
seeds `RoleSpare` for an entry with `Result == nil`, so the `Result == nil || RoleSpare == nil` skip
does not apply.

Two consequences worth heading off:

1. **C6d risks landing dead code.** Adding a "role-level objector blocks removal" rule inside
   `votesFromRoleSpare` changes the return value of a function that, in this scenario, is not reached.
2. **Its natural test will pass for the wrong reason.** Every existing unit test in this area calls
   `safeRemovalReplicasForRole` directly. A fixture built that way *will* go red before the change and
   green after — demonstrating the new branch works, while proving nothing about production behaviour,
   because the gate short-circuits the same input one frame up. If C6d proceeds in any form, I will
   hold it to **at least one fixture that drives `scaleDownRoleIterated`** (or the optimizer entry
   point) end-to-end, so the assertion covers the gate-plus-magnitude composition rather than the
   magnitude alone.

Recommendation for the planner: re-derive (c) against the gate. Either it is already satisfied — in
which case C6d becomes a test-only commit pinning the existing behaviour, which is worth having — or
there is a path I did not find, in which case the plan should name the caller that reaches the
magnitude without the gate, since I could not.

**Related, and it sharpens the wording:** the plan calls (c)'s desired outcome a **veto**. Inside
`votesFromRoleSpare` a veto can only be expressed as a `0`-vote, and after C6b a `0`-vote is no longer
absolute — the dominance correction pulls `v*` above the extremum whenever a participant carries a
strictly higher score (Finding 8's mechanism, applied here). With every shipped config at
`score: 1.0` the two coincide, so this is latent rather than live. But if the intent is that an
explicit role-level "no spare" is *hard*, that belongs in the gate, where it is score-independent —
which is exactly where it already is.

### Finding 12 (should-fix, defect in PR-1 code — out of PR-2's scope to fix, worth an issue) — the scale-from-zero complement omits `Role`, so a disaggregated model can acquire a spurious `both` role capacity alongside its real per-role entries

Found while establishing whether Finding 4's map-miss vote is reachable. The throughput analyzer builds
`VariantCapacity` values at two sites, and they disagree on `Role`
([throughput/analyzer.go:372-382](../../ta-anchor-dynamic-refresh/internal/engines/analyzers/throughput/analyzer.go#L372-L382)
and [:409-413](../../ta-anchor-dynamic-refresh/internal/engines/analyzers/throughput/analyzer.go#L409-L413)):

```go
variantCapacities = append(variantCapacities, domain.VariantCapacity{
    VariantName: variantName,
    Role:        state.role,          // main loop — role set
    ...
})
...
variantCapacities = append(variantCapacities, domain.VariantCapacity{
    VariantName:        vs.VariantName,
    PerReplicaCapacity: st.lastPerReplicaSupply,
    Reason:             itlReasonScaleFromZero,   // no Role field
})
```

`AggregateByRole` maps an empty role onto `domain.RoleBoth`
([aggregation.go:75-78](../../ta-anchor-dynamic-refresh/internal/engines/aggregation/aggregation.go#L75-L78)),
so on a **disaggregated** model with at least one zero-replica variant, the analyzer's `byRole` becomes
`{decode: …, both: …}`. That has `len(byRole) == 2`, so it clears `aggregateRoleCapacities`'s
non-disaggregated early return (`len(byRole) == 1 && hasBoth`) and yields a `RoleCapacities` map holding
a real per-role entry **and** a `both` entry. `both` is the synthetic single-role stand-in for
non-disaggregated models — the surrounding code treats the two as mutually exclusive, and that very
function's comment says so: *"Non-disaggregated: only a 'both' bucket (or nothing)."*

Downstream, `initRoleState` takes the `RoleCapacities != nil` branch and seeds the bogus role into
`roles`, `pickerState[i][both]` and `s[i].RoleSpare[both]`, with all-zero totals (the `:409` literal
sets no `ReplicaCount` and no `TotalDemand`, so `TotalSupply += 0 × PRC` and `TotalDemand += 0`).

Impact, stated as far as I traced it and no further: `RoleSpare[both] == 0` makes
`needsScaleDownForRole(s, "both")` veto that role, which is harmless because no live replica sits in it;
a zero-RC `both` role entering the scale-up role loop allocates nothing. **I did not find a case where
it produces a wrong replica count.** So: a data-shape defect with no demonstrated numeric consequence,
which is why I am recording it rather than treating it as blocking — but it is the only mechanism I
found that can desync an analyzer's role-key set from its PRC-key set, which is the precondition
Finding 4 needs. This is PR-1 code (the scale-from-zero complement); PR-2 should not fix it. It wants a
GitHub issue, or a one-line `Role: vs.Role` addition folded into whichever PR next touches that block.

### Finding 4 — status update (downgraded from "plausible bug" to "asymmetry worth closing")

Finding 4 (recorded under C7) observed that `votesFromRoleSpare` reads a missing `RoleSpare[role]` as
`0.0` and so votes to hold removal at zero, where its sibling `needsScaleDownForRole` abstains (N7).
The code comment at HEAD confirms the asymmetry is deliberate and unresolved: *"a live entry whose
RoleSpare map exists but carries no key for role still votes, reading the map-miss as 0.0 … whether a
role-level silence should abstain instead is a behavioral question."*

Reachability now traced. Firing it needs an analyzer that lacks the role key **but** has a positive PRC
for a variant of that role. Both producers derive their role set from the same variant slice that
supplies the PRCs — saturation at [analyzer.go:136](../../ta-anchor-dynamic-refresh/internal/engines/analyzers/saturation_v2/analyzer.go#L136),
throughput via `aggregateRoleCapacities` over its own `variantCapacities` — so the two key sets are
normally in lock-step and the case cannot arise. The one divergence path is Finding 12's role-less
entry, and that entry exists only for variants with **no live replicas this cycle**, where a
`safeRemovalReplicasForRole` of `0` removes nothing that was going to be removed anyway.

So: real in the code, admitted in its own comment, but I cannot produce a production input where it
changes a replica count. Recommendation unchanged in substance, softened in urgency — C6d should adopt
the two-value lookup (`v, ok := e.RoleSpare[role]`) because it is two lines, makes the ballot agree
with the gate it sits behind, and retires a documented open question. It should **not** be presented
as fixing a live bug.

### Outstanding — pre-C6d

- Findings 11 and 12 → routed to the planner. 11 is time-sensitive (it changes what C6d should be, or
  whether it should exist); 12 is PR-1 code and only needs a home.
- The C6d checklist I will hold the commit to: finding (c)'s rule, if implemented, is exercised by at
  least one fixture that goes through `scaleDownRoleIterated` rather than calling the magnitude helper
  directly; C7's N7 abstain in `needsScaleDownForRole` is **not** regressed (the two-value lookup and
  the `liveCount > 0` floor both survive); if the key-miss vote is converted to an abstain, the
  `liveCount`-equivalent floor is added to the ballot too, so "every voter abstained" does not collapse
  to an unbounded removal; goldens re-run by me and unmoved.
- **Added after C7's re-check came back negative:** C6d is the last commit whose fixtures are *required*
  to drive `scaleDownRoleIterated` end-to-end, so it is the last cheap chance to close **Finding 16**
  (anchor PRC 0 silently excludes a variant from scale-down). Check whether any of the three fixtures
  incidentally carries an anchor `PerReplicaCapacity` of 0 alongside a positive `RoleSpare`; if one does,
  the `:125` skip is pinned for free and Finding 16 closes. If none does, Finding 16 stays latent — an
  acceptable outcome, not something to ask the coder to add.

## §4a — full-branch inventory at C6b (supersedes the per-commit running totals)

I re-ran the sweep across the whole branch instead of incrementally, and the total is materially higher
than the running count in Findings 1/2/3/5. Recording it once, precisely, so the eventual cleanup has a
worklist rather than a number.

### Finding 13 (should-fix, supersedes the "22 locations" running total) — 32 code/doc locations plus **all nine** commit messages; the commit-message half cannot be fixed by a sweep commit, and the window to fix it cheaply is open right now

**Code and docs — 32 locations, every one introduced by PR-2.** The same grep at the base
(`075a208e`) returns **zero**: PR-1's own §4a strip was complete, so none of this is inherited and
PR-1 sets the precedent that it is expected to be cleaned before push.

| File | Locations |
|---|---|
| `internal/engines/pipeline/analyzer_helpers.go` | 119, 149, 214, 550†, 584, 671, 682, 694, 806 |
| `internal/engines/pipeline/analyzer_helpers_test.go` | 153, 193, 339, 375, 376, 746, 777 |
| `internal/engines/pipeline/rescale.go` | 49, 348, 539, 560 |
| `internal/engines/pipeline/optimizer_dynamic_refresh_test.go` | 3, 14, 17 |
| `internal/engines/pipeline/optimizer_liveness_test.go` | 3, 10, 75 |
| `internal/engines/pipeline/optimizer_combine_characterization_test.go` | 42, 104 |
| **`docs/developer-guide/multi-analyzer-pipeline.md`** | **338, 472** |
| `internal/engines/pipeline/optimizer_interfaces.go` | 54 |
| `internal/engines/pipeline/rescale_test.go` | 152 |

The two dev-guide hits are the worst of the set — a shipped Type 4 doc is the most reader-visible
surface on the branch, and `N7`/`N8` resolve to nothing for its audience.

**† A distinct sub-class at `analyzer_helpers.go:550`:** *"The single-vote invariant … is upheld by not
running this at all rather than running it to a no-op — see `combined-analyzer-optimizer-design.md`
§ invariants #7."* That file is not in the repo (`git ls-files` confirms), so the pointer dangles for
every reader of merged code. Introduced by C2 (`b106b929`). The prose before the pointer is
self-sufficient — the fix is to delete the citation, not to replace it.

**A second sub-class worth separating: `Bug #n` masquerades as a GitHub issue reference.** Eight of the
32 (`analyzer_helpers.go:584`, `:806`, `analyzer_helpers_test.go:746`, `:777`, `rescale.go:49`, `:539`,
`:560`, `rescale_test.go:152`) plus three commit subjects carry `Bug #1`/`Bug #2`/`Bug #3` — the plan
§2 numbering. This is sharper than the `N7`-class leak: `N7` is merely opaque, whereas `Bug #2` looks
like a tracker reference, so a reader follows it to an unrelated issue #2 and is actively misled. It
also collides with the one form I confirmed earlier as *legitimate* — `#1513` in the golden's comment
is a real GitHub PR number and should stay. Both shapes now sit in the same package, indistinguishable
by form. Reword these to the behavior ("the anchor's uniform PRC", "raw units vs replica space").

**Commit messages — all nine commits, and a sweep commit cannot touch them.** 6 of 9 subjects and 8 of
9 bodies carry a token; no commit is clean:

| Commit | Subject leak | Body leak |
|---|---|---|
| `680bebdb` | `(N2)` | `PR-1`, `PR-2` |
| `b106b929` | — | `PR-1's Test 9` |
| `50034d15` | `(Bug #2)` | `C4`, `Bug #1`, `C4's` |
| `07b8fdb7` | `(Bug #1)` | `C3`, `Bug #2` |
| `3c9d45bb` | `(Bug #3)` | `N3` |
| `952d2fff` | — | `N8`, `N7` |
| `1140a4c2` | — | `PR-1`, `C1-C7` |
| `8eb6ee2d` | `(C6a)` | `C6b`, `C6d` |
| `d9f3b97e` | `(C6b)` | — |

My earlier advice — "one sweep commit near the end" — is right for the 32 code locations and **wrong
for these**. Commit messages are only reachable by rewriting history (`rebase -i`, reword ×9). A tenth
commit cannot retroactively clean the nine subjects that `git log --oneline` and the GitHub commit list
will show permanently.

**Why the timing matters, and why it favours acting now.** `origin/ta-anchor-dynamic-refresh@f6485980`
is already orphaned by PR-1's own reword, so a force-push is required for this branch regardless of
whether the messages are touched. Folding the reword into that unavoidable force-push costs nothing
extra. The moment a GitHub PR is opened and reviewers begin commenting, the same reword becomes a
history rewrite under review — which the project's "no rebase of live PR branches" rule exists to
prevent. So this is cheapest strictly before the PR is opened, and it is PR-1's exact precedent (its
F1/F3/F4 token strips rode the rebase it needed anyway).

Neither half is a correctness defect and neither should block a commit. Routing note: the reword is a
history rewrite on a pushed branch, so per convention it is the planner's force-push and needs Dean's
explicit go-ahead — not something I ask the coder for directly.

**Not PR-2's:** `docs/developer-guide/throughput-analyzer.md:698` cites
`plans/planning/TA-Plan.md` / `TA-PR4-plan.md` — pre-existing on `main`, already tracked as a main-side
§4a location in `governance-follow-ups.md`. The `docs/superpowers/` and `locator.go:4` pointers are
**not** violations: they target in-repo paths, so they resolve for a reader of merged code.

### Outstanding — §4a

- 32 code/doc locations → one sweep commit, ideally folded into C9 (which already touches the dev-guide).
- 9 commit messages → reword pass on the pre-PR force-push; planner-owned, needs Dean's go-ahead.
- Re-run both greps after C6c, C6d, C10, C9 — the count has risen with every commit so far.

## Plan-doc hygiene (found while prepping the C9 checklist)

### Finding 14 (should-fix, plan-side, acutely relevant to the commit in flight) — the plan's TOC line ranges are stale by +35 to +100 lines, and the plan's own Reading Protocol tells the coder to fetch by those ranges

I went to read §4 (ship gate) at its TOC-listed `L781:845` and got the tail of §2e.3 plus all of §3.
Checking every entry: the TOC is correct through §2 (L197), then drifts progressively.

| Section | TOC says | Actually | Off by | Fetching the TOC range actually returns |
|---|---|---|---|---|
| §2d.5 Fair share (Bug #5) — currency | L534:556 | **L569:626** | +35 | §2d.4 (a)/(b)/(c) |
| §2d.6 T1.4 — the existing Score test | L557:583 | **L627:653** | +70 | §2d.4's (c) + section footer |
| §2e.3 Effect, churn, ordering | L685:745 | L755:815 | +70 | §2e.1/§2e.2 |
| §3 Per-iteration dynamic refresh | L746:780 | L816:850 | +70 | §2e.3 |
| **§4 Ship gate & tests** | L781:845 | **L851:922** | +70 | §2e.3 tail + §3 |
| **§5 Dev-guide sections (per commit)** | L846:914 | **L923:1005** | +77 | §4 ship gate |
| **§6 Semantic-pivot grep steps** | L915:973 | **L1006:1073** | +91 | §5 dev-guide text |
| §7 Out of scope / deferred | L974:1024 | L1074:1124 | +100 | §6 greps |

(§0/§1/§1.1/§2 are still exact; the drift begins at §2b, L258 → L293.) The TOC's last entry ends at
L1024; the file is 1124 lines, so the final 100 lines are unreachable by the TOC.

**Why this is more than cosmetic.** The plan opens with a Reading Protocol instructing agents to read the
TOC and then *"fetch sections on demand (`Read <file> offset:<start> limit:<end−start+1>`)"*. Fetching by
a stale range does not error — it silently returns a **different, plausible-looking section**. Three
consequences are live right now:

- **§2d.5 and §2d.6 are the spec for the work in flight.** The coder is on C6c, whose whole subject is
  `fairShareValue` currency (§2d.5) and the T1.4 rewrite (§2d.6). Fetching §2d.5 by TOC returns §2d.4 —
  the (a)/(b)/(c) findings — which *reads* like relevant fair-share material (it contains finding (b),
  about `fairShareValue`!) but is not the currency spec and does not contain the T1.4 rewrite
  instructions. This is the worst possible failure shape: wrong section, right topic.
- **§6 is the semantic-pivot grep steps**, which CODER-CONVENTIONS §3 makes mandatory. Fetching L915:973
  returns dev-guide prose with no greps in it. A conscientious coder concludes the plan omitted the grep
  step and writes a handoff about the gap (a wasted cycle); a less careful one skips the grep.
- **§5 is the per-commit dev-guide map**, which CONVENTIONS requires be specific enough to act on.
  Fetching it returns §4's test requirements instead.

**Fix is mechanical and already prescribed.** CONVENTIONS: *"Before handing any plan doc to a coder, run
`bash plans/scripts/toc-refresh.sh <plan-file.md>` … Idempotent — run again after any structural edit."*
The C10 fold-ins (through plan tip `62c37c46`) added content without a refresh. One command fixes all of
it.

**Not mine to run.** `ta-anchor-dynamic-refresh-plan.md` is a Type 3 plan — planner-owned. Per the
pre-action gate this goes back as a handoff even though the fix is a single idempotent script and I can
see exactly what it would do. Routed to the planner.

**Self-check performed.** My own Findings 9–12 cite §2d.4/§2d.5/§2d.6, so I re-read §2d.4 at its *actual*
L534:568 to confirm I had not quoted the wrong region. Finding 11's quote of (c) is verbatim-correct, and
§2d.4's closing sentence — *"key present and `<= 0` ⇒ **veto**"* — is exactly the rule
`needsScaleDownForRole` already implements PRC-independently, which is the substance of Finding 11. No
correction needed to any prior finding.

### Outstanding — plan hygiene

- Finding 14 → planner: run `toc-refresh.sh` on the plan. Worth doing before the coder next fetches
  §2d.5/§2d.6/§4/§5/§6 — i.e. ideally before C6c is finished.
  **Update 2026-08-07 05:20 — actioned, then immediately overtaken.** `ffb945c1` ran the refresh **and**
  added 130 lines in the same commit, refresh first. So the shipped TOC is exact for `62c37c46` and off for
  `ffb945c1`: +1 (§2b–§2d.4), **+33** (§2d.5–§4), +72 (§5), +75 (§6), +82 (§7); §7's range still ends at
  L1124 against a 1206-line file. The finding stands with a sharper root cause — **the refresh has to be the
  last step of a plan edit; run first, it is indistinguishable from not run.** Two consequences are live and
  both are re-raised in `plan__ta-anchor-pr2-toc-refresh-ran-before-edits.md`:
  - **§2d.5 truncates at exactly the new content.** TOC `L569:626` vs actual `L602:659` — the fetch returns
    §2d.4's tail plus §2d.5's first 25 lines, ending mid-sentence inside *Reference PRC*, and omits *"The
    fall-through case (ii) must survive"* (L635-651) entirely: the 25→5→25 table, the why-the-suite-misses-it
    argument, the §4 fixture pointer. The single most important thing `ffb945c1` added, invisible to a
    TOC-driven read, in a fetch that ends on a complete paragraph and so reads finished.
  - **The clause I missed is still unreachable the same way.** §4 TOC `L851:922` vs actual `L884:994`; the
    C10 fixture-tolerance clause now sits at **L943** — outside the range, again. Not an excuse for the miss
    (a range visibly starting mid-§3 should have stopped me), but it makes the failure mode reproducible
    rather than a one-off, and §4 owns the test requirements for every remaining commit.

---

## C6c fold-in verification (plan `ffb945c1`) — Findings 9/10 closed, one new low-severity note

`ffb945c1` folds `plan__ta-anchor-pr2-c6c-fsv-currency-gaps.md`. It is **more thorough than what I raised**,
and I verified its load-bearing claims against the code at `d9f3b97e` rather than taking them on the page.

### Findings 9 and 10 — CLOSED (folded, and extended)

- **Finding 10** (the `maxDemand` fallback as an unnamed fifth lock-step site) → plan §2 #5 **(v)**, with
  more than I asked for: keep-and-fix rather than delete (deletion would need a §4b classification and would
  change the `fsv > 0` admission at `:134`), the reachability argument via `ApplyDefaults` rewriting
  `Priority == 0 → 1.0`, and the pre-existing max-vs-sum asymmetry named as pre-existing rather than folded
  silently into C6c. The doc comment at `:53-60` is also named. Nothing left from my side.
- **Finding 9** (the `fairShareCap` cross-variant mismatch on fall-through) → plan §2 #5 **(ii)** plus §2d.5
  *The fall-through case (ii) must survive*, with the fix I could not supply: `prcRef` needs **no new closure
  parameter**, because the closure already computes `sortByCostEfficiencyAsc(roleVCs)` and `prcRef` is that
  slice's first `PRC > 0` entry. Cleaner than anything I proposed.
- **Site (iv) is the planner's own**, found while verifying §2d.5, and is the sharper half of the bug: the
  `ps[i][role] > target` clamp at `~:285-291` compares **raw capacity** against `target`, so it truncates
  every role to a handful of capacity units the moment `target` becomes replica-space. Inert today only
  because `target` is the sum over roles. I had not found it.

### Claims I verified in code (all confirmed; one is stronger than the plan states)

> ⚠️ **The fourth row is VOID as of plan `1a116e7a`** — and it is the one row here that under-warns, so
> do not carry it forward. It concluded "**no golden can move on (ii) at any fixture shape**," which was
> true in **replica space** (the cap divided the `prcRef` rescale straight back out). GPU space replaces
> the cap with `floor(remaining_GPUs / GPUsPerReplica)`, and **`ceil → floor` does not cancel**: the
> sat-only goldens *do* reach the cap at `sorted[0]` (one active model ⇒ `allocationMean = 0` ⇒
> `target = fsv`, generally fractional). The plan retracted its own matching claim in §2d.5 *Goldens* and
> now requires: run the goldens **per commit**, and if one moves, **prove** the delta is exactly the
> one-replica `floor` boundary and take it to Dean via a `plan__` handoff before touching a golden. Rows
> 1–3 stand as written (row 3's no-mutation check on `sortByCostEfficiencyAsc` is still useful — C2's
> input integrity does not depend on the pivot).

| Plan claim | Verdict |
|---|---|
| `costEfficiency` returns `math.MaxFloat64` for `PRC <= 0`, so `sorted[0]` is the first `PRC > 0` entry | **Confirmed** — `cost_aware_optimizer.go`, the `if vc.PerReplicaCapacity <= 0 { return math.MaxFloat64 }` guard |
| `fairShareCap` is at `greedy_score_optimizer.go:423` (corrected from `:421`) | **Confirmed** — `fairShareCap := int(math.Ceil(target / vc.PerReplicaCapacity))` sits at `:423`, between the `gpusAvail < gpusPR` skip (`:420`) and the `headroom <= 0` skip (`:427`), exactly as §2 #5 (ii) describes |
| `sort.Slice` deterministic for identical input ⇒ `prcRef` bit-identical on both sides | **Confirmed**, and safer than the argument needs: `sortByCostEfficiencyAsc` does `make` + `copy` **before** sorting, so it never mutates its input. Both sides can sort the same slice with no ordering dependence between the calls, and no side effect on `w.anchor.VariantCapacities` for later consumers (`refreshAnchorSizing` iterates that slice — I checked specifically because an in-place sort would have perturbed C2's input; it does not) |
| the rescale is neutral because "for `vc == v_role` the ratio is exactly 1" | **Confirmed, and understated.** `combineVotes` returns `float64` with no internal `ceil`, so `target` after (i) is an unrounded `demand/prcRef`; the rescale is then `ceil((demand/prcRef) × prcRef / vc.PRC)`, and `prcRef` **cancels for every candidate**, not just for `v_role`. So site (ii) reproduces today's `ceil(demand/vc.PRC)` for the whole loop, and **no golden can move on (ii) at any fixture shape** — a stronger ship-gate argument than the one written, which only covers the single-variant case |

### Finding 15 — **MOOT** (plan `1a116e7a`: the round trip no longer exists) — the `prcRef` round-trip can push an exact-integer quotient over a `ceil` boundary

> Historical. The mechanism was *divide by one PRC, multiply by another*; GPU space has one conversion
> **in** (row 0) and one **out** (row 8), and the cap divides by `GPUsPerReplica` — immutable topology.
> Nothing to keep in sync, so there is no round-trip to push a quotient over a boundary. A *different*
> boundary hazard is now deliberate at row 6 (`ceil → floor`); it is not this one, and it is specified
> rather than latent. Nothing for me to check at C6c from this finding.

The cancellation above is algebraic, not bit-exact. `fl(fl(fl(d/p) × p) / q)` carries up to three roundings,
so it can land at `(d/q)(1 + ~3·2⁻⁵³)`. Where `d/q` is **exactly** an integer *n*, `math.Ceil` then returns
**n+1** where today it returns *n* — an off-by-one in the cap, silently, on round numbers.

I am not raising this as a handoff, because the bite zone is genuinely narrow at both ends:

- **Production values are safe by inexactness.** `target = w.remaining − mean` is an arbitrary float and PRCs
  come from `μ` computations (2618.93-shaped), so `d/q` is essentially never integral and `ceil` has margin.
- **Fixture values are safe by exactness.** The §2d.5 table's own case — `d=50000, p=10000, q=2000` — is
  exact at every step (`50000/10000 = 5.0`, `5.0 × 10000 = 50000.0`, `50000.0/2000 = 25.0`), so it yields 25
  and not 26. Decimal integers of that size are exactly representable, and so is each quotient.
- The residue is the seam: a fixture with a **non-round** `prcRef` (4600, 2618.93) whose demand happens to
  divide evenly by the *other* candidate's PRC. Reachable by construction, not by accident.

There is no `ceil`-tolerance idiom to reach for if it does bite — `:423`, `analyzer_helpers.go:520` and
`rescale.go:585` are all bare `math.Ceil` (`rescale.go` uses `1e-9` only for comparisons, `:106`/`:121`).
The clean formulation is to avoid the round-trip rather than to add an epsilon: keep the demand-space sum
available alongside the replica-space `target` and compute the cap from it directly. **What I will check at
C6c:** if the coder writes the literal product, re-derive the new fall-through fixture's expected cap by hand
and confirm it is not sitting on an integer boundary; if they retain a demand-space quantity, this is moot.

### Outstanding — pre-C6c (revised)

- Findings 9 and 10: **closed**, folded into plan §2 #5 (i)/(ii)/(v) and §2d.5 by `ffb945c1`. No handoff open.
- Finding 15: **mine to check at C6c review**, not the planner's to act on.
- Checklist for C6c, unchanged from the earlier section except where `ffb945c1` sharpened it:
  1. `Score` gone from all six names in plan §6's grep.
  2. **Five** lock-step sites converted, not four — (i) `fairShareValue` primary + all three call sites
     (`:133`, `:348`, `:350`), (ii) `fairShareCap` with the `prcRef` rescale, (iii) the scale-down tie-break,
     (iv) the `ps[i][role] > target` clamp, (v) the fallback return.
  3. `prcRef` and `v_role` sourced from the **same** slice and the **same** role filter — a separately-built
     copy re-opens the mismatch through a second door.
  4. The fallback **kept**, not deleted (else a §4b DEPRECATED classification is owed).
  5. The `:53-60` doc comment rewritten — it names `Score`.
  6. T1.4 rewritten per §2d.6, asserting both the replica number **and** the binder index.
  7. The new fall-through fixture is **multi-variant within one role** — every existing fsv fixture is
     single-variant-per-role, where the error is identically zero.
  8. Goldens **re-run by me** on a scratch extract, not just reported green; §2d.5 predicts they cannot move.
     **Corrected 2026-08-07 — green goldens are necessary but NOT sufficient for site (ii).** I enumerated
     all 8 and none can see the `prcRef` rescale (see **Finding 18**'s coverage table): the picker returns
     at `sorted[0]` = `v_role` where the ratio is 1.0 by construction, the only spec with differing
     same-role PRCs (A4) never reaches its second candidate, and the only spec that does reach two
     same-role candidates (B2) has identical PRCs. So do not read green goldens as evidence the rescale
     landed — that is what checklist item 7's fall-through fixture is for, and item 7 is now the **sole**
     guard for site (ii).
  9. **Six** fsv-formula locations updated — four in the dev guide, two in code. **The plan now says six
     too** (`9f09b91d`, folding **Finding 17** — verify against the plan's own §5/§6 text, not against this
     item, since the plan is what the coder reads). Docs: `multi-analyzer-pipeline.md:622` and
     `:675`, `quota-limiter.md:284` (`### Fair-share interaction`, "priority × score × unmet demand") and
     `quota-limiter.md:328` (the parenthetical caveat, "priority × score × demand"). Code:
     `greedy_score_optimizer.go:53-60` (`fairShareValue`'s own doc comment, already in plan §5) and
     `:15-18` (the `GreedyByScoreOptimizer` **type** doc comment, not in §5). A C6c that edits only
     `multi-analyzer-pipeline.md` leaves a stale Score-bearing formula shipped in `quota-limiter.md`; one
     that satisfies §6's six-function criterion literally leaves the exported type's own doc comment
     asserting `priority × Σᵢ(Remainingᵢ × Scoreᵢ)`. While in `quota-limiter.md`, the worked example
     (~L309-325, "Wants" 3/4/4, mean ≈ 3.67) already reasons in replicas, so its "worked-example caveat"
     hedge should go and **no number in it changes** — if a number does change, the fsv conversion is wrong.
  10. Do **not** trust §5's `~L` line numbers: they are as-of `f6485980`, PR-1's *pre-rebase* tip, whereas
      PR-2's base is `075a208e`. §5 says to grep the heading text, and every entry supplies it — use that.
  11. **Review C6c and C6d against plan tip `08e264bd`, and check which spec the diff actually implements.**
      Two planner triggers landed *after* C6b and were still unconsumed when I checked: `…__c10-effect-corrected.md`
      and `…__c6c-c6d-c10-plan-updates.md` (the latter written one minute after `08e264bd` itself). C6b
      committed at 03:37; those bells rang at 03:16 and 05:13. The coder had consumed
      `…__c6-answered-plus-c10.md` (`.WIP`) before resuming C6, so it is working from *some* post-block plan
      state — but not necessarily the one that re-derived C6d's trigger as mid-loop rather than at role entry,
      nor the one that added the `quota-limiter.md` fsv copy and the C10 tolerance bound. If the C6c/C6d diff
      matches the pre-`08e264bd` spec, that is a finding against the diff, not against the plan. This is a
      note to *me* about which revision to diff against; the doorbell is already ringing twice, so a third
      trigger from me would add nothing.

---

## C6d fold-in verification (plan `08e264bd`) — Finding 11 superseded, accepted

The planner's `08e264bd` **partially** corrected Finding 11, and its commit message is explicit that this
is "a partial correction of the handoff, not an acceptance". I verified both halves independently rather
than taking the correction on trust, and I accept it. Finding 11 is **SUPERSEDED** — not withdrawn, not
upheld.

**What survived from Finding 11.** The observation that a direct `safeRemovalReplicasForRole` unit call
with `RoleSpare[role] = 0` is green *for the wrong reason* — `needsScaleDownForRole` vetoes the role
before the pipeline can ever deliver that state at role entry, so such a test passes identically before
and after the change and proves nothing. That is now recorded in plan §4's C6d preamble as
"green for the wrong reason", with the requirement that **every** C6d fixture drive
`scaleDownRoleIterated` end-to-end. This is the useful half.

**What I had wrong.** I inferred from the same observation that the fix was therefore unreachable and
should be dropped or reduced to a test-only change. It is reachable **mid-loop**: the veto is evaluated
once per role *before* `scaleDownVariantSet` iterates, and `applyDeallocationForRole` decrements
`RoleSpare[role]` as each variant sheds. A `RoleSpare[role]` that is positive at role entry can therefore
reach exactly 0 partway through the variant loop, with later variants still to be considered. The fix
stays, and it is not test-only.

**Verification 1 — the arithmetic, by hand from the shipped loop.** From `combineVotes`
(`analyzer_helpers.go:398-406`): `excess := vt.Score - votes[b].Score`, `correction += (e - vt.Value) * excess`,
`return e - correction/sumScore`. With `up=false`, binder X voting 0 and Y voting 10, and `s_Y > s_X`:
the extremum `e = 0`, so `correction = (0 - 10)(s_Y - s_X) = -10(s_Y - s_X)`, which is **negative**, giving

  `v* = 0 - (-10(s_Y - s_X))/(s_X + s_Y) = +10(s_Y - s_X)/(s_X + s_Y) > 0`

X's `0` is pulled positive and removal proceeds — matching the plan's derivation exactly. At scores
1/10 the magnitude is `10 × 9/11 = 8.18`, floor **8**. This is why the plan's second C6d fixture is
"the case that proves the fix must be a veto rather than a vote": a vote of 0 is *weighable*, and
dominance weighting will weigh it away. Only a veto is unweighable.

**Verification 2 — the four structural claims, in code.**

| Claim | Site | Verified |
|---|---|---|
| Veto evaluated once per role, outside the variant loop | `cost_aware_optimizer.go:439` (gate) vs `:447` (loop) | ✅ |
| Magnitude is per-variant, re-queried each iteration | `:139` `maxRemovable(vc)` → `:449` `safeRemovalReplicasForRole` | ✅ |
| Spare is decremented and clamped as variants shed | `analyzer_helpers.go:658-660` | ✅ |
| Magnitude divides by each voter's **own** PRC, not the anchor's | `analyzer_helpers.go:502` | ✅ |

**One point checked and deliberately *not* raised.** The "outscored objector" fixture only goes red if
the two voters carry **unequal** scores — at `s_X = s_Y` the correction term is identically zero and X's
`0` survives as the extremum, so the fixture would be green before the fix and prove nothing. Before
writing this up I read plan §4 and §2d.4: §2d.4 already states "(Only `s_Y ≤ s_X` leaves `v* = 0`.)" and
§4's fixture spec already requires that X "carries a lower `Score` than the other voter". **Already
covered — no handoff sent.** Reading §4 *before* reporting is the exact step whose omission produced the
withdrawn C10 tolerance handoff; applying it here is what kept this from being a third redundant ask.

---

## Finding 16 (latent, no handoff) — anchor PRC 0 excludes a variant from scale-down entirely

**Not a blocker. Not currently reachable. Recorded so C7's review has a specific thing to check.**

Under N8, when the binding analyzer omits a variant the merged anchor entry keeps
`PerReplicaCapacity = 0` — deliberate, and documented in place:

```go
// else: the binder omits this variant — PerReplicaCapacity stays 0
// (abstain), uniformly regardless of whether saturation votes (N8; ...)
```
— `analyzer_helpers.go:213-216`

The scale-down path then reads *the anchor's* PRC as an eligibility guard, while the removal magnitude
reads *each voter's own* PRC:

- `scaleDownVariantSet` skips on the anchor: `if vc.PerReplicaCapacity <= 0 { continue }` — `cost_aware_optimizer.go:125`
- `votesFromRoleSpare` sizes per voter: `e.RoleSpare[role] / prc` with `prc = prcForVariant(e.Result, name)` — `analyzer_helpers.go:502`

So a variant that the **binder** omits but another **live voter** sizes with positive spare is skipped
from shedding altogether, even though the role's veto has already cleared and that voter would have
permitted removal. The guard and the magnitude disagree about which PRC is authoritative.

**Why it is not reachable today**, checked config by config:

| Config | Binder | Divergence? |
|---|---|---|
| `[sat]` only | sat | No — sat is the identity carrier and "emits every configured variant" (`:191`), so it omits nothing. |
| `[sat, TA]`, sat voting | sat | No — same reason. |
| `[sat, TA]`, sat enabled but dead | TA | No — dead sat is pruned from `votingResults`, so TA is the only voter; it omits the variant on both paths and the two agree. |
| `[sat, TA]`, sat enabled + **live** but not informative | TA | No, but only because of an unasserted invariant — see below. |
| `[TA]` only | TA | No — single voter, guard and magnitude read the same result. |
| ≥2 non-saturation voters | lowest-index | **Yes** — voter 2 sizes what the binder omits. |

The divergent row needs two non-saturation voters, which PR-2 makes *mechanically* possible but no shipped
config produces. Same class as Finding 15: latent, bounded at both ends, no handoff.

**The fifth row is the near-miss, and it is worth writing down precisely** — it would put the divergence in
the *shipped* `[sat, TA]` config with a single non-saturation analyzer, so "needs two non-sat voters" would
stop being a bound. The voter set and the binder set are filtered differently:

| Set | Filter | Site |
|---|---|---|
| voters | `Enabled && Live` | `votingResults` — `analyzer_helpers.go:227-238` |
| binder-eligible | `Enabled && Live && ResultIsInformative` | `bindingAnchor` — `analyzer_helpers.go:143-162` |

The gap between them is exactly *live but not informative*. Such a saturation result **votes** while TA
**binds** — one non-sat analyzer is enough, and the guard/magnitude disagreement above becomes reachable.

It does not happen today, and the reason is not in the engine — it is a property of the producer.
`ResultIsInformative` keys on `Reason`, never on PRC (`:53-63`), so the two agree only because every
`Reason` in its exclusion set happens to imply `PerReplicaCapacity == 0`:

- **`ReasonNoData`** — set at `analyzer.go:431`, in the `else` of `len(replicas) > 0`. `perReplicaCapacity`
  is declared *inside* the per-variant loop (`:370`), so it is a fresh zero on that branch. PRC 0. Safe.
- **`ReasonError`** — the one production producer is `k2SourceLabel`'s defensive default (`:814`), reached
  when `k2Labels[medIdx.K2Priority]` misses. Its only call site is `:420`, **inside** the branch that has
  already assigned `perReplicaCapacity = float64(median(capacities))` at `:399`. So this reason arrives with
  a *positive* PRC — it is the combination that would open the divergence.

That default is unreachable in production, which is what closes the row: `ReplicaCapacity` has exactly two
construction sites (`:209`, `:277`), `computeK2` returns one of the four mapped constants on all four of its
return paths (`:303-334`), and `k2Source` is `iota + 1` so all four are keys in `k2Labels`. `K2Priority` is
therefore never the unmapped zero, and `:814` is reachable only from a hand-built fixture that omits the
field. With PRC 0 on every variant, a non-binding saturation voter is then dropped outright by
`votesFromRoleSpare`'s own `if prc <= 0 { continue }` (`:499`) — it sizes nothing, so guard and magnitude
cannot disagree.

**So the invariant Finding 16's fifth row rests on is: `Reason ∈ {NoData, Error}` ⇒ `PerReplicaCapacity == 0`.**
Nothing asserts it, and three ordinary edits would break it: adding a `k2Source` constant without a
`k2Labels` entry (or a third `ReplicaCapacity` construction site that leaves `K2Priority` unset), hoisting
`perReplicaCapacity`'s declaration out of the loop at `:370`, or adding a `Reason` to
`ResultIsInformative`'s exclusion set that does not imply PRC 0.

Worth noting that half of this coupling is already documented, in the same file that defines the other half.
`types.go:29-31` says `satReasonNoData` "aliases the shared pipeline sentinel so this producer and the
engine's liveness gate (`pipeline.ResultIsInformative`) cannot drift apart" — the `NoData` half. The
`ReasonError` half of the identical coupling is undocumented, and it is the half where PRC is already
positive. **No handoff:** all of this is PR-1/pre-existing code, PR-2 changes none of it, and the conclusion
is that the shipped configs are safe. Recorded because the *reason* they are safe is three files away from
the code that depends on it.

**C7 checklist item — checked against `952d2fff`, answer is negative.** §4's C7 line includes "Test 2
rewrite (v2 PRC=0 under N8)" — the one fixture family that puts an anchor PRC of 0 in front of this
code — so I went back through C7's diff (reviewed before this finding existed) to see whether that
rewrite happens to pin the **scale-down** skip as well, which would close the finding by construction at
zero cost. It does not. None of C7's three new/rewritten fixtures reaches
`scaleDownVariantSet`'s `if vc.PerReplicaCapacity <= 0 { continue }`:

| C7 fixture | What it drives | Reaches the scale-down skip? |
|---|---|---|
| Test 2 (`analyzer_helpers_test.go`) | `bindingAnchor` directly — asserts `VariantCapacities[1].PerReplicaCapacity == 0.0` and `Reason == ""` | No — never reaches the optimizer |
| VG-up (`optimizer_liveness_test.go:28`) | `NewCostAwareOptimizer().Optimize(...)`, but on the **scale-up** branch (stale `RequiredCapacity: 100000`, asserts target stays 1) | No — wrong branch |
| both `needsScaleDownForRole` specs (`:75`, `:89`) | the veto function called directly | No — not `scaleDownRoleIterated` |

So Finding 16 stays **latent**, not closed. The nearest remaining opportunity is C6d, whose §4 wording
already requires that "**Every fixture here must drive `scaleDownRoleIterated` end-to-end**" — three
fixtures that by construction go through the exact call path this finding concerns. At C6d review, check
whether any of them incidentally carries an anchor PRC of 0; if one does, the finding closes there
instead. If none does, it stays latent and the invariant above stays unasserted — which is an acceptable
outcome for PR-2, since the shipped configs are safe and PR-2 changes none of the coupled code.

**Adjacent note on C7's two `needsScaleDownForRole` specs (no finding).** The N7 abstain spec builds `ta`
via `makeNamed` (which leaves `RoleSpare` nil) and then calls `_, _ = initRoleState(s)` to seed
`RoleSpare[RoleBoth] = 5000` — relying on `initRoleState` mutating `s[i].RoleSpare` through the slice's
backing array, which it does (`analyzer_helpers.go:293-307`). That works, and `makeNamed` does set
`Live: true`, so the live-voter abstain path is genuinely exercised. But the `initRoleState` call is
documentary rather than load-bearing for the assertion: `needsScaleDownForRole` reads
`spare, ok := e.RoleSpare[role]`, and a nil map and a populated-map-missing-the-key are the same input
class (`ok == false`, abstain). The spec would therefore still pass if `initRoleState` stopped seeding
`RoleBoth` entirely. It pins the abstain **branch** correctly; it does not pin the distinction its own
comment draws ("only `RoleBoth`, no `prefill` key"). Not worth changing — noted so a later reader does
not credit this spec with catching a regression in `initRoleState`'s seeding.

---

## Verified clean — the scale-down path needs no anchor refresh

`refreshAnchorSizing` is invoked only inside `allocateForModelPaired`, i.e. on the scale-up branch
(`cost_aware_optimizer.go:61-66`). The scale-down branch calls `scaleDownRoleIterated` with the
un-refreshed `anchor.VariantCapacities`. I checked whether that is a §3 gap. **It is not**, and the
reason is structural rather than incidental: on scale-down the anchor's PRC is never used for sizing.

| Anchor field read on scale-down | Used for | Stale-sensitive? |
|---|---|---|
| `PerReplicaCapacity` | `> 0` eligibility guard only (`:125`) | No — a stale-but-positive value guards identically (but see Finding 16 for the 0 case) |
| `Cost`, `VariantName` | ordering (`sortVariantsForScaleDown`) | No — identity, sourced from the identity carrier |
| `AcceleratorName`, `Cost`, `Utilization` | `buildDecisionsWithOptimizer` observability | No — identity/observability, not sizing |

Removal magnitude comes entirely from `safeRemovalReplicasForRole` → `votesFromRoleSpare`, which divides
each voter's `RoleSpare[role]` by **that voter's own** PRC read straight from its `Result`
(`analyzer_helpers.go:502`), never from the anchor. Refreshing the anchor mid-scale-down would change
nothing a decision depends on. No finding; recorded because "the refresh is missing on one of the two
branches" is the kind of asymmetry a later reader will re-raise, and the answer is worth having written
down once.

---

## C9 checklist (no handoff — §4 already says "explicit commit")

§4 requires C9 to remove the sat-only #1513 goldens "as an **explicit commit** (not an implicit drop)"
with a message that "states the multi-vote suite that now covers the sub-case". Dean's RELAX/REMOVE
decision is recorded with his name and date, and the goldens do gate C1–C8 before removal, so the
removal itself is settled and I am not re-opening it.

One residue is worth verifying **at the diff** rather than pre-emptively amending a plan that already
says "explicit commit": the failure mode this guards against is a commit that deletes the goldens *and*
adjusts a multi-vote expectation in the same breath, which would make "the multi-vote suite covers it"
unfalsifiable — the suite would have been edited to be green rather than shown to be green. So at C9:

1. The removal commit is **removal-only** — no expected-value edits to any other test in the same commit.
2. The multi-vote suite is already green on the parent commit, verified by me on a scratch extract, so
   the deletion demonstrably subtracts coverage that was already replaced.
3. The commit message names the covering suite, and the named suite genuinely contains a `[sat]`-only
   and a `[TA]`-only sub-case (§4's wording requires both).
4. §4a: the message must not carry `#1513`'s plans-side framing — the PR number itself is a real GitHub
   reference and is fine.

**5. There are two adjacent files whose names both read "characterization goldens", and only one of them
is in C9's removal scope.** §4 scopes the removal to "the *sat-only* characterization goldens (landed via
their own PR #1513)". Checked provenance with `--diff-filter=A`:

| File | Specs | Added by | In C9's removal scope? |
|---|---|---|---|
| `optimizer_characterization_test.go` | 8 (smoke, A1–A4, B1–B2, C1) | `35b336ea` — #1513's own harness commit | **Yes** — this is the sat-only suite |
| `optimizer_combine_characterization_test.go` | 1 (two-analyzer scale-up, throughput demand dominates) | `a0795e36` — PR-1's C2, "derive the per-model anchor on demand" | **No** — not sat-only, not a #1513 artifact |

The second file is a test **PR-1 shipped inside its own commit**, and it is already a `[sat, TA]` golden —
which makes it the natural host for the multi-vote suite §4 line 958 asks C9 to add, not something to
delete. A `git rm` that reaches for "the characterization goldens" and takes both would silently remove
PR-1 coverage in a commit whose stated purpose is removing #1513's, and the §4b classification owed would
be for the wrong file.

**6. Spec-count arithmetic makes both of the above mechanically checkable.** Baseline measured by me on a
clean extract of `d9f3b97e` (C6b): **334 of 334 specs pass** in `internal/engines/pipeline`. So after C9:

- `optimizer_characterization_test.go` gone, `optimizer_combine_characterization_test.go` still present;
- spec count = `334 − 8 + (specs the multi-vote suite adds)` — if it comes out at `334 − 9 + n`, the
  combine golden went with them.

Recording the baseline number here because after C9 there is no cheap way to recover it: the count is the
only artifact that distinguishes "removed 8" from "removed 9".

---

## C10 — plan arithmetic independently re-derived (so review goes straight to the code)

Every number in §2e.3 and §5's C10 block checks out by hand, on the shipped fixture
(`analyzer_test.go:266-274`: `A=0.073 B=0.006 KV_max=1024000 KVreq=4600`). `N_sat = k·KV_max/KVreq`,
`ITL_sat = A·k + B`, `μ_sat = N_sat/ITL_sat`:

| k | `N_sat` | `ITL_sat` | `μ_sat` | note |
|---|---|---|---|---|
| 0.85 | 189.2174 | 0.06805 | 2780.56 | today (deleted `DefaultKSat`) |
| 0.80 | 178.0870 | 0.06440 | 2765.33 | post-C10 default (`DefaultKvCacheThreshold`) |
| 0.50 | 111.3043 | 0.04250 | **2618.93** | the C10 `KvCacheThreshold: 0.5` fixture |

Default-path shift = `2765.33/2780.56 − 1` = **−0.548%**, matching §2e.3. My earlier ~5.9% figure was the
numerator alone; §2e.3 now records the correction and, correctly, tells the coder to keep the 6% figure out
of the commit message.

**Two things I had queued to raise and did not, because the plan already covers them.** Recording the
checks so they are not re-done:

- **The default moves 0.85 → 0.80, so every existing TA fixture re-bases**, since no TA test sets
  `input.Config` and all take the fallback. §2e.2 states the fallback choice and why ("A 0.85 nil-config
  fallback would keep a second definition of 'full' alive in exactly the path the TA unit tests exercise"),
  and §2e.3 works out that the three `TotalSupply` assertions sit at `±10%` (`muSat*0.10`), so a 0.55% shift
  cannot go red. Verified: `2780.56` and `2765.33` are both inside `2782.0 ± 278.2`.
- **The dangerous case is a green gate on a wrong expectation.** §2e.3 already names it: re-deriving by
  scaling `0.80/0.85 = 0.9412` alone lands ~5% off, which the ±10% tolerance swallows. This is why the new
  k=0.5 fixture must *not* inherit the `muSat*0.10` idiom.

**At C10 review, therefore, the arithmetic is settled and I check only:** that the k=0.5 fixture asserts
`2618.9` within `~1%` (band `[2592.7, 2645.1]`) and not a `muSat*0.10` band; that it goes **red** when I flip
`resolveKSat` back to `0.85` on a scratch extract (2780.56 is outside the band — the fixture genuinely
discriminates); that `resolveKSat` threads to all **four** sites of §2e.2's table; that `DefaultKSat` greps
to zero while `DefaultNearKSatMargin` survives with re-anchored prose; that the `:259-264` derivation comment
no longer spells `0.85`; and that the five `throughput-analyzer.md` locations in §5 are all edited, including
the constants-table row swap and the *retained* EPP half of the known-limitations line.

### C10 pre-measured inventory (baseline at `d9f3b97e`, so the grep-to-zero has a denominator)

`DefaultKSat` appears **17 times** across 6 files. Split by what C10 owes each one:

| Kind | Count | Locations |
|---|---|---|
| the definition (deleted) | 2 | `throughput/constants.go:52` (doc), `:56` (the `= 0.85`) |
| **code uses** (threaded) | 4 | `analyzer.go:295`, `analyzer.go:719`, `itl_model.go:53`, `analyzer.go:845` |
| prose (rewritten) | 11 | `throughput-analyzer.md` ×5 (`:460 :470 :639 :675 :692`) · `constants.go:89`,`:91` (inside `DefaultNearKSatMargin`'s own comment) · `analyzer.go:708`,`:796` · `itl_model.go:52` · `itl_model_test.go:136` |

**§2e.2's four table rows are exactly the four code uses — verified exhaustive, nothing is missing from the
plan.** That is the useful conclusion: after C10 the entire residue is prose, so a `DefaultKSat` grep that
still returns hits is a doc-sweep miss, not a threading miss. Note two of the eleven prose hits live in
`DefaultNearKSatMargin`'s *own* doc comment — the constant §2e.2 says must survive — so "delete every line
mentioning `DefaultKSat`" would take the surviving constant's documentation with it.

**`FitITLModel`'s signature growth is contained, and the plan's "it is exported" note overstates the blast
radius in a useful direction.** Callers, all in-package: 1 production (`analyzer.go:565`) and **10 test call
sites** in `itl_model_test.go` (`:48 :56 :64 :72 :75 :81 :92 :99 :107`, plus the `Describe`). No caller
outside `internal/engines/analyzers/throughput` anywhere in the repo. `validITLModel` has 2 production
callers, both named correctly by the plan (`itl_model.go:88`, `analyzer.go:602`).

**The trap §2e.2 identifies for the nil-config fallback reappears at those 10 call sites, and the plan does
not extend it there.** Its argument is that a `0.85` fallback "would keep a second definition of 'full' alive
in exactly the path the TA unit tests exercise". A test that satisfies the new parameter by passing a literal
`0.85` does the same thing by another route — compiles, passes, and pins the old basis. At C10 I check what
those call sites pass: `config.DefaultKvCacheThreshold`, or a value the test derives, but not a bare `0.85`.
(The one fixture whose *expectation* depends on k is `:136-137`, `validITLModel(0.01, -1.0)` ⇒ false: at both
0.85 and 0.80 that is `≈ −0.99 ≤ 0`, so it stays red-correct either way and only its comment needs rewriting.)

**Why the `itl_model.go` row is load-bearing and not tidy-up — calibrated, because a consumer-side guard
already backstops most of it.** `validITLModel` accepts iff `a·k + b > 0`, and `a > itlSlopeEpsilon > 0` is
enforced two guards earlier, so `a·k + b` is strictly increasing in `k`. A guard left at 0.85 while the
consumer resolves 0.80 is therefore strictly *more permissive* than its consumer — and 0.80 < 0.85 means the
new default sits on the unsound side, not the conservative one. It is not a divide-by-zero, because
`analyzer.go:296` independently does `if itlSat <= 0 { continue }`. But that backstop checks the **sign**,
whereas the guard's own comment gives its purpose as near-zero ("*a noisy fit can yield negative b (valid
a>0), making `ITLAt(DefaultKSat)` near-zero and inflating supply*"). A model with `0 < a·0.80 + b < 0.05a`
passes the stale validator *and* `:296`, then divides by a near-zero `itlSat`. At the fixture's `a = 0.073`
that band is `(0, 0.00365)` against a normal `itlSat ≈ 0.0644`, i.e. up to ~18× inflated supply, reachable
only for `b ≈ −0.058` — the strongly-negative-intercept noisy fit the comment names. Narrow, but it is the
exact failure the guard exists for, and skipping the row as cosmetic would have C10 *open* it. So: threaded
from the same `resolveKSat` result the consumer uses, not a second resolution and not a literal.

---

## Finding 17 (should-fix, pre-emptive — plan-side undercount) — **CLOSED** (`9f09b91d`) — the Score-bearing fsv formula is written in **six** places, and the two the plan misses both slip §6's greps as worded

**Closed 2026-08-07 by plan commit `9f09b91d`**, ~9 minutes after the handoff went out and before C6c was
written — the cheap window held. All four suggested edits landed, and one landed stronger than asked: I had
suggested changing `quota-limiter.md`'s "one location" to two, and the planner instead specified **deleting**
the `:327-329` parenthetical rather than softening it, on the grounds that a softened copy still survives
§6's grep-to-zero and costs the same mid-commit round-trip. That is the right call and it is now the plan's
instruction. Verified after the fold-in: the plan says "**Six copies total**" in §5 and "**four places**" for
the doc-half grep in §6; §6's code-grep criterion now names `greedy_score_optimizer.go`'s file- and
type-level doc comments explicitly, which is the only path by which `:15-18` is reachable; the four cited
doc line numbers (`:284`, `:328`, `:622`, `:675`) match my measured grep exactly; and the TOC line ranges
(§5 L995:1096, §6 L1097:1180, §7 L1181:1231) resolve to the real headings, so the refresh ran after the
content edits. **At C6c review, check the diff against the plan's text, not against this finding** — the
plan is what the coder reads, and it is now the more precise of the two.

Original finding follows, kept because it records the *method* (measure the denominator before reviewing the
sweep) that produced it.

**Handoff sent** (`plan__ta-anchor-c6c-fsv-formula-copies.md`), because C6c is not yet written and this is
free to fix now and a coder round-trip after. Found by pre-measuring §6's C6c greps at `d9f3b97e` to get a
denominator for the grep-to-zero check, rather than by reading the plan's prose.

Plan §5 (L1001-1002) states *"The fsv formula appears in **three** places across two files"*; §6 (L1113)
repeats the same three as the pre-fix expectation. Measured at `d9f3b97e`:

| Location | Text | In plan's edit map? |
|---|---|---|
| `multi-analyzer-pipeline.md:622` | `fairShareValue = priority × Σᵢ Score_i × …` | Yes |
| `multi-analyzer-pipeline.md:675` | `fsv = Priority × Σᵢ Score_i × …` | Yes |
| `quota-limiter.md:284` | "priority × score × unmet demand" | Yes (§5's "one location") |
| `quota-limiter.md:328` | "priority × score × demand" | **No** |
| `greedy_score_optimizer.go:53-60` | `fsv = priority × Σᵢ Score_i × …` | Yes |
| `greedy_score_optimizer.go:15-18` | `priority × Σᵢ(Remainingᵢ × Scoreᵢ)` | **No** |

**Why `:15-18` is the more serious of the two.** It is the doc comment on the exported
`GreedyByScoreOptimizer` type — the first prose a reader of the file being changed encounters — and it
asserts both halves of what C6c changes (Score inside fsv; demand units). It slips **both** C6c greps as
their acceptance criteria are phrased:

- the code grep is `grep -rn "Score" internal/engines/pipeline/`, but the criterion is "no `Score` reference
  in `fairShareValue` … `fairShareCap`, `computeMean`, `sortByRemainingDesc`, `allocateForModel`, or
  `sortVariantsForScaleDown`" — and `:18` is inside none of those six, so the criterion passes with it stale;
- the currency grep is `fairShareValue|w.remaining|fsv|remaining demand|unmet demand`, and `:17` says
  "fair-share priority **value**" — none of those tokens match.

`quota-limiter.md:328` is milder: it sits inside the same `### Fair-share interaction` section as `:284`
(L278-330), which §5 does send the coder into, and §5 separately says the L327-329 "hedge can go" — deleting
that sentence removes the copy incidentally. The gap is that §5 calls it "**one** location" and never names
the formula inside the hedge, so a coder who *softens* the hedge rather than deleting it produces one grep
survivor and gets routed into a `plan__` round-trip mid-commit — which is the expensive path §6's preamble
prescribes for genuinely unanticipated hits.

**Two things I checked and did not raise**, both because the plan already covers them — the sixth and
seventh consecutive candidate findings to die that way, which is a good sign about the plan:

- The fall-through fixture only goes red if the *un-allocated* variant is `sorted[0]` by
  cost-**efficiency**; if the allocated one is `sorted[0]` then `prcRef == PRC_vc`, the ratio is exactly 1,
  and the fixture is green before and after the fix. §4's C6c bullet already pins it: "different PRCs **and**
  different costs, the cheaper-**efficiency** one made infeasible".
- `docs/plans/engine/rescale-alpha.md:8` ("priority × demand") is rescale-alpha's group-budget rule, not
  fsv, and C5 changed the demand→GPU *conversion* rather than that weighting. Excluded deliberately.

**§2d.5's arithmetic re-derived independently** (same discipline that caught Finding 6), and it holds:
`target_new = 50000/10000 = 5`; with the rescale `ceil(5 × 10000/2000) = 25`; without it `ceil(5) = 5`;
under-allocation factor exactly 5, matching §4's "5 instead of 25". The neutrality claim for `vc == v_role`
also holds — `costEfficiency` returns `math.MaxFloat64` for `PRC <= 0` (`cost_aware_optimizer.go:238-243`),
so `sorted[0]` is the first positive-PRC candidate and same-slice-same-rule makes `prcRef` bit-identical to
`v_role.PerReplicaCapacity`, giving a ratio of exactly `1.0`.

**Pre-measured baselines for the C6c grep-to-zero** (so a survivor is distinguishable from a miscount):
doc-half grep = **4** hits today, not 3; `fairShareCap` is a **local variable** at
`greedy_score_optimizer.go:423` (`ceil(target / vc.PerReplicaCapacity)`), not a function, so it will not
appear in a symbol search; fsv's three call sites are `:133`, `:348`, `:350`; the Score multiply is `:73`
and the raw-unit fallback is `:78-91`.

---

## C6d pre-measurement — no new finding; the mid-loop mechanism traced to its exact defect line

Same pre-measurement pass for C6d, and unlike C6c it turned up nothing the plan misses. Recorded because
the trace names the one line the fix has to change, which makes the diff review a comparison.

**Grep denominator.** §6's C6d grep (`RoleSpare|prc <= 0|prcForVariant`, `internal/ docs/`) = **91** hits at
`d9f3b97e`, of which 29 are in `_test.go` and 62 are non-test. Unlike C10's, this grep has no
grep-to-zero target — it is a re-read-every-hit grep — so the number is only a completeness check that the
coder read the whole set.

**The defect line.** The C6d primary-red fixture works through this chain, which is worth having written
down once because the fix site is *not* the function the plan's finding is named after:

1. Live objector X sizes **v1 only** and enters the role with `RoleSpare[R] > 0`, so
   `needsScaleDownForRole` passes at role entry (`cost_aware_optimizer.go:439`, outside the variant loop).
2. v1 sheds. `applyDeallocationForRole` decrements X because X *does* have `prc > 0` for v1
   (`analyzer_helpers.go:654-658`), clamping at 0 (`:659-661`). X's role spare is now exhausted.
3. The loop reaches v2. `votesFromRoleSpare`'s `if prc <= 0 { continue }` (`:499`) drops X from the ballot
   entirely, because X has no `VariantCapacities` entry for v2 — so X's exhausted spare casts **no vote**,
   `combineVotes` never sees it, and v2's replicas come off.

`:499` is the line that makes an exhausted live objector invisible, and it is in `votesFromRoleSpare`, not
in `safeRemovalReplicasForRole` whose doc comment C6d must rewrite. This is the same skip-on-no-PRC pattern
as my **Finding 4** (downgraded to "asymmetry worth closing", owned by C6d) — so C6d closes Finding 4, and
a C6d that changes only `safeRemovalReplicasForRole`'s arithmetic without addressing the ballot-level skip
would leave the fixture green-before-and-after.

**The three comments, verbatim at baseline** (so I can diff the rewrite rather than judge it fresh):

| Site | Text today | Wrong after C6d? |
|---|---|---|
| `analyzer_helpers.go:629-631` | "Returns 0 when no live analyzer **sizes** v" | Yes — it will also return 0 when a live analyzer that does *not* size v objects at role level |
| `:645-648` | "non-live entries are already excluded from the veto … and the safe-removal minimum … so mutating their RoleSpare here is harmless — nothing reads it back" | Not false — the claim is about **non-live** entries, and they stay excluded. But the premise it leans on ("nothing reads it back") becomes load-bearing for *live* entries in a new way, so the plan's "re-read it against the new PRC-blind path" is the right instruction rather than a rewrite order |
| `:232-233` | "Scale-down was already Live-gated at point of use (`needsScaleDownForRole`, `safeRemovalReplicasForRole`)" | Still accurate — both remain Live-gated; only the *PRC* blindness changes |

**One coherence check I ran and it passes.** After C6d, the veto is PRC-blind but `applyDeallocationForRole`
stays PRC-*aware* (`:655` skips `prc <= 0`). That asymmetry is deliberate and consistent: an analyzer that
sizes no variant in the role never has its spare drawn down, so it never reaches the `<= 0` state that
vetoes — it simply grants removal, which is the pre-existing behavior. And no live keyed analyzer can be at
`<= 0` at role *entry*, because `needsScaleDownForRole` already vetoes that. So the only reachable veto is
the mid-loop one, exactly as §2d.4 (c) claims. No finding.

---

## Finding 18 — **CLOSED (`5b1e1606`), then MOOT (`1a116e7a`)** — §2d.5's `prcRef` neutrality assumes the anchor slice is stable, but C2's own refresh rewrites it mid-loop

> Historical, and worth keeping only as the reason the pivot is *safer*, not merely different. This
> finding was correct against the replica-space design and the planner folded the fix (capture `prcRef`
> before the refresh, thread it, forbid in-closure derivation). The frozen Type 1 then **deleted the
> whole construction** — plan §2d.5 *What stops existing* now retires by name every artifact this finding
> produced: the threaded `prcRef` parameter, the copied value map, the capture-before-refresh ordering at
> `greedy_score_optimizer.go:310`, the grep forbidding in-closure derivation, and the 5× fall-through cap
> table with its value-drift / identity-drift pair. Plan §2d.5 closure property 2 states the reason: the
> hazard is **gone, not solved** — in GPU space the cap divides by immutable topology, so invariant 9's
> drift cannot reach it. **Do not port any requirement from this section into the C6c review.** What does
> survive the pivot is the *reference-variant approximation in the numerator* (rows 0–2 price a claim
> using `referenceVariantForRole`'s candidate, exact only if the picker lands there) — that is an
> approximation, not the round-trip error this finding was about.

**Handoff sent** (`plan__ta-anchor-c6c-prcref-refresh-currency.md`) — C6c is still unwritten, so this is free
to fix now. Found by chasing a *different* question (are the goldens sensitive to the rescale?) into the
allocation loop, which is where the mutation lives.

§2d.5 grounds site (i)/(ii) agreement in slice identity: *"Feed both sides the **same**
`w.anchor.VariantCapacities` slice: `sort.Slice` is deterministic for a given input, so **identical input ⇒
identical `sorted[0]`**"*. The slice-identity half is true and I verified it — site (i)'s `anchor`
(`greedy_score_optimizer.go:125`) is the object stored as `w.anchor`, and `:311` passes
`w.anchor.VariantCapacities` into the allocator. **The "identical input" half is false**, because PR-2's C2
mutates that slice's *contents* between the two reads:

| Step | Site | What happens |
|---|---|---|
| 1 | `:133` / `:348` / `:350` | `w.remaining = fairShareValue(...)` — site (i) divides by `prcRef` **here**, so `target` is denominated in *this* `prcRef` |
| 2 | `:273` | `target := w.remaining - mean` — fixed scalar |
| 3 | `:310` | `pick := fairShareRolePick(target, ...)` — `target` **captured into the closure**, pre-loop |
| 4 | `analyzer_helpers.go:737` | `refreshAnchorSizing(variants, s, pickerState)` — **rewrites `variants[i].PerReplicaCapacity`** (`:569`), every iteration, **before** `pick` at `:743` |
| 5 | `:423` | `fairShareCap := ceil(target / vc.PerReplicaCapacity)` — site (ii) reads the *mutated* field |

`target_new × prcRef = target_old` holds only if step 5's `prcRef` is step 1's value. §2d.5's guidance —
same rule, same slice, both sides — applied literally *inside* the closure re-derives `prcRef` from the
post-refresh slice, which is the broken form. **Fix: capture `prcRef` where fsv is computed and thread it
in alongside `target`; do not re-derive it in the closure.**

Two independent failure modes, and the value argument does not imply the second:

- **Value drift.** Against §2d.5's own table (`v_role` = `v1` PRC 10000, `v2` PRC 2000, `target` 50000 ⇒ 5):
  if the refresh moves `v1` to 8000, a closure-recomputed `prcRef` yields `ceil(5 × 8000/2000) = 20` where
  the right answer is still `25`. Same failure mode as the 5× under-allocation §2d.5 documents, smaller and
  harder to see.
- **Identity drift.** `costEfficiency` is `Cost/PRC` (`cost_aware_optimizer.go:238-243`), so rewriting PRC
  can **reorder** `sortByCostEfficiencyAsc` — `sorted[0]` may be a *different variant* on iteration 2.

**Why nothing planned catches it.** `refreshAnchorSizing` early-returns at `len(s) <= 1`
(`analyzer_helpers.go:552-554`), so the refresh is a no-op with one voting analyzer. Every #1513 golden is
sat-v2-only ⇒ blind. And §4's fall-through fixture, **as specified**, does not say multi-analyzer ⇒ it
separates rescale-from-no-rescale (its stated job) but not captured-from-recomputed `prcRef`. So the defect
sits on the ≥2-live-analyzer path that PR-2 exists to serve, with no red test.

### The goldens are blind to the `prcRef` rescale generally (my checklist item 8, corrected)

Enumerated while getting a denominator for the above. `fairShareRolePick` **returns on the first candidate
with `capN > 0`** (`:432-434`), so normally only `sorted[0]`'s cap is computed — and `sorted[0]` *is*
`v_role`, ratio 1.0 by construction. Reaching a later candidate needs the `PRC <= 0` (`:411`),
`gpusAvail < gpusPR` (`:420`), or `headroom <= 0` (`:427`) skip. No golden sets `MaxReplicas` at all, and
`unlimitedConstraints` is 1,000,000 GPUs per pool:

| Spec | Same-role variants | PRCs | Why it cannot see the rescale |
|---|---|---|---|
| smoke | — | — | trivial no-op, no allocation |
| A1 / A2 / A3 | 1 | 10000 | `sorted[0]` is the only candidate ⇒ ratio 1.0 |
| **A4** | **2** | **10000 / 20000** | loop returns at `sorted[0]`=`cheap`; `expensive`'s cap is never computed |
| B1 | 1 per role × 2 | 10000 / 10000 | one candidate per role ⇒ ratio 1.0 |
| **B2** | **2 in prefill** | **10000 / 10000 (equal)** | both reached, but equal PRCs ⇒ every ratio 1.0 regardless |
| C1 | 1 | 10000 | single variant; and the quota binds via `gpusAvail/gpusPR = 1`, not `fairShareCap` |

§2d.5's prediction ("they stay green") is correct, and its stated reason ("single-variant-per-role") is
correct for 6 of 8 — A4 and B2 are green for the two extra reasons above. The review consequence is mine,
not the plan's: **green goldens at C6c are necessary but not sufficient for site (ii)**, and checklist
item 7's fall-through fixture is the sole guard. Item 8 now says so.

**Not verified:** that a realistic multi-analyzer refresh moves the reference variant's PRC by enough to
change a replica count. The mechanism is present and unguarded; magnitude depends on fixture construction.
The 10000→8000 numbers are illustrative, not measured.

### Sharpening (2026-08-07, after the first handoff) — the plan *mandates* the broken form, in two places

Second handoff sent: `plan__ta-anchor-c6c-prcref-site-ii-closure-param.md` (sibling, because the first is
`.WIP` with the planner). My first handoff treated the in-closure derivation as something a *literal
reading* of §2d.5 would produce. That understated it. §2 #5 site (ii), **plan L254-256**, instructs it
outright:

> `prcRef` needs **no new closure parameter** — the closure already computes
> `sortByCostEfficiencyAsc(roleVCs)`, and `prcRef` is that sorted slice's first `PRC > 0` entry

So there are two mandates, not one paragraph open to misreading — and **§2 #5 is the per-commit site
enumeration**, i.e. the half the coder follows most literally. Folding only §2d.5 would leave the plan
self-contradictory on the single decision C6c turns on, which is a worse end state than either half
alone. That is why the supplement went out mid-`.WIP` instead of waiting for C6c.

The distinction the plan misses: the ratio **is** exactly 1.0 *within* an iteration (§2d.5 is right about
that), while the *value* drifts *between* iterations. Same-slice guarantees the former and is silent on
the latter. So this bites on the **reference candidate itself** — precisely the case §2d.5 certifies as
neutral — not only on fall-through.

One correction to my own first handoff, carried into the second: `prcRef` is **per-role**, not a scalar
(§2d.5 L623-624 says "the *role's* first candidate"; site (i)'s fsv sums over roles). The threaded value
is `map[string]float64`. `:310` is a valid capture point — it runs before `allocateForModelPaired` at
`:311`, so the slice is still in the state that produced `target`.

### Scope — narrowed, not widened (verified at `d9f3b97e`)

Checked whether the hazard reaches the other lock-step sites. It does not, which means the fold-in is
bounded and no further handoff is owed:

| Question | Answer | Consequence |
|---|---|---|
| Does the scale-down path refresh? | **No.** `refreshAnchorSizing` has exactly one non-test call site, `analyzer_helpers.go:737`, inside `allocateForModelPaired`'s scale-up loop | site (iii) `sortVariantsForScaleDown` unaffected |
| Is site (ii) one location or a family? | **One.** `greedy_score_optimizer.go:423` is the package's only `ceil(target / PRC)` | no sweep needed |
| Do the vote helpers share `prcRef`? | **No.** `:445` / `:472` / `:502` divide by each analyzer's own `prcForVariant` — correct per-analyzer conversion, a different quantity | untouched |
| Does `costGreedyRolePick` have the same bug? | Shares `allocateForModelPaired` (`cost_aware_optimizer.go:62`) and therefore the refresh, but has no `target` scalar to desync | not a second instance |

Trivial nit also sent, since the planner is in the file: **plan L604** says "the **four** sites (i)–(iv)"
where there are five (§2 #5 header L185 says "5", and (v) is at L271) — stale count from before (v) existed.

**Review consequence:** checklist item for C6c hardens from "`prcRef` captured, not re-derived" to
"`prcRef` is a **per-role map** captured at fsv time and threaded through the signature; the dead
`_ = s` / `_ = roles` lines at `:399-400` must not become the derivation source." If the planner declines
the fold-in and leaves (ii) as written, that is the plan owner's call and I review C6c against the plan
as it stands at landing time — but I will record the divergence rather than pass it silently.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## Finding 19 (should-fix, systemic — plan gap + code) — PR-2 has shipped 28 plans-branch tokens; §6 greps one of the three families

**Handoff sent** (`plan__ta-anchor-pr2-4a-token-gap.md`). Found by cross-checking the planner's `.HOLD`
reviewer checklist against §4a and then measuring instead of assuming. This is the §4a re-sweep item from
my todo list, pulled forward — because measuring it early showed it is (a) already violated, (b) partly in
commit messages with a closing window, and (c) growing with every remaining commit.

**Measured at `d9f3b97e`, provenance split per file against PR-1 tip `075a208e`:**

| Family | In-tree | PR-2-introduced | Inherited |
|---|---|---|---|
| `\bN[0-9]\b` (N2/N3/N7/N8, dataflow-map §9) | 17 | **16** | 1 (`greedy_score_optimizer_test.go`) |
| `\bBug #[0-9]` (plan §2 numbering) | 8 | **8** | 0 |

Plus **4 commit messages** — `680bebdb` (N2), `50034d15` (Bug #2), `07b8fdb7` (Bug #1), `3c9d45bb`
(Bug #3). **Total 28**, across all four artifact classes §4a names explicitly:

| Class | Count | Worst of it |
|---|---|---|
| shipped non-test code | 13 | `analyzer_helpers.go` ×8, `rescale.go` ×4, `optimizer_interfaces.go:54` |
| tests (comments + `It()` names) | 9 | `analyzer_helpers_test.go` ×6 |
| **dev-guide (Type 4, ships in the diff)** | 2 | `multi-analyzer-pipeline.md:338` "(N7)", `:472` "(N8)" |
| commit messages | 4 | the four above |

The dev-guide pair is the most consequential: Type 4 must stand alone for a reviewer reading only the
diff, and "(N7)" resolves to nothing for ev-shindin.

**Why this is a plan gap first.** §6 is thorough on semantic pivots but carries exactly one §4a-flavoured
grep — C8's `\((a|b)\)` — which the coder ran and closed (`1140a4c2`). No `Nn` grep, no `Bug #n` grep, no
commit-message check. Per CODER-CONVENTIONS §2 the coder had no scope to infer and correctly did not
invent one. Sharper still: §6's **C6d** bullet (L1145-1155) tells the coder to keep the `N7` abstain prose
at `analyzer_helpers.go:671`/`:682`/`:694` accurate — pointing straight at three of the tokens without
saying to strip them. Following §6 as written perpetuates them.

**Timing.** `gh pr list --head ta-anchor-dynamic-refresh` returns nothing ⇒ no GitHub PR ⇒ the §4
commit-message reword window is open. If it is to happen, before C6c makes it a 9-commit rebase rather
than 13. The reword/accept call is the planner's and Dean's, not mine; I flagged the window, not an outcome.

**Correction to my own prior notes:** the `\((a|b)\)` grep-to-zero criterion is **not achievable as
specified**. All 17 surviving hits are false positives — `math.Abs(a)`, `string(b)`, `c.getTarget(a)`,
`cmp.Compare(b.Priority, a.Priority)`, and four ordinary English "(a)… (b)…" enumerations in unrelated
files. C8 did its real job; the criterion needs rewording so a genuine hit isn't lost in the noise.

**Also settles a divergence I was about to raise and did not need to:** the planner's `.HOLD` checklist
lists `#1513` as a forbidden token, whereas I had recorded real GitHub numbers as legitimate. Moot —
`grep -rn 1513 internal/ docs/` returns **zero**, and the plan itself cites `#1228` at L1173. Only
plans-branch identifiers are in scope.

**Stale-checklist note for when the `.HOLD` is armed:** that checklist predates the current plan — item 6
says "**3** lock-step sites" where the plan now says **5** (L185, with (iv)/(v) added later), and it has
**no C10 item at all**. Treat the plan as authoritative over it.

**Verified:** every count above, by grep at `d9f3b97e` plus `git show 075a208e:<path>` per file; that §6
contains no `Nn`/`Bug #n` grep; that all 17 `\((a|b)\)` hits are false positives (read each); that no
GitHub PR exists. **Not verified:** that each token has a faithful prose replacement — per-site authoring,
the coder's work.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## Finding 20 (should-fix, pre-emptive — plan-side) — §4's fall-through fixture cannot go red at `Optimize()` level; site (ii) is observable only by calling the picker directly

**Status:** open, handoff sent. **Scope:** plan §4 C6c fixture wording (L960-980) and the §2d.5
motivation table (L676-700). No code implication for PR-1 or for commits already landed.

### What the plan specifies

§4's C6c bullet designates a *fall-through cap* fixture as the guard for lock-step site (ii)
(`fairShareCap`'s `prcRef` rescale):

> a **fall-through cap** fixture for site (ii): one role, two variants with different PRCs **and**
> different costs, the cheaper-efficiency one made infeasible via `MaxReplicas` headroom, asserting the
> cap the **pricier** variant receives — red without the `prcRef` rescale (5 instead of 25 on §2d.5's
> numbers)

and §2d.5's table motivates the rescale as an allocation-outcome defect:

> | today | **25** = `ceil(50000/2000)` |
> | (i)+(ii) without the rescale | **5** = `ceil(5)` |
> | (i)+(ii) with the `prcRef` rescale | **25** = `ceil(5 × 10000/2000)` ✓ |
>
> A silent 5× under-allocation, on exactly the path the cost-aware optimizer exists to serve

Every other fixture in the §4 C6c list is an `Optimize()`-level scenario, and this one is described
in `Optimize()` vocabulary (`MaxReplicas` headroom, per-role variants, costs). The natural reading is
an end-to-end fixture asserting `TargetReplicas`.

### What I measured

Built the plan's own scenario at PR-2 base `d9f3b97e` in a `/tmp` extract, with a one-line knob on
`greedy_score_optimizer.go:423` forcing the cap denominator to the reference PRC (10000) instead of
`vc.PerReplicaCapacity` — which reproduces the "(i)+(ii) without the rescale" cap value of **5**
exactly, against the real value of **25**. Three probes, `PerReplicaCapacity` 10000 (`v1`, cheapest
efficiency, pinned infeasible via `MaxReplicas: 1`) vs 2000 (`v2`), demand 50000:

| Probe | real cap | simulated missing rescale | discriminates? |
|---|---|---|---|
| single-role, `Optimize()` | `map[v1:1 v2:26]` | `map[v1:1 v2:26]` | **no** |
| P/D, `Optimize()` (joint Δ_util trim in play) | `map[d1:6 p1:1 p2:26]` | `map[d1:6 p1:1 p2:26]` | **no** |
| direct `fairShareRolePick` call | `variant=v2 capN=25` | `variant=v2 capN=5` | **yes** |

And at the extreme: forcing `fairShareCap` to **1** still yields `v2 → 26`. The only difference is
**25 loop iterations instead of 1**.

### Why the end-to-end fixture is blind

`allocateForModelPaired` (`analyzer_helpers.go:717-800`) loops `for anyRoleNeedsScaleUp(pickerState,
roles)` and re-invokes `pick` every iteration. So the two bounds do different jobs:

- **`ps` (site (iv)'s clamp) bounds the allocation total** — the loop runs until per-role demand is
  exhausted.
- **`fairShareCap` (site (ii)) bounds only per-iteration progress** — understate it and the loop takes
  more turns to reach the same total.

There is no iteration bound on that loop, so an understated cap costs iterations, not replicas. The
plan's `5` and `25` are therefore **cap values, not allocation outcomes** — which is why they match my
unit probe to the digit and are invisible in both `Optimize()` probes.

### Consequences

1. **The fixture's level must be specified, and only one level works.** As worded, a coder who writes
   this as an `Optimize()` scenario produces a test that is green with *and* without the rescale — a
   fixture that reads as a guard and is not one. The guard has to be a direct call to the closure
   returned by `fairShareRolePick`, asserting the returned `capN`. That is observable (25 vs 5) and it
   is the only level at which the plan's own numbers are reachable. Worth noting the plan's phrase
   "asserting the cap the pricier variant receives" is already *compatible* with the unit level — the
   fix is to say so explicitly rather than leave it to inference, because everything around it is
   end-to-end.
2. **§2d.5's "silent 5× under-allocation" does not reproduce end-to-end.** In both scenarios I ran, the
   final decision is identical with and without the rescale. As an outcome claim the sentence is not
   supported; as a claim about the per-iteration cap it is exact. Whether that reframing weakens the
   case for site (ii) is **the planner's call, not mine** — a 5× understated cap is still a real defect
   in the picker's contract, it is still worth fixing, and "the loop happens to compensate today" is a
   thin invariant to rely on. I am flagging that the *stated* motivation and the *measurable* effect are
   not the same thing, so the plan doesn't rest a fixture on an effect that isn't there.

### Caveats — what I did not verify

- This is a **simulation at the pre-C6c base**, not a run of C6c. It reproduces the cap *value*
  faithfully, and shows the loop compensates **in the current architecture**.
- Post-C6c, site (iv)'s clamp moves to replica space along with `target`. Whether the loop still
  compensates once `ps` and `target` are both converted is **not** established by this probe — the `k`
  computation in `allocateForModelPaired` reads `demand/prc`, and I have not traced the converted
  currency through it. **I re-check this against the coder's actual C6c code**, and if the conversion
  breaks the compensation then §2d.5's outcome claim becomes true post-C6c and this finding's
  consequence 2 falls away (consequence 1 stands either way — an end-to-end fixture that is green both
  ways today needs re-proving, not assuming).
- I did not test a GPU-scarce pool. Within a single `allocateForModel` call the pool drains identically
  regardless of iteration count, so I do not expect a difference, but I did not measure it.

**Verified:** all six probe results above, run twice; the `Optimize()` outputs are byte-identical
across the knob; the extreme cap=1 case; that the scratch tree is a `/tmp` extract and no worktree file
was modified. **Not verified:** the post-C6c currency question above; GPU-scarce behaviour.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## Findings 18 and 19 — **CLOSED** (`5b1e1606`), arithmetic independently re-verified

Plan commit `5b1e1606` (+149/−37) folds both. Checked against the diff and against code, not against
the commit message.

### Finding 18 — closed, and the planner went further than the handoff asked

| Item | Status |
|---|---|
| §2 #5 (ii)'s "`prcRef` needs **no new closure parameter**" reversed | ✓ now "must be a new threaded parameter, and must **NOT** be derived inside the closure", carrying "(corrected 2026-08-07 — this sentence previously said the opposite)" so the reversal is auditable |
| Per-role, not scalar | ✓ `prcRef map[string]float64` (role → reference PRC); signature `fairShareRolePick(target, prcRef, s, roles)`; ratio `prcRef[role] / vc.PerReplicaCapacity`; explicit "**Do not source `prcRef` from `roleVCs`**" |
| Value-capture framing in §2d.5 | ✓ as a set-off blockquote, "**Capture the value, do not re-derive the rule**" |
| §2 #5 header "four sites (i)–(iv)" → five | ✓ |
| Refresh-currency fixture in §4 | ✓ with the `len(s) <= 1` early-return rationale spelled out, and an instruction to assert the PRC *movement* so the fixture cannot silently degrade into a no-op |
| §6 close-out item | ✓ |

Two additions I did not ask for and that improve the fold-in:

- **A second, independent failure mode.** Beyond `prcRef`'s *value* drifting between fsv time and cap
  time, the refresh can reorder `sortByCostEfficiencyAsc`, so `sorted[0]` may be a **different variant**
  on iteration 2 than on iteration 1. "Capturing the value fixes both; re-deriving the rule fixes
  neither" — correct, and it is the sharper argument of the two.
- **A blast-radius bound I had not established.** Verified independently by the planner: `refreshAnchorSizing`
  has exactly one non-test call site (`analyzer_helpers.go:737`); `scaleDownRoleIterated` never refreshes,
  so site (iii) is unaffected; `greedy_score_optimizer.go:423` is the package's only `ceil(target / PRC)`;
  and the vote helpers (`:445`, `:472`, `:502`) divide by each analyzer's own `prcForVariant`, a different
  quantity, correctly per-analyzer. This converts "fold-in is bounded to (ii)" from assertion to
  measurement.

**Caveat carried into C6c review:** the new refresh-currency fixture inherits **Finding 20**'s level
question — it also discriminates only through the cap, so if written at `Optimize()` level it may be
green both ways. Flagged in Finding 20's handoff as a hypothesis; I measure it at C6c.

### Finding 19 — closed; every number re-verified, one nit

§6 now carries a cross-cutting token-sweep bullet with the criterion stated as **zero *PR-2-introduced*
hits, not zero hits** — which is the correction that mattered, since 8 of the inherited hits are the
#1513 goldens' own `Commit 2/3/4` scenario labels that PR-2 must not churn.

I re-ran the plan's exact regex at both revisions. Text-file totals: **48** at `d9f3b97e`, **17** at
`075a208e`, delta **31**. The per-file PR-2 list sums to 31 (`analyzer_helpers.go` 8 ·
`analyzer_helpers_test.go` 7 · `rescale.go` 4 · `optimizer_liveness_test.go` 3 ·
`optimizer_dynamic_refresh_test.go` 3 · `optimizer_combine_characterization_test.go` 2 ·
`multi-analyzer-pipeline.md` 2 · `optimizer_interfaces.go` 1 · `rescale_test.go` 1); the inherited
six-file list sums to 17; the class split 13 code + 16 test + 2 dev-guide = 31. **Every figure in that
bullet is exact.**

**Nit (not worth a handoff on its own):** the regex as written, run over `internal/ docs/developer-guide/`,
also matches **8 binary PNGs** under the dev-guide (`panel-*.png`, `wva.rules*.png`,
`debugging-with-remote-clusters.png`). A coder running it literally gets `Binary file … matches` noise on
top of the 48. Adding `-I` suppresses it. The bullet's explicit per-file target list means nobody is
actually going to miscount, so this is cosmetic — I'll fold it into a later handoff if I have other
business with the planner rather than spend a round trip on it.

**Correction to my own Finding 19 count.** I reported 4 commit messages carrying tokens; that was
measured at an earlier tip, before C6a/C6b and two others landed. Re-measured at `d9f3b97e`: **all 9**
commit messages carry at least one token in the message body, and **6 of the 9 carry one in the subject
line** — the surface `git log --oneline` and GitHub's commit list render. So the plan's "reword ×9" is
literally right, not an over-estimate, and the reader-visible count is 6. This makes the effort argument
slightly *stronger* than I had it, and Dean's cost/benefit should use these numbers, not mine:

| | tokens in subject | tokens anywhere in message |
|---|---|---|
| commits | 6 of 9 | 9 of 9 |

The plan correctly routes the reword itself to Dean as a decision, records "not worth it" as a
legitimate answer to be accepted explicitly rather than by omission, and names both deadlines (the
force-push window closing when the PR opens; the 9-vs-13 effort point before C6c).

**Verified:** the fold-in diff for both findings; the 48/17/31 arithmetic and all three sub-tallies, by
re-running the regex at both revisions; the 9-of-9 and 6-of-9 commit-message counts; that
`refreshAnchorSizing` has one non-test call site. **Not verified:** that the refresh-currency fixture can
go red as specified — that is Finding 20's open question, resolved at C6c.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## Finding 20 — **CLOSED** (`70c985b9`), with a caveat the planner caught that I had missed

Plan commit `70c985b9` (+70/−21) folds it. Both requested edits landed, plus a mechanism trace and a
new §6 criterion.

| Requested | Status |
|---|---|
| State the fall-through fixture's level | ✓ "**This one is a unit test, not an `Optimize()` scenario**" — call the returned closure directly, assert `capN`, with the measured numbers and the reason inline |
| Same for the refresh-currency fixture | ✓ "**Write this one at unit level too**", with its level explicitly recorded as unproven in *both* directions |
| Correct §2d.5's outcome claim | ✓ "**the three rows are cap values, not allocation outcomes**", carrying "this paragraph previously closed 'a silent 5× under-allocation'" so the correction is auditable |
| §1.1 commit-map row | ✓ both cap fixtures now marked "**both unit-level** … an `Optimize()` fixture is green both ways, measured" |
| New §6 check | ✓ `grep -n "fairShareRolePick(" internal/engines/pipeline/*_test.go` — both cap fixtures must appear, i.e. call the closure directly. "A test that cannot go red is worse than no test — it reads as coverage." |

### The planner supplied the mechanism I had only measured

I established the *equivalence* empirically; the plan now explains *why*, and I verified every claim
line-exact at `d9f3b97e`:

| Claim | Site | Verified |
|---|---|---|
| Cap enters only via `n = min(bottleneckReplicas, capN)` | `analyzer_helpers.go:760` | ✓ |
| `k = max(floor(deltaUtil·demand/prc), min(1, n))` — a `min(1, n)` **forward-progress floor** | `:788` | ✓ |
| Demand drain is `pickerState[i][role] -= k·prcI` — driven by `k`, not the cap | `:816` | ✓ |
| Pool drain is `available[…] -= k · gpusPerReplica` — likewise `k` | `:819` | ✓ |

So the cap cannot gate termination: `pick` only ever returns `capN > 0`
(`greedy_score_optimizer.go:439`), which makes `n ≥ 1`, which makes `min(1, n) = 1`, which floors `k` at
1 — guaranteed forward progress regardless of how badly the cap is understated. That is a better
account than "the loop re-picks", and it is the load-bearing invariant the compensation rests on.

### The caveat I missed, and the planner caught

**Both of my probes ran with the refresh inert.** `withSatEntry` builds a *single* ballot entry, so
`len(s) == 1` and `refreshAnchorSizing` hit its early-return (`analyzer_helpers.go:552-554`) — it
executed **zero** times in the single-role *and* P/D runs. I listed the post-C6c currency question and
GPU scarcity as caveats but not this one, and it is the more consequential omission: with ≥2 voting
analyzers the refresh runs **once per iteration** (`:737`), so an understated cap turning 1 iteration
into 25 means 25 opportunities for `sorted[0]`'s identity to move under it. My equivalence result
simply does not transfer to the multi-analyzer case, in either direction.

Consequence for my own C6c review: I cannot treat "the loop compensates" as established for the
refresh-currency fixture. Its level is genuinely open and I measure it rather than infer it.

### Site (ii) stays in scope — correctly, and not on my finding's strength

The plan keeps it for three reasons that don't depend on the outcome claim: the cap is a stated
contract and 5-where-25-is-right is wrong on its face; the compensation is architectural happenstance
resting on an undocumented `min(1, n)` floor; and the measured equivalence was obtained with the
refresh inert. That is the right disposition. My finding narrowed the *fixture level* and corrected a
*motivation*; it never argued against the fix, and the plan does not read it as having done so.

**Verified:** the fold-in diff; all four mechanism claims by line at `d9f3b97e`; the `len(s) <= 1`
early-return and that both my probes were single-entry; the new §6 grep as written. **Not verified:**
whether the refresh-currency fixture can go red at either level — open, measured at C6c; and the
post-C6c site-(iv) currency question, likewise open.

---

## Finding 21 (should-fix, plan-side) — the coder's C6c design handoff was written against a plan ~6h stale; two of its six questions rest on superseded text, and one proposed extraction would undo Finding 18/19

The coder wrote `plan__ta-anchor-c6c-fairshare-currency.md` (outbox, 08-07 10:54) holding C6c for six
design decisions. Three are genuinely open and well-argued. Two are already settled in the plan, in the
coder's own preferred direction. One rests on a premise the plan explicitly forbids. The cause is
mechanical, not judgment: the handoff quotes plan text that changed at `ffb945c1` (08-07 **05:01**),
five hours fifty-three minutes before the handoff was written, and **seven** planner triggers sit
unconsumed as `.md` in `session/handoffs/` — including `c6c-prcref-and-token-sweep`,
`c6c-fixture-level` and `c6c-source-citations-reverified`, each of which points at exactly the text a
question re-asks.

Staleness is provable from the handoff's own words: it says "the plan's **four-site** list" (the plan
has said **Five** since `ffb945c1`, L239), "The plan does not mention the fallback at all" (site (v),
L305-321), quotes (iii)'s note as "coordinate all **three** edits" (current text: "coordinate **both**
edits", L295-297), and says of `quota-limiter.md` "§5 never lists this file" (the C6c row has listed it,
with the two-copies count, since `ffb945c1`, L186). Four independent quotations, all pre-`ffb945c1`.

### Triage

| Q | Coder's framing | Verdict |
|---|---|---|
| Q1 signature | fork, leans (a) | **settled** L249-253 = its (a), with a reason it did not have. Its *scope* half is new but **misreads site (ii)** — see below |
| Q2 fallback | "**a plan gap**, not a preference" | **not a gap** — site (v) L305-321 specifies its (a) and forbids its (b). One-sentence (b)-cross-ref is the only residual |
| Q3 site (iv) shape | fork, offers a third shape | **genuinely open** — plan L301 offers two shapes, chooses neither. Its third shape looks better; I have mechanism input |
| Q4 priority in the cap | flag, leans (a)+(c) | **confirmed gap**, credit the coder. "priority-scaled" appears nowhere in the plan |
| Q5 move (iii) to C6d | leans defer | **premise wrong** — the plan forbids the coupling it assumes. (iii) can land in C6c |
| Q6 T1.4 shape | leans split | **agree**, and it independently re-derived `70c985b9`'s unit-level conclusion |

### Q1's scope half is the one that would do damage

The coder proposes extracting `cheapestSizedVariantForRole` so that fsv, `fairShareRolePick` and
`roleDemandGPUs` "converge", with the stated risk: *"If they disagree, fsv is denominated in a variant
the allocator never picks, which is the same class of bug C6c exists to fix."*

They are **allowed to disagree, and site (ii) is the compensation.** Plan L259-263 exists precisely
because the picker legitimately falls through past `v_role` on two conditions the selector does not
model — `gpusAvail < gpusPR` (`greedy_score_optimizer.go:420`) and `headroom <= 0` (`:427`) — and the
`prcRef` ratio rescales the cap for whichever candidate the loop lands on. Forcing agreement is not
possible (the picker *must* fall through) and folding "make all three agree" invites the reading that
the ratio is redundant — which is Finding 18/19's correction undone.

The count is also off, in both directions. There are **four** such loops at `d9f3b97e`, not three —
`fairShareRolePick` (`greedy_score_optimizer.go:410`), `costGreedyRolePick`
(`cost_aware_optimizer.go:85`, loop `:94`), `fillRole` (`rescale.go:431`, loop `:439`) and
`roleDemandGPUs` (`rescale.go:569`, loop `:572`) — and **none of them is a cheapest-sized-variant
selector**. All four iterate the sorted slice and take the first *feasible* candidate; `roleDemandGPUs`
additionally scopes to one accelerator via `variantsOnType`, so its "cheapest" is a different variant
by construction. A helper as specified would therefore have exactly **one** consumer in C6c's design —
fsv's `v_role`, which is the same choice as `prcRef`'s reference by definition — and could not be
pushed into any picker loop without changing its semantics.

So: the extraction is not wrong to want, but it unifies one use with itself, and its stated
justification is a misreading of the mechanism the plan already installs.

### Q5's premise is the thing the plan forbids

Q5 defers (iii) because *"C6d changes the abstain/veto shape of `votesFromRoleSpare`, which changes
which entry binds, which is the very thing this tie-break reads."* Both halves fail:

- §2d.4 (c) states the fix as a per-variant re-check **in `safeRemovalReplicasForRole`** and says in
  terms: *"Do **not** express this as a synthetic 0-vote inside `votesFromRoleSpare`."* C6d gates that
  function's *return*; the ballot is untouched, so the binder `sortVariantsForScaleDown` would read is
  untouched. (`safeRemovalReplicasForRole` calls `combineVotes(votesFromRoleSpare(s, role, v), false)`
  at `analyzer_helpers.go:633`; `sortVariantsForScaleDown` is a separate consumer of the same ballot.)
- N7 abstain is **C7**, landed at `952d2fff`. The abstain shape (iii) reads is already final. The plan
  says this explicitly: "(Distinct from C7's N7 *abstain*.)"

The planner's revision of (iii)'s note — from "coordinate all three" to "C6d … does not touch this
tie-break" — is **correct**, and Q5 is answered by reading it. Worth keeping from Q5: its two
mechanical notes are right and are *not* in the plan. `sortVariantsForScaleDown(s, roleVCs)` takes no
`role` (`cost_aware_optimizer.go:165`) and both callers have one in scope (`:446`, `rescale.go:414`) —
verified exactly as claimed; and mapping a no-ballot variant's binder `-1` to tie-break key 0 keeps
today's `weighted` behaviour for the same input.

### Q3 — open, and my Finding 20 work bears on it

The coder's third shape converts the *bound* into each analyzer's units and leaves `ps` in raw
capacity, rather than moving `ps` into replica space. One consequence is directly in my scope: my C6c
checklist carries "measure whether converting site (iv) to replica space preserves the loop
compensation, since `k = floor(deltaUtil·demand/prc)` (`analyzer_helpers.go:788`) reads demand against
PRC." Under the coder's shape `ps` stays commensurable with `prc`, so **that question dissolves**; it
arises only under the plan's first phrasing. That is independent evidence for the coder's shape, and it
is mine to contribute rather than theirs to know.

Its sub-question (an analyzer with no PRC for `v_role` is left unclamped) is sound for the reason given
— it cannot participate in `votesFromPickerState` for `v_role` either, so it cannot drive allocation of
`v_role`. Worth a plan sentence, as they ask.

### Q4 — confirmed, and one extension

`priority-scaled` appears nowhere in the plan; L255 calls `target` "the fsv-unit `target`" without
saying that unit carries the `priority` factor. The coder is right that the honest comment must say
priority-scaled replicas, and right that C6c does not change the arithmetic. Extension: site (v)'s fix
**deliberately drops** `priority` from the fallback (L310), so post-C6c the primary is priority-scaled
and the fallback is not. That is necessary — including it would make the fallback ≤ 0 whenever it
fires — but it means site (v)'s "fixes the currency" should be read as *fixes the demand→replica
conversion*, not *makes the two paths equal*. The residual cross-model incomparability
(`computeMean` / `sortByRemainingDesc` mixing a priority-scaled fsv with an unscaled fallback) is
**pre-existing and narrowed, not introduced** — today the fallback returns raw max demand against a
`priority × Score × Σ` primary — and is unreachable in production for the reason the plan already
gives at L316-318 (`ApplyDefaults` rewrites `Priority == 0` to `1.0`,
`config/saturation_scaling.go:275-276`). Doc-level; (a)+(c) is right.

### Q2's residual

The fix is fully specified, so the code lands right whether or not the text changes. But the coder's
actual ask is legitimate and cheap: (b)'s claim that it "falls out of the participation filter" holds
only because the *fixed* fallback also carries that filter. One cross-reference in (b)'s text closes
it. Their stated motivation for keeping the fallback — "the only thing standing between `priority: 0`
and a model that never scales" — is undercut by `ApplyDefaults`; the plan's own reachability paragraph
is the better reason for the same conclusion.

### Not my call, and I am not making it

Whether to answer Q1's extraction, Q3's shape and Q4's comment is the planner's, and whether C10 jumps
the §1.1 git order is Dean's. I am recording verdicts on *premises*, which is checkable, and leaving
the forks alone.

**Verified:** all four stale quotations against `ffb945c1`'s diff and the current plan text; the seven
unconsumed triggers; §2d.4 (c)'s synthetic-0-vote prohibition; N7's landing in C7 (`952d2fff`); the
four candidate loops and their enclosing functions at `d9f3b97e`; `sortVariantsForScaleDown`'s
signature and both callers; `safeRemovalReplicasForRole:633`'s ballot call; the absence of
"priority-scaled" from the plan; site (v)'s and L1047's fixture coverage. **Not verified:** whether
the coder's Q3 shape survives contact with `applyDeallocationForRole` (not read at this depth) — that
is a C6c-review item, not a precondition for answering Q3.

---

## C6c design pivot to GPU space (plan `1a116e7a`) — what in this review is now historical

**No code changed. This is a spec pivot, and it lands on my review doc rather than on the branch** —
the coder had not written C6c when it happened, so there is nothing here to re-review, only material of
mine to retire before it misleads someone. Recorded on 2026-08-07 after reading plan §2d.5 as rewritten
from the now-**frozen** Type 1 (`combined-analyzer-optimizer-design.md`, `Status: FINAL`, authoritative —
which also actions the T1 finding I handed the planner).

**What changed.** fsv's currency pivots from **replica space** to **GPU space**, with one conversion
function applied once per ballot entry:

```
toGPUs(metric, PRC, GPUsPerReplica) = (metric / PRC) × GPUsPerReplica
```

Nine per-site unit rows now govern (Type 1 `W5` is the authority; plan §2d.5's table is derived detail).
The two that matter most to a reviewer: row 6 makes `fairShareCap` a whole-replica **`floor`** fill
(`floor(remaining_GPUs / GPUsPerReplica)`, then `min` with the real pool) — **not `ceil`** — and row 8
keeps site (iv)'s clamp in *that analyzer's own metric*, converting the GPU bound back down through its
own PRC and `GPUsPerReplica` with `ps` left raw. Rows 5 and 7 are dimensionless and **never spent**;
the plan's mechanical check is worth stealing verbatim for the diff read: *if a number has no unit, it
must not appear on the left of an assignment that reduces a budget.*

### Supersession map — precise, because three of my findings are NOT affected

| mine | status under `1a116e7a` | why |
|---|---|---|
| **Finding 15** | **MOOT** | the round trip it depended on no longer exists (one conversion in, one out) |
| **Finding 18** (+ its `5b1e1606` closure, *Sharpening*, *Scope*) | **CLOSED then MOOT** | correct against replica space; §2d.5 *What stops existing* retires by name every artifact it produced |
| my 4th verified claim, "no golden can move on (ii) at any fixture shape" | **VOID — and it under-warns** | `ceil → floor` does not cancel; see the inline marker at that table |
| C6c checklist items **2, 3, 8** | **retired** | item 3 (`prcRef` same-slice sourcing) is the deleted requirement; item 8's prediction is the void claim; item 2's site list survives but **site (iii) moved to C6d** |
| **Finding 19** (§4a plans-branch tokens) | **unaffected** | orthogonal to currency; the 31-token PR-2 delta and the 9/6 commit-message counts stand |
| **Finding 20** (cap bounds iterations, not replicas) | **unaffected — and PROMOTED** | plan §2d.5 now carries it as a standing fact: cap enters only at `n = min(bottleneckReplicas, capN)` (`:760`), `k`'s `min(1, n)` floor (`:788`) and drain driven by `k` (`:816`/`:819`), so an understated cap costs iterations not replicas — *which is why a cap of `0` is a different animal and §2f requires skip, not zero-cap*. My caveat still holds: both probes ran with `refreshAnchorSizing` inert |
| **Finding 21** (staleness) | **unaffected, and now doubly evidenced** | the pivot is a second, larger instance: my own header sat at `e0aa9bad` while the plan reached `1a116e7a` |

**My Finding 21 triage was adopted essentially verbatim.** The plan's DECIDED box declining the
cross-site `cheapestSizedVariantForRole` extraction rests on all four points I verified: the loops take
the first **feasible** candidate (not the cheapest), they **must** fall through past the reference variant
when the accelerator pool is dry (`greedy_score_optimizer.go:420`) or the cheap variant is at
`MaxReplicas` (`:427`), there are **four** such loops not three, and `rescale.go` stays out of C6c. Two
helper extractions *are* sanctioned — the row-0 `toGPUs` conversion and the row-6 whole-replica `floor`
fill — because C11 makes three grant sites share one ceiling. Signature decided as option (a):
`fairShareValue(priority, s, ps, roles, variants)`. The reference picker is
`referenceVariantForRole(vcs, role) (domain.VariantCapacity, bool)` — named for *denominating the claim*,
not for picking what gets allocated; fsv's reference and the picker's landing variant are **allowed and
expected to disagree**.

### C6c review checklist — rebuilt against GPU space

Replaces items 2/3/8 above; items 1, 4, 5, 6, 7, 9, 10 carry over unchanged (`Score` gone from all six
names; fallback **kept** not deleted, else a §4b DEPRECATED classification is owed; the `:53-60` doc
comment rewritten; T1.4 asserting replica number **and** binder index; the multi-variant-within-one-role
fall-through fixture; six fsv-formula copies — four docs incl. both `quota-limiter.md` sites, two code,
one of them the exported **type** comment at `:15-18`; and §5's `~L` numbers are as-of `f6485980`, so
grep the heading text).

1. **`toGPUs` is the only conversion in, row 8 the only one out.** Any third conversion, or a
   compensating factor anywhere in rows 1–6, is a defect — the pivot's whole claim is that rows 1–6 are
   uniformly GPUs.
2. **Row 1 is `max_i` across analyzers, row 2 `Σ_role` across roles.** A `Σ_i` across analyzers is the
   bug the pivot exists to fix; `Σ_role` is legal **only** at row 2 (invariant 10).
3. **Row 0's `W4` rule: no PRC ⇒ contributes nothing.** Not "contributes its raw metric," not zero-then-spent.
4. **Site (ii) is `floor`, and the `ceil → floor` change is called out in the commit message.** The plan
   states this is *not* status-quo-preserving at the boundary; a commit that ships it silently is a
   finding regardless of whether tests pass.
5. **Goldens per commit, and treat a move as a bug until proven otherwise.** The plan's escalation path
   is mandatory: prove the delta is exactly one replica on a mid-replica share, then `plan__` handoff to
   Dean *before* adjusting any golden. I re-run them myself on a scratch extract rather than accept a
   report — and unlike the old item 8, green goldens are now genuinely informative here.
6. **Site (iii) is out of C6c** — it moved to C6d (the coder's Q5 leaning, accepted). If the C6c diff
   touches the scale-down tie-break, that is a scope finding.
7. **The two fixture cancellation traps.** The `[sat]`-only ordering fixture **must vary
   `GPUsPerReplica` across the two models** — equal values cancel the new factor and the fixture cannot
   detect the pivot at all. Same trap multi-role: prefill and decode sharing either PRC *or*
   `GPUsPerReplica` cannot distinguish correct from role-mixing.
8. **New: the mid-replica `floor` boundary fixture must call the closure directly.** Finding 20's
   measurement is why — at `Optimize()` level the cap only costs iterations, so an end-to-end fixture
   cannot go red on a one-replica cap delta.
9. **Invariant 7 needs a *direct* test, not an inference from goldens** — assert `anchor ==
   saturationEntry` field-for-field before/during/after allocation, and assert the per-iteration sizing
   refresh is **not** invoked. Observe the `withSatEntry`-stability rule (carried from the #1513 review,
   Finding 2).
10. **Do not accept "the sat-only goldens cover the combine."** Plan invariant 8 makes a one-analyzer
    ballot an algebraic pass-through (`b = 0`, `excess = 0`), so those goldens cannot cover combine
    arithmetic — the plan calls asserting otherwise a **category error**, and I should too.
11. **Site (iv)'s `[sat]`-only inertness is SINGLE-ROLE ONLY.** The plan flags this explicitly; do not
    let a `[sat]`-only P/D fixture be read as evidence (iv) is inert.

### Three new commit rows arrived with the pivot — not yet reviewed, and two change behavior

Also new since my last pass, so my "13-item / 15-row" framing is itself stale: §1.1 is now **C1–C11**.

- **C6e (`W1`)** — one fair-share entitlement per **model**, `Σ_role spend ≤ target`. **TA-AMPLIFIED, not
  TA-created:** `[sat]`-only P/D already makes two independent full-budget draws (one per role); TA makes
  it `|analyzers| × |roles|` = 4. **This changes `[sat]`-only P/D behavior whenever the budget binds** —
  needs a `[sat]`-only P/D fixture *and* a `[sat,TA]` one, and a §4b classification if anything is removed.
- **C6f (`W4`)** — no conversion factor ⇒ no spend. TA-CREATED (a single analyzer is always its own
  conversion factor), so `[sat]`-only goldens cannot cover it either way.
- **C11 (`FZ-admission`)** — a never-measured variant is invisible when `PRC <= 0`. TA-CREATED; this is
  the row that makes three grant sites share one ceiling, hence the two sanctioned helper extractions.
  Worth checking against my **Finding 16** (anchor PRC 0 excludes a variant from scale-down entirely) —
  same `PRC <= 0` predicate, different path; C11 may or may not subsume it, and I should not assume.

**Verified for this section:** plan §2d.5 as rewritten (L924:1050) — the `toGPUs` formula, all nine unit
rows, the three closure properties, the five *What stops existing* bullets, the *What survives* paragraph,
the per-site `[sat]`-only table, the two deliberate behavior changes, the fixture-cancellation
requirement, and the retracted goldens claim; §1.1's C6c/C6e/C6f/C11 rows (L268-271); the §5 dev-guide map
rows for C6c/C6e/C6f/C11 (L1911-1919); the DECIDED boxes at L400-438; and the Type 1 header now reading
`Status: FINAL (frozen 2026-08-07) · AUTHORITATIVE`. **Not verified:** §7.1's `W1`–`W5` answers at
L2224:2283 (read only as far as the §2d.5 cross-references required) and the Type 1's own `W5` unit table —
I am trusting plan §2d.5's reproduction of it, which the plan itself flags as derived detail. Both are
C6c-review reads, not preconditions for retiring stale material.

---

## C11 pre-measurement — another session's ranking correction, independently confirmed (with two refinements)

**No handoff from me.** `session/handoffs/plan__ta-anchor-c11-ranking-claim-correction.md` (from the
Type-1 owner session, `.WIP` with a planner as I write) already requests the plan-doc edits, and C11 is
four commits out. This is my *review-side* record — what I will check in the C11 diff — plus my
verification of its central claim, which I did not take on trust. Everything below is read at the
**committed** baseline `d9f3b97e` via `git show`, not the working tree (the coder is mid-edit on C6c).

**Its central claim is correct, and it inverts something on my own checklist.** I had C11 down as
"the sentinel ranks behind measured options" from the Type 1. It does the opposite:

- `variantCost` / `variantAccel` are built **only** from `inputMetrics`
  (`saturation_v2/analyzer.go:352-360`), and `cost := variantCost[vs.VariantName]` /
  `accelerator := variantAccel[...]` are plain map lookups — a zero-replica variant misses both, so
  **`Cost = 0` and `AcceleratorName = ""`**, emitted as such at `:441-446`.
- The `if accelerator == "" { accelerator = replicas[0].AcceleratorName }` fix-up cannot rescue it: it
  is inside a block that indexes `replicas[0]`, which requires replicas to exist.
- `bindingAnchor` copies `Cost` from the (a) carrier verbatim (`analyzer_helpers.go:202`), so the
  anchor inherits the zero.
- `costEfficiency` = `Cost / PRC` with a `PRC <= 0 → MaxFloat64` guard
  (`cost_aware_optimizer.go:237-242`). With the C11 sentinel `PRC = 1`: `0 / 1 = 0`, the **minimum**
  attainable value for any non-negative cost, and `sortByCostEfficiencyAsc` sorts **ascending**
  (`:228-235`) ⇒ the sentinel sorts **first**, unconditionally.
- Peers tie at `0` under unstable `sort.Slice` ⇒ **never assert which never-measured peer wins.**
- Path asymmetry confirmed: `costGreedyRolePick` takes `_ map[string]int` and ignores the budget
  (`cost_aware_optimizer.go:85-109`), whereas `fairShareRolePick` does
  `gpusAvail := available[vc.AcceleratorName]; if gpusAvail < gpusPR { continue }`
  (`greedy_score_optimizer.go:419-422`) — with `AcceleratorName == ""` that is `available[""] = 0 < 1`,
  so the sentinel is **skipped on the fair-share path regardless of PRC**. Eligibility and ranking are
  therefore only observable through the **cost** optimizer.

### Refinement 1 — "unbounded grant" would be wrong, and I nearly wrote it

`costGreedyRolePick` returns `math.MaxInt` when `MaxReplicas` is nil, which reads like an unbounded
grant to a never-measured variant. It is not: the returned count becomes `capByRole[role]` and is
immediately `min`'d — `n = min(roleBottleneckReplicas(...), capByRole[role])`
(`analyzer_helpers.go:758`). `MaxInt` defers the bound to `roleBottleneckReplicas`; it does not escape
one. I checked this before recording it, and the check killed the finding I was about to write.

### Refinement 2 — the real hazard is mis-*sizing*, not mis-ranking, and it is a factor of the true PRC

This is the sharper reason the cap is load-bearing, and neither the Type 1 nor the correction handoff
states it. `PRC = 1` is not a neutral placeholder — it is a *denominator*, and both bounds divide by it:

- `roleBottleneckReplicas` sizes the need as demand ÷ PRC, so a sentinel PRC of `1` inflates the
  computed replica need by the ratio of the variant's true PRC to 1 (with the PRC magnitudes in this
  codebase — thousands — that is a three-to-four-order-of-magnitude inflation, not a rounding error);
- `k = max(floor(deltaUtil × demand / prc), min(1, n))` (`:788`) divides by the same `prc`, and `k` is
  what drives allocation and pool drain (`:816`, `:819`) — my promoted Finding 20 material.

**The arithmetic does close, and cleanly:** if the one-replica ceiling clamps `n` to 1, then
`utilByRole = n × prc / demand = 1/demand`, so
`k = max(floor((1/demand) × demand / 1), min(1, 1)) = 1`. A ceiling applied at `n` propagates to `k`
correctly and the inflation is fully neutralised. **But that is precisely why the ceiling's placement is
the whole ballgame:** it must land where `capByRole`/`n` is formed, at *every* granting site. A C11 that
caps the fair-share path and misses the cost path would pass a fair-share fixture (where the sentinel is
already skipped on the empty `AcceleratorName`) while leaving the one path that can actually select the
sentinel sized by a PRC of 1.

### C11 checklist (replaces "check vs Finding 16" as the whole entry)

1. **Expect the sentinel to sort FIRST.** Do not raise a finding that it fails to rank last — the Type 1
   `:1530-1533` rationale is wrong and is being corrected in the Type 3. Verify against the corrected
   plan text, not against the Type 1.
2. **The one-replica ceiling is present at every granting site, and clamps `n`/`capByRole`** — not only
   the pick's return value on one path. This is the single assertion I care most about in C11.
3. **Specs must run through the cost optimizer**, or they assert nothing about eligibility/ranking.
4. **The fixture must produce `Cost = 0` the way production does** — no replica metrics for that variant.
   A rigged non-zero `Cost` encodes an invariant production does not have.
5. **No assertion about which never-measured peer wins** (tie at 0, unstable sort).
6. **Self-healing pinned by a spec**, ideally: after admission the variant has metrics and ranks normally.
   The design rests on this, and it is cheap to assert.
7. **`analyzer_helpers.go:213-216` must be updated** — *"Not proactively selectable; genuine cold-starts
   fall to the reactive scale-from-zero engine"* is the exact claim C11 reverses. Verified present at
   `d9f3b97e`. §4a applies: name *the saturation zero-replica cost bug* in prose, no plans-branch token.
8. **`N5` and the empty-`AcceleratorName` half must NOT be fixed in C11** (both out of PR-2; the latter
   would move `[sat]`-only goldens). If the diff fixes either, that is a scope finding.
9. **Finding 16 is NOT subsumed.** Same `PRC <= 0` population, different path: mine is *scale-down*
   exclusion, C11 is *scale-up* admission. C11's sentinel makes PRC positive for the never-measured
   case, so it may incidentally narrow Finding 16's population — but Finding 16 also covers variants
   that go PRC-0 for other reasons (binder abstention, N8), which C11 does not touch. Keep it open.

**Verified:** every line reference above at `d9f3b97e`. **Not verified:** the ceiling's actual insertion
points (C11 is unwritten), and whether `roleBottleneckReplicas`' internals bound the sentinel some other
way — I read its call site and its `min`, not its body, so item 2 stays an assertion to check rather than
a defect I am claiming.

---

## C6c dev-guide sub-checklist — resolving the plan's "(both copies)"

Plan §5 assigns C6c three dev-guide homes: `multi-analyzer-pipeline.md` `### Fair-share iteration` and
`### Scale-down path`, plus `quota-limiter.md` `### Fair-share interaction` **"(both copies)"**. That
parenthetical is ambiguous and I resolved it before it could become a finding in either direction.

**There is exactly one tracked `quota-limiter.md`** (`docs/developer-guide/quota-limiter.md`;
`git ls-files | grep quota-limiter` returns one path at `d9f3b97e`). So "both copies" is **not** two
files. It is the same fair-share-metric statement written twice *inside* that one file:

- `:284` — the `### Fair-share interaction` bullet: *"the average of the active models' remaining
  fair-share metric (priority × score × unmet demand — see the worked-example caveat below)"*
- `:327-328` — the worked example's own caveat: *"The exact per-round means come from the fair-share
  metric — priority × score × demand — so treat the numbers here as an illustration of the …"*

Both spell out the fsv terms, and **"unmet demand" / "demand" is exactly the quantity the pivot
re-denominates.** So the doc obligation is real, not cosmetic:

1. **Both statements updated, or neither.** Updating `:284` and leaving `:327` is the classic
   duplicate-prose miss, and `:284` explicitly forward-references `:327`, so a half-edit leaves the file
   self-contradicting.
2. **Do not expect a `ceil → floor` doc edit here.** `grep -rn 'fairShareCap\|math.Ceil\|Ceil(' docs/`
   returns **nothing** at `d9f3b97e` — the dev guide never stated the cap arithmetic, so C6c's
   one-replica behavior change has no existing prose to correct in `quota-limiter.md`. If the coder adds
   it, that is fine but not required; if the coder *doesn't*, that is **not** a finding. (`### Fair-share
   iteration` in `multi-analyzer-pipeline.md` is the plan's home for the arithmetic itself.)
3. **Whether the fsv terms need a named unit at all is a judgement call, not a defect.** Unit-table row 5
   makes `priority × claim` a dimensionless **rank** that is never spent, so "priority × score × unmet
   demand" may remain correct as written even after the pivot. I will accept either an unchanged
   statement *with* a rationale in the commit message, or a statement that names the unit — but not
   silence on a term the pivot touches.
4. **`### Scale-down path` is C6c *and* C6d.** Both rows in the §5 map name it. If C6c edits it, C6d must
   still be able to; watch for C6c pre-empting C6d's content, which would make C6d's diff look empty and
   break the per-commit attribution that motivated the C6c-first ordering.

**Working-set observation, not a review:** as I write, the coder's tree carries
`cost_aware_optimizer.go` alongside `greedy_score_optimizer.go` and both dev-guide files — consistent
with a multi-site bug-#5 commit and with the §5 map. I am recording it only so that a C6c diff *without*
a `cost_aware_optimizer.go` hunk prompts me to ask which site was dropped, rather than passing unnoticed.
Uncommitted work is not reviewed.

---

## C6c review (`34b18bc5`) — the `ceil`/`floor` fork, and three plan defects I independently confirm

**Commit:** `34b18bc5` "pipeline: convert the fair-share claim to GPUs before comparing models",
6 files, +564/−96. Tree at review time carried uncommitted `M analyzer_helpers.go` /
`M cost_aware_optimizer.go` (C6d in flight) — **not reviewed**.

**A correction to my own draft, since it changed the verdict.** I had this written up as a silent
deviation — the "gate rationalization" failure mode, a coder arguing at length in a commit message
for a choice the frozen design rules out by name. That framing was **wrong**, and I only found out
because I read `plan__ta-anchor-c6c-ceil-eviction-fork.md.WIP` before filing. The coder implemented
the mandated `floor` first, **measured** it, diagnosed a real termination defect, backed it out, and
raised it as an explicit design fork addressed to the planner — *"This is a design fork, not a bug fix
I folded in silently … it is your call, and I am naming it rather than shipping it either way without
you."* That is the process working. The finding below is a fork awaiting Dean, **not** a coder defect.

### Finding 22 (OPEN DESIGN FORK — Dean's call; not a coder defect) — `fairShareCap` still rounds the entitlement up, against a frozen Type 1 decision, because the mandated `floor` evicts models instead of deferring them

**What the authorities require.** Four sites, and they rule out the shipped construction by name:

- Type 1 (FINAL, frozen @ `8c2a9b04`) decision item 7, L42-43: "`fairShareCap` becomes a whole-replica
  **`floor` fill**, not `ceil`-of-a-division."
- Type 1 `W5` row 6, L2481: "`floor(remaining_GPUs / GPUsPerReplica)`, then `min` with the real pool.
  **Not a divide-and-round**."
- Type 1 L1159-1168: "Note **`floor`, not `ceil`**: this is a budget, and a partial replica is not
  affordable. `ceil` … **over-grants by up to one replica at every boundary** … **Flag it in the commit
  message** — it is the one place the conversion is not value-neutral."
- Plan §2 site (ii) L433 ("row 6: a whole-replica `floor` fill") and §6 L2035-2036 ("`fairShareCap`'s
  must be **gone**, replaced by the whole-replica `floor` fill").

**What shipped.** `greedy_score_optimizer.go:619` — `replicasToCover(entitlementGPUs, gpusPerReplica)
= int(math.Ceil(entitlementGPUs / float64(gpusPerReplica)))`, called as
`capN := min(replicasToCover(target, gpusPR), gpusAvail/gpusPR)`. The **divisor** pivoted correctly
(PRC → `GPUsPerReplica`, which is the actual bug-#5 fix); the **rounding** did not.

**The coder's evidence, and my independent confirmation of the mechanism.** Writing the plan's `floor`
exactly produced **9 failures of 334**, with deltas up to **−4 replicas** and one (`bv` 6→2) under an
*unconstrained* GPU budget — far outside the plan's "one replica at a mid-replica boundary" stop
condition, so no golden was touched. I verified the diagnosed mechanism against the code rather than
relaying it:

- `fairShareRolePick` returns `("", 0)` only when **no** variant in the role clears every gate — a
  single `capN == 0` merely `continue`s to the next variant. So eviction needs the model to place
  nothing anywhere, which is exactly what a sub-one-replica entitlement produces at every variant.
- `allocateForModel` returns `w.remaining < oldRemaining`, i.e. **false** when nothing was placed.
- `fairShareScaleUp:248-252` then sets `w.remaining = -1`, and `filterActive:441-449` drops the model
  from `active` for the **rest of the cycle**. It is never revisited as the mean falls in later rounds
  and its entitlement grows past a whole replica.

So under `floor`, a model behind the water level by less than one replica's worth of GPUs is not
deferred — it is **evicted with zero replicas**. Under `ceil`, `target > 0` guaranteed `capN >= 1`, so
every iteration made progress. The collapse-to-1 signature in the coder's table is that, and the
mechanism claim holds.

**Which way the evidence points** (the call is Dean's; a reviewer owes him the read, not silence).
The coder's technical argument is strong, and the Type 1's stated *rationale* is the weak link:
`gpusAvail/gpusPR` is integer division on the **real pool**, and it was already integer division
before C6c. That term, not the entitlement rounding, is what prevents overcommit. The Type 1's "a
partial replica is not affordable" treats the entitlement as a budget; in `fairShareRolePick` it is a
water-level **gap**, and rounding a gap up cannot commit a GPU that does not exist. On that reading
`floor` on the entitlement buys no hardware safety and costs convergence.

But `ceil` does concede the thing the Type 1 objected to — a model owed a fraction of a replica takes
a whole one. **The coder's own option (b) is the only resolution that satisfies both**: make
`capN == 0` mean *defer*, not *evict*, which requires `!allocated` to stop unconditionally setting
`remaining = -1`. That is a change to the loop's **termination argument**, not to the cap, and the
coder is right that it deserves its own commit with its own convergence reasoning. If Dean wants the
frozen design honoured rather than amended, that is the path — not a one-line `ceil → floor`.

**Residual risk if the fork resolves to `floor`.** Three artifacts currently read as *endorsement* of
`ceil` and must be revisited **together**, or a future coder implementing the frozen design will face
a red test that appears to bless the thing they are removing:

1. `greedy_score_optimizer_test.go:1386` — `It("rounds the entitlement up to a whole replica and the
   pool down", …)`, asserting `capN == 3` for a 5-GPU entitlement at 2 GPUs/replica. The spec is
   well-built (direct closure call, exactly the level Finding 20 says site (ii) is observable at) —
   its **name and comments** are the hazard, not its construction.
2. `replicasToCover`'s doc comment ("rounding up").
3. The commit message's justification paragraph.

### Finding 23 (nit — fixable now, one amend, branch still unpushed) — `34b18bc5`'s message presents the rounding as settled and reads the green goldens as confirmation

Two things a reader of `34b18bc5` alone cannot learn, both cheap to fix while the branch is local:

- **The message does not say the fork is open.** It documents `ceil` as "a deliberate choice" and
  argues for it, which is accurate but reads as *decided*. A frozen Type 1 decision was deliberately
  not implemented and is awaiting Dean — the message should say that. The plan required this commit to
  call out the `ceil → floor` behavior change; since the change was not made, the message should
  call out **that** instead. The handoff carries the fork correctly; the permanent code-side history
  does not.
- **"Every golden is unchanged" is *expected* under retained `ceil`, not evidence.** Site (ii) is the
  one site that could have moved a golden, and it did not move because it was not changed. The pivot's
  value-neutrality is established by the other five sites; the goldens are **silent** on the cap. Worth
  stating so nobody later reads the green goldens as having exercised it. (The message's own
  cross-reference — value-neutral "on one condition that is item 3" — is *correct*: I verified that
  building site (v) from score-weighted `combineVotes` would have moved the numbers.)

### Three plan defects the coder found — all independently confirmed

Credit to the coder; recording them so the planner strikes the wrong text rather than letting it
survive as apparent authority.

1. **§2 #5(i) L394-397 is factually wrong.** It says `GPUsPerReplica` "lives on the same
   `VariantCapacity`" and calls `gpusPerReplica(vc)`. Confirmed false: `domain.VariantCapacity`
   (`internal/domain/analyzer.go`) carries `VariantName / AcceleratorName / Cost / Role /
   ReplicaCount / PendingReplicas / PerReplicaCapacity / Reason` and **no** `GPUsPerReplica`; the field
   is on `domain.VariantReplicaState` (`internal/domain/saturation_analyzer.go`), reachable only via
   `gpusPerReplicaFromState(stateMap, name)`. **The DECIDED option-(a) signature therefore cannot reach
   the factor at all.** The coder's `+ stateMap` extension is the minimal correct fix; the decision
   text needs one more parameter than it anticipated.
2. **§2 site (v)'s "build the fallback from `combineVotes`" is wrong twice.** Confirmed:
   `votesFromPickerState:445` computes `Value: state[i][role] / prc` — it **already** divides by PRC,
   so a `toGPUs` on its output divides a second time; and `combineVotes(_, true)` is score-weighted by
   construction (its own doc comment: "Callers round once, **after the weighting**"), which would put a
   ranking weight back into the number the model spends — the invariant the design states as
   *priority orders, never scales*. The coder implemented the plan's **other**, consistent statement
   (plain unweighted `max_i`). Correct choice; the inconsistent statement should be struck.
3. **§6's `ceil(` grep finds nothing.** Confirmed: `grep -rn "ceil(" internal/engines/pipeline/`
   returns zero hits because Go spells it `math.Ceil(`. Run case-insensitively it finds three, and they
   classify exactly as the coder says — `greedy_score_optimizer.go:619` is the fork above;
   `analyzer_helpers.go:520` (`roleBottleneckReplicas`) and `rescale.go:585` (`roleDemandGPUs`) are both
   `int(math.Ceil(value))` on a **combined demand vote → replica count**, which is the case plan
   L2036-2038 explicitly says must **stay**. Suggest `grep -rni "ceil("`.

### §4's invariant-7 ship gate is on no commit — confirmed independently

The coder flags that §4 L1440-1449's invariant-7 check — a **direct** test that a one-analyzer
`[sat]` ballot leaves the anchor equal to the saturation entry field-for-field, plus a not-invoked
assertion on the per-variant sizing refresh — is assigned to no commit in §4. This is the same gap
already on my C6c checklist, and I confirm it: it is a real PR-level §4 omission, not a coder
oversight. C9 is a reasonable home. It cannot be satisfied by the goldens (invariant 8: a one-analyzer
ballot is an algebraic pass-through, so sat-only goldens cannot exercise combine arithmetic).

### The correct remainder of C6c — substantial, and it is most of the commit

Not buried by the fork. All verified against the diff:

- `toGPUs` / `fromGPUs` returning `(float64, bool)`, with `ok == false` on
  `perReplicaCapacity <= 0 || gpusPerReplica <= 0` — a single conversion boundary in each direction
  (rows 0 and 8), not a conversion sprinkled per call site.
- `claimGPUs` doing `max_i` **within** a role and `Σ_role` **across** roles (rows 1 and 2, and legal
  only there), skipping unpriceable entries.
- `fairShareValue` reduced to `priority × claimGPUs` with the fallback returning the **unweighted**
  claim — so both paths return GPUs, and Score is out of the spend.
- Site (iv)'s clamp converting the bound down through **each entry's own** PRC while `ps` stays raw —
  the unit-table row 8 shape, and the third of the three shapes the coder had proposed.
- Fixtures that **vary `GPUsPerReplica`** (1 vs 3 for ordering; prefill 1 vs decode 4 for the multi-role
  clamp), which is what escapes the cancellation trap the plan warns about at L1024-1027 — a fixture
  holding it constant "cannot detect the pivot at all".
- `referenceVariantForRole` documenting the surviving reference-variant approximation instead of
  silently keeping it.
- The `cost_aware_optimizer.go` hunk is comment-only, and correctly so: the scale-down score-weighted
  tie-break is an **ordering** key, not the fair-share metric, so the invariant permits the weight
  there. The coder added one clarifying clause at the canonical definition site rather than duplicating
  it at every call site, and left `rescale.go:380` alone. I agree with both calls — and with the
  judgement that those two inventory entries are **not** false after C6c.

**No handoff from me on Finding 22.** `plan__ta-anchor-c6c-ceil-eviction-fork.md.WIP` already carries
the fork to a planner with better evidence than I could add (a measured 9-failure run I cannot
reproduce without editing code, which is outside my scope). A second overlapping handoff is the churn
this review has been documenting. Findings 23 and the three plan defects ride the same fork resolution
and need no separate channel. What I owe Dean directly is unchanged and listed in Finding 13's window.

[↑ TOC](#toc)

## C6d review (`330fcd26`) — the fix is better than the one I pre-measured; the ballot underneath it is still non-compliant

`330fcd26` "pipeline: re-check the role veto per variant; shed by coverage/GPU (C6d)" — 5 files,
+507/−61 (`analyzer_helpers.go` +152/−, `cost_aware_optimizer.go` +56/−, `cost_aware_optimizer_test.go`
+270, dev-guide +84, `rescale.go` +6). Tree clean at the C6d tip. Gates re-run by me, not taken from
the coder's report: `go build ./...` clean, `gofmt -l` clean, `go test ./internal/engines/pipeline/...
-count=1` → `ok 0.046s`. **Neither golden file is touched** (grep count 0) — correct, and § *Golden
coverage* below establishes that the goldens *structurally cannot* cover the key this commit changes.

### The dominance arithmetic — verified independently, because it decides whether the fix design is right

The whole C6d design rests on one claim: a veto cannot be expressed as a synthetic `0` vote, because
`combineVotes` does not treat a `0` as absolute. I re-derived the tail rather than accept it:

```
correction += (e − vt.Value) · excess     for excess = vt.Score − votes[b].Score > 0
return e − correction/sumScore
```

A `0` vote binds (`e = 0`, `correction = 0`) **only when nothing outscores it**. Any higher-scored
voter contributes a negative correction term and lifts the result back above zero. So a `0` vote is
absolute exactly in the *uniform-score* case — which is the shipped configuration, since `voteScore`
returns `1.0` for every entry with `Score <= 0`. The coder's refusal to encode the veto as a synthetic
zero vote is **arithmetically correct, not a rationalization**: under any non-uniform score assignment
the veto would silently evaporate. The chosen mechanism — a pre-combine predicate `roleSpareVetoed`
consulted *before* the ballot runs — is score-blind and PRC-blind, so it cannot be diluted.

### Finding 24 (no defect — credit, and a correction to my own pre-measurement)

My C6d pre-measurement predicted the defect line was `votesFromRoleSpare`'s `prc <= 0` skip, and the
fix would be to that skip. **That prediction was wrong, and the coder's fix is strictly better.** Two
paths reach the same wrong outcome:

| path | objector's fate under a ballot-level fix | under the pre-combine predicate |
|---|---|---|
| objector cannot *price* variant `v` (`prc <= 0` → skipped) | still skipped; veto still lost | caught — predicate never looks at PRC |
| objector *is* priced but is outscored | vote cast, then diluted by dominance | caught — predicate runs before the combine |

Fixing the skip covers the first path only, and covers it by *forcing a vote at a PRC the objector
does not have* — which is the mixed-unit defect the rest of PR-2 exists to remove. The pre-combine
predicate covers both cleanly. The refactor sharing it with `needsScaleDownForRole` is
behavior-preserving: both old and new return true iff some live keyed entry has `spare <= 0`, and both
return false when `liveCount == 0`. I checked that equivalence directly rather than inferring it from
the tests passing.

**Also to the coder's credit:** the `applyDeallocationForRole` key-presence guard is a latent bug they
*found*, not one the plan named. The plan's §2d.5 site list does not include it. Their handoff
classifies it correctly. This is the second time in PR-2 that the coder has surfaced a real defect
outside the plan's inventory (Finding 20's site (ii) was the first), and both times the plan was the
thing that was incomplete.

### Finding 25 (should-fix — safe today for a structural reason, not by design) — `votesFromRoleSpare` still materializes a missing role key as a `0` vote, which is N7's *veto* value

C6d fixed the veto predicate and `applyDeallocationForRole`, but left the ballot itself
non-compliant. The asymmetry is visible in one file:

```go
// roleSpareVetoed — correct: presence-checked
if spare, ok := e.RoleSpare[role]; ok && spare <= 0 { return true }

// votesFromRoleSpare — bare index: a MISSING key reads 0.0 and casts a 0 vote
out = append(out, replicaVote{Index: i, Value: e.RoleSpare[role] / prc, Score: voteScore(e)})
```

N7 defines a missing role key as **abstain** and a present `<= 0` as **veto**. The bare index collapses
the first into the second. The entry should be skipped, exactly as the `e.Result == nil` and
`prc <= 0` cases above it are.

**Why it is safe today, and the invariant to watch.** I traced reachability rather than assume it.
`initRoleState` populates `RoleSpare[role]` for every role in `e.Result.RoleCapacities`, or
`RoleSpare[both] = e.Spare` for the non-disaggregated shape. So a missing key requires an analyzer
whose reported role set diverges from the role being ordered. That can arise from PR-1's Finding 12
(`throughput/analyzer.go:409-413` sets no `Role` on the scale-from-zero branch, and
`aggregateRoleCapacities` derives its keys from exactly that field) — but the shapes that produce a
missing role key also leave that role with **no anchor variants to shed**, so it self-cancels. The
coder's "safe today" holds, for a stronger and more structural reason than they gave.

The invariant to watch — worth stating in C9's dev-guide text, not just here — is: *an analyzer's
`RoleSpare` key set must not diverge from the role set of the variants it prices.* Anything that
breaks that (a per-role analyzer gaining a role it cannot price, or Finding 12 being fixed in a way
that adds role keys without adding capacities) makes this reachable, and it fails **toward
over-removal**: the missing key becomes a vote of `0`, and under uniform scores a `0` binds.

An earlier draft of this finding nearly went out claiming TA never decomposes per-role at all — which
would have made the mission's own `[sat,TA]` P/D target configuration a live functional hole. It came
from a grep at the wrong path (`internal/analyzers/…`, where the tree is
`internal/engines/analyzers/…`). `throughput/analyzer.go:481` does decompose via
`aggregateRoleCapacities`. Corrected before it entered this doc; recording the near-miss because the
same wrong path could mislead the next reader.

### Finding 26 (should-fix, test-only) — fixture 3 is green only on an inherited score spread, and names a property that is false under shipped configuration

`cost_aware_optimizer_test.go` fixture 3, *"still lets removal proceed when the role key is missing
(N7 abstain)"*, sets `abstainer` Score 1 / `RoleSpare{"prefill": 1234}` and `trusted` Score 3 /
`RoleSpare{both: 1000}`. Ordering role `both`:

- `roleSpareVetoed(s, "both")` → abstainer's `both` key absent (`ok` false, no veto); trusted's
  `1000 > 0` (no veto). Proceeds to the ballot.
- `votesFromRoleSpare` → abstainer casts `0/500 = 0` (Finding 25's bare index); trusted casts
  `1000/100 = 10`.
- `combineVotes` down: `b` = abstainer, `e = 0`; `excess = 3 − 1 = 2`; `correction = (0−10)·2 = −20`;
  `sumScore = 4`; result `0 − (−20/4) = 5 > 0` → removal proceeds. Assertion passes.

Normalize both Scores to `1` — the shipped default — and `excess = 0`, `correction = 0`, result `= 0`,
which is **not** `> 0`: removal does not proceed and the fixture goes red. So the fixture passes on a
3:1 spread inherited from fixture 2, and the property in its name does not hold in production
configuration. It is currently encoding Finding 25's defective behavior as though it were the intended
contract. Two clean resolutions, both cheap: fix Finding 25 (then the abstainer is skipped, one live
voter remains, and the fixture is green at uniform scores for the right reason), or keep the fixture as
a deliberate red-on-normalization canary with the score spread named in the test body as load-bearing.
Silently leaving it is the option to avoid.

### Row 7 conformance, and golden coverage — the coder's conclusion is right, the stated reason is not

`coveragePerGPU` implements plan row 7 verbatim: `max_i` of `prc / float64(gpusPR)` (not `Σ_i`),
skipping `prc <= 0`, `best` initialized `0.0`; comparator Cost-desc → coveragePerGPU-asc → name-asc.
Dimensionless, comparator-only, never spent. Matches the Type 1 blockquote and §2d.5 row 7.

The coder justifies the untouched goldens with *"no golden has an exact Cost tie."* **That is false at
file scope** — B1 has `prefill-v` and `decode-v` both at `Cost: 5.0`. The conclusion survives for a
different and more robust reason, which I established per-scenario:

| golden | 2+ variants in one role bucket on the scale-down path? | Cost values | row-7 key consulted? |
|---|---|---|---|
| smoke, A2, C1 | no (single variant) | — | no |
| A3 | yes (`v1`, `v2`) | 5.0 vs 15.0 | no — Cost-desc resolves |
| B2 prefill | yes (`cheap-p`, `expensive-p`) | 5.0 vs 15.0 | no — Cost-desc resolves |
| B2 decode | no (`decode-v` alone) | — | no |
| B1 | genuine 5.0 tie, but `Role: prefill` vs `Role: decode` → **different buckets** | 5.0 = 5.0 | no |

So the row-7 tie-break key is **unreachable in all eight golden scenarios**: wherever a bucket holds
two variants, Cost differs and the primary key decides. That is why none moved — not luck, and not the
absence of a tie. The distinction matters for maintenance: under the coder's stated reason, adding a
second decode variant at `Cost: 5.0` would still read as "no tie exists" while quietly making the key
live.

**Two of my own measurements were wrong here and are corrected on the record.** (1) I earlier recorded
`Role:` as appearing **0** times in the sat-only golden and reasoned that all variants therefore share
one bucket; the true count is **14** (the 0 belongs to `optimizer_combine_characterization_test.go`, a
different file). (2) I then inferred from a `10/3` ↔ `10/3` count match that cost-tied variants share
`GPUsPerReplica`; joining the two structs by `VariantName` shows `Cost: 5.0` spans `GPUsPerReplica`
{1, 2}, so that inference was a coincidence of counts. Both errors pointed at the same right answer by
luck, which is why I re-derived it per scenario.

**The goldens' blindness is answered properly by this commit.** Fixtures 5–8 give the row-7 key direct
*discriminating* coverage — each flips under the old `Σ_i Score_i · PRC_i` key:

| fixture | new key → order | old weighted-sum key → order |
|---|---|---|
| 5 "coverage per GPU, not raw capacity" | a 100/1, b 200/4=50 → `[b,a]` | a 180, b 350 → `[a,b]` |
| 6 "maximum, not a sum" | a max 100, b max 150 → `[a,b]` | a 200, b 160 → `[b,a]` |
| 7 "ignores Score" | a 100, b 150 → `[a,b]` | a 1010, b 115 → `[b,a]` |
| 8 end-to-end shed order | larger-replica variant first | — |

This is the same shape as invariant 8's reasoning (a one-analyzer ballot is an algebraic pass-through,
so goldens cannot cover combine arithmetic and direct tests must): a key the characterization suite
cannot reach needs unit coverage, and it now has four fixtures of it, each proven red against the
superseded key.

### Two smaller items

**`sortVariantsForScaleDown` is not Live-gated.** The new loop checks `e.Result == nil` but not
`e.Live`, so a dead analyzer's PRCs still contribute to `max_i`. Pre-existing shape, not introduced
here, and **ordering-only** — it can reorder shed candidates but cannot over-remove, because every
quantity that *sizes* a removal goes through the Live-gated ballot. Recording it as a C9/VG-up
adjacency rather than a C6d defect: if the combine-liveness hardening touches
`Enabled && Live` consistency, this is the one remaining un-gated read of `Result` on the scale-down
path.

**Dev-guide region overlap — checked, no conflict.** My C6c checklist flagged that both commits touch
`docs/developer-guide/multi-analyzer-pipeline.md`. C6c: +45/−14. C6d: +84, hunks at `@@ -285`,
`@@ -338,12 +343,18` and `@@ -594,21 +605,58` — the shifted offsets confirm they are sequential edits
to the same two regions (`## How results combine`, `### Scale-down path`), not divergent ones. For
C9's endgame the note is that this file has now been rewritten in the same two regions by two commits,
so the final consistency pass should read those regions whole rather than diffing the last commit.

### §4a — C6d is the tenth leaking commit, and the first to add tokens to *production* comments

Measured precisely rather than by counting `+` lines: `N7` in `analyzer_helpers.go` goes **3 → 7**
(four new). Every prior leak in PR-2 was in a commit message or a test description; C6d puts
plans-branch identifiers into shipped production doc-comments, where a reader of merged code has no
way to resolve them. Findings 13 and 19's tally moves from nine commits to **ten**, and Finding 13's
reword window now covers ten messages. The four new production tokens are C9-fixable prose (`N7` →
"a missing role key means the analyzer abstains on that role; a present non-positive balance is a
veto"), and they are additional to the 32 code/doc locations already inventoried.

### Finding 4 — CLOSED by this commit

Finding 4 (raised pre-emptively against the plan's §2d.5 finding-(c) spec) asked whether the role-level
veto would be re-checked per variant rather than once per role. It is: `roleSpareVetoed` is consulted
inside `safeRemovalReplicasForRole`, per variant, before the combine. Closed on the code, not on the
plan.

**No handoff from me on C6d.** Findings 25 and 26 are code-side and belong to the coder's own next
pass; the coder's `plan__ta-anchor-c6d-veto-and-row7-findings.md.WIP` already carries the open
collector hole to a planner, and Finding 25 is the same defect with the reachability argument attached
— a second channel would duplicate it. Finding 26 is a test-only nit inside the coder's write scope.
Finding 24's credit needs no channel. What I owe Dean directly is listed in Finding 13's window, now
at ten commits.

[↑ TOC](#toc)

## Type-1 adjudications routed to me (two `review__` handoffs, 2026-08-07)

The planner routed two defects in the **frozen** Type 1 (`combined-analyzer-optimizer-design.md`,
FINAL @ `8c2a9b04`) to me for a verdict, on Dean's instruction *"If you found a problem in your type 1
then handoff to your own plan reviewer. It own it."* Both handoffs are correctly formatted (`from:` /
`to:` / `session:` + prose, addressed to `review`), both marked `.WIP` by me.

**Scope note, stated because it constrains the deliverable.** A Type 1 is not in my write scope — the
role table gives the review agent Type 6 docs and handoffs only, and Type 1 is a *read* for every role
here. So what I own is the **verdict**, recorded below; the amendment itself belongs to whoever owns
the frozen doc. I am not editing `combined-analyzer-optimizer-design.md`, and Dean's relayed
instruction (reaching me second-hand inside a trigger) does not change that boundary.

### Adjudication 1 — `fairShareCap` `ceil` vs `floor` (my Finding 22): the frozen mandate should be **amended**, and there is a third option nobody has named

The Type 1 mandates, at `:1159-1160`:

```
fairShareCap = floor( remaining_GPUs / GPUsPerReplica[vc] )     // whole-replica fill
capN         = min( fairShareCap, gpusAvail / GPUsPerReplica[vc] )
```

and simultaneously argues the other side at `:1281` and `:2260` — *"the **pool** is enforced, the
**fair share** is [not]"*. Both verified verbatim. That is the internal tension, and it is what makes
this an amendment question rather than a compliance question.

**The planner's non-termination proof is correct, and I verified it independently.** `fairShareScaleUp`
is a bare `for {}` at `:210` whose only exits are `len(active) == 0` and `totalGPUs == 0`. Under the
coder's option (b) — "`capN == 0` means defer, not evict" — a model with a sub-one-replica entitlement
grants nothing, so `allocated` stays false, the `w.remaining = -1` eviction is skipped, `totalGPUs`
never moves, and the model stays active forever. With exactly one such model active, `mean == remaining`
so the `remaining > mean` reset at `:255` does not fire either, and `len(active) == 1` forces
`allocationMean = 0` so `target = remaining > 0` re-enters the same path. **Infinite loop, confirmed.**
Option (b) is therefore not a drop-in; it needs a new termination invariant.

**Option (c), which neither the coder nor the planner named, and which I recommend considering first:**

```
fairShareCap = max( 1, floor( remaining_GPUs / GPUsPerReplica[vc] ) )
capN         = min( fairShareCap, gpusAvail / GPUsPerReplica[vc] )
```

| entitlement | today (`ceil`) | frozen T1 (`floor`) | option (c) |
|---|---|---|---|
| 0.4 replicas | 1 | **0 → evicts the model** | 1 |
| 2.4 replicas | 3 (over-grants) | 2 | **2** |
| 3.0 replicas | 3 | 3 | 3 |

Option (c) satisfies the Type 1's *stated intent* — no over-grant above one replica, "a partial replica
is not affordable" — while eliminating both the eviction and the non-termination hazard, because a
grant of ≥ 1 always happens when the pool allows, so `allocated` becomes true and the loop makes
progress. Termination is preserved exactly as today: the picker still returns `("", 0)` when every
variant is unpriceable, pool-starved, or at `MaxReplicas` headroom, which still yields the
`remaining = -1` exit. The pool remains enforced by the unchanged `min`.

**Verdict.** The frozen `:1159-1160` mandate as written is defective — not because `floor` is the wrong
rounding, but because `floor` alone silently repurposes a *sizing* result as an *eviction* signal, and
the loop's contract cannot absorb that. `gpusAvail/gpusPR` already floors against the real pool, so the
pool term alone prevents overcommit; the mandate treats a water-level gap as a spendable budget, which
is the same category error the `:1281`/`:2260` passages warn against. Ranked recommendation:

1. **Option (c)** — amend `:1159-1160` to the `max(1, floor(…))` form. Honors the intent, bounded
   ≤ 1-replica-per-grant behavior change, no eviction, no new invariant.
2. **Restore `ceil` + amend the Type 1** (the planner's recommendation) — zero behavior change, zero
   risk, but leaves the over-grant the Type 1 wanted removed.
3. **Option (b)** — only with an explicit new termination invariant. Not a drop-in.

I have **not measured** option (c) and cannot: it requires editing code, which is outside my scope. It
would move some of the coder's 9 measured failures (any asserting `ceil(x)` for non-integer `x > 1`)
but **not** the `bv 6→2` collapse, which was eviction. That measurement is the coder's, and it is the
one piece of evidence needed before choosing. **This remains Dean's call** — I am supplying a third
option and a defect verdict, not resolving the fork.

### Adjudication 2 — row 7's internal contradiction: I concur with the planner, and the strike must be narrower than either of us first said

The Type 1 specifies the scale-down tie-break twice, four lines apart, selecting **different
analyzers**: `:1176-1179` says tie-break on the *binder's* PRC, while the `:1181-1186` blockquote and
row 7 at `:2482` say dimensionless coverage per GPU combined with `max_i`. The coder implemented the
blockquote. **Verified: the coder resolved it correctly**, and `coveragePerGPU` matches the blockquote
verbatim.

**My independent corroboration** that the blockquote is the intended survivor: the binder's-PRC reading
is not implementable without giving `sortVariantsForScaleDown` the role *and* a ballot to run — and the
Type 1's own parenthetical concedes exactly this, *"(which requires the function to learn which role it
is ordering)"*. C6d instead threads only `stateMap` for `GPUsPerReplica`. The superseded reading
carries its own admission of the cost that makes it the loser.

**Where I refine the planner's warning.** The planner flagged that **one** clause of the superseded
sentence is still live. It is **two**, and both are implemented — so a wholesale strike of `:1176-1179`
would silently drop two satisfied requirements:

| clause | status | implemented as |
|---|---|---|
| "tie-break on the *binder's* PRC (which requires the function to learn which role it is ordering)" | **superseded** — strike this only | — |
| "name-ascending as the final key" | **live** | comparator's third key |
| "give a variant with no scale-down ballot at all the same key today's weighted sum yields … so that edge does not move" | **live** | `best` initialized `0.0`; old Σ over an empty set was also 0 |

**Verdict.** Surgical strike of the mechanism clause only; keep both trailing requirements, ideally
re-homed into the blockquote so the sentence's survivors are not orphaned when the mechanism goes. No
code change, no Type-3 change — the planner's handoff explicitly requests no Type-3 action from me and
I am taking none.

**One claim in that handoff I cannot let stand as reasoning**, though its conclusion is right: *"no
#1513 golden has an exact Cost tie and none moved."* B1 has a genuine `Cost: 5.0` tie
(`prefill-v`/`decode-v`); it is split across role buckets. The robust reason is the per-scenario table
in § *Golden coverage* above — the row-7 key is unreachable in all eight scenarios because Cost-desc
resolves first in every multi-variant bucket. Same conclusion, different and durable reason.

---

## C11 pre-review — Finding 27 (the FZ-admission ranking inversion)

Prompted by `plan__ta-anchor-c11-ranking-claim-correction.md` (Type-1 owner session → planner, not
addressed to me; read-only). C11 has not landed; this is a pre-measurement so the finding is on the
record before the code exists, in the same shape as the C6d pre-measurement.

### What I verified of the handoff (dispositive claim: CONFIRMED)

`Cost` arrives as **0** for a never-measured variant. Three reads at tip `330fcd26`:

1. `internal/engines/pipeline/analyzer_helpers.go:202` — the anchor merge copies `Cost` from the
   **(a) carrier** (saturation's entry), never from the binder.
2. `internal/engines/analyzers/saturation_v2/analyzer.go:353-360` — `variantCost` is populated by
   iterating `inputMetrics` only.
3. `:373` — `cost := variantCost[vs.VariantName]`, a **bare map index**. A zero-replica variant
   contributes no `inputMetrics`, so the lookup misses and `cost` is the zero value.

Same shape as Finding 25's bare-index defect, in a different file. Worth noting as a pattern: a
missing key silently becoming a meaningful `0` has now produced two separate findings on this branch.

### Amendment (same day, after reading the plan's C6e/C11 sections)

Two things below are **stronger than first recorded**, and one correction to my own framing.

**(1) The frozen Type 1 does not merely omit the premise — it states both halves of the
contradiction, and never connects them.** `combined-analyzer-optimizer-design.md:1334` is the `N5`
row:

> Saturation reports `Cost = 0` for a zero-replica variant; the (a) identity merge propagates it to
> **all three configs**, and `costEfficiency = Cost / PRC = 0` then **ranks that variant cheapest**.

`:1530-1532` then asserts, of the same population, that it *"ranks **behind** every measured
option."* Same doc, ~200 lines apart, opposite conclusions. So my "one unstated premise" framing
above is **too generous**: the premise is stated, in a table the reader passes on the way to the
claim. The defect is an unreconciled internal contradiction in a **frozen** document, which is a
different and more serious class than a missing caveat. The refinement in the next section still
stands on the arithmetic; only my characterization of the doc's failure mode changes.

**(2) The rejection rationale for the alternative is void by the same fact.** Type 1 `:1544-1545`,
transcribed to Type 3 `:1315-1316`, rejects the self-clamping `PRC = TotalDemand` seed because *"it
makes the never-seen variant rank **best** precisely when scale-up is needed."* With `Cost = 0`,
`PRC = 1` **also** ranks it best. The stated ground therefore does not distinguish the chosen
mechanism from the rejected one.

The decision still stands — but on the cap and the one-bite-then-measure intent, not on this
comparison. Left as-is, the doc reads *"we rejected X because it does exactly what our choice
does,"* which is the kind of thing a reviewer of the eventual PR will find.

**(3) The Type 3 carries the claim in FOUR places, not the two the handoff names.** It cites `:288`
and `:1324`. Also live:

| Site | Text | Why it matters |
|---|---|---|
| `:288` | *"ranking (it sorts **behind** every measured option)"* | named in the handoff |
| `:1324` | §2f ranking row, marked ✅ | named in the handoff |
| **`:1608-1612`** | C11 assertion 4 in full: *"must rank **behind** every measured option: when a measured variant is feasible, assert it is the one chosen"* | **the operative one** — this is the text a coder writing C11 reads to build the spec |
| **`:2199-2200`** | *"a sentinel variant prices at raw cost and sorts behind every measured option"* | load-bearing for the §2.4-retirement argument |

`:1608-1612` is the one that actually costs something if missed: edit only `:288` and `:1324` and the
coder still writes the false assertion, because `:1608` is where the assertion's shape is specified.
With `:1315-1316` from (2), that is **five** edit sites in the Type 3.

### Where I refine the handoff's framing (one point, and it matters forward)

The handoff states *"Both halves are false, from the same root cause."* That overstates it. The
condition for the sentinel to rank behind a measured variant is

```
Cost_s / 1  >  Cost_m / PRC_m        ⟺        Cost_s  >  Cost_m / PRC_m
```

and because measured `PRC_m ≫ 1`, the right-hand side is *tiny* — so **almost any positive `Cost_s`
satisfies it**. The Type 1's `PRC ≫ 1` intuition is therefore sound; it fails at exactly one value,
`Cost_s = 0`, which is the production value. The rationale is not wrong in principle — it is wrong
because of one unstated premise (`Cost_s > 0`).

This is not pedantry: it means the intended guarantee is **recoverable** the moment the saturation
zero-replica cost bug is fixed, with no change to C11. That is the strongest argument for the
handoff's optional dormant spec, and it is the sentence a future reader needs. "The rationale was
always false" would tell them to redesign something that is fine.

### What neither the handoff nor the plan says: C11 *introduces* the inversion

Today the claimed property **holds** — by a mechanism the Type 1 never cites:

- `cost_aware_optimizer.go:267-270` — `costEfficiency` returns `math.MaxFloat64` when
  `PerReplicaCapacity <= 0`. A never-measured variant sorts **strictly last** in its role.
- `cost_aware_optimizer.go:95-97` — `costGreedyRolePick` then `continue`s on `PRC <= 0` anyway.

So the sentinel population is guarded **twice** today: sorted last *and* skipped. C11's `PRC = 1`
lifts the variant out of the `MaxFloat64` branch into `Cost/PRC = 0/1 = 0`, which sorts **strictly
first**, and simultaneously clears the skip. Both guards fall to the same one-line change.

The honest characterization is therefore *"C11 inverts a property that currently holds"* — a
regression introduced by the fix — not *"the Type 1 mis-stated a property that never held."* The
consequence for review: after C11 the **one-replica cap is the sole remaining guard** on this
population, where today there are three (sort-last, skip, and no cap needed). That is what makes the
plan's `:2065-2080` tag/cap-coupling grep load-bearing, and it is a stronger reason than the handoff
gives.

### Concrete hazard to check when C11 lands

`cost_aware_optimizer.go:99-106` — the pick returns `headroom` when `MaxReplicas` is set and
non-zero, and **`math.MaxInt`** otherwise (`:106`). A sentinel that now sorts first therefore claims
an *unbounded* grant on the `MaxReplicas == nil` path. So:

> If C11 implements the one-replica ceiling only inside the `MaxReplicas` headroom branch, the
> `MaxReplicas == nil` path bypasses it completely and the sentinel absorbs the entire grant.

The cap must sit at the granting site (or unconditionally in the pick), not in the headroom branch.
This is the failure the handoff's suggested assertion-2 shape catches; I am naming the exact line it
has to catch.

### Golden risk: measured at zero, for a reason worth recording

No golden can move through the ranking path, because **none has a never-measured input variant**.
Every input `VariantCapacity` across all eight scenarios carries `PerReplicaCapacity: 10000` and
`ReplicaCount >= 2`.

One trap for the next reader: grepping `Replicas: 0` in `optimizer_characterization_test.go` hits
`:342` (`"expensive-p": {Replicas: 0, ...}`) in scenario B2, which looks like a zero-replica input.
It is not — that line is inside the **`want` map** (the expected post-decision target after
`expensive-p` is fully removed). B2's *input* for `expensive-p` is
`ReplicaCount: 2, PerReplicaCapacity: 10000` (`:317`). The sentinel population is empty in the
goldens.

### Checklist additions for C11 (extends the existing 9 items)

10. The one-replica cap is at the granting site, not only in the `MaxReplicas != nil` branch
    (`cost_aware_optimizer.go:99-106`) — see the hazard above.
11. Every spec produces `Cost = 0` the way production does (no replica metrics for that variant), not
    by rigging a non-zero `Cost` — otherwise the spec asserts an invariant production lacks.
12. No spec asserts *which* of several never-measured peers wins: they tie at efficiency `0` under
    `sort.Slice` (`:260-262`), which is unstable. Set-level totals only.
13. `analyzer_helpers.go:213-216` — the comment *"Not proactively selectable; genuine cold-starts
    fall to the reactive scale-from-zero engine"* is the exact claim C11 reverses, and must change in
    the same commit. Confirmed present at `330fcd26`.
14. The greedy path is **not** a substitute for the cost path in these specs: `fairShareRolePick`
    gates on `available[vc.AcceleratorName]` (`greedy_score_optimizer.go:419-422`), and a
    never-measured variant's `AcceleratorName` is empty from the same zero-replica lookup
    (`saturation_v2/analyzer.go:372`), so `available[""] == 0` skips it regardless of PRC. Verified.
    Pre-existing; **not** C11's to fix.

Items 13 and 14 are the handoff's; 10–12 are mine. Item 14 is the one that would otherwise cost the
coder an afternoon debugging a working sentinel, so it is worth carrying even though it is a
non-finding.

### Scope note

The requested edits land in the **Type 3** (`§2f` ranking row, C11 assertion 2, the grep block) and
the defect is in the **frozen Type 1** at `:1530-1533`. Neither is in my write scope. I am recording
the verification and the two refinements here and routing them to the planner; the Type-1 touch is
Dean's call, as the handoff itself says.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## C6e review (`784c2b5c`) — `pipeline: one fair-share entitlement per model, drawn in sequence`

3 files, +420/−21 (production +241, test +154 additions-only, dev-guide +46). DCO signed. Reviewed
against plan §C6e (`1a116e7a`).

**What landed, and it is good work.** Three coordinated changes: (a) a new `debitCommittedDemand`
called after `initRoleState` and before the clamp, charging already-committed replicas against the
entitlement; (b) the clamp restructured from role-outer/entry-inner to entry-outer/role-inner over a
hoisted `roleRefs` slice, carrying a per-entry running `balance` with an unconditional one-replica
floor; (c) `fairShareRolePick` gains a `committed0` snapshot and a per-role `reserved` ledger, with a
per-draw holdback for roles that have not yet drawn, `firstDraw`, and `capN := replicasToCover(share,
gpusPR)` — replacing the pre-C6c `fairShareCap := ceil(target / PRC)` and the `_ = s; _ = roles`
stubs.

**Verified sound, independently:**

- **The starvation guarantee holds.** `reserved[first] ≤ balance − 1` ⇒ `share_last ≥ 1` ⇒
  `replicasToCover(≥1, gpusPR) ≥ 1`, so the last role always draws at least one replica.
  Holdback-on-every-draw paired with `replicasToCover`'s round-up is a sound combination, not a
  coincidence.
- **The `reserved`-clear heuristic matches its only caller.** `allocateForModelPaired` is
  all-roles-or-nothing and commits after the full pick sweep, so "same role draws twice ⇒ clear all
  reservations" is exactly right.
- **The fixture arithmetic reproduces.** decode-v 4, prefill-v 2, spent 7, mean-v 1 all re-derived
  from the code, and the inline counterfactual (prefill-v 7, decode-v 4, 12 GPUs out of a 7-GPU pool,
  `available` → −5) reproduces exactly. A genuine characterization, not a fitted expectation.
- **The test diff is additions-only** (+154, zero deletions) — independent evidence that no existing
  spec moved.

### Correction to my own pre-registered expectation

I wrote, before this commit existed:

> C6e is the first commit in the sequence where **a moving `[sat]`-only P/D golden is expected, not a
> bug** … If the coder's commit reports "no golden moved," that is the signal to look harder, the
> inverse of the rule for C1–C6d.

**That was wrong in its premise, and the commit is right.** The coder's reasoning — `target` is
`w.remaining − allocationMean`, and `allocationMean = 0` whenever `len(active) == 1`, so a
single-model fixture gets `target == claim` — is correct, and the conclusion generalises further than
the commit claims. Because `claimGPUs` (`:85-106`) **sums** role claims in GPUs, the entitlement for a
single active model equals exactly the roles' combined spend; the shared balance therefore binds at
exactly the sum and never below it. So **`W1` is unreachable without multi-model contention**, and
"every existing golden is single-model" stops being an assertion that needs checking and becomes a
sufficient proof that no golden *can* move. It is also precisely why the new fixture needs a second
mean-setter model to observe anything at all — which the coder's own comment says.

### Finding 28 (should-fix, test-only) — the suite pins site (iv) but not site (ii); the whole ledger apparatus is asserted by nothing

Plan §C6e names **two** defects to pin: the per-role budget in `fairShareRolePick`, and the
per-`(analyzer, role)` clamp against the full target. The suite pins one.

The structural reason is short: **with a single analyzer entry, the clamp's per-entry running balance
and the picker's per-model ledger are the same constraint.** Spec 1 is sat-only — one entry — so it
cannot separate them. Fixing the clamp alone introduces a shared balance across roles *there*, which
produces the sequenced split by itself. Tracing confirms the digits: decode-v 4, prefill-v 2, spent 7
— identical to the assertions.

| variant of the fix | spec 1 (sat-only) | spec 2 (two voters) |
|---|---|---|
| neither site fixed (pre-C6e) | RED | RED |
| picker budget only | — | **RED** (decode-v 2, prefill-v 2, spent 3) |
| **clamp only** | **GREEN** | **GREEN** (decode-v 4, prefill-v 2, spent 7) |
| both (as landed) | GREEN | GREEN |

So spec 2 *is* a genuine discriminator for the clamp — that part works. But no spec goes red when the
picker-budget half is reverted, which means `committed0`, `reserved`, the per-draw holdback and
`firstDraw` — the largest and most intricate part of a +241 production diff — are pinned by no
assertion in the branch.

"Both specs fail on the old code" is true, since the old code had neither fix. It is a strictly weaker
property than "each named defect is pinned", and it is the property the suite actually has.

Two details sharpen this rather than soften it:

1. **The fixture comment asserts a causal story the assertion cannot distinguish.** At the draw split
   it reads: *"Decode draws first and its share is 7 less the one GPU held back for prefill, so it
   takes 6 / 2 = 3 replicas; prefill draws against the 1 GPU that is left and takes 1."* That
   describes the picker holdback. The same digits arise from the clamp acting alone.
2. **The plan asked for a fixture shape that would have discriminated, and it was not used.** §C6e
   asks for "roles that would each individually fit but jointly overrun." In the shipped fixture both
   roles individually *exceed* `target` — which is exactly what lets the clamp-only variant pass.

**The discriminating technique is already established one commit earlier, by this same coder.**
`34b18bc5`'s message: *"the cap is asserted by calling the returned pick closure, because at the
optimizer level the cap bounds per-iteration progress while a separate bound governs the allocation
total, and a fixture there stays green either way."* That is this problem, named and solved, in the
immediately preceding commit.

This is **Finding 20's shape recurring** — and Finding 20 was promoted into the plan, so the general
instruction is already there. C6e is where it was not applied.

### Finding 29 (should-fix, dev-guide) — "gets `mean == 0`" is false under the section's own use of `mean`

The new "Fair-share iteration" paragraph says the single-model case "gets `mean == 0`". What
`fairShareScaleUp:292-297` zeroes is the separate `allocationMean`. `mean` itself (`:285`,
`computeMean(active)`) is **not** zero for a single active model — it equals that model's own
remaining — and it keeps governing the `w.remaining > mean` drop check at `:308`.

This matters because the same dev-guide section uses `mean` in steps 1–3 as the **water level**, so
"mean == 0" reads as "the water level is zero", which is the inverse of what happens: the water level
is the model's entire claim, which is why `target == claim` and why no golden moves. The mechanism the
paragraph explains is right; the variable name is wrong, and wrong in the direction that makes the
explanation self-defeating.

### Finding 30 (nit, test-only) — the deliberate behaviour change is declared in the commit message but not in the `It()`

§C6e requires the expected `[sat]`-only movement be stated "in the commit message **and** in the
`It()`". The commit message does it. All three `It()` descriptions read as pure invariants ("spends
one shared balance across the roles, never one per role" / "does not multiply the entitlement by the
number of analyzers" / "draws the roles in a deterministic order"). Same root as Finding 28: a fixture
built to a different shape than the one specified.

### Four candidate findings verified and retracted — none filed

Recorded because the verification is the load-bearing part, and because at C6c I nearly filed a
materially false finding by writing it up before reading the coder's account.

1. **`debitCommittedDemand`'s nil guard too coarse for a partly-seeded entry** — retracted:
   `initRoleState` seeds all-or-nothing per entry, so `if _, seeded := ps[i][role]; !seeded` is exact.
2. **Currency mixing in `balance := target − float64(spentGPUs)`** — retracted: `claimGPUs` already
   denominates `target` in GPUs. I also correct my own intermediate claim that the ledger makes `W2`
   non-linear: the pre-C6e per-role cap was already linear in priority, so C6e is a strict tightening
   and changes nothing for `W2`.
3. **Mixed-ballot phantom role** — retracted as theoretical: both analyzers publish `RoleCapacities`.
4. **The `RoleBoth`/`freshPs` half-applied debit** (`:346-351`) — retracted, and this one took two
   source reads to kill: `saturation_v2/analyzer.go` `aggregateByRole` returns `nil` when
   `!hasDisaggregation`, and `throughput/analyzer.go` `aggregateRoleCapacities` returns `nil` when
   `len(byRole)==0 || (len(byRole)==1 && hasBoth)`. So `RoleCapacities == nil` ⟺ non-disaggregated,
   exactly as `analyzer_helpers.go:275` documents, and the debit's nil guard is exact. (Also checked:
   `saturation/engine_v2.go:508` writes inside `range r.RoleCapacities`, so a nil map is a no-op, not
   a panic.)

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## Claim pricing under `GPUsPerReplica` asymmetry — three handoffs adjudicated

Three artifacts routed to me as `review__`: the planner's
`ta-anchor-claim-pricing-gpuspr-asymmetry`, the coder's measured
`ta-anchor-claim-inflation-measured-single-analyzer`, and the planner's addendum
`ta-anchor-claim-pricing-headroom-root`.

**Verdict: the defect is real, and the measurement stands.** Verified at tip:

- `claimGPUs:86-97` takes **both** conversion factors from the reference variant — `gpusPR :=
  gpusPerReplicaFromState(stateMap, vc.VariantName)` and `prcForVariant(e.Result, vc.VariantName)`,
  where `vc = referenceVariantForRole(...)`.
- `referenceVariantForRole:840-843` filters on `vc.PerReplicaCapacity > 0` and nothing else — **no
  headroom check**, confirming the planner's addendum.
- So `claim = demand/PRC_ref × gpusPR_ref` while `spend = n × gpusPR_picked`, equal only when the two
  variants agree on `GPUsPerReplica`.

**I re-derived both rows of the coder's two-model measurement from the code and both reproduce**
(X +3 / Y +1 asymmetric; X +2 / Y +2 symmetric, the latter over three iterations). One GPU moves from
Y to X because a variant X provably cannot buy is described as consuming three GPUs per replica. The
pool is honored in both runs (4 = 4), so this is a pure redistribution between models — which is why
no pool check and no `#1513` golden can catch it: every golden is single-model per pass.

### Finding 31 (should-fix — Type-1 rationale defect, not a C6e code defect) — the doc comment's dismissal answers a question about the *cap*, and the reference is chosen by money-efficiency but used to denominate a GPU quantity

`referenceVariantForRole`'s doc comment (`:829-838`) anticipates reference ≠ picked and dismisses it:

> That disagreement needs no correction in GPU space: the cap divides by whichever candidate the
> picker landed on, and GPUs per replica is immutable deployment topology rather than a re-derived
> capacity.

Two things are wrong with this. The planner's handoff identifies the first:

1. **It names the wrong approximation.** The paragraph that follows scopes the acknowledged
   imprecision to unequal **per-replica capacities**. The defect is in **`GPUsPerReplica`** — the very
   quantity offered as the reason the divergence is safe. Immutability is not the property needed;
   agreement between the two conversions is, and they do not agree.
2. **It is an answer about the cap, not the claim** — my addition. "The cap divides by whichever
   candidate the picker landed on" is *true and irrelevant*: the cap is consistent with the spend by
   construction. The **claim** is not, and the claim is the model's ranking key and its per-pass
   `target`. The sentence closes a question nobody needed answered while leaving the one that matters
   untouched.

**The deeper statement, which no handoff makes.** `sortByCostEfficiencyAsc` orders by `Cost / PRC` —
*money* per unit of served capacity. The reference variant is therefore the **money-cheapest** one, and
its `GPUsPerReplica` is then used to denominate a **GPU** quantity. Nothing ties the money-cheapest
variant to the GPU cost of serving the role's demand. That is the category mismatch;
headroom-blindness is the sub-case where the resulting divergence is *permanent and predictable*
rather than transient, which is why both reproducers are built on it. So headroom is the shared
**trigger**, not the shared root.

**Consequence for the fix menu.** The planner's headroom filter removes both measured cases, is ~3
lines, and — as the planner says honestly — converts a measured distortion into a narrower unmeasured
one. It does not address the class, because it does not make the claim consumption-faithful.

**Option (d), which none of the three handoffs raises:** select the reference *for pricing* by **GPU**
efficiency — the minimum of `gpusPR / PRC` over the role's feasible candidates — rather than by cost
efficiency. Properties: the claim becomes a true lower bound on the GPUs needed to serve the role, so
it can never be inflated; it is headroom-independent, so it also covers the transient case the
headroom filter misses; it degenerates to today's value whenever the role's variants share a
`GPUsPerReplica`, which is every existing fixture; and under-claiming is the conservative direction
for fair share (lower rank, lower `target`) while spend stays bounded by the cap, which already
converts through the picked variant. Cost is comparable to the headroom filter. Its limit: it changes
pricing only, not pick order, so the money-cheapest variant is still what gets bought — the claim
becomes a floor on the model's true GPU need rather than a prediction of its spend.

**Disposition is not mine.** The Type 1 is frozen at `8c2a9b04` and outside my write scope; a
post-freeze touch to its GPU-space rationale is Dean's call, exactly as recorded for Finding 27's
`:1530-1533`. Both handoffs address me as "Type-1 owner"; my role is internal code reviewer, and the
choice between accept-and-document, the cheap partial, and option (d) has PR-2 scope implications
belonging to Dean and the Type-3 owner. **Recorded, routed, not decided.**

### Finding 32 (should-fix, process) — the addendum's "treat it as settled" rests on a derivation that cannot execute

The addendum states it verified the coder's measurement "independently of his harness" and concludes
*"the measurement is not harness-dependent. Treat it as settled."* The derivation it gives applies the
`w.remaining <= mean` branch (`:295-296`) to compute `allocationMean = 6 − 9/2 = 1.5`. But `w` is
`active[0]` **after `sortByRemainingDesc`** (`:289-290`) — the **maximum** — so `w.remaining <= mean`
is unreachable unless every active model's remaining is equal. In the asymmetric run `9 ≠ 3`, so the
real values are `allocationMean = mean = 6` and `target = 3`, not `7.5`.

The row's *outcome* survives: `n = min(bottleneck 3, capN)` and the bottleneck binds at 3 either way,
so the derivation reaches the right answer for the wrong reason. The symmetric row's first step is
correct (`3 <= 3` genuinely holds), then takes the same unreachable branch; the true path is three
iterations (X +2, Y +1, Y +1) arriving at the same X 3 / Y 3.

So **the measurement is confirmed — by my re-derivation, not by the addendum's.** Worth recording
because the addendum explicitly upgraded the finding to *settled* on the strength of that arithmetic,
and the identical slip would materially change any fixture where `capN` rather than the bottleneck
binds — which is most of the interesting ones.

### The coder's fixture question resolved itself, correctly, without me

The coder offered: *"say the word if you want it kept as a real fixture instead and I will land it."*
I did not answer it — a reviewer cannot direct a coder, and the fixture decision belongs in the Type 3.
It resolved anyway: `537b0153` landed the dormant-spec shape the **planner** recommended (see below).
Recording the non-answer because the offer was addressed to me and the right response to a misrouted
question is to leave it misrouted, not to accept the authority being offered.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## C6f landed (`a679f2ad`) — review pending; credit for pre-empting Finding 31

`pipeline: abstain is not exempt -- make W4 a tested property (C6f)`, 6 files +246/−3.

**Verified: the production edits are comment-only.** Stripping comment and blank lines from the diff
of all four production files leaves exactly two hunks, both a `continue` whose trailing comment moved
above it. So "test-only plus comments and prose; no behaviour change, and therefore no golden moved"
is accurate as stated — checked rather than taken.

Credit, ahead of the full review: the message states the claim-pricing mechanism correctly and
unprompted (reference vs picked, the `GPUsPerReplica` disagreement, `claimGPUs` pricing through one
value and `fairShareRolePick` spending through the other), declares in capitals that the abstention
property is **not fully gated by these fixtures**, puts the scope warning where a reader of the file
will see it, and declines to assume a disposition. It also revises the plan's own expectation — §C6f
lists C6f among the commits whose goldens should move, and the message explains why that expectation
does not survive C6f's own answer, since the `continue` at the per-role clamp already *is* the
abstention. That is the right way to disagree with a plan: in writing, with the reason.

Full C6f review pending, including the eleven gate comments' entry-abstains vs variant-unpriced split.

---

## `537b0153` review — `pipeline: pin the claim-pricing distortion as a dormant spec`

Test-only, +88/−0, one file. DCO signed. **Not in the plan** — the coder says so in the first line and
isolates it in its own commit so it can be reverted without touching C6f. Correct instinct, and the
right granularity.

**Verified, and this is the best-shaped artifact on the branch:**

- **`PIt` is real.** Ginkgo v2.28.1 `core_dsl.go` does define `PIt`; the coder says it checked the
  vendored source rather than assuming, and there was no prior `PIt`/`XIt` precedent in the tree —
  both claims hold.
- **It asserts the honest split, not today's numbers** — `pricey-x 3`, `y-v 3`, `cheap-x 1`. This is
  the planner's recommended shape and the correct one: a characterization fixture pinning `X 4 / Y 2`
  would freeze the distortion and make the eventual fix read as a regression.
- **It asserts both sides of the redistribution.** `Expect(dm["y-v"]...).To(Equal(3), "Y is a
  bystander and must not be starved")` is the load-bearing assertion — the failure mode is a transfer,
  so pinning X alone would miss it. The inline comment says exactly this.
- **"Red when enabled" is a verified claim, not a placeholder** — X reaches 4 where the spec wants 3.
  A dormant spec nobody ever ran red would be worthless; this one was.
- **The fixture is minimal and its unbuyability is structural**, not contrived: `MaxReplicas: &one`
  with `CurrentReplicas: 1` pins `cheap-x` at its ceiling while `Cost: 5.0` vs `20.0` at equal PRC
  makes it the cost-efficiency winner and therefore the reference. One analyzer, no abstention escape.
- **The comment says it encodes a premise, not a decision,** and states the delete condition. That is
  the honest way to carry a spec whose expected value is an open question.

This closes the coverage gap I recorded above: the measured distortion is no longer unprotected.

### Finding 33 (should-fix, §4a — new class) — plans-branch handoff paths are now cited inside shipped test comments

Two code comments now point at the orphan `plans` branch by path:

- `greedy_score_optimizer_test.go:1602` — `plans/session/handoffs/plan__ta-anchor-c6f-w4-no-spend-is-false.md` (C6f)
- `greedy_score_optimizer_test.go:1741` — `Refs: plans/session/handoffs/review__ta-anchor-claim-pricing-gpuspr-asymmetry.md, review__ta-anchor-claim-inflation-measured-single-analyzer.md, review__ta-anchor-claim-pricing-headroom-root.md` (this commit)

§4a bans plans-branch section identifiers *and* pointers to plans-branch documents. These are the
worse class: a token like `W4` is at least guessable from context, whereas a path into an orphan
branch a reader of merged code cannot check out is unresolvable by construction — and these
specifically point at *handoffs*, the most ephemeral artifacts in the workspace, which are renamed to
`.DONE` and `git rm`-ed in a later sync commit. The reference will be dead before the PR merges.

The intent is right and worth preserving: a reader who finds a dormant spec needs to know where the
open question lives. The §4a-compliant form is prose — "the measured two-model reproducer and the
open pricing question are recorded in the internal design review" — with no path. **These are the
first plans-branch *paths* PR-2 has put in code**; earlier leaks were all bare tokens. Base
`075a208e` has exactly one such path anywhere in the tree, `docs/developer-guide/throughput-analyzer.md:698`
(`plans/planning/TA-Plan.md`, `TA-PR4-plan.md`) — pre-existing, already in `main`, already tracked in
`governance-follow-ups.md`. That precedent explains the habit; it does not license extending it.

Also new in this commit, same family: `Measured on this exact fixture at 784c2b5c` cites a
pre-rebase branch SHA that will not survive the `rebase -i` the branch already needs.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## §4a — definitive recount at `537b0153` (supersedes every earlier figure in this doc)

I have miscounted this twice by under-matching, so this pass enumerates per commit and per file rather
than reporting a total.

**Commit messages — 14 commits · 13 token-bearing · 10 token-bearing subjects · 1 fully clean.**
`34b18bc5` (C6c) remains the only §4a-compliant message on the branch. `537b0153`'s subject is clean;
its body carries `C6f`, `W4`, `Type-1 owner`.

This supersedes CURRENT.md's "all nine (6/9 subjects, 8/9 bodies)", Finding 13's "all nine" at L1372,
and my own "ten" at L3195 — all three are stale, and each was accurate when written.

**Code and docs — attribution against base `075a208e`, which is what makes this actionable:**

| surface | at base (inherited) | PR-2-introduced | at tip |
|---|---|---|---|
| production `.go` doc comments | **0** | **19** | 19 |
| test `.go` comments / descriptions | 11 (of which 3 are `config_test.go`'s generic local "Test 1/2/3" enumeration, not a plans ref) | ~30 | 41 |
| dev-guide `.md` | 1 — `throughput-analyzer.md:698`, a plans-branch *path* | 4 — `multi-analyzer-pipeline.md` `N7`×2, `N8`, "Type-1 owner" | 5 |
| plans-branch **paths** in `.go` | 0 | **2** (Finding 33) | 2 |

The attribution is the finding here: **PR-1 leaked into test comments only; PR-2 is the first to put
plans-branch tokens into production doc comments** — 19 lines across `analyzer_helpers.go` (12),
`rescale.go` (4), `greedy_score_optimizer.go` (2), `optimizer_interfaces.go` (1). C6e's own production
delta is +2, both new: `(W1)` at `greedy_score_optimizer.go:330` and `(Bug #1)` at `:338`, in
`debitCommittedDemand`'s doc comment.

CURRENT.md's figure of "32 code/doc token locations" is now **~49 lines** (19 production + ~30 test),
plus 4 dev-guide and 2 paths. Growth is roughly linear in commits, so the C9 cleanup gets bigger with
every commit that ships prose.

**Reword cost, restated with the corrected magnitude:** 13 commits to reword, not nine and not ten,
and it rises with C11/C10/C9. The branch still needs a force-push regardless
(`origin/…@f6485980` is orphaned), so the `rebase -i` remains ~free until PR-2 opens, at which point
it becomes a live-PR history rewrite. Recommendation unchanged; magnitude corrected. The ~49 code
locations are C9's natural host and are genuinely unhurried — **except Finding 33's two paths**, which
should not ship even in a draft PR, because the artifacts they name are scheduled for deletion.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## C6f full review — `a679f2ad`, "abstain is not exempt"

*Supersedes the placeholder "full C6f review pending" note recorded above. 6 files, +246/−3;
production edits confirmed comment-only by reading every hunk.*

### Credit, stated first because it is unusual

Three things in this commit are better than the plan asked for:

- It **declares its own coverage gap in capitals** — `W4 IS NOT FULLY GATED BY THESE FIXTURES` — and
  puts the scope warning in the fixture's `Context` comment, where a reader who trusts the file
  will hit it, rather than only in the commit message where nobody looks after merge.
- It **disagrees with the Type 3 in writing, with a reason.** The plan lists C6f among the commits
  whose goldens are expected to move; the commit argues that expectation "does not survive its own
  W4 answer", because the `continue` at the clamp already *is* the abstention, so there is no
  mechanism left to change. That is correct, and it is the right way to handle a plan claim a coder
  believes is wrong.
- It **fixes a category slip in the plan's own prose.** The plan calls all six `PerReplicaCapacity
  <= 0` sites "the analyzer abstains". The commit splits them: the **entry** abstains (5 in
  `analyzer_helpers.go`, `coveragePerGPU`, `debitCommittedDemand`) versus the **variant** is
  unpriced and so not selectable (the six the plan names). Both readings are defensible in
  isolation; conflating them is what let the unpriced draw read as harmless. The pricing framing
  resolves it without weakening either, as claimed.
- **It found a MAJOR behavioral defect in a `W`-item's stated contract, measured it, refused to fix it
  unilaterally, and kept moving.** `plan__ta-anchor-c6f-w4-no-spend-is-false.md` presents a two-option
  fork — ship `W4` with a scoped fixture and a named hole, or change the abstention so it reaches the
  vote — states plainly that option 2 is the one that makes `W4` true, and declines to choose because
  it is a mechanism change beyond C6f's scope. That is exactly the escalation the conventions ask for,
  and it took the non-blocking default rather than stopping with nothing delivered. It also reports an
  unexplained negative result (regime D, P/D with equal `GPUsPerReplica`, holds) and says *"I do not
  have a confirmed mechanism for why, and I am not guessing one"* — reporting an unexplained green is
  harder than reporting a red, and most sessions would have called D confirmation of a boundary.

The equality-not-magnitude choice is also right, and for the reason given: asserting a number would
pin today's arithmetic instead of the property. Using the same model identity in both ballots so
`Equal` covers action, cost and replica counts — rather than a hand-picked accessor — is the
stronger form of the assertion and worth keeping as a pattern.

### Finding 34 — W4's "not budget-exempt" guarantee has a reachable hole; the abstention leaves the abstainer's demand **unclamped**

**Severity: MAJOR (behavioral). MEASURED — but not by me, and not first.**

**Attribution correction, written after I filed the paragraphs below.** I drafted this finding from a
code read and labelled it "derived, not measured". That label was wrong and the framing gave me credit
I had not earned. The coder had **already measured this defect**, filed it to the planner as
`plan__ta-anchor-c6f-w4-no-spend-is-false.md`, and written the measured counterexample into the
fixture's own `SCOPE` comment — where it says, in the shipped source, that the inflation is *"upstream
of W4 and reachable with ONE analyzer"* and that *"W4 is NOT fully gated by them."* I read that
comment before drafting and still framed the defect as mine to surface. It is not. **What is mine is
the mechanism trace** — the six-link table below, and specifically links 3, 5 and 6
(`anyRoleNeedsScaleUp`, the `combineVotes` maximum, the `firstDraw` floor), which the coder's handoff
does not enumerate. That trace explains *why* the coder's measurement comes out the way it does; it
does not establish the defect.

W4's prose says an abstaining analyzer "contributes no claim and it spends nothing. It is not
budget-exempt — an exempt voter draws on a budget it never contributed to." The first half is true
of `claimGPUs` (`greedy_score_optimizer.go:99`). The second half does not hold at the clamp, because
the abstention there is implemented as `continue` — which skips the charge **and skips the clamp**,
leaving the abstaining entry's per-role demand at its full seeded value:

```go
bound, ok := fromGPUs(balance, prc, ref.gpusPR)
if !ok {
    continue // no conversion factor ⇒ no budget to bind this entry
}
```
`greedy_score_optimizer.go:449-452`

An abstaining voter that keeps its whole vote and pays nothing into the shared balance is the
permissive reading of "abstain", not the conservative one. The conservative alternative —
`ps[i][ref.role] = 0`, i.e. drop the demand you cannot price — is a different policy with different
behavior, and nothing in the branch states which was chosen. The comment says "no budget to bind
this entry", which describes the charge and is silent on the retained demand.

The retained demand is not inert. Six links, each read at `4fb49ac6`:

| # | site | what it does with the abstainer's retained demand |
|---|---|---|
| 1 | `analyzer_helpers.go` `initRoleState` | seeds `pickerState[i][RoleBoth] = e.Remaining` for **every** entry with a non-nil `Result` — no pricing, enablement or liveness filter |
| 2 | `greedy_score_optimizer.go:451` | `continue` leaves that seed **unclamped** and uncharged |
| 3 | `analyzer_helpers.go` `anyRoleNeedsScaleUp` | `for _, m := range state { if m[role] > 0 { return true } }` — scans **all** entries, so the abstainer alone keeps the scale-up loop alive |
| 4 | `analyzer_helpers.go` `votesFromPickerState` | gates on `prcForVariant(e.Result, variant)` for the **picked** variant, not the reference — so the abstainer **votes** whenever reference ≠ picked and it prices the pick |
| 5 | `analyzer_helpers.go` `combineVotes(votes, true)` | `up && votes[i].Value > votes[b].Value` — takes the **maximum**, so a large retained demand becomes the binder |
| 6 | `greedy_score_optimizer.go` `fairShareRolePick` | `if firstDraw && capN < 1 { capN = 1 }` — grants one replica even when the entitlement is ≈ 0 |

Composed: **a model whose claiming analyzer asks for nothing, and whose only positive demand comes
from an analyzer that could not price the role's reference variant, can still be granted a replica —
driven entirely by the voter that contributed no claim.** That is verbatim the hazard W4 names.

Note which link makes it reachable rather than theoretical: link 4. `votesFromPickerState` keys on
the **picked** variant while the clamp keys on the **reference** variant, so the two gates disagree
in exactly the reference ≠ picked regime — and C6f's own spec 2 constructs that regime deliberately.
The commit is one fixture parameter away from exhibiting this.

**The measurement, quoted from the coder's own reproducer** (single role, pool 100 non-binding, `sat`
demand 30000, TA demand 100000 pricing only `pricey-v`):

| regime | `[sat]` | `[sat, TA]` |
|---|---|---|
| A — reference variant open, picker lands on it | `pricey-v` 1 | 1 |
| B — reference at ceiling, both 1 GPU/replica | `pricey-v` 4 | 4 |
| **C — reference at ceiling, 3 GPUs/replica vs 1** | **`pricey-v` 4** | **`pricey-v` 10** |

`cheap-v` (reference) PRC 10000 at 3 GPUs/replica with `MaxReplicas: 1`; `pricey-v` (picked) PRC 10000
at 1 GPU/replica. Case C is the equality violation: **+3 replicas becomes +9**, and the arithmetic
names whose budget was spent — sat's claim is priced at the reference variant, `30000/10000 × 3 = 9`
GPUs, single model so `target == claim == 9`, converted at the *picked* variant's 1 GPU/replica →
`capN = 9`, and TA drew all nine.

**Why B is green and C is not** — this is where my trace earns its place. The claim is priced through
the reference variant and `capN` converts it through the picked one. When the two share a
`GPUsPerReplica`, `capN` lands exactly on the replica count the claiming analyzer would have asked for
alone, so link 5's maximum is bounded by the entitlement whatever the abstainer votes: `n =
min(bottleneck, capN)` is capN either way. The asymmetry breaks that coincidence — it inflates the
claim in GPUs while leaving the picked variant cheap to buy, `capN` opens to 9, and links 3–5 fill it.
So the six-link chain is the *mechanism*, and the reference-vs-picked `GPUsPerReplica` asymmetry is the
*enabling condition*. Neither alone is the finding.

**One route in the chain is still unmeasured, and it is not the coder's.** Links 3 and 6 admit a
second path that needs no `GPUsPerReplica` asymmetry at all: zero the claiming analyzer's demand
entirely and leave the abstainer as the only positive voter. Then `claim = 0`, `target = 0`, `capN =
replicasToCover(0, 1) = 0` — and `if firstDraw && capN < 1 { capN = 1 }` grants one replica anyway,
kept alive through the pass by the unfiltered `anyRoleNeedsScaleUp`. **Untested.** The coder's regimes
A/B/D do not cover it (all have positive sat demand), so it is neither confirmed nor excluded by the
measurement above. If it holds, the defect is not confined to the asymmetric configuration the coder
found and the "corner, not systemic" assessment needs revisiting; if it does not, some gate upstream
drops the model and that gate is worth naming. Either way it is one fixture, no production change.

**What I am not claiming.** I have not established that the permissive policy is *wrong* — granting
one replica to a model some live analyzer believes is under-served may well be the intended
behavior, and links 3 and 6 both look deliberate. The finding is that **W4's stated contract and the
shipped code disagree**, the disagreement is reachable, and nothing pins which side is intended.
This is a disposition question for the Type 1, not a bug fix for the coder to guess at.

### Finding 35 — neither C6f fixture discriminates the gate it names

**Severity: MEDIUM (coverage). Same family as Finding 28, opposite direction.**

Both specs are green for reasons other than the abstention gate:

- **Spec 1** (`reference == picked`): the picker lands on `cheap-v`, which TA cannot price, so
  `votesFromPickerState` excludes TA from the vote independently of the clamp. TA has zero influence
  by **vote-exclusion**, not by abstention. The fixture comment claims "Both of W4's halves are
  exercised: no claim (`claimGPUs` passes over the entry) and no spend" — the no-claim half is
  genuinely exercised; the no-spend half is redundantly guaranteed here and so not discriminated.
- **Spec 2** (`reference != picked`): TA does vote, but `capN` binds at 3 in both ballots, as above.
  Substitute the conservative abstention (`ps[i][role] = 0`) and the output is unchanged — the
  combine's maximum falls from 10 to 3, still ≥ `capN`. **Both plausible abstention policies produce
  identical output**, so the fixture cannot tell them apart.

This is the mirror of Finding 28. There, C6e's suite pinned the per-`(analyzer, role)` clamp but not
`fairShareRolePick`'s per-role budget, because with a single analyzer entry the two are the same
constraint. Here, C6f's suite pins the **entitlement cap** but not the **abstention gate**, because
in the aligned regime the cap subsumes the gate. Same failure mode — a fixture green for a mechanism
other than the one named — reached from opposite ends of the same code path.

**Second attribution correction.** I wrote that the coder's disclosure was "adjacent but not the same
claim" — that it named only the misaligned regime while Finding 35 named the aligned one. Wrong: the
handoff says *"A and B are green only because `capN` happens to coincide with sat's own bottleneck"*,
which is precisely the aligned-regime point, stated before I made it. **What survives as mine is the
policy-discrimination framing** — that substituting the conservative abstention (`ps[i][role] = 0`)
leaves the output of both shipped specs unchanged, so the suite cannot distinguish the two candidate
policies and therefore pins neither — **and the two-role fixture** proposed below, which is a
different shape from anything in the handoff. The bare observation that the fixtures do not gate `W4`
is the coder's, is in the shipped `SCOPE` comment in capitals, and I should have cited it rather than
re-derived it.

**One fixture family closes both this and Finding 28:** a **two-role** model where the abstaining
entry can price exactly one of the two roles. That separates the clamp's per-entry running balance
from the picker's per-model ledger (Finding 28's requirement, since the roles draw in sequence and
the second role's `bound` depends on what the first charged), and it makes the skipped charge
observable independently of `target` (Finding 35's requirement). §C6f's own text asked for "roles
that would each individually fit but jointly overrun" — that is close to this shape, and the shipped
single-role fixture is what dropped it. The discriminating technique is already established one
commit earlier, in `34b18bc5`'s message.

### Finding 36 — a shipped gate comment forward-references C11, which has not landed

**Severity: LOW (documentation), but it ships in production source.**

`fairShareRolePick`'s `PerReplicaCapacity <= 0` gate now reads:

> The gate asks whether the variant has a price, not whether some number is zero -- a variant
> admitted at a sentinel price is priced, and passes.

`greedy_score_optimizer.go`, and the same framing across the other ten gates. There is no admission
sentinel in the tree at `4fb49ac6` — it arrives with C11. A reader of this commit in isolation
cannot resolve "admitted at a sentinel price"; a reader of the merged squash can. Because PR-2 is one
indivisible PR this resolves itself at merge, so I would not hold the commit for it — but it is
worth noting that the *reason* the wording is safe is a property of the PR's shape, not of the
comment. If C11 is ever dropped or deferred out of PR-2, these eleven comments describe a mechanism
that does not exist, and they are the kind of prose nobody re-reads.

The commit message anticipates this and defends it ("it survives C11 making one of them deliberately
passable"), which is the right instinct pointed forward instead of back. Filed as LOW because the
fix is one clause, and because the framing itself — a rule about pricing rather than about zero — is
correct and is an improvement on "skipped".

### Dev-guide addition (+58) — the strongest prose on the branch, with one taxonomy leak

The `multi-analyzer-pipeline.md` addition documents the claim-pricing defect, both measured
consequences, and says of the near-miss: *"the safety here is a coincidence of two independent
filters rather than a guarantee."* That sentence is the most honest line in the developer guide and
should survive C9.

Documenting a known defect in a Type 4 doc is **compliant**, not a violation: Type 4 must reflect the
actual code state of the branch, and the defect *is* the actual code state. The objection I would
have raised — "no forward-looking content" — does not apply, because the doc describes what the code
does today and does not promise a fix.

What does not belong is the routing: *"The claim-pricing question is open with the Type-1 owner."*
"Type-1 owner" is plans-branch taxonomy, meaningless to a reader of merged code, and it points at a
process rather than at the code. The §4a-clean form states the open question without naming who owns
it. **Partly fixed at `4fb49ac6`** — see the next section.

### §4a delta for C6f

Production: comment-only edits across `analyzer_helpers.go`, `cost_aware_optimizer.go`,
`greedy_score_optimizer.go`, `rescale.go`. The token count does not fall — the gate comments were
rewritten, not de-tokenised — and the fixture `Context` added `W4`, `C6f` and (at the time) two
plans-branch **paths** plus "Type-1 owner". The paths were the Finding 33 sites.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## `4fb49ac6` — Finding 33 fixed proactively, plus the dev-guide `mean` slip

*Landed as `2a0db749`, then amended to `4fb49ac6`; I verified `git diff 2a0db749 4fb49ac6` is empty,
so the amend is **message-only** and no re-review of content is needed. 2 files, +12/−13.*

**Finding 33 — resolved.** Both plans-branch **paths** are gone from
`greedy_score_optimizer_test.go`, replaced with prose that says the same thing without an
unresolvable reference: *"Whether a claim may be priced through a variant the picker cannot buy is an
open design question, not a settled contract."* That is the §4a-clean form of the sentence, and it
carries the same warning. This is the one item I had flagged as not safe to defer to C9, and it was
fixed within the hour without a trigger from me.

**A fix I did not ask for and would not have thought to ask for.** The dormant spec's *"Measured on
this exact fixture at `784c2b5c`"* became *"Measured on this exact fixture, against the claim pricing
as it stands."* I had noted the pre-rebase SHA as a concern; replacing it with a description of the
*state* rather than a pointer to a commit is the better fix, because the SHA would have been dead
after any rebase whereas the phrase stays true.

**The `mean` slip — fixed and then strengthened.** The dev guide said a single active model "gets
`mean == 0`". It is `allocationMean` that is forced to zero; `mean` is the water level, is unchanged,
and still governs the above-the-level drop check. Corrected, and the correction adds the structural
argument: `claimGPUs` sums the role claims in the same GPU currency the roles are charged in, so with
one active model the entitlement equals the combined spend exactly — *"No single-model golden can
move on this."*

That is the same argument I derived when correcting my own pre-registered expectation for C6e, in the
section above, arrived at independently. Two independent derivations of a structural impossibility is
better evidence than either alone, and it upgrades the claim from "no golden in this suite moves" to
"no golden of this shape can move". Worth keeping in the dev guide verbatim.

**What survives.** One taxonomy token remains in shipped source:

```
internal/engines/pipeline/greedy_score_optimizer_test.go:1709:
    // is an OPEN question with the Type-1 owner. If the disposition is that
```

— in the dormant spec's own `DORMANT AND PROVISIONAL` header. The C6f `Context` occurrence was
fixed; this one was missed. The dev-guide occurrence is also gone. So the §4a table above updates
to: plans-branch **paths** in shipped `.go` → **0** introduced by PR-2 (was 2); the single
pre-existing path at `throughput-analyzer.md:698` is untouched base content, already tracked in
`governance-follow-ups.md`, and remains the only one in the tree. "Type-1 owner" in shipped source:
**1**, down from 2 plus one in the dev guide.

The reword count is unaffected — `4fb49ac6` is a fourteenth commit whose own subject and body carry
plans-branch tokens, so it joins the set rather than reducing it.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## Retraction — my option (d) neutrality claim was wrong

**The planner's correction in `review__ta-anchor-option-d-neutrality-is-contingent.md` is right and I
accept it in full.** I wrote that option (d) — pricing the claim through GPU efficiency,
`min(gpusPR / PRC)` over feasible candidates — *"degenerates to today's value whenever a role's
variants share `GPUsPerReplica`, which is every existing fixture."* It does not.

With equal `gpusPR`, `min(gpusPR / PRC)` reduces to **`max(PRC)`** — the capacity-densest variant —
while today's `sortByCostEfficiencyAsc` gives `min(Cost / PRC)`, the money-cheapest. Those coincide
only when PRC is *also* equal across the role. Equal `GPUsPerReplica` is not sufficient, and the
counterexample is already in the suite — golden scenario A,
`optimizer_characterization_test.go:225-247`:

| variant | Cost | PRC | gpusPR | today `Cost/PRC` | (d) `gpusPR/PRC` |
|---|---|---|---|---|---|
| `cheap` | 5 | 10000 | 1 | **0.00050** ← wins | 0.00010 |
| `expensive` | 15 | 20000 | 1 | 0.00075 | **0.00005** ← wins |

At `remaining = 5000` the claim is `5000/10000 × 1 = 0.5` GPUs today versus `5000/20000 × 1 = 0.25`
under (d). **The claim halves, at equal `GPUsPerReplica`.** My statement was not a slip in wording;
it was a wrong reduction, and it was load-bearing for the neutrality argument.

**The conclusion survives, the argument does not.** (d) *is* golden-neutral across the suite, but
contingently: `replicasToCover` ceils both `0.5` and `0.25` to `capN = 1`, and `cheap`'s own
bottleneck `ceil(5000/10000) = 1` binds equally, so the decision set is unchanged and scenario A
stays green; scenario B (`:322-348`) is pure scale-down and never reaches `claimGPUs`. Contingent-via-
`ceil`-plus-a-binding-bottleneck is precisely the class of reasoning Finding 32 calls unsafe, so the
planner is right to refuse "degenerates to today's value" as the recorded justification. **Recorded
justification, corrected:** *(d) moves no golden because `ceil` and a binding bottleneck absorb the
halved claim in the one scenario that reaches `claimGPUs` at all — not because its value equals
today's.*

Two consequences I accept into the option-(d) write-up:

1. (d) changes the **ranking key** for any role with unequal PRC — which scenario A has. Ranking
   under multi-model contention is not golden-covered at all, since every golden is
   single-model-per-pass. That is the same blindness the coder and I independently established for
   the claim-pricing defect itself, now applying to the candidate fix.
2. (d) inherits the sensitivity Finding 32 identifies: wherever `capN` binds instead of the
   bottleneck, halving the claim halves `target` and can drop `capN` by a replica.

Neither argues against (d). It still addresses the root — a **money** quantity denominating a **GPU**
quantity — where the headroom filter addresses only the trigger, and its feasibility filter subsumes
the headroom filter outright. It argues that its neutrality must be stated contingently.

**I verified the planner's golden scan myself rather than accepting it,** since it is now load-bearing
for both candidates. At `4fb49ac6`, in `optimizer_characterization_test.go`: `MaxReplicas` appears
**zero** times, so the headroom filter's predicate can never fire in any golden; and `GPUsPerReplica`
is uniform within every role — all `1` except `:278-279` (both `2`, prefill and decode) and `:385` (a
single variant at `2`). Both claims confirmed. This is a **structural** confirmation of the
"no golden can catch this" conclusion, independent of the pool-honored argument the coder and I each
used: the golden set constructs neither an unbuyable reference variant nor an intra-role
`GPUsPerReplica` asymmetry, so neither defect has a fixture that could express it.

**Retraction count.** This is the fifth item I have withdrawn on this branch, and the second where the
error was a wrong reduction rather than an unread line. The first four were candidate C6e findings
retracted before filing; this one was **filed**, routed to the planner in
`plan__ta-anchor-claim-pricing-verdict-and-c6e-gap.md`, and had to be corrected back. The pattern
worth naming: both wrong-reduction errors came from asserting that two expressions coincide without
substituting values. Substituting the suite's own numbers would have caught this in one line, and
that is now my standing check before claiming any equivalence.

Routing note accepted: the planner's two earlier handoffs addressed me as "Type-1 owner", which is
neither my role nor within my write scope. I am the internal code reviewer for this branch; the Type 1
is Dean's. The mis-routing is also what put the phrase into shipped source at
`greedy_score_optimizer_test.go:1709`.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## `a46c7eea` — "pin the fair-share shared balance, not just the per-role clamp"

*Test-only, 1 file, +73. Landed unprompted, in direct answer to Finding 28.*

### Finding 28 — CLOSED, and closed better than I asked

The commit delivers exactly the shape Finding 28 said was missing, states the under-delivery in its
own first paragraph, and **confirms my claim by mutation** rather than by argument: replacing the
shared balance with a per-role budget makes prefill draw 6 instead of 1 and makes the spent-out
iteration hand out 3 again, while *"the two pre-existing `Optimize()` specs stay green under that same
mutant."* That last clause is the finding restated as an executed experiment. A mutation result is the
strongest available answer to "your fixture does not discriminate", and it is not something I asked
for.

I verified the arithmetic against `fairShareRolePick` at `eb12089a` rather than trusting the message.
Entitlement 6 GPUs, `decode-v` PRC 4000 at 2 GPUs/replica, `prefill-v` PRC 5000 at 1:

| draw | `spentGPUs` | `balance` | holdback | `share` | `capN` | `reserved[role]` |
|---|---|---|---|---|---|---|
| decode | 0 | 6 | −1 (prefill undrawn) | 5 | `ceil(5/2)` = **3** | `min(3×2, 5)` = **5** |
| prefill | 0 | 6 − 5 = 1 | 0 (decode drawn) | 1 | `ceil(1/1)` = **1** | `min(1, 1)` = 1 |

and after the caller commits (`targets` → `{decode-v: 4, prefill-v: 2}`): `reserved` resets on
decode's re-draw, `spentGPUs = 3×2 + 1×1 = 7`, `balance = −1`, `share = −2`,
`replicasToCover(−2, 2) = 0` via its `<= 0` guard, `firstDraw = false` so the floor does not fire,
`capN > 0` is false → `("", 0)`. Both specs are sound, and the choice to call the returned closure
directly is correctly justified: at `Optimize()` level the `replicasToCover` round-up and the pool
`min` both move the totals, so the balance is not observable there.

**One qualification on scope.** This closes the half of Finding 28 about the picker's own ledger. It
does **not** close Finding 35 — the abstention gate at `greedy_score_optimizer.go:451` is still
undiscriminated, and this fixture cannot reach it (single sat-only ballot entry, which prices both
variants). The two-role fixture I proposed for closing both was a *combined* shape; this delivers the
ledger half only. Finding 35 stands.

### Finding 37 — the entitlement is enforced against reservations, not against grants; the new fixture demonstrates a 7-GPU spend on a 6-GPU entitlement without asserting it

**Severity: MEDIUM (behavioral, and possibly intended — a Type-1 disposition question).**

Spec 1 grants decode 3 replicas at 2 GPUs/replica and prefill 1 at 1 — **7 GPUs against a 6-GPU
entitlement.** Spec 2's own comment states the commit as *"6 GPUs for decode, 1 for prefill"* and the
message says *"Entitlement 6 GPUs"*, so the overrun is present in the fixture's own numbers and named
in neither. Two mechanisms produce it, both deliberate in code comments, neither reconciled with the
word "entitlement":

**(a) The round-up clamp.** `reserved[role] = max(0, min(capN × gpusPR, share))`. Decode *consumes* 6
GPUs but is *charged* 5, because charging 6 would *"take back the room this role's successors were
just left"*. So the balance is shared in **charge** space while the pool is spent in **grant** space,
and the gap is the `replicasToCover` round-up — bounded per role by `gpusPR − 1` GPUs, and taken by
every role that rounds up.

**(b) The uncharged floor** — see Finding 38.

`replicasToCover`'s doc comment is the closest thing to a justification: *"rounding up here cannot
overcommit hardware: the caller mins this against the real pool."* That is true and is not the issue.
Hardware is safe; the **fair share between models** is what leaks, and the fair share is the thing
`fairShareRolePick` exists to enforce. A model that rounds up on every role systematically takes more
than its water-level gap, and under contention that is taken from another model.

**Why this is a disposition question and not a bug report.** Rounding up is the stated policy
(*"whether a model owed a fraction of a replica may take the one indivisible unit"*), and per-role
round-up is arguably its honest extension to P/D. What is missing is anywhere that says the
entitlement is therefore **soft by up to one replica per role**. The `W1` prose calls it *"one shared
balance"*, which reads as a hard bound. If the softness is intended, it belongs in the Type 1 and in
the dev guide; if not, the charge should be `capN × gpusPR` and the holdback made to absorb it.

**What would make this measurable:** the fixture already does. Adding one assertion —
`3×2 + 1×1 == 7 > 6` stated as an accepted overrun, or a total-spend assertion — converts a
demonstrated-but-unnamed property into a pinned one. That is a one-line addition to a spec that
already computes both numbers.

### Finding 38 — `firstDraw` is not "first draw"; it fires for every role until the caller commits, and its grant is charged nothing

**Severity: MEDIUM (documentation-vs-behavior, with a behavioral tail).**

```go
firstDraw := spentGPUs == 0
...
if firstDraw && capN < 1 {
    capN = 1   // "First draw only: it grants past the balance"
}
```

`spentGPUs` is derived from `targets` versus `committed0`, so it stays `0` for **every** role's draw
until the caller writes a grant back. The comment says *"First draw only"* and the variable is named
`firstDraw`, but the condition is "nothing committed yet" — which is a property of the *iteration*,
not of the draw. In spec 1, prefill's draw has `firstDraw == true` even though decode has already
drawn and reserved 5 GPUs.

Reachable consequence, traced (not measured): entitlement 1 GPU, the same two roles.

| draw | `balance` | `share` | `capN` | granted | `reserved` |
|---|---|---|---|---|---|
| decode | 1 | 1 − 1 = 0 | `replicasToCover(0,2)` = 0 → **floor → 1** | 1 replica = **2 GPUs** | `min(2, 0)` = **0** |
| prefill | 1 − 0 = 1 | 1 | 1 | 1 replica = 1 GPU | 1 |

**3 GPUs granted against a 1-GPU entitlement, and the first role's 2 GPUs are charged zero** — the
`min(…, share)` clamp of Finding 37(a) collapses to `0` exactly when the floor fires, because the
floor fires precisely when `share < gpusPR`. So the floor's grant is invisible to the ledger, and the
next role sees the balance undiminished. Bounded by the number of roles (2 today), so the blast radius
is small; the part worth fixing is that nothing in the code or the fixture says it happens.

I am not asserting the behavior is wrong. Granting each role its indivisible unit is defensible for a
P/D model that cannot serve with a role at zero, and the comment's *"only before the first commit is
an empty pick fatal to the whole model rather than a defer"* is a real hazard. The finding is that
**`firstDraw`'s name and comment describe a narrower rule than the code implements**, and that the
uncharged grant is the second mechanism behind Finding 37. Renaming it (`preCommit`, `nothingCommitted`)
and saying "every role, until the caller commits" would cost one line and remove the trap.

### Finding 39 — the closure's cross-iteration bound is a precondition on the caller that nothing states

**Severity: LOW (contract clarity).**

Spec 2 is named *"does not hand back the whole entitlement on the next iteration"* and passes because
the test **updates `targets`** between iterations. The protection is `spentGPUs`, computed from
`targets − committed0`. If a caller re-draws without committing, `reserved` is reset by the
drawn-already branch, `spentGPUs` stays `0`, and the role is sized against the **full** entitlement
again — the exact failure the spec is named for.

So the closure is correct only for callers that write grants into `targets` before the next draw.
`allocateForModel`/`allocateForModelPaired` do, so there is no live bug. But the closure is a
returned function with a stateful ledger and an unstated precondition, and spec 2 pins the
happy-path caller rather than the contract. One sentence on `fairShareRolePick`'s doc comment —
"grants must be reflected in `targets` before the next draw; the ledger measures spend from them" —
closes it. Cheaper than a spec.

### Finding 40 — two new §4a leaks, introduced by this commit

**Severity: LOW individually; noted because the very next commit claims the sweep is finished.**

```
greedy_score_optimizer_test.go:1557:  // §C6e asks for the other shape — roles that would EACH individually fit
greedy_score_optimizer_test.go:1576:  // would mask the balance, which is the masking §C6e names.
```

These are the **core** §4a class — a plans-branch *section identifier*, not merely a path. `§C6e`
resolves for nobody reading merged code, and unlike `W4` or `N7` (which at least read as local
labels defined in the surrounding prose) it is explicitly a pointer into
`ta-anchor-dynamic-refresh-plan.md`. Both are one-clause fixes: *"the fair-share entitlement's own
commit asks for the other shape"* → the plan section named descriptively, or simply dropped, since
both sentences read fine without the citation.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## `eb12089a` — the last `Type-1 owner` in test source, and a completeness claim that does not hold

*Comment-only, 1 file, +4/−4. Fixes exactly the site I flagged in the `4fb49ac6` note above.*

The fix itself is right and its reasoning is better than mine. I flagged `Type-1 owner` as a §4a
violation — unresolvable to a reader of merged code. The commit adds a second, independent ground:
*"it is factually wrong — the role does not own that question and the person it pointed at has
declined the label"*, and concludes that *"naming the question as open, without routing it, says
everything a reader of a dormant spec needs and nothing that can go stale."* Removing the routing
rather than correcting it is the durable fix; a corrected name would have rotted on the next role
change.

### Finding 41 — "the last of the four sites" is false at its own tip; two live leaks remain, one of which I wrongly reported as fixed

**Severity: LOW (accuracy of a completeness claim), but it is the claim that would stop the next sweep.**

The message says this commit *"Completes the §4a hygiene pass over what my own commits shipped … the
last of the four sites."* At `eb12089a` that is not the case. Verified by grep at that tip:

1. **`§C6e` ×2** — `greedy_score_optimizer_test.go:1557,:1576`, introduced by `a46c7eea`, the
   immediately preceding commit. Finding 40. The sweep was scoped to the four sites known when it was
   planned and did not re-run against the tip it landed on.
2. **`Type-1 owner` in the dev guide** — `docs/developer-guide/multi-analyzer-pipeline.md:803`:
   *"The claim-pricing question is open with the Type-1 owner"*. Still live, and it ships in the PR
   diff as Type 4 reference material.

**Correction to my own `4fb49ac6` note above: I wrote "The dev-guide occurrence is also gone." It was
never removed.** I verified `Type-1` occurrences in that file across all six revisions of the C6f
sequence — `a679f2ad`, `2a0db749`, `4fb49ac6`, `537b0153`, `a46c7eea`, `eb12089a` — and the count is
**1 at every single one**. `4fb49ac6` did touch the dev guide (+9/−2, the `mean`/`allocationMean`
fix) which is presumably why I read the token as swept with it, but the sentence is untouched. This is
my third attribution or fact error in this segment, all three in the same direction: reporting
something as resolved on the strength of an adjacent change rather than checking the artifact.
**Standing check added, alongside the substitute-the-numbers one from the option-(d) retraction: never
report a token, path or leak as removed without grepping the tip.**

Both remaining sites are one-clause fixes and both are in files C9 will touch anyway. The reason to
say so now rather than let C9 absorb them is that a commit message asserting the class is closed is
what makes the next reader skip the grep — which is precisely how I got the dev-guide line wrong.

### Running §4a state at `eb12089a`

Self-introduced by PR-2 and still live: **`§C6e` ×2** (test comments) + **`Type-1 owner` ×1**
(dev guide) = **3**. Plans-branch *paths* in shipped source: **0** (Finding 33 stayed fixed).
`Type-1 owner` in shipped `.go`: **0** (this commit). Pre-existing at base and out of PR-2's scope:
`docs/developer-guide/throughput-analyzer.md:698`, tracked in `governance-follow-ups.md`.

The known bulk C9 must strip is unchanged and unaffected by any of this: `W1`/`W4`, `N2`/`N3`/`N7`/`N8`,
`T1.3`/`T1.4`, `PR-2`, across `greedy_score_optimizer.go`, `analyzer_helpers.go`, `rescale.go`, both
test files and the dev guide.

**Reword count: 16.** `a46c7eea` and `eb12089a` both carry plans-branch tokens in their messages
(`§4a`, `C6e`), so the window Dean has not yet ruled on has grown from 13 commits to 16 — still free
while the branch is unpushed, still a live-PR history rewrite once PR-2 opens.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## C11 pre-registration — written against the frozen Type 1, before the diff exists

*Recorded at coder tip `eb12089a` with C11 uncommitted (`analyzer_helpers.go`,
`cost_aware_optimizer.go`, `greedy_score_optimizer.go`, `rescale.go` modified). Pre-registering makes
these falsifiable: if the diff refutes a prediction below, that is recorded as a miss, not quietly
dropped. The Finding 27 pre-review is the precedent, and the option-(d) retraction is why the habit
exists.*

Reviewed against the **frozen Type 1** decision block `(D-a)`/`(D-b)`, not the derived Type 3 — the
mechanism and cap were decided in the Type 1 precisely so they would not be coder latitude, so that is
the text C11 answers to. Line numbers in `(D-a)`/`(D-b)` are stated as of `d9f3b97e`; C6a–C6f moved all
three grant sites, so every one is re-derived at `eb12089a` below.

### Already verified — the `(D-a)` "rides the existing gates" claim holds

`(D-a)` rejects a separate *admissible* predicate on the grounds that it would need threading through
**six** independent anchor-`PRC <= 0` gates. I counted them at the tip. Exactly six, and they are the
same six:

| `(D-a)` says (`@d9f3b97e`) | at `eb12089a` | function |
|---|---|---|
| `cost_aware_optimizer.go:95` | `:100` | `costGreedyRolePick` |
| `cost_aware_optimizer.go:125` | `:135` | (second cost path) |
| `cost_aware_optimizer.go:239` | `:284` | (third cost path) |
| `greedy_score_optimizer.go:411` | `:686` | `fairShareRolePick` (fn now at `:621`) |
| `rescale.go:443` | `:446` | `fillRole` |
| `rescale.go:573` | `:579` | `roleDemandGPUs` neighbourhood |

No seventh gate has appeared, so no site admits the sentinel unaudited. The five `prc <= 0` gates in
`analyzer_helpers.go` and the two in the optimizers are **ballot**-side (`prcForVariant`), so the
sentinel never reaches them — which is `(D-a)`'s `applyAllocation` argument, and it checks out.

C6f has also already pre-wired the `fairShareRolePick` gate comment (`:683-685`): *"The gate asks
whether the variant has a price, not whether some number is zero — a variant admitted at a sentinel
price is priced, and passes."* Correct in substance and it is what makes the sentinel work; it is also
the forward-reference already on the ledger as Finding 36.

### Finding 42 (pre-registered, MEDIUM-to-HIGH — a defect in the *governing text*, whichever way the diff goes) — `(D-b)`'s "fold into the existing `MaxReplicas` machinery" leaves the sentinel unbounded whenever `MaxReplicas` is nil, at all three grant sites

`(D-b)` instructs, per site: *"fold into that same `headroom` computation, **including its
`headroom <= 0 → continue`**"* · *"same clamp, same skip"* · *"add the ceiling to that same `break`
condition."* At all three sites that machinery sits **behind a nil-guard**, and the ceiling folded into
it inherits the guard:

**1. `costGreedyRolePick` — `cost_aware_optimizer.go:104-111`**
```go
if state.MaxReplicas != nil && *state.MaxReplicas > 0 {
    headroom := *state.MaxReplicas - targets[vc.VariantName]
    if headroom <= 0 { continue }
    return vc.VariantName, headroom
}
return vc.VariantName, math.MaxInt        // ← outside the block the instruction names
```
`(D-b)` cites *"`cap` = `MaxReplicas − targets[v]`, else `MaxInt`"*, so it **saw** the `MaxInt` branch —
and then located the fix in the other one.

**2. `fairShareRolePick` — `greedy_score_optimizer.go:711-717`** — same nil-guard around the only clamp
and the only skip.

**3. `fillRole` — `rescale.go:454-460`**
```go
for wantGPUs-spent >= g {
    if st.MaxReplicas != nil && *st.MaxReplicas > 0 && targets[...] >= *st.MaxReplicas { break }
    targets[vc.VariantName]++
```
The worst of the three: a single `&&` chain rooted on `!= nil`, and the loop is bounded by nothing else
but `wantGPUs`. Adding a conjunct to that chain reproduces exactly the unboundedness `(D-b)` opens by
naming — *"`targets[v]++` in a loop bounded only by `MaxReplicas`"*.

**Why this is reachable rather than theoretical.** `MaxReplicas` is `*int`
(`internal/domain/saturation_analyzer.go:325`), the guard treats nil and `0` alike as *unbounded*, and
the sentinel's target population is **never-seen, zero-replica variants** — the population least likely
to carry a tuned ceiling. So the escape is not an edge case of the fix; it is the fix's default case.
Severity is then `(D-b)`'s own worked warning, unmitigated: *"a single never-seen variant can absorb the
whole budget one request-per-second at a time"* — at `PRC = 1`, `fillRole` buys `wantGPUs / gpusPR`
replicas of a variant nobody has measured.

**This is a Type-1 amendment either way, which is why it is worth filing before the diff.**
- If C11 follows `(D-b)` literally → a real code defect, and the instruction caused it.
- If C11 hoists the ceiling out of the nil-guard → correct code that **contradicts its governing text**,
  and `(D-b)`'s per-site table is then wrong on all three rows.

Only the second outcome is good code, and it still leaves the Type 1 needing a correction. The fix in
both cases is the same shape: the ceiling is an **unconditional** clamp on the sentinel variant's
target, applied *whether or not* `MaxReplicas` is set — i.e. `cap = min(cap, 1 - targets[v])` with its
own `<= 0 → continue`/`break`, sibling to the `MaxReplicas` clamp rather than nested inside it. Note
`1 - targets[v]`, not `1`: `(D-b)` is explicit that the bound is on the **target**, *"not on a single
iteration, so a repeated allocation loop cannot buy a second replica by going round again"* — a literal
`cap = min(cap, 1)` satisfies the sentence and not the requirement.

**Routing:** planner, as a `(D-b)` amendment. Not a coder judgment call — `(D-b)` exists because Dean
ruled *"don't leave design decsions to coder"*, so the coder deviating from it silently is the wrong
resolution even when the deviation is correct.

### Finding 43 (pre-registered, LOW-to-MEDIUM — an ordering constraint nothing states) — the one-replica ceiling is only effective if it is applied *after* C6e's `firstDraw` floor

In `fairShareRolePick` at `eb12089a` the sequence is:

```
:701   capN := replicasToCover(share, gpusPR)
:702   if firstDraw && capN < 1 { capN = 1 }      ← floor, raises to 1
:710   capN = min(capN, gpusAvail/gpusPR)         ← pool clamp
:711   if state.MaxReplicas != nil && ... {  capN = min(capN, headroom) }   ← headroom clamp
:718   if capN > 0 { ... return vc.VariantName, capN }
```

The floor **raises** `capN` past every bound computed before it. So a ceiling placed with the
`MaxReplicas` clamp is safe, and a ceiling placed next to `replicasToCover` — which is where a coder
reading *"cap the sentinel at one replica"* might naturally put it, since that is where replica counts
are first computed — is **silently defeated by the next line**: ceiling drives `capN` to `0`, the floor
lifts it back to `1`, and a replica the ceiling forbade is granted.

So `(D-b)`'s correctness at this site rests on the *layout* of a function C6e rewrote after `(D-b)` was
frozen, and neither the Type 1 nor the code says so. One comment at the floor — "clamps below this line
are authoritative; this floor deliberately precedes them" — would make the constraint explicit and
survive the next edit to the function.

**Bounded, and one part I have not established.** Finding 38 showed `firstDraw` stays true for every
role until the caller commits, so a mis-ordered ceiling would be defeated once per role rather than
once per model. Within a single closure the floor cannot fire on a *second* grant of the same variant,
because `spentGPUs` goes positive after the caller writes the first grant back — so the "buy a second
replica by going round again" hazard `(D-b)` names is not reachable *this* way. The case I have **not**
checked is two roles resolving to the same sentinel variant in one pre-commit window (a variant serving
both roles, or `role == "both"`), where both draws would see `firstDraw == true`. I am not asserting it
is reachable; I am recording that I did not test it and that it is the one route by which a mis-ordered
ceiling would breach the *target* bound rather than merely the per-role one.

### Resolved before the diff — the `ReplicaCount == 0` guard is sufficient on its own, and no `[sat]`-only golden may move

I had this on the checklist as a risk: if C11's guard is only `ReplicaCount == 0` with no
binder-identity test, does a saturation config that fails to seed then admit a sentinel — making C11 a
`[sat]`-only behaviour change, moving the saturation-only goldens, and contradicting `(D-a)`'s own
**TA-CREATED** classification? **Checked at `eb12089a`: no. The branch is structurally unreachable
under `[sat]`-only, and a bare `ReplicaCount == 0` guard is correct.** Recording it so I do not raise it
as a defect when the diff lands.

The sentinel site is the merge miss at `analyzer_helpers.go:212-221` — `if b, ok := bByName[a.VariantName]; ok`,
whose `else` today is a **comment only** (`:218-221`), PRC left at its zero value. So C11 must add a real
branch there. Reachability of that branch is decided by two selections above it:

- **`satNR` is located by name, not by vote** (`:138-144`) — *"It may be present even when it does not
  vote"*.
- **`aCarrier = satNR` whenever `satNR != nil`** (`:176-178`), and **`binding = satNR`** iff saturation is
  `Enabled && Live && Informative` (`:149-151`).

Therefore under `[sat]`-only, exactly two cases, and neither reaches the branch:

| `[sat]`-only case | outcome |
|---|---|
| saturation votes | `binding == aCarrier == satNR` — **the same pointer**, so `bByName` is built from the identical slice the merge loop iterates ⇒ `ok` is always true |
| saturation does not vote | the `default` arm finds no non-saturation entry ⇒ `binding == nil` ⇒ `:168-170` returns **nil, no anchor at all** |

This is a cleaner argument than the Type 1's own (*"saturation always binds and always seeds"*, which
would depend on the analytic ladder never failing): the lookup cannot miss because the two lists are the
same object, whatever saturation computed. Same conclusion, stronger ground. It also means `(D-a)`'s
*"when the binder is not saturation and …"* phrasing describes a condition that is **automatically
satisfied**, not one that has to be tested — so shipping only the `ReplicaCount == 0` guard is not a gap.

**The falsifiable consequence, worth more than the checklist item it replaces:** C11's merge-site change
cannot move any `[sat]`-only golden. So **if a `[sat]`-only golden moves under C11, the cause is the cap
at the three grant sites failing to key on the sentinel tag** — a general clamp rather than a tagged one.
That is precisely the property `(D-a)` says the `Reason` tag exists for (*"it is what the cap keys on"*),
which makes the `[sat]`-only goldens a direct test of it. Pre-registered accordingly: **goldens move ⇒
the cap is untagged**, not "goldens move ⇒ rebaseline".

One premise I have **not** verified and am not endorsing: `(D-a)`'s claim that in a *TA-binding* config
`ReplicaCount == 0` plus a binder miss is *precisely* "never seen", on the grounds that TA's own
scale-from-zero complement already covers previously-live zero-replica variants from persisted supply. If
that complement has a hole, the sentinel would also fire for a variant that *has* been measured and is
merely idle — where `(D-a)` itself says abstain is right. Flagged as an unchecked dependency, not a
finding.

### Rest of the C11 checklist, to verify against the diff

Mechanism `(D-a)`: sentinel written at the merge-miss `else` (`analyzer_helpers.go:218-221`) only ·
`Reason` set to a dedicated constant
alongside the PRC, moving as a set at both write sites (`:207-212`, `refreshAnchorSizing:569-572`) ·
the refresh's `continue` branches (`:562`, `:566`) must **leave the sentinel standing**.

Cap `(D-b)`: all three sites, target-scoped, each with its skip/break half — the `→ continue` is
load-bearing, since returning `cap = 0` drives `n = 0 → utilByRole = 0 → deltaUtil = 0 → break` and
kills the model's whole allocation loop instead of moving to the next variant · **not** implemented by
leaning on `allocateForModelPaired`'s `k` inheritance, which `(D-b)` calls *"a consequence, not the
mechanism"* · no changes at the five sites `(D-b)` clears (`applyAllocation`, `roleDemandGPUs`, the
scale-down/reclaim paths, `TotalCapacity`) — a change there is scope creep to flag, not to praise.

Carried in from the ledger: Finding 16's `PRC <= 0` predicate; Finding 27's ranking inversion — noting
that `(D-a)`'s ranking argument (*"because measured PRCs are ≫ 1, a never-seen variant ranks behind
every measured option"*) is the claim the other session's `plan__ta-anchor-c11-ranking-claim-correction`
already corrects, since `Cost = 0` collapses `Cost / PRC` to `0` and sorts the sentinel **first**;
whether C11 inherits that hole is a diff question. And §4a: re-sweep, with the `§C6e` ×2 and dev-guide
`Type-1 owner` of Finding 41 still outstanding going in.

---

## While C11 was in flight — the abstain-gate audit re-counted, and C6f's scoping verified at `eb12089a`

Three checks run against the tip while the C11 diff was being written. **All three came back in the
coder's favour, and two of them are corrections to me, not to it.** Recording them because a review that
only accumulates findings is not measuring anything.

### The gate count is 13, not 11 — and every one of them is commented

The C6f handoff states *"the eleven `prc <= 0` / `PerReplicaCapacity <= 0` gates carry
abstain-as-a-pricing-rule comments."* At `eb12089a` there are **thirteen**, in the 6 + 7 split my earlier
`(D-a)` audit derived:

| side | gates |
|---|---|
| anchor-side `vc.PerReplicaCapacity <= 0` (6) | `cost_aware_optimizer.go:100`, `:135`, `:284` · `greedy_score_optimizer.go:686` · `rescale.go:446`, `:579` |
| ballot-side `prc <= 0` (7) | `analyzer_helpers.go:77`, `:447`, `:478`, `:522`, `:768` · `cost_aware_optimizer.go:206` · `greedy_score_optimizer.go:368` |

**All 13 carry the comment.** So "eleven" undercounts the coder's own work; it is not a gap, and no gate
is unaudited.

**Why this matters for C11 rather than being bookkeeping:** the comments are uniformly worded as a rule
about *pricing*, not about zero — *"cannot price v, so it abstains"*. A `Reason`-tagged `PRC = 1` sentinel
is priced, so it passes all thirteen by the rule as written, with nothing to reword. `(D-a)`'s premise
that the sentinel meets only audited gates is now verified across **13** sites rather than the 6 I had
checked, and the "is there a fourteenth gate that admits it unaudited" risk is closed by enumeration.

### Method: a near-miss false positive, and a third standing check

My first pass scanned four lines *above* each gate and reported **6 of 13 as uncommented**. Every one of
those six has the comment on the first line *inside* the block. Had I written that up, I would have
manufactured a hole in the coder's audit trail — the same failure shape as the option-(d) retraction and
the never-removed dev-guide correction, arriving from a new direction: not a stale fact, but a
measurement whose instrument was too narrow to see the thing it was looking for.

**Third standing check, alongside the other two:** *before calling an artifact missing, confirm the
window was wide enough to contain it.* The existing pair — substitute the numbers before endorsing a
formula; never report a token as removed without grepping the tip — both guard against asserting a
change that did not happen. This one guards the converse: asserting an absence that is only an absence
of evidence.

The same discipline paid twice more in the same pass. The dev-guide hit
`throughput-analyzer.md:698` (*"Design: `plans/planning/TA-Plan.md`, `plans/planning/TA-PR4-plan.md`"*) is
a real §4a violation — a shipped Type 4 doc citing plans-branch documents by path — but `git grep -c` at
`eb12089a`, `075a208e` **and** `upstream/main` all return 1, so it is **pre-existing on `main` and not
PR-2's**. It belongs in the pre-existing main-side §4a bucket in `governance-follow-ups.md`, and
attributing it here would have been a false charge against this branch. Worth noting as a *class* my
sweeps had been missing, though: they were token-based (`W1`, `§C6e`, `N8`), and a plans-branch **path**
is the other half of the rule. `internal/config/saturation_scaling.go:45`'s `docs/plans/engine/…` is an
in-repo path, not a plans-branch one — not a violation.

### C6f's scoping is honest, and the pointer strip did not cost the reader the caveat

The concern worth having about `4fb49ac6` (*"drop plans-branch paths from shipped comments"*) is that
stripping the pointer to the handoff could take the caveat with it, leaving a fixture that reads as
*"`W4` is tested"*. **It did not.** At the tip the Context comment (`greedy_score_optimizer_test.go:1660-1677`)
carries the counterexample in full — the measured `[sat] → 4` vs `[sat,TA] → 10`, the fixture that
produces it, the statement that the inflation *"is upstream of W4 and reachable with ONE analyzer"*, and
the flat sentence **"the fixtures below therefore cover the aligned regime deliberately, and W4 is NOT
fully gated by them."** The second `It()` names the regime boundary itself and pre-empts the misreading:
*"Make the two GPUsPerReplica values differ and this equality fails; that is the open claim-pricing
question, not a defect in this fixture."* Numbers and warning survived; only the plans-branch filename
went. That is the right outcome of the strip, and it is what Finding 35 asked for.

### Credit where it is due — the dormant spec is the correct shape for an undecided defect

`537b0153` lands the two-model redistribution probe as a **`PIt`** asserting the *honest* split
(`pricey-x` 3, `y-v` 3, `cheap-x` 1 — *"Y is a bystander and must not be starved"*) rather than a
characterization fixture pinning today's 4/2. Its header says why: a characterization fixture *"would
freeze the distortion and make the eventual fix look like a regression; this goes green when a fix
lands"*, and *"if the disposition is that today's pricing is correct as designed, delete this spec — it
encodes a premise, not a decision."*

That is the right handling of a measured defect whose disposition is not yet decided, and it is not what
the plan asked for. It also **closes the coverage question I was going to route**: the coder's offer
(*"say the word if you want [`zz_c6f_probe_test.go`] kept as a real fixture"*) is already satisfied — the
probe is in-tree, pending, asserting the fix. No recommendation to send.

**What remains open here is a Type-1 disposition, not code and not coverage:** whether a claim may be
priced through a variant the picker provably cannot buy. That question is already routed and measured —
`review__ta-anchor-claim-inflation-measured-single-analyzer.md` establishes it redistributes a GPU
between models with **one** analyzer and no `W4` escape, so `W4`'s abstention escape *reveals* the
inflation rather than causing it. Its corollary matters for whichever fix lands: barring the abstainer
from the vote would not touch the mispricing, because the mispricing is in reference *selection*
(`PerReplicaCapacity > 0` with no headroom test), upstream of who votes.

### §4a commit-message exposure, measured exactly — 15 of 17, and one embeds handoff filenames

I had been carrying "16 commits to reword". **Measured at `eb12089a` against base `075a208e`: 17 commits,
of which 15 carry a plans-branch token in the message.** Only `eb12089a` and `34b18bc5` are clean. My
figure was wrong in both directions — it overstated the reword count and understated the total.

- **6 subjects** carry tokens: `a679f2ad` (`C6f`, `W4`), `784c2b5c` (`C6e`), `330fcd26` (`C6d`),
  `d9f3b97e` (`C6b`), `8eb6ee2d` (`C6a`), `680bebdb` (`N2`).
- **15 bodies** carry them — `W1`/`W4`, `N2`/`N3`/`N7`/`N8`, `U2`, `C1`–`C11`, `T1.x`, `PR-1`/`PR-2`,
  `Type-1 owner`.
- **`a679f2ad` is the worst single case and a class the earlier counts missed:** its body cites two
  plans-branch documents *by filename* — `plan__ta-anchor-c6f-w4-no-spend-is-false.md` and
  `review__ta-anchor-claim-inflation-measured-single-analyzer.md`. A token like `W4` is opaque to a
  `main` reader; a handoff filename is worse, because it reads as a resolvable reference and is not one.
  This is the same leak class as the pre-existing dev-guide `plans/planning/…` path above, arriving in
  permanent code-side history rather than a doc.

The arithmetic on the window is unchanged in shape and now exact: **15 messages to reword while the branch
is unpushed and needs a force-push anyway, against 17-plus once C11/C10/C9 land and the PR is open, at
which point it is a live-PR history rewrite.** *"Not worth it"* remains a legitimate answer — but it
should be answered against 15, not my previous guess.

[Back to plan](ta-anchor-dynamic-refresh-plan.md)

---

## `b6bb525c` — C11: `(D-b)` lands, `(D-a)` is deferred. Both pre-registered findings hit.

Reviewed at tip `b6bb525c` *"pipeline: bound a from-zero-admitted variant at the grant sites (C11
D-b)"* — 6 files, +279/−14. This is the commit Findings 42 and 43 were pre-registered against, before
the diff existed. **Both are hits**, and the commit additionally defers half of a frozen Type-1
decision, which is the substantive review question.

### Finding 42 — CONFIRMED and resolved. The prediction held in the "deviated" branch.

Pre-registration: `(D-b)`'s instruction to fold the ceiling into each site's existing headroom
computation leaves the sentinel unbounded whenever `MaxReplicas` is nil, at all three grant sites —
and it is a Type-1 amendment **either way** (followed literally → a code defect the instruction
caused; deviated from → correct code contradicting all three rows of `(D-b)`'s table).

The coder found the same escape independently and took the deviate branch, stating it plainly in the
message: at all three sites the headroom computation sits behind a nil-guard whose fall-through treats
unset as unbounded — `costGreedyRolePick` returns `math.MaxInt`, `fillRole`'s loop is bounded by
nothing else, `fairShareRolePick` applies no clamp. Its framing is sharper than mine was: *"the
population least likely to carry a tuned ceiling is exactly the never-measured one the ceiling is
for."*

The fix is one helper, `analyzer_helpers.go:111-120`, merging configured `MaxReplicas` with the
admission ceiling and reporting the tighter, with all three sites routed through it. I checked the
"nothing else moves" claim rather than taking it:

| site | before | after | untagged behaviour |
|---|---|---|---|
| `cost_aware_optimizer.go:104` | `if MaxReplicas != nil && *MaxReplicas > 0 { headroom := *MaxReplicas - targets[v] …` | `if maxTarget, bounded := maxTargetReplicas(vc, state); bounded { headroom := maxTarget - targets[v] …` | identical |
| `greedy_score_optimizer.go:718` | same shape | same shape | identical |
| `rescale.go:452-458` | `if st.MaxReplicas != nil && *st.MaxReplicas > 0 && targets[v] >= *st.MaxReplicas { break }` | `if bounded && targets[v] >= maxTarget { break }`, hoisted above the loop | identical |

`bounded` reproduces `MaxReplicas != nil && *MaxReplicas > 0` exactly, and `maxTarget` is
`*MaxReplicas`, so the claim is accurate at all three. Note this **faithfully preserves a pre-existing
oddity**: an explicit `MaxReplicas == 0` is treated as *unbounded*, not as "zero replicas allowed".
That is not C11's doing and must not be charged to it — but C11 does centralize it into one place,
which is the first time it has been fixable in one edit. Boundary cases are clean: tagged with
`MaxReplicas == 0` → capped at 1 (the safe direction); tagged with `MaxReplicas == 1` → `1 < 1` false,
bound stays 1 from the first clause — no off-by-one.

Two things I did not predict and credit:

- **"Skip an exhausted ceiling, never return a cap of 0."** A returned 0 makes the caller compute
  `deltaUtil == 0` and break the whole model's allocation loop, so a bounded-out variant would take
  every variant queued behind it down with it. All three sites `continue`/`break` instead. The Type 1
  does not state this, and the literal reading of `(D-b)` ("cap the target at one") invites exactly
  the 0-returning shape. This is a correctness insight, not a style choice.
- **The `fillRole` hoist** (`rescale.go:454-458`) — the bound does not depend on the loop, so
  computing it once is both correct and a micro-improvement over the previous per-iteration nil-deref.
  Comment states the target-not-iteration semantics: *"an allocator that comes round again finds
  `targets[v]` already at the bound and buys nothing more."*

**The amendment I predicted is now owed.** `(D-b)`'s three-row table in the frozen Type 1 describes
folding the ceiling into each site's `MaxReplicas` branch. The shipped code deliberately does not, for
a stated and correct reason. The Type 1 is wrong in a way the code is right about — that is the
Type-1 owner's edit, not the coder's, and the coder correctly did not touch the design doc.

### Finding 43 — CONFIRMED and resolved, including the documentation I asked for.

Pre-registration: the ceiling is only effective if applied **after** C6e's `firstDraw` floor, and
`(D-b)`'s correctness rests on undocumented function layout — a later reorder would silently defeat it.

`greedy_score_optimizer.go:701-724` has the ordering right: `capN := replicasToCover(share, gpusPR)`
→ `firstDraw` floor raises it to 1 at `:711` → `capN = min(capN, gpusAvail/gpusPR)` at `:713` → the
admission/`MaxReplicas` clamp at `:718-724`, ending in `capN = min(capN, headroom)`. And the ordering
constraint is now stated **at the floor**, which is where a future reorderer will read it:

> This raises capN, so every bound must be applied after it, not before. The two clamps below rely on
> that ordering.

That is precisely the remediation the finding asked for. The site-specific skip rationale is also
recorded at `:714-717` (the `capN > 0` guard below would return an empty pick and abandon the role).

### Finding 44 — `(D-a)` is not implementable as specified. The deferral is correct, and the defect is the Type 1's.

`(D-a)` — the anchor-side write that would tag a variant for the ceiling — is **DEFERRED**, recorded
both in the commit message and in shipped code at `analyzer_helpers.go:77` (*"DEFERRED: nothing writes
this tag yet"*). The coder's reason: an anchor-only sentinel makes a variant **selectable without
making it sizable**. Selection reads the anchor; the replica count comes from the ballot via
`votesFromPickerState → combineVotes → roleBottleneckReplicas`, which abstains for a variant no voting
entry prices and yields 0 → `n = min(0, cap) = 0` → `deltaUtil == 0` → `allocateForModelPaired`
breaks, costing the model every variant behind the admitted one. Verified by mutation: with the
sentinel written the measured variant stays put; with it disabled the same fixture scales.

I can close this argument harder than the coder does, and the conclusion goes further than "risky".

My own pre-registered reachability work (§ *C11 pre-registration*) established that the merge's
sentinel branch — `analyzer_helpers.go:212`'s `else` — is **unreachable whenever saturation binds**,
because `binding == aCarrier == satNR` is the same pointer (`:211/:213` and the carrier assignment),
so `bByName` is built from the identical slice the merge loop iterates and the lookup always hits. The
branch is therefore reachable in exactly one domain: **saturation present but not binding**, with some
other analyzer binding and omitting the variant. Enumerate that domain against the vote gate
(`Enabled && Live`, `analyzer_helpers.go:318`):

| sub-case | does saturation vote? | is the admitted variant priced by any voter? |
|---|---|---|
| sat `!Enabled` | no | no → `roleBottleneckReplicas` abstains → 0 |
| sat `Enabled && !Live` | no | no → abstains → 0 |
| sat `Enabled && Live && !Informative` | yes | its entries are no-data/error, PRC 0 → the ballot-side `prc <= 0` gates skip → 0 |

**In every reachable sub-case the admitted variant is unsizable.** So `(D-a)` as written cannot
produce a scaled-from-zero replica in *any* configuration — not "usually", not "unless tuned". The
coder's mutation result is not a corner case it happened to find; it is the whole domain. That makes
the `N8` question (may the sentinel enter the voting set?) a **prerequisite for `(D-a)`, not an
optional refinement**, and it means `(D-a)` shipped as specified would have been a pure regression:
it removes allocations and adds none.

Verdict: **the deviation is sound and I endorse it.** The process question is real and I am recording
it rather than resolving it — `FZ-admission` was decided *in* the frozen Type 1 specifically so it
would not be coder latitude (*"don't leave design decsions to coder"*), and half of it has now been
deferred coder-side. But the coder did the three things that make that defensible: disclosed it in the
commit message, disclosed it in shipped code at the constant, and routed the design question as a
handoff instead of deciding it. The alternative — implementing a known regression because the design
said so — would have been worse. **The owed action is a Type-1 amendment, and it is not the coder's.**

Convergence note, with credit where it is due: the coder had *already* documented the sentinel's
reachable domain at `analyzer_helpers.go:184-192` before I re-derived it here. I am not claiming
priority on the domain; what is new above is the exhaustive sub-case table showing the domain and the
sizing gap are the *same* set.

Also confirmed independently by this commit: **Finding 27**'s ranking inversion. The message corrects
`(D-b)`'s premise that the admitted variant would sort last — `PRC = 1` degenerates cost efficiency to
`Cost`, but a never-measured variant's `Cost` arrives as 0 from the same zero-replica lookup, so the
ratio is `0/1` and it sorts **first**. That matches the other session's
`plan__ta-anchor-c11-ranking-claim-correction.md` conclusion, reached separately. The code's response
is right: tests state the ranking the code actually has, and the ceiling is documented as the *only*
guard rather than one of several.

### Finding 45 — MINOR (doc precision). The stated reason for refusing the saturation fallback is too strong.

`analyzer_helpers.go:184-192` justifies not falling back to saturation's own sizing for an omitted
variant:

> A binder omits a variant only when the binder itself is enabled-but-not-binding — `Enabled &&
> !(Live && Informative)` — which is precisely the condition under which its own sizing is
> untrustworthy (stale or no-data).

The **conclusion is correct** — a lookup miss can only occur when saturation is not the binder, and in
all three sub-cases tabulated above saturation has nothing usable to borrow. But the premise as
written is false: `ResultIsInformative` is an *any-variant* predicate (`:57-61` returns true on the
first informative entry), so a perfectly healthy binder can be `Enabled && Live && Informative` in
aggregate and still price nothing for one specific variant — which is the *expected* shape for a
never-measured from-zero variant under a throughput binder. A binder omitting a variant does not imply
the binder is unhealthy.

Low severity because nothing downstream depends on it, but worth fixing because the false premise
licenses a bad future inference — "the binder is healthy here, so the fallback is safe" — which the
correct reasoning does not support. C9 is the natural host; the fix is to justify the refusal on the
carrier/binder split and the metric-scale-mixing argument (both already present at `:189-192`) and
drop the health claim.

### Finding 46 — `(D-b)` ships as an inactive guard. Disclosed, but it needs three follow-through items.

With `(D-a)` deferred, **nothing in non-test code writes `ReasonFromZeroAdmission`** — I grepped the
tip: the constant appears only in its own declaration and doc comment, the `maxTargetReplicas` read,
and two cross-references. The tag is constructed only by tests (`analyzer_helpers_test.go` ×1,
`cost_aware_optimizer_test.go` ×2). So the second clause of `maxTargetReplicas` is unreachable in the
shipped binary, and C11's entire behavioural contribution to production is *nil* — by design, and
stated as such at `:77`.

That is the honest way to land half a decision, and I am not flagging it as a defect. It does carry
three follow-through items:

1. **C9's dev guide must not describe the ceiling as an active guard.** The code says "nothing writes
   this tag yet"; prose that says "from-zero variants are capped at one replica" would be false on
   the merged tree. Added to my C9 watch list.
2. **The deferral needs a planner-side home.** Per the project's deferral-documentation rule, a
   DEFERRED removal is captured by the planner in the Type 1/Type 3 and in CURRENT.md § Issues to
   Open. The coder has done its half (classification + reason + handoff); the capture is owed.
3. **Export scope is fine — checked, not assumed.** `ReasonFromZeroAdmission` is exported with nothing
   outside the package using it, which would normally be a finding; but `ReasonNoData` and
   `ReasonError` in the same family are also exported (`:40-47`), so this is consistency, not leakage.
   No action.

### §4a — C11 adds to the debt C9 is meant to clear

Shipped-code token count moves **46 → 53** (`internal/**` + `docs/**`). The added lines contain nine
occurrences: `C11` ×4, `N8` ×3, `Type-1 owner` ×1, `D-b` ×1 — including two in the new constant's doc
block (`:87-88`, *"an `N8` question, so it is the Type-1 owner's"*) and one at `:185`. These are
exactly the class C9 is scheduled to strip, so C11 has grown C9's job while doing good work elsewhere.
Not a blocker — C9 has not run yet — but the trend is now three commits deep and worth naming: the
prose that makes these commits reviewable is written in plans-branch vocabulary, and every such
sentence is a C9 edit.

Commit-message reword window: `b6bb525c`'s message carries `C11`, `D-a`, `D-b`, `N8` and
`Type-1 owner`, taking the count to **17 of 19 commits** needing a reword. Still free while the branch
is unpushed; a live-PR history rewrite once PR-2 opens.

### Gates

Not independently verified — I do not build or test in the coder's worktree. The status file predates
this commit (`last_update: 2026-08-07T21:00:00Z`, `current_step` still reads C6d), so gate results for
`b6bb525c` are unrecorded. Not a finding against the code; noted so a later reader does not mistake
this section for a gate sign-off.

### Finding 47 — of the two sites a tagged variant can actually reach, the one the code names as the worst case is the one with no test, and its omission is the only one left undisclosed

Not predicted. Found by auditing the 182 new test lines rather than the 97 new code lines — Finding 46
established that with `(D-a)` deferred the tests are the *only* thing exercising the ceiling anywhere,
which makes their discrimination load-bearing rather than supporting.

`(D-b)` clamps three grant sites. Their reachability for a tagged variant — the question that decides
what a test is worth at each — is not uniform:

| site | tagged variant reaches it? | why | C11 test |
|---|---|---|---|
| `costGreedyRolePick` | **yes** | no accelerator gate before the clamp | **3 behavioural specs** |
| `fairShareRolePick` | **no** | `gpusAvail := available[vc.AcceleratorName]` then `continue` on `<= 0`; a never-measured variant's `AcceleratorName` is empty | none — **disclosed and justified** in the test comment |
| `fillRole` | **yes** | see below | **none, and no disclosure** |

`fillRole`'s only gates before the clamp are `rescale.go:446` `vc.PerReplicaCapacity <= 0` and `:450`
`g <= 0`. A `PRC = 1` sentinel passes the first *by construction* — 1 is the tag's whole point — and
the second reads `gpusPerReplicaFromState(stateMap, ...)`, which is **state**-derived, not
capacity-derived, so the empty `AcceleratorName` that stops `fairShareRolePick` does not stop this. A
tagged variant arrives at the clamp.

What makes the gap worth a finding rather than a note is that this is the site the commit itself
nominates as the dangerous one. `rescale.go:456-459`:

> *"read through the helper because this loop is otherwise unbounded whenever MaxReplicas is unset --
> which is where a from-zero variant would absorb the whole role's GPUs one unit of capacity at a
> time."*

and `analyzer_helpers.go:103-104`: *"fillRole's loop is bounded only inside the MaxReplicas
condition."* The inner `for wantGPUs-spent >= g` loop breaks **only** under `bounded`, so the entire
claim that a tagged variant takes one bite instead of the role's whole budget rests, at this site, on
prose. Combined with Finding 46 — nothing writes the tag, so production exercises none of this —
"untested" here means *wholly unvalidated*, not *validated in the field but not in CI*.

**Fair accounting of what C11 owes.** `fillRole` has zero direct test references tree-wide (`git grep
fillRole` at `b6bb525c` returns four hits: two comments, one caller at `rescale.go:388`, one
definition). That absence is **pre-existing** — C11 did not remove coverage, and the site was already
reachable only through its caller. The charge is narrower and, I think, still fair: C11 added a guard
at a site with no direct test, added none, and *did* write the justification for skipping the other
site. One omission is reasoned in the test file; the identical omission at a reachable site is silent.
A later reader diffing the tests will find the disclosed gap and conclude the undisclosed one was
covered.

**Cost to close is near zero, and the fixture is maximally discriminating.** `fillRole` is unexported
but in-package, and takes plain arguments — `variants, role, stateMap, targets, wantGPUs` — with no
`available` map and no interfaces to stand up. One tagged `VariantCapacity{PerReplicaCapacity: 1,
Reason: ReasonFromZeroAdmission}`, a state with `GPUsPerReplica: 1` and `MaxReplicas` nil, and
`wantGPUs: 10` asserts `spent == 1` and `targets[v] == 1`. The same fixture against the pre-C11 body
returns `spent == 10` — a 10× miss, not an off-by-one. That is the strongest discrimination signal
available anywhere in C11, and it is the one not taken.

**Severity: low now, by exactly the reasoning that makes it worth recording.** While `(D-a)` is
deferred the site is dormant (Finding 46), so nothing is broken today. It becomes the untested half of
the guard at the precise moment `(D-a)` lands — i.e. the moment the guard starts mattering — and by
then the commit that would naturally have carried the test is many commits back. Recommendation, for
whoever owns the disposition: either land the ~15-line fixture with C11, or list it explicitly as owed
work in the `(D-a)` follow-up. Not silently, and not as "covered by the helper's unit tests" — the
four `maxTargetReplicas` specs prove the helper returns the right number, which is not the same claim
as the loop honouring it.

**No §4a delta.** This finding proposes a test, not a comment; nothing here adds a token.

---

## C10 pre-registration — one blocker in the plan, and four scorable predictions

Written **before** C10 exists, from frozen-Type-1-derived plan §2e (L1108-1247). Same method that
produced Findings 42 and 43, both of which scored. Nothing here is a code finding yet; Finding 48 is a
**plan defect**, and P1-P4 are predictions I will score against the commit when it lands.

### Finding 48 (plan defect, blocking C10) — §2e.2's "verified no cycle" is false, and the cycle it misses is test-only, so `go build` will not reveal it

Plan §2e.2 L1169-1170:

> New import of `internal/config` into `throughput` — **verified no cycle** (`internal/config` imports
> no `internal/engines` package).

The parenthetical is wrong. `internal/config/config_test.go` — **`package config`, an in-package test
file** — imports `internal/engines/analyzers/throughput` and uses `throughput.AnalyzerName` at `:23`.
It exists as a drift guard: `config.go:341` declares `const throughputAnalyzerName = "throughput"` and
the comment at `:338-340` says the literal is duplicated *"rather than importing
internal/engines/analyzers/throughput.AnalyzerName) because internal/config is a lower layer than the
analyzers package"* — so the production file avoids the import **deliberately**, and the test file
closes the loop on purpose to catch a rename.

What that does to C10:

| build | graph | result |
|---|---|---|
| `go build ./...` | `throughput → config → domain` | **acyclic — green** |
| `go test ./internal/config/...` | `config[test]` (= `config.go` + `config_test.go`) `→ throughput → config` | **`import cycle not allowed in test`** |

An in-package test file may not import a package that depends on the package under test; that
restriction is the reason Go has external test packages at all. So the plan's clearance is not merely
imprecise, it points away from the failure: a coder who trusts "verified no cycle" and runs `go build`
first sees green and then hits a cycle error whose stated cause has already been ruled out in writing.

**Why the precedent misleads.** `saturation_v2/analyzer.go` imports `internal/config` and asserts the
concrete config type exactly as §2e.2 proposes — that idiom is established and correct *there*. It is
not transferable to `throughput` for one reason that has nothing to do with layering: config's test
file points at **throughput specifically**. Of the analyzer packages, throughput is the single one for
which the standard idiom does not compile.

**Both halves of `resolveKSat` need the import**, so it cannot be partially avoided: the type
`SaturationScalingConfig` (`internal/config/saturation_scaling.go:12`) and the fallback
`DefaultKvCacheThreshold = 0.80` (`:241`) both live in `internal/config`.

**Remedies, and the one to avoid.** The concern is the plan owner's, not mine, but the option space is
narrow enough to be worth stating because the cheapest-looking path is the harmful one:

1. **Avoid the import** *(recommended)*. Assert a narrow method-bearing interface rather than the
   concrete type — `cfg.(interface{ KvCacheThresholdValue() float64 })` — which requires adding that
   one method to `SaturationScalingConfig` (an edit *inside* `internal/config`, no cycle), and give the
   0.80 fallback a home reachable without importing config. Keeps the documented layering, keeps the
   drift guard, no test surgery. Note the symmetry: duplicating a constant and guarding it with a drift
   test is *precisely* what `config.go:338-341` already does in the other direction — the same remedy
   applies in reverse.
2. Move the drift guard to an external `package config_test`. Legal, but it reads the unexported
   `throughputAnalyzerName`, so that identifier has to be exported or the guard rewritten — weakening
   the protection the duplication comment depends on.
3. Resolve k_sat at the engine boundary and pass a `float64` into TA. Works (pipeline already imports
   config) but is a larger design change than the problem needs, and TA already *receives*
   `input.Config` — it simply never reads it.
4. **Delete the drift guard.** The path of least resistance and the one to refuse. It silently removes
   a real protection, and it is a §4b-classifiable deletion that nobody would think to classify,
   because it looks like a build fix rather than a behaviour change.

Severity: **blocking C10, not shipped-defect.** `make test` runs `./internal/...` and so *does* catch
it — the gate is sound. The cost is a mid-commit stall with the plan's own text arguing against the
true cause, plus the live risk of remedy 4.

### P1 (verified arithmetic) — the file's ambient tolerance idiom cannot detect a broken `resolveKSat`, even at `KvCacheThreshold: 0.5`

Plan row L289 asks for a `KvCacheThreshold: 0.5` fixture expecting **2618.9** at **≤1% relative**. I
re-derived all three points from the shipped fixture (`A=0.073, B=0.006, KV_max=1024000, KVreq=4600`;
`μ(k) = (k·KV_max/KVreq)/(A·k+B)`) and the plan's numbers are right:

| k | `N_sat` | `ITL_sat` | `μ_sat` |
|---|---|---|---|
| 0.85 (broken / pinned) | 189.2174 | 0.06805 | 2780.56 |
| 0.80 (post-C10 default) | 178.0870 | 0.06440 | 2765.33 |
| 0.50 (proposed fixture) | 111.3043 | 0.04250 | **2618.93** |

Broken-vs-expected gap at the fixture is `161.63/2618.93` = **6.171%**, which is where §2e.3's 6.17%
comes from. The file's ambient idiom is `BeNumerically("~", muSat, muSat*0.10)` with `muSat = 2782.0`
(`analyzer_test.go:273`) — a **±278.2** window, i.e. `[2340.7, 2897.1]`, which **contains 2780.56**. A
`≤1%` window is `[2592.7, 2645.1]`, which excludes it.

**Prediction:** if the new fixture is written with the surrounding `muSat*0.10` idiom rather than an
explicit ≤1% bound, it passes whether `resolveKSat` works or is hard-pinned at 0.85, and C10 ships with
a test that proves nothing. This is the same failure class as Finding 47 — a guard whose only exercise
is a test that cannot discriminate — and the plan flags the risk itself, so a miss here is a plan-read
miss, not an unforeseeable one.

### P2 — `DefaultKSat` must reach zero references, comments included

Inventory at `b6bb525c`: `analyzer.go` ×5, `constants.go` ×4, `itl_model.go` ×2, `itl_model_test.go` ×1
(the comment at `:136`), `docs/developer-guide/throughput-analyzer.md` ×5. §2e.2 deletes the constant
(§4b **DEPRECATED**), and CONVENTIONS' semantic-pivot rule applies with the grep term named in the plan
— so the coder is obligated, and a surviving comment reference is scoreable rather than arguable. The
doc-side 5 belong to C9 if they do not move here.

### P3 — the derivation comment at `analyzer_test.go:259-264` is the most likely silent omission

It spells `0.85` into its `N_sat` and `ITL_sat` lines. §2e.3 requires rewriting it against the resolved
k_sat *and* re-deriving the printed numbers. Nothing goes red if it is skipped (P1: ±10% absorbs
0.55%), which is exactly the profile of an omission that survives a green gate.

### P4 — the "~6%" figure must not appear in C10's message

§2e.3 L1221-1223 is explicit: justify as correctness and configurability, keep 6% out of the commit
message. The true default-config effect is **−0.548%**. An earlier plan draft's ~5.9% was
`1 − 0.80/0.85` — the numerator alone, off by ~11×, corrected on a reviewer finding. Directly scoreable.

### P5 — `checkVariantGPSMismatch` gains a parameter and has no test, by prior deferral

Its coverage was split out of the ITL/demand test work and remains open with no owner. A signature
change landing untested is *acceptable* on that basis — but per Finding 47 the question is whether the
omission is **disclosed**. Prediction: it lands silently. Cheap to satisfy: one sentence in the commit
message or a comment noting the pre-existing gap.

---

## C10 review — `1a50b418` "throughput: read k_sat from config instead of hard-coding it (C10)"

9 files, +359/−64. Reviewed against plan §2e (`ta-anchor-dynamic-refresh-plan.md:1154-1251`) and the
five predictions pre-registered above.

**Net verdict: the strongest commit in PR-2.** The blocking plan defect I raised was independently
found and fixed by a mechanism better than the one I proposed; four of five predictions hit, and the
fifth was wrong in the coder's favour. One §4a violation (one line, cheap), one imprecision in the
commit message, and a drive-by comment correction that I adjudicate as correct.

### Finding 48 — SCORED: HIT. Real cycle, and remedy 4 was not taken.

The plan's §2e.2 clearance ("the new import was verified cycle-free") was false, exactly as
pre-registered. The coder hit it, diagnosed it identically, and disclosed it in the commit message:
`internal/config/config_test.go` is an in-package test importing throughput to drift-check
`throughputAnalyzerName`, so an import in the other direction is a cycle **in the config test binary**
while `go build ./...` stays clean.

The remedy is **better than my remedy 1**. I proposed a `KSat()` accessor plus a direct import;
the coder added the accessor (`saturation_scaling.go:242-244`) *and* reads it through a structural
interface, so throughput never imports `internal/config` at all:

```go
func resolveKSat(cfg domain.AnalyzerConfig) float64 {
	if p, ok := cfg.(interface{ KSat() float64 }); ok {
		if k := p.KSat(); k > 0 { return k }
	}
	return fallbackKSat
}
```

This keeps the layering claim honest rather than merely working around it, and it degrades correctly
for any future analyzer config that has not adopted the accessor (`otherAnalyzerConfig` in the test
covers exactly that). **Remedy 4 was not taken** — `config_test.go`'s drift guard survives intact,
which was the outcome I flagged as the one unacceptable disposition.

*One imprecision, non-blocking.* The message says the cycle is such that "`go build ./...` stays clean
and only `go vet ./internal/config/` reports it." `go test ./internal/config/` must also fail, since it
compiles `config.go` + `config_test.go` into one package that would then import throughput — Go reports
`import cycle not allowed in test` at build time for the test binary. So `make test` is a second net,
not just vet. This changes nothing about the outcome (the cycle was avoided entirely) but the narrower
claim would understate the safety net if the situation ever recurs. I have not run either command —
I do not build in the coder's worktree — so this is reasoning from Go's test-package semantics, not a
measured result.

### Prediction scorecard

| | Prediction | Outcome |
|---|---|---|
| **P1** | the new discriminator will reuse the ambient `muSat*0.10` window, which provably contains the broken value 2780.56 | **HIT** — avoided. `k_sat_test.go:98` sets `tolerance = 0.002` (0.2% relative) and pins `k = 0.50` alongside the default. |
| **P2** | `DefaultKSat` reaches zero references, comments included | **HIT** — zero tree-wide. `DefaultNearKSatMargin` retained (6 refs), as planned. |
| **P3** | the stale `0.85` derivation comment at `analyzer_test.go:259-264` is the most likely silent omission | **WRONG, in the coder's favour** — updated in full (`0.85→0.80`, `189.2→178.1`, `0.068→0.0644`, `muSat 2782.0→2765.0`) *and* extended with why the ±10% band cannot pin k_sat. |
| **P4** | the "~6%" figure must stay out of the commit message | **HIT** — the message states **0.55%** and explains the near-cancellation ("k appears in both the numerator and the denominator … and largely divides out"). |
| **P5** | `checkVariantGPSMismatch` gains a parameter with no test; the question is whether the omission is disclosed | **PARTIAL** — parameter added (`analyzer.go:835`, call site `:371`), still no test. Not disclosed in the commit, but the gap is a tracked, owner-less backlog item predating this work, so it is disclosed *elsewhere*. Acceptable; no finding. |

**Three-way agreement on the arithmetic.** My independent derivation from the shipped fixture
(`A=0.073, B=0.006, KV_max=1024000, KVreq=4600`) gave μ(0.85)=2780.56, μ(0.80)=2765.33,
μ(0.50)=2618.93. The coder's table at `k_sat_test.go:80-82` is identical to the last digit, and the
0.55% figure is the overstatement relative to the *correct* value (15.23/2765.33), which is the right
denominator. The plan's own 6.17% was the k=0.50 discriminator gap, not the default-config effect —
both numbers are right about different things, and C10 uses each in the correct place.

### Endorsed: the `engine_v2.go` comment correction (unplanned site, +15/−6)

Not in §2e. It replaces a comment asserting that `&config` "has had saturation's per-entry threshold
overrides applied (the loop above)" and that non-saturation results "are discarded", with the opposite
claim: nothing rewrites the config, and the other analyzers' results are consumed. Since the two
comments contradict each other, one had to be wrong about the code. **The new one is right:**

- `config config.SaturationScalingConfig` is a **by-value** parameter (`engine_v2.go:104`).
- `resolveThresholds(analyzerName string, cfg config.SaturationScalingConfig) (scaleUp, scaleDown float64)`
  (`:395`) takes it by value and **returns** floats — it cannot mutate the caller's copy.
- `applyUniversalThreshold(r *domain.AnalyzerResult, scaleUp, scaleDown float64)` (`:476`) mutates the
  **result**, not the config.
- `Config: &config` (`:140`) therefore hands out an unrewritten struct.

There is also **no loop above** — the two preceding statements are the `resolveThresholds` and
`applyUniversalThreshold` calls. I checked PR-1's tip: the same comment, with the same "(the loop
above)" reference and no loop, is already there. So this is an **inherited** false comment, not one
PR-2 introduced, and the "harmless … their results are discarded" half had additionally gone stale on
this branch, where the multi-vote combine consumes those results. Correcting it here is right and not
scope creep: C10's whole premise is that TA now reads `KvCacheThreshold` off that same config, so a
reader who believed the old comment would conclude TA reads a rewritten value. Disclosed in the
message's final paragraph.

### Finding 49 — §4a violation in a code comment (new instance of the class)

`internal/engines/analyzers/throughput/k_sat_test.go:163`:

```go
// and whose scale-up watermark is 0.85. Pre-C10 this priced at k = 0.85;
```

`C10` is a commit-map label from the task plan. It is meaningless to a reader of the merged code, which
is precisely what §4a forbids — and unlike the commit-message instances of this class (fixable only by
`rebase -i` reword), this one is a one-line edit, so it belongs in C9's sweep or an amend. The prose
already carries the meaning; "Before this change" suffices.

Softer instance, same class: the commit message says "the plan has `resolveKSat` type-assert …" and
"Two deviations from the plan". No path or filename, so it is outside the literal prohibition, but
"the plan" does not resolve for anyone reading `main`'s history. Not worth a reword on its own — noted
so C9's sweep can decide whether the class includes bare "the plan".

### Verified sound (no action)

- **The k_sat validation chain is closed.** `resolveKSat` guards `k > 0`; `ApplyDefaults` writes 0.80
  when the field is zero (`saturation_scaling.go:294`); `Validate` rejects outside `[0,1]` (`:401`).
  A config-driven input into capacity math is the kind of thing that wants a guard, and it has three.
- **`fallbackKSat`'s duplication is pinned, not merely commented.** `TestFallbackKSatMatchesConfigDefault`
  is the mirror of `config`'s existing `throughputAnalyzerName` guard, so the reciprocal duplication is
  symmetric and both directions fail loudly on drift. The comment at `constants.go:52-67` names the
  reason, the reciprocal, and the pinning test.
- **`DefaultNearKSatMargin`'s comment now distinguishes margin from threshold** — "A genuine margin,
  unlike the k_sat it is measured from, so it stays a constant." This is the distinction PR-2 has been
  getting wrong elsewhere; here it is stated precisely.
- **`FitITLModel`'s exported signature growth breaks nothing** — no callers outside the throughput
  package (two dev-guide mentions only), re-verified at this tip.
- **Dev-guide (+28) is accurate and honest.** Reframes k_sat as configuration rather than a constant,
  keeps the watermark contrast, corrects the near-saturation example (0.75 → 0.70) with the right
  parenthetical about which of the two operands is constant, updates the constants table, and
  **narrows rather than deletes** the EPP open item — the remaining half (nothing holds the EPP's own
  notion of full to the same number) is stated as still open.

### §4a ledger — authoritative counts, correcting two figures I had been carrying

Recounted at three tips with one fixed pattern
(`C<n>[a-f]?` · `PR-1/2` · `W<n>` · `N<n>` · `U<n>` · `D-a/D-b` · `T1.<n>` · `FZ-admission`), text files
only, over `internal/**` and `docs/**`:

| tip | code/doc token locations | commit messages carrying a token |
|---|---|---|
| `075a208e` (PR-1 tip, base) | **7** (inherited) | — |
| `b6bb525c` (C11) | **52** | 16 of 18 |
| `1a50b418` (C10) | **53** | **17 of 19** |

Two corrections to figures in earlier sections of this doc:

1. **The code/doc count at `b6bb525c` was 52, not 53.** I had recorded 53 there; 53 is the count *after*
   C10, which added exactly one location — `k_sat_test.go:163`, i.e. Finding 49. So PR-2 has introduced
   **46** new token locations on top of 7 inherited from PR-1, and C9's sweep is a 53-location job of
   which 7 are not PR-2's to fix (though they are equally invisible to a `main` reader).
2. **The message count at `b6bb525c` was 16 of 18, not 17 of 19.** 17 of 19 is correct as of C10. My
   earlier figure counted a commit ahead of itself; the number I have been quoting to Dean is right
   *now* but was one high at the time I quoted it.

An earlier grep of mine also reported ~61 locations — that run included 8 `Binary file … matches` lines
from the dev-guide PNGs, whose bytes happen to match the pattern. Those are not token locations; the
counts above use `git grep -I`.

**Cost-of-waiting, restated on the corrected basis:** every commit added to PR-2 while it is unpushed
adds one more message to a `rebase -i` that is currently free (the branch needs a force-push anyway).
The trajectory is 16 → 17 across one commit, with C9 still to land. Once PR-2 opens, the same edit is a
live-PR history rewrite. The 53 code/doc locations are separate and unhurried — C9 is their natural
host, and one of them is now a finding rather than a bulk-sweep item.

---

## `79a590d6` "pipeline: test the admission ceiling at fillRole (C11 D-b follow-up)" — Finding 47 CLOSED

Test-only, +73 in `rescale_test.go`. Direct response to Finding 47.

### Finding 47 — CLOSED, over-delivered

I asked for ~15 lines proving the clamp fires at `fillRole`. The commit ships five specs that close the
whole `min(ceiling, MaxReplicas)` truth table:

| spec | tag | `MaxReplicas` | asserts |
|---|---|---|---|
| grants one replica out of the role's GPUs | yes | nil | `targets = 1`, `spent = 1` of 10 |
| does not top up on a second pass | yes | nil | second call over the same map spends 0 |
| absorbs the whole role when untagged | no | nil | `targets = 10` — the negative control |
| honours a configured `MaxReplicas` | no | 3 | `targets = 3` |
| ceiling wins over a looser `MaxReplicas` | yes | 8 | `targets = 1` |

**Discrimination verified by reasoning** (I do not run tests in the coder's worktree). With the tag check
disabled, `maxTargetReplicas` returns `bounded = false` for the nil-`MaxReplicas` cases, so: spec 1 grants
10 not 1 → fails; spec 2's second pass runs the loop again from `targets = 10` and spends 10 not 0 →
fails; spec 5 grants 8 not 1 → fails. Specs 3 and 4 are untagged and pass either way. So the message's
"all three ceiling specs here fail with the tag check disabled" is exactly right about *which* three.

Spec 3 is what makes spec 1 mean anything — same capacity, same state, tag removed, 10 replicas instead
of 1. That is the 10× margin Finding 47 predicted, asserted rather than argued.

Two of the five go beyond the charge and are the more interesting ones. Spec 2 pins that the bound is on
the **target**, not on one invocation — the four `maxTargetReplicas` unit specs prove the helper returns
the right number and say nothing about the loop honouring it, which is precisely the gap Finding 47 was
about. Spec 4 guards the converse regression: the new ceiling must not eat the pre-existing bound.

**The disclosure is also what was asked for.** The message states "fillRole had no direct test references
tree-wide before this; that gap is pre-existing and only the ceiling is covered here." Finding 47's charge
was never that `fillRole` lacked coverage — that is pre-existing — but that a guard was added at a
reachable untested site *silently* while the unreachable site's omission was reasoned in a comment, so the
silence read as coverage. Naming the residual gap resolves it.

### Finding 50 — `max` shadowing reintroduced (minor)

`rescale_test.go:239` and `:248` declare `max := 3` / `max := 8`, shadowing the Go builtin. Two facts make
this worth a line rather than nothing:

- These are the **only two** `max :=` declarations in the repo at this tip (`internal/**`, `cmd/**`).
- The pattern was flagged by ev-shindin in the #1246 review (`roleBottleneckReplicas`,
  `roleAggRemaining`), a cleanup item is still in the backlog for it, and **those sites are now gone** —
  `analyzer_helpers.go:977` uses the builtin correctly (`max(int(math.Floor(...)), min(1, n))`). So the
  codebase has moved off the pattern and this commit is the sole place reintroducing it.

Not a gate failure: gocritic's builtin-shadow check is not on by default, and the coder's gates were
green, so this passes `make lint`. It is a convention regression against a maintainer's stated objection.
`maxRep := 3` costs nothing. There is no competing local idiom to follow — no other pipeline test declares
a `MaxReplicas` local at all.

### §4a delta

- **One new code-comment token:** `rescale_test.go` — "The from-zero admission ceiling (C11) is what
  stops…". Text-only locations **53 → 54**.
- **Message class now 18 of 20.** Subject carries `C11` and `D-b`; body adds `PR-2`.
- **New sub-class worth naming:** "Raised by the PR-2 internal review as Finding 47." Attribution to an
  internal review document by finding number is unresolvable for anyone reading `main` — worse than a bare
  "the plan", because it looks like a precise citation. This will recur every time a commit answers a
  finding, so it is better fixed as a habit than swept. The reviewable content ("the site was reachable,
  untested, and the disclosure written for the unreachable site made the silence read as coverage") is
  already in the message and stands on its own without the attribution.

### Verified sound

- **`"T1-ols"` is a faithful untagged control, not a straw value.** It is the real tier-1 OLS reason
  (`throughput/constants.go:129`), unexported, so pipeline tests use the bare literal — the established
  idiom here, with 6+ prior uses in `analyzer_helpers_test.go`. The negative control therefore exercises a
  reason string production actually emits.

---

## Operational observation — the status file has fallen nine commits behind

> **RESOLVED by the coder itself, 2026-08-08T00:50Z — no action needed.** The status file now reads
> `C9a LANDED — tip 757fc6f5` and is current with the branch; the nine-commit gap below is closed, and
> the superseded `C6d`/`330fcd26` text is retained there as explicitly-marked history. Left in place
> because the failure mode it describes is worth keeping on the record: the gap opened and closed without
> anyone outside the coder's session noticing, which is the property that made it worth writing down. It
> also dates my own observation — it was accurate for about four hours.

Not a code finding; recorded because the status file is the one channel designed to answer "where is the
coder?" without interrupting it, and right now it answers wrongly.

At `79a590d6`, `session/status/ta-anchor-dynamic-refresh.md` reads
`last_update: 2026-08-07T21:00:00Z` and `current_step: **C6d LANDED — tip 330fcd26**`. `330fcd26` is a
genuine ancestor of the tip (verified with `merge-base --is-ancestor`), so this is staleness rather than
divergence — but nine commits have landed since it was written:

```
784c2b5c  one fair-share entitlement per model, drawn in sequence (C6e)
a679f2ad  abstain is not exempt -- make W4 a tested property (C6f)
537b0153  pin the claim-pricing distortion as a dormant spec
4fb49ac6  drop plans-branch paths from shipped comments; fix the mean claim
a46c7eea  pin the fair-share shared balance, not just the per-role clamp
eb12089a  drop the mis-routed role label from a shipped comment
b6bb525c  bound a from-zero-admitted variant at the grant sites (C11 D-b)
1a50b418  read k_sat from config instead of hard-coding it (C10)
79a590d6  test the admission ceiling at fillRole (C11 D-b follow-up)
```

Two of the nine are the largest commits on the branch (C11 and C10), and C10 carries a disclosed deviation
from the plan (the import cycle) that a reader of the status file would have no way to know about. The
convention's stated failure mode is that stale status looks like a crashed session; here the inverse also
holds — the branch is nine commits healthier than the status file claims.

`state: coding` and `blocked_on: nothing blocks coding` are both still accurate, which is why this has
gone unnoticed: the fields that would look alarming if wrong are right, and the field that is wrong
(`current_step`) reads plausibly.

I am not routing this to the coder. A reviewer telling a coder to update its status file is direction, not
review, and the conventions put status writes solely in the coder's hands. Flagging it for Dean is the
correct channel, and this entry is the record.

---

## `757fc6f5` — docs: capacity-gauge currency gap + the deprioritize idiom

Documentation-only, 2 files, +50/−3, no code change. **Verdict: sound.** Every substantive claim was
checked against the code and every one of them holds, several of them to the line. It also closes a real
staleness defect in a shipped reference doc, and it is the **first §4a-clean commit on the branch**.

The commit's own framing — "two documentation-only items with no code change to pair with, so they have no
commit of their own and would otherwise go unwritten" — is the right instinct. Both items are things a
reader would otherwise have to discover by reading the source.

### Claims verified against code

**1. RC/SC come from the anchor, per-role with a model-level fallback.** Exact.
`buildDecisionsWithOptimizer` (`cost_aware_optimizer.go:296`) at `:356-367`: seeds from
`anchor.RequiredCapacity/SpareCapacity`, then overwrites from `anchor.RoleCapacities[role]` when that role
has an entry, with `role == "" → RoleBoth`. The doc's "per-role when the binder has an entry for the
variant's role, model-level otherwise" is a precise reading.

**2. The `unit` label is stamped unconditionally for every V2 decision.** Exact, and the attribution to
`enrichDecisionsWithKvTokenData` is right. `saturation/engine.go:1297` sets
`d.RequiredCapacityUnit = constants.UnitContinuous` **outside** the `if a, ok := agg[...]` guard, so it
lands on every decision whether or not KV aggregates exist for it. It is the only non-test assignment of
either unit constant in the tree, and it is reached from `optimizeV2` (`engine.go:955`) at Stage 4
(`:1062`) over `allDecisions`. So "every V2 decision unconditionally" is not an approximation.

**3. The help text names the KV-token analyzer as the source.** Both gauges. `metrics.go:183` (required):
`"continuous" → token demand from the Token-based analyzer`; `metrics.go:176` (spare): `→ token surplus
from the Token-based analyzer, max(0, TotalSupply - TotalDemand/scaleDownBoundary)`. When a throughput
result is the binder, both the label and the help attribute the value to an analyzer that did not produce
it. The gap is real and correctly described.

**4. The binder can change between cycles.** Exact. `bindingAnchor` (`analyzer_helpers.go:196`) binds
saturation when `Enabled && Live && ResultIsInformative` (`:211`), and otherwise falls through to the
lowest-ballot-index enabled+live+informative non-saturation entry (`:214-228`). A staleness lapse drops
`Live`, which hands binding elsewhere with no metric-label change — which is exactly the failure mode the
note warns about, and the one that makes this worth documenting rather than filing.

**5. The priority claims — all three, to the line.** `ApplyDefaults` rewrites an exact zero:
`saturation_scaling.go:290-291` `if c.Priority == 0 { c.Priority = DefaultPriority }` with
`DefaultPriority = 1.0`. `Merge` skips an exact zero override: `:377-378` `if override.Priority != 0`,
leaving the global value. `Validate` accepts it: `:413-414` rejects only `< 0`. So `priority: 0` is erased
twice over and passes validation while doing the opposite of what it looks like — a genuinely
counter-intuitive behaviour that deserved to be written down.

**6. The first-draw floor is real and load-bearing for exactly this case.**
`greedy_score_optimizer.go:702-711`: `if firstDraw && capN < 1 { capN = 1 }`. And it matters here
specifically because `replicasToCover` returns **0** for a non-positive entitlement (`:834-835`) — so
without the floor a model whose share rounds away would be skipped rather than served. The doc's "served
in single-replica steps, via the first-draw floor, once the higher-priority models have been satisfied or
dropped" is an accurate description of the mechanism, including the "what the others leave" part: the draw
still has to clear `gpusAvail < gpusPR` (`:692`), so leftovers are a real precondition, not a formality.

**7. The replaced note — the old text was wrong in both halves, and the new text is right in all of
them.** The universal post-step is in this tree and it is per-analyzer: `engine_v2.go:122-123` resolves and
applies saturation's thresholds, `:181-182` does the same inside the loop with
`resolveThresholds(entry.name, config)` — the analyzer's own registered override. And
`applyUniversalThreshold` recalibrates at both scopes: model-level at `:481-494`, then every
`RoleCapacities` entry at `:496+`. "at model level and per role", "for every analyzer", "using either the
analyzer's own registered override or these model-level values" — all three clauses check out.

**8. Both new anchor links resolve.** `#data-model-analyzerresult--namedanalyzerresult` matches
`multi-analyzer-pipeline.md:531` `## Data model: AnalyzerResult → NamedAnalyzerResult` — including the
double hyphen the dropped `→` produces in the GitHub slug. `#v2-analyzer-parameters` matches
`saturation-scaling-config.md:159`. Broken anchors in shipped docs are cheap to ship and annoying to find;
these are correct.

### Credit where it is due

Removing the `multi-analyzer-threshold` forward reference is the right call and the message's reasoning for
it — "a shipped reference doc should also not send readers to an unmerged PR, so the forward reference is
gone rather than updated" — is exactly the Type 4 discipline. Updating it would have preserved a pointer
that cannot resolve for anyone reading the merged tree.

The "please do not file it as a bug or fix the defaulting — the fix would break every config that omits the
field" framing is also worth noting. It documents not just the behaviour but why the behaviour must stay,
which is what stops a future reader from "fixing" it.

### Finding 51 — a §4a comment whose fix is not a token strip

`internal/engines/pipeline/analyzer_helpers.go:216-218`:

```go
// Otherwise the lowest-ballot-index enabled+live+informative
// non-saturation entry binds (N2 deterministic tie-break): once PR-2
// admits multiple non-saturation voters, a later qualifying entry does
// not overwrite the earlier one — it votes without binding.
```

Two problems, and the second is the one that matters:

- **Two §4a tokens** (`N2`, `PR-2`) in a shipped code comment. Already inside the 54-location count.
- **The tense is wrong on this branch.** "once PR-2 admits multiple non-saturation voters" describes as a
  future event something that is already true in the same tree: `votingResults`
  (`analyzer_helpers.go:315-323`) admits every `Enabled && Live` entry with no cap on how many
  non-saturation ones qualify. The condition the comment defers to has already arrived.

Flagging it because a mechanical §4a sweep makes this worse, not better: strip the tokens and you get
"once this change admits multiple non-saturation voters", which is still future-tense about the present.
The correct rewrite states the invariant in the present — *with multiple non-saturation voters admitted, a
later qualifying entry does not overwrite the earlier one; it votes without binding* — which is both
§4a-clean and true. This is the general hazard with the sweep: the tokens are load-bearing markers of
"written before X landed", so some of the 54 are stale in content and not merely in vocabulary.

### One precision nit, not a request

The doc says a small positive priority "sorts the model behind every other model in the fair-share loop".
Strictly the ordering key is `priority × claim` (`fairShareValue:135`, sorted descending by
`sortByRemainingDesc:768`), so a deprioritized model outranks a normal-priority one when its claim is more
than `1/priority` times larger — 100000× at `0.00001`. In GPU space, where claims are single- or
double-digit, that cannot happen, so the simplification is fair and I would not change the sentence. Noted
only so the exactness of the surrounding claims is not read as exactness here too.

### Ledger delta

- **Code/doc token locations: 54, unchanged.** The added doc lines are token-free.
- **Commit-message class: 18 of 21** (was 18 of 20). The denominator moved, the numerator did not — this is
  the first message on the branch that carries no plans-branch identifier, and it is a docs commit, which
  is the easiest case. Still: it demonstrates the messages can be written this way.
- **This commit is not the §4a sweep** and does not claim to be. It carries no commit label, and the plan's
  dev-guide-plus-goldens commit is still ahead of us, so the sweep and the remaining doc corrections
  (`analyzer_helpers.go:213-216`, the path/filename class, Finding 46's constraint on describing the
  from-zero ceiling) all remain pending there.

---

## C9 is now decomposed in the status file — one scoping match, one gap

The coder's status file at `2026-08-08T00:50Z` breaks the last plan item into five sub-commits. Recording
it because it changes what I should be watching for, and because one of the five closes a question I had
open while another opens a risk.

| sub-item | content | state |
|---|---|---|
| C9a | the two homeless doc items (`U5` + `W3`), docs-only | **DONE — `757fc6f5`** |
| C9b | rest of the dev-guide prose + four `analyzer_helpers.go` prose repairs | not started |
| C9c | the `[sat, TA]` multi-vote golden suite + the Invariant 7 direct test | not started |
| C9d | explicit removal of the sat-only goldens the multi-vote suite supersedes | not started |
| C9e | the §4a token sweep, **scoped to the PR-2 delta** | not started |

**The C9e scoping is right, and it matches my ledger exactly.** The status file states "47 of 54
locations; the 7 inherited at base `075a208e` are out of scope" — 54 − 7 = 47, and both the total and the
inherited count are the figures in my corrected ledger. Scoping the sweep to the delta is also the correct
call on its own merits: the 7 inherited locations are pre-existing on `main` and belong to the separate
governance cleanup, not to this PR. Fixing them here would inflate the diff with unrelated churn and take
credit for someone else's backlog item.

**C9b confirms two of my findings are being actioned as written** — the scale-from-zero section is slated
to be written as **DEFERRED** rather than as an active guard (Finding 46, which is the constraint that
matters most in that section, because describing an unshipped tag-writer as a live mechanism would be the
worst kind of doc defect: confidently wrong about a safety property), and Finding 29's `mean` →
`allocationMean` rename is in.

### The gap: Finding 51's site is in neither list

C9b's four prose-repair sites in `analyzer_helpers.go` are `:65-69`, `:176-182`, `:184-192`, `:280-286`.
Finding 51's site is **`:216-218`** — between the third and fourth, and in none of them. So on the current
decomposition that comment is reached only by C9e, the token sweep.

That is exactly the failure mode Finding 51 was written to flag. A token-only strip turns

```go
// (N2 deterministic tie-break): once PR-2 admits multiple non-saturation voters, …
```

into something like "once this change admits multiple non-saturation voters, …" — still future-tense about
a condition `votingResults` (`:315-323`) already satisfies on this branch. The comment would come out of
the sweep §4a-clean and still wrong, and a clean sweep is precisely the thing nobody re-reads afterwards.
So the residual risk here is higher than for the other 46 locations, not lower.

I am not directing where it gets fixed — C9b and C9e are both plausible homes, and the sub-item split is
the coder's to make. The point is only that "§4a-clean" and "true" come apart at this one location, so
whichever commit takes it needs to do a prose rewrite and not a token substitution.

---

## The C9e scoping has project precedent, and the inherited 7 have a tracked home

Follow-up to the section above. I had endorsed C9e's delta-only scoping on first-principles grounds
(unrelated churn, someone else's backlog). It turns out this project has already made the identical call
once, which is stronger than my reasoning.

`session/handoffs/review__ta-model-level-demand-f3.md` — a stale, never-processed review request from
2026-07-29, for work that has since landed as **#1480** (`f9f04d81` on `main`) — describes that branch's
own §4a pass in these terms:

> F3 touched 14 C-introduced plans-branch identifier sites (comment/test-desc only, no logic change);
> status file lists each site. Two pre-existing upstream §4a refs (dev-guide:671, test:1189, from #1250)
> left untouched and tracked as out-of-scope.

Same three-part shape as C9e: sweep the sites this branch introduced, leave the pre-existing ones, track
them elsewhere. So the coder's 47-of-54 split is not a novel judgement call — it is the established
convention on this repo, and a reviewer objecting to it would be objecting to precedent.

**Verified independently, not just taken from the handoff.** At base `075a208e`,
`internal/engines/analyzers/throughput/analyzer_test.go:983` reads
`// Regression test for F1: EPP present (ArrivalRate > 0) but no completions`. `F1` is a
`multi-analyzer-design.md` design-item identifier — the pre-analysis-extraction item — so this is a
genuine inherited violation of exactly the class the older handoff describes, still present on the base.
The two line numbers quoted above (`dev-guide:671`, `test:1189`) are as-of that branch's tip and have
drifted since; I did not attempt to re-resolve them, and they are not load-bearing for the conclusion.

**These are tracked, not orphaned.** `CURRENT.md` carries "Pre-existing `main`-side §4a-cleanup locations →
`planning/governance-follow-ups.md`". So the inherited 7 already have an owner and a home, and C9e leaving
them alone does not drop them on the floor — which was the only real objection to delta-only scoping.

Consequence for my own review of C9e: **I should not expect the inherited 7 to move, and I should not
score their survival as an incomplete sweep.** Noting that explicitly because a §4a-clean claim is easy to
mis-audit — re-running the full grep after C9e will still return non-zero, and the correct reading of that
is success, not shortfall.

### A note on auditability

The precedent's other half is worth flagging: that branch's status file **enumerated each of the 14 sites**.
For a 47-site sweep the equivalent is what makes the commit checkable by anyone other than its author —
without a per-site list, verifying the sweep means re-deriving the whole location set and diffing it against
the commit, and any location the sweep silently missed is indistinguishable from one it correctly judged
out-of-scope. Not a request about how to structure the commit; a statement of what my C9e review will
otherwise have to reconstruct from scratch.

### Housekeeping — a second obsolete `review__` handoff

`review__ta-model-level-demand-f3.md` is a bare `.md` addressed to the review role, sitting unprocessed
since 2026-07-29 for a branch that merged 2026-07-30. It is the second such file, alongside
`review__ta-anchor-refactor-v2-pr1-checklist.md` (obsolete since PR-1 merged as #1516). I am deliberately
**not** renaming either to `.DONE`: I did not process them, and marking them consumed would assert a review
that never happened. Both are on the list for Dean's cleanup call. Flagged together because two stale
bare-`.md` files in a directory whose whole protocol is "bare `.md` means unread" is a small ongoing
false-positive source — the coder's own status file has had to carve out an explicit exception list for the
same reason.

### Self-disclosure — a fourth `cd`-into-sibling slip, with a new cause

Recording it because the cause differs from the previous three and is the more mechanizable one.

The previous three slips were `cd` calls I intended as `cd`. This one was a **guard that did not guard**: I
wrote `cd <sibling> 2>/dev/null; echo "SKIP-no-cd"` believing the `cd` would fail and the echo would prove
it. The `cd` succeeded, the echo printed the reassuring string anyway, and the session CWD sat inside the
coder's worktree for one subsequent call. Suppressing stderr and printing a fixed string is not a check —
it reads like one, which is worse than no check at all.

**No damage, and the existing gate is what caught it.** The next command was a `pwd` + `git branch` before a
commit, per the convention; it showed `ta-anchor-dynamic-refresh` and the write failed on its own (my
target path is relative to `plans/` and does not exist there), so nothing was created in the coder's tree
and its tip and working set are untouched. I verified that explicitly rather than assuming: `git status
--porcelain` on the sibling shows only the coder's own two in-flight C9b files and **no untracked
entries**, which is what a failed heredoc leaves behind — nothing.

Two things follow. First, this strengthens rather than weakens the case for a mechanical gate: four
occurrences, three different intents, one of them a *defensive* construct, all in one reviewer session. The
pre-commit `pwd` check has now caught the consequence twice, which is good, but it catches at commit time,
after arbitrarily many reads have already run from the wrong directory. Second, the correct idiom for what I
was attempting is not a suppressed `cd` at all — every sibling access in this role should be
`git -C <abs-path>` or an absolute path, with no `cd` in the pipeline to succeed by accident. I have
switched the surrounding commands to absolute paths.

Incidental but useful: the same check revealed the coder is **mid-C9b right now** —
`docs/developer-guide/multi-analyzer-pipeline.md` and `internal/engines/pipeline/analyzer_helpers.go` are
both dirty in its tree, which are precisely C9b's two subjects. That is a reason to stay further out, not
closer in; I am reviewing committed state only and will not read its uncommitted working copy.

---

## Pre-registration — C9b (in flight now)

Written before the commit lands, against committed tip `757fc6f5`, so the predictions are falsifiable.
Pre-registration caught Finding 48 before C10, so it is worth the cost again here. Six predictions, and
**the second is a retraction of my own earlier instruction** — that one matters more than the rest,
because acting on the superseded version would introduce a defect rather than fix one.

### P2 (highest priority) — my C11 checklist items 7 and 13 are now WRONG. Do not act on them.

Both items said, of `analyzer_helpers.go`'s *"Not proactively selectable; genuine cold-starts fall to the
reactive scale-from-zero engine"*:

> the exact claim C11 reverses, and must change in the same commit

**That was written on the assumption that `(D-a)` would ship.** It did not — `(D-a)` is deferred, nothing
writes `ReasonFromZeroAdmission`, so `PerReplicaCapacity` still stays 0 for a binder-omitted variant and
the variant still is *not* proactively selectable. C11 shipped `(D-b)`, the ceiling, which constrains an
admission that never happens. **The claim is therefore true as written, and "correcting" it would replace a
true statement with a false one.**

The current text at `:176-182` has in fact already been revised the right way — it keeps "not proactively
selectable" *and* adds "Proactively admitting the zero-replica case … is deferred; see
ReasonFromZeroAdmission for why an anchor-side sentinel alone does not achieve it." That is
deferral-consistent and I would leave it alone.

So my prediction for this site is inverted from my earlier checklist: **the correct C9b outcome at
`:176-182` is little or no semantic change.** If the diff makes the variant sound selectable, or drops the
deferral clause, that is a regression traceable to my own stale instruction, and I will score it as my
error and not the coder's. Retracting items 7 and 13 explicitly for that reason.

### P1 — `:65-69`, the `ReasonFromZeroAdmission` doc comment must read as dormant (Finding 46)

Current text says the constant "marks a variant the anchor admitted on the from-zero sentinel" and that
"the one-replica ceiling in `maxTargetReplicas` keys on this tag". Both clauses are individually accurate
about the *code*, and together they read as a live mechanism. Nothing writes the tag, so the ceiling is
unreachable in production. **Predicted PASS condition:** the comment states that no code currently sets
this `Reason`, so the ceiling is dormant. **FAIL:** the deferral is implied only by omission, or stated
only in the dev-guide and not here — this constant is what a reader greps to when they see the ceiling.

### P3 — `:184-192` must fix the false premise, keep the correct conclusion (Finding 45)

The premise *"A binder omits a variant only when the binder itself is enabled-but-not-binding —
`Enabled && !(Live && Informative)`"* is false: `ResultIsInformative` is an **any-variant** predicate
(`:57-61` returns on the first informative entry), so a fully healthy binder can be
`Enabled && Live && Informative` in aggregate and still price nothing for one variant — which is the
*expected* shape for a never-measured variant under a throughput binder. The conclusion (do not borrow
saturation's sizing) is right and should survive. **PASS:** premise restated so it does not claim binder
ill-health; conclusion intact; the `(N8)` token gone. **FAIL:** the token is stripped and the false premise
survives — the §4a-clean-but-still-wrong pattern of Finding 51.

### P4 — `:280-286` carries a token *and* leans on a premise I have declined to endorse

Two separate things at this site. The `(N8)` token is ordinary sweep material. The prose also asserts
"Previously-live variants now at zero are covered by TA's own scale-from-zero complement from persisted
supply" — which is the `(D-a)` premise I explicitly flagged as **an unchecked dependency, not a finding**:
if that complement has a hole, the reasoning covers a variant that *has* been measured and is merely idle.
**PASS:** the claim is left at its current strength or hedged. **FAIL:** a repair pass restates it more
confidently, converting an unverified dependency into a flat assertion in shipped code. Also note
Finding 12 — the complement omits `Role` — so any restatement must not claim per-role coverage.

### P5 — the dev-guide scale-from-zero section, written as DEFERRED (Finding 46)

The status file already commits to this ("written as **DEFERRED** … the ceiling must NOT be described as an
active guard"), so this is a low-risk prediction. **FAIL** is any phrasing where a reader concludes
from-zero admission is a thing the system currently does.

### P6 — Finding 29's `mean` → `allocationMean` in `### Fair-share iteration`

Mechanical rename; **PASS** is the rename applied consistently within the section, **FAIL** is a partial
rename leaving both spellings, which is worse than neither.

### What I am not predicting

Nothing about the four sites' §4a tokens *as tokens* — those belong to C9e's 47 and I will score them
there. The overlap is only where a token strip and a prose fix pull in different directions (P3, and
Finding 51 at `:216-218`, which is in **neither** C9b's four sites nor a prose commit).

---

## The C9e sweep, enumerated per site — 48, not 47, and one of my own rulings was wrong

I built an independent token pattern from scratch rather than reusing the curated one behind my earlier
figure, ran it over the committed tip and over base `075a208e`, and differenced by normalized text so
that line shifts do not read as new sites. Result: **56 token-bearing lines at the tip, 9 at base.**

The delta reconciles two ways, and the difference between them is the interesting part:

- **47** lines carry a token that PR-2 *introduced*. This matches the coder's C9e scoping figure and my
  own ledger exactly — arrived at independently, so the figure is now corroborated rather than merely
  restated.
- **48** lines carry a token *and* were authored or rewritten by PR-2. The extra one is
  `greedy_score_optimizer_test.go:881`, where PR-2 replaced the whole test description and re-typed the
  inherited `T1.4:` prefix:

  | | text |
  |---|---|
  | base | `It("T1.4: non-uniform Score across two analyzers drives fair-share ordering", …` |
  | tip | `It("T1.4: priority orders fair share, and a trusted analyzer does not inflate its model's claim", …` |

**I resolve the boundary in favour of in-scope.** "Inherited, therefore out of scope" is a statement
about lines nobody touched; this line was in the coder's hands and the token was re-typed into it. 48 is
the number C9e should be scored against.

### Class breakdown

| class | sites | why it matters |
|---|---|---|
| dev-guide markdown | 3 | all in `multi-analyzer-pipeline.md`, which **C9b is editing right now** |
| production Go | 14 | ships in the merged tree; the highest-value class |
| test Go | 31 | |

Production-code sites are `analyzer_helpers.go` ×11 (`:87`, `:185`, `:216`, `:281`, `:576`, `:724`,
`:813`, `:830`, `:853`, `:863`, `:886`), plus `greedy_score_optimizer.go:330` (`W1`),
`optimizer_interfaces.go:54` (`N2`), and `rescale.go:348` (`N3`).

**A scoring caution I am writing down before it can bite me:** the three dev-guide sites sit in a file
C9b has open. If C9b resolves them, they will be absent by the time C9e lands, and the correct reading
is that they were fixed early — not that C9e's sweep is three short. Same trap in the other direction as
the inherited set: the arithmetic only means something if I know which commit was supposed to reach each
site.

### Finding 52 — test-plan IDs *are* a §4a class; my earlier ruling was wrong

I previously ruled that golden scenario names and test-plan IDs both fall outside §4a. **The scenario-name
half is right and the test-plan-ID half is wrong,** and the test is mechanical: does the token resolve for
someone reading only the merged tree?

- `C1`, `A1`–`A4`, `V1` name fixtures and engine versions **defined in the test file itself**. They
  resolve. Not violations. (`V2`/`V1`/`V0`/`V100` dominate any naive grep — **416 of the 478** raw token
  matches at the tip — and `V100` is an accelerator model. A pattern that does not exclude them is
  unusable. This is the same over-match that I caught and refused to build a figure on earlier; the
  refusal was right.)
- `T1.3` / `T1.4` are defined **nowhere in the code tree**. The only definition is
  `ta-anchor-dynamic-refresh-plan.md`, where §2d.6 is titled "T1.4". A reader of merged code sees a bare
  `T1.4:` prefix with no referent — which is precisely what §4a prohibits.

Consequence: `:881` is in scope as argued above, and the inherited `T1.3` pair at `:803`/`:810` is a
genuine violation rather than a false positive. They stay out of C9e's mandate, but they belong in the
inherited backlog, and they are three lines apart from a site C9e must touch — so fixing them is nearly
free if Dean wants the file clean in one pass. That is his call, not something I will score.

### Finding 53 — `§C6e` is a section pointer, not a commit label, and cannot be token-stripped

`greedy_score_optimizer_test.go:1557` and `:1576` read *"§C6e asks for the other shape"* and *"which is
the masking §C6e names."* The `§` sigil makes these pointers into a plans-branch document's section, a
distinct spelling from the bare commit labels elsewhere. They cannot be repaired by deleting the token:
*"§ asks for the other shape"* is not a sentence, and *"which is the masking names"* is worse. Both need
the referent replaced by what the section actually says. Same shape as Finding 51 — a site where a
mechanical strip yields §4a-clean prose that is either meaningless or false.

### A sub-class worth separating: tokens that will become false, not merely unresolvable

Most of the 48 fail only to resolve. Five make an affirmative claim about branch history that a squash
merge will falsify — PR-1 landed as a single squash commit, so per-commit labels will not exist in
`main` at all:

- `optimizer_dynamic_refresh_test.go:3`, `:14`, `:17` — *"Per-iteration dynamic refresh (PR-2 C2)"*,
  *"Before C2, refreshAnchorSizing does not exist"*, *"is red before C2 … and green after."* This
  documents a red/green TDD relationship to a commit boundary that will have been squashed away.
- `optimizer_liveness_test.go:3` — *"Liveness fixes for the multi-vote combine (PR-2 C7)"*.
- `k_sat_test.go:163` — *"Pre-C10 this priced at k = 0.85"* (Finding 49).

These are worth fixing first if C9e is ever time-boxed: an unresolvable token is a reader's dead end,
whereas a false historical claim actively misleads. The repair is the same in each case — state the
behavioural before/after without naming the commit.

### Confirmations

Present at the committed tip, as previously recorded: Finding 51 at `analyzer_helpers.go:216`; Finding 49
at `k_sat_test.go:163`; the `(C11)` comment at `rescale_test.go:186`. The `D-b` token appears once, at
`cost_aware_optimizer_test.go:1001`, sharing a line with `C11`.

### Commit messages — 18 of 21, recounted at the tip

Same pattern, applied to `%s` + `%b` over `075a208e..757fc6f5`. **18 of 21** messages carry a token;
three are clean (`34b18bc5`, `eb12089a`, `757fc6f5`). Frequency, most-cited first: `W4` ×10, `D-b` ×6,
`C6f` ×6, `C11` ×6, `C6e` ×5, `W1` ×4, `C6b` ×4, `PR-1` ×3, `N7` ×3, then a long tail including `D-a` ×2
and `Finding 47` ×1.

Two observations that bear on the reword decision:

**`Finding 47` is the least resolvable token on the branch.** It cites a numbered finding in *this
review doc* — a `Status: DRAFT` Type 6 artifact on an orphan branch that will never be published
anywhere a reader of `main` can reach. Every other token at least points at a design or plan document
that exists as a coherent thing; this one points into my working notes. If the reword happens, this is
the clearest single case for it.

**`4fb49ac6` is a mention, not a use — and it is the weakest of the 18.** The commit whose subject is
*"drop plans-branch paths from shipped comments"* carries a token in its own body, but the sentence is
*"a token like `W4` is at least guessable from"* — the coder is reasoning about scoping and naming a
token as an example of the category. A reader follows that sentence without resolving `W4`. I would not
count it as a defect on its own; I note it because a mechanical grep will flag it, and whoever runs the
reword should not spend effort "fixing" a sentence that is already readable.


---

## C9b (`2ae440e3`) — verdict: all six pre-registrations pass, and two new Type-4 defects

*"docs: write from-zero admission as deferred and fix four false premises"* — 3 files, +100/−29,
DCO-signed. Documentation and comments only; I take the "no behavioural change, no golden moved" claim
as consistent with the diff (no non-comment line changed outside the one test-entry rename) but I do
not sign off gate results — I do not build or test in the coder's worktree.

| # | prediction | outcome |
|---|---|---|
| **P1** | the dormancy statement lands, or is already present | **PASS** — already landed with C11; this commit adds only a forward pointer from the lead paragraph (`:63-78`: *"That ceiling is dormant — see DEFERRED below before reading any of this as something the running system does."*). Correct call: the statement was not missing, only reachable too late. |
| **P2** | little or no semantic change at the "not proactively selectable" site | **PASS, precisely** — the true clause survives verbatim (*"PerReplicaCapacity stays 0 and it is not proactively selectable, because its sizing must not be invented. That holds whether or not the variant is running."*); only the false qualifier *"which is the one nobody has ever measured"* was excised. The coder also stated plainly that *"the checklist items that asked for its reversal have been retracted"* — acting on my superseded checklist would have **introduced** a falsehood here, and it didn't happen. |
| **P3** | false premise fixed, correct conclusion kept (Finding 45) | **PASS** — premise deleted, not patched; replaced by a structural reachability argument, and the condition corrected to `!(Enabled && Live && Informative)`. `(N8)` token gone. Verified independently below. |
| **P4** | the persisted-supply claim left at strength or hedged | **PASS, beyond criterion** — hedged (*"usually covered"*) **and** the specific hole named (*"that persisted supply expires on an idle window"*). Does not claim per-role coverage, so Finding 12 stays clear. `TA's own` → `the throughput analyzer's own`. |
| **P5** | dev-guide section reads as DEFERRED, not an active guard (Finding 46) | **PASS, decisively** — titled *"built, not enabled"*; *"do not read it as a description of what happens on a live cluster"*; *"Claim one does **not** ship: nothing in production code writes the tag."* |
| **P6** | `mean` → `allocationMean`, consistently | **PASS** — `the *allocation* mean is forced to 0` → `allocationMean is forced to 0`. Names the identifier instead of describing it; no split spelling left. |

### The `costEfficiency` claim is correct, and sharper than the message says

C9b asserts an admitted variant *"sorts **first**"*. `costEfficiency` returns `math.MaxFloat64` — sorts
**last** — and its own doc comment says so. Both are true of disjoint cases, and the chain resolves
cleanly:

1. `Cost` is copied from the **carrier** (`Cost: a.Cost`, `analyzer_helpers.go:281`), and saturation
   builds `variantCost` from `rm.Cost` over `ReplicaMetrics`. A zero-replica variant contributes no
   metrics, so the map lookup **misses** and `cost` is the zero value. `Cost == 0` — verified at its
   root, and the root is why: cost is derived from per-replica metrics that do not exist at zero
   replicas. That is `N5`, correctly attributed and correctly held out of scope.
2. `PerReplicaCapacity` is copied from the **binder**, so an admitted variant carries the sentinel
   `1` — which is `> 0`, so it **escapes** the `PerReplicaCapacity <= 0` guard entirely.
3. `0 / 1 == 0` ⇒ it sorts **first**, tying with every never-measured peer under an unstable sort.

The stronger reading, which the message does not state: **admission defeats the guard's stated
intent.** `costEfficiency`'s comment says `MaxFloat64` avoids *"pretending its efficiency is zero,
which would make the one variant nobody can price the cheapest thing in the pool"* — and admission
causes exactly that, because the guard keys on non-positive PRC while admission's whole purpose is to
make PRC positive. The message's *"no sentinel value repairs it"* is right for a reason it leaves
implicit: the numerator is 0, so `0/x == 0` for **any** positive sentinel. This is corroboration for
the deferral, not an argument against it.

**Independently corroborated.** The designer's `plan__ta-anchor-da-sentinel-belongs-on-the-ballot.md`
(cc'd to me, no action requested) derives the same ordering from the same code — *"`0/1 = 0` ⇒ `V_zero`
sorts **first**. The bad path is therefore the default ordering, not an unlucky one"* — and traces it
to the same break-out-of-the-whole-loop regression, concluding *"There is no live bug to bypass
today."* Three independent derivations now agree: my read of the comparator, C9b's message, and the
Type-1 owner's trace.

### The three factual claims in the rewritten merge comment all check out

The comment this commit replaced rested on a false premise. The replacement makes three checkable
claims, and each verifies exactly:

- **Reachability** — the carrier is located by name only (`s[i].Name == domain.SaturationAnalyzerName
  && s[i].Result != nil`), with **no** Enabled/Live test. So when saturation binds it is both carrier
  and binder, `bByName` is built from the very slice the merge iterates, every lookup hits, and the
  else branch is unreachable. Reachable exactly when a saturation entry exists as carrier but does not
  bind. The coder's widening of the condition to `!(Enabled && Live && Informative)` is correct, and
  the reasoning is **stronger** than what it replaced: a structural proof rather than a claim about
  analyzer behaviour.
- **TA eviction** — `throughput/analyzer.go:160-161` deletes per-variant state past
  `2*DefaultObservationMaxAge`, with `DefaultObservationMaxAge = 30 * time.Minute`. So a lapsed variant
  does reach the branch having been measured. Exact.
- **Saturation holds a capacity this merge declines to borrow** — at zero ready replicas saturation
  falls to `capacityStore.Get` → `estimateStoredCapacity` (P0-store) or `lookupCompatibleCapacity`
  (cross-variant estimation), both yielding a **positive** PRC. The merge takes PRC from the binder, so
  it genuinely does not borrow it. Exact. (Note the package is `saturation_v2`, not the `saturation`
  path CURRENT.md cites.)

`maxTargetReplicas`' claim that *"for a variant without the tag the result is the `MaxReplicas` check
verbatim"* also holds: an untagged variant cannot enter the admission branch, so the function reduces
to `*state.MaxReplicas, true` when set and positive, else `0, false`. Its doc comment additionally
earns its keep by explaining why this is a function at all — two of the three grant sites treat *absent*
`MaxReplicas` as unbounded, so a ceiling folded into the existing headroom branch would be skipped on
exactly the configurations that do not set it, silently.

### Finding 54 — C9b adds a §4a token to the Type 4 dev guide, while its message reports only removals

C9b's message says *"C9e's ledger shrinks by the four tokens this commit removes."* True of
`analyzer_helpers.go`. But the same commit **adds** one to the dev guide, and fixes none of the three
already there:

| dev-guide §4a token-lines | base `075a208e` | C9a `757fc6f5` | tip `2ae440e3` |
|---|---|---|---|
| count | 0 | 3 | **4** |

The new one is `multi-analyzer-pipeline.md:565` — *"Whether the sentinel may instead enter the *voting*
set is an **N8** question; the reasoning is recorded at `ReasonFromZeroAdmission` in
`analyzer_helpers.go`."* Net across the tree is −4 **+1**, so the dev-guide sub-ledger of my 48-site
enumeration goes **3 → 4**, and the honest summary is "removes four, adds one," not "shrinks by four."

Severity is low and the fix is one line. The sentence's *second* half is exemplary — it points the
reader at in-tree reasoning, which is precisely what a Type 4 doc should do. Only the token fails,
because `N8` resolves nowhere in the merged tree. Naming the question instead of its identifier keeps
everything: *"Whether the sentinel may instead be written on the binding analyzer's own ballot entry is
an open question; the reasoning is recorded at `ReasonFromZeroAdmission`…"* — which, per the designer's
handoff, is exactly the question under consideration.

This also amends my own standing instruction to myself not to score those three dev-guide sites as C9e
misses "if C9b already fixed them": **it did not fix them.** All four remain C9e's.

### Finding 55 — `"This PR ships…"` is a PR-schedule reference in a Type 4 doc

`multi-analyzer-pipeline.md:531`: *"The rule above … has a narrow intended exception. **This PR** ships
the exception's *guard* and not its *trigger*."* Newly introduced (base: 0 occurrences, tip: 1).

CONVENTIONS' Type 4 rule is explicit — a reference doc *"must always reflect the actual code state of
the branch it is on. Do not include PR-schedule references."* On the merged tree there is no "this PR",
so the sentence dates itself the moment it lands, and after the next PR touches this area it reads as a
claim about the wrong change. The repair is trivial and loses nothing: *"The exception's guard ships;
its trigger does not."* The paragraph's substance — which half is live — is already carried by the
sentences around it.

Worth naming the irony rather than treating these as sloppiness: this subsection's entire purpose is
scrupulous honesty about dormancy, and it achieves that (P5 passes decisively) while tripping two
Type-4 hygiene rules on the way. Both are one-line fixes in prose the commit otherwise got right.

### The commit message itself is not §4a-clean — 19 of 22

C9a was the first §4a-clean message on this branch. C9b is not: its body carries `C9b`, `C11`, `(D-a)`,
`N5`, `N8`, `Finding 51`, `PR-2`, `P1`, and `Finding 29`. That takes the reword ledger to **19 of 22**
commit messages. As with the others this is a body-only defect and the sweep cost is unchanged in kind
— but it moves the count, and every commit that lands before the reword decision adds to it.

The `Finding 51` and `P1` / `Finding 29` tokens are the interesting sub-case: they are pointers into
**this review doc**, which is plans-branch-only. They are the same class as `Finding 47` (already
flagged as the least-resolvable token on the branch) — a reader of the merged tree cannot resolve
"Finding 51" even in principle, because the document defining it will never exist in that tree.

### Finding 51 — taken here, and rewritten rather than stripped

Confirmed **PASS**. The site (`analyzer_helpers.go:224-230`) is the binder tie-break, and the repair
fixed the tense error I flagged, not just the tokens: *"More than one non-saturation entry can qualify
here — `votingResults` caps neither the count nor the kind — and when several do, a later one does not
overwrite the earlier: it votes without binding."* Both `N2` and `PR-2` gone. The failure mode I named
in the P3/Finding-51 pairing — clean tokens, surviving falsehood — did not occur at any of the five
sites this commit touched.

### Tip-staleness is now a branch-wide pattern, not three separate slips

Not a code finding, but it bears on whether the artifacts I check code *against* can be trusted, which
is why I record it here rather than dropping it.

Four instances on this branch, across three different roles:

1. Three documents flagged for tip-staleness in `designer__t1-1-not-shipped-and-pending-edits-exists.md`.
2. The designer's own `plan__ta-anchor-da-sentinel-belongs-on-the-ballot.md` — labelled with a
   remembered SHA while its citations came from a dump read at a different tip; corrected by a sibling
   errata handoff (two line refs, no substance change) because the sender rule forbids editing a file
   already marked `.WIP`.
3. The coder's status file — a nine-commit gap earlier (flagged, then resolved), and stale by one commit
   again right now (`C9a LANDED — tip 757fc6f5` at `00:50Z` while the tip is `2ae440e3` from `01:21Z`).
   One commit mid-work is minor; the recurrence is the point.
4. CURRENT.md, which lags by design and which I have had to treat as a summary rather than a source
   throughout this review.

The mechanism is identical every time, and the designer diagnosed it precisely on themselves: *"I wrote
the citations from a `git show HEAD:` dump taken earlier in my session and labelled it with the SHA I
had recorded at that time, rather than re-reading `rev-parse HEAD` at authoring time. On a branch
committing this fast, a dump is only valid for the SHA you read it at."*

Three roles converging on one failure mode makes it a process defect rather than individual
carelessness, which puts it on the governance list beside the four `cd`-into-sibling slips. The
candidate rule is one line: **cite the SHA you read at, obtained at read time — never `HEAD`, and never
a SHA recalled from earlier in the session.** Concretely, `git show <sha>:<path>` rather than
`git show HEAD:<path>`.

Every citation in my own C9b verdict above is pinned this way (`git show 2ae440e3:…`), which is why the
errata's two corrections do not touch any of my numbers. I note that as evidence the rule is cheap to
follow, not as a claim to have been careful — I have four disclosed scope slips of my own on this
branch, in a different category.

---

## Pre-registration for C9c and C9d — four predictions, before either lands

Same discipline as the C9a and C9b pre-registrations: written against the committed tip `2ae440e3` and
the coder's own scoping, so the score cannot be adjusted after the fact. C9c is the `[sat, TA]`
multi-vote golden suite (encoding the `[sat]`-only and `[TA]`-only sub-cases) plus the Invariant 7
direct test, with the scale-down half of the deferred property and #1513 Finding 2's `withSatEntry`
stability rule folded in. C9d is the explicit removal of the #1513 sat-only goldens the new suite
supersedes.

C9d deserves the most scrutiny of anything remaining on this branch. Removing characterization goldens
is the one act in a PR of this shape that can shrink coverage while every gate stays green, and these
particular goldens were the **land-first ship gate** for the whole anchor refactor.

### Q1 — the removal must be proven per scenario, not asserted

**PASS:** a per-scenario mapping — each removed #1513 golden named, alongside the multi-vote scenario
that subsumes it, with the *asserted decision set* shown equivalent rather than the scenario name merely
matching. **FAIL:** a blanket *"the multi-vote suite supersedes these"* with no per-scenario
correspondence. That is the identical auditability gap I flagged for C9e and I will score it identically:
without the mapping, a silently-dropped scenario is indistinguishable from one correctly judged
redundant, and the reader cannot tell which happened.

### Q2 — the `[sat]`-only sub-case may not be equivalent to the standalone `[sat]`-only golden

This is a live hazard, not a hypothetical. #1513's own Finding 2 was a `withSatEntry` stability note,
and the coder has folded that rule into C9c — so the multi-vote harness demonstrably constructs the
ballot differently from the standalone goldens. If the harness adds an entry, the `[sat]`-only sub-case
travels a different combine path than the golden it replaces, and "we encode the `[sat]`-only sub-case"
would then be true of the name and false of the coverage.

**PASS:** the equivalence is stated and grounded — either the harness yields an identical ballot for that
sub-case, or the difference is named and argued harmless. **FAIL:** the sub-case is presented as
unchanged with no account of the harness difference.

### Q3 — the Invariant 7 direct test must discriminate

**PASS:** the test fails when the invariant is violated, either demonstrated or argued via the specific
mutation that would break it. **FAIL:** a test that passes whether or not the invariant holds. I have
audited test discrimination throughout this review and this is the same bar, not a higher one for the
last commits.

### Q4 — C9c's golden will freeze the unresolved ceil/floor fork

The strongest of the four, because it is already determined by the tip. `replicasToCover`
(`greedy_score_optimizer.go:837`) still computes `int(math.Ceil(entitlementGPUs / gpusPerReplica))`,
while plan §2d.5 specifies a whole-replica **floor** fill at `fairShareCap`. The coder's own scoping note
records that C9's quota-constrained multi-vote golden *also* exercises `fairShareValue`/`fairShareCap` —
which is why C9 was ordered after C6c in the first place. A golden authored now therefore encodes
**ceil**, the side of the fork the plan says is wrong.

**PASS:** the fork resolves before C9c lands; or the golden avoids asserting on a mid-replica boundary
where ceil and floor differ; or the commit names the exposure explicitly. **FAIL:** a golden that
silently freezes ceil. The tell is unmistakable — a golden introduced in this PR that a later commit in
the *same* PR has to move. That is exactly the attribution property the C6c-first ordering was
load-bearing for, so tripping it here would spend the ordering's whole benefit at the last commit.

### What I am not predicting

Nothing about C9e, which I have already enumerated per site (48 in scope, now **4** dev-guide rather than
3 after C9b). And nothing about gate results — I do not build or test in the coder's worktree, so
`make test` / `make lint` outcomes are the coder's to report and Dean's to accept, never mine to sign
off.

---

## The P/D scale-up break: verified live on this branch, but **inherited, not PR-2's**

The designer's `plan__ta-anchor-pd-fix-is-one-line-already-on-main.md` (cc'd to me, no action asked)
derives a break I had not found. I verified all six steps independently at `2ae440e3` via
`git show <sha>:`, and the chain holds:

| # | site | verified |
|---|---|---|
| 1 | `throughput/analyzer.go` sfz complement | builds `VariantCapacity{VariantName, PerReplicaCapacity, Reason}` — **no `Role`** ✓ |
| 2 | `distributeDemandByRole:923-926` | blank `Role` → `domain.RoleBoth` ✓ |
| 3 | `aggregateRoleCapacities` nil-guard | returns nil only when `len(byRole)==0 \|\| (len==1 && hasBoth)`; with prefill+decode+**both** `len==3`, so it does **not** fire ✓ |
| 4 | `initRoleState:377-385` | unions `roleSet[role]` over **every** voting entry with non-nil `RoleCapacities` ✓ |
| 5 | `:948-960` | `pick("both")` → `v == ""` → `allPicked = false` → inner `break`, then `if !allPicked { break }` **before** `nByRole` or any commit ✓ |

So the effect is as stated: on a disaggregated model with any previously-measured variant at zero
replicas, the whole model gets **zero** scale-up decisions, on the first iteration, before anything is
allocated. And TA does not need to win the bind — step 4 unions over the voting set, so TA being
`Enabled && Live` suffices while saturation holds the anchor throughout.

### Attribution — the part the handoff leaves ambiguous, and it changes the severity

"Already live on this branch" is true, and a reader can easily take it to mean PR-2 introduced it. It
did not. Two checks:

- The identical construction, **byte for byte**, is already at `075a208e` — PR-1's tip, PR-2's base.
- `git diff 075a208e..2ae440e3 -- internal/engines/analyzers/throughput/analyzer.go` filtered to
  `Role`-bearing lines returns **nothing**. PR-2 never touched it.

So this is **inherited from PR-1, fixed upstream by `a38d7b73` before PR-1 merged, and absent here only
because PR-2 is stacked on PR-1's pre-merge tip** (`merge-base --is-ancestor a38d7b73 HEAD` → ABSENT,
which I confirmed). It is not a PR-2 regression and must not be scored as one.

It is still a PR-2 *shipping* concern, for one reason that has nothing to do with fault: **if PR-2 opens
without rebasing, it presents a branch carrying a P/D break that `main` has already fixed.** The rebase
onto `main@57f3fe64`+ — already recorded as PR-2's target — resolves it for free, along with the other
three operator-visible fixes in `a38d7b73`. That makes the rebase the strictly better of the two shapes
the handoff offers, and it is the coder's/Dean's call, not mine.

### §3's general invariant is real but narrower than stated

The handoff generalizes to: "**any** voting entry that does not report per-role `RoleCapacities` injects
`both` into `roles`." The `else` branch at `:389-397` does do that. But the reachable set is small:
`saturation_v2/analyzer.go:136` **does** populate `RoleCapacities`, so saturation never takes that
branch on a P/D model — which is why P/D allocation works at all today, and why the observed break
comes from TA's own blank-`Role` complement rather than from a nil-`RoleCapacities` entry. Stated as a
conditional the claim is correct; stated as a live surface it overstates. Worth keeping straight,
because the narrow version is fixed by one line and the broad version would imply P/D is broken for
every multi-analyzer config, which it is not.

### PR-2 does not widen it — checked, because this is the half that would be mine

If any PR-2 change caused a voting entry on a P/D model to lose its `RoleCapacities`, that *would* be a
PR-2 regression. It does not. The `analyzer_helpers.go` delta touches `RoleCapacities` only to **read**
it (`rc, ok := e.Result.RoleCapacities[role]`) plus two comments, and adds no `RoleCapacities: nil`
producer anywhere. PR-2's new abstention paths (C6f abstain-when-unpriced, N7) abstain on
`PerReplicaCapacity <= 0`, which is a *value* test downstream of the key set — it cannot inject a role
key. Clean.

### One structural note that is mine and is new

`roles` is computed **once**, by `initRoleState`, *before* the `for anyRoleNeedsScaleUp` loop.
PR-2's `refreshAnchorSizing` runs **inside** that loop. So per-iteration dynamic re-binding — PR-2's
headline mechanism — **cannot heal a key-set mismatch even in principle**: the phantom `both` persists
across every iteration, and re-binding only ever refreshes *sizing* for keys already in the set. Not new
breakage, and not a defect in the re-binding design; but it forecloses an assumption someone could
reasonably make ("dynamic re-binding will re-derive the roles"), and it is the reason the repair has to
sit at the derivation rather than in the loop — which is the same conclusion the designer reaches from
the joint-commit side.

### Corroboration for Q4, from an independent read

The designer's withdrawal handoff independently verified that `math.Ceil` at `greedy_score_optimizer.go:837`
is the **only** `math.Ceil`-or-`Floor` in the non-test file, and that C6c landed as `34b18bc5`. That is
exactly my Q4 pre-registration: the ceil/floor fork is **unresolved at the tip**, and it is now formally a
doc-vs-code divergence (his `T1-1`) awaiting Dean — the frozen Type 1 mandates `floor`, the tree ships
`ceil` with a written justification. He withdrew its urgency and his C6c scheduling instruction, and
states the compiled branch is the safe side. Q4 stands unchanged: a C9c golden authored now still risks
freezing the side the Type 1 calls wrong.

### Tip-staleness, fifth instance — and this one is recursive

The pattern I recorded gains an instance from the same handoff. The designer told the planner its tip
table was "stale by one"; it was **four** (`b6bb525c` → `1a50b418` → `79a590d6` → `757fc6f5` →
`2ae440e3`). Self-diagnosed cause: he compared *subject lines* instead of running `rev-list --count`.
This is the strongest evidence yet for the candidate rule, because it is an error **in the correction of
a staleness error** — one layer up, same mechanism. His own framing is the right one to adopt: the useful
conclusion is not that everyone is sloppy, but that **a recorded SHA is worthless without a
`rev-list --count` against it**, and none of the four documents ran one.

### Finding 47 needs no action — my doc already closed it

§3 of the withdrawal handoff asks the planner not to route Finding 47 as owed work, because `79a590d6`
supplies the fixture. Agreed, and already recorded above at `## 79a590d6 … Finding 47 CLOSED` — including
the point that the commit **over**-delivered (five specs, not the one I proposed, with the untagged
negative control being the spec that makes the other four discriminating). The handoff I routed,
`plan__ta-anchor-c11-fillrole-clamp-untested.md`, is therefore overtaken; I do not edit it, per the
sender-never-edits rule, and the designer has now told its recipient.

One boundary to keep visible: `79a590d6` proves the *guard*, using a fixture-manufactured
`ReasonFromZeroAdmission` tag. That is the correct way to test a dormant guard, and it gives **no**
coverage of the *trigger*, because nothing in production writes the tag. That is not a gap in the test —
it is precisely Finding 46, and the two must not be collapsed into each other.

### Finding 56 — the one-line fix is `st.role`, not `vs.Role`, and that voids the shape-2 safety argument

Three parties now disagree about what the upstream fix actually says: the designer's handoff §2 states
`Role: vs.Role`; the planner's A36 corrects it to `Role: st.role`. The object is in the shared bare repo,
so this is settleable rather than arguable. At `a38d7b73`, hunk `@@ -408,6 +415,7 @@`:

```go
+			Role:               st.role,
```

**The planner is right.** The value comes from the *persisted* per-variant state, not from the
`VariantStates` loop variable.

This is not pedantry, because the whole safety case for shape 2 ("one line on the branch now") was that
the text is *identical to `main`*, hence a clean no-op at rebase time. Written as `vs.Role` it is a
**different expression**, so that argument fails on its own terms: even granting that `:253` keeps the two
in sync so behaviour matches, the rebase would then meet a real conflict on that line rather than a
no-op, and resolving it means re-deciding the same question under conflict pressure. Combined with the
attribution above, shape 1 (rebase) is now the better option on three independent grounds — it is due
anyway, it brings the two operator-visible fixes, and it is the only one whose safety argument survives
contact with the actual hunk.

### Finding 57 — the phantom bucket has a second, quieter consequence that neither handoff derives

Upstream's replacement comment at `a38d7b73` names **two** effects of a blank-role entry, not one:

> "would therefore manufacture a phantom `both` bucket — which **dilutes each role's demand share** and
> leaves the paired allocator unable to pick a variant for it"

Both handoffs derive only the second. The first is independently reachable and has its own blast radius.
`distributeDemandByRole:923-935` builds its role set with `RolePrefill` **excluded**, then computes
`share := demand / float64(len(roles))`. On a disaggregated model:

- correct: `roles = {decode}` → `len == 1` → decode receives the **full** model decode demand
- with the phantom: `roles = {decode, both}` → `len == 2` → decode receives **half**

So decode's arrival demand is understated by exactly **2×**, and that share flows into
`aggregateRoleCapacities` → TA's `RoleCapacities[decode].TotalDemand` → the engine's threshold post-step,
which is what writes per-role `RequiredCapacity`/`SpareCapacity`. Those are published values.

Why it matters separately from the break: the allocation `break` means no scale-up *decisions*, but the
corrupted per-role RC/SC is computed and **reported** regardless, on a path that does not depend on the
pick succeeding. So an operator watching per-role required-capacity sees a halved decode requirement,
which reads as a healthy under-subscribed role rather than as a stalled one. That is the same
failure-signature problem as the `OptimizationReady=True`-with-no-event bug `a38d7b73` also fixes: the
cluster stops acting and the telemetry does not say so.

Neither the designer's chain nor A36 is wrong; both simply stop at the loud effect. Recording the quiet
one because it survives every workaround that only addresses the `break` — including "turn the `break`
into a skip", which the designer already rejected for other reasons, and which would leave the dilution
fully intact while making the symptom *less* visible.

---

## The `fairShareCap` rounding fork: not a doc-vs-code tie, and the branch now argues both sides

Prompted by a low-priority hygiene item — pin the ceil-endorsing artifacts with exact SHAs so I do not
myself cite a stale one after writing about that failure mode. The pin turned into the finding below.

**Two hypotheses of mine, both falsified.** Recording them because each was cheap to test and each would
have retired the item wrongly.

1. *"There are two rounding terms and C6c already floors the mandated one."* `greedy_score_optimizer.go`
   `:698-699` does say the cap has two terms — *"the entitlement rounds up … while the real pool rounds
   down"* — so I checked whether the authority's `floor` names the pool. It does not. Type 1 `:1158-1160`
   writes `fairShareCap = floor(remaining_GPUs / GPUsPerReplica[vc])` and then mins the pool on a
   *separate* line, so `remaining_GPUs` is the entitlement. The mandate lands on exactly the term the code
   `ceil`s.
2. *"The frozen Type 1 contains both prescriptions, so the coder had contradictory guidance."* It does
   carry the retired `ceil(target · PRC_ref/PRC_vc)` shape at `:1135-1151`, but under an explicit
   **"⚠ SUPERSEDED by the GPU decision above — retained as the derivation only"**, and the superseding
   text says the `PRC_ref` map and its capture-ordering rule *"stop existing."* The authority is
   internally consistent. The coder had one prescription, not two.

So the designer's `T1-1` framing is right and mine was wrong. What the pin did establish is that the
divergence is **larger and better-anticipated** than a rounding preference.

### The mandate is four-part, and the branch inverts all four

Type 1 `:1163-1168`, verbatim:

> Note **`floor`, not `ceil`**: this is a budget, and a partial replica is not affordable. `ceil` was the
> pre-existing rounding and over-grants by up to one replica at every boundary; changing it is a
> **one-replica behavior change at the boundary** and needs a fixture that lands mid-replica, or it will
> not be observed. Flag it in the commit message — it is the one place the conversion is not value-neutral.

Transcribed into the Type 3 three times: row 6 of the unit table (`:951`), the C6c commit row (`:282` —
*"Status-quo-preserving **except** the `ceil → floor` boundary, which must be called out in the commit
message"*), and the value-neutrality row (`:1012`).

| the authority asked for | the branch at `2ae440e3` ships |
|---|---|
| `floor` on the entitlement | `ceil` — `replicasToCover:837`, `int(math.Ceil(entitlementGPUs / gpusPerReplica))` |
| the reason: a partial replica is not affordable | a 13-line counter-rationale at `:824-836` — the entitlement is *"a water-level gap, not a pool of GPUs on hand"* |
| *"a fixture that lands mid-replica, or it will not be observed"* | that fixture exists — `greedy_score_optimizer_test.go:1386`, `It("rounds the entitlement up to a whole replica and the pool down")` — asserting the **opposite** direction |
| *"Flag it in the commit message"* | flagged, arguing **for** round-up: *"The rule: round up when asking how many replicas a demand needs, round down when asking how many the pool can pay for"* (`34b18bc5`) |

Rows 3 and 4 are the ones that matter for review, because they are where a divergence becomes
undiscoverable. The authority required a mid-replica fixture *precisely so the change would be visible*;
the branch spends that exact fixture slot on freezing the pre-existing direction. And the
commit-message instruction is formally satisfied and substantively inverted — the message presents
round-up as *"the rule"* with no signal that the governing document says the opposite. **A reviewer
reading only this branch cannot discover that a divergence occurred.** That is the defect, and it is
independent of which direction Dean ultimately picks.

### The code's argument beats the Type 1's stated reason — and loses to the branch's own dev-guide

Worth saying plainly, because "coder ignored the spec" would be the wrong summary. The Type 1 justifies
`floor` with *"this is a budget, and a partial replica is not affordable"* — but its own next line is
`capN = min(fairShareCap, gpusAvail / GPUsPerReplica[vc])`. Affordability lives in that `min`. So the
Type 1 invokes a guard it has already installed elsewhere, and the entitlement's rounding is not an
affordability question at all; it is a **fairness** question — may a model owed a fraction of a replica
take a whole one. The coder's `:826-836` identifies this correctly and is the better-reasoned of the two
texts. The designer conceded the same ("the water-level-gap-not-a-pool distinction is exactly the right
axis").

On fairness, though, the branch's *own* Type 4 prose argues the other way.
`multi-analyzer-pipeline.md:801-807` bounds the indivisible-replica allowance to the **first** draw:

> On the model's **first** draw only, a role may additionally take one indivisible replica even when the
> balance no longer covers it … **Kept on past the first draw, that floor would be a per-iteration drip
> the entitlement never bounds.**

That is the same allowance `ceil` grants — except the documented mechanism is bounded to one draw and
implemented explicitly (`greedy_score_optimizer.go:453-456`), while `replicasToCover`'s `ceil` applies on
**every** draw. So the branch carries two mechanisms for one allowance: one bounded, documented, and
argued for; one unbounded, undocumented, and delivering what the dev-guide names as the failure mode.

**The falsifiable part, which I have not traced and am not asserting:** whether the unbounded form
actually drips. `W1`'s balance decrement (C6e) plus the `!allocated ⇒ remaining = -1` termination should
stop a repeat grant, and `:831` claims *"the caller's water-level check then stops it from taking a
second."* If that holds, the effect is a bounded one-replica over-grant per role per boundary rather than
a drip. Either way the redundancy stands, and the dev-guide's stated principle is the strongest argument
on the record for the authority's direction — sourced from the branch, not from the Type 1.

### The search surface: 8 endorsement sites, 1 reachable by the obvious grep

This corrects my own standing item, which named three artifacts and implied `ceil|floor` would find them.
Fork-relevant sites (`fairShareCap`/`replicasToCover` only — *not* the demand→replica `ceil` at Type 1
`:334`/`:609`, which is mandated and correct, nor the `combineVotes` up/down asymmetry at
`analyzer_helpers.go:629`/`:807`, which is not in dispute):

| # | site | `ceil`/`floor` token? |
|---|---|---|
| 1 | `greedy_score_optimizer.go:837` — the `math.Ceil` itself | **yes** |
| 2 | `:824-836` — `replicasToCover` doc comment | **yes** ("floored separately") |
| 3 | `:698-699`, `:704` — two-term cap comment at the call site | no ("rounds up"/"rounds down") |
| 4 | `:453-456` — first-draw indivisible-unit comment citing `replicasToCover` | "floor", but meaning a *minimum* |
| 5 | `:610` — "the indivisible unit: a role may take one replica" | no |
| 6 | `greedy_score_optimizer_test.go:1386` — the mid-replica fixture's name | no |
| 7 | `:1400` — that fixture's worked comment | no |
| 8 | `34b18bc5` — C6c's commit message body | no ("round up"/"round down") |

So a `git grep -i ceil` fix-up pass lands **1 of 8** — only #1. I previously wrote "2 of 8", which
credited #2 to the search; #2 says "floored", not "ceil", so the grep never sees it. Verified per line:
of `:453`, `:595`, `:659`, `:829` and `:837`, exactly one (`:837`) matches `-i ceil`.

Widening to `git grep -iE "ceil|floor"` reaches **3 of 8** (#1, #2, #4) and simultaneously surfaces two
hits that are *not* fork sites — `:595` ("Two floors keep the sequence from starving whoever draws
last") and `:659` ("See the second floor below"), both C6e additions in which *floor* means
**minimum**, not round-down.

Counted per token rather than per site, inside the one file that owns the policy:
`greedy_score_optimizer.go` carries four `floor` mentions (`:453`, `:595`, `:659`, `:829`) plus one
`math.Ceil` (`:837`), and **only `:829` is a round-down statement**. Three of the four say *minimum*. So
the widened grep's false-positive rate on the rounding question is 3:1 — the trap is not one line as I
first wrote, it is the dominant reading of the token in this file.

The plan's own incantation is worse than either. §6 specifies case-sensitive `grep -rn "ceil("`, which
across `internal/engines/pipeline/` returns **30 hits, every one of them in a `_test.go` file** and none
in non-test code: they are `ceil(x/y)` mathematical notation in test names and worked comments
(`It("computes max cross-analyzer ceil(roleRemaining/PRC)"`, `// cheap gets ceil(25000/10000)=3`)
describing the demand→replica conversion that is *not* in dispute. A coder running the plan as written
gets a wall of noise containing zero production sites. The coder's suggested `-i` repair reaches four
non-test sites across `internal/` — the fork at `:837`, plus `analyzer_helpers.go:629`, `rescale.go:598`
and `queueingmodel/analyzer.go:379`, the last of which its own count omitted by scoping to `pipeline/`.
All three of those stay.

My item was right that C6c's message endorses `ceil` and wrong that a token search would find it — the
message never uses either word.

Two consequences. Whoever flips the fork leaves at least five prose endorsements behind, including a
*test name* that then contradicts its own assertion. And #8 is the one that hardens: rewritable now while
the branch is unpushed, permanent once PR-2 opens. It joins the §4a reword window as a second,
independent reason that window is worth spending.

### Type 4 gap

No dev-guide text states the entitlement's rounding direction at all — `grep -i "fairShareCap\|
replicasToCover"` across `docs/` returns nothing. The Type 3 named *"pipeline 'Fair-share iteration'"* as
C6c's doc target, and that section (`:786-807`) documents the two floors and the first-draw rule but not
the rounding. On a change the authority itself calls a one-replica behavior change, that is a Type 4 gap
whichever direction survives; C9 is its natural host.

### Q4 resolves early — FAIL — in a unit test, not a golden

Pre-registered wording: *"**FAIL:** a golden that silently freezes `ceil`. The tell is unmistakable — a
golden introduced in this PR that a later commit in the same PR has to move."*

The freeze already happened, at `greedy_score_optimizer_test.go:1386`, and it is a unit test rather than a
golden — so the mechanism I predicted is exactly right and the artifact class is wrong. Scoring it FAIL
rather than N/A: the substance of the prediction was that this PR would lock in the disputed direction
before the dispute resolved, and it has. Had I kept watching only C9c I would have missed it, which is the
lesson worth keeping — **pre-register on the mechanism, then sweep every artifact class the mechanism can
inhabit**, not just the one the upcoming commit happens to use.

### Disposition

Not scoreable as a code defect while Dean's call is open, and I am not asking for a code change. Three
things are scoreable independent of his call:

1. **The divergence is undeclared.** The authority's own commit-message instruction was answered with a
   rationale for the opposite direction. Cost to fix: one sentence in `34b18bc5`, free while unpushed.
2. **The mandated observability fixture was spent on the opposite assertion** (`:1386`). If the fork
   resolves to `floor`, that test must be inverted or deleted — a cost the authority explicitly tried to
   pre-pay.
3. **Type 4 documents neither direction**, on a behavior change the authority flagged as non-value-neutral.

Routing to the planner as fyi, since T1-1 is already open with the designer and Dean; the new content is
the four-part inversion, the dev-guide counter-argument, and the 8-vs-2 search surface. Nothing here
needs the coder to stop.

---

## Finding 47 is closed by code, and `79a590d6` is the first fixture in this PR with a stated, correct mutation result

The designer's `plan__ta-anchor-designer-withdraws-t1-1-and-the-coder-accusation.md` §3 asks me not to
route Finding 47 as owed work, because the `fillRole` fixture already exists. Verified independently at
`79a590d6` rather than accepted: **closed, and closed better than I asked for.**

`79a590d6` *"pipeline: test the admission ceiling at fillRole (C11 D-b follow-up)"* — test-only, +73 in
`rescale_test.go`, a `Describe("fillRole")` block. My proposed assertion is present essentially verbatim,
including the trailing rationale string:

```go
Expect(spent).To(Equal(1), "the other 9 GPUs stay unspent and fall to the caller")
```

The commit message credits *"Raised by the PR-2 internal review as Finding 47"* and concedes the
pre-existing-gap point on its own initiative: *"fillRole had no direct test references tree-wide before
this; that gap is pre-existing and only the ceiling is covered here."* Shape 1 of my disposition question
— land the fixture with C11 while the code is fresh — is what happened. **Nothing carries into C9.**

### The discrimination claim: I suspected it of over-claiming and I was wrong

The message asserts *"Verified discriminating: all three ceiling specs here fail with the tag check
disabled."* On the first 95 lines of the diff I had three specs in view, one of which asserts an
**untagged** variant takes all 10 GPUs — which would obviously still pass with the tag check disabled.
I recorded that as a probable over-claim and went to count the specs.

There are **five**, and the word *"ceiling"* partitions them exactly. Traced against `rescale.go:431`,
whose inner loop breaks only on `bounded && targets[v] >= maxTarget` and otherwise runs until `wantGPUs`
is exhausted — so disabling the tag check drops `bounded` to false whenever `MaxReplicas` is unset:

| # | spec | tag | MaxReplicas | expects | tag check disabled |
|---|---|---|---|---|---|
| 1 | grants one replica out of the whole role's GPUs | admitted | nil | 1 | 10 → **FAIL** |
| 2 | does not top up on a second pass | admitted | nil | spent 0, target 1 | `bounded=false`, re-spends → **FAIL** |
| 3 | absorbs the whole role when the same variant is untagged | untagged | nil | 10 | 10 → **PASS** (control) |
| 4 | keeps honouring a configured MaxReplicas when it is the tighter bound | untagged | 3 | 3 | 3 → **PASS** (control) |
| 5 | takes the admission ceiling over a looser MaxReplicas | admitted | 8 | 1 | 8 → **FAIL** |

Three fail, two pass, and the two that pass are the ones that *must* — they are the negative controls
that make the other three mean something. The claim is precise, not loose: it says *the three ceiling
specs*, not *all three specs*. **My reading error, not the coder's over-claim** — I partitioned on
position in the diff instead of on the property each spec pins, which is the same class of mistake as
scoring Q4 on the artifact I predicted rather than the mechanism.

This is the structure I have been asking for across the whole sweep — positive specs plus controls that
survive the mutation, with the mutation result stated — and it is the first commit in PR-2 to ship it
unprompted. Spec 2 is the subtlest and the one I would not have thought to ask for: the ceiling is on the
*target*, not the invocation, so a pre-populated `targets` map at the bound must buy nothing. The code
comment at that line says exactly that, and the spec is what stops the comment from being a claim.

### A §4a false-positive trap: `T1-ols` is real code, not a plans token

Specs 3 and 4 set `untagged.Reason = "T1-ols"`. That is **not** a §4a violation and must not be swept:

- `itlReasonT1OLS = "T1-ols"` — `internal/engines/analyzers/throughput/constants.go:129`, *"tier-1: OLS
  fit from live observations"*, documented as a legal `Reason` at `internal/domain/analyzer.go:150`.
- The constant is **unexported and in another package**, so a `pipeline` test cannot reference it. The
  raw string is forced, and it matches the established idiom — 12 pre-existing occurrences in
  `analyzer_helpers_test.go` alone.

The trap for the C9e sweep: **`T1`/`T2` here are ITL *tier* names and collide in shape with the
plans-branch `T1-1`/`T1-7` identifiers this review and the designer's handoffs use.** A §4a grep for
`T1` scores **28 occurrences across 10 files** (`docs/developer-guide/cycle-log.md` included), and every
one is legitimate. This is the second trap of its kind in the sweep, after
`greedy_score_optimizer.go:453-456` — which contains the token *floor* while endorsing round-up. Both
say the same thing: **the token is not the finding**, and a sweep driven by grep hits rather than by
meaning will strip real code and miss real prose.

### Designer §4's tip correction, verified

Tip **is** `2ae440e3` — **22** commits off PR-1's base `075a208e`, working tree carrying one untracked
file, `optimizer_invariant7_test.go`. **C10 has landed** as `1a50b418`, so the branch is past it, not
"now on" it. My own doc already carries all twelve of the recent commits (`330fcd26` … `2ae440e3`), so
the record here needed no repair — but the designer's underlying point stands and is the right lesson:
a recorded SHA is worth nothing without a `rev-list --count` against it. Five instances of tip-staleness
across four documents now; this is the sixth check and the first to come back clean.

On T1-1 itself, the designer §2 withdraws its urgency and reframes it as a doc-vs-code divergence that is
Dean's call, with the compiled branch being the safe one. That is consistent with the preceding section
and does not change it: the reviewable defect is not which direction wins, it is that **the divergence is
undeclared**, the mandated mid-replica fixture was spent on the opposite assertion, and eight endorsement
sites would have to move together with only one reachable by the obvious grep.

### Finding 62 CLOSED — 21 of 25, agreed three ways; and the reword pass has its own trap

The coder accepted Finding 62 in full: *"I wrote 'C9e's own message is written token-free.' **That is
false.**"* It adds `a9afb740` to the reword list, and on the one disputed message it adopts my rule over its
own — `b106b929`'s only hit is *"PR-1's Test 9"*, and a PR reference resolves from `main`, so it is not a
violation. Denominator 25, numerator 21.

I re-derived it rather than adopting it, and **my first instrument was wrong in the same way Finding 60
was.** `\bC[0-9]+\b` cannot match `C6b`/`C6c`/`C6e` — the trailing letter breaks the word boundary — so my
first pass returned 18 of 25. Allowing an optional letter suffix gives 22, and one of those 22 is a false
positive: `757fc6f5`'s only match is *"every **V2** decision"*, which is the saturation engine V2, a real
in-repo identifier. 22 − 1 = **21 of 25**, agreeing with the coder and with my earlier count. That is now
the fourth instance of one shape — a sweep patterned on a sub-form of the thing it is checking — and the
third time it bit *my* instrument rather than the coder's.

**The trap in the reword itself.** A mechanical strip of all 21 would damage three legitimate classes,
visible in `4e369f10` alone: `A100`/`H100` are GPU models; `A1`–`A4` and `C1` are **golden scenario names
defined in the test file the commit removes**; only `C9d` is a plan-commit label. The same discrimination
C9e's repair applied to comments — mention-vs-use, and real-identifier-vs-plan-token — has to be applied
per message. The reword is 21 commits, not 21 sed invocations.

### Finding 64 — the fork's price was measured two commits before the mitigation that narrows it

This is the most consequential thing in this section, and neither the coder's close-out nor the designer's
withdrawal mentions it: **the 9-failure measurement that prices the fork was taken on a code shape that no
longer exists.**

The measurement is C6c's. The coder implemented the plan's `floor` (`wholeReplicaFill`) exactly as
specified, got **9 failures out of 334** with deltas up to −4 (`bv` 6→2 under an *unconstrained* budget),
diagnosed the cause, and backed it out. The diagnosis was precise and I verified it independently: `floor`
is not a smaller allocation, it is a **termination** — `capN == 0` returns an empty pick, `allocated ==
false`, and `fairShareScaleUp` sets `w.remaining = -1`, dropping the model from `active` permanently.

**What changed after the measurement.** `firstDraw` is **absent** at C6c (`34b18bc5`) and was introduced
by **C6e (`784c2b5c`)**, two commits later:

```go
capN := replicasToCover(share, gpusPR)
if firstDraw && capN < 1 {
	// ... First draw only: it grants past the balance, and only before the
	// first commit is an empty pick fatal to the whole model rather than a defer.
	capN = 1
}
```

That comment *is* the C6c eviction diagnosis, encoded as a fix. I verified the whole chain at HEAD:

1. `firstDraw := spentGPUs == 0` (`:660`) — true only when nothing is committed for this model yet.
2. The guard forces `capN = 1`, so the first draw cannot be empty when a priced, affordable,
   headroom-uncapped candidate exists.
3. `allocateForModel` returns **`w.remaining < oldRemaining`** — progress, not pick-emptiness.
4. So a non-empty first draw makes `allocated == true`, and `!allocated → w.remaining = -1` never fires.

**The guard is strictly more load-bearing under `floor` than under `ceil`.** `replicasToCover` returns 0
only when `entitlementGPUs <= 0`; otherwise `ceil ≥ 1`. So under the shipped `ceil`, `firstDraw && capN <
1` can fire *only* on an exhausted balance. Under `floor` it would fire whenever `0 < share < gpusPR` —
exactly the sub-replica-entitlement case that produced the eviction signature. C6e was written for the
`ceil` world and happens to be precisely the `floor` mitigation.

Compare the coder's own option (b): *"the honest fix is that `capN == 0` must mean defer, not evict, which
means `!allocated` can no longer unconditionally set `remaining = -1`, and that is a change to the loop's
termination argument."* C6e reaches the same end by the other route — rather than making `!allocated`
non-fatal, it makes the first draw non-empty so `!allocated` cannot fire for a model that has a viable
candidate. The work option (b) priced as "more than a one-line commit" is, for the dominant case, already
in the branch.

**Bound on this finding — what I am not claiming.** I have not re-measured. I do not build or test in the
coder's worktree, so no failure count from me is signed off. I claim the *mechanism* is neutralized for
the first-draw case, verified by reading; I do **not** claim the 9 becomes any particular smaller number.
Two residuals are untouched by the guard and would still bite under `floor`: draws after the first (where
`capN == 0` now genuinely defers, since `allocated` is already true — the intended behavior), and a model
whose first draw finds no priced or affordable candidate at all, which the fork does not affect either way.

**Why it matters as a review finding.** The close-out handoff says only that the fork "is still open in the
tree" and was "avoided by construction." The designer's §2 withdraws T1-1's urgency and reframes it as a
doc-vs-code divergence with "the branch currently compiled is the safe one." Both are true statements that
omit the same fact. The result is that **Dean is being asked to decide a fork priced at C6c, in a PR that
subsequently shipped the mitigation which addresses that price.** The refresh is cheap — flip `math.Ceil`
to `math.Floor` at `:837` and run the existing suite at HEAD — and it is the one input that would make the
decision informed rather than historical.

### Finding 65 — the refresh landed: mechanism confirmed, price narrower than either of us said

**RESOLVES Finding 64.** The coder re-measured (`plan__ta-anchor-ceil-floor-remeasured-at-head.md`):
`math.Ceil` → `math.Floor` at `:837`, full engine suite at HEAD `a9afb740`, then reverted — mutation
uncommitted, tree clean at `a9afb740`, suite re-verified green after revert, no golden adjusted, **no
verdict offered**. It also re-verified my three structural claims itself before running rather than
accepting them, and states plainly that 334-vs-386 is not like-for-like. That is the right shape for a
measurement handoff, and the discipline is worth recording separately from the number.

|  | C6c `34b18bc5` | HEAD `a9afb740` |
|---|---|---|
| failures | 9 of 334 | **5 of 386** |
| worst delta | −4 (`bv` 6→2, unconstrained budget) | **−2** |
| collapse-to-1 / eviction rows | 2 | **0** |

**Scored against the bound I set.** I claimed the *mechanism*, explicitly not a number, and named two
residuals. The mechanism claim holds: both rows whose signature was eviction are green under `floor` at
HEAD — `optimizer_equivalence_test.go` `bv` (the −4) and the `team-b` row — the `w.remaining = -1`
signature is absent from the output, and all five survivors are plain shortfalls (`2` vs `4` at `:175`
and `:230`; `2` vs `3` at `:1405`, `:1592`, `:1613`). Nothing returns 0 or 1.

**Correcting my own residual, against myself: the guard does more than I credited it with.**
`pick := fairShareRolePick(target, w.s, w.roles)` is constructed **inside `allocateForModel`** (`:490`),
so `committed0` is snapshotted per **model-turn**, not per cycle, and `firstDraw := spentGPUs == 0` is
therefore true at the opening draw of *every* turn. For a **single-role** model (`RoleBoth`) the opening
draw is the only draw, so the guard fires on every turn and residual 1 ("draws after the first") **does
not exist on that path at all**. It is a multi-role residual only, where role 2+ sees `spentGPUs > 0`.
The measurement corroborates this behaviorally rather than only by reading: the `team-b` assertion
(`:2185`, `dm["b"] > 2`) is single-role and recovers under `floor` at HEAD — which is what a per-turn
guard predicts and a once-per-model guard does not. Residual 2 (a first draw with no priced or
affordable candidate) is fork-independent and the run neither confirms nor refutes it.

**The coder's carve-out is right in kind and under-applied — the surviving price is 2 specs, not 4.**
It excludes `:1405` from the bill because that spec *is* a statement about the fork, and that is correct:
the name at `:1386` is *"rounds the entitlement up to a whole replica and the pool down"* and the comment
at `:1400-1402` argues the round-up in prose. But `:1592` and `:1613` are the **same class** — direct
`fairShareRolePick` closure calls asserting `capN == 3` for a 5-GPU draw at 2 GPUs per replica, with the
comment at `:1588-1589` saying *"5 GPUs at 2 per replica, rounded up."* Their *subject* is the
shared-balance ledger, but the number that moves under `floor` is the rounding, and the property each
spec exists to pin survives the flip untouched: prefill's `capN == 1` is 1 GPU at 1 GPU per replica
either way, so "the remainder, not a second copy of the entitlement" and "does not hand back the whole
entitlement next iteration" both still hold. So the honest split is **3 seam-expectation updates**
(`:1405`, `:1592`, `:1613`) and **2 genuine behavioral costs** (`:175`, `:230`).

**The 2 that remain are dearer than "one or two replicas short" reads.** Both are the Optimize()-level
design-doc walkthroughs, and the mechanism is not a single boundary rounding: the first-draw guard grants
exactly **one** replica where `ceil`'s cap covered the whole entitlement, and the loop then removes the
model for still being above the mean (`:308-312`, with `filterActive` keeping only `remaining > 0` at
`:742`) — so the recovery is bounded at one replica per turn rather than converging by re-picking. At
`:175` that is `a-v1` 4 → 2 in a two-model fixture whose pool comment reads *"4 replicas worth"*; at
`:230` the three-model priority-weighted split flattens. Whether the unspent headroom is Dean-relevant is
his call, but it should be presented as *pool GPUs left unallocated*, not as a rounding artifact.

**A general claim written into the file is refuted by this very run.** `:1387-1390` says: *"at Optimize()
level an understated cap costs iterations rather than replicas, because the allocation total is bounded
elsewhere and each iteration re-picks."* Under `floor` at Optimize() level it costs **replicas** —
`:175`/`:230` are exactly that level — because `:308-312` denies the unbounded re-pick the sentence
assumes. It is a `ceil`-world claim stated generally, and it is load-bearing prose for the fork's
justification, so it moves with the fork rather than surviving it.

**The endorsement footprint is larger than the 8 I counted.** My §6 correction counted 8 sites in
non-test `greedy_score_optimizer.go`, only `:837` reachable by `git grep -i ceil`. The test file adds at
least five more that must move together: `:1386` (the spec name, which must invert), `:1387-1390`,
`:1400-1402`, `:1560` (*"the round-up in `replicasToCover`"*), and `:1588-1589`. **None of the five
contains the token either**, so the grep-reachability figure stays 1 while the denominator grows to ≥13.
Keep this list distinct from the coder's "four other endorsement sites": three of those
(`analyzer_helpers.go:629`, `rescale.go:598`, `queueingmodel/analyzer.go:379`) are unrelated code that
**stays put**. One list is "must all move," the other is "must not be touched"; merging them is how a
mechanical pass damages the wrong sites.

**Scoping a sentence of my own that the run would otherwise falsify.** My note below on C9's goldens says
*"if the fork resolves to floor, nothing in the new suite has to move."* The measurement is the check on
it and it holds — **for C9's golden material specifically**: all five failures are in
`greedy_score_optimizer_test.go`, none in `optimizer_invariant7_test.go` or the C9c goldens. Read more
broadly than C9 it is now false, since two C6e specs are among the five. Scoped, it stands.

**Two small ones.** `:2154` is the `rB` fixture declaration; the assertion that actually fails is
`:2185` — harmless here, but citing the fixture instead of the failing line is the same
verify-the-pointer imprecision that made the competing tip-SHA claims expensive to check. And the
handoff's own framing *"all four are one or two replicas short at a mid-replica boundary — which is the
plan's own stop condition"* reads as if the plan's condition is met; on the split above, the two specs
that carry real cost are short by two, not one, and by a mechanism the plan did not anticipate.

**Net.** The fork is now priced on the shipped code rather than on a shape that no longer exists: no
eviction, worst delta −2, two behavioral specs plus three seam-expectation updates. That is a materially
smaller bill than 9-of-334-with-a-−4. The call remains Dean's and I am not making it; what changed is
that it is now informed.

Routed to the planner, which owns the fork's disposition ask and consumed the C6c handoff at its original
content. Re-measuring is a coder action and I am not directing it; the fork itself is Dean's call and I am
not making it.

---

## The partial-scale-from-zero verdict: Findings 56/57 confirmed by `main`, and the `[sat]` WORKS cell has two preconditions

`plan__ta-anchor-partial-sfz-per-config-verdict.md` (designer → planner, cc me, `ask: decide`) retracts
"nothing is broken" about partial scale-from-zero and traces it per config. Four of its claims bear on my
findings; I verified the two that are new rather than accepting them.

### Confirmed, and it upgrades Finding 56's evidence

**Finding 56 (`st.role`, not `vs.Role`) is now confirmed by `main` itself.** I derived `st.role` from the
in-house idiom — the live loop at `throughput/analyzer.go:400` uses `Role: state.role`, refreshed from
`vs.Role` each cycle at `:253`. The designer verified against `a38d7b73` in `Main/` and I re-ran it:

```
+			Role:               st.role,
```

Byte-identical. That matters beyond being right: it is what preserves the clean-no-op-at-rebase property
Dean's *"line now, rebase later"* depends on. Under the earlier `vs.Role` reading that property was void.

**Finding 57 (the 2× decode dilution) is credited as independently underived** — *"neither my earlier
handoff nor the planner's derived it."* And the provenance call in `386e6477` stands: PR-1-inherited, not
a PR-2 regression.

Also confirmed: `saturation_v2/analyzer.go` sets `Role: vs.Role` in the `append` **outside** the capacity
ladder, so it is set on every path including `satReasonNoData`. Sat cannot manufacture a phantom role
bucket. The asymmetry with TA is structural, not incidental.

### The three-tier ladder is real

Verified at `2ae440e3`, `saturation_v2/analyzer.go`: an `if / else if / else if / else` chain — live
median over ready replicas → own stored record (`capacityStore.Get`, `rec.EffectiveCapacity > 0`) →
`lookupCompatibleCapacity` cross-variant → `satReasonNoData`. And the design intent is written out at
`capacity_store.go:121-128`, verbatim as quoted: *"Provide a conservative capacity estimate so that
brand-new variants with no live data or compatible siblings can still be considered for scale-up."*

So the retraction is right and the `[sat]`-only config is the one that works **by design**, not by luck.

### But "called per-VA unconditionally — no pods required" is two claims, and only one holds

The pod-independence holds and is the load-bearing half: `LoadFromScaleTarget` parses the Deployment/LWS
**spec** via `ParseEngineArgs`, so a variant at zero replicas is fine. **"Unconditionally" does not.**
`internal/engines/saturation/engine_v2.go:38-50` — note the path is `engines/saturation/`, not
`engines/analyzers/saturation/` as cited:

```go
for _, va := range variantAutoscalings {
	key := utils.GetNamespacedKey(va.Namespace, va.GetScaleTargetName())
	scaleTarget := scaleTargets[key]
	if scaleTarget == nil {
		logger.V(logging.DEBUG).Info("No scale target found for VA, skipping capacity store pre-population", ...)
		continue
	}
	...
	e.capacityStore.LoadFromScaleTarget(namespace, modelID, va.Name, accelerator, gpuCount, scaleTarget)
```

So tier 2 has **two** preconditions, both pod-independent but neither vacuous:

1. **The scale target must resolve** in `scaleTargets[key]`. Miss ⇒ no pre-population, silently, at
   `DEBUG`. In the posed scenario the Deployment/LWS still exists (scaled to 0, not deleted), so this
   normally holds — which is why the verdict survives. It is a precondition, not a defect.
2. **The parsed engine args must yield a positive budget.** `capacity_store.go:126-128` sets
   `record.EffectiveCapacity = params.EffectiveMaxBatchedTokens` only
   `if record.EffectiveCapacity <= 0 && params.EffectiveMaxBatchedTokens > 0`. A spec that does not
   expose `--max-num-batched-tokens` (or an equivalent the parser recognises) leaves
   `EffectiveCapacity` at 0, so `rec.EffectiveCapacity > 0` fails and the ladder falls through to
   tier 3, then to `satReasonNoData`.

Neither breaks the retraction. Both matter because **§5's deferral grounds rest on the word "works"**:
*"partial scale-from-zero works in every config where saturation votes."* With the preconditions stated,
the accurate form is *works wherever sat can price the cold variant from spec or from a compatible
sibling* — which is the common case and a sound basis for deferring, but is not unconditional, and the
gap is **silent at DEBUG** exactly like the `[TA]`-only cell the deferral is about.

### The self-diagnosis survives one layer into its own correction

§2 of that handoff diagnoses §9's failure as *"mechanism-complete, use-case-blind"* — verdicts answering
a **consistency** predicate read as answers to a **liveness** predicate — and §2(c) names the specific
habit: *a caveat recorded, then dropped one line later.* That is exactly right, and it is the most useful
paragraph in the mission for how these docs should be audited.

It also recurs in the corrected text. §1.1's ladder is described tier-by-tier and correctly; the table
one screen up compresses it to **WORKS**, and the preconditions do not travel. Same shape, one layer
down, in the document written to fix it. Not a reason to distrust the verdict — the verdict is right —
but a reason to think the fix for §9 is **structural** rather than editorial: if a per-config table's
cells cannot carry their preconditions, the preconditions have to live in the cell (a footnote marker,
a third column) or they will keep being dropped by the next person who reads only the table. That is a
stronger version of the handoff's own proposed remedy (*"add a liveness verdict alongside the
consistency verdict"*), and it generalises past this one map.

### Not my call, and not blocking

`ask: decide` is addressed to the planner and the disposition is Dean's. I take no position on defer vs
close-in-PR-2; the review-relevant content is that the two findings the verdict rests on are confirmed,
one of them by `main`, and that the deferral's grounds should carry the two preconditions above rather
than the unqualified "works". Nothing here asks the coder to stop.

---

## C9c (`209e148f`) and C9d (`4e369f10`) — all four pre-registered questions scored

Scored against the bars I committed in `58b55399` **before** either commit existed, re-read first so the
scoring could not drift to fit what landed. C9c adds the multi-vote goldens plus the Invariant 7 direct
test (2 files, **+879**, no deletions); C9d removes the #1513 sat-only goldens (1 file, **+17/−352**).
Both verified tests-only by `--stat` and `--name-only`: **no non-test path is touched by either.**

### Q1 — PASS, and above the bar I set

My bar asked for "each removed golden named, alongside the multi-vote scenario that subsumes it, with the
*asserted decision set* shown equivalent rather than the scenario name merely matching." C9d's message
carries a seven-row table doing exactly that, one line per removed spec, literal decision set on the left.
Three things put it above the bar:

1. **Identity, not equivalence.** I spot-checked two of seven against the pre-image rather than trusting
   the table. Removed A1 asserted `{"v": {Replicas: 4, RequiredCapacity: 15000, SpareCapacity: 0,
   Utilization: 0.71}}`; M1's `shapeSatOnly` entry asserts the same map **byte-identically**. C1 →
   M7 likewise (`{Replicas: 2, RC 50000, SC 0, U 0.9}`). The transcription even carries its provenance —
   `// Transcribed verbatim from A1 (captured main@9906dac5)` — which is the right annotation for a
   characterization literal, because it records *where the number came from* and not merely that it was
   copied.
2. **Identity extended to the call, which my bar did not ask for.** The message claims the optimizer and
   constraints pairing was "verified pair by pair" and enumerates it. Checked on both spot-checks: A1 ran
   `CostAware(…, nil)` + `GreedyByScore(…, unlimitedConstraints("A100"))` and M1 runs that same pair;
   C1 was GreedyByScore-only with a quota/unconstrained pair plus a constrained-below-unconstrained
   check, and M7 reproduces that shape. A decision set can be preserved while silently losing an
   optimizer; this closes that gap.
3. **The one non-identical case is broken out rather than folded in.** The eighth removed spec — the
   harness smoke test, `{v: 2, RC 0, SC 0, U 0.5}` — is explicitly refused the word "identical" and
   labelled *subsumption*, with what survives (property and purpose, into M3) separated from what does
   not (its literal set, "because it was a different fixture"). That is the distinction whose absence I
   would have scored as the auditability gap, volunteered without being asked. It also checks out: M3
   mirrors A3's *two*-variant fixture, so the smoke test's single-variant literals are genuinely not
   reproduced anywhere, exactly as stated.

Also correct on the deletion-documentation rule: classified in terms, "a considered removal of superseded
coverage, not a deprecation and not a deferral," with the reason a characterization suite should *not*
outlive its refactor (leaving it on `main` would freeze today's allocation arithmetic as a permanent
optimizer contract). One piece of knowledge from the removed prose — CostAware ignores
`ResourceConstraints` entirely — was relocated to a named home rather than lost with its spec; verified
present in M7's header comment. Spec delta `394 → 386` matches the diff exactly: **8 `It(` removed, 0
added.** The three shared helpers survive (`expectDecisionSet:43`, `unlimitedConstraints:68`, and
`goldenDecision`, still referenced by `:43`'s own signature).

### Q2 — PASS on the first horn, verified in code rather than argued

The bar: "either the harness yields an identical ballot for that sub-case, or the difference is named and
argued harmless." It is the first, and it holds by construction, which is stronger than an argument.
`applyShape`'s `case shapeSatOnly:` is a bare `return req` — I read the case body rather than relying on
the header comment (*"shapeSatOnly deliberately touches nothing"*). So the `[sat]`-only ballot is
`withSatEntry(sat, req)`, the identical construction the standalone goldens used. The hazard I flagged —
that #1513's own Finding 2 `withSatEntry` stability rule implied the harness might build the ballot
differently — does not materialise: **the same helper builds both, so a future change to `withSatEntry`
moves the new goldens and the old ones together rather than sparing one.** That is the durability property
#1513 Finding 2 actually wanted, and it is now structural rather than remembered.

### Q3 — PASS, the sharpest discrimination account in the PR

Bar: "the test fails when the invariant is violated, either demonstrated or argued via the specific
mutation." `optimizer_invariant7_test.go`'s third spec does all three parts:

- **Named mutation, verified real.** The guard is `if len(s) <= 1 { return }` at
  `analyzer_helpers.go:661-663`, genuine code and not a comment.
- **Decidable outcome.** The fixture is deliberately out of step with the ballot — every sizing field
  differs from saturation's — so a refresh that ran would rewrite them and `Expect(variants).To(
  Equal(before))` fails. The test says so at the site, and says *why* the fixture is unrealistic:
  *"Nothing builds an anchor like this -- that is the point. The subject is the guard, not a realistic
  anchor."*
- **An in-test control.** The same call with a second voting entry *does* rewrite the slice, asserted
  immediately below. So the primary assertion pins the early return rather than an inert fixture.

And the boundary is stated: *"deleting the early return fails exactly one spec in the package, the third
one, while the two equality specs stay green -- which is why the equality specs alone were not enough."*
That is right, and it is the subtle part — the two equality specs use *realistic* anchors, where a refresh
that ran would recompute the same values, so removing the guard is semantically invisible to them. A
reviewer who only had the equality specs would have concluded Invariant 7 was covered when the guard was
untested. This is the second consecutive commit (after `79a590d6`) to ship the mutation result unprompted.

### Q4 — my prediction is falsified; the hazard was anticipated and neutralised

Stated plainly, because the polarity matters: Q4 predicted *"C9c's golden will freeze the unresolved
ceil/floor fork."* **It does not.** M7's quota fixture is deliberately constructed fork-neutral, and I
verified the arithmetic rather than the claim: `NamespacePools{"team-a": {"A100": {Limit: 4, Used: 2}}}`
at `GPUsPerReplica: 2` leaves exactly two free GPUs = exactly one replica, so `ceil` and `floor` agree and
no golden pins either side. The reasoning is written at the site, not just in the message: *"An exact
whole-replica entitlement, so the unresolved ceil/floor fork in `replicasToCover` cannot be frozen by this
golden either way."*

Consequences for my own committed finding, recorded honestly:

- **Item #1 (the divergence is undeclared) — remedied.** C9c's message states it (*"replicasToCover still
  rounds a GPU entitlement up where the plan specifies a whole-replica floor, and that fork is unresolved
  in this tree"*) and M7's comment states it again in code. A reviewer reading only this branch can now
  discover the divergence. That was the item I priced at "one sentence, free while unpushed"; it was paid
  from a different commit than I expected, which does not make it unpaid.
- **Items #2 and #3 — unchanged.** The mandated fixture still spends its assertion on the opposite
  direction, and the Type 4 doc still documents neither. The earlier freeze at
  `greedy_score_optimizer_test.go:1386` also stands: it is a unit test rather than a golden, so C9c/C9d's
  fork-neutrality does not reach it.

Net: the *mechanism* behind Q4 was real — a golden authored at this tip was in a position to freeze the
fork — and the coder saw it and defused it. Twice now on Q4 I have had to separate mechanism from
artifact; this time the separation lands in the coder's favour and I am scoring it that way.

---

## Finding 58 — a §4a site that two independent sweeps both missed, and the reason why

`internal/engines/pipeline/analyzer_helpers.go:659` carries, inside a shipped code comment:

```go
// combined-analyzer-optimizer-design.md § invariants #7.
```

That is a plans-branch document cited by filename and section from code that merges. It is unresolvable
for a reader of `main` — the same class §4a names explicitly. **New in PR-2**, not inherited: the grep is
clean at PR-1's tip `075a208e`, and `-S` places its introduction in `b106b929` (the per-iteration refresh),
which added two such citations. One of the two — `§ anchor` — was removed incidentally by C6a `8eb6ee2d`.
This one survives at the tip.

The interesting part is *why* it survived, because it was not for lack of sweeping. Two sweeps have run
over this ground and both missed this site:

- **The coder's own dedicated sweep, `4fb49ac6`** — literally titled *"drop plans-branch paths from
  shipped comments."* Its message even distinguishes the two classes: plans-branch **paths** are "a worse
  class than the bare plan tokens the cross-cutting sweep is scoped to." What it removed confirms the
  pattern it matched: `plans/session/handoffs/plan__…md`, a `Refs:` block of three `review__…md` names.
  Every removal carries a directory prefix or a `handoff`/`review__` shape.
- **My own 48-site enumeration**, which patterned on plans-branch *identifiers* (`T1-n`, `W-n`, `§`-refs).

This site is neither. It is a bare design-doc filename with no directory prefix and no identifier token —
so it falls in the **seam between the two patterns**, invisible to a path-shaped grep and to a
token-shaped grep alike. I am recording my own miss as prominently as the coder's, because the point is
not that either of us was careless: it is that **two sweeps patterned on two different shapes left a gap
exactly where the shapes did not overlap**, which is the concrete form of the argument I have been making
about grep-driven compliance. The fix for C9e is a *class*-based check — "does this comment name anything
a `main` reader cannot open" — not a third pattern.

**Disposition:** one line, comment-only, no code change. C9e is its natural host. Cheap now; it is the
kind of thing that survives to merge precisely because every individual sweep was scoped reasonably.

## Finding 59 — the `T1-ols` sweep trap grew by 13 inside C9c itself

Recorded as sweep-hazard evidence, not a defect: `T1-ols` is a legitimate ITL tier name
(`throughput/constants.go:129`, unexported, hence the raw string in `pipeline` tests). It now stands at
**35 occurrences across 11 files**, of which **13 are in the two files C9c just added** (12 in
`optimizer_multivote_characterization_test.go`, 1 in `optimizer_invariant7_test.go`).

So between my flagging the trap and C9e running, the trap grew inside the commit range the sweep must
cover — and every new occurrence is correct code that a `T1-` sweep must leave alone. Together with
`greedy_score_optimizer.go:453-456` (the word "floor" used for an unrelated rounding endorsement), the
C9e sweep now has two live traps pulling in opposite directions: strip a real identifier and you break
code, and both traps sit in files the sweep will open. This is the second independent reason the C9e
check should be class-based rather than pattern-based; Finding 58 is the first.

---

## Pre-registration: R1–R4 for C9e

Written **before C9e exists**, same reason Q1–Q4 were: a sweep commit is the easiest kind to rationalise
after the fact, and it can be rationalised in *both* directions — over-crediting a grep that came back
clean, or over-penalising a site correctly left alone. Committing the bars first is what makes either
verdict mean anything. The in-scope figure is now **49**: the 48 enumerated sites plus Finding 58.

### R1 — per-site accounting, not a count

**PASS:** every one of the 49 in-scope sites is either moved or explicitly named as not-moved with its
reason. **FAIL:** a summary count with no per-site trail. This is deliberately the identical bar I set for
Q1 and scored C9d against — without the trail, a missed site is indistinguishable from one correctly
judged out of scope, and the reader cannot tell which happened. Consistency here matters more than
severity: I should not hold a sweep to a looser standard than I held a removal.

### R2 — prose rewrite, not token strip. The load-bearing bar.

§4a's remedy is *"use descriptive prose instead"* — the identifier goes, the knowledge stays. The failure
mode that passes every grep while doing real damage is deleting `(W4)` and leaving a dangling sentence, or
deleting the comment wholesale, so the token count reaches zero and the reader loses why the code is
shaped that way.

**PASS:** each site's replacement carries the semantic content forward — a reader who never saw the token
learns what it meant. **FAIL:** tokens gone, content gone with them. Findings 51 and 53 are the two I
already flagged as specifically needing rewrites rather than strips, so they are the named test cases.
Precedent in the branch's favour: `4fb49ac6` handled exactly this correctly, saying the intent behind the
offending comments was right and *"the compliant form is to say so in prose, which is what they now do."*
That is the standard, and it was set by the coder, not by me.

### R3 — the two traps must survive untouched

**PASS:** `T1-ols` (35 occurrences, 11 files) and `greedy_score_optimizer.go:453-456`'s "floor" are
untouched; better still if the commit names them as deliberately-skipped false positives, since that
demonstrates the sweep distinguished them rather than never reaching them. **FAIL:** any legitimate
identifier stripped — code broken or prose falsified in the name of compliance. This one is mechanically
checkable and I will check it by re-grepping rather than reading the message: the count must still be 35
across 11 files, and `:453-456` must still endorse round-up.

### R4 — the inherited 7 must not move, and I must not score their survival

Pre-committing to this so I cannot drift into it. The inherited sites are out of C9e's mandate and have a
tracked home in `planning/governance-follow-ups.md`. **PASS:** they are absent from the diff, or noted as
tracked. **FAIL — on my side, not the coder's:** me reading a still-non-zero full-tree grep after C9e as a
sweep shortfall. Re-running the unrestricted grep *will* return hits, and the correct reading of that
number is "delta-only scoping worked as designed," not "the sweep is short." I have flagged this trap
twice already in this document; the point of writing it as a bar is that flagging it is not the same as
being immune to it.

### What would change my mind about Finding 58

Stated in advance for the same reason: if C9e leaves `analyzer_helpers.go:659` in place *and says why* —
for instance that a design-doc filename is judged materially different from a handoff path because the
design doc is the durable artifact — that is a defensible position and I will record it as a disagreement,
not a miss. What I would score as a miss is silence: the site absent from both the diff and the message.

---

## C9e — `a9afb740` — scored against R1–R4

**Commit:** `a9afb740` *"docs: make every reference in shipped comments resolvable from main"* — 15 files,
**+106/−83**. Comments and prose only, plus one disclosed identifier rename. Bars pre-registered in
`42229a1b`, re-read before the diff. **PR-2 is code-complete at this tip: 25 commits on `075a208e`.**

The title is already the answer to Findings 58/59. "Resolvable from `main`" is a **class**, not a pattern —
the reframing those findings argued for, arrived at without being told to.

### R1 — PASS in substance; the bar itself was mis-specified

**The count question resolves in the coder's favour, and my figure was the short one.** The close-out
handoff derives **54 introduced + 8 inherited** by `git blame` against `git rev-list 075a208e..HEAD`
*before* reading the planner's figure, converging with the plan's independently-reached "54 locations."
My pre-registration said 49 in-scope + 7 inherited. Both are correct **at their own tips**: C9c and C9d
*created* sites after my enumeration — 28 dangling `A1..C1` labels plus tokens in two new files. Mine was
as-of `2ae440e3`; the coder's is as-of `4e369f10`. Not a discrepancy — different clocks.

The inherited 7→8 gap is **my instrument**, not the coder's arithmetic (Finding 60). All 8 verified present
at HEAD and at base `075a208e`.

R1 asked for a per-site trail for all in-scope sites. **That was the wrong instrument for a sweep, and the
error is mine.** For C9d's deletions the trail was load-bearing because a silently-dropped scenario is
invisible without the pre-image. For a sweep the end state is **directly verifiable by me**: I ran the
class grep over `*.go` and `docs/`, and the only survivors are inherited. R1's purpose — no silent misses
— is met by verification. I record the letter as unmet and the bar as mine to have specified better,
rather than scoring a shortfall the artifact does not have.

### R2 — PASS, explicitly and by example

*"The repair is not a strip."* Verified: `"abstains (N7)" → "abstains"` where the prose already carried the
substance; `"C11's territory" → "the from-zero admission exception's territory"`; `"not C11's to close" →
"not this ceiling's to close"`; two sites where the referent had to be replaced rather than removed. Five
squash-falsified sites went first — the `optimizer_dynamic_refresh_test.go` header claiming "red before C2
and green after," an `optimizer_liveness_test.go` spec titled for "PR-2 C7," `k_sat_test.go:163`'s "Pre-C10
this priced at k = 0.85."

**One case exceeds the bar.** C9d's deletion of the A-definitions left the multi-vote tables' "M1 mirrors
A1" labels as 28 dangling references. Rewriting all 28 would have satisfied R2 and lost the mapping; the
seven names are instead **defined in that file's own header**, so the labels keep their referent and gain a
resolvable one. That is a repair of a regression the previous commit caused, caught without being reported.

### R3 — PASS, verified mechanically rather than from the message

Both traps survive: `T1-ols` still **35 occurrences across 11 files** (an unexported constant in another
package — stripping any breaks compilation), and `greedy_score_optimizer.go:453` still uses "floor" for the
indivisible-unit **round-up** policy. The message names both and says they were "verified and deliberately
left standing"; I checked the tree, not the claim.

### R4 — the guard fired, and I am obeying it

My class grep returns **2** surviving in-scope-shaped hits; the coder's broader instrument lists **8**. All
are inherited — present at base — and **all already ship in `main`** (verified against `upstream/main`).
Per R4 as written: *"the correct reading of that number is 'delta-only scoping worked as designed,' not
'the sweep is short.'"* Not scored as shortfall. They belong to the pre-existing `main`-side cleanup class
already tracked in `governance-follow-ups.md`.

### Finding 58 — closed, and better than the deletion I proposed

Grep for `combined-analyzer-optimizer-design` across `*.go` and `docs/` is now **empty**. The citation was
**repointed**, not stripped: `refreshAnchorSizing`'s single-vote no-op now cites
`docs/developer-guide/multi-analyzer-pipeline.md` § "Scale-up path" → "Per-iteration anchor refresh," on the
reasoning that *"deleting that citation would have cost a reader the explanation; the dev guide had acquired
it in the meantime."* My pre-committed "defensible disagreement" branch went unused — the site was neither
left silently nor stripped, and the message independently reconstructs the seam argument.

---

## Finding 60 — my own §4a instrument excluded a category the rule names

**Class:** reviewer-instrument defect. **Not a code finding.**

My sweep filtered candidate lines to `//` comments and `docs/` prose. `greedy_score_optimizer_test.go:810`
is `It("T1.3: priority × Score weighting drives fair-share ordering", ...)` — the token sits in a **test
description**, which §4a names explicitly alongside comments and commit messages. My filter excluded a whole
category the rule enumerates, which is why I found 2 of the 8 inherited sites.

This is the third instance of one shape, and the shape is the finding: **an instrument matched to a
sub-form of the question answers a narrower question than the one asked.** `4fb49ac6` matched *paths*; my
enumeration matched *identifiers*; my filter matched *comment syntax*. Each was internally consistent and
each left a seam. Only the class question — "does this name something a `main` reader cannot open" — spans
them, which is what C9e's title says.

## Finding 61 — the class has token-free members, so no pattern can ever span it

**Severity: minor** (inherited; out of PR-2's scope). Recorded because it settles the method question.

Three of the 8 inherited sites carry **no token at all**:

| Site | Text |
|---|---|
| `throughput/analyzer.go:362` | "diverging from **the plan's** specified RequestRate-weighted model" |
| `throughput/analyzer_test.go:1205` | "Specs 1–5 from **plan §3.4**" |
| `pipeline/analyzer_helpers.go:411` | "**Design § Architecture/D**: (model, role) is the unit of allocation" |

No `N`/`W`/`U`/`C`-family regex reaches these, and no path regex does either — they reference plans-branch
documents in ordinary prose. Any future §4a sweep specified as a token list is **guaranteed** to miss this
sub-class. The coder's class-based check found them; both prior pattern-based sweeps could not have.

## Finding 62 — C9e's own message reintroduces the token list it removed

**Severity: minor.** Affects the reword ledger, not the code.

Verified independently over `rev-list 075a208e..HEAD`: **21 of 25** commit messages carry a plans-branch
token. The close-out handoff says "21 of 24" — numerator exact, denominator one short (25 commits, not 24) —
and says *"C9e's own message is written token-free,"* which is **false as stated**: it contains
`N2, N3, N7, N8, W1, W4, U2, T1.4` and `PR-2 C2, C7, C10, C11, C6e, D-b`.

In substance the coder is nearly right — the tokens appear only as the **object of description**, and a
§4a-cleanup commit arguably cannot describe its own work without naming what it removed. But a `main`
reader meeting that enumeration in `git log` has exactly the problem §4a exists to prevent, and the rule
carries no quoting exemption. It should not be recorded as an exception. The fix in a reword is available in
the message itself: it already says "plan-item labels" and "per-commit labels" one clause earlier, so
dropping the enumerations costs nothing.

**Ledger for Dean: 21 of 25.**

## Finding 63 — `throughput-analyzer.md:609` is a broken link, filed under the wrong class

**Severity: minor** (inherited; a one-character fix). **Correcting my own near-miss:** I first read this as
a coder false positive because the filename exists.

`docs/developer-guide/throughput-analyzer.md:609` links `` [`saturation-scaling-config.md`](../saturation-scaling-config.md) ``.
From `docs/developer-guide/` the `../` resolves to `docs/saturation-scaling-config.md`, which is **absent**;
the real file is `docs/developer-guide/saturation-scaling-config.md`, in the same directory. The `../` is
one level too high.

So it *is* a genuine "not resolvable from `main`" site — but it is the `cmd/main.go:167` class (a stale
in-repo link) rather than the plans-branch-reference class the handoff files it under. Both are Dean's or
the planner's, not PR-2's. Worth stating precisely because **the filename existing is not the link
resolving**, and checking resolution rather than existence is what separated the two.

## Finding 47 — CLOSED by `79a590d6`, verified independently, exceeding the ask

I asked for roughly a 15-line `fillRole` fixture. `Describe("fillRole")` at `rescale_test.go:183` lands
**five** specs, and the discrimination is structural rather than argued: `wantGPUs = 10` against
`PerReplicaCapacity: 1`, `GPUsPerReplica: 1`, `MaxReplicas: nil`, so removing the clamp moves the result
1 → 10 — a **10× margin**, no interpretation needed.

| Spec | Role |
|---|---|
| grants one replica out of the whole role's GPUs | positive; my proposed assertion verbatim at `:213` |
| does not top up on a second pass | idempotence — the bound is on the target, not the invocation |
| **absorbs the whole role when the same variant is untagged** | **negative control**; "the measure of what the tag buys: 10 rather than 1" |
| honours a configured `MaxReplicas` when it is tighter | the ceiling does not displace the existing bound |
| takes the admission ceiling over a looser `MaxReplicas` | the interaction in the other direction |

The negative control is the spec my own bar would have asked for and my finding did not. The commit message
also concedes the reachability argument rather than restating it as its own: `fillRole`'s only pre-clamp
gates are `PerReplicaCapacity <= 0`, "which a sentinel at 1 passes by construction."

## Design question correctly routed, not decided — the `both`-shape publication split

Recorded as a **strength**, since the tempting failure here is a silent coder-side design fork.

With both analyzers voting, saturation binds the *anchor* — so model-level `RequiredCapacity`/`SpareCapacity`
stay saturation's — while the per-(role, variant) *sizing* binder is whichever entry demands more replicas.
Two published shapes follow and look like defects:

- **M1 `both`** publishes saturation's `RequiredCapacity` 15000 beside a replica count driven by
  throughput's 40000.
- **M2 `both`** publishes saturation's `SpareCapacity` 30000 on a decision **forbidden to spend any of it**
  — one live voter reporting explicit zero spare vetoes the role.

The coder froze both as goldens with the oddity named, and wrote *"I am not treating this as a bug; I am
refusing to decide it."* That is the right disposition: a golden that pins a possibly-wrong-but-specified
behavior **with the oddity stated** is auditable, and if the Type 1 moves, the goldens move with it. Quietly
"correcting" either would have been an unrecorded design fork inside a test commit. Routed to the planner as
a Type-1 question, which is where it belongs.

Note the same discipline on the rounding fork: the new suite avoids `replicasToCover`'s ceil/floor question
**by construction** — 1e6-GPU pools where the entitlement never binds, and a quota fixture leaving exactly
2 free GPUs at 2 per replica, where ceil and floor agree at 1 — with the exposure named rather than
implied: *"avoiding it is not the same as it being absent."* If the fork resolves to floor, nothing in the
new suite has to move.

## Finding 66 — `AD5` verified at HEAD: the conclusion holds, all three stated mechanisms do not, and the severity is understated

Three documents now describe `AD5`: the designer's Addendum-1 handoff, the coder's correction, and the
planner's verification. **All three reach the right conclusion — prefill is not sized during a saturation
outage — and all three name a mechanism that does not fire.** I verified the chain independently at HEAD
`a9afb740`. The conclusion survives; the placement advice in all three does not, and the consequence is
worse than any of them states.

Scope note first: **the disposition is the planner's and Dean's, not mine.** I am supplying the mechanism
and the severity, because the fix placement each document proposes would produce a predicate that never
fires, and because the severity gap changes what "defer" costs.

### What I credit

- The designer's `AD5` conclusion, and its instinct that `VG-up` is the trigger worth catching *before*
  the branch lands rather than after.
- The coder's catch that `AD5`'s `rescale.go:554-570` citation is a **stale-revision** citation, not a
  mis-numbering: bug #3 (`07b8fdb7` + `3c9d45bb`) moved sizing onto the ballot, and at HEAD `:597` reads
  `combineVotes(votesFromTotalDemand(s, role, bestVariant), true)`. Verified: the cited line range lands
  inside the *base* function's body. (One phrasing correction to the coder's own note, immaterial to its
  point: `952d2fff` is the 20th of 25 commits — five before the tip, not "20 commits before code-complete.")
- The planner's §3 correction of the `N7` mechanism. Verified at `analyzer_helpers.go:891`: a missing role
  key reads `if _, ok := e.RoleSpare[role]; !ok { continue }` — *"this analyzer doesn't decompose this role;
  abstain, not veto"* — and the function returns `liveCount > 0`. The veto framing was wrong; the
  disposition survives, and the planner is right that the framing matters because it makes a teardown look
  impossible when it is not.

### The decisive read: the anchor is built from the raw list, not the ballot

Every anchor construction passes the **unpruned** results — `bindingAnchor(req.AnalyzerResults)` at
`cost_aware_optimizer.go:48`, `:309`, `greedy_score_optimizer.go:171`, `:212`, `rescale.go:229`, `:346`,
`:492`, `:513`, `:624`, `:639` — while `votingResults(...)` is a *separate* call producing the ballot `s`.
And `bindingAnchor` locates saturation **by name, not by vote** (`:208-217`, whose comment says so
explicitly: *"It may be present even when it does not vote"*).

This is deliberate and it is correct: a stale saturation still carries the model's **identity** —
`AcceleratorName`, `Cost`, `Role`, `ReplicaCount` (`:279-284`) — so accelerator topology survives an
outage even though the stale entry is barred from voting. `VG-up` prunes the ballot without disturbing it.

Three consequences, each killing one proposed fix site:

1. **`AcceleratorName` survives**, so `variantsOnType(anchor.VariantCapacities, accType)` is non-empty and
   the reference-variant loop at `rescale.go:582-592` finds a candidate. The planner's §2 chain —
   `bestVariant == ""`, returning 0 *before* the combine — **does not fire.** (It would fire if TA were the
   identity carrier, since TA sets no `AcceleratorName` at `analyzer.go:398-408`; but that needs saturation
   absent from the results entirely, not merely stale.)
2. **TA prices live prefill variants.** The per-variant loop skips only on missing shape (`:297`), no ITL
   model (`:312`), non-positive `itlSat` (`:322`), and `supply == 0` (`:327`) — nothing role-gates
   `perReplicaSupply`, and the `RolePrefill` guard at `:364` scopes only the decode ITL/OL averaging. So a
   running prefill variant reaches `:398-408` with `PerReplicaCapacity > 0`, the merge's sizing lookup hits
   (`analyzer_helpers.go:286-291`), and the anchor's prefill PRC is **positive**. The `:292-302`
   "binder omits this variant" comment the planner cites describes a different case — a variant the binder
   *cannot* price, i.e. one at zero replicas.
3. **TA's `RoleCapacities` has a `prefill` key.** `Role: state.role` at `:400` → `AggregateByRole`
   (`aggregation.go:72-86`) → `aggregateRoleCapacities` (`analyzer.go:953-970`). So the ballot lookup
   `rc, ok := e.Result.RoleCapacities[role]` succeeds, and the coder's abstain branch — no role key, hence
   no vote — **does not fire either.**

### The operative mechanism: a real vote, honestly valued zero

With the key present and the PRC positive, `votesFromTotalDemand` (`:545-570`) emits a genuine vote whose
`Value` is `0 / prc` = 0. The zero is authored upstream, in `distributeDemandByRole:928`'s
`if role != domain.RolePrefill` exclusion — **deliberate and documented** at `:912-917`: both demand terms
are decode-rate-denominated, so there is no prefill-denominated demand to distribute. `TAdec` has no model
of prefill demand, and says so by producing nothing.

The zero then survives arithmetic that looks like it should round it away. `combineVotes(…, true)` returns
`(0, binder ≥ 0)`: the trust correction accumulates only where `excess := vt.Score - votes[b].Score` is
strictly positive (`:484-493`), so with a single vote the binder's own excess is 0, the correction is 0, and
the result is **exactly** 0 — not an epsilon that `int(math.Ceil(value))` at `:598` would lift to 1.

**So the state is "an analyzer that models this role priced it at zero", not "nobody priced it".** That
distinction is the entire placement problem: a hold predicate keyed on `binder < 0`, on an empty vote set,
or on `bestVariant == ""` — the three sites the three documents propose between them — **would not fire in
`AD5`'s own scenario.** This is the abstain-versus-veto seam PR-2 already settled for pricing, arriving
again one layer up; and it is the planner's own §4 question, which is therefore not a refinement to make
later but the precondition for the predicate existing at all.

Where the abstain branch *does* arise is the zero-replica corner: the from-zero complement leaves `Role`
unset (`analyzer.go:419-421`, deliberately), both `AggregateByRole:75-78` and `distributeDemandByRole:924-926`
coerce `""` → `both`, and `aggregateRoleCapacities:956` returns **nil** when the only key is `both`. A
predicate written for that corner and one written for `AD5` are not the same predicate.

### The gauge half is a second site, not the same one

`AD5`'s invisibility claim is live, and it is now a *separate* site from sizing.
`cost_aware_optimizer.go:350-367` still reads `anchor.RoleCapacities[role]` wholesale and assigns
`decision.RequiredCapacity` from it. Bug #3 moved **sizing** onto the ballot and left **observability** on
the anchor. Since the anchor's `RoleCapacities` is `binding.Result.RoleCapacities` verbatim (`:266`) and TA
binds, the prefill gauge publishes TA's structural zero.

Consequence for whoever fixes this: **a sizing-only fix leaves the operator-facing series at 0.** Two
sites, one per half of `AD5`.

### The severity: two scale-down paths, and a teardown nobody has named

The planner's §2 states that *"the scale-down gate does not [protect the role] either, because
`scaleDownVariantSet` consults neither `needsScaleDownForRole` nor `safeRemovalReplicasForRole`."*
`scaleDownVariantSet` is a **helper parameterised by a `maxRemovable` callback** (`:124-131`), so what it
consults is entirely up to its caller — and there are two, which differ exactly here:

**Path A — `scaleDownRoleIterated` (`:474-505`), reached from `cost_aware_optimizer.go:65` and
`greedy_score_optimizer.go:225`.** This one **does** consult both: the role gate at `:488` and
`safeRemovalReplicasForRole` as `maxRemovable` at `:498`. Under `AD5`'s preconditions those gates pass
rather than protect:

- Dispatch reaches it when `!anyRoleNeedsScaleUp(ps, roles)` (`:61-66`) — i.e. steady state. **No opt-in,
  no contention required.**
- `roleSpareVetoed(s, prefill)` is false: TA's prefill `SpareCapacity` is
  `TotalSupply − TotalDemand/scaleDown` (`engine_v2.go:474-506`, applied to registered analyzers too per
  `:91`/`:182`) with `TotalDemand = 0`, hence the **full prefill supply** — positive, so no veto.
- `needsScaleDownForRole` then counts TA as live-with-key → `liveCount == 1` → **true**.
- `safeRemovalReplicasForRole` min-combines `RoleSpare[prefill] / prc` ≈ the **entire prefill fleet**.
- `scaleDownVariantSet` sheds to `minReplicas` (0 when unset), with the cheapest-at-1 positional rule
  (`:159-161`) leaving exactly one replica on the cheapest prefill variant.

This path is **inherited, not PR-2's**: base `075a208e` had `safeRemovalReplicasForRole` at `:390` with the
same `!e.Live` / `prc <= 0` abstain structure and min-across-live semantics, and a stale saturation was
already skipped there by `!e.Live` regardless of ballot pruning. `VG-up` does not create it; it **widens
the window**, by removing stale-but-positive `RequiredCapacity` that would sometimes have diverted the
model to the allocate branch instead.

**Path B — `reclaimRole` (`rescale.go:404-427`), reached from `:382`.** This one consults neither gate: its
`maxRemovable` is a pure GPU delta (`remaining / g`, `:416-422`). The chain:
`demByRole[prefill] = roleDemandGPUs(...) = 0` → `distributeGPUsByWeight` (`:661-706`) reserves each role
only its floor and apportions the remainder by demand weight, so prefill receives
`roleFloorGPUs = minReplicas × GPUsPerReplica` = **0 when `minReplicas` is unset** → `rt < rc` → reclaim of
the role's whole GPU allocation. **The PRC ≤ 0 skip at `:139` does not protect a live prefill variant**,
because TA prices it (above). Narrower reachability than path A — rescale must be enabled for the scope and
the group contended (`:204-213`, `:239`) — but this half **is** newly unmasked by `VG-up`: pre-`VG-up` a
stale-but-enabled saturation sat in the ballot and kept `demByRole[prefill] > 0`.

**So `AD5`'s framing — *"a model that quietly stops scaling half of itself"* — understates it.** Under the
same preconditions the model does not merely fail to grow prefill; it **sheds prefill to ~1 replica** while
decode scales normally, and the prefill `wva_required_capacity` series reads 0 throughout. A missed
scale-up is a lost opportunity; this is an active drain on a role that is serving traffic.

This also corrects the planner's §1 cancellation story. Its claim — that the `PerReplicaCapacity <= 0` skip
is *"the only thing declining the prefill reclaim"*, hence that `(D-a)`'s deferral plus `AD3`'s scoping hold
the cancellation in place — **holds only for a zero-replica prefill variant.** For a *live* one TA already
supplies a positive PRC, so the skip is already not firing, and nothing downstream of it declines the
reclaim today. The coupling the planner wants recorded is real for the from-zero case and worth recording;
it is not what protects a running prefill role, because nothing does.

### Evidence status, and the test that would settle it

**PLAUSIBLE by reading, not CONFIRMED by execution.** I do not build or test in the coder's worktree, so
every step above is a source read, not an observed run. The chains are short and each link is quoted, but
the composition is exactly the kind of thing a fixture settles and eyeballs do not.

The decisive test is cheap and belongs with the `VG-up` commit: a P/D model, `[sat,TA]`, saturation
`Enabled: true, Live: false`, TA live and binding, prefill and decode variants each at ≥ 2 replicas, no
`MinReplicas`. Assert on the steady-state (path A) dispatch that prefill's target is **not** reduced. The
same fixture with rescale enabled and the group contended covers path B. Both should be red today if this
reading is right; if either is green, my chain is wrong somewhere and I would want to know which link.

### Two smaller items

**The designer's unverified tier-2 row — closed, and it does not widen the residual.** Neither precondition
blocks a zero-replica variant: the `engine_v2.go:38-53` prepopulate loop iterates `variantAutoscalings`
(VA *specs*, which exist for a scaled-to-zero variant) and its `:42` skip catches a **missing** scale
target, not a target scaled to zero; and `capacity_store.go:126-128` exists for precisely this case per its
own comment — *"so that brand-new variants with no live data or compatible siblings can still be considered
for scale-up."* The coder reached the same conclusion; I verified it independently rather than relaying it.
One sharpening the designer may want: on a freshly-constructed record `EffectiveCapacity` is always 0, so
`EffectiveCapacity <= 0 && EffectiveMaxBatchedTokens > 0` reduces to the second conjunct alone — the rung
is gated on the params being present, nothing more.

**My own authority line.** This review's header cites the frozen Type 1 and plan `1a116e7a`. Addendum 1 is
later and governs where they overlap, and is currently reachable only by filename — so I have added it here
rather than waiting on the Type-3 and CURRENT.md pointers, which are the planner's and sync's to place:
design authority for this review is `combined-analyzer-optimizer-design.md` (FINAL, frozen `8c2a9b04`)
**together with** `combined-analyzer-optimizer-design-addendum-1.md`, the latter governing on overlap.

---

## Finding 67 — `AD5` is CONFIRMED by execution; my attribution was wrong on one path and is *conditional* on the other

Three parties have now converged on `AD5` and each of us got a different piece wrong. This finding records
the corrections in the direction they actually run, including mine.

**Credit where it belongs.** The coder built the fixture I specified in Finding 66 §5, ran it as a scratch
diagnostic in the pipeline package, and deleted it (tip unchanged at `a9afb740`, `git status` empty, the 386
pipeline specs green throughout). Its measured result:

| prefill start | cost-aware | greedy | decode (control) |
|---|---|---|---|
| 2 | **1** | **1** | 2 ✓ |
| 4 | **1** | **1** | 4 ✓ |
| 8 | **1** | **1** | 8 ✓ |

Decode holds at its start in both optimizers, so the collapse is **role-selective** — the signature Finding
66 predicted. And prefill goes to 1 **regardless of where it started, in a single pass**. The coder is right
that this is worse than my own wording: *"sheds prefill to ~1 replica"* invites "loses a replica or two,"
while the measurement is that **starting size does not matter at all** — an 8-replica prefill tier sheds 7 in
one reconcile. The cost of leaving `AD5` open is not proportional to fleet size; it is the whole prefill tier
minus one, every time the window opens. **Finding 66's severity paragraph should be read with that
substitution.**

I also verified the coder's own strengthening refinement rather than relaying it: `distributeDemandByRole` has
**exactly two call sites**, `analyzer.go:478` and `:483`, and they are the sole constructors of both demand
maps. So TA reports prefill `TotalDemand == 0` for **every P/D model, always** — structural, not a
data-dependent edge case. The exposure is unconditional whenever TA is the only live voter.

### I was wrong about `reclaimRole`: that path is inherited

Finding 66 §2 called the `reclaimRole` half *"newly unmasked by `VG-up`."* **That is wrong, and the planner's
correction is right.** Checked at base `075a208e` rather than argued:

- Base `bindingAnchor:183` already reads **`RoleCapacities: binding.Result.RoleCapacities`** — binder-sourced,
  not carrier-sourced. So the anchor's prefill `RoleCapacities` came from the binder at base too.
- Base's binder gate is already `Enabled && Live && Informative`, so in the `AD5` fixture base **already bound
  TA** and already read prefill `TotalDemand = 0` off that anchor.
- Base `roleDemandGPUs` had no ballot parameter at all — the `s` argument is bug #3's addition.

So prefill's target already collapsed to its floor at base, `rt < rc` already fired, and base already
reclaimed the role's whole allocation. Ballot pruning cannot push a demand of 0 lower. Path B drains at base
unchanged, and my attribution there was simply a mistake.

### But the dispatch makes the *other* path conditional — and neither peer document checks it

Both peer documents treat `scaleDownRoleIterated` as flatly inherited. It is not, because **reachability** is
governed by a dispatch that reads the ballot *without* a liveness filter:

- Base `votingResults:234-240` prunes on **`e.Enabled` alone**; HEAD `:332-338` on `e.Enabled && e.Live`. That
  difference *is* `VG-up`.
- Base's dispatch is byte-identical in shape to HEAD's: `s := votingResults(...)` → `initRoleState(s)` →
  `if anyRoleNeedsScaleUp(ps, roles) { allocateForModelPaired } else { scaleDownRoleIterated }`.
- **`initRoleState` applies no liveness filter.** It sets `pickerState[i][role] = rc.RequiredCapacity` for
  every entry with a non-nil `Result` and non-nil `RoleCapacities` — dead entries included.
- **`anyRoleNeedsScaleUp` is a global OR across every entry and every role**: one positive `RequiredCapacity`
  anywhere returns true.

Therefore at base, a dead-but-`Enabled` saturation whose stale `RoleCapacities` carries **any** role with
`RC > 0` sends the model down the **scale-up** branch, and `scaleDownRoleIterated` is never reached — no
path-A drain at base. `VG-up` removes that entry; only TA remains; prefill's `RC` is structurally 0 and
decode's is covered; the dispatch falls through to scale-down and prefill collapses.

So **path A is inherited only when the dead analyzer's final snapshot has no positive `RC` on any role.**
Note the OR spans *roles*: a positive **decode** `RC` alone suffices to divert, which makes the diverting case
considerably broader than "prefill needed scale-up."

This is not a quibble, because it moves the planner's stated *basis* for deferring. Its counterfactual
dismissal — a protection that *"never existed in any shipped state"* — is correct for path B's demand-weight
route, but for path A the masking **did** exist in shipped base, via the dispatch. Base's behavior in that
case is of course its own bug (it scales up on stale data), so this is bug-masking-bug again; the difference
is that **this** masking shipped. For a saturation that dies holding any positive `RC`, PR-2 converts *"scales
up on stale data"* into *"sheds prefill to one replica."* The machinery is inherited; the reachability in that
reconcile is not.

### The floor at 1 is explained — and it is the path instrumentation the coder said it lacked

The coder flagged that it measured 1 and never 0, and that `reclaimRole` predicts 0, but did not chase which
path ran. Both questions have one answer. `scaleDownVariantSet:157-161` carries the **cheapest-at-1 positional
rule** (`#1237`'s): for the last, cheapest variant, when `current-n < 1` and no more-expensive variant still
holds replicas, `n = current - 1`. With a single prefill variant, `i == len(sortedVariants)-1` and
`sortedVariants[:i]` is empty, so it floors at **exactly 1 from any height, in one pass** — precisely the
measured table.

`reclaimRole` has no such rule; its `maxRemovable` is a pure GPU delta and would have produced **0**. **So
measuring 1 rather than 0 *is* the instrumentation: the confirmed runs took `scaleDownRoleIterated`, and path
B was not executed.** Two consequences: the coder's "either a clamp intervened or it took the
`scaleDownRoleIterated` path" is a single statement, not a disjunction — the clamp lives *in* that path; and
the confirmed table says nothing about path B. Which leaves the uncomfortable pairing that **the path whose
attribution is unconditionally "inherited" is the one nobody has run, and the path that has been executed is
the one whose attribution is conditional.**

### Status and the experiment that settles attribution

- **Path A (`scaleDownRoleIterated`): CONFIRMED by execution** — coder's diagnostic, both optimizers, 2/4/8
  all → 1, decode held as control.
- **Path B (`reclaimRole`): PLAUSIBLE by reading, unexecuted.** Inherited from base, per the correction above.
- **Attribution: CONDITIONAL, and settleable cheaply.** Run the same fixture at **base** in two variants —
  stale saturation `RoleCapacities` all-zero, and with any one role positive. Prediction: base drains in the
  first and **does not** in the second; HEAD drains in both. If that holds, "inherited" is the right word for
  the all-zero case only, and the positive-`RC` case is a reachability regression PR-2 authored.

I do not build or test in the coder's worktree, so everything above that is not the coder's table is a source
read at `a9afb740` and `075a208e`, quoted inline. The disposition — defer, fix, or file — remains the
planner's and Dean's; my only ask is that whichever word the Type 1 uses, "inherited" carries the condition
rather than dropping it.

---

## Finding 68 — my Finding 67 path instrumentation is wrong; `reclaimRole` honors cheapest-at-1 too. The base run confirms the branch of my prediction that was never in dispute, and cannot have tested the other one.

**Severity: correction (of my own Finding 67, and of one shared prediction). Evidence: source reads at
`a9afb740` and `075a208e`, plus the coder's base/HEAD execution table.**

Input: the coder's `plan__ta-anchor-ad5-attribution-settled-base-drains-identically.md` — it built the
instrument I named and ran it on **both** sides, in a throwaway detached worktree (`git worktree add --detach
/tmp/ad5-base 075a208e`), removed afterward, no branch moved. Its table:

| start (each role) | base `075a208e` | HEAD `a9afb740` |
|---|---|---|
| 2 | pf = **1**, dc = 2 | pf = **1**, dc = 2 |
| 4 | pf = **1**, dc = 4 | pf = **1**, dc = 4 |
| 8 | pf = **1**, dc = 8 | pf = **1**, dc = 8 |

### 1. Retracting my path instrumentation. The function's own doc comment says the opposite.

Finding 67 claimed *"`reclaimRole` has no such rule — pure GPU delta, would give **0**. So measuring 1 rather
than 0 is itself the path instrumentation."* **That is wrong.** `reclaimRole` does not implement its own
shedding loop — it *calls* `scaleDownVariantSet` (`rescale.go:415`) and passes a `maxRemovable` callback. The
cheapest-at-1 positional rule lives **inside** that helper (`cost_aware_optimizer.go:157-161`), so it fires
for **both** callers regardless of the callback. `reclaimRole`'s own doc comment states it plainly —
`rescale.go:402-403`, *"respecting minReplicas and **the cheapest-at-1 protection**, via
scaleDownVariantSet"* — and that comment is **byte-identical at base** (`075a208e:rescale.go:387-388`, with
the `scaleDownVariantSet` call in-body). I asserted the negation of a sentence written in the function I was
reasoning about; reading the callee's rule and not the caller's one-line delegation is the whole of the
mistake.

Consequences, in order of who they touch:

- **Mine.** The pairing Finding 67 closed on — *"the path whose attribution is unconditionally 'inherited' is
  the one nobody has run, and the executed path is the one whose attribution is conditional"* — **has no
  basis.** Both paths floor at exactly 1. **Which path either run took is unknown**, exactly as the coder
  said in its §3 (*"I did not instrument which gate either run took"*). Strike the inference; the two-sentence
  conclusion built on it goes with it.
- **The planner's.** Its §2 bullet — `reclaimRole` *"the role gets only its floor (0 when `minReplicas` is
  unset), so `rt < rc` and the whole allocation is reclaimed"* — predicts **0** by the same omission. The
  helper caps it at 1. Worth correcting because the coder has now flagged the mismatch twice as an
  unexplained residual against that prediction.
- **The coder's open item.** *"The floor at 1 is still unexplained"* — it is explained, and this is the half
  of Finding 67 that survives intact: cheapest-at-1, `if i == len(sortedVariants)-1 && current-n < 1 &&
  !anyHasReplicas(sortedVariants[:i], targets) { n = current - 1 }`. New here: the rule is **present at base**
  (`075a208e:cost_aware_optimizer.go:142`, same line), which is why the floor is 1 on both sides and at every
  height. A single prefill variant, last in cost-descending order with nothing more expensive still holding
  replicas, is floored at 1 from any height in one pass — whichever of the two paths ran.

### 2. What the base run establishes, and the one variable it did not vary

**Accepted without reservation: for the composition as specified, the drain is inherited.** Base and HEAD are
a tie at every height, decode holding as control. That is the planner's attribution claim, confirmed by
execution rather than reading, and it is now better evidenced than my Finding 66/67 reading of it was.

What it does **not** reach is the discriminating variable of my dispatch analysis, and the reason is a field
name. The coder's §2 refinement gave the dead saturation entry *"a non-zero stale prefill `TotalDemand`"* —
offered as the stronger case, which it would be if the dispatch read that field. It does not:

- `RoleCapacity` carries `TotalDemand` (`domain/analyzer.go:82`) and `RequiredCapacity`
  (`:88`) as **separate fields**;
- `initRoleState` seeds from `rc.RequiredCapacity` **only** (`analyzer_helpers.go:369-405`; the
  `greedy_score_optimizer.go:320` doc says so in words), and `anyRoleNeedsScaleUp` (`:709-718`) tests those
  seeded values;
- the only code that derives a per-role `RequiredCapacity` **from** a per-role `TotalDemand` is
  `applyUniversalThreshold` (`saturation/engine_v2.go:496-512`), which lives in the **saturation engine** and
  runs when that analyzer's result is post-processed — not when a hand-built `AnalyzerResult` is handed
  straight to an optimizer.

So a fixture that sets stale `TotalDemand` and leaves `RequiredCapacity` zero presents the dispatch with all
zeros — which is precisely the **all-zero-`RC`** branch of the prediction in Finding 67, the branch where I
already conceded "inherited" is the right word. The run confirms the half that was never in dispute.

### 3. What would refute me, stated as a one-line change

The untested branch needs the field the dispatch actually reads. At **base**, on the same fixture, set the
dead entry's `RoleCapacities[<any role>].RequiredCapacity` to any positive value — decode alone suffices,
since the OR spans roles — and re-run:

- if base **stops draining**, base's `Enabled`-only pruning was masking the drain through the dispatch, and
  `VG-up` makes it reachable in that reconcile;
- if base **still drains**, my dispatch reading is wrong and I retract it in full, with no residue: `AD5` is
  inherited unconditionally and the Type 1 should say so without the qualifier I asked for.

Two conditions on reading that result, both learned the hard way above: the run needs **path
instrumentation** (which of `scaleDownRoleIterated` / `reclaimRole` produced the target), because the outcome
value can no longer distinguish them; and `TotalDemand` must be left alone, so the only thing varying is the
field under test.

### 4. Standing

Unchanged: `reclaimRole`'s **machinery** is inherited — conceded in Finding 67 on base links
(`bindingAnchor:183` binder-sourced at base, base binder gate already `Enabled && Live && Informative`, base
`roleDemandGPUs` ballot-free) — and severity is unchanged and should not be softened. What is now weaker than
Finding 67 claimed is my knowledge of **which path executed**: none. What is unchanged is the dispatch reading
itself, which no run has yet addressed. I have corrected the record with all three recipients of Finding 67
rather than letting the pairing stand, and I flagged my own error before the coder or planner had to find it.
