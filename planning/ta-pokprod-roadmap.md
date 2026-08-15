# TA on pokprod — Roadmap (Type 2)

**Status:** LIVE, created 2026-08-15 — a real structural gap, not filled until now. The mission has
run since 2026-07-30 with one Type 1 (architecture) and several Type 3s (execution history, live
scenarios, tool docs, results) but no mission-level roadmap tracking alternatives considered,
decisions made, and what's active/next at a glance. This doc is that missing layer — it doesn't
restate Type-3 detail or the ledger's 55 decisions, it points into them.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md)
(Type 1, durable contracts) · [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md)
(Type 3, settled phased history) · [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md)
(Type 3, live checklist) · [`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger,
`grep -n '^## D-nn'`).

---

## Mission phases, at a glance

| Phase | What | Status |
|---|---|---|
| 0 | Preserve legacy TA3 harness work, archive, fresh `benchmark` branch | ✅ DONE (2026-07-29) |
| 1 | Methodology pivot to controlled shared-cluster setup | ✅ DONE (2026-07-30) |
| 2 | Harness build, fork-patch presence-gates | ✅ DONE |
| 3 | Namespace standup (`dhl-wva-209`) | ✅ DONE |
| 4 | Live cluster runs — 2026-08-10 7-cell campaign | ✅ DONE |
| 4b | Rerun/gap-fill campaign (calibration-probe, prefill-knee, dwell reruns) | ✅ DONE — coverage matrix closed 2026-08-14 |
| 5 | Results tooling — extractor/render toolchain, results-tree, campaign report | ✅ DONE — report relocated to `benchmark/docs/benchmark-reports/` 2026-08-15 |
| 6 | Deep-dive investigations (dwell limit cycle, OOM root cause, controller-restart policy) | 🔵 ACTIVE — mechanisms found, several open design questions deliberately deferred |
| 7 | Doc-coverage cleanup (undocumented scratch tools) | 🔵 ACTIVE — draft plan written, Dean's classification call pending |
| 8 | Per-request data recovery for viz (panels 1a/1b) | 🆕 NEW 2026-08-15 — this roadmap entry, see below |

Full execution detail for phases 0-5: [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md).

## Active threads

**Dwell limit cycle.** Mechanism found (D-21): `P1-obs` anomalous sample + created→ready replica
lag, not a control-loop defect. Real gap identified: no forecast that already-ordered/created
replicas will relieve the queue (D-45 §2) — shared between saturation and TA. **Deliberately
deferred by Dean** — needs a proper Type 1 (or Type-1 family) for TA covering theory/goals/
algorithms first, then a Type 2 breaking it into scoped tasks, before this specific mechanism gets
its own Type 1 slice. Not started.

**Doc-coverage cleanup.** D-51 found the gap is 7 tools wide, not 2 — `envoy_per_request.py` and
`serving_replicas.py` got a retroactive Type 3
([`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md)); the other
5 got a draft classification recommendation
([`pokprod-scratch-tools-doc-coverage-cleanup-plan.md`](pokprod-scratch-tools-doc-coverage-cleanup-plan.md)).
Dean's classification call not yet made on either.

**Per-request data recovery for viz (new, 2026-08-15).** viz-panels-planner handed over a full raw-
data inventory for panels 1a/1b's empty-on-most-runs gap (per-request collection disabled by
design, D-12). Confirmed independently this session: neither `metrics/processed/*.json`
(aggregate/cumulative only) nor EPP's `"EPP received request"`/`"Request handled"` lines (routing
latency only, same TTFT/output-size gap as `igw_pods.log`) closes the gap alone. **This is this
scope's to design and build** (viz consumes, doesn't build) — continues in
[`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md), which already
carries the two existing tools and the open generalization-ownership question this ask answers.
**Not yet designed** — next actual step, this session.

**Controller-restart hold-at-current-replicas policy (D-46).** Mechanism found (deliberate
by-design hold, not a bug) — read-only source trace. Open question is a policy call ("is 'hold'
right for a *sustained* window"), Dean's, not urgent.

## Alternatives considered and rejected (worth keeping visible)

- **Direct load generation instead of inference-perf** (D-41) — rejected, explicitly: broader
  scope than the OOM fix needed, and a credibility/trust issue (using our own tool to showcase our
  own work is suspect), not just technical.
- **The p4/parallelism variant as the default OOM workaround** (D-42, reaffirmed twice at D-50) —
  rejected as a silent default; an unmodified retry is tried first every time an OOM recurs, only
  escalating to p4 if that fails, so the two aren't interchangeable defaults.
- **Gitignore-pattern widening vs. pull-up-and-commit** for the viz-output-nesting gap (D-52) —
  pull-up chosen, matching existing precedent, to keep one canonical tracked location rather than
  two.

## What's next (this session)

Design the per-request extraction mechanism for panels 1a/1b, scoped to one worked example run
(`dean-20260813-005321-943`) first, per viz-panels-planner's ask. Lands in
[`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md) as its next
section, not a new file — see that doc's own "Open question, not resolved by this doc" section,
which this work now resolves.
