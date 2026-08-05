last_update: 2026-07-30T13:45:00+03:00
state: in-progress
current_step: second rebase (onto #1486) complete, all gates green, fresh review requested (this rebase carries a real logic change, not a pure replay)

## Branch
ta-gate-observability at ta-gate-observability/ ; tip 1a6d2fd3 (rebased onto upstream/main da58c0e0, PR #1486 ScalingPolicy Phase 1 merged; supersedes tip 9062ebd2 based on f9f04d81). PR #1502 open on this branch (base main, was CONFLICTING before this rebase).

## Pre-rebase plan (2026-07-30, trigger: ta-gate-observability__upstream-rebase.md)
Rebase target: `upstream/main` (moving ref), currently `f9f04d81` — one hop ahead of my base
`f5261c8e` via PR C #1480's merge commit.

Commits to replay, one-line behavior to preserve each:
- `033b0529` refactor — `ThroughputAnalyzerEnabled()` extracted onto `config.Config`; boolean
  result identical to the old package-main predicate for every input.
- `67ac0476` feat — `ConfigMapReconciler.ThroughputRegistered` field + Warning event
  (`ThroughputAnalyzerRestartRequired`) + restart log on global-ConfigMap TA-enablement
  divergence from the frozen startup decision; namespace-local excluded.

Expected conflict surface: C's diff (`f5261c8e..f9f04d81`) touches `docs/developer-guide/
throughput-analyzer.md` at hunks starting L368, L448, L517, L594 (all in the "Demand Estimation"
section) — my Commit 2 touches the same file but at L18-32 (Overview/Enablement callout, well
above C's hunks). No other file overlap: C touches `internal/collector/replica_metrics.go`,
`internal/collector/registration/throughput_analyzer.go`, `internal/domain/analyzer.go`,
`internal/engines/analyzers/throughput/*`, `internal/engines/saturation/engine*.go`,
`internal/constants/metrics.go`, `docs/developer-guide/multi-analyzer-pipeline.md` — none of
which I touch. Expect a clean, conflict-free rebase.

Post-rebase verification checklist:
1. Per-file diff inventory: `git diff <pre-rebase-tip> <post-rebase-tip> -- <file>` for each of
   my 5 touched files + dev-guide; confirm no hunk was dropped/altered by the 3-way merge.
2. Per-commit message-vs-diff check: re-read both commits' diffs against their messages.
3. Full gate re-run: `make test`, `make lint`, `gofmt`, `go build`, DCO, §4a grep.

## Post-rebase result (2026-07-30)

Rebase completed with **zero conflicts**, confirming the pre-rebase file-overlap analysis: `git
rebase upstream/main` applied both commits cleanly. Verification:

1. Per-file diff inventory — all 6 files not touched by C (`cmd/main.go`, both `internal/config/`
   files, `internal/constants/constants.go`, both `internal/controller/` files) are **byte-
   identical** between the pre-rebase tip (`67ac0476`) and post-rebase tip (`9062ebd2`) via
   `git diff 67ac0476 9062ebd2 -- <file>` (empty output). `docs/developer-guide/
   throughput-analyzer.md` differs only by C's own content (verified the diff between the two
   tips contains exclusively C's "Model-Level Decode Demand" rewrite, none of mine); my added
   paragraph ("Editing the ConfigMap without restarting is surfaced, not silent...") is present
   verbatim in the post-rebase file via `git diff f9f04d81 HEAD -- <file>`, isolated as a clean
   11-line addition with no interaction with C's hunks (confirming the pre-rebase L18-32 vs
   L368+ non-overlap prediction).
2. Per-commit message-vs-diff check — both commits' `git show --stat` output (file lists,
   insertion/deletion counts) is unchanged from pre-rebase; messages still accurately describe
   the diffs (deletion count in Commit 1 was already off-by-N by design since `cmd/main_test.go`
   deletion is a rename target, not new — confirmed no drift).
3. Full gate re-run: `go build ./...` clean, `gofmt -l` clean, `make test` exit 0 (full suite incl.
   `internal/controller` envtest), `make lint` 0 issues, DCO 2/2 signed, §4a grep clean.

New tip `9062ebd2` supersedes `67ac0476` everywhere (status file, handoffs). Old tip is dangling
(not referenced elsewhere) — no cleanup needed, will be GC'd. Not pushed (origin still tracks the
pre-rebase / empty-base ref); awaiting Dean's confirmation before any push.

## Second rebase (2026-07-30, trigger: ta-gate-observability__rebase-1486.md)

Upstream merged **#1486** (ScalingPolicy Phase 1) while PR #1502 (opened from the previous
rebase's tip `9062ebd2`) was open, putting #1502 into `CONFLICTING`/`DIRTY`. Per the plan's
rewritten Pre-push step 0, rebased onto `upstream/main` (now `da58c0e0`) and resolved:

1. **`cmd/main.go` — real textual conflict**, at two sites: (a) delete/modify on the whole
   `throughputAnalyzerEnabled` function (my Commit 1 deletes it; #1486 had edited it in place to
   use `aw.EffectiveType()` instead of `aw.Name`) — resolved by taking the deletion (function is
   being extracted, not kept) since the extraction target already needed the same fix; (b) two
   adjacent edits to the same line (my call-site swap vs #1486's new `SetLimiterBuilder` block
   inserted just above it) in both Commit 1's and Commit 2's replay — resolved by keeping both.
2. **`internal/config/config.go` — silent semantic gap, exactly as the plan predicted**: my new
   `ThroughputAnalyzerEnabled()` method auto-merged cleanly (#1486's diff never touches it — the
   method didn't exist on `main` yet) but still compared `aw.Name`, which would have silently
   diverged from #1486's `aw.EffectiveType()` convention everywhere else. Applied the plan's
   specified fix by hand: `aw.Name ==` → `aw.EffectiveType() ==`. Added 2 test cases (Type
   overriding a different Name to enable; Name matching but Type overriding to disable) — the gate
   now honors `type:` the same way `engine_v2.go`'s analyzer-matching does.
3. **Commit message accuracy**: Commit 1's original message claimed "pure refactor, boolean result
   identical for every input" — no longer true post-EffectiveType-fix, so amended it (via
   `git rebase -i` stopping at that commit) to describe the behavior change and its test coverage,
   per CONVENTIONS "commit messages must reflect the diff."

New tips: **`5614afb4`** (Commit 1, amended) and **`1a6d2fd3`** (Commit 2) — supersede `cade59b0`/
`def0ceeb` (intermediate, pre-amend) and `9062ebd2`/`033b0529`/`67ac0476` (pre-#1486-rebase).

Post-rebase verification: files not touched by #1486 (`internal/constants/constants.go`, both
`internal/controller/` files, `docs/developer-guide/throughput-analyzer.md`) confirmed byte-
identical between the pre-this-rebase tip (`9062ebd2`) and new tip via `git diff 9062ebd2 HEAD --
<file>` (empty). Both commits' `git show --stat` re-checked against their messages. Full gates:
`go build` clean, `gofmt -l` clean, `make test` exit 0, `make lint` 0 issues, DCO 2/2, §4a grep
clean.

**This rebase is not a pure replay** — it carries a real behavior change (the `EffectiveType()`
fix). Per CODER-CONVENTIONS §5.4 ("routine rebase-only pushes... are exempt" from re-review,
implying non-routine ones are not), wrote a fresh `review__ta-gate-observability-ready.md`
trigger rather than relying on the prior "ready to push" verdict, which predates this logic
change. Still not pushed — PR #1502 stays `CONFLICTING` on GitHub until the planner force-pushes
with Dean's confirmation.

## Recent commits
- 1a6d2fd3 — feat(controller): warn when a live ConfigMap edit can't change TA registration (rebased, was 9062ebd2 / 67ac0476)
- 5614afb4 — refactor(config): extract ThroughputAnalyzerEnabled onto config.Config (rebased + amended for the EffectiveType fix; was e0265771 / 033b0529)

## Tests added / moved
- internal/config/config_test.go:TestConfig_ThroughputAnalyzerEnabled — 7 cases (absent, absent-with-other-analyzers, enabled-explicit, enabled-nil-default, disabled-explicit, plus 2 added in the #1486 rebase: Type-overrides-Name-to-enable, Type-overrides-Name-to-disable); migrated from cmd/main_test.go:TestThroughputAnalyzerEnabled (deleted, package main's predicate it covered was extracted to config.Config)
- internal/controller/configmap_reconciler_test.go — new Context "Reconcile - Throughput Analyzer Registration Divergence", 5 specs:
  - registered=false, global config enables TA → Warning event emitted
  - registered=true, global config omits TA → Warning event emitted (converse direction)
  - registered=true, global config enables TA (match) → no event
  - registered=false, global config omits TA (match) → no event
  - namespace-local saturation ConfigMap enabling TA → no event (documents the non-goal)

## Verified
- make test — PASS (full suite, including internal/controller envtest suite: 35 of 35 specs)
- gofmt -l ./internal/... ./cmd/... — clean (no pkg/ dir in this branch's tree)
- make lint — 0 issues
- go build ./... — clean (confirms no import cycle from Commit 1's config.SaturationConfig() usage)
- DCO — both commits carry Signed-off-by: Dean H Lorenz <dean@il.ibm.com>
- §4a grep (plans-branch-identifier leak check) — clean on both commits' diffs

## Developer guide
- docs/developer-guide/throughput-analyzer.md — added a paragraph after the existing "Runtime toggling requires a restart" callout: describes the new Warning event (reason ThroughputAnalyzerRestartRequired) + restart log on global-ConfigMap divergence, fires both directions, and states the namespace-local non-coverage explicitly. No forward-looking "pending PR" language — the frozen-registration gate itself is described as current behavior, not a stopgap pending a future PR (per Type 4 rule).

## Open questions for Dean
- None. Plan was unambiguous; no coding judgment calls arose beyond commit-splitting mechanics (documented below).

## Not done / known limitations
- Per plan's explicit non-goals: no hot-reload of the analyzer registry, no namespace-local divergence detection, no WVA user-guide change (cross-repo llm-d/llm-d doc coordination is issue #1498, out of this PR's scope).

## Notes
Plan specified "Commit 1 — extract ThroughputAnalyzerEnabled()" and "Commit 2 — detect live
enablement change" as two separate commits, but both touch cmd/main.go's registration call site
(Commit 1: `throughputAnalyzerEnabled(cfg)` → `cfg.ThroughputAnalyzerEnabled()`; Commit 2: that
→ the shared `taRegistered` local). Split cleanly by staging Commit 1's files, stashing Commit 2's
unstaged changes with `git stash push --keep-index`, verifying build/test/lint against the
isolated Commit-1 tree, committing, then popping the stash and re-applying the `taRegistered`
wiring for Commit 2. Both commits verified independently buildable/testable/lintable, not just
the final combined state.

Also found and fixed a test-isolation issue while writing the reconciler tests: the new
"namespace-local path does not emit" spec creates a namespace-local `wva-saturation-scaling-config`
ConfigMap in the shared envtest cluster without cleanup, which collided (`already exists`, 409)
with the pre-existing "should reconcile namespace-local saturation ConfigMap" spec on a different
Ginkgo random-seed ordering. Fixed by adding `DeferCleanup` to delete the ConfigMap after the new
spec runs — no change to the pre-existing test needed.
