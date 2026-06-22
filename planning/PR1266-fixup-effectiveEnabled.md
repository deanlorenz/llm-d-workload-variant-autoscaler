# PR #1266 fixup — `effectiveEnabled` opt-in semantics

> ⚠️ **STOPGAP — do not implement as written.** This plan fixes only the absent-entry opt-in default. A more thorough fix is deferred: dynamic enable/disable of all analyzers via runtime config changes, removal of the `throughputAnalyzerEnabled` gate in `cmd/main.go`, and a decision on hot-reload of analyzer registrations. Discuss the full design before coding. See memory `analyzer-dynamic-registration`.

**Type:** 3 (task plan) · **Parent:** #1266 (multi-analyzer-addendum)
**Branch:** new, off `main` after #1266 merges · **Size:** 2-line fix + 1 test update

---

## The bug

`effectiveEnabled` in `internal/engines/saturation/engine_v2.go` returns `true`
when an analyzer has no entry in `cfg.Analyzers`. This means a registered-but-
unconfigured analyzer runs and participates in the all-down veto gate
(`needsScaleDownForRole` requires ALL analyzers in the slice to agree).

Scenario: the throughput analyzer (#1250) is registered in `cmd/main.go`. An
operator's existing config has no `throughput` entry in `Analyzers`. The
throughput analyzer runs, returns `SpareCapacity=0`, and vetoes scale-down —
without the operator ever explicitly enabling it.

The principle should be **opt-in**: an analyzer registered in code must be
explicitly present in `cfg.Analyzers` to participate in scaling decisions.
Saturation is exempt — it is guarded by the `SaturationAnalyzerName` check
before `effectiveEnabled` is ever reached.

---

## Fix

### 1. `internal/engines/saturation/engine_v2.go`

Change the final `return true` in `effectiveEnabled` to `return false`, and
update the comment:

```go
// effectiveEnabled returns true only when the analyzer has an explicit entry
// in cfg.Analyzers that is either enabled:true or has no Enabled field
// (nil, before ApplyDefaults runs). Absent entries return false — analyzers
// are opt-in: an analyzer registered in code does not participate until the
// operator explicitly adds it to cfg.Analyzers.
// Saturation is not subject to this check (it is guarded upstream by the
// SaturationAnalyzerName guard before effectiveEnabled is called).
func effectiveEnabled(analyzerName string, cfg config.SaturationScalingConfig) bool {
    for _, aw := range cfg.Analyzers {
        if aw.Name == analyzerName {
            if aw.Enabled != nil {
                return *aw.Enabled
            }
            return true
        }
    }
    return false  // absent from config → opt-in default: do not run
}
```

### 2. `internal/engines/saturation/engine_v2_population_test.go`

Update the `effectiveEnabled` unit spec for absent entries:

```go
It("returns false when the analyzer is absent from config", func() {
    Expect(effectiveEnabled("throughput", config.SaturationScalingConfig{})).To(BeFalse())
})
```

(Was `BeTrue()`.)

---

## Impact check

- Saturation: unaffected — excluded by name guard before `effectiveEnabled`.
- Existing single-analyzer configs: unaffected — `ApplyDefaults` always
  ensures a saturation entry exists; saturation runs unconditionally.
- Multi-analyzer configs with explicit entries: unaffected — explicit entries
  are found in the loop; `Enabled` nil → `true`, `false` → `false`.
- Unconfigured registered analyzers: now disabled by default (opt-in). **This
  is the intended behavior change.** Operators must add the analyzer to
  `cfg.Analyzers` to enable it.

---

## Commit

```
engines/saturation: effectiveEnabled — opt-in default for unconfigured analyzers

An analyzer absent from cfg.Analyzers now returns false (disabled) rather
than true (enabled). Registered-but-unconfigured analyzers no longer run
and cannot veto scale-down. Operators must explicitly add an Analyzers entry
to enable a non-saturation analyzer.

Saturation is unaffected (name guard runs before effectiveEnabled is reached).
```

Sign-off: `--signoff`

---

## When to land

After #1266 merges. Single commit, base `main`. No other files touched.
