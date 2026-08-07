# ta-anchor-dynamic-refresh (PR-2) — Internal Review

**Type:** 6 (review) · **Status:** DRAFT (partial — C1–C5, C7, C8, C6a, C6b reviewed; C6c, C6d, C10,
C9 not yet landed) · **Branch:** `ta-anchor-dynamic-refresh`, tip `d9f3b97e` (base
`ta-anchor-refactor-v2@075a208e`, stacked/parallel per §0) · **Reviewed against:**
[`planning/ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) (tip `62c37c46`)
§1.1 commit map, §2d score semantics, §4 ship gate, §5 dev-guide map, §6 semantic-pivot grep ·
**Reviewer:** internal (this session) · **Date:** 2026-08-06 → 2026-08-07 (rolling).

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
   `μ = (0.5·1024000/4600)/(0.073·0.5+0.006) = 111.30/0.0425 = 2618.9` — a 5.8% drop from 2780.56, which
   *does* clear ±10%… but only just. If the coder writes that fixture with a tolerance ≥ ~6% it asserts
   nothing.

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
- Confirm the `KvCacheThreshold: 0.5` fixture's tolerance is tight enough to actually fail at 0.85.
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
  Still best handled as one sweep commit near the end.
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

[Back to plan](ta-anchor-dynamic-refresh-plan.md)
