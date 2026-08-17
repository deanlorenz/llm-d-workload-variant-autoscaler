# Session start

### convention: session-start
description: Coder sessions invoke /s-coder before touching any file, since CODER-CONVENTIONS.md is not auto-loaded.
scope: any coder session, at session start
trigger: session start, in any worktree, whether launched there or moved there via EnterWorktree
status: active
origin: session/CONVENTIONS.md § Agent roles and document ownership (C12)

**Coder sessions: invoke /s-coder before touching any file.** session/CODER-CONVENTIONS.md is
**not** auto-loaded — it used to be imported by plans/CLAUDE.md, which meant every planner, chat and
sync session paid for it while the sessions that actually needed it did not get it: code worktrees
carry only the upstream CLAUDE.md (`see @AGENTS.md`), and `EnterWorktree` re-roots the chain, so a
coder launched in a worktree — or one that moved into it — loaded none of its rules. The `s-coder`
skill loads it on demand and is reachable from every worktree via the container .claude/skills/
symlink. This applies to both launch paths: started in `plans` then `EnterWorktree`, or started
directly in the worktree.

### convention: session-start-title-convention
description: Session titles follow [icon] subject Role, with the role word spelled out (Coder/Review/Planner/Triage/Sync/Chat) since the icon alone is ambiguous; PR-bound sessions lead with PR #<N>.
scope: anyone naming or renaming a session
trigger: producing a session title, via the s-session-name skill or the auto-namer default
status: active
origin: feedback_session_title_convention.md

Session titles read `[icon] <subject> <Role>`, e.g. `💻 pd-role-ceiling Coder`,
`📐 utilization-terminology Planner`, `💬 session-title Chat`. Dean doesn't reliably remember which
icon maps to which role, so a spelled-out **role word** is appended: Coder / Review / Planner /
Triage / Sync / Chat. Prefer **shorter** subjects when clear (2–3 words).

Icon↔role: 🔍 Triage · 👀 Review · 📐 Planner · 🔄 Sync · 💻 Coder · 💬 Chat. (Role word is
**Review**, not "Reviewer" — reads better as "PR #1229 Review".)

**PR-bound sessions must lead the subject with `PR #<N>`** so they line up uniformly in history,
role word by mode: `👀 PR #1229 Review` (reviewing a PR), `🔍 PR #1246 Triage` (working reviewer
comments/CI to land a PR), `💻 PR #1250 Coder` (coding fixes on an open PR). **Non-PR sessions:**
`[icon] <topic> <Role>`. Internal code/doc reviews use the same 👀 icon and read
`👀 <topic> Review`, distinct from PR reviews only by the `PR #<N>` lead. An auto-namer that runs
on the first prompt can detect a `PR #<N>`/`#<N>` there and emit the `PR #N` subject
automatically — if so, its output still needs to match this shape, not override it.
