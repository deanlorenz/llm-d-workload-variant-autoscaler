# Where the `benchmark` status file lives

**Authoritative copy: `plans/session/status/benchmark.md`, on the `plans` branch.**

That is the path every convention points at, the one the planner and sync sessions read, and
the only copy that should ever be cited. This directory does **not** hold a second copy.

## Why there is a README here instead of a status file

Until 2026-08-09 the status file was maintained *here*, in the benchmark worktree, and copied to
`plans/` by the planner. The reason was a belief that a harness-isolated coder session could not
write to `plans/session/status/` at all. That belief was half right, and the half that was wrong
is what produced the duplicate:

- The **`Write`/`Edit` tools** are blocked from the shared-checkout path by worktree isolation.
- **Bash `cp`/`mv`/redirect are not.** They reach `plans/session/status/` and
  `plans/session/handoffs/` normally, including the full `.md` -> `.WIP` -> `.DONE` rename cycle.

So the file could have been maintained at its canonical path all along. Because it wasn't, two
byte-identical 170,783-byte copies accumulated -- one tracked here, one uncommitted in `plans/` --
with no declared authority. No content was ever lost, but nothing recorded which one led, and a
reader had no way to tell a stale copy from a current one.

## The workflow that replaces it

Dean's direction, 2026-08-09: the coder owns the `plans/` copy outright and maintains it directly.

1. Edit the scratch copy at `session-notes/local/benchmark.md` (untracked -- see `.gitignore`),
   which is what the `Write`/`Edit` tools can reach.
2. Copy it to the authoritative path on save:
   `cp session-notes/local/benchmark.md ../plans/session/status/benchmark.md`
3. Commit it on the `plans` branch.

The scratch copy is an editing surface, not state. If it disagrees with `plans/`, `plans/` is
right and the scratch copy is simply out of date.

Historical note: every status section written before 2026-08-09 (through §18, the 2026-08-08 dwell
run) was authored under the old arrangement. That history is preserved in this branch's git log --
`git log --follow -- session-notes/status/benchmark.md` -- and its content carried forward intact
into the authoritative copy, so nothing needs to be recovered from here.
