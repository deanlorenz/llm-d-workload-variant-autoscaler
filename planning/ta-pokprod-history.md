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
