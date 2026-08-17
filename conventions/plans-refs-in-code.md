# Plans refs in code

### convention: plans-refs-in-code
description: Code-side artifacts (comments, docstrings, identifiers, dev-guide text, tests, commit messages) must not reference plans-branch section identifiers; expand to descriptive prose instead.
scope: coder writing code-side artifacts on a code branch
trigger: writing a comment, docstring, identifier, dev-guide text, test description, or commit message that would otherwise cite a plans-branch identifier
status: active
origin: session/CODER-CONVENTIONS.md §4a No plans-branch references in code-side artifacts (CC11)

**4a. No plans-branch references in code-side artifacts.**

Code comments, doc-strings, function names, identifiers, dev-guide
text, test descriptions, and commit messages on code branches must
not reference plans-branch documents by section identifier. The
plans branch is invisible to a reader of the merged code — tokens
like `F3`, `A10`, `T1`, `B2`, `D1`, or pointers to
`planning/*-plan.md` / `planning/*-review.md` are meaningless to
them. Use descriptive prose instead.

| Bad (in code/commit) | Good |
|---|---|
| `// fixture for future SC suppression (F3)` | `// fixture for future per-analyzer status-return work that will restore the SC gate` |
| `// see optimizer-plan §B2` | `// see the paired-allocation min-util commit logic` |
| `// per design F1 — pre-analysis extraction` | `// future cleanup: extract per-variant metadata collection out of the saturation analyzer` |

Plan and review docs you're reading freely use those identifiers
because both ends of the conversation are on the plans branch. When
you transcribe content into code, strip the identifier and keep the
prose. Same rule for commit messages — they're permanent code-side
history.

If a plan section directs you to add a code comment with specific
content, treat any plans-branch identifier in that content as
shorthand for the prose; expand it before writing. If unclear,
write a planner handoff and ask.

### convention: plans-refs-in-code-grep-gate
description: Mechanical grep gate for catching plans-branch identifier leaks (decision #, review finding, Fn, plan section refs) in added code comments and test descriptions before push.
scope: coder before push; reviewer during review
trigger: before push, on the diff's added comment/test lines; during review, on code comments and It/Describe strings
status: active
origin: governance-follow-ups.md sec 2026-07-29 PR C sec4a leaks (GF4)

The 4a rule above is a vigilance rule with no gate of its own — it is violated by *transcription*,
when a coder copies a plan/review sentence (which correctly uses plans-branch identifiers) into a
code comment or test description verbatim. One incident shipped 14 such leaks across two commits,
found only on a manual round-3/4 re-scan after two earlier review rounds scanned only dev-guide
text, not code comments or test description strings, and a round-3 grep was too narrow (7
reported vs. 14 actual). The mechanical gate that would have caught all of them the first time:
grep the diff's added comment/test lines for

```
decision #|Decision #|review finding|\bF[0-9]\b|plan section|TA-[a-z]+ section|planning path|-plan file|-review file
```

(the real pattern also matches literal `planning/`, -plan.md, and -review.md — written above
with prose stand-ins so this entry's own text doesn't itself trip the plans-refs-in-code check).
Run this as a coder pre-push step on the diff's added comment/test lines, and as a reviewer step
that additionally covers code comments plus `It`/`Describe` strings, not just dev-guide text —
same structure as `semantic-pivot-grep`.
