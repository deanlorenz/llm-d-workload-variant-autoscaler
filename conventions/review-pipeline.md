# Review pipeline

### convention: review-pipeline
description: Four-stage review pipeline (scope, checkers, intent, merge-and-rule) with a pluggable stage-1 checker contract.
scope: review agent running or requested to run a review
trigger: running or requesting a review of a PR/branch
status: active
origin: session/CONVENTIONS.md § Document Taxonomy, Type 6 — review pipeline (C9)

**Type 6 — review** (`planning/*-review.md`, e.g. TA-TA3-review.md)
Output of the /design-review skill. Documents implementation correctness findings: bugs, doc
gaps, NTH items, and confirmed-correct items. Scoped to a branch or design doc. Carries a
`Status: DRAFT` header until the user finalizes the findings in discussion; only `Status: FINAL`
docs are ready for consumption by the plan agent. Never write to a `*-review.md` file unless
you are acting as the review agent.

#### Review pipeline — four stages, with a pluggable checker slot

The stages are fixed; **stage 1 is a set, so new capabilities plug in without changing the pipeline.**

| Stage | What |
|---|---|
| **0 — scope** | Read the Type 3, the commit list, and the diff boundaries. Establishes what the PR *claims*. |
| **1 — check the code** | Run every available **checker** (see contract). Produces defect *candidates* with no knowledge of intent. |
| **2 — understand intent** | Plan-vs-diff, commit-message-vs-diff integrity, §4a token scan, DCO, gate results, golden-file scope, deletion classification. Only the review agent can do this. |
| **3 — merge and rule** | For each stage-1 candidate decide: real and in scope, real but backlog-not-blocking, or refuted. Survivors become numbered Findings in the Type 6 doc. |

**Checker contract** — anything satisfying this may be added to stage 1, and adding one changes
nothing in stages 0, 2 or 3:

- **read-only**: no working-tree writes, no GitHub writes, no git write-verbs
- emits findings as *(file, line, claim, concrete failure scenario, verdict)* — a claim with no
  failure scenario is speculation and does not enter stage 3
- independently skippable: an unavailable checker degrades coverage, never blocks the review
- carries no authority: a checker reports, the review agent rules

Current checkers: the built-in **/code-review** skill, run at `high` or `max`. Breadth is wanted
here — it admits uncertain findings, which is correct precisely because stage 2 filters on intent that
the checker cannot see. **Never pass `--comment`** (posts to GitHub) or **`--fix`** (writes the working
tree); either breaks the review agent's read-only boundary. Candidates for later: Go pitfall and
idiom checks, reuse/duplication against imported modules and the standard library, security review.

The coder may run the same checkers on itself before signalling push-ready, and *may* use `--fix`
there since it owns its worktree — see CODER-CONVENTIONS.md §5.4. That is a self-check, not a
review; it does not substitute for stages 2–3.

### convention: review-pipeline-coder-self-check
description: Before signalling push-ready, a coder runs the same stage-1 checkers on its own diff and may use --fix, then files a review trigger.
scope: coder whose commits are complete and all gates are green
trigger: about to signal push-ready
status: active
origin: session/CODER-CONVENTIONS.md §5.4 Internal review request before push-ready (CC16)

**5.4 Internal review request — before signalling push-ready.**

When your commits are complete and all gates are green, write a review
trigger **before** sending the push-ready `sync__` handoff:

```
plans/session/handoffs/review__<branch>-ready.md
```

Format — same trigger shape as §5.3 (to / reason / refs / note):

```
to: review
reason: code-review-before-push
refs:
  - <branch>/ (worktree)
  - planning/<branch>-plan.md
note: <N> commits on <base>@<sha>; all gates green
```

The plan-agent sees the trigger and invokes /code-review on your
branch before authorising the push to origin. Do **not** write the
push-ready `sync__*.md` handoff until the review is complete and any
blocking findings are addressed (or explicitly accepted by Dean).

This applies to all PRs, including rebases that produce a materially
different diff. Routine rebase-only pushes (no logic change, no new
commits) are exempt.

**Self-check before you signal.** Before writing the review trigger, run the
stage-1 checkers on your own diff — currently the built-in /code-review
skill (see CONVENTIONS.md § Review pipeline). You own your worktree, so
you **may** use `--fix` here; the review agent may not. Two rules:

- **Never pass `--comment`** — it posts to GitHub, which no coder may do.
- **Fix or account for every finding before signalling.** If you disagree
  with one, say so in the trigger's note or your status file with the reason.
  Silently leaving a known finding for the reviewer wastes the round.

This is a self-check, not a review. It cannot see your plan, so it says
nothing about whether the diff matches it — that is stages 2–3, and it is the
review agent's job. Passing the checkers is not push-readiness.
