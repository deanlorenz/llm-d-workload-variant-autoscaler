# Addendum 8 — plans-tooling becomes the main dev branch for plans, not a throwaway kickoff worktree

**Amends** [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) (design, FINAL, frozen
2026-08-10) § Migration, specifically the "Own worktree for the tooling, copied over at an atomic
deliberate kickoff" decision recorded in that design's own digest and § Decided list. The parent is not
edited: this is the amendment channel it names.

**Status: decided by Dean, 2026-08-15.**

---

## What changed

The original plan (per the frozen design and its digest) treated `plans-tooling` as a **throwaway
development worktree**: build the migration tooling there in isolation, then copy the finished result
into `plans/` in one deliberate kickoff action, after which `plans-tooling`'s own development history
would stay behind on its own branch, not become part of `plans`'s ongoing history.

Dean, 2026-08-15: *"We are going to use plans-tooling for all code work and for all rules migration
work. It will become our main dev branch for plans."*

This is a real scope change, not a rewording:

- `plans-tooling` is no longer scoped to *just* the tooling spec's four scripts (`sec`/`conv`/
  `conv-list`/`conv-lint`) plus the authoring spec's three (`conv-new`/`conv-edit`/`conv-rename`). It
  becomes the working branch for **all** code work on the plans tree and **all** rules-migration work
  going forward — a durable branch, not a scratch worktree with a planned end-of-life copy-over.
- The "atomic deliberate kickoff copy" step (moving `plans-tooling`'s content into `plans/` in one
  action, per the design's own § Decided list) is **superseded by this decision** — if `plans-tooling`
  *is* the dev branch now, there may be no separate copy-over step at all, or it may become a
  fast-forward/merge instead of a copy. Not resolved here; flagged as an open consequence below.

## Immediate practical effect

A coder session and an internal code-reviewer session are being started in `plans-tooling`
(2026-08-15), with the coder's first task being the `conventions-authoring-spec.md` slice
(`conv-new`/`conv-edit`/`conv-rename`, S1-S3) — the natural next step after the already-landed
read-side tools, on a spec already reviewed as good. This addendum records the branch-role change that
makes that assignment durable rather than scoped to one throwaway task.

One untracked leftover exists in the worktree from an earlier trial harvest pass:
`conventions/code-deletion.md`, never committed. Flagged for the coder to check in about rather than
silently absorb or discard, since its provenance (a planner's own trial, not part of any spec) isn't
something a coder should resolve unilaterally.

## Background-agent launch, 2026-08-15 — mechanism found, one defect fixed

Dean asked for a coder and internal-code-reviewer, both persistent sessions he directs only through
the planner (not directly), with a read-only progress view he can watch. Findings from actually doing
this, captured as they occurred rather than only at the end:

- **`claude --bg`** (background agent, distinct from both `claude -p` one-shot and the in-process
  `Agent` tool) is the correct primitive — `claude agents --json` gives structured status
  (`state`/`status`/`waitingFor`) for scripting, `claude logs <id>` gives raw terminal output (not
  reliably clean — see below), `claude attach <id>` opens it interactively, `claude stop <id>` ends it.
- **`claude logs <id>` returns raw ANSI/terminal escape sequences**, not clean text — unusable for a
  planner to parse directly. `claude agents --json` is the reliable structured-status path instead.
- **Real defect, found and fixed:** launching with `--permission-mode acceptEdits` left both agents
  stuck at `state: blocked, waitingFor: "permission prompt"` — `acceptEdits` only covers file-edit
  operations, not the broader tool calls (Bash, reads outside default-allowed paths, etc.) a session
  needs just to start working, and nobody is present to answer an interactive prompt for a background
  agent. Fixed by relaunching with `--permission-mode auto`, which matches this project's own documented
  model (CONVENTIONS.md: interactive only on genuine judgment calls, everything else unprompted) —
  confirmed unblocked (`state: working`) after relaunch. **Anyone launching a `claude --bg` agent in this
  project should default to `--permission-mode auto`, not `acceptEdits`.**
- **VS Code has no native support for this workflow, researched and confirmed (not guessed):** no
  panel/tree view for background agents, no passive live-streaming view, no way to restrict which
  session type opens interactively vs. only via background dispatch. The closest approximation for
  Dean's "read-only progress view" ask is running `claude agents` in a VS Code integrated terminal
  himself and leaving it open — an interactive TUI he doesn't type into, not a true passive stream.
  Dean explicitly deferred formalizing the "planners are the only interactive webview sessions, every
  other role is agent-only" governance model as its own design item — this is recorded here as the
  supporting research, not as that decision.
- **Session auto-naming picked up "Planner" as the role suffix for the coder** (`"name":
  "📐 coder-session-plans-tooling-branch Planner"`) — the auto-namer inferred the role word from
  context and got it wrong (coder ≠ planner). Cosmetic, not corrected, flagged in case it causes
  confusion later when distinguishing agents by name alone.
- **Two live agents as of this writing:** coder `14d876ac` (plans-tooling, building
  conv-new/conv-edit/conv-rename per `conventions-authoring-spec.md` S1-S3), reviewer `3da4ba42`
  (launched from `plans`, scoped to review the coder's work once ready, explicitly told to wait).

**Second round of findings, same day — `auto` mode does not fully close the human-in-the-loop gap:**

- **`SendMessage`/`ListAgents` failed to reach either background agent**, even with the exact display
  name from `ListAgents`'s own output, with and without its `[ref]` suffix. Both calls returned "No
  agent... is reachable." Consistent with the already-recorded finding in memory
  `feedback_sendmessage_vs_file_handoffs` (2026-08-13: "it did not reliably work") — this is a second,
  independent occurrence, not a one-off. `claude -p --resume <session-id>` also does not work for a live
  background agent ("Session ... is currently running as a background agent... Use `claude agents` to
  find and attach to it, or add `--fork-session` to branch off a copy" — the latter creates a *new*
  session, not what's needed). **The only reliable way found to get new instructions to a running
  background agent is the file-based handoff protocol** — which is also the *correct* channel
  architecturally (it preserves the audit trail and state-machine ownership rules), not merely a
  fallback for a broken shortcut.
- **Real mistake, caught and fixed immediately:** the first handoff attempt was written to
  `plans-tooling/session/handoffs/` — wrong, since that path doesn't exist as a coordination surface;
  the shared handoff directory is `plans/session/handoffs/` regardless of which worktree a session's
  CWD happens to be in. A coder session operating with CWD in a code worktree still needs the shared
  `plans/session/handoffs/` path, exactly as every other coder in this project's existing convention
  already does. The stray directory was deleted before anything read it; corrected file written to
  `plans/session/handoffs/coder-plans-tooling__s1-test-mechanism-approved.md`.
- **`--permission-mode auto` reduces prompts but does not eliminate all of them.** Both agents later
  surfaced a `needsInput`/`Needs input` state visible only in `claude agents`' live TUI — genuinely
  requiring a human to answer at that exact interface, which broke the "Dean never interacts with the
  agent directly" boundary out of necessity (Dean answered directly since no other channel could reach
  the agent at that moment). This is a real, currently-unresolved gap in the ownership model Dean is
  describing (2026-08-15, same day, separate concern from this addendum's launch-mechanics content):
  a planner cannot yet guarantee it is the *only* channel through which an agent it owns receives input.
  Not designed around here — flagged for whatever eventually formalizes the "planner-owns-agents"
  governance model.
- **Despite the above, both agents' actual work quality was strong.** The reviewer independently
  re-derived the full four-stage review pipeline from CONVENTIONS.md and correctly scoped itself to
  S1-S3 only, unprompted; it also independently rediscovered the same "move a convention between topic
  files" open design gap flagged in `conventions-authoring-spec.md`'s own Intent section. The coder found
  a real, non-obvious parsing detail on its own (a convention field written as bare `key:` with no
  trailing space is invisible to `conv-lint`'s field regex, which requires `^[a-z][a-z-]*:[[:space:]]`
  — meaning an unsupplied field is reported as *missing* rather than *empty*, which is exactly the
  behavior the spec calls for), asked a well-reasoned question about test mechanics before writing any
  code (the existing harness diffs read-only fixtures; `conv-new` necessarily mutates files, so it
  proposed fixed deterministic scratch dirs under `tests/tmp/` rather than `mktemp`, plus a `.gitignore`
  entry), and committed S1 (`65553806`) cleanly once approved, leaving the untracked leftover
  `conventions/code-deletion.md` untouched exactly as instructed.
- **Resolved: how Dean can actually follow a background agent's output.** `claude logs <id>` and
  `session-extract.sh` against the agent's own transcript JSONL (findable at
  `~/.claude/projects/<cwd-with-slashes-as-dashes>/<session-id>.jsonl`, same location and shape as every
  other Claude Code transcript) both fall short for this purpose — `logs` dumps raw unreadable ANSI, and
  `session-extract.sh` is deliberately built to surface only *user*-authored turns, not the agent's own
  reasoning or actions, so it shows almost nothing for a background agent nobody is chatting with.
  **`claude attach <id>`, interacted with normally (the same live TUI Dean was already using), is the
  actual answer** — real-time, complete, shows everything the agent is doing. Dean found this himself.
  Net effect: watching a background agent's *output* is solved (attach); *sending it new instructions*
  without becoming its sole conversational partner is still open, per the file-handoff-is-the-reliable-
  channel finding above — attaching to type at it defeats the "only through the planner" boundary the
  same way answering a stray prompt did.

## Session end, 2026-08-15 — both agents stopped and examined before transcript deletion

Per Dean's explicit request ("stop all... examine... capture and delete everything"): both background
agents (coder `14d876ac`, reviewer `3da4ba42`) were stopped via `claude stop <id>` — confirmed gone from
both `claude agents --json` and the process table before proceeding. Full inventory was taken first
(`claude agents --json`, unfiltered) to confirm only these two `kind: background` entries belonged to
this planner session; the six `kind: interactive` entries in the same listing (including this session
itself) were left untouched — they are other live sessions' work, not this session's to stop.

**Real finding, would have been lost without checking before delete: the coder got further than last
verified.** `plans-tooling` shows S2 committed (`57f4874a`, `conv-edit.sh`) in addition to the
previously-confirmed S1 (`65553806`) — only S3 (`conv-rename`) remains unbuilt. S2's commit message
documents catching a genuinely subtle bug before the golden test could hide it: trailing blank lines
between a convention's section and whatever follows (next heading or EOF) belong to the file's
structure, not the section being replaced — splicing at the untrimmed boundary glued the replacement
directly onto the next heading. Fixed by mirroring `sec.sh`'s own read-side trim on write. Round-trip
tested (`conv | conv-edit --from <output> | conv` byte-exact). Working tree left clean, the untracked
`conventions/code-deletion.md` leftover still untouched throughout — same discipline as S1.

The reviewer's transcript (37 records total, all Bash/Read tool calls) contained nothing beyond what is
already captured above — it read exactly what it was told to, invoked `/code-review` zero times (the
coder never signaled anything ready), and wrote no files anywhere. Nothing further to preserve from it.

Both transcript files (`~/.claude/projects/.../14d876ac-*.jsonl`, 755KB;
`~/.claude/projects/.../3da4ba42-*.jsonl`, 73KB) are being deleted after this capture, per Dean's
explicit instruction — their substance now lives here and in the `plans-tooling` git history (S1/S2
commits), not only in the (now-deleted) transcripts.

## Still open — consequences not yet worked out

- **What happens to the planned "copy into `plans/`" kickoff step**, now that `plans-tooling` is meant
  to persist as the dev branch rather than be retired after one copy. Candidates: `plans-tooling`
  effectively *becomes* `plans` (a rename/merge), or `plans` stays the canonical branch and
  `plans-tooling` becomes a long-lived feature branch that periodically merges forward — not decided.
- **Governance implications** — `session/CONVENTIONS.md`'s existing rules about who may write to
  `planning/` (multi-writer) versus `session/` (single-writer via sync) were written assuming `plans` is
  the one active branch for this kind of work. Whether those rules need restating for a dual-branch
  (`plans` + `plans-tooling`) reality, or whether `plans-tooling` simply inherits them as-is once it's
  understood as "the same branch, different name," is not addressed here.
- **DCO/gate posture — resolved for now, revisit later.** `conventions-authoring-spec.md`'s own
  Prerequisites say "No DCO on this lineage. Never push." for `plans-tooling`, written under the
  throwaway-worktree assumption. Dean's call, 2026-08-15: **keep this as the default for now** — nothing
  about the main-dev-branch decision itself changes push/DCO rules; the coder launched today stays
  local-only, no DCO required, until Dean explicitly revisits this Prerequisite. Not a permanent answer,
  just the safe default while the branch-role change's other consequences are still being worked out.
