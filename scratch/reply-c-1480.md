Thanks for the review, @ev-shindin. Both points addressed — pointers to the changes:

**1. No-EPP / arrival = 0 → possible scale-down.** Confirmed intentional and safe within this PR's scope: zero demand only *permits* scale-down — it can't force a scale action or drive scale-up — and the all-live-agree gate still governs whether a scale-down actually happens. I documented that reasoning in-code at the demand-assembly site in `94accd09`.

On the operator requirement — agreed it should be a hard, user-facing statement, not just the developer guide. Operator enablement docs live in llm-d/llm-d, tracked here as #1498 (TA is opt-in + restart-required); I've extended it with a third requirement: **do not enable the ThroughputAnalyzer without EPP arrival metrics present**, since without them a busy model reads as idle. The doc change lands as a PR against llm-d/llm-d.

**2. Broken query vs. idle model.** I considered the `ArrivalRate == 0 && ΣRequestRate > 0` cross-check but didn't use it: `ReplicaMetrics.RequestRate` is a completion/processed rate, not an arrival rate — a draining engine keeps `RequestRate > 0` after arrivals have legitimately dropped to zero, so that condition is a normal ramp-down state and would false-positive constantly. I documented why RequestRate isn't an arrival proxy in `94accd09`.

The sound signal is temporal, not instantaneous — "supply has been live but demand has never been observed for a full staleness window." That's implemented as an observability-only WARN in the liveness path in the companion PR #1481 (`c32235be`); it never sets liveness and never affects a scale decision.
