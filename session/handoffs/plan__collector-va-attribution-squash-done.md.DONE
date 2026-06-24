from: collector-va-attribution
session: squash + amend complete; ready for force-push

## What changed
Squashed the 3 commits (7157c7d2 / 85bd65de / 59e9990d) into one clean commit:

  6c0c6d7d feat(collector): resolve VA attribution behind an Attributor seam

Message reflects the full diff including R1 (builder error-return, DEBUG skip
log) and R2 (UnattributedReadyPods event). DCO present.

Gates re-run on the squashed commit:
- git branch --show-current → collector-va-attribution ✓
- gofmt -l internal/ cmd/ pkg/ → empty ✓
- make test → PASS ✓
- make lint → 0 issues ✓
- go build ./... → clean ✓
- make manifests → no diff from this change (pre-existing RBAC drift reverted) ✓
- Signed-off-by: Dean H Lorenz <dean@il.ibm.com> ✓

## Dean's action required
Force-push to replace the 3-commit origin tip with the squashed commit:

  git push --force-with-lease origin collector-va-attribution

Then open the PR against main.

## Update CURRENT.md
- Update collector-va-attribution: squashed to single commit 6c0c6d7d; local
  branch is 1 commit ahead of pre-squash origin; awaiting Dean force-push +
  PR open + CI + ev-shindin review.
