# TA3.1 — Complete PR #1250 + Post-Review Follow-Up (PR-B)

> **Status: ACTIVE** — Bug A/B/C done + rebased + pushed (`b0284253`). **Round-2
> review fixes pending** (smoke `saturation_v2_test.go:280` failing — throughput
> veto; see "Review-driven fixes (round 2)" below). D1/D2/T1/T2 already in PR;
> PR-B STANDBY.
>
> Triage doc: [`planning/PR1250-review.md`](PR1250-review.md)
> Rebase resolution: [`planning/PR1267-impact-and-decisions.md`](PR1267-impact-and-decisions.md)

---

## Review-driven fixes (round 2) — Coder Task

A code review of #1250 surfaced 5 should-fix items + nits. The headline is a
**real CI failure**: the smoke test `saturation_v2_test.go:280` ("V2 should
recommend scale-down …") fails because the ThroughputAnalyzer is registered
unconditionally and, post-#1246, its result is consumed in the optimizer's
cross-analyzer scale-down aggregation. With no usable throughput data in the
smoke env it contributes `RoleSpare ≤ 0`; `safeRemovalReplicasForRole`
(`internal/engines/pipeline/analyzer_helpers.go`) takes the **min** across
analyzers and returns 0 if any contributor has `RoleSpare ≤ 0` → the saturation
scale-down is vetoed → `no-change` at utilization 0.333.

Scope decision (Dean, 2026-06-16): **fix all of items 1–5 + nits in this pass.**

### Approach & rationale — registration gate (item 5, the CI fix)

**Decision: make the ThroughputAnalyzer opt-in by gating its *registration* on
config.** In `cmd/main.go`, only call `RegisterThroughputAnalyzerQueries` +
`engine.RegisterAnalyzer(throughput…)` when the saturation config enables the
throughput analyzer. The shipped default config lists only
`analyzers: [{name: saturation}]`, so by default throughput is never registered
→ never in `analyzersSnapshot` → the consumption loop never sees it → no veto.
Behaves "as if throughput did not exist" by default. **No dependency on #1266**
(its `effectiveEnabled` gate is not in TA3's base, and even merged it defaults
absent→enabled, so it would not skip an unlisted-but-registered analyzer).

*Why a registration (startup) gate and not a consumption gate:* the consumption
gate is the correct long-term home (`effectiveEnabled` opt-in fix, tracked in
[`PR1266-fixup-effectiveEnabled.md`](PR1266-fixup-effectiveEnabled.md)) — it
honors runtime configmap toggles. The registration gate is a self-contained
stopgap that unblocks #1250 now without touching the engine/optimizer.

*Known limitation (document in code + dev-guide):* registration is frozen after
`StartOptimizeLoop`, so the gate is **startup-time** — enabling throughput via a
runtime configmap edit requires a controller restart. When the consumption-gate
opt-in fix lands, **remove this registration gate** so live toggling works. The
gate is explicitly a stopgap.

### Item 5 — registration gate (`cmd/main.go` ~L465)

Add a helper and wrap the two registration calls:

```go
// throughputAnalyzerEnabled reports whether any saturation config entry lists
// the throughput analyzer with enabled != false. Startup-time gate: an
// unconfigured deployment never registers (and therefore never consumes) the
// throughput analyzer, so it cannot influence scaling. Runtime enablement via
// configmap requires a controller restart (registration is frozen after
// StartOptimizeLoop). The per-cycle consumption gate is the long-term home and
// supersedes this stopgap; see the effectiveEnabled opt-in follow-up.
func throughputAnalyzerEnabled(cfg <match existing cfg type>) bool {
	for _, sc := range cfg.SaturationConfig() { // default + any per-model/namespace entries
		for _, aw := range sc.Analyzers {
			if aw.Name == throughput.AnalyzerName && (aw.Enabled == nil || *aw.Enabled) {
				return true
			}
		}
	}
	return false
}
```

```go
if throughputAnalyzerEnabled(cfg) {
	registration.RegisterThroughputAnalyzerQueries(sourceRegistry)
	if err := engine.RegisterAnalyzer(throughput.AnalyzerName, throughput.NewThroughputAnalyzer()); err != nil {
		return err
	}
}
```

- Match the existing `cfg` type in `cmd/main.go` (`cfg.SaturationConfig()` returns
  `map[string]config.SaturationScalingConfig`).
- Iterating **all** entries (not just `"default"`) means a per-model/namespace
  override that enables throughput at startup also registers it.

**E2E wiring test (`test/e2e/throughput_analyzer_test.go`):** it writes
`throughputBothEnabledConfig` in `BeforeAll` *at runtime*, but the controller is
already running with the default (saturation-only) config — so with the gate,
throughput won't register. The test's assertions are generic (MetricsAvailable +
DesiredOptimizedAlloc, satisfied by saturation alone), so it stays green but
stops actually exercising throughput. **Make it a true wiring check:** after
writing the both-enabled config, trigger a controller rollout restart
(`kubectl rollout restart deploy/<controller> -n <ns>` equivalent via the e2e
client) and wait for the new pod Ready before asserting, so the gate registers
throughput at the new start. If a restart is impractical in the smoke harness,
fall back to: keep the test green via generic assertions, add a code comment that
it no longer exercises throughput wiring under the opt-in gate, and note the gap
in the handoff for a follow-up. Coder picks based on harness feasibility and
reports which path was taken.

### Item 1 — tier-2 OLS uses unfiltered metrics (`analyzer.go:249, :292`)

`Observe` filters to healthy replicas (`filterHealthyForShape`, L122) but
`Analyze` passes raw all-replica `variantMetrics` into `resolveITLModel` (L249)
and `checkVariantGPSMismatch` (L292). Stale replicas with a frozen high `AvgITL`
bias tier-2 OLS slope A upward → systematic under-provisioning.

Fix: in the `Analyze` per-variant loop, compute once
`healthyMetrics := filterHealthyForShape(variantMetrics)` and pass `healthyMetrics`
to **both** `resolveITLModel` and `checkVariantGPSMismatch`. **Keep the unfiltered
`variantMetrics`** for supply-side replica counting (booting replicas should count
toward supply) — identify those uses in the loop and leave them on `variantMetrics`.

### Item 2 — `FitITLModel` lacks ITL-at-saturation guard (`itl_model.go` ~L50)

A noisy OLS can yield negative intercept B with valid A>0, making `ITLAt(DefaultKSat)`
near-zero/negative and inflating supply `nSat/itlSat`. After the existing `if A <= 0`
guard add:

```go
if A*DefaultKSat + B <= 0 {
	return ITLModel{}, false
}
```

Tier-2 (constrained OLS in `resolveITLModel`) pins B ≥ `DefaultBaselineITLSec`
(0.006) and requires A>0, so `A·kSat+B > 0` always — no guard needed there. Only
`FitITLModel` (tier-1) needs it.

### Item 3 — remove dead `itl_knowledge_store.go` (+ its test)

`itlKnowledgeStore` is declared and unit-tested but never wired into
`ThroughputAnalyzer` (verified: no non-test references). Remove both
`internal/engines/analyzers/throughput/itl_knowledge_store.go` and
`internal/engines/analyzers/throughput/itl_knowledge_store_test.go`. Check
`constants.go` for any constant used **only** by the store and remove if orphaned.
`go build ./...` + `make test` must stay green.

### Item 4 — remove dead `has*` sentinels (`replica_metrics.go:364/366/368, :706/725/744`)

`hasGenTokenRate` / `hasKvInstant` / `hasVLLMRate` are written but never read.
They were added (Bug A) as the "internal half" of #1264, but #1264's public half
(`*float64` fields in `interfaces.ReplicaMetrics`) is deferred, so there is no
consumer and gating the field copy would be a no-op. **Remove** the three struct
fields and their three assignment lines. #1264 reintroduces them together with the
consumer when it lands. (Supersedes the Bug A Fix-2 note above that added them.)

### Nits (fold in)

- **`RolePrefill` constant.** Add `RolePrefill = "prefill"` in
  `internal/interfaces/saturation_analyzer.go` next to `RoleBoth`; use it at
  `analyzer.go:287` and `:761` in place of the `"prefill"` string literal.
- **Doc comment** on `recordUnattributedReadyPodsEvent` (`replica_metrics.go:96`)
  — explain the one-event-per-VA-per-cycle dedup via `vaEventTracker`.
- **`ctrl.LoggerFrom(ctx)` over `ctrl.Log`** in `Observe`/`Analyze` bodies (keeps
  reconcile-scoped fields). For helpers without `ctx` (`resolveITLModel`,
  `checkVariantGPSMismatch`), thread the logger from the caller only if cheap;
  otherwise leave and note it. Coder judgment.

**NOT folded — deferred:** the nit "capture `Observe`'s returned `SanityReport`
map in `Analyze`" is coupled to gating demand on the sanity report, which is the
deferred [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261)
work. Capturing it now with no consumer would be an unused variable (lint fail).
Leave the `TODO(#1261)` at `analyzer.go:247` as-is.

### Semantic cross-reference greps (run after edits, update every hit)

- `grep -rn "hasGenTokenRate\|hasKvInstant\|hasVLLMRate" internal/` → must be empty after item 4.
- `grep -rn "itlKnowledgeStore\|ITLKnowledgeStore\|NewITLKnowledgeStore" internal/` → must be empty after item 3.
- `grep -rn '"prefill"' internal/engines/analyzers/throughput/` → only doc-comment/string-doc occurrences may remain; code literals at :287/:761 become `interfaces.RolePrefill`.

### Suggested commit structure

1. `cmd: register throughput analyzer only when enabled in config` — item 5 + dev-guide note (throughput is opt-in) + e2e wiring-test adjustment.
2. `engines/throughput: filter stale replicas from ITL fit; guard ITL-at-saturation` — items 1 + 2.
3. `engines/throughput, collector: remove dead itl_knowledge_store and has* sentinels` — items 3 + 4.
4. `engines/throughput: RolePrefill const; doc comment; reconcile-scoped logger` — nits.

### Dev-guide

Update `docs/developer-guide/throughput-analyzer.md`: add a short "Enablement"
note — the analyzer is **opt-in**, registered only when the saturation config
lists `throughput` (enabled), and that runtime enablement currently requires a
controller restart (startup-time gate; stopgap pending the per-cycle consumption
gate). Reflect actual code state only.

### Gates + push

Standard pre-push (CONVENTIONS): `gofmt` clean, `make test` pass, `make lint`
clean, `go build ./...` clean, DCO on every commit. Then internal review
(`review__TA3-ready.md` trigger) before requesting the push from Dean.

---

## Complete #1250 — Coder Task

Two bugs from ev-shindin's review are fixed (`ce39267e`). The remaining
task is: rebase onto `main@04f95779` resolving 3-file conflict, fold in
`UnattributedReadyPods` event (Bug C below), gates, push.

### Bug A — throughput metrics always zero (key mismatch)

**Root cause (pre-existing, introduced in #1051/TA1):**
`replica_metrics.go` processes the three throughput query results using
`value.Labels["pod"]` as the `podData` map key (bare pod name, e.g.
`"pod-abc"`). All other processing loops use `buildInstanceKey(value.Labels)`
which produces a composite `"pod-abc:8000"` key. The entries never merge.
At assembly, the throughput-only entry has `hasKv = false` and is dropped.
Result: `GenerationTokenRate`, `KvUsageInstant`, and `VLLMRequestRate` are
always zero in every `ReplicaMetrics` the throughput analyzer receives.

The throughput queries also need `instance` in their `by()` clause so the
result labels include it — `buildInstanceKey` cannot produce the composite
key from `pod`-only results.

**Fix 1 — `internal/collector/registration/throughput_analyzer.go`**

Change all three `by()` clauses to include `instance` and `llm_d_ai_variant`:

```
// Before (lines 108, 120, 133):
sum by (pod) (rate(vllm:request_generation_tokens_sum{...}[1m]))
max by (pod) (vllm:kv_cache_usage_perc{...})
sum by (pod) (rate(vllm:request_generation_tokens_count{...}[1m]))

// After:
sum by (instance, pod, llm_d_ai_variant) (rate(vllm:request_generation_tokens_sum{...}[1m]))
max by (instance, pod, llm_d_ai_variant) (vllm:kv_cache_usage_perc{...})
sum by (instance, pod, llm_d_ai_variant) (rate(vllm:request_generation_tokens_count{...}[1m]))
```

Add the standard preserve comment above each registration (matching
saturation.go pattern):
```go
// Preserves instance (IP:port for composite key), pod (for pod lookup),
// and llm_d_ai_variant (for direct pod-to-VA mapping).
```

Note: `llm_d_ai_variant` in the `by()` clause handles VA attribution on
current main. It is a temporary addition: once PR #1260 (pod→VA derivation)
and issue #1263 (remove label from all groupbys) land on main, this label
is dropped from all three queries in a follow-up commit. #1263 is the
explicit tracker for that cleanup across all analyzer queries.

**Fix 2 — `internal/collector/replica_metrics.go`**

In the three throughput processing loops (lines ~558, ~579, ~600), replace
the bare-pod-key pattern with `buildInstanceKey`. Also add `has*` boolean
fields to `podMetricData` (aligns with issue #1264 direction):

```go
// In podMetricData struct — add alongside the existing fields:
hasGenTokenRate bool
hasKvInstant    bool
hasVLLMRate     bool

// Before (same pattern in all three loops):
podName := value.Labels["pod"]
if podName == "" {
    podName = value.Labels["pod_name"]
}
if podName == "" {
    continue
}
if podData[podName] == nil {
    podData[podName] = &podMetricData{}
}
podData[podName].generationTokenRate = value.Value   // (or .kvUsageInstant / .vllmRequestRate)

// After:
instanceKey, podName, _ := buildInstanceKey(value.Labels)
if instanceKey == "" {
    continue
}
if podData[instanceKey] == nil {
    podData[instanceKey] = &podMetricData{}
}
podData[instanceKey].generationTokenRate = value.Value   // (or .kvUsageInstant / .vllmRequestRate)
podData[instanceKey].hasGenTokenRate = true              // (or .hasKvInstant / .hasVLLMRate)
```

`podName` from `buildInstanceKey` is available for logging if needed; the
map key changes from bare pod name to composite instance key.

The `has*` flags are the internal half of issue #1264's minimum fix
(distinguishing "metric not collected" from "genuine zero"). The public
half — propagating the three throughput fields as `*float64` in
`interfaces.ReplicaMetrics` — is follow-up work tracked in #1264 and
does not need to land in this PR. The flags are cheap to add now and
avoid a second pass through this struct when #1264 work begins.

### Bug B — ev-shindin review: three small comment/doc items

In `internal/engines/analyzers/throughput/analyzer.go`:

- **Line 208** — add one-line comment: `Analyze` is assumed single-flight;
  concurrent `VariantState()` snapshots may observe partial state across the
  lock gaps.
- **Line 343** — update the TODO comment to note scale-down risk explicitly
  and link [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261).
- **Line 243** — update the TODO comment to note sanity-gate deferral and
  link [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261).

### Bug C — UnattributedReadyPods event (fold-in from #1275)

The only non-superseded piece from the closed `collector-va-attribution` (#1275)
branch is a per-VA K8s Warning event fired when a scale target has Ready pods
but none were attributed this cycle. Fold into the same rebase commit since it
lives in the same file/layer (`replica_metrics.go`). Source: squashed commit
`6c0c6d7d` on `origin/collector-va-attribution`.

**File 1 — `internal/constants/constants.go`**

Add the constant alongside the existing `K8SEvent*` block:
```go
K8SEventUnattributedReadyPods = "UnattributedReadyPods"
```

**File 2 — `internal/collector/replica_metrics.go`**

In `CollectReplicaMetrics` (the public wrapper), insert the attribution check
**after** the metrics-unavailability event loop and **before** `if err != nil {
return nil, err }`. Add a `logger` var if not already present in scope:

```go
// Warn when a VA has Ready pods but none are attributed to it this cycle.
// Only runs when the model produced at least one attributed replica — model-wide
// emptiness is the availability path above; the scrape-lag gate keeps quiet there.
if err == nil && len(replicaMetrics) > 0 {
    attributed := make(map[string]int, len(variantAutoscalings))
    for i := range replicaMetrics {
        attributed[replicaMetrics[i].VariantName]++
    }
    for _, va := range variantAutoscalings {
        if attributed[va.Name] > 0 {
            continue
        }
        stKey := utils.GetNamespacedKey(va.Namespace, va.GetScaleTargetName())
        st, ok := scaleTargets[stKey]
        if !ok || st == nil {
            continue
        }
        if ready := st.GetStatusReadyReplicas(); ready > 0 {
            ctrl.LoggerFrom(ctx).V(logging.DEBUG).Info("VA has ready pods but none attributed",
                "va", va.Name, "namespace", va.Namespace, "readyReplicas", ready)
            c.recordUnattributedReadyPodsEvent(va, ready, vaEventTracker)
        }
    }
}
```

Add the helper method (anywhere in the file, near `recordMetricsUnavailableEvent`):

```go
func (c *ReplicaMetricsCollector) recordUnattributedReadyPodsEvent(
    va *llmdVariantAutoscalingV1alpha1.VariantAutoscaling,
    readyCount int32,
    vaEventTracker map[string]bool,
) {
    if c.recorder == nil {
        return
    }
    key := utils.GetNamespacedKey(va.Namespace, va.Name)
    if vaEventTracker != nil {
        if _, ok := vaEventTracker[key]; ok { // one event per VA per cycle
            return
        }
    }
    c.recorder.Event(va, corev1.EventTypeWarning, constants.K8SEventUnattributedReadyPods,
        fmt.Sprintf("%s has %d ready pod(s) but none attributed; "+
            "verify the llm-d.ai/variant pod label on the scale target equals %q",
            va.Name, readyCount, va.Name))
    if vaEventTracker != nil {
        vaEventTracker[key] = true
    }
}
```

**File 3 — `internal/collector/replica_metrics_test.go`**

Add a test `TestCollectReplicaMetrics_UnattributedReadyPodsEvent` that:
- Provides Prometheus results for one pod/instance but with a `vaName` that does NOT match any VA name in `variantAutoscalings`
- Provides a scale target with `GetStatusReadyReplicas() > 0`
- Confirms a `Warning/UnattributedReadyPods` event is emitted by the recorder
- Confirms a second call does NOT re-emit (deduped via `vaEventTracker`)

### Commit structure

**Commit 1** — `collector: fix throughput query labels and processing key`
*(already on branch — replay/keep during rebase)*
- `internal/collector/registration/throughput_analyzer.go` — Fix 1 above
- `internal/collector/replica_metrics.go` — Fix 2 above (Bug A) + Bug C fold-in

Note: during the rebase, squash Bug C into Commit 1 (same file, same layer).

**Commit 2** — `engines/analyzers/throughput: single-flight note; link #1261 for deferred gates`
*(already on branch — replay/keep during rebase)*
- `internal/engines/analyzers/throughput/analyzer.go` — Bug B items above

### Verification

After the fix, a unit or integration test should confirm that populating
both KV-cache and generation-token-rate results for the same pod produces
**one** `ReplicaMetrics` entry with both `KvUsageInstant` and
`GenerationTokenRate` non-zero (not two separate entries, one of which is
dropped). Existing `replica_metrics` tests in
`internal/collector/replica_metrics_test.go` and
`internal/collector/build_instance_key_test.go` cover the key-building
side; add or confirm a test that exercises the throughput merge path.

### Longer-term alignment

| Issue | Relation to this PR | Action |
|---|---|---|
| ~~#1260 — pod→VA derivation~~ | Merged as #1267 (`c55906a4`) | #1267 retained the label as fast path + added owner-walk; label stays in `by()` for now. |
| ~~#1263 — remove label from all groupbys~~ | **CLOSED** — superseded by #1267 | #1267 made label optional (fast path + shadow pods); forced removal would regress shadow-pod attribution. No follow-up needed. |
| [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264) — nil vs zero in `ReplicaMetrics` | #1250 is a prerequisite; #1264 builds on top | `*float64` interface change for the 3 fields + sanity-check update — separate PR after #1250 merges |

The `has*` flags added in Fix 2 are the internal half of #1264's minimum fix
and reduce the delta when #1264 work begins.

### Rebase + push (after commits above)

New base is `main@04f95779` (upstream/main, includes #1267/#1270/#1271).
Conflict resolution is specified in [`planning/PR1267-impact-and-decisions.md`](PR1267-impact-and-decisions.md) § "How TA3's A1 fix must be replayed."

1. `git branch --show-current` → must be `TA3`
2. `git status` → no uncommitted changes; `git fetch upstream`
3. `git rebase upstream/main`
4. **Three conflict files** — resolve as follows:
   - `internal/collector/replica_metrics.go`: change the 3 throughput loop call sites from `buildInstanceKey(value.Labels)` → `c.buildInstanceKey(ctx, namespace, value.Labels)` (the closure was removed by #1267; it is now a method). Keep `has*` flags. Add Bug C block in `CollectReplicaMetrics` wrapper + `recordUnattributedReadyPodsEvent` helper.
   - `internal/collector/replica_metrics_test.go`: add 4th `nil` arg to `NewReplicaMetricsCollector` in `TestCollectReplicaMetrics_ThroughputKeyMerge` (and add `TestCollectReplicaMetrics_UnattributedReadyPodsEvent`).
   - `cmd/main.go`: keep all upstream locator wiring + keep TA3's `registration` and `throughput` imports + `RegisterThroughputAnalyzerQueries` + `RegisterAnalyzer` calls.
5. Also add `K8SEventUnattributedReadyPods` constant to `internal/constants/constants.go` (new addition, no conflict).
6. `gofmt -l ./internal/... ./pkg/... ./cmd/...` → empty
7. `make test` → all pass
8. `make lint` → clean
9. `go build ./...` → clean
10. DCO: `git log upstream/main..HEAD --format="%b" | grep Signed-off-by` → one per commit (27 commits after rebase)
11. Push: present commit range + force-with-lease rationale to Dean, wait for approval
12. Update PR description with #1261 link + scale-down risk note: draft text for Dean, wait for approval before `gh pr edit`

---

---

## 0. Background

PR #1250 (branch `TA3`, assignee ev-shindin) carries 24 commits above
`main@badc48be`. The final coder session added the follow-up items from
the TA-PR5 review before the PR was opened:

| Item | Commit | Status |
|---|---|---|
| D1 — Rewrite `Analyze` doc-comment | `26394354` | **IN PR #1250** |
| D2 — Drop/rewrite stale comment on `computeLocalDemand` | `26394354` | **IN PR #1250** |
| T1 — Rename GPS-suppression test `Describe`/`It` blocks | `ea218f6d` | **IN PR #1250** |
| T2 — Add 5 aggregation-helper linearity specs | `ea218f6d` | **IN PR #1250** |
| ndots fix (e2e) | `3c838547` | **IN PR #1250** (should become own PR — see §4) |

Because these items are in-band with #1250, a separate PR-B is only needed
if (a) ev-shindin requests changes that cannot be squashed into #1250 during
review, or (b) additional items surface from ev-shindin's review that are
clearly out of scope for #1250.

Reference docs: [`TA-PR5-plan.md`](TA-PR5-plan.md) §6.1,
[`TA-PR5-review.md`](TA-PR5-review.md) §§ D1, D2, T1, T2.

---

## 1. What was done (verification record)

### D1 — Stale `Analyze` doc-comment (commit `26394354`)

**File:** `internal/engines/analyzers/throughput/analyzer.go`

**Old text (lines 180-188 in the reviewed version):**
```
// RequiredCapacity and SpareCapacity are computed from model-level totals, not
// per-variant deficits. This prevents conflicting signals when one variant is
// overloaded while another has spare capacity. PendingReplicas is included in
// anticipated supply to suppress scale-up thrashing while pods are starting.
// SpareCapacity is only emitted when EPP is deployed (ArrivalRate > 0).
//
// For P/D disaggregated models, RoleCapacities provides per-role breakdowns.
// No role is excluded from supply/demand computation. RequiredCapacity is
// suppressed for the prefill role: decode rate is never the prefill bottleneck.
```

**New text (as committed):**
```
// TA publishes TotalSupply, TotalAnticipatedSupply, and TotalDemand on the
// returned AnalyzerResult; RequiredCapacity and SpareCapacity are left zero.
// The engine's universal threshold post-step writes RC/SC after Analyze returns.
// PendingReplicas are included in TotalAnticipatedSupply to suppress redundant
// scale-up while pods are starting. Scheduler queue demand is split across
// non-prefill roles via distributeQueueDemandByRole.
//
// For P/D disaggregated models, RoleCapacities carries per-role Total* fields
// (TotalSupply, TotalAnticipatedSupply, TotalDemand); RC/SC per role are also
// left zero for the engine post-step. Prefill TotalDemand is negligible after
// the OL guard in computeLocalDemand.
```

The new text accurately describes the post-PR-5 contract: TA publishes raw
`Total*`; RC/SC are the engine post-step's responsibility.

### D2 — Stale comment on `computeLocalDemand` (commit `26394354`)

**File:** `internal/engines/analyzers/throughput/analyzer.go` (around
the `computeLocalDemand` function, previously described as line 527 in
the reviewed version).

**Old text:**
```
// This estimate is used for scale-up only; SpareCapacity still requires EPP.
```

**New text (as committed):**
```
// This path is scale-up only: k*-based demand may undercount arriving load
// without EPP. The engine post-step determines SC from the published totals.
```

The "SpareCapacity still requires EPP" claim was stale after the EPP/GPS
SC gate was dropped in PR-5. The replacement accurately describes the
current behavior: SC is determined by the engine post-step from the
published totals.

### T1 — GPS-suppression test block rename (commit `ea218f6d`)

**File:** `internal/engines/analyzers/throughput/analyzer_test.go`

The `Describe` and all five `It` strings were renamed from the pre-PR-5
framing ("GPS verification suppresses SpareCapacity") to reflect the
current state (preserved fixtures for a future SC-gate PR). A block
comment was added at the top of the `Describe` explaining the deferral.

Renamed strings (current, as of commit `ea218f6d` + `24917288`):

| Location | New string |
|---|---|
| `Describe` | `"Analyze — GPS-mismatch scenarios (preserved fixtures for future SC gate)"` |
| L1361 `It` | `"GPS within 15% of model prediction — fixture for future SC pass-through"` |
| L1377 `It` | `"GPS deviates > 15% at k* ≥ DefaultGPSMinKForVerification — fixture for future SC suppression"` |
| L1390 `It` | `"GPS deviates but k* < DefaultGPSMinKForVerification — fixture for future SC pass-through"` |
| L1406 `It` | `"GenerationTokenRate is zero (metric absent) — fixture for future SC pass-through"` |
| L1421 `It` | `"RC remains nonzero under GPS mismatch — fixture for future SC suppression"` |

All scenario data, input coefficients, and `SpareCapacity == 0` assertions
were preserved verbatim. The block comment does not reference plans-branch
identifiers per CODER-CONVENTIONS §4a.

Follow-up commit `24917288` stripped a plans-branch reference (`F3`) from
the block comment that slipped through in the initial rename commit.

### T2 — Aggregation-helper linearity specs (commit `ea218f6d`)

**File:** `internal/engines/analyzers/throughput/analyzer_test.go`

Five specs were added under the existing `Describe("Analyze — aggregation
helper consistency", …)` block (lines 960-1106 in the current file):

1. `TotalSupply == aggregation.SumTotalSupply(VariantCapacities)` — two
   variants with OLS-ready windows; verifies model-level sum is exactly
   the variant-slice sum.
2. `TotalAnticipatedSupply == aggregation.SumTotalAnticipatedSupply(VariantCapacities)`
   — one variant with one pending replica; verifies pending-replica
   anticipation carries through the sum.
3. `TotalDemand == aggregation.SumTotalDemand(VariantCapacities) + queue demand`
   — one variant with non-empty scheduler queue; verifies queue demand
   was added on top of the variant-slice sum.
4. `RoleCapacities[role].TotalAnticipatedSupply` matches per-role aggregation
   via `aggregation.AggregateByRole(result.VariantCapacities)` — P/D
   disaggregated fixture.
5. `RoleCapacities[decode].TotalDemand` includes the queue-demand share;
   `RoleCapacities[prefill].TotalDemand` is unchanged (queue skips prefill).

These lock the linearity invariant the engine post-step depends on. Before
these specs, a future refactor that double-counted a variant or skipped a
role would only surface downstream (wrong RC/SC from the engine), not in
TA's own test suite.

---

## 2. Nothing remaining for D1, D2, T1, T2

All four items are in PR #1250. When #1250 merges, these items land on
`main` as part of the TA3 commit set. No separate PR-B action is needed
for them.

---

## 3. Decision tree: when is PR-B needed?

### 3.1 ev-shindin requests changes to existing D1/D2/T1/T2 commits

If the review requests minor rewording or corrections to the doc-comment
or test renames, those can be addressed as fixup commits on TA3 before
merge — no separate PR-B.

If the review requests substantive behavioral changes to the GPS test
block or the aggregation specs, those are in scope for a targeted commit
on TA3.

A separate PR-B is only needed if #1250 merges before all review items are
addressed (e.g., if the review finds a new correctness bug requiring a
companion fix after merge).

### 3.2 New items from ev-shindin's review

Items that are doc-only, test-only, or doc+test with no behavior change
are candidates for PR-B. Behavioral fixes to `analyzer.go` should be
evaluated against scope: small isolated fixes can go in PR-B; larger
changes warranting their own commit history should become their own
named PR.

### 3.3 ndots standalone PR (see §4)

The ndots fix (`3c838547`) is in PR #1250 but was noted in CURRENT.md as
needing its own standalone PR. This is resolved by the fact that the fix
is already in #1250 — it either merges with #1250 or is extracted before
merge. See §4.

### 3.4 PR-1052 deferred fixes (separate scope)

The 10 items in [`PR1052-deferred-fixes.md`](PR1052-deferred-fixes.md) are
from the TA2 review (PR #1052, merged 2026-05-19). They are independent of
TA3 and do not belong in PR-B unless Dean decides to group them for
convenience. They have their own plan doc and should be tracked separately.

---

## 4. ndots fix: resolution

`test/e2e/fixtures/workload_builder.go` commit `3c838547` sets `ndots:2`
on load-generator pods to fix musl DNS on corporate networks. This fix is
a standalone e2e infrastructure fix, not part of the TA3 contract changes.
CURRENT.md notes it "needs its own PR before/with TA3 merge."

**Options:**

A. **Leave in #1250.** The fix is small, e2e-scoped, and unrelated to
   analyzer logic. ev-shindin can review it as part of #1250. This is the
   path of least friction.

B. **Extract as a standalone PR.** If ev-shindin objects to the scope
   conflation, or if there are CI concerns, extract `3c838547` as a
   separate PR with base `main`, get it merged first, then rebase #1250
   onto the updated `main`.

**Decision:** defer to Dean. If no objection, leave in #1250 (option A).
If asked to extract, the coder should:

1. Identify the diff: `git show 3c838547 -- test/e2e/fixtures/workload_builder.go`
2. Create a new branch from `main`
3. Cherry-pick `3c838547` onto the new branch
4. Open a standalone PR (base `main`, one commit, no other changes)
5. Once merged, rebase TA3 onto the updated `main` (single-commit rebase,
   expect no conflicts since only e2e/fixtures/ was touched)

---

## 5. If PR-B is needed: commit structure

If a separate PR-B is needed (see §3), the intended commit structure is:

**Commit 1 (doc+rename only, no behavior change):**
```
engines/analyzers/throughput: fix stale doc-comments and rename GPS-suppression test blocks
```
- `internal/engines/analyzers/throughput/analyzer.go`: D1 + D2 fixes
- `internal/engines/analyzers/throughput/analyzer_test.go`: T1 renames

This commit is a clean separation: all naming/prose changes, zero logic
changes, reviewers can confirm by inspection that nothing behavioral
changed.

**Commit 2 (test coverage only, no behavior change):**
```
engines/analyzers/throughput: add aggregation-helper linearity specs
```
- `internal/engines/analyzers/throughput/analyzer_test.go`: T2 specs

Separate commit so the diff is a clean additive set of test specs with
no interleaving with rename changes.

In practice these two commits are already on the TA3 branch; PR-B would
cherry-pick them (or equivalent patches) onto a branch off of the
post-#1250-merge `main`.

---

## 6. Pre-push checklist (if PR-B is opened)

Per CONVENTIONS.md pre-push checklist, in order:

1. `git branch --show-current` — confirm branch is the PR-B branch (not `TA3`, not `main`).
2. `gofmt -l ./internal/... ./pkg/... ./cmd/...` — must produce no output.
3. `make test` — all tests pass.
4. `make lint` — clean. This runs golangci-lint with the repo's `.golangci.yml`; it is a required gate and catches findings that `gofmt`/`go build`/`make test` do not.
5. DCO sign-off — every commit must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Verify with `git log upstream/main..HEAD --format="%b" | grep Signed-off-by`.
6. `go build ./...` — clean.

---

## 7. Key file paths

All paths are relative to the TA3 worktree
(`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/TA3/`):

| Path | Role |
|---|---|
| `internal/engines/analyzers/throughput/analyzer.go` | D1, D2 — doc-comments |
| `internal/engines/analyzers/throughput/analyzer_test.go` | T1, T2 — test renames and new specs |
| `internal/engines/aggregation/aggregation.go` | Aggregation helpers T2 specs call (`SumTotalSupply`, `SumTotalAnticipatedSupply`, `SumTotalDemand`, `AggregateByRole`) |
| `test/e2e/fixtures/workload_builder.go` | ndots fix — see §4 |

---

## 8. Out of scope

- **ndots standalone PR** (see §4 — decision pending, currently in #1250).
- **PR-1052 deferred fixes** — independent scope, own plan doc at [`PR1052-deferred-fixes.md`](PR1052-deferred-fixes.md).
- **`anyEPP` / `anyGPSMismatch` computed-and-discarded placeholders** (`_ = anyEPP; _ = anyGPSMismatch` in `analyzer.go`) — deliberate placeholders for the future per-analyzer status-return PR. Leave as-is; do not remove.
- **SC gate restoration** — deferred to a broader future PR that adds per-analyzer status-return state. Tracked in the multi-analyzer design doc under "Future direction." The GPS test fixtures in the renamed block are preserved precisely for this future PR.
- **`RegisterAnalyzer` error-return wiring** (H1 from the TA-PR5 review) — already landed in commit `a1343d6a` on TA3. In PR #1250.
