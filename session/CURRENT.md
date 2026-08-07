# Current Work

**Last updated:** 2026-08-07

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts) — live WIP only:**

- **2026-08-07 — Anchor-refactor mission (goldens PR #1513 OPEN; PR-1 `ta-anchor-refactor-v2` = **PR #1516 OPEN**,
  push-ready review APPROVE; PR-2 `ta-anchor-dynamic-refresh` **CODING IN FLIGHT @ C6b**, gate steps 1–2
  CLEARED — now waiting only on Dean's resume-coding go-ahead).** Reshaping the multi-analyzer engine so it builds the anchor (topology
  carrier) and passes the enabled-analyzer list as the ballot — "no special voting code" (Dean's corrected
  model). **goldens** `ta-anchor-goldens@a2f49ccf` = **PR [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513) OPEN**
  (characterization gate freezing sat-v2-only decision-SET-identity keyed by VariantName; test-only +409/−0;
  base `upstream/main@9906dac5`; reviewer ev-shindin; `origin/ta-anchor-goldens` pushed; internal review
  FINAL — Finding 1 fixed, Finding 2 = `withSatEntry`-stability coordination note carried into the PR-1
  kickoff; **land-first** decided). **PR-1 mechanism REDESIGNED 2026-08-05** — the review agent found the
  stored-`ModelScalingRequest.Anchor` design (the Aug-4 fold-in, commits `68bda1a1`/`192ae06b`, and the
  abandoned branch commit `34055d77`) unnecessarily complex and **superseded** it with a no-stored-field
  two-phase mechanism. `planning/ta-anchor-refactor-review.md` restructured into Part 1 (review of the
  now-**SUPERSEDED** `ta-anchor-refactor-plan.md`) / Part 2 (redesign spec) / Part 3 (review of the v2
  plan, verdict APPROVE) / **Round 2** (2026-08-05, reconciled against plan tip `2e83c7fe`: verdict still
  APPROVE, zero MAJOR/correctness findings — the earlier `[sat,TA]` core concern is **RESOLVED**; 4
  doc-only findings V8/V9 should-fix + V10/V11 minor) — doc still **DRAFT** (Dean marks FINAL at his
  discretion). **`planning/ta-anchor-refactor-v2-plan.md` is now Status: FINAL** (`c279bdeb` folds
  Round-2 V8–V11; coder-ready): Phase-1 `runAnalyzersAndScore` tags every ballot entry `Enabled` (+
  existing `Live`), makes no decisions; Phase-2 `bindingAnchor` derives the anchor **on demand** by a
  per-variant merge keyed by `VariantName` ((a) identity from saturation, (b) sizing from the binding
  analyzer). **Scale-from-zero cost/PRC design** (Dean, 2026-08-05, commit `2e83c7fe` — supersedes the
  interim MAX-sentinel version `2ccf51b7`): TA emits PRC only (no Cost/AcceleratorName persistence); the
  (b)-sizing fallback is **enablement-gated** (valid only when saturation is enabled); `[TA]`-only
  zero-replica variants get PRC=0 (suppressed — reactive `scalefromzero` covers cold-start), with a
  documented (not gated) known-limitation that `[TA]`-only then cost-mis-ranks like `[sat]`-only until a
  separate pre-existing sat `Cost=0` bug is fixed (out of scope here). **Worktree/branch `ta-anchor-refactor-v2`** cut off the goldens tip `a2f49ccf`; PR-1 is now
  **CODE-COMPLETE C1–C5, reworded, rebased onto `upstream/main@aadaa596` (#1509), and pushed to
  `origin/ta-anchor-refactor-v2@075a208e` — NO GitHub PR yet** (Dean holding). 10-commit stack = 5
  characterization goldens riding (#1513 unmerged, expected in the diff) + C1–C5 (`387d69ac` tag-Enabled
  / `a0795e36` on-demand `bindingAnchor` merge / `279134eb` refuse-QM / `7eae42cb` TA PRC-only
  scale-from-zero / `075a208e` dev-guide). Close-out done: F1/F3/F4 (C2 reword + §4a token strips)
  applied in the rebase, F2 knowingly relaxed (Dean sign-off, no code); §13 checklist + per-commit
  goldens+Test 9 green C1→C5 + DCO on all 10 verified; recovery tags `pre-rebase-f6485980` /
  `post-rebase-clean`. **Internal push-ready review COMPLETE — verdict APPROVE, push-ready** (trigger
  `.DONE`): rebase integrity PASS — `git diff --stat pre-rebase-f6485980 075a208e` is exactly 4 files
  (#1509's `cmd/main.go`, 2 new watcher files, the intended F3 rewrap), with the other 22 stack files and
  all 5 goldens **byte-identical**, so no silent hunk loss; DCO ×10; §4a own production code clean (the 2
  residual doc pointers are pre-existing #1246/#1250). **PR-1 is now GitHub PR
  [#1516](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1516) — OPEN, ready-for-review,
  MERGEABLE**, base `main`, head `deanlorenz:ta-anchor-refactor-v2@075a208e`, reviewer ev-shindin,
  assignee deanlorenz, title *"refactor(pipeline): derive the per-model anchor on demand; add analyzer
  enablement"* — opened by the planner on Dean's explicit authorization. Deletion classes now formally
  recorded (review-confirmed): **DEPRECATED** the `saturationEntry(...)` getter, superseded by
  `bindingAnchor` (the always-saturation-is-the-sizing-source assumption is gone); **DEFERRED** the QM
  optimize path — `optimizeQueueingModel` / `runQueueingModelAnalysis` / `buildQMConfig` stay in-tree
  behind a blank reference so staticcheck U1000 stays quiet, and re-enabling is just restoring the
  dispatch (**this is the existing F10 re-enable path, not a new backlog item**). **Residual disposition
  (Dean's call, non-blocking):** rebasing before #1513 merged folded the goldens into PR-1's own history,
  so their §4a header tokens ride #1516's diff — accept, or merge #1513 first; either way the coder must
  **NOT** rewrite those goldens commits (would diverge from `origin/ta-anchor-goldens`). New forward item:
  **PR-1 Finding 12** (`Role:` vs `vs.Role`, `throughput/analyzer.go:409-413`) needs an issue-or-fold call
  from Dean and must **not** be fixed in PR-2. Review docs
  `planning/ta-anchor-refactor-v2-code-review.md` + `ta-anchor-refactor-review.md` Part 3/Round 2 remain
  DRAFT and **uncommitted** on the plans worktree — reviewer-owned; flag before any worktree reset.
  Old branch `ta-anchor-refactor@34055d77` left unpushed, for Dean to `git boidem` at his convenience.
  Out-of-scope/deferred for PR-1: QM path (explicit-error refusal, DEFERRED §12), AnalyzerName
  validation (separate PR), the sat `Cost=0`-for-zero-replica bug (separate fix); **§2.4 partial
  scale-from-zero picker is no longer deferred — RETIRED as a separate scope item** by PR-2's C11 (the
  sentinel + one-replica cap makes the choice exist, and the existing cost / fair-share ranking *is* the
  picker); PR-1's own §12 still lists it, so the Type 3 keeps it struck-through-with-reason.
  **PR-2 `ta-anchor-dynamic-refresh` — CODING IN FLIGHT, PAUSED awaiting Dean's resume-coding
  go-ahead.** ONE indivisible PR, **stacked/parallel on PR-1 — NOT merge-gated**. Commit map is now
  **C1–C11** — the four remaining commits became **seven**: **C6c** (bug #5 currency pivot) · **C6d**
  (finding (c) + bug #5 site (iii)) · **C6e** (new — `W1` fair-share double-spend) · **C6f** (new —
  `W4` abstain-when-unpriced) · **C11** (new — `FZ-admission`) · **C10** (`k_sat`) · **C9**
  (dev-guide + goldens); **git order ≠ label order**:
  `C1–C5 → C7 → C8 → C6a–C6b → C6c → C6d → C6e → C6f → C11 → C10 → C9` — C6c-before-C6e/C6f/C11 is
  **load-bearing, not convenience**: C6c is the only one of the four that preserves behavior, so keeping
  the behavior changes after it is what makes a per-commit golden re-run attributable. Landed: C1–C5 + C7 + C8 + C6a (`8eb6ee2d`, +392/−110) +
  C6b (`d9f3b97e`, +198/−23), all DCO-signed, all gates green (`gofmt`, `go build`, `go vet`,
  `go test -count=1`, `make lint` 0 issues), **no golden moved** (incl. the #1513 saturation-only
  goldens and the two-analyzer combine golden) — **true of the landed commits only; do not read it
  forward onto C6c**, where the `ceil → floor` change legitimately *may* move a `[sat]`-only golden.
  **C6c has zero edits** — scoped read-only, then held on Dean's call (*"bigger change … send a handoff
  to planner"*); its six questions were **all answered inside the Type-3 refresh** — confirmed by the
  coder after re-reading §0/§1.1/§2d.5 at `1a116e7a` (Q1 extraction guidance §2d.5 — capture the value,
  don't re-derive the rule; Q2 → site (v), converted-not-deleted; **Q3 → unit-table row 8** = keep `ps`
  raw and convert the *bound* down through that analyzer's own PRC + `GPUsPerReplica`, which was the
  third shape the coder had proposed; **Q4 → unit-table row 5** = `priority × claim` is a dimensionless
  **rank** that is never spent (invariant 11, *"priority orders, never scales"*) — *dividing `priority`
  back out* is `W2`, deferred **and settled**, which is a different question from Q4 itself; **Q5 → a
  reversal, not a coder misread** — the pre-refresh answer was "site (iii) stays in C6c", and the freeze
  moved it to C6d as unit-table row 7 because it is the one bug-#5 site on the scale-down path, where
  `U2`'s negative test belongs; Q6 → T1.4 splits §2d.6), so
  `plan__ta-anchor-c6c-fairshare-currency.md` is now `.DONE`. ⚠️ That handoff is a **historical record,
  not a spec** — it was written 10:58 against a plan revision the refresh superseded, and its site-(ii)
  `ceil(target)` proposal is **ruled out by the GPU-space pivot** — the fair-share target is a GPU
  quantity (unit-table row 4) and the single whole-replica conversion happens once, at `fairShareCap`,
  as a **`floor`** of `remaining_GPUs / GPUsPerReplica` (row 6); there is no per-role reference PRC to
  thread, so a `ceil(target × prcRef/PRC)` cap has no referent. Do not implement C6c from it.
  ⚠️ **The `prcRef` machinery is retired, not refined** (§2d.5 *What stops existing* — *"delete on sight;
  do not port forward"*): any text or future handoff citing `prcRef` as something the coder must thread
  is stale by that token, including the earlier framing in this file.
  **Three-step gate (Dean, 2026-08-07): (1) Type-1 freeze — ✅ CLEARED** (`combined-analyzer-optimizer-design.md`
  **Status: FINAL, frozen 2026-08-07 @ `8c2a9b04`**, decision queue **EMPTY**; `FZ-admission` decided
  *in the Type 1* per *"don't leave design decsions to coder"* — mechanism = a `Reason`-tagged
  **`PRC = 1` sentinel** in `PerReplicaCapacity` (separate eligibility predicate rejected: six gate
  sites, and it splits eligibility from ranking), cap = a one-replica **target** ceiling at the three
  sites that can grant replicas; stated principle — a design choice the Type 1 declines to make is a
  defect in the Type 1, not coder latitude). **(2) Type-3 refresh — ✅ CLEARED** — the Type 3 was
  refreshed against the frozen Type 1 and committed on `plans` as **`1a116e7a`** (2283 lines, TOC
  regenerated by `scripts/toc-refresh.sh`, 15 top-level sections; **no code changed**, still
  coder-ready). **(3) Resume coding — the only remaining gate: Dean's explicit go-ahead.** He starts the
  coder; the planner is *not* arming the kickoff. Coder **and** its code reviewer are both still holding
  (`review__ta-anchor-dynamic-refresh-checklist` remains `.HOLD`; the coder's own
  `ta-anchor-dynamic-refresh__kickoff` is `.WIP` — consumed back when coding started, so don't look for
  a held kickoff — and no *new* one is being armed);
  the coder's **C10-first offer is declined**. The coder has confirmed it read the planner's
  spec-complete clearance as **FYI, not permission** ("do not code yet") — branch unchanged at
  `d9f3b97e`, tree clean, nothing pushed. **Bug #5's currency is GPU space, not replica space** —
  `toGPUs(metric, PRC, GPUsPerReplica)`, nine-row per-site unit table in plan §2d.5. Two consequences:
  (1) the **landed C3 `roleAggRemaining` stays in replica space** and needs no re-denomination; (2)
  `fairShareCap` becomes a whole-replica **`floor`** fill (was `ceil`) — a **one-replica behavior
  change** at every mid-replica boundary, to be called out in C6c's commit message. New plan section
  **§2f** carries the `FZ-admission` transcription (mechanism + cap, both decided in the Type 1).
  **Fold-in dispositions, now landed in the plan rather than pending:** `W1` → **C6e**; `W4` → **C6f**;
  `W5` → **C6c**; `W3` and `U5` → **C9, documentation only** (rename nothing, add nothing);
  `FZ-admission` → **C11 + §2f**. **`W2` with `U4` is deferred *and settled, not open*** — answered,
  then deferred as a future TODO on Dean's own criticality test; it must not be recorded anywhere as an
  open question. **C10 (`k_sat` fold-in, plan §2e):** TA hard-codes `DefaultKSat = 0.85` (an HPA-style
  *watermark*, not a utilization target) instead of saturation's `KvCacheThreshold` (0.80), and never
  reads the `input.Config` it receives → `resolveKSat` resolver threaded through four call sites
  (`ITLAt` in `Analyze`, `computeVariantSupply`, `validITLModel` → exported `FitITLModel` +
  `resolveITLModel`, `checkVariantGPSMismatch`); `DefaultKSat` **deleted** (DEPRECATED), fallback
  `DefaultKvCacheThreshold` (0.80), `DefaultNearKSatMargin` (0.10) retained. **Effect is sub-1%, not
  "~6%"** — `kSat` enters PRC *twice* (`N_sat = kSat·KV_max/KVreq` divided by `itlSat = A·kSat + B`),
  so `μ(0.80)/μ(0.85) = (0.80/0.85)·(A·0.85+B)/(A·0.80+B)`; realistic band **0.4%–2.5%**, **−0.548%**
  on the shipped fixture (`A=0.073 B=0.006`) — justification is **correctness + configurability**, not
  a systematic correction. Also absorbs the four arithmetic bugs (**#5 is five lock-step sites, not
  three**), per-iteration dynamic re-binding, the combine-liveness hardening (VG-up `Enabled&&Live`,
  N8 drop-the-(b)-fallback, N2/N7 tie-break/abstain), and §2c notation cleanup. Branch local tip
  `d9f3b97e`; `origin/ta-anchor-dynamic-refresh@f6485980` orphaned by PR-1's reword (force-push
  pending Dean's OK). **Fold-in scope** (Dean: *"everything folds into PR-2"*; roll-up table at
  `combined-analyzer-optimizer-design.md:2064`) — **in:** currency pivot/`W5`, `W1`, `W4`,
  `FZ-admission`, `VG-up`, the 4 arithmetic bugs + re-binding; **out:** `W2` with `U4`, `U5`'s new
  metric series, `N9` (reactive `scalefromzero` residual), `AnalyzerName` validation, sat `Cost = 0`
  zero-replica (`N5`); `W3` = documentation only. Open GitHub-issue questions (Dean's call, none filed
  yet): the QM multi-analyzer-contract work, and the sat-v2 zero-replica `Cost=0` bug. **Doc taxonomy
  (Dean, 2026-08-07):** `planning/multi-analyzer-dataflow-map.md` and `ta-anchor-refactor-review.md`
  Part 2 are formally **source traces, not authorities** — cite for per-site line evidence only; where
  a map and the Type 1 disagree, the Type 1 governs and the map is stale. Two corrections not to carry
  downstream: review finding **V6**'s claim about the (b)-fallback's domain is **inverted** (superseded
  by `N1`), and `applyAllocation` is **not** a sentinel sizing hazard (it reads the ballot, never the
  anchor) — the real unbounded grant is `fillRole`. Design authority
  [`planning/combined-analyzer-optimizer-design.md`](../planning/combined-analyzer-optimizer-design.md)
  — **Status: FINAL, frozen 2026-08-07 @ `8c2a9b04`**; governs the Type 3 on disagreement;
  plans [`planning/ta-anchor-refactor-v2-plan.md`](../planning/ta-anchor-refactor-v2-plan.md) (FINAL) /
  [`planning/ta-anchor-refactor-plan.md`](../planning/ta-anchor-refactor-plan.md) (SUPERSEDED) /
  [`planning/ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md) (tip
  **`1a116e7a`** — refreshed against the frozen Type 1).
- **2026-08-07 — autoscaling-viz: real-trace toolchain built, MIGRATED to its own branch + worktree,
  near path is our own runs.** Four-command chain `fetch_run.sh` → `extract_real_trace.py` →
  `render_real_trace.py` → `publish_result.sh` (≈2 k lines of Python + a `README.md`; `publish_result.sh`
  never pushes), exercised end-to-end on our own 2026-08-03 staircase run
  (`real-trace/staircase-20260803/`): **12 PASS / 4 FAIL** coverage, capacity model within **0.6%** of the
  observed concurrency ceiling with **zero free parameters**, measured ITL knee agreeing with the
  prefill-heavy prediction, 94 s boot lag cleanly captured (`desired` 1→2 at t+454 s, `ready` at t+548 s).
  **Migration EXECUTED** (Dean's go-ahead; branch name is **`autoscaling-viz`**, *not* `viz-tools`) —
  `git subtree split -P scratch/autoscaling-viz`, worktree at container top level, **orphan lineage
  verified** by set-intersecting `rev-list` (0 commits shared with `plans`), 145 tracked files, clean.
  Home had to move before the tools could be shared at all: `plans` is an orphan branch of internal
  state, so cloning it to hand over a plotting script hands over CURRENT.md and every planning/review
  doc. **The split nearly lost the one irreplaceable input** — `metrics/raw/` (217 Prometheus scrape
  files, 20 MB, the only time-resolved metrics source) was hidden from `subtree split`'s tracked-files-only
  semantics by a **nested** `.gitignore`; now durable as `metrics-raw.tar.gz` (**1,935,604 bytes**,
  ≈10.5:1). `per_request_head.json` (2.4 MB) deliberately stayed out on the **no-prompt-text rule**
  (plan §15.2 — 50 records embed 0.86 MB of prompt + SSE text, so it is a rule, not a size budget); cost
  measured via a simulated fresh clone: **8 PASS / 7 FAIL** from a clone vs 12/4 locally (the gap is
  exactly the per-request-derived rows + panels 1/4) — future fix is a text-stripped numeric-only head,
  not committing the file. Completeness verified **by content**: preserve copy
  `~/viz-migration-preserve-20260807` (419 files, 51 MB), every file `cmp`-compared, bijection closed
  exactly (145 split + 274 copied = 419); recommend **not** deleting it yet — it is the only copy of
  `per_request_head.json` outside the worktree. `results/` is now tracked. **Prose reproducibility
  verified** (Dean asked): no prose is hand-authored into `out/` — every phrase resolves to a string
  literal in tracked Python (`stability.py` / `run.py` / `sweep.py` / `report.py`), regeneration is
  `python run.py && python report.py`, seeded `random.Random(1)`, deterministic; the HTML is a build
  artifact, safely. **Dean's originals policy (new, load-bearing):** *"no need to keep GB originals. They
  live where they were born … I don't copy over and never commit."* → the durable artifact is the
  processed form plus a provenance ref; this is what invalidated "regenerable via `fetch_run.sh`".
  **Near path is our own runs, not Ofer's** (he is out this weekend): re-fetch the full per-request file
  (the committed demand trace is a 50-record head covering **9.19 s of a 1276 s run**, time anchor
  `refused-short-trace`, and `post_run_analyze.sh` output was never captured), and re-design the run to
  hold at saturation then step down with requests in flight — all four FAILs collapse to that one run-design
  change. Panel 4 stays **deferred by Dean** (his order: finalise the fetch plan → fetch other runs →
  *then* panel 4). Still open on the design side: preemption modelling, first-cut scope (plan §12.2
  items 1–2), and a `runs/<label>/` + `provenance.json` restructure (deliberately kept out of the
  migration so completeness verification stayed clean). Plan + cold-resume entry point is
  `autoscaling-viz/real-trace-viz-plan.md` **in its own worktree** — do *not* link the `plans`-relative
  `scratch/` path, which is dead by design (`git rm -r scratch/autoscaling-viz` landed as `9ccd5e23`,
  145 files / −21702; the 227 MB `.venv`/leftover reclaim item is therefore moot). Pushed:
  `origin/autoscaling-viz` @ `a40dae11`, local tip **`40b28ee9`** (1 commit ahead — the plan-doc
  reconciliation that already fixed the "§14.4/§14.6/§15 + README still say viz-tools" staleness).
  `viz-results` retired (tag `archive/viz-results`). No PR Status row — no code branch, no PR, not headed
  upstream.
- **2026-08-03 — ta-itl-demand-test-gaps → PR #1511 OPEN.** The 3 optional ITL/demand/supply test-gaps
  ev-shindin flagged in PR F #1503 (plus a folded-in `computeVariantSupply` direct-coverage pair) shipped
  as **PR [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511)** into upstream
  `main` (head `ta-itl-demand-test-gaps@96263639`, base `main@6bfb73e1`, 5 test-only commits DCO-signed,
  reviewer ev-shindin, assignee deanlorenz). Two internal reviews APPROVE; review FINAL
  [`planning/ta-itl-demand-test-gaps-review.md`](../planning/ta-itl-demand-test-gaps-review.md). Targeting
  0.9 (freeze 2026-08-06); MERGEABLE, awaiting Evgeny + CI. Deferred: `checkVariantGPSMismatch` diagnostic
  coverage → separate future test-only task.
- **2026-08-03 — sat_v2 cannot be disabled via config (F1 gap); Dean spawning a separate planner.**
  Root-caused (not a regression): `saturation/engine_v2.go` unconditionally prepends the saturation result
  and `effectiveEnabled` skips it by name, so `saturation:{enabled:false}` is a silent no-op — traced to
  deferred design item F1 "Pre-analysis extraction" ([`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md):506-511).
  The existing `planning/wva-analyzer-lifecycle-plan.md` Commit-2c "zero-signal" design is **REJECTED by
  Dean** ("risky hack"; warnings added to the plan, commit `663a9624`) — a real fix must solve
  `VariantCapacities` sourcing, not fake a neutral result. Dean is spawning a dedicated planner to
  scope/design it (possibly still in 0.9 — freeze was delayed). Surfaced while the **benchmark TA-lead
  experiment** coder is holding, blocked on separate planner deliverables (two-phase calibration+trigger
  workload + a "faster" methodology) plus an open feasibility question (does TA raise RC ahead of
  `k_sat=0.85`, or key off the same threshold?) — independent thread, do not conflate.
- **2026-07-15 — optimizer-pd-role-ceiling: code+tests complete; dev-guide edits UNCOMMITTED; clean-design discussion in progress.** All 10 planned tests landed (6 commits, tip `0c33a3eb`, all gates green). **⚠️ Uncommitted state:** the planner (authorized by Dean; coder done) edited the Type 4 dev-guide directly in the worktree — saturation single-source note + worked example + edge-case→test table + why-coupled paragraph — **`M multi-analyzer-pipeline.md`, NOT committed** (pending Dean's review). Separately, Dean opened a design discussion on making the optimizer's data-flow/algorithm doc *clean* (analyzers→utilization desired/achieved; optimizer coordinates AND/OR; constraints); captured in new Type 1 doc [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) — **Phase 1 (discussion) done, Phase 2 (clean design) drafted & awaiting Dean's review of 2 framing questions, Phase 3 (verify code vs. clean model) not started.** Suspected real bug surfaced: anticipated supply is in the denominator, not counted toward achieved (see design doc § Open issues #2 — needs a trace). **Resume 2026-07-16:** answer the 2 Phase-2 questions, lock clean design, do Phase 3, then restructure dev-guide. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).

**Recently landed (1-liners; fuller entries in [`session/history.md`](history.md) → *Activity log*):**

- 2026-07-30 — `ta-testing` refreshed → `6bfb73e1`; signed tag `ta-0.9-test-20260730` + quay image `:ta-0.9` (registry digest `sha256:80dec0e9728f…`) both pushed (executes the §4.1 refresh trigger).
- 2026-07-31 — CURRENT.md / history.md restructuring committed on `plans` (landed history extracted to the archive).

**Older / historical:** the compressed activity tail (TA 0.9 era back through 2026-05) lives in [`session/history.md`](history.md) → *Activity log* sections — fetch one section at a time per that file's Reading Protocol, do not inline here. Most recent landmark: **TA 0.9 fully landed (all six PRs #1478/#1479/#1480/#1481/#1502/#1503) 2026-07-30, `main` tip `6bfb73e1`.**

---

## PR Status — open / active only

Landed & closed rows (TA 0.9 stack, TA3 & earlier missions, upstream reviews & proposals) are
archived in [`session/history.md`](history.md) → *PR Status* sections. Only in-flight / actionable
rows stay here.

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| wva-analyzer-lifecycle | — | **PLAN — PARTIALLY REJECTED / re-scoping.** Config-driven analyzer activation + ManagedAnalyzer lifecycle. Splits into **Half A** (config-driven lifecycle + live-set refactor — Commits 1/3/4/5; ~1–2 days; `effectiveEnabled`/Commit 3g already on `main`; main risk = `NewEngine` ripple vs in-flight #1501) and **Half B** (genuinely disabling saturation — Commit 2c **REJECTED by Dean 2026-07-31**: "zero-signal" is a risky hack; needs F1 "pre-analysis extraction" to solve `VariantCapacities` sourcing; unscoped). Dean spawning a **separate planner** to scope the real sat_v2-disable fix; awaiting his call: carve Half-A-only vs scope Half-B/F1 vs hold. Warnings added to plan (`663a9624`). Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| ta-itl-demand-test-gaps | [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511) | **OPEN** — cover ITL-model / demand / supply guard branches (ev-shindin's PR F #1503 non-blocking notes + folded-in `computeVariantSupply` pair). Head `ta-itl-demand-test-gaps@96263639`, base `main@6bfb73e1`, 5 test-only commits DCO-signed, `origin/ta-itl-demand-test-gaps` pushed. Reviewer ev-shindin, assignee deanlorenz. Two internal reviews APPROVE; review FINAL [`planning/ta-itl-demand-test-gaps-review.md`](../planning/ta-itl-demand-test-gaps-review.md). Targeting 0.9 (freeze 2026-08-06). MERGEABLE; awaiting Evgeny + CI. Plan: [`planning/ta-itl-demand-test-gaps-plan.md`](../planning/ta-itl-demand-test-gaps-plan.md). | `96263639` |
| ta-anchor-goldens | [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513) | **OPEN** — characterization "golden" gate (test-only, +409/−0, 1 file) freezing the saturation-only optimizer decision SET (keyed by VariantName; land-first ship gate for the anchor refactor). Head `ta-anchor-goldens@a2f49ccf`, base `upstream/main@9906dac5`, reviewer ev-shindin, `origin/ta-anchor-goldens` pushed. Internal review FINAL (Finding 1 fixed; Finding 2 = `withSatEntry`-stability note carried to PR-1 kickoff). Plan: [`planning/ta-anchor-goldens-plan.md`](../planning/ta-anchor-goldens-plan.md); review [`planning/ta-anchor-goldens-review.md`](../planning/ta-anchor-goldens-review.md). | `a2f49ccf` |
| ta-anchor-refactor | — | **SUPERSEDED (2026-08-05) by `ta-anchor-refactor-v2`** — see that row. Stored-`ModelScalingRequest.Anchor` design (Aug-4 review fold-in `68bda1a1`/`192ae06b`) found unnecessarily complex; superseded by a no-stored-field two-phase redesign. Plan doc header marked `Status: SUPERSEDED` (commit `9721b587`); kept for history (Part 1 subject of `planning/ta-anchor-refactor-review.md`). Branch commit `34055d77` left unpushed; Dean to `git boidem` at his convenience. Plan: [`planning/ta-anchor-refactor-plan.md`](../planning/ta-anchor-refactor-plan.md) (superseded). | `34055d77` (unpushed, superseded) |
| ta-anchor-refactor-v2 | [#1516](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1516) | **OPEN (ready-for-review, MERGEABLE) — push-ready review APPROVE.** PR title *"refactor(pipeline): derive the per-model anchor on demand; add analyzer enablement"*; base `llm-d/…:main`, head `deanlorenz:ta-anchor-refactor-v2@075a208e`, reviewer ev-shindin, assignee deanlorenz; opened by the planner on Dean's explicit authorization. Push-ready review verdict **APPROVE**: rebase integrity PASS (`git diff --stat pre-rebase-f6485980 075a208e` = exactly 4 files — #1509's `cmd/main.go`, 2 new watcher files, the intended F3 rewrap — with the other 22 stack files and all 5 goldens **byte-identical**, so no silent hunk loss), DCO ×10, §4a own production code clean (2 residual doc pointers are pre-existing #1246/#1250). Deletion classes: **DEPRECATED** `saturationEntry(...)` getter → superseded by `bindingAnchor`; **DEFERRED** the QM optimize path (`optimizeQueueingModel`/`runQueueingModelAnalysis`/`buildQMConfig` retained in-tree behind a blank reference so staticcheck U1000 stays quiet; re-enable = restore the dispatch — **this is the existing F10 path, not a new backlog item**). Residual (Dean's call, non-blocking): the #1513-owned goldens ride #1516's diff since the rebase preceded #1513's merge — accept, or merge #1513 first; either way the coder must **NOT** rewrite those goldens commits. New forward item: **Finding 12** (`Role:` vs `vs.Role`, `throughput/analyzer.go:409-413`) needs Dean's issue-or-fold call and must **not** be fixed in PR-2. Live PR-1 plan: no-stored-field two-phase anchor mechanism (Phase-1 tags ballot entries `Enabled`; Phase-2 `bindingAnchor` derives the anchor on demand, per-variant merge keyed by `VariantName`). Plan `Status: FINAL` (`c279bdeb`) on `plans`; review is Part 3 + **Round 2** of `planning/ta-anchor-refactor-review.md` (still DRAFT, and that content is **UNCOMMITTED** in the shared worktree — flag if a worktree reset is proposed) — verdict APPROVE both rounds (review content pending commit), zero MAJOR/correctness findings; Round 2 (2026-08-05, reconciled against `2e83c7fe`) resolved the earlier `[sat,TA]` core concern and found 4 doc-only findings V8–V11, all folded into the FINAL plan. Scale-from-zero cost/PRC design (`2e83c7fe`, supersedes the interim MAX-sentinel version `2ccf51b7`): TA emits PRC only, (b)-fallback enablement-gated, `[TA]`-only zero-replica suppressed to PRC=0 with a documented (not gated) known-limitation. Scope: 5 commits (Phase-1 / Phase-2 / QM-as-error+liveness-noop / TA-PRC-only complement / dev-guide); zero combine-arithmetic change; decision-SET-identity ship gate via #1513 goldens; opt-in enablement. Deferred/out-of-scope: QM path (DEFERRED §12), AnalyzerName validation, sat `Cost=0`-for-zero-replica bug; the §2.4 partial scale-from-zero picker is **no longer deferred — RETIRED as a separate scope item** by PR-2's C11 (PR-1's own §12 still lists it, so the Type 3 keeps it struck-through-with-reason rather than deleted). Branch `ta-anchor-refactor-v2` @ `075a208e` (base rebased onto `upstream/main@aadaa596`/#1509; 5 goldens ride the diff since #1513 is unmerged), **pushed to `origin/ta-anchor-refactor-v2`** (Dean-authorized). C1–C5 all landed + reworded (F1/F3/F4 in the rebase, F2 knowingly relaxed w/ Dean's explicit sign-off — infeasible for Test 5's annotation-sourced fixture, the engine persists no CRD status); §13 + per-commit goldens/Test 9 green + DCO on all 10; recovery tags `pre-rebase-f6485980`/`post-rebase-clean`. Coder status file is current. **Next:** ev-shindin's review + CI on #1516; Dean's calls on the goldens ride-along and on Finding 12. Review doc `ta-anchor-refactor-v2-code-review.md` DRAFT (uncommitted, reviewer-owned — committing it is the review agent's job). Plan: [`planning/ta-anchor-refactor-v2-plan.md`](../planning/ta-anchor-refactor-v2-plan.md). | `075a208e` (C1–C5 + 5 goldens; on origin) |
| ta-anchor-dynamic-refresh | — | **CODING IN FLIGHT — PAUSED awaiting Dean's resume-coding go-ahead (gate steps 1–2 CLEARED); stacked/parallel on PR-1 (NOT merge-gated).** ONE indivisible PR-2: multi-vote combine (§1) + 4 arithmetic bug fixes #1/#2/#3/#5 (§2 — **#5 is five lock-step sites, not three**) + per-iteration dynamic re-binding (§3) + combine-liveness hardening (§2b: VG-up `Enabled&&Live`, N8, N2/N7) + (a)/(b) notation cleanup (§2c) + **C10 `k_sat` fold-in (§2e)** + **C11 `FZ-admission` (§2f)**. Commit map **C1–C11** — the four remaining commits became **seven**: **C6c** (bug #5 currency pivot) · **C6d** (finding (c) + bug #5 site (iii)) · **C6e** (new — `W1` fair-share double-spend) · **C6f** (new — `W4` abstain-when-unpriced) · **C11** (new — `FZ-admission`) · **C10** (`k_sat`) · **C9** (dev-guide + goldens). **git order ≠ labels**: `C1–C5 → C7 → C8 → C6a–C6b → C6c → C6d → C6e → C6f → C11 → C10 → C9` — C6c-first is **load-bearing** (only behavior-preserving one of the four ⇒ per-commit golden re-runs stay attributable). Landed C1–C5 + C7 + C8 + C6a (`8eb6ee2d`) + C6b (`d9f3b97e`), DCO-signed, all gates green, **no golden moved — of the landed commits only; do not read forward onto C6c**, where `ceil → floor` may legitimately move a `[sat]`-only #1513 golden. **C6c zero edits** (held on Dean's call; its six questions all answered inside the refresh, coder-confirmed against `1a116e7a` — Q3 → row 8, Q4 → row 5 (`priority` is a rank, never spent), **Q5 = a reversal** (site (iii) moved C6c→C6d), so `plan__ta-anchor-c6c-fairshare-currency.md` is now `.DONE`; it is a historical record, **not a spec**: its site-(ii) `ceil(target)` shape is ruled out by the GPU-space unit table (rows 4 and 6 — one `floor` conversion at `fairShareCap`, **no per-role reference PRC**; the `prcRef` machinery is retired, so any text citing it as a coder requirement is stale)). **Bug #5's currency is GPU space, not replica space** — `toGPUs(metric, PRC, GPUsPerReplica)`, nine-row unit table §2d.5 ⇒ landed **C3 `roleAggRemaining` stays replica space** (no re-denomination), and `fairShareCap` becomes a whole-replica **`floor`** fill (was `ceil`) = a one-replica behavior change to flag in C6c's message. **Three-step gate:** (1) Type-1 freeze ✅ **CLEARED** (`combined-analyzer-optimizer-design.md` FINAL/frozen @ `8c2a9b04`, queue EMPTY, `FZ-admission` = `Reason`-tagged `PRC = 1` sentinel + one-replica target ceiling at the 3 granting sites); (2) Type-3 refresh ✅ **CLEARED** (`1a116e7a`, 2283 lines, TOC regenerated, 15 sections, no code changed, still coder-ready); (3) **resume coding — Dean's explicit go-ahead only.** He starts the coder; the planner is not arming a *new* kickoff (`review__…-checklist` stays `.HOLD`; the coder's `__kickoff` is `.WIP` from the original start of coding). Coder **and** code reviewer still holding; C10-first offer **declined**. C10: `resolveKSat` resolver + 4 threaded call sites, `DefaultKSat` **deleted** (DEPRECATED), fallback `DefaultKvCacheThreshold` 0.80 — effect is **sub-1%** (`kSat` enters PRC twice; band 0.4–2.5%, **−0.548%** on the shipped fixture), justified by correctness + configurability, **not** "~6%". Fold-in dispositions now **landed in the plan**: `W1`→C6e, `W4`→C6f, `W5`→C6c, `FZ-admission`→C11+§2f, `W3`+`U5`→C9 **docs only**; **out:** `W2`+`U4` (**deferred *and settled* — not an open question**), `U5` metrics, `N9`, `AnalyzerName` validation, sat `Cost = 0` (`N5`). **§2.4 partial scale-from-zero picker RETIRED** as a separate scope item (C11 subsumes it). Local tip `d9f3b97e`; `origin/ta-anchor-dynamic-refresh@f6485980` orphaned by PR-1's reword (force-push pending Dean's OK). Handoff hygiene done by the planner: the **seven** stale coder triggers (read by the coder 2026-08-07 ~11:10, content superseded by the freeze) are now `.DONE`, replaced by one refs-only trigger — `ta-anchor-dynamic-refresh__c6c-onward-plan-refreshed.md` (the handoff named it `__type1-frozen-plan-refreshed`; it was renamed + rewritten at 19:25 and the coder has already marked it `.WIP`); four `plan__` handoffs consumed by the refresh are `.DONE`. Plan: [`planning/ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md) (tip **`1a116e7a`**; Type 1 governs on disagreement). | `d9f3b97e` (local; origin @ `f6485980`) |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; clean-design discussion in progress** — 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). Clean-design capture: [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) (Phase 2 drafted, awaiting Dean; suspected anticipated-supply-in-denominator bug flagged). Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| (upstream) rate-anchored k2 | #1501 | **Reviewed 2026-07-30 — COMMENTED posted** (deanlorenz, 15:54:47Z) — rate-anchored `k2` estimator for saturation-v2 (fixes #1500 shed-to-one on prefill-heavy traffic). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` (unconditional registration adds per-cycle Prometheus load in the default TA-off config — load-only, no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR — no worktree. Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md). | (incoming) |
| ta-testing (integration) | — | **REFRESHED 2026-07-30 → tip `6bfb73e1`** (§4.1 trigger EXECUTED). Repointed to `upstream/main` directly (`git checkout -B`, pointer move, no hand-merge) now C/D/E/F all merged. New signed tag `ta-0.9-test-20260730` **pushed to origin** (does not replace the historical `ta-0.9-test-20260728` on `db530eed`). All gates green (`make test`/lint/build; `pkg/` gone → drop from the 3-dir gofmt invocation past this tip). Image `quay.io/deanlorenz/llm-d-workload-variant-autoscaler:ta-0.9` **pushed to quay** (local ID `sha256:3d438b65c8…`, registry digest `sha256:80dec0e9728f…`, linux/amd64). **Integration role now vestigial** — a plain `main@6bfb73e1` checkout already has everything C/D/E/F contributed; branch value is just a stable Dean-owned tag/image pipeline name. Cleanup deferred (old tag + stale `origin/ta-testing`@`db530eed` + local `ta-model-level-demand` worktree — non-urgent, at Dean's direction). Status: `session/status/ta-testing.md`. | `6bfb73e1` |

---

## Blocked on

- **Pokprod TA benchmark — first live controlled standup** is blocked on **Dean's explicit go-ahead**
  (Phase-4 Step 0). All prep is done (dry-run, hazard analysis, fork patches, Phase-3 namespace setup);
  also awaiting Dean's OK on 3 fork-only pushes (`6505de62`, the 3 presence-gate patches) and the
  upstream-patch-proposal decision. See § Benchmark + `session/status/benchmark.md`.

## Next steps

- **TA 0.9 coding — FULLY LANDED (all six PRs MERGED 2026-07-30; `main` tip `6bfb73e1`).** Per-PR merge
  detail + roll-up in [`session/history.md`](history.md) (PR Status + Activity log). Trackers #1495/#1496/#1497 CLOSED (C and F
  have none — under the epics). **Remaining follow-ups (all optional / GitHub-write / need Dean's
  direction):** (1) epics #1492/#1493/#1494 + adopted #1005 — decide whether to update/close now all
  PRs merged; (2) the 3 optional test gaps on F are now **shipped as PR [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511)** (open, reviewer ev-shindin — see PR Status row); (3) PR #1501 ask-#1 watch (see PR Status row);
  (4) governance retrospective open Q — in [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md);
  (5) cleanup — old tag `ta-0.9-test-20260728` + stale `origin/ta-testing`@`db530eed` + local `ta-model-level-demand` worktree; non-urgent, raise removal with Dean (see `ta-testing` PR Status row).
- **TA 0.9 test-branch + controller-image refresh (§4.1 trigger — EXECUTED 2026-07-30).** Done: `ta-testing`
  repointed to `main@6bfb73e1`, signed tag `ta-0.9-test-20260730` pushed to origin, image `:ta-0.9` (digest
  `sha256:80dec0e9728f…`) pushed to quay — all Dean-authorized. See the `ta-testing` PR Status row; no
  outstanding action for this refresh.
- **TA 0.9 release notes / Highlights — DEFERRED to code freeze.** Mechanism + drafts in
  [`planning/ta-0.9-release-notes.md`](../planning/ta-0.9-release-notes.md): the ` ```release-note ``` `
  PR block is NOT auto-harvested (no `.github/release.yml`); GitHub auto-notes derive from PR
  *titles* in `v0.8.0..v0.9.0`; the only editorial lever is a hand-written `## Highlights` block at
  release. Highlights draft ready but held until code freeze. Do NOT create an in-repo
  `docs/CHANGELOG-v0.9.0.md`. Slack epics + Highlights notes already POSTED by Dean 2026-07-29.
  Design-docs PR (item 5) still DEFERRED post-code-freeze.
- **Rescale Beta PRs — re-check against RC-2/RC-4 when they land.** PR #1452 (rescale Alpha) merged
  2026-07-28. Tracking issue [#1447](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1447)
  covers RC-1 (damping bypass) and RC-3 (#1003-deferred partition) but its text does **not** mention
  RC-2 (reclaim bypasses the multi-analyzer scale-down gate) or RC-4 (P/D fill lacks joint per-role
  throttle), despite ev-shindin's reply calling all four "valid and addressed in beta." Dean is
  following up with Evgeny directly as the primary path; this is the backstop — when a Beta-stage
  rescale PR shows up for review, check it against [`planning/PR1452-review.md`](../planning/PR1452-review.md)
  § RC-2/RC-4 before assuming they're resolved.
- **llm-d/llm-d guides currency check (NEW, planner task — Dean directive 2026-07-30).** Read the
  canonical **llm-d/llm-d** `guides/` on `main` (explicitly *not* the WVA repo guides, *not*
  llm-d-benchmark docs) and diff the recommended standup against what our `benchmark-standup(-shared)`
  flow actually applies (via the `deanlorenz/llm-d-benchmark` fork, `wva-ta-benchmark`); flag anything
  where the benchmark standup lags. Coder head-start already found: (a) vLLM image `v0.25.0` in
  `guides/recipes/modelserver/components/images/gpu-vllm/` — **already applied** to `hack/benchmark/.env`
  (was `v0.14.0`); (b) a `USER=llm-d` env workaround for vllm-project/vllm#44548 the guides treat as
  required at v0.20.0+ — **verify the benchmark ms-values template injects it**; (c) guides are now
  kustomize-**Component** based (images centralized under `recipes/modelserver/components/images/<accel>`)
  vs the helmfile flow the benchmark standup uses — assess topology match; (d) there is a
  `workload-autoscaling` guide in llm-d/llm-d worth reading as the canonical autoscaling standup
  reference. Drift feeds either `.env` (coder-appliable local pins) or `wva-ta-benchmark` fork patches;
  do **not** block the pending live standup on this unless something is a correctness hazard. Full
  brief was in handoff `plan__llm-d-guides-standup-currency-check.md`.
- **TA forward plan — P0 items all DONE** (I-21/22/23 via A #1478, I-5 both halves via A′ #1479 + E #1502).
  Next: review [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md) with Dean before coding P1 items
  (collector key unification I-1 = highest-risk correctness; test-rot I-11 unlocks reviewability).
- **sat_v2 cannot be disabled via config (F1 gap) — awaiting Dean's separate planner + scope call (2026-08-03).**
  Root cause: `saturation/engine_v2.go` unconditionally prepends the saturation result and
  `effectiveEnabled` only skips it by name, so `saturation:{enabled:false}` is a silent no-op. The real
  fix requires F1 "pre-analysis extraction" ([`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md):506-511)
  to source `VariantCapacities` independent of the saturation scaling contribution. The
  `wva-analyzer-lifecycle-plan.md` Commit-2c "zero-signal" design is **REJECTED** (risky hack; warnings
  committed `663a9624`). Dean is spawning a dedicated planner; do NOT start the real fix until he scopes
  it. Interacts with the benchmark TA-lead thread below (that coder wants sat_v2 off) — keep separate.
- **wva-analyzer-lifecycle (PLAN — PARTIALLY REJECTED / re-scoping):** ManagedAnalyzer lifecycle
  (Activate/Deactivate/Reactivate), config-driven registration, live-set refactor, effectiveEnabled fix,
  remove startup gate. **Split**: Half A (lifecycle/live-set — Commits 1/3/4/5, low-risk, ~1–2 days; note
  Commit 3g's effectiveEnabled fix already landed on `main`) vs Half B (disabling saturation — Commit 2c
  REJECTED, needs the F1 fix above). Awaiting Dean's carve/scope/hold decision (see PR Status row). Plan:
  [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). Supersedes the
  `PR1266-fixup-effectiveEnabled.md` stopgap.
- **anchor-refactor mission (ta-anchor-goldens #1513 → ta-anchor-refactor-v2 PR-1 → ta-anchor-dynamic-refresh PR-2):**
  goldens ship gate is **PR [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513)**
  (open, reviewer ev-shindin, land-first). **PR-1 was redesigned 2026-08-05**: the review agent found the
  stored-`.Anchor` design (Aug-4 fold-in `68bda1a1`/`192ae06b`, abandoned branch commit `34055d77`)
  superseded by a simpler no-stored-field two-phase mechanism — old plan `ta-anchor-refactor-plan.md` now
  `Status: SUPERSEDED`; live plan **`planning/ta-anchor-refactor-v2-plan.md`** is now **Status: FINAL**
  (`c279bdeb`). Reviewed across Part 3 + **Round 2** of `planning/ta-anchor-refactor-review.md` (still
  DRAFT, and that content is **UNCOMMITTED** in the shared worktree) — **verdict APPROVE both rounds**
  (review content pending commit), zero MAJOR/correctness findings; Round 2 (reconciled against plan tip
  `2e83c7fe`) resolved the earlier `[sat,TA]` core concern and found 4 doc-only findings V8–V11, all
  folded into the FINAL plan. Scale-from-zero cost/PRC design (`2e83c7fe`; supersedes the interim
  MAX-sentinel version `2ccf51b7`): TA emits PRC only, (b)-fallback enablement-gated, `[TA]`-only
  zero-replica suppressed to PRC=0 (documented, not gated, known-limitation — resolved later by a
  separate sat `Cost=0` fix). **PR-1 is now GitHub PR
  [#1516](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1516) — OPEN, ready-for-review,
  MERGEABLE** (head `075a208e`, reviewer ev-shindin, assignee deanlorenz); push-ready review **APPROVE**
  (rebase integrity PASS — 22 stack files + all 5 goldens byte-identical; DCO ×10; §4a clean). Old branch
  `ta-anchor-refactor@34055d77` left unpushed for Dean to `git boidem`. **Open on PR-1 — all Dean's calls:**
  (a) the goldens ride-along (accept #1513's §4a tokens in #1516's diff, or merge #1513 first — the coder
  must **not** rewrite those goldens commits); (b) **Finding 12** (`Role:` vs `vs.Role`,
  `throughput/analyzer.go:409-413`) — issue or fold, but **not** in PR-2; (c) marking the review docs FINAL
  (the review agent must commit the still-uncommitted `ta-anchor-refactor-v2-code-review.md` +
  `ta-anchor-refactor-review.md` Part 3/Round 2 edits — not the planner's/sync's job); (d) two
  GitHub-issue questions, none filed: QM multi-analyzer-contract work, sat-v2 zero-replica `Cost=0` bug.
  `plan__ta-anchor-dataflow-map-pr1-delta.md` remains an open planner-task (optional §9 addition to
  `multi-analyzer-dataflow-map.md`, deferred by Dean — not sync's to consume), now partly overtaken: the
  map's §9 findings live in the Type 1's § findings, so any delta work is about the map's own currency.
  **PR-2 `ta-anchor-dynamic-refresh` — coding IN FLIGHT (C1–C5+C7+C8+C6a+C6b landed, tip `d9f3b97e`),
  PAUSED at step 3 of the three-step gate:** Type-1 freeze ✅ → Type-3 refresh ✅ (`1a116e7a`) →
  **resume coding, which needs Dean's explicit go-ahead** (he starts the coder; the planner is not arming
  `ta-anchor-dynamic-refresh__kickoff` / `review__ta-anchor-dynamic-refresh-checklist`, both `.HOLD`).
  Commit map is now **C1–C11**; also his: the **force-push** of `origin/ta-anchor-dynamic-refresh`
  (`f6485980`, orphaned) to `d9f3b97e`. Design-level "what" questions `W1`–`W5` now live in the
  **Type 1's § open**, not in the task plan — and all of them are now dispositioned in the refreshed
  Type 3 (`W1`→C6e, `W4`→C6f, `W5`→C6c, `W3`→C9 docs-only, `W2`+`U4` deferred-and-settled);
  `planning/multi-analyzer-dataflow-map.md` and `ta-anchor-refactor-review.md` Part 2 are
  **source traces, not authorities**. ⚠️ **Time-boxed decision for Dean — the PR-2 §4a commit-message
  reword window closes when PR-2 opens.** A plans-branch token appears in **all nine** PR-2 commit messages
  (6/9 subjects, 8/9 bodies), **zero inherited** (grep at base `075a208e` is clean); a tenth commit cannot
  fix messages — only `rebase -i` + reword ×9. The branch needs a force-push anyway
  (`origin/…@f6485980` is orphaned), so it is ~free now and becomes a live-PR history rewrite once the PR
  opens. **Cost of waiting, now quantified in plan §4: 9 commits to reword now vs 16 later** (C6c/C6d/C6e/
  C6f/C11/C10/C9 each add another). *"Not worth it" is a legitimate answer; silence is not.* (The 32
  code/doc token locations are separate and unhurried — C9 is their natural host.) **`W2`/`U4` is no
  longer an open question for Dean** — it was answered and then deferred as a future TODO on his own
  criticality test (*"is this critical for TA integration. If not then it becomes a future TODO."*);
  record it as settled-deferred, not open.
  Plans: [`planning/ta-anchor-refactor-v2-plan.md`](../planning/ta-anchor-refactor-v2-plan.md) (FINAL),
  [`planning/ta-anchor-refactor-plan.md`](../planning/ta-anchor-refactor-plan.md) (superseded),
  [`planning/ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md);
  design authority [`planning/combined-analyzer-optimizer-design.md`](../planning/combined-analyzer-optimizer-design.md)
  (**FINAL, frozen @ `8c2a9b04`** — governs the Type 3 on disagreement).
- **optimizer-pd-role-ceiling (RESUME 2026-07-16 — clean-design discussion):** code + all 10 tests done (tip `0c33a3eb`); dev-guide edits made-but-UNCOMMITTED in the worktree. Active thread is Dean's clean-design effort in [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md): **(1)** answer the 2 Phase-2 framing questions (see that doc's § Resume), **(2)** lock the clean logical/data-flow, **(3)** Phase 3 — verify code vs. the clean model and resolve open issues 1–4 (notably the suspected anticipated-supply-in-denominator bug), **(4)** restructure the dev-guide into clean-design + implementation sections. Only after that: commit the dev-guide, act on the pending code-review trigger, propose the push. Do NOT commit/push until Dean directs. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).
- **analyzer-metric-interface (PR #1444 MERGED → issue [#1455](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1455)):** enhancement tracked (Phase 1 metric exposure → Phase 2 external PromQL wrapper → Phase 3 polish). **Implementation deprioritized** — do NOT start until higher-priority work clears and Dean scopes Phase 1. **Archive `analyzer-metric-proposal` branch/worktree ~2026-08-13** (`git boidem`), after confirming Evgeny has no further commits.
- **Issues to file (at Dean's direction — do not file without confirmation):** Q1+Q2 from
  `planning/open-items-roadmap.md`; TA forward-plan I-1..I-25 (see [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md)).
  Already filed 2026-07-29: I-5 half-2 → #1497, I-16 → #1495, epics #1492/#1493/#1494 + #1005, veto-liveness
  #1496, cross-repo doc #1498. Pre-existing `main`-side §4a-cleanup locations → [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md).
  EPP-metric 0.9 rename needs no new issue — #1202 owns it (verification posted 2026-07-27; migrate with an old-name `or` fallback).
- **TA3 post-merge:** triage 3 pre-existing smoke failures (`smoke_test.go:339,:542,:1724`); Step 2f E2E discussion.
- **Parallel track (NOT authorized):** WVA-vs-KEDA benchmark — see § Benchmark.
- **Governance follow-up — repeat scope-boundary incidents + candidate gates.** Full detail
  (incidents 07-14 reviewer-worktree / 07-26 unauthorized-subagent / 07-27 formula-fork / 07-29
  §4a-leaks, the reviewer-highlight default, the plan-authoring-grep note, and 8 candidate
  directions incl. the open "who edits CONVENTIONS.md" question) now lives in
  [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md). None actioned yet.

---

## Benchmark: WVA vs KEDA — NOT AUTHORIZED

> **STOP — do not begin implementation.** The plan needs Dean review + explicit go-ahead before any coding. A new coding session that sees this entry MUST NOT start writing code, manifests, Makefile changes, or Go test files based on this plan. Open a discussion first, summarise the plan back to Dean, take feedback, and wait for an explicit "go ahead and implement."
>
> When approved: this STOP block is removed and the status line in PR Status updated.

**Docs:**
- [`planning/benchmark-wva-vs-keda.md`](../planning/benchmark-wva-vs-keda.md) — Type 1 design / approach. Scenarios, structural argument, decisions. Start here.
- [`planning/benchmark-wva-vs-keda-plan.md`](../planning/benchmark-wva-vs-keda-plan.md) — Type 3 implementation reference. Configs, Go types, Ginkgo skeleton, OpenShift sizing, coder guide. Not yet reviewed/approved.

**Pokprod TA3 testing track (separate from WVA-vs-KEDA above):** [`planning/ta-pokprod-testing-plan.md`](../planning/ta-pokprod-testing-plan.md) (Status: DRAFT; Phases 1–4 gated on its own STOP block). **Phase 0 done locally 2026-07-29** (benchmark worktree): stale TA3 branch preserved as `benchmark-ta3-legacy` @ `892e1efa` (docs only — the two writeup docs; 2026-06-15 raw results discarded per Dean) + signed tag `archive/benchmark-ta3-legacy` → `892e1efa`; fresh `benchmark` @ `11d70a8a` (= upstream/main, has A #1478 + A′ #1479); untracked local `benchmark/reference-legacy/` holds 3 guidellm workload profiles + patched-guide sample + settings for re-application. **Awaiting Dean's pushes** (fork/origin only, never upstream): `git push origin archive/benchmark-ta3-legacy`, then `git push -u origin benchmark` (⚠️ rewrites `origin/benchmark` — `--force-with-lease`; the 2 harness commits survive via the archive tag + legacy branch). Status file: [`session/status/benchmark.md`](status/benchmark.md).

**Methodology pivot (Dean redirection, 2026-07-30).** Pivoted to a **controlled shared-cluster
setup** (our-NS-only `-p dhl-wva-209`; skip steps `02`/`08`; never full teardown; end-user path runs
standard PUBLIC llm-d-benchmark, our fork is a safety-net only; waits on Ofer's two-variant scenario
landing upstream). Planner Type-3 revision DONE (`de688be8`/`593abb4a`/`bcb0b468` on `plans`; §6
controlled-setup rewrite + §7.0 longer-term goals — supersedes memory
`project_benchmark_makefile_two_variant_todo`). Phase 2 harness `6505de62` (fork-only, NOT pushed);
Phase 3 EXECUTED (`dhl-wva-209` created); hazard analysis resolved (live steps `00,03✎,04,05,07✎,09`;
3 fork-patch presence-gates applied, uncommitted). Blocked-on-Dean items in § Blocked on; 4 coder
review points in the status file. Full detail: [`planning/ta-pokprod-testing-plan.md`](../planning/ta-pokprod-testing-plan.md)
+ [`session/status/benchmark.md`](status/benchmark.md) (state: `blocked`).

**TA-lead experiment — "does ThroughputAnalyzer trigger scale-up faster than saturation?" (setup
check → planner, 2026-08-03).** Dean's next benchmark: run combined **TA+SAT** and test whether a
*calibrated* TA raises RequiredCapacity while `k* < k_sat = 0.85` — leading saturation's reactive
KV-threshold trip. **Coder is HOLDING** (clean baseline on `dhl-wva-209`, no run in flight); the
setup check went to the **planner**, who owes: (a) a **two-phase workload** (Phase A sub-scale
calibration sweeping KV util `[0.15, 0.85]` so TA collects ≥10 OLS samples with `KSpread ≥ 0.30`
and flips `T2-default → OLS-Ready` *without* itself scaling — `wva_sat2_short` jumps straight to
saturating rates, unsuitable; Phase B trigger step), and (b) a **"faster" methodology** (Δt from a
fixed reference to HPA `desiredReplicas: 2`, A/B SAT-only vs TA+SAT on identical workload, repeats +
noise floor). **Open feasibility question the planner must answer before a cluster run:** does TA's
`Analyze()` actually raise RC ahead of the KV threshold, or does it also key off `k* ≥ k_sat = 0.85`
(`DefaultKSat = 0.85`, "mirrors" saturation) — if the latter, a lead is impossible by construction
and the experiment needs reframing. Depends on (but is a **separate thread** from) the sat_v2-disable
F1 gap in § Next steps — the earlier attempt to isolate TA via `saturation:{enabled:false}` was the
no-op that surfaced that bug; the TA-lead experiment runs TA+SAT combined, so it does **not** need
sat_v2 disabled. Setup-check detail in handoff `plan__ta-sat-scaleup-lead-setup.md`.

---

## Completed missions (archived)

Full blocks for the **TA3 (ThroughputAnalyzer)** mission, the **Multi-Analyzer** mission, and the
**Deferred fixes (TA2 / PR-3 follow-ups)** list now live in [`session/history.md`](history.md) →
*Mission* / *Deferred fixes* sections. Live forward work from those missions stays in § Next steps
and § Issues to Open below (TA3 smoke-failure triage; the TA forward plan; the deferred TA2 fixes).

---

## Issues to Open (post-merge)

Multi-analyzer — full detail in [`planning/multi-analyzer-design.md`](../planning/multi-analyzer-design.md) § Future direction:

- Per-analyzer status-return state (`AnalyzerStatus`: SuppressSC/SuppressRC/Fail; restores TA EPP-queue + GPS gating; subsumes F9) → **F3** — **FILED as [#1261](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1261)** (framed as analyzer interface extension: accept-for-SC/RC/all + sanity helper mechanism; motivated by TA3 #1250 review)
- ~~Remove `llm_d_ai_variant` from all PromQL groupbys~~ — **FILED as [#1263](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1263); CLOSED** — superseded by #1267 (label retained as fast path + shadow-pod resolution; owner-walk handles Deployment/LWS). See [`planning/PR1267-impact-and-decisions.md`](../planning/PR1267-impact-and-decisions.md).
- Distinguish unavailable metric from genuine zero in `ReplicaMetrics` (`*float64` nil semantics for 3 throughput fields + sanity update) — **FILED as [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264)** (prerequisite: #1250 Bug A fix; follow-up after #1250 merges)
- Per-analyzer observability metrics + decision-enrichment hook (generalize `enrichDecisionsWithKvTokenData`) → **F4**
- ~~Engine model-level RC/SC for disaggregated models~~ → **F5** CLOSED (resolved by #1246 `initRoleState`)
- ~~Replica-count accounting consistency (TA `len(variantMetrics)` vs sat_v2 `readyCount`)~~ → **F8** — **RESOLVED** by `34c9be9b` (`ReplicaCount = nKV`, mirrors sat_v2)
- Fold queueing-model into the V2 multi-analyzer engine (Option A; + 4 pre-existing QM oversights) → **F10** — **this is also the re-enable path for the QM optimize path DEFERRED by PR-1 #1516 C3** (`optimizeQueueingModel`/`runQueueingModelAnalysis`/`buildQMConfig` stay in-tree behind a blank reference; re-enabling = restoring the dispatch). No separate backlog item.
- Per-role RC/SC canonical end-to-end (drop optimizer synthesis; resolves F5) → **F12**
- Cost picker integer-rounding suboptimality → **F13**
- Engine SchedulerQueue wiring — ✅ landed with #1246 merge (2026-06-10, `09e1c386`).

Infra / misc (no design-doc home; file as separate issues):

- **TA forward plan** — 26 internal issues + 5 deferred features (correctness, observability, tests, architecture, docs): [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md).
  - **Deferred features (Group 0)** — code removed during #1250 dev cycle whose design intent is preserved: D-1 ITL knowledge store (historical A,B per variant, warm-up skip), D-2 GPS-mismatch SC gate, D-3 EPP-absent SC gate, D-4 FreshnessStatus staleness gate (dead end-to-end), D-5 `has*` throughput sentinels (nil-vs-zero for 3 fields). None are deprecated — all return in later PRs (D-2/D-3 via #1261, D-4 via I-6, D-5 via #1264, D-1 via I-18).
  - Key issues: collector key unification (I-1, P0 latent bug), gate observability (I-5, P0), dev guide fixes (I-21–23, P0), per-analyzer status return (I-17→#1261), effectiveEnabled (I-16→`planning/PR1266-fixup-effectiveEnabled.md`).
- ~~**ta-itl-demand-test-gaps**~~ — **SHIPPED as PR [#1511](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1511)** (open, reviewer ev-shindin; ITL-model validator + `computeLocalDemand` + folded-in `computeVariantSupply` pair). No longer a backlog item — tracked in PR Status. Plan: [`planning/ta-itl-demand-test-gaps-plan.md`](../planning/ta-itl-demand-test-gaps-plan.md).
- **`checkVariantGPSMismatch` test coverage (deferred, no owner)** — split out of #1511 (4 earlier skip guards to satisfy, no existing test block, diagnostic-only). Separate future test task; recorded in the `ta-itl-demand-test-gaps-plan.md` Commit-4 §. Create a branch when assigned.
- **EPP system-wide `k_sat` unification (NEW 2026-08-07, surfaced by PR-2 C10)** — PR-2 makes TA resolve `k_sat` from the saturation analyzer's `KvCacheThreshold` (0.80) instead of its own hard-coded `0.85`, but the *system-wide* value the EPP uses is still a third, unrelated copy. The existing `TODO: unify with the system-wide k_sat used by the EPP` moves onto `resolveKSat` as the single place to fix. File at Dean's direction.
- **Prometheus ITL-model gauges** — `wva_throughput_analyzer_itl_model_{a,b}` (labels namespace/model_id/variant/tier); see forward plan I-8.
- **EPP image version mismatch** — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0 (infra bug).
- **Gateway prompt bug** — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true` (infra bug).
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable (Makefile bug).
- ~~**ndots fix standalone PR**~~ — landed with #1250 merge (`efca1b4c`). No action needed.
- ~~**E2E throughput wiring test is a no-op under the opt-in gate**~~ — `b2f1d7ef` converted to fake-metrics/saturation-driven; coverage honesty comment added. Gap acknowledged; TA-isolated scale-up signal has no e2e coverage (by design — covered by unit tests). See forward plan I-14 (e2e robustness) and I-11 (test rot).
- **`runRegisteredAnalyzers` deletion** — dead-code in `engine_v2.go`; not removed in #1266. Standalone cleanup PR. Plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4.
- **Optimizer `max`-shadowing cleanup** — `analyzer_helpers.go`: `roleBottleneckReplicas` (~L132) and `roleAggRemaining` (~L151) declare local `max` shadowing the Go builtin; flagged by ev-shindin in #1246 review. Minor cleanup; file post-merge.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| planner | `planning/open-items-roadmap.md` | **SCORED** (2026-06-15) | All areas scored (multi-analyzer, TA, D52/EV52). Committed `c71db32d`. See roadmap for Q1/Q2 priority list and dep graph. **Both #1250 and #1266 now merged — file Q1+Q2 items as GitHub issues.** |
| planner | `session/handoffs/plan__ta-anchor-doc-taxonomy-findings.md` | **OPEN** (`.WIP`) | Five doc-taxonomy findings for Dean to accept / reject / defer — **not** resolved by the Type-3 refresh. Deliberately still open. **Not sync's to consume.** |
| planner | `session/handoffs/plan__ta-anchor-dataflow-map-pr1-delta.md` | **OPEN** | Optional §9 addition to `multi-analyzer-dataflow-map.md`, deferred by Dean; partly overtaken — the map's §9 findings now live in the Type 1's § findings, so any delta is about the map's own currency. **Not sync's to consume.** |
