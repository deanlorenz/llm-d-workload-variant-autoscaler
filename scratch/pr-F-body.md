## What

A batch of defensive correctness guards for the ThroughputAnalyzer / saturation pipeline (no behavior change on the happy path):

- **reject NaN `k`** in `ObservationWindow.Add` (a bad fit can't poison the observation window);
- **wire real per-replica metric freshness** in the collector (the staleness gate was previously inert);
- **share one ITL-model validator** across both fit tiers (removes divergent validation);
- **reject NaN / out-of-range KV usage** in `computeLocalDemand`;
- **harden the liveness engine** against a zero optimization interval and a zero `AnalyzedAt` timestamp, and extend the all-removed-vs-transient prune comment (the three follow-ups raised on the veto-liveness review).

## Testing

Unit tests per guard; `make test` full-repo green; lint 0; gofmt/build clean.

```release-note
Hardened the ThroughputAnalyzer and saturation liveness engine against NaN/out-of-range inputs, a zero optimization interval, and a zero analysis timestamp; per-replica metric freshness is now honored.
```
