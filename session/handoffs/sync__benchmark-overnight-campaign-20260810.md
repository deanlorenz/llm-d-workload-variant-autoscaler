from: benchmark
to: sync
session: benchmark overnight campaign 2026-08-10

## What changed

Ten local commits on `benchmark`, all DCO-signed. **Cluster was used with Dean's explicit
approval** (autonomous, overnight, including the un-pause he authorised); **GPUs freed at the end**
per his instruction.

Guard tooling (`env_guard.py`, `env_wizard.py`, `apply_images.py` + Makefile wiring into the 10
destructive targets), the 3×2 scenario matrix + baseline cell, `hack/benchmark/campaign/` drivers,
three harness-blocker fixes, and the earlier extractor fix / own-guide / state-hygiene work from §19.

## Refs

- `plans/session/status/benchmark.md` **§20** — the live state section (§18 = dwell findings, §19 =
  tooling round). Authoritative copy, saved this session.
- `plans/session/handoffs/plan__benchmark-overnight-campaign.md` — the planner-side items.
- `plans/session/handoffs/plan__benchmark-env-guard-design.md` — the settled guard design.

## Update CURRENT.md — benchmark entry

**2026-08-10 — pokprod benchmark: guard tooling + scenario matrix; autoscaling confirmed on the PR-2
image.** *WIP.* Built and wired the env-guard contract Dean specified: a run must be described by a
**named** `X.env` carrying `KUBE_CONTEXT`, verified against the live context, guarding the **10
destructive** targets only (read-only targets deliberately ungated), with `UNSAFE=confirm|once|silent`
as a first-class escape hatch and `make benchmark-init` running a wizard when no env file exists.
`benchmark-apply-images` closes a real gap — the image pin previously reached the cluster **only** via
standup, so an A/B across controller images had no clean deployment path; **verified working**, it
rolled the controller to the PR-2 image and re-observed the running pod. **Autoscaling confirmed
end-to-end on `ta-0.9-anchor-pr2-20260809`:** the validation cell generated load and the controller
scaled **1 → 2 → 3** replicas.

**Three previously-unknown harness blockers found and fixed**, each of which blocked *all* load
generation: (a) `BENCHMARK_WORKLOAD` names an **upstream-catalog** profile fetched over the network and
is **not** how to select one of ours — the scenario's `harness.experimentProfile` was hardcoded, so a
per-cell load shape was not expressible; now driven by a new `BENCHMARK_PROFILE`; (b) the system
`python3` lacks **PyYAML** (the benchmark venv has it) and three helpers were invoked as bare
`python3`; (c) `experimentProfile` **cannot** be a substitution token, because the workload sync
validates it from the *source* scenario before substitution runs.

⚠️ **Carry verbatim:** (1) **Do NOT read the `m-ta-*` cell names as a finding.** They are *configured*
throughput-only per Dean's instruction (*"PR-2 should fix it… do not verify, just test as is"*);
whether the engine actually stops prepending the saturation result is what the runs test. Per-analyzer
`analyzer-result` counts from each cell's saved controller log are the evidence. (2) **A paused
ScaledObject yields a flat replica trace that reads as a legitimate no-scaling result** — whatever
pauses it must un-pause it. (3) **Restart the controller between cells**; in-memory capacity history
otherwise makes run N a function of run N-1's load. (4) `session-notes/local/` is **gitignored** —
anything there is not preserved.

## PR Status

No change — `benchmark` has no PR and is not headed upstream. Note the arm/matrix `.env` files carry
headers marking them **private to this branch**: `hack/benchmark/` *is* tracked upstream and `main`
tracks no `.env` at all.

## Blocked on

Unchanged and untouched by this session: Dean's §7.6 (a)/(b) answer, the gateway access-log follower
(T9), the coder's remaining preconditions, and run approval for the *dwell-redesign* work. Tonight's
runs were the scenario matrix Dean asked for directly, not that staged run.

---

## ADDENDUM — campaign finished; results in. GPUs FREED and verified.

Campaign stopped early (Dean: *"putting the laptop to sleep"*) but **all 7 cells have data**. 156
snapshots, **every cell 100% hydrated**, including three whose live analysis failed and were recovered
offline from saved controller logs.

🚨 **GPUs FREED and verified twice** (manual ~07:57Z + campaign trap 08:02:41Z): no decode pods, no
harness pods; only gateway/EPP/controller/PVC remain. **The ScaledObject is PAUSED at 0 — un-pausing is
a mandatory first step of the next run**, or the trace is flat and reads as a legitimate no-scaling
result.

### Four results for CURRENT.md's benchmark entry

1. **Saturation CANNOT be disabled on `ta-0.9-anchor-pr2-20260809` — answers Dean's question: PR-2 does
   NOT fix it.** HIGH confidence: 3 cells, both profiles, full-run counts. Configured
   `analyzers:[throughput]` → saturation still emits one full `analyzer-result` per tick (37 lines over
   21 min; 8 over the truncated dwell cell). **The control makes it clean:** configured
   `analyzers:[saturation]` silences throughput completely (**0** lines). So the list is honoured for
   throughput and ignored for saturation. **Keep the `saturation:{enabled:false}` silent-no-op item
   open** — this is the first measured confirmation, on the newest image. Detail:
   `plan__benchmark-sat-disable-still-broken-on-pr2.md`.
2. **The dwell limit cycle is analyzer-INDEPENDENT.** HIGH confidence: both dwell configs hit the
   replica cap (10) twice; neither staircase config exceeded 9. **It tracks the workload, not the
   configuration** — consistent with §18's replica-lag account and §7.6's "controller-configuration
   lever" conclusion.
3. **`prc` collapse is a third, SEPARATE variable.** MEDIUM. Present in `m-ta-staircase` (5.26×) and
   `m-sat-dwell` (1.56×); absent in three others **including a cell that limit-cycled**. So it is **not
   the cause** of the limit cycle — the staircase results alone would have implied it was. §18's
   collapse mechanism is reproduced and its "mechanism, not tuning" diagnosis confirmed.
4. **The replica target oscillates while `rc = 0` and util ≈ 0.2** — the most interesting open thread.
   Points at the decision/optimizer path rather than the analyzer. Not investigated; no code read.

### Weakest link — carry it verbatim

**One run per cell, no repeats, no noise floor.** The image A/B (PR-2 → 3 replicas vs old → 2)
additionally started from different replica counts (1 vs 2). These are **mechanism observations, not
benchmark results**, and should not be quoted as measured effects.

### Also worth a row somewhere

**A harness reporting bug, reproducible on the dwell profile (3 for 3, 0 for 3 on staircase):** the
treatment logs `complete`, then an unconditional `if errors:` fails the step on a `Traceback` from
`process_epp_logs.py` that is itself labelled *non-fatal*. The load ran fine (all 5 stages, 148-149
scrape snapshots, 20 plots) but `run_metadata.yaml` is never written, which breaks the timeseries dump.
Fix candidate for the fork/upstream list: write the metadata before the error check, or keep the
non-fatal EPP failure out of `errors`.

### Not run

`m-ta-dwell` ran only ~10 of ~40 min (campaign stopped mid-cell). Its analyzer counts are valid; its
replica path is not a usable trace. A clean re-run of that one cell would complete the matrix.

---

## ⚠️ CORRECTION TO THE ADDENDUM — result #1 is RETRACTED

**Do not fold result #1 ("Saturation CANNOT be disabled… PR-2 does NOT fix it") into CURRENT.md. It is
false.** Dean corrected it: disabling saturation was never meant to stop it computing or logging — only
to stop it participating in the scaling math. The code does exactly that
(`saturation/engine_v2.go:150`, `satVotes`): compute and log always, vote conditionally. So counting
`analyzer-result` lines cannot answer the question, and that is all I did.

The engine logs the real signal once per tick, and it was already in my saved logs: **37 ×
"saturation analyzer is absent from the configured analyzer list: it will not vote and cannot veto
scale-down"** in the TA-only cell, **0** in the sat-only cell. Also `scaling-decision` counts 40 / 37 /
**19** for sat / satta / TA-only.

**Withdrawn:** the disable claim; "PR-2 does not fix it"; "the matrix has 2 configurations, not 3" (it
has **3**); and the claim that this campaign confirmed the `saturation:{enabled:false}` silent-no-op —
that backlog item should be left **exactly as it was**, and note `enabled:false` is a different
mechanism from list-omission anyway.

**Results #2, #3 and #4 stand**, and #2 is *strengthened*, since the matrix is now a genuine
3-configuration comparison. The "weakest link" paragraph and the harness-reporting-bug row are
unaffected.

Full detail and the retraction: `plans/session/status/benchmark.md` §20.21 and
`plan__benchmark-sat-disable-still-broken-on-pr2.md` (now a retraction notice).
