# Current md format

### convention: current-md-bounded-shape
description: CURRENT.md holds live state only; bounded shape via history.md split, rolling recent-activity window, PR Status rules, editing discipline, single-writer model, editing lock.
scope: sync session writing CURRENT.md; any session assessing what belongs there
trigger: writing to, or deciding whether something belongs in, CURRENT.md
status: active
origin: session/CONVENTIONS.md § Document Taxonomy, Type 5 — session state (C8)

**Type 5 — session state** (session/CURRENT.md)
Living work tracker; lets any new session resume without prior memory. Holds **operational
state + short abstracts only** — references permanent docs rather than duplicating them;
landed history lives in git. Updated continuously — by the plan-agent directly, or by coding
agents via handoff files.

*Bounded shape (prevents unbounded growth):*
- **CURRENT.md holds live state only.** Landed/closed history lives in the companion archive
  session/history.md — a TOC-indexed, fetch-on-demand doc (Reading Protocol + `## TOC` +
  section-at-a-time, same micro-rules pattern as Type-3 plans; index via
  plans/scripts/toc-refresh.sh session/history.md). CURRENT.md is loaded into every session's
  context via @session/CURRENT.md; history.md is **not**, so keeping it out of CURRENT.md is the
  whole point. history.md entries **may be fuller** than the old compressed tail *because* they are
  read one section at a time, never whole.
- **Recent activity** in CURRENT.md is a rolling window of **active-WIP abstracts only** (≈5 head
  items). Once an item's work has landed (merged/closed) and its substance is in git or a permanent
  doc, move it out of CURRENT.md into session/history.md → *Activity log* (as a dated 1-liner or
  fuller entry carrying a PR#/commit-SHA/doc ref) — do not leave a compressed tail accreting in
  CURRENT.md.
- **In-flight work has a permanent home too — its Type 3 plan doc.** The rule above only fires once
  an item has *landed*, so while work is in flight nothing is ever eligible to move, and CURRENT.md
  silently becomes the de-facto permanent home for WIP state. That is the one thing it must not be:
  it is the **only auto-loaded** file, while Type-3 plans and history.md are both fetch-on-demand.
  So **the planner captures state and reasoning in the Type 3 as the work proceeds** — that is where
  WIP state lives, written down as it is learned rather than reconstructed later. **CURRENT.md then
  points back to the plan: an abstract plus a pointer. It is not a state store.**
  **Per-session duty:** every planner session documents *its own* progress in *its own* plan doc, as
  it goes — not in CURRENT.md, and not on another thread's behalf. **Verbosity here tracks whether a
  thread needs its state re-stated, not whether it is still WIP.** An entry stays verbose only while
  it is being actively worked or is blocked on a named decision; once its state is documented in its
  plan, it reduces to a one-or-two-line abstract plus the ref. **A thread with no session running is
  still WIP** — so long as its plan docs and memories live, it is fully resumable, by the same session
  or a new one, and reducing its entry says nothing about whether the work is alive. Never let a
  reduced entry imply an abandoned thread: keep the ref exact, name what is owed and by whom, and
  leave any armed footgun verbose. A WIP entry exists
  for **state, recoverability and disambiguation — not brevity**, which makes the ordering strictly
  one-way: **the state must already exist in its Type 3 (or Type 1) home before any text here is
  reduced.** Never trim a WIP entry to hit a length. A length target would reward deleting state that
  has nowhere to go, which is the same loss mode the editing discipline below guards against.
- **Compressing CURRENT.md is validate-only — never edit someone else's plan doc to make room.**
  Every in-flight Type 3 / Type 1 has an owner who may be editing it right now, so the sync session
  (or anyone tidying CURRENT.md) may **only check that the content is present** in that doc. If a
  detail turns out to have **no home yet, do not write it into the plan doc**: leave the CURRENT.md
  text uncompressed and send a plan__<topic>.md handoff asking the owner to fold it in. Compression
  of that item waits for the owner. session/history.md is the one exception — it is sync-owned, so
  copy-then-verify into it directly. (Same boundary as the reviewer-writes-in-a-coder's-tree
  incident: a concurrent owner's uncommitted work is invisible to you.)
  (Diagnosed 2026-08-09, after CURRENT.md went 22.9KB → 71.2KB in eight days while remaining
  technically compliant with the landed-item rule above — the gap was routing, not size. See
  [planning/context-cost-reduction-plan.md](../planning/context-cost-reduction-plan.md).)
- **PR Status** in CURRENT.md lists **open / in-flight / actionable rows only**. When a PR merges or
  closes, move its row to session/history.md → *PR Status* sections and re-run toc-refresh.sh.
- **Completed missions** (landed multi-PR efforts) live as blocks in session/history.md →
  *Mission* sections, not in CURRENT.md — CURRENT.md keeps at most a one-line pointer plus any
  still-live forward work in § Next steps / § Issues to Open.
- **Backlogs** (Issues to Open, …) are *refs, not prose*: link the design-doc `Fnn`/`Ann`
  item or a one-line title; full prose lives in the permanent doc.
- **One source per task**: the per-task section holds the abstract; the PR-Status row is a
  one-line pointer. No triplication.

*Editing discipline (content-loss is costly):*
- **verify-or-copy-then-delete, per item.** Before removing any detail, confirm it already
  exists in its permanent home (design/plan doc, or git via a commit/PR ID). If it does,
  delete here; if not, copy it there and verify first. A forward-looking TODO with no other
  home must never be dropped. A handoff that says "drop this section" still requires the
  verification — the planner doesn't drop on the coder/reviewer's say-so, only on confirmed
  capture elsewhere. Items that have genuinely become irrelevant (a PR merged, a question
  resolved, a blocker cleared) are fine to remove outright — but state why in the commit
  message or leave a one-line history note; when in doubt, keep the content with a
  "(historical, see X)" annotation rather than delete.
- **Tidy by targeted edits, never a blind wholesale rewrite.** A full-file rewrite reconstructs
  from memory and silently loses items that don't fit the template. Edit section by section;
  if you must rewrite, diff old-vs-new and account for every removed line before committing.
- **Ref integrity.** CURRENT.md is updated *last*. When a referenced doc changes (especially
  design-doc `Fnn`/`Ann` anchors, which renumber), re-validate CURRENT.md's refs into it and
  fix any that no longer resolve.
- **Single-writer model (2026-07-28).** Only **one dedicated sync session** writes CURRENT.md
  (and other canonical session/ shared state — the PR Status table, Blocked-on, Next steps,
  Pending handoffs). Every other session — including other planner instances and auto-mode
  sessions — only *submits* handoffs; none edits CURRENT.md directly, and none invokes
  /sync-current. Scope is CURRENT.md + session/ state only; planning/ Type-3 docs remain
  multi-writer (request risky planning/ deletions via handoff to be safe).
- **Editing lock.** The session/handoffs/current__editing.md.WIP sentinel is the gate. The
  dedicated sync session creates it before writing CURRENT.md and renames it to
  `current__editing.md.DONE` after committing. Any session that sees `.WIP` refuses to sync
  and writes a `sync__*.md` handoff instead.

### convention: current-md-quick-rule
description: Before writing into CURRENT.md, ask whether it belongs in a permanent doc instead.
scope: any session about to add content to CURRENT.md
trigger: about to write into session state
status: active
origin: session/CONVENTIONS.md § Quick rule (C13)

**Quick rule.**

Before writing anything into the session state (Type 5, CURRENT.md), ask: does this belong in
a design, roadmap, task plan, or reference (Types 1–4) instead? Only keep it in session state
if it is not yet captured elsewhere. When it is captured, replace the content with a link.

### convention: current-md-per-task-sections
description: CURRENT.md is structured as per-task sections; never overwrite a sibling task's 'Last session' or other transient state when saving a different task's state.
scope: sync session writing CURRENT.md
trigger: about to edit CURRENT.md for one task while other tasks have their own sections
status: active
origin: feedback_current_md_per_task.md

When updating CURRENT.md, never overwrite an existing semantic unit (a "Last session" heading
or any task-scoped section) with a different task's content. Dean rotates between parallel
tasks, and each task's session-level state is independent and must be preserved — to save state
for the current task, add a new section or update a section that already belongs to that task;
never repurpose a sibling task's slot. Erasing a sibling task's "Last session" entry destroys its
continuity record between sessions even when long-form planning sections still exist below it —
the session entries capture session-by-session decisions and reasoning that aren't duplicated in
the plan docs, and resuming the other task cold on a later day requires that record to still be
there. Before editing any file under session/, re-read this file's own bounded-shape section
above rather than trusting recollection of "which section is mine." Treat overwriting an
existing semantic unit as a substantial edit even when the bytes-changed count is low.
