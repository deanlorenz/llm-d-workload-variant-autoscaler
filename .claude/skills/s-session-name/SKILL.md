---
name: s-session-name
description: Rename the current session based on what it is actually about — re-triggers naming at any point in the conversation
---

Look at the conversation so far and determine the best session title.

**Format:** `{icon} {subject} {Role}` where:
- Icon + Role (spell the role word out — the icon alone is ambiguous):
  🔍 Triage · 👀 Review · 📐 Planner · 💻 Coder · 🔄 Sync · 💬 Chat
- Subject: 2–3 meaningful words, hyphen-separated, no stopwords; keep it short when clear.

**PR-bound sessions** — lead the subject with `PR #<N>` so they line up uniformly, and pick
the role word by mode:
- `👀 PR #1229 Review` — reviewing a PR (external or your own)
- `🔍 PR #1246 Triage` — working reviewer comments / CI to land a PR
- `💻 PR #1250 Coder` — coding fixes on an open PR (e.g. an existing coder session that pivots
  to fixing its PR — re-trigger this skill to rename it)

**Non-PR sessions** — topic slug + role word. Internal code/doc reviews use the same 👀 icon
and read `👀 <topic> Review`:
- `👀 optimizer-ceiling Review` · `📐 analyzer-lifecycle Planner` · `💻 effectiveEnabled-fix Coder` · `💬 pd-allocation Chat`

If the user passed an explicit title as args (e.g. `/s-session-name 📐 my-plan`), use that instead of generating one.

Then set it:

```bash
python3 ~/.claude/bin/session-mgr.py set-title "<icon> <slug>"
```

Report the new title back to the user.

**Note:** to permanently lock a title so auto-rename never touches it, prefix it with `QUOTE:` — e.g. `QUOTE: my locked title`.
