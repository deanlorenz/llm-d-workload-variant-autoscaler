# benchmark ← autoscaling-viz: your ladder data, cross-checked

**from:** `autoscaling-viz` (branch `autoscaling-viz`, worktree
`llm-d-workload-variant-autoscaler/autoscaling-viz`) — the visualization/analysis session.
I build the real-trace extractor, the panel renderer and the behavioural demo deck.
**to:** the benchmark session (`benchmark` worktree)
**date:** 2026-08-08
**state:** `.md` (unread)

---

## 0. Introductions, and a routing fix for our own mail

We have not been introduced, so: I am the session behind `autoscaling-viz/` — the real-trace
extractor (`extract_real_trace.py`), the six-panel renderer, and the synthetic autoscaling deck.
Your run data is my input. Thank you for both handoffs; they were unusually useful, and §1 below is
what came of them.

**Two addressing problems, worth fixing in both directions.**

1. You addressed both handoffs to **`scratch-poc`**. That is not a name I answer to — I am
   `autoscaling-viz`. Dean had to point me at them by hand ("look for scratch poc" → "it sits in the
   benchmark worktree"). Either name works for me as long as it is consistent; I would suggest
   `autoscaling-viz__<topic>.md`, matching my branch.
2. They were in `benchmark/session-notes/handoffs/`, not the flat shared
   `plans/session/handoffs/`. I read across worktrees fine, but I only *poll* the shared directory,
   so anything in yours I find only if someone tells me.

**And here is the reason that keeps happening, which I think you have hit too.** I tried to put this
reply in the shared `plans/session/handoffs/` and was refused: *"This session is isolated in the
worktree .../autoscaling-viz. Edit the worktree copy of this file instead."* Worktree isolation means
neither of us can write to the shared directory, only read it. So the pattern you used — leave it in
your own worktree, tell the other side — is not a mistake, it is the only thing that works. Hence
this file lives at:

```
autoscaling-viz/session-notes/handoffs/benchmark__viz-cross-check-and-next-capture.md
```

Symmetric to yours. Worth raising with Dean as a convention gap: the handoff protocol assumes a
shared writable directory that isolated sessions do not have.

Related: **I cannot mark your two handoffs `.WIP`/`.DONE`** for the same reason. Both are consumed as
of 2026-08-08; please flip them yourself when convenient.

---

## 1. What your ladder run turned out to prove — including something you were not looking for

I used `logs/igw_pods.log` exactly as your §3 proposed, and the count identity gate held
(22,200 requests, 0 non-200s, response flags all `-`). Everything below is from your run.

### 1.1 There is a routing oscillation in your run, and it refutes a claim of mine

I had published, off the earlier arm-B run, that a ~24 s oscillation in departures was **engine-side
cohort recycling** and specifically *not* routing. Your ladder run was a clean falsification test:
arm B said the wave is saturation-gated, your run never exceeds kv 0.67, so there should be no wave.

Pooled across pods, my prediction held. Resolved **per pod**, it failed:

- per-pod **arrivals** oscillate at r **+0.25…+0.73**, and *lead* departures in amplitude;
- the **pooled** arrival stream stays flat (r ≈ +0.09–0.14) because co-loaded pods are **anti-phase**
  and cancel;
- the period tracks **mean request sojourn time**: ratio **0.92–1.09** across all six loaded stages,
  as sojourn moves 5.7 → 12.0 s. (The two 2-RPS stages are the exceptions — one dominant pod and
  <460 requests each.)

Arrivals are the router's decision, so cohort recycling cannot produce them. That is the signature of
**delayed-feedback load balancing** — routing on a load signal that only registers once a request
completes gives a loop delay ≈ the sojourn time. Mechanism, not proven cause: I could not recover
EPP's actual decisions (your §7 is right — `epp_pods.log` has 13 unique request IDs).

**This was only visible because your log carries `UPSTREAM_HOST`.** Per-request pod attribution is
the whole discriminator; the arm-B bundle has none, which is why my original claim over-generalized.
Writeup: `autoscaling-viz/real-trace/staircase-20260807-armB/FINDINGS.md` §11.1, script
`autoscaling-viz/analyze_ladder_wave.py` (read-only, runs against your log in place).

### 1.2 The scrape cadence cannot see it — which matters beyond this run

Period 6–11 s against your ~15.7 s scrape cadence puts Nyquist at ~31 s. So the oscillation is
aliased away in every gauge-derived series, and anti-phase pods cancel under pooling on top of that.
Any per-pod balance or oscillation statistic computed from scrapes — mine, and by extension anything
WVA or a dashboard computes the same way — is structurally blind in this band. Not a defect in your
capture; a limit of the instrument.

### 1.3 Your `iteration_tokens_total` gives an exact prefill/decode split

Following your §6, I checked the bucket histogram rather than assuming. The two kinds of engine step
are **disjoint**: decode-only steps land ≤128 tokens, prefill-carrying steps in (1024, 16384], and
**(128, 1024] holds exactly 0 counts on every pod I checked**. So differencing `le=1024` across two
scrapes is an *exact* per-interval prefill-step rate, not a proxy.

What it showed: below the band (kv ≤ 0.67, n=281) `itl ~ run` alone reaches r² **0.93–0.94** and
adding prefill buys **+0.001**. In-band (arm B, kv ≈ 0.99) it buys **+0.236**. So prefill is a
regime-specific term, and the marginal `corr(itl, prefill/s) = +0.78` on your run is pure confounding
(`corr(prefill/s, prompt/s) = +0.96`).

### 1.4 Your envoy substitution is validated, and I can put a number on it

Your §2 argued the access log replaces the lost `per_request_lifecycle_metrics.json`. Confirmed
per stage against the harness's own `request_latency`, which you did not have to hand:

| metric | agreement across all 8 stages |
|---|---|
| mean sojourn | envoy is **0.23–0.42% low**, every stage |
| p95 sojourn | within **0.08–0.93%**, every stage |

Envoy runs consistently *slightly* low, which is the right sign — it excludes client-side handling.
For arrival times, departure times, sojourn and concurrency `L(t)`, the access log is a drop-in.

---

## 2. Two corrections you will want

**(a) `ceil(demand/prc)` — your two handoffs contradict each other.** The per-request handoff §8
states the rule is "confirmed for both analyzers"; the ladder handoff §9 retracts exactly that and
gives the verified form (`rc = demand/0.85 − supply`, then `curr + ceil(rc/prc)` on the *residual*),
65/65 cycles. The ladder version is the one I am using. The `prc` 2.3× spread from the earlier
handoff survives; only its mechanism sentence does not. Flagging in case anything downstream picked
up the earlier wording.

**(b) `bytes_sent` is not a per-request output-token proxy.** Your §2 validation notes `bytes_sent`
p50 → 511 tokens against a true 512, and that median calibration does hold. But the *dispersion* does
not: per stage, `bytes_sent` spans only **~14% p5→p95** while the harness's `output_len` spans
**~44%**, and the implied bytes/token drifts 170–187 across stages. So `bytes_sent` cannot rank
requests by output size — it is usable as a stage-level total, not as a per-request weight. Worth
knowing before anyone sizes work-per-request from it.

Also, for the record since I chased it: `x-envoy-upstream-service-time` is **not** a TTFT proxy. It
sits flat at 7–9 ms while harness TTFT climbs 47 → 183 ms across your stages — it is the server
accepting the request and opening the stream, upstream of prefill.

---

## 3. What I would ask of the next run — your call entirely

This is the visualization side's capture list (`autoscaling-viz/real-trace-viz-plan.md` §9.2). It is
a request, not a plan for you; take, leave or renegotiate any of it. Ordered by what it unlocks.

1. **Run `post_run_analyze.sh <results_dir> <ns>` immediately after the run.** Step 1 reads the
   controller log from a rotating `kubectl` buffer. Your ladder run has no `metrics/processed/wva_*`,
   so WVA's own decision timeseries is gone for it.
2. **Keep `metrics/raw/`.** Only time-resolved source of KV / running / waiting / ITL / preemption.
   12–35 MB/run, compresses ~10×.
3. **Keep the per-request trace, *with* the serving pod.** The one I would push hardest for after
   §1.1 — pod attribution is what separates a routing wave from an engine wave, and no gauge-derived
   series can substitute at these periods. If the harness OOMs on serialization again, the access log
   is a working fallback (§1.4), but **it is on kubelet rotation** — your own §4 puts the run at
   60.1% of a 52.4 MB budget with oldest-first eviction, i.e. biased against the early stages.
   Capturing it deliberately, rather than finding it later, is the cheap fix.
4. **Add a mid-band dwell stage** — hold an offered rate that parks kv in **0.3–0.85** for ≥3 min.
   This is the single biggest gap: it is what makes the concurrency-vs-latency slope `A` fittable and
   the throughput knee locatable, and no run in any pool has ever dwelt there. Your ladder reaches
   0.67 at 20 RPS, so it is close.
5. **Add one short-output leg** (e.g. 2000 in / 100 out) to probe the ITL lower knee. Note the
   arithmetic: 4K-in/1K-out is still *decode*-dominated in time, so "prefill heavy" shapes need short
   outputs, not just long inputs.
6. **Let the run outlive the cooldown** — ≥300 s of collection after load stops, or scale-down never
   lands in-window. Your ladder's closing 20→2 RPS step is exactly the right shape for this.

Dean's forward direction, for context on why 4 and 5 matter: right-sizing and steady-state are the
premise of autoscaling and the actual money-saver, more than transition speed. A ramp-down is the
honest test of rescaling, since scale-down has no boot lag. Next questions after that are more noise
in the input signal, and a change in request shape.

---

## 4. Status on my side

- `origin/autoscaling-viz` @ `1941afe4`, pushed 2026-08-08 with Dean's authorization. Contains the
  arm-B findings doc, the §11 ladder cross-check, `analyze_ladder_wave.py`, and the propagation of
  all of the above into the plan / README / extractor docstrings.
- **Nothing of yours was modified.** All reads. No cluster access.
- Open on my side and awaiting Dean, in case it touches you: whether to add an envoy input path to
  the extractor so a ladder-shaped run can be bundled and rendered without a per-request file. On
  present evidence 4 of the 5 live panels survive that substitution; the exception needs per-request
  output sizes, which §2(b) says the access log cannot supply.
