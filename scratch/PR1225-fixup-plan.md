# PR #1225 Fixup Plan — ev-shindin review response

**Date:** 2026-06-04  
**PR:** [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225) — engines/saturation: multi-analyzer registry  
**Reviewer:** ev-shindin  
**Branch:** `multi-analyzer-registration`  
**Current tip:** `dd9834d2` (4 commits — includes first fixup)

---

## Status — what has already been applied

| Change | Status |
|---|---|
| Rename `RegisterAnalyzer` → `MustRegisterAnalyzer` | ✅ Applied in `dd9834d2` — **needs reverting** (see Change 1 below) |
| Downgrade plugin-failure log level to `V(DEBUG).Info` | ✅ Applied in `dd9834d2` — keep |
| Code comment for config-leak tracking PR #1228 | ✅ Applied in `dd9834d2` — keep |

---

## Change 1 — Revert rename; switch to `error` return (reviewer follow-up)

**Context:** Original comment offered two options: rename to `MustRegisterAnalyzer` OR return `error`. We chose the rename. Reviewer follow-up confirms they prefer `error` return — the repo convention for setup-time misuse is `error`, not panic.

**Revert:** rename `MustRegisterAnalyzer` back to `RegisterAnalyzer`.

**New behaviour — `RegisterAnalyzer` returns `error`:**

```go
// RegisterAnalyzer adds an external analyzer to the engine's analyzer
// registry. Returns an error if called after StartOptimizeLoop or if
// name is already registered. Must complete before StartOptimizeLoop.
func (e *Engine) RegisterAnalyzer(name string, a interfaces.Analyzer) error {
    if e.started {
        return fmt.Errorf("RegisterAnalyzer: called after StartOptimizeLoop")
    }
    for i := range e.analyzers {
        if e.analyzers[i].name == name {
            return fmt.Errorf("RegisterAnalyzer: duplicate analyzer name %q", name)
        }
    }
    e.analyzers = append(e.analyzers, analyzerEntry{name: name, analyzer: a})
    return nil
}
```

**Files to change:**
- `internal/engines/saturation/engine.go` — signature + body
- `internal/engines/saturation/engine_register_test.go` — T3 and T4 flip from `PanicWith` → `MatchError`; T2/T5/T9 add `Expect(...).To(Succeed())` on the return value; rename call sites back to `RegisterAnalyzer`
- `docs/developer-guide/saturation-scaling-config.md` — revert `MustRegisterAnalyzer` back to `RegisterAnalyzer`; update API description to show `error` return and note callers must check it

**No external call sites to update:** `cmd/main.go` on main has no `RegisterAnalyzer` call yet (wired by TA PR-5). The only call sites are in `engine_register_test.go` on this branch.

---

## Change 2 — Downgrade plugin-failure log level (already applied, keep)

Already landed in `dd9834d2`. No further action.

---

## Change 3 — Config-leak comment (already applied, keep)

Already landed in `dd9834d2`. No further action.

---

## Commit plan

One additional commit on top of `dd9834d2`:

```
engines/saturation: RegisterAnalyzer returns error instead of panic

Per reviewer preference: replace the two panic conditions in
RegisterAnalyzer (called-after-Start and duplicate name) with error
returns. Matches repo convention for setup-time misuse — callers that
ignore the error get a clear message at registration time rather than
a panic at startup.

Reverts the MustRegisterAnalyzer rename from the previous fixup;
plain RegisterAnalyzer with error-return semantics is idiomatic.
```

**No force-push needed** — this is a new commit on top of the existing stack, not a history rewrite.

---

## PR comment draft for this follow-up

> Changed `RegisterAnalyzer` to return `error` instead of panicking — reverts the `MustRegisterAnalyzer` rename from the previous push. Both misuse conditions (called after `StartOptimizeLoop`, duplicate name) now return descriptive errors rather than panicking.

---

## PR comment drafts (already published — for reference)

*(Comments 2 and 3 were published in the previous session and do not need updating.)*

---

## Change 2 — Downgrade plugin-failure log level

**Reviewer comment:** `engine_v2.go:197`  
**Rationale:** A persistently broken registered analyzer would spam `Error` logs every optimize cycle (default 30s). The engine itself is healthy; this is a plugin issue, non-fatal. `Error` is too loud.

**File to change:** `internal/engines/saturation/engine_v2.go` — in `runRegisteredAnalyzer`

**Current:**
```go
func runRegisteredAnalyzer(...) {
    defer func() {
        if r := recover(); r != nil {
            logger.Error(fmt.Errorf("panic: %v", r),
                "registered analyzer panicked; result discarded on this branch",
                "name", entry.name, "modelID", modelID)
        }
    }()
    if _, err := entry.analyzer.Analyze(ctx, input); err != nil {
        logger.Error(err, "registered analyzer failed; result discarded on this branch",
            "name", entry.name, "modelID", modelID)
    }
}
```

**Proposed:**
```go
func runRegisteredAnalyzer(...) {
    defer func() {
        if r := recover(); r != nil {
            logger.V(logging.DEBUG).Info("registered analyzer panicked; result discarded",
                "name", entry.name, "modelID", modelID, "panic", r)
        }
    }()
    if _, err := entry.analyzer.Analyze(ctx, input); err != nil {
        logger.V(logging.DEBUG).Info("registered analyzer failed; result discarded",
            "name", entry.name, "modelID", modelID, "error", err)
    }
}
```

**Rationale for `V(logging.DEBUG).Info` over `V(1).Error`:** `Error` still carries the connotation of engine-level failure. Using `Info` at debug verbosity makes clear this is plugin-level noise, not an engine error. Consistent with how the engine logs other non-fatal advisory info.

---

## Change 3 — Acknowledge comment 2 (no code change)

**Reviewer comment:** `engine_v2.go:127` — saturation config leaks threshold overrides into non-saturation analyzers' `AnalyzerInput`.  
**Resolution:** Reply only. Confirm tracked on `multi-analyzer-threshold` (PR #1228).

---

## Commit plan

One commit on top of `66001d47`:

```
engines/saturation: address ev-shindin review — rename + log level

Rename RegisterAnalyzer → MustRegisterAnalyzer per Go Must-prefix
convention for functions that panic on misuse (cf. prometheus.MustRegister).

Downgrade plugin-failure log level from Error to V(DEBUG).Info in
runRegisteredAnalyzer: a persistently broken registered analyzer is a
plugin issue, not an engine error, and Error-logging it every optimize
cycle would spam operator logs with non-actionable noise.
```

Then **force-push** with `--force-with-lease` to `origin/multi-analyzer-registration` (reason: rename changes public API surface, cleaner as amended history than a "fixup" commit on top of a PR the reviewer already read).

---

## PR comment drafts (publish after Dean approves)

### Reply to comment 1 (engine.go:262)

> Good point — renamed to `MustRegisterAnalyzer` in the latest push. Matches the `prometheus.MustRegister` / `regexp.MustCompile` convention.

### Reply to comment 2 (engine_v2.go:127)

> Noted — this is a known wart from the precursor saturation-only threshold-override loop that mutates the local `config` copy before `AnalyzerInput` is built. It's harmless on this branch (non-saturation results discarded), and the clean fix — engine applies thresholds universally after each analyzer runs rather than pre-mutating the config — is the subject of `multi-analyzer-threshold` (PR #1228). I'll add a comment in the code pointing at that PR so it's visible to future readers.

### Reply to comment 3 (engine_v2.go:197)

> Good catch — downgraded to `V(DEBUG).Info` in the latest push. Plugin failure is non-fatal and shouldn't show up as an engine `Error` in operator logs on every cycle.

### Top-level review reply

> Thanks for the review! Addressed in the latest push:
> - Renamed `RegisterAnalyzer` → `MustRegisterAnalyzer` (comment 1)
> - Downgraded plugin-failure logging from `Error` to `V(DEBUG).Info` (comment 3)
> - Comment 2 (threshold override leak into non-saturation `AnalyzerInput`): confirmed harmless on this branch and tracked on PR #1228.
