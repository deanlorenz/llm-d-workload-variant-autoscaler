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

**1. A live OpenShift bearer token is committed inside the results tree.** Every cell's
`run/inference-perf-*.yaml` carries `LLMDBENCH_BASE64_CONTEXT_CONTENTS`, which base64-decodes to a
kubeconfig containing a `sha256~…` bearer token for `DEAN@il.ibm.com` on
`api.pokprod001.ete14.res.ibm.com`. **7 copies**, one per cell. The token must be **rotated**, and no
copy/publish step (figures, overview, anything handed to Ofer) may carry those manifests along. Flagged
to Dean 2026-08-10; not actioned by this doc.

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

## Finding 3 — `prc` collapse is a third, separate variable

Reproduced live in `m-ta-staircase`: `prc` fell **329011 → 195774 → 62538 (5.26×)** after a single
`P1-obs` tick, then **stuck** at the collapsed value via `P2-hist` for the rest of the run. Supply
followed it down (329011 → 125076), so utilization crossed 1.0 and `rc` went positive — the controller
scaled against a capacity estimate that had fallen through the floor, not against real load growth.
§18 measured up to 13×; this run 5.26×; same direction, same sticking, same `P1-obs`→`P2-hist` sequence.
**§18's "mechanism, not a tuning problem" diagnosis is confirmed.**

**It is not the limit cycle's cause.** Present in `m-ta-staircase` (5.26×) and `m-sat-dwell` (1.56×);
**absent in three cells including one that limit-cycled**. The staircase results alone would have implied
causation. Three phenomena are now separable: the limit cycle, the `prc` collapse, and the analyzer
configuration.

**New detail worth a Type-1 look:** `m-sat-staircase` *also* entered `P1-obs` but its `prc` stayed at
329011. So collapse is **not** a deterministic consequence of entering `P1-obs` — something about the
observed `k2` at that tick decides whether the history is poisoned. The specific question to aim at: how
the observed `k2` is written into the bucket-keyed capacity history.

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
2. **All three dwell cells are blind to user-visible cost** — panel 1a is empty ("no per-request trace in
   this bundle"). See § *The 1a gap* — this is a harness bug, not missing instrumentation.
3. **The capacity model fails its own self-check on every staircase cell.** `m-ta-staircase`:
   `pred=212.4 obs=78.0`, **63% error**. The extractor flags it as a SELF-CHECK FAILURE. The "capacity
   ceiling" line drawn in panels 1b and 5 is the *model's prediction* and the model is currently wrong by
   ~2.7× on these runs. Do not present it as a validated ceiling.
4. **`m-ta-dwell` is not a usable trace.** Truncated at ~360 s of a ~40-minute cell (campaign stopped —
   Dean: *"putting the laptop to sleep"*); ITL fit r²=0.11 on n=36; replicas fall to 0 at the end because
   the ScaledObject was paused. Its **analyzer counts are valid**; its replica path and ITL fit are not.
5. **Router-oscillation numbers in panel 3 are not an oscillation test.** The panel says so. A 6–11 s
   oscillation is below Nyquist at the ~15.7 s scrape cadence; only a per-request trace carrying
   `UPSTREAM_HOST` can see it.
6. **The `m-ta-*` cell names are not findings.** They are *configured* throughput-only per Dean's
   instruction; the runs test what the engine does with that configuration.

---

## The 1a gap — what "no per-request trace" costs (answers Dean's question, 2026-08-10)

The **offered** workload survives in full; the **delivered** workload does not.

Offered load is recoverable from each cell's `run/inference-perf-*.yaml`:
`LLMDBENCH_RUN_EXPERIMENT_HARNESS_WORKLOAD_NAME` (`ta_autoscale_dwell.yaml` /
`ta_autoscale_staircase.yaml`), model `unsloth/Meta-Llama-3.1-8B-Instruct`, a 16-CPU/32Gi harness pod, and
the gateway endpoint. So "what did we ask for" is never in doubt.

| question | without panel 1a |
|---|---|
| Offered rate and shape | ✅ from the profile yaml |
| Replica trajectory, `desired` vs `ready`, boot lag | ✅ panel 2 — the limit cycle is intact |
| Per-pod running / waiting, queue depth | ✅ panels 3, 4 |
| **TTFT, wait-before-first-token, goodput** | ❌ gone |
| **Whether requests failed or timed out** | ❌ gone |
| **Arrival vs departure rate** (was the offered load actually delivered?) | ❌ gone |
| **Router oscillation / `UPSTREAM_HOST`** | ❌ gone |
| ITL fit quality | ⚠️ degraded — scrape-derived samples only (hence r²=0.87 vs 0.92–0.94) |

**The concrete loss.** Finding 1 exists *because* `m-sat-staircase`'s 9 replicas came with `>60s / failed`
TTFT bars. Run that same cell on the dwell profile and you would see the replica excursion and **not know
whether users were served**. A limit cycle that delivers acceptably and one that drops requests are
**indistinguishable** in panels 2–5.

**Verdict:** the dwell *mechanism* is understood (Findings 2 and 3 stand on panels 2–5 alone, which is why
§7.6's conclusions are safe). The dwell's *user-visible cost* is unmeasured. For "is this regime
acceptable?" the dwell cells cannot answer.

**Root cause — a harness bug, ~2 lines.** Reproducible on the dwell profile (**3 for 3**; 0 for 3 on
staircase): the treatment logs `complete`, then an unconditional `if errors:` fails the step on a
`Traceback` from `process_epp_logs.py` that is itself labelled *non-fatal*. Load ran fine (all 5 stages,
148–149 scrape snapshots, 20 plots) but `run_metadata.yaml` is never written, which breaks the timeseries
dump and the per-request extraction. Fix: write the metadata **before** the error check, or keep the
non-fatal EPP failure out of `errors`.

**Priority argument.** This fix outranks re-running `m-ta-dwell`: it is ~2 lines, converts **three blind
cells into three complete ones**, and re-running without it merely reproduces the blindness. Recommended
order: fix → re-run `m-ta-dwell` → re-extract all three dwell cells.

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

**Owed, and by whom:**
- **Benchmark coder** — decide whether the figures need a **tracked** home under `session-notes/` (the
  canonical `viz/` copies are inside gitignored `dean-*/`, so they do not survive a cleanup or a fresh
  clone); fix the `run_metadata.yaml` error-ordering bug; re-run `m-ta-dwell` and re-extract the dwell
  cells.
- **Dean** — **rotate the leaked bearer token**; choose the figure location; decide whether the campaign
  results fold into the Type 3 or stay a standalone doc (this doc is currently standalone).
- **Planner** — audit the plans for any framing that assumed "removing saturation from the list isolates
  TA": that assumption is *sound* after §20.21 (list-omission does stop it voting), but the earlier
  retracted claim briefly implied otherwise, so anything written between those two points needs a check.
  Not yet done.

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
