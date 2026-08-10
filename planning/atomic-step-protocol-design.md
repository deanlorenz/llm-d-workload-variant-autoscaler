# Atomic-Step Execution Protocol

**design** · **Status: FINAL — frozen 2026-08-10 by Dean.**

Frozen means the design is settled and governs: reopen only for architectural replanning, and amend
through an explicit addendum rather than editing. § Decided, do not re-litigate is binding. Open items
in § Open and parked are genuinely open — freezing the design does not close them.

Implementation has **not** started. What exists: this design, its companion
[`doc-and-session-model.md`](doc-and-session-model.md), and `scripts/session-extract.sh` with the
checkpoint mechanism. Migration 1 — the tooling, the harvest, the coverage audit — is unbuilt.

Supersedes the **repeating-rules half** of [`micro-rules-design.md`](micro-rules-design.md) (the
`rules/` + `INDEX.md` mechanism, never built). That document's **fetch-protocol half** — Reading
Protocol, TOC, and `scripts/toc-refresh.sh` — has landed and survives, amended by § Addressing and
fetch below.

*(That document calls those halves its "Type 1" and "Type 2". Those numbers are local to it and have
nothing to do with the document taxonomy in [`doc-and-session-model.md`](doc-and-session-model.md) —
which is one more reason the numbering is being retired.)*

---

## Reading Protocol

This document is addressed by section. Read this protocol and the TOC, then fetch only the
sections you need — by anchor link, or by extracting the heading's section from the file.
(In Claude Code: `scripts/sec.sh` once it exists, or `Read` with a bounded range.)
There are deliberately **no line numbers** in the TOC; see § Addressing and fetch.

---

## TOC

- [Intent](#intent)
- [The inversion](#the-inversion)
- [Layer model](#layer-model)
- [The step](#the-step)
- [Document shape](#document-shape)
- [Addressing and fetch](#addressing-and-fetch)
- [Micro-conventions](#micro-conventions)
- [Coder state](#coder-state)
- [Roles and session modes](#roles-and-session-modes)
- [plan-lint](#plan-lint)
- [Auto mode](#auto-mode)
- [Enforcement](#enforcement)
- [Portability](#portability)
- [Consequences for existing artifacts](#consequences-for-existing-artifacts)
- [Migration](#migration)
- [Decided, do not re-litigate](#decided-do-not-re-litigate)
- [Open and parked](#open-and-parked)
- [Provenance](#provenance)

---

## Intent

**Goal.** A coder agent that follows a plan step by step, in auto mode, launchable as a plain
shell/CLI session (Bob or Claude), that never improvises an action the plan did not specify, and
that carries so little standing context it cannot forget the rule that binds the step it is on.

**Dean's constraints, as given:**

1. Coders are simple. They follow a plan. They do not take actions they *think* or *presume* Dean
   wants.
2. Coders run in auto mode (no per-operation prompting).
3. Coders launch as a shell/CLI session from their worktree, not only from a webview.
4. **If a coder has no rule for a step, it does not run the step.** The spec owner lays down the rules
   per step.
5. Each step is short to read — small standing-context cost, and immediate context for that step.
6. Each step is atomic enough that the coder cannot forget it mid-step. This is where careful
   planning pays off.
7. The coder records its state and memory between steps.
8. **No existing rule is lost.** Every rule in `CONVENTIONS.md` and `CODER-CONVENTIONS.md` exists
   because Dean either encountered the bad behavior or set out to prevent it. That some future coder
   never exercises a rule says nothing about the rule — absence of exercise is not absence of need.
   Two distinct operations, not to be conflated:
   - **Migration** — a rule moves to a new home and keeps binding. Needs verification that it
     arrived, not approval. This is the whole of Migration 1.
   - **Removal** — a rule stops existing. Only reachable after **long probation**, and **only Dean
     approves it**, per rule.

**Why the previous approach failed.** Two failure modes were already diagnosed (see
[`micro-rules-design.md`](micro-rules-design.md) § Problem and memory `coder-enforcement-direction`):

- **Mode A** — enumeration gap: a step absent from the plan simply does not happen.
- **Mode B** — judgment substitution at a gate: the coder runs the gate, sees failures, and
  rationalizes them as acceptable. An early strict rule read at session start loses to three hours
  of accumulated "basically done" context.

Adding prose to the conventions made Mode B worse: longer documents, more diluted rules. The fix is
not more text — it is injecting the rule **at the moment it binds**, and removing the surface on
which judgment gets substituted.

---

## The inversion

Today a coder holds a **rulebook** and reads a plan. Under this design a coder holds almost nothing
and executes **work orders that carry their own rules**.

That flips the default at the point of missing guidance:

| | Missing guidance means |
|---|---|
| Today | improvise (Mode B) |
| This design | **halt and ask the spec owner** |

Constraint 4 is only enforceable if *"do I have a rule?"* is a **missing field**, not a judgment
call — judgment under context pressure is precisely what fails. Hence the step schema in § The step.

---

## Layer model

Three layers. Each is small, and each has one job.

**1. Role kernel** — `roles/coder.md`, holding only what cannot be per-step. A **new file under a new
name**, not an edit of `session/CODER-CONVENTIONS.md`: the old file stays frozen where it is so an
old session keeps loading exactly what it loaded before, and the filename alone tells you which
regime a session is in (§ Migration). Nothing is deleted from the old file by creating this one.
Its most important content is *expectation-setting*: the coder must expect a convention for every
step and halt when one is absent. Plus the standing prohibitions (never leave your tree, no
push, no GitHub writes, no `CURRENT.md`), how to record state, and: **finishing your assigned range
means stop, not continue into unassigned steps.**

**2. Micro-conventions** — `conventions/` (see § Micro-conventions). Fetched by name, at the moment
of need, never loaded standing.

**3. Steps** — the executable units, living in the code spec (see § The step, § Document shape).

**Consequence — the rulebook mostly redistributes.** Walking the current `CODER-CONVENTIONS.md`:
§1 worktree scope becomes the step's `scope:` field; §3 tests becomes `verify:`; §4 dev-guide
becomes a step; §5 status becomes `record:`; §9 templates become micro-conventions. What is
irreducible is prohibitions + halt + record. That is the kernel, and it is small.

**Consequence — coders load neither `CONVENTIONS.md` nor `CURRENT.md`.** A coder's context is the
kernel plus its own plan. `CURRENT.md` is a ledger and calendar, not a trigger for action; coders
have no reason to read it. This is also the real answer to the "coders load no coder conventions"
defect recorded in [`context-cost-reduction-plan.md`](context-cost-reduction-plan.md) § Defect 2:
not *route the 5.6k-token rulebook into worktrees*, but **coders need almost none of it** — the
rulebook was compensating for plans that did not carry their own rules.

---

## The step

### Two layers per step

A step is split by *when* its content is needed, not by who reads it:

- **Brief** — intent, decisions made, rationale, expected hazards. Short. Read as orientation,
  before execution, for every step in the assigned range.
- **Detail** — pre-checks, exact commands, file lists, post-checks, the rule manifest. Fetched
  **only** when that step is actually executed.

Dean's worked example is a rebase: *"idea and intent are clear, expected and potential conflicts are
clear — but only when the coder actually does the rebase should it list the files, run the
interactive rebase, and check the list at the end."* Intent up front; mechanics at execution.

The briefs are what preserve the **surrounding narrative**, which must not be lost. A coder that
understands only its current step cannot tell when the plan has stopped matching reality.

### Step schema

```
## S07 — <imperative title>
brief:      intent · decisions made · rationale · expected hazards   (3–5 lines)
scope:      <paths this step may write — the only ones>
do:         <2–6 imperative lines; closed actions, no alternatives, no goals>
conventions: <manifest with triggers, or the literal `none`>
verify:     <exact commands + expected result>
done_when:  <observable predicate>
on_fail:    halt
record:     <what to append to the step log>
```

`do:` states **closed actions**, never goals. Over-reach originates in goal-shaped steps ("make the
tests pass") because a goal leaves a gap that gets filled with presumption. `do:` plus `done_when:`
leaves no gap.

### Rule manifest, with triggers

Rules are **linked, not inlined**. Inlining makes steps long, and long steps get forgotten — which
is the failure mode being designed against. The round trip is not waste: it is the mechanism, because
it places the rule in the most recent position in context exactly when it binds.

Each entry carries a **trigger**, so a step does not pull conventions that never fire. The field names
the noun, so entries carry only trigger and name:

```
conventions:
  BEFORE commit → commit-dco
  IF you delete → code-deletion
  AFTER rebase  → rebase-post
```

A convention that fires on *every* commit belongs in the kernel's manifest, not in each step: the **link**
is standing, the **fetch** is per-commit. Zero per-step text, freshness preserved.

### `conventions: none` is a legal value

`conventions:` must be **affirmatively stated**. Omission → halt. The literal `none` → proceed.

Without this, steps that genuinely need none ("add this test case") force the spec owner to invent
ceremonial conventions, and within a week the coder learns to read a missing field as meaning `none` —
which silently retires constraint 4.

### Step size

One step = one commit; smaller commits are better. Read-only steps (a grep audit) produce a step-log
entry and no commit.

Bound step size by **tool calls, not lines** — roughly 5–15. A fifteen-line step that takes forty
tool calls forgets itself regardless of how short it reads.

### Re-read before declaring done

The coder re-reads its step section before writing the step-log entry. One fetch, and it puts
`verify:` and `done_when:` in the most recent context at exactly the gate where Mode B strikes. This
is the cheapest available anti-rationalization measure.

---

## Document shape

The code spec has **two audiences and one source**. No new document type: the clean
session-role ↔ document-type relationship ([`doc-and-session-model.md`](doc-and-session-model.md) —
each role with clear
inputs it follows and outputs it owns) is worth preserving.

Audience separation is a **physical divide**, not a tagging scheme:

```
## Intent                    ← Dean, plan-confirmation, external review, code-verification
## Step index                ← the briefs, in order: the narrative
──────────── execution detail below ────────────
## S05 — <title>             ← coder, at execution
## S06 — <title>
```

- **`## Intent` is a bounded review surface** with fixed fields: `intent`, `current call stack`,
  `planned call stack`, `new components`, `new conventions`. Plans have become too long to review fully;
  a fixed field list makes review bounded rather than diligence-dependent. Note the symmetry — the
  step schema bounds the coder's judgment, the intent schema bounds Dean's review.
- **`new conventions:`** declares which micro-conventions the plan relies on or introduces. This
  closes constraint 4 mechanically: a plan citing a convention that does not exist fails `plan-lint`
  at authoring time, so a runtime halt for a missing one becomes rare — and therefore meaningful.
- **`## Step index` is contiguous**, so one fetch gets the whole arc. No second artifact, hence
  nothing to keep in sync and nothing to drift.
- **The TOC is a reference, not a reading outline** — a lookup table for finding a section, not an
  instruction for what to read. The reading outline is the Reading Protocol plus the coder's entry
  point.
- **The coder's entry point is explicit**: read `## Intent`, read `## Step index`, start at your
  assigned step.
- Rule *bodies* never appear in a plan — only links. So the code-verifier reading intent, briefs and
  details never has to skip past convention text; the divide falls out for free.

This document is a design doc, so the divide does not apply to it — it applies to code specs.

---

## Addressing and fetch

### Headings are the markers

A section is addressed by its heading:

```
### convention: commit-dco
```

which is simultaneously a human-visible section, a GitHub anchor (`#convention-commit-dco`, so cross-doc
markdown links work in the browser), and a grep/awk target. Extraction is "from this heading to the
next heading of the same or higher level" — no end sentinel, no extra syntax, nothing to sync.

Invisible HTML-comment sentinels were considered and rejected: they are not anchor targets and not
human-readable.

### No line numbers

Line numbers are a **global index over a mutable document**: any insertion invalidates every range
below it, so editing is O(whole document) by construction, and a stale range silently mis-points.
Heading-addressing removes the need for them entirely.

Line ranges are therefore retired **across the whole plans tree**, not only in `conventions/`. They were
only ever a local accelerator, and they are inert for an external reader on the fork's web view,
where anchors work and `L120:164` is decoration.

### The fetch tool

One extractor, two entry points:

- `sec <file> <id>...` — any TOC'd document: code specs, designs, `history.md`, `CONVENTIONS.md`
- `conv <name>...` — the same engine, with the file discovered by scanning `conventions/`

Properties that matter:

- **Storage and consumption are separate concerns.** Micro-conventions are *stored* the way Dean
  prefers to read them (few topical files, sectioned) and *consumed* one named convention at a time.
- **No index file.** The marker carries the name, so the tool scans `conventions/`. Nothing to maintain,
  nothing to go stale.
- **Extraction is local CPU only** — awk/grep effort, negligible. The containing file never enters
  the model's context; only the extracted section does. File size is irrelevant to token cost.
- **The residual cost is one round trip per invocation**, regardless of how many sections are
  pulled. So the tool **must accept multiple names in one call** — that is what makes a step's whole
  convention set a single fetch.
- **An unresolved name must fail loudly** — nonzero exit, message on stderr, never silent empty
  output. Otherwise "typo in the name" and "the convention is empty" are indistinguishable to the
  coder, and halt-on-missing quietly degrades into proceed-with-nothing. Exit codes are part of the
  contract.

### Why minimal fetch actually happens

Sessions have been observed reading whole documents despite explicit instructions. Levers, weakest
to strongest:

1. Prose instruction — observed to fail.
2. Structure that makes whole-document reading visibly expensive (N calls instead of one).
3. A `PreToolUse` hook rejecting an unbounded read of a plan document.
4. **Make the minimal fetch the easiest verb available.**

(4) is the strongest and cheapest, and it arrives free with name-addressed fetch: if the natural
thing to type is `conv commit-dco`, there is no convenient whole-document verb to reach for. The
path of least resistance becomes the correct one — a design property rather than a rule anyone has
to remember. Same move as putting conventions in the step instead of the rulebook.

---

## Micro-conventions

Dean's term, and the directory is named for it: **`conventions/`**, not `rules/`. "Rules" is a vendor
primitive elsewhere (`.cursor/rules`, `.clinerules`), and these are deliberately vendor-neutral
(§ Portability); "convention" is also already Dean's own vocabulary, so it carries no new baggage.

*Disambiguation during coexistence:* "conventions" would otherwise name three things at once — the
frozen `session/CONVENTIONS.md`, this directory, and the general notion. Path-qualify whenever it
could matter: `conventions/commit-dco` versus `session/CONVENTIONS.md`. In prose, "rule" remains the
plain English word for a governing statement; a **named** one is a convention.

**Storage:** a few topical files — e.g. `conventions/commits.md`, `conventions/git.md`,
`conventions/code-hygiene.md`, `conventions/handoffs.md` — each holding several named conventions as
`### convention: <name>` sections, with an internal TOC for human reading. Past roughly 150 lines,
split the topic rather than adding an addressing scheme.

**Consumption:** by name, one at a time, via `conv <name>` (§ Addressing and fetch). A coder never
reads the other 90 lines of the topic file.

**Status.** Each convention carries `status: active` or `status: probation`. Probation means *kept,
present and binding* — it still fires, it is still fetched, it is still followed. It only marks it as
accumulating evidence about whether it is rare or stale. Probation is never a soft delete and
never suppresses anything. It runs **long**, and its only possible outcome is a proposal to Dean; he
alone decides removal (constraint 8).

### Authored like a memory, not edited like a file

Dean's framing (2026-08-10): *"adding a convention should be like adding a memory — Claude creates it
to match what I said or some incident. I never go and edit memory files directly."* That fixes the
interface: **Dean's interface is the conversation; the tools below are the agent's.** He states
something normative, or an incident happens; the agent recognizes it, confirms nothing already covers
it, proposes the text, and writes it. He never opens the file.

Consequently capture is a **standing behavior in the policy-writer role kernel**, not a command Dean
has to remember to type — memory-writing is not a slash command either. Any other role that hears a
normative statement raises a `policy__` handoff rather than writing the convention itself; ownership
stays with one role.

What the memory model contributes, point by point:

| Memory | Convention |
|---|---|
| one file = one fact | one section = one convention; never two ideas in one |
| `description:` — used to judge relevance at **recall** | `description:` — used by the spec owner to find the right one when writing a step manifest |
| `MEMORY.md`, one line each, auto-loaded | **no stored index.** `conv-list` computes name + description by scanning, so it cannot drift — and conventions must *not* be auto-loaded (§ Addressing and fetch) |
| body: fact, then **Why**, then **How to apply** | same shape, plus `origin:` — the incident or instruction that caused it |
| `[[name]]` links, liberally; dangling links are fine | same; a dangling link marks a convention worth writing |
| check for an existing file first; update, don't duplicate | **search descriptions before minting.** Near-duplicates get cited inconsistently by different steps |
| don't save what the repo already records | don't mint one that a step's `do:` already states — that is how ceremonial conventions breed |
| **delete memories that turn out wrong** | **does not carry over.** Constraint 8: long probation, Dean approves. Memories are beliefs; conventions are policy caused by an incident, so removal destroys history |

So the section header carries a small fixed set of fields:

```
### convention: commit-dco
description: every commit carries a DCO Signed-off-by trailer
scope:       coder
trigger:     BEFORE commit
status:      active
origin:      incident — a rebase dropped sign-off, CI blocked, force-push needed to recover
```

`trigger:` here is the **default**, so the spec owner need not invent one per step and standing
kernel-level conventions have one intrinsically; a step manifest may override it. This is what keeps
manifests to trigger-plus-name.

One rot check worth inheriting: recalled memories "reflect what was true when written — verify a named
file or flag still exists." A convention citing a script or path can go stale the same way, so
`conv-lint` should check that referenced paths resolve.

### Authoring — never freehand

Once a coder fetches by marker and a plan cites by name, these files are a **published interface**,
not prose. Hand-editing threatens two different things.

*Structural integrity — mechanically checkable, and every failure is silent:*

- a malformed marker (`### Convention:`, `##convention:`, `## convention:`) makes the convention
  unfetchable, and the coder halts exactly as if it did not exist
- a stray `##` inserted inside a section **truncates** it at extraction; a `####` subsection gets
  **swallowed** into it — the fetched text differs from the text a human reads
- duplicate names across topic files make `conv <name>` ambiguous
- a missing `status:` breaks probation tracking

*Change discipline — not derivable from the file:*

- a new convention needs its **why** (which incident, or which behavior is being pre-empted), or
  constraint 8's probation judgments become guesswork years later
- a rename or removal **orphans every step manifest citing it**

Hence four tools and one gate:

| | |
|---|---|
| `conv-new <name> --topic <file>` | writes the exact marker, `status: active`, and required provenance; refuses if the name exists anywhere |
| `conv-edit <name>` | extracts the section, takes a replacement, splices it back between its marker and the next same-or-higher heading; neighbors untouched |
| `conv-rename <old> <new>` | renames **and** rewrites every citation across `planning/` and `roles/`, or refuses. Delete likewise: refuse while any citation exists |
| `conv-list` | computed index: name + `description` for every convention, so nothing is stored and nothing drifts |
| `conv-lint` | marker format · name uniqueness · required fields present · heading levels sane · no orphan citations · referenced paths resolve |
| **pre-commit hook on `plans`** | runs `conv-lint`; rejects a commit touching `conventions/` that fails |

The hook is git-level on purpose — it binds whoever made the edit, human or agent, under any harness.
`conv-lint` also runs inside `plan-lint` (§ plan-lint).

`conv-edit` is the parked writing-protocol problem (§ Open and parked) solved only for this narrow
case, which is tractable *because* sections are small and marker-delimited. It does not generalize to
plan documents yet, and this is not a reopening of that thread.

**Two limits, stated rather than glossed.** The hook enforces *structure*, not *process*: well-formed
markdown written by hand will pass, and that is acceptable — structure is what the tooling depends on,
and the tools exist to make it automatic, not to forbid thought. And **authorization needs no new
channel**: `new conventions:` already sits in `## Intent`, Dean's bounded review surface, so every new
convention reaches him at plan review by construction.

The same reasoning extends to `roles/` (structured and cited) and to step sections in plans (already
covered by `plan-lint`). General principle: **anything the tooling addresses structurally gets a
writer and a validator.**

**Location:** tracked on the `plans` branch, as today. A container symlink may be added for coder
convenience, but links *inside* documents stay repo-relative so an external copy resolves without it.

**On prior art (unverified in detail).** Claude Code has no `rules` primitive — its levers are
`CLAUDE.md` and `@`-imports, skills, and hooks. The `rules/`-directory pattern circulating as
best practice appears to come from editors whose rule files carry **auto-attach metadata** (globs,
always-apply). If so, the "stronger enforcement" impression comes from *conditional auto-injection*,
not from the file being small — which means the per-step trigger field is the portable
hand-rolled version of the same mechanism, and a hook is the enforcing version. Worth confirming
against current vendor documentation before relying on the comparison.

---

## Coder state

No new artifact. A coder's output is code; its tracking is commits plus code comments; its other
state already has a home in `session/status/<branch>.md`. That file becomes the coder's **ledger**.

One mechanical amendment: status files are rewritten in place today (a snapshot), while a ledger
needs history — a snapshot cannot answer "which commit came from S07". So keep the snapshot header
and add an **append-only `## Step log`** below it:

```
S07 · commit abc1234 · verify pass · <one line>
```

Readers: cold resume reads the tail (which step is next); **code-verification reads the whole log**
(did commits land where the plan meant them to land). The verifier is why the append matters.

The ledger cannot live in the code spec: the spec owner owns that document, and a coder appending into
it would break the clean ownership that justifies having no new document type.

"Living document / tracks progress" in the existing code-spec definition means the **spec owner's** WIP
while the spec is being written or modified — likewise the design for designers and the review for
reviewers. Coders are the exception. When work is done and reviewed, the spec owner folds status into
the plan (coded, PR pushed, …), as it already does today.

---

## Roles and session modes

Role is declared at session start or on resume, and the declaration should be the thing that loads
the role's rules — not a prose statement that a session may or may not act on.

**Skill prefix `r-` for roles**, distinct from `s-` utilities, so the two are distinguishable in the
skill listing: `r-coder`, `r-epic`, `r-spec`, `r-designer`, `r-confirm`, `r-verify`, `r-pr`,
`r-triage`, `r-policy`, `r-sync` — one per role, per
[`doc-and-session-model.md`](doc-and-session-model.md) § Roles.

**Two invocation paths, one skill:**

- **Interactive (Dean's path)** — bare `/r-coder`. Dean does not always use the exact worktree name
  and will not know step numbers, so the skill resolves them: `git worktree list` for branches,
  `planning/*-plan.md` for plans, the plan's `## Step index` for the range. The picker offers
  **titled** steps, never bare numbers.
  - **The default needs no numbers at all:** the step log records what is done, so "continue from
    the ledger" is the standing default. Dean chooses explicitly only when deviating. He marks no
    checklist; the coder's own ledger is the marker.
- **Deterministic (machine path)** — `/r-coder <branch> <step-range>` for a Claude-launched coder.

**The confirm-back handshake is the skill's mandated first action:** state worktree, branch, plan
path and assigned range, then stop for Dean's confirmation. Dean already performs this ritual
manually; encoding it in the skill means it cannot be skipped.

**Reliability note.** Prose-triggered skill invocation depends on the skill appearing in the session
listing, and 5 of 9 `s-*` skills were found missing from it (see
[`context-cost-reduction-plan.md`](context-cost-reduction-plan.md) Track 4a). A silent miss looks
exactly like a session that read its rules. Typed invocation is deterministic; prefer it.

**Auto-rename is unreliable for now.** Setting the session title from the role skill is attractive
(the role shows in the icon), but Claude Code re-persists its in-memory title every prompt and
clobbers `set-title` in long sessions. Treat rename-from-skill as pending that hook fix.

### The four reviews are distinct

"Review" was overloaded and should not be used unqualified:

| Activity | Reader | Reads | Against |
|---|---|---|---|
| **Plan finalization** | Dean | intent, plus whatever he chooses | his judgment — not scriptable |
| **Spec confirmation** (`r-confirm`) | design owner or a review session | the code spec | the epic plan and design |
| **External review** | outside human + their agent | the code spec | general engineering sense |
| **Code verification** (`r-verify`) | verifier session | the code, **then** the spec | the spec's intent |

Plan confirmation is *design → plan*; code verification is *plan → code*. Same activity, adjacent
layers. `plan-lint` is none of the four — it is a mechanical pre-check that runs before all of them,
so no reviewer spends attention on missing fields or dead links.

**Code verification reads code first, then the plan.** This is an anti-anchoring device, not mere
sequencing: reading the plan first shows the reviewer what was promised instead of what was built.
Its reading list is intent, the briefs, and step details as needed — never rule bodies. It sits
above a coder.

---

## plan-lint

Mechanical, cheap, and the thing that keeps runtime halts rare enough to be meaningful. Proposed
checks:

- every step has a brief and a detail section
- `conventions:` present on every step (possibly the literal `none`)
- every convention name in every manifest resolves
- `done_when:` present on every step
- one commit declared per step
- `## Intent` present with all fixed fields
- no line-number references (§ Addressing and fetch)

**Three runners, one script:**

1. **Planner**, as the last authoring step — the slot `toc-refresh.sh` occupies today.
2. **Coder**, over its assigned range at start. Not redundant: the spec owner's run proves the spec was
   clean *when written*, and a plan is a moving reference, not a snapshot. Mid-flight edits are
   exactly when a step loses its `conventions:` line.
3. **`r-confirm`**, as its step 0.

---

## Auto mode

The term covers two axes that are easy to conflate. Only the first is what "auto" means here.

**Axis A — harness permission prompting.** Whether the tool layer asks before each `Edit`, `Write`
or `Bash` call. "Auto mode" means this is off: mechanical operations inside the coder's sanctioned
scope run without a prompt. (In Claude Code this is the permission mode; the exact flag should be
confirmed against current documentation before being written into a skill.)

**Auto is the target from the start, not an earned end state.** A manually-approved coder is close to
useless: there is far too much detail for Dean to read, so approvals go fast, and the key decisions
are exactly what gets missed. Rapid-fire approval is worse than none — it produces the appearance of
oversight while providing none of it. So Axis A is off from the first run, and safety comes from the
mechanisms below rather than from a human in the loop of every write.

**Axis B — judgment interrupts. On, always, and this is the load-bearing half.**

> The coder stops and asks its spec owner whenever it is **unsure**. Never presume. Never assume. Never
> guess. Never make a judgment call. A coder follows orders. Limited scope. **It owns
> implementation, not intent.** Not sure — stop, ask.

**Where the question surfaces.** The halt routes to the **spec owner**, which raises it with Dean **in
its own chat — never the coder's.** Dean does not watch a coder work, so the coder's session is
structurally the wrong place to ask a human anything. This also means the spec owner must be alive for
a halt to reach anyone; see § Open and parked, halt discovery.

**The spec owner also lands the work.** It judges push-readiness, performs the push, opens the PR,
follows CI and triggers immediate corrections — it holds the detail and is already alive, so there is
no separate landing role. Coders still never push (§ Enforcement). On first external review a
**triage** session takes over and turns comments into a new code spec, additions to the existing one,
or both.

That last line is why halting is structural rather than cautious: an intent question is *outside the
coder's ownership*, so it has no standing to answer it, however obvious the answer looks. A halt for
a missing rule, an ambiguity or a surprise is not a failure of auto mode — it is the mechanism.

Today's prompting model is the inverse of what is wanted: it interrupts on mechanics (run a test,
format a file) and is silent on judgment, which is model-side and therefore ungated.

**What replaces the prompt.** A per-call prompt is a crude proxy for scope enforcement — a human
eyeballing each write. The step's `scope:` field plus the post-step check (§ Enforcement) is a
precise one, checked mechanically instead of by attention. Since auto is on from the first run, that
post-step check is **tooling, not a later phase** — it lands before any coder runs (§ Migration).

---

## Enforcement

**Shared rules convey intent. How other harnesses follow and enforce them is their problem.**
Enforcement is harness-local; the rule text is the contract.

**Portable layer (required, works under Bob or Claude)** — post-step verification:

- `git status` shows only paths inside the step's `scope:`; anything else halts before commit
- DCO sign-off verified before the step is declared done
- `verify:` commands run, `done_when:` predicate observed

**Claude Code hardening layer (opportunistic, must not be depended on)** — hooks for what is
mechanical, catastrophic if missed, and *not* per-step:

1. `Write`/`Edit` outside the current step's `scope:` → block. The load-bearing one once auto mode
   is on. It is also the only one with real complexity, since the hook must read the current
   `scope:` from the coder's status file.
2. `git commit` without DCO sign-off → block. Stateless, trivial.
3. `git push` from a coder session → block. Stateless, trivial.

Optionally, an unbounded read of a plan document → reject (§ Addressing and fetch, lever 3).

**Physical confinement already exists** for the launch model Dean wants: terminal-launch-from-worktree
was verified as confining (memory `coder-write-confinement`). Requirement 2 (auto mode) and
requirement 3 (shell/CLI launch) are therefore aligned, not in tension — the launch model he prefers
is the safe one. Its only cost was the conventions-loading defect, which the layer model removes.

---

## Portability

Plans must be consumable by other AI agents and by external human reviewers without any Claude-local
state. The distribution path is the `plans` branch on Dean's fork; markdown links work in-document
and across documents there. An export skill is unnecessary.

Consequences, all concrete:

- **Claude-specific mechanisms are loaders only, never the contract.** `@`-imports, skills, hooks —
  convenience. The contract is markdown files with relative links.
- **Reading Protocol boilerplate must not carry Claude tool syntax.** The current form,
  `Read <file> offset:<n> limit:<m>`, is a Claude tool signature. State the intent, with the tool
  call as a parenthetical example.
- **Anchors are the portable addressing contract**; line ranges are inert on GitHub's rendered
  markdown (§ Addressing and fetch).
- **No plan references `CURRENT.md` or session state.**
- **The `## Intent` block must be self-contained for an outsider.** Plans-branch tokens — `W1`,
  `AD8`, `F3`, `N5`, `C6c` — are load-bearing internally and meaningless externally. The existing
  §4a rule already bans them in code artifacts for this reason; external review extends the same
  requirement to `## Intent`. Spell out on first use, or carry a two-line legend. Cheap now,
  unrecoverable at 2,000 lines.

---

## Consequences for existing artifacts

Nothing below has been done. Sequencing note: the skill rename and `CODER-CONVENTIONS.md` collide
directly with work landing in a concurrent session (Track 1d of
[`context-cost-reduction-plan.md`](context-cost-reduction-plan.md)), so they queue behind it.

| Artifact | Change |
|---|---|
| `session/CONVENTIONS.md` | **frozen in place, not rewritten.** Old sessions keep loading it unchanged. Only correction: the dead `plans/rules/INDEX.md` reference (see defects below), plus a header pointer to this design |
| `session/CODER-CONVENTIONS.md` | **frozen in place**, same reasoning; a header pointer only |
| `roles/coder.md`, `roles/spec.md`, `roles/epic.md`, … | **new**, new names — one kernel per role in [`doc-and-session-model.md`](doc-and-session-model.md) § Roles, loaded by the matching `r-*` skill |
| `planning/doc-and-session-model.md` | **new** — the taxonomy and role-model prose extracted from `CONVENTIONS.md`, which is design material, not a rule (§ Migration) |
| `planning/micro-rules-design.md` | mark its repeating-rules half superseded by this document; its fetch-protocol half survives |
| `conventions/` | **new** — create topic files; no `INDEX.md` (§ Addressing and fetch) |
| `scripts/` | add the extractor (`sec` / `conv`), the authoring tools (`conv-new` / `conv-edit` / `conv-rename`), `conv-lint`, and `plan-lint` |
| plans-branch pre-commit hook | add the `conv-lint` gate on `conventions/` |
| `scripts/toc-refresh.sh` | keep anchor/TOC generation; drop the line-range half, including the double-run stabilization pass |
| `.claude/skills/` | `s-coder` → `r-coder`, plus its container symlink; add the interactive picker and the confirm-back handshake |

### Two live defects, found while designing

1. **`CONVENTIONS.md` cites a path that has never existed.** It states that the available rule files
   are listed in `plans/rules/INDEX.md`, *"added to CLAUDE.md; always in context."* Both clauses are
   false — `plans/rules/` does not exist and `plans/CLAUDE.md` does not import it. An epic or spec
   session following that sentence hits a dead path today.
2. **`CODER-CONVENTIONS.md` §0 currently mandates over-reach.** Verbatim: *"note ALL modified,
   staged, and untracked files. **This is your full work scope regardless of how the session was
   triggered.**"* Under step-atomic execution this must invert — scope comes from the step, and a
   dirty tree at bootstrap is a **halt condition**, not scope to absorb. This rule and constraint 1
   cannot both stand.

---

## Migration

Two migrations. Only the first is required, and it is front-loaded: **all** the tooling and **all**
the rule extraction come first, and its purpose is to retire `CONVENTIONS.md` and
`CODER-CONVENTIONS.md` as the load-bearing documents. The second converts existing plans and is
optional. Throughout, **both regimes co-exist** — and the skills and hooks land as early as possible,
so every new session is on the new regime from its first prompt while old plans keep running.

### Distinct names make the regime unambiguous

New artifacts get **new names**; the old files are **frozen in place**, not edited into the new
shape. So:

- an old session loads `session/CONVENTIONS.md` + `session/CODER-CONVENTIONS.md` through
  `plans/CLAUDE.md`, exactly as it does today
- a new session loads `roles/<role>.md` through its `r-*` skill, and fetches `conv <name>` on demand
- the filename tells you which regime you are in — no flag, no registry, no ambiguity

This also avoids a whole class of breakage: many documents cite `session/CONVENTIONS.md` by path, so
renaming the old files would strand those references. Freezing costs nothing; the files stop growing
and become inert once nothing loads them.

### Migration 1 — build everything, extract everything, then retire

**M1.0 — Tooling, complete before extraction.**
- the extractor: `sec <file> <id>...` and `conv <name>...`, multi-name in one call, loud failure on
  unresolved names (§ Addressing and fetch)
- `plan-lint` (§ plan-lint), permissive at first
- the convention authoring tools and `conv-lint`, plus the plans-branch pre-commit hook
  (§ Micro-conventions, authoring) — these land **with** the extraction in M1.2, since M1.2 is the
  first bulk write into `conventions/` and doing it by hand is exactly what they prevent
- **the portable post-step check** — `scope:` containment, DCO, `verify:`/`done_when:` (§ Enforcement).
  This is in M1.0 and not later precisely because auto mode is on from the first run (§ Auto mode)
- the coverage checker for M1.3

**M1.1 — Skills and hooks, as early as possible.** `r-coder` (from `s-coder`) plus
`r-designer`, `r-epic`, `r-spec`, `r-confirm`, `r-verify`, `r-pr`, `r-triage`, `r-policy`, `r-sync`;
the interactive picker and confirm-back handshake;
the two stateless hooks (DCO, push-block). Early because every new session should be on the new
mechanism immediately — the old documents standing untouched is what makes that safe.

**M1.2 — Harvest every rule, from every source.** Harvesting is not limited to the two convention
files (Dean, 2026-08-10). Sources, split by whether they are enumerable:

*Bounded — these are what M1.3's coverage audit is computed over:*

- `session/CONVENTIONS.md` and `session/CODER-CONVENTIONS.md`
- the **`feedback_*` memories** — many are already conventions in memory form
  (`feedback_no_cd_sibling`, `feedback_dco_signoff`, `feedback_coder_worktree_discipline`, …), plus
  the working-practice `project_*` ones
- **recorded incidents** — [`governance-follow-ups.md`](governance-follow-ups.md) holds four
  (reviewer-worktree 07-14, unauthorized-subagent 07-26, formula-fork 07-27, §4a-leaks 07-29); others
  sit in CURRENT.md and in review findings

*Unbounded — a stream, deliberately **excluded** from the coverage audit:*

- **best practices**, and new incidents as they occur. These feed the standing capture behavior
  (§ Micro-conventions, authored like a memory), not the migration. Folding a stream into a bijection
  check makes Migration 1 unfinishable.

**Reconcile, do not concatenate.** The same rule frequently exists in two or three sources at once —
DCO sign-off appears in CONVENTIONS' pre-push checklist, CODER-CONVENTIONS §8 *and*
`feedback_dco_signoff`. Where sources differ in detail, that difference is evidence about which was
authoritative: record every source on the convention and **surface the conflict to Dean** rather than
resolving it by choosing. A silently merged divergence is worse than either original.

**Two classes of harvest, and only one is free:**

- **Relocated** — an existing written rule moves and keeps binding. Migration; needs verification it
  arrived, not approval (constraint 8).
- **Newly articulated** — an incident happened and nobody ever wrote the rule. This is new policy, so
  it needs Dean's confirmation, and `new conventions:` in the plan's `## Intent` is the channel.

**What becomes of a harvested memory (open — Dean's call).** Leaving the rule in both places is the
drift this design exists to remove. Recommendation: the memory shrinks to a **one-line pointer** at the
convention. The two have different consumers — memory is auto-recalled across every session type,
conventions are fetched deliberately at a step — so the pointer keeps the "you already learned this"
signal firing while the convention holds authority. Ordering is the existing one: the content must
exist in the convention *before* the memory is reduced.

Expect **three** residue classes, not two:

| Class | Destination |
|---|---|
| per-step rule | a named micro-convention in `conventions/<topic>.md` |
| standing, role-scoped | the role kernel `roles/<role>.md` |
| model / taxonomy prose | `planning/doc-and-session-model.md` — this is design material, not a rule at all |

The third class is the one easy to miss: `CONVENTIONS.md` carries the document taxonomy, the
role↔document ownership table and the handoff model. None of that is a rule anyone follows at a step;
it is the design of the system. It also connects to the parked taxonomy rename (§ Open and parked).

**M1.3 — Coverage audit, machine-checked.** Constraint 8 becomes a verified property rather than a
promise: enumerate every section of both old files **and every harvested memory and incident record**
(the bounded sources in M1.2), enumerate every micro-convention, kernel section and model section, and
assert the mapping is **total with no orphans**. A script, not a reading. Its output is the table Dean
reviews — which is also where source conflicts and the newly-articulated class appear for his
decision.

The unbounded sources are out of scope here by construction; the audit closes over a **dated snapshot**
of the bounded set, and anything arriving afterwards is ordinary standing capture, not migration debt.

**M1.4 — Retire, meaning stop loading.** Once coverage is total, `plans/CLAUDE.md` can drop the old
imports and the old files go inert with a header pointer. **This is migration, not removal, and needs
no per-rule approval** — every rule still exists and still binds, from a new location. Removal is a
separate, much later question (§ Micro-conventions, rule status).

### Migration 2 — existing plans, optional and lazy

**Do not convert en masse, and do not convert frozen plans.** PR-2's plan is frozen and
code-complete; rewriting it risks a live mission for zero gain.

Convert **on next substantial touch**: when a plan is being materially edited anyway, author the edit
in the new shape. Cost is bounded and paid only where there is already work. Coexistence is free
because the shape is self-describing — presence of `## Intent` + `## Step index` means new protocol,
absence means old, and `r-coder` detects which.

WIP plans are the natural candidates; a plan that is merely *open* but untouched can stay as it is
indefinitely.

### First run

The first real coder run is a smoke test of the protocol, not a gate on anything in M1 — extraction
completeness is the gate, and it is verified by M1.3 rather than by observing a coder. A small,
low-design-risk task is the right first one (the deferred `checkVariantGPSMismatch` test coverage
fits: test-only, no owner, few steps). Its value is finding protocol defects — a step whose `do:` was
goal-shaped, a missing trigger, a `verify:` that cannot actually be observed.

Instrument it: every halt goes in the step log, and every halt is a defect in the *plan*, not in the
coder.

### What could stop it

- **Skill-listing dropout** (5 of 9 `s-*` skills were found missing) would make M1.1 fail silently —
  verify presence before depending on it.
- **The M1.2 audit contradicting the layer model** — if most content classifies as standing rather
  than per-step, the kernel is larger than assumed and the step schema needs revisiting first.
- **The portable post-step check slipping out of M1.0**, which would put auto mode in front of its
  own safety net.

---

## Decided, do not re-litigate

Recorded so a future session does not reopen them.

- **Rules are linked, not inlined.** Inlining lengthens steps, and long steps get forgotten. The
  round trip buys recency and is therefore the mechanism, not overhead. (An earlier
  inline-by-compile recommendation was withdrawn.)
- **The coder does get the narrative.** An earlier proposal that the coder never read the plan
  document is rejected: plan intent and per-step intent, decisions and rationale must reach it. Only
  Dean-facing prose is excluded, and only execution detail is deferred.
- **No new document type.** Audience partition happens inside the code spec.
- **No dual TOC.** The TOC is a reference; a single one suffices, with a physical divide.
- **No separate ledger file.** The status file is the ledger.
- **No line numbers.** Headings address sections.
- **`conventions/` is never edited freehand.** Structure is load-bearing and every malformation is
  silent, so authoring goes through `conv-new` / `conv-edit` / `conv-rename`, gated by `conv-lint` in
  a plans-branch pre-commit hook. Renames repair citations or refuse; deletions refuse while cited.
- **Conventions are authored like memories.** The agent writes them from what Dean said or from an
  incident; Dean never edits the files. Capture is a standing behavior of the **policy-writer** role,
  not a command he types. Memory's delete-when-wrong norm is explicitly **not** inherited.
- **No index file under `conventions/`.** The marker carries the name, and `conv-list` computes the
  name + `description` listing on demand — an index that cannot go stale.
- **`conventions: none` is legal and required to be explicit.** Omission halts.
- **The directory is `conventions/`, not `rules/`** (Dean, 2026-08-10 — "convention seems more
  neutral"). Vendor-neutral, and already his vocabulary. Artifact names follow: `### convention:
  <name>` markers, the `conventions:` step field, the `new conventions:` intent field, and the `conv`
  fetch verb. Plain English "rule" survives in prose where it means a governing statement.
- **Coders never read `CURRENT.md`.** It is a ledger and calendar, not a trigger for action.
- **Hooks are hardening on the Claude Code path only**, never the contract.
- **Auto mode from the first run.** Not an earned end state. A manually-approved coder is near
  useless — too much detail to read, so approval goes fast and the key decisions are what gets
  missed. An earlier proposal to run the first pilot interactively is rejected; the post-step check
  moves into M1.0 instead.
- **Migration is not removal.** Relocating a rule needs verification that it arrived, not approval.
  Removal needs long probation and Dean's per-rule approval. An earlier framing that gated each
  relocation on his approval was wrong.
- **New names for new artifacts; old files frozen, not rewritten.** The filename identifies the
  regime, and existing path references stay valid.
- **Existing plans convert lazily, on next substantial touch. Frozen plans never convert.**

---

## Open and parked

**Parked by Dean, with a thread of its own to come:**

- **Writing protocol.** Reading by section works, more or less. Writing does not: an incremental
  modification reads the whole document, and edits invalidate a line-numbered TOC. Candidate
  directions Dean raised — a TOC-less working copy with the original as reference, refreshed once at
  the end; exploding into per-section files while editing and gathering back on refresh; or a
  different extraction mechanism per section. One bit of this was **not** parked and is settled
  above: build on heading-addressing, not line ranges, since that is what makes an in-place section
  replace possible at all.
- **Taxonomy rename — ✅ DONE 2026-08-10**, no longer parked. The types and roles are named in
  [`doc-and-session-model.md`](doc-and-session-model.md); the numbers are retired from conversation,
  handoffs and triggers immediately, and survive as parenthetical aliases inside documents for one
  migration cycle only.

**Deferred by Dean 2026-08-10 — workspace layout stays exactly as it is.** Two options were
considered and set aside: moving `roles/`/`conventions/` under the container's `.claude/`, and re-rooting
the `plans` worktree at the container. The first was rejected on principle — `.claude/` is
vendor-scoped, and these documents are deliberately not (§ Portability); the best practices that put
rules there assume a single-harness world. The second is merely deferred, not rejected. So `roles/`
and `conventions/` live at the `plans` worktree root beside `planning/`, `session/` and `scripts/`, and the
`r-*` skills resolve the path (skill discovery keeps using the existing container symlinks).

Notes for whoever revisits the re-root: the container `.claude/` is already almost entirely symlinks
into `plans/` — including `settings.json` → `plans/.claude/container-settings.json` — so the
"untracked container config" argument for re-rooting does not hold. And a container-rooted `plans`
worktree would need a `.gitignore` covering 19 worktree directories plus `repo/` plus a dozen loose
files, growing by a line per branch. The load-bearing unknown remains whether a container-root
`CLAUDE.md` is discovered by a session launched in a sibling worktree — if it is, it must stay ~3
lines and import nothing, or every coder re-inherits the standing context this design removes.

**Halt discovery — open, and it gates unattended auto mode.** A coder halt routes to its spec owner,
but if that session is closed nothing surfaces. Dean does not watch coders by design, so a halted
coder is silent rather than obviously stuck. Candidates: the coder raises a notification, or halted
state becomes visible in `session/status/` and is polled. Needs deciding before an auto-mode coder runs
unattended. Also recorded in [`doc-and-session-model.md`](doc-and-session-model.md) § Open.

**Still open in this design:**

- Exact script naming and whether `sec` and `conv` are one file or two.
- What becomes of a harvested `feedback_*` memory — pointer, or left as is (§ Migration, M1.2).
- Whether the harvest reaches the **global** `~/.claude/CLAUDE.md` rules (no in-place shell edits,
  large-change approval, verify public APIs before suggesting). They are conventions by any reading,
  but they are project-agnostic and cross-project, which is the project-specific-versus-common split
  already flagged in memory `role-specific-conventions`. Probably out of scope; worth deciding rather
  than drifting.
- How `scope:` on a convention relates to the role kernels — the intended distinction is *standing*
  (kernel) versus *fetched at a step* (convention), not who it binds, so `scope:` governs which roles
  may cite it. Pin down during the M1.2 harvest, when the actual text is in front of us.
- Whether the `scope:` hook (Enforcement item 1) is worth its complexity in the first cut.
- Confirming the vendor prior-art comparison in § Micro-conventions against current documentation.

---

## Provenance

Brainstormed with Dean 2026-08-09 in a session that began by recovering the older
`micro-rules-design.md` thread. Inputs: memories `coder-enforcement-direction`,
`role-specific-conventions`, `coder-autonomy-direction`, `workflow-architecture-directions`,
`coder-write-confinement`, `context-cost-reduction`; documents
[`micro-rules-design.md`](micro-rules-design.md) and
[`context-cost-reduction-plan.md`](context-cost-reduction-plan.md).

Dean's durable preferences that shaped it: smaller modular documents over bundled ones;
interface contracts per unit (clear input, clear output, clear interface); modes, skills and
commands as one concept; and enforcement preferably not specific to one harness.
