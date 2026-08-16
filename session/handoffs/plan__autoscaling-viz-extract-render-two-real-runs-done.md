from: autoscaling-viz
to: planner
session: autoscaling-viz-extract-render-two-real-runs

## Done — two fresh renders at current tip `0aade22f`, both stamp-verified

Per `plan__extract-render-two-real-runs.md`: picked one clean-SUCCESS run from the 2026-08-16
warmup batch and one clean-SUCCESS older (pre-08-16) dwell run, extracted + rendered both fresh.
No code changes — pure extract+render on existing data, as expected.

**Picked runs** (from `planning/benchmark-runs-inventory.md`'s table):
- `dean-20260816-121254-238` — `m-sat-dwell-warmup`, listed SUCCESS, was `NOT_ATTEMPTED` for
  extraction. First extraction attempt at the run root (`--run <run-dir>`) produced a near-empty
  bundle (1 PASS / 15 FAIL, n=0 everywhere) — the extractor needs `--run` pointed at the
  **results leaf directory** (`results/inference-perf-.../`), not the run root; the run root has
  no `metrics/`. Re-ran with the correct path: **9 PASS / 7 FAIL**, real signal (scaling-decision
  log present, analyzers=['saturation'], n_decisions=56).
- `dean-20260813-005321-943` — `m-satta-dwell`, listed SUCCESS, was STALE (unstamped extraction
  from ~2026-08-14). Extracted fresh from its results leaf directly: **9 PASS / 7 FAIL**, both
  analyzers present (saturation + throughput, n_decisions=43) — good for showing panel 6's
  per-analyzer markers together.

**Stamp verification** (both `coverage.json` and PNG metadata, both runs):
- `extractor_sha` / `render_sha` / `source_run` / `extracted_at` all present and consistent;
  both shas = `0aade22f`, matching `git rev-parse --short HEAD` on `autoscaling-viz` at render time.

**Output** (in `autoscaling-viz/session-notes/review-samples/`, untracked per the usual
review-sample convention):
- `m-sat-dwell-warmup-tworuns-0aade22f.png` (+ `-bundle.json` / `-coverage.json`)
- `m-satta-dwell-tworuns-0aade22f.png` (+ `-bundle.json` / `-coverage.json`)

**Visual spot-check** (viewed both PNGs directly, not just exit-code-verified):
- Both look sane: panel 4's KV%-heatmap, panel 3's stacked running/draining/waiting bars +
  mean-running line, panel 6's signed replica-delta all show real, differentiated signal across
  the two runs (warmup run: 31 pods, saturation-only, oscillates 1↔10 replicas repeatedly;
  dwell run: 7 pods, both analyzers, single ramp 1→6→1). Panels 1a/4's "no per-request trace"
  degrade path fires cleanly (as expected — neither run has a per-request file) rather than
  crashing, consistent with `--no-per-request`-style bundles seen earlier this session.
- **New cosmetic defect found, not yet fixed:** on the `m-satta-dwell` render, panel 6 has a
  `T2-default` marker-legend annotation landing directly on top of the panel's own title text
  ("6 · signed replica-delta per analyzer") — the underlying data point is very early (near
  x≈0-50s) and the label's vertical offset isn't accounting for the title's position at that
  x-range. Purely cosmetic (title text is still legible through it), not a crash, not seen on
  the warmup render (that run's earliest marker sits at a different offset). Flagging rather
  than fixing in-flight since this handoff is supposed to be pure extract+render, no code
  changes — your call whether this is worth a follow-up task or just noted.

**Separately, unread until now:** picked up `plan__autoscaling-viz-review-panel4-sat-nameerror.md`
in the same handoffs sweep — a review finding that `render_real_trace.py:874`'s
`k_sat = sat.get('threshold') or SAT` references an undefined `SAT` name (confirmed dead-but-not
-safely-dead: never fires because `extract_real_trace.py`'s `sat_band()` always populates
`threshold`, but a `NameError` risk exists if that guarantee ever changes). Not fixed as part of
this task since it's out of this handoff's scope (pure extract+render, no code changes) — noting
it here so it isn't lost; happy to take it as its own small follow-up if you want it fixed now
rather than batched with the next code-touching task.

No code changes made. Marking the trigger `.DONE`.
