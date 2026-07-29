# TA Gate Observability — Type 3 Task Plan (PR E)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-gate-observability` cut from the current tip of `main` (the moving ref — `git worktree add … main`, never a pinned SHA). Authored against `bf8fd8d9`; anchors re-verified against `main` `dfc21e2c` on 2026-07-29 and all intact through the #1491 utils-split. Any SHA here is informational-as-of-authoring only.
**Size:** 1 refactor + 1 behavior commit + tests + dev-guide · **Reviewer session:** yes (operator-facing safety behavior)
**Depends on:** nothing (independent of C `#1480` / D `#1481`). A′ `#1479` already merged into `main`.

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L24:61
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L62:85
- [Background — why registration is frozen {#background}](#background--why-registration-is-frozen-background) L86:111
- [Commit 1 — extract ThroughputAnalyzerEnabled() to config.Config {#commit-1}](#commit-1--extract-throughputanalyzerenabled-to-configconfig-commit-1) L112:152
- [Commit 2 — detect live enablement change, warn to restart {#commit-2}](#commit-2--detect-live-enablement-change-warn-to-restart-commit-2) L153:216
- [Semantic-pivot grep step {#grep}](#semantic-pivot-grep-step-grep) L217:238
- [Tests {#tests}](#tests-tests) L239:263
- [Developer guide {#devguide}](#developer-guide-devguide) L264:284
- [Cross-repo companion (llm-d/llm-d) {#crossrepo}](#cross-repo-companion-llm-dllm-d-crossrepo) L285:303
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L304:317

## Overview {#overview}

This is the second half of **I-5** (gate observability). A′ (`#1479`, merged) landed
**half 1**: a startup log line when the ThroughputAnalyzer (TA) gate evaluates to false, so an
operator can tell from logs whether TA was registered at boot.

**Half 2 — the runtime-edit blind spot — is unaddressed and is what this PR fixes.**

Analyzer registration is **frozen at controller startup**: `cmd/main.go:533-535` calls
`RegisterAnalyzer(throughput.AnalyzerName, …)` only if `throughputAnalyzerEnabled(cfg)` is true at
boot, and after `StartOptimizeLoop` (`cmd/main.go:544`, and the parallel path at `:559`) the
registry is never mutated again. The `ConfigMapReconciler` watches the saturation ConfigMap and
hot-updates `r.Config` on every edit (`handleSaturationConfigMap`,
`internal/controller/configmap_reconciler.go:164`) — but that updated config is only *consumed* by
the per-cycle analysis for **already-registered** analyzers. **Enabling TA by editing the
ConfigMap at runtime does nothing** until the controller restarts, and today there is **no signal
at all** that the edit was inert.

**Decision (Dean, 2026-07-28):** ship the **stopgap** for 0.9 — a controller restart is an
acceptable operator action for 0.9. When the reconciler detects that the live config's
TA-enabled state differs from the registration decision frozen at startup, it emits:

1. A **Kubernetes Warning event** on the ConfigMap object, reason
   `ThroughputAnalyzerRestartRequired`, and
2. A **log line** that **explicitly tells the operator to restart the controller**.

The proper fix — removing the frozen-registration gate so enable/disable is hot-applied — is
`wva-analyzer-lifecycle` scope (post-0.9). This PR is the 0.9 stopgap only; the dev-guide note
must say so without a forward-looking "pending PR" reference (Type 4 rule).

"Disabled by default" needs **no code** — verified 2026-07-28 at all three layers: (a)
`throughputAnalyzerEnabled` returns false when TA is absent; (b) the shipped
`config/base/manager/saturation-scaling-configmap.yaml` default analyzers block lists only
`- name: saturation, score: 1.0`; (c) per-cycle `effectiveEnabled` fall-through returns false
(A′). A′ already added `TestThroughputAnalyzerEnabled` covering the default-off gate.

[↑ TOC](#toc)

## Scope and non-goals {#scope}

**In scope:**
- Extract the TA-enablement predicate out of `package main` into a reusable
  `(*config.Config).ThroughputAnalyzerEnabled()` method so the reconciler and `cmd/main.go` share
  one definition (Commit 1).
- Thread the frozen startup registration decision into `ConfigMapReconciler` and emit a Warning
  event + restart log when the live config diverges from it (Commit 2).
- Unit tests for the new reconciler behavior and the migrated predicate.
- Dev-guide update in `docs/developer-guide/throughput-analyzer.md`.

**Non-goals (do NOT do in this PR):**
- Removing or changing the frozen-registration mechanism itself (that is `wva-analyzer-lifecycle`).
- Any hot-reload of the analyzer registry.
- Namespace-local saturation ConfigMap TA-enablement detection — startup registration reads the
  **global** config (`cfg.SaturationConfig()`), so the divergence check is scoped to the **global**
  ConfigMap path (`isGlobal == true`). Namespace-local enablement is a documented limitation, not
  handled here. State this explicitly in the dev guide.
- Any WVA **user-guide** change. Operator-facing "TA is opt-in + restart-required" documentation
  goes to the **llm-d/llm-d** repo — see § Cross-repo companion.
- Default-off changes — already true, no code.

[↑ TOC](#toc)

## Background — why registration is frozen {#background}

Read these before editing, to confirm the anchors are still current on your branch base:

- `cmd/main.go:98-107` — `throughputAnalyzerEnabled(cfg *config.Config) bool`: iterates
  `cfg.SaturationConfig()`, returns true iff a `throughput` analyzer entry exists with `Enabled`
  nil-or-true. The doc comment already states the restart requirement ("RegisterAnalyzer is frozen
  after StartOptimizeLoop").
- `cmd/main.go:533-535` — registration call site, guarded by `throughputAnalyzerEnabled(cfg)`.
- `cmd/main.go:544` and `:559` — `go engine.StartOptimizeLoop(ctx)`; registry is immutable after.
- `cmd/main.go:400` — `configMapReconciler := &controller.ConfigMapReconciler{…}` construction
  site (where the frozen decision must be injected).
- `internal/controller/configmap_reconciler.go:38-44` — `ConfigMapReconciler` struct (already has
  `Recorder record.EventRecorder`, line 43).
- `internal/controller/configmap_reconciler.go:46-48` — the kubebuilder RBAC marker already grants
  `events` `create;patch` (no RBAC change needed).
- `internal/controller/configmap_reconciler.go:164-178` — `handleSaturationConfigMap`: parses
  `cm.Data` → `configs`, then `UpdateSaturationConfig` (global) or
  `UpdateSaturationConfigForNamespace`. **The divergence check goes here, on the `isGlobal` path,
  after the update.**
- Existing `(*config.Config)` enablement helpers to mirror in style:
  `internal/config/config.go:320 CoordinatorEnabled()`, `:342 ScaleToZeroEnabled()`,
  `:350 LimitedModeEnabled()`.

[↑ TOC](#toc)

## Commit 1 — extract ThroughputAnalyzerEnabled() to config.Config {#commit-1}

**Goal:** one shared enablement predicate, so Commit 2's reconciler check cannot drift from the
startup registration check.

**Steps:**

1. Add to `internal/config/config.go`, next to the other `*Enabled()` helpers (~L320-350):
   ```go
   // ThroughputAnalyzerEnabled reports whether the global saturation config
   // opts the throughput analyzer in (an entry named throughput.AnalyzerName
   // with Enabled nil-or-true). This is the same predicate cmd/main.go uses to
   // decide startup registration; the reconciler uses it to detect a live-config
   // divergence from the frozen registration decision.
   func (c *Config) ThroughputAnalyzerEnabled() bool { … }
   ```
   Body = the exact loop from `cmd/main.go`'s `throughputAnalyzerEnabled`, reading
   `c.SaturationConfig()`. **Import note:** `internal/config` must not import the throughput
   analyzer package (would create an import cycle risk / layering violation). Compare against the
   **string literal** `"throughput"` — but avoid a bare magic string: define or reuse a
   config-level constant (check whether `config` already has an analyzer-name constant; if not,
   use the literal with a comment cross-referencing `throughput.AnalyzerName`, since `config` is a
   lower layer than `engines/analyzers/throughput`). Confirm no cycle with
   `go build ./...` after.

2. In `cmd/main.go`: replace the body of `throughputAnalyzerEnabled(cfg)` with a call to
   `cfg.ThroughputAnalyzerEnabled()`, **or** delete the local function and call
   `cfg.ThroughputAnalyzerEnabled()` directly at `:533`. Prefer deletion for one source of truth —
   but see the grep step (§grep): A′ added `TestThroughputAnalyzerEnabled` against the
   package-`main` function, so deleting it requires migrating that test.

3. Migrate `TestThroughputAnalyzerEnabled` (added by A′, currently in the `cmd` test package) to
   `internal/config` as `TestConfig_ThroughputAnalyzerEnabled`, preserving all 5 cases (absent;
   absent-with-other-analyzers; enabled-explicit; enabled-nil-default; disabled-explicit). If you
   keep a thin `main` wrapper instead of deleting, keep a minimal smoke test there too.

**Behavior invariant:** this commit is a pure refactor — the boolean result for every input is
identical to A′'s. No functional change; the divergence detection is entirely Commit 2.

[↑ TOC](#toc)

## Commit 2 — detect live enablement change, warn to restart {#commit-2}

**Goal:** on a global saturation-ConfigMap edit that flips TA-enablement relative to the frozen
startup decision, emit a Warning event + restart log.

**Steps:**

1. Add a field to `ConfigMapReconciler` (`configmap_reconciler.go:38-44`):
   ```go
   // ThroughputRegistered is the throughput-analyzer registration decision
   // frozen at startup (cmd/main.go). Analyzer registration cannot change
   // without a controller restart; the reconciler compares live config against
   // this to warn when a runtime edit would be silently inert.
   ThroughputRegistered bool
   ```

2. In `cmd/main.go:400`, set `ThroughputRegistered:` from the **same value** used for the
   registration decision at `:533` — capture it once into a local
   (`taRegistered := cfg.ThroughputAnalyzerEnabled()`), use it both at the registration guard and
   in the reconciler literal, so the two can never disagree.

3. In `handleSaturationConfigMap` (`configmap_reconciler.go:164`), **after** the config update, on
   the **global path only**:
   ```go
   if isGlobal {
       r.Config.UpdateSaturationConfig(configs)
       logger.Info("Updated global saturation config from ConfigMap", "entries", count)

       if want := r.Config.ThroughputAnalyzerEnabled(); want != r.ThroughputRegistered {
           msg := fmt.Sprintf(
               "Throughput analyzer enablement in config (%t) differs from the "+
                   "registration frozen at controller startup (%t); analyzer registration "+
                   "cannot change at runtime. Restart the wva-controller-manager to apply.",
               want, r.ThroughputRegistered)
           logger.Info(msg) // operator-facing; also emit a K8s Warning event
           if r.Recorder != nil {
               r.Recorder.Event(cm, corev1.EventTypeWarning,
                   "ThroughputAnalyzerRestartRequired", msg)
           }
       }
   } else {
       … // unchanged; namespace-local path does not participate (see non-goals)
   }
   ```
   - Reason constant string: `ThroughputAnalyzerRestartRequired`. If the controller package has a
     conventional home for event-reason constants, define it there; otherwise a local `const` in
     `configmap_reconciler.go` is fine — do not invent a cross-package constants file.
   - The `r.Recorder != nil` guard mirrors existing nil-safety for the recorder (some test
     harnesses construct the reconciler without one). Confirm the existing pattern in the file /
     sibling reconcilers and match it.
   - The event object is `cm` (the ConfigMap being reconciled) — the same object the reconcile is
     about, so the event is discoverable via `kubectl describe configmap`.

**Behavior:** fires on **both** divergence directions — config now enables TA but it was not
registered (the common case), and config now disables TA but it was registered at boot. Both are
operator-visible surprises that a restart resolves.

**Deletion classification:** none — this PR only adds. If Commit 1 deletes the package-`main`
`throughputAnalyzerEnabled`, classify it in the handoff as **DEPRECATED** (superseded by
`(*config.Config).ThroughputAnalyzerEnabled()`, same behavior, moved for reuse) — no design intent
lost.

[↑ TOC](#toc)

## Semantic-pivot grep step {#grep}

Commit 1 moves/renames a predicate. Run after implementation and update every hit (comments,
docstrings, tests) before committing:

```bash
grep -rn "throughputAnalyzerEnabled" cmd/ internal/ docs/
grep -rn "TestThroughputAnalyzerEnabled" cmd/ internal/
```

Expected hits and required action:
- `cmd/main.go` call site(s) — repoint to `cfg.ThroughputAnalyzerEnabled()` or the wrapper.
- The A′ test `TestThroughputAnalyzerEnabled` — migrated per Commit 1 step 3.
- The doc comment at `cmd/main.go:98-107` — if the function is deleted, its restart-requirement
  prose must move to the new `config` method's doc comment (do not lose it).
- Any dev-guide reference to the function by name — update to the new location.

If any hit is outside this PR's scope, hand it back via a planner handoff rather than editing
across scope (per CODER-CONVENTIONS pre-action gate).

[↑ TOC](#toc)

## Tests {#tests}

All in `internal/controller/configmap_reconciler_test.go` (exists) unless noted:

1. **`registered=false`, global config enables TA → Warning event emitted.** Construct the
   reconciler with `ThroughputRegistered: false` and a
   `record.NewFakeRecorder(N)`; reconcile a global saturation ConfigMap whose data enables the
   throughput analyzer; assert exactly one event on the fake recorder channel containing
   `ThroughputAnalyzerRestartRequired` and `Warning`.
2. **`registered=true`, global config disables/omits TA → Warning event emitted** (converse
   direction).
3. **`registered=true`, global config enables TA (match) → no event.** Drain the fake recorder,
   assert empty.
4. **`registered=false`, global config omits TA (match) → no event.**
5. **Namespace-local path does not emit** — reconcile a namespace-local saturation ConfigMap that
   enables TA with `ThroughputRegistered: false`; assert no event (documents the non-goal).
6. **Migrated predicate test** — `internal/config`: `TestConfig_ThroughputAnalyzerEnabled`, 5
   cases from A′ (see Commit 1 step 3).

Use `record.NewFakeRecorder` from `k8s.io/client-go/tools/record` — check how sibling reconciler
tests in this package already assert events and match that idiom (do not introduce a new event
-assertion helper if one exists).

[↑ TOC](#toc)

## Developer guide {#devguide}

Edit `docs/developer-guide/throughput-analyzer.md` (Type 4 — reflect current code only, no
forward-looking "pending PR" text):

- In the **registration / restart-requirement** section (the note A′ rewrote — grep
  `restart` / `frozen` / `RegisterAnalyzer` to find it): add that the controller now **emits a
  Kubernetes Warning event** (reason `ThroughputAnalyzerRestartRequired`) **and a log line** when a
  runtime edit to the **global** saturation ConfigMap changes TA-enablement relative to the
  registration frozen at startup, and that the operator must **restart the controller** to apply.
- State the **namespace-local limitation** explicitly: the divergence warning covers the global
  ConfigMap only.
- Do **not** describe this as a stopgap-pending-lifecycle in a way that references a future PR;
  describe the current behavior as-is. A neutral "registration is fixed at startup" framing is
  correct and not forward-looking.

No other dev-guide file is affected (the `AnalyzerInput` contract in `multi-analyzer-pipeline.md`
is unchanged by this PR).

[↑ TOC](#toc)

## Cross-repo companion (llm-d/llm-d) {#crossrepo}

Operator-facing enablement/restart documentation lives in **llm-d/llm-d** (WVA config docs/values),
**not** the WVA user guide. There is already in-flight work fixing the llm-d/llm-d WVA guides for
0.9 — **coordinate, do not open a duplicate.** Candidate homes (verify before acting, all
read-only-scanned 2026-07-28):

- **PR #2130** (gyliu513) — *docs(observability): add per-guide troubleshooting for workload
  autoscaling* — strongest candidate for a "TA not registered / restart after config edit" note.
- **PR #2010** (shuynh2017) — *Doc: add WVA scale limiter feature*.
- **Issue #2124** — *wva-controller-manager never becomes Available (0/7)* — possibly the same
  class of config confusion.

This is **out of WVA (this repo) write scope** — it is a coordination/tracking item for Dean or
the docs owner. **Tracked as WVA-repo issue #1498** (*"docs: WVA guides in llm-d/llm-d must state
TA is opt-in and restart-required"*, filed 2026-07-29). The coder does **not** touch llm-d/llm-d.

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

Run in order (per CONVENTIONS pre-push checklist):
1. `git branch --show-current` — confirm `ta-gate-observability`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass (include the new reconciler + config tests).
4. `make lint` — clean (required gate; not caught by build/test).
5. DCO — every commit `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
6. `go build ./...` — clean (confirms no import cycle from Commit 1).

Then write the `review__ta-gate-observability-ready.md` trigger (per CODER-CONVENTIONS §5.4)
before the push-ready plan handoff. No push without Dean's explicit confirmation.

[↑ TOC](#toc)
