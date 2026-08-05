# ta-gate-observability (PR E) — Review

**Status: DRAFT**

This doc has two parts: a **pre-implementation plan review** (below, done before a branch
existed) and a **code review** (§ Code review, done against the 2 landed commits, this is the
FINAL verdict for push-readiness).

## Part 1 — Plan review (pre-implementation)

**Scope:** [`planning/ta-gate-observability-plan.md`](ta-gate-observability-plan.md) only. At the
time this part was written, no branch/worktree/PR existed yet for `ta-gate-observability` (per
`session/CURRENT.md`), so anchors and assumptions were checked against the current `main` tip
rather than a code diff.

**Note on base drift:** the plan's own header already anticipates this ("Any SHA here is
informational-as-of-authoring only"). At review time `main` had moved to `f5261c8e`, which
includes PR D (`#1481`, veto-liveness) **merged 2026-07-30** — new since the plan was
last anchor-verified (2026-07-29 against `dfc21e2c`). None of D's changes touch
`cmd/main.go`, `internal/config/config.go`, or `internal/controller/configmap_reconciler.go`, so
this PR's anchors are unaffected. Flagged separately to the planner (see handoff
`plan__pr1481-merged-current-stale.md`) since it's a CURRENT.md staleness issue, not a
gate-observability plan issue.

## Anchors verified against `main@f5261c8e`

All cited line numbers/functions checked by direct read, not just grep:

| Plan citation | Verified |
|---|---|
| `cmd/main.go:98-107` doc comment + `throughputAnalyzerEnabled` | ✅ (func now at :107, comment :98-106 — 1-line drift, harmless) |
| `cmd/main.go:533-535` registration call site | ✅ exact |
| `cmd/main.go:544` / `:559` `StartOptimizeLoop` | ✅ exact |
| `cmd/main.go:400` reconciler construction site | ✅ exact, `Recorder: mgr.GetEventRecorderFor(...)` already wired |
| `configmap_reconciler.go:38-44` struct incl. `Recorder record.EventRecorder` (line 43) | ✅ exact |
| `configmap_reconciler.go:46-48` RBAC `events` `create;patch` | ✅ exact (line 48) |
| `configmap_reconciler.go:164-178` `handleSaturationConfigMap`, `isGlobal` branch | ✅ exact |
| `config.go:320/342/350` sibling `*Enabled()` helpers | ✅ (`CoordinatorEnabled`, `ScaleToZeroEnabled`, `LimitedModeEnabled`) |
| A′'s `TestThroughputAnalyzerEnabled` in `cmd/main_test.go`, 5 cases | ✅ exact match to plan's case list |
| Dev-guide restart-requirement note (grep `restart`/`frozen`/`RegisterAnalyzer`) | ✅ `docs/developer-guide/throughput-analyzer.md:20-31` |
| No existing `internal/config` → `throughput` import (cycle risk claim) | ✅ confirmed no cycle either direction |

Plan is well-anchored. No stale line references found.

## Findings

### 1. Event-reason constant home already exists — plan should point at it directly (NTH, doc-accuracy)

Commit 2 step 3 says:

> Reason constant string: `ThroughputAnalyzerRestartRequired`. If the controller package has a
> conventional home for event-reason constants, define it there; otherwise a local `const` in
> `configmap_reconciler.go` is fine — do not invent a cross-package constants file.

This reads as an open question, but the codebase already has one: `internal/constants/constants.go`
defines every other K8s event reason string used via `Recorder.Event(...)` in this repo —
`K8SEventScaledUp`, `K8SEventScaledDown`, `K8SEventResourceConstrained`,
`K8SEventMetricsUnavailable`, `K8SEventScaledToZero`, `K8SEventOptimizationFailed`,
`K8SEventUnattributedReadyPods` (all consumed from `internal/engines/saturation/engine.go`,
`internal/engines/scalefromzero/engine.go`, `internal/collector/replica_metrics.go`). This file is
already imported in `configmap_reconciler.go` (`internal/constants`, see the import block) — no new
import needed.

A local `const` in `configmap_reconciler.go` would be the **first** event-reason constant in the
codebase not defined in `internal/constants`, breaking an established, actively-used convention for
no reason — the "otherwise" branch of the plan's instruction isn't actually available.

**Suggested plan fix:** replace the "if/otherwise" framing with a direct instruction: add
`K8SEventThroughputAnalyzerRestartRequired = "ThroughputAnalyzerRestartRequired"` to
`internal/constants/constants.go` alongside the existing `K8SEvent*` block, and reference
`constants.K8SEventThroughputAnalyzerRestartRequired` in the `Recorder.Event(...)` call instead of
the bare string literal shown in the plan's code sketch.

### 2. "Confirm the existing nil-guard pattern" — no `Recorder != nil` check exists yet to mirror (NTH, doc-accuracy)

Commit 2 step 3 also says:

> The `r.Recorder != nil` guard mirrors existing nil-safety for the recorder (some test harnesses
> construct the reconciler without one). Confirm the existing pattern in the file / sibling
> reconcilers and match it.

Checked: `Recorder` is never actually called (`.Event(...)`) anywhere in `internal/controller`
today — the field exists (added with A′/#1479, unused so far) and is genuinely left nil in two
test harnesses (`configmap_bootstrap_test.go:388`, `:419`), confirming the "some test harnesses
construct without one" half. But there is **no existing `r.Recorder != nil` guard anywhere in
`internal/controller`** to "confirm and match" — this PR's guard would be the first. Not a blocker
(the plan's own code sketch already writes the correct guard), just means the coder shouldn't go
looking for a pattern that isn't there; word the instruction as "add the guard" rather than
"confirm and match an existing pattern."

## Confirmed correct (no issue)

- Import-cycle claim for Commit 1 (`internal/config` must not import `throughput`) — verified: no
  cycle risk in either direction; the migrated test (`internal/config` package) can safely import
  `internal/engines/analyzers/throughput` for `throughput.AnalyzerName` in test data, since
  `throughput` has no transitive dependency on `internal/config`.
- Non-goal scoping (namespace-local path, hot-reload, user-guide) is consistent with current code —
  `handleSaturationConfigMap`'s `isGlobal`/else branches exist exactly as described.
- Test plan (6 cases) is complete and matches the existing `FakeRecorder` idiom already used in
  `configmap_test_helpers_test.go` / `configmap_reconciler_test.go:510`.
- §4a discipline: plan prose does not leak plans-branch identifiers into any code-comment/test-desc
  text it specifies — the sketched Go comments read as plain prose.

## Plan-review verdict

No blocking findings. Two NTH doc-accuracy fixes (both above) worth folding in before or during
implementation — neither changes scope or behavior, both just tighten instructions the coder would
otherwise have to re-derive themselves (and #1 nudges the coder away from introducing a
convention-breaking local constant). Plan is otherwise implementation-ready.

---

## Part 2 — Code review

**Branch:** `ta-gate-observability`, tip `67ac0476`, 2 commits on `upstream/main@f5261c8e`
(includes merged A′ #1479 + D #1481). Not pushed; no PR yet.

### Change highlight

| Commit | What | Type |
|---|---|---|
| `033b0529` | Move `throughputAnalyzerEnabled(cfg)` out of `package main` onto `(*config.Config).ThroughputAnalyzerEnabled()`; migrate its test to `internal/config`; delete `cmd/main_test.go`. Pure refactor — boolean result unchanged for every input. | logic (behavior-preserving) |
| `67ac0476` | Add `ConfigMapReconciler.ThroughputRegistered bool`; capture it once in `cmd/main.go` from the same value used at the registration call site; on a global saturation-ConfigMap reconcile, warn (K8s Warning event, reason `ThroughputAnalyzerRestartRequired`, + log line) when live TA-enablement diverges from that frozen decision, in both directions. New `internal/constants.K8SEventThroughputAnalyzerRestartRequired`. Dev-guide updated. | logic + doc |

**Left out of scope (correctly, per plan non-goals):** removing/changing the frozen-registration
gate itself (`wva-analyzer-lifecycle` territory); any hot-reload; namespace-local divergence
detection (test 5 documents this as a no-op, not an oversight); WVA user-guide changes (cross-repo,
tracked as issue #1498).

### Critical section

The whole behavioral change is one method, `warnIfThroughputRegistrationDiverged`
(`internal/controller/configmap_reconciler.go`), called from `handleSaturationConfigMap`'s
`isGlobal` branch only:

```go
func (r *ConfigMapReconciler) warnIfThroughputRegistrationDiverged(logger logr.Logger, cm *corev1.ConfigMap) {
	want := r.Config.ThroughputAnalyzerEnabled()
	if want == r.ThroughputRegistered {
		return
	}
	msg := fmt.Sprintf(
		"Throughput analyzer enablement in config (%t) differs from the registration "+
			"frozen at controller startup (%t); analyzer registration cannot change at "+
			"runtime. Restart the wva-controller-manager to apply.",
		want, r.ThroughputRegistered)
	logger.Info(msg)
	if r.Recorder != nil {
		r.Recorder.Event(cm, corev1.EventTypeWarning, constants.K8SEventThroughputAnalyzerRestartRequired, msg)
	}
}
```

`r.ThroughputRegistered` is set exactly once, in `cmd/main.go`, from `taRegistered :=
cfg.ThroughputAnalyzerEnabled()` captured right after `BootstrapInitialConfigMaps` completes — the
same local is used later to gate `RegisterAnalyzer`, so the two decisions structurally cannot
diverge from each other (only from a later live-config edit, which is exactly what this method
detects).

### Verification performed (independent of the coder's own gate run)

- Anchors: all plan-cited line numbers/functions re-checked directly against `main@f5261c8e` before
  the branch existed — all accurate (Part 1).
- Diffs read in full for both commits (not just stat) — no surprises vs. commit messages; no §4a
  leaks (`decision #|review finding|F[0-9]|plan §|TA-[a-z]+ §|planning/|-plan\.md|-review\.md` grep
  clean on the diff); no stale references to the deleted `throughputAnalyzerEnabled`/
  `TestThroughputAnalyzerEnabled` names anywhere in the tree.
- Re-ran independently (not trusting the status file's report): `gofmt -l internal/ cmd/` (clean),
  `go build ./...` (clean), `go test ./internal/config/... ./internal/controller/... ./cmd/...`
  (all pass), `golangci-lint run ./internal/config/... ./internal/controller/... ./cmd/...`
  (0 issues), DCO present on both commits, exactly 2 commits ahead of `upstream/main` with a clean
  merge-base at the claimed tip.
- Both Part-1 NTH findings were addressed in the actual implementation: the new event reason is
  `constants.K8SEventThroughputAnalyzerRestartRequired` in `internal/constants/constants.go`
  (alongside the existing `K8SEvent*` block, not a local const), and the `Recorder != nil` guard is
  written directly without over-claiming a pre-existing pattern to mirror.
- `taRegistered` capture-once ordering verified by reading the surrounding `cmd/main.go` control
  flow: captured after config-map bootstrap, before the (later-executing, inside the leader-only
  runnable) registration guard; no intervening mutation of the saturation config between capture
  and either consumption site.
- Test file read in full: 5 new specs match the plan's 5 test cases exactly, including the
  `Warning`-substring assertion (matches `record.FakeRecorder`'s known `"eventtype reason message"`
  format) and the namespace-local non-participation case with `DeferCleanup` (the coder's
  documented test-isolation fix).

### Findings

None. No blocking or non-blocking findings against the code itself.

### Verdict

**Ready to push**, pending Dean's explicit push confirmation (per CONVENTIONS — no push without
that, regardless of review outcome). Plan and code match; all gates independently re-verified
green; both Part-1 plan nits were already resolved in the implementation.

---

## Part 3 — Post-rebase re-verification (2026-07-30)

`upstream/main` advanced `f5261c8e` → `f9f04d81` (PR C `#1480` merged) while this review was in
progress on the sibling `ta-correctness-guards` branch. The coder rebased `ta-gate-observability`
onto the new tip; new tip `9062ebd2` (was `67ac0476`; commit SHAs changed as expected, messages
unchanged: `e0265771`/`9062ebd2`).

**Independently re-verified, not just trusting the handoff:**

- `diff <(git diff f5261c8e..67ac0476) <(git diff f9f04d81..9062ebd2)` — the **only** difference
  between the pre- and post-rebase diffs is the blob-hash `index` line for
  `docs/developer-guide/throughput-analyzer.md`; every hunk (added/removed lines) is byte-identical.
  Confirmed by reading the actual post-rebase hunk: this branch's dev-guide addition lands at line
  29 of the file, well above where C's changes land (~line 500+) — genuinely zero overlap, exactly
  as the coder's pre-rebase file-overlap analysis predicted. No silent hunk drop, no compile-break
  (unlike the sibling branch, which had one).
- `gofmt -l ./internal ./cmd` — clean; `go build ./...` — clean; `make lint` — 0 issues; `make test`
  — full suite PASS (note: `internal/cmd` now reports "no test files" / 0.0% coverage, which is
  expected — `cmd/main_test.go` was deleted in Commit 1, migrated to `internal/config`, not a
  regression).
- DCO — 2/2 signed. §4a scan (widened pattern, diff + commit messages) — clean.

**Verdict unchanged: still ready to push**, pending Dean's confirmation. The rebase was a pure
no-conflict replay with no code-level interaction with C's changes — nothing in Part 1/2's findings
or verdict is affected.

---

## Part 4 — Second rebase re-verification (2026-07-30) — PR #1502, real logic change

This branch is now open upstream as **PR #1502**. `upstream/main` advanced again,
`f9f04d81` → `da58c0e0` (**#1486**, "ScalingPolicy schema Phase 1"), putting #1502 into
`CONFLICTING`/`DIRTY` on GitHub (confirmed via `gh pr view 1502 -R llm-d/llm-d-workload-variant-autoscaler`
— `headRefOid` there is still the Part-3 tip `9062ebd2`; the rebase below is local-only, not yet
pushed). New tips: **`5614afb4`** (Commit 1, message amended) and **`1a6d2fd3`** (Commit 2), base
now `upstream/main@da58c0e0`.

**Unlike Part 3, this rebase carries a real, intentional behavior change — verified directly, not
just from the handoff:**

`#1486` added `AnalyzerScoreConfig.Type` / `EffectiveType()` (falls back to `Name` when `Type` is
unset) and migrated every analyzer-identity comparison in `engine_v2.go` from `aw.Name ==` to
`aw.EffectiveType() ==`. This branch's Commit 1 moved `throughputAnalyzerEnabled` out of
`cmd/main.go` onto `(*Config).ThroughputAnalyzerEnabled()` — a predicate that does the exact same
kind of analyzer-identity lookup. Confirmed by reading the code directly:

- `internal/config/saturation_scaling.go:138` — `EffectiveType()` is exactly `#1486`'s new
  accessor, doing what the commit claims (Type override, Name fallback).
- `internal/config/config.go` (post-rebase) — the new `ThroughputAnalyzerEnabled()` method uses
  `aw.EffectiveType() == throughputAnalyzerName`, consistent with every other analyzer-matching
  call site in the codebase. Had this been left as `aw.Name ==` (the pre-rebase code, and what a
  purely mechanical rebase would have produced, since `#1486`'s diff never touches this
  not-yet-existing method), this gate would have silently diverged from `engine_v2.go`'s matching
  semantics — an operator using `type: throughput` with a different `name:` would register the
  analyzer but this gate would report it disabled, or vice versa. This is the same "two validators
  that can drift apart" failure shape as `ta-correctness-guards`' own I-2 guard — caught here before
  it shipped rather than after.
- Two new test cases in `internal/config/config_test.go`
  (`TestConfig_ThroughputAnalyzerEnabled`) directly exercise this: `Type` overriding a different
  `Name` to enable, and `Name` matching but `Type` overriding to disable. Read both in full — they
  correctly isolate the `EffectiveType()` vs `Name` distinction rather than just re-testing the
  already-covered `Enabled`/nil cases.
- `cmd/main.go`'s own conflict (both this branch and `#1486` edited the old, now-deleted
  `throughputAnalyzerEnabled` function) resolved correctly: this branch's deletion (moved to
  `config.Config`) plus `#1486`'s new `engine.SetLimiterBuilder(...)` block both survive, confirmed
  by direct diff read, not just trusting a clean `git rebase` exit code.
- **Commit message discipline:** Commit 1's message previously claimed "pure refactor, boolean
  result identical for every input" — no longer true after the `EffectiveType()` fix. The coder
  amended it to state the behavior change explicitly and scope the "pure refactor" claim to "every
  input that predates the Type field" — read the full amended message; it accurately describes the
  diff (per CONVENTIONS: commit messages must reflect the diff, especially after a rebase).

**Full gate re-run:** `gofmt` clean, `go build ./...` clean, `make test` full-repo PASS, `make lint`
0 issues, DCO 2/2 (`git log da58c0e0..1a6d2fd3`), §4a scan (diff + commit messages) clean.

### Verdict (Part 4)

**Ready to push.** This is a substantive, correct fix (not a mechanical replay) that keeps the new
registration-observability gate consistent with `#1486`'s analyzer-identity convention — verdict
upgraded in confidence, not just carried forward. Remaining step is the planner's force-push to
origin/upstream with Dean's confirmation, which will resolve #1502's current `CONFLICTING` state.
