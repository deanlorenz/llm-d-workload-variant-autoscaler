# Metric-Based Analyzer Interface — internal working notes (plans-branch)

> **Canonical doc:** the proposal now lives on the code branch as
> `docs/proposals/analyzer-metric-interface.md` (branch `analyzer-metric-proposal`,
> **PR [#1444](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1444)**, tip
> `ff3e168b`, Status: Draft). That house-template version is authoritative and
> standalone-readable — do **not** maintain a second full copy here. This plans-branch file keeps
> only the internal record: how the doc evolved after promotion, plus open questions and
> cross-references deliberately kept out of the external proposal. (The full pre-promotion body is
> recoverable from git — see commit `2bf66605` on the plans branch.)

## Evolution since promotion

- **`39a83d0b`** — initial promotion to the code branch (Dean): house-template form of the design
  worked out on the plans branch.
- **`607699f5`** — Evgeny Shindin (maintainer / PR approver) correctness pass:
  - `last()` is not a PromQL aggregator → demand `sum(max_over_time(Q[w]))` (one series per
    model[, role]); target `avg by(pod)(avg_over_time(Q[w]))`, reduced pod→$S$ by average.
  - external `Q` must be a **bare selector**; an arbitrary expression (a converted KEDA query, or
    WVA's own analyzer queries) needs a `{{scope}}` placeholder / translation step.
  - configurable `modelLabel`/`namespaceLabel` (real metrics use `model_name` /
    `target_model_name`, or none) + `EscapePromQLValue` escaping of free-form modelIDs.
  - guards: target `P ≤ 0` is **missing** (divide-by-zero in `⌈D/P⌉`); demand `orZero` opt-in for
    signals that vanish (no series) at zero load.
  - provenance/description moved **off** the value series onto separate series (avoid churn);
    coordination *math* (sum/min) vs *logic* precision; duplicate label `L` rejected; `modelID:"*"`.
- **`ff3e168b`** — Dean follow-up (this session), on top of Evgeny's pass:
  - `perRole` → a **`match:`** ScaledObject selector, applied uniformly to `demand` and `target`.
  - `role` grounded in the `llm-d.ai/role` pod-template label (via `getRoleFromScaleTarget`,
    `internal/engines/saturation/engine.go`) — **not** a metric label, which is why per-role queries
    are needed.
  - provenance `E` defined as a **free-form producer token** (internal = existing reason code;
    external = the winning fallback's `e:`), emitted on the separate provenance series.
  - per-role demand reconciled as **utilization-space** coordination (min over roles); no cross-role
    demand normalization needed.
  - `orZero` promoted from a buried comment to an explained option.

Reply to Evgeny summarizing the follow-up: PR #1444 comment `issuecomment-5047415526`.

## Open questions (kept out of the external proposal)

1. **`description` label.** Whether to expose the optional free-form `description` (role / GPU count /
   inference-pool name) — per Evgeny, on a separate `wva_analyzer_info` series rather than a
   value-series label — or keep the label set minimal.
2. **Staleness (implementation detail).** The definition does **not** let a user set a staleness
   limit; each query implies its own period and the analyze-loop period is fixed here. Behavior when a
   query returns stale data is a wrapper implementation detail, TBD — noted, not specified.
3. **Reduction grammar.** Confirm the pod→$S$ reduction set: `avg` (default), plus
   `median`/`min`/`max`. No weighted reduction is planned.

## Internal cross-references

- `planning/optimizer-coordination-design.md` — the coordination model (analyzers as metric
  providers; optimizer AND/OR over utilizations; supply taxonomy). This proposal is the *interface*
  counterpart to that *coordination* design; the per-role-demand / utilization-space reconciliation is
  mirrored there.
- `planning/multi-analyzer-design.md` — current analyzer/engine/optimizer architecture. Future
  directions there on analyzer-published demand and per-analyzer observability metrics are unified by
  this proposal. Two things noted for future, deliberately out of scope: (a) relocating cross-target
  aggregation from analyzers into the engine (shared helpers already make this a call-site move);
  (b) the analyzer status-return / reliability mechanism, the internal-code form of the discrete
  scale-down suppression.
- `planning/error-paths-design.md` — internal error-path handling for degraded/missing signals;
  detail deliberately kept out of the external proposal.
