# Session digest — atomic-step protocol + doc/session model

**Session:** designer role, `plans` worktree. Started 2026-08-09, continued 2026-08-10.
**Captured through:** `2026-08-09T23:49:24Z` (UTC — transcript timestamps are UTC; a local-time
marker silently skips or re-reads turns). Advanced by the checkpoint tick.
**Owned documents:** [`planning/atomic-step-protocol-design.md`](../../planning/atomic-step-protocol-design.md),
[`planning/doc-and-session-model.md`](../../planning/doc-and-session-model.md).

Successor-facing. Findings, Dean's decisions, incomplete tasks, recap, next. Not a history: moot
clarifications, edit history and superseded suggestions are deliberately absent.

---

## Dean's decisions

Authoritative. Do not re-litigate — several were reversals of my proposals.

- **`conventions/`, not `rules/`** — *"convention seems more neutral."* Vendor-neutral, and already his
  vocabulary. Artifact names follow: `### convention: <name>`, `conventions:` step field,
  `new conventions:` intent field, `conv` fetch verb.
- **Auto mode from the first run**, not an earned end state — *"manual coder is almost useless. I cannot
  read every change, too much detail. I end up approving fast, missing any key decisions."*
- **Axis B, verbatim** — *"coder stops and asks planner for directions when it is unsure. Never presume.
  Never assume. never guess. never make a judgement call. A coder should follow orders. Limited scope.
  Owns implementation not intent. Not sure -- stop. ask."*
- **Conventions are linked, not inlined** — inlining lengthens steps and long steps get forgotten. The
  round trip buys recency and is the mechanism.
- **The coder does get the narrative** — plan intent plus per-step intent, decisions and rationale.
  Only Dean-facing prose is excluded; only execution detail is deferred.
- **No rule is ever lost.** Migration (a rule moves, keeps binding) needs verification, not approval.
  **Removal** needs long probation and Dean's per-rule approval.
- **Conventions are authored like memories** — the agent writes them from what Dean said or an
  incident; he never edits the files. Never freehand; a clean process only.
- **New names for new artifacts; old files frozen, not rewritten.** The filename identifies the regime.
- **Layout stays as it is.** Moving `roles/`/`conventions/` under `.claude/` is **rejected on
  principle** (vendor-scoped directory, vendor-neutral content). Container re-root is **deferred**.
- **Own worktree for the tooling**, copied over at an atomic deliberate kickoff.
- **Doc names, not numbers, in conversation** — design, epic plan, code spec, reference, review,
  session state, policy, channel.
- **epic plan** for the breakdown doc; **policy-writer** for the policy role; **`ask`** as his token.
- **No separate landing role** — the spec owner judges push-readiness, pushes, opens the PR, follows CI.
  Triage opens on first external review.
- **Live questions go in the spec owner's chat, never the coder's** — he does not watch a coder work.
- **The epic step is mandatory**; skipping it was wrong. **One session, one role** — he has switched a
  live session mid-stream and that produced the conflation.
- **Harvest from conventions, memories, best practices and incidents** — not just the two files.
- **CURRENT.md is a ledger and calendar, not a trigger for action.** Coders never read it.
- **The checkpoint tick reads the saved transcripts, not live context** — *"It can be a periodic
  background check -- checks the previous saved jsons, compare to working doc, add state."* He also
  rejected my durability framing outright: *"not convinced. I often lose valuable decisions and next
  steps (yet to be done) when a session compacts."*
- **The digest is not session state** — *"persistence in git via CURRENT is not this — the main session
  already creates a sync__ when major events/decision happen."* Two separate channels; neither feeds
  the other.
- **What a digest must contain** — *"key finding, my decisions, steps (tasks) listed but not yet
  complete + recap + next"*; and must exclude full history, moot or already-folded clarifications, edit
  history and edit suggestions.
- **Use the doc names, never the numbers, when talking to him** (captured as memory
  `feedback_doc_names_not_numbers`).

## Key findings

- **Compaction, not crashes, is the dominant loss channel.** Transcripts are append-only and survive
  compaction (54 markers alongside 1,515 user records in one 51 MB file) — but the *working context* is
  replaced, so a dropped decision is durable on disk and unavailable to the session. Nothing bridges
  the two. **Corollary that reversed the design:** a tick distilling from live context is structurally
  blind to what a prior compaction dropped, so the tick must read the transcript.
- **User turns extract cheaply and are the highest-value content**: they are the records whose
  `message.content` is a plain string (tool results are also typed `user` but carry structured blocks).
  **25 turns / 17 KB from a 1.7 MB transcript** — a hundredfold reduction.
- **Transcript timestamps are UTC.** A local-time bound fails silently in both directions; local 02:51
  on the 10th is 23:51 UTC on the 9th.
- **Transcript findability is solved** by `scripts/session-extract.sh --list`, which prints each
  transcript with its opening prompt.
- **Writing is the save; committing is durability.** A crash loses only what was never written.
- **`plan` carries 146 of 302 handoffs (48%); `sync` carries 0.** One token absorbed several roles.
- **26 of 91 planning documents matched no naming pattern** — nine kinds we had never named.
- **11 roles vs 10 skills:** 5 map cleanly, `s-plan` covers two roles, `s-design-review` is ambiguous,
  **7 roles have no skill.**
- **`CONVENTIONS.md` cites `plans/rules/INDEX.md` as always-in-context. Both clauses are false** — the
  path has never existed.
- **`CODER-CONVENTIONS.md` §0 mandates over-reach**: *"This is your full work scope regardless of how
  the session was triggered."* Incompatible with step-atomic execution.
- **Heading-addressing retires line numbers tree-wide** — line numbers are a global index over a mutable
  document, so editing is O(whole doc) and stale ranges mis-point silently.
- The container `.claude/` is almost entirely symlinks into `plans/`, **including `settings.json`** — so
  the "untracked container config" argument for re-rooting does not hold. But `.claude/worktrees/` holds
  **261 MB of orphaned checkouts** git has already forgotten.

## Tasks listed, not complete

- **Code spec for the tooling slice** — `sec` + `conv` + `conv-list` + `conv-lint`. Next deliverable.
  Orphan worktree `plans-tooling`, golden tests against fixtures, no Go gates, no DCO.
- ~~`CONVENTIONS.md` header pointer~~ — **done**: superseded-by banner plus the dead
  `plans/rules/INDEX.md` reference corrected in place. File stays frozen otherwise.
- ~~Memory: full-names-in-conversation preference~~ — **done**: `feedback_doc_names_not_numbers`.
- Not ready to build, and why: `conv-rename` (no step manifests to scan yet), `plan-lint` (would
  validate a shape no document uses yet).

## Open questions

Dean's: what becomes of a harvested `feedback_*` memory — pointer or leave as is; whether the harvest
reaches the global `~/.claude/CLAUDE.md` rules; the checkpoint interval; the 261 MB orphaned worktrees
and the 19 registered ones, many long merged.

Design-level: **halt discovery** (a halt reaches a closed spec-owner session and surfaces nowhere —
gates unattended auto mode); **transcript findability** (82 UUID-named files, no subject index);
`s-design-review`'s true role; whether source trace / analysis / explainer / register / release
artifact become named types; how `scope:` relates to role kernels; whether `sec` and `conv` are one
script or two; whether the `scope:` hook earns its complexity; confirming the vendor prior-art claim.

## Recap

Two design documents written and committed (`611a4414`, `c0d417d1`). The coder model inverts: it holds
almost nothing and executes work orders carrying their own conventions; a step with no stated
convention halts. The taxonomy is named and the numbers retired. Migration is front-loaded — all
tooling and all harvesting first, coverage machine-checked, then the old files stop being loaded.

## Next

Write the code spec for the `sec`/`conv`/`conv-list`/`conv-lint` slice, on the orphan `plans-tooling`
worktree. Then M1.1 skills.

Two things a *successor* session must know:

- **`plans` is 9 commits ahead of `origin/plans`** (4 from this session, 5 from a concurrent one). Push
  needs Dean's explicit per-push confirmation; it has not been given.
- **Both design documents are still `Status: DRAFT`.** Flipping either to FINAL is Dean's call alone —
  plan finalization is the one review in the model that is not scriptable.
- The checkpoint tick is **session-only** and dies with this session. A successor must schedule its own.

Reaching `CURRENT.md` requires a `sync__` handoff — a designer session cannot write it (single-writer),
and per Dean that channel is already served by handoffs at major decisions, not by this digest.
