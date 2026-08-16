from: benchmark
to: plan (viz-panels scope)
session: benchmark

## Built and verified: hack/benchmark/estimate_per_request.py (commit a092536f)

Per the design in envoy-per-request-recovery-tool-plan.md's "Per-request data extraction/
estimation for panels 1a/1b" section, built against dean-20260813-005321-943 (m-satta-dwell)
only, per your own request. Consolidates two techniques into new code -- no existing scratch
tool modified/moved/deleted. Full detail in session/status/benchmark.md §20.41.

Output written to metrics/processed/per_request_estimated.json under that run's results leaf
(gitignored like every other metrics/processed output -- not committed, code only is).

## Finding 1: the target run's own Envoy trace is truncated -- affects this run's estimate directly

19,388 in-window requests vs the harness's own attempted total of 21,120 (delta -1,732),
concentrated at the START of the window (first Envoy arrival 3m39s after harness_start). Matches
the known kubelet-log-rotation-eviction risk envoy_per_request.py's own docstring already warns
about -- first time it's actually been hit on a real run. Consequence for this specific output:
**stage 0 (the 5rps entry rung) has ZERO requests in the estimate** -- entirely evicted, not an
artifact of my code. Designed around it (timestamp-based stage assignment instead of positional
partitioning, so the gap doesn't corrupt the other stages), but the gap itself is real and this
run's stage-0 estimate simply doesn't exist.

**Playbook implication, worth raising rather than silently working around:** if per-request
estimation is going to be a standing fallback for future runs too, the run playbook should make
sure the full trace is actually captured before this gap recurs -- e.g. via the already-built
gateway-log-follower (captures continuously to the PVC, not vulnerable to the same post-run
kubectl-logs rotation cliff) rather than relying on a post-run harvest. Not my call how the
playbook should change; flagging the concrete mechanism so whoever owns that decision has it.

## Finding 2: an unexplained rate anomaly in the estimate, not resolved

Stage 4 (2rps drain, 720s) shows an OBSERVED rate of 3.16 req/s in the Envoy trace -- 58% above
its configured rate. Stages 2-3 track their configured rates within 5% (19.09/20, 24.84/26), so
this isn't a general offset in my window math -- it's specific to stage 4. Two candidate
explanations, neither confirmed: (a) genuine traffic behavior (e.g. responses queued during the
26rps rung draining into what looks like new stage-4 arrivals to Envoy, since Envoy logs on
receipt not completion), or (b) an artifact of my own trailing-margin window (the last stage has
no upper time bound other than a +120s drain allowance, which could be pulling in something it
shouldn't). Did not debug further or guess at a fix -- flagging precisely so you can decide
whether this matters for panel 1a/1b's purposes before I spend more time on it.

## Not yet done

Generalizing beyond this one run -- explicitly out of scope for this handoff, per your own
"build and run against dean-20260813-005321-943 only, first" framing.
