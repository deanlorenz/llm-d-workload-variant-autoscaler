# TA on pokprod — Open Scenarios (Type 3, live)

**Status:** LIVE — this is the actively-changing surface, kept separate from the settled execution plan
on purpose. **Scope:** workload-scenario design questions, the dwell mechanism, and the checklist of
what's decided vs. still needs Dean.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md) (Type 1) ·
[`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md) (Type 3, settled phases) ·
[`ta-pokprod-history.md`](ta-pokprod-history.md) (decision ledger — `[[D-nn]]` fetchable by
`grep -n '^## D-nn'`) · [`ta-pokprod-campaign-report.md`](ta-pokprod-campaign-report.md) (all
results/findings across every run to date, superseding the two prior results docs) ·
[`autoscaling-viz-design.md`](autoscaling-viz-design.md) (Type 1, viz-side capacity/estimation model —
owns the theory/simulation legs referenced below).

---

## Priority triage, 2026-08-16 (Dean's own ordering — not acted on yet, tracked only)

Dean reviewed the full open-items list and set explicit priority/handling per item. **Nothing
below is executed** — this is a tracking pass so nothing gets lost, per his direct request
("track it all, we don't want to lose it... do not act yet, we should prioritize").

| # | Item | Dean's call |
|---|---|---|
| 1 | Gateway-log harvest doesn't read the follower's PVC copy ([[D-63]]) | **NEEDS FIX — discuss first.** Wants a discussion to understand the right fix before anything is written, not a unilateral pick among the 3 options already listed. |
| 2 | `run_cell.sh`'s failure path can clobber a different run's config | Understood, **revisit later** — not now. |
| 3 | The p4 run's 4-pod combined-gateway-log shape (both the original campaign's `dean-20260813-130251-004` and any future p4 cells) | Coder already ran with parallelism successfully — this is purely an **extraction-tooling gap**: `estimate_per_request.py` needs to handle the 4-logs-combined-into-one case. **Not urgent, but a real Type 3 + fix are needed** eventually. |
| 4 | Truncated old runs (`dean-20260810-105211-685` and any future truncation) | **Merged with the old item 5 — same case.** Old truncated runs are unrecoverable; **abandon/archive them**, don't chase. Going forward, **new runs should not truncate, and if one does, we should notice** — an active detection gap, not just an acceptance policy. |
| 6 | Controller-restart hold-at-current-replicas policy question ([[D-40]]/[[D-46]]) | Dean doesn't remember where this is documented — **needs to look it up before he can address it.** Pointer: `ta-pokprod-history.md` D-40/D-46, and the checklist row below. |
| 7 | Doc-coverage cleanup classification, 19 scratch scripts ([[D-54]]/[[D-56]]) — **merged with old item 8, same thing** | **Still parked, not a priority.** No classification decision made. |
| 9 | Coder reply-routing pattern (replies landing on the wrong sibling scope) | ✅ **ROOT CAUSE FOUND 2026-08-17** — the trigger format has no `from:` field at all (handoffs do, triggers don't), so a reply falls back to `refs:`-chain provenance, which diverges from "who actually sent this" exactly when a design doc is re-triggered by a different scope. Forwarded as a real format gap, not a habit fix, to the protocol-design owner. [[D-73]] |
| 10 | §5.5-item-4 runbook fold-vs-stub call | Understood — **wait until Stage A's results are confirmed as expected** before touching the runbook question. |
| 11 | Handoff-file git-tracking inconsistency (bare `mv`, not `git mv`, 439 files accidentally tracked) — found 2026-08-16 while investigating an unrelated broad commit | ✅ **CLOSED on this side** — not this scope's to fix; handed off to the handoff-protocol design owner with Dean's ruling attached (pointers only, no git history, sync__ carries the real record). Picked up, consumed, no reply needed. [[D-72]] |
| 12 | **Stage B — the full clean-recapture campaign** | ⬜ **OPEN, NOT LAUNCHED.** Scoped in [`ta-pokprod-clean-recapture-plan.md`](ta-pokprod-clean-recapture-plan.md) § Stage B (all 6 workload templates × each workload's own config set). Stage A closed 7/7 clean 2026-08-16 and GPUs are freed, so nothing technical blocks it — it needs **Dean's explicit run approval** like any cluster run. *Row added 2026-08-17: the two `/s-state-park` reports below both list "12/Stage B" among the still-open items, but the table itself never had a row 12 — a real tracking gap, now closed.* |
| 13 | **Commit the 83 uncommitted viz-refresh entries on the `benchmark` worktree** | ⬜ **OPEN, this scope's to do** — handed over by the autoscaling-viz scope, explicitly non-blocking and not time-sensitive. 57 modified + 10 new `viz/` dirs + 16 `good-panels.png` symlinks, at the canonical gitignore-allowlisted location. The coder stood down with a clean tree at `590e8b91`, so no coder session will pick this up. [[D-75]] |
| 14 | **`reset_run.py`'s existence-check-not-completeness-check defect** | ⬜ **OPEN, LIVE, UNFIXED** — `hack/benchmark/reset_run.py:270-272` still `rm -rf`s a PVC directory on a name match with no size/count comparison; re-verified in source 2026-08-17. Procedural mitigation only (run `verify_pvc_vs_host.py` first). Once caught all four host copies incomplete; `--apply` would have made the loss permanent. [[D-74]] |

**Not re-numbered from the original 11-item scan** so the numbering stays stable across
conversations — 5 and 8 are folded into 4 and 7 respectively, not deleted, so a future reader
tracing "item 5" back finds the merge note rather than a gap. Items 12–14 were appended 2026-08-17
(12 recovered from the park reports, 13–14 surfaced by the state-file cleanup pass) — appended, never
inserted, for the same numbering-stability reason.

---

## Checklist — what still needs Dean, at a glance

| Item | Status | Ref |
|---|---|---|
| Confirm the three §1 scenario asks | ✅ **CLOSED 2026-08-12** | [[D-23]] |
| §2 operating-point fork, (a) vs (b) | ✅ **DECIDED 2026-08-11 — (a)** | [[D-19]] |
| T9 gateway log-follower | ✅ **DONE 2026-08-12 — wired into `benchmark-run`, not yet live-verified** | [[D-22]], [[D-27]] |
| §5.5-item-4 fold-vs-stub call for the pokprod runbook | ⬜ **OPEN, Dean's** | execution plan §7.1 T6 |
| Dwell forecast Type-1 scoping | ⬜ **OPEN, Dean's — explicitly deferred to him** | [[D-21]] |
| §2c: can one context map to multiple namespaces? | ✅ **DECIDED 2026-08-13 — no; enforce context-matches-`.env`-namespace, fail closed** | [[D-44]] |
| Approve the extractor's log-format-drift fix (substantial single-file edit) | ✅ **ALREADY FIXED 2026-08-10, `add1d400`, predates this doc's OPEN marker — stale checklist row, not a live gap** | [[D-29]] §3.2, [[D-46]] |
| Route the bucket-keyed `prc` collapse fix (§3.1) to Dean or decide who owns it | ✅ **DECIDED 2026-08-13 — lower priority, WVA issue later, not now; workaround = shift tested workload's output length off the 500-token bucket edge** | [[D-28]] §3.1 |
| `postprocess.py`'s missing-field bug | ✅ **FIXED 2026-08-12 — supports both harness formats, verified against a real run** | [[D-39]] |
| Controller-restart stuck-at-10-replicas incident (`rc=0`, no scale-down) | ✅ **MECHANISM FOUND 2026-08-13 (background, read-only) — `applySaturationDecisions` deliberately holds at current replicas on no-fresh-decision, by design (avoids scale-to-zero on a transient uninformative cycle); is "hold" the right policy for a *sustained* window? — that's Dean's open question now, not "is it a bug"** | [[D-40]], [[D-46]] |
| inference-perf OOM — root cause found; fix DECIDED and **VALIDATED 2026-08-13** by a real 4-pod run, 0 errors | ✅ **DONE** | [[D-41]], [[D-42]], [[D-43]] |
| Controlled-run / timestamped-replay + agentic-replay capability — longer-term, not "benchmark generates load itself" | 🕐 **DEFERRED 2026-08-13 — real community work exists to catch up on eventually; not now, focus stays on the tools we have** | [[D-45]] |
| Viz output missing/stale for runs since 2026-08-10 | ✅ **RESOLVED 2026-08-14 — 18 runs regenerated with a version stamp, pulled up to git-trackable location** | [[D-43]], [[D-50]], [[D-52]], [`benchmark/docs/benchmark-reports/ta-pokprod-campaign-report.md`](../../benchmark/docs/benchmark-reports/ta-pokprod-campaign-report.md) |
| Doc-coverage gap: scratch tools never promoted, undocumented — corrected 2026-08-15 from 5 to 17 (a full directory listing found 12 more D-51's own source list missed) | ✅ **DRAFT CLEANUP PLAN REWRITTEN 2026-08-15 — recommendation (10 DEFERRED-as-pattern, 7 promote-as-is), Dean's classification call not yet made** | [[D-51]], [[D-56]], [`pokprod-scratch-tools-doc-coverage-cleanup-plan.md`](pokprod-scratch-tools-doc-coverage-cleanup-plan.md) |
| Move `ta-pokprod-campaign-report.md` to `benchmark/docs/benchmark-reports/` | ✅ **DONE 2026-08-15 — relocated, links fixed for same-worktree resolution, stub left at old path** | [[D-53]] |
| Per-request TTFT/output-size estimation for viz panels 1a/1b — 1 example run | 🔵 **boundary-spike bug FIXED; stage-4 rate anomaly still open; stage-0 truncation root-caused (D-63), one-off re-harvest in progress; viz asked to verify through their own toolchain** | [[D-55]], [[D-57]], [[D-59]], [[D-60]], [[D-62]], [[D-63]], [[D-64]], [`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md) |
| Per-request extraction batch for the other 14 run-leaves missing per-request data | 🔵 **IN PROGRESS 2026-08-16 — handed to coder** | [[D-64]] |
| Gateway-log harvest never reads the follower's durable PVC copy — root-caused, needs a design call on 3 options | ⬜ **OPEN, Dean's, not decided** | [[D-63]] |
| vLLM `--enable-per-request-metrics` flag on the pinned v0.20.2 image | ✅ **ANSWERED 2026-08-16 — definitive NO, flag not recognized, rejected at CLI parse time** | [[D-58]], [[D-61]] |
| Any cluster run | ⬜ **always, per-run** | standing rule |

**Nothing else in this doc is waiting on Dean right now.** The dwell mechanism itself is being worked
in a dedicated session — see § 3 below — not blocked on anything here.

---

## 1. Scenario gaps — three asks, all confirmed

Source: the ladder-run cross-check, itself the product of an independent `autoscaling-viz` review.
**Status: DECIDED, all three — closed 2026-08-12.** [[D-23]]

**1.1 — A mid-band dwell stage.** Hold an offered rate that parks KV utilization inside the no-action
band for ≥3 min. No run had ever dwelt there as of the original ask; every run to date was either
sub-band or pinned above it by a replica cap, not by load. **Superseded mechanism, unchanged goal** —
see §2 below: raising the offered rate under a tracking controller doesn't reliably move steady-state
KV, so this is an analyzer-configuration question, not a workload one. [[D-18]]

**The exact no-action band, derived not guessed.** Not a separate calculation — it's the direct
definition of `saturation_v2`'s two universal thresholds
(`internal/config/saturation_scaling.go:54-64`): scale-up fires once `demand/supply > 0.85`,
scale-down once `demand/supply < 0.70`. **The band is exactly `[0.70, 0.85]`** — narrower than an
earlier `[0.3, 0.85]` guess. 0.67 (the original ladder run's reading) sits just below 0.70 — outside the
band on the low side, not inside it. [[D-20]]

**Not yet derived:** TA's own no-action band, and the TA+SAT combined band, are not necessarily this
same interval — deriving them is a prerequisite for testing those configurations against §2's decision.

**1.2 — A short-output leg** (e.g. 2000 in / 100 out), to probe the ITL lower knee. The current
"long-input" shapes are decode-dominated, not prefill-heavy — prefill-heavy needs short outputs, not
merely long inputs. Corroborating measurement: `itl ~ running` alone reaches r² 0.93–0.94 below the
band; adding a prefill term buys +0.001 there vs. +0.236 in-band. Same mechanism defect as §1.1 applies
here, more sharply — a knee is a property of load *per replica*, and the autoscaler's job is to keep
load per replica off it. Implemented (`ta_prefill_knee.yaml.in`) but its sharp instrument is a fixed
replica count with autoscaling off, a scenario decision not yet made.

**1.3 — Let the run outlive the cooldown.** ≥300 s of collection after load stops, or scale-down never
lands inside the measurement window. **Agreed with an addition:** any scenario starting above 0
replicas needs its analysis window to start after boot lag clears, matching the simulation convention
already used elsewhere — **not yet implemented in the extractor**, which currently analyzes from t=0
regardless of starting replica count.

**Measurement constraint, applies to all three.** A routing oscillation with a 6–11 s period is aliased
away by every gauge-derived series at the ~15.7 s scrape cadence (Nyquist ~31 s) — it was visible at all
only because the gateway access log records `UPSTREAM_HOST`. A finer scrape rate does not fix this and
neither does a per-pod gauge; the per-request trace is a requirement, not a nice-to-have.

**Two corrections to propagate wherever cited:** the decision rule is `rc = demand/0.85 − supply`, then
`curr + ceil(rc/prc)` applied to the residual — not `ceil(demand/prc)`. And `bytes_sent` is not a valid
per-request output-token weight (median calibrates, dispersion doesn't); `x-envoy-upstream-service-time`
is not TTFT (flat while harness TTFT climbs).

**Retention exception.** The multi-GB per-replica files go on cleanup; `metrics/raw/` stays (12–35
MB/run, the only time-resolved source of KV/running/waiting/ITL/preemption).

---

## 2. The dwell operating point — decided, generalized

**Decision: (a).** Saturation alone, uncapped. Generalizes to *any* analyzer combination under test —
not a SAT-specific answer. [[D-19]]

The goal itself was corrected first: not "manufacture a dwell so a slope is fittable," but "run long
enough, under whichever analyzer combination is under test, that eventual steady-state arrival is
observable at all." Transition time is a secondary measurement, not the target. [[D-18]]

| Option | Configuration | What it measures |
|---|---|---|
| **(a) — decided** | Saturation alone, uncapped (TA off, `maxReplicas` at 10) | SAT's own right-sizing, isolated from the combined optimizer |
| (b) — instrument only, not a default | A deliberate replica cap | the cap itself — every latency number at a binding cap describes the cap, not the controller |

**The sawtooth already ran — not a fallback still to try.** The staged quantization-sawtooth workload
(two 360 s rungs, 20 and 26 RPS) executed in the 2026-08-10 campaign as all three `*-dwell` cells.
Neither sat-voting cell reached steady state — both hit the replica cap of 10 twice (a limit cycle,
analyzer-independent). This does **not** confirm or refute (a) — it shows the runs were too short to
test steady-state arrival at all *and* (§3.1 below) that a limit-cycling system has no well-defined
mean operating point regardless of duration — both problems, not one, which is exactly what the dwell
deep-dive below is now investigating.

---

## 3. The dwell limit cycle — mechanism found, forecast gap open

**A dedicated deep-dive session answered "why does the limit cycle happen."** Full trace:
[`session/status/dwell-deep-dive.md`](../session/status/dwell-deep-dive.md); folded into
[`ta-pokprod-campaign-20260810-results.md`](ta-pokprod-campaign-20260810-results.md) Finding 2. [[D-21]]

- A single anomalous `P1-obs` sample triggers the excursion — real, by-design (unclamped demand/supply
  ratio), not a units bug.
- The dominant lag is created→ready, not ordered→created — physical (model load + GPU scheduling
  contention under concurrent boots), not a control-loop defect. The controller retreats from its own
  peak order before the last replica it asked for ever becomes ready.
- `TotalAnticipatedSupply` is confirmed correctly implemented — no double-booking.

**The actual gap, new Type-1 design surface, not a bug fix:** the demand side has no forecast that
already-ordered, already-created (not-yet-ready) replicas will relieve the queue once ready — so demand
is sized off an instantaneous snapshot that's already about to shrink. Shared between saturation and
TA. **Whether/how to scope this is explicitly Dean's call**, tracked at
`session/handoffs/plan__dwell-limit-cycle-forecast-todo.md.WIP` — not decided here.

**PVC ceiling, a deliberate omission:** a rung above 26 RPS doesn't fit the 20Gi results PVC beside the
two dwell rungs (~5.1 GB more) — the natural follow-up only if a longer dwell run still reads outside
`[0.70, 0.85]`.

### 3.1 Two earlier, distinct mechanisms — found on the original 2026-08-08 dwell run, not superseded

**A separate contributing mechanism the deep-dive (§3 above) never addressed: bucket-keyed capacity
history.** [[D-28]] `prc` collapses because saturation's capacity history keys on a *discretized
bucket* of average output length (edges at 100/500 tokens), and the workload's mean output (512, sd
20) sits 12 tokens above the 500-token edge — ordinary sampling noise flips the bucket key mid-run,
swapping in a history from a different workload. Status: a strong, code-located hypothesis, not
confirmed from logs (the analyzer never emits `outputBucket`/`historyKey`). **Not yet fixed or
disproven.** A second, compounding finding from the same run: capacity history is contaminated across
runs with no time-based invalidation — this is the origin of the "restart the controller before each
run" protocol already in §5 below, not a new item.

**Real measurement, not inference, on why the mean is the wrong statistic for a limit cycle.**
[[D-29]] Per-rung KV was measured directly from vLLM scrapes on the original dwell run: rung A
(20 RPS) mean kv **0.127**, rung B (26 RPS) mean kv **0.248** — neither near 0.67, neither in-band by a
literal mean-based reading. But the distribution is **bimodal**, not unimodal (rung B: p90 0.994, max
1.000, despite a mean of 0.248) — the run traverses the full 1↔10 replica range *inside* each rung at
constant offered rate. **No single number describes an operating point for a system that is
limit-cycling — this holds regardless of run duration**, not only because a run is too short. Any
re-run's readout should report the distribution (p50/p90/max), not the mean, and the fix for §3's
oscillation is a precondition for a mean-based comparison to mean anything at all, not merely a
nice-to-have refinement.

**A genuine accidental dwell was observed on that run, and it independently corroborates §3's
readiness-lag finding — a full week before the dedicated deep-dive confirmed it with a code trace.**
The 14 RPS entry rung parked kv at mean 0.623, p50 0.990 — because replica count was lagging the
offered load (1→4 while 14 RPS was already arriving), not because of the rate itself. Consequence for
§2's (a)/(b): (b) works because a cap *is* enforced lag; (a) only works if SAT's watermarks actually
bind, and on this run they did not — SAT and throughput contradicted each other outright at one tick,
and the optimizer resolved to no-change. Not a vote against the (a) decision (still §2's answer), but
a real reason its success on any given run isn't guaranteed.

### 3.2 Two operational items missing from the cold-resume checklist — added here, not yet in §5

- **STALE, corrected 2026-08-13 — the extractor's log-format-drift bug was already fixed 2026-08-10
  (`add1d400`), before this section's "not fixed, needs approval" line was ever accurate.** [[D-29]],
  [[D-46]] Original finding, for the record: `dump_wva_target_timeseries.py`'s pattern matched a log
  line the controller no longer emits, and the existing anti-clobber guard only fired on an *empty*
  result, not a non-empty-but-null one — so a drifted parse could overwrite good data while looking
  healthy. **Fixed:** the current script accepts the controller's actual `analyzer-result` line
  (`ANALYZER_RESULT_PAT`) with a fallback pattern for older builds, tracks a separate `hydrated` count
  distinct from raw sample count, refuses to overwrite an existing hydrated file with an unhydrated
  new parse, and prints a loud `WARNING:` (not a silent success line) when a parse drifts again.
  Verified directly against the current script source, not inferred from the commit message alone.
- **A GPU-pause trap, not yet a precondition anywhere.** Pausing a ScaledObject to release its GPU
  (`autoscaling.keda.sh/paused-replicas="0"`) holds it at 0 **indefinitely** — scaling the Deployment
  directly does not override the pause. A run launched without first un-pausing
  (`autoscaling.keda.sh/paused-replicas-`, then confirm `PAUSED` reads `<none>`) produces a flat
  0-replica trace that reads as a legitimate no-scaling result. **Added as precondition 5 in §5 below.**

---

## 4. Workload coverage matrix + theory/simulation/real baseline

**Two asks, Dean.** [[D-13]] *(cross-referenced from the campaign doc, not a standalone D-entry —
folded here as it's scenario-design surface)*

**4.1 — A coverage matrix. ✅ BUILT 2026-08-13** —
[`ta-pokprod-workload-coverage.md`](ta-pokprod-workload-coverage.md) [[D-47]]. All 6 canonical
`ta_*.yaml.in` templates tabled with purpose, shape, run count, and outcome — every template has
run at least once.

**4.2 — A three-artifact baseline, not just a table.** *"Theory based on simulation + viz, simulation
based on actual workload generated + viz — a synthetic baseline before we actually benchmark."* Three
artifacts per workload, in order: (1) a theoretical prediction from the analytical model alone, rendered
through the viz panel set on synthetic input; (2) a simulation driven by the actual generated workload
(not the analytical idealization), same panel set, still before touching a cluster; (3) the real
benchmark result, compared against both rather than read cold. Would likely have flagged the sawtooth
cells' actual problem — not merely "too short," but that a limit-cycling system has no well-defined
mean operating point at all (§3.1) — before spending cluster time on them.

**Ownership split, resolved 2026-08-13.** [[D-47]] 4.1 (the coverage matrix — what benchmark *runs*)
built here, in benchmark-execution scope, as a Type 3 rather than needing a new benchmark Type 1.
4.2 (theory/simulation legs — what viz *computes*) remains viz-panels-planner's, unbuilt, tracked
in that scope's own docs.

---

## 5. Cold-resume state for the staged dwell run

**Staged and unlaunched.** No cluster action has been taken and no run is proposed. Standing rule
holds: no run without Dean's explicit approval.

- **Config staged, not launched:** the dwell and prefill-knee workload files, local-only on `benchmark`.
- **Precondition 1–4:** reclaim the results PVC to ≥14 GB with `verify_pvc_vs_host.py` gating it;
  confirm the 96Gi harness pod schedules; set the 5-GPU footprint flag; run `post_run_analyze.sh`
  immediately after. **Caveat, [[D-29]]:** promptness alone is not sufficient — the extractor
  (`dump_wva_target_timeseries.py`) can report a plausible-looking snapshot count while every field is
  silently unpopulated, due to log-format drift, not rotation. Verify the *populated* output, not just
  that the script ran without error, before trusting a run's `metrics/processed/wva_*`.
- **Precondition 5 (added, [[D-29]]): un-pause the ScaledObject before launching.** If it was paused
  to release GPUs between runs, KEDA holds it at 0 indefinitely regardless of Deployment edits — a run
  launched without un-pausing first (`autoscaling.keda.sh/paused-replicas-`, confirm `PAUSED` reads
  `<none>`) produces a flat 0-replica trace that silently reads as a legitimate no-scaling result.
- **Precondition 6 (added, [[D-31]]): save the raw controller log during the run, not just parse it
  live.** `kubectl logs ... > controller-<run-id>.log` running for the duration, so the log can be
  re-parsed offline (`--log-file <log> --no-window`) if the live parse window has passed or the
  live-window promptness precondition above wasn't met in time. A saved log survives both rotation and
  the [[D-29]] drift failure mode; a fast live parse survives only rotation. Part of the ladder run's
  missing `metrics/processed/wva_*` was originally attributed to rotation and may in fact have been
  this drift instead.
- **Restart the controller before each run** — capacity history is bucket-keyed and was found
  contaminated across runs. Adopted protocol, not a suggestion.
- **GPU state:** the ladder run's GPUs are released; one GPU remains held by the decode replica's
  `minReplicas=1` steady state — separate open question, coder-tracked.
- **T9 is DONE** — the gateway log-follower is wired into `benchmark-run` automatically (commit
  `3ab8128a`, execution plan §7.1 T9, [[D-27]]). Structurally verified, not yet exercised live — the
  dwell run itself will be its first real exercise.

**Next steps, in order:**
1. Coder satisfies the six preconditions above; restarts the controller.
2. Dean approves the run. Coder runs it, then `post_run_analyze.sh` immediately.
3. Dwell deep-dive session's own findings (§3 above) determine whether a longer run is the next
   experiment, or whether the forecast-gap work supersedes running more dwell attempts.


---

**Process-report history.** Two verbose `/s-state-park` source reports (2026-08-16/17) that used to
sit here were folded into [[D-77]] on 2026-08-17 — their substance was already in the ledger (D-72,
D-73), and the one fact they held uniquely (the sole spawned subagent, id `a8351539ecd1d9127`,
completed, findings in [[D-57]]) is preserved there. Park reports belong in a status file, not in a
live scenario doc; this scope now has one at
[`session/status/planner-pokprod-benchmark.md`](../session/status/planner-pokprod-benchmark.md).
