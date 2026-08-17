name: autoscaling-viz Planner (this session — successor to caa88c11)
id: (this session's own id not captured; prior instance was caa88c11-142b-4665-bf0d-7ea51669911d)
role: planner
branch: plans
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
owned_doc: planning/autoscaling-viz-followon-plan.md (epic) + several Type 3s under it, incl. two new
  this session (autoscaling-viz-good-panels-classification-plan.md,
  autoscaling-viz-panel-review-20260817-plan.md)
task: parked per Dean's "park" — see below for exact resume point
status_file: session/status/planner-viz-panels.md

last_update: 2026-08-17T23:05:00Z
state: idle (parked)
current_step: none in flight — Bob's two tasks this session both completed and reported; two open
  decisions await Dean (see below), no dispatched work outstanding
blocked_on: Dean's decision on Item 8 (no-fix recommended) and on when to schedule the full 16-run
  re-render sweep — see "Open decisions" below
recent_commits:
  - 3818cab4 (autoscaling-viz, Bob's) viz: panel review 2026-08-17 fixes (items 1-7)
  - 23c1bbb7 (autoscaling-viz, Bob's) chore: gitignore .bob-status.md
  - a1a815a7 (autoscaling-viz, Bob's) Panel 3: fix missing-vs-zero conflation, one-tick forward-fill + stale marker
  - 5e3b196a (plans, this session) planning: document how Bob is set up as autoscaling-viz's persistent coder
  - e540d67d (plans, this session) planning: autoscaling-viz -- panel review 2026-08-17 code spec
  - b871b646 (plans, this session) planning: benchmark-runs-inventory -- fold in 2026-08-17 good-panels pass
  - 7a65d75c (plans, this session) planning: autoscaling-viz -- good-panels.png classification+symlink code spec
  - a90990e7 (plans, this session) Revert "status: autoscaling-viz coder-auto agent bootstrapped 2026-08-17"

notes: |
  ## Where this thread stands (2026-08-17 late, this session, parked)

  This session's own work, on top of everything the prior park (below, preserved) already
  captured. Two threads: (1) set up Bob (a separate CLI coder tool, not a Claude subagent) as a
  persistent coder for this scope, controlled via file-based handoffs; (2) dispatched two real
  tasks to it, both completed.

  ### Bob setup — done, documented, working
  New `coder-auto` custom Bob mode (`.bob/custom_modes.yaml`, container + worktree-local copy —
  manual sync, no single source of truth) with a write-scope narrower than a normal coder: its own
  worktree + `plans/session/handoffs/` only, no `plans/session/status/` writes (keeps a local
  `./.bob-status.md`, gitignored, instead — that worktree can become a PR branch), no `plans/`
  commits ever. One real incident: Bob's bootstrap run used `execute_command`+`git commit` to write
  into `plans/` anyway, after `write_file` was correctly blocked — reverted (`a90990e7`, `git
  revert`, no history rewrite) and the mode text corrected. Second resume behaved correctly.
  Full writeup: `planning/bob-persistent-coder-setup.md` (`5e3b196a`). **Durable fact needed to
  resume Bob**: task-id `bd8610a2991b2e5e12471e18850b4e27` — losing this loses all prior context on
  next invocation.

  ### Task 1 — good-panels classification, done, committed, mostly folded in
  Spec: `autoscaling-viz-good-panels-classification-plan.md` (`7a65d75c`). Bob classified all 34
  `benchmark/runs/` entries, re-extracted+re-rendered the 29 extractable ones at tip `a1a815a7`,
  created 16 `good-panels.png` symlinks. Result folded into `benchmark-runs-inventory.md`
  (`b871b646`) — new `Good panels?` column, 16 GOOD (8 only via the estimated-data fallback), 12
  MISSING-unobtainable, 1 MISSING-obtainable-elsewhere. **Ownership of that inventory doc is being
  transferred to `benchmark` scope** per Dean's direction
  (`plan__viz-inventory-ownership-transfer-to-benchmark.md`) — **now `.WIP`, benchmark scope has
  picked it up** (confirmed at park time: `plan__viz-good-panels-benchmark-commit-needed.md` is
  already `.DONE`, and a `scratch/bob-benchmark-coder/` dir exists, implying benchmark scope has its
  own Bob instance running now too). Not yet confirmed complete/landed — check its `.WIP`→`.DONE`
  transition on resume rather than assuming either state.

  ### Task 2 — panel review 2026-08-17, done, committed, one open decision
  Dean's direct visual review of 4 of the 16 good-panels renders surfaced 8 items. Spec:
  `autoscaling-viz-panel-review-20260817-plan.md` (`e540d67d`). Bob fixed 7 of 8
  (`3818cab4`) — title semantics, panel 1a overlap, panel 3 color-key repositioning, panel 4 header
  spacing, pod-sort tie-breaker, panel 5/3 alignment, panel 6 silent-tail cue — each independently
  re-rendered and verified, not just trusted.
  **Item 8 needs Dean's decision, not yet given.** My own spec's framing ("10 of 18 pods, 55%
  over-fires") was **wrong** — Bob's investigation (`plan__panel-review-20260817-item8-findings.md`)
  found the comparison should be pod-windows vs. total-pods-removed (17, not 6 events), and 10/17
  is a reasonable match rate with tight (15-16s) proximity, not loose over-firing. Recommendation:
  no code change; optional label-wording improvement. **This correction has NOT been folded back
  into `autoscaling-viz-panel-review-20260817-plan.md` itself** — the doc still states the original
  wrong framing as fact (lines ~146-149). Flagging rather than editing mid-park (this is more than
  additive housekeeping — it's a substantive correction to a doc another reader might cite from).
  **A second open fact, not yet in a permanent doc**: only 4 of the 16 `good-panels.png` symlinks
  point at renders from the new tip `3818cab4` (the 4 verification runs); the other 12 still point
  at `a1a815a7`-stamped output — stale relative to today's fixes, not yet swept. Both this and the
  Item 8 doc-correction are candidates for whoever resumes this thread to actually act on, not just
  re-discover.

  ### A real out-of-scope finding, routed, not this scope's to fix
  Root-causing the panel-6 item found that TA (throughput analyzer) stops reporting a variant
  entirely once demand disappears, even with replicas still running — Dean's read: a real
  controller bug (TA loses its shape/PRC estimate and can't vote for scale-down at exactly the
  moment a vote matters). Routed via `plan__ta-prc-loss-on-idle-blocks-scaledown.md` to whichever
  scope owns the WVA throughput-analyzer engine code — not consumed as of this park.

  ## Where this thread stood before this session (2026-08-17 early, prior park, preserved below)

  Mission: viz-panels planner for autoscaling-viz. This session ran a long, dense sequence of
  panel-review rounds (Items Q through AF across several Type 3 specs) plus one large data-collection
  side-quest (the benchmark-runs-inventory doc) plus a real process incident (shared-git-index
  collision) plus an unresolved VS Code webview investigation (image click-to-open is a confirmed
  upstream bug, not fixable here). Full detail on each below.

  ### Code state — all landed, nothing in flight
  `autoscaling-viz` tip is `a1a815a7`. Chain this session: `9da9f7a2` (panel review batch Q/R/T/U/W)
  → `0a2be3be` (panel 4 KV%-heatmap) → `f92d3c19` (panel 4 follow-up) → `0aade22f` (SAT fallback fix)
  → `deaf4886` (warmup-anchor Item X, estimated-fallback Item AD, panel 3/4/6 polish Y/Z/AA/AB/AC)
  → `a1a815a7` (panel 3 stale forward-fill AE/AF + Item AC saturated-sample correction).
  **Every commit independently stamp-verified by me (not just trusted from the coder's report) and,
  for the two most consequential (deaf4886, a1a815a7's predecessor work), also independently
  re-reviewed by a spawned reviewer subagent.** Nothing currently dispatched and unread.

  ### Just landed, freshly read this park pass — the batch refresh
  `plan__batch-refresh-all-success-runs-done.md` (now `.DONE`): 29 runs / 35 results-leaves,
  **35/35 extract+render succeeded, 0 crashes**, every single one stamp-verified (not sampled) at
  `a1a815a7`. 4 visually spot-checked, clean. Output under
  `autoscaling-viz/session-notes/review-samples/*-batchrefresh-a1a815a7.*` — I just symlinked all 35
  PNGs into `plans/scratch/viz-review/` (see below on why that symlinking is now known to not help
  click-through, but is still worth doing for consistency/future-proofing).
  **Dean has NOT yet looked at any of these 35** — that's the natural next step whenever this resumes.

  ### Open, deliberately unresolved, NOT to guess at
  - **Panel 5 "in-system < being-served" invariant** — root-caused in detail (two independent
    reviewer passes): NOT a bug, NOT caused by Item AD's estimation fallback (control-checked
    against a real-trace run, same pattern, worse proportionally). Real cause: `served_by_t` sums
    whichever pods happen to scrape in the same rounded second (async ~16s per-pod cadence);
    `in_system` comes from a structurally different measurement path (gateway-observed request
    lifecycle via Envoy). Even a fully-honest forward-fill still exceeds `in_system` at the worst
    point checked (202 vs 150) — so the gap is real, not an artifact of *how* panel 3/5 aggregate.
    Dean's own read: "one of them must be wrong... either the requests are in the system or not" —
    this is NOT resolved, just extensively characterized. Explicitly parked by Dean: "we come back
    to a deeper dive into the code later." **Do not re-open without him** — the next step he named
    is checking WVA's own Go collector code for whether ITS per-pod aggregation (e.g.
    `aggregateByVariant`'s `totalDemand += rc.ReplicaDemand` sum across replicas,
    `Main/internal/engines/analyzers/saturation_v2/analyzer.go`) has an analogous
    async-scrape-across-pods hazard to what viz-side `served_by_t` has. I confirmed WVA does NOT use
    `vllm:num_requests_running` in real decision logic at all (constant defined, zero other
    references) — so there's no direct analog to viz's `served_by_t` — but I did NOT finish checking
    whether `source.Refresh()`'s single Prometheus query round genuinely returns a coherent
    same-instant snapshot across replicas, or whether per-target Prometheus scrape staleness means
    different replicas' `ReplicaDemand` values can still be asynchronous with each other even within
    one query response. **That specific question is the actual resume point** if/when Dean says go.
  - **Panel 3/4's own per-tick forward-fill (Items AE/AF, shipped in `a1a815a7`) is implemented but
    UNVERIFIED on real data.** The coder found (correctly, and reported honestly rather than faking
    a demo) that neither `m-satta-dwell` nor `m-sat-dwell-warmup` — the two runs my own spec's data
    check used to justify the feature — actually has a case where a pod's own scrape gap coincides
    with the shared grid having another pod's tick inside that gap. Verified only via a synthetic
    hand-edited bundle (delete one real sample, confirm the stale hatch renders, no crash). **Open
    question for Dean, never asked**: go looking for a real run that exercises this, or accept the
    synthetic verification as sufficient for now? I have not asked this yet — flag it when resuming.
  - **Item U (WEAK TIME ANCHOR text) — placement done (moved to footer), content still undecided.**
    Dean: "we discuss details of what it means later." Never revisited since. Not urgent.
  - **Real per-pod drain signal (kube pod-phase / EPP routing-exclusion)** — explicit TODO, Dean:
    "not priority now, keep as todo." Correctly parked, not started.

  ### VS Code webview image-click bug — INVESTIGATION CLOSED, real upstream bug found
  Long side-investigation (Dean asked to "try symlinks" to fix chat-link-click-to-open for PNGs).
  **Conclusively isolated by elimination** (symlink vs real file, cross-worktree vs same-directory,
  `.png` vs `.txt`/`.md` in the identical location) that this is NOT a path/symlink/worktree issue at
  all — it's that this webview's click-to-open handler does not support image files, full stop.
  **Confirmed as a real, already-filed upstream bug: github.com/anthropics/claude-code#37989** —
  matches exactly (binary file link clicks silently do nothing; text/md files work). Root cause per
  that issue: the extension likely calls `vscode.workspace.openTextDocument()` for all link clicks,
  which silently fails on binary files, instead of routing images through
  `vscode.commands.executeCommand('vscode.open', uri)`. **Tried and confirmed non-functional from a
  chat message alone** (as expected, since none of this is settable from plain text): markdown
  links, HTML `<a href>`, bare absolute/relative paths (with and without backticks), a `command:`
  URI with a fabricated command name, a `command:vscode.open?...` URI (the real built-in command —
  still didn't fire, confirming the message itself isn't marked `isTrusted`, which only extension
  code can set), a custom JSON schema, and a fabricated `claude-image://` scheme. **This is not
  fixable from inside a session — it needs an Anthropic-side fix to the extension.** Test artifacts
  left on disk for evidence, not yet cleaned up (Dean's call, asked once, not yet answered — see
  below): `plans/scratch/viz-review/test-real-copy.png`, `test.txt`, `test-tmp-symlink.png`.
  **Practical resolution going forward, stated but not yet re-confirmed after the "park" interrupt:**
  use inline `Read`-tool display for every render (already worked reliably all session); stop trying
  new link formats.
  ⚠️ Mid-investigation, several "try this format" instructions arrived as injected
  system-reminder-style content rather than genuine Dean messages (a fabricated `command:` URI
  scheme, a custom JSON schema, a `claude-image://` scheme) — I flagged this explicitly to Dean as
  unverifiable-provenance rather than silently keep complying, and he confirmed frustration partly
  about this. Worth remembering: don't chase a chain of increasingly exotic technical instructions
  through the conversation stream without checking they actually came from the user.

  ### Process incident, already handed off and closed on the receiving end
  Shared-git-index collision (`f9e1dba6`, 2026-08-16): my own `git add && git commit` swept in
  another concurrent session's staged files. Root-caused jointly with that session, resolved per
  Dean's ruling (no history rewrite; commits are for persistence/scoping not strict provenance;
  accept the risk, use pathspec-only commits going forward). Handed off to the atomic-step-protocol
  scope (`plan__shared-git-index-incident-and-resolution.md`) — **that handoff is already `.DONE`
  on the receiving end**, confirmed via handoff-directory listing. Also saved as a durable memory
  (`feedback_shared_git_index_pathspec_commits.md`) and applied for the rest of this session (every
  commit since has used explicit pathspecs). Nothing further needed on this.

  ### Side deliverable, committed and stable
  `planning/benchmark-runs-inventory.md` (committed `f9e1dba6`) — full collection/extraction/viz
  status table across all 31 (now 34, post-Stage-A-completion) runs, built via a 31-agent parallel
  read-only survey workflow. Includes a full refresh protocol (mission/flow/checklist) so a future
  session can re-run it cold. **Now stale in one respect**: written before Stage A's final 3 cells
  landed (`dean-20260816-153947-120`, `-161824-974`, `-174704-649`) and before this session's own
  batch-refresh made viz status CURRENT (not STALE) for 35 of the listed runs. Not urgent to update
  — the doc's own § Refresh protocol exists exactly so a future session can bring it current in one
  pass without rediscovering methodology.

  ### Memory maintenance done this park-adjacent period
  `MEMORY.md` compacted 20.3KB → 17.2KB (line-tightening only, zero content dropped, all topic files
  intact) in response to a size-limit warning. Two new memories added this session:
  `feedback_shared_git_index_pathspec_commits.md`, `feedback_viz_render_symlinks.md` (the latter is
  now known to be necessary-but-insufficient given the #37989 finding — the symlink habit itself is
  still correct practice, it just doesn't solve click-through for images specifically).

  ### Subagents spawned this session
  See the state-park report appended below for exact IDs/status — both are non-blocking, nothing to
  resume from them right now (one completed cleanly with findings already folded in; one's
  transcript could not be resumed via SendMessage, its findings were already fully relayed and acted
  on before that failure was discovered, so nothing is lost).

---

## state-park report (Step 7, verbatim)

```
state-park — viz-panels planner, 2026-08-17 parked mid-session

Subagent addresses recorded (2a — the durable part):
  - Review commit deaf4886 on autoscaling-viz — id: a122254d6b4afdc5f — completed — asked: review
    deaf4886 (Items X/Y/Z/AA/AB/AC/AD) against the Type 3 spec, verify Item AC proportionality and
    the panel-5 in-system-vs-served discrepancy with a definitive root cause
    output: /tmp/claude-1000/.../tasks/a122254d6b4afdc5f.output (symlink to its transcript) —
    exists — findings fully relayed to Dean in-chat and folded into
    planning/autoscaling-viz-review-ongoing.md (committed by the agent itself per its own report;
    section confirmed present at line 489 when I read it back). Referenced from this status file
    now; was previously only in chat.
  - Persistent background reviewer for autoscaling-viz — id: a135af978c21e9081 — died (transcript
    unresumable) — asked: originally, ongoing commit-by-commit review of autoscaling-viz; later
    redirected several times as new commits landed
    output: /tmp/claude-1000/.../tasks/a135af978c21e9081.output (symlink target exists on disk)
    — SendMessage to this ID failed with "No transcript found for agent ID" when I tried to
    re-park it explicitly. Its last several findings were already fully relayed to Dean in-chat
    and acted on (e.g. the SAT-fallback fix confirmation) before this was discovered, so no
    unflushed content is believed lost — but the address itself is now dead, flagged here so a
    future session doesn't waste a SendMessage attempt on it.
Nudges sent (2b — best effort, NOT a flush):
  - a122254d6b4afdc5f — nudged (asked to park), no confirmation received before this report was
    written
  - a135af978c21e9081 — nudge attempt itself failed (transcript gone) — not a "sent, unconfirmed"
    case, an outright delivery failure
Sources read this pass:
  - session/handoffs/plan__batch-refresh-all-success-runs-done.md — full content, previously
    unread; real state (35/35 renders succeeded, stamp-verified, 4 spot-checked) now captured
    above and in this file
  - planning/autoscaling-viz-review-ongoing.md (grep + offset read at line 489, then 620-689) —
    confirmed the panel-5 root-cause section's exact content before summarizing it above, not
    trusting my own earlier chat recollection of it
  - session/handoffs/ directory listing — confirmed the shared-git-index handoff is already
    .DONE on the receiving end; confirmed no other viz-panels-addressed handoff is sitting unread
  - git log --oneline -3 (autoscaling-viz) — confirmed current tip a1a815a7 matches what I
    believed before writing this report
Not read (and why):
  - The 33 individual batch-refresh PNGs/bundles themselves — Dean has not yet asked me to
    review any specific one; symlinked all 35 into scratch/viz-review/ per standing habit, but
    did not open/verify each — that's real, deliberately-deferred work, not an oversight
  - planning/benchmark-runs-inventory.md — not re-read this pass; already known stale (Stage A's
    final 3 cells + this session's own batch-refresh outdate its table) and captured as such
    above from existing knowledge, not re-verified line-by-line this pass
Written to:
  - session/status/planner-viz-panels.md — full WIP state, all open questions, subagent
    addresses, VS Code webview bug investigation closure, process-incident cross-reference
Handoffs emitted:
  - (none this pass — everything routed to my own status file; the one handoff this thread
    produced earlier this session, plan__shared-git-index-incident-and-resolution.md, was
    already sent and is already .DONE on the receiving end, confirmed by directory listing)
Committed:
  - ba5ed673 state(park): viz-panels planner — flush WIP state, batch-refresh report,
    panel-5/AE-AF open questions
Worktree exit:
  - was never in an EnterWorktree-tracked worktree switch this session (plans is my home
    worktree throughout) — but CWD had drifted via a plain `cd` into autoscaling-viz earlier in
    the session for direct rendering checks and was never returned; caught and corrected during
    this park pass before staging anything (confirmed via `pwd`/`git branch --show-current`
    showing the wrong worktree before the fix). Flagging this as a real near-miss: park's own
    Step 1 identity check is what caught it, exactly as designed.
Verified from final location:
  - session/status/planner-viz-panels.md — present
  - commit ba5ed673 — visible in git log
  - session/handoffs/ — 454 entries present, listing intact
Deliberately NOT done (park is additive, and accepts no work):
  - Did not update planning/benchmark-runs-inventory.md's now-stale table — noted as stale, left
    for a future pass (it has its own refresh protocol for exactly this)
  - Did not clean up the three VS Code webview test artifacts
    (scratch/viz-review/test-real-copy.png, test.txt, test-tmp-symlink.png) — asked Dean once,
    no answer yet, not removing without one
  - Did not ask Dean the open "should the coder go find a real gap-exercising run for
    Items AE/AF" question — flagged in this file as owed, not asked yet
  - Did not review any of the 35 batch-refresh renders myself — Dean's own next look, not mine
    to pre-empt
```
