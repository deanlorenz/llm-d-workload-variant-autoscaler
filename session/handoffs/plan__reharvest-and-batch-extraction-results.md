from: benchmark
to: plan (viz-panels scope)
session: benchmark

## Task 1 (reharvest-one-run): done, exact match

dean-20260813-005321-943 re-harvested from the follower's PVC file, replacing the truncated
harvested copy. Re-ran estimate_per_request.py: 21,120/21,120, delta +0 (was 19,388/21,120).
Stage 0 now has 550 requests (5.10 req/s observed vs 5.0 configured) -- the gap you flagged is
closed. Confirmed the stage-4 rate anomaly (my earlier Finding 2) is unchanged after the fix --
2,430 requests, same 3.16 vs 2.0 observed/configured -- so that's confirmed to be a separate,
still-open question, not caused by the truncation.

## Task 2 (extract-remaining-runs): 9 of the 13 (or 14, see count note) leaves done exact, 2
run-shapes flagged as genuinely unprocessable, not silently forced through

Full per-run table and the count discrepancy note in session/status/benchmark.md §20.45. Summary:
7 leaves went from no-data to an exact-match per-request estimate (21,120/21,120 or 7,110/7,110);
1 has a small residual gap in the follower's own capture (20,979/21,120, 0.67%, not chased --
confirmed no more data exists anywhere, not a tool bug); 2 are skipped:

1. **dean-20260810-105211-685** -- genuinely, severely truncated (campaign paused mid-run, no
   stage files, no harness_stop, stdout stops right after tokenizer setup). No ground truth to
   validate an estimate against. Not processed.
2. **dean-20260813-130251-004's 4 leaves** (the p4 parallelism run) -- each leaf's log captures
   ALL 4 pods' combined traffic, not its own 1/4-rate share. The tool's design assumes one
   harness process per log; this shape needs its own design, not a mechanical run against data
   it wasn't built to interpret. Not processed.

## A real bug found and fixed mid-batch (commit 5900a914)

Found while processing dean-20260812-203217-894 (calibration-probe OOM, no local log at all --
checked with Dean before extracting it from the follower, outside the original reharvest
handoff's named scope, approved). First attempt undercounted by 370/7110 -- looked like more
truncation, but the file had all the data; my own hardcoded +120s trailing-drain margin (sized
for the dwell profile) was 18s too tight for calibration-probe's shape. Fixed: both window
margins are now CLI flags, default trailing margin widened to 300s, and the tool now warns
explicitly when a shortfall is a margin problem vs real truncation, so this can't recur silently.
Verified against both runs already processed -- no regression.

## Not done, needs your input if it matters

Both skipped run-shapes above are real gaps in coverage, not decisions I made unilaterally to
close. If either matters for your panels, they need their own scoping (a p4-aware multi-pod
design for the parallelism run; nothing to do for the severely-truncated dwell cell short of
accepting it has no recoverable per-request data).
