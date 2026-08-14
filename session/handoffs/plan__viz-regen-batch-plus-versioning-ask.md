from: plan (pokprod/benchmark-execution scope)
to: plan (autoscaling-viz scope)
session: viz-panels

Dean directly reviewed the 7 existing `viz/panels.png` files today (2026-08-14) — the first time
anyone has actually opened one since they were generated. Two findings, both real:

## 1. All 7 existing panels are stale — 6 commits behind current render code

Generated 2026-08-12 11:55:23 (single batch, right after `cff4e4c0` panel-6-add landed), but the
render script has moved 6 commits since: `037106f2` (title fallback, panel-3 legend/hatch/edge),
`fbecfe26` (panel 1b y-axis capping, panel 3 request-domain redesign), `08927557` (fix-round 1),
`3f12aaa1` (panel 6 redesign — signed replica-delta), `e188d244` (drain-window backward-scan
bound). The 7 PNGs show the pre-redesign panel 6 shape (actually — checking again, they predate
panel 6 rendering into these specific files entirely; they only show panels 1a/1b/2/3/4/5) and none
of the later fixes. **Every run needs its panels regenerated against current code before anyone
trusts what's in them.**

**Runs needing regen (7, currently stale):**
- `dean-20260810-064736-555` (m-satta-staircase)
- `dean-20260810-072736-888` (b-satta-staircase)
- `dean-20260810-080708-371` (m-sat-staircase)
- `dean-20260810-084756-739` (m-ta-staircase)
- `dean-20260810-092644-320` (m-satta-dwell)
- `dean-20260810-100827-539` (m-sat-dwell)
- `dean-20260810-105211-685` (m-ta-dwell, truncated — panels valid for what they show, just stale)

**Runs never rendered at all (14, no `viz/` directory exists):**
- `dean-20260812-152105-714` (prefill-knee, TA)
- `dean-20260812-154829-365` (interrupted, no REPORT.md — probably skip)
- `dean-20260812-203217-894` (calibration-probe, TA, OOM'd)
- `dean-20260812-231722-822` (calibration-probe, TA, clean retry)
- `dean-20260813-000928-609` (dwell rerun, TA)
- `dean-20260813-005321-943` (dwell rerun, satTA)
- `dean-20260813-013728-756` (dwell rerun, sat)
- `dean-20260813-130251-004` (calibration-probe-p4, 4 parallel pods)
- `dean-20260814-031317-105` (unclear, check before rendering)
- `dean-20260814-032308-959` (prefill-knee, sat)
- `dean-20260814-035754-869` (prefill-knee, satTA)
- `dean-20260814-043416-513` (unclear, check before rendering)
- `dean-20260814-044129-931` (calibration-probe, sat, OOM'd)
- `dean-20260814-050448-704` (calibration-probe, sat, clean retry)
- `dean-20260814-053822-692` (calibration-probe, satTA)

21 run directories total; 19 need action (2 interrupted/unclear ones flagged for a judgment call
on whether they're worth rendering at all).

## 2. No version stamp anywhere — Dean's direct ask

"Please verify that all panels.png (many many copies) are now using the latest code. Perhaps add a
version somewhere so we can track this." There is currently no way to look at a `panels.png` and
know which commit of `render_real_trace.py`/`extract_real_trace.py` produced it — I only found the
staleness above by manually diffing file mtimes against `git log`, which doesn't scale past one
spot-check and isn't something a report reader can do themselves. **Ask: stamp each render with
something that answers "what code made this" at a glance** — e.g. the render script's own git SHA
(or `git describe`) baked into the PNG itself (a small text annotation, same pattern as the
existing "not exercised by this run" / "caveats" footer lines already in the panel) and/or into a
sibling metadata file next to `panels.png`. Whatever form fits this toolchain's existing patterns
— the requirement is just that staleness becomes checkable without a manual git-log spot-check.

## Not urgent, but flagging: this session's own report cites these panels

`plans/planning/ta-pokprod-campaign-report.md` (benchmark-execution scope, not this scope's to
edit) currently says "no viz output exists for any run since 2026-08-10" — technically true for
runs after 2026-08-10 but incomplete: it doesn't mention the 7 *existing but stale* panels from the
2026-08-10 campaign itself, since I hadn't looked at them until Dean did. That correction is mine
to make on my own doc, not yours — noting only so the two scopes' pictures of "what viz output
exists" stay reconciled once this batch lands.

No specific timeline requested — Dean is reviewing panels directly while this lands, not blocking
on it.
