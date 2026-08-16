# Roadmap — atomic-step-protocol mission

**roadmap** (Type 2) · Living document. Updated as work lands; not a snapshot. Started 2026-08-16 —
this mission ran for several days as a design (Type 1) plus ten addenda before getting a Type 2 at all,
which is itself the gap this doc closes.

## At a glance

**Mission:** replace `CONVENTIONS.md`/`CODER-CONVENTIONS.md` (monolithic, always-loaded, no per-step
addressing) with `conventions/` + `roles/` (heading-addressed, fetched by name, harvested from every
existing source with nothing lost) — plus, along the way, real infrastructure for running multiple
agents (coder, reviewer) reliably in the background.

**Principles:**
- Migration is not removal. A rule moving needs verification it arrived, not approval. Removal needs
  long probation and Dean's explicit sign-off, per rule.
- No rule invented; every convention traces to something Dean actually said or an actual incident.
- Cost discipline: local shell computation is free, model tokens are not — push lookup/filtering work
  into scripts, only relevant output reaches a session's context.
- Reversibility, not "does this feel risky," is the axis for whether a coder proceeds-and-marks or
  halts.
- Design first, code second — when this order inverted (Addendum 7), it produced two hidden defects;
  every addendum since has been written before the code it describes, or alongside it as a revision
  target, not after.

**Approach:** see the inventory and phase breakdown below. In short — four originally-planned specs
(harvest, step-gates, authoring, role-skills) plus, discovered along the way, three more (checkpoint
capture, sync watchers, doc tooling) needed to close a real governance gap: most of this project's own
tooling had no Type 3 spec at all.

**Needs you, right now:**
- Per Dean 2026-08-16: this mission's checkpoint/sync/guard work is a **safety mechanism, not the
  highest priority** — it doesn't block other work. What's actually needed now: **missing tools,
  missing roles, the harvest.** Phase 4's checkpoint/sync governance gap (below) is CLOSED as of
  today; Phases 5-7 (review, harvest, coverage) are the live front. Reconcile Addendum 6 (`/s-park`)
  with Addendum 9 (broadcast channel) whenever convenient — likely the same mechanism, not yet merged.

**Checklist — phases, in order:**
- [x] Phase 0 — design frozen (`atomic-step-protocol-design.md`, 2026-08-10).
- [x] Phase 1 — four original specs written (harvest, step-gates, authoring, role-skills); all
  reviewed by Dean as "good."
- [x] Phase 2 — read-side tooling built (`sec`/`conv`/`conv-list`/`conv-lint`, `conventions-tooling-spec.md`).
- [~] Phase 3 — write-side tooling in progress (`conventions-authoring-spec.md`: S1/S2/S3 landed,
  S4/S5 not started).
- [x] Phase 4 — governance gap found AND CLOSED, 2026-08-16: retroactive specs for all
  previously-undocumented scripts, a real guard-mechanism redesign (Addendum 10, corrected same day
  after a real pid-vs-session_id design error), the shared guard library actually built and migrated
  into all five call sites (`session-snapshot.sh`, `tick-shared-scan.sh`, `sync-main-watch.sh`,
  `sync-current-watch.sh`, plus `tier1-session-start.sh`'s launch line), the `sync-main` family
  generalized over container/repo-identity/tracked-branch, and every live defect found along the way
  fixed. Full detail below — this phase is done, not just "in progress."
- [x] Phase 5 — design review of the three new retroactive specs (Opus, `checkpoint-specs-review.md`).
  All 10 findings closed: Finding 2 resolved against the corrected Addendum 10 design (was framed
  against a since-retracted premise); Findings 1/3/4/5/9 fixed in the specs and/or code; Findings 6-8/10
  were "worth noting," folded in.
- [ ] Phase 6 — harvest itself (`conventions-harvest-spec.md`'s M1.2). The repo-scope/global
  classification axis is now designed (`harvest-classification.md`, 2026-08-16) but the harvest pass
  over the ~30 `feedback_*`/`project_*` memories and `governance-follow-ups.md` incidents has not
  run — **per Dean, this is now a live priority, not a deferred one.**
- [ ] Phase 7 — coverage audit (M1.3), stop loading old files (M1.4). Not started; depends on Phase 6.
- [ ] **New, not yet a phase**: missing roles (per Dean 2026-08-16, needed now, not designed yet —
  `role-skills-spec.md` covers role *skills* mechanics, not which roles exist or what's missing).
- [ ] **Coverage-audit and step-gate tooling — specced but never built, absent from this roadmap's
  own tracking until 2026-08-16.** `conventions-harvest-spec.md` S1 (`coverage-check`) and
  `step-gates-spec.md` S1-S6 (`step-check`, `plan-lint`) are both fully executable specs (do/verify/
  done_when present throughout) sitting in `DRAFT — awaiting Dean's finalization` status, but were
  never assigned to a coder or listed in the script inventory below. Both are **hand-to-coder now**
  per Dean's direct instruction — `step-gates-spec.md` has no dependency on the harvest and can build
  immediately; `conventions-harvest-spec.md` S1 (`coverage-check`) can run against an empty
  `conventions/` and record a baseline, so it doesn't need to wait for Phase 6's actual harvest pass
  either.
- [ ] **Rule-outline/trigger-index mechanism (Addendum 5) — deliberately delayed** (Dean, 2026-08-16):
  *"important but let's delay this. Start from full list (still saves 3x over current conventions).
  We can switch later, see if mechanism works."* The two/three-tier index (main index always loaded →
  sub-index per category → full convention on demand) stays a "try later" idea; the harvest proceeds
  on the current flat `conv <name>` fetch-by-name mechanism, which is already ~4.7× cheaper than
  today's always-loaded `CONVENTIONS.md`/`CODER-CONVENTIONS.md`. Memory-shaped sub-index question
  (Addendum 5 §"memory to fetch rule outlines") folds into the same delayed item — Dean: *"seems
  identical to [the trigger-index question]. Should be captured in same doc."* Both should live
  together wherever Addendum 5 is revisited, not as two separate future items.
- [ ] **Reaffirmed rule bundle (Addendum 4) — approved, needs a real design pass, not yet done.**
  Dean, 2026-08-16: *"yes. must plan."* Extends the original question with a template mechanism:
  *"a rule or step could fetch a 'pre-baked' prompt template — here is a list of things you need to
  do to fulfill this step, here is the checklist... can that be written as a rule? I suppose so, but
  as a template it can fill with concrete values."* So the design isn't just "cite a bundle of
  existing rules to reaffirm them" (Addendum 4's original framing) — it now also covers a
  **parameterized checklist template** a step can fetch and fill with the step's own concrete
  values, which reads as a genuinely new mechanism, not just a naming question for the existing
  `conventions:` field. Needs a real Type-3-or-addendum-level design pass before building; not
  attempted here.
- [ ] **Mid-turn note handling (Addendum 12) — raised 2026-08-17, real candidate mechanism proposed
  same day, not yet designed in full.** Dean observed this session handling mid-turn notes well by
  carrying full conversational context, and asked to formalize the pattern — flagging two real, separate
  open questions (disruption to the main thread; session-independence). **Reframing proposed by Dean**:
  don't route at capture time — append a raw candidate to a maintained, plan-like file (cheap, needs no
  judgment), and have the **policy-writer** role (one of the eleven roles, "missing entirely" — not yet
  built, per `doc-and-session-model.md`) periodically consolidate the candidates file, using the same
  skill mechanism in a different mode. Splits one hard problem (route correctly, immediately, regardless
  of session) into two easier ones (capture faithfully, immediately vs. consolidate correctly,
  periodically, by one specific role) — substantially eases both original questions without fully
  closing either (see the addendum's own § for exactly what remains open). Confirmed same day, checked
  directly: this is not Addendum 4 raised twice — it *is* Addendum 4 (2026-08-13), same idea, correctly
  cross-referenced. **Second pass, same day, raises the bar rather than closing it**: no policy-writer
  session will typically be alive to consolidate, so (a) a candidate entry must be rich enough for a
  cold-start rework, not a pointer a live consolidator would flesh out from memory, and (b) something
  needs to actively surface that candidates are pending — Dean's own suggestion, whichever session is
  "always running (like sync__)" alerts him, rather than relying on anyone noticing unprompted. Neither
  designed yet.
- [ ] **Channel protocol (Addendum 9) — designed 2026-08-16, real detail, NOT yet an executable
  spec.** Mailbox files (`session/mailboxes/<channel>.log`, one per relationship, append-only,
  two event types) plus a shared broadcast/discovery channel (`session/mailboxes/broadcast.log`,
  three usage patterns — lookup, presence announcement, general broadcast — riding the same file).
  Directly answers today's own C11 fix (the addressless "broadcast handoff" mess) and the
  live-session-identity gap from `doc-and-session-model.md` item 5 — this is the actual mechanism
  that should replace both, once built. **Not hand-to-coder-ready like step-gates/coverage-check
  above**: no do/verify/done_when steps exist yet, and several things are explicitly "not yet
  decided" in the addendum itself (exact line grammar/prefixes, whether `announce` lines get
  pruned, the shared lookup script's own name). Needs a Type-3 code spec written from this design
  before dispatch. Also explicitly gated on reconciling with Addendum 6 (`/s-park`) first — likely
  the same underlying mechanism, not yet merged into one design.
- [ ] **Addendum 2 (shared Tier-2 consolidation) — built, its own checklist is now stale.** Guard
  rebuild it asked for is done (`f9e1dba6`, today). Two items from its own checklist never made it
  into this roadmap: hand ownership of `tick-shared-scan.sh` to a live sync session, and authorize
  the first real (non-sandbox) start. Both still open; not urgent per Dean's own "safety mechanism,
  not blocking" framing for this whole cluster.
- [ ] **Addendum 3 (CURRENT.md indexable) — correctly self-parked, cross-referencing here so it
  isn't invisible.** Deprioritized by Dean 2026-08-15/16, "not a priority, left for later." No
  active checklist in the addendum itself; nothing to do until revisited.
- [ ] **Addendum 6 (`/s-park`) — corrected 2026-08-17 (Dean): only HALF is built.** `s-state-park`
  (`.claude/skills/s-state-park/`) exists and does the *flush* half well — a session's own decisions,
  findings, footguns, subagent resume addresses, additive-only, run proactively at risk points
  including "Dean says he's closing the laptop." **Checked directly**: it is self-invoked, one
  session flushing its own context — it does not send anything that reaches *other* live sessions.
  Addendum 6's original ask was specifically the other half — a signal reaching **every** live
  session at once (*"I run this to notify all... all would finish what they do, stop, and report
  ready for parking"*) — which is exactly the still-missing broadcast/discovery channel from
  Addendum 9, not a duplicate of `s-state-park`. So: the *action* each session takes on being told to
  park is built; the *telling* is not. Still blocked on Addendum 9 as stated above, now for the
  precise reason (Addendum 9's broadcast log is the mechanism that would carry the `please-park`
  signal to `s-state-park` in each session, not a separate `/s-park` skill to build from scratch).

---

## Full script inventory (as of 2026-08-16, end of day)

| Script | Spec | Status |
|---|---|---|
| `sec.sh` | `conventions-tooling-spec.md` | landed |
| `conv.sh` | `conventions-tooling-spec.md` | landed |
| `conv-list.sh` | `conventions-tooling-spec.md` | landed |
| `conv-lint.sh` | `conventions-tooling-spec.md` | landed |
| `conv-new.sh` | `conventions-authoring-spec.md` S1 | landed, `65553806` |
| `conv-edit.sh` | `conventions-authoring-spec.md` S2 | landed, `57f4874a` |
| `conv-rename.sh` | `conventions-authoring-spec.md` S3 | landed, `afd17a4a`, reviewed clean (37/37 tests) |
| pre-commit hook | `conventions-authoring-spec.md` S4 | not started |
| README (write side) | `conventions-authoring-spec.md` S5 | not started |
| `single-instance-guard.sh` | `checkpoint-capture-spec.md` S0 | **landed**, `f9e1dba6`, corrected design (session_id/role-constant key, not pid) |
| S0b handle registry | `checkpoint-capture-spec.md` S0b | still not designed in detail |
| `session-extract.sh` | `checkpoint-capture-spec.md` S1 | landed, no defect |
| `session-snapshot.sh` | `checkpoint-capture-spec.md` S2 | landed, guard migrated (`f9e1dba6`); marker-poisoning bug found+fixed (`31d9911a`) |
| `tick-consolidate.sh` | `checkpoint-capture-spec.md` S3 | landed, no defect |
| `tick-shared-scan.sh` | `checkpoint-capture-spec.md` S4 | landed, guard migrated (`f9e1dba6`); still not run live (operational, not a defect) |
| `tick-live-index.sh` | `checkpoint-capture-spec.md` S5 | landed; known latent `stat -f %m` bug, tracked in CURRENT.md, left out of scope |
| `tier1-session-start.sh` | `checkpoint-capture-spec.md` S6 | landed, Defect 1 **FIXED** (`5ae7fec2`); still not wired into `container-settings.json` — needs Dean's approval |
| `sync-main-session-start.sh` | `sync-watchers-spec.md` S1 | landed, Defect A + Defect B **FIXED** (`d036c054`); config-driven (`4c6f646b`) |
| `sync-main-watch.sh` | `sync-watchers-spec.md` S2 | landed, guard migrated + Defect C fixed (`f9e1dba6`); config-driven (`4c6f646b`) |
| `sync-main-once.sh` | `sync-watchers-spec.md` S3 | landed, config-driven (`4c6f646b`) |
| `sync-main-status.sh` | `sync-watchers-spec.md` S4 | landed, dead-watcher-reads-RUNNING bug **FIXED** (`4aa81218`); config-driven (`4c6f646b`) |
| S5 `sync-main-config.sh` + `sync-main.conf` | `sync-watchers-spec.md` S5 | **new, landed** `4c6f646b` — generalizes the whole family over container/repo-identity/tracked-branch |
| `sync-current-watch.sh` | `sync-watchers-spec.md`, own section | guard migrated + kill-switch fixed + status-lies bug fixed, `b60cb935` |
| `toc-refresh.sh` | `doc-tooling-spec.md` S1 | landed, no defect, structurally superseded by the mission's own direction |

**Not scripts, but part of this mission's output:** `harvest-classification.md` (repo-scope/global
axis designed 2026-08-16; the ~30-memory harvest pass itself still not run — **now a live priority
per Dean, not deferred**), eleven design addenda (`atomic-step-protocol-design-addendum-1.md` through
`-11.md`), the call-stack convention generalized into `doc-and-session-model.md`, this roadmap.

## Live defects — ALL FIXED as of 2026-08-16

Every defect this roadmap previously tracked as open is now closed. Kept here as a record, not a
todo list:

1. **Defect 1** (`checkpoint-capture-spec.md` S6) — `tier1-session-start.sh` omitted `--origin-pid`/
   `--session-id`. **Fixed**, `5ae7fec2`.
2. **Defect A** (`sync-watchers-spec.md` S1) — `sync-main-session-start.sh` omitted `--origin-pid`.
   **Fixed**, `d036c054`.
3. **Defect B** (`sync-watchers-spec.md` S1) — stale flock/anchor comment. **Fixed**, `d036c054`.
4. **Defect C** (`sync-watchers-spec.md` S2, found in design review) — `sync-main-watch.sh`'s status
   file lied about liveness after a crash. **Fixed**, `f9e1dba6`.
5. **`sync-main-status.sh`/`sync-main-session-start.sh` dead-watcher-reads-RUNNING** (`date -d ""`
   succeeds and returns midnight, defeating the `|| echo 0` fallback) — found in the llm-scaler
   portability sweep. **Fixed**, `4aa81218`.
6. **`session-snapshot.sh` marker poisoning** — a user turn's own `## `-headed text could poison the
   Tier-1 marker, causing silent multi-day capture loss (confirmed live on two real sessions). **Fixed**,
   `31d9911a`.
7. **`sync-current-watch.sh`'s kill-switch and status-lies bug** — was checking "any Claude process
   anywhere," not the originating one; same status-hardcoding bug as Defect C. **Fixed**, `b60cb935`.

## Duplication — FIXED

The single-instance guard block was implemented near-identically in five separate call sites.
[Addendum 10](atomic-step-protocol-design-addendum-10.md) (corrected same day after a real
pid-vs-session_id design error was found and fixed) specified a shared library; **built and migrated
into all five**: `session-snapshot.sh`, `tick-shared-scan.sh`, `sync-main-watch.sh`,
`sync-current-watch.sh` (`scripts/lib/single-instance-guard.sh`), plus the config-loading duplication
across the four `sync-main-*` scripts, also collapsed into a shared library
(`scripts/lib/sync-main-config.sh`, new with S5).

## Low-priority backlog, tracked not urgent

- **`planning-map.md` refresh tool** — no mechanism keeps `planning/planning-map.md` current as
  docs land or get superseded. Two options floated, not decided: a `toc-refresh.sh`-style regen
  script, or treat it as a point-in-time snapshot regenerated on request. Per
  `plan__planning-map-refresh-tool-todo.md` (sync-session, 2026-08-15) — explicitly "not urgent,"
  same family as this mission's own tooling but not blocking anything.
- **Token accounting on automatic activity** — [Addendum 11](atomic-step-protocol-design-addendum-11.md)
  states the requirement (every auto-tool records spend; total consumption from automatic protocols
  must be bounded, per two prior incidents — chatty handoff cycles, 30s-cadence monitors). No general
  bound mechanism exists yet beyond Tier-2's own `--daily-cap`; `sync-current-watch.sh`'s 30s poll
  loop is the concrete example cited, left unchanged pending a real design pass.

## Background-agent infrastructure, built alongside the specs

Two background agents (coder, internal-code-reviewer) launched and operated 2026-08-15/16 against the
`plans-tooling` branch. Real findings, all recorded in
[`atomic-step-protocol-design-addendum-8.md`](atomic-step-protocol-design-addendum-8.md):
`--permission-mode acceptEdits` blocks a background agent that has nobody to answer its prompts (use
`auto`); `SendMessage`/`ListAgents` cannot reach `claude --bg` agents at all, confirmed by direct
research (they are architecturally out of that tool's addressable set, not a naming bug); the only
reliable way to send a running background agent new instructions is a file-based handoff — which
directly motivated [Addendum 9](atomic-step-protocol-design-addendum-9.md)'s mailbox/broadcast redesign,
since neither agent polls `session/handoffs/` on its own without being told to check at a specific
moment.
