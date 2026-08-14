# Panel review, 2026-08-14 — Dean's review of the version-stamped m-satta-dwell regen

**Status:** DRAFT. Source: Dean reviewing
`benchmark/runs/dean-20260810-092644-320/results/inference-perf-1786343242-zr01gi_1/viz/panels.png`,
confirmed version-stamped at current tip (`870fff6d`) via embedded PNG metadata.

> **Reading Protocol:** Read this section and the TOC, then fetch only the item you need via
> `Read <this-file> offset:<start> limit:<end-start+1>`. Do not read the whole file up front.

## TOC {#toc}

- [Confirmed good, no action {#confirmed-good}](#confirmed-good-no-action-confirmed-good) L18:26
- [Item N — per-request data gap: NOT this scope's to schedule {#item-n-per-request-gap}](#item-n--per-request-data-gap-not-this-scopes-to-schedule-item-n-per-request-gap) L27:46
- [Item O — CONFIRMED: drain windows end ~15-16s before their matched drop, systematically {#item-o-drain-offset}](#item-o--confirmed-drain-windows-end-15-16s-before-their-matched-drop-systematically-item-o-drain-offset) L47:81
- [Item P — overlay weight too thick {#item-p-overlay-weight}](#item-p--overlay-weight-too-thick-item-p-overlay-weight) L82:93
- [Cross-references](#cross-references) L94:101

## Confirmed good, no action {#confirmed-good}

- **Panel 1b's capacity-ceiling annotations** — Dean: "good." Task 2's y-axis cap + off-chart
  replica-count labels confirmed working as intended.
- **Panel 6** — Dean: "very good." The signed replica-delta-per-analyzer redesign (Task 3) landed
  well.

[↑ TOC](#toc)

## Item N — per-request data gap: NOT this scope's to schedule {#item-n-per-request-gap}

**Corrected 2026-08-15 — scope clarified directly by Dean.** Panels 1a/1b/5 are empty on this run
because `per_request_lifecycle_metrics.json` is disabled by design (documented, settled, on the
`benchmark` side — `session/status/benchmark.md` §20.24-20.25). This item's disposition, stated
plainly by Dean: **"handling of pre-requests data... not your scope unless benchmark planner assigns
it to you."** Same for "enhancing the extraction tools" (e.g. wiring an Envoy-access-log fallback
into `extract_real_trace.py`) — **"could be your work if assigned by planner."**

**Status as of this correction:** routed to the `benchmark`-execution scope via
`session/handoffs/plan__envoy-per-request-tool-scope-and-process-gap.md`. Their response (commit
`c0dad178`) confirmed a real doc-coverage gap (a validated, working tool —
`session-notes/scratch/envoy_per_request.py` — with no Type 3/1/6 after 6 days of use) and closed it
with a new [`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md),
explicitly leaving the generalization/ownership question "asked, not yet answered." **This item is
therefore closed on this doc** — nothing further scheduled here unless/until the benchmark planner
assigns extraction-tool work to this scope. Do not re-open or re-derive.

[↑ TOC](#toc)

## Item O — CONFIRMED: drain windows end ~15-16s before their matched drop, systematically {#item-o-drain-offset}

Dean: "the drain annotations on p3 are suspect. don't seem to match the replica down signals."
**Traced directly against this exact bundle** (all 6 pods with a `drain_windows` entry, matched
against the run's actual `desired`-count drop events):

| pod | window end (rel s) | nearest `desired` drop (rel s) | offset |
|---|---|---|---|
| `2vxwj` | 689 | 704 | −15s |
| `9kb6w` | 1282 | 1297 | −15s |
| `gzvfj` | 1282 | 1297 | −15s |
| `l9s5k` | 1472 | 1487 | −15s |
| `mhrkh` | 872 | 888 | −16s |
| `njwp6` | 689 | 704 | −15s |

**Every single window ends 15-16 seconds before its matched drop — not noise, a consistent
systematic offset.** This is the same scrape-cadence mismatch the Task 4 fix's own commit message
already named (the aggregate `ready`-poll runs on a coarser cadence than the per-pod scrape), but
the fix's own verification apparently didn't catch that the offset, while now correctly *bounded*,
is still consistently present in the *displayed* window's end — worth a closer look at whether the
window should be extended to the drop event's own timestamp (bridging the scrape gap) rather than
stopping at the pod's last observed sample, or whether this offset is expected/acceptable and just
needs documenting.

**Also observed, not yet resolved:** two of this run's scale-down events remove more replicas than
have a matched drain window — the `desired: 10→7` drop (t≈704, removes 3) has only 2 matched pods;
the `desired: 10→6` drop (t≈1297, removes 4) has only 2 matched pods. Checked whether other pods
disappear near those same instants and aren't picked up: **no** — only the 2 matched pods actually
have a last-sample near either drop in this bundle. So this may not be a bug (those "missing"
replicas may have ended their life some other way entirely, or the desired-count arithmetic doesn't
map 1:1 to individual pod disappearances) — flagging as an open question for the coder's own trace,
not a confirmed defect the way the offset above is.

[↑ TOC](#toc)

## Item P — overlay weight too thick {#item-p-overlay-weight}

Dean: "both drain and waiting overlays (dots and dashes) are too thick." Confirms and reinforces
the Item K finding already captured in
[`autoscaling-viz-panel3-visual-scheme-plan.md`](autoscaling-viz-panel3-visual-scheme-plan.md)
(Task 8, currently queued behind Task 7) — no new spec needed, this is corroborating evidence for
work already scoped.

[↑ TOC](#toc)

---

## Cross-references

- Parent epic: [`autoscaling-viz-followon-plan.md`](autoscaling-viz-followon-plan.md)
- Task 4 spec (drain-window fix): [`autoscaling-viz-drain-window-fix-plan.md`](autoscaling-viz-drain-window-fix-plan.md)
- Task 8 spec (visual scheme, corroborated by Item P): [`autoscaling-viz-panel3-visual-scheme-plan.md`](autoscaling-viz-panel3-visual-scheme-plan.md)
- Sample reviewed: `benchmark/runs/dean-20260810-092644-320/results/inference-perf-1786343242-zr01gi_1/viz/panels.png`

[↑ TOC](#toc)
