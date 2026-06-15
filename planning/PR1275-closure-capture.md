# #1275 (collector-va-attribution) — closure capture

**Type:** reference · **Date:** 2026-06-15 · **Status:** FINAL

#1275 is being closed (superseded by #1267). This records what it contained and
where each piece lands, so nothing is silently lost. Branch tip at closure:
`6c0c6d7d` (origin/collector-va-attribution); PR #1275; implements #1263.

## Why closed

#1267 (`feat/pod-locator`, merged `c55906a4`) solved the same goal — make
`llm-d.ai/variant` optional — with a richer mechanism (ownerReference-walk
`PodLocator` → managed HPA/ScaledObject) and **kept the label** as the fast path
and the shadow-pod resolution mechanism. #1275's central move (drop the label from
all 11 queries + resolve via a pod-object `Attributor` seam) is both redundant with
#1267 and, if forced onto #1267, a **shadow-pod regression**. See
[`PR1267-impact-and-decisions.md`](PR1267-impact-and-decisions.md).

## Disposition of each piece

| #1275 piece | Disposition |
|---|---|
| Drop `llm_d_ai_variant` from 11 queries | **Dropped** — #1267 deliberately retains the label (fast path + shadow pods). |
| `Attributor` seam + `internal/collector/attribution` package (pod-object label read) | **Dropped / superseded** — `locator.PodLocator` is the seam; owner-walk is the resolution. |
| identity-only `buildInstanceKey` (2-return closure) | **Dropped** — #1267 made it a 3-return method with locator fallback. |
| **A1 throughput key-mismatch fix** (add `instance` to 3 throughput queries; re-key 3 loops; `ThroughputKeyMerge` test) | **Delivered by #1250** — TA3 already carries it (label-retained form). Replays onto #1267's method form during the #1250 rebase. |
| **`UnattributedReadyPods` event** (R1/R2 — constant + helper + gated check + tests) | **Relocate** → fold into the #1250 rebase (same file/layer). Fallback: standalone follow-up issue. **Only genuinely orphaned piece.** |
| Docs: `variant-attribution.md`, `controller-behavior.md` edits | **Dropped / superseded** — #1267 wrote its own locator docs + controller-behavior edits. |

## Recoverable source

The full implementation (v1 + R1 + R2) is the single squashed commit `6c0c6d7d` on
`origin/collector-va-attribution`. If the branch is archived via `git boidem`, it
becomes tag `archive/collector-va-attribution` (pushed to origin) — the
`UnattributedReadyPods` constant/helper/check + tests are recoverable there for the
#1250 fold-in.

## Plan-branch docs now stale (this branch is dead)

`planning/collector-va-attribution-plan.md` (incl. R1/R2/finalization sections) is
historical only — no longer an active plan. The `session/handoffs/collector-va-attribution__*`
triggers and `plan__collector-va-attribution-*` handoffs are spent; sweep at the
next `/sync-current`.
