# Pre push

### convention: pre-push-checklist
description: Ordered pre-push checklist: branch check, gofmt, tests, lint, DCO sign-off, build.
scope: anyone about to git push or submit a PR
trigger: before every git push or PR submission
status: active
origin: session/CONVENTIONS.md § Pre-push checklist (C37)

**Pre-push checklist (run in order before every `git push` or PR submission).**
1. **Check current branch** — `git branch --show-current`. Confirm you are on the intended branch before any commit, amend, or rebase.
2. **gofmt** — `gofmt -l ./internal/... ./pkg/... ./cmd/...`. No output means clean.
3. **Tests** — `go test ./internal/... ./pkg/... ./cmd/...`. All pass.
4. **Lint** — `make lint`. Clean. This runs golangci-lint with the repo's `.golangci.yml` (nakedret, unparam, gocritic, staticcheck, …) — CI's `lint-and-test` job blocks on it, and **gofmt/build/test do NOT catch these** (they are lint-only findings that compile and pass tests). Skipping this step is how PR #1246 went green locally but failed CI lint.
5. **DCO sign-off** — every commit must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Use `git commit --signoff` or `git commit --amend --signoff`. Verify with `git log upstream/main..HEAD --format="%b" | grep Signed-off-by`. DCO failure blocks CI and requires a force-push after the PR is open.
6. **Build** — `go build ./...`. Clean.

### convention: pre-push-no-push-without-confirmation
description: Never run git push without Dean's explicit confirmation for that specific push; state branch, commit range, and push type first.
scope: anyone about to run git push
trigger: about to push
status: active
origin: session/CONVENTIONS.md § No push without explicit confirmation (C38)

**No push without explicit confirmation.**
Never run `git push` (or any variant) without Dean's explicit confirmation for that specific push.
State what branch will be pushed, the commit range, and whether it is a force push — then wait for
approval. Do not infer approval from earlier conversation context.

### convention: pre-push-warn-active-pr
description: If the target branch has an open PR, state its number and title before pushing and wait for confirmation.
scope: anyone about to push to a branch with an open PR
trigger: about to push to a branch, before confirming it has no open PR
status: active
origin: session/CONVENTIONS.md § Warn before pushing to an active PR branch (C39)

**Warn before pushing to an active PR branch.**
If the target branch has an open PR (check `gh pr view <branch>`), state the PR number and title
before pushing and wait for confirmation. This prevents accidental history rewrites or force-pushes
that would disrupt reviewers.

### convention: pre-push-force-push-explain
description: History-rewrite pushes are used only after a rebase or amend, never for new commits; state the reason first and prefer the safer lease-checked flag.
scope: anyone about to push after a history rewrite
trigger: about to push after a rebase or amend
status: active
origin: session/CONVENTIONS.md § Force-push only after history rewrite, and explain why (C41)

**Force-push only after history rewrite, and explain why.**
Use `git push --force-with-lease` only after a rebase or amend — never for new commits on top of a
branch. Before force-pushing, state the reason (e.g., "rebased onto upstream/main", "amended to
add DCO sign-off") and wait for confirmation. Prefer `--force-with-lease` over `--force`.
