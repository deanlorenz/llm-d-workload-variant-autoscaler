# ta-anchor-dynamic-refresh (PR-2) — Internal Review

**Type:** 6 (review) · **Status:** DRAFT (partial — C1–C5, C7, C8, C6a, C6b reviewed; C6c, C6d, C10,
C9 not yet landed) · **Branch:** `ta-anchor-dynamic-refresh`, tip `d9f3b97e` (base
`ta-anchor-refactor-v2@075a208e`, stacked/parallel per §0) · **Reviewed against:**
[`planning/ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) **at plan revision
`1a116e7a`** §1.1 commit map, §2d score semantics, §4 ship gate, §5 dev-guide map, §6 semantic-pivot
grep · **Reviewer:** internal (this session) · **Date:** 2026-08-06 → 2026-08-07 (rolling).

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
`C1–C5 → C7 → C8 → C6a–C6d → C10 → C9` — the C-labels are stable identifiers, not a sequence.

Reviewed so far: C1 `680bebdb`, C2 `b106b929`, C3 `50034d15`, C4 `07b8fdb7`, C5 `3c9d45bb`,
C7 `952d2fff`, C8 `1140a4c2`, C6a `8eb6ee2d`, C6b `d9f3b97e`. Still to come: C6c (fair share —
highest-risk commit on the branch), C6d (role-level veto; owns Finding 4), C10 (`resolveKSat`),
C9 (dev-guide + goldens endgame). Each commit is diffed against **PR-1's tip `075a208e`**, not
`main`, and every gate is re-run by me on a clean `git archive` extract rather than taken from the
coder's report.

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

[Back to plan](ta-anchor-dynamic-refresh-plan.md)
