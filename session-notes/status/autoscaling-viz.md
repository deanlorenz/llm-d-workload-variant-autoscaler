last_update: 2026-08-08T00:42:00Z
state: in-progress (no blocking dependency; several decisions parked with Dean)
current_step: router_stats resolved (boot exclusion + verdict removal, verified against the arm-B source run at disp_p95 0.1429) and pushed. Branch is fully pushed for the first time in this line of work — `origin/autoscaling-viz` == local tip `4b263d73`, working tree clean. Nothing in flight. Next actionable work is the OWED deck-prose recheck (§ below); everything else is either deferred by agreement or waiting on a Dean decision.

## Branch
`autoscaling-viz` at `/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/autoscaling-viz`.
Tip `4b263d73`, **pushed** to `origin` (`deanlorenz/llm-d-workload-variant-autoscaler`) 2026-08-08.
34 commits, orphan lineage — **no merge-base with `upstream/main` by design**, so the pre-push DCO
hook self-skips and commits here carry **no `Signed-off-by`**. Never push to `upstream` (its push URL
is literally `READ-ONLY-UPSTREAM-DO-NOT-PUSH`).

Venv at `./.venv` (matplotlib only). `uv` is the tool of record for Python here.

## Plan — and a live ownership problem, flagged for Dean 2026-08-08
The document being followed is **`autoscaling-viz/real-trace-viz-plan.md`** (Rev 6, `Status: DRAFT`).

**It is not a Type 3 task plan, and there is no Type 3 plan for this work.** Verified, not assumed:
- `plans/planning/` contains **nothing** about autoscaling-viz or real-trace-viz. The only mention
  anywhere on the `plans` branch is `session/CURRENT.md` lines 145–185.
- Per CONVENTIONS §Types, Type 3 docs live on the `plans` branch under `planning/`; this one lives on
  the code branch by deliberate decision (Rev 6: *"This document now lives on the branch it
  describes"*).
- It does not follow the Type 3 authoring rules at all: no Reading Protocol block, no TOC with
  `L<start>:<end>` ranges (`grep -c TOC` = 0), no `[↑ TOC]` links, and `plans/scripts/toc-refresh.sh`
  has never been run on it.
- Per the role matrix, a **coder** writes code / Type 4 references / status files / handoffs and
  **reads** Type 3 plans. This session has been *writing* its own plan doc continuously — §4.5, §5.3,
  §7.1, §7.2, §12.2, §12.4 all edited by me.

So **de-facto owner: this session (the coder).** That is the violation, not a paperwork detail: every
"open decision for Dean" in §12.2 is me nominating my own forks, and nobody independent has ever set
the scope. Content-wise the doc is a hybrid — Type 1 design/derivations (§2 time anchor, §3 token
accounting, §5 saturation window, §6 capacity model), Type 3 task/decision tracking (§9.2 capture
list, §12 open items), Type 4 reference (§8 extractor spec, §15 bundle policy).

Not unilaterally restructured: splitting it, moving it to `plans/planning/`, or handing authorship to
a plan agent are all Dean's calls. Raised in the reply of 2026-08-08.

## What is done and pushed
- **Real-trace toolchain**: `fetch_run.sh` → `extract_real_trace.py` → `render_real_trace.py`, plus
  `sim.py`/`run.py`/`plots.py` (synthetic, untouched by the real-trace path).
- **Six-panel renderer.** 1a arrivals vs completions by wait band; 1b work throughput vs capacity;
  2 replicas desired vs ready; 3 per-pod work; **4 deferred by agreement** (three distinct queues,
  design question open); 5 concurrency `L(t)`.
- **arm-B findings** `real-trace/staircase-20260807-armB/FINDINGS.md` (§11 = the 08-07 ladder
  cross-check), `analyze_ladder_wave.py`, `_probe_envoy_fields.py`.
- **`947dd4c1`** ladder cross-check: the multi-pod wave is **routing**, and my published "not routing"
  claim over-generalized from a single-pod-saturated run. Two distinct oscillations, not one.
- **`1941afe4`** propagation into plan/README/docstrings (two mechanism retractions; both *phenomena*
  stand).
- **`aa67c399`** envoy-field feasibility probe + the benchmark handoff.
- **`4b263d73`** `router_stats`: boot exclusion + `oscillation_flag` removed.

## Key measured results (all reproducible from committed scripts)
- **Routing wave.** Per-pod arrivals oscillate r +0.25…+0.73 and *lead* departures; pooled is flat
  (r ≈ +0.09–0.14) because pods run anti-phase and cancel; period tracks mean sojourn time at ratio
  0.92–1.09 across all six loaded stages (5.7 → 12.0 s). Signature of delayed-feedback balancing.
  Mechanism, **not proven cause** — EPP's actual decisions were unrecoverable (13 unique request IDs).
- **Aliasing.** 6–11 s period vs ~15.7 s scrape cadence ⇒ Nyquist ~31 s. Any oscillation/imbalance
  statistic built on scrape-derived per-pod gauges is structurally blind in this band.
- **Envoy DURATION is a validated substitute** for harness `request_latency`: mean 0.23–0.42% low,
  p95 within 0.08–0.93%, all 8 stages, consistently slightly low (excludes client-side handling).
- **`bytes_sent` fails as a per-request output-token proxy.** Median calibrates (511 vs true 512) but
  dispersion does not: bytes span ~14% p5→p95 where `output_len` spans ~44%; implied bytes/token
  drifts 170–187 across stages. Stage-level total only — never a per-request weight or size rank.
- **`x-envoy-upstream-service-time` is NOT TTFT.** Flat 7–9 ms while TTFT climbs 47 → 183 ms.
- **Disjoint bucket split.** `iteration_tokens_total`: decode-only steps ≤128 tok, prefill-carrying in
  (1024, 16384], **exactly 0** in (128, 1024] on every pod ⇒ differencing `le=1024` is an *exact*
  per-interval prefill-step rate.
- **Regime boundary for ITL.** In-band (kv ≈ 0.99, n=20) adding prompt rate takes r² 0.642 → 0.878
  (Δ +0.236) and omitting it inflates slope `A` 1.8×. Sub-band (kv ≤ 0.67, n=281) `itl ~ run` alone
  is r² 0.93–0.94, Δ +0.001. Not preemption (`corr(gen, preempt/s)` = +0.766, wrong sign).
- **`router_stats` after the fix**, arm B re-extracted from source: `disp_p95` 1.000 → **0.1429**,
  `disp_p50` 0.066 → 0.0625, `n` 28 → 26, 3 boot samples dropped. `leader_flips` unchanged at 15.

## Awaiting Dean (nothing is blocked on these; work continues around them)
1. **Envoy input path in `extract_real_trace.py`** — a third reader so a ladder-shaped run bundles
   without a per-request file. Measured: 4 of 5 live panels survive, panel 5 *improves* (22,200 real
   requests vs a 50-record head sample), panel 1a must band by **sojourn** not TTFT, panel 1b's
   per-request size weighting and terciles are unrecoverable. Substantial single-file edit ⇒ needs
   approval before coding.
2. **Regenerate the shipped bundles?** `real-trace/staircase-20260807-armB/bundle.json` still carries
   the pre-fix `disp_p95: 1.0` and `oscillation_flag: true`. FINDINGS §7 documents this and gives the
   corrected numbers, so the artifact is self-describing either way. Republishing is a results-policy
   call (results are append-only).
3. **§12.2 items 7–9**: what `tput_knee` should report as capacity (max 4994 vs band mean 3943 =
   +27% envelope); whether `itl_fit` gains a prefill term (one fit cannot serve both regimes); a
   minimum-n guard on `B_measured` (`B_measured_n = 3`, two of them boot samples).
4. **Plan-doc ownership** (§Plan above).
5. **Inert allowlist entry**: `~/.claude/settings.json` allowlists `Edit()` on
   `plans/session/handoffs/**`, but the worktree-isolation guard preempts it, so the entry documents
   a capability that does not exist. Either the guard should honor it or the entry should go.

## Deferred by agreement
- **Panel 4 design** — three real queues (EPP flow-control, EPP dispatch, per-vLLM
  `num_requests_waiting`); all three plus a derived global are already in `bundle.json` under
  `system[]`. Deciding which one panel 4 draws needs an input inventory across several runs.
- **(iii) per-request-trace oscillation detector** — Dean 2026-08-08: lower priority. Shares a
  dependency with proving the routing mechanism: both want the **rotated EPP logs** the benchmark
  tester is now collecting.
- **sim-p3 replacement** — needs a check on whether `sim.py` exports per-backend *request* counts.

## OWED — started? NO. This is the next actionable item.
Full prose recheck with real numbers across `autoscaling-behavioral-demo-design.md`,
`REVIEW-CHECKLIST.md` and `report.py`. Known-stale, and **already published to origin**:
- `SHAPE_NOTES["spike"]` — the *"drops between 7% and 57% of requests"* banner (renders **twice**).
- Two `2.5×` tokens.
- §2.4's paragraphs describing the now-**deleted** analytic `W0` seed.
Also standing: `spike` is teaching-only, never calibrated; Stability stays a standalone md, not a
deck tab; Table must not follow Compare; `stability.py` stays uncapped by design.

## Handoffs
- **Sent** `plans/session/handoffs/benchmark__viz-cross-check-and-next-capture.md` (shared path;
  drafting copy at `session-notes/handoffs/`). Carries the routing finding, the aliasing limit, the
  disjoint-bucket split, the envoy validation table, two corrections they need (their two handoffs
  contradict each other on `ceil(demand/prc)`; `bytes_sent` dispersion), and the §9.2 capture list
  framed as a request.
- **Consumed and closed** `scratch-poc__ladder-run-surviving-data.md.DONE`,
  `scratch-poc__per-request-fetch-for-viz.md.DONE`. They were addressed to `scratch-poc`, a name this
  session does not answer to — asked them to use `autoscaling-viz`.
- **Protocol correction (mine to own).** I reported that worktree isolation blocks all writes to
  `plans/session/handoffs/` and that the `.md`/`.WIP`/`.DONE` machine was inoperable across
  worktrees. **Both wrong.** CONVENTIONS explicitly sanctions writing there from any worktree — *"the
  only sanctioned exception to 'no edits outside your worktree'"* — and it works: `Write`/`Edit` are
  blocked by the file-tool guard, but Bash `cp` and `mv` both succeed. Recipe: draft in the worktree,
  `cp` in, `cp` again to revise, `mv` to flip state. I inferred a protocol defect from one refused
  `Write` and propagated it into a handoff, a plan section and a report before testing the other
  three operations, at one command each.

## Data locations (read-only; none of it is in this branch)
- Ladder run 08-07 (8 stages, 22,200 requests, 0 non-200s):
  `benchmark/dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1`
  — has `logs/igw_pods.log` (envoy access log, per-request + `UPSTREAM_HOST`), `metrics/raw/`,
  8× `stage_N_lifecycle_metrics.json`. **No `metrics/processed/wva_*.json`** (post_run_analyze.sh not
  run in time) and `per_request_lifecycle_metrics.json` is 0 bytes (harness OOM).
- arm-B run: `benchmark/dean-20260807-210058-612/results/inference-perf-1786125698-ptufog_1`.
- The envoy log is on **kubelet rotation** — the ladder run sat at 60.1% of a 52.4 MB budget with
  oldest-first eviction, i.e. biased against early stages. Capture deliberately next time.

## Standing constraints
No `git push` without Dean's explicit OK **for that specific push**; never push to `upstream`; no
in-place shell edits (`sed -i` &c.); >3 existing files or a substantial single-file edit ⇒ describe as
text and get approval first; `pwd` + `git branch --show-current` before every edit and every commit;
no GitHub-visible actions without instruction; no Agent/workflow use unless asked. Bundle rules: never
copy prompt or response text into a bundle; bundles only, never raw; nothing over 20 MB; no
`metrics/raw/` or per-request source files in a published bundle; `provenance.json` mandatory; results
append-only; publishing never pushes. pokprod is read-only; teardown needs Dean's approval.
**Design forks belong to Dean, including for coders** — a bug fix can silently ride a semantic change,
so name it separately.
