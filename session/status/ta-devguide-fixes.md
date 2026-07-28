last_update: 2026-07-26T20:45:00Z
state: in-progress
current_step: NTH-1 review finding applied (f931a4e9); all 4 commits landed, gates green; review FINAL/APPROVE. Awaiting Dean's push confirmation.

## Branch
ta-devguide-fixes at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/ta-devguide-fixes ; tip f931a4e9 (base main@f5b7577c)

## Recent commits
- f931a4e9 — docs(throughput-analyzer): add missing port label to ArrivalRate groupby  [NTH-1, folded in per review]
- 444cd4a3 — docs(throughput-analyzer): clarify ReplicaCount is the KV-derived ready count  [I-23]
- 570bd528 — docs(throughput-analyzer): drop removed itl_knowledge_store references  [I-22]
- d2d86c0f — docs(throughput-analyzer): fix stale PromQL groupby labels  [I-21]

## Tests added / moved
(none — doc-only PR; no test changes required)

## Verified
- go build ./... — clean (last full run; f931a4e9 is doc-only, cannot regress)
- gofmt -l ./internal ./pkg ./cmd — clean
- make lint — 0 issues (doc-only final commit cannot regress lint)
- DCO sign-off present on all 4 commits (verified via git log; f931a4e9 confirmed)
- NTH-1 grep: only one `by (pod_name` line in the doc, now `sum by (pod_name, port, namespace)`;
  matches source template queueing_model.go:43. Table row renders (6-pipe columns).

## Developer guide
- docs/developer-guide/throughput-analyzer.md:
  - I-21/I-22/I-23 as previously recorded.
  - NTH-1 (commit f931a4e9): ArrivalRate row L214 `sum by (pod_name, namespace)` →
    `sum by (pod_name, port, namespace)`, matching QuerySchedulerDispatchRate template at
    internal/collector/registration/queueing_model.go:43. Pre-existing/out-of-original-scope
    finding surfaced by internal review; Dean elected to fold into this PR (accepts near-term
    double-touch with PR C ta-model-level-demand, which will likely rewrite this row again).
- internal/collector/registration/throughput_analyzer.go (commit d2d86c0f, optional companion):
  updated stale "max by (pod)" comment to match the actual template groupby.

## Open questions for Dean
(none)

## Not done / known limitations
(none — all planned commits + the folded-in NTH-1 review finding landed)

## Notes
Internal review FINAL, verdict APPROVE (planning/ta-devguide-fixes-review.md). NTH-1 was the
only finding and is non-blocking; applied per Dean's fold-in decision. review-findings trigger
processed and marked .DONE. Push-ready handoff to planner written. NOT pushed — awaiting Dean's
explicit push confirmation and origin-branch creation (git push -u origin ta-devguide-fixes).
