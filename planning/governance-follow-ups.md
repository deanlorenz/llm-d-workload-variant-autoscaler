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
- `internal/engines/analyzers/throughput/constants.go:85` — `"the decode-dominated regime (N_pre ≈ 1,
  TA-supply.md §3.1)"`; a plans-branch Type-1 doc citation plus a section identifier, in a shipped
  production comment. (found via `ta-anchor-dynamic-refresh`'s §4a sweep, 2026-08-08)
- `internal/engines/pipeline/analyzer_helpers.go:411,:419` — `"Design § Architecture/D"` and `"per
  design A10"`. Same class. (found via `ta-anchor-dynamic-refresh`'s §4a sweep, 2026-08-08)

All four re-verified byte-identical between `ta-anchor-dynamic-refresh@6d55fbd7` and `upstream/main`
2026-08-08 — inherited, not any PR-2-family branch's to fix.

### Broken doc links on `main` (different defect class — not §4a tokens, found the same way)
- `cmd/main.go:165-169` — a comment links
  `https://github.com/llm-d/…/blob/main/docs/user-guide/configuration.md`, which does not exist
  (`docs/user-guide/` contains only `monitoring.md` and `sglang-backend.md`). A 404 shipped to users
  reading the source, not just an internal citation.
- `docs/developer-guide/throughput-analyzer.md:609` — `` [`saturation-scaling-config.md`](../saturation-scaling-config.md) ``
  resolves to `docs/saturation-scaling-config.md`, which doesn't exist; the real file is
  `docs/developer-guide/saturation-scaling-config.md`. Two-character fix (`../` → `./`). Verified still
  present at `ta-anchor-dynamic-refresh@6d55fbd7`, in a file that branch's own C9 dev-guide commits
  already touch — cheap to fold into whatever branch next edits that file's neighborhood, but not
  routed there as an action; recorded here so it isn't lost either way.

(found via `ta-anchor-dynamic-refresh` internal review, 2026-08-08; none of the six items above block
any in-flight PR — all pre-existing on `main`, surfaced incidentally by PR-2's §4a sweep)

---

## CODER-CONVENTIONS.md self-contradiction incidents (2026-08-13)

Different failure class from the scope-boundary incidents above: not an agent acting on a
document's mention without checking scope, but a doc's own **first-read shorthand contradicting
its own later correct instruction** — coders absorb the terse early version before ever reaching
the correct fuller one in the same file.

**(a) §0 modeled the forbidden `cd` pattern as the sanctioned handoff-write recipe.** §0's
"Why this matters" bullet read "Only need `cd ../plans/session/...` for status/handoff writes
(sanctioned exception per §1)" — directly contradicting both CONVENTIONS.md's "never use bare
`cd`... applies to all agents" rule and §1's own correct `cp`/`mv`-based exception three sections
later. Coders read §0 first, `cd` out of their worktree to write a handoff, and then had no
documented way back — `EnterWorktree(path: <absolute-path>)` can self-rescue, but nothing told
coders that. No prior stranding incident found on record; may have been happening silently
(informally rescued by Dean, never logged) or this is the first time it was named. **Fixed** —
§0 now points to `cp`/`mv` and states the `EnterWorktree(path: ...)` self-rescue explicitly.

**(b) §5.2 had no "split before naming" step, so mixed content defaulted to `sync__`.** Dean
observed (not visible on disk, since he corrected every instance before it could be audited)
that coders repeatedly drafted one combined handoff — CURRENT-update content plus a
planner/reviewer/sibling-facing question or decision — and named the whole thing `sync__`,
splitting it into two files (a correct `sync__` plus a `plan__`/trigger) only after correction.
All admitted they didn't know why they'd conflated the two. The `sync__` vs `plan__` *definitions*
were already unambiguous (verified by direct read); the gap was that nothing told a coder to
separate the thought before picking a filename. **Fixed** — §5.2 now opens with an explicit
split-first instruction before the two destination bullets.

Both fixes are stopgaps on the frozen `CODER-CONVENTIONS.md`, per
[`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) § Migration 1 — they fold into
that migration's M1.2 harvest as **relocated** (existing written rule moving, not new policy) when
it runs; don't re-derive them from scratch. Whoever runs M1.2 should treat this section, not just
the two files' current text, as the source for these two rules' history and rationale.

---

## Handoff-routing misroute — reported by the sender, not independently verified (2026-08-13)

**As told to the planner by Dean; the specific handoff file(s) could not be located in the current
`session/handoffs/` state to confirm forensically — recorded from his description, and he flagged that
his own recollection of the exact sequence may not be fully accurate.**

A planner session sent a planning-flavored handoff addressed with a bare topic/branch token (e.g.
`to: autoscaling-viz` or an equivalent filename prefix) intending to reach a **planner** working that
mission. A **coder** session on the same branch/topic claimed it instead — the recipient token named a
*topic*, not a *role*, and both a planner and a coder session existed for that same topic at the time.
Reported sequence of what went wrong, as three distinct failures rather than one:

1. **The `to:` field's ambiguity is the root cause.** A bare branch/topic name (the existing convention
   for triggers, per CONVENTIONS.md § Handoffs — `<recipient>__<topic>.md`, recipient = branch name) does
   not distinguish "the coder working this branch" from "the planner working this mission" when both
   exist. The sender needed the *planner*, but the addressing scheme only has room for a topic.
2. **The coder recognized the content was planning-flavored but still processed it as its own** — marking
   it `.WIP` rather than leaving it untouched for the actual intended recipient once the mismatch was
   apparent. Per CONVENTIONS.md's own state machine, only the addressed recipient should ever mark
   `.WIP`; recognizing a probable misaddress should have been a reason to leave the file alone and
   surface the ambiguity, not to proceed anyway.
3. **A planner separately moved a handoff to `.DONE` that it had not sent and was not addressed to it** —
   the coder's own outgoing handoff, mistaken for something the planner needed to close out. This is the
   same "never edit, `mv`, or `rm` someone else's pending handoff" rule already stated in
   CODER-CONVENTIONS.md §8 and CONVENTIONS.md's state-machine section, violated from the planner side
   this time rather than the coder side.
4. **Some senders correct their own handoff post-send, which is legitimate** as long as the file is not
   yet `.WIP` — but nothing in the current protocol distinguishes an author's own legitimate
   self-correction from a different session tampering with a file that isn't theirs. Both look identical
   on disk: the file's content simply changed.

**Disposition, corrected same day: partially patched now, not held for the redesign.** The addressing
half of the fix (declare identity explicitly rather than being addressed by a guessed name) turned out
small and additive enough to apply directly to `session/CONVENTIONS.md`'s status-file format rather than
wait — see that file's "Identity block — mandatory" text (added 2026-08-13), which every session now
maintains in its own status file: name, id, role, branch, worktree, owned doc, task, status-file path.
The remaining half — a **sync-maintained live-session index** built from these identity blocks, serving
handoff-routing resolution, stale/dead-session detection (including a peer-comparison signal: if the
cohort of live sessions, sync included, has recently checked in and one specific session hasn't, that is
evidence of a stuck session *now*, sharper than any fixed-age threshold), and a machine-optimized "state
of things" reference — is still design/build work, tracked in
[`atomic-step-protocol-design-addendum-3.md`](atomic-step-protocol-design-addendum-3.md) § Relationship to
other open items, owned by the same planner thread (`atomic-step-protocol-brainstorm`).

**The stated fix direction (Dean, 2026-08-13), not yet designed:** *"we need to make the handoff protocol
more robust... the TO field to express the role+task more than name. Can use name too after a
'conversation' starts and you get a reply. Must be short. Token waste is still a big problem."* I.e. the
addressing scheme should default to **role + task** (e.g. "planner, autoscaling-viz-panel3" rather than
just "autoscaling-viz"), with a concrete session/agent **name** usable once a reply has established which
specific session is on the other end of an exchange — and whatever the mechanism, it must stay short,
since the token cost of handoff overhead is an explicitly live concern independent of this incident.

Same underlying pattern as the CODER-CONVENTIONS incidents above in one respect (a governance/protocol
gap causing wrong handling that the affected sessions had no way to detect from inside their own scope)
but a distinct failure mode (addressing ambiguity across concurrent role/topic combinations, not a doc's
internal self-contradiction) — kept as its own section rather than merged.

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
