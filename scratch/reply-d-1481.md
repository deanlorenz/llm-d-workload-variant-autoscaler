Thanks, @ev-shindin — both follow-ups folded into this PR:

**1. Shared `no-data`/`error` sentinels.** Done in `61060530` — exported `pipeline.ReasonNoData` / `pipeline.ReasonError` as the single source of truth; `ResultIsInformative` and the saturation analyzer now reference the same constants, so a rename can't silently drift the liveness classification.

**2. `lastGoodAnalysis` eviction.** Done in `c32235be` — a selective prune at the per-cycle boundary evicts model keys no longer in the active-model set while keeping timestamps for still-active models. It's targeted eviction, not a per-cycle reset (the latch is deliberately cross-cycle: a transient `no-data` with a recent good result must still count as live). The map is in-memory, so it also clears on a controller restart.

The same commit adds an observability-only demand-liveness warning (supply live but no demand for a full staleness window — the temporal broken-arrival signal referenced from #1480 point 2); it's log-only and never gates a decision.

On the `AnalyzedAt` aside — good to flag. Both saturation and throughput set it today; the liveness code keys off it deliberately, and that implicit contract is called out in the liveness comments (`33226cd4`/`c32235be`).
