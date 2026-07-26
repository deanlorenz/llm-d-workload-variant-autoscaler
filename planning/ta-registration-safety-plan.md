# TA Registration Safety — Type 3 Task Plan (PR A′)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-registration-safety` off `main` (`f5b7577c`)
**Size:** 2 code edits + 1 test-file update + 1 log line · **Reviewer session:** yes (small, high-consequence)

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L20:54
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L55:72
- [Commit 1 — effectiveEnabled opt-in (the veto fix) {#commit-1}](#commit-1--effectiveenabled-opt-in-the-veto-fix-commit-1) L73:140
- [Commit 2 — startup log when TA gate is false {#commit-2}](#commit-2--startup-log-when-ta-gate-is-false-commit-2) L141:185
- [Semantic-pivot grep step {#grep}](#semantic-pivot-grep-step-grep) L186:203
- [Developer guide {#devguide}](#developer-guide-devguide) L204:220
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L221:234

## Overview {#overview}

Two independent safety fixes that must land before the ThroughputAnalyzer (TA) is
turned on in any real cluster. Both stem from the same latent hazard: TA can be
*registered* while an operator has not *explicitly* configured it.

1. **The veto bug (I-16).** `effectiveEnabled` in
   `internal/engines/saturation/engine_v2.go:193` returns `true` when an analyzer
   has **no entry** in `cfg.Analyzers`. A registered-but-unconfigured analyzer
   therefore runs, returns `SpareCapacity=0`, and — because the per-role scale-down
   decision requires **all** analyzers in the slice to agree — **silently vetoes
   scale-down**. `#1266` already fixed the *explicit* `Enabled:false` case; the
   **absent/nil** case is still live. The principle is opt-in: an analyzer registered
   in code must be explicitly present in `cfg.Analyzers` to participate.

2. **Silent gate (I-5, part 1).** When `throughputAnalyzerEnabled(cfg)` returns false
   at startup (`cmd/main.go:532`), there is **no log line**. An operator cannot tell
   from logs whether TA evaluated the gate to false or the code never reached that path.

**This PR covers only the config-absence half of the veto.** It removes a *config-absent*
analyzer from the vote (opt-in hygiene — it never enters the slice). The broader
principle — *an analyzer that is configured but currently uninformative (never had
metrics, error state, stale), regardless of cause, must not veto scale-down; and
saturation's token-capacity result is not blanket-exempt* — is handled by
**PR D (`ta-veto-liveness`)**, a per-analyzer liveness gate on `needsScaleDownForRole`.
The two are complementary and independent; land in either order. See
[`ta-veto-liveness-plan.md`](ta-veto-liveness-plan.md).

**Deliberately deferred to `wva-analyzer-lifecycle` (post-0.9), NOT in this PR:**
the frozen-registration removal and the "runtime configmap edit silently ignored"
K8s Warning event (I-5 part 2). This PR is a strict subset of the lifecycle plan's
D5 (`absent → false`) — zero rework when lifecycle lands.

[↑ TOC](#toc)

## Scope and non-goals {#scope}

**In scope (files this PR may touch):**
- `internal/engines/saturation/engine_v2.go` — `effectiveEnabled` return + comment.
- `internal/engines/saturation/engine_v2_population_test.go` — flip the absent-entry assertions.
- `cmd/main.go` — add the `else` startup log branch.
- `docs/developer-guide/multi-analyzer-pipeline.md` — opt-in semantics section (see §devguide).

**Non-goals (do NOT do here — belong to `wva-analyzer-lifecycle`):**
- Do **not** remove `throughputAnalyzerEnabled` or the startup gate.
- Do **not** touch `RegisterAnalyzer` / `StartOptimizeLoop` freezing.
- Do **not** add the configmap-divergence K8s event.

If the plan seems to require any of the above, stop and write a planner handoff — do
not expand scope.

[↑ TOC](#toc)

## Commit 1 — effectiveEnabled opt-in (the veto fix) {#commit-1}

**File:** `internal/engines/saturation/engine_v2.go`, function `effectiveEnabled` at L193.

Read it first: `Read internal/engines/saturation/engine_v2.go offset:193 limit:30`.
Current behaviour: iterates `cfg.Analyzers`; if a matching entry is found it honours
`aw.Enabled` (nil → true); if **no** entry matches it falls through to a final
`return true`.

**Change:** the final fall-through `return true` becomes `return false`, and the
doc comment is rewritten to state the opt-in contract. Target comment + body:

```go
// effectiveEnabled reports whether the named analyzer should participate in this
// cycle's scaling decision. An analyzer is opt-in: it participates only when it has
// an explicit entry in cfg.Analyzers whose Enabled is true (or nil, i.e. present but
// not yet defaulted). An analyzer registered in code but ABSENT from cfg.Analyzers
// does NOT participate — this prevents a registered-but-unconfigured analyzer (e.g.
// throughput) from returning SpareCapacity=0 and silently vetoing scale-down.
// Saturation is exempt: it is guarded by the SaturationAnalyzerName check upstream
// (engine_v2.go ~L136) before effectiveEnabled is ever called.
func effectiveEnabled(analyzerName string, cfg config.SaturationScalingConfig) bool {
    for _, aw := range cfg.Analyzers {
        if aw.Name == analyzerName {
            if aw.Enabled != nil {
                return *aw.Enabled
            }
            return true // present, not yet defaulted → participates
        }
    }
    return false // absent → opt-in: does not participate
}
```

**Verify the saturation exemption still holds** before committing: confirm the guard
at `engine_v2.go:136` (`if entry.name == domain.SaturationAnalyzerName { ... }`)
short-circuits before the `!effectiveEnabled(...)` check at L139. Saturation must never
be gated off by this change. If that guard has moved or changed shape, stop and write a
handoff — the change is unsafe without it.

**Tests (same commit):** `internal/engines/saturation/engine_v2_population_test.go`,
`Describe("effectiveEnabled")` at L65. Read `Read ... offset:65 limit:40`. Current
assertions:
- L67 — absent entry (empty config) → `BeTrue()`  → **flip to `BeFalse()`**
- L76 — some other analyzer present, `throughput` absent → `BeTrue()` → **flip to `BeFalse()`**
- L86 — explicit `Enabled:false` → `BeFalse()` → **unchanged**
- L96 — present, `Enabled` nil (or true) → `BeTrue()` → **unchanged**

Update the spec descriptions so they read as opt-in ("absent entry does NOT
participate"), not the old "defaults to enabled". Add one spec asserting a
scale-down scenario is **not** vetoed by an unconfigured throughput analyzer if a
natural fixture exists; otherwise note the gap in your status file (do not force it).

**Commit message:**
```
saturation: make effectiveEnabled opt-in (absent entry → false)

A registered-but-unconfigured analyzer previously ran and returned
SpareCapacity=0, silently vetoing scale-down because needsScaleDownForRole
requires all analyzers to agree. effectiveEnabled now returns false for
analyzers absent from cfg.Analyzers; participation is opt-in via an explicit
config entry. Saturation remains exempt (guarded upstream by name).

Completes the absent/nil half of the #1266 effectiveEnabled fix.
```

[↑ TOC](#toc)

## Commit 2 — startup log when TA gate is false {#commit-2}

**File:** `cmd/main.go`. Read `Read cmd/main.go offset:530 limit:12`. Current shape at
L532-537:

```go
if throughputAnalyzerEnabled(cfg) {
    registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
    if err := engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer()); err != nil {
        return err
    }
    setupLog.Info("ThroughputAnalyzer registered (enabled in saturation config)")
}
```

**Change:** add an `else` branch so the disabled path is observable:

```go
} else {
    setupLog.Info("ThroughputAnalyzer NOT registered — no saturation config entry " +
        "enables 'throughput'. Add it to the analyzers config and restart the " +
        "controller to enable it.")
}
```

Keep the "restart" wording accurate to *current* code (registration is still frozen
after `StartOptimizeLoop` — that is what `wva-analyzer-lifecycle` will later remove).
Do **not** soften it to imply hot-reload works.

No new test is strictly required for a log line; if the gate function
`throughputAnalyzerEnabled` (cmd/main.go:106) has no unit test, add a small table
test for it (enabled / disabled / absent) in `cmd/main_test.go` — this is I-12 and is
cheap to co-locate here.

**Commit message:**
```
cmd: log when ThroughputAnalyzer is not registered

The disabled path was silent; an operator could not confirm from logs whether
the throughput gate evaluated to false. Add an else-branch log line. Also add a
unit test for throughputAnalyzerEnabled (enabled/disabled/absent).
```

[↑ TOC](#toc)

## Semantic-pivot grep step {#grep}

Commit 1 changes the behavioral contract of `effectiveEnabled` (absent now means
"off", previously "on"). After implementing, run:

```bash
git -C . grep -n "effectiveEnabled\|opt-in\|defaults to enabled\|absent.*enabled\|unconfigured analyzer" \
  -- internal/engines/saturation/ docs/developer-guide/
```

Scan every hit in comments, docstrings, and dev-guide prose for wording that still
says an absent/unconfigured analyzer defaults to enabled, and update it to the opt-in
contract. Report the hit list in your status file. If a hit is outside your write
scope (e.g. another dev-guide file with a stale claim), note it in a planner handoff
rather than editing across scope.

[↑ TOC](#toc)

## Developer guide {#devguide}

**Target:** `docs/developer-guide/multi-analyzer-pipeline.md`.

Find the section that documents analyzer enablement / the `effectiveEnabled` gate
(grep the file for `effectiveEnabled` / `enabled` / `opt-in`). Update it to state:
an analyzer registered in code participates **only** when explicitly present in
`cfg.Analyzers`; an absent entry means the analyzer does not run and does not affect
scaling decisions; saturation is exempt (guarded by name). Add one sentence noting the
scale-down-veto hazard this prevents.

If the file has no section covering this, add a short subsection under the existing
enablement/config discussion. Do not create forward-looking references to the
lifecycle work — describe only current code (Type 4 rule).

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

Run in order (see CONVENTIONS Pre-push checklist):
1. `git branch --show-current` → `ta-registration-safety`.
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty.
3. `make test` — all pass.
4. `make lint` — clean.
5. DCO: every commit `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` (`git commit -s`).
6. `go build ./...` — clean.

When green, write `plans/session/handoffs/review__ta-registration-safety-ready.md`
(reason: code-review-before-push; refs: this plan + worktree) and stop. Do not push.

[↑ TOC](#toc)
