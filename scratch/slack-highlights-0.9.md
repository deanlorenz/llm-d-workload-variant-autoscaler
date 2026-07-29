# Slack note — 0.9 Highlights (DRAFT, send at/after code freeze)

*Slack mrkdwn. Some PRs below are still open — numbers/lines to be confirmed against the final
`v0.8.0..v0.9.0` tag range before the release goes out.*

---

*WVA 0.9 — Highlights (draft)*

0.9 is about making autoscaling decisions *correct, safe, and observable* for disaggregated (prefill/decode) serving. The multi-analyzer engine and Throughput Analyzer from the 0.8 line are hardened for production, the P/D-aware optimizer gets several correctness fixes, the default saturation analyzer moves to the token/capacity V2 model, and a broad set of new metrics, logs, and alerts make scaling behavior visible.

*Key Features*
• *Multi-analyzer pipeline, matured* — pluggable analyzers behind one optimizer: scale up if any analyzer needs capacity, down only when all agree there's spare. 0.9 hardens the lifecycle: participation is now *opt-in* (an absent config entry no longer silently enables an analyzer), and scale-down is *liveness-gated* so a stalled/errored/never-reporting analyzer can't veto it. _(#1479, #1481)_
• *Throughput Analyzer, production-hardened* — proactive scaling from a fitted per-token-latency model + KV capacity. Now derives decode demand from the *model-level* arrival rate rather than per-instance summation (fixing cases where it ran but never triggered scale-up), and its dev guide is synced to the code. _(#1480, #1478)_
• *P/D role-aware optimizer* — aggregates capacity per role and allocates prefill/decode jointly (min-over-role utilization) instead of treating a model as one pool. 0.9 correctness fixes: waiting local-queue requests charged by role; instances counted by DP-rank, not raw pods. _(#1470, #1469, #1392)_
• *V2 saturation analyzer is now the default* — token/capacity-based, replacing percentage-based V1. See Upgrade Steps. _(#1442)_
• *Priority-weighted GPU rescale under contention* (Alpha, opt-in, off by default) — redistributes GPU budget across a competition group by priority + demand, within physical/quota limits. _(#1452)_
• *Observability across the scaling loop* — structured per-cycle `analyzer-result` / `scaling-decision` logs with a per-decision reason; new metrics for available GPUs, config-info, per-model freshness, and V2 saturation decisions; shipped PrometheusRule alerting. _(#1318, #1328, #1190, and related metrics fixes)_

*Notable Bug Fixes*
• TA never triggered scale-up when per-pod arrival rate didn't attribute to the model — now model-level demand. _(#1480)_
• A stalled/errored/stale analyzer could silently veto scale-down — now liveness-gated, with a no-live-analyzer safety floor. _(#1481)_
• Saturation V2 under-counted demand for long-generation workloads (waiting-request output tokens by P/D role). _(#1470)_
• Saturation V2 mis-scaled data-parallel models by counting pods instead of DP-rank instances. _(#1469)_
• Saturation V1 utilization metric computed incorrectly. _(#1392)_
• Metrics fixes: pods-with-metrics gauge, available-GPUs metric, V2 decision metrics, analyzer-mode logging.

*:warning: Upgrade Steps & Deprecations*
• *Action required — default saturation analyzer is now V2 (#1442).* May produce different decisions than V1 for the same workload — review dashboards/alert thresholds. To stay on V1, remove the `analyzers:` section (and V2-only `scaleUpThreshold`/`scaleDownBoundary`) from the `default` entry of the saturation ConfigMap.
• *Behavioral default — analyzer participation is opt-in (#1479).* An absent config entry no longer enables an analyzer; confirm your `analyzers:` config explicitly lists everything you expect to run.
• *Saturation V2 demand accounting changed (#1470)* — saturation-utilization values (and alerts baselined on them) may shift for long-generation workloads; re-baseline if needed.

*Known Issues*
• Enabling an analyzer by editing the saturation ConfigMap at runtime needs a controller restart to take effect; today it's silent. A warning (log + K8s Event) is planned (#1497) but may not land in 0.9.
• Analyzers can't yet return a per-analyzer status to suppress only spare- or only required-capacity decisions. Tracked in #1261.

---
*Note: a few of these are still open (#1480, #1481) and may shift before release — I'll update this once they merge and the tag range is final.*
