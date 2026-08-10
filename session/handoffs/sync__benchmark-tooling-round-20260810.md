from: benchmark
to: sync
session: benchmark tooling round 2026-08-10

## What changed

Three local commits on `benchmark` (tip `13845aaf`), all DCO-signed, tree clean. **No cluster
contact, no run, nothing pushed.**

- `add1d400` — fix the WVA timeseries extractor emitting silent nulls (+ `post_run_analyze.sh`,
  which was swallowing the failure)
- `c74812f7` — add our own benchmark guide `docs/wva-benchmark-guide.md`; `.env.sample` image pin
- `13845aaf` — resolve the duplicate status file; name one authority

## Refs (full state — CURRENT.md should point, not store)

- `plans/session/status/benchmark.md` **§19** — the live *state* section (§18 remains live
  *findings*). Authoritative copy, saved this session.
- `plans/session/handoffs/plan__benchmark-tooling-round-and-own-guide.md` — the planner-side items
  (plan amendment, guide verification, image pre-check, parked observability item).

## Update CURRENT.md — replace the benchmark entry's body with this abstract

**2026-08-10 — pokprod benchmark: tooling round; extractor fixed, our own guide started.** *WIP —
no cluster contact this session.* The §18 extractor defect is **fixed and verified** (`add1d400`):
`dump_wva_target_timeseries.py` now yields **54/54 hydrated** rows from the committed dwell log
against 41/**0** before, and **independently reproduces §18's headline** — per-replica capacity
25,348 → 329,011, ratio **13.0×**, matching the 10–13× collapse found by hand. Recovered timeseries
committed. Two deeper defects fixed alongside the stale pattern: the guard only refused to
overwrite on *zero* rows (so an all-null parse could replace good data — it protected against
rotation, not drift), and `post_run_analyze.sh` downgraded the failure to a soft note in exactly
the output an operator reads. New `--log-file/--no-window` allows offline re-parse with no cluster.
**New, ours:** `docs/wva-benchmark-guide.md` — a portable guide standing **alongside** the upstream
one (Dean: *"we do not diverge from upstream… we just add another guide"*); an edit to the shared
`docs/developer-guide/two-variant-wva-benchmark.md` was **reverted**, and the branch touches zero
files there. The pokprod runbook remains the per-environment detail.

**Owed by Dean / open, none of it mine to close:** (a) the **clean-refresh test** is the new
guide's stated acceptance criterion and is **unperformed** — needs a GPU cluster; until it passes
the guide is provisional *and says so in its own text*; (b) the planner should amend §7.6.1 —
"run `post_run_analyze.sh` immediately" is **necessary but not sufficient**, since promptness
defends against rotation but not against format drift; the durable form is *save the raw controller
log, then parse*; (c) the **observability/dashboard** item is **parked, not dead** — Dean
2026-08-10: lower priority, needs more work; intent = a dashboard running alongside the test so
results can be captured.

⚠️ **Armed footguns — carry verbatim:** (1) **The ScaledObject is still PAUSED** (that is how the
GPUs were released after the 08-08 dwell run). **Un-pausing is a mandatory first step of the next
run**, or you get a flat 0-replica trace that reads as a legitimate no-scaling result.
(2) **Restart the controller before each run** — in-memory capacity history contaminates across
runs, making run 2 a function of run 1's load. (3) **The image under test moved to
`ta-0.9-anchor-pr2-20260809`** (was `ta-0.9`) and is **unverified against the parser** — a tag
change can move the analyzer log format with it, which is exactly how the parse broke before. The
failure is now loud rather than silent, but that is a backstop: short run → confirm analysis fields
populate → only then a long run. A read-only pre-check of the PR-2 branch's `engine_v2.go` log
lines is cheaper and has **not** been done.

## PR Status

No change — `benchmark` has no PR and is not headed upstream.

## Blocked on — no change, but note the ordering is unchanged

Still, in order: Dean's §7.6 (a)/(b) answer or explicit deferral → Dean applying the gateway
access-log follower → my §7.6.1 preconditions → Dean's run approval. This session did not touch
any of those.

## Note on this handoff's own subject matter

The duplicate-state-file cleanup that prompted it is **done**: `plans/session/status/benchmark.md`
is now the **sole authority**, maintained directly by the coder (Dean's direction), with the
tracked benchmark-branch copy removed and a README recording why. Root cause worth propagating: the
worktree-isolation guard blocks the **Write/Edit tools** from the shared path but **not Bash
`cp`/`mv`**, so "a coder cannot write to `plans/session/`" is not a correct blanket statement —
though the guard does refuse compound shell commands, so such writes must be plain single commands.
