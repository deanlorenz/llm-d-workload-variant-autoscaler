name: sync-session
id: c1b50362-abc7-4c15-87f2-4125ba0f0043
role: sync
branch: plans
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
owned_doc: planning/atomic-step-protocol-design-addendum-7.md
task: checkpoint-script guards (origin-pid lifecycle + dedup) — coded, tested, committed; review deferred
status_file: session/status/sync-session.md

last_update: 2026-08-15T00:20:00+03:00
state: idle
current_step: parked — safe to close VS Code
blocked_on: none
recent_commits:
  - 750f9c5d checkpoint(guards): origin-pid lifecycle + atomic single-instance guards; drain before exit

## What landed

`750f9c5d` on `plans` (local only, **not pushed** — 19 commits ahead of origin/plans, most from
other sessions). Three checkpoint scripts reworked, plus a new design doc:

- `scripts/session-snapshot.sh` (Tier-1), `scripts/tick-shared-scan.sh` (Tier-2),
  `scripts/sync-main-watch.sh` — `--origin-pid` dead-man's-switch (`kill -0`, final work **then**
  exit), two-guard dedup (atomic `mkdir` + `pgrep`), 1-week mtime staleness reclaim, no lock files,
  no traps for the guard.
- `planning/atomic-step-protocol-design-addendum-7.md` — the design, written retroactively (84 lines).
- `scripts/tier1-session-start.sh` — added but **NOT wired**.

Verified behaviorally: 5/5 exactly one survivor on simultaneous launch; stale guard reclaimed; fresh
guard respected and not deleted; guard released during normal run; final pass evidenced in log on
origin death.

## Next step (Dean's instruction, 2026-08-15)

**Do not continue coding in `plans`.** Ongoing work belongs in a worktree. The scripts are already
coded, so they stay as they are here. The **review process resumes later** in the `plans-tooling`
worktree or a fresh/temp one — deliberately not mixed with `plans-tooling`'s existing in-flight work.

## Review status — INCOMPLETE, and the convention was not followed

Two ad-hoc `general-purpose` subagents were used as checkers. Their findings were real and are fixed
(the pgrep race, `stat -f %m`, `--once` divergence). **But neither was a conventions-conforming
review:** CONVENTIONS.md § Review pipeline requires a Type 6 doc (`planning/*-review.md`,
`Status: DRAFT`) produced by the review-agent role via `/s-design-review`. No Type 6 doc exists.

Two open questions, deliberately unanswered rather than guessed:
1. **Who runs it.** This session wrote the code, so self-reviewing under a role designed to be
   independent is the wrong shape. Recommendation: spawn it, keep this session in `sync`.
2. **Scope form.** `/s-design-review` expects a branch/PR/design-doc; this is uncommitted-then-
   committed work in `plans` with no PR. Design-doc scope
   (`atomic-step-protocol-design-addendum-7`) fits best.

## Carry forward

- **`tick-live-index.sh:111` still has the `stat -f %m` bug.** Same defect fixed in the other three;
  left alone as out-of-scope. Not urgent (fallback path only), but it is a real latent crash.
- **Four production loops still run the OLD interface** (no `--origin-pid`): `session-snapshot.sh`
  pids 16342 + 629315, `sync-main-watch.sh` 89026, `tick-shared-scan.sh` 620370. They work; they
  just predate this commit. Restarting them under the new interface is a **separate, approved step**
  — not done, and it needs `tier1-session-start.sh` finished first.
- **`tier1-session-start.sh` is incomplete:** needs `--origin-pid "$PPID"` (it currently passes
  nothing, so it would fail the new required-arg validation), plus a `container-settings.json`
  SessionStart hook entry. That settings edit was blocked once by `guard-settings-edit.sh` and needs
  explicit approval — do not self-approve it.
- **`.claude/settings.json` has another session's uncommitted permission additions.** Left untouched.

## Process lessons recorded in the addendum

Three defects, one shape: a guard released before the thing it protects exists. Root cause was no
Type 3 plan — code was written straight from conversation, so a review had nothing to check against.
The addendum's § Verification required exists to stop testing the guard mechanism instead of the
script's purpose.

---

## 2026-08-17 park — everything above this line is stale, left as-is (park is additive)

The "Carry forward" section above is largely resolved by later work this session did not do
directly — flagging the staleness rather than rewriting it (that's sweep/consolidate's job, not
park's). Notably: the guard mechanism has been rebuilt at least twice since (addendum-7 →
addendum-10, retracted same-day → session_id/role-constant keyed, per `single-instance-guard.sh`),
`tier1-session-start.sh` ownership was transferred to the atomic-step-protocol-brainstorm planner
(`plan__tier1-session-start-ownership-transfer.md`), and several production loops were restarted.
Do not trust the specific pids/commit-SHAs above without re-verifying.

### This session's actual current state

**Uncommitted right now:** `.claude/skills/s-sync-current/SKILL.md` — real, substantive,
already-Dean-approved edits (each carries a `user-approved-settings-change` marker): corrected
Step 1a/4-6 to stop treating handoffs as git-preservable (they're gitignored at every state —
`.md`/`.WIP`/`.DONE`/`.RETRACTED`, confirmed by reading `.gitignore` directly), and added a new
Step 3a item 7 encoding the durable-vs-transient doc rule below. **This file has NOT been
committed** — do that before treating this park as complete for this thread.

**New rules established this session, previously undocumented anywhere, now encoded into
`s-sync-current/SKILL.md`'s Step 3a item 7 (once that edit is committed):**
1. Only Type 1/2/3/4/6 docs count as durable compression targets, and only once confirmed not
   currently live (ask the owner if unsure). Type 5 (session state — CURRENT.md, `session/status/*.md`)
   and session digests (`session/digests/*.raw.md`) are transient by construction and must never be
   what a compressed CURRENT.md summary depends on for permanence — a status file may ride along as
   "here's the live state right now," never as the sole citation.
2. There is no formal "consolidate transient state into a doc" operation (Dean: don't call it
   "digest" — that word already names the opposite, raw un-consolidated files; use "consolidate,"
   matching `tick-consolidate.sh`'s own naming). It's manual, by whoever owns the durable doc.
3. **Consolidation ownership is not tied to who produced the state.** A status file is often
   coder-owned (sometimes a since-exited background job); folding its findings into a Type 1/2/3 is
   the *owning planner's* job regardless. This corrected an assumption I was making implicitly in
   three separate handoffs sent today before the rule was stated explicitly.

**Separate correction, also not yet written anywhere before this park:** peeking at other sessions'
handoffs (even ones addressed `to: planner`/`to: review`, not to sync) is fine for my own
orientation/liveness-checking, but the content must never leak into CURRENT.md — only `sync__`
traffic addressed to me, or a direct ask to the actual owner, may become CURRENT.md content. I
violated the spirit of this once this session (stating a "ta-anchor/autoscaling-viz are dormant"
conclusion to Dean that was actually wrong, derived from misreading the situation rather than from
peeked content directly — no CURRENT.md leak occurred, verified by checking `git status`/`git log`
before and after, but the near-miss is why this rule is now explicit).

**Real, useful token-cost finding, not yet written anywhere:** investigated Dean's ~700M-token
question by parsing every transcript's `usage` blocks directly (not file-size guessing) —
`cache_read_input_tokens` totals ~13.1 **billion** across 83 transcripts, dwarfing output (64M) and
input (22M). Confirmed directly, not assumed: none of the automated checkpoint tooling
(`session-snapshot.sh`/Tier-1, `tick-shared-scan.sh`/Tier-2, `sync-main-watch.sh`) is the source —
Tier-1 is pure shell by design, Tier-2's usage log was empty and its registry didn't even exist
(zero real model calls made), main-sync never touches a model. The actual source is 7 concurrent
long-lived `claude` processes (several 1+ day old at time of checking), each paying cache-read cost
that compounds every turn as their own conversation grows. Discussed with Dean: park+`/clear`+
cold-resume, and a `fork`+`/compact`+code pattern (pay the expensive read-in once, fork before
coding work adds turns, compact each fork immediately so coding turns pay against a summary rather
than full history) — with the caveat that `/compact` is lossy (54-compactions-in-one-session
finding already in `doc-and-session-model.md`), so anything load-bearing from the shared read-in
step should be written to a durable file **before** forking, not trusted to survive compaction.
This finding and the mitigation discussion exist only in this conversation as of writing this park
entry — no separate doc captures it yet, and none is proposed here (would need Dean's call on
whether it's worth a standalone note or just this status-file record).

**Two open handoffs sent by this session, unanswered as of this park:**
- `session/handoffs/plan__state-commands-current-entry-too-large.md` → chat session (state-commands
  port) — asking them to confirm/consolidate their CURRENT.md entry.
- `session/handoffs/plan__pokprod-benchmark-current-entry-too-large.md` → whoever owns
  `ta-pokprod-roadmap.md`/`ta-pokprod-history.md` — same ask, already corrected once this session to
  stop citing `session/status/benchmark.md` as if it were durable.

No armed footguns beyond the uncommitted `SKILL.md` edit above. CURRENT.md itself is clean —
confirmed via `git status` immediately before writing this entry.

---

## 2026-08-17, later same day — second park: full sync cycle done, size reduction confirmed

**Prior park's open items, resolved:** the `SKILL.md` edit was committed (`ee5cb005`, same park).
Both handoffs it flagged as unanswered got real replies and were consumed in the sync pass below.

### This pass's work

Ran a full `/s-sync-current` cycle. Five handoffs consumed: `sat-v2-f1-gap-compress-to-summary-
and-ref` (already satisfied by an earlier edit — verified both target spots, no further change
needed); `pokprod-benchmark-entry-compressed-20260817` (compressed a ~188-line block to ~24 lines
+ refs into `ta-pokprod-roadmap.md`/`ta-pokprod-open-scenarios.md`/`ta-pokprod-history.md`, the
sender having independently verified the ledger D-1..D-72 sequential/complete/no-gaps first);
`micro-rules-migration-complete` (new active-WIP entry, `plans-tooling`'s overnight 5-step
mandate); `autoscaling-viz-good-panels-done` + `autoscaling-viz-status-compressed-and-current-
refresh` (merged into one refreshed entry, tip `a1a815a7`, replacing a stale `cff4e4c0`-era
block). During Step 3a reconciliation, found and removed two further blocks already fully
superseded by content read this session (a stale shared-Tier-2 Next-steps entry; a stale
2026-08-08 pokprod tooling-plan entry) — neither needed a handoff first, since their content was
independently confirmed present in docs already read and cited elsewhere in this same pass.

**Net result, Dean-verified:** CURRENT.md went 786 → 593 lines (−193, ~25%) despite two new
entries being added. Committed `1ac5537b`, pushed to `origin/plans` (`553186b6..1ac5537b`).

**A real process near-miss, caught and fixed correctly this time:** the concurrent-sync watcher
(`sync-current-watch.sh`) raced its own baseline write again — the exact failure mode the skill's
own Step 7 already documents (watcher holds `last_known_current_sha` in memory from its own
startup read; editing the status file while it's still running gets silently overwritten on the
next poll). Caught it happening live (a `git diff` write to the status file failed with "modified
since read," then the watcher's own next poll visibly reverted my edit) instead of assuming the
file write had taken effect. Fixed per the skill's prescribed order: `TaskStop` the watcher first,
verified via a real `/proc` scan that no process remained, wrote the fresh baseline, then
restarted via `Monitor`. Confirmed working by observing the new watcher's own first real poll
report `SAFE` (not a stale `CONFLICT`) against a genuinely-pending handoff. Baseline commit
`3b723ad2`, also pushed.

**Two new handoffs arrived during/after this pass, correctly left for the next sync cycle, not
folded in here:** `sync__pokprod-benchmark-state-cleanup-20260817.md`,
`sync__panel-review-20260817-done.md`. Neither read in detail — deliberately, this park is not a
sync pass.

No corrections, no rejected approaches, no armed footguns from this pass. Working tree clean
(`git status` shows nothing outstanding beyond what's about to be committed by this park itself).
