# ev-shindin reply drafts — PR C (#1480) and PR D (#1481)

Status: DRAFT — **do NOT post.** For Dean's review/edit, then explicit per-comment confirmation
before any `gh` write. Written by planner 2026-07-29 from the locked triage design. Plans updated:
`planning/ta-model-level-demand-plan.md` (C.1/C.2 comment-only fold) and
`planning/ta-veto-liveness-plan.md` (round-2: D.1/D.2/D.3).

---

## PR D (#1481) — reply to ev-shindin

**Re: duplicated `"no-data"`/`"error"` reason strings across packages (D.1)**

> Good catch. Folding a de-dup into this PR: where the import graph allows, I'll move the
> sentinels to the lower-level (`pipeline`) package and export them so the saturation analyzer
> references one definition. If a shared constant would create an import cycle, I'll add a
> cross-package pin test instead so the two can't drift silently (a rename on one side would
> otherwise disable liveness detection with no compile error).

**Re: prune `lastGoodAnalysis` (D.2)**

> Agreed. Adding a selective prune at the per-cycle boundary — evict model keys that are no
> longer in the current active-model set, keeping the timestamps for still-active models. It's a
> targeted eviction, not a per-cycle reset: the latch is deliberately cross-cycle (a transient
> `no-data` with a recent good result must still count as live). The map is in-memory only, so
> it also clears on a controller restart.

**(Optional — mention the related detector so the reviewer sees it coming)**

> Related: I'm also adding an observability-only signal at the same liveness site — a warning
> when an analyzer has a live capacity/supply signal but has reported no demand for a full
> staleness window (typically a broken arrival query / EPP not reporting). It's log-only: it
> never sets liveness and never affects the scale-down vote.

---

## PR C (#1480) — reply to ev-shindin

**Re: with no EPP (arrival = 0), TA could scale down spuriously (C.1)**

> This is intentional and safe. With no served-rate floor, `ArrivalRate = 0 → TotalDemand = 0`,
> and zero demand only *permits* scale-down — it never forces a scale action and never drives
> scale-up. So a missing/zero arrival signal can't cause a spurious scale-up, and the
> all-live-agree gate still governs whether a scale-down actually happens. Adding a code comment
> at the demand assembly to make that explicit.

**Re: warn when `ArrivalRate == 0` but `ΣRequestRate`/KV/waiting > 0 (C.2)**

> I looked at this, but `ReplicaMetrics.RequestRate` is a request *completion/processed* rate,
> not an arrival rate — a draining engine keeps `RequestRate > 0` after arrivals have legitimately
> dropped to zero, so `ArrivalRate == 0 && ΣRequestRate > 0` is a normal ramp-down state and the
> check would false-positive constantly. The sound broken-arrival signal is temporal rather than
> instantaneous: "supply has been live but demand has never been observed for a full staleness
> window." I'm adding exactly that as an observability-only warning in the engine liveness path
> (in the liveness PR), rather than an instantaneous cross-check here. Adding a comment here
> explaining why RequestRate isn't used as a proxy.

---

## Posting checklist (for Dean)

- [ ] Approve/edit each reply above.
- [ ] Confirm the `gh` write per PR (`gh api` PATCH workaround if `gh pr comment` is needed — but
      these are review-comment replies; confirm the exact mechanism/thread with Dean).
- [ ] Decide whether the "related detector" paragraph goes on D (it references work in this PR)
      or is dropped to keep the reply tight.
