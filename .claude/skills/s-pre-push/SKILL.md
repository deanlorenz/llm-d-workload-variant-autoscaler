---
name: s-pre-push
description: Run the pre-push checklist before every git push or PR submission. Checks branch, gofmt, tests, DCO sign-off, and build. Reports results and stops on any failure. Invoke with /pre-push [target-branch] where target-branch is the branch you intend to push (defaults to current branch).
disable-model-invocation: true
allowed-tools: Bash(git branch:*), Bash(git log:*), Bash(git diff:*), Bash(gofmt:*), Bash(go test:*), Bash(go build:*), Bash(grep:*)
---

# Pre-Push Checklist

**Arguments:** $ARGUMENTS (optional target branch — defaults to current branch)

Run all five checks in order. Stop and report failure immediately if any check does not pass. Do not suggest pushing until all five are green.

---

## Check 1 — Branch

```bash
git branch --show-current
```

Report the current branch. If $ARGUMENTS names a specific branch, confirm the current branch matches. If it doesn't match, stop and tell the user.

---

## Check 2 — gofmt

```bash
gofmt -l ./internal/... ./pkg/... ./cmd/...
```

- **Pass**: no output.
- **Fail**: one or more files listed. Report them and stop. Do not proceed to tests with unformatted code.

---

## Check 3 — Tests

```bash
go test ./internal/... ./pkg/... ./cmd/...
```

- **Pass**: all packages pass.
- **Fail**: report the failing package(s) and test name(s). Stop.

---

## Check 4 — DCO sign-off

```bash
git log upstream/main..HEAD --format="%H %s%n%b" | grep -c "Signed-off-by:"
git log upstream/main..HEAD --format="%H %s" | wc -l
```

Every commit since `upstream/main` must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Compare the sign-off count to the commit count.

- **Pass**: counts match (every commit has at least one sign-off line).
- **Fail**: list the commits missing sign-off. Stop. Fixing requires `git rebase --signoff upstream/main` or amending individual commits — tell the user which.

If `upstream/main` is not reachable (e.g. no upstream remote configured), fall back to `origin/main`.

---

## Check 5 — Build

```bash
go build ./...
```

- **Pass**: exits 0 with no output.
- **Fail**: report the error and stop.

---

## Report

After all checks pass, print a single summary:

```
✓ branch:  <branch-name>
✓ gofmt:   clean
✓ tests:   <N> packages passed
✓ DCO:     <N> commits signed off
✓ build:   clean

Ready to push.
```

Do not push automatically. The user decides when to run `git push`.
