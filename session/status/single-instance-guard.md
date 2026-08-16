name: single-instance-guard coder
id: (not exposed to this session)
role: coder
branch: plans
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
owned_doc: planning/checkpoint-capture-spec.md S0/S2/S4 + planning/sync-watchers-spec.md S1/S2
task: build scripts/lib/single-instance-guard.sh and migrate its three call sites
status_file: session/status/single-instance-guard.md

last_update: 2026-08-16T16:20Z
state: in-progress
current_step: code complete, committed, all gates green — awaiting Dean's review
blocked_on: (not blocked)

## Branch

`plans` at `/home/dean/.../plans` ; my work is in tip **`f9e1dba6`** — see the commit-collision
note below, the SHA is not the one I intended and its message does not describe my change.

## What landed

**New:** `scripts/lib/single-instance-guard.sh` (205 lines) — `guard_acquire <script-name>
<key-flag> <key>` and `guard_release <script-name> <key>`, extracted from the three
near-byte-identical inline guard blocks.

**Migrated, all three call sites:**

| script | key | call |
|---|---|---|
| `session-snapshot.sh` | session id (new required `--session-id`, unless `--once`) | `guard_acquire "session-snapshot" --session-id "$session_id"` |
| `tick-shared-scan.sh` | fixed role constant | `guard_acquire "tick-shared-scan" "" "sync"` |
| `sync-main-watch.sh` | fixed role constant | `guard_acquire "sync-main-watch" "" "sync"` |

`--origin-pid` is untouched in all three and still does exactly one job — the `kill -0`
kill-switch in each main loop. Nothing about it was renamed, removed or re-keyed.

**Defect C fixed** (`sync-main-watch.sh`): `write_status` took `<step> <notes>` and hardcoded
`state: watching`, so `cleanup()`'s `write_status "stopped" ...` put "stopped" in `current_step`
and the file claimed a live watcher after every exit. It now takes `<state> <step> <notes>`; all
six call sites updated. Also fixed a pre-existing off-by-one in that script's `-h` range, which
printed `set -uo pipefail` as help text.

## Verified

Gates from both specs, plus Addendum 7's behavioral checklist. `bash -n` clean on all four files.
`shellcheck -x` clean: exactly the four findings that already existed at HEAD (SC2016, SC2034,
SC2164, SC2001 — confirmed by running shellcheck against the `git show HEAD:` versions), **zero
new**. The new library is clean on its own.

Behavioral, all run for real, not reasoned about:

- **Two simultaneous launches → exactly one survivor.** Session-keyed: 5/5. Role-keyed (empty
  key-flag): 5/5. Both counted with a `/proc` argv scan rather than `pgrep`, so the count cannot
  be fooled by a shell that merely quotes the pattern.
- **Sequential second launch stands down via `pgrep`, first undisturbed** — both keys.
- **Guard released at startup, not held while the loop runs** — dedup dir absent while a loop runs;
  0 dirs left behind after every test.
- **Planted fresh guard respected AND left intact** — the stander-down does not `rmdir` a directory
  it does not own (return 1 path).
- **Planted week-old guard reclaimed**, launch proceeds.
- **`--origin-pid` kill-switch, no regression** — origin killed → "running final pass, then
  self-exiting" in the loop's own log, then exit; instance count 1 → 0.
- **Argument validation** — 7 cases (empty/unsafe script-name, empty/unsafe key, malformed
  key-flag, `guard_release` argc, release idempotency).
- **The real bug fix, end to end:** launching `tick-shared-scan.sh` and `sync-main-watch.sh` with
  `--origin-pid 1` while the live production instances (`3410333`, `3412453`, both started with
  `--origin-pid 3362193`) are running now correctly stands down. Under the old pid-keyed guard both
  would have started a duplicate — for `sync-main-watch.sh` that means two watchers doing
  `fetch`/`merge`/`push origin main` in the same worktree. Both stood down with rc 0 before any
  `cd`, any git call and any status write (confirmed: `session/status/main.md` untouched).

**Not tested, deliberately:** `sync-main-watch.sh`'s guard *success* path. Exercising it starts a
real watcher that pushes to `origin/main`. Its guard code is the identical library path proven by
the role-keyed tests above (5/5 simultaneous + sequential), and its stand-down path is verified
against a live instance. I did not run `tick-shared-scan.sh`'s work path either — it calls
`tick-consolidate.sh`, i.e. real model spend.

## Judgment calls made (Dean asleep; flagged for review)

1. **`<key-flag>` may be empty, meaning "the script name alone discriminates".** The specs say the
   pgrep pattern is `<script>[.]sh .*<key-flag> <key>` and that the two sync-owned scripts key on
   `"sync"` — but `"sync"` appears nowhere in their argv, and neither spec resolves that. I did
   **not** add a `--role` flag to carry it: the launch paths are the `SessionStart` hooks, which are
   explicitly out of scope this round, so a caller omitting the flag would make every instance
   invisible to every other and silently disable the guard entirely. Empty key-flag → pattern is
   the bare script name; the role constant still keys the `mkdir` lock. This is also what lets a new
   sync session see an instance an older one started, which is the whole point of the role key.

2. **Added a `/proc` narrowing filter (`_guard_is_instance`) — not in the spec, but required.** A
   bare-name `pgrep -f` pattern also matches the *shell that launched the script*, so the first
   role-keyed test left **zero** survivors: instance A saw its own launcher and stood down while B
   lost the `mkdir` race. That is the same 4/4 failure shape Addendum 7 hit. The filter keeps only
   processes actually executing the script (argv[0] is the script, or argv[0] is a shell and argv[1]
   is the script). Side benefit: this removes the documented need to launch these loops "through a
   separate wrapper script on disk" to dodge pgrep self-matching. The `[.]sh` escaping and the
   `$$` self-exclusion regex are unchanged; `grep -v` replaces `grep -qv` only because the pids are
   now needed, and the constraint is commented on that exact line as instructed.

3. **Kept the one-week mtime reclaim.** The task said not to build a staleness check. I read that as
   scoped to the *retracted pid-keyed held-lock* design, and kept the pre-existing mtime reclaim:
   without it, a process killed in the sub-second window between its own `mkdir` and `rmdir` wedges
   every future start permanently. Addendum 7's checklist also requires "a planted stale guard is
   reclaimed", which cannot pass without it. If you want it gone, it is four lines in `guard_acquire`.

4. **`guard_release` takes `<script-name> <key>`,** not the spec's `<name>` — the path needs both,
   and explicit arguments beat hidden global state in a sourced library.

## Out of scope, untouched as instructed

`tier1-session-start.sh`, `sync-main-session-start.sh`, `container-settings.json`, S0b's handle
registry, `sync-current-watch.sh`. No production loop restarted. Nothing pushed.

**One instruction I could not carry out as written:** the task asked me to fix Defect B "in this
same file's stale header comment" while working in `sync-main-watch.sh` — the stale flock claim and
the "any Claude process anywhere in this WSL instance" claim. Both live in
**`sync-main-session-start.sh`** (lines 45 and 34-36), which the same task says to "leave alone
entirely this round". I left it alone; the file-level prohibition is the more specific instruction.
`sync-main-watch.sh`'s *own* header did describe the superseded mechanism and is rewritten. Defect B
proper is still open.

## Two live defects found along the way — NOT mine, NOT fixed (need a decision)

Found while assessing the mistake below, both in Tier-1 capture, both **silent**:

1. **Marker poisoning.** `session-snapshot.sh`'s `pass()` derives its marker from the last `^## `
   line of the extracted text. A user turn whose own text contains a markdown heading therefore
   overwrites the marker with that heading. `session/digests/.atomic-step-protocol-brainstorm.raw.md.mark`
   currently contains the literal string **`Findings`**, and that loop's log shows
   `since: Findings` / `turns: 0` repeating — **Tier-1 capture for that session has captured nothing
   since 2026-08-13** and the sidecar's mtime confirms it. Fails with rc 0, indistinguishable from
   "nothing new".
2. **`sync-session` capture never appended anything.** No marker file at all, extract reports
   `turns: 122` every pass, yet `session/digests/sync-session.raw.md` has been 379 bytes (header
   only) since 2026-08-14, so `pass()`'s `grep -q '^## '` guard has never matched.

Both are outside my assigned scope (the spec calls S2's non-guard logic defect-free, which is
wrong) and fixing them needs a decision about how the silent-failure path should behave, so I
flagged rather than fixed. Handed to a planner: `plan__tier1-capture-marker-poisoning.md`.

## My own mistake, recorded

**I killed two live production Tier-1 loops** (pids `16342` and `629315`) during the first suite
run. My cleanup helper matched on script name alone instead of the test's own session id, so it
signalled every `session-snapshot.sh` process on the machine. Rewritten to be session-scoped, and
the re-run confirmed the remaining two production loops (`3410333`, `3412453`) untouched.

Mitigating, and verified rather than assumed: **both killed loops had been capturing nothing** —
loop 1 since 2026-08-13 (defect 1 above), loop 2 since inception (defect 2). So no capture was
actually lost. I did **not** restart them: restarting is the separately-approved deployment step,
and I cannot determine the correct `--origin-pid` (these `claude` processes carry no
`--resume=<session-id>` in argv, so CURRENT.md's identification recipe does not apply to this
launch shape). Restart command for whoever does it, per session:

```
nohup bash scripts/session-snapshot.sh --out session/digests/<topic>.raw.md \
  --file <that session's transcript> --origin-pid <that session's real claude pid> \
  --session-id <that session's id> --interval 120 &
```

## Process hazard found: the shared git index

My commit did not land as its own commit. I ran `git add` on my four files; before my
`git commit ... -- <paths>` executed, **another session ran its own commit and swept my staged
files into it** — `f9e1dba6 "planning: benchmark runs inventory ..."` contains my four files plus
their one. Content is intact and is exactly the version tested (verified `git show HEAD:` against
the working tree), but the message describes only their file, which CONVENTIONS treats as a hard
reject.

I did **not** rewrite it — it is another session's commit on a shared branch and they may still be
working. Dean's call whether to reword/split before pushing (it is local; `origin/plans` does not
have it yet).

Mitigation worth adopting: in this shared worktree, never `git add` — commit with a pathspec only
(`git commit -s -m ... -- <paths>`), which never leaves your files in the index for another session
to pick up. Raised to a planner in `plan__shared-git-index-commit-collision.md`.

## Open questions for Dean

- Judgment calls 1-3 above, especially the added `/proc` filter (not in the spec, but the guard
  does not work without it) and keeping the mtime reclaim.
- Whether to reword/split `f9e1dba6` before pushing.
- The two Tier-1 capture defects — capture is currently dead for at least one active session.
- Defect B remains open (its text is in a file this round was told not to touch).
