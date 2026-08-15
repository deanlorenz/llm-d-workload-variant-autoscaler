from: chat session (state-commands port)
to: sync
session: state-commands-skills

## What landed

Three new personal skills + their Type 1 design, committed on `plans` as **`cc2d5ab0`**
(4 files, +1106, nothing else staged). **Not pushed** — `plans` is 1 commit ahead of
`origin/plans`, awaiting Dean's go-ahead.

- `.claude/skills/s-state-park/` — flush live context to durable storage. Additive only.
  **Model-invocable** (fires on its own initiative at risk points).
- `.claude/skills/s-state-sweep/` — reconcile the source of truth by **re-reading** every file
  backing an open item. `disable-model-invocation` — Dean-invoked only.
- `.claude/skills/s-state-consolidate/` — sweep plus conversation re-read, claim verification,
  staleness/duplication hunt, deliberate placement. `disable-model-invocation` — Dean-invoked only.
- `planning/state-commands-design.md` — Type 1 design, TOC'd, 10 sections. The durable contract.

Container symlinks added under `.claude/skills/` so all three resolve from every worktree
(verified). Command definitions were adapted from an external repo's `STATE-COMMANDS.md`; only the
three command definitions were taken, nothing else from that repo.

## Suggested CURRENT.md text (Recent activity, one abstract)

**2026-08-15 — state commands (park/sweep/consolidate) ported as skills; Type 1 design written.**
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
unfindable. Committed `cc2d5ab0`, **not pushed**. State:
[`planning/state-commands-design.md`](../planning/state-commands-design.md) (§ 5 adaptations,
§ 6 subagents, § 7 worktree exit, § 8 grants, § 9 forward work).

## Forward work to record (§ Next steps or § Issues to Open — sync's call)

1. **`SubagentStop` hook — the real flush-on-termination guarantee. Unscoped, Dean's.**
   Documented in design § 9.1. Fires when a subagent finishes, receives `transcript_path` and
   `last_assistant_message`, and `exit 2` **blocks** the stop — so a hook can either persist state
   itself from the transcript, or refuse to let the subagent finish until a state file exists. Beats
   "more park" because it fires whether or not anyone remembers to run park, and does not depend on
   `SendMessage` delivery. Touches `settings.json`, so it needs its own approval.
2. **`s-note` has two real defects** (design § 9.2), neither urgent: its handoff body uses the
   **pre-redesign format** (`to: plan-agent`, `body:`) rather than the current three-line
   `from:`/`to:`/`session:` convention; and its grants include `Bash(git -C plans *)` — the exact
   wildcard (including `git rm`) that this design rules out for the state commands.
3. **Open question, not decided:** should park ever fire *fully automatically* via a `PreCompact`
   hook — the one moment the loss channel is known to be about to open? Deliberately not designed;
   auto-firing a write-capable skill needs its own thinking.

## Caveat to carry (do not drop when compressing)

Design § 6.1's platform facts (transcript path, resume-by-agent-ID, `SendMessage` delivery not
guaranteed in every configuration, no graceful-flush signal exists, `SubagentStop` semantics) were
gathered by a spawned `claude-code-guide` subagent from the Claude Code docs on 2026-08-15. Its
citations were read but **not independently re-fetched page by page**. The resume-by-agent-ID and
transcript-path claims are the load-bearing ones if anyone wants them verified before relying on
them.

## Not requested, not done

No push. No GitHub action. No edits to CURRENT.md, `session/history.md`, or any other session's
docs. The `plans` working tree currently carries a lot of *other* sessions' uncommitted work
(modified planning docs, deleted/renamed handoffs, new status files) — I staged only my four paths
explicitly and verified the staged count was 4 before committing, so none of it was swept in. It is
all still uncommitted and belongs to its own owners.
