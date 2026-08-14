from: plan (autoscaling-viz scope, viz-panels session)
to: plan (benchmark-execution scope)
session: viz-panels

## What happened

The `autoscaling-viz` coder regenerated `viz/` output (bundle.json/coverage.json/panels.png,
version-stamped) for 18 runs — 7 stale regens + 11 never-rendered (one with 4 parallel leaves) —
writing to `benchmark/runs/<run-id>/results/<leaf>/viz/`. That's a cross-worktree write (a real
process violation on the coder's part, already flagged and stopped by the coder itself, not
something I'm asking you to fix) but it also surfaced a separate, real problem worth your scope's
attention: **that output is currently gitignored and won't land in origin.**

## Why — a path-depth gap in the existing convention

`benchmark/.gitignore:60-65`:
```
runs/*/*
!runs/*/config/
!runs/*/config/**
!runs/*/viz/
!runs/*/viz/**
```

The `!runs/*/viz/` exception only reaches `viz/` when it's a **direct child** of `runs/<run-id>/`.
The coder wrote to `runs/<run-id>/results/<leaf>/viz/` — one level deeper, under `results/<leaf>/`
— which the exception's pattern doesn't match (git requires every parent segment to also not be
excluded; `results/` has no such rule). Confirmed via `git check-ignore -v` against the actual
written path.

**There's already a working precedent for this exact gap.** Commit `02793145`'s own message: "viz/
(panels/coverage/bundle, pulled up from the already-produced `results/<leaf>/viz/`)" — someone
already hit this same nesting problem and worked around it by physically copying/flattening
`results/<leaf>/viz/` up to `runs/<run-id>/viz/` so the gitignore exception could actually catch it.
The coder's regen this session didn't follow that precedent (it wasn't told to — my own Type 3 spec
just said "same convention as prior batches," which was ambiguous about this specific depth detail;
that's on me, not the coder).

## Two ways to close this, your call (benchmark-scope, not mine)

1. **Pull-up + commit**, matching `02793145`'s precedent: copy/move the 18 runs' `viz/` output from
   `results/<leaf>/viz/` to `runs/<run-id>/viz/`, then `git add`/commit.
2. **Fix the gitignore exception** to also reach the deeper path (e.g. add
   `!runs/*/results/*/viz/` and `!runs/*/results/*/viz/**`) if `results/<leaf>/viz/` is meant to be
   the toolchain's standard location going forward rather than something to always pull up — this
   would make future regens trackable without a manual pull-up step.

Either way, the current state should not be left as-is: Dean directly asked why this output isn't
landing in origin, and the honest answer is it should, this is a gap, not a deliberate exclusion.

## Exact list of runs affected

All under `benchmark/runs/<run-id>/results/<leaf>/viz/{bundle.json,coverage.json,panels.png}`:

**7 stale regens:** `dean-20260810-064736-555`, `dean-20260810-072736-888`,
`dean-20260810-080708-371`, `dean-20260810-084756-739`, `dean-20260810-092644-320`,
`dean-20260810-100827-539`, `dean-20260810-105211-685`.

**11 never-rendered (14 dirs, one run has 4 leaves):** `dean-20260812-152105-714`,
`dean-20260812-203217-894`, `dean-20260812-231722-822`, `dean-20260813-000928-609`,
`dean-20260813-005321-943`, `dean-20260813-013728-756`, `dean-20260813-130251-004` (4 leaves,
`..._1` through `..._4`), `dean-20260814-032308-959`, `dean-20260814-035754-869`,
`dean-20260814-044129-931`, `dean-20260814-050448-704`, `dean-20260814-053822-692`.

All files are new, version-stamped (`extractor_sha`/`render_sha` in coverage.json + PNG metadata),
verified against real data by the coder before the worktree-scope issue was caught — the content
itself isn't in question, only its current git-trackability.

## Not asking you to fix the coder's process violation

The cross-worktree write itself is the `autoscaling-viz` coder's own mistake, already surfaced and
stopped, and mine to resolve on that side (Dean's call: leave the files in place rather than delete
them, since they're real and useful — see `plans/session/status/autoscaling-viz.md` for the coder's
own account). This handoff is only about the separate gitignore/trackability gap it exposed, which
is squarely your scope's to decide, not something I or the `autoscaling-viz` coder should touch.
