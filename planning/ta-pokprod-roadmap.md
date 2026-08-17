# TA on pokprod — Roadmap (Type 2)

**Status:** LIVE, created 2026-08-15 — a real structural gap, not filled until now. The mission has
run since 2026-07-30 with one Type 1 (architecture) and several Type 3s (execution history, live
scenarios, tool docs, results) but no mission-level roadmap tracking alternatives considered,
decisions made, and what's active/next at a glance. This doc is that missing layer — it doesn't
restate Type-3 detail or the ledger's 55 decisions, it points into them.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md)
(Type 1, durable contracts) · [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md)
(Type 3, settled phased history) · [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md)
(Type 3, live checklist) · [`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger,
`grep -n '^## D-nn'`).

---

## Mission phases, at a glance

| Phase | What | Status |
|---|---|---|
| 0 | Preserve legacy TA3 harness work, archive, fresh `benchmark` branch | ✅ DONE (2026-07-29) |
| 1 | Methodology pivot to controlled shared-cluster setup | ✅ DONE (2026-07-30) |
| 2 | Harness build, fork-patch presence-gates | ✅ DONE |
| 3 | Namespace standup (`dhl-wva-209`) | ✅ DONE |
| 4 | Live cluster runs — 2026-08-10 7-cell campaign | ✅ DONE |
| 4b | Rerun/gap-fill campaign (calibration-probe, prefill-knee, dwell reruns) | ✅ DONE — coverage matrix closed 2026-08-14 |
| 5 | Results tooling — extractor/render toolchain, results-tree, campaign report | ✅ DONE — report relocated to `benchmark/docs/benchmark-reports/` 2026-08-15 |
| 6 | Deep-dive investigations (dwell limit cycle, OOM root cause, controller-restart policy) | 🔵 ACTIVE — mechanisms found, several open design questions deliberately deferred |
| 7 | Doc-coverage cleanup (undocumented scratch tools) | 🔵 ACTIVE — draft plan written, Dean's classification call pending |
| 8 | Per-request data recovery for viz (panels 1a/1b) | 🆕 NEW 2026-08-15 — this roadmap entry, see below |
| 9 | Clean recapture campaign — warmup + log-capture fix + exploratory instrumentation | ✅ Stage A COMPLETE 2026-08-16, 7/7 cells clean, GPUs freed — Stage B (full campaign) not yet launched — [`ta-pokprod-clean-recapture-plan.md`](ta-pokprod-clean-recapture-plan.md) |

Full execution detail for phases 0-5: [`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md).

## Active threads

**Dwell limit cycle.** Mechanism found (D-21): `P1-obs` anomalous sample + created→ready replica
lag, not a control-loop defect. Real gap identified: no forecast that already-ordered/created
replicas will relieve the queue (D-45 §2) — shared between saturation and TA. **Deliberately
deferred by Dean** — needs a proper Type 1 (or Type-1 family) for TA covering theory/goals/
algorithms first, then a Type 2 breaking it into scoped tasks, before this specific mechanism gets
its own Type 1 slice. Not started.

**Doc-coverage cleanup.** D-51 found the gap real; **corrected 2026-08-15 (D-56) from 5 to 17
tools** — a full directory listing of `session-notes/scratch/` (19 scripts total) found 12 D-51's
own source list missed. `envoy_per_request.py`/`serving_replicas.py` have a retroactive Type 3
([`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md)); the other
17 have a rewritten draft classification (10 DEFERRED-as-pattern, 7 promote-as-is)
([`pokprod-scratch-tools-doc-coverage-cleanup-plan.md`](pokprod-scratch-tools-doc-coverage-cleanup-plan.md)).
Dean's classification call not yet made on either.

**Per-request data extraction/estimation (2026-08-15; BUILT 2026-08-16).** Not "the viz work" — this
scope's own task of getting the right per-request data out of (or estimated from) what a run actually
produces, prompted by viz-panels-planner surfacing panels 1a/1b's gap but scoped and owned here.
Correction, same day: the goal is extracting the right data, not preserving any particular
existing tool — consolidate what's reusable from the tools already written (envoy/EPP-log
parsing, histogram-bucket estimation per D-55, the ladder-run analysis scripts) into one coherent
design, broader than any single log source. **Don't delete old work** — every existing scratch
tool stays on disk; this consolidates by borrowing techniques into a clean design, not by
replacing files. Design + build live in
[`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md).
**Status: built and generalized** — estimation tool written, a real boundary-spike bug found and
fixed ([[D-62]]), one-off re-harvest plus batch extraction across 13 leaves done ([[D-64]],
[[D-66]]), now covering 18/21 run-leaves. Viz's own consumption is tracked on viz's roadmap, not
here. **Still open in this scope:** the stage-4 rate anomaly, the p4 4-pod combined-log extraction
gap (triage item 3), and `dean-20260810-105211-685`'s obtainable-elsewhere re-estimation ([[D-75]]).

**Controller-restart hold-at-current-replicas policy (D-46).** Mechanism found (deliberate
by-design hold, not a bug) — read-only source trace. Open question is a policy call ("is 'hold'
right for a *sustained* window"), Dean's, not urgent.

## Alternatives considered and rejected (worth keeping visible)

- **Direct load generation instead of inference-perf** (D-41) — rejected, explicitly: broader
  scope than the OOM fix needed, and a credibility/trust issue (using our own tool to showcase our
  own work is suspect), not just technical.
- **The p4/parallelism variant as the default OOM workaround** (D-42, reaffirmed twice at D-50) —
  rejected as a silent default; an unmodified retry is tried first every time an OOM recurs, only
  escalating to p4 if that fails, so the two aren't interchangeable defaults.
- **Gitignore-pattern widening vs. pull-up-and-commit** for the viz-output-nesting gap (D-52) —
  pull-up chosen, matching existing precedent, to keep one canonical tracked location rather than
  two.

## What's next

**Nothing is in flight and no session is standing by.** The mission is fully resumable from this
doc plus [`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) § Priority triage. The
per-request extraction design that used to be named here as "next" was **built 2026-08-16** — see
the Active-threads entry above; this pointer was stale against the ledger and is corrected.

Live, in Dean's own 2026-08-16 priority order (§ Priority triage owns the detail — do not duplicate
it here):

1. **Gateway-log harvest doesn't read the follower's PVC copy** ([[D-63]]) — needs a **discussion
   with Dean first**, explicitly not a unilateral pick among the 3 known options.
2. **p4 4-pod combined-gateway-log extraction gap** — a real Type 3 + fix, not urgent.
3. **Truncated-run detection going forward** — old truncated runs are abandoned by decision; the
   open gap is *noticing* a new truncation, not accepting old ones.
4. **Controller-restart hold-policy question** ([[D-40]]/[[D-46]]) — Dean's; pointer is those two
   ledger entries plus the checklist row.
5. **Doc-coverage cleanup**, 19 scratch scripts ([[D-54]]/[[D-56]]) — parked, no classification call.
6. **Runbook fold-vs-stub call** — Dean said wait until Stage A's results were confirmed; Stage A is
   now complete, so this is unblocked and may be ready to revisit.
7. **Stage B** (full clean-recapture campaign) — scoped in
   [`ta-pokprod-clean-recapture-plan.md`](ta-pokprod-clean-recapture-plan.md), **not launched**; any
   run needs Dean's explicit approval.

**Owed by this scope, not blocking anything:** commit the 83 uncommitted viz-refresh entries on the
`benchmark` worktree ([[D-75]]), and decide whether to re-estimate
`dean-20260810-105211-685` from its 54.5 MB raw Envoy log.
