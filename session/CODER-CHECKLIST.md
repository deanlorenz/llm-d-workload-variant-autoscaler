# Coder Agent Pre-Completion Checklist

**MANDATORY verification before calling `attempt_completion`**

Run these checks in order. ALL must pass before declaring work complete.

## 1. Worktree State
```bash
git status
```
- ✅ Output shows "nothing to commit, working tree clean"
- ❌ ANY modified/untracked files → commit or explain why they exist

## 2. Current Branch
```bash
git branch --show-current
```
- ✅ Confirms you are on the intended branch
- ❌ Wrong branch → STOP, report error

## 3. Code Formatting
```bash
gofmt -l ./internal/... ./pkg/... ./cmd/...
```
- ✅ No output (all files formatted)
- ❌ ANY output → run `gofmt -w` on those files, commit

## 4. Tests
```bash
make test
```
- ✅ All tests pass
- ❌ ANY failures → fix or document pre-existing breakage

## 5. Lint (ENTIRE CODEBASE)
```bash
make lint
```
- ✅ "0 issues" and exit code 0
- ❌ ANY issues → fix them (unparam, gocritic, staticcheck, etc. are ALL blocking)
- **CRITICAL:** This runs on entire codebase, not just files you edited

## 6. DCO Sign-off (ALL COMMITS)
```bash
git log upstream/main..HEAD --format="%H %s%n%b" | grep -c "Signed-off-by"
git log upstream/main..HEAD --oneline | wc -l
```
- ✅ Both counts match (every commit has sign-off)
- ❌ Mismatch → amend missing commits with `git commit --amend --signoff`

## 7. Build
```bash
go build ./...
```
- ✅ Clean build
- ❌ Build errors → fix them

## 8. Final Verification
- ✅ All 7 gates above passed
- ✅ `git status` still clean
- ✅ Status file updated with current state
- ✅ Trigger file (if any) marked .DONE

**Only after ALL checks pass:** Call `attempt_completion`

## Common Failures

**"Ready for push" with dirty worktree**
- Symptom: `git status` shows modified files
- Fix: Commit ALL changes or explain why they are uncommitted

**Partial lint check**
- Symptom: Only checked files you edited
- Fix: Run `make lint` (checks entire codebase)

**Missing DCO on some commits**
- Symptom: Commit count > sign-off count
- Fix: `git rebase -i upstream/main` and add sign-offs

**Premature completion**
- Symptom: Declared complete before running all 8 checks
- Fix: Run the checklist, do not skip steps
