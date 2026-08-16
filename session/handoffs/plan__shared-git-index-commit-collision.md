from: plans (single-instance-guard coder)
to: planner
session: shared-git-index-hazard

A process hazard worth a convention, found by hitting it: **multiple sessions working in the `plans`
worktree share one git index, so a `git add` from one session can be committed by another.**

## What happened

I finished and tested four files, ran `git add` on exactly those four, then ran
`git commit -s -F - -- <those four paths>`. My commit returned *"no changes added to commit"* — because
in the window between the two commands another session ran its own commit, which picked up everything
staged in the shared index. The result is commit **`f9e1dba6`**, message *"planning: benchmark runs
inventory -- collection/extraction/viz status for all 31 runs"*, containing that session's one
`planning/` file **plus my four `scripts/` files**.

Both sessions did something individually reasonable. Neither did anything wrong per the current
rules. The index is simply shared state that nothing in `CONVENTIONS.md` treats as shared — unlike
CURRENT.md, handoffs and status files, which all have explicit single-writer or ownership protocols.

## Why it matters

`CONVENTIONS.md` § Key Working Rules is emphatic that *"Commit messages must reflect the diff"* and
calls a mismatch a hard reject. This collision produces exactly that mismatch, silently, with no
warning from git and no error on the winning side. The losing side finds out only because its own
commit fails — and a session that ran `git add` and then did something else first would not find out
at all.

It also defeats the review pipeline in a small way: a reviewer reading `f9e1dba6` by its message has
no reason to expect four shell scripts in it.

## Suggested convention (a one-liner, plus the reason)

**In a worktree that concurrent sessions share, never `git add`. Commit with a pathspec only:**

```
git commit -s -m "..." -- <path> [<path> ...]
```

A pathspec commit takes the working-tree state of exactly those paths and **never leaves anything in
the index** for another session's commit to sweep up. It is also the only form that is safe when the
index already contains someone else's staged work — which is the normal state here, not an edge case.
Corollary: never `git commit -a`, and never `git restore --staged` someone else's staged file to
"clean up" before your own commit (I nearly did; it would have silently undone their staging).

This is `plans`-specific in practice — code branches get one coder per worktree — but the rule is
cheap enough to state unconditionally.

## What I did and did not do about `f9e1dba6`

Content is intact and is exactly the version I tested (verified `git show HEAD:<path>` against the
working tree for all four files). I did **not** rewrite, reword or split it: it is another session's
commit, on a shared branch, and they may still be working. It is local — `origin/plans` does not have
it — so a reword or split is still available if Dean wants one; that is his call, not mine.

Detail and test results: `session/status/single-instance-guard.md`.
