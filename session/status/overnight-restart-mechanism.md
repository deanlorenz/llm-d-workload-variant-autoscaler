name: overnight-restart-mechanism
id: (see this session's own transcript)
role: planner
branch: plans (this status file); plans-tooling (the owned code spec)
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans-tooling
owned_doc: plans-tooling/planning/overnight-restart-mechanism-plan.md
task: Step 0 (tier1-session-start.sh hook wiring) done and verified mechanically; Steps 1-3 unblocked, not started
status_file: session/status/overnight-restart-mechanism.md

last_update: 2026-08-18T00:00:00Z (approximate)
state: idle (Step 0 done; awaiting either a real fresh-session verification or Dean's next-step direction)
current_step: none -- parked after Step 0
notes: freeform below

## What happened, in one paragraph

Dean asked for a token-saving mechanism for long/overnight auto-mode sessions: detect when a
restart makes sense, and safely fork-and-switch without ever destroying the old session. Full
design discussion resolved several open questions (fork mechanism confirmed real via `/branch`;
Alt1/Alt2/Alt3 restart alternatives left undecided, empirical measurement deferred; §10's
no-autonomous-closure principle explicitly and knowingly crossed as a narrow, named exception;
collision risk solved by making park itself the mandatory safe-boundary action, not a separate
gate). Plan approved 2026-08-18. Code spec written and committed on `plans-tooling`:
`planning/overnight-restart-mechanism-plan.md` (commits `21014e16`, `da267eb8`).

**Step 0 turned out to be a real, independent finding**, not just "wire the hook": the hook was
already correctly written, bug-fixed, and Dean-approved into the container's `settings.json`, but
never fired because settings.json does not inherit across directory levels and every real session
here launches rooted at a single worktree, never the container. Confirmed via `/proc/<pid>/cwd` on
all 4 live sessions (all `cwd=plans`) and zero hook-evidence in any transcript. Fixed by merging
the hooks directly into `plans/.claude/settings.json` — commit `b7961000` on `plans`, Dean's
explicit approval obtained for that specific settings.json edit.

## State, per step

- **Step 0 — DONE, verified mechanically, one thing still open.** Simulated a real `SessionStart`
  JSON payload directly against `tier1-session-start.sh` post-fix: produced a live Tier-1
  `session-snapshot.sh` loop with correct digest naming and args, cleaned up after. **Still
  unverified: whether Claude Code's actual `SessionStart` event mechanism fires this on a genuine
  fresh session launch** — this session cannot trigger that on itself. Next fresh session started
  in `plans` is the natural test; check for a `session-<uuid>.raw.md` digest and a live
  `session-snapshot.sh` process shortly after that session starts.
- **Steps 1-3 — unblocked, not started.** Step 1 (real numbers into `session/.tier2-usage.log`)
  has no open design question and is the natural next build. Step 2 (restart probe skill) and
  Step 3 (trigger detector) both depend on Step 1's ledger format and on Step 0's verification
  landing clean.

## Armed footguns / things worth carrying verbatim

- **None currently armed.** No paused process, no uncommitted risky state. Both `plans` commits
  (`b7961000`, and the earlier micro-rules-migration park commits from the prior session) and both
  `plans-tooling` commits (`21014e16`, `da267eb8`) are committed but **NOT pushed** to their
  respective origins — normal per the project's no-push-without-confirmation rule, not a defect,
  but worth stating so a cold resume doesn't assume they're already on origin.
- **`plans/.claude/settings.json` still carries another session's 5 uncommitted-looking-but-now-
  actually-committed accept-once permission lines** (added 2026-08-17 22:55 by an unrelated
  session, folded into commit `b7961000` alongside this fix since they were already sitting in the
  same file). Not attributed or discarded, per CURRENT.md's own standing instruction — just noting
  they rode along in this commit's diff, so a `git show b7961000` will show them as "added" even
  though they predate this change and aren't part of it.

## Open, not resolved, explicitly Dean's call

1. Whether the real `SessionStart` firing works end-to-end — needs a genuine fresh session start
   in `plans` to confirm (see Step 0 note above). Not something this session can self-verify.
2. Everything the code spec's own "Deferred, Dean's call" section lists is unchanged: Alt 3
   measurement harness, Bob/cheaper-model Tier-2 delegation, composite-score thresholds, and the
   open question of whether Step 1's target scripts get edited on `plans` directly (as Step 0's
   fix just did) or migrated into `plans-tooling` first — Step 0's precedent (edit on `plans`
   directly, since these are operational scripts) is now the working answer unless Dean says
   otherwise.
3. Whether to push either branch's new commits. Not done, not asked.

## Verified before parking

- Both `plans-tooling` commits present in `git log --oneline` there (`21014e16`, `da267eb8`).
- `plans` commit `b7961000` present in `git log --oneline` here (confirmed above, 3-commit tail
  shown includes it).
- `plans/.claude/settings.json` re-validated as syntactically correct JSON after the edit (Claude
  Code's own settings validator accepted it on write; also cross-checked with `python3 -m
  json.tool`).
- The Step 0 mechanical test (synthetic `SessionStart` payload → live Tier-1 loop → cleaned up)
  left no residue: confirmed `session/digests/session-test-verify-hook-*` files removed, confirmed
  no orphaned `session-snapshot.sh` process for that test session-id still running.
