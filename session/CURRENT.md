# Current Work

**Last updated:** 2026-08-15

> ⚠️ **Before editing this file:** re-read `session/CONVENTIONS.md` (Type-5 paragraph + per-task rule). CURRENT.md holds **operational state + short abstracts only** — design/per-PR detail live in `planning/`, landed history in git; never overwrite a sibling task's state. **Recent activity is a bounded rolling window:** a short head of active-WIP abstracts + a tail of 1-liners, each carrying a PR#/commit-SHA or doc ref. Compress an item to a pointer only once its substance is in git or a permanent doc — never just delete.

---

## Recent activity

**Active (full abstracts) — live WIP only:**

- **2026-08-17 — micro-rules migration: overnight 5-step mandate substantively complete on
  `plans-tooling`, pushed.** All 5 steps done: 11 role specs; full harvest of
  `CONVENTIONS.md`/`CODER-CONVENTIONS.md`/~78 memories/`governance-follow-ups.md` into
  `conventions/` (22 files, ~80 entries); new `coll.sh`/`coll-list.sh`/`coll-lint.sh`/
  `coverage-check.sh` tools; 11 role-collections + 8 step-collections + 2 pre-packaged prompts;
  coverage-check shows 62/62 and 42/54 covered, every remaining gap individually accounted for,
  none silent. One real process gap found and fixed: enrichment additions to existing entries
  weren't updating their `origin:` citations — 17 fixed by hand. **Explicitly NOT done, Dean's
  call:** the `role:`-destined harvest rows (coder/sync-scoped memories, separate pass); 5 small
  naming/placement decisions (candidate topics `conv:writing-style`/`conv:tooling-preferences`, a
  `chat-links.md` fold-in, two mechanism-vs-rule borderline cases); 3 proposed additions to
  `doc-and-session-model.md` (handed off, out of harvest coder's write scope). **The cutover —
  merging `plans-tooling` into `plans` — has NOT happened and must not happen without Dean's
  explicit review and go-ahead**; `plans/CLAUDE.md` untouched, nothing here attempted or proposed
  that merge.
  **2026-08-19 (overnight, auto mode) — checklist items 1/2/2a/3/5/9/10/25 closed; items 4/8
  deliberately deferred; item 5's automated part (11-18) BLOCKED on Dean.** First run under
  revised parallel-coder rules (isolated worktrees, merged back only after independent
  verification) — 3 temp worktrees created and removed, their branches kept per this project's
  archive-don't-delete convention. Real defects found and fixed before merging: 4 prefetch design
  bugs caught by hand testing; 3 bugs in a dispatched coder's `source-coverage-check.sh` found by
  an independent review agent (false-success on empty/unreadable files, a fenced-code-block
  false-positive hiding 19 real lines, a duplicated rule); `conv-lint.sh` rule 15 extended to
  resolve `../`-relative paths too. **⚠️ Genuinely open, needs Dean's decision:** the checklist's
  own pre-A gate says items 1-10 "must all finish before Item 5's automated part starts" — tonight
  named items 4/8 as deferrable but never said this waives the gate, so items 11-18 (the actual
  Item 5 work) are **NOT started**, pending his read. Recorded as an open blockquote directly in
  `plans-tooling/planning/micro-rules-checklist.md` § Pre-A gate (commit `b334e3dd`). No armed
  footguns — `plans-tooling` clean, 101/101 tests pass, `conv-lint`/`coll-lint` exit 0; 54 commits
  ahead of `origin/plans-tooling`, not pushed (no confirmation requested or given, per the
  standing rule). State:
  [`session/status/micro-rules-migration.md`](status/micro-rules-migration.md); owned doc:
  `plans-tooling/planning/micro-rules-migration-plan.md`.

- **2026-08-16 — single-instance guard mechanism (session_id/role-constant keyed, not pid) built
  and migrated into all five call sites, plus the `sync-main` family generalized over
  container/repo/branch; every found defect (Defect C, marker-poisoning, dead-watcher-reads-RUNNING,
  and others found along the way) fixed.** Full state:
  [`session/status/single-instance-guard.md`](status/single-instance-guard.md); design + as-built
  detail: [`planning/checkpoint-capture-spec.md`](../planning/checkpoint-capture-spec.md),
  [`planning/sync-watchers-spec.md`](../planning/sync-watchers-spec.md),
  [`atomic-step-protocol-design-addendum-10.md`](../planning/atomic-step-protocol-design-addendum-10.md),
  [`atomic-step-protocol-roadmap.md`](../planning/atomic-step-protocol-roadmap.md) (refreshed
  end-of-day 2026-08-16, reflects everything as landed).
- **2026-08-15 — state commands (park/sweep/consolidate) ported as skills; Type 1 design written.**
  Three skills for making sure nothing important is lost, at increasing depth — `/s-state-park`
  (flush live context; additive only; model-invocable), `/s-state-sweep` and `/s-state-consolidate`
  (both Dean-invoked only, read broadly, may restructure). The load-bearing rule is a **mandatory
  source report**: without a list of what was read, the command has only been *claimed*, not
  performed — memory and conversational context are never sources. Adapted to this workspace's
  ownership model: role-aware write scope (own docs directly, `sync__`/`plan__` handoffs for shared
  state; coders get the narrower worktree + two-shared-paths scope), and **no `mv` in any of the
  three** because renaming a handoff `.WIP`/`.DONE` is a session *accepting and finishing* work,
  which a state command never does. Two findings worth carrying: (a) subagent transcripts already
  persist at `~/.claude/projects/{project}/{sessionId}/subagents/agent-{agentId}.jsonl` and survive a
  parent restart, and subagents resume **by agent ID** — so the fragile thing is the *address*, not
  the state; park records IDs into durable state and additionally best-effort-nudges running agents,
  reporting the two separately so an unconfirmed nudge never reads as a completed flush; (b) exiting a
  worktree is **correctness, not tidiness** — CC migrates the session on enter/exit and only sessions
  in `plans` appear in the VSCode extension history, so a park ending inside a worktree is itself
  unfindable. Committed `cc2d5ab0`, **not pushed**. ⚠️ Design § 6.1's platform facts (transcript
  path, resume-by-agent-ID, `SendMessage` delivery, `SubagentStop` semantics) came from a spawned
  `claude-code-guide` subagent's reading of the Claude Code docs — read, not independently
  re-fetched page by page; the resume-by-agent-ID and transcript-path claims are the load-bearing
  ones if anyone wants them verified before relying on them. State:
  [`planning/state-commands-design.md`](../planning/state-commands-design.md) (§ 5 adaptations,
  § 6 subagents, § 7 worktree exit, § 8 grants, § 9 forward work).

- **2026-08-14/15 — checkpoint scripts: origin-pid lifecycle + atomic single-instance guards.
  Coded, tested, committed; review DEFERRED to a worktree by Dean's instruction.** Commit
  **`750f9c5d`** on `plans`, **local only, not pushed**. Three scripts reworked —
  `scripts/session-snapshot.sh` (Tier-1 capture), `scripts/tick-shared-scan.sh` (Tier-2 shared
  consolidation), `scripts/sync-main-watch.sh` (main fast-forward). All three now take
  `--origin-pid <pid>` — the Claude session that launched them, captured at launch because a
  detached child reparents to init and cannot re-derive it — checked with `kill -0` each pass; on
  origin death they run **one final unit of their own real work, then exit**. Lock files are gone,
  replaced by two guards answering two different questions: an atomic `mkdir` on a fixed
  per-origin-pid path (two instances starting the same instant, when nothing exists for `pgrep` to
  find) plus the `pgrep` check (a watcher already running from an earlier launch), with a 1-week
  mtime staleness reclaim as the backstop for a process killed mid-startup. No traps for the guard.
  Verified **behaviorally, not by inspection**: 5/5 exactly one survivor on simultaneous launch,
  planted stale guard reclaimed, planted fresh guard respected and not deleted, guard released while
  the loop runs, final pass evidenced in the log on origin death.
  **Three defects found en route, all one shape — a guard released before the thing it protects
  exists:** (1) the dead-man's-switch originally exited *before* the final pass, which for Tier-1/
  Tier-2 defeats their whole purpose — and the same bug had sat in `sync-main-watch.sh`'s
  `anchor_alive()` since 2026-08-12, uncaught; (2) `pgrep`-only dedup had no atomic step, so two
  simultaneous launches left **zero** survivors, 4/4; (3) `stat -f %m` is wrong on GNU coreutils
  (`-f` takes a format, so `%m` became a filename operand and `stat` printed a filesystem block while
  exiting 0 — the `|| echo 0` fallback was unreachable and prose reached `$(( ))`), replaced with
  `date -r`. **Root cause of the pattern: no Type 3 plan existed** — code came straight from
  conversation, so no review had anything to check against. New
  [`planning/atomic-step-protocol-design-addendum-7.md`](../planning/atomic-step-protocol-design-addendum-7.md)
  is that plan, written retroactively (84 lines), and carries the verification checklist.
  **⚠️ Review is INCOMPLETE and did not follow CONVENTIONS § Review pipeline.** Two ad-hoc
  `general-purpose` subagents acted as checkers — their findings were real and are fixed — but no
  **Type 6 doc** (`planning/*-review.md`, `Status: DRAFT`, review-agent role via `/s-design-review`)
  exists. Two questions left open rather than guessed: **who runs it** (this session wrote the code,
  so self-review is the wrong shape — recommend spawning) and **which scope form** (design-doc scope
  fits; there is no branch/PR). Per Dean: **stop coding in `plans`** — the scripts stay as-is here,
  and the review resumes in `plans-tooling` or a fresh/temp worktree, deliberately not mixed with
  `plans-tooling`'s in-flight work.
  **⚠️ Armed footguns, carry verbatim:** (1) **`scripts/tier1-session-start.sh` is committed but NOT
  wired and NOT functional** — it passes no `--origin-pid`, so it would fail the new required-arg
  validation; it also needs a `container-settings.json` SessionStart entry, which
  `guard-settings-edit.sh` blocked once and must **not** be self-approved. (2) **Four production
  loops still run the OLD interface** (`session-snapshot.sh` pids 16342 + 629315,
  `sync-main-watch.sh` 89026, `tick-shared-scan.sh` 620370) — they work, they just predate the
  commit; restarting them is a separate approved step, gated on (1). (3) **`tick-live-index.sh:111`
  still carries the `stat -f %m` bug** — same latent crash, left out-of-scope. (4)
  **`.claude/settings.json` holds another session's uncommitted permission additions** — untouched
  here; do not attribute or discard them.
  **2026-08-15/16 — pushed; guard mechanism further fixed and re-verified; two of the four
  production loops restarted; hook-wiring ownership handed off.** Pushed to `origin/plans`
  (`e59dd371`, clean fast-forward). Two further real bugs found and fixed in review, not just the
  three above: **a `pgrep`-only dedup left ZERO survivors on simultaneous launch** (both instances
  see each other and both stand down) — fixed by adding an atomic `mkdir` guard ahead of the `pgrep`
  check, released inline (no trap — the mtime-staleness check already covers a guard abandoned by a
  killed process, so a trap was redundant machinery); and **`--once` mode diverged between scripts**
  on whether it also skipped the dedup guards (`session-snapshot.sh` didn't, `tick-shared-scan.sh`
  did) — made consistent. Re-verified behaviorally after each fix, not by inspection alone. Manually
  started `tick-shared-scan.sh` (pid `3410333`) and `sync-main-watch.sh` (pid `3412453`) here under
  the new interface — both confirmed running via a real `/proc` scan (not `pgrep`, which self-matched
  the literal `--origin-pid <n>` text typed into the launching shell call — a testing artifact, not a
  script defect; worked around by launching through a separate wrapper script on disk).
  **`session-snapshot.sh`'s auto-start ownership transferred**, per Dean's instruction — the
  atomic-step-protocol-brainstorm planner now owns finishing `tier1-session-start.sh` (needs
  `--origin-pid "$PPID"` wired in, plus the still-unapproved `container-settings.json` hook entry);
  handoff `plan__tier1-session-start-ownership-transfer.md` sent. Manual start command for any
  session in the meantime: `nohup bash scripts/session-snapshot.sh --out
  session/digests/<topic>.raw.md --file <own transcript path> --origin-pid <own real claude pid>
  --interval 120 &` (the pid must be the actual long-lived `claude` process, found by matching
  `--resume=<session-id>` in its argv — not a shell wrapper pid, which dies and respawns per tool
  call). **`tick-live-index.sh:111`'s `stat -f %m` bug moved from a footnote here into a tracked
  backlog item** — see § Issues to Open. **Still open, unchanged:** the Type 6 review itself (who
  runs it, which scope form) — explicitly deferred to `plans-tooling` or a fresh worktree, not
  continued here per Dean's instruction. **Also landed this window, same scope:** a new
  [`planning/planning-map.md`](../planning/planning-map.md) (`Status: DRAFT`) indexing every
  `planning/` doc by type and topic cluster, approved by Dean as "good enough for now." Its own
  § Gaps names that it has no refresh mechanism yet — handed to the atomic-step-protocol-brainstorm
  planner as a non-urgent TODO (`plan__planning-map-refresh-tool-todo.md`).
  **State:** [`session/status/sync-session.md`](status/sync-session.md) (cold-resume detail).
- **2026-08-07/09 — Anchor-refactor mission. PR-1 MERGED; PR-2 = #1523 OPEN, green, awaiting external
  review.**
  **PR-1 `ta-anchor-refactor-v2` = [#1516](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1516)
  MERGED** 2026-08-07 17:48:05Z, squash **`57f3fe64`** on `main` (29 files, +2077/−166). Full mission
  detail — the Aug-5 redesign, both review rounds, the C1–C5 close-out, ev-shindin's pre-merge
  `a38d7b73` (Finding 12 fixed, plus three further real defects in the newly opt-in TA path), and the
  DEPRECATED/DEFERRED classes — is archived in [`session/history.md`](history.md) → *Activity log — 2026-08*.
  **PR-1 residuals still live:** (a) review docs `planning/ta-anchor-refactor-v2-code-review.md` +
  `ta-anchor-refactor-review.md` Part 3/Round 2 are **committed `fe372ce8`** (1237 insertions, incl.
  the definitive push-ready APPROVE section; the sole-copy hazard is **gone** — no worktree-reset
  warning needed), and remain **`Status: DRAFT` pending Dean's FINAL call**; (b) goldens **#1513 is a no-op** (its content rode
  #1516's squash; diff vs `main` is empty) needing only a close call — GitHub write, Dean's;
  (c) superseded `ta-anchor-refactor@34055d77` unpushed, for `git boidem` at leisure.
  **PR-2 = [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) — OPEN, PUSHED,
  FULLY GREEN. Nothing blocked, nothing outstanding to push.** Tip **`14a5d6cc`**, **28 commits** on
  `main@a6b39809`; local ≡ origin ≡ PR head. `MERGEABLE` / `REVIEW_REQUIRED` — no *external* review
  submitted yet; internal review is complete and clean (Findings **76/77/78**). CI all pass — `gate`,
  `DCO`, `signed-commits`, `lint-and-test`, `kustomize-build`, `check-code-changes`, `e2e-tests-full`,
  `e2e-tests-smoke`; all 28 commits DCO- **and** crypto-signed.
  **Every previously-open decision is closed:** `AD8` (b) placement → **in this PR**, landed as `C12`
  (`4e5bbf12`, pre-rebase `136a214a`), reviewed defect-free (Finding 77); `ceil`/`floor` → **retracted,
  never a fork** (`1cca5563`); the §4a commit-message reword → **executed** during the rebase; the plan
  freeze → done; the rebase onto `main` → reviewed clean (Finding 78) and independently re-verified for
  dropped hunks (none).
  **No planner is standing by — deliberate, not abandonment;** the thread is fully resumable from its plan
  doc alone. **Live forward work, all released, none blocking merge:** `B2` (a discriminating spec for
  `fairShareRolePick`'s per-role budget) is **UNCLAIMED** — recommended as its own small test-only PR after
  #1523 merges; it pins existing-correct-but-under-tested behavior rather than fixing a defect.
  **Dean's, none blocking merge:** (a) two PR-*body* claims run ahead of the code — "partial proactive
  from-zero admission" is **built-not-enabled** (C11 (D-a) deferred), and the body omits that regime (i),
  the freeze, survives (`C12` closes only the drain); (b) **PR-2's 0.9 inclusion — open by design, his call
  after merge**; (c) requesting an external review on #1523.
  **⚠️ Armed footguns, carry verbatim:** (1) #1523 shows a **stale `github-actions` comment "Unsigned
  commits detected!"** — posted 9 s after the PR opened against the pre-re-sign push; the bot never
  retracts and `signed-commits` **passes**. Do not read it as a live failure and do not re-sign.
  (2) **Do NOT record PR-2 as in-or-out of 0.9** — the tag-is-freeze-marker /
  `release-0.9`-branch-is-actual-content distinction was about **PR-1**. (3) Plan **§1.1.0's ledger SHAs
  are pre-rebase and no longer resolve**, kept deliberately as history. (4) **`AD8` (b)'s "third site" is
  not a gap** — it is reached via the same abstain predicate at `votesFromTotalDemand`; do not schedule it.
  **State:** [`session/status/planner-ta-anchor-pr2.md`](status/planner-ta-anchor-pr2.md) (**CLOSED** —
  carries the handoff inventory + footgun list) · Type 3
  [`ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md) § *Where the branch
  actually is* + § *Open items and next steps* (**claim from that owner table**) · review doc
  `planning/ta-anchor-dynamic-refresh-review.md` Findings 76/77/78 · Type 1
  [`combined-analyzer-optimizer-design.md`](../planning/combined-analyzer-optimizer-design.md) FINAL
  @ `8c2a9b04` + Addendum **Rev 7 @ `43f20c65`** (governs where they overlap).
- **2026-08-07 through 2026-08-17 — autoscaling-viz mission, tip now `a1a815a7`. Status file
  compressed 1060→147 lines; good-panels classification complete.** Runs in its own
  `autoscaling-viz` branch/worktree, no PR, not headed upstream. Everything since the last
  recorded tip (`cff4e4c0`) is committed, local-only, **not pushed** (origin sits at `4b263d73`):
  panel 4 KV%-heatmap repurpose, panel 4/3/6 followups (incl. a real infinite-loop bug), a latent
  SAT-NameError fix, warmup-anchor + estimated-data-fallback + panel polish round 2, panel 3 stale
  forward-fill, and a full batch refresh of all 35 real-run leaves (0 crashes, all stamps
  verified). **Good-panels classification complete** (commit `23c1bbb7`): 16/29 extractable runs
  are GOOD (trustworthy, per-request trace PASS at tip `a1a815a7` — `ls
  benchmark/runs/*/viz/good-panels.png` returns exactly those 16); 12 MISSING-unobtainable (no
  per-request signals on disk); 1 MISSING-obtainable-elsewhere (`dean-20260810-105211-685`, raw
  Envoy log 54 MB, handed to benchmark scope). **Status-file compression itself:**
  `session/status/autoscaling-viz.md` rewritten (commit `c6f22d67`) from a 1060-line narrative
  into a 147-line pointer table — every prior task's outcome now lives in its owning Type 3 plan
  doc's own `## Outcome` section (15 plan docs touched), not deleted without a confirmed permanent
  home first. Two real gaps found and fixed in the process: `autoscaling-viz-panel3-stale-forward-
  fill-plan.md`'s own gap-count table used a looser gap definition than the shipped mechanism's
  actual one (re-verified: zero fillable gaps on either named run under the real mechanism, now
  recorded in the plan doc); Item AA's outcome (never recorded — now says tried, kept, flagged as
  Dean's judgment call). **Open / next:** inventory update pending
  (`plan__viz-good-panels-inventory-update.md`, planner to fold into
  `planning/benchmark-runs-inventory.md`); benchmark scope to decide on the one
  obtainable-elsewhere run.
  **2026-08-17 — panel review, 7/8 items done (commit `3818cab4`).** Items 1–7 (title fix, p1a
  title overlap, p3 color strip, p4 header gap, pod sort tie-breaker, p5 L(t) alignment, p6
  silent-tail cue) implemented and verified. Item 8 (drain over-firing) investigated — no actual
  over-firing found on the named run; findings in `plan__panel-review-20260817-item8-findings.md`,
  **decision pending Dean**. Full re-render of all 16 GOOD runs deferred as its own follow-up
  pass. No armed footguns — working tree clean, nothing uncommitted anywhere in scope. Session
  idle, watching for next trigger. State:
  [`session/status/autoscaling-viz.md`](status/autoscaling-viz.md) — history table names the exact
  plan doc + § Outcome for every landed task; prior narrative preserved in `plans` git history
  before commit `c6f22d67` if ever needed.
- **2026-08-10 through 2026-08-17 — pokprod TA benchmark campaign. Coverage-matrix closed;
  "clean recapture" Stage A complete; per-request estimation in progress.** Running since
  2026-07-30. Coverage-matrix campaign (21 experiments, 6 workload shapes) closed `D-50`; results
  report relocated to
  [`benchmark/docs/benchmark-reports/ta-pokprod-campaign-report.md`](../../benchmark/docs/benchmark-reports/ta-pokprod-campaign-report.md)
  `D-53`. First-ever Type 2 roadmap created, closing a real structural gap the mission ran without
  for weeks: [`ta-pokprod-roadmap.md`](../planning/ta-pokprod-roadmap.md) — **start here**, it
  points into everything else. **Stage A of a "clean recapture" campaign (warmup + fixed
  log-capture wiring + exploratory instrumentation) is COMPLETE — 7/7 cells landed, clean, GPUs
  freed** (`D-65`–`D-69`); found and fixed a real harness OOM (workload silently needed 96Gi not
  the scenario's 32Gi default, plus a compounding trap where a fix to the embedded
  `llm-d-benchmark` clone got silently overwritten by `make benchmark-run`'s own copy step every
  invocation). **Stage B (full campaign re-run) not yet launched.** Per-request TTFT/output-size
  estimation for viz panels 1a/1b built and generalized to 18/21 run-leaves (no true per-request
  source exists under the standing OOM-risk collection-disable policy, so the design estimates
  from Envoy-log arrival/duration anchored to per-stage vLLM histogram distributions); a candidate
  to replace estimation with true measurement (vLLM's `--enable-per-request-metrics` flag) was
  investigated and found **absent** on the pinned v0.20.2 image — closed for now. **Full priority
  triage done 2026-08-16** (`D-71`) — Dean set explicit handling per open item, all tracked in
  [`ta-pokprod-open-scenarios.md`](../planning/ta-pokprod-open-scenarios.md) § *Priority triage*,
  now **items 1–14**; genuinely open, in his priority order: gateway-harvest wiring fix (needs
  discussion), p4 4-pod combined-log extraction gap (non-urgent), truncated-run detection (real
  open gap), controller-restart hold-policy question (`D-40`/`D-46`), doc-coverage cleanup for 19
  scratch scripts (parked), pokprod runbook fold-vs-stub call (may be ready to revisit now Stage A
  exists), **Stage B tracked as item 12** (previously cited only in park reports, no table row —
  closed as a tracking gap), **83 uncommitted viz-refresh entries on `benchmark`** handed over
  non-blocking from autoscaling-viz, planner's to commit (item 13, `D-75`), **`reset_run.py`'s
  existence-check defect, LIVE and UNFIXED** — `hack/benchmark/reset_run.py:270-272` `rm -rf`s a
  PVC directory on a name match with no size/count check (item 14, `D-74`). **Deliberately
  deferred by Dean, not forgotten:** the dwell-forecast Type-1 design (shared queue-load-forecast
  mechanism), the bucket-keyed `prc` collapse bug, controlled-run/timestamped-replay capability.
  **A process finding, closed:** `session/handoffs/` used bare `mv` not `git mv` for state
  transitions, so 439 tracked files accumulated as delete+add pairs rather than real git history —
  handed to the handoff-protocol design owner with Dean's ruling attached (pointers only, no
  retroactive git-history change); consumed, closed (`D-72`).
  **⚠️ Armed footguns, carry verbatim:** (1) **the ScaledObject is left PAUSED at 0** on
  `dhl-wva-209` — KEDA holds it indefinitely, and a future run launched without un-pausing first
  traces flat at 0 replicas and reads as a legitimate no-scaling result; (2) **`reset_run.py` can
  permanently delete incomplete PVC data** (item 14 above) — mitigation is procedural only, run
  `session-notes/scratch/verify_pvc_vs_host.py` first; it once found all four host copies
  incomplete, where `--apply` would have made the loss permanent; (3) **`benchmark` is 34 commits
  ahead of `origin/benchmark`, 0 behind — all unpushed**, durable locally but origin a month
  stale, no push proposed or approved (`D-75`). State:
  [`ta-pokprod-roadmap.md`](../planning/ta-pokprod-roadmap.md) (start here) +
  [`ta-pokprod-open-scenarios.md`](../planning/ta-pokprod-open-scenarios.md) § *Priority triage* +
  checklist + [`ta-pokprod-history.md`](../planning/ta-pokprod-history.md) (`D-1`…`D-77`,
  append-only, grep-lookup) + [`session/status/planner-pokprod-benchmark.md`](status/planner-pokprod-benchmark.md)
  (new planner state file) + [`session/status/benchmark.md`](status/benchmark.md) (coder state,
  compressed 5411→~130 lines).
- **2026-08-11 — dwell limit cycle root-caused: replica-readiness lag, not a bookkeeping bug.**
  Dedicated deep-dive session traced `m-satta-dwell`/`m-sat-dwell` controller logs against the actual
  saturation_v2/optimizer code, not log inference. The ramp-to-cap excursions are saturation's
  `P1-obs` (`k2SrcObserved`) priority reading a real, large `waitingQueueDemand` snapshot —
  `util>1` is by design, not a bug; reproduces worse SAT-only than SAT+TA, and TA-only doesn't drive
  it because saturation isn't voting there. Dean's abstract accounting model (ready supply is the
  only "real" supply; the allocator handles the RC delta; the actuator nets out in-flight orders) was
  traced end-to-end and **holds structurally** — no double-counting. The lag decomposes into two
  hops against ground-truth Deployment status: **ordered→created is fast** (~1 tick, matches the
  KEDA poll interval, not the bottleneck); **created→ready is slow and worsens with concurrent boot
  count** — in the first excursion, ready peaked at 9 and never reached the ordered/created peak of
  10, so the controller began retreating from its own peak order before the last requested replica
  ever became ready. This is the dominant mechanism, and it is **physical** (model load + GPU
  scheduling contention under concurrent boots), **not a WVA control-loop defect**. Dean's synthesis:
  the pending-vs-actual lag is real and can't be circumvented; double-booking is correctly avoided
  today; the real gap is a missing forecast — forward-work item handed to a working planner via
  `plan__dwell-limit-cycle-forecast-todo.md` (not restated here; that is a Type-1 task, not a
  CURRENT-update). State/resume: [`session/status/dwell-deep-dive.md`](status/dwell-deep-dive.md) —
  full code trace with file:line citations, the two-hop lag table, and the synthesis; do not delete,
  it backs the Type-1 TODO.
- **2026-08-03 — sat_v2 F1 gap (cannot disable saturation via config) — STILL OPEN, verified but not
  yet closed.** New evidence (2026-08-16) that PR-1's `satVotes` gate may have fixed this as a side
  effect is now independently verified against two tests at PR-2's own tip — detail and citations in
  [`ta-anchor-dynamic-refresh-plan.md`](../planning/ta-anchor-dynamic-refresh-plan.md) §7. Routed to
  the PR-2 reviewer for a numbered finding; **stays open until that finding lands and PR-2 merges.**
- **2026-07-15 — optimizer-pd-role-ceiling: code + all 10 tests landed (`0c33a3eb`), gates green.
  Re-validated against the anchor refactor 2026-08-16 — updated 2026-08-17.** *WIP — no session
  running; resumable from its plan.* ⚠️ Dev-guide edits the planner made directly are still
  **UNCOMMITTED** in the worktree (`M multi-analyzer-pipeline.md`). The mission's original re-
  validation ask (`plan__optimizer-pd-role-ceiling-revalidate-against-pr2.md`, sent 2026-08-09) has
  been answered: the suspected denominator bug (Q2) **does not exist in either `main` or PR-2's
  code** — both independently rewrote `allocateForModelPaired`'s `roleAggRemaining` since this
  mission's tip, and the specific numerator the bug report described is gone, not relocated. 4 of
  the 10 tests are fixable but redundant with `main`'s own coverage; 6 test a formula neither
  `main` nor PR-2 computes anymore. Rebase cost: small in file count but lands on the one function
  both `main` and PR-2 rewrote — expect a real conflict, not a clean reapply; this branch also
  hasn't re-verified `make lint` under the go 1.26/golangci-lint 2.10 bump. **No rebase attempted or
  proposed** — documentation only, nothing pushed. **One fresh, genuinely open design question,
  Dean's to judge:** PR-2's new find-the-winner/read-its-demand-directly shape for
  `roleAggRemaining` is a different design than `optimizer-coordination-design.md`'s
  achieved=current+anticipated+committed clean model — nobody has checked whether PR-2's shape is
  equivalent, better, or a third approach. Full detail + file:line citations:
  `planning/optimizer-pd-role-ceiling-plan.md` § "Re-validation against the anchor refactor
  (2026-08-16)". State: `planning/optimizer-pd-role-ceiling-plan.md` +
  [`optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md) § Resume.
**Recently landed (1-liners; fuller entries in [`session/history.md`](history.md) → *Activity log*):**

- 2026-07-30 — `ta-testing` refreshed → `6bfb73e1`; signed tag `ta-0.9-test-20260730` + quay image `:ta-0.9` (registry digest `sha256:80dec0e9728f…`) both pushed (executes the §4.1 refresh trigger).
- 2026-07-31 — CURRENT.md / history.md restructuring committed on `plans` (landed history extracted to the archive).
- 2026-08-07 — `ta-itl-demand-test-gaps` **PR #1511 MERGED** 17:40:56Z (merge `8b3663ed` on `main`; test-only, 5 commits; landed via the background `main`-sync watcher). Residual: `checkVariantGPSMismatch` coverage still deferred (see § Issues to Open).

**Older / historical:** the compressed activity tail (TA 0.9 era back through 2026-05) lives in [`session/history.md`](history.md) → *Activity log* sections — fetch one section at a time per that file's Reading Protocol, do not inline here. Most recent landmark: **TA 0.9 fully landed (all six PRs #1478/#1479/#1480/#1481/#1502/#1503) 2026-07-30, `main` tip `6bfb73e1`.**

---

## PR Status — open / active only

Landed & closed rows (TA 0.9 stack, TA3 & earlier missions, upstream reviews & proposals) are
archived in [`session/history.md`](history.md) → *PR Status* sections. Only in-flight / actionable
rows stay here.

| Branch                | PR    | Status                                                            | Tip       |
|-----------------------|-------|-------------------------------------------------------------------|-----------|
| wva-analyzer-lifecycle | — | **PLAN — PARTIALLY REJECTED / re-scoping.** Config-driven analyzer activation + ManagedAnalyzer lifecycle. Splits into **Half A** (config-driven lifecycle + live-set refactor — Commits 1/3/4/5; ~1–2 days; `effectiveEnabled`/Commit 3g already on `main`; main risk = `NewEngine` ripple vs in-flight #1501) and **Half B** (genuinely disabling saturation — Commit 2c **REJECTED by Dean 2026-07-31**: "zero-signal" is a risky hack). ⚠️ **This row's "needs F1 pre-analysis extraction, unscoped" claim has new counter-evidence, found 2026-08-16 — see § Recent activity's sat_v2 entry. NOT confirmed resolved** — a `satVotes` gate exists on `main` via PR-1 #1516 that looks like it does what F1 asked for, but this needs verification in PR-2's own review before Half B's carve decision changes. Not re-scoped here. Warnings added to plan (`663a9624`). Supersedes `PR1266-fixup-effectiveEnabled.md`. Plan: [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). | — |
| ta-anchor-goldens | [#1513](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1513) | **OPEN but now a NO-OP — needs only a close call (Dean's; GitHub write).** Characterization "golden" gate (test-only, +409/−0, 1 file: `internal/engines/pipeline/optimizer_characterization_test.go`) freezing the saturation-only optimizer decision SET keyed by VariantName; was the land-first ship gate for the anchor refactor. **Its content is already in `main`:** PR-1 #1516 was rebased onto this branch's tip before opening, and #1516's **squash** merge (`57f3fe64`, 2026-08-07 17:48:05Z) therefore landed the file — `git diff 57f3fe64 a2f49ccf -- <that file>` is **empty**, so the PR has nothing left to contribute and its purpose was served. No code action; the coder must still **NOT** rewrite the goldens commits. Head `ta-anchor-goldens@a2f49ccf`, base `upstream/main@9906dac5`, reviewer ev-shindin, `origin/ta-anchor-goldens` pushed. Internal review FINAL (Finding 1 fixed; Finding 2 = `withSatEntry`-stability note, carried into PR-1 and landed there). Plan: [`planning/ta-anchor-goldens-plan.md`](../planning/ta-anchor-goldens-plan.md); review [`planning/ta-anchor-goldens-review.md`](../planning/ta-anchor-goldens-review.md). | `a2f49ccf` |
| ta-anchor-dynamic-refresh | [#1523](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1523) | **OPEN, pushed, CI all-green.** Tip `14a5d6cc`, 28 commits on `main@a6b39809`; local ≡ origin ≡ PR head. `MERGEABLE` / `REVIEW_REQUIRED` — internal review clean (Findings 76/77/78), **no external review yet**. All decisions closed (`AD8` (b) → `C12`; `ceil`/`floor` retracted; §4a reword executed; rebase clean). Open, none blocking merge: `B2` (**UNCLAIMED**), and Dean's PR-body accuracy + 0.9 call + review request. ⚠️ The **"Unsigned commits detected!"** bot comment is stale — `signed-commits` passes. Detail: [`session/status/planner-ta-anchor-pr2.md`](status/planner-ta-anchor-pr2.md) (CLOSED). | `14a5d6cc` |
| optimizer-pd-role-ceiling | — | **IMPLEMENTED; dev-guide edits UNCOMMITTED; re-validated against the anchor refactor 2026-08-16.** 6 commits (`a694012a`…`0c33a3eb`), all 10 tests landed, gates green. Planner made dev-guide edits directly (`M multi-analyzer-pipeline.md`, **not committed**). ⚠️ **The "suspected anticipated-supply-in-denominator bug" is RETIRED, not open** — verified by direct code diff that the numerator it described doesn't exist in `main` or PR-2, since both independently rewrote `allocateForModelPaired`'s `roleAggRemaining`. **New, genuinely open question:** whether PR-2's replacement shape is equivalent to, better than, or a third approach vs. [`optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md)'s clean model — Dean's to judge. Detail: `planning/optimizer-pd-role-ceiling-plan.md` § "Re-validation against the anchor refactor (2026-08-16)". Not pushed. Plan: [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md). | `0c33a3eb` (+uncommitted) |
| (upstream) rate-anchored k2 | #1501 | **Reviewed 2026-07-30 — COMMENTED posted** (deanlorenz, 15:54:47Z) — rate-anchored `k2` estimator for saturation-v2 (fixes #1500 shed-to-one on prefill-heavy traffic). 2 non-blocking asks: (1) gate `RegisterRateCapacityQueries` on `EnableRateAnchoredK2` (unconditional registration adds per-cycle Prometheus load in the default TA-off config — load-only, no correctness impact); (2) rebase onto current `main` (#1486 touches the same `NewEngine`). Estimator/tests sound, no blockers. Incoming PR — no worktree. Review FINAL: [`planning/PR1501-review.md`](../planning/PR1501-review.md). | (incoming) |

---

## Blocked on

- **Pokprod TA benchmark — first live controlled standup** is blocked on **Dean's explicit go-ahead**
  (Phase-4 Step 0). All prep is done (dry-run, hazard analysis, fork patches, Phase-3 namespace setup);
  also awaiting Dean's OK on 3 fork-only pushes (`6505de62`, the 3 presence-gate patches) and the
  upstream-patch-proposal decision. See § Benchmark + `session/status/benchmark.md`.
- **The staged pokprod dwell run** is blocked on, in order: Dean's §7.6 (a)/(b) answer (or an
  explicit deferral), the coder's four preconditions (§7.6.1), and finally Dean's run approval.
  **Corrected 2026-08-16:** this used to also list "Dean applying the gateway access-log follower
  (T9)" as a blocker — T9 has been **DONE since 2026-08-12**, wired automatically into
  `benchmark-run` (see § Recent activity's pokprod entry) and no longer needs Dean's hand; this
  line was stale against CURRENT.md's own already-recorded fact and is corrected, not new
  information.

## Next steps

- **State commands — 3 forward-work items from the 2026-08-15 port, none claimed yet.**
  (1) **`SubagentStop` hook — unscoped, Dean's.** The real flush-on-termination guarantee (design
  § 9.1): fires when a subagent finishes, receives `transcript_path` + `last_assistant_message`,
  and `exit 2` **blocks** the stop — beats "more park" since it fires whether or not anyone
  remembers to run it, and doesn't depend on `SendMessage` delivery. Touches `settings.json`, needs
  its own approval. (2) **`s-note` has two real defects** (design § 9.2), neither urgent: its
  handoff body still uses the pre-redesign `to: plan-agent`/`body:` format instead of the current
  `from:`/`to:`/`session:` convention; its grants include the exact `Bash(git -C plans *)` wildcard
  (incl. `git rm`) this design rules out for the state commands. (3) **Open design question, not
  decided:** should park ever fire fully automatically via a `PreCompact` hook — the one moment the
  loss channel is known to be about to open? Deliberately not designed yet; auto-firing a
  write-capable skill needs its own thinking. Detail:
  [`planning/state-commands-design.md`](../planning/state-commands-design.md) § 9.
- **TA 0.9 — LANDED (all six PRs MERGED 2026-07-30, `main` tip `6bfb73e1`; test-branch + `:ta-0.9`
  image refresh EXECUTED).** Detail in [`session/history.md`](history.md). **Live follow-ups, all
  Dean's:** (1) epics #1492/#1493/#1494 + adopted #1005 — update or close now every PR is merged;
  (2) PR #1501 ask-#1 watch (see its PR Status row); (3) governance retrospective open Q →
  [`planning/governance-follow-ups.md`](../planning/governance-follow-ups.md); (4) cleanup — old tag
  `ta-0.9-test-20260728`, stale `origin/ta-testing`@`db530eed`, local `ta-model-level-demand`
  worktree (non-urgent). The 3 optional test gaps on F are done (#1511); only the deferred
  `checkVariantGPSMismatch` coverage remains, in § Issues to Open.
- **TA 0.9 release notes / Highlights — ⏰ CODE FREEZE REACHED (2026-08-07). This is the freeze, NOT
  the final cut — critical fixes can still be pushed (Dean, 2026-08-07).** Verified state: tag
  **`v0.9.0` exists on upstream** (lightweight, → commit **`aadaa596`** = #1509 "fix(crd): restart
  when KEDA or LWS CRDs are installed after startup"), and asm582's release-prep
  **PR [#1522](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1522)
  MERGED** 18:07:18Z (`d5d58640`, pins `config/base/manager/kustomization.yaml`
  `newTag: main → v0.9.0`) — but **no GitHub Release is published yet** (latest is still v0.8.0), and
  there is **no `release-0.9` branch** (release-0.6/0.7/0.8 exist). **A lightweight tag can be
  re-pointed, and v0.8.0 ran rc2→rc5 before its final tag** — so neither the tag point nor the 0.9.0
  content set is settled. What the freeze does settle is the **"held until code freeze" trigger for
  the hand-written `## Highlights` block: that work is now unblocked.** Mechanism + drafts in
  [`planning/ta-0.9-release-notes.md`](../planning/ta-0.9-release-notes.md): the ` ```release-note ``` `
  PR block is NOT auto-harvested (no `.github/release.yml`); GitHub auto-notes derive from PR
  *titles* in `v0.8.0..v0.9.0`; Highlights is the only editorial lever. Do NOT create an in-repo
  `docs/CHANGELOG-v0.9.0.md`. Slack epics + Highlights notes already POSTED by Dean 2026-07-29.
  Design-docs PR (item 5) still DEFERRED post-code-freeze.
  **⚠️ Open question for Highlights, NOT a settled exclusion — three commits sit on `main` *after* the
  current tag point:** `8b3663ed` (#1511, test-only), **`57f3fe64` (#1516, the anchor refactor PR-1)**,
  and `d5d58640` (#1522's own prep commit). If the tag stays at `aadaa596` they are 0.10.0 material; if
  it is re-pointed (or an rc sequence runs, as in 0.8.0) they are in 0.9.0. **Do not describe #1516 as
  in-or-out of 0.9.0 until the final tag point is known** — check `git ls-remote --tags upstream` at
  writing time rather than trusting this line. Corollary of the same ordering: the tagged tree at
  `aadaa596` does **not** contain #1522's own `v0.9.0` image pin, which is itself a reason the tag is
  likely still to move. Raising any of this upstream is Dean's call; no GitHub write made.
- **Toolchain moved on `main` (2026-08-07, post-freeze) — affects every branch that rebases.**
  PR [#1512](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1512) (`a6b39809`, Wen Zhou)
  bumps **go.mod `go 1.25.0 → 1.26.0`** and **`GOLANGCI_LINT_VERSION v2.8.0 → v2.10.0`** (Makefile + the
  `ci-pr-checks` / `ci-e2e-openshift` lint action + Dockerfile + CONTRIBUTING + `docs/developer-guide/development.md`
  + `.claude/agents/go-reuse-checker.md`; 8 files, +9/−9). Two practical consequences: (1) **a green
  `make lint` from before this commit does not carry forward** — 2.8→2.10 is two minor releases of linter
  changes, so any branch whose gates were verified under 2.8.0 (now only `optimizer-pd-role-ceiling` @ `0c33a3eb` — **PR-2 is clear: #1523's
  `lint-and-test` passes under 2.10.0**) must re-run `make lint` after rebasing, and
  new findings there are the bump's, not a regression; (2) **no stale-binary hazard** — the Makefile rule is
  version-keyed (`bin/golangci-lint-$(GOLANGCI_LINT_VERSION)` + `ln -sf`), so `make lint` fetches 2.10.0 and
  re-points the symlink on its own. Local `go` is **already 1.26.0**, so there is no toolchain gap to close.
  Landing after the v0.9.0 tag point is consistent with the freeze still accepting fixes.
- **Pokprod benchmark tooling — one Dean-owned item left (§7.1 of `ta-pokprod-execution-plan.md`,
  the doc this bullet cited is now SUPERSEDED and split into four — see the pokprod entry in
  § Recent activity).** **T9 is DONE** — wired into `benchmark-run` automatically, no longer needs
  Dean's hand. **T10**: file upstream llm-d-benchmark issues for the two guards-only-fork
  violators (later, after §2b's migration isolates them) — still his.
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
- **sat_v2 cannot be disabled via config (F1 gap) — STILL OPEN, new evidence 2026-08-16, needs
  verification, not resolved.** The claim below predates PR-1 #1516's `satVotes` gate, confirmed
  present on `main` by reading code directly (see § Recent activity for full detail). This is a
  finding, not a closed item — stays open until verified in PR-2's own review and until PR-2
  merges. Do not treat the "do NOT start until Dean scopes it" instruction as lifted based on this
  alone.
- **wva-analyzer-lifecycle (PLAN — PARTIALLY REJECTED / re-scoping):** ManagedAnalyzer lifecycle
  (Activate/Deactivate/Reactivate), config-driven registration, live-set refactor, effectiveEnabled fix,
  remove startup gate. **Split**: Half A (lifecycle/live-set — Commits 1/3/4/5, low-risk, ~1–2 days; note
  Commit 3g's effectiveEnabled fix already landed on `main`) vs Half B (disabling saturation — Commit 2c
  REJECTED, needs the F1 fix above). Awaiting Dean's carve/scope/hold decision (see PR Status row). Plan:
  [`planning/wva-analyzer-lifecycle-plan.md`](../planning/wva-analyzer-lifecycle-plan.md). Supersedes the
  `PR1266-fixup-effectiveEnabled.md` stopgap.
- **anchor-refactor mission — forward work only.** State and detail live in § Recent activity and
  the Type 3's owner table; not restated here. **Dean's, none blocking merge:** (a) request an
  **external review on #1523** (`REVIEW_REQUIRED`); (b) two PR-*body* claims run ahead of the code —
  "partial proactive from-zero admission" is built-not-enabled, and the body omits that regime (i), the
  freeze, survives; (c) **PR-2's 0.9 inclusion — open by design, decide after merge**; (d) close goldens
  **#1513** (no-op — GitHub write); (e) `git boidem` the superseded `ta-anchor-refactor@34055d77`
  (unpushed); (f) file, or decline, the two GitHub issues — QM multi-analyzer-contract work, and the
  sat-v2 zero-replica `Cost=0` bug (`AD7`/`N5`); (g) mark the PR-1 review docs **FINAL** — the
  reviewer's commit half is **DONE** (`fe372ce8`), both remain `Status: DRAFT` and only Dean's FINAL
  call is left. **Unclaimed, for a new planner:** `B2` (discriminating
  `fairShareRolePick` spec) as its own small test-only PR after #1523 merges; and
  `plan__ta-anchor-dataflow-map-pr1-delta.md`, still open and deferred by Dean — **not sync's to consume**.
  (The `optimizer-pd-role-ceiling` re-validation ask this used to list is **answered** — see § Recent
  activity's optimizer-pd-role-ceiling entry, 2026-08-16.)
- **optimizer-pd-role-ceiling (RESUME — clean-design discussion, updated 2026-08-17 against the
  2026-08-16 re-validation):** code + all 10 tests done (tip `0c33a3eb`); dev-guide edits
  made-but-UNCOMMITTED in the worktree. **The suspected anticipated-supply-in-denominator bug is
  RETIRED, not open** — see § Recent activity's entry above for detail. Active thread is Dean's
  clean-design effort in [`planning/optimizer-coordination-design.md`](../planning/optimizer-coordination-design.md):
  **(1)** answer the 2 Phase-2 framing questions (see that doc's § Resume), **(2)** lock the clean
  logical/data-flow, **(3)** Phase 3 — verify code vs. the clean model, now against PR-2's actual
  `roleAggRemaining` shape rather than the retired bug report, **(4)** restructure the dev-guide
  into clean-design + implementation sections, **(5)** NEW — judge whether PR-2's
  find-the-winner/read-its-demand-directly shape is equivalent to, better than, or a genuinely
  different approach from the clean model. Only after that: commit the dev-guide, act on the
  pending code-review trigger, propose the push. Do NOT commit/push until Dean directs. Plan:
  [`planning/optimizer-pd-role-ceiling-plan.md`](../planning/optimizer-pd-role-ceiling-plan.md).
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

**Pokprod TA3 testing track (separate from WVA-vs-KEDA above):** landed history, historical
`ta-pokprod-testing-plan.md` (now **SUPERSEDED**, split 2026-08-12 into
[`ta-pokprod-architecture-design.md`](../planning/ta-pokprod-architecture-design.md) /
[`ta-pokprod-execution-plan.md`](../planning/ta-pokprod-execution-plan.md) /
[`ta-pokprod-open-scenarios.md`](../planning/ta-pokprod-open-scenarios.md) /
[`ta-pokprod-history.md`](../planning/ta-pokprod-history.md) — see the pokprod entry in
§ Recent activity for current state; the STOP block this used to reference was lifted long ago,
the mission has been running since 2026-07-30). **Phase 0 done locally 2026-07-29** (benchmark
worktree): stale TA3 branch preserved as `benchmark-ta3-legacy` @ `892e1efa` (docs only — the two
writeup docs; 2026-06-15 raw results discarded per Dean) + signed tag `archive/benchmark-ta3-legacy`
→ `892e1efa`; fresh `benchmark` @ `11d70a8a` (= upstream/main, has A #1478 + A′ #1479); untracked
local `benchmark/reference-legacy/` holds 3 guidellm workload profiles + patched-guide sample +
settings for re-application. **Awaiting Dean's pushes** (fork/origin only, never upstream):
`git push origin archive/benchmark-ta3-legacy`, then `git push -u origin benchmark` (⚠️ rewrites
`origin/benchmark` — `--force-with-lease`; the 2 harness commits survive via the archive tag +
legacy branch). Status file: [`session/status/benchmark.md`](status/benchmark.md).

**Methodology pivot (Dean redirection, 2026-07-30).** Pivoted to a **controlled shared-cluster
setup** (our-NS-only `-p dhl-wva-209`; skip steps `02`/`08`; never full teardown; end-user path runs
standard PUBLIC llm-d-benchmark, our fork is a safety-net only; waits on Ofer's two-variant scenario
landing upstream). Planner Type-3 revision DONE (`de688be8`/`593abb4a`/`bcb0b468` on `plans`; §6
controlled-setup rewrite + §7.0 longer-term goals — supersedes memory
`project_benchmark_makefile_two_variant_todo`). Phase 2 harness `6505de62` (fork-only, NOT pushed);
Phase 3 EXECUTED (`dhl-wva-209` created); hazard analysis resolved (live steps `00,03✎,04,05,07✎,09`;
3 fork-patch presence-gates applied, uncommitted). Blocked-on-Dean items in § Blocked on; 4 coder
review points in the status file. Full detail now in
[`ta-pokprod-execution-plan.md`](../planning/ta-pokprod-execution-plan.md) (settled) and
[`ta-pokprod-open-scenarios.md`](../planning/ta-pokprod-open-scenarios.md) (live)
+ [`session/status/benchmark.md`](status/benchmark.md) (state: `blocked`).
**The tooling track** (now `ta-pokprod-execution-plan.md` §7.1, T1–T12 with owners — only T10 is
Dean's now, T9 landed 2026-08-12) and the dwell-run cold-resume block (now
`ta-pokprod-open-scenarios.md` §5) moved with the split; the methodology-pivot text
above stays accurate.

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
- Distinguish unavailable metric from genuine zero in `ReplicaMetrics` (`*float64` nil semantics for 3 throughput fields + sanity update) — **FILED as [#1264](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1264)** (prerequisite: #1250 Bug A fix; follow-up after #1250 merges)
- Per-analyzer observability metrics + decision-enrichment hook (generalize `enrichDecisionsWithKvTokenData`) → **F4**
- Fold queueing-model into the V2 multi-analyzer engine (Option A; + 4 pre-existing QM oversights) → **F10** — **this is also the re-enable path for the QM optimize path DEFERRED by PR-1 #1516 C3** (`optimizeQueueingModel`/`runQueueingModelAnalysis`/`buildQMConfig` stay in-tree behind a blank reference; re-enabling = restoring the dispatch). No separate backlog item.
- Per-role RC/SC canonical end-to-end (drop optimizer synthesis; resolves F5) → **F12**
- Cost picker integer-rounding suboptimality → **F13**
- Engine SchedulerQueue wiring — ✅ landed with #1246 merge (2026-06-10, `09e1c386`).

Infra / misc (no design-doc home; file as separate issues):

- **`scripts/tick-live-index.sh:111` — `stat -f %m` is wrong on GNU coreutils** (internal tooling, not
  a WVA issue — no GitHub issue needed, just a fix when that script is next touched). `-f` takes a
  *format*, so `%m` is parsed as a filename operand: `stat` prints a filesystem block and **exits 0**,
  which makes the `|| echo 0` fallback unreachable and can feed prose into `$(( ))`. Same defect was
  fixed in the three checkpoint scripts via `date -r` (`750f9c5d`); this fourth site was left
  out-of-scope deliberately. Latent (fallback path only), not live.

- **TA forward plan** — 26 internal issues + 5 deferred features (correctness, observability, tests, architecture, docs): [`planning/TA-forward-plan.md`](../planning/TA-forward-plan.md).
  - **Deferred features (Group 0)** — code removed during #1250 dev cycle whose design intent is preserved: D-1 ITL knowledge store (historical A,B per variant, warm-up skip), D-2 GPS-mismatch SC gate, D-3 EPP-absent SC gate, D-4 FreshnessStatus staleness gate (dead end-to-end), D-5 `has*` throughput sentinels (nil-vs-zero for 3 fields). None are deprecated — all return in later PRs (D-2/D-3 via #1261, D-4 via I-6, D-5 via #1264, D-1 via I-18).
  - Key issues: collector key unification (I-1, P0 latent bug), gate observability (I-5, P0), dev guide fixes (I-21–23, P0), per-analyzer status return (I-17→#1261), effectiveEnabled (I-16→`planning/PR1266-fixup-effectiveEnabled.md`).
- **`checkVariantGPSMismatch` test coverage (deferred, no owner)** — split out of #1511 (4 earlier skip guards to satisfy, no existing test block, diagnostic-only). **Survives #1511's merge — still open.** Separate future test task; recorded in the `ta-itl-demand-test-gaps-plan.md` Commit-4 §. Create a branch when assigned.
- **EPP system-wide `k_sat` unification (NEW 2026-08-07, surfaced by PR-2 C10)** — PR-2 makes TA resolve `k_sat` from the saturation analyzer's `KvCacheThreshold` (0.80) instead of its own hard-coded `0.85`, but the *system-wide* value the EPP uses is still a third, unrelated copy. The existing `TODO: unify with the system-wide k_sat used by the EPP` moves onto `resolveKSat` as the single place to fix. File at Dean's direction.
- **Prometheus ITL-model gauges** — `wva_throughput_analyzer_itl_model_{a,b}` (labels namespace/model_id/variant/tier); see forward plan I-8.
- **EPP image version mismatch** — `install.sh` patches EPP v0.7.0 vs local llm-d v0.5.0 (infra bug).
- **Gateway prompt bug** — `install_core.sh` interactive prompt with `E2E_TESTS_ENABLED=false` despite `INSTALL_GATEWAY_CTRLPLANE=true` (infra bug).
- **Makefile IMG always set** — `deploy-e2e-infra` registry-image path unreachable (Makefile bug).
- **`runRegisteredAnalyzers` deletion** — dead-code in `engine_v2.go`; not removed in #1266. Standalone cleanup PR. Plan: [`planning/multi-analyzer-addendum-plan.md`](../planning/multi-analyzer-addendum-plan.md) § Item 4.
- **Optimizer `max`-shadowing cleanup** — `analyzer_helpers.go`: `roleBottleneckReplicas` (~L132) and `roleAggRemaining` (~L151) declare local `max` shadowing the Go builtin; flagged by ev-shindin in #1246 review. Minor cleanup; file post-merge.
- **Align the informativeness predicate with the RC that reaches the optimizer (Type-1 design question, later round — not PR-2)** — `ResultIsInformative` scans only per-variant `Reason`, while the `RequiredCapacity` the optimizer consumes comes from `RoleCapacities` via `applyUniversalThreshold` (`saturation/engine_v2.go:476-513`), which never mentions `VariantCapacities` — so a saturation result can be non-informative while carrying a positive role RC. **Latent, not live** (Type-1 Addendum-1 Rev 6: the capacity store keeps saturation informative in every reachable configuration), which is why it is a design question rather than a bug to schedule. Closing it means either having informativeness consider role demand, or having the scheduler-queue term mark the variants it speaks for. Not a revival of the rejected liveness-aware-refusal option (different site — the liveness computation, not a second refusal predicate in the optimizer). File at Dean's direction.

---

## Pending handoffs

| Agent | Doc | Status | Note |
|---|---|---|---|
| reviewer | `scratch/PR1092-short-draft.md` | READY | PR #1092 (VA CRD removal proposal) — short review comment draft ready; counter-proposal pending integration before Dean posts |
| reviewer | `planning/benchmark-wva-vs-keda-plan.md` | DRAFT | WVA-vs-KEDA benchmark plan — two scenarios (cost-optimal ramp + starvation prevention); awaiting Dean review before coder implementation |
| planner | `planning/open-items-roadmap.md` | **SCORED** (2026-06-15) | All areas scored (multi-analyzer, TA, D52/EV52). Committed `c71db32d`. See roadmap for Q1/Q2 priority list and dep graph. **Both #1250 and #1266 now merged — file Q1+Q2 items as GitHub issues.** |
| planner | `session/handoffs/plan__ta-anchor-doc-taxonomy-findings.md` | **OPEN** (`.WIP`) | Five doc-taxonomy findings for Dean to accept / reject / defer — **not** resolved by the Type-3 refresh. Deliberately still open. **Not sync's to consume.** |
| planner | `session/handoffs/plan__ta-anchor-dataflow-map-pr1-delta.md` | **OPEN** | Optional §9 addition to `multi-analyzer-dataflow-map.md`, deferred by Dean; partly overtaken — the map's §9 findings now live in the Type 1's § findings, so any delta is about the map's own currency. **Not sync's to consume.** |
