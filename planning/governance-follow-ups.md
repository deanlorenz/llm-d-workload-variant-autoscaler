# Governance & Process Follow-ups

**Status:** LIVING backlog (extracted from `session/CURRENT.md` § Next steps 2026-07-30 to keep
CURRENT.md bounded). These are process/governance TODOs that are **not yet actioned** and have no
other permanent home. When one is designed/applied, record the outcome here and drop the item.

Ownership is itself open — see candidate direction (3): who may edit `session/CONVENTIONS.md` is
currently unassigned in the doc-ownership table.

---

## Repeat scope-boundary incidents (2026-07-14, 2026-07-26, 2026-07-27, 2026-07-29)

Common underlying pattern: an agent acts on something a document *mentions* rather than checking
scope first, even though CONVENTIONS.md already states the principle in prose ("documents describe
what should happen; scope boundaries govern who does it").

### 2026-07-14 — reviewer-worktree
A reviewer ran `git stash` + `git checkout` directly in a coder's active worktree for a lookup that
had a read-only answer (`git show <rev>:<path>`); state was recovered byte-identical, but Dean wants
a *gate*, not another prose reminder.

### 2026-07-26 — PR C unauthorized subagent
The `ta-model-level-demand` (PR C) coder read its Type 3 plan's "PARALLEL FACT-FIND ... launch as a
read-only research agent" line and called the Agent tool immediately, without asking — the plan's
mention of a parallel task was misread as an instruction addressed to the coder itself. The spawned
agent also malfunctioned (permission hooks blocked its file reads as if it were bound by the coder's
own worktree-scope rules). Dean stopped the coder mid-session; ~17 minutes/tokens wasted.
Root cause + fix already applied: (a) the plan-doc phrasing was rewritten (`9684c867`) to explicitly
disclaim coder action; (b) a doc gap was identified — neither CODER-CONVENTIONS.md §7 nor §8 mentions
"spawning a subagent via the Agent tool" as an action category at all (both are framed around file
writes / git verbs / GitHub actions); (c) feedback memories were saved
(`feedback_coder_no_unauthorized_subagents`, `feedback_plan_doc_no_other_role_actions`).

### 2026-07-27 — PR C silent formula-semantics fork (related but distinct, same session)
While fixing a genuine, adjacent bug (model-level `avgOL` was reading live per-cycle data instead of
tracked `WorkloadShape`, reintroducing an EPP-warm-up regression), the coder also changed the
plan-specified formula's *weighting semantics* — a RequestRate-weighted average across all replicas
became an unweighted mean across non-prefill variants — and documented only the data-source fix, not
the weighting change. It surfaced only because the reviewer re-derived the formula by hand against the
plan's literal wording (review: `planning/ta-model-level-demand-review.md` F1). Existing memory
`feedback_doc_accuracy_discipline` already states the general rule ("design evolution is normal —
elevate forks early"); this is the first concrete coder-side violation of it. CODER-CONVENTIONS.md has
no rule covering "your bug fix also changed a plan-specified formula's output for an input class the
plan's examples didn't cover — flag that as its own decision point, not folded into the bug-fix
narrative."

### 2026-07-29 — PR C §4a leaks (prevention + detection both failed)
PR C shipped **14** §4a plans-branch-identifier leaks in code comments / test descriptions
(`decision #1`, `review finding F1`, `§Tests 1-4`, `TA-demand §3.3/§3.5`, `TA-supply §5.5`, bare
`F1`), introduced across two logic commits and found only on a manual round-3/4 re-scan (fixed in
`b2acffd6`). Root cause has two halves: **(prevention)** §4a is violated by *transcription* — the
coder copied plan/review sentences (which correctly use the identifiers) into code comments verbatim;
§4a is a vigilance rule with no gate (compiles, passes gofmt/lint/test/DCO). **(detection)** failed at
all three eyeball stages: coder pre-push checklist has no §4a step; reviewer rounds 1–2 scanned only
dev-guide text, not code comments / `It(...)` strings; round-3 grep was too narrow (7 reported vs 14
actual). This is the **4th** PR-C convention slip caught only by manual re-derivation. **Concrete
remedy (one mechanical gate):** grep the diff's added comment/test lines for

```
decision #|Decision #|review finding|\bF[0-9]\b|plan §|TA-[a-z]+ §|planning/|-plan\.md|-review\.md
```

— add to both the coder pre-push checklist and the reviewer checklist (reviewer grep must cover code
comments + `It`/`Describe` strings, not just dev-guide text). Same structure as
`feedback_semantic_pivot_grep`.

Consumed handoffs for the above: `plan__review-agent-worktree-incident-and-gates.md` (07-14),
`plan__coder-conventions-subagent-gate.md` (07-26), `plan__review-4a-gap-and-highlight-default.md`
Item 1 (07-29).

### Pre-existing `main`-side §4a leaks (backlog, from PR C round-4)
Untouched by PR C — introduced by #1250 `efca1b4c`. Fold into the TA-forward-plan §4a/dev-hygiene
backlog or clean via a standalone one-line PR:
- `docs/developer-guide/throughput-analyzer.md:671` — `Design: plans/planning/TA-Plan.md…`
- `internal/engines/analyzers/throughput/analyzer_test.go` — `Regression test for F1…` (~:982),
  `Specs 1–5 from plan §3.4` (:1189)

---

## Reviewer-highlight default (Dean's request 2026-07-29)

A second requirement for the proposed `REVIEWER-CONVENTIONS.md`. Dean liked the round-4 close-out
format and wants it to be the **default deliverable for internal code reviewers**:
(a) a **change highlight** — per-commit table (commit → one-line what → type: logic / comment-only /
doc) plus an explicit list of what was left out of scope and why;
(b) a **critical section** — the smallest region of shipping code that carries the PR's actual
behavior, shown inline so the verdict is legible without reopening the diff.
Applies to the FINAL / ready-to-push close-out, not every interim round.
(Consumed handoff: `plan__review-4a-gap-and-highlight-default.md`, Item 2.)

---

## Plan-authoring process note (from A′ review, not yet actioned)

The coder found 3 pre-existing tests broke on the `effectiveEnabled` behavioral-contract change
because their fixtures relied on "absent config entry defaults to enabled" as a shorthand for "just
use defaults" — none were in the plan's declared file list, only found because the coder searched
broadly. Suggests the semantic-pivot-grep step (CONVENTIONS.md, per-task rule) should widen to
`grep -rl` across all `_test.go` files for the changed function/default, not just the files being
edited, for any future behavioral-contract-change plan. Not yet folded into CONVENTIONS.md — same
ownership question as candidate direction (3).

---

## Candidate directions to evaluate (not yet designed)

1. **Mechanical enforcement** via a PreToolUse-style hook / `settings.json` permission rule — for
   07-14, blocking `git stash|checkout|reset|rebase|merge` when CWD ≠ the session's declared
   worktree; for 07-26, gating Agent-tool calls from role-scoped sessions pending explicit
   confirmation. `update-config` skill is the likely entry point for both.
2. **A `REVIEWER-CONVENTIONS.md`** with its own pre-action checklist, mirroring `CODER-CONVENTIONS.md`
   (would also host the reviewer-highlight default above).
3. **Clarify who may edit `CONVENTIONS.md`** itself — currently unowned in the doc-ownership table
   (open since 07-14, still open). Gates directions (2), (4), (6), (7).
4. Add an explicit "coders/reviewers never spawn subagents without asking first, even when a document
   mentions launching one" rule to CONVENTIONS.md (not CODER-CONVENTIONS.md only, since the principle
   applies to every role) — exact wording TBD by whoever owns the edit, pending (3).
5. Name a concrete safe pattern for "run code at a historical revision" (temp worktree/clone) so it
   isn't improvised under pressure again.
6. For the 07-27 formula-fork instance, mirror the existing semantic-pivot-grep rule structure —
   require the coder to flag, as its own decision point, any implementation change that alters a
   plan-specified formula's output for an input class the plan's own examples didn't cover.
7. Add the §4a mechanical grep (see the 2026-07-29 incident) to both the coder pre-push checklist and
   the reviewer checklist — a single deterministic gate that would have caught all 14 leaks the first
   time.
8. Add the reviewer-highlight default (change-highlight table + inline critical section) to the
   proposed `REVIEWER-CONVENTIONS.md`.

---

## Retrospective open question (F merged 2026-07-30)

Was the F coder's 2nd unprompted §4a commit-message history-rework (`reset --soft` + recommit, tree
byte-identical) an acceptable extension of the earlier approval? Undecided.
