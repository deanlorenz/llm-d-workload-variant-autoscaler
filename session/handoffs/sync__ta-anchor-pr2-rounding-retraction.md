from: plan (ta-anchor-dynamic-refresh Type-3 owner)
to: sync
session: correction to sync__ta-anchor-pr2-code-complete-reviewed-no-defects.md — rounding was never open

## What changed

My prior handoff (still unconsumed) listed **two** things remaining as Dean's: `ceil`/`floor` rounding
and `AD8` (b) placement. The first was a mis-scoping on my part, caught by a designer correction and
verified against the shipped code (commit `1cca5563` on `plans`):

`capN = min(replicasToCover(share, gpusPR), gpusAvail/gpusPR)` rounds its two terms in **opposite
directions on purpose** — the entitlement (`replicasToCover`) rounds up, the pool (`gpusAvail/gpusPR`)
rounds down — per a shipped comment stating the rule explicitly. The frozen Type 1's `floor` mandate is
about the pool term only and is already satisfied by the shipped code. There was never a discrepancy
between the Type 1 and the tree to hold open; I had conflated two different quantities into one fork.

## Update CURRENT.md

Wherever the prior handoff's content lands, drop the `ceil`/`floor` item from "what remains Dean's."
**Only `AD8` (b) placement remains open.** Also: the plan's authorized §4a residual (`multi-analyzer-
pipeline.md:858`) is now **DONE** (`6d55fbd7`), not merely authorized — the branch tip moved from
`a9afb740` (25 commits) to `6d55fbd7` (26 commits) since the prior handoff was written.
