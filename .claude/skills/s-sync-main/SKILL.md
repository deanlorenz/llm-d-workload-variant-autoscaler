---
name: s-sync-main
description: Fast-forward local main from upstream/main and push to origin/main. No-arg = interactive (check status, ask what to do). watch/status/stop/sync args skip the menu and act directly. Invoke with /s-sync-main [watch|status|stop|sync].
allowed-tools: Bash(cd:*), Bash(claude -p:*), Bash(bash plans/scripts/sync-main-watch.sh:*), Bash(cat:*), Bash(kill:*), Bash(date:*), Read, Monitor, TaskStop, AskUserQuestion
---

# Sync Main from Upstream

Fast-forward `local main` to `upstream/main` and push to `origin/main`. One skill, one status
file (`plans/session/status/main.md`), four things it can do:

- **status** — read-only check: is the background watcher alive, what's the current tip.
- **watch** — start the background watcher (Monitor tool) if not already running. Keeps `main`
  continuously synced for as long as this session stays open.
- **stop** — stop the watcher.
- **sync** — one-shot blocking fetch/ff-merge/push, regardless of watcher state.

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

## watch — starting the background poller

Only if the check above says not running:

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

If this is the same session that started the watcher: `TaskStop` with that task's ID.

If not (a fresh/different session, or the task ID was lost) — fall back to killing the PID
recorded in the status file:

```bash
pid=$(grep '^watcher_pid:' /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/session/status/main.md | awk '{print $2}')
kill "$pid" 2>/dev/null
```

The script traps its own exit and rewrites the status file to `current_step: stopped` —
re-check the status file afterward to confirm. `main` stays wherever it last landed; no more
auto-sync until `watch` runs again.

## sync — one-shot blocking sync

Runs regardless of whether the watcher is active (harmless overlap — both just do
fetch/ff-merge/push, idempotently).

```bash
cd /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/Main
```

```bash
claude -p "Run each as a separate Bash call in order: (1) git branch --show-current (2) git fetch upstream (3) git merge --ff-only upstream/main — if this fails stop and report, do not run step 4 (4) git push origin main. Report what was fetched (new commits or already up to date) and whether the push succeeded." --allowed-tools "Bash(git branch --show-current),Bash(git fetch upstream),Bash(git merge --ff-only upstream/main),Bash(git push origin main)" --no-session-persistence
```

Report the output to Dean.
