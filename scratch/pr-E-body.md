## What

Second half of the ThroughputAnalyzer (TA) gate-observability work. Analyzer registration is **frozen at controller startup** — `RegisterAnalyzer(throughput, …)` runs only if TA is enabled at boot, and the registry is never mutated afterward. The `ConfigMapReconciler` hot-updates the in-memory config on every ConfigMap edit, but that only affects *already-registered* analyzers. So **enabling TA by editing the ConfigMap at runtime silently does nothing** until the controller restarts, with no signal that the edit was inert.

This PR adds the signal (0.9 stopgap — a restart is an acceptable operator action for 0.9):
- a **Kubernetes Warning event** on the ConfigMap, reason `ThroughputAnalyzerRestartRequired`, and
- a **log line** telling the operator to restart the controller,

emitted when the live config's TA-enabled state diverges from the registration decision frozen at startup.

Commit 1 extracts `ThroughputAnalyzerEnabled()` onto `config.Config` (one shared predicate for the startup gate and the reconciler). It is otherwise a pure refactor with one deliberate change: rebasing onto #1486 (which added `AnalyzerScoreConfig.Type` / `EffectiveType()`), the extracted gate now matches on `aw.EffectiveType()` like every other analyzer-selection site, so `- type: throughput` enables TA as well as `- name: throughput` (covered by two new test cases). Commit 2 adds the detection + event/log.

## Scope

- "Disabled by default" needs no code (verified at all three layers) — unchanged.
- Out of scope: namespace-local ConfigMaps; the proper fix (removing the frozen-registration gate for true hot enable/disable) is tracked separately as post-0.9 lifecycle work.

## Testing

New `internal/config` + `configmap_reconciler` tests; envtest suite green; lint/gofmt/build clean.

```release-note
The controller now emits a Kubernetes Warning event and a log line advising a restart when a ConfigMap edit enables or disables the ThroughputAnalyzer at runtime, since analyzer registration is fixed at startup.
```
