# Handoff → planner: setup check for "does TA accelerate scale-up?" (TA+SAT combined)

## TL;DR
Dean's next experiment: run the analyzers in **combined TA+SAT mode** and test whether
the **ThroughputAnalyzer (TA) triggers scale-up *faster*** than saturation alone — i.e.
whether TA's proactive/model-driven signal leads saturation's reactive KV-threshold signal.
Dean flagged this **"may need to change the workload."**

Dean asked the **setup check** to go to the planner. The coder (benchmark session) is
**holding** — it will run TA+SAT only after the planner returns (a) a workload design that
lets TA both *calibrate* and *demonstrate a lead*, and (b) a methodology for measuring
"faster." The cluster is at a clean baseline; no run is in flight.

## What's already validated (evidence from this session, dhl-wva-209, guidellm harness)
- **SAT-only (V2 saturation), short profile → clean 1→2→1.** guidellm native profile
  `wva_sat2_short` (`rate: [12,24]` × 180s, 4096/1024 tokens, `text_completions`).
  Scale-up fired ~1.9 min after load start; cooldown to 1 ~4 min after load end.
  Ran end-to-end with **zero code change** (native guidellm profile sidesteps the
  Makefile local-`.in` filename bug — see prior handoff
  `plan__benchmark-harness-guidellm-vs-inferenceperf.md`).
- **"TA-in-isolation" is NOT achievable via config.** Patching the saturation-scaling CM to
  `saturation: {enabled: false}` + `throughput: {score: 1.0}` and restarting the controller
  registered TA (`cmd/main.go:509 ThroughputAnalyzer registered`) — but saturation still
  drove the scale-up. Root cause in code:
  - `internal/engines/saturation/engine_v2.go:126-134` — the **saturation result is
    unconditionally prepended** as the base analyzer every cycle.
  - `effectiveEnabled` (`engine_v2.go:198`) is only consulted for *non-saturation* analyzers;
    the loop `continue`s past saturation (L136). Comment L196-197: **"Saturation is exempt."**
  - So `saturation: enabled:false` is a **no-op** — there is no config/flag/env to disable
    saturation or select a "throughput-only" engine (checked `variantautoscaling-config` CM
    and the controller args/env: only `--config-file`, `SATURATION_CONFIG_MAP_NAME`,
    `WVA_LIMITED_MODE=false`). TA-only requires the **deferred analyzer-enablement code fix**,
    not a live config change.
- **TA did not calibrate in the 6-min run.** At the scale-up reconcile:
  `throughput: util=0.589, rc=0, reason=T2-default` (tier-2 baseline ITL — OLS window never
  reached `MinSamples=10` / `MinKSpread≥0.30`) vs `saturation: util=3.24, rc=923851,
  reason=P1-obs`. TA's own signal was rc=0 (util 0.589 < scaleUp 0.85), so even setting the
  no-op aside, TA would not have scaled here.

## Hypothesis / theory of change to validate (this is the crux of the setup check)
TA models decode ITL as `ITL(k) = A·k + B` and compares projected supply μ_dec against
demand λ_dec; saturation reacts when KV util crosses `k_sat = 0.85`. **If TA is calibrated
(Ready), it can raise RequiredCapacity while k\* is still < 0.85 — before saturation trips —
producing an earlier scale-up under any-up combine.**

**Open question the planner must resolve before we run:** does the TA `Analyze()` path
(`internal/engines/analyzers/throughput/analyzer.go`) actually raise RC ahead of the KV
threshold, or does it also key off `k\* ≥ k_sat = 0.85` (constants.go `DefaultKSat = 0.85`,
which "mirrors" saturation)? If TA's scale-up condition collapses onto the same k_sat,
"faster" may be impossible by construction and the experiment needs reframing (e.g. measure
TA's contribution to scale-*down* damping / proactive smoothing instead). Please confirm the
lead is mechanically possible before the coder burns a cluster run.

## Setup-check deliverables requested from the planner
1. **Config (clean TA+SAT):** `analyzers: [{name: saturation, score: 1.0}, {name: throughput,
   score: 1.0}]`; any-up / all-down. Controller restart required (startup gate). NB current CM
   is still the no-op isolation shape — coder will replace it with this on your go.
2. **Workload design (the "may need to change the workload" part):** a **two-phase** guidellm
   profile —
   - *Phase A (calibration):* sustained but **sub-scale** load that sweeps KV util across
     `[0.15, 0.85]` so TA collects ≥10 valid samples with `KSpread ≥ 0.30` and its reason
     flips `T2-default → OLS-Ready`. Must **not** itself trigger scale-up (else the A/B is
     moot). Observations above 0.85 are rejected, so the sweep must stay under it.
   - *Phase B (trigger):* a step-up that should induce scale, positioned so a *calibrated* TA
     can lead saturation.
   - Note timing: `GLOBAL_OPT_INTERVAL = 60s` and `MinSamples = 10` ⇒ Phase A needs ≥~10 min
     of varied load; `ObservationMaxAge = 30min` bounds the window. Current `wva_sat2_short`
     (jumps straight to saturating rates) is unsuitable for calibration.
3. **Methodology:** define "faster" precisely — Δt from a fixed reference (load-start, or λ
   crossing per-replica capacity) to HPA `desiredReplicas: 2`. **A/B on the identical
   workload:** SAT-only baseline vs TA+SAT, everything else held constant. Specify how many
   repeats and what counts as a real difference vs noise (single-run Δt is noisy).
4. **Verification signals:** per-analyzer `analyzer-result` log lines (rc, sc, util, reason —
   watch TA `reason` flip off `T2-default`) and HPA/deploy scale timestamps. The coder's
   replica monitor + a controller-log tail on `analyzer=throughput` cover this.

## Current cluster state (coder is holding here)
- NS `dhl-wva-209`: decode `unsloth--608e585a-instruct-decode` **1/1** (baseline);
  SO `...-decode-scaler` Ready/Active; KEDA HPA min1/max2 at **1**; gpu-reservation **0**
  (1 H100 free for a scale to 2); controller pod healthy, **TA registered**.
- Optimizer CM `workload-variant-autoscaler-wva-saturation-scaling-config` `data.default` =
  `analyzers:[saturation{enabled:false}, throughput{score:1.0}], enableLimiter:false`
  (the no-op isolation shape). Original SAT-only shape to restore if needed:
  `analyzers:[- name: saturation]` + `kvCacheThreshold:0.80, queueLengthThreshold:5,
  kvSpareTrigger:0.1, queueSpareTrigger:3, enableLimiter:false`.

## Uncommitted artifacts in the benchmark worktree (not pushed)
- `llm-d-benchmark/workload/profiles/guidellm/wva_sat2_short.yaml.in` — new native profile
  (in the vendored clone; gitignored).
- `hack/benchmark/scenarios/guides/wva-sat2-tp1.yaml` — `experimentProfile` + usage-comment
  edits (Tier-2, overridden by `-w`; harmless).
