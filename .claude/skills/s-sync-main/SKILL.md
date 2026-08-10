---
name: s-sync-main
description: Fast-forward local main from upstream/main and push to origin/main. No-arg = interactive (check status, ask what to do). watch/status/stop/sync args skip the menu and act directly. Invoke with /s-sync-main [watch|status|stop|sync].
allowed-tools: Bash(bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-status.sh), Bash(bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-watch.sh), Bash(( cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main && bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-once.sh )), Bash(cat:*), Bash(grep:*), Bash(kill:*), Read, Monitor, TaskStop, AskUserQuestion
---

# Sync Main from Upstream

Fast-forward `local main` to `upstream/main` and push to `origin/main`. One skill, one status
file (`plans/session/status/main.md`), four things it can do:

- **status** — read-only check: is the background watcher alive, what's the current tip.
- **watch** — start the background watcher (Monitor tool) if not already running, so sync events
  arrive as conversation notifications. Usually unnecessary — see *Auto-start* below.
- **stop** — stop the watcher.
- **sync** — one-shot fetch/ff-merge/push in the background, regardless of watcher state.

**A watcher is normally already running without anyone asking**: the `SessionStart` hook
auto-starts one in this worktree on every startup/resume. See *Auto-start* below for what that
implies about notifications and stopping.

## No-arg invocation — interactive

If `/s-sync-main` is run with no argument:

1. Run the status check (below) and report it plainly — watcher running or not, current tip,
   last_check/last_sync timestamps, any push failure noted.
2. Use `AskUserQuestion` to ask what to do next, with options scoped to the current state:
   - If **not running**: "Start watch mode", "Run once now (one-shot sync)", "Nothing — just checking"
   - If **running**: "Stop the watcher", "Run once anyway (one-shot sync)", "Nothing — just checking"
3. Execute whichever mode was chosen, per the sections below. "Nothing" ends here — no action.

An explicit arg (`status` / `watch` / `stop` / `sync`) skips the menu and runs that mode directly.

---

## status — checking if the watcher is running

One allowlisted Bash call — the **first line is the gate verdict** (staleness), the rest is the
status file:

```bash
bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-status.sh
```

The date math lives inside the script (not on the command line) so this runs with no `$(...)`
substitution — it's allowlisted in the shared container settings and never prompts. The watcher
heartbeats every 60s, so a `last_check` under ~150s → **RUNNING**; older or missing → **STALE /
NOT RUNNING** (dead, or never started on this machine). After the verdict line the status file
gives `current_step`, the tip under `## Branch`, and any push failure under `## Notes`. A stale
`watcher_pid` from a previous session is expected and harmless — ignore it.

This check has no side effects — safe to run any time, from any worktree.

## Auto-start (no invocation needed)

The `plans` worktree **is** the designated sync-main session, so a live watcher is its normal
steady state. The `SessionStart` hook (`scripts/sync-main-session-start.sh`, registered on
`startup|resume` in the container settings) checks the heartbeat and, if no watcher is alive,
**starts one itself — detached, with no prompt.** So on every reload/resume of this session the
watcher comes back automatically; you do not need to run `/s-sync-main watch`.

**Exactly one watcher can ever run**, regardless of how many sessions start or resume: the watch
script holds an `flock` on `/tmp/sync-main-watch.lock` for its whole life, and any redundant
instance reports the incumbent's pid and exits 0 without touching the status file. The lock is
released by the kernel if the holder is killed, so there is no stale-pidfile cleanup. (The
heartbeat check in the hook is only a cheap early-out — it is racy on its own, which is how two
watchers came to be running on 2026-08-10.)

Because it lives in WSL under `/init` rather than under Claude, it **outlives the session**: a
reload/resume finds it already running and starts nothing. It is bound to this worktree twice
over — the script hardcodes the `Main` worktree as its git target, and the hook fires only when
session CWD is exactly the `plans` path.

**One consequence to know:** a hook-started watcher is a detached `setsid nohup` process, **not
a harness-tracked task.** `TaskStop` cannot reach it, and its sync events do **not** arrive as
conversation notifications — read `session/status/main.md` (or `/s-sync-main status`) to see what
it has done, and use `stop` below (the PID path) to end it. A watcher started in-session via
`watch` below *is* harness-tracked and does notify. Both keep `main` synced identically; they
differ only in observability and how you stop them.

## watch — starting the background poller in-session

Use when you want sync events as **conversation notifications** (the auto-started watcher is
silent). Only if the check above says not running:

```
Monitor({
  command: "bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-watch.sh",
  description: "watch upstream/main, auto-sync on change",
  persistent: true
})
```

The script polls cheaply (`git ls-remote` every 60s — a ref query, not a full fetch) and only
runs the real fetch/ff-merge/push when the upstream SHA actually changes, so it won't dirty this
session or spend tokens during quiet periods — you'll only get notified when a sync actually
happens or fails. It writes `plans/session/status/main.md` on every poll (heartbeat) and on
every sync. Report the returned task ID; keep it in mind for `stop` within this same session —
it is not persisted anywhere, so a different session can't reuse it (see `stop` below).

If the check says already running, report that instead of starting a second one.

## stop — stopping the watcher

If this session started it **via the Monitor tool** (`watch` above): `TaskStop` with that task's ID.

Otherwise — a **hook-auto-started** watcher (the common case; not harness-tracked), a different
session, or a lost task ID — kill the PID recorded in the status file:

```bash
pid=$(grep '^watcher_pid:' /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/session/status/main.md | awk '{print $2}')
kill "$pid" 2>/dev/null
```

The script traps its own exit and rewrites the status file to `current_step: stopped` —
re-check the status file afterward to confirm. `main` stays wherever it last landed; no more
auto-sync until `watch` runs again.

## sync — one-shot sync

Runs regardless of whether the watcher is active (harmless overlap — both just do
fetch/ff-merge/push, idempotently).

**Never `cd` in the calling shell.** Bash-tool CWD persists across every later call in the
session, so a bare `cd` silently relocates subsequent commits and `git add`s into the wrong
worktree. Put the `cd` inside a **subshell** so it dies with the command, and run it in the
**background** so the sync never blocks the session:

```
Bash({
  command: "( cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main && bash /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/scripts/sync-main-once.sh )",
  run_in_background: true,
  description: "one-shot sync of main from upstream"
})
```

The parentheses are load-bearing: the `cd` applies only inside the subshell, so the session's
CWD is untouched no matter how the script exits. `run_in_background: true` returns immediately
and re-invokes you with the result when it finishes.

`sync-main-once.sh` does the whole sequence itself (branch check → fetch → `merge --ff-only` →
push, aborting before the push if the merge is not a fast-forward) and rewrites
`plans/session/status/main.md` the same way the watcher does. No `claude -p` subprocess and no
model turn is involved — this is four git commands, so spawning a nested agent to run them was
pure overhead.

Report the outcome once the background task reports back: what was fetched (new commits or
already up to date), the resulting tip, and whether the push succeeded.
