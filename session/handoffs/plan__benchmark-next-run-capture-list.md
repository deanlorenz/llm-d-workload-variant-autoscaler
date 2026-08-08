# plan ← benchmark: next-run capture + scenario changes for `ta-pokprod-testing-plan.md`

**to:** the benchmark/TA testing planner (owner of `plans/planning/ta-pokprod-testing-plan.md`)
**from:** the `benchmark` session (branch `benchmark`, worktree
`llm-d-workload-variant-autoscaler/benchmark`) — the one that builds and runs the harness on
pokprod in `dhl-wva-209`.
**date:** 2026-08-08
**state:** `.md` (unread)
**asks for:** an update to `plans/planning/ta-pokprod-testing-plan.md`. Items in §3 change the
ladder itself, which is not mine to change.

> Delivery note: this session cannot use its editor to write into the shared checkout (worktree
> isolation refuses it), so the authored copy lives at
> `benchmark/session-notes/handoffs/plan__benchmark-next-run-capture-list.md` and this is a `cp` of
> it — the same channel used to sync `plans/session/status/benchmark.md`. The two are identical.
> For the same reason I cannot flip this file to `.WIP`/`.DONE` afterwards; the recipient should.

---

## Why this exists

The 8-stage ladder run of 2026-08-07 is analysed and its data has now been independently
cross-checked by the visualization session (`autoscaling-viz`). That cross-check produced a
capture list for the next run. Three of the items are harness-side and I will implement them; three
change the workload scenario and belong in the plan.

Sources, in order of authority:

- `benchmark/session-notes/status/benchmark.md` **§17.11** — my record of the cross-check, with
  the numbers and the reasoning behind each item. §17 as a whole is the ladder-run analysis;
  §17.8 is the consolidated open-items list.
- `autoscaling-viz/session-notes/handoffs/benchmark__viz-cross-check-and-next-capture.md`
  (committed `aa67c399` on branch `autoscaling-viz`) — the cross-check itself; its §3 is the list.
- `autoscaling-viz/real-trace-viz-plan.md` §9.2 — their standing capture requirements.

Note on locating those: both are in **other worktrees**. Read them with
`git show <branch>:<path>` or by absolute path; do not `cd`.

---

## 1. The one finding that should drive the plan, not just the capture list

The ladder run contains a **routing oscillation** with a period of **6–11 s**, tracking mean
request sojourn time (ratio 0.92–1.09 across all six loaded stages as sojourn moves 5.7 → 12.0 s).
Per-pod arrivals oscillate at r **+0.25…+0.73**; the *pooled* arrival stream looks flat
(r ≈ +0.09–0.14) because co-loaded pods run anti-phase and cancel.

Two consequences for how we plan measurement:

1. **Our scrape cadence cannot see it.** At ~15.7 s between scrapes, Nyquist is ~31 s. Anything in
   this band is aliased away in **every gauge-derived series** — ours, and by extension anything
   WVA or a Grafana panel computes the same way. Pooling hides it a second time.
2. **Only a per-request trace carrying the serving pod can see it.** It was visible solely because
   the gateway access log records `UPSTREAM_HOST`. This is why §2's per-request item is not a
   nice-to-have.

I would suggest the plan say this explicitly wherever it specifies metrics collection, because the
natural assumption — that a finer scrape rate or a per-pod gauge would do — is false here.

## 2. Harness-side — mine, listed so the plan can rely on them

No planner action needed; tracked in my §17.8.

- **Gateway access-log follower.** Built (`hack/benchmark/gateway-log-follower.{sh,yaml}`),
  namespace-scoped and read-only, writes to the PVC so a per-request trace survives kubelet log
  rotation and survives the operator's laptop closing. **Not yet applied** — the local permission
  classifier blocked the `kubectl apply`; it needs Dean to run it or grant the rule. Until it is
  applied, a per-request trace is again a bet against rotation.
- **Run `post_run_analyze.sh <results_dir> <ns>` immediately after the run**, and add
  controller-log capture to the harvest path. The ladder run has no `metrics/processed/wva_*`, so
  WVA's own decision timeseries is gone for it — the controller log is read from a rotating buffer
  and the post-run step was not run promptly.
- **Keep the per-request trace with the serving pod**, per §1.
- **Retention scope sharpened.** The multi-GB per-replica files go; **`metrics/raw/` stays**
  (12–35 MB/run, compresses ~10×, and the only time-resolved source of KV / running / waiting /
  ITL / preemption). If the plan states the retention rule anywhere, it should carry this
  exception, because a blunt reading of "delete the big data" would take it.

## 3. Scenario changes — the actual ask

These need Dean's agreement and a plan edit. Ordered by what they unlock.

### 3.1 A mid-band dwell stage — the largest gap

Hold an offered rate that parks KV utilisation in **0.3–0.85** for **≥3 min**.

The viz session calls this their single biggest gap, and I agree with the reasoning: it is what
makes the concurrency-vs-latency slope fittable and the throughput knee locatable, and **no run in
any pool has ever dwelt there**. Every run we have is either sub-saturation (our ladder tops out at
kv 0.67 at 20 RPS) or pinned at kv ≈ 0.99 (arm B). The interesting region is between them, and it
is precisely the region an autoscaler is supposed to hold a service in.

Our ladder is close, so this is likely a short extension rather than a new scenario: another rung
or two above 20 RPS, held long enough to be a dwell rather than a step. The exact rate should be
found by measurement, not predicted — the relationship between offered RPS and KV is what we are
trying to characterise. I can run a short probe to locate it if the plan wants a number first.

### 3.2 One short-output leg

E.g. **2000 in / 100 out**, to probe the ITL lower knee.

The arithmetic is the point: 4K-in/1K-out is still **decode**-dominated in time, so our current
"long input" shapes are not prefill-heavy in any useful sense. Prefill-heavy needs *short outputs*,
not just long inputs. Related: on our run, `itl ~ running` alone reaches r² 0.93–0.94 below the
band and adding prefill buys **+0.001**, whereas in-band it buys **+0.236** — prefill is a
regime-specific term, so a shape that isolates it is worth having.

### 3.3 Let the run outlive the cooldown

**≥300 s of collection after load stops**, or scale-down never lands inside the measurement
window. Our closing 20→2 RPS step is already the right shape; it is the collection window that
needs extending, not the load profile.

This also matters for Dean's stated forward direction, relayed via the cross-check: **right-sizing
and steady-state are the premise of autoscaling and the real money-saver, more than transition
speed**, and a ramp-down is the honest test of rescaling because scale-down has no boot lag. If
that is the priority, the plan's emphasis may want to shift from step-response timing toward
sustained correct sizing — which is 3.1 plus 3.3 together. Dean's call; flagging it because it
reads like a change of emphasis rather than an added stage. Named next after that: more noise in
the input signal, and a change in request shape.

## 4. Two corrections to propagate if the plan quotes either

- **The decision rule.** If anything in the plan (or anything derived from my earlier per-request
  handoff) says the engine computes `ceil(demand/prc)`, that is **wrong and was retracted**.
  Verified form, 65/65 cycles: `rc = demand/0.85 − supply`, then `curr + ceil(rc/prc)` applied to
  the *residual*. My own two handoffs contradicted each other on this; the ladder one is correct.
  Details in §17.11(a) and §17.5.
- **`bytes_sent` is not a per-request output-token weight.** The median calibration holds (511
  implied vs a true 512) but the dispersion does not — ~14 % p5→p95 vs `output_len`'s ~44 %, and
  implied bytes/token drifts 170–187 across stages. Stage-level totals only. Likewise
  `x-envoy-upstream-service-time` is **not** TTFT (flat 7–9 ms while harness TTFT climbs
  47 → 183 ms). Both are now caveated in `session-notes/scratch/envoy_per_request.py`.

## 5. Not part of the ask

- Nothing here needs a cluster action, and no run is proposed. Dean's standing rule holds: **wait
  for his approval before any run.**
- The GPUs from the ladder run are released; one GPU remains held by the decode replica's
  `minReplicas=1` steady state, which is a separate open question in my §17.8 item 3.
