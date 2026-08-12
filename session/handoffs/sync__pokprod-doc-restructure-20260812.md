from: plans (planner session, pokprod benchmark thread)
to: sync
session: pokprod doc restructure — split ta-pokprod-testing-plan.md into 4 docs

## What changed

`planning/ta-pokprod-testing-plan.md` (1643 lines, mixing durable architecture, settled execution
history, live scenario work, and a scattered decision ledger) has been split into four focused docs,
per Dean's explicit request ("restructure the doc. careful steps. do not lose info. split into t1 and
t3 if needed"):

- `planning/ta-pokprod-architecture-design.md` — Type 1, durable contracts.
- `planning/ta-pokprod-execution-plan.md` — Type 3, settled phased execution (Phases 0–4 core,
  ownership map, tooling track T1–T12).
- `planning/ta-pokprod-open-scenarios.md` — Type 3, LIVE — the actively-changing scenario surface
  (dwell mechanism, no-action-band derivation, coverage-matrix ask), with a checklist of what still
  needs Dean at the top.
- `planning/ta-pokprod-history.md` — decision & correction ledger, append-only, fetchable by
  decision-ID (`D-1` through `D-27`) or topic tag without reading the whole file — grep-based lookup
  by design (Dean's stated priority: reads must be fast and tool-free; write cost doesn't matter).

The original doc is **not deleted** — it's marked SUPERSEDED at the top with links to the four new
docs, and its full content is preserved below a `<details>` fold for two things the new docs
deliberately don't duplicate (the unexecuted Grafana-observability fact-finding recipe, and several
coder-status-file citations that describe what the doc said at the time they were written).

**A careful cross-check pass found and repaired ~13 real content gaps** before finalizing the split
(not just reorganizing — actually re-deriving lost detail): Ofer's fork identity, the exact refresh-tag
mechanism and digest, the 1a/1b PR-worktree names, two cosmetic Makefile defects' exact text, the four
genuinely-unconditional shared-write audit with commit hashes, the `gateway.className` literal-vs-
detected finding and its consequence for the end-user goal, the residual-hardcode verification command,
the legacy-runbook fallback note, a `docker.io` cleanup flag, and — most importantly — a mislabeled
"DONE" on the inference-perf load-gen fix, which is **not yet implemented** (now corrected and tracked
as T12).

**Mid-restructure, an unread handoff surfaced newer state that had to be folded in before finishing:**
`sync__benchmark-campaign-migration-and-t9-20260812.md` (from `benchmark`, not yet processed) reported
the 7 pre-existing 2026-08-10 campaign directories migrated into the new `runs/` tree, the parallel
`session-notes/campaign-viz/` figure mirror deleted (resolving an architecture-doc gap this restructure
had itself just flagged as "not yet reconciled"), and T9 actually wired into `benchmark-run`
(`3ab8128a`) — closing that item for real, not just correcting its framing. It also corrected the
bearer-token hazard's exact file location (`environment/context.ctx`, not the originally-flagged
`run/*.yaml` — the earlier removal targeted the wrong file; the ask itself, rotation, is unchanged and
still Dean's). All three are folded into the new docs and the ledger (`[[D-27]]`).

## Update CURRENT.md

Every CURRENT.md line currently pointing at `ta-pokprod-testing-plan.md` §-numbers should be repointed:

- Line ~185 (`§7.6.1 (cold resume) + §9.1 (T1–T11 owners)`) → repoint to
  `ta-pokprod-open-scenarios.md` §5 (cold-resume state) and `ta-pokprod-execution-plan.md` §7.1
  (tooling track, now T1–T12).
- Line ~285 (`two Dean-owned items (§9.1 ...)`) → **T9 is no longer Dean-owned — it's DONE**, wired
  into `benchmark-run` automatically ([[D-27]] in the history ledger). T10 (file upstream issues) is
  still Dean's, tracked in `ta-pokprod-execution-plan.md` §7.1.
- Line ~370/~380 (`[Status: DRAFT; Phases 1–4 gated on its own STOP block]` /
  `Full detail: [ta-pokprod-testing-plan.md]`) → this framing is now stale on two counts: the STOP
  block was lifted long ago (the mission has been running since 2026-07-30+), and the doc it points at
  is superseded. Repoint to `ta-pokprod-execution-plan.md` for settled state and
  `ta-pokprod-open-scenarios.md` for what's still live.

**Also worth folding into the CURRENT.md benchmark entry, since it's news this sync hasn't yet
carried:** the 08-12 campaign-directory migration (56 files, verified clean of the bearer-token
pattern) and T9's real wiring (commit `3ab8128a`) — currently only recorded in
`session/status/benchmark.md` §20.28 and the unprocessed `sync__benchmark-campaign-migration-and-t9-20260812.md`,
not yet in CURRENT.md at all.

## Not touched, flagged for whoever picks it up next

- **`session/handoffs/plan__benchmark-env-guard-design.md`** (addressed to the planner, dated
  2026-08-10, still open/unconsumed) — a real, settled `.env`-contract redesign (X.env naming instead
  of context-keyed, a guard-not-tiers model, a wizard forward-item) that supersedes part of
  `ta-pokprod-architecture-design.md` §5. **Deliberately not folded into this restructure** — Dean
  chose to keep the mechanical split and new-content-addition as separate passes. Still owed.
- **`session/handoffs/sync__benchmark-campaign-migration-and-t9-20260812.md`** — not yet consumed by
  a sync pass; its CURRENT.md-facing content is folded into this handoff above, but the original
  should still be marked `.DONE` once acted on (or left for the next sync pass to consume directly —
  either resolves it, don't double-apply).
- **`session/handoffs/benchmark__pokprod-plan-tooling-track.md`** (open, dated 2026-08-08) — a trigger
  to the benchmark coder citing line ranges in the now-superseded doc. Stale regardless of this
  restructure (several rounds of correction happened after it was sent); not repaired, since triggers
  carry no instructions and the coder re-reads the plan fresh rather than trusting old line numbers.

## Pending handoffs table

No handoffs consumed by this session. `plan__benchmark-env-guard-design.md` and
`sync__benchmark-campaign-migration-and-t9-20260812.md` both remain open — see above.
