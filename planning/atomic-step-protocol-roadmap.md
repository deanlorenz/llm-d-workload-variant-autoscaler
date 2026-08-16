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
- None blocking. Two coder-agent runs are in flight (S3 conv-rename); reconcile Addendum 6 (`/s-park`)
  with Addendum 9 (broadcast channel) whenever convenient — likely the same mechanism, not yet merged.

**Checklist — phases, in order:**
- [x] Phase 0 — design frozen (`atomic-step-protocol-design.md`, 2026-08-10).
- [x] Phase 1 — four original specs written (harvest, step-gates, authoring, role-skills); all
  reviewed by Dean as "good."
- [x] Phase 2 — read-side tooling built (`sec`/`conv`/`conv-list`/`conv-lint`, `conventions-tooling-spec.md`).
- [~] Phase 3 — write-side tooling in progress (`conventions-authoring-spec.md`: S1/S2 landed, S3 in
  progress, S4/S5 not started).
- [x] Phase 4 — governance gap found and closed: retroactive specs for all previously-undocumented
  scripts (`checkpoint-capture-spec.md`, `sync-watchers-spec.md`, `doc-tooling-spec.md`), plus a real
  guard-mechanism redesign (Addendum 10) discovered while writing them.
- [ ] Phase 5 — design review of the three new retroactive specs (Opus), before further coder work
  against them.
- [ ] Phase 6 — harvest itself (`conventions-harvest-spec.md`'s M1.2), blocked on the policy-writer
  classification table — `harvest-classification.md` exists for the two convention files only; the
  ~30 `feedback_*`/`project_*` memories and `governance-follow-ups.md` incidents are a separate,
  not-yet-started pass.
- [ ] Phase 7 — coverage audit (M1.3), stop loading old files (M1.4). Not started; depends on Phase 6.

---

## Full script inventory (as of 2026-08-16)

| Script | Spec | Status |
|---|---|---|
| `sec.sh` | `conventions-tooling-spec.md` | landed |
| `conv.sh` | `conventions-tooling-spec.md` | landed |
| `conv-list.sh` | `conventions-tooling-spec.md` | landed |
| `conv-lint.sh` | `conventions-tooling-spec.md` | landed |
| `conv-new.sh` | `conventions-authoring-spec.md` S1 | landed, `65553806` |
| `conv-edit.sh` | `conventions-authoring-spec.md` S2 | landed, `57f4874a` |
| `conv-rename.sh` | `conventions-authoring-spec.md` S3 | **in progress**, coder `f1b28556` |
| pre-commit hook | `conventions-authoring-spec.md` S4 | not started |
| README (write side) | `conventions-authoring-spec.md` S5 | not started |
| `single-instance-guard.sh` | `checkpoint-capture-spec.md` S0/S0b | **not started** — new, per Addendum 10 |
| `session-extract.sh` | `checkpoint-capture-spec.md` S1 | landed, unaffected by the guard redesign |
| `session-snapshot.sh` | `checkpoint-capture-spec.md` S2 | landed; guard block needs migrating to S0 |
| `tick-consolidate.sh` | `checkpoint-capture-spec.md` S3 | landed, no defect |
| `tick-shared-scan.sh` | `checkpoint-capture-spec.md` S4 | built, sandbox-only; guard needs migrating to S0 |
| `tick-live-index.sh` | `checkpoint-capture-spec.md` S5 | landed, no defect |
| `tier1-session-start.sh` | `checkpoint-capture-spec.md` S6 | landed, **contains Defect 1** (missing `--origin-pid`), not wired into any hook |
| `sync-main-session-start.sh` | `sync-watchers-spec.md` S1 | landed, **contains Defect A + Defect B** |
| `sync-main-watch.sh` | `sync-watchers-spec.md` S2 | landed; guard block needs migrating to S0 |
| `sync-main-once.sh` | `sync-watchers-spec.md` S3 | landed, no defect |
| `sync-main-status.sh` | `sync-watchers-spec.md` S4 | landed, no defect |
| `sync-current-watch.sh` | **none — explicitly out of scope, needs its own spec** | still on the old flock/`anchor_alive` pattern |
| `toc-refresh.sh` | `doc-tooling-spec.md` S1 | landed, no defect, structurally superseded by the mission's own direction |

**Not scripts, but part of this mission's output:** `harvest-classification.md` (partial — two
convention files done, memories/incidents pass not started), ten design addenda
(`atomic-step-protocol-design-addendum-1.md` through `-10.md`), this roadmap.

## Live defects found, not yet fixed

1. **Defect 1** (`checkpoint-capture-spec.md` S6) — `tier1-session-start.sh` omits `--origin-pid` when
   launching `session-snapshot.sh`, which requires it unconditionally (unless `--once`). Would fail
   every invocation if the hook were ever wired into `container-settings.json` — it currently isn't.
2. **Defect A** (`sync-watchers-spec.md` S1) — `sync-main-session-start.sh` omits `--origin-pid` when
   launching `sync-main-watch.sh`, which requires it with no escape at all. Same failure shape as
   Defect 1, independently discovered, in a sibling hook.
3. **Defect B** (`sync-watchers-spec.md` S1) — the same hook's comment block still describes an flock
   mechanism that no longer exists (superseded by Addendum 7's `mkdir`/`pgrep` guard, itself now being
   further revised by Addendum 10).

None of these three block anything currently running — all three affect hooks that are not yet wired
into `container-settings.json`, so nothing in production is actually broken by them today. They are
real bugs waiting to bite the moment someone flips the switch these hooks are gated behind.

## Duplication found and being fixed

The single-instance guard block (`mkdir`-based atomic dedup + `pgrep` liveness check + stale-guard
reclaim) is implemented near-identically in **three separate scripts**: `session-snapshot.sh`,
`tick-shared-scan.sh`, `sync-main-watch.sh`. [Addendum 10](atomic-step-protocol-design-addendum-10.md)
redesigns the staleness signal (pid-alive primary, mtime-age fallback) and specifies a shared library
(`scripts/lib/single-instance-guard.sh`) all three should source instead. Not built yet — this is the
S0/S0b step in `checkpoint-capture-spec.md`, blocking the guard-migration steps in both that spec and
`sync-watchers-spec.md`.

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
