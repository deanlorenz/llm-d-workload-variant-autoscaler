# Version-stamp renders + regenerate all stale/missing viz output — Code Spec (Type 3)

**Status:** READY FOR CODER. Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
Item 9. Source: `session/handoffs/plan__viz-regen-batch-plus-versioning-ask.md` — Dean's direct
review of the 7 existing `panels.png` files, 2026-08-14.

> **Reading Protocol:** Read this section and the TOC, then fetch only the section you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Goal {#goal}](#goal-goal) L18:29
- [Part 1 — version stamp {#part-1-stamp}](#part-1--version-stamp-part-1-stamp) L30:63
- [Part 1b — PNG metadata, so the file is self-contained {#part-1b-png-metadata}](#part-1b--png-metadata-so-the-file-is-self-contained-part-1b-png-metadata) L64:87
- [Part 2 — regenerate the 21 run directories {#part-2-regen}](#part-2--regenerate-the-21-run-directories-part-2-regen) L88:120
- [Verification {#verification}](#verification-verification) L121:135

## Goal {#goal}

Two related problems, both from Dean opening actual rendered PNGs for the first time since
2026-08-12: (1) every existing `panels.png` is stale — up to 6 commits behind the current
`render_real_trace.py`/`extract_real_trace.py` — with no way to tell this from the file itself; (2)
14 (now more, see below) run directories have no `viz/` output at all. Fix the detectability problem
first (Part 1), then use it to do the batch regen correctly (Part 2) rather than the other way
around — otherwise the regen just produces another undated batch with the same blind spot next time
the render code changes.

[↑ TOC](#toc)

## Part 1 — version stamp {#part-1-stamp}

**Placement, per Dean's direct answers:** extend the existing footer text (the `caveats:`/`not
exercised by this run:` line already written at `render_real_trace.py`'s `fig.text(0.008, 0.004,
foot, ...)` call, near the end of `render()`) rather than adding a separate corner annotation — same
place a reader already looks for meta-info about the figure's trustworthiness. Also write it into
`coverage.json` (machine-checkable, not just human-eyeball) rather than PNG-only.

**What to stamp:** the git SHA (short form, e.g. `git rev-parse --short HEAD` at extraction/render
time) of the `autoscaling-viz` worktree, for both `extract_real_trace.py` (bundle/coverage
generation time) and `render_real_trace.py` (render time) — they can differ if a bundle was
extracted on one commit and rendered later on another, and that's exactly the kind of staleness gap
Dean's finding surfaced, so don't collapse them into one stamp.

**Concrete implementation, not mandated — the coder may find a cleaner mechanism:**
- Extractor: at the point `cov` (the coverage dict) is built and before `json.dump(cov, fh, ...)` at
  `extract_real_trace.py:1491`, add a top-level key, e.g. `cov['extractor_sha'] = <short SHA>` —
  compute it via `subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=<script's own dir>,
  ...)` (standard-library only, per the extractor's own design-constraints docstring — `subprocess`
  is stdlib, this is fine) with a graceful fallback (e.g. `'unknown'`) if `git` isn't available or
  the directory isn't a git repo, so this never becomes a hard failure.
- Renderer: same approach, its own short SHA, added to the `coverage` dict it already receives (or a
  separate lookup) and included in the footer text — e.g. `foot += f' | rendered @ {render_sha},
  bundle extracted @ {cov.get("extractor_sha", "?")}'`. Keep it terse; the footer is already dense
  with caveat text, per Dean's own past feedback about panel-density elsewhere on this branch — this
  is exactly the kind of thing that regresses readability if not kept short.
- If `extractor_sha` and `render_sha` don't match the *coder's own current* branch tip at the moment
  someone reads the figure, that's the staleness signal — no need to build automated
  staleness-checking tooling as part of this Type 3 (that's a separate, later ask if Dean wants it);
  the requirement here is just that the information is present and checkable by hand or a future
  script, not that a checker script exists yet.

[↑ TOC](#toc)

## Part 1b — PNG metadata, so the file is self-contained {#part-1b-png-metadata}

**Dean's question, worth acting on:** should some of this provenance live in the PNG's own
metadata, not just the footer text and `coverage.json`? Yes — the footer is for a human glancing at
the figure, but a `panels.png` routinely gets copied out of its own directory (mirrors under
`session-notes/review-samples/`, backlog copies, review samples) and separated from its sidecar
`coverage.json` in the process — this branch's own history already has multiple examples of exactly
that. Embedded metadata travels with the file regardless.

**Mechanism:** PNG's native text-chunk metadata (`tEXt`/`iTXt`), not EXIF (EXIF is a JPEG/TIFF
convention, not natively part of the PNG spec, and libpng/most PNG readers don't expect it there —
use PNG's own mechanism instead). `matplotlib.pyplot.savefig()` already accepts a `metadata=` dict
kwarg that's passed straight through to Pillow's PNG writer — no new dependency, no new write path,
just pass a dict at the existing `fig.savefig(path, dpi=120)` call site
(`render_real_trace.py`, near the end of `render()`).

**What to embed:** at minimum, the same two SHAs as the footer (`extractor_sha`, `render_sha`), plus
the source run ID/leaf path and the extraction timestamp — enough that `identify -verbose
panels.png` or `PIL.Image.open(...).info` on an orphaned copy, with no sidecar file at all, still
answers "what produced this and from what." Keep the *human-visible* footer terse (per Part 1); the
embedded metadata can be more complete since nobody's expected to read it by eye.

[↑ TOC](#toc)

## Part 2 — regenerate the 21 run directories {#part-2-regen}

**Do this only after Part 1 lands**, so the regenerated batch is itself stamped — regenerating
first and stamping second just recreates the same blind spot one version later.

**7 runs needing regen** (stale, from before this branch's 5 recent commits):
`dean-20260810-064736-555`, `dean-20260810-072736-888`, `dean-20260810-080708-371`,
`dean-20260810-084756-739`, `dean-20260810-092644-320`, `dean-20260810-100827-539`,
`dean-20260810-105211-685` (truncated run — panels valid for what they show, still regen for the
version stamp).

**14 runs never rendered**, per the handoff's own list — 12 clearly identified by workload/analyzer
combination, 2 flagged by the handoff's author as "unclear, check before rendering"
(`dean-20260814-031317-105`, `dean-20260814-043416-513`) and one flagged as "probably skip"
(`dean-20260812-154829-365`, interrupted, no `REPORT.md`). **Use judgment on the 2 unclear ones** —
check what's actually in each run directory (does it have the inputs `extract_real_trace.py` needs?
does it look like a real completed run or a false start?) before deciding to render or skip; don't
render blindly just because a run directory exists. Skip the interrupted one unless inspection shows
it's actually usable.

**By the time this Type 3 is picked up, check `plans/session/handoffs/` and
`benchmark/runs/` again for anything newer than 2026-08-14** — this handoff's run list is a snapshot,
and the benchmark-execution scope is actively running new cells in parallel (per Dean's own
"current focus is making it all work over different scenarios" framing from earlier this branch's
history). Don't treat the list above as exhaustive if the run directory has grown since.

**Output location:** same convention as prior batches — `<run-root>/results/<leaf>/viz/` (canonical)
and/or `session-notes/review-samples/` mirrors, matching whatever the coder's own established
pattern from Task 5's backlog rerun was (unambiguous per-run subdirectories, bundle+coverage+PNG
together) — don't invent a new location scheme.

[↑ TOC](#toc)

## Verification {#verification}

- Confirm the footer/coverage stamp actually appears and is legible on at least 2 regenerated
  renders (one from the "stale" batch, one from the "never rendered" batch).
- Confirm the PNG-embedded metadata (Part 1b) is actually present and readable on a copy separated
  from its `coverage.json` — e.g. `python3 -c "from PIL import Image; print(Image.open('panels.png').info)"`
  or `identify -verbose` on a PNG moved to a scratch location with no sidecar file next to it.
- Confirm the stamped SHA matches `git -C autoscaling-viz rev-parse --short HEAD` at the time of the
  render (sanity check that the stamping mechanism reads the right repo, not a stale cached value).
- Spot-check that a run genuinely missing `git` context (if any exist) degrades to the fallback
  value rather than crashing.
- Report final run-by-run outcome (regenerated / skipped-and-why / already-current) in
  `session/status/autoscaling-viz.md`, per this branch's existing verification-logging convention.

[↑ TOC](#toc)
