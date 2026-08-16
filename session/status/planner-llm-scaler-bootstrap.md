name: llm-scaler-workspace-bootstrap Planner
id: (not surfaced to this session)
role: planner
branch: plans
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
owned_doc: planning/llm-scaler-workspace-bootstrap-design.md
task: design doc for standing up a second VSCode workspace for deanlorenz/llm-scaler (effort 2 = WVA refactor)
status_file: session/status/planner-llm-scaler-bootstrap.md

last_update: 2026-08-16T05:35:00Z
state: idle — parked
current_step: doc DRAFT complete through three rounds of Dean's rulings; three handoffs sent to the tooling planner; nothing in flight
blocked_on: (not blocked) — execution is GATED on the new plans tooling + atomic-step rules completing (R1), which this session does not own
recent_commits:
  - (see commit made by this park)

---

## What this session did

Authored `planning/llm-scaler-workspace-bootstrap-design.md` (DRAFT, ~75 KB) — a **design/discussion**
doc, not a plan, for bootstrapping a second workspace at `git@github.com:deanlorenz/llm-scaler.git`
following this environment's construction (bare repo + worktrees + plans branch + conventions + skills +
session protocol). Ran a hardcoding/portability sweep as its evidence base.

Dean issued **eleven rulings across three rounds** (R1–R11, § 0 of the doc). All six original decisions
D1–D6 are now settled or retired.

## Decisions as they stand (detail in the doc, not restated here)

- **R1 / gate:** the whole bootstrap waits on the new plans tooling + atomic-step rules (both WIP).
  Not this session's to unblock.
- **R2:** the port is an **allowlist, not a mirror** — an entry crosses only if someone can say what
  breaks without it.
- **R3:** Dean bootstraps manually; the whole `plans/` dir may be copied as **reference**. Retires D4.
- **R4:** scope is **effort 2 only**; effort 3 (KEDA scaler) is out. D1 → N/A.
- **R5:** `sync-main` must be **generalized** over (repo, container, branch), not path-fixed — the new
  repo has no `main`. → routed, see handoffs.
- **R6:** capture the **bootstrap mechanism**, not just this migration; `dean-ai-overlay` was built for
  this. Doc § 7.
- **R7:** container `.claude` must be tracked — plans holds content, container holds symlinks.
  **Already implemented**; my § 2.4 was wrong, corrected.
- **R8:** `spec-as-code` is **parked-but-wanted**, not junk. My misclassification.
- **R9:** `.bob/` + `.revisions/` — see if we can live without them; **but** a new TODO stands: correct
  **Bob-as-coder settings** under these conventions.
- **R10:** git remotes need full analysis + push protection. → doc § 2.7.
- **R11:** memory harvest gets a design doc, owned by atomic-step Type-2 work, applied in this
  migration's context. → routed.

## Two corrections I made to my own work (do not let these revert)

1. **§ 2.4 claimed the container `.claude/settings.json` was untracked.** It is a **symlink** to
   `plans/.claude/container-settings.json`. I inferred "untracked" from the container not being a git
   repo without checking the file *type*. This produced a bogus D2 counter-proposal for something
   already implemented. Dean's recollection was right.
2. **§ 2.5 classified `spec-as-code` as junk.** Wrong — parked-but-wanted (R8). General lesson now in
   the doc: *staleness is not abandonment; only the owner can tell them apart.*

## ⚠️ Findings that are live regardless of this doc

**NEW BUG, verified not inferred — `sync-main-status.sh` reports RUNNING for a dead watcher.**
`sync-main-status.sh:20-21`, duplicated at `sync-main-session-start.sh:19-20`:
`lc_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)`. **`date -d "" ` succeeds with exit 0**,
returning *midnight today* — so `|| echo 0` is unreachable and `age` becomes seconds-since-midnight.
Gate is `age -lt 150`, so **between 00:00 and 00:02:30 a dead watcher reads RUNNING**; outside that
window, STALE with a nonsense age. Verified on this machine: `date -d "" +%s` → midnight, rc=0;
`date -d "garbage"` → fallback works. **Same class as the tracked `stat -f %m` bug** — a command that
*succeeds on bad input*, so the `||` fallback never fires. Two confirmed instances ⇒ worth grepping as
a class. Routed to the tooling planner.

**`tick-live-index.sh:111` `stat -f %m` confirmed STILL LIVE** (2026-08-16) and is the only remaining
`stat -f` in `scripts/`. Already a CURRENT.md backlog item; flagged as a near-free drive-by because the
plans-tooling coder is in these files now.

**Config hazard:** `branch.main.remote` **and** `branch.ta-testing.remote` are both `upstream`. Saved
today by two layers — `remote.pushdefault=origin` and `remote.upstream.pushurl=READ-ONLY-UPSTREAM-DO-NOT-PUSH`
(an intentionally invalid URL; genuinely the best pattern here, carry it to the new repo). **The hazard
is in copying:** reproduce `branch.*.remote` while dropping `pushdefault` and both branches re-arm.

**Path-collision risk:** `~/code/llm-d/` holds ~14 sibling repos including **`llm-d-wva/`** and
**`wva-dean/`** — WVA-named, unexplained, adjacent to where a new container would go. Named, not
investigated.

## Not armed, but worth knowing

- Nothing I did touches a cluster, a remote, or another owner's doc. No push. No GitHub write.
- The doc is **uncommitted DRAFT** until this park's commit; Dean has not been asked to approve it as
  FINAL.
- `planning/harvest-classification.md` is **modified in the working tree by another session** — I read
  it but did not touch it. My requirement for it went out as a `plan__` handoff, deliberately.

## Open items (§ 6 of the doc)

1. Where the bootstrap mechanism lives — overlay vs plans-tooling vs both (§ 7.2 recommends deciding
   *after* R1's gate, since plans-tooling's final scope is unknown).
2. Is the tooling inventory complete? "Need them all" settled disposition, not exhaustiveness — and the
   R8 miss is the precedent, since the list came from CURRENT.md's view of *active* work.
3. **Bob-as-coder conventions** (R9) — how a Bob session loads the coder rulebook, respects worktree
   confinement + the write gate, joins the handoff protocol. `feedback_sendmessage_vs_file_handoffs`
   already records that the file protocol was chosen partly *because* it works cross-tool (Bob named);
   the channel exists, the rulebook-loading half does not.
4. Interpreter pin for the new container — depends on tooling that doesn't exist yet.
5. What are `llm-d-wva/` and `wva-dean/`?

## Pre-gate work that does NOT wait (§ 4)

- Trigger the memory-harvest pass (routed) — contributes the **repo-specific vs global** axis.
- Generalize `sync-main` **here**, where a real `main` exists to test against (routed).
- Write the remote-verification assertion (every push URL is `origin` or a `READ-ONLY-*` sentinel) —
  useful in *this* container immediately, then ported rather than newly written.
- Keep the § 2 sweep current; re-run is two greps (§ 8 lists them).

## Resume

Read `planning/llm-scaler-workspace-bootstrap-design.md` — § 0 for the eleven rulings, § 2 for the sweep
findings, § 3 for settled decisions, § 6 for what is still open, § 8 for sources + unverified claims.
Everything needed for a cold resume is in that doc; this file is the pointer plus the live findings above.
