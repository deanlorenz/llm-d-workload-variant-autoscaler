# Context & Token Cost Reduction — standing context, round trips, tool output

**Type:** 3 (task plan) · **Status: ACTIVE** — approved by Dean 2026-08-09, Track 0 landing first.
**Motivation:** Dean's network is slow; the ask was "reduce output tokens for bash and other tools."
Measurement moved the target — see § Cost model. Two defects found while measuring outrank the
token work entirely and are captured here so they are not lost: § Defect 1 and § Defect 2.

---

## Reading Protocol

> Read this Reading Protocol + `## TOC`, then fetch sections on demand
> (`Read <file> offset:<start> limit:<end−start+1>`). Re-run `toc-refresh.sh` after structural edits.

---

## TOC

- [Cost model — what actually costs bytes](#cost-model--what-actually-costs-bytes) L31:57
- [Measurements](#measurements) L58:88
- [Defect 1 — the sync protocol destroys unrecoverable handoffs](#defect-1--the-sync-protocol-destroys-unrecoverable-handoffs) L89:116
- [Defect 2 — coders load no coder conventions](#defect-2--coders-load-no-coder-conventions) L117:154
- [CURRENT.md drift — a routing problem, not a size problem](#currentmd-drift--a-routing-problem-not-a-size-problem) L155:215
- [Triage of the 8 candidate proposals](#triage-of-the-8-candidate-proposals) L216:235
- [Tier 1 — the approved four tracks](#tier-1--the-approved-four-tracks) L236:290
- [Tier 2 — round-trip reduction](#tier-2--round-trip-reduction) L291:308
- [Tier 3 — per-result volume](#tier-3--per-result-volume) L309:326
- [Verification](#verification) L327:343
- [Status and resume](#status-and-resume) L344:353

## Cost model — what actually costs bytes

Three separate costs, wildly different in size. The original framing ("make bash quieter") targets
the smallest of them.

| Cost | Size | Driver |
|---|---|---|
| **Standing context re-upload** | ~32k tok from the CLAUDE.md chain alone (+ skill listing + memory) | every prompt-cache miss |
| **Round-trip latency** | LiteLLM proxy stalls 5–57 s on ~30% of requests | every tool call = one request |
| **Bash result volume** | 50–2,000 tok | what the 8 proposals target |

Two facts make the ranking lopsided:

1. **The prompt cache TTL is 5 minutes.** Any thinking gap longer than that re-uploads the entire
   context. One cache miss costs the equivalent of 20–800 bash results.
2. **The bottleneck is per-request, not per-byte.** Dean's 2026-08-09 triage (round 2) proved the
   LiteLLM proxy itself stalls on ~30% of requests, independent of payload, model, or provider —
   demonstrated by a model-free `/health/readiness` stall of 6.24 s. So **round-trip count** and
   **standing size** dominate; result verbosity is third-order.

Corollary worth remembering: `verbose` and `viewMode` look like the obvious knobs and are
irrelevant — they control local rendering, not what is uploaded. All network cost here is API traffic.

[↑ TOC](#toc)

---

## Measurements

Always-loaded chain, 2026-08-09:

```
CLAUDE.md                        0.1KB      ~18 tok
session/CONVENTIONS.md          32.0KB    ~8,192 tok
session/CODER-CONVENTIONS.md    21.9KB    ~5,604 tok
session/CURRENT.md              71.2KB   ~18,235 tok
                        total  125.2KB   ~32,050 tok
```

`CURRENT.md` by section (chars, not lines — the PR Status rows are ~2,000-word *single lines*, so
line counts mislead badly):

```
Recent activity                 29.6KB   (42%)
Next steps                      16.9KB   (24%)
PR Status                        9.7KB   (14%)
Issues to Open                   6.4KB    (9%)
Benchmark                        4.6KB
Pending handoffs                 1.3KB
Blocked on                       0.8KB
```

`session/history.md` is 43.9KB and is **not** auto-loaded — that separation is working as designed.

[↑ TOC](#toc)

---

## Defect 1 — the sync protocol destroys unrecoverable handoffs

**Found 2026-08-09. This is a live data-loss bug in the documented protocol, not a hypothetical.**

`CONVENTIONS.md` explicitly permits senders to leave handoffs uncommitted: *"Handoffs need not be
committed by the submitting session — all sessions share the `plans/` worktree filesystem, so the
sync session reads uncommitted handoff files directly and commits/consumes them in its batch."*

But `.claude/skills/s-sync-current/SKILL.md` Step 5 branches on tracked-ness and, for an
**untracked** `.DONE` file, resolves it with plain `rm` ("removes untracked `.DONE` files via `rm`
rather than `git rm`"). So consuming an uncommitted handoff **deletes content that was never in
git** — permanently, with no trace. Dean's description: *"when the handoff is deleted, we no longer
know what happened and cannot recover."*

Scale at time of discovery: **19 of 314 handoffs untracked**, including
`sync__ta-anchor-pr2-code-complete-reviewed-no-defects.md` (3.6KB, the substantive PR-2 state).

**Fix (Track 1a):** `git add` the handoff *as received* before marking `.DONE`, then `git rm`.
Delete the untracked-`rm` branch entirely. Recovery then becomes
`git log --diff-filter=D -- session/handoffs/`.

Related root causes Dean named, worth keeping in view: handoff mixups arise from naming, inability
to edit/rename in `plans` from some sessions, and sessions wrongly taking ownership.

[↑ TOC](#toc)

---

## Defect 2 — coders load no coder conventions

**Found 2026-08-09.** `CODER-CONVENTIONS.md` (5.6k tokens) is imported by exactly one file:

```
plans/CLAUDE.md:
  @session/CONVENTIONS.md
  @session/CODER-CONVENTIONS.md
  @session/CURRENT.md
```

Code worktrees carry a 33-byte `CLAUDE.md` whose entire content is `see @AGENTS.md for instructions.`
— the upstream project's file, unrelated to Dean's conventions. The container directory has no
`CLAUDE.md` at all.

Consequences, both bad:

- A coder launched from a terminal **in its worktree** loads none of its rulebook — no worktree-scope
  rules, no handoff protocol, no DCO discipline, no pre-push checklist. This is the launch model
  enabled earlier the same day (see `project_coder_write_confinement`).
- A coder that starts in `plans` and then `EnterWorktree`s **also** loses it, because that re-roots
  the CLAUDE.md chain to the worktree.
- Meanwhile every planner / chat / sync session pays 5.6k tokens for rules it never uses.

Dean's constraints for the fix: **both launch paths must work**; there is no existing skill that
makes a session a coder; he declares the role conversationally at session start and asks the session
to confirm it understands the conventions; only coders need them, and **all** coders must read them.

**Fix (Track 1d):** an `s-coder` skill as a thin loader over the unchanged `CODER-CONVENTIONS.md`,
plus a container symlink so it is reachable from every worktree via directory walk-up (the
established pattern — nine such symlinks already exist for the other `s-*` skills), plus dropping
the always-on import, plus a two-line pointer in the always-loaded `CONVENTIONS.md` so the mechanism
does not rest solely on the skill listing.

[↑ TOC](#toc)

---

## CURRENT.md drift — a routing problem, not a size problem

Growth, sampled from git:

```
2026-06-01   31.7KB
2026-07-01   19.9KB   <- a successful compression happened here
2026-07-20   20.8KB
2026-08-01   22.9KB
2026-08-09   71.2KB   <- 3.1x in 8 days
```

*(A 2026-05-01 sample read 71.2KB — an artifact: no commit predates that date, so `git show` fell
through to the index. Discarded.)*

Not gradual rot: a step change during one intense mission (anchor PR-1 + PR-2, ~30 handoffs, many
concurrent sessions).

**Dean's correction to the diagnosis (2026-08-09), which supersedes an earlier line-cap proposal:**

> WIP should focus on saving state, recoverability, disambiguity, not save space — the correct
> behavior is to ensure state is saved somewhere (typically Type 3 or Type 1 plan), before reducing
> the text.

So the failure is **routing, not volume**. A WIP entry exists for state, recoverability and
disambiguation; brevity is not its purpose. A line cap would actively reward deleting state that has
nowhere else to live — the very loss mode `CONVENTIONS.md` guards against with
verify-or-copy-then-delete.

**Dean's third framing (2026-08-09), which names the causal chain:** *"Planner should document their
state as they go and capture their thoughts in the plan. State and updates to CURRENT are meant to
point back to the plan. Not as a state store."* So the drift is a **planner-discipline** failure
upstream of any sync-time tidying: state that should have been written into the Type 3 as it was
learned accumulated in CURRENT.md instead, as prose rather than as references. Sync-time compression
is only the symptom-side remedy; the durable fix is that the planner writes the plan as it goes and
CURRENT.md carries pointers.

The actual gap: today's Type-5 text says compress an item *"once its substance is in git or a
permanent doc."* For **in-flight** work nothing has landed, so that condition is never satisfied and
nothing is ever eligible. CURRENT.md therefore became the de-facto permanent home for WIP state —
which is the one thing it must not be, since it is the only auto-loaded file of the three while the
Type 3 plan doc and `history.md` are both fetch-on-demand. Triplication then multiplied it by three.

**Rule to add (Track 1c):** for in-flight work the permanent home is the Type 3 plan doc; CURRENT.md
carries an abstract plus a pointer; **the item's owner** writes detail down into the Type 3 as it is
learned; and no text is compressed in CURRENT.md until its home exists. Size becomes an outcome of
correct routing rather than a target.

**Second half of the rule (Dean, 2026-08-09) — compression is validate-only.** Every in-flight
Type 3 / Type 1 has an owner who may be editing it at that moment, so a session tidying CURRENT.md
may only *check* that the content is present there. It must **never edit someone else's plan doc to
make room.** If a detail has no home yet, the correct action is to leave the CURRENT.md text
uncompressed and send a `plan__<topic>.md` handoff asking the owner to fold it in — compression of
that item waits. `session/history.md` is the one exception, being sync-owned. This is the same
boundary as the reviewer-writes-in-a-coder's-tree incident: a concurrent owner's uncommitted work is
invisible to you, so "I'll just add it for them" can silently clobber or duplicate.

[↑ TOC](#toc)

---

## Triage of the 8 candidate proposals

From an earlier chat with another assistant. Directionally reasonable, but it misses round-trip count
entirely and over-weights the one thing already over-done.

| # | Proposal | Verdict |
|---|---|---|
| 1 | Quiet wrapper commands | **Keep** — as committed `scripts/*.sh`, not shell aliases (shell state does not persist between Bash calls) |
| 2 | Machine-readable commands | **Keep** — `--short`, `--oneline`, `--json` + `jq -r`; real 5–10× on specific commands |
| 3 | Save expensive commands | **Keep** — merges into #1 |
| 4 | Maintain a project state file | **Inverted** — one exists, and at 18.2k tokens it is the *largest single cost*, not a solution |
| 5 | Maintain a session snapshot | **Skip** — already covered by memory + `session/status/`; adding more compounds #4 |
| 6 | Add instructions to CLAUDE.md | **Cap at ~3 lines** — CLAUDE.md is in context every turn, so verbose instructions are self-defeating; also advisory, and agents drift from it over long sessions |
| 7 | Cache frequently requested info | **Same trap as #4**, plus staleness — `CONVENTIONS.md` already warns about stale refs |
| 8 | Force concise command output | **Keep, but mechanically** — a `PreToolUse` hook, not an instruction |

[↑ TOC](#toc)

---

## Tier 1 — the approved four tracks

Approved 2026-08-09. Order: `0 → 1a → 1b → 1c → 2 → 3 → 4a → 1d → 4b`. One commit per lettered
item. Local only; the `plans` branch takes no DCO sign-off; nothing pushed.

Dependencies are real, not stylistic: 1a before 2 (else consuming the untracked handoff destroys
it), 2 before 3 (fact changes and volume changes get attributable diffs — same reasoning as the
C6c-before-behavior-changes rule), 3a before 3b/3c (home before compression), 4a before 1d (silent
failure risk).

**Track 0 — durable record.** This document, plus a memory pointer and the Defect 2 finding appended
to `project_coder_write_confinement`.

**Track 1 — rules and protocol** (governance; scrutinize hardest):
- **1a** fix the shredder — `.claude/skills/s-sync-current/SKILL.md` Steps 4–5
- **1b** commit the 19 untracked handoffs as-is; no renames, no edits (several are other sessions'
  `plan__*.WIP`, which are not this session's to touch)
- **1c** add the in-flight routing rule to `CONVENTIONS.md` (see § drift)
- **1d** route coder conventions to coders (see § Defect 2)

**Track 2 — sync fold-in** (changes recorded facts, nothing else). Lock was free
(`current__editing.md.DONE`). Two pending handoffs make the PR-2 entry stale in ~6 ways:

- code-complete **and reviewed** — Finding 76, `052b6792`, **no defects found**; tip `6d55fbd7`,
  26 commits on `075a208e`, tree clean, nothing pushed
- Type 1 = Addendum 1 **Rev 7 `43f20c65`** (CURRENT.md said Rev 6 `423eb2a8`); Type 3 = **`4fa91b7e`**
  (CURRENT.md said `1a116e7a`)
- Dean's resume go-ahead was **already relayed** via trigger `c6ea7ee9` — the recorded
  "PAUSED awaiting Dean's resume-coding go-ahead" was wrong
- **`ceil`/`floor` retracted** — never a real fork. `capN = min(replicasToCover(share, gpusPR),
  gpusAvail/gpusPR)` rounds its two terms in opposite directions *on purpose*; the Type 1's `floor`
  mandate covers the pool term only and the shipped code already satisfies it
- **only `AD8` (b) placement** remains Dean's; `B2` (a discriminating spec for `fairShareRolePick`'s
  per-role budget) remains the planner's
- push will need `--force-with-lease` (`origin/ta-anchor-dynamic-refresh@f6485980` orphaned)
- new incident to record: the reviewer's two read-only `cd`-into-coder's-worktree slips
  (Finding 76 §7), self-disclosed

**Track 3 — cleanup** (volume only, zero fact changes): **3a** home audit (gating), **3b**
de-triplicate — anchor/PR-2, `optimizer-pd-role-ceiling`, autoscaling-viz and benchmark each appear
at near-full length in Recent activity **and** PR Status **and** Next steps, which
`CONVENTIONS.md` already forbids ("One source per task"); deduplicating loses nothing because the
text is literally repeated — **3c** move landed content into existing `history.md` sections then
`bash scripts/toc-refresh.sh session/history.md`, **3d** re-validate refs, CURRENT.md written last.

**Track 4 — skill listing:** **4a** diagnose why 5 of 9 `s-*` skills are absent from the session
listing (`s-design-review`, `s-note`, `s-plan`, `s-pre-push`, `s-sync-current`) while four generic
skills with long descriptions are present — this is a prerequisite for 1d, because if `s-coder` is
dropped the same way the mechanism fails silently. **4b** trim via `skillOverrides`
(`name-only` / `user-invocable-only`) and possibly `skillListingMaxDescChars` (default 1536).

[↑ TOC](#toc)

---

## Tier 2 — round-trip reduction

Not yet scheduled. This is the lever the 8 proposals missed, and given the per-request bottleneck it
is likely the best latency-per-effort available.

- **A repo digest script.** `scripts/` already hosts `toc-refresh.sh`. One script emitting branch +
  short status + last commits + pending handoffs replaces four calls; at 5–57 s of stall risk per
  call that is a large saving. CLAUDE.md then costs ~15 tokens (`for repo state run scripts/st.sh`)
  and the script's own complexity costs zero context. This is proposal #1/#3 done properly.
- **Batching** independent probes with `&&` into one call.
- **Parallel tool calls** in a single message for genuinely independent work.
- **Delegating expensive exploration to subagents** — their tool churn stays in their own context and
  only the final report returns. Note Dean's standing rule: do not call the Agent tool unless asked.

[↑ TOC](#toc)

---

## Tier 3 — per-result volume

Not yet scheduled. Smallest of the three costs; two mechanical options that need no discipline:

- **`env` in settings** — `NO_COLOR=1`, `GIT_PAGER=cat`, `PAGER=cat`. ANSI escapes are pure token
  waste. Trivial, no downside.
- **A `PreToolUse` hook on Bash using `updatedInput`** to rewrite known-verbose commands
  (`make test` → `make test 2>&1 | tail -30`). The hook's `if` field scopes it by permission-rule
  syntax (`if: "Bash(make *)"`) so it costs nothing elsewhere. This is proposal #8 enforced
  mechanically rather than by instruction — which matters, because CLAUDE.md instructions are
  advisory and agents drift from them across a long session.

Plus the unglamorous one: machine-readable flags at the call site (proposal #2).

[↑ TOC](#toc)

---

## Verification

- **No loss — the one that matters.** For every SHA, PR number, and `Fnn`/`Ann` anchor removed from
  CURRENT.md, confirm it resolves in `history.md` or a `planning/` doc. Review `git diff --stat` per
  commit. Per `CONVENTIONS.md`: targeted edits, never a wholesale rewrite.
- **Recovery drill.** After consuming, confirm `git log --diff-filter=D -- session/handoffs/`
  returns the consumed handoffs' full text — impossible before Track 1a.
- **Refs.** Every `history.md` link in CURRENT.md resolves; `toc-refresh.sh` is idempotent (run
  twice, second run clean).
- **Size.** Re-measure the chain; expect ~32k → ~13k tokens as a by-product of Tracks 1c/1d/3.
- **`s-coder`.** Needs a fresh session from both `plans` and a worktree to confirm it appears in the
  listing. Dean's to check — a running session cannot restart itself.

[↑ TOC](#toc)

---

## Status and resume

- **Track 0** — this document. In progress.
- **Tracks 1a–4b** — approved, not started. See § Tier 1 for the order and the dependency reasons.
- **Tier 2 / Tier 3** — documented, not scheduled, no decision pending from Dean.

Cold-resume entry point: read § Cost model, then § Tier 1. The two defects are the reason this
document exists at all and are the parts that must not be lost.

[↑ TOC](#toc)
