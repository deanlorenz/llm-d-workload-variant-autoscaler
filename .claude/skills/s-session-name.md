---
name: s-session-name
description: Rename the current session based on what it is actually about — re-triggers naming at any point in the conversation
---

Look at the conversation so far and determine the best session title.

**Format:** `{icon} {slug}` where:
- Icon: 🔍 triage · 👀 review · 📐 plan · 💻 code · 🔄 sync · 💬 chat
- Slug: 3–5 meaningful words, hyphen-separated, no stopwords

Examples: `🔍 pr-1318-triage`, `📐 analyzer-lifecycle-plan`, `💻 fix-effectiveEnabled-bug`

If the user passed an explicit title as args (e.g. `/s-session-name 📐 my-plan`), use that instead of generating one.

Then set it:

```bash
python3 ~/.claude/bin/session-mgr.py set-title "<icon> <slug>"
```

Report the new title back to the user.

**Note:** to permanently lock a title so auto-rename never touches it, prefix it with `QUOTE:` — e.g. `QUOTE: my locked title`.
