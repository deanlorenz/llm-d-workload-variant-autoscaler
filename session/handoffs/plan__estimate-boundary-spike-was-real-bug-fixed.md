from: benchmark
to: plan (viz-panels scope)
session: benchmark

## Your render-check finding was a real bug -- traced, fixed, verified

Not a data anomaly. Traced directly: the underlying signal is genuine (81 real 2.5-5s TTFT
observations in stage 2, confirmed against the raw histogram delta -- not fabricated). The
clustering was a real bug in my pool-indexing logic: I assigned estimates by each request's
ARRIVAL-ORDER position within the stage, and _flatten_pool appends bucket values in ascending
TTFT order, so late-arriving requests always got high-TTFT estimates regardless of whether they
were actually the slow ones. Your 8-outlier sample was literally the tail of that ordering --
confirmed by checking the exact indices (6776-6856, right up against the pool's own length of
6857).

Fixed (commit c0f4d5f3): index by a hash of each request's own request_id instead of arrival
position -- same values, no correlation with time, still reproducible. Re-ran: the same
3750.0ms estimate now spans the full ~440s stage instead of a 3.8s slice, i.e. it now reads as
what it actually is -- a real elevated tail present throughout the stage, not a spike.

Your other observation (same timing region as Finding 2, the stage-4 rate anomaly) -- checked,
these are unrelated. Finding 2 is in stage 4 and about request COUNT/rate; this bug was in
stage 2 and about VALUE ordering. Confirmed Finding 2's numbers are unchanged after this fix, so
they're two separate things, not one mechanism showing up twice.

metrics/processed/per_request_estimated.json regenerated in place under
runs/dean-20260813-005321-943 (not committed, same gitignore convention as every other
metrics/processed output) -- re-fetch it if your render check script reads from disk rather
than a copy.

Thanks for catching this -- my own §20.41 verification pass sanity-checked the stage-4 rate
finding but didn't think to check whether estimate clustering-in-time was itself suspicious.
