# Addendum 14 — what "role" actually means here, and the non-functional requirements

**Status: Dean's own definition, 2026-08-17. Reframes Addendum 13's build order — supersedes its
implicit "multi-agent-team scoping" framing, does not discard its per-role inventory.**

## At a glance

**Mission:** define "role" precisely before building any kernel — the term was overloaded, and
Addendum 13's research (correctly) surveyed existing material but implicitly framed roles as
multi-agent-team scoping. Dean's actual framing is different in kind: roles are a **solo-session
discipline mechanism**, relevant even with one session running, inspired by Bob's static modes and
Claude Code's own Plan mode — not a team-coordination problem.

**Approach:** capture Dean's definition and every non-functional requirement verbatim, organized so
the eventual role-kernel design can be checked against them line by line. No kernel content written
here — this is the frame Addendum 13's build order must be re-read against, not a replacement for its
per-role inventory.

**Needs you:** confirm this framing is captured correctly before Addendum 13's build order proceeds —
several of its findings (tool allowlists, hooks, MCP) may need re-scoping once "roles are not
team-coordination" is applied.

**Checklist:**
- [ ] Re-check Addendum 13's build order against this framing — does "build sync first" still make
  sense once roles are understood as solo-session modes rather than team-member scoping?
- [ ] Design the non-functional requirements below (observability, traceability, token-saving,
  Bob-integration, ease-of-use) as their own thread — they are not role-kernel content, but they
  constrain how any role kernel gets built and surfaced.
- [ ] Decide whether the benchmark-coder's non-standard scope (external commands, not a worktree-only
  coder) becomes its own role or stays a documented coder exception.

---

## What "role" means — Dean's definition, verbatim

*"Roles are not team members. Almost orthogonal. Roles are relevant even with a single active
session. The goal is to create a defined 'mode of work' with precise scope and structure. It started
as a mechanism for context switching for me. Making sure I scope each session. I wanted to make sure I
use each session optimally, not overstepping boundaries. The inspiration is Bob modes, but these are
fairly static. The closest thing in Claude may be the 'Plan' mode."*

**Consequence for the design:** a role is not "which agent does this work" — it is "which mode is this
*session* in right now, and what does that mode permit/forbid." Multiple sessions in the same role is
not a coordination problem to solve; one session in one role at a time is the actual unit. This directly
reframes several of Addendum 13's research findings, which (correctly, as research) surveyed
multi-agent-team patterns (task partitioning, agent-to-agent messaging, shared task lists) — those
remain useful, but they are not what "role" is *for* here.

**The taxonomy already does the real work.** *"The taxonomy already defines scope well. Clear inputs
and outputs. Clear ownership. If we just follow the taxonomy then we are in good shape. Rarely step on
other sessions. Rarely have any conflicts."* Roles are downstream of the artifact taxonomy
(`doc-and-session-model.md` § Artifact types), not a separate scoping system layered on top of it.

**`CONVENTIONS.md`/`CODER-CONVENTIONS.md` are the best reference, not a fossil to replace wholesale.**
*"The existing CONVENTIONS are the best ref. They already capture many per-role boundaries. The
CODER_CONVENTIONS were extracted from CONVENTION when the file became too big. They define what a
coder does and how it should behave."* The harvest (Phase 6) relocates this content into `conv:`/
`role:` destinations — it does not need to reinvent the boundaries, which already exist and work.

## Safety rules — where they actually are, and where they are not

**Coder is the one role with real safety rules, and they are narrow.** Worktree confinement is the
core one: no push, no GitHub post, no writing outside the worktree, no external commands. *"The main
one is that coders work in worktrees. They never try to do anything out of that box."*

**One coder-shaped exception already exists and needs a decision:** *"the benchmark tester/coder...
is not really a coder and should maybe have its own role"* — it runs external commands (cluster
operations, load generation) that a normal coder's worktree confinement would forbid. Not resolved
here — tracked in the checklist above.

**Every other role has almost no safety rules.** *"There are almost no safety rules for any other
roles. They work on the same worktree and do what they like. The main safety is that each has very
specific documents it owns (which are tied to its role). Conflicts are rare but happen. I try to
prevent them by not assigning overlapping tasks (not by roles)."* — conflict avoidance today is
Dean's own task-assignment discipline, not a role-enforced mechanism. Any future automated conflict
prevention (e.g., a real `role:` lock) is additive on top of this, not a replacement for it.

**Cross-role global safety rules exist and are NOT role-specific.** *"No GH without EXPLICIT
permission, never push anything upstream, no push without permission, extra check for push to an open
PR branch, etc."* These belong to the standing/kernel-vs-convention question already open in
`atomic-step-protocol-design-addendum-4.md` (the "posture vs. checklist" question, concretely C44) —
Addendum 14 confirms these are cross-cutting, not per-role, which is evidence toward resolving that
open question, not a resolution of it by itself.

## Mechanism preferences — narrow tool allowlists, hooks, and subagent types

**Tool allowlists are probably too hard to maintain, in principle not objected to.** *"Tool allow
list[s] are probably too difficult to maintain. I do not object to the principal. Coders and verifiers
must be able to work in full auto mode. Their boundaries are clear. Other roles I usually run in auto
mode too — it seems to work fine. (the problems I have with my context disappearing in the scrolled
text is not role-specific.)"* Read: broad auto-mode is the working default; allowlists are a
maintenance cost Dean is skeptical of, not a mechanism he's asking to be built out per role.

**Hooks are overkill except for a few very specific global points.** *"Hooks are overkill in most
cases. I only want them to enforce very specific points — e.g., some global safety rules. Not role
specific usually."* Directly narrows Addendum 13's "use hooks for conditional logic" recommendation —
hooks are for the cross-role global rules above, not a per-role enforcement layer.

**Only 3 subagent types matter in practice: coder, verifier, fact-finder.** *"I mostly use only 3
types (coder/verifier/fact-finder). Coder is the problematic one and should live in a worktree. Others
are usually harmless (only read and produce one report file)."* This is a much smaller surface than
the 11-role taxonomy's own list — the 11 roles are what a *session* can be; these 3 are what a
*subagent* actually is in practice. The two lists are not the same thing and should not be conflated
in the design.

**Task partition is role focus, and may need work as parallelism grows.** *"Task partition — that is
the role focus. Now that I run multiple instances of each role I may need better task partition.
However, most roles are already bound clearly to a specific topic and/or task."* Consistent with "role
is a mode, not a team member" — partitioning is by topic/task, roles just happen to already imply
reasonable boundaries most of the time.

**Agent-to-agent messaging: works better than expected, not blocking.** *"Would love if it works. my
handoff channels work better than I expected (with some problems). Can improve, willing to use
existing mechanisms, but not something blocking at this point."* File-based handoffs are the proven
mechanism; `SendMessage`/cross-session messaging stays a "nice if it works" track, not a dependency.

**Shared task lists: shared list, unshared ownership, and it's already a chain.** *"lists are shared
but ownership of lists is not. Coders follow a 'task list' in a spec. planner create specs by following
epics. designers create epics following type 1, etc."* This describes the flow diagram in
`doc-and-session-model.md` § Flows precisely — worth cross-referencing rather than treating as new.

**"Role" as a literal field: yes, in name and handoffs.** Direct confirmation that role should appear
in a session's own display name and in handoff `to:`/`from:` addressing — matching the direction
already recorded in `doc-and-session-model.md` item 5 (2026-08-16, `<topic/task>-<role>` identity) and
Addendum 12 (the note-candidate mechanism's routing). Not a new requirement; a confirmation of one
already tracked.

**Tool permissions/hooks: minimal now, wants control eventually, tracking usage patterns as the
path there.** *"Eventually I would like control. Enforce behavior (e.g., I don't like sed -i, yet
every session tries it, I don't like cd, yet every session tries it, I want git -C but agents forget,
...). Right now I can't control this, whitelisting is too much to handle. I black list extreme cases.
Hope Claude does a good enough job. I may try to track tools to classify usage patterns. Bottom line:
minimal tools permissions and hooks. revisit later."* Three concrete, named recurring violations
(`sed -i`, bare `cd`, forgetting `git -C`) — these already have global rules against them
(`feedback_no_inplace_edits`, `feedback_no_cd_sibling`, worktree-scope conventions), so the gap isn't
"no rule exists," it's "the rule isn't mechanically enforced and sessions keep tripping on it anyway."
A usage-pattern-tracking mechanism is a real, deliberately deferred idea — not designed here.

**MCP servers: acknowledged unknown, not a requirement.** *"don't know enough about this."* Not a gap
to close in this design pass.

## Non-functional requirements

1. **Interop with other AI agents, specifically Bob.** Bob must be usable as a valid background coder
   (already reasonably safe — worktree-confined) and should take on mechanical/automation work
   (summaries, rephrasing, message analysis) that currently has no home. *"It is now an underutilized
   resource that I have many free tokens for."* This is a real, named gap — none of today's mechanical
   work (Tier-1/Tier-2, the note-candidate capture from Addendum 12, triage's CI/comment fetching) is
   currently offloaded to Bob, and per Dean it should be.
2. **Portable to another GitHub project.** *"(almost) nothing specific to this project."* Anything
   built should default to project-agnostic; project-specific detail is the exception, marked as such
   — matches the existing `(WVA-specific)` marker convention already used in `CODER-CONVENTIONS.md`
   per `project_role_specific_conventions` memory.
3. **Observable.** Token counts, what's currently happening, who's alive. Directly the same gap
   Addendum 12's "discovery/alert" checklist item names, and the same gap this session hit today
   (checking `claude agents --json` by hand, repeatedly, to find blocked/stale agents) — not a new
   requirement, a confirmation that it's a real, recurring pain point worth designing for properly
   rather than ad hoc.
4. **Traceable.** "How much work did I do the past month. Proof of work." Not yet designed anywhere —
   no existing mechanism answers this; closest analog is `session/history.md`'s append-only ledger,
   but that is per-mission narrative, not a work/output accounting.
5. **Token-conscious, especially for parallel work.** Local tools, best-model-per-job, use Bob, stop at
   a limit. Directly the same concern as `atomic-step-protocol-design-addendum-11.md` (token
   accounting is a standing requirement) — this generalizes it: not just "record what was spent" but
   "actively choose cheaper paths (local tools, Bob, the right model) and have a hard stop."
6. **Easy to use, given how Dean actually works today.** Jumps between session editors; the VSCode
   "open editors" panel does most of the "which session needs me" job already, but *within* a session
   it's harder — text can scroll past unseen, especially in auto mode. **Direct restatement of the
   rule already established today in this very conversation**: *"all information, answers to
   questions, open items, checklists, etc. need to be in a doc I can follow. Important/high-priority
   items need to be very clear and navigable. I can answer in the prompt. Claude can edit the doc —
   mark items done, record my answer, etc."* This is not a new requirement — it is Dean re-stating,
   in his own words, the exact correction he gave earlier in this session ("correct form is a doc I
   can review, not endless prose in session") as a standing non-functional requirement for the whole
   role design, not a one-off style note.

## What this changes about Addendum 13

Addendum 13's per-role inventory (what already exists, what's missing) stays valid — it is a correct
survey regardless of framing. What changes is the *build order's* justification and the *external
best-practices* section's relevance:

- Addendum 13's external research (tool allowlists, task partitioning, agent-to-agent handoff) answers
  "how do I scope a multi-agent team" — useful background, but per this addendum, **not the actual
  problem roles solve here.** Do not over-index on those patterns when writing role kernels.
- The build order in Addendum 13 (sync → coder → triage → confirm+verify → epic+spec → designer → pr
  → policy-writer) was justified by "richest existing material first." Under this addendum's framing,
  a role kernel's job is narrower and cheaper than a full multi-agent scoping design — it's a **mode
  switch document**, closer to how `EnterWorktree` or Plan mode work than to a subagent permission
  boundary. This may mean the order can be more aggressive (several roles built in one pass) since the
  actual content per role is smaller than Addendum 13 assumed. Not decided — flagged for the checklist.
- The non-functional requirements above (especially #6, doc-not-prose) are not role-kernel content at
  all — they are requirements on *any* output this design produces, including this very addendum.
