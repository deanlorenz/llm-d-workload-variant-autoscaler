---
name: s-pr-triage
description: Fetch all reviewer comments, inline threads, and CI status for one of Dean's PRs and produce a local planning/PR<N>-review.md doc on the plans branch. No GitHub posting. Invoke with /s-pr-triage [PR-number] or /s-pr-triage to auto-detect from the current branch.
allowed-tools: Bash(gh pr view:*), Bash(gh pr checks:*), Bash(gh api repos/*/pulls/*/reviews:*), Bash(gh api repos/*/pulls/*/comments:*), Bash(gh api repos/*/issues/*/comments:*), Bash(git -C plans:*), Bash(git rev-parse:*), Write
---

# PR Triage

**Arguments:** $ARGUMENTS (PR number, or empty to auto-detect from current branch)

Produce a local `plans/planning/PR<N>-review.md` summarising reviewer comments, CI status, and pending actions. Do not post anything to GitHub.

## Step 1: Identify PR

```bash
gh pr view ${ARGUMENTS} --json number,title,url,state,isDraft,headRefName,baseRefName,headRefOid 2>/dev/null \
  || gh pr view --json number,title,url,state,isDraft,headRefName,baseRefName,headRefOid
```

If the PR is not found or is a draft, stop and tell the user.

Record: PR number, title, URL, head SHA (short: first 7 chars), base branch.

## Step 2: Check for existing review doc

```bash
ls plans/planning/PR<N>-review.md 2>/dev/null
```

If it exists, read it — the new doc will update it rather than start from scratch. Note its current Status line.

## Step 3: Fetch CI status

```bash
gh pr checks <N>
```

Classify each check as ✅ pass, ❌ fail, ⏭ skipping, or 🔄 pending.
Note any failures with their detail URL.

## Step 4: Fetch reviewer activity

Run all three in parallel:

```bash
# Formal reviews (APPROVED / CHANGES_REQUESTED / COMMENTED)
gh api repos/{owner}/{repo}/pulls/<N>/reviews \
  --jq '.[] | {state: .state, author: .user.login, body: .body, submitted_at: .submitted_at}'

# Inline code comments (review threads)
gh api repos/{owner}/{repo}/pulls/<N>/comments \
  --jq '.[] | {author: .user.login, path: .path, line: .line, body: .body, created_at: .created_at}'

# General issue comments
gh api repos/{owner}/{repo}/issues/<N>/comments \
  --jq '.[] | {author: .user.login, body: .body, created_at: .created_at}'
```

Filter out comments from `deanlorenz` (those are your own replies, not reviewer asks) and from `claude-code-bot` / any bot whose body starts with `<!-- claude-pr-review -->`.

## Step 5: Synthesise

For each non-Dean commenter, determine:
- **Formal review state**: APPROVED / CHANGES_REQUESTED / COMMENTED (from Step 4a)
- **Open threads**: inline comments not yet resolved (Step 4b). A thread is open if the reviewer has not replied with approval or the conversation has not been marked resolved.
- **Open questions**: general comments that end with a question and have no reply from Dean after them (Step 4c).
- **Answered questions**: general comments where Dean has replied.

Derive **Pending Actions**:
- Any CHANGES_REQUESTED review → action required
- Any unresolved inline thread → action required
- Any open question (no Dean reply) → action required
- No LGTM/APPROVED yet → note as "awaiting approval"

## Step 6: Write the review doc

If `plans/planning/PR<N>-review.md` does not exist, create it. If it does, update it in place — preserve any existing Discussion or Code Review Findings sections that were written manually.

The doc format:

```markdown
# PR #<N> Review Summary

**Status: DRAFT**

**PR:** [<title>](<url>)
**Head:** `<short-sha>`
**Reviewed:** <today's date YYYY-MM-DD>

---

## CI

<one bullet per non-skipped check with emoji>

---

## Review Status

<summary: APPROVED by X / CHANGES_REQUESTED by X / Awaiting approval — no LGTM yet>

---

## Comment Threads

<one block per reviewer with open/answered status and a 1–2 sentence summary of their ask and Dean's reply>

---

## Pending Actions

- [ ] <specific action required, one per item>

(omit this section entirely if there are no pending actions)

---

## Discussion

_[to be filled in with discussion before finalizing]_
```

Rules:
- Status stays DRAFT until explicitly set to FINAL.
- If all reviewers have APPROVED and there are no pending actions, note "No pending actions."
- If a reviewer asked a question and Dean replied and there has been no follow-up, mark it "(open, answered)" — it may still need a response.
- If a reviewer asked a question and Dean has not replied, mark it "(open, unanswered)".
- Inline threads: group by reviewer, list file path and 1-line summary of the ask.
- Do not quote full comment bodies — summarise in 1–2 sentences.
- Do not include Dean's own comments unless they are the only content (i.e., self-review).

## Step 7: Commit to plans branch

```bash
git -C plans add planning/PR<N>-review.md
git -C plans commit -m "planning: triage PR #<N> — <one-line status summary>"
```

Report the file path and a one-line summary of what was found (CI status, reviewer status, number of pending actions).
