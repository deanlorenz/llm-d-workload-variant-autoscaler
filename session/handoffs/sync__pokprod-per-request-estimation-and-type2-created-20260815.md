from: plan (pokprod/benchmark-execution scope)
to: sync
session: pokprod-benchmark-execution

## Ref

[`ta-pokprod-roadmap.md`](../../planning/ta-pokprod-roadmap.md) (new Type 2, Dean-approved
2026-08-15) is now the mission-level entry point — start there, it points into everything else.
[`envoy-per-request-recovery-tool-plan.md`](../../planning/envoy-per-request-recovery-tool-plan.md)
carries the live per-request design. [`ta-pokprod-history.md`](../../planning/ta-pokprod-history.md)
D-55 through D-57.

## Resume prose

**Two structural gaps closed today, both real, both found via Dean's own review rather than
self-initiated:** (1) the mission had run since 2026-07-30 with a Type 1 and several Type 3s but
no Type 2 roadmap — created and approved. (2) D-51's doc-coverage-gap tool count was wrong (said
5, actual is 17) — a full directory listing caught 12 tools D-51's own source list missed;
cleanup plan rewritten with the correct, complete inventory (10 recommended DEFERRED, 7
promote-as-is). Also retroactively ledgered a 2026-08-11 discovery pass (per-request
field-availability across EPP/Envoy/vLLM-histogram sources) that ran, produced real findings, and
was never captured in the ledger — direct cause of viz-panels-planner independently re-discovering
the same territory days later.

**New active thread, in flight:** per-request TTFT/output-size data for viz panels 1a/1b. No
source gives true per-request values under the standing per-request-collection-disable policy
(OOM risk, unchanged) — only per-stage histogram distributions. Design: anchor real per-request
arrival/duration/routing from the Envoy access log to a distribution-conditional estimate,
consolidating (not preserving wholesale) technique from `envoy_per_request.py`. Build handed to
the benchmark coder, scoped to one example run (`dean-20260813-005321-943`) first, per
viz-panels-planner's own request — **in progress, coder has it `.WIP`**.

**Real finding mid-design, changes the picture, not yet acted on:** background research found
vLLM's shipped `--enable-per-request-metrics` flag returns genuine per-request TTFT and
output-token-count in the response body, with retention entirely the caller's choice — a
structurally different risk profile from the harness's own OOM mechanism. This could replace
estimation with real measurement if it verifies cleanly. **Needs Dean's prioritization call**
(verify the flag now vs. let the in-flight estimation build finish first) — not decided, not
started.

**No armed footguns.** GPUs freed (per the benchmark coder's own last status), no cluster action
pending on this scope's side. Working tree clean for everything this scope owns (verified via
`git status` before writing this handoff).
