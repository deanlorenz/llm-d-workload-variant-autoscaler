from: sync-session (plans)
to: plan (atomic-step-protocol-brainstorm)
session: checkpoint-guard-facts-not-yet-in-any-doc

## What this is

Not new design work — Dean already made the calls in
[`atomic-step-protocol-design-addendum-10.md`](../../planning/atomic-step-protocol-design-addendum-10.md)
(pid-based staleness, shared library, handle registry). This is a punch-list of facts that only
exist right now in commit messages, `session/CURRENT.md` prose, or this session's own conversation
— nowhere durable. Fold them into whichever doc actually owns each, when you revise
[`checkpoint-capture-spec.md`](../../planning/checkpoint-capture-spec.md) to match addendum-10 (which
your own addendum-10 already says is paused pending that revision — this handoff is input for that
pass, not a new task).

## Facts with no durable home yet

1. **A `pgrep`-only dedup left ZERO survivors on simultaneous launch, not one** — both instances see
   each other and both stand down. This was addendum-7's own headline finding
   ("Verification required" item 1 already documents the requirement to test for it), but the
   *symptom description* — "left zero, 4/4" — is only in a commit message (`750f9c5d`) and
   `session/CURRENT.md`, not in addendum-7's prose itself. Minor, but worth carrying into whatever
   doc ends up being the canonical incident record.

2. **`--once` mode diverged between scripts on whether it skipped the dedup guards.**
   `tick-shared-scan.sh` correctly skipped both guards under `--once`; `session-snapshot.sh` didn't,
   until fixed. This is a real defect that was found and fixed **after** addendum-7 was written, so
   it isn't in addendum-7's "Defect history" section at all. Same shape as the other three defects
   addendum-7 already catalogs (copied-without-checking-purpose) — belongs alongside them.

3. **A `pgrep -f` self-match testing artifact, not a script defect, cost real debugging time twice.**
   Typing `--origin-pid <literal-pid>` into an interactive shell call makes that exact string appear
   in the *calling* shell wrapper's own argv for the duration of that call — `pgrep -f` then matches
   the wrapper as a false "already running," even though no real second instance of the target
   script exists. Confirmed via independent raw `/proc/<pid>/cmdline` scans (bypassing `pgrep`
   entirely) both times. Workaround: launch through a separate wrapper script on disk, never a Bash
   call whose own literal text contains the search pattern. This is purely a testing/interactive-use
   gotcha — a real launcher (a hook, a script calling another script) never has this problem — but
   it's worth one line somewhere so the next person testing these scripts doesn't lose the same time
   rediscovering it. Best guess for where it belongs: a note in `checkpoint-capture-spec.md`'s
   testing/verification guidance, if that section exists or gets added.

4. **`scripts/sync-current-watch.sh` was never migrated to the Addendum-7 guard scheme at all.**
   Still runs the old `flock` + `anchor_alive()` pattern. Confirmed by reading the file directly —
   its own comment ("same pattern as sync-main-watch.sh") is now false, since that script moved on.
   Addendum-7's "Still open" list does not mention this script. Flagged to me by a handoff from this
   same planner (`plan__tick-shared-scan-guard-superseded-by-addendum-7.md`, currently sitting
   misfiled as `plan__` though addressed `to: sync` — I'll handle the routing/`.DONE` separately,
   not this handoff's concern) — restating here so it's visible from the design side too, since
   addendum-10's shared-library refactor is the natural point to bring this fourth script in line
   rather than leaving it on a fifth different scheme.

5. **Two of the four old-interface production loops were manually restarted under the pre-addendum-10
   interface** (`tick-shared-scan.sh` pid `3410333`, `sync-main-watch.sh` pid `3412453`, both with
   `--origin-pid` pinned to this session's real Claude process pid, found via matching
   `--resume=<session-id>` in `/proc/<pid>/cmdline` rather than trusting any shell wrapper pid).
   Recorded in `session/CURRENT.md` only. Worth knowing before addendum-10's shared-library refactor
   lands, since those two running processes will need a deliberate restart under whatever new
   interface `guard_acquire`/`guard_release` end up requiring — not something to assume away.

## Not asking for

No new design decisions — addendum-10 already made them. No code from me — per worktree-scope
rules, this session doesn't code checkpoint scripts beyond what's already committed. Just: don't
let these five facts fall through the crack between "fixed in conversation" and "written somewhere
a cold session could find them."
