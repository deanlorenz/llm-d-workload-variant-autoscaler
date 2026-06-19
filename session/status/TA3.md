last_update: 2026-06-16T08:00:00Z
state: in-progress
current_step: Round-3 fixes complete (F1–F5 + nits); awaiting Dean's push selection

## Branch
TA3 at /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/TA3 ; tip 8fcaaaed
39 commits above upstream/main@04f95779 (NO PUSH since f11f5120)

## Round-3 commits (above f11f5120, each independently droppable)
- 8bf3d44f — F1 EPP warm-up fix (KEEPER — standalone)
- d187b670 — F2 TotalCapacity doc-accuracy
- 5b4bfa58 — F3 skip orphan instances in throughput loops
- 8754af50 — F4 ctx threading + Add returns bool
- 0a6c93eb — nits: defensive B guard, nDec>0 comment
- 8fcaaaed — F5 e2e controller restart + skip-guard (companion to gate)

## Verified
- make test — PASS
- make lint — 0 issues
- go build ./... — clean
- gofmt — clean
- DCO: 39/39 signed

## Not done (awaiting Dean)
- Push: Dean selects which commits to include + confirms force-with-lease
- F1 is the standalone keeper; F2–F5 each droppable by truncation
- F5 not droppable if full-E2E green matters (companion to the gate)
