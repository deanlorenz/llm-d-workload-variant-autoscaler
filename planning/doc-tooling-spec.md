# Code spec — doc tooling (`toc-refresh.sh`)

**code spec** · **Status: DRAFT — retroactive, written 2026-08-16.**

## At a glance

**Mission:** document `toc-refresh.sh`, the one remaining script with no governing spec, and name the
tension between what it does and where this whole mission is headed.

**Approach:** one script, no changes proposed. `toc-refresh.sh` maintains `L<start>:<end>` line-range
TOCs for old-regime plan documents — exactly the mechanism
[`atomic-step-protocol-design.md`](atomic-step-protocol-design.md) retires in favor of heading-addressed
`sec`/`conv` fetch. It is not broken; it is the tool for a regime this mission is migrating away from.

**Needs you:** none blocking. Worth knowing: this script has no natural "fix" — it will become inert
once every doc it maintains has migrated to the new heading-addressed shape (per the parent design's
own Migration section), not before.

**Checklist:**
- [ ] None active. Revisit when Migration 1 (harvest) actually runs and old-regime docs start
  converting — at that point, decide whether to retire this script or keep it for whatever old-shape
  docs remain.

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then read the one step.

---

## Intent

**intent** — document `toc-refresh.sh` as-built, and name the structural tension it sits in: it exists
to maintain line-numbered TOCs for markdown plan documents (adding back-to-TOC links, regenerating a
`## TOC` block with GitHub-anchor links and `L<start>:<end>` ranges), which is exactly the mechanism
`atomic-step-protocol-design.md` names as retired: *"Line ranges are therefore retired across the whole
plans tree... They were only ever a local accelerator."* Both `conventions-tooling-spec.md` and
`checkpoint-capture-spec.md`'s own Reading Protocol sections explicitly instruct: *"There are no line
numbers, and `scripts/toc-refresh.sh` must NOT be run against this file."*

**This is not a defect in the script — it is a defect in the inventory that let it go undocumented
while the project's own direction moved past it.** `toc-refresh.sh` still correctly does what it was
built to do (idempotent back-to-TOC insertion, GitHub-flavored-markdown anchor generation, a two-pass
regeneration to stabilize line numbers after the TOC's own size changes), and is still the right tool
for any plan document that has *not yet* migrated to the new heading-addressed shape. There is nothing
to fix; there is something to eventually retire, on a timeline this spec does not set (that belongs to
the parent design's own Migration 1 schedule, not to this retroactive documentation pass).

**current call stack, as-built:**

```
plans/scripts/toc-refresh.sh <plan-file.md>
  1. add_backtoc  — insert missing [↑ TOC](#toc) links at section boundaries (sibling/parent depth
                     only; never between a section's intro and its first child)
  2. regen_toc    — regenerate the ## TOC block: GitHub-style anchors, L<start>:<end> per section
  3. regen_toc again — a second pass, because step 2 changes the file's own line count, which
                     invalidates the ranges regen_toc itself just wrote in the first pass
```

**new components** — none.

**new conventions** — none identified; this is pure utility tooling, not something a coder or planner
cites per-step.

---

## Prerequisites

None — the script already lives in `plans/scripts/`, on the `plans` branch, self-contained (no
dependency on any other script in this inventory).

**Gates** — `bash -n toc-refresh.sh`; `shellcheck` if installed. No Go, no DCO, no `make test`.

---

## Step index

**S1 — `toc-refresh.sh` (no defect found, structurally superseded, not yet retired).** Idempotent by
design (re-running on an already-processed file adds nothing new — checked directly against its own
`has_bt` guard logic in `add_backtoc`'s awk script). Its anchor algorithm matches GitHub-flavored
markdown exactly (lowercase, strip non-alnum/space/hyphen, spaces to hyphens with no collapsing — an em
dash's two surrounding spaces become a double hyphen, e.g. "Type 1 — Foo" → `type-1--foo`), which is
worth stating precisely since a hand-written anchor that doesn't match this algorithm's output would
silently produce a dead link, and nothing in the script itself would catch that. No defect found in the
script's own logic. **The only "issue" is scope, not correctness**: every new document this mission
produces (this doc included, and every addendum and spec written since 2026-08-13) is written in the
heading-addressed shape from the start and explicitly instructed never to run this tool — so this
script's active user base shrinks over time by design, not by anyone deciding to deprecate it outright.
No action item follows from that observation in this pass; it is recorded so a future session does not
rediscover the tension from scratch.
