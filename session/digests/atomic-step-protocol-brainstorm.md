# Session digest — atomic-step protocol + doc/session model

**Session:** designer role, `plans` worktree. Started 2026-08-09, continued 2026-08-10.
**Captured through:** `2026-08-12T08:48:12.566Z` (UTC — transcript timestamps are UTC; a local-time
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
- **Both designs are FINAL** — *"finalize both docs."* Frozen 2026-08-10; amend by addendum, never by
  editing; the open items remain open.
- **The tick runs in every session** — *"the tick should run in every session."* Since a scheduled tick
  is session-scoped and dies with its session, scheduling it is a start-of-session action, placed in the
  always-loaded `CONVENTIONS.md` for reload safety.
- **Push authorized** — *"push it."* `plans` → `origin/plans`, fast-forward.
- **Fix the extractor before anything else** — *"fix the extractor first."* Done; see the defect entry
  below. The tooling code spec is next.
- **The reviewer's 941 uncommitted lines are off this session's plate** — *"I'll have the reviwer check."*
- **Checkpointing has two separate goals** — *"(a) write enough so can recover on a panic (that does not
  involve the main session at all, no output); (b) identify that main session is missing some critical
  info and making sure it gets it (or at least saving it as state)."* Only (b) needs judgment, so only
  (b) costs context; (a) must be free.
- **Smaller option first; the subagent is deferred, not rejected** — *"maybe start with the smaller
  option. I don't have a problem with the tick only updating the session if new, uncaptured content
  found."* Hence `--count` gating rather than delegation.
- **Worktree creation and background auto-mode coders are authorized** — *"I allow you to create all the
  needed worktrees. You can also launch background coder agents in auto mode inside those worktrees."*
  Standing, not per-instance.
- **One code spec per unit of work, one coder per spec** — his question *"so you are creating a type 3 per
  spec and we will assign a coder for each?"* Answered: steps are the unit of atomicity **within** a
  coder's run, not of assignment; parallelism comes from independent specs, not from splitting one spec's
  steps.
- **Nothing to invoke before sleeping the machine** — his question, answered: the transcript persists
  within ~8 s and the snapshot loop mirrors it every 120 s, so an unannounced sleep costs at most the
  distillation since the last tick, which is recoverable from the transcript. Saying "checkpoint" is the
  explicit fast path.
- **All remaining code specs written up for review** — *"write up all the type 3 docs. I will review
  tomorrow when I wake up."* Four specs landed as `161fb27b`; **his review is pending and nothing should
  be launched against them until it happens.**
- **Tick stopped for the night** — *"stop the tick, I'm going to sleep."* Cron `070a4709` cancelled; the
  snapshot loop was left running. Re-arming on resume is the session's own responsibility per the
  every-session rule in `CONVENTIONS.md`.

  ⚠️ *The three rulings above arrived in a **mid-turn message the extractor did not capture** (it is
  absent from an extract spanning its arrival). They are recorded here from session context, not from the
  transcript — a second confirmed instance of digest defect 2 below, and evidence that a tick relying on
  the extractor alone would have silently dropped three of Dean's decisions.*

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
- **System task-notifications are extracted as mid-turn "user" turns.** A background-task completion
  notice is enqueued exactly like a real mid-turn message, so it arrives in the extract marked
  `(mid-turn)` and counts toward the tick's non-zero count. Nobody said it. This pollutes the digest's
  highest-value class — Dean's verbatim words — and inflates the count that decides whether a tick does
  work. Needs the same content-prefix filter as the `CHECKPOINT TICK` prompt.
- **Two defects in the checkpoint tick, found by its first real run (2026-08-10T00:17Z):**
  1. **The tick's own cron prompt is extracted as a user turn.** It is a plain-string user record like
     any other, so every tick re-reads its own instructions and the extract grows with tick count. The
     filter must exclude cron-injected prompts.
  2. **A mid-turn user message was silently missed.** "ready to finalize?" arrived mid-turn at roughly
     00:14Z and does **not** appear in an extract bounded at 23:49Z — so mid-turn injections are not
     plain-string user records. This is the exact failure class the mechanism exists to prevent: a
     silent omission that looks identical to "nothing new". Needs the record shape confirmed and the
     filter widened before the tick can be trusted. **Confirmed a second time at 00:20Z**, when a
     mid-turn message carrying three separate rulings was missed — so this is reproducible, not a
     one-off, and it drops high-value content specifically. **FIXED 2026-08-10** (Dean: *"fix the
     extractor first"*): a mid-turn message is recorded as `type: "queue-operation"` /
     `operation: "enqueue"` and **never** as a `user` record. Filter now reads both shapes, takes
     `enqueue` only (`dequeue` duplicates it, `remove` was cancelled and never said), and deduplicates
     on text because a message draining *after* a turn is recorded twice ~30 s apart while a mid-turn
     one is recorded once. **25 → 34 turns** on this session: 11 mid-turn messages recovered, 2
     duplicates removed.
- **The push moved 13 commits, not the 12 announced.** `origin/plans` went `1020e7fa → 06b6c32e`; the
  extra commit (`06b6c32e`, a concurrent session's `s-sync-main` change) landed in the ~2-minute window
  between counting and pushing. Pushing a branch pushes its tip, so anything committed in that gap rides
  along. On a shared worktree the range must be re-read immediately before the push, not before the
  announcement.
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
- ~~Bound the raw sidecar's growth~~ — *"verify file does not grow forever."* **Checked: growth is
  bounded** (each turn appended exactly once; 38 turns, 0 duplicate headers, ~19 KB — linear in
  conversation length). No cap needed. But the check found **two real bugs**, both fixed:
  1. **The loop had been silently dead for 18 minutes.** A `queue-operation` record with a **null**
     `content` aborted `jq`, and `2>/dev/null` in the loop made the failure identical to "no new turns".
     Same silence-looks-like-success failure the design warns about, recurring inside the code written to
     prevent it. Now type-guarded, with stderr logged and the exit code checked.
  2. **It was reading another session's transcript.** `ls -t` picks newest-by-mtime, and a concurrent
     plans session became newest as soon as it wrote — so the sidecar would have mirrored the wrong
     conversation while missing this one. **mtime is not identity.** The loop is pinned with `--file`; the
     extractor warns when resolving by mtime with several transcripts present.
- ~~Pin the tick's transcript too~~ — **done**; now job `c9a58666`, which also reports SKIPPED on a
  failed check and ignores system task-notifications.
- **Install `shellcheck`** — *"install spellcheck"* (the shell linter, not a prose one). Blocked: `sudo`
  requires a password here, so Dean must run `sudo apt install -y shellcheck` himself; candidate is
  `0.9.0-1`. Until then that gate is **unmet, not passed**, on every script the tooling coder wrote.
- **Decide the halt rule** — his question *"the current coder still uses the old hult rule?"* Answer:
  unchanged, nothing softened. So the next coder launched against the remaining specs will very likely
  repeat the four judgment calls. Two levers, neither chosen: tighten the specs so nothing is left to
  decide (the S5 self-contradiction was mine), or give the rule a mechanical gate rather than trusting
  instruction. **A pending decision, not a resolved finding.**
- **The tick's cost, measured — and it inverts the assumption it was built on.** 55 ticks fired; **only
  9 produced anything** (84% empty). Measurable per empty tick: ~610 tokens of prompt (2,450 chars) plus
  ~200 of call/result/reply ≈ **800 tokens**, so ~45k across all 55. That is the small part. The dominant
  cost is that **each tick is a separate API request 15 minutes apart against a 5-minute prompt-cache
  TTL**, so every tick is a guaranteed cache miss that re-uploads the whole conversation — plausibly
  100–200k input tokens each, i.e. millions in total (an estimate from the TTL and interval, not a
  measurement; context size is not readable from inside a session).
  **The design assumed idle time is free. It is the opposite:** idle is exactly when the cache has
  expired, so an idle tick is the most expensive kind — which undercuts the reason `CronCreate` was
  chosen (that it fires when idle). Note goal (a) is unaffected: the snapshot loop costs nothing.
- **Whether to change the tick's cadence** — offered, unanswered. Options, cheapest first: a much longer
  interval (hourly or on demand, harmless because the transcript retains everything meanwhile);
  event-driven firing only after substantive turns; or delegating to a subagent, which pays its own
  context instead of re-uploading this one. That last option had been judged weakened by `--count`; the
  cache-miss cost revives it.
- **Whether to add `plans-tooling` to `wva.code-workspace`** — offered, not answered. Creating a git
  worktree does **not** add it to VS Code: the workspace folders are an explicit list in that file, so
  every new worktree needs an entry (or *Add Folder to Workspace*) before it is visible in the editor.
  Worth remembering because it recurs with every worktree the migration creates. Caveat also recorded:
  a multi-root workspace entry is a convenience for Dean, not a boundary — it makes the folder writable
  to a webview session, which is why terminal-launch is the confining path.
- **Advance the marker from the extract, never by hand.** The overnight catch-up set it to a guessed
  `05:52Z` while the real turns were at `07:56Z` and `09:13Z`, so the next tick re-surfaced two already
  captured turns. Harmless here — appending is idempotent by diffing — but the marker must always come
  from the newest extracted timestamp.
- **Coder running on the tooling spec** — `plans-tooling` orphan worktree created, background coder
  launched under `--permission-mode auto` (task `bxykv31hw`, log `/tmp/coder-plans-tooling.log`).
  Progress lands in `session/status/plans-tooling.md`. The spec is still DRAFT; the launch authorization
  was treated as acceptance, and the work is reversible (orphan branch, unpushed, stoppable).
- **`cd`-then-Agent is no longer viable** — shell CWD resets after every Bash call, so a subagent would
  inherit `plans/` and the worktree confinement would be fiction. Use a `claude -p` subprocess, whose
  `cd` lives inside the same invocation. Memory `feedback_subagent_cwd_pattern` and
  `feedback_no_cd_sibling` describe the old pattern and are now stale on this point.

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

**Parked 2026-08-11 ~20:15Z.** All five code specs are written and committed; the `sec`/`conv`/`conv-list`/
`conv-lint` slice is **built and green** (7 commits on `plans-tooling`, 21 tests, 0 failed, shellcheck-clean).

**Awaiting Dean, nothing blocked on an agent:**

- **Review the four remaining code specs** (`161fb27b`, plus `6a02f914` on step-gates). Nothing should be
  launched against them until he has.
- **`plans` is 8 commits ahead of `origin/plans`.** Push needs his explicit per-push confirmation.
- **Kickoff copy of `plans-tooling` into `plans/`** — his single deliberate action; the tooling is
  unpushed and uncopied. Development history stays on `plans-tooling`.
- **Enforcement of the judgment mark** — Addendum 1 adopts tags; `step-gates-spec.md` S3/S6 specify the
  checks, but neither is built, so all four obligations still rest on coder compliance.

**State a successor needs:**

- Designs are **FINAL, frozen 2026-08-10**, amended by
  [`atomic-step-protocol-design-addendum-1.md`](../../planning/atomic-step-protocol-design-addendum-1.md)
  (halt rule re-cut on **reversibility**, approved 2026-08-11).
- The scheduled cron tick is **retired** — `session/.tick-disabled` makes `session-extract.sh` refuse and
  tells any session still running one to cancel its own job. Replacement is the two-tier
  `session-snapshot.sh` loop (free, model-free gate) plus `tick-consolidate.sh` (rare, `aws/claude-haiku-4-5`,
  ~488-token prompt). Both die with the session; a successor starts its own loop.
- `shellcheck` is now installed, so that gate is met rather than skipped.
- Not this session's: `planning/multi-analyzer-dataflow-map.md` (modified) and
  `planning/autoscaling-viz-design.md` (new, untracked) belong to other sessions — leave them alone.

Reaching `CURRENT.md` requires a `sync__` handoff — a designer session cannot write it (single-writer),
and per Dean that channel is already served by handoffs at major decisions, not by this digest.

---

## Consolidated capture

Appended by `scripts/tick-consolidate.sh`: turns selected by a small model, text spliced verbatim
by the script. Uncurated — the sections above are the curated record.

### 2026-08-11T16:11:26.120Z

- **task** — Stop tick, estimate total tokens from yesterday
  > stop the tick. Estimate total tokens from yesterday
- **decision** — Tick optimization: cheap model, no-op idle, context limit, local ledger
  > we need to reduce this effort.
  > 1. use a cheap model for the tick work
  > 2. tick should be no-op if there is no new data in the main session -- e.g., an idle session should not send any tick info to claude.
  > 3. maximal context should only be until last compact
  > 4. can keep local ledger and invoke the tick to update a local ledge only, once every X ticks to actually incorprate the info into conext/state
- **decision** — Disable script; evaluate cheap models; tier 1,2 approved
  > 1. lets disable the script so existing sessions cannot run it.
  > 2. My remote litellm proxy also has a self hosted  rits/google/gemma-4-31B model -- is that enough?
  > 3. Other cheap models are gemini-2.5-flash, got-5-nano-2025-08-07, gpt-5-mini-2025-08-07, gpt-oss-120b, gemin-3.5-flash-lite
  > 4. Tier 1,2 OK
- **ruling** — Focus discussion on tokens not latency; try claude or curl
  > our latest discussion is about tokens, not latency
  > can try using claude and move to curl if needed

### 2026-08-11T16:22:08.734Z

- **question** — shell check, add loop invoking
  > what shell is running?
  > add the loop invoking

### 2026-08-11T16:57:32.395Z

- **question** — spellcheck setup requirements and sudo usage explanation
  > what do I need for speelcheck? why sudo? what is it doing?

### 2026-08-11T19:56:49.311Z

- **question** — Halt-rule decision and workspace-entry question
  > I installed it. 
  > what is the the halt-rule decision, and the workspace-entry question.
- **ruling** — Code action reversibility requirements and destructive operation halt policy
  > (d) is OK, however, it still overstepped given the current rule -- I don't like it. Rules are there to obay. I accept rule change suggestions -- that is fine. Everything coder did could have be proposed to me or to planner to fix or approve. 
  > I am willing to let the coder act on some of these ambiguous items, provided that it is reversible. Given that coder commit their work anyway it may be OK to continue and not block; however, the assumption/presummption/guess/etc should be surfaced, documented, brought back to decision AND reverted when needs to be. Not sure about the checkpoint mechanism, perhaps tags. That said, distructive non revertable action should halt (eg run a change on the cluster).
  > worksapce -- yes it should. need to refresh code-workspace

### 2026-08-11T20:15:26.944Z

- **question** — Explain difference between step-check and plan-lint
  > explain step-check vs plan-lint
- **task** — Add judgment-mark check to step-check spec
  > add the judgment-mark check to step-check in the spec. 
  > would I also need plan-lint to check those judgments?

### 2026-08-12T08:48:12.566Z

- **ruling** — Decisions need clear ownership and lifecycle tracking across documents
  > decisions I made in a planner keep surfacing back up. Seems like the open issue and decision made on them are stored in multiple places. We need a clear owner for every decision (in terms of which document, not which session) and that should track the lifecylce per decision (raised, todo, WIP, partial, decided, why, rejected alternatives, closed) -- most of these are refs
