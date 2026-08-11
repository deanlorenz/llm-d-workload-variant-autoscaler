# Pokprod campaign 2026-08-10 — 7-cell scenario matrix, results and figures

**Status:** DRAFT
**Type:** 6 (results write-up; companion to Type 3 [`ta-pokprod-testing-plan.md`](ta-pokprod-testing-plan.md))
**Run date:** 2026-08-10, overnight, on `dhl-wva-209` (pokprod), with Dean's explicit approval
**Controller image:** `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9-anchor-pr2-20260809`
@ `sha256:5487953c82ab48136cb7f3e02b23f1dd329fd37ecb58896507104dfe26d05f4f`
(built from PR-2 `ta-anchor-dynamic-refresh@14a5d6cc`, PR
[#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523))

---

## Reading protocol

Read this section and § *The matrix*, then fetch only the finding you care about. The figures are the
primary artifact; this doc exists to say what each one shows and what it does **not** license.

---

## ⚠️ Two hazards before anything else

**1. RESOLVED 2026-08-10 — a live OpenShift bearer token was present in the results tree (never
committed).** Every cell's `run/inference-perf-*.yaml` carried `LLMDBENCH_BASE64_CONTEXT_CONTENTS`,
which base64-decodes to a kubeconfig containing a `sha256~…` bearer token for `DEAN@il.ibm.com` on
`api.pokprod001.ete14.res.ibm.com`. It never reached git — those files live under gitignored `dean-*/`
directories — but they were readable on disk, and every copy/mirror step made from that tree (the
`plans/scratch/` mirror, the coder's tracked `session-notes/campaign-viz/`) had to be checked clean
before use.

**Mechanism, traced:** this is upstream `llm-d-benchmark` behavior, not something the WVA fork
introduced. `setup/run.sh:183` captures the operator's active kube context to `context.ctx`;
`build/llm-d-benchmark.sh:25-26` decodes it back into `~/.kube/config` **inside the harness pod**, so
the harness can `kubectl`/`oc` from within the cluster it's benchmarking. Every run embeds whatever
token is live in the operator's context at launch time.

**Disposition, Dean's call:** all 7 files were **removed** (verified: 0 copies anywhere in either
worktree, `sha256~…` pattern grepped clean tree-wide). pokprod itself rotates and forces a new token
every few hours regardless, and **there is no need to persist a bearer token beyond the active session
— the live k8s context is sufficient**; a saved token only creates a standing artifact with no
corresponding need. This resolves the immediate exposure. It does **not** fix the mechanism above: the
*next* campaign will embed whatever token is live in the context at that time, into fresh `dean-*/`
directories, by the same upstream code path. A durable fix (e.g. a scoped service-account token
injected via secret, rather than the operator's personal context) is upstream `llm-d-benchmark`
engineering — tracked as a checklist item, not fixed here. See § *Documentation drift checklist* below.

**2. The campaign's original headline finding was RETRACTED mid-flight.** The first report claimed
"saturation cannot be disabled on the PR-2 image". That is **false** — see § *Finding 1*. Any external
reference to the earlier claim (including this planner's own summary to Dean before the correction
landed) is superseded. `status/benchmark.md` §20.21 is the retraction of record.

---

## The matrix

Seven cells: two workload profiles × three analyzer configurations, plus one baseline. Same image, same
namespace, same 7920-request offered load per staircase cell.

| cell | profile | analyzers (voting) | peak replicas | ITL fit | TTFT quality | figure |
|---|---|---|---|---|---|---|
| `b-satta-staircase` | staircase | sat+TA — **baseline** | 2 (no scale-down) | 0.170·k+9.6 (r²=0.92) | all green | [panels](../scratch/campaign-20260810-viz/b-satta-staircase.png) · [coverage](../scratch/campaign-20260810-viz/b-satta-staircase-coverage.json) |
| `m-satta-staircase` | staircase | sat+TA | 3 | 0.178·k+9.5 (r²=0.94) | all green | [panels](../scratch/campaign-20260810-viz/m-satta-staircase.png) · [coverage](../scratch/campaign-20260810-viz/m-satta-staircase-coverage.json) |
| `m-ta-staircase` | staircase | **TA only** (sat non-voting) | 3 | 0.169·k+9.6 (r²=0.93) | all green | [panels](../scratch/campaign-20260810-viz/m-ta-staircase.png) · [coverage](../scratch/campaign-20260810-viz/m-ta-staircase-coverage.json) |
| `m-sat-staircase` | staircase | **sat only** (TA non-voting) | **9 desired / 8 ready** | 0.162·k+9.6 (r²=0.92) | **>60s / failed** | [panels](../scratch/campaign-20260810-viz/m-sat-staircase.png) · [coverage](../scratch/campaign-20260810-viz/m-sat-staircase-coverage.json) |
| `m-satta-dwell` | dwell | sat+TA | **10 (cap), twice** | 0.172·k+9.4 (r²=0.87) | ❌ no per-request | [panels](../scratch/campaign-20260810-viz/m-satta-dwell.png) · [coverage](../scratch/campaign-20260810-viz/m-satta-dwell-coverage.json) |
| `m-sat-dwell` | dwell | sat only | **10 (cap), twice** | 0.202·k+8.6 (r²=0.87) | ❌ no per-request | [panels](../scratch/campaign-20260810-viz/m-sat-dwell.png) · [coverage](../scratch/campaign-20260810-viz/m-sat-dwell-coverage.json) |
| `m-ta-dwell` | dwell | TA only | 3 — **truncated ~10 of 40 min** | 0.051·k+13.5 (**r²=0.11**) | ❌ no per-request | [panels](../scratch/campaign-20260810-viz/m-ta-dwell.png) · [coverage](../scratch/campaign-20260810-viz/m-ta-dwell-coverage.json) |

### Where the figures live

**Canonical (Dean's instruction, 2026-08-10): beside their own run data**, at
`benchmark/<results-root>/results/inference-perf-*_1/viz/{panels.png,coverage.json,bundle.json}` — one
`viz/` per cell, 276 KB–2.0 MB each. The `<results-root>` per cell is in the map below; the `viz` column
above links the planner-scope mirror because a doc on the `plans` branch cannot resolve a relative path
into a sibling worktree.

> **⚠️ `dean-*/` IS GITIGNORED** (`benchmark/.gitignore:43`), with the rule's own comment stating *"whatever
> survives a run belongs in `session-notes/`"*. So the canonical copies are **on disk but not preserved by
> git** — deleting a `dean-*` directory takes its figures with it, and a fresh clone has none of them. If
> these figures need to survive, a tracked location under `session-notes/` (which is *not* ignored, unlike
> `session-notes/campaign-runs/` and `session-notes/scratch/ladder-run/`) is the only durable home. That
> is a **benchmark-coder** decision on a **benchmark-coder** tree; flagged, not made.

**Planner-scope mirror:** [`scratch/campaign-20260810-viz/`](../scratch/campaign-20260810-viz/) — the seven
PNGs plus `coverage.json`, committed on `plans` (3.0 MB), so this doc's links resolve and the analysis is
self-contained even if the ignored copies are cleaned up. Mirror, not source; `bundle.json` is not mirrored
(1.5 MB × 4 staircase cells) — regenerate per § *How the figures were produced*.

**Cell → results directory map.** Paths are relative to the `benchmark` worktree root. The canonical
figures are at `<root>/results/<leaf>/viz/`. `results-dir.txt` in each `session-notes/campaign-runs/<cell>/`
stores **only the leaf name**, not the root — which is why resolving a cell to its data takes both columns.

| cell | results root | leaf (`results/<leaf>/viz/`) |
|---|---|---|
| `b-satta-staircase` | `dean-20260810-072736-888` | `inference-perf-1786336098-ofaw6f_1` |
| `m-satta-staircase` | `dean-20260810-064736-555` | `inference-perf-1786333694-u86rqu_1` |
| `m-sat-staircase` | `dean-20260810-080708-371` | `inference-perf-1786338510-g00qeo_1` |
| `m-ta-staircase` | `dean-20260810-084756-739` | `inference-perf-1786340933-m9emm7_1` |
| `m-satta-dwell` | `dean-20260810-092644-320` | `inference-perf-1786343242-zr01gi_1` |
| `m-sat-dwell` | `dean-20260810-100827-539` | `inference-perf-1786345748-yivu77_1` |
| `m-ta-dwell` | `dean-20260810-105211-685` | `inference-perf-1786348370-brv0r3_1` |

---

## Finding 1 — the three configurations are genuinely different, and the plots show it

**This is the strongest confirmation of §20.21's correction.** The retracted claim rested on counting
`analyzer-result` log lines. The engine's design is **compute-and-log always, vote conditionally**
(`satVotes`, `saturation/engine_v2.go:150`), so those counts cannot answer the disable question — and
the engine says so explicitly once per tick ("saturation analyzer is absent from the configured
analyzer list: it will not vote and cannot veto scale-down"), 37 times in `m-ta-staircase`, 0 in
`m-sat-staircase`.

The traces settle it independently of any log line:

- **sat-only over-provisions AND delivers worse latency.** `m-sat-staircase` reaches **9 desired / 8
  ready** replicas and drives TTFT into the `>60s / failed` band (panel 1a, t≈450–600 s), with ~900
  requests in system and a ~500-deep engine queue (panel 4, source (c)).
- **Both TA-voting configs stay at 3 replicas**, all-green TTFT, ~150 in system.
- Same offered load, same image, same 7920 requests.

So saturation-voting is not a logging artifact — it changes the replica trajectory by 3× and the
user-visible latency from "all green" to "failed". `m-ta-*` really is TA-not-voting, and the matrix has
**three** configurations, not two.

**Corroborating signal:** `scaling-decision` lines per cell — 40 (`m-sat-staircase`), 37
(`m-satta-staircase`), **19** (`m-ta-staircase`). The TA-only cell produced roughly half as many
decisions, consistent with saturation not voting.

**Scope limit.** What is measured is that the *voting set* changes behavior. `saturation:{enabled:false}`
is a **different mechanism** from analyzer-list omission and remains **untested in both directions** —
the long-standing silent-no-op item is neither confirmed nor refuted by this campaign. Do not cite these
cells for it.

**Open question this leaves, and it is the interesting one.** `m-ta-staircase` still produced 19 scaling
decisions and a live replica path (2→3→2→3→2) with saturation non-voting. What drove them — the
throughput analyzer alone, as designed? The matrix data can address this; nobody has looked.

---

## Finding 2 — the dwell limit cycle is real, and analyzer-independent

`m-satta-dwell` and `m-sat-dwell` show the **same envelope** in panel 2: ride to the replica cap of 10,
collapse to 2, climb again — two full excursions each. Different analyzer configurations, indistinguishable
shape. Neither staircase cell exceeded 9.

This is Type-3 §7.6's conclusion holding on real traces rather than inference: the dwell is a property of
the **controller/workload interaction**, not of the analyzer configuration. It also strengthens §7.6's
central argument — steady-state KV under a tracking controller is a *controlled* variable, so the dwell is
a configuration lever rather than an offered-rate one.

**Panel 2 also shows the mechanism: replica lag, not rate.** In `m-satta-dwell` the `desired` (red) trace
jumps to 10 while `ready` (purple) trails by 300+ s — **boot mean 316 s over 9 steps**, versus 70–95 s in
the staircase cells. The controller keeps asking for more capacity while the previous batch is still
booting. That is exactly §18's replica-lag account, now visible rather than argued.

---

## Finding 3 — CORRECTED 2026-08-10: saturation's internal `prc` still collapses even while non-voting

> **This finding was misframed and is corrected here, not retracted outright — the underlying
> observation stands, the causal story attached to it does not.** Original framing: reported as a
> finding *of* `m-ta-staircase` (the TA-only cell), implying the collapse was part of what drove that
> run's scaling. Dean, 2026-08-10, reviewing 1b for that cell: *"capacity matches load — not sure sat is
> correct [to discuss] for a TA-only experiment."* He is right. `prc`, `P1-obs`, and `P2-hist` are
> **saturation-v2** internals (`saturation_v2/types.go`); in `m-ta-staircase`, saturation is **not
> voting** (§20.21, Finding 1). A grep of that cell's controller log finds only **one** `P1-obs`-adjacent
> line, not the tick-by-tick sequence the original write-up implied. And 1b for that cell shows capacity
> tracking delivered load with no visible pathology — consistent with a non-voting analyzer's internal
> state never reaching the decision.

**What actually happened, restated without the causal claim:** saturation's own capacity estimate
(`prc`) fell **329011 → 195774 → 62538 (5.26×)** in `m-ta-staircase`'s controller log after a `P1-obs`
entry, then stuck at the collapsed value via `P2-hist`. That collapse is real — it is in the log — but
because saturation was non-voting in this cell, **there is no evidence it affected `m-ta-staircase`'s own
scaling decisions.** The compute-and-log-always design (§20.21) means saturation keeps computing `prc`
whether or not anyone acts on it, so seeing it collapse here is a fact about **saturation's estimator**,
not about the throughput analyzer or about what drove this particular run's replicas.

**§18's "mechanism, not a tuning problem" diagnosis is not affected by this correction** — §18's original
observations were on cells where saturation *was* voting, so the mechanism itself (a rolling-average
history that can get poisoned by one bad observed sample) still stands. What's corrected is only which
cells this finding is evidence *about*: it speaks to saturation's estimator behavior in general, sampled
here on a cell where that estimator happened to be a passenger, not a driver.

**Still worth a Type-1 look, reframed:** `m-sat-staircase` (saturation *voting*) also entered `P1-obs`
but its `prc` stayed at 329011 — so the collapse is not a deterministic consequence of entering
`P1-obs` even within cells where it matters. The question — how the observed `k2` gets written into the
bucket-keyed history, and why one entry into `P1-obs` poisons it and another doesn't — is unchanged by
this correction; only its evidentiary weight from `m-ta-staircase` specifically should be discounted.

**Reason-code reference** (source-checked, `saturation_v2/types.go`) — worth folding into a Type 4 doc:
`P1-obs` = `k2SrcObserved` "queue saturated: tokensInUse" · `P2-hist` = `k2SrcHistorical` "rolling average
from prior observations" · `P3-k2` = `k2SrcDerived` "estimated from deployment args" · `P4-k1` =
`k2SrcFallback` "fallback to k1 (memory-bound)". `P1-obs` is the **intended observed path**, not an
anomaly.

---

## Finding 4 — the replica target oscillates while `rc = 0` and util ≈ 0.2

The most interesting open thread, and **uninvestigated** — no code read, no root cause. Points at the
decision/optimizer path rather than the analyzer, since neither demand nor utilization justifies motion.
Recorded here so it is not lost.

---

## What the figures do NOT license

Read this before quoting any number above.

1. **One run per cell. No repeats, no noise floor.** These are **mechanism observations, not benchmark
   results**. The image A/B in particular (PR-2 → 3 replicas vs the older image → 2) *also* started from
   different replica counts (1 vs 2), so it is not a controlled comparison of images.
2. **CORRECTED — all three dwell cells are missing per-request resolution, not "blind to user-visible
   cost".** Panel 1a is empty, but per-stage latency/failure/token-rate data survives intact in
   `stage_N_lifecycle_metrics.json` for all five stages of all three cells. See § *The 1a gap* for the
   corrected diagnosis — the earlier "harness bug, ~2 lines" claim in this doc was itself wrong.
3. **CORRECTED 2026-08-10 — the self-check failure and the 1b "capacity ceiling" line are TWO DIFFERENT
   QUANTITIES, not the same model.** Original wording conflated them; Dean caught it, correctly noting
   1b visually tracks delivered load, not 60%+ off. They share no code path in `extract_real_trace.py`:
   - **1b's dashed "capacity ceiling"** is a **rate** — `ready replicas × tok/s per pod`, where the
     per-pod rate is `tput_knee()`: the *empirically observed* peak generation throughput on that same
     run (a `max` over the measured curve, explicitly documented as an upper-envelope estimate, not a
     model prediction). It tracks visually because it is calibrated **from** the data it is drawn over.
   - **SELF-CHECK 3** is a **concurrency count** — `capacity()`'s `max_conc_pred = kv_tokens /
     footprint_tok`, a KV-budget model from `num_gpu_blocks × block_size` divided by a per-request
     footprint estimate (`I×(1-prefix_hit) + O/2`), compared against `max_conc_obs`, the peak
     concurrent-requests actually observed. `m-ta-staircase`: pred=212.4, obs=78.0, 63% error. This is
     the number that is wrong by ~2.7×, and it is a **request-count** model, not the rate line in 1b/5.

   So: **1b and 5's rate ceilings are empirical and are not what the self-check is complaining about.**
   What is unvalidated is the *concurrency* prediction (would-be panel-3 KV ceiling), whose footprint
   model (`I×(1-hit) + O/2`) is the actual suspect — worth checking against real per-request I/O length
   once that data exists (see § *Per-request data — inventory and plan*).
   **⚠️ See § *`tput_knee()` and `capacity()` were never reviewed* below — this whole item explains what
   the code does; it is not evidence the code's approach is the right one.**
4. **`m-ta-dwell` is not a usable trace.** Truncated at ~360 s of a ~40-minute cell (campaign stopped —
   Dean: *"putting the laptop to sleep"*); ITL fit r²=0.11 on n=36; replicas fall to 0 at the end because
   the ScaledObject was paused. Its **analyzer counts are valid**; its replica path and ITL fit are not.
5. **Router-oscillation numbers in panel 3 are not an oscillation test.** The panel says so. A 6–11 s
   oscillation is below Nyquist at the ~15.7 s scrape cadence; only a per-request trace carrying
   `UPSTREAM_HOST` can see it.
6. **The `m-ta-*` cell names are not findings.** They are *configured* throughput-only per Dean's
   instruction; the runs test what the engine does with that configuration.

---

## The 1a gap — CORRECTED 2026-08-10: root cause was wrong; the loss is narrower than reported

> **The original diagnosis in this section was wrong and is replaced, not merely annotated.** It claimed
> `run_metadata.yaml` is "never written" by a ~2-line harness bug, and that all of TTFT/failure/
> arrival-vs-departure/router-oscillation were "gone" for all three dwell cells. **Checked directly
> against the actual result directories on 2026-08-10: `run_metadata.yaml` exists, and so do all five
> `stage_N_lifecycle_metrics.json` files plus `summary_lifecycle_metrics.json`, each with real content.**
> The **only** empty file is `per_request_lifecycle_metrics.json` — 0 bytes, in every dwell cell checked.
> So the failure is real but much narrower than described, and the "~2-line fix" theory does not match
> what is actually on disk. The likely mechanism is the one the dwell workload's own header predicts
> (`ta_autoscale_dwell.yaml`'s SIZING comment): the per-request trace is sized to ~11.3 GB against a
> harness pod OOM boundary the same doc documents at ~11.9 GB — a serialization death, not a control-flow
> bug in an error handler.

**What we actually have per stage, per dwell cell** (from `stage_N_lifecycle_metrics.json`, real numbers
from `m-satta-dwell` stage 2, the 20 rps dwell rung):

| field | value |
|---|---|
| requested / achieved rate | 20.0 / 20.018 req/s |
| count (successes / failures) | 7200 / 0 |
| request latency | mean 6.72 s · p95 9.00 · p99 14.19 · max 16.59 |
| normalized time per output token | mean 7.58 ms |
| **input tokens/sec** | **40,330** |
| **output tokens/sec** | **18,066** |
| schedule delay (generator kept up with target rate?) | p95 0.094 s |

**Revised cost table** — this is per-*stage*, not per-*request*, but it is real and on disk today, no
re-run needed:

| question | without `per_request_lifecycle_metrics.json` |
|---|---|
| Offered rate and shape | ✅ from the profile yaml |
| **Achieved rate, per stage** | ✅ `stage_N.load_summary.achieved_rate` — was wrongly marked "gone" |
| **Delivered latency distribution, per stage** | ✅ `stage_N.successes.latency.*` (mean/p95/p99/max) — was wrongly marked "gone" |
| **Failure count, per stage** | ✅ `stage_N.successes.count` vs `failures.count` — was wrongly marked "gone" |
| **Input/output token rate, per stage** | ✅ `stage_N.throughput.{input,output}_tokens_per_sec` |
| Replica trajectory, `desired` vs `ready`, boot lag | ✅ panel 2 |
| Per-pod running / waiting, queue depth | ✅ panels 3, 4 |
| Per-*request* TTFT / ITL (fine time resolution within a stage) | ❌ genuinely gone — this is what the empty file cost |
| Router oscillation / `UPSTREAM_HOST` | ❌ genuinely gone — needs a per-request trace by construction |
| ITL fit quality | ⚠️ degraded to scrape-derived samples (r²=0.87 vs 0.92–0.94) |

**Revised verdict.** The dwell cells are not "blind" — panel 1a can be rebuilt at **stage** resolution
from data already on disk (5 points per cell instead of a continuous per-request curve), and that
already answers "did users get served" per stage, including the exact question that made Finding 1
possible on the staircase cells. What is genuinely and only lost is *within-stage* resolution: the shape
of the latency distribution as load ramps inside a single 360 s rung, and anything that needs
per-request identity (router pod, exact arrival instant).

**Priority, corrected.** Given the size-boundary root cause, re-running `m-ta-dwell` with the
per-request collector **enabled** would very likely reproduce the same OOM — not a productive next step
on its own. See § *Per-request data — inventory and plan* below for the disposition Dean has set for
per-request collection generally (disable it; find fallback signals instead).

---

## `tput_knee()` and `capacity()` were never reviewed (Dean, 2026-08-10)

**Dean, on `tput_knee()`:** *"I don't remember discussing it / reviewing it, and making a decision."*
Checked directly: correct. Both `tput_knee()` and `capacity()`/`max_conc_pred` were introduced in the
toolchain's very first commit, **`ca7f2c74`** (2026-08-07, authored by Dean himself, in `autoscaling-viz`)
— every "Dean approved" line in that worktree's plan doc is about the **migration** (branch/worktree
moves, the name `autoscaling-viz`), never about these two functions' design. §6 of the plan does record
Dean's memory-bound *formula* (`I·(1−pfx_hit) + O/2`, validated once to <1% against one run's peak) — but
that is the shape of the model, not a review of `capacity()`/`max_conc_pred` as they exist in code today,
and it says nothing about `tput_knee()` at all. **Anything in this doc citing either function's output
should be read as "what the code currently does," not "a reviewed and agreed method."**

**Dean's objection to `max_conc_pred`, stated precisely — and it survives inspection of the code:**
`capacity()` computes ONE global number (`kv_tokens / footprint_tok`, memory-bound formula) and compares
it against `max_conc_obs`, the single observed peak. There is no time window, no local-error tracking, no
handling of regime transitions. Restated in Dean's terms: real `num_running(t)` has (at least) three
distinct behaviors — **a(t)**, the pre-saturation trajectory, which is *not constant, not linear in
load, and jumps* (replica boots, preemption events); **b**, the near-saturation value the model is
actually trying to predict, which is *harder to track precisely because it's not a fixed point*; and
**c**, the fully-saturated ceiling, which is just `max()` and "does not mean much" on its own — it's a
ceiling, not a description of behavior below it. `capacity()` fits none of these directly: it predicts a
single number and checks it once against `max_conc_obs`, which is closest to **c**, so the 63% error on
`m-ta-staircase` (a cell that never saturates — panel 1b shows capacity tracking load throughout, per
Finding 3's correction above) is close to a category error: **checking a saturated-regime ceiling formula
against a run that stayed in the a(t)/b regime the whole time.** That the error is large there may say
more about applying the check outside its intended regime than about the formula being wrong.

**Both SAT and TA make their own demand/supply estimates, and Dean's point generalizes beyond this one
viz function:** demand estimates tend to be tractable, supply estimates are multi-modal at best (exactly
the a(t)/b/c split above), and averaging across a run — which is what a single `max_conc_pred` number
does — is not expected to be accurate in either analyzer's actual operating regime. This is the same
concern as Finding 3's correction (a single-tick sample, `P1-obs`, gets treated as representative and
then sticks via `P2-hist`) and the §7.6 controller-configuration-lever argument (steady state is a moving
target under a tracking controller, not a fixed point to average toward) — three independent findings in
this campaign all point at the same underlying issue: **static/global estimates get applied to a
quantity that is actually piecewise or regime-dependent, and nobody has yet computed how the error
behaves as a function of time or regime.**

**Not litigated here — flagged as an open design question needing Dean's actual review**, which has
never happened for these two functions:
1. Should `capacity()` report a **windowed** or regime-classified value instead of one global number?
2. What is the local error of `max_conc_pred` as a function of time / regime (a(t) vs b vs c), rather
   than one point-in-time comparison against `max_conc_obs`?
3. Is `tput_knee()`'s `argmax`-over-stable-bins approach (documented in its own docstring as an
   upper-envelope estimate, "the best this hardware was ever seen to do," not a sizing number) the right
   quantity for the 1b/5 "capacity ceiling" line, given it is now known to be visually convincing
   *because* it's calibrated from the same curve it overlays — which could mask exactly the kind of
   regime-dependent error Dean is asking about?

**A concrete, previously-unexploited signal for this: EPP scorer debug logs.** Found this session,
directly answering Dean's *"epp in debug mode can emit scorer info… estimates prefill effort and cache
behavior per that request."* Confirmed in `logs/epp_pods.log` (11 MB/cell, already on disk for every
campaign cell): every scheduling decision emits, keyed by `x-request-id` and per candidate endpoint —
- `kv-cache-utilization-scorer` score **and** that endpoint's live `KVCacheUsagePercent`,
  `RunningRequestsSize`, `WaitingQueueSize`, `CacheNumBlocks`/`CacheBlockSize` at that instant;
- `prefix-cache-scorer` score (0 or nonzero per request — a **per-request** prefix-hit signal, where
  `capacity()` today only has an aggregate rate `pfx_hit` averaged over the whole run);
- `queue-scorer` score.

This is real, timestamped, per-request, per-pod state at scheduling time — not TTFT or output length
directly, but exactly the kind of local signal that could let `max_conc_pred`'s error be computed as a
function of time/regime instead of once globally, and it directly answers part of the per-request
discovery task below (prefix-hit rate, at minimum, no longer needs to be an aggregate assumption).
**Not yet mined for this purpose — added to the discovery task, not analyzed here.**

---

## Type 1 homes — where the missing designs go (Dean, 2026-08-10)

**The `tput_knee()`/`capacity()` review has no doc to review against, because no Type 1 covers this
material at all.** Checked directly: `planning/benchmark-observability-plan.md` is the nearest-sounding
candidate and is a Type 3 for a *different* effort (WVA's own `k2`/saturation decision logging) — it
never mentions `tput_knee`, `capacity()`, or concurrency estimation. The only place the estimation
*design* lives is `autoscaling-viz/real-trace-viz-plan.md` §5.3/§6, a Type-3-shaped worktree
implementation doc, not a Type 1. There was never a frozen design to check the code against — the gap
predates this campaign.

**Scoping, decided:** two Type 1s, split by **worktree responsibility**, cross-referenced where they
touch rather than merged into one:

- **Benchmark Type 1** — setup, runs, workload preparation, collection, results management, and calling
  into viz. Owns: the `.env`/context contract (§2c of the testing plan already covers part of this and
  should likely fold in or be superseded by this doc), the results-persistence tree (§ *Folder structure*
  below), per-request collection policy (§ *Per-request data*, next section), the harness-credential
  mechanism (§ *the bearer token*, above).
- **Viz Type 1** — visualization, post-test analysis, synthetic simulation, and simulation-following-a-
  test. Owns: the capacity/knee estimation model (`tput_knee()`, `capacity()`/`max_conc_pred`, and the
  three open review questions above), the coverage-check specification (§ *Coverage checks —
  undocumented*), panel design including the missing scaling-decision panel.

**Not written yet.** This section records the scoping decision only. Creating the two docs, migrating
the relevant material out of `real-trace-viz-plan.md` and `ta-pokprod-testing-plan.md`, and running
Dean's actual review against the viz one are all separate, sequenced work — see the checklist below.

---

## Documentation drift checklist (Dean, 2026-08-10 — "we need a checklist, not resolve everything immediately")

Checked what actually needs revisiting, rather than assuming everything referencing this campaign is
stale. Listed, not fixed:

- [ ] **Type 1 — benchmark.** Does not exist. Create per § *Type 1 homes* above. Candidate content:
  §2b/§2b-bis/§2c of `ta-pokprod-testing-plan.md` (two-fork contract, artifact tree, config contract),
  the per-request collection decision, the harness-credential mechanism.
- [ ] **Type 1 — viz.** Does not exist. Create per § *Type 1 homes* above. Candidate content: §5–§8 of
  `autoscaling-viz/real-trace-viz-plan.md` (ITL validity window, capacity model, coverage spec), the
  `tput_knee()`/`capacity()` open review questions from this doc.
- [ ] **`combined-analyzer-optimizer-design.md` (Type 1)** — spot-checked this session: its one reference
  to "saturation cannot be disabled" cites the pre-existing gap by its established name, **not** the
  retracted campaign claim. Clean on this pass. Worth a second look once the F1 sat-disable fix design
  (the item this doc is actually tracking) exists.
- [ ] **Epic** — whichever epic tracks the pokprod benchmark/TA validation work should be checked for any
  claim inherited from the retracted Finding-1-predecessor or Finding 3's original misattribution. Not
  checked this session — no epic doc was located in this pass; may need identifying first.
- [ ] **Type 3, `ta-pokprod-testing-plan.md`, §7.6/§7.6.1** — written *predicting* what this campaign then
  measured. Nobody has closed that loop: §7.6's (a)/(b) operating-point fork is still open, and §7.6.1's
  cold-resume state predates the actual campaign results existing. Needs a pass reconciling prediction
  against measurement.
- [ ] **`session/CURRENT.md`** — spot-checked this session: already self-corrects with its own
  "RETRACTED — do not cite" marker on the sat-disable claim. Clean.
- [ ] **Upstream `llm-d-benchmark` mechanism fix** (bearer-token embedding, § *the bearer token* above) —
  not a doc, but a real engineering item with no current home. File as an upstream issue candidate once
  §9.1 T10's "later" arrives, or sooner if Dean wants it tracked separately.
- [ ] **Full sweep** — this pass checked the obvious candidates (grep for cell names, the sat-disable
  phrase, and this doc's own filename) across `planning/` and `session/CURRENT.md`. A thorough sweep
  across every `planning/*.md` for `prc`/`k2Source`/`P1-obs` or other sat-v2-estimator-internals
  references has **not** been run — flagged, not done.

---

## Per-request data — disposition and discovery plan (Dean, 2026-08-10)

**Decision: disable per-request collection in inference-perf. No benchmark Makefile target should
enable it going forward.** Reasons, verbatim: it is unreliable (the OOM above is direct evidence — its
own sizing math admits it's borderline before every run), it consumes excessive disk on the harness pod,
and — the detail that changes how anyone should read the existing traces — **it collects per-*packet*
information, not per-request as the name implies.** (`per_request_lifecycle_metrics.json`'s size on a
successful staircase run, ~1.5 MB bundle / 7920 requests, is consistent with something finer-grained
than one record per request.) This reframes every per-request number already cited in this doc
(`n=7920`, the ITL fits, the router-imbalance stats on the four staircase cells that *did* produce this
file) as **derived from a stream that over-collects relative to what it's used for** — the numbers
aren't wrong, but the collection mechanism generating them is being retired regardless of whether a given
run happened to survive it.

**What we keep as the reliable base: per-stage summaries.** Confirmed on disk for every cell, dwell
included — see the corrected § *The 1a gap* above. Rate, latency distribution, failure count, and token
throughput, all per stage, at zero additional collection cost (already part of `inference-perf`'s
non-per-request reporting).

**Open discovery task — a full log scan, not just EPP.** The exact ask: enumerate the fields we need or
can estimate per request — **arrival time, TTFT, input length, output length, processing time**, and
whatever else the logs can yield — then scan every available log source, not only EPP, to see what's
actually recoverable. Sources known to exist and not yet fully mined:

| source | size (dwell cell) | sampled content (this session, partial) |
|---|---|---|
| `logs/epp_pods.log` | 11 MB | EPP debug log. Carries `x-request-id` per HTTP body chunk (`HandleResponseBody is triggered` — 34,978 lines in one dwell cell) and named scheduler-plugin events (`Calculated score`, `Request handled`, `LLM request assembled` — 62 each, matching the request count). **Confirmed this session** (Dean's lead): `Calculated score` lines carry, per `x-request-id` per candidate endpoint, `kv-cache-utilization-scorer` score + that endpoint's live `KVCacheUsagePercent`/`RunningRequestsSize`/`WaitingQueueSize`, `prefix-cache-scorer` score (a **per-request** prefix-hit signal — see § above), and `queue-scorer` score. **No token-count fields found in this session's sample** — needs a full field scan, not a spot-check, before ruling anything out. |
| `logs/igw_pods.log` | 38 MB | Gateway (Istio) pod log. This session's sample was Istio's own startup/info noise, not an access-log line with request ID or duration — but only the first lines were read; the bulk is unscanned. |
| `metrics/raw/*_metrics.log` | 144 KB × N snapshots | Per-pod Prometheus scrape snapshots, already what panels 2–5 are built from. Worth checking specifically for an EPP-emitted metric (Dean's suggestion) that carries request-level info not in the debug log. |
| `controller.log` | ~200 KB | WVA controller's own decisions — this is the source for the wanted **scaling-decision panel** (see below), not per-request data, but worth scanning for anything unexpected. |

**Task for the discovery pass:** (1) write the exact field list needed/wanted (arrival time, TTFT, input
length, output length, processing time, plus any others worth estimating); (2) scan the full schema of
each log source above — every distinct `msg`/field combination, not a sample — cross-referenced against
that field list; (3) report what is directly present, what can be *derived* (e.g. request count per
window as a demand-rate proxy even without per-request timing), and what needs a source not yet
inventoried; (4) note explicitly that most of what feeds the existing figures already comes from
Prometheus scrapes — some of the wanted fields may already be sitting in `metrics/raw/` unused, or
derivable from the graphs already drawn, before reaching for a new collection mechanism.

**Not yet done.** This is a discovery task, not a result — nothing above should be read as "the fields
aren't available," only as "not yet fully searched."

---

## Missing: a scaling-decision panel

**Dean asked for a bottom panel showing scaling *reasons*, as captured in the logs. There is no such
panel today.** The renderer (`render_real_trace.py`) draws six: 1a (request throughput/goodput), 1b
(work throughput), 2 (desired vs ready replicas), 3 (requests per pod), 4 (queue sources), 5
(concurrency vs slot capacity). None of them show *why* a scaling decision fired.

The reason codes exist and are already being read manually in this doc's own Finding 3 — `controller.log`
carries per-tick `scaling-decision` lines and the `P1-obs`/`P2-hist`/`P3-k2`/`P4-k1` capacity-source
codes (`saturation_v2/types.go`), plus the explicit "analyzer absent from configured list: will not
vote" lines that settled §20.21. All of that is currently hand-grepped per finding rather than plotted.
A dedicated panel — decision reason vs time, aligned with panel 2's replica trace — is the natural next
addition to the toolchain, and would have made Finding 3's correction visible on the figure itself rather
than requiring a log grep to catch Dean's objection. **Not built. Flagged as the priority addition.**

---

## Coverage checks — undocumented

The extractor's 16 PASS/FAIL self-check lines (`Calibrate A`, `Trust B`, `Characterize saturation`, …)
have no accompanying doc explaining what each one asserts, why it matters, or what a FAIL should prompt
someone to do. They're read correctly in this doc's caveats section by inspecting the extractor source
directly, which is not a sustainable way for anyone else to use them. **Owed:** a short reference — one
line per check, in the `autoscaling-viz` worktree — naming the assertion and its threshold.

---

## Folder structure — where results live, and what a `make` target should produce

**Not yet settled to Dean's satisfaction as of 2026-08-10** ("I still don't understand where the results
live and what is the folder structure. Someone running the make target should get a consistent result.")
Recorded here as the working answer, pending the coder building it and Dean confirming it reads clearly
in practice:

```
benchmark/
├── tools/ → ../hack/benchmark      symlink (§2b-bis, already decided — nothing moves)
├── campaigns/<YYYYMMDD>/           curated, cross-cell write-ups (this doc's eventual home)
└── runs/<run-id>/                  ONE run, EVERYTHING about it, single lifecycle
    ├── config/                     the .env used, workload profile, analyzer config, image pin
    │                                 — the reproducible set. Dean: "we mainly need the benchmark
    │                                 configuration... that is how it becomes reproducible."
    ├── raw/                        harness output, scrapes, per-stage summaries — large, disposable
    ├── viz/                        panels.png, coverage.json, bundle.json — SAME lifecycle as raw/,
    │                                 not a separate copy (see below)
    └── REPORT.md                   metrics table + relative links into viz/ and raw/
```

**Figures must not be copies.** Corrected this session — the `plans/scratch/campaign-20260810-viz/`
mirror created for this doc's own links is exactly the anti-pattern Dean flagged: *"like the existing
benchmark analysis graphs, they should live with the results and their lifecycle should be managed
together — if I delete an old result I want to also delete all the artifacts, including the panel
figures."* Once `benchmark/runs/<id>/viz/` exists as the canonical, git-tracked home, the `plans/`
mirror should be **deleted**, not maintained as a second copy.

**The matrix should link to everything.** Once the tree above exists, the per-cell table at the top of
this doc should link, per cell: the panels PNG, the raw per-stage JSON, any other result graphs, and the
`REPORT.md`/config for that run — not just the panels PNG as it does today.

**Not yet built.** Recorded here as the target; execution is the benchmark coder's per the trigger
already sent (`benchmark__results-tree-and-campaign-persistence.md`), which should be re-read against
this section's refinement (config/raw/viz coupled per run, not a separate campaigns-only tree).

---

## Fixes to the benchmark harness — scope decision (Dean, 2026-08-10)

**All harness fixes happen on Dean's fork for now.** Not upstream, not yet. *"We can later figure out
what belongs as issues/PRs on the benchmark repos."* This applies to whatever the per-request discovery
task above surfaces, and to anything else found while building the tree above.

**Excessive generated data is discarded by a playbook, not accumulated.** *"For now, excessive data
generated by benchmark can be discarded by our playbook. We keep only what we need."* The reproducible
set from § *Folder structure* (`config/`) is what's kept; `raw/` is retained only as long as useful and
is explicitly disposable, not an archival requirement. No playbook has been written yet — owed, likely
as a `hack/benchmark/` script that prunes a `runs/<id>/raw/` down to whatever `REPORT.md` still
references.

---

## How the figures were produced

Two-stage toolchain in the `autoscaling-viz` worktree, run read-only against the benchmark results:

```bash
cd <...>/autoscaling-viz
uv run --project . python extract_real_trace.py \
  --run <benchmark>/dean-<ts>/results/inference-perf-<id>_1 \
  --out <outdir>/<cell>
uv run --project . python render_real_trace.py \
  --bundle <outdir>/<cell>/bundle.json \
  --out <outdir>/<cell>/panels.png --title "<cell>"
```

Each cell yields `bundle.json`, `coverage.json`, `panels.png`.

> **⚠️ Path trap, cost ~1 wasted extraction.** `--run` must point at the **leaf**
> `results/inference-perf-*_1/` directory, **not** the `dean-*` root. The campaign nests one level deeper
> than the extractor's `<run>/metrics/processed/` expectation. Pointed at the root it does **not** error —
> it emits a 1-PASS/14-FAIL bundle with `n=0` everywhere plus a mild "no post_run_analyze.sh output"
> warning, which reads like a failed *run* rather than a bad *path*. **Candidate guard:** have
> `extract_real_trace.py` fail loudly, or auto-descend into `results/*_1/`, when `metrics/processed/` is
> absent but a single `results/*/metrics/processed/` exists. (Viz worktree = planner-sanctioned; this is a
> real code change and is **not** made by this doc.)

Coverage per cell was 12 PASS / 4 FAIL on the staircase cells (`m-ta-staircase` verified in detail: 152
scrape samples, 7920 per-request records, kv_span 0.43). `--quiet` **suppresses the self-check lines** —
omit it if you want the PASS/FAIL table.

---

## Provenance and durability

| artifact | location | durable? |
|---|---|---|
| Raw results (7 cells) | `benchmark/dean-2026081*/` | ✅ on disk, ⚠️ **token-bearing** |
| Cell metadata (`controller.log`, `analyzer-config.txt`, `scaledobject.yaml`, `images.txt`, `run.log`) | `benchmark/session-notes/campaign-runs/<cell>/` | ✅ |
| Coder's live state | `plans/session/status/benchmark.md` §20 (§20.21 = the retraction) | ✅ committed |
| **Bundles + figures — canonical** | `benchmark/dean-*/results/*_1/viz/` | ⚠️ on disk, **gitignored** |
| Figures — planner mirror | `plans/scratch/campaign-20260810-viz/` | ✅ committed on `plans` |

**Owed, and by whom — updated 2026-08-10, third pass (token resolved; Type 1 scoping; drift checklist):**
- **Bearer token — RESOLVED.** All 7 files removed, verified clean tree-wide. No standing action; the
  upstream mechanism fix is a checklist item (§ *Documentation drift checklist*), not a today task.
- **Dean** — the actual review of `tput_knee()` / `capacity()`, once the new Type 1 section exists to
  review it against (§ *Type 1 homes*, below) — three concrete design questions are listed in § *never
  reviewed* above and none are the planner's or coder's to decide.
- **Benchmark coder** — build the `benchmark/{tools→,campaigns/,runs/}` tree (§ *Folder structure*
  below); disable per-request collection in the benchmark Makefile targets (§ *Per-request data*);
  discard excessive per-run data per a to-be-written playbook keeping only the reproducible set; **run
  the per-request discovery task** (§ *Per-request data*) — exact field list, full schema scan of
  `epp_pods.log` / `igw_pods.log` / `metrics/raw/` / `controller.log`, including mining the EPP scorer
  debug lines (confirmed this session: per-request `kv-cache-utilization-scorer` +
  `prefix-cache-scorer` + `queue-scorer` output, keyed by `x-request-id`) for local demand/supply
  signal that could feed question 2 above (local error of `max_conc_pred` vs time/regime). Do all of
  this **on Dean's fork only** — upstream issues/PRs are explicitly deferred ("we can later figure out
  what belongs as issues/PRs on the benchmark repos"). Trigger:
  `session/handoffs/benchmark__viz-model-review-and-per-request-discovery.md`.
- **A dedicated new session** — the dwell limit cycle itself (Finding 2, §7.6) is being handed off
  separately per Dean's request; see `session/handoffs/dwell-deep-dive__handoff.md`. Not folded into this
  doc's findings beyond what is already written.
- **Planner / `autoscaling-viz` worktree** — audit the plans for any framing that assumed "removing
  saturation from the list isolates TA" (still open — Finding 1 is sound after §20.21, but text written
  between the retracted claim and the correction needs a check); add a scaling-decision-reason panel to
  the renderer (no such panel exists today — see § *Missing: a scaling-decision panel*); document what
  each of the 16 coverage checks actually asserts (§ *Coverage checks — undocumented*). None of these
  should touch `tput_knee()`/`capacity()`'s actual approach ahead of Dean's review above.

---

## Cross-references

- Type 3 [`ta-pokprod-testing-plan.md`](ta-pokprod-testing-plan.md) — §7.4 (scenario gaps), §7.6 (the
  operating-point argument these runs test), §7.6.1 (cold resume), §9.1 (T1–T11 owners)
- `plans/session/status/benchmark.md` §18 (dwell findings) · §19 (tooling round) · §20 (this campaign) ·
  **§20.21 (the retraction)**
- Handoffs: `sync__benchmark-overnight-campaign-20260810.md`,
  `plan__benchmark-sat-disable-still-broken-on-pr2.md` (⚠️ **its headline is retracted** — read alongside
  §20.21), `plan__benchmark-env-guard-design.md`
- PR-2 [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) — the code under test
