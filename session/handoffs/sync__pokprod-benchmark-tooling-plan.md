from: plans (planner session — owner of `planning/ta-pokprod-testing-plan.md`)
to: sync
session: pokprod-benchmark-tooling-plan

## What changed

`planning/ta-pokprod-testing-plan.md` (Type 3) grew from ~1003 → **1457 lines** across two
sittings on 2026-08-07/08. **Four new sections** (§2b, §2c, §5.7, §7.6 + §7.6.1, §9.1) and six
updated ones. No code touched, no cluster contact, no pushes, nothing outside `plans/`.

Also on the plans worktree: two refs-only coder triggers written, two planner-addressed handoffs
consumed to `.DONE`.

**Commit:** see the commit that lands alongside this handoff on `plans` (the plan doc + the four
handoff files). `plans` also still carries the **unpushed** `e5f3abf1` + `f29e86ae` from earlier
sessions — force-nothing, just not yet pushed; every push needs Dean's per-push confirmation.

### The framing change that drives everything else

Dean, 2026-08-08: *"This is more than just a test plan it is also a test tooling plan."* The doc is
now both. §1 carries an update block recording the harness as-built (33 files under
`hack/benchmark/`, 22 branch-added; `benchmark` branch **9 commits ahead of `origin/benchmark`, all
local**) and the two runs of record (08-03 staircase, 08-07 8-stage ladder — both single-variant;
two-variant built but never run).

### New sections

- **§2b Two-fork contract.** Dean's rule: the **llm-d-benchmark fork holds guards only**; tools +
  Makefile + `hack/` belong to **WVA** (his WVA fork is *"a temp measure"*). Audit of the fork's four
  commits: `963bb00` ✓ guard, `e88b882` ✓ guard, `7a1b478` ✗ tooling, `cfe6088` ✗ tooling. Migrating
  the two violators leaves the fork at 2 commits / 3 files, all under `standup/`. (`50c8da8` +
  `6d5ff6b` are Ofer's — not cleanup items.)
- **§2c Configuration contract.** `Makefile:45`'s `-include` is **fail-open**, so a missing `.env`
  is silently tolerated and `?=` defaults take over. Replaced by a **fail-closed, kube-context-keyed**
  `.env` (`hack/benchmark/env/<context>.env`) plus a `WVA_ENV_CONTEXT`/`_SERVER`/`_NAMESPACE`
  assertion triple, arm-derived `BENCHMARK_REPO_REF`/`BENCHMARK_SPEC`, and a wizard
  (`make benchmark-configure`) with an **on-branch** skill. Dean's ordering constraint is recorded
  verbatim: *"safely running in a shared cluster is the most important thing."* Also fixes the
  preflight call-site gap — defined at `Makefile:579-587`, called from **one** site (`:604`), with
  twelve other NS-requiring targets uncovered.
- **§5.7 The KEDA arm is present but unrunnable** — three verified blockers (spec absent from every
  reachable ref; the KEDA path selects an **unguarded** ref; the clone-safety branch is lossy), plus
  two cosmetic defects. Written as a **prerequisite**, not a sub-task: T2 gates T3. Dean's *"we need
  to KEDA benches too"* is what makes this blocking rather than informational.
- **§7.6 + §7.6.1 The dwell is a controller-configuration lever, not a workload lever** — the
  substantive finding of this session; see below.
- **§9.1 Tooling track** — T1–T11 with an owner per row. **T9 and T10 are Dean's**, not the coder's.

### The §7.6 finding — worth a line in CURRENT

An addendum handoff from the benchmark coder showed that **§7.4.1's stated mechanism cannot deliver
§7.4.1's stated goal.** Under a tracking controller, steady-state KV is a **controlled** variable —
closer to rate-*invariant* than rate-proportional — so "hold an offered rate that parks KV in
0.3–0.85" asks the workload profile to do what only the analyzer configuration can do. The
observation the ask was built on is a fact about configuration, not rate: the 08-07 ladder sat at
kv 0.67 because TA dominated the combine and provisioned **ahead of** saturation; arm B hit kv ≈ 0.99
because its `ScaledObject` was capped at **2 replicas**. §7.4.2 (the ITL-knee leg) has the same defect
more sharply — a knee is a property of load *per replica*, and the autoscaler's job is to keep load
off the knee.

**One decision is now Dean's and blocks §7.4.1:** (a) saturation analyzer alone, **uncapped** — its
own 0.85/0.70 watermarks put steady state *inside* the band by design, costs no extra requests, but
measures SAT's right-sizing rather than the combined optimizer's; or (b) a deliberate replica cap —
guaranteed, but it **measures the cap**, which is why the ladder rejected one. Coder and planner both
recommend **(a)**. A fallback needing no decision is already staged (replica-quantization sawtooth:
20 and 26 RPS × 360 s, 1.3× apart, the 20 RPS rung retained as a deliberate control) — so the run is
informative either way.

## Update CURRENT.md

**§ Recent activity — add one active abstract** (this thread has none; the existing 2026-08-07
autoscaling-viz item is a *different* thread and must not be overwritten):

> **2026-08-08 — pokprod benchmark: the Type 3 is now a tooling plan as well as a test plan; the
> mid-band dwell turns out to be a controller-configuration decision, not a workload one.**
> `planning/ta-pokprod-testing-plan.md` → 1457 lines, four new sections. Dean's **guards-only fork
> split** is now contractual (§2b: harness fork = guards; tools/Makefile/`hack/` = WVA; 2 of the
> fork's 4 commits violate it and migrate out, leaving 2 commits / 3 files). The `.env` contract is
> **fail-closed and kube-context-keyed** with a `WVA_ENV_*` assertion triple, arm-derived
> refs, a wizard + on-branch skill, and preflight spread from **one** call site to six (§2c) — Dean's
> constraint: *"safely running in a shared cluster is the most important thing."* Doc surface
> collapses to **one runbook** (§5.5 item 4). The **KEDA arm is present but unrunnable** — three
> verified blockers, a prerequisite rather than a task (§5.7). **§7.6 is the substantive finding:**
> steady-state KV under a tracking controller is a *controlled* variable, so §7.4.1's dwell cannot be
> reached by raising the offered rate — the 08-07 ladder's kv 0.67 and arm B's kv 0.99 are facts about
> configuration (TA provisioning ahead of saturation; a 2-replica cap), not rate. **Dean owes one
> decision:** (a) saturation-alone-uncapped *(recommended by coder and planner)* vs (b) a deliberate
> replica cap — or defer both behind the already-staged quantization-sawtooth run (20 + 26 RPS ×
> 360 s, 20 RPS retained as a control, informative either way). Nothing launched, no cluster contact,
> nothing pushed. Cold resume: **§7.6.1** (staged status, four preconditions, ordered next steps) and
> **§9.1** (T1–T11 with owners).

**§ Blocked on — add:**

> - **The staged pokprod dwell run** is blocked on, in order: Dean's §7.6 (a)/(b) answer (or an
>   explicit deferral), Dean applying the gateway access-log follower (§9.1 **T9** — the coder's
>   permission classifier blocks the `kubectl apply`, and without it every per-request trace is a bet
>   against log rotation), the coder's four preconditions (§7.6.1), and finally Dean's run approval.

**§ Benchmark section — append a pointer**, don't rewrite it: the pokprod Type 3 now carries a
tooling track (§9.1 T1–T11) and a cold-resume block (§7.6.1); the existing methodology-pivot text
stays accurate.

**§ Pending handoffs table:**
- **Remove** `plan__benchmark-next-run-capture-list.md` and `plan__benchmark-dwell-operating-point.md`
  — both consumed by this session and renamed `.DONE` (they were never listed, but if either got
  added, drop it).
- **Leave alone**: `plan__ta-anchor-doc-taxonomy-findings.md` and
  `plan__ta-anchor-dataflow-map-pr1-delta.md` — both still **OPEN**, both belong to the anchor thread,
  **not sync's to consume**.
- Two new refs-only coder triggers are open and awaiting the benchmark coder:
  `benchmark__pokprod-plan-tooling-track.md` and `benchmark__dwell-operating-point-in-plan.md`. The
  coder owns their `.WIP`/`.DONE` transitions. Also still open from before:
  `benchmark__observability-plan.md`, `benchmark__tier-a-image-moved-to-main-tip.md`,
  `benchmark__viz-cross-check-and-next-capture.md`.

**§ Next steps — add a row** for the two Dean-owned tooling items so they don't get lost in the plan:
§9.1 **T9** (apply the gateway log-follower — Dean personally) and **T10** (file upstream
llm-d-benchmark issues for the two guards — later, Dean's call, after T2 isolates them).

## Open questions / follow-ups

- **Unconfirmed by the planner:** the coder reports Dean **approved all three** §7.4 scenario asks and
  has implemented two workload files. I did not encode that as fact — §7.4 keeps its **OPEN** marker
  and §7.6 records the claim as a claim. If Dean confirms, §7.4's status line should flip and this is
  the note to act on.
- **§5.5 item 4** leaves one call open: fold-and-**delete** vs fold-and-**stub** for
  `docs/two-variant-wva-pokprod-runbook.md` (405 lines, fork-owned). Recommendation: delete.
- **Reportable, not actionable** (unchanged from the prior sync, restated so they don't decay):
  `"path": "."` in `wva.code-workspace` defeats worktree confinement; `publish_result.sh --commit`
  still targets the retired `viz-results` branch (`BRANCH="viz-results"`, line 28); the harness
  clone has a dirty `output_token_correction.py` plus a stray `.bak`; `session-notes/` (29 files)
  would ship to Ofer as-is.
- **One GPU remains held** on pokprod by the decode replica's `minReplicas=1` steady state — the
  ladder run's other GPUs are released. Separate open question (coder's §17.8 item 3).
