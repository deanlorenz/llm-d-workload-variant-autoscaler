---
type: review
pr: 1442
title: "feat(saturation)!: default to V2 (token/capacity-based) saturation analyzer"
author: ev-shindin
status: FINAL — approved (LGTM) + 2 non-blocking comments posted 2026-07-22
date: 2026-07-22
---

# PR #1442 Review — V2 saturation analyzer becomes the default

**PR:** [#1442](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1442)
**Author:** ev-shindin
**Base:** main | **Head:** `feat/v2-default-analyzer` (ev-shindin fork) | **State:** open
**Scale:** 12 files, +470/−35
**CI:** all green (lint-and-test, e2e-tests-full 15m43s, e2e-tests-smoke 10m20s, DCO, signed-commits, kustomize-build)
**Reviewed:** 2026-07-22 (no prior reviews/comments on the PR)
**Milestone:** v0.9.0 — V2 default, V1 still selectable (tracking issue #1441)

---

## What it does

Flips the shipped saturation `default` to the **V2 (token/capacity-based)** analyzer by adding an
`analyzers:` section (+ `scaleUpThreshold`/`scaleDownBoundary`) to the two shipped ConfigMaps.
Selection uses the existing `GetAnalyzerName()` mechanism; operators opt back to **V1
(percentage-based)** by deleting the `analyzers:` section. Breaking change per `release-process.md`
(Conventional-Commits `feat(saturation)!:` + `BREAKING CHANGE:` footer + README upgrade note).

Core code change: because analyzer **selection is global** but **thresholds are per-model/namespace**,
a V1-style entry (no `analyzers:`) can be routed onto the V2 path. The PR calibrates the V2
thresholds on the **final resolved config** (post-merge) via a new `ApplyV2ThresholdDefaults()`,
rather than in `ApplyDefaults()`, so a V1-style override cannot clobber a tuned global during
`Merge`. `resolveSaturationConfig` also resets an inverted `scaleUp <= scaleDown` pair produced by a
cross-entry merge, and `Validate()` now range/consistency-checks the V2 thresholds whenever set,
regardless of `IsV2()`.

---

## Verdict

**Correct, well-tested, well-documented. No blocking findings.** Two review-comment items (below),
both non-blocking. Ready to approve once those are addressed or accepted.

---

## Confirmed correct (verified against base source)

- **The "selection global / thresholds per-namespace" premise is real, not hand-waving.**
  - Selection: `engine.go:421-426` reads `e.Config.SaturationConfig()` (pure global) and branches on
    `globalSatCfgMap["default"].GetAnalyzerName()`.
  - Thresholds: `engine.go:584` reads `SaturationConfigForNamespace()` (namespace-local > global) for
    `resolveSaturationConfig`.
  - These are **different sources**: a tenant's namespace-local `default` written V1-style resolves
    to a config with `IsV2()==false`, yet the global flip routes it onto the V2 path. `resolveThresholds`
    (`engine_v2.go:187`) then feeds `cfg.ScaleUpThreshold/ScaleDownBoundary` into `applyUniversalThreshold`.
    Zero thresholds there would break the scale-up/down post-step — so the **post-merge, `IsV2()`-independent
    defaulting is genuinely load-bearing**, and the stated reason for placing it post-merge (not in
    `ApplyDefaults`) is correct given `Merge`'s "non-zero override wins" semantics.
- **`Validate()` tightening has no regression.** Walked old-vs-new branches: the non-zero global range
  check (`< 0 || > 1`) treats exactly-0 as "unset" (defaulted elsewhere); the `IsV2()` block still rejects
  `<= 0` so a skipped-`ApplyDefaults` V2 config is still caught. Inversion is caught by the new non-zero
  relational check. The V1-style-inverted-thresholds-rejected case is the intended tightening.
- **Reset always yields a valid pair:** `DefaultScaleUpThreshold=0.85 > DefaultScaleDownBoundary=0.70`.
- **V1 path is genuinely inert** to the new V2 defaulting (docstring claim verified).
- **Per-analyzer overrides can't create a validation gap:** they require a non-empty `Analyzers` list ⇒
  `IsV2()` true ⇒ still validated in the `IsV2()` block; a V1-style entry can't carry them.
- **`ApplyDefaults` docstring updated** to point at `ApplyV2ThresholdDefaults` — no stale cross-reference.
- **Test quality is high:**
  - `engine_v2_test.go` reproduces **production parse order** (each entry `ApplyDefaults()`'d individually
    before storage); the tuned-global-survives, fully-V1-style-namespace, and inverted-pair-reset specs each
    isolate a distinct path, and the author states the fix-dependent specs fail when the post-merge call is removed.
  - `shipped_configmap_test.go` (new) reads the actual shipped YAML and asserts `IsV2()` + `Validate()` — a
    real guard against a silent YAML/indentation revert to V1 that every e2e suite would otherwise mask.
  - e2e sglang V1-guard reasoning is correct (fixture `token_usage=0.85` sits exactly at V2's
    `scaleUpThreshold=0.85`, which V2 must *exceed* → non-deterministic under V2); fail-fast-on-non-NotFound
    prevents a destructive `AfterAll`. e2e-full passing confirms the helpers compile.

---

## Review-comment items (non-blocking)

### RC-1 — Inverted-pair reset: keep base's validated pair + surface it (middle ground). DECIDED.

`resolveSaturationConfig` currently resets **both** thresholds to hardcoded defaults when a cross-entry
merge yields `scaleUp <= scaleDown`, silently — discarding, e.g., an operator's tuned global `scaleUp=0.95`
when a namespace sets `scaleDown=0.97`. `resolveSaturationConfig` runs in the reconcile hot loop and returns
a value (not an error), so "make it an error" would drop the model from autoscaling on a config typo — worse
than a safe fallback.

**Decision (Dean, 2026-07-22):** middle ground — on inversion, **drop only the override's threshold
contribution and keep the base's validated pair**, and **emit a K8s Event / error log** so the conflict is
visible. This preserves a tuned global and makes the reset loud instead of silent, without dropping the model.

### RC-2 — README upgrade note is silent on the per-model flip. DECIDED (doc-only).

The "Upgrading to v0.9.0" README section covers the global default flip + opt-out, but a reader with existing
**per-model/namespace V1-style overrides** may assume those stay V1; because selection is global, they flip to
V2 too. The developer-guide's "selection is global; thresholds per-model" blockquote covers this well; the
more-prominent README doesn't. **Add one sentence to the README upgrade note.**

> Note on the earlier "make it an error to have both / if the override is silent" idea: a blanket
> "error if both V1 and V2 fields present" is not viable — the shipped V2 `default` intentionally carries the
> V1-only `kvSpareTrigger`/`queueSpareTrigger` fields (so opt-out is just "delete the `analyzers:` block"),
> `Validate()` permits this today, and `shipped_configmap_test.go` depends on it; partial overrides
> (`kvCacheThreshold: 0.85` alone) are silent-on-selection *by design*. The "error on silent mismatch" intent
> is really the per-config-selection redesign — see the out-of-scope note below.

---

## Out of scope for this PR (follow-up)

**Per-config analyzer selection (dissolves the whole class).** Make selection key on the **resolved config's
`IsV2()`** instead of the global `default`. Then a V1-style per-model/namespace override means "this model runs
V1" (also the more intuitive operator model); `ApplyDefaults`'s existing `IsV2()` branch handles thresholds; and
**both `ApplyV2ThresholdDefaults()` and the inverted-pair reset disappear** — the "V1-style entry on the V2 path"
case stops existing. This is a semantic change beyond "flip the default" (a V1-style override would opt a model
back to V1, which some existing overrides may not intend), so it is **not** part of #1442.

**Disposition (Dean, 2026-07-22):** agreed out of scope for #1442; **worth noting in
`planning/optimizer-coordination-design.md`** (the "who owns selection vs. thresholds" thread), **independent of
the #1442 PR comment thread.** Handed to planner to fold into the design doc.
