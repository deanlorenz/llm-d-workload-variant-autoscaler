# Classify + re-render + symlink `good-panels.png` across all `benchmark/runs/` — Code Spec (Type 3)

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

**Status:** READY

**Owner:** autoscaling-viz coder (Bob, `coder-auto` mode). Companion doc:
[`benchmark-runs-inventory.md`](benchmark-runs-inventory.md) — this spec extends and refreshes it,
does not replace it.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L24:42
- [Scope boundary — what you do NOT do {#scope}](#scope-boundary--what-you-do-not-do-scope) L43:58
- [Classification scheme {#classification}](#classification-scheme-classification) L59:93
- [Procedure {#procedure}](#procedure-procedure) L94:136
- [Canonical viz location — already decided, do not re-litigate {#canonical}](#canonical-viz-location--already-decided-do-not-re-litigate-canonical) L137:153
- [The `good-panels.png` symlink {#symlink}](#the-good-panelspng-symlink-symlink) L154:177
- [Updating the inventory doc {#inventory-update}](#updating-the-inventory-doc-inventory-update) L178:199
- [Handoff to benchmark scope {#handoff}](#handoff-to-benchmark-scope-handoff) L200:211
- [Verification {#verification}](#verification-verification) L212:228

## Goal {#goal}

Dean cannot easily tell which `panels.png` files across `benchmark/runs/` are trustworthy — current
render, real (not missing) per-request data. Build a `good-panels.png` symlink next to every run's
`panels.png` that passes both checks, and only those. For everything that doesn't pass:

- If the render is just **stale** (data is fine, code has moved on) — **re-render it** (in scope,
  this is your own render code).
- If the data is **missing and genuinely unobtainable** from anything on disk — mark it so nobody
  (including a future you) keeps re-attempting it.
- If the data is **missing but obtainable** (raw source exists, e.g. `per_request_estimated.json` or
  an Envoy log, just not yet extracted) — mark it differently, and hand it to `benchmark` scope. **You
  do not extract it yourself** — see § Scope boundary.

The deliverable a human actually looks at is the symlink: `ls benchmark/runs/*/viz/good-panels.png`
should return exactly the trustworthy set, nothing else.

[↑ TOC](#toc)

## Scope boundary — what you do NOT do {#scope}

**Obtaining/extracting missing per-request data is `benchmark` scope's job, not yours.** That data
lives on a different worktree (`benchmark/`), and — per this workspace's role/scope rules — you may
read anything there but write nothing except the specific `viz/` outputs this spec authorizes (see
§ Canonical viz location). If you find a run whose `per_request_estimated.json` or raw Envoy log
already exists but was never turned into a bundle, do **not** run any extraction against it yourself
and do **not** ask `benchmark`-scope to run your extractor for you. Classify it as "obtainable
elsewhere" (§ Classification scheme) and hand it off (§ Handoff to benchmark scope). The actual
extraction, if it happens, is their call and their code to run.

You also do not decide the canonical-viz-location question — it is already decided (§ Canonical viz
location) from prior work on this branch and on `benchmark`. Follow it, do not re-derive it.

[↑ TOC](#toc)

## Classification scheme {#classification}

For every run directory under `benchmark/runs/`, using only what `benchmark-runs-inventory.md`
already tracks plus a fresh read where the doc is stale, assign exactly one of:

1. **GOOD** — `panels.png` exists at the canonical location, its embedded `extractor_sha`/
   `render_sha` (read via `PIL.Image.open(path).info`, same mechanism the version-stamp work
   already uses) match current `git -C autoscaling-viz rev-parse --short HEAD`, AND the
   corresponding `coverage.json`'s `"Per-request trace present"` row is `PASS` (real or ESTIMATED
   data both count — an ESTIMATED-labeled bundle is still informative, just visually flagged as such
   by the renderer itself; see `autoscaling-viz-warmup-anchor-and-panel-polish-plan.md` Item AD).
   → gets the `good-panels.png` symlink.

2. **STALE — needs rerender** — data is fine (per-request trace PASS, or the run's own workload
   genuinely has no per-request collection by design and that's the *only* gap), but the PNG's
   stamp is behind current tip. → re-render (§ Procedure step 2). After a successful rerender, this
   becomes GOOD or one of the MISSING states below, depending on what the fresh coverage check
   finds — a stale render can hide a data gap that a fresh render would surface.

3. **MISSING — unobtainable** — `"Per-request trace present"` is FAIL, and none of
   `per_request_lifecycle_metrics.json` (real), `metrics/processed/per_request_estimated.json`
   (estimated fallback), or `logs/igw_pods.log` with real content (>1000 bytes — raw Envoy access
   log, the estimation tool's own input) exist anywhere under that run's results leaf. Nothing on
   disk could produce per-request data for this run, full stop.

4. **MISSING — obtainable elsewhere** — same FAIL, but at least one of the three files above exists.
   Something *could* turn this into real data, but only `benchmark`-scope's own tooling does that,
   and only on their decision.

5. **COLLECTION-FAILED** — the run itself never produced usable data at all (per
   `benchmark-runs-inventory.md`'s existing `Collection: FAILED` rows) — no viz is possible, full
   stop, not a viz-side gap. Leave these alone entirely; they're not this spec's concern.

[↑ TOC](#toc)

## Procedure {#procedure}

1. **Get the fresh run list and current tip.**
   ```bash
   ls benchmark/runs/ | sort
   git -C autoscaling-viz rev-parse --short HEAD
   ```
   Diff against `benchmark-runs-inventory.md`'s table — as of this spec's authoring, 3 runs are
   newer than the doc's last snapshot: `dean-20260816-153947-120`, `dean-20260816-161824-974`,
   `dean-20260816-174704-649`. None of the three has a run-root `viz/` yet (checked: `find
   benchmark/runs/<id> -maxdepth 1 -type d -name viz` returns nothing for any of them) — treat as
   `NOT_ATTEMPTED`, same bucket the doc already uses for that state.

2. **For every run with `Collection: SUCCESS` or `PARTIAL` (real data, not a collection failure) and
   viz stamped behind current tip: re-extract + re-render into the canonical location** (§ Canonical
   viz location). Reuse the exact procedure `autoscaling-viz-batch-refresh-all-success-runs-plan.md`
   already used and verified — same tooling, same stamp-verification discipline (confirm
   `extractor_sha`/`render_sha` in both `coverage.json` and the PNG's own embedded metadata after
   each render, against `git rev-parse --short HEAD`, for every single run, not a sample). For a
   multi-leaf run, extract+render leaf `_1` only, matching `REPORT.md`'s own primary-leaf convention
   — do not pull up a different leaf without checking which one `REPORT.md` treats as primary first.

3. **For every run with `"Per-request trace present": FAIL`** (whether freshly re-rendered in step 2
   or already current), check for the three obtainability signals in § Classification scheme item 3
   vs. 4, read-only:
   ```bash
   find <run>/results/<leaf> -maxdepth 1 -iname "per_request_lifecycle_metrics.json" -size +100c
   find <run>/results/<leaf>/metrics/processed -maxdepth 1 -iname "per_request_estimated.json"
   find <run>/results/<leaf>/logs -maxdepth 1 -iname "igw_pods.log" -size +1000c
   ```
   Classify per item 3 (none found → unobtainable) or item 4 (any found → obtainable elsewhere).
   **Do not run any extraction, even the estimated-fallback path, against these** — that crosses
   into `benchmark` scope per § Scope boundary.

4. **For every run now classified GOOD, create the symlink** (§ The good-panels.png symlink).

5. **Update `benchmark-runs-inventory.md`** with the refreshed state (§ Updating the inventory doc).

6. **Write a `plan__` handoff** listing every MISSING-obtainable-elsewhere run for the benchmark
   scope's planner to pick up or decline (§ Handoff to benchmark scope).

[↑ TOC](#toc)

## Canonical viz location — already decided, do not re-litigate {#canonical}

**The run-root `viz/` directory is canonical** (`benchmark/runs/<run>/viz/{bundle.json,
coverage.json, panels.png}`), not the nested `results/<leaf>/viz/` copy. This was settled during the
2026-08-14 "viz pull-up" work (`session/status/benchmark.md` §20.36) and is enforced by
`benchmark/.gitignore`'s own allowlist: `!runs/*/viz/` and `!runs/*/viz/**` are explicitly
un-ignored, while nothing un-ignores `runs/*/results/*/viz/` — so only the run-root copy is ever
git-tracked. For a multi-leaf run, the pull-up used leaf `_1` as the source, matching `REPORT.md`'s
own primary-leaf convention — follow the same rule.

The nested `results/<leaf>/viz/` copies that already exist are leftover duplicates from before the
pull-up decision. **Do not delete them** (not this spec's job, and deleting isn't necessary for the
symlink or classification to work) — just don't treat them as canonical, and don't bother
re-rendering into them. If you re-extract+re-render a run, write only to the run-root `viz/`.

[↑ TOC](#toc)

## The `good-panels.png` symlink {#symlink}

For every run classified GOOD (§ Classification scheme item 1), create, at the run-root canonical
location:

```bash
cd benchmark/runs/<run>/viz && ln -sf panels.png good-panels.png
```

Relative symlink (`panels.png`, not an absolute path) so it survives the directory being moved or
copied. `ln -sf` so re-running this spec is idempotent — always safe to re-point, never errors on
"already exists."

**When a run stops being GOOD** (a future code change makes today's render stale again, or a
re-render surfaces a data gap that wasn't visible before): remove the symlink rather than leaving it
pointing at a now-stale/wrong file.
```bash
rm -f benchmark/runs/<run>/viz/good-panels.png
```
A dangling or wrong `good-panels.png` is worse than a missing one — it actively misleads. Prefer
"absent" over "present but wrong" if a classification is ever uncertain.

[↑ TOC](#toc)

## Updating the inventory doc {#inventory-update}

`benchmark-runs-inventory.md`'s table gets one new column, `Good panels?`, with one of: `YES`,
`NO — reclassified below` (for anything not GOOD, pointing at whichever of the 4 non-GOOD states
applies — reuse the existing Extraction/Viz columns rather than duplicating state in a 5th column;
just add the `Good panels?` column as the derived summary).

Follow the doc's own § Refresh protocol checklist for the mechanics (diff run list, get current sha,
per-run checks, update table, keep old headline findings that are still true, retire ones that
aren't — do not blindly overwrite). Add a new headline finding summarizing the `good-panels.png`
rollout: how many runs are GOOD now, how many were re-rendered, how many are MISSING-unobtainable vs
MISSING-obtainable. Run `bash plans/scripts/toc-refresh.sh planning/benchmark-runs-inventory.md`
after editing.

**You (the coder) do not edit `plans/planning/*.md` directly — see your write-scope override.** Per
the `coder-auto` mode's corrected scope, you do not have write access to `plans/planning/` at all,
even for a doc your own worktree effectively drives the content of. Produce the refreshed table +
findings as content in your handoff/local status file, and ask the planner to fold it into the
inventory doc — do not attempt to write it yourself, and do not try to route around the block.

[↑ TOC](#toc)

## Handoff to benchmark scope {#handoff}

Write `plan__viz-good-panels-missing-obtainable-data.md` (to the benchmark scope's planner, not to
sync) listing every run classified MISSING-obtainable-elsewhere: run ID, which of the three signals
was found (real/estimated/envoy), and the coverage.json's own FAIL detail string. Frame it as
information, not an instruction — `benchmark` scope decides whether/when to extract, per this
workspace's trigger convention (a trigger carries no instructions, only refs; this is closer to a
`plan__` since it's new information for a decision, not a re-read-this-doc nudge, but keep the same
neutral framing: state what was found, not what you think should happen next).

[↑ TOC](#toc)

## Verification {#verification}

- Every run in `ls benchmark/runs/*/viz/good-panels.png` must independently pass both the stamp
  check and the per-request-trace check when re-verified by hand — spot-check at least 5 across
  different workload shapes, not just trust the classification pass.
- Every run classified MISSING-unobtainable must show zero results for all three `find` checks in
  § Procedure step 3 — re-verify at least 3 by hand.
- No run should have `good-panels.png` pointing at a `panels.png` whose PNG-embedded stamp doesn't
  match current tip — this is the one invariant that must never be violated, since it's the whole
  point of the exercise.
- Confirm idempotency: running the classification+symlink pass twice in a row with no code changes
  in between produces byte-identical results (no new symlinks, no removed ones, no changed targets).
- Report final counts (GOOD / re-rendered-to-GOOD / MISSING-unobtainable / MISSING-obtainable /
  collection-failed-skipped) in your local status file and the handoff to the planner — do not just
  say "done," give the numbers.

[↑ TOC](#toc)
