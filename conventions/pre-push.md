# Pre push

### convention: pre-push-checklist
description: Ordered pre-push checklist: branch check, gofmt, tests, lint, DCO sign-off, build.
scope: anyone about to git push or submit a PR
trigger: before every git push or PR submission
status: active
origin: session/CONVENTIONS.md § Pre-push checklist (C37); feedback_dco_signoff.md (FM10, automated-hook + rebase-fix detail), feedback_git_commit_identity.md (FM18, no -c user.name override)

**Pre-push checklist (run in order before every `git push` or PR submission).**
1. **Check current branch** — `git branch --show-current`. Confirm you are on the intended branch before any commit, amend, or rebase.
2. **gofmt** — `gofmt -l ./internal/... ./pkg/... ./cmd/...`. No output means clean.
3. **Tests** — `go test ./internal/... ./pkg/... ./cmd/...`. All pass.
4. **Lint** — `make lint`. Clean. This runs golangci-lint with the repo's `.golangci.yml` (nakedret, unparam, gocritic, staticcheck, …) — CI's `lint-and-test` job blocks on it, and **gofmt/build/test do NOT catch these** (they are lint-only findings that compile and pass tests). Skipping this step is how PR #1246 went green locally but failed CI lint.
5. **DCO sign-off** — every commit must carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`. Use `git commit --signoff` or `git commit --amend --signoff`. Verify with `git log upstream/main..HEAD --format="%b" | grep Signed-off-by`. DCO failure blocks CI and requires a force-push after the PR is open.

   `git rebase`/`git rebase --onto` replay commits verbatim — they do **not** carry forward
   `Signed-off-by` lines from the original commits, so any commit written before the current
   session (e.g. earlier commits from before a rebase) will be missing the sign-off afterward.
   Compare the sign-off count against the commit count:
   ```
   git log upstream/main..HEAD --format="%b" | grep -c "Signed-off-by"
   git log upstream/main..HEAD --oneline | wc -l
   ```
   If they don't match, fix with
   `git rebase --exec 'git commit --amend --signoff --no-edit' $(git merge-base HEAD upstream/main)`,
   then force-push with `--force-with-lease`. A `pre-push` git hook in the bare repository
   (shared by all worktrees) checks every commit for `Signed-off-by` and aborts the push if any
   are missing, printing the exact fix command — the permanent guard; the manual check above is
   a backup. Do not pass `-c user.name=...`/`-c user.email=...` or set `GIT_AUTHOR_*`/
   `GIT_COMMITTER_*` env vars on the commit itself — the repo's own git config already resolves
   the correct identity; just `git commit -s -m "..."` and, if you want to be sure, verify
   afterward with `git log -1 --format='%an <%ae>'`.
6. **Build** — `go build ./...`. Clean.

### convention: pre-push-no-push-without-confirmation
description: Never run git push without Dean's explicit confirmation for that specific push; state branch, commit range, and push type first.
scope: anyone about to run git push
trigger: about to push
status: active
origin: session/CONVENTIONS.md § No push without explicit confirmation (C38); feedback_no_push_without_confirmation.md (FM27, never-chain-commit-and-push detail)

**No push without explicit confirmation.**
Never run `git push` (or any variant) without Dean's explicit confirmation for that specific push.
State what branch will be pushed, the commit range, and whether it is a force push — then wait for
approval. Do not infer approval from earlier conversation context. This applies to every commit no
matter how small or obvious, and it applies fresh to each push — approval for a prior commit does
not carry forward to the next one. Never chain `git commit ... && git push ...` in a single
command; state the commit SHA and what will be pushed, then stop and wait as a separate step.

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
origin: session/CONVENTIONS.md § Force-push only after history rewrite, and explain why (C41); feedback_force_push_owner_is_planner.md (FM15, planner-owns-force-push detail)

**Force-push only after history rewrite, and explain why.**
Use `git push --force-with-lease` only after a rebase or amend — never for new commits on top of a
branch. Before force-pushing, state the reason (e.g., "rebased onto upstream/main", "amended to
add DCO sign-off") and wait for confirmation. Prefer `--force-with-lease` over `--force`.

**Ownership: the planner force-pushes PR branches, not the coder and not "Dean" personally.**
The coder-never-pushes rule above means the coder stops at a clean local commit plus a handoff;
the push itself — including any force-push — is a separate role action owned by the planner
(who also does the rebases / integration-branch assembly). In status files and handoffs, write
"NOT pushed — planner force-pushes #<n> when ready," not "Dean force-pushes." The coder still
never pushes and still warns before any push it is somehow asked to do.

### convention: pre-push-scope-narrow-to-named-artifact
description: "Push your plan/your file" names the content, not authorization to push the whole branch tip; on plans specifically, the planner never blanket-pushes — Dean pushes plans himself.
scope: planner or coder about to push in response to a named-artifact push instruction
trigger: told to push a specific named file/doc/commit rather than "the branch"
status: active
origin: feedback_push_scope_narrow_to_named_artifact.md

When Dean says "push your plan" (or "push your file," or names a specific doc/commit), that is
scoped to the content he named — not blanket authorization to push the branch to its current tip.
On a branch whose tip is written by many concurrent sessions (e.g. `plans`), your own commit is
very often not the only thing sitting ahead of origin/<branch>, and it may not even be
contiguous with other unpushed work at the tip. Git cannot literally push "only one file" — a
push moves a branch ref across all its ancestor commits — so before pushing in response to a
"push X" naming a specific artifact, run `git log origin/<branch>..<branch>` and check whether
the range contains commits beyond the one(s) named. If it does, surface that explicitly
("pushing would also carry N other commits from [topic/session] — push all of it, or do you want
just yours?") before pushing, rather than assuming the broader push is implied.

**Standing rule on `plans` specifically: the planner commits its part locally and never
blanket-pushes the shared branch; Dean pushes `plans` himself** — he's the only one who knows
whether other sessions' commits are OK to publish. So when asked "is X committed?", confirm the
mission's commits are all in local history and stop there; do not propose or run
`git push origin plans`. This is distinct from a code branch, which is all one mission's work and
does get an origin push, with per-push confirmation as above.
