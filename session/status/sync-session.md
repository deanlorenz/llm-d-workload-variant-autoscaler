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
