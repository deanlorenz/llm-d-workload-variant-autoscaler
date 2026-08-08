# PR-2 rebase — `ta-anchor-dynamic-refresh` onto `main` (post PR-1 merge)

**Type:** pre-rebase plan (ephemeral — delete once the rebase is verified). Written per
`session/CONVENTIONS.md`'s non-trivial-rebase discipline: multi-commit stack (26, soon 27 with `C12`)
AND touched files have moved on the new base.

**Status: PLANNED, NOT EXECUTED.** Coder is mid-`C12`; do not run this until `C12` lands and gates are
green. This doc is the artifact that lets the rebase happen without re-deriving the analysis.

## Why the target is `--onto`, not a bare rebase

PR-1 (`ta-anchor-refactor-v2`) squash-merged into `main` as `57f3fe64`. PR-2's actual base,
`075a208e` (a real commit on PR-1's pre-squash branch), is **not an ancestor of `main`** — verified:
`git merge-base --is-ancestor 075a208e main` → no. `git merge-base HEAD main` → `aadaa596` (the commit
*before* PR-1 started). A bare `git rebase main` would therefore replay PR-1's entire 29-file diff as
if it were new, on top of a tree that already has it (squashed) — ~10 spurious conflicts, all noise.

**Correct command, from the `ta-anchor-dynamic-refresh` worktree, after verifying `pwd` + branch:**

```
git rebase --onto main 075a208e
```

This replays only PR-2's own 26 (soon 27) commits' diffs onto `main`'s current tip, skipping the
already-squashed PR-1 history entirely.

## Verified blast radius (read-only, `git merge-tree --merge-base=075a208e main HEAD` at `main@a6b39809`)

**2 files conflict. Everything else auto-merges clean.**

| File | Conflict | Resolution |
|---|---|---|
| `internal/engines/pipeline/analyzer_helpers.go` | `bindingAnchor`'s per-variant merge: `main` extracted a shared `buildCapacityMap` helper for the same map-building loop PR-2 built inline, with updated comment wording ("identity carrier" / "sizing", replacing PR-1-era "(a)"/"(b)" phrasing this branch's own C8 already retired) | **Take both**: call `buildCapacityMap(binding.Result.VariantCapacities)` (main's refactor) and keep PR-2's comment wording (the more current one — main's still frames it in "(a)"/"(b)" terms this branch deliberately dropped) |
| `internal/engines/pipeline/rescale.go` | `applyRescale`: both branches independently added the *identical* `if anchor == nil { return nil }` guard (right after `bindingAnchor(...)`), with different comment justifications for why it's needed now | **Keep the guard once** (duplicate, not divergent — no functional choice to make); either comment is accurate, pick one and drop the other |

Auto-merges clean: `throughput/analyzer.go`, `throughput/analyzer_test.go`, `throughput/itl_model_test.go`,
`pipeline/rescale_test.go`, `saturation/engine.go`, `saturation/engine_queueing_model.go`,
`saturation/engine_v2.go`.

**Full auto-merge log for the record** (base `075a208e`, ours `main@a6b39809`, theirs
`ta-anchor-dynamic-refresh@6d55fbd7`):
```
Auto-merging internal/engines/analyzers/throughput/analyzer.go
Auto-merging internal/engines/analyzers/throughput/analyzer_test.go
Auto-merging internal/engines/analyzers/throughput/itl_model_test.go
Auto-merging internal/engines/pipeline/analyzer_helpers.go
CONFLICT (content): Merge conflict in internal/engines/pipeline/analyzer_helpers.go
Auto-merging internal/engines/pipeline/rescale.go
CONFLICT (content): Merge conflict in internal/engines/pipeline/rescale.go
Auto-merging internal/engines/pipeline/rescale_test.go
Auto-merging internal/engines/saturation/engine.go
Auto-merging internal/engines/saturation/engine_queueing_model.go
Auto-merging internal/engines/saturation/engine_v2.go
```

## Ordered commit list — behavior to preserve, per commit (`075a208e..6d55fbd7`, oldest first)

| # | SHA | Behavior to preserve through the rebase |
|---|---|---|
| 1 | `680bebdb` | Deterministic binder tie-break (lowest analyzer index) replaces nil-on-ambiguity |
| 2 | `b106b929` | Per-iteration dynamic refresh — binder re-selects as remaining demand shifts mid-water-fill |
| 3 | `50034d15` | `roleAggRemaining` MAX in replica space, not raw mixed units (Bug #2) |
| 4 | `07b8fdb7` | `allocateForModelPaired` decrements per-analyzer by its own PRC, not the anchor's (Bug #1) |
| 5 | `3c9d45bb` | Rescale water-fill combines demand-to-GPU conversion across voters (Bug #3) + N3 nil-guard |
| 6 | `952d2fff` | Voting set liveness-gated (`Enabled && Live`); sizing fallback dropped (N8) |
| 7 | `1140a4c2` | `(a)/(b)` notation stripped from comments/docs; byte-identical behavior |
| 8 | `8eb6ee2d` | Cross-analyzer combine hoisted into one `combineVotes` helper; uniform scores ⇒ byte-identical |
| 9 | `d9f3b97e` | Score dominance weighting — `(sᵢ − s_bind)⁺` term; rounding once at the call site |
| 10 | `34b18bc5` | Fair-share claim converted to GPUs before comparing models (currency pivot) |
| 11 | `330fcd26` | Per-variant role-veto re-check (finding c) + scale-down tie-break moved here |
| 12 | `784c2b5c` | One fair-share entitlement per model, spent jointly across roles (`W1`) |
| 13 | `a679f2ad` | No-conversion-factor ⇒ abstain, not budget-exempt (`W4`), tested property |
| 14 | `537b0153` | Claim-pricing distortion pinned as a dormant, deliberately-red `PIt` spec |
| 15 | `4fb49ac6` | Plans-branch-path §4a strip; mean-claim fix — no behavior change |
| 16 | `a46c7eea` | Fair-share shared balance pinned, not just the per-role clamp |
| 17 | `eb12089a` | Mis-routed role label dropped from a shipped comment — no behavior change |
| 18 | `b6bb525c` | `(D-b)` one-replica ceiling at the three grant sites via `maxTargetReplicas` |
| 19 | `1a50b418` | `resolveKSat` — TA reads saturation's configured k_sat instead of hard-coded 0.85 (C10) |
| 20 | `79a590d6` | `fillRole` admission-ceiling test coverage (Finding 47 follow-up) |
| 21 | `757fc6f5` | Capacity-gauge currency gap + priority-idiom doc prose (`U5`/`W3`, docs only) |
| 22 | `2ae440e3` | From-zero admission documented as *built, not enabled*; four false premises fixed |
| 23 | `209e148f` | Multi-vote decision goldens + Invariant 7 direct test pinned |
| 24 | `4e369f10` | Sat-only characterization goldens removed, one-line-per-spec mapping to their multi-vote replacement |
| 25 | `a9afb740` | §4a sweep — every shipped-comment reference resolvable from `main`; one `max→maxRep` rename |
| 26 | `6d55fbd7` | The one authorized §4a residual: "Type-1 owner" → "analyzer-design owner" |
| 27 | *(pending)* | `C12` — `AD8` option (b), per [`ta-anchor-dynamic-refresh-plan.md` §2g](ta-anchor-dynamic-refresh-plan.md#2g-ad8) |

No commit here rewrites another's SHA (this is a fresh `--onto` rebase, not a history edit) — the
"behavior to preserve" column exists so the post-rebase diff check below has something concrete to
check against, not because any commit message is suspected of drifting from its diff.

## Post-rebase verification checklist

1. **Pre-rebase snapshot.** Before rebasing, record the pre-rebase tip (this doc's own commit range,
   `075a208e..<C12-sha>`) and run the full gate battery once more so there's a known-green baseline to
   diff against: `gofmt -l`, `go build ./...`, `go vet ./...`, `go test ./internal/...` (spec count),
   `make lint`.
2. **Per-file diff inventory** (CONVENTIONS' rebase-integrity step). For each of the two conflicted
   files, `git diff <pre-rebase-tip> <post-rebase-tip> -- <file>` and confirm the resolution above is
   what actually landed — `buildCapacityMap` called in `analyzer_helpers.go`, exactly one `anchor == nil`
   guard in `rescale.go`.
3. **Per-commit message-vs-diff check**, focused on the two touched files: for every commit in the
   26/27-row table above whose diff touches `analyzer_helpers.go` or `rescale.go`
   (`git log --oneline -- internal/engines/pipeline/analyzer_helpers.go internal/engines/pipeline/rescale.go`
   over the post-rebase range), re-read that commit's message against its post-rebase diff. The rebase
   only replays two files' worth of conflicts; every other commit's diff should be byte-identical to its
   pre-rebase form (`git diff <pre> <post> -- <commit's other files>` empty), so this check is bounded,
   not a full re-audit.
4. **Full gate battery again, post-rebase**: `gofmt -l ./internal/... ./pkg/... ./cmd/...` clean;
   `go build ./...` clean; `go vet ./...` clean; `go test ./internal/...` — same spec count as the
   pre-rebase baseline (currently 386 of 387, plus whatever `C12` adds); `make lint` — **note the
   toolchain moved under this branch** (golangci-lint 2.8.0 → 2.10.0, PR #1512, already on `main`), so a
   pre-rebase-green `make lint` does not carry forward; run it fresh regardless of step 1's result.
5. **`-race` on the fair-share + per-iteration-refresh suites specifically** — concurrency-sensitive per
   `session/CONVENTIONS.md`'s pre-push checklist and this plan's own §4.
6. **Backstop, if either conflicted file's post-rebase behavior is unclear from reading**: the existing
   spec suite already covers both — `analyzer_helpers.go`'s merge behavior via the anchor/binding
   characterization tests, `rescale.go`'s nil-guard via `applyRescale`'s own fixtures. A clean `go test`
   run over both is the practical backstop; no new test is needed solely for the rebase.
7. **DCO sign-off** carries through a `git rebase --onto` automatically (it replays commits, doesn't
   strip trailers) — verify anyway per CONVENTIONS: `git log <pre-rebase-tip>..<post-rebase-tip> --format="%b" | grep -c Signed-off-by` should equal the commit count.
8. **Do not push after this rebase without Dean's explicit confirmation** — this is the rebase that
   orphans `origin/ta-anchor-dynamic-refresh@f6485980` (already orphaned by PR-1's own reword; this
   rebase changes the base further) and needs `--force-with-lease`, stated as such when asking.

## Who runs this, and when

Coder's action, once `C12` is committed and its own gates are green — this rebase is **separate from**
`C12`'s implementation and should not be interleaved with it (rebasing mid-feature-commit risks exactly
the kind of silent hunk loss CONVENTIONS' rebase-integrity section warns about). Sequence: finish `C12`
→ verify `C12` alone → run this rebase → run the checklist above → report back before any push.
