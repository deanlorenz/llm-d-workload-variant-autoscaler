name: viz-panels Planner
id: caa88c11-142b-4665-bf0d-7ea51669911d
role: planner
branch: plans
worktree: /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans
owned_doc: planning/autoscaling-viz-followon-plan.md (epic) + several Type 3s under it
task: parked mid-session per Dean's "park" — see below for exact resume point
status_file: session/status/planner-viz-panels.md

last_update: 2026-08-17T02:21:00Z
state: idle (parked)
current_step: none in flight — all dispatched coder work has landed and been read
blocked_on: none — waiting on Dean's next direction
recent_commits:
  - a1a815a7 (autoscaling-viz, coder's) Panel 3: fix missing-vs-zero conflation, one-tick forward-fill + stale marker
  - 809debac (plans) planning(autoscaling-viz): correct Item AC -- exclude saturated samples from per-pod peak
  - 85b22c19 (plans) planning(autoscaling-viz): batch extract+render spec for all 29 clean-collection runs

notes: |
  ## Where this thread stands (2026-08-17, parked)

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
