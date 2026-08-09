# Document and Session Model

**Status: DRAFT** — written 2026-08-10 from a brainstorm with Dean. Awaiting his finalization.

Names every artifact this workspace produces and every session role that owns one, and describes how
they connect. Replaces the `Type 1 … Type 6` numbering, which is opaque and — worse — implies a single
pipeline when the reality is a graph.

Companion to [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md), which governs how a
coder executes a code spec. This document governs what the artifacts are and who owns them.

---

## Reading Protocol

Addressed by section. Read this protocol and the contents list, then fetch only the sections you need —
by anchor link, or by extracting from its heading to the next heading of the same or higher level.
There are deliberately no line numbers.

---

## Contents

- [Why this exists](#why-this-exists)
- [Three categories](#three-categories)
- [Artifact types](#artifact-types)
- [Kinds the audit found](#kinds-the-audit-found)
- [Roles](#roles)
- [Flows](#flows)
- [Rules the naming exposes](#rules-the-naming-exposes)
- [Skill surface](#skill-surface)
- [Audit evidence](#audit-evidence)
- [Adoption](#adoption)
- [Open](#open)
- [Provenance](#provenance)

---

## Why this exists

The numbering hid real problems, and each one has cost something:

- **`planner` named two different roles** — the owner of the design-to-units-of-work breakdown, and the
  owner of a single code task. Dean has switched a live session from one to the other mid-stream, and
  has **skipped the breakdown step entirely, which he judges was wrong.**
- **`review` is generic**, but three unrelated activities produce one: checking a code spec against its
  epic plan and design, checking code against its code spec, and reviewing a PR on GitHub.
- **Policy had no type and no role.** That absence is how `CONVENTIONS.md` reached 32 KB while carrying
  a reference to a path that has never existed.
- **Channels** — status files, handoffs, triggers — were untyped.
- **The push → PR → CI → triage path was unnamed.** Dean asks "the planner" for it.
- **Dean was not in the roles table**, despite owning every approval.

Names are not cosmetic here: handoff routing *is* the name, via the `to:` header and the filename
prefix. A `sync`-versus-`plan` conflation already caused 16 handoffs to be consumed by the wrong role
(2026-08-03), and § Audit evidence shows how lopsided the prefixes have become.

[↑ Contents](#contents)

---

## Three categories

| Category | Members | Note |
|---|---|---|
| **Documents** | design · epic plan · code spec · reference · review · session state | the six that had numbers |
| **Policy** | `conventions/` · `roles/` | **new type** — the gap that let the conventions files drift |
| **Channels** | status file · handoff · trigger | **new type** |

[↑ Contents](#contents)

---

## Artifact types

| Name | Was | Lives | Owner |
|---|---|---|---|
| **design** | Type 1 | `planning/*-design.md` | designer |
| **epic plan** | Type 2 | `planning/*-epic.md` | epic |
| **code spec** | Type 3 | `planning/*-spec.md` | spec |
| **reference** | Type 4 | `docs/developer-guide/` — ships in the PR | coder |
| **review** | Type 6 | `planning/*-review.md`, with a `reviews:` header naming its subject | confirm · verify · pr |
| **session state** | Type 5 | `session/CURRENT.md`, `session/history.md` | sync |
| **policy** | — | `conventions/`, `roles/` | policy-writer |
| **channel** | — | `session/status/`, `session/handoffs/` | each sender owns its own |

Definitions where the rename changes the meaning:

- **design** — concepts, algorithms, goals. Its input is **conversation**: a discussion, a chat, a
  brainstorm. Frozen before work starts; amended through an explicit addendum rather than edited.
- **epic plan** — takes a design and breaks it into units of work, turning abstract items into a
  concrete code roadmap. The unit is typically a PR. Named for the GitHub epics that already group
  those PRs. **Durable, not transient**: it holds the alternatives considered and the decisions made.
- **code spec** — one unit of work, executable by a coder. The unit is typically a PR, but that is not
  always known in advance, which is why it is a *spec* rather than a *PR plan*.
- **review** — always names its subject; see § Roles for the three that produce one.

[↑ Contents](#contents)

---

## Kinds the audit found

Classifying all 91 documents in `planning/` left 26 that fit none of the types above. They are listed
rather than forced, because most are legitimate kinds we simply had not named:

| Kind | Examples | Disposition |
|---|---|---|
| **source trace** | `multi-analyzer-dataflow-map.md`, `multi-analyzer-postrefactor-map.md` | Already ruled by Dean (2026-08-07) to be **traces, not authorities** — cite for per-site line evidence only; the design governs on disagreement. Deserves its own type name. |
| **analysis** | `scale-from-to-zero-analysis.md` | Output of an investigation. Neither a design (proposes nothing) nor a review (judges nothing). |
| **explainer** | `p-d-logic-explainer.md` | Written for Dean, not shipped in a PR — so it is not a reference. |
| **register** | `governance-follow-ups.md`, `open-items-roadmap.md`, `ta-0.9-epic-issues.md` | Backlogs and incident collections. Feed the policy-writer and the epic. |
| **design addendum** | `combined-analyzer-optimizer-design-addendum-1.md` | The amendment channel for a frozen design. Additive, governs where it overlaps. |
| **fixup code spec** | `PR1266-fixup-effectiveEnabled.md` | Confirms the triage → code spec edge in § Flows: this is exactly that output. |
| **policy, misfiled** | `multi-analyzer-coder-rules.md` | Coder rules living in `planning/`. Migrates to `conventions/` + `roles/`. |
| **release artifact** | `ta-0.9-release-notes.md` | Not a design, plan, or review. |
| **working scratch** | `ta-anchor-dynamic-refresh-PENDING-EDITS.md`, `*-coder-checklist.md`, `*-note.md` | In-flight fragments of a code spec. Should fold into their spec or become channels. |

Four documents named as designs in `CONVENTIONS.md` — `TA-notation.md`, `TA-demand.md`,
`TA-supply.md`, `TA-overview.md` — simply predate the `*-design.md` suffix. They are designs.

[↑ Contents](#contents)

---

## Roles

Each role owns artifacts, reads others, and has **one unique handoff token**.

| Role | Token | Owns | Reads |
|---|---|---|---|
| **Dean** | `ask` | approvals, finalization, every removal | anything |
| **designer** | `designer` | design | conversation, incidents, code |
| **epic** | `epic` | epic plan | design |
| **spec** | `spec` | code spec; **push, PR open, CI watch, immediate corrections** | epic plan, design, reviews |
| **coder** | `<branch>` | code, reference, status file and step ledger | its code spec only |
| **confirm** | `confirm` | review of a code spec | code spec, epic plan, design |
| **verify** | `verify` | review of code | **code first**, then the code spec |
| **pr** | `pr` | review of a GitHub PR | the PR |
| **triage** | `triage` | a fixup code spec, or additions to an existing one | PR comments, CI output |
| **policy-writer** | `policy` | `conventions/`, `roles/` | Dean's statements, incidents, existing policy, `feedback_*` memories |
| **sync** | `sync` | session state | handoffs |

Notes that carry weight:

- **`designer` keeps its existing token** — 12 handoffs already use it. Practice wins over tidiness,
  and it removes any `design`-versus-`designer` ambiguity.
- **`spec` owns landing, not just authoring.** It judges push-readiness, performs the push, opens the
  PR, follows CI and triggers immediate corrections. It holds the detail and is already alive, so
  splitting this off into a separate role would only lose context. Coders still never push.
- **`triage` opens on first external review**, not at PR creation. Its output becomes a new code spec,
  additions to the existing one, or both.
- **`verify` reads code before the spec.** This is an anti-anchoring rule, not sequencing: reading the
  spec first shows you what was promised instead of what was built.
- **`spec` and `sync` share their first letter** and diverge at the second. Never abbreviate either.
- **`pr` is not the upstream project's `pr-review` skill**, which reviews code inside a PR diff. This
  role reviews the PR as a GitHub artifact.

[↑ Contents](#contents)

---

## Flows

Not one pipeline. A graph, with two non-document entry points, one cycle, and two sinks.

```
conversation ──▶ design ──▶ epic plan ──▶ code spec ──▶ code + reference
  (designer)    (designer)    (epic)        (spec)          (coder)
                                 ▲            │                │
                                 │       confirm review        │
                                 │                             ▼
  incident ──▶ convention        └─── triage ◀── PR / CI ◀── push + PR
 (policy-writer)                        │                     (spec)
                                        └──▶ code spec          │
                                                          verify review
                                                                │
  every role ──▶ handoff ──▶ session state (sync) ◀─────────────┘
  every role ──▶ ask ──▶ Dean ──▶ decision
```

- **Two entry points are not documents.** A design starts from discussion; a convention starts from
  something Dean said or from an incident.
- **One cycle:** coder → push and PR → CI or external review → triage → code spec → coder.
- **Two sinks:** session state, and session state compacted into `history.md`.
- **A coder halt routes to its `spec` owner**, which surfaces the question to Dean **in its own chat**.
  Dean does not watch a coder work, so the coder's chat is never the place a question gets asked.

[↑ Contents](#contents)

---

## Rules the naming exposes

- **One session, one role.** Changing role requires a new session, or an explicit re-declaration with a
  fresh confirm-back. Mid-session drift from epic to spec is what produced the conflation.
- **The epic plan is mandatory for multi-PR work.** Skipping it was wrong: it is where abstract design
  becomes concrete units, and where alternatives are recorded.
- **A review names its subject** via a `reviews:` header — `code spec`, `code`, or `PR`.
- **Policy has a lifecycle**: `status: active | probation`, probation runs long, and removal is Dean's
  alone. Migration to a new home is not removal.
- **`planning/` is multi-writer.** A code spec can be edited by any spec session while a coder executes
  from it, which is why freezing the spec before handoff is the mitigation, not a formality.
- **Use the full names in conversation, not the numbers.** This binds speech, handoffs and triggers
  immediately — say *design*, *epic plan*, *code spec*, *reference*, *review*, *session state*,
  *policy*, *channel*. Numeric aliases survive **inside documents only**, for one migration cycle, so
  existing cross-references stay resolvable.

[↑ Contents](#contents)

---

## Skill surface

One skill per role, `r-` prefix separating roles from `s-` utilities:

`/r-designer` · `/r-epic` · `/r-spec` · `/r-coder` · `/r-confirm` · `/r-verify` · `/r-pr` ·
`/r-triage` · `/r-policy` · `/r-sync`

Against the ten skills that exist today:

| Existing | Maps to | Note |
|---|---|---|
| `s-coder` | coder | rename to `r-coder` |
| `s-plan` | **epic and spec** | the conflation, in skill form — splits in two |
| `s-pr-triage` | triage | rename to `r-triage` |
| `s-sync-current` | sync | rename to `r-sync` |
| `s-design-review` | **confirm or verify — ambiguous** | it produces findings about implementation against a design, which is neither review cleanly. Resolve when splitting. |
| `s-pre-push`, `s-sync-main`, `s-note`, `s-session-done`, `s-session-name` | utilities | stay `s-` |

**Missing entirely:** designer, epic, spec, confirm, verify, pr, policy-writer. Creating them is
migration step M1.1 in [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md), not part of
this document.

[↑ Contents](#contents)

---

## Audit evidence

Measured 2026-08-10.

**Handoff tokens actually in use** — 302 files in `session/handoffs/`:

```
plan                        146   (48%)
review                       37
<branch names>             ~100   across 20 branches
designer                     12
current                       1   (the CURRENT.md editing sentinel)
sync                          0
```

`plan` carries nearly half of all handoffs while `sync` currently carries none — the clearest possible
statement that one token has been absorbing work belonging to several roles.

**Documents in `planning/`** — 91 total: 35 `*-plan.md`, 21 `*-review.md`, 8 `*-design.md`, 2 `*-map.md`,
1 `*-note.md`, and **26 that matched no naming pattern** (§ Kinds the audit found).

**Roles versus skills:** eleven roles, ten skills, of which five map cleanly, one is ambiguous, one
covers two roles, and seven roles have no skill at all.

[↑ Contents](#contents)

---

## Adoption

- **No mass file renames.** `planning/*-plan.md` → `*-spec.md` would touch 35 files plus every
  reference in `CURRENT.md`. Rename **lazily, on next substantial touch** — the same policy chosen for
  converting plans to the atomic-step shape.
- **`CONVENTIONS.md` is frozen**, not restructured. Its taxonomy and role sections move here during
  migration M1.2; until then it gets a header pointer only.
- **Numeric aliases stay in documents for one migration cycle**, then drop.

[↑ Contents](#contents)

---

## Open

**Halt discovery.** A coder halt routes to its `spec` owner — but if that session is closed, nothing
surfaces. Dean does not watch coders by design, so a halt can sit unnoticed indefinitely, and under
auto mode a halted coder is silent rather than obviously stuck. Candidates: the coder raises a
notification, or halted state is made visible in `session/status/` and polled. **Needs a decision
before auto-mode coders run unattended.**

**`s-design-review`'s true role** — confirm or verify (§ Skill surface).

**Whether `source trace`, `analysis`, `explainer`, `register` and `release artifact` become named types**
or stay informal (§ Kinds the audit found).

[↑ Contents](#contents)

---

## Provenance

Brainstormed with Dean 2026-08-10, continuing the session that produced
[`atomic-step-protocol-design.md`](atomic-step-protocol-design.md). Names decided by Dean: **epic plan**
for the breakdown document, **policy-writer** for the policy role, **`ask`** as his own handoff token,
**no separate landing role** (the spec owner owns push, PR and CI), and **full names rather than
numbers in conversation**.

[↑ Contents](#contents)
