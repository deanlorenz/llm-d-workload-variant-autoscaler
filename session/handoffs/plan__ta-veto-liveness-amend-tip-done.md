from: ta-veto-liveness
session: amend-tip-ci-retrigger

## What changed
Per the plan's addendum ("D (#1481) CI re-trigger via tip amend"), amended
`ta-veto-liveness`'s tip commit in place:

```
git commit --amend --no-edit -s
```

New tip: `1df0f871` (was `832baa08`).

Verified all the addendum's conditions:
- New SHA differs from the old tip: `832baa08` → `1df0f871`.
- Still exactly 6 commits off `ef28744b` (`git log ef28744b..HEAD --oneline`).
- Exactly one `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>` trailer on the
  amended commit — `-s` did not duplicate it (checked before assuming it was
  safe to pass `-s`; it wasn't needed to add a new one, and git's own dedup
  kept it at one).
- DCO count across the range still 6/6.
- Content byte-identical: `git diff 832baa08 HEAD` is empty, and
  `git rev-parse 832baa08^{tree}` == `git rev-parse HEAD^{tree}`.
- `git fetch origin` confirmed `origin/ta-veto-liveness` was still at the old
  `832baa08` before this amend (i.e. the amend is local-only right now).

No other branch touched — A/A′/C are untouched, per the addendum ("No other
branch is touched").

## Do NOT push
Not pushed. Dean force-pushes (`--force-with-lease`) to fire the `synchronize`
event that re-dispatches #1481's `lint-and-test` `pull_request` workflow.

## Update CURRENT.md
- Bump `ta-veto-liveness` / #1481's tip in the PR-Status table to `1df0f871`
  (superseding `832baa08` from the forward-rebase handoff).
- A/A′/C tips are unchanged from the prior forward-rebase handoff.

## Not done
- No push (Dean's call, per addendum).
- Plan doc `planning/ta-09-rebase-ef28744b.md` not deleted — still says "once
  verified and force-pushed"; this amend hasn't been force-pushed yet.

## Open questions / follow-ups
- None — addendum's task fully done and verified.
