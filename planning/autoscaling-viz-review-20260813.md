# autoscaling-viz — code review, 2026-08-13

**Status:** DRAFT
**Scope:** three commits on `autoscaling-viz` — `037106f2` (bugfix cluster), `fbecfe26` + `08927557`
(panel3-redesign + its fix round, reviewed as one unit). Excludes `cff4e4c0` (panel 6's original
cut) — superseded by an in-progress redesign (Task 3); its review trigger is stale, not reviewed
here as live work.
**Reviewer:** background review agent, this session, 2026-08-13. Verified independently — re-extracted
the flagged sample from a clean checkout of each reviewed commit, not by reading the diff alone.

> **Reading Protocol:** Read this section and the TOC, then fetch only the item you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Verdict {#verdict}](#verdict-verdict) L22:28
- [Confirmed correct {#confirmed-correct}](#confirmed-correct-confirmed-correct) L29:46
- [Finding 1 — drain-window bound (already tracked, corroborated independently) {#finding-1-drain-window}](#finding-1--drain-window-bound-already-tracked-corroborated-independently-finding-1-drain-window) L47:61
- [Finding 2 — panel 3 title text is stale {#finding-2-title-text}](#finding-2--panel-3-title-text-is-stale-finding-2-title-text) L62:71
- [Stale trigger to withdraw {#stale-trigger}](#stale-trigger-to-withdraw-stale-trigger) L72:78

## Verdict {#verdict}

**Push-ready**, with one already-known defect to route (not re-fix here) and one minor cosmetic
finding. Neither blocks a push; both are recorded for whoever picks up the next round of panel work.

[↑ TOC](#toc)

## Confirmed correct {#confirmed-correct}

- **`037106f2`** (title fallback + panel-3 legend/hatch/edge) matches
  `autoscaling-viz-bugfix-cluster-plan.md` exactly. Independently re-extracted the flagged sample
  (`dean-20260810-092644-320`'s `inference-perf-1786343242-zr01gi_1`) against this commit:
  `meta.workload`/`model`/`namespace` all populate correctly (`m-satta-dwell` /
  `unsloth/Meta-Llama-3.1-8B-Instruct` / `dhl-wva-209`), replacing the prior `?` fallbacks. Legend/
  hatch/edge fixes confirmed visually.
- **`fbecfe26` + `08927557`** (panel 1b y-axis cap + panel 3 request-domain redesign) matches
  `autoscaling-viz-panel3-redesign-plan.md`. The two regressions the planner's own re-render caught
  in the first cut — the cap silently no-op'ing on runs with no per-request trace, and the legend
  regressing to a 21-row overflow on a 15-pod run — are **genuinely fixed** in `08927557`. Verified
  from a clean extraction of code at that exact commit (isolated from the live worktree, which has
  uncommitted Task 3 work on top), re-running `extract_real_trace.py`/`render_real_trace.py` against
  the same flagged run from scratch. Output matches the planner's own verification sample.

[↑ TOC](#toc)

## Finding 1 — drain-window bound (already tracked, corroborated independently) {#finding-1-drain-window}

`pod_drain_windows()`'s backward scan in `extract_real_trace.py` has no bound tied to the replica
set's actual `desired`-transition time — it walks back through a pod's entire continuously-busy
history, which can mislabel long, fully-desired serving time as "draining." **Not a new finding**:
this is the exact mechanism Dean's own follow-up review
([`autoscaling-viz-panel-review-20260813-followup.md`](autoscaling-viz-panel-review-20260813-followup.md)
§ Item J) already root-caused from a live cell (`m-ta-staircase`, pod `r2tnh`). The reviewer
corroborated it independently, from the code, arriving at the same root cause via a different path.
Fix plan already exists ([`autoscaling-viz-drain-window-fix-plan.md`](autoscaling-viz-drain-window-fix-plan.md),
Task 4) and is deliberately on hold pending Task 3 — do not re-open or re-scope, this is confirmation
only.

[↑ TOC](#toc)

## Finding 2 — panel 3 title text is stale {#finding-2-title-text}

Minor, cosmetic. Panel 3's on-figure title string still reads "running, waiting, router-side" —
never updated to mention the new draining band or the EPP-queue rename, even though the code comment
directly above the title-setting line was updated as part of the redesign. Cheap fix, low priority;
worth folding into whichever commit next touches panel 3's rendering code (e.g. alongside Task 4 or
the visual-scheme work in Item K of the follow-up review) rather than a standalone commit.

[↑ TOC](#toc)

## Stale trigger to withdraw {#stale-trigger}

`session/handoffs/review__autoscaling-viz-ready.md` (filed for `cff4e4c0`, panel 6's now-superseded
first cut) should be archived/withdrawn rather than acted on — Task 3's redesign is in progress,
uncommitted, in the `autoscaling-viz` worktree as of this review.

[↑ TOC](#toc)
