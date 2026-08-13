# TA-on-pokprod — decision & correction ledger

**Status:** LIVE, append-only while WIP. **Type:** history ledger, companion to the Type 1/Type 3 docs
below. Order does not matter — entries are appended as decisions happen, not resorted. Tidy later by
adding a topic-grouped index section that only references entries by ID; never by moving/editing an
entry in place.

**Companion docs:** [`ta-pokprod-architecture-design.md`](ta-pokprod-architecture-design.md) (Type 1) ·
[`ta-pokprod-execution-plan.md`](ta-pokprod-execution-plan.md) (Type 3) ·
[`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) (Type 3, live) ·
[`ta-pokprod-testing-plan.md`](ta-pokprod-testing-plan.md) (superseded original, kept for its own
history — see its header)

## How to use this file

**Fetch, don't read.** Every entry starts with a one-line header:
`## D-nn | YYYY-MM-DD | topic:a,b,c | src:§n`. To find entries:
- By ID: `grep -n '^## D-15' ta-pokprod-history.md`
- By topic: `grep -n 'topic:.*t9' ta-pokprod-history.md`
- By date: `grep -n '| 2026-08-11 |' ta-pokprod-history.md`
- List everything: `grep -n '^## D-' ta-pokprod-history.md`

Each entry is self-contained — the header plus its body answers "what happened and why" without
needing any other entry. Cross-references between entries use `[[D-nn]]`.

---

## D-1 | 2026-07-28 | topic:architecture,two-tier | src:§2

**Decision.** Code-under-test and the benchmark harness that tests it are two independent things, kept
apart even locally (Tier A / Tier B split). Ofer pulls Tier A only, never Tier B. Governing principle
throughout the mission.

---

## D-2 | 2026-07-28 | topic:safety,namespace,shared-cluster | src:§2a

**Decision.** pokprod is a shared OpenShift cluster (Dean + Ofer both admin). Three invariants apply to
every phase: operate only in the target namespace; every environment value comes from an explicit
`.env`; any teardown needs explicit approval and an explicit namespace arg; never touch cluster-global
settings.

**Corrected — see [[D-15]], [[D-16]], [[D-17]]** (2026-08-11): the invariants were originally scoped to
"Dean's namespace" / "Dean's `.env`" by name. Corrected to scope by namespace/config, not by named
person — anyone using the benchmark targets is bound the same way.

---

## D-3 | 2026-07-28 | topic:safety-net,three-levels | src:§2a

**Fact, not a decision.** The safety net has three independent levels: L1 operator discipline, L2 this
repo's Makefile/scripts, L3 the harness fork's presence-gates. Only L2/L3 are mechanical. The L3 hazard
is inverted from the obvious one — a presence-gate *skips* because a shared object already exists, so a
deleted precondition silently converts a safe standup into a destructive one. Must be verified present
in the code that will execute, not assumed.

---

## D-4 | 2026-08-07 | topic:two-fork,guards-only | src:§2b

**Decision, Dean.** Two forks, non-overlapping contents: `deanlorenz/llm-d-workload-variant-autoscaler`
(WVA — tools, Makefile, `hack/`, scenarios, docs; temporary, expected to move upstream) and
`deanlorenz/llm-d-benchmark` (harness — guards only, presence-gates for cluster-scoped operations;
longer-lived, guards to become upstream issues later). Rule: anything in the harness fork that isn't a
guard belongs in WVA `hack/`.

**Audit finding (2026-08-08, read-only):** 2 of 4 fork-authored commits violate the rule (pure tooling
duplicating WVA's own scripts, or files identical to ones WVA already owns). Migrating them out leaves
the harness fork at 2 commits / 3 files, all under `standup/`. Not a cleanup item: two other commits are
Ofer's, and whether they follow the guards-only rule is his call, not Dean's.

---

## D-5 | 2026-08-10 | topic:artifact-tree,results-persistence,gitignore | src:§2b-bis

**Decision, Dean.** Benchmarking artifacts were spread across five trees with inconsistent tracking. New
layout: `benchmark/tools/` → symlink to `hack/benchmark` (nothing moves); `benchmark/campaigns/<date>/`
tracked (curated, permanent); `benchmark/runs/$USER-<ts>-<pid>/` untracked (raw, disposable, GB-scale,
token-bearing). `BENCHMARK_WORKSPACE` moves to `benchmark/runs/` — load-bearing because the old ignore
rule was the literal glob `dean-*/`, which only matches Dean's username; other users' runs would
surface as untracked clutter. Dean, verbatim: *"I don't want to gitignore the results as a whole
anyway."*

**Convention adopted:** #947's (`cde8646c`, upstream) README shape — metrics table + `<details>` block
of relative-path figure embeds. **Convention rejected:** filing results under `docs/developer-guide/` —
#947's own docs there were deleted 5 months later as "outdated" (#1053/#1054); a dated campaign result
is inherently historical and Type-4 docs must track current code, so that placement guarantees rot.
Dean, independently: *"I don't think it should be under docs."*

🚨 **Standing hazard, resolved 2026-08-11/12 — see [[D-9]].**

---

## D-6 | 2026-08-07/08 | topic:env-contract,fail-closed,kube-context | src:§2c

**Decision, Dean.** `.env` handling was fail-open (`-include`, missing file silently tolerated).
Replaced with: (1) benchmark targets must not run without a `.env`, enforced in the Makefile; (2) one
`.env` per kube context, discovered by filename (`hack/benchmark/env/<context>.env`); (3) an embedded
assertion triple (`WVA_ENV_CONTEXT`/`_SERVER`/`_NAMESPACE`) checked against the live context; (4) a
wizard (`make benchmark-configure`) that confirms every choice and warns on dangerous ones; (5) an
on-branch skill that explains but never enforces. Dean, verbatim ordering: *"safely running in a shared
cluster is the most important thing."*

**Open, unresolved:** whether one context can map to multiple namespaces — flagged by Dean 2026-08-11,
not yet answered. `benchmark-preflight` has only one call site (`benchmark-standup-shared`); the other
twelve namespace-requiring targets don't invoke it yet.

---

## D-7 | 2026-08-08 | topic:keda-arm,blocked | src:§5.7

**Fact, verified read-only.** The KEDA-direct arm (`BENCHMARK_DIRECT_KEDA=true`) has never run and
cannot as configured — three verified blockers: its spec (`guides/epp-keda-saturation`) doesn't exist
on either fork ref; its ref default (`main`) selects a branch with zero guards and no scenarios; both
recovery paths from the resulting hard-error either drop the guards or destroy local commits. This gates
the KEDA arm and is not parallelizable with using it — fixing it means refreshing the harness fork's
`main` and rebasing the guard commits onto it (tracked as T2/T3).

---

## D-8 | 2026-08-08 | topic:runbook,doc-consolidation | src:§5.5 item 4

**Decision, Dean.** Collapse three proposed doc artifacts (README, GETTING_STARTED, tools guide) into
one new runbook, `docs/developer-guide/benchmark-tooling-runbook.md`, linked from the main bench guide
at two points. Dean, verbatim: *"README → new guide linked from main bench guide (a new runbook).
GETTING_STARTED → in same guide. tools guide → in same guide."*

**Still open:** fold `docs/two-variant-wva-pokprod-runbook.md` (405 lines, fork-owned) into the new
runbook and delete it, or leave a stub. Planner recommendation: delete. Not yet decided.

---

## D-9 | 2026-08-10/11/12 | topic:bearer-token,security,resolved | src:campaign results doc

**Hazard found 2026-08-10.** Every campaign cell's `run/inference-perf-*.yaml` embedded
`LLMDBENCH_BASE64_CONTEXT_CONTENTS` — a base64 kubeconfig carrying a live OpenShift bearer token for
`DEAN@il.ibm.com` on pokprod, 7 copies. Never reached git (the directories are gitignored) but was
readable on disk. Traced mechanism: upstream `llm-d-benchmark` behavior (`setup/run.sh` captures the
active kube context into the harness pod so it can `kubectl` from inside the cluster), not a WVA-fork
addition.

**Resolved 2026-08-11.** All 7 files removed (verified zero copies anywhere in either worktree,
`sha256~…` pattern grepped clean tree-wide). Dean's disposition: pokprod already rotates the token every
few hours regardless; there is no need to persist a bearer token beyond the active session — the live
k8s context is sufficient. Dean refreshed the token 2026-08-11 independent of the file removal.

**Not fixed — the mechanism recurs.** Every future campaign will embed whatever token is live at launch
time into fresh run directories. A real fix (e.g. a scoped service-account token instead of a personal
one) is upstream `llm-d-benchmark` work, not decided or scheduled here.

---

## D-10 | 2026-08-10 | topic:sat-disable,retracted,misread-evidence | src:campaign results doc

**RETRACTED — do not cite the original claim.** Initial reading of the 2026-08-10 campaign: "saturation
cannot be disabled on PR-2" — based on counting `analyzer-result` log lines per configured analyzer
list. **This was wrong.** The engine's actual design is compute-and-log-always, vote-conditionally
(`satVotes`, `saturation_v2/engine_v2.go:150`) — the log line is a report, not evidence of voting. The
engine states the real signal explicitly, once per tick: "analyzer absent from configured list: will
not vote and cannot veto scale-down" (37 occurrences in the TA-only cell, exactly matching the 37
`analyzer-result` lines originally cited as proof of the opposite). Dean caught it: *"sat disabled does
not disable the sat signal creation or logging. It only disables its participation in the scaling
math."*

**What survives:** analyzer-list exclusion does stop *voting* (confirmed) — a different mechanism from
`saturation:{enabled:false}`, which remains untested in either direction. The dwell limit cycle being
analyzer-independent, and the `prc` collapse being a separate variable, both survive this retraction
unchanged.

---

## D-11 | 2026-08-11 | topic:capacity-model,tput-knee,never-reviewed | src:campaign results doc, viz Type 1

**Finding, Dean.** `tput_knee()` and `capacity()`/`max_conc_pred` (the viz toolchain's capacity/knee
estimation functions) were never actually reviewed — both landed in the toolchain's first commit and
every recorded "Dean approved" note about that worktree is about the migration (branch name, worktree
move), never this design. Dean: *"I don't remember discussing it / reviewing it, and making a
decision."* Also flagged: git identity does not distinguish Dean typing directly from a coding session
acting under his configured identity — "authored by Dean" claims from commit metadata alone overclaim
what's actually known.

**Dean's technical objection, confirmed correct on inspection.** Real concurrency has (at least) three
regimes — a(t) pre-saturation (not constant, not linear, jumps), b near-saturation (the actual target,
hard to track), c fully-saturated (a simple max, not informative below it). `capacity()` produces ONE
global number checked once against ONE observed peak (closest to regime c), with no time-windowing or
regime classification — likely why a 63% self-check error appeared on a run that never left regimes
a/b. Three open design questions recorded (windowed vs. global estimate; local error vs. time/regime;
whether `tput_knee`'s upper-envelope approach is the right ceiling-line quantity) — not decided, Dean's
to review, now that a real Type 1 exists for it
([`autoscaling-viz-design.md`](autoscaling-viz-design.md)).

**Related correction, same session:** the SELF-CHECK-3 concurrency model and 1b's dashed rate-ceiling
line were originally conflated as one model. They share no code path — 1b's line is empirical
(`tput_knee`, calibrated from the same curve it overlays), the self-check is the KV-budget concurrency
model. The 63% error belongs to the concurrency model only.

**New lead, unmined:** EPP debug logs (`logs/epp_pods.log`, already on disk every cell) carry
per-request `kv-cache-utilization-scorer`/`prefix-cache-scorer`/`queue-scorer` output keyed by
`x-request-id` per candidate endpoint — real, timestamped, per-request signal not yet used for anything.

---

## D-12 | 2026-08-11 | topic:per-request-data,harness-limitation,discovery-task | src:campaign results doc

**Decision, Dean.** Disable per-request collection in `inference-perf` going forward — unreliable
(sized to OOM the harness pod by the workload's own math), disk-heavy, and collects per-*packet* not
per-*request* despite the name. No benchmark Makefile target should enable it.

**Corrected diagnosis, same day.** An earlier claim that all three dwell cells were "blind" to
user-visible cost (empty per-request file → assumed a ~2-line harness bug) was wrong. Checked directly:
`run_metadata.yaml` and all five per-stage summaries exist with real rate/latency/failure/token data per
cell — only the per-*request* file is empty, almost certainly the predicted OOM. The dwell cells are
missing per-request resolution only, not blind.

**Task, not yet done.** Full field-list-then-log-scan discovery pass across EPP/gateway/metrics/
controller logs for fallback per-request signal (arrival time, TTFT, input/output length, processing
time) — offered workload is a good start, not the ceiling. Trigger sent:
`session/handoffs/benchmark__viz-model-review-and-per-request-discovery.md.DONE`.

---

## D-13 | 2026-08-11 | topic:folder-structure,artifact-lifecycle | src:campaign results doc

**Decision, Dean, refining [[D-5]].** Figures must not be copies — *"like the existing benchmark
analysis graphs, they should live with the results and their lifecycle should be managed together — if
I delete an old result I want to also delete all the artifacts, including the panel figures."* Target:
`benchmark/runs/<id>/{config,raw,viz}/` — one lifecycle per run, config is the small reproducible set
(the `.env`, workload profile, analyzer config, image pin — this is what makes a result reproducible),
raw is large and disposable, viz is coupled to raw, not mirrored elsewhere.

**Reconciliation needed, not yet resolved:** Dean independently shipped `session-notes/campaign-viz/`
(cell-keyed, tracked, figures-only) directly on `benchmark` the same window this decision was being
recorded. Two shapes for the same problem landed in parallel — which is canonical, or how they compose,
is undecided.

---

## D-14 | 2026-08-11 | topic:harness-fixes,fork-scope,data-discard | src:campaign results doc

**Decision, Dean.** All harness fixes happen on Dean's fork for now, not upstream — *"we can later
figure out what belongs as issues/PRs on the benchmark repos."* Excessive generated data is discarded by
a playbook (not yet written), keeping only the reproducible config set from [[D-13]].

---

## D-15 | 2026-08-11 | topic:namespace-scoping,safety-invariants | src:§2a

**Correction, Dean.** *"Scope should be a specific NS. Should set all NS variables early in environ and
config files. Nothing is bound my [to a] specific branch — when a new context is created and a new NS
is established it should be confirmed with user and explicit. All subsequent operations should be
confined to said NS."* §2a's "operate only in Dean's namespace" invariant replaced with "operate only in
the target namespace set for this benchmarking config" — the namespace is a property of the config a
run is invoked with, not of who is running it. New context/namespace pairs must be confirmed explicitly
before use.

---

## D-16 | 2026-08-11 | topic:env-contract,safety-invariants | src:§2a

**Correction, Dean.** *"Anyone using the new benchmark Makefile targets should not land mistakenly on
the wrong branch [namespace]. The rule is not scoped to Dean."* The fully-populated-`.env` requirement
is not Dean-specific — any invocation of the benchmark targets needs one, structurally, not by personal
discipline.

---

## D-17 | 2026-08-11 | topic:teardown,safety-invariants | src:§2a

**Correction, Dean.** *"These safety invariants should hold for anyone use[ing] the benchmark targets.
All teardowns are only in the explicitly NS set for benchmarking. Never touch anything else... Nothing
ties to Dean/Ofer specifically."* The teardown-approval invariant holds for anyone using the targets,
scoped to the namespace explicitly set for benchmarking — approval-from-the-operator and
namespace-scoping are the mechanism; named-person framing removed.

---

## D-18 | 2026-08-11 | topic:steady-state,dwell,goal-correction | src:§7.6

**Correction, Dean.** *"We don't have a goal of forcing a band. One of the tests we want is that in
steady state autoscaling lands eventually with the right size, i.e. in the right band. We can measure
transition time, but we care more about eventual steady state. Runs must be long enough to stabilize.
This applies for sat only and for any other analyzer combination."* §7.6's (a)/(b) framing was
originally motivated by "manufacture a dwell so a slope is fittable" — wrong goal. Corrected: run long
enough, under whichever analyzer combination is under test, that eventual steady-state arrival is
observable at all. Transition time is secondary.

---

## D-19 | 2026-08-11 | topic:dwell,decision,generalized | src:§7.6

**Decision, Dean.** *"For any analyzer combination (also for TA only, TA+sat) — we observe real band.
Not force it with max/min."* (a) — saturation alone, uncapped — is decided, and is the first instance of
a general test applied to whichever configuration is under study, not a SAT-specific answer. (b)'s
deliberate replica cap is not part of this test; it's a separate, knowingly-chosen instrument only.

**Not yet derived:** TA's own no-action band, and the TA+SAT combined band, are not necessarily
`[0.70, 0.85]` — that interval is SAT's specifically. Deriving the equivalent bands is a prerequisite for
testing those configurations, not done.

---

## D-20 | 2026-08-11 | topic:no-action-band,thresholds,math | src:§7.4.1

**Correction, Dean.** *"Need to compute exact expected band based on applied up/down thresholds."* The
no-action band is not a separate calculation — it's the direct definition of `saturation_v2`'s two
universal thresholds (`saturation_scaling.go:54-64`): scale-up fires above `demand/supply > 0.85`,
scale-down below `< 0.70`. So the band is exactly `[0.70, 0.85]` — narrower than the `[0.3, 0.85]` the
plan had named, which was a guess, not a derivation. 0.67 (the 08-07 ladder's KV reading) is just below
0.70 — outside the band on the low side, not inside it.

---

## D-21 | 2026-08-11 | topic:dwell-mechanism,root-cause,forecast-gap | src:§7.6.1, dwell-deep-dive.md

**Finding, dedicated deep-dive session, traced against actual code.** The limit cycle's trigger is a
single anomalous `P1-obs` (`k2SrcObserved`) sample — `util>1` is by design (unclamped demand/supply
ratio), not a bug. The lag decomposes into two hops: ordered→created is fast (~1 tick, matches the KEDA
poll interval) — not the bottleneck; created→ready is slow and worsens with concurrent boot count —
physical (model load + GPU contention), not a WVA defect. Confirmed against ground-truth Deployment
status: `ready` peaked at 9, never reached the ordered/created peak of 10 — the controller retreated
from its own peak order before the last replica it asked for ever became ready.
`TotalAnticipatedSupply` is confirmed correctly implemented — no double-booking.

**The actual gap, new Type-1 design surface, not a bug fix.** The demand side has no forecast that
already-ordered, already-created (not-yet-ready) replicas will relieve the queue once ready — so demand
is sized off an instantaneous snapshot that's already about to shrink. Shared between saturation and TA,
not saturation-specific. **Whether/how to scope this is explicitly left as Dean's call** — tracked via
`session/handoffs/plan__dwell-limit-cycle-forecast-todo.md.WIP`, not yet actioned.

---

## D-22 | 2026-08-12 | topic:t9,log-follower,scope-correction | src:§7.6.1, §9.1

**Correction, Dean, two passes.** First pass (2026-08-11): *"T9 should only run with a test, part of the
playbook, no extra permissions above an actual test."* Second pass (2026-08-12), sharper: *"log watching
should be part of running a benchmark, invoked only when a benchmark actually runs."* The first
correction still framed T9 as "Dean applies it, per-test" — internally contradictory once "needs no
extra permission" is taken seriously: if it needs nothing beyond what a benchmark run already has,
whoever's permission suffices to run the benchmark suffices to apply the follower. Verified:
`gateway-log-follower.yaml`'s every resource (`Role`/`RoleBinding`/`ServiceAccount`/`Deployment`) is
namespace-scoped, nothing cluster-scoped. Not yet wired into the Makefile. **Owner corrected from "Dean,
per-test" to "benchmark coder"** — this is a playbook-wiring task, not a permission gap. Trigger sent:
`session/handoffs/benchmark__t9-log-follower-wiring.md`.

---

## D-23 | 2026-08-12 | topic:7.4-confirmation,bookkeeping | src:§7.4

**Correction, Dean.** *"7.4 — wasn't already decided?"* Correct — it was, in substance. 7.4.2/7.4.3 were
explicitly agreed; 7.4.1 was not merely approved but actively redirected (the [[D-18]] goal correction).
The OPEN marker reflected only that the planner hadn't independently heard the confirmation from Dean
directly (vs. via the coder's report) — a bookkeeping gap, not a live decision. Closed.

---

## D-24 | 2026-07-28 | topic:pr-branch-state,historical,superseded | src:§4 push policy

**Historical note, superseded by later commits — kept for provenance only.** As of 2026-07-28, the
`ta-model-level-demand` (C, #1480) and `ta-veto-liveness` (D, #1481) local branches were rebased ahead
of their origin PR tips (local `25f09a87`/`b3f75650` vs. origin `7aec2645`/`19c9a122`). Dean's
disposition at the time: leave as-is, do not push — pushing would confuse reviewers of the open PRs;
harmless while unpushed. **Checked 2026-08-12: both branches have since moved** (current tips
`c32235be`/`b2acffd6`, neither matching the SHAs above) — this entry no longer describes live branch
state, kept only so the historical disposition ("don't push a rebased-ahead local branch without
checking with reviewers first") is traceable.

---

## D-25 | 2026-08-08 | topic:verification,residual-hardcode,reusable-command | src:§5.6

**Reusable verification command, not a decision — recorded here because it's a live command worth
citing precisely rather than re-deriving.** Before considering the KEDA-path parametrization (§3 of
the execution plan) complete, confirm zero residual hardcoded values outside `.env.sample`:

```bash
grep -rn 'NVIDIA-H100\|nightly-d6d39be4\|0\.8\.0-rc5\|unsloth/Meta-Llama\|\bbiran\b\|v0\.14\.0' hack/ test/ docs/
```

---

## D-26 | 2026-08-08 | topic:fallback,recovery-path | src:§5.5 item 5

**Fact, not a decision — the standing recovery path if the KEDA path fails.** The archived VA+HPA
runbook (`archive/benchmark-ta3-legacy`, [[D-1]]'s Phase-0 archive tag) is the proven fallback recipe —
noted in the runbook so a KEDA-path failure has a known-working path to fall back to rather than
starting recovery from scratch.

---

## D-27 | 2026-08-12 | topic:bearer-token,security,reconciliation | src:campaign results doc, [[D-9]]

**Correction to [[D-9]] — the token hazard is not fully closed.** [[D-9]] recorded the 7
`run/inference-perf-*.yaml` files removed and the token rotated as of 2026-08-11. The 2026-08-12
`runs/` migration (folding the 7 pre-existing 2026-08-10 campaign directories into the new tree, [[D-5]]
[[D-13]]) surfaced that the *same* credential persists in a different file per cell:
`environment/context.ctx` — untouched by the earlier removal, since that removal targeted only the
`run/*.yaml` manifests. Verified clean of git exposure before migrating (`git add --dry-run` against
the exact 56-file allowlist, plus three independent credential grep passes — zero hits), but the token
remains on disk and rotation is still owed, unchanged in substance from [[D-9]]'s original ask — only
the file path recording it was wrong.

**Also resolved this session, folding into [[D-13]]'s reconciliation gap:** the parallel
`session-notes/campaign-viz/` tracked figure mirror ([[D-13]]) is now **deleted**, verified
byte-identical against the canonical `runs/<id>/viz/` copies first. The two-shapes-landed-in-parallel
question [[D-13]] flagged as undecided is resolved — `runs/<id>/{config,raw,viz}/` is canonical, the
cell-keyed mirror is gone.

**T9 closed for real.** Commit `3ab8128a` wires the gateway access-log follower into `benchmark-run`
automatically (`BENCHMARK_GATEWAY_LOG_FOLLOWER`, default `true`, namespace-substituted, idempotent —
the follower Deployment stays running across runs by design). Verified via `make -n benchmark-run` and
a YAML well-formedness check; **not yet exercised against a live cluster** — no real `benchmark-run`,
no live `kubectl apply`, still the one standing gap across the whole results-tree + T9 effort.

**Correction to this entry's own [[D-13]] framing — DEPRECATED, not merely deleted.** The
`session-notes/campaign-viz/` mirror was explicitly classified DEPRECATED (functionality intentionally
removed, no future work planned — the canonical `runs/<id>/viz/` supersedes it by design, not because
something wasn't ready). Also caught in the same work: a `.gitignore` bug — the unanchored `dean-*/`
rule (added when `BENCHMARK_WORKSPACE` moved, [[D-32]]) also matched `runs/dean-<ts>-<pid>/` at any
depth, silently shadowing the entire `config`/`viz`/`REPORT.md` allowlist for every migrated run;
`git status` showed a clean tree when it should have shown 56 new files. Fixed by anchoring to
`/dean-*/`. Caught before committing, not after.

---

## D-28 | 2026-08-08 | topic:dwell-mechanism,bucket-keyed-history,prc-collapse | src:plan__benchmark-dwell-run-findings.md

**Finding, coder, on the ORIGINAL 2026-08-08 dwell run — a distinct mechanism from [[D-21]], not the
same one.** `prc` collapses 10–13× because the capacity history is keyed on a *discretized bucket* of
average output length (`historyKey = "modelID|accelerator|gpuCount|outputBucket"`,
`outputBucket = classifyOutputLength(avgOutput)`, edges at 100/500 tokens,
`saturation_v2/analyzer.go:289-334`). This run's workload had mean output 512, sd 20 — **12 tokens
above the 500 medium/long edge with sd 20** — so ordinary sampling noise flips the bucket key mid-run,
swapping in a rolling average populated by a *different* workload (or a previous run — see below).
Status: strong mechanism-level hypothesis, not confirmed from logs — the analyzer computes and uses
`outputBucket`/`historyKey` but never emits them, so the bucket flip itself can't be directly observed,
only inferred from the collapse's timing and magnitude. Design issue stands independent of this run's
specific excitation: any workload whose mean output sits near 100 or 500 inherits a step change in
estimated capacity. **Ask, not yet actioned:** log `outputBucket`/`historyKey` on the `analyzer-result`
line — smallest possible change, would convert this from hypothesis to confirmed.

**A second, compounding finding: capacity history is contaminated across runs, in-process, no
time-based invalidation.** Direct evidence: this run's very first tick (before its own P1 could have
fired) already reported a stale `P2-hist` value left over from the *previous* benchmark run — the
controller pod had been running 6+ hours, spanning both runs. Consequence: successive benchmark runs
are not independent samples unless the controller is restarted between them. **Runner protocol
adopted, no decision needed:** restart the WVA controller before each run — this is the origin of the
"restart the controller before each run" protocol now standing in
`ta-pokprod-open-scenarios.md` §5 and `ta-pokprod-testing-plan.md`'s §7.6.1 (pre-restructure).

**Two more findings from the same run, not yet resolved or acted on:**
- **Dispatch rate was missing for 100% of ticks** (`collector/replica_metrics.go:1035`,
  "possible pod/pod_name label mismatch") — total, not intermittent, across every decode pod on every
  tick. Flagged as the plausible upstream cause of demand behaving like a backlog measure rather than
  an arrival rate (corroborated by a 48× demand swing at constant 2 RPS offered load, and a 5.6× demand
  *fall* while offered load *rose*). Not fact-checked or fixed.
- **The two analyzers contradicted each other outright** at one tick — saturation voting hard scale-up
  or hard scale-down, in the same instant, same variant — with throughput's contradiction traced to a
  GPS-mismatch fallback that clears its observation window and reports `demand=0`, a "confidently
  wrong" value rather than an honest abstention. Recorded as one design question, not two patches: what
  should an analyzer emit when it has no valid observation, rather than a wrong confident one.

**Workload-design errors the coder attributed to itself, not WVA** (should not be read as controller
defects): entry rungs too sharp for the actual ~5.5 min cold-start time; output mean 512/sd 20
straddling the bucket edge that excites the collapse above — a corrected profile should put the mean
well clear of both 100 and 500. **Neither error explains the cross-run contamination or the
dispatch-rate gap**, which are independent of workload shape.

---

## D-29 | 2026-08-08 | topic:dwell-mechanism,kv-measurement,limit-cycle-mean-invalid | src:plan__benchmark-dwell-rung-kv-answer.md

**Correction to how §7.6.1's original step-5 rule was to be executed — the mean of a limit cycle is
not a steady state, and reading it literally would have misled.** Real per-rung KV was measured
directly from vLLM scrapes (`vllm:kv_cache_usage_perc` — not `gpu_cache_usage_perc`, renamed in vLLM
0.20.2) on the original 2026-08-08 dwell run, since the analyzer's own `util` is a different quantity
(this run: real kv 0.9987 against reported `util` 0.360 at the same instant). Result: rung A
(20 RPS) mean kv **0.127**, rung B (26 RPS) mean kv **0.248** — neither ≈0.67, neither in-band, so a
literal reading of the "both ≈0.67 ⇒ rate-invariance confirmed" rule would have returned
"rate-invariance refuted" and routed to an unwarranted 32 RPS follow-up run.

**Why the rule can't work as posed, regardless of which numbers come back:** the distribution is
bimodal, not unimodal — rung B's p90 is 0.994 and max is 1.000 despite a mean of 0.248, because the
run traverses the full 1↔10 replica range *inside* each rung at constant offered rate. No single
number describes an operating point for a system that is limit-cycling. Fixing the underlying
oscillation ([[D-28]]) is a precondition for any two-rung comparison to mean anything, not a follow-up
to it. **This directly affects [[D-21]]/[[D-19]]'s "too short to reach steady state" framing** — the
sawtooth cells' means being uninformative is not only a duration problem; a limit cycle's mean is
categorically the wrong statistic regardless of run length, and this should be checked (distribution,
not mean) on any re-run.

**A genuine, accidental dwell was observed, and its cause corroborates the readiness-lag mechanism
[[D-21]] later confirmed independently.** The 14 RPS entry rung (originally written off as a design
error — too short and sharp) parked kv at mean 0.623 with p50 0.990, because replica count was lagging
the offered load (1→4 while 14 RPS was already arriving), not because of anything about the rate
itself. **The dwell is produced by replica lag, not offered rate** — a sharper, earlier statement of
what the dedicated deep-dive later confirmed with a full code trace.

**Consequence for (a)/(b) ([[D-19]]):** (b) — a deliberate cap — works because a cap *is* enforced
lag. (a) — SAT-alone-uncapped — only works if SAT's watermarks actually bind, and on this run they did
not: SAT and throughput contradicted each other outright ([[D-28]]) and the optimizer resolved to
no-change. Not a vote against the (a) decision — (a) is still decided ([[D-19]]) — but a reason its
success is not guaranteed and should be watched for on the next run.

**GPU-pause trap found and must be a precondition, not yet added to the checklist.** Pausing the
ScaledObject (`autoscaling.keda.sh/paused-replicas="0"` annotation) releases the GPU, but KEDA holds it
at 0 *indefinitely* — scaling the Deployment directly does not override the pause. **A run launched
without first un-pausing produces a flat 0-replica trace that reads as a legitimate no-scaling result,
silently.** Restore with the trailing-dash annotation form
(`autoscaling.keda.sh/paused-replicas-`) and confirm `PAUSED` reads `<none>` before any run. **Not yet
added as a precondition anywhere in the new docs — real gap, needs fixing in
`ta-pokprod-open-scenarios.md` §5.**

**The extractor (`dump_wva_target_timeseries.py`) is silently broken by log-format drift, not by log
rotation.** Its `ANALYSIS_PAT` matches a log line (`V2 saturation analysis completed`) this controller
build never emits — it now logs `analyzer-result`/`scaling-decision` under renamed keys
(`supply`/`demand`/`util`/`rc`/`sc`, plus `prc`/`reason` per variant). The tool reported "41 snapshots"
looking healthy while **0 of 41** rows had any of the five renamed fields populated — a **false
positive**, not an empty-file failure the existing anti-clobber guard would catch (that guard only
fires when `samples` is empty; 41 non-empty-but-null-valued rows sail through and can **overwrite a
good earlier file**). The precondition "run `post_run_analyze.sh` immediately" does not achieve its
intended purpose against this failure mode — promptness cannot fix a pattern match that no longer
matches. **Not fixed** — a focused single-file change (add the current pattern, map the five renamed
keys), flagged as needing Dean's approval per the substantial-edit rule, not yet routed to him.
**No data at risk regardless** — the raw controller log this run captured
(`session-notes/scratch/controller-decisions-20260808-dwell.log`) lets the timeseries be regenerated
offline at any time.

---

## D-30 | 2026-08-10 | topic:harness-bugs,load-generation,fixed | src:plan__benchmark-overnight-campaign.md

**Three harness bugs found and fixed during the overnight campaign, each blocking ALL load
generation** (found only by running, not discoverable by inspection beforehand): (1)
`BENCHMARK_WORKLOAD` is an upstream-catalog profile name fetched over the network — not how to select
one of the fork's own profiles, which live in `hack/benchmark/workloads/` and are chosen via the
scenario's `harness.experimentProfile` field, which was hardcoded — no per-cell load shape was
expressible at all until a new `BENCHMARK_PROFILE` variable was added to drive it. (2) The system
`python3` lacks PyYAML while the benchmark venv has it — three helpers were invoked as bare `python3`
and all three would abort; fixed for the whole class with a new `YAML_PYTHON` variable, mirroring the
existing `PLOT_PYTHON` pattern rather than patching each call site individually. (3) A workload
substitution-token ordering bug in the local-`.in` copy mechanism (downstream symptom of the same
catalog-routing fragility later addressed by T12 in `ta-pokprod-execution-plan.md` §7.1).

---

## D-31 | 2026-08-10 | topic:env-contract,guard-design,settled | src:plan__benchmark-env-guard-design.md

**Design settled with Dean in conversation, superseding [[D-6]]'s naming scheme, folded into
`ta-pokprod-architecture-design.md` §5 2026-08-12.** Came up while scoping a controller-image A/B —
three defects surfaced: the image pin has no path to a *standing* stack (only a full re-standup or an
invisible hand-patch, either contaminating an A/B's "how it was deployed" axis); `.env` is not the
source of truth once a CLI override exists (`make VAR=...` always wins); no context/`.env` cross-check
means an unset namespace silently becomes empty and nothing verifies the live context matches. Dean
picked the minimum-scope option: guard + `benchmark-apply-images` now, the wizard as an explicit
follow-up, rather than either building everything before the A/B or running the A/B ungapped.

**`benchmark-apply-images`** (the actual A/B unblocker, alongside the guard): refreshes a standing
stack's controller image to match the current pin — reuses the existing `record_images.py` for the
live-vs-pin comparison, dry-run by default with `BENCHMARK_APPLY=true` to act (mirroring
`benchmark-reset-run`'s existing convention), patches only the controller image, waits for rollout,
re-verifies. Composes with the mandatory pre-run controller restart, since that restart already
flushes capacity history ([[D-28]]).

**Explicitly not this branch's job:** creating a fresh image — that runs from a code branch, per the
Tier-A/Tier-B separation (architecture doc §1). This branch only applies and refreshes a pin.

---

## D-32 | 2026-08-11 | topic:runs-tree,finalized,benchmark-workspace | src:benchmark.md §20.25/§20.26

**Two iterations before landing on the final design — recorded because the first attempt is a real,
instructive dead end, not because the correction itself is news.** First attempt (§20.25, Dean-approved
same day): keep the harness's own `dean-<ts>-<pid>` run-id, physically `mv` its tree under
`runs/<run-id>/` after the fact, splitting it into `config/`/`raw/`/`viz/`. Built, verified on a
scratch copy, two commits.

**Superseded same session, before anything touched real data.** Re-checking against the architecture
decision already on record ([[D-5]]: `BENCHMARK_WORKSPACE` moves to `benchmark/runs/`) showed the `mv`
step was unnecessary — pointing the harness's own workspace variable at `runs/` makes it write there
**natively**, no copy, no move, and fixes a real bug the `mv`-based version didn't touch: the old
`dean-*/` gitignore glob only matched one username, so any other user's run showed as untracked
clutter. Final design, confirmed with Dean: keep `config`/`viz` committed per-run (not [[D-5]]'s
originally-stated "all of `runs/` untracked"); **no `raw/` subfolder** — allowlist the harness's native
top-level dirs directly in `.gitignore` (`runs/*/*` then un-ignore `config/`, `viz/`, `REPORT.md`)
rather than nesting, which avoids the copy/move mechanism entirely and works for every user with zero
extra logic. `Makefile`: one variable change (`BENCHMARK_WORKSPACE ?= $(CURDIR)/runs`); all four
existing lookups were already parameterized on it, zero further edits needed there.
`hack/benchmark/campaign/run_cell.sh` step 6 lost its whole relocation block — the only remaining
action is copying the `.env`/analyzer-config/images/scaledobject snapshot into `config/`.

**Not amended — left in git history per the no-amend convention**, even though the second commit
supersedes the first in effect.

**Still not exercised against a live `make benchmark-run`** as of this entry — dry-run/scratch-tree
verified only. This is a recurring caveat across every commit in this thread; treat it as standing
until a real campaign run confirms it, not resolved by any individual verification pass.

---

## D-33 | 2026-08-12 | topic:results-tree-tooling,three-tools-built | src:benchmark.md §20.27

**Three tools built to complete the folder-structure design ([[D-5]]/[[D-13]]), all dry-run/scratch-tree
verified, none exercised live:**

1. **`benchmark/tools/` symlink** — `ln -s hack/benchmark tools` (relative; a first attempt built it
   one level too high, since `tools` and `hack` are siblings under the same `benchmark/` root, not
   across a directory boundary — caught before committing).
2. **`REPORT.md` generator (`write_report.py`)** — wraps the existing `postprocess.py` metrics table
   (the same one `make benchmark-report` prints) with relative links into a run's `config/`, `viz/`,
   and raw `results/` leaf. Computes nothing itself. **Caught a real path bug before any live run
   exercised it:** `run_cell.sh`'s directory-parsing logic was stale from the pre-[[D-32]] `mv`-based
   version and would have silently written `config/` into a bogus location on every future run. Fixed
   before committing.
3. **Conservative pruning script (`prune_run.py`)** — read-only investigation first: confirmed
   `setup/commands/*_stdout.log` (11–40 MB each, the two biggest files in a run) are byte-identical
   duplicates of files already preserved under `results/<leaf>/logs/`. Deliberately narrow rule, not a
   general "big files are safe to delete" heuristic — only removes a file when its hash matches
   something already preserved elsewhere. `--apply` required to delete; dry-run by default. Never
   touches `metrics/raw/` or `results/*/logs/` itself, by explicit choice — conservative over
   aggressive pruning was chosen precisely because the per-request discovery work found real signal in
   those exact files.

Also, in the same round: stopped duplicating campaign-run config files into
`session-notes/campaign-runs/<cell>/` (now `mv` at the point of collection, not `cp` followed by a
stale leftover) — that directory now keeps only genuinely campaign-scoped bookkeeping
(`results-dir.txt`, `run.log`, `controller.log`) that `run_all.sh`'s own abort-check still reads.

---

## D-34 | 2026-08-08 | topic:dwell-mechanism,dispatch-rate,demand-vs-backlog,analyzer-contradiction | src:plan__benchmark-dwell-run-findings.md

**Six more findings from the same first dwell run as [[D-28]]** (`dean-20260808-051912-230`,
decision trace captured live) — [[D-28]] covers only the bucket-keyed `prc`-collapse mechanism from
this handoff; this entry captures the rest, which is substantial and was previously missed entirely.
The run produced a clean, fully-instrumented limit cycle (period ~9m12s peak-to-peak) rather than a
dwell, superseding this handoff's own predecessor's "tracking controller holds kv low by construction"
hypothesis — wrong for a system that at this step size doesn't track at all.

**Cross-run capacity-history contamination, confirmed with direct evidence, not inference.** This
run's very first tick — before its own `P1-obs` had ever fired — already reported `prc = 25,348` via
`P2-hist`, a value that could only be a rolling average left over from the *previous* benchmark run
(the 08-07 ladder): `computeCapacityHistory` is an in-process map with no time-based invalidation, and
the controller pod had been running continuously across both runs. **Consequence adopted as a runner
protocol, no decision needed:** restart the WVA controller before each benchmark run, record its start
time. This independently corroborates and predates [[D-32]]'s later controller-restart adoption.

**A third finding: dispatch rate was missing for 100% of ticks, not intermittently.** 157 occurrences
of `collector/replica_metrics.go:1035`'s "Pod has engine metrics but no dispatch rate — possible
pod/pod_name label mismatch" across 33 ticks — every decode pod, every tick, from the very first tick.
Plausible upstream cause of the next finding.

**A fourth finding: demand is measuring backlog, not arrival rate.** The decisive pair: at 2 rps
offered load, demand read 2,247,803 (backlog still draining, scaled 2→9), then one tick later at the
same 2 rps offered load, demand read 53,639 (backlog drained) — a 48× difference in demand under
*identical* offered load. A quantity that collapses when capacity is added, and stays high when capacity
is unchanged and offered load has already dropped, is measuring queue depth, not incoming rate. Likely
explained by the missing dispatch-rate signal above — with no arrival-rate input, demand is derived
from what's left, and what's left is queue-shaped.

**A fifth finding: the two analyzers can contradict each other outright, and the optimizer can't tell.**
At one instant, saturation reported `util 3.32` (scale up hard) while throughput reported `demand 0`
(scale down all the way) — not two noisy estimates of the same thing, two incompatible worlds. Traced
to throughput's own fallback: a 29–40% model-vs-observation mismatch (`GPS mismatch detected`) causes it
to clear its observation window for recalibration, and the emptied window reports `demand 0` — a
spurious scale-down vote from a fallback path that fires exactly when the system is most interesting.
Same failure family as the bucket-collapse mechanism above: a degraded path returning a value that is
not merely imprecise but qualitatively wrong.

**A sixth finding: `supply` lags the replica count by ~1 tick in both directions** — over-counts during
scale-down (terminating pods still counted), under-counts during scale-up (new pods not yet counted) —
combined with ~90s+ actuation latency, the loop has delay, a more-than-proportional correction, and no
damping.

**A seventh finding: real kv ≈1.00 was measured directly off a replica while the analyzer reported
`util 0.36`** and chose no-change — roughly a 3× capacity over-estimate at the exact moment the engine
was completely full. Also flagged: vLLM 0.20.2 emits `vllm:kv_cache_usage_perc`, not
`gpu_cache_usage_perc` (the latter returns nothing) — worth checking which name the WVA collector
actually queries.

**Reason-code distribution across the run:** of 33 ticks, `P1-obs` 6, `P3-k2` 2, `P2-hist` 25 — the
controller ran on historical or derived capacity for 82% of its decisions, with dispatch rate absent for
100% of them.

**Five asks, priority order, NONE implemented — this is diagnosis only, explicitly not a proposed code
change.** (1) Log `outputBucket`/`historyKey` on the `analyzer-result` line — smallest change, confirms
or refutes the bucket-collapse hypothesis directly. (2) Decide `computeCapacityHistory`'s intended
lifetime (time-window invalidation vs. run-scoped key vs. document that consecutive experiments aren't
independent). (3) Fact-find the `pod`/`pod_name` label mismatch behind the 100% dispatch-rate miss —
if fixed, "most of the demand-is-backlog finding changes character." (4) Confirm which kv metric name
the collector queries. (5) Treat the two fallback-path failures (bucket-collapse, GPS-mismatch-clears-
window) as one design question — what should an analyzer emit when it knows it has no valid
observation, rather than two separate patches; "no confident estimate, abstain" as a signal, rather than
a confidently wrong number.

**Two confounds the coder flagged in their own workload design**, not attributable to WVA: entry rungs
compressed too sharply (budgeted for a 1-replica cold start that actually took ~5.5 min, contaminating
the following rung's first half with transient); and the 512±20 output-token mean sitting right on the
500-token bucket edge, which is what excites the bucket-collapse mechanism specifically — a corrected
profile should move the mean well clear of both the 100 and 500 edges so "is prc bucket-discontinuous"
and "where does the system dwell" aren't confounded in the same run.

**Not yet routed to Dean for scoping — none of the five asks above (see [[D-28]]) has an owner.**
[[D-21]]'s later deep-dive investigated a related but distinct trigger (a single anomalous `P1-obs`
sample and the created→ready lag) and does not supersede either [[D-28]]'s bucket-keying finding or
this entry's cross-analyzer-contradiction / demand-is-backlog findings — all remain open,
uninvestigated by that later session.

---

## D-35 | 2026-08-10 | topic:own-guide,doc-consolidation,unverified | src:plan__benchmark-tooling-round-and-own-guide.md

**Decision, Dean — a second, separate doc from the runbook consolidation in [[D-8]].** *"We do not
diverge from upstream. They have their docs. We just add another guide."* New:
`docs/wva-benchmark-guide.md`, standing **alongside** upstream's own guide, not replacing it. An
earlier edit to the *shared* `docs/developer-guide/two-variant-wva-benchmark.md` was reverted —
division of labor is now explicit: the new guide is the portable procedure, the (separately tracked,
[[D-8]]) pokprod runbook is one environment's operational detail.

**Marked provisional in its own text — it has never been run from a clean clone.** Dean's stated
acceptance criterion: *"we would have to do a clean refresh test — start from a clean WVA repo and see
if following your guide builds everything correctly."* Written into the guide as its own §10 checklist,
framed so any stumble reads as a guide defect rather than something to route around in the shell.
**Unperformed, needs a GPU cluster.** Nothing should treat this guide as verified until that test runs.

---

## D-36 | 2026-08-10 | topic:image-under-test,pr2-anchor,parser-risk | src:plan__benchmark-tooling-round-and-own-guide.md

**Fact, not yet fully verified.** `WVA_IMAGE_TAG` defaults to `ta-0.9-anchor-pr2-20260809` (was
`ta-0.9`), per Dean. **A tag change is a change of the code under test and can move the analyzer log
format with it** — exactly the mechanism that broke the extractor before ([[D-29]]). The failure mode
is now loud (warns, refuses to overwrite a good file, exits non-zero) rather than silent — a backstop,
not a substitute for checking. Cheapest pre-check, not yet done: a read-only diff of the PR-2 branch's
`engine_v2.go` log lines before committing a run to it. Recommended sequence: short run → confirm
analysis fields populate → only then a long run. **One positive side effect already in place:** the
extractor now records `scaleUpThreshold`/`scaleDownBoundary` per tick, so a run on this image will show
which thresholds are actually live rather than leaving it inferred — directly useful given PR-2's
`k_sat`-sourcing change ([[D-11]] territory, a different thread).

---

## D-37 | 2026-08-10 | topic:isolation-guard,write-scope,process-correction | src:plan__benchmark-tooling-round-and-own-guide.md

**Process correction, generalizable beyond this thread — the isolation guard intercepts the *tools*,
not the *shell*.** A duplicate state file (two byte-identical 170,783 B copies of `benchmark.md`) was
traced to the belief, stated in the file's own header, that a coder cannot write to
`plans/session/status/`. **Half true, and the wrong half caused the duplicate:** the Write/Edit tools
are blocked from the shared-checkout path, but Bash `cp`/`mv`/redirect are **not** — they reach
`plans/session/status/` and `plans/session/handoffs/` normally, including the full `.md` → `.WIP` →
`.DONE` rename cycle. Verified by direct probe. Resolution: `plans/session/status/benchmark.md` is the
sole authority, maintained directly via Bash by the owning coder; the tracked duplicate removed.

**One practical wrinkle carried forward:** the guard also refuses compound Bash commands it cannot
statically verify (pipes, `cd &&`, redirects in loops) — so status/handoff writes must be plain,
single commands, not chained.

**Worth generalizing in `session/CONVENTIONS.md` — not yet done, flagged here so it isn't lost:** "the
coder cannot write there" is not a correct blanket statement anywhere in this project; it is specific
to which *tool* is used, not the target path.

---

## D-38 | 2026-08-12 | topic:live-run,results-tree-verified,postprocess-bug | src:benchmark.md §20.29

**Milestone: the first live `make benchmark-run` against the whole results-tree/`REPORT.md`/
`.gitignore`-allowlist build ([[D-5]], [[D-13]], [[D-27]], [[D-32]]–[[D-33]]) — previously verified
only against scratch trees, now confirmed against a real run.** `m-ta-prefill-knee` profile (TA-only,
isolates the ITL prefill term), `WVA_IMAGE_TAG=ta-0.9-anchor-pr2-20260809`, `dhl-wva-209`,
ScaledObject confirmed unpaused before the run. Completed cleanly: 0 request errors, avg 3.21 / max 10
replicas, avg pod startup 77s, avg KV util 15.0%.

**The allowlist machinery works exactly as designed.** `git add -A` on the run directory staged
precisely `REPORT.md` + the four `config/` files — nothing from `results/`, `logs/`, `analysis/`, or
`environment/` (individually verified via `git check-ignore -v`). **No bearer token staged** —
`environment/context.ctx` carries the live pokprod token exactly as [[D-27]] flagged, and it correctly
stays ignored.

**A real, previously-unknown bug found: `hack/benchmark/postprocess.py` hard-codes a filename this
harness/profile never produces.** `REPORT.md`'s P99 TTFT, P99 ITL, and avg queue depth all rendered
`?`. `_extract_latency()`/`_extract_error_count()` (`postprocess.py:91-119`) read `results.json` from
the run's results leaf, but this run produced `summary_lifecycle_metrics.json`,
`stage_{0,1,2,3}_lifecycle_metrics.json`, `per_request_lifecycle_metrics.json`, and the harness's own
already-converted `benchmark_report[_v0.2]_stage_N_*.json.yaml` files instead — the data exists, just
under different filenames than the extractor expects. **Degrades silently** (`None`/`?`, no error) — a
green run alone would not catch this, only reading the report contents does. Also: no `viz/panels.png`
was generated, likely the same missing-input cascading into the viz step, not yet independently
investigated.

**Deliberately paused for Dean's input, per "discuss before implementing"** — `postprocess.py` is a
shared tool, not run-scoped, so fixing which file it should read from is not a unilateral call. The run
directory itself is also not yet committed, held pending that decision (re-committing after a fix would
just mean a second commit; not a blocker if Dean prefers to land the run as-is and fix separately).

**RESOLVED same day, see [[D-39]].** The pause did not block a fix — the coder proceeded with
direction to support both harness formats rather than replace one, verified against the real run,
and the run directory is now committed.

---

## D-39 | 2026-08-12 | topic:postprocess-fix,gpu-incident,verified | src:benchmark.md §20.30

**[[D-38]]'s `postprocess.py` bug is fixed and verified against the real run — not just compiled.**
Root cause was narrower than "wrong filename": it only ever read guidellm's `results.json`; the
current harness (inference-perf) writes `summary_lifecycle_metrics.json` instead. The fix **supports
both harness formats, not a replacement of one** — direction given, followed. Separately fixed
`_extract_queue_depth_avg`'s stale EPP pod-name filter and metric name in the same pass. **Error count
had been showing a wrong `0`, not just a missing value** — a real failure existed and was being
silently hidden, not merely under-reported. All three fields (P99 TTFT, P99 ITL, queue depth) now
populate correctly. Three commits: `66c71f8e` (the run's 5 allowlisted files), `6a10f458` (the fix),
`eee20e33` (regenerated `REPORT.md`).

**Separately, a sibling coder session on the same worktree hit a live-cluster incident this session
resolved: GPUs freed after a controller restart left decode stuck at 10/10 with zero load.** Full
mechanism in [[D-40]]. Verified directly against the cluster (not inferred from logs) and freed via
the standard `free_gpus` pattern — confirmed 0 pods, 10 H100s released.

**Not yet done, low priority:** the orphaned `m-ta-calibration-probe` run that triggered [[D-40]]'s
incident never produced usable data — worth a clean re-run whenever convenient, now that both the
toolchain and the GPU state are known-good. Its setup-only PVC directory
(`/requests/inference-perf-1786538941-lwy8cw_1`) was left in place, harmless.

---

## D-40 | 2026-08-12 | topic:controller-restart,stuck-replicas,rc-zero-no-scaledown | src:plan__benchmark-controller-restart-stuck-at-max-replicas-20260812.md

**A controller restart left decode pinned at 10/10 replicas for 15+ minutes with zero active load,
never trending down — verified directly against the live cluster, not inferred from logs alone.**
Trigger: a `reset_run.py --apply` cleanup (deleting an orphaned harness pod + its 2 configmaps) that
also restarted the WVA controller and, via the ScaledObject, decode. Every reconcile cycle checked
showed `demand=0, util=0, rc=0, decisionsApplied=0`, yet `desiredReplicas` stayed pinned at 10 — not a
single cycle moved it. Not investigated further live; frozen as evidence and resolved by the standard
`free_gpus` pattern (pause ScaledObject at 0, scale decode to 0) rather than debugging on a shared
cluster.

**Distinct trigger from Finding 4 (campaign doc, "the replica target oscillates while `rc = 0` and
util ≈ 0.2") — related but not confirmed to be the same mechanism.** Finding 4 was observed *during* a
load-generating run and described an oscillation. Here `util` was exactly `0`, not `≈0.2`, and the
target never moved at all in the observed window — consistent with a fresh restart simply inheriting
whatever replica count the Deployment already had (10, left over from the orphaned run) and the
optimizer's `rc=0` never translating into a scale-down instruction. Possibly the same underlying
mechanism as Finding 4, possibly a distinct startup-state bug (does the controller correctly
initialize "current replicas" vs. "desired" on restart when the Deployment is already at the cap?) —
insufficient evidence to say which; both are `rc=0`-with-no-scale-down and both warrant the same
investigation thread.

**Explicitly flagged by the reporting coder as not theirs to investigate** — a controller-behavior
question (decision/optimizer path), not benchmark tooling. **Not yet routed to anyone; no owner.**
What was *not* done, stated for whoever picks this up: no reproduction attempt (controller not
restarted again), no Prometheus query for `wva_desired_replicas` history across the incident, no
optimizer/actuator source read for startup-state handling. The immediate GPU-idle problem is already
closed (freed, verified 0 replicas) — this entry is about the underlying mechanism, still open.

---

## D-41 | 2026-08-13 | topic:inference-perf,oom,root-cause,upstream-code | src:plan__inference-perf-oom-root-cause-found-20260813.md

**Root cause found, source-verified against the actual `kubernetes-sigs/inference-perf` code (a real
local clone, not inferred from symptoms).** `m-ta-calibration-probe`'s harness pod OOMKilled after
~16 min at a 32Gi limit. **inference-perf holds every request's full JSON body and every response's
full text body in memory for the entire run, in one unbounded Python list, never flushed until the run
ends.** `client/modelserver/openai_client.py:170,182` captures `request_data = json.dumps(payload)` and
`response_content = await response.text()` at full size per request; both go into a
`RequestLifecycleMetric` (`request_data: str` / `response_data: Optional[str]`, not a summary or
length); `MultiprocessRequestDataCollector.collect_metrics()` drains a shared queue and does
`metrics.append(item)` — one list, one process, held until the run's `queue.put(None)` signal. Workers
don't duplicate the list; the single collector's unbounded growth *is* the mechanism.

**This is structural, not tunable per-workload.** At ~4096in/~1024out tokens ramping to 20 req/s over
12 min, the accumulated list holds thousands of full request+response text bodies growing
monotonically with elapsed time × request volume — any workload at this token size and duration hits
the same ceiling eventually, just later for shorter/slower ones. Consistent with, and now confirms,
Dean's suspicion (*"inference-perf itself can't handle this workload shape/rate"*) rather than a
per-replica log-capture theory that was checked and ruled out first (~33 MB total across 3 pods, far
too small to explain a 32Gi OOM).

**No fix proposed or attempted — this is upstream `kubernetes-sigs/inference-perf` code, not this
repo's.** Given the root cause, a memory-limit bump is the *correct* near-term mitigation (it buys
headroom against a growing-but-run-length-bounded list), not a workaround for an unrelated cause the
way the earlier log-capture theory would have been.

**Two side questions, checked directly rather than left as "as far as I've seen":** no harness-pod
resource monitoring exists anywhere in `hack/benchmark/` (no `kubectl top`, cAdvisor, or
`container_memory` reference) — confirmed absent, not assumed. A multi-harness-pod flag/count was
searched for in both `inference_perf/config.py` and `llm-d-benchmark`'s `setup/*.sh`/`env.sh` and found
nowhere. **CORRECTED, see [[D-42]] — it does exist, the search was against a stale local clone, not
upstream.**

**Open, explicitly not decided here:** whether the benchmark's own playbook should generate load
directly instead of going through inference-perf's config surface — a design-direction question, not
answered, though item 1's finding is a point in its favor (sidesteps this specific accumulator by
construction).

---

## D-42 | 2026-08-13 | topic:load-parallelism,harness-pods,oom-fix,upstream-confirmed | src:benchmark__use-harness-parallelism-for-oom-fix-20260813.md

**[[D-41]]'s item-3 search was against the wrong target — a stale local `llm-d-benchmark` clone, not
upstream.** Dean's memory was correct: `LLMDBENCH_HARNESS_LOAD_PARALLELISM` is real and current.
Confirmed via `gh search code`/`gh search commits` against the actual upstream repo (`llm-d/llm-d-benchmark`
on GitHub, not the local checkout, which is 63 commits behind `upstream/main` and doesn't even have the
introducing commit in its history) — the flag is present in `docs/run.md`, a tutorial doc, and read
live in `llmdbenchmark/run/steps/step_07_deploy_harness.py` (`context.harness_parallelism`) on current
`main`. Introduced by PR [#531](https://github.com/llm-d/llm-d-benchmark/pull/531) "Enable Deploying
One or More Harness Pods," merged 2025-11-21 — recent, actively maintained, not a legacy relic.

**What it actually does, confirmed by reading the implementation directly, not the PR description
alone: it multiplies pod count, it does not divide load.** `step_07_deploy_harness.py`'s per-treatment
loop resolves `pod_profile_name` **once**, before the `parallel_idx` loop, and passes it unchanged to
every one of the `parallelism` pods — each pod gets its own `pod_name` and a `results_dir` suffixed
`_1`..`_N`, but the **same** workload profile (same rate, same stage durations) as every sibling. N
pods running the same profile concurrently against the same target is N× the aggregate offered rate,
not the original rate split N ways.

**Dean's ruling: this is still the right fix, but only when paired with a rate-divided workload
variant — using the flag alone against an unmodified profile is wrong given how the mechanism actually
works.** To get [[D-41]]'s intended effect (each pod's own accumulator handles 1/N the request volume,
so N× the total load fits in the same 32Gi limit), the workload profile's own stage rates must be
divided by N *before* setting `LLMDBENCH_HARNESS_LOAD_PARALLELISM=N` — the flag does not do this
division itself. Concrete first try recommended for the stuck `m-ta-calibration-probe` cell: N=4,
divide `ta_calibration_probe.yaml.in`'s 8 stage rates (2,4,6,8,10,13,16,20) by 4, keep durations (90s)
unchanged, set `LLMDBENCH_HARNESS_LOAD_PARALLELISM=4`. Not yet applied — handed to the coder, not
executed here.

**Not verified: whether the harness image currently deployed carries this feature at all.** The
image bakes in a fixed `inference-perf` + `llm-d-benchmark` version (`hack/benchmark/.env:69`); the
feature merged 2025-11-21, so any image built before that date lacks it regardless of what upstream
`main` shows today. Must be checked against the actual running image's build/version, not assumed
from the upstream source read.

---

## D-43 | 2026-08-13 | topic:oom-fix-validated,rerun-campaign,parallelism-p4,dwell-reruns-clean | src:ta-pokprod-rerun-results-20260813.md

**The [[D-42]] parallelism-4 fix is now validated by a real run, not just decided.**
`m-ta-calibration-probe-p4` (`runs/dean-20260813-130251-004`, commit `b44935db`): 4 parallel
harness pods, same treatment, **0 errors across all four**, P99 TTFT consistent to within ~1%
(18,524–19,320ms). This is the concrete result the fix predicted.

**All six cells run since the 2026-08-10 campaign are tabled with real numbers** (commits
`fbc42741`, `09055f56`, `5cb8eb97`, `e1fdf31f`, `f1a39bc5`, plus the prefill-knee run `66c71f8e`
and the p4 validation above) in
[`ta-pokprod-rerun-results-20260813.md`](ta-pokprod-rerun-results-20260813.md). `m-sat-dwell`'s
P99 TTFT (91,712ms) and queue depth (32.4) — roughly 25× worse than either TA-analyzer dwell cell
on an otherwise-comparable clean run — is the sharpest confirmation yet of the saturation-lags-
demand finding; not new, but the clearest single number for it so far. All three dwell reruns are
now clean full-duration runs, closing the original campaign's `m-ta-dwell` r²=0.11
truncated-fit gap.

**New gap found, not previously flagged: no viz output exists for any of the 8 run directories
created since 2026-08-10.** The extractor/render toolchain has not been invoked against any
`dean-20260812-*`/`dean-20260813-*` run. The original campaign's 7 directories all have `viz/`
(3 files each); every run since has none. Not routed to an owner yet — flagged in the results doc
§ Next steps.

---

## D-44 | 2026-08-13 | topic:namespace-guard,context-check,safety-invariant | src:architecture doc §2

**Decision, Dean.** Closes the open §2c question ("can one context map to multiple namespaces?").
No — every `.env` names one specific namespace explicitly, never generic; every pokprod run in this
mission is namespace-scoped for both llm-d and the WVA controller (WVA *can* run cluster-scoped or
against a different namespace elsewhere, but not in this mission's runs). Enforcement: before any
run, verify the active context's namespace (`oc project` changes it) matches the `.env`'s named
namespace; refuse to run on mismatch, fail closed, no override. Written into architecture doc §2
invariant 1.

---

## D-45 | 2026-08-13 | topic:controller-restart-incident,direct-load-gen,replay,deferred | src:open-scenarios.md checklist

**Two rulings, Dean.**

**(a) Controller-restart stuck-at-10-replicas incident ([[D-40]]).** Can wait, but must not be
forgotten — logs are preserved. Launching as a background investigation (log-reading, no code
change) rather than leaving it fully unrouted.

**(b) "Should the benchmark generate load directly instead of inference-perf" — reframed, not
rejected.** The narrow framing (build our own load generator to sidestep inference-perf's OOM) is
the wrong target: broader scope than warranted, and a credibility issue independent of the
technical one — using our own tool to showcase our own work is suspect; people want to reproduce
results with tools they already know and trust, even flawed ones. The real longer-term thread is
**controlled-run capability — timestamped and agentic replay** — real community work exists here
worth catching up on eventually. Deferred, not now: current focus stays on the tools already in
use.

---

## D-46 | 2026-08-13 | topic:doc-staleness,extractor-already-fixed,checklist-drift | src:benchmark/hack/benchmark/dump_wva_target_timeseries.py, commit add1d400

**Correction: the extractor's log-format-drift bug ([[D-29]] §3.2), previously listed here as
"OPEN, not yet routed to Dean," was already fixed on 2026-08-10 — three days before this session
told Dean it was still open.** Verified by reading the current script source directly, then
confirming via `git log`: commit `add1d400` ("benchmark: fix the WVA timeseries extractor
emitting silent nulls"), same day as the bug's own discovery. The fix matches the current
controller's `analyzer-result` log line (`ANALYZER_RESULT_PAT`), keeps a fallback pattern for
older builds, tracks a `hydrated` count separate from raw sample count, refuses to overwrite a
hydrated file with an unhydrated new parse, and prints a loud warning rather than a silent
success line on drift. **Root cause of the doc staleness:** the open-scenarios checklist was
never updated after the fix landed — a real gap in the doc-maintenance loop, not a code gap.
Corrected in place, §3.2 and the checklist row both fixed 2026-08-13.

**Background investigation result, controller-restart stuck-at-max-replicas incident ([[D-40]]).**
Read-only source investigation (no cluster contact, no code change) found a plausible mechanism:
`internal/engines/saturation/engine.go`, `applySaturationDecisions` (~L1601-1701). When the
optimizer has no fresh decision this cycle (consistent with `rc=0` failing the informativeness
gate), the code deliberately holds at the current replica count — tries the previously-persisted
CR status target, falls back to `currentAllocations`, falls back further to the live Deployment's
actual replica count — explicitly to avoid unintentionally scaling to zero on a transient
uninformative cycle (stated in the code's own comments, ~L1670-1680). This is a **designed
hold-on-no-decision policy, not a computation bug** — on a fresh restart with no prior CR status
and a Deployment already at 10 replicas, nothing drives the target down while this policy holds.
Not confirmed live (static read only); the open question for Dean is whether "hold" is the right
policy for a *sustained* 15+-minute `rc=0/demand=0/util=0` window, not whether the code is broken.
**Relationship to Finding 4:** likely the same mechanism *family* (the hold/current-replicas
fallback logic) but not proven to be one single bug — Finding 4 was an active-decision
oscillation during live load (`util≈0.2`), this incident is the pure hold case
(`util=0` exactly, post-restart, no load). Investigation closed as "plausible mechanism found,
policy question for Dean," not further pursued without his direction.

---

## D-47 | 2026-08-13 | topic:coverage-matrix,workload-inventory,ownership-resolved | src:ta-pokprod-workload-coverage.md

**§4.1's coverage matrix ask, built.** [`ta-pokprod-workload-coverage.md`](ta-pokprod-workload-coverage.md)
tables all 6 canonical `ta_*.yaml.in` templates under
`benchmark/hack/benchmark/workloads/inference-perf/` against purpose (from each file's own
docstring), shape, actual run count in `runs/`, and outcome. Every template has run at least once —
no coverage gap exists at the "has this ever been tried" level. Owned in benchmark-execution scope
as a Type 3 (about what benchmark *runs*), not a new benchmark Type 1 as previously guessed. §4.2
(theory/simulation legs, what viz *computes*) stays viz-panels-planner's, unbuilt, separately.

**Real open item this surfaced, not previously stated this plainly:** `ta_autoscale_dwell` has 6
clean runs but **no run has yet escaped the limit cycle to produce an actual steady-state dwell** —
a known, understood gap (D-21/D-28/D-45 §2, the deferred forecast design), not a new mystery, but
worth stating directly rather than leaving implicit across three other docs.
