Part of #1492 (Epic A — Multi-analyzer pipeline & analyzer lifecycle).

A stalled, errored, or never-reporting analyzer could silently veto scale-down. Gate the veto on **per-analyzer liveness**: an analyzer with no recent informative result cannot block scale-down, and if no analyzer is live for a model, scale-down is withheld (safety floor).

Fixed by #1481 (merged, f5261c8e).
