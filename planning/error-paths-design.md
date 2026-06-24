# Error Paths Design — WVA Analyzers

**Status:** DRAFT (2026-06-24)
**Supersedes:** GitHub issue #1261 — that issue is too narrow; this doc covers the full
design and will be used to file a replacement top-level feature issue with sub-issues.
**Related:** `planning/multi-analyzer-design.md` § Future direction F3 (original proposal,
superseded by this doc); `planning/TA-forward-plan.md` § I-17

---

## TOC {#toc}

- [Background](#background) L35:45
- [Core Engine/Optimizer Rules](#core-engineoptimizer-rules) L46:62
- [Problem Summary](#problem-summary) L63:101
- [Design Principle — Separation of Diagnosis and Decision](#design-principle--separation-of-diagnosis-and-decision) L102:120
- [Issue Structure](#issue-structure) L121:138
- [Signal Vocabulary — MeasurementBias](#signal-vocabulary--measurementbias) L139:184
- [Engine/Optimizer — Bias-to-Action Mapping](#engineoptimizer--bias-to-action-mapping) L185:230
  - [SC (SpareCapacity / scale-down signal)](#sc-sparecapacity--scale-down-signal) L187:199
  - [RC (RequiredCapacity / scale-up signal)](#rc-requiredcapacity--scale-up-signal) L200:212
  - [Cross-analyzer behavior](#cross-analyzer-behavior) L213:230
- [GPS Mismatch — Design](#gps-mismatch--design) L231:272
  - [Direction analysis](#direction-analysis) L238:250
  - [Escalation state machine (tracked inside TA)](#escalation-state-machine-tracked-inside-ta) L251:272
- [Analyzer Error Path Inventory](#analyzer-error-path-inventory) L273:343
  - [Throughput Analyzer (TA) — analyzer-level errors](#throughput-analyzer-ta--analyzer-level-errors) L275:286
  - [Throughput Analyzer (TA) — per-variant errors](#throughput-analyzer-ta--per-variant-errors) L287:298
  - [Throughput Analyzer (TA) — internal helper return-0 violations](#throughput-analyzer-ta--internal-helper-return-0-violations) L299:322
  - [Saturation Analyzer (sat_v2) — per-variant errors](#saturation-analyzer-satv2--per-variant-errors) L323:333
  - [Queueing Model (QM) — deferred](#queueing-model-qm--deferred) L334:343
- [Work Checklist](#work-checklist) L344:390
- [Deferred](#deferred) L391:400

## Background

The WVA engine runs one or more analyzers each cycle. Each analyzer produces an
`AnalyzerResult` containing `SpareCapacity` (SC — how much capacity can safely be
removed) and `RequiredCapacity` (RC — how much additional capacity is needed).
The engine's threshold post-step computes these from each analyzer's measured
`TotalSupply` and `TotalDemand` across all variants. The optimizer then allocates
scale-up and scale-down decisions across variants and roles.

[↑ TOC](#toc)

## Core Engine/Optimizer Rules

These rules are fixed and govern how analyzer results are combined:

- **Scale UP on any:** if any analyzer signals positive required capacity, scale up.
- **Scale DOWN on consensus:** a scale-down proceeds only if all participating analyzers
  agree — i.e., none zero out their SC contribution.

As a consequence, every analyzer has implicit veto power on scale-down. If only one
analyzer is enabled and it has an unreliable signal, scale-up does not happen
automatically — the directional hint on RC (described below) is how the engine remains
useful in a degraded state.

[↑ TOC](#toc)

---

## Problem Summary

Several error conditions in the analyzer stack are currently invisible to the engine:

1. **No degraded-signal contract.** When an analyzer's result is unreliable (supply model
   wrong, demand data missing), it returns a normal `AnalyzerResult` with no flag. The
   engine cannot distinguish a reliable result from a degraded one and may make wrong
   scale-up or scale-down decisions.

2. **TA silent variant omission.** When the Throughput Analyzer (TA) cannot analyze a
   variant (missing KV capability, no scheduler queue data for that variant, insufficient
   replica data), it silently skips the variant via `continue`. The engine receives a
   partial result with no indication of what was omitted. `TotalDemand` is understated;
   `RequiredCapacity` may be too low.

3. **Sat_v2 all-replicas-missing.** When the saturation analyzer cannot obtain
   `cache_config_info` for any replica of a variant, it computes a zero-valued
   `VariantCapacity` entry with no error signal. The per-replica capacity (PRC) cannot
   be estimated, but the engine sees a normal zero-demand entry.

4. **TA internal helpers return 0 on error.** Several internal functions in the
   Throughput Analyzer return `0` or `(0, 0, 0)` on error conditions where `0` is also
   a valid result. Callers cannot distinguish a legitimate zero from a failure.

5. **QM zero-valued entries.** The Queueing Model analyzer appends an all-zero
   `VariantCapacity` entry when a variant has no metrics or traffic data. Zero demand
   implies large spare capacity, which can trigger a spurious scale-down. **This item
   is deferred** — QM requires a broader overhaul; it is listed here for completeness
   and will use the same error contract once reworked.

**Design constraint:** All analyzers (sat_v2, TA, QM, future analyzers) must propagate
errors to the engine using the same contract. The contract must accommodate all known
error paths. If a new error path cannot be expressed, the contract is extended — not
worked around with analyzer-specific behavior.

[↑ TOC](#toc)

---

## Design Principle — Separation of Diagnosis and Decision

The **analyzer** knows the implication of its own errors. It reports a
*measurement bias* — what it knows about the direction and reliability of each
computed metric — as a structured signal.

The **engine/optimizer** maps that signal to a conservative action (zero out SC,
tighten thresholds, or exclude the analyzer). The engine may also track
cross-analyzer patterns, but does not require complex history — if the signal
changes, the engine behavior changes with it.

This separation keeps the interface stable: an analyzer never says "veto" or
"sit out" (those are policy decisions). It says "I computed SC but it is
overestimated" or "I have no measurement for this variant."

[↑ TOC](#toc)

---

## Issue Structure

File one top-level feature issue linking to this doc, with sub-issues per component:

```
[feat] Structured analyzer error propagation
  └─ [sub] MeasurementBias interface contract (AnalyzerResult + VariantCapacity)
  └─ [sub] Engine/optimizer bias-aware decisions
  └─ [sub] TA internal return-0 cleanup (prerequisite for TA wiring)
  └─ [sub] TA error path wiring (GPS mismatch, EPP absent, per-variant missing data)
  └─ [sub] Sat_v2 error path wiring (all-replicas-missing)
  └─ [sub] Observability — log/event on degraded analyzer state
```

[↑ TOC](#toc)

---

## Signal Vocabulary — MeasurementBias

A single shared type expresses the quality of a computed metric (SC or RC) at both
the analyzer-result level and the per-variant level:

```go
// MeasurementBias describes what an analyzer knows about the direction of error
// in a computed metric (SpareCapacity or RequiredCapacity).
// The analyzer sets this; the engine/optimizer decides the action.
type MeasurementBias int

const (
    BiasOK             MeasurementBias = iota // reliable; use as-is
    BiasOverestimated                          // metric is higher than actual reality
    BiasUnderestimated                         // metric is lower than actual reality
    BiasEstimated                              // stale or extrapolated data used;
                                               // direction believed correct, lower confidence
    BiasUnreliable                             // computed but direction unknown
    BiasNoData                                 // could not compute at all
)
```

`MeasurementBias` is added to both `AnalyzerResult` (one bias per metric across all
variants) and `VariantCapacity` (one bias per metric for that variant):

```go
// Added to AnalyzerResult:
SCBias MeasurementBias  // bias in the aggregate SpareCapacity for this result
RCBias MeasurementBias  // bias in the aggregate RequiredCapacity for this result

// Added to VariantCapacity:
SCBias MeasurementBias  // bias in this variant's contribution to SpareCapacity
RCBias MeasurementBias  // bias in this variant's contribution to RequiredCapacity
```

**Disabled-for-cycle.** When an analyzer has no usable result for a cycle (EPP queue
absent, config error, all variants failing), it returns `BiasNoData` on both fields at
the result level. The engine treats this as the analyzer being absent for that cycle —
equivalent to the existing `(nil, error)` return path, but structured so that
observability (logging, K8s events) can distinguish "TA not configured" from
"TA disabled this cycle due to missing EPP."

[↑ TOC](#toc)

---

## Engine/Optimizer — Bias-to-Action Mapping

### SC (SpareCapacity / scale-down signal)

| SCBias | Engine action |
|---|---|
| `BiasOK` | Use SC as-is |
| `BiasOverestimated` | Zero SC for this analyzer (do not scale down based on this result) |
| `BiasUnderestimated` | Participate in scale-down, but require a higher spare-capacity threshold before acting |
| `BiasEstimated` | Participate in scale-down; apply a slight conservative threshold offset; log warning |
| `BiasUnreliable` | Zero SC for this analyzer (direction unknown — same conservative treatment as Overestimated) |
| `BiasNoData` | Exclude this analyzer from the scale-down decision entirely |

[↑ TOC](#toc)

### RC (RequiredCapacity / scale-up signal)

| RCBias | Engine action |
|---|---|
| `BiasOK` | Use RC as-is |
| `BiasOverestimated` | Use RC; scale-up may be more than strictly needed, but over-provisioning is tolerable |
| `BiasUnderestimated` | Use RC but apply a tighter (more conservative) scale-up threshold — the analyzer is signaling under-provisioning risk |
| `BiasEstimated` | Use RC; apply a slight conservative threshold offset; log warning |
| `BiasUnreliable` | Use RC with the most conservative threshold; log warning |
| `BiasNoData` | Exclude this analyzer from the scale-up decision entirely |

[↑ TOC](#toc)

### Cross-analyzer behavior

Scale-down requires consensus. An analyzer with `SCBias == BiasOverestimated` or
`BiasUnreliable` zeros its SC contribution, which prevents scale-down from that
analyzer's perspective — because the remaining analyzers alone must supply the full
consensus. An analyzer with `SCBias == BiasNoData` is excluded entirely; the remaining
analyzers form the consensus without it. An analyzer with `BiasUnderestimated` or
`BiasEstimated` still participates (non-zero SC, conservative threshold), so it does
not by itself block scale-down.

For scale-up: `BiasNoData` excludes the analyzer. All other states contribute RC
(with varying threshold conservatism). "Scale up on any" means a single participating
analyzer with positive RC is sufficient to trigger scale-up.

[↑ TOC](#toc)

---

## GPS Mismatch — Design

GPS (Generated-Tokens-Per-Second) mismatch: the measured throughput of a variant
deviates significantly from what TA's ITL(k_sat) model predicts. When this occurs,
TA's per-replica capacity (PRC) estimate is based on a wrong model, making both SC
and RC unreliable.

### Direction analysis

| Mismatch direction | PRC estimate | SC effect | RC effect |
|---|---|---|---|
| Actual < predicted (replicas slower than model) | Overestimated | SC too high → `SCBias = BiasOverestimated` | RC too low → `RCBias = BiasUnderestimated` |
| Actual > predicted (replicas faster than model) | Underestimated | SC too low → `SCBias = BiasUnderestimated` | RC too high → `RCBias = BiasOverestimated` |
| Direction cannot be determined | Unknown | `SCBias = BiasUnreliable` | `RCBias = BiasUnreliable` |

TA computes both predicted and actual throughput, so it can determine the mismatch
direction and set the bias fields accordingly rather than defaulting to `Unreliable`.

[↑ TOC](#toc)

### Escalation state machine (tracked inside TA)

TA's internal state store already maintains per-variant state across cycles. TA
increments a per-variant mismatch counter and escalates the returned bias:

```
OK → GPS mismatch detected this cycle
  → [short-term] return directional bias (Overestimated or Underestimated)
     if estimator resets (transient blip clears) → return to BiasOK
  → [sustained, N consecutive cycles] return BiasUnreliable
     (direction confidence lost; N is a configurable threshold, TBD)
  → [all variants sustained] result-level SCBias=NoData, RCBias=NoData
     (TA effectively disabled for the cycle)
```

The engine does not maintain separate persistence for GPS mismatch — TA's returned
bias already reflects the escalation. The engine acts on the current cycle's signal.

[↑ TOC](#toc)

---

## Analyzer Error Path Inventory

### Throughput Analyzer (TA) — analyzer-level errors

| Condition | Current behavior | Target signal |
|---|---|---|
| `SchedulerQueue == nil` (EPP queue absent) | `_ = anyEPP` — silently ignored | Result: `SCBias=NoData, RCBias=NoData` (TA disabled for cycle) |
| `anyGPSMismatch` (actual < predicted) | `_ = anyGPSMismatch` — ignored | Per-variant + result: `SCBias=Overestimated, RCBias=Underestimated` |
| `anyGPSMismatch` (actual > predicted) | `_ = anyGPSMismatch` — ignored | Per-variant + result: `SCBias=Underestimated, RCBias=Overestimated` |
| `anyGPSMismatch` sustained N cycles | `_ = anyGPSMismatch` — ignored | Escalate to `SCBias=Unreliable, RCBias=Unreliable` per variant |
| `anyGPSMismatch` all variants sustained | `_ = anyGPSMismatch` — ignored | Result: `SCBias=NoData, RCBias=NoData` |

[↑ TOC](#toc)

### Throughput Analyzer (TA) — per-variant errors

| Condition | Current behavior | Target signal |
|---|---|---|
| Variant missing KV capability | `continue` — variant silently dropped | `VariantCapacity` entry with `SCBias=NoData, RCBias=NoData` |
| Variant missing scheduler queue data | `continue` — variant silently dropped | `VariantCapacity` entry with `SCBias=NoData, RCBias=NoData` |
| Insufficient replica data for variant, prior-cycle store data available | `continue` — variant silently dropped | `VariantCapacity` entry with `SCBias=Estimated, RCBias=Estimated` |
| Insufficient replica data for variant, no prior store data | `continue` — variant silently dropped | `VariantCapacity` entry with `SCBias=NoData, RCBias=NoData` |
| Internal helper returns 0 on error (see section below) | 0 indistinguishable from valid value | Fix return type; propagate error to set variant bias fields |

[↑ TOC](#toc)

### Throughput Analyzer (TA) — internal helper return-0 violations

Several TA helper functions return `0` or `(0, 0, 0)` on error conditions where `0`
is also a valid computed value, making the error invisible to callers:

| File:Line | Condition | Current return | Required fix |
|---|---|---|---|
| `internal/engines/analyzers/throughput/analyzer.go:566` | No replicas eligible for local demand | `return 0` | `return 0, err` — 0 is valid demand |
| `internal/engines/analyzers/throughput/analyzer.go:593` | Invalid queue parameters | `return 0` | `return 0, err` |
| `internal/engines/analyzers/throughput/analyzer.go:615-616` | No KV-capable replicas in variant | `return 0, 0, 0` | `return 0, 0, 0, err` |
| `internal/engines/analyzers/throughput/analyzer.go:654` | No eligible replicas for shape averaging | `return 0, 0, 0` | `return 0, 0, 0, err` |
| `internal/engines/analyzers/throughput/analyzer.go:678` | Division-by-zero guard | `return 0` | `return 0, err` |

Fix rule: `0` is only acceptable as an error sentinel if `0` cannot be a valid return
value for that function. Follow standard Go: `(value, error)` for fallible functions;
`*T` where `nil` signals absence. Errors from these functions propagate up to the
variant processing loop in `Analyze()`, where they set `SCBias` / `RCBias` on the
`VariantCapacity` entry.

These fixes are a prerequisite for the TA error-wiring work above: the error must
reach `Analyze()` before it can be expressed as a bias.

[↑ TOC](#toc)

### Saturation Analyzer (sat_v2) — per-variant errors

| Condition | Current behavior | Target signal |
|---|---|---|
| All replicas of a variant missing `cache_config_info` | Zero `VariantCapacity` appended (silent) | `VariantCapacity` entry with `SCBias=NoData, RCBias=NoData` |
| Some replicas of a variant missing `cache_config_info` | PRC median computed from available subset | No change — partial subset is valid; replicas are assumed identical, so missing metrics for some do not change PRC |
| Config type mismatch | `return nil, error` | Existing `(nil, error)` return is sufficient |
| Context cancellation | `return nil, error` | Existing `(nil, error)` return is sufficient |

[↑ TOC](#toc)

### Queueing Model (QM) — deferred

| Condition | Current behavior | Note |
|---|---|---|
| Variant has no metrics or traffic data | All-zero `VariantCapacity` appended | Zero demand → overstated SC → bad scale-down risk. Fix deferred with QM overhaul. When reworked, use `MeasurementBias` contract. |

[↑ TOC](#toc)

---

## Work Checklist

**Interface contract (foundation — all other items depend on this):**
- [ ] File top-level feature issue + sub-issues; close #1261 as superseded
- [ ] Define `MeasurementBias` type in `internal/interfaces/`
- [ ] Add `SCBias`, `RCBias MeasurementBias` to `AnalyzerResult`
- [ ] Add `SCBias`, `RCBias MeasurementBias` to `VariantCapacity`

**Engine/optimizer:**
- [ ] Engine post-step: apply SC bias-to-action mapping (zero SC on Overestimated/Unreliable;
      conservative threshold on Underestimated/Estimated; sit-out on NoData)
- [ ] Engine post-step: apply RC bias-to-action mapping (conservative threshold on
      Underestimated/Estimated/Unreliable; sit-out on NoData)
- [ ] Optimizer: per-variant bias-aware allocation — NoData variants excluded from
      this analyzer's SC/RC contribution; other bias values use conservative thresholds

**TA — return-0 fixes (prerequisite for TA wiring):**
- [ ] Fix `analyzer.go:566` — `return 0` → `return 0, err`
- [ ] Fix `analyzer.go:593` — `return 0` → `return 0, err`
- [ ] Fix `analyzer.go:615-616` — `return 0, 0, 0` → `return 0, 0, 0, err`
- [ ] Fix `analyzer.go:654` — `return 0, 0, 0` → `return 0, 0, 0, err`
- [ ] Fix `analyzer.go:678` — `return 0` → `return 0, err`

**TA — error wiring:**
- [ ] Wire `SchedulerQueue == nil` → result-level `SCBias=NoData, RCBias=NoData`
- [ ] Wire `anyGPSMismatch` (directional) → per-variant and result-level SC/RC bias
- [ ] Implement GPS mismatch escalation counter in TA state store
      (directional → Unreliable after N cycles; all-variants Unreliable → NoData at result level)
- [ ] Wire per-variant missing KV / missing data → `SCBias=NoData, RCBias=NoData`
      (or `Estimated` when prior-cycle store data is available for the variant)
- [ ] Remove dead `_ = anyEPP`, `_ = anyGPSMismatch` placeholders

**Sat_v2 — error wiring:**
- [ ] Wire all-replicas-missing for a variant → `VariantCapacity` entry with
      `SCBias=NoData, RCBias=NoData`

**Observability:**
- [ ] Log warning + K8s event when result-level `SCBias=NoData && RCBias=NoData`
      (analyzer disabled for cycle) — satisfies I-5 observability goal
- [ ] Log warning when any per-variant or result-level bias is not `BiasOK`
- [ ] Include `SCBias` / `RCBias` fields in the structured per-cycle log lines
      (the `analyzer-result` log line introduced in PR #1318)

[↑ TOC](#toc)

---

## Deferred

**QM zero-valued VariantCapacity** — fix deferred pending QM overhaul. Root problem:
`errorVariantCapacity` in `internal/engines/analyzers/queueingmodel/analyzer.go:284-295`
appends an all-zero `VariantCapacity` (zero demand, zero capacity) for variants with
missing metrics. Zero demand produces inflated SC, which can trigger a spurious
scale-down. A `// TODO` comment at line 291 already flags this. When QM is overhauled,
it must adopt the `MeasurementBias` contract defined above.

[↑ TOC](#toc)
