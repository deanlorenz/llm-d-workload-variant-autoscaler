Nice fix — the detector (rates decide *when* we're at the limit) / measurement (resident
tokens record *what* it's worth) split is clean, and the per-bucket running-min ceiling
read identically by every replica is the key move: it collapses the variant median to one
value so an idle sibling can't lift capacity and re-trigger the shed-to-one loop.
Estimator is genuinely inert with the switch off, tests are thorough. Two asks before merge:

**1. Gate the query registration on the switch too.** `RegisterRateCapacityQueries` runs
unconditionally in `NewEngine`, independent of `EnableRateAnchoredK2`. Since
`QueryRequestRate`/`QueryKvUsageInstant` are already in the always-executed
`engineSpecificReplicaQueries` list, this changes execution, not just registration:
pre-PR with TA off, `Build()` returned "query not found" and no Prometheus call was made;
post-PR both run every replica-collection cycle. That's the default config (TA off), so
we ship a per-cycle Prometheus load increase even though nothing reads those fields until
the switch flips — contradicting the doc's "inert until the constant is flipped" framing.
No correctness impact (I checked — no always-on reader). Suggest gating
`RegisterRateCapacityQueries` on `EnableRateAnchoredK2`; or, if you mean to always collect
μ, note that in the doc.

**2. Please rebase onto current `main`.** A few commits behind, and #1486 touches the same
`NewEngine` (limiter-builder machinery). Should be a clean adjacency, but worth doing
explicitly and re-running gates.

Minor: `QueryKvUsageInstant` is collateral in the shared registrar (estimator never reads
it) — a one-line doc note would help; dissolves if you take the gating suggestion.
