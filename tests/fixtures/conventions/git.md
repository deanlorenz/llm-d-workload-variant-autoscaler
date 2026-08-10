# Git conventions

Fixture file. The conventions below are illustrative, not authoritative.

### convention: no-push-without-confirmation
description: Never run git push without explicit confirmation for that push.
scope: all branches, all agents
trigger: about to run git push
status: active
origin: repeated correction

Confirmation is per push, not per session. Approval of one push does not carry
to the next.

### convention: verify-cwd-before-commit
description: Run pwd and git branch --show-current immediately before every commit.
scope: any worktree
trigger: before git commit
status: active
origin: silent wrong-branch commits

A commit issued from the wrong working directory lands on the wrong branch with
no error, so the check has to precede the commit rather than follow it.

### convention: archive-never-delete
description: Archive a finished branch instead of deleting it.
scope: local branch cleanup
trigger: finishing with a branch
status: active
origin: git alias convention

An archived branch keeps its history reachable by tag. A deleted one is
recoverable only by reflog, and only for a while.
