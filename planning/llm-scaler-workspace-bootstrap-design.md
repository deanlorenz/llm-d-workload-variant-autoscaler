# llm-scaler workspace bootstrap — design discussion

**Status:** DRAFT — discussion doc, nothing approved, nothing executed
**Type:** design (Type 1)
**Created:** 2026-08-16 · **Revised:** 2026-08-16, three rounds (R1–R3, R4–R8, R9–R11 — see § 0)
**Scope:** standing up a second VSCode workspace for `git@github.com:deanlorenz/llm-scaler.git`,
carrying this workspace's conventions/tooling/session machinery forward, while three projects run
concurrently.

> This doc is a **discussion**, not a plan. It records the problem shape, the findings from a
> hardcoding sweep run 2026-08-16, and the decisions that need making — with recommendations, so
> each one is a yes/no rather than an open essay. Sequencing is sketched at the end but is
> deliberately not a step-by-step: staging comes after the decisions land.

---

## 0. Rulings that reshape this doc (Dean, 2026-08-16)

Three rulings, each of which retires or narrows something below. Recorded here rather than only
edited in, so the change in framing is visible.

**R1 — The new repo waits on the new plans tooling and atomic-step rules.** Both are WIP. Since the
new repo is to be configured with the new version only, starting before they are complete would
mean either bootstrapping against a moving target or bootstrapping the old tooling and migrating
twice. So this doc's own execution is **gated**, and the gate is not in this doc's control.
*Consequence:* § 4's sequencing is now a *post-gate* sketch. What remains actionable **now** is the
part that is useful regardless — the portability findings (§ 2) and the decisions that shape the
target (§ 3). The doc's value in the meantime is as the standing record of what the bootstrap will
have to handle, kept current as the tooling lands.

**R2 — Do not copy junk.** The container `.claude/` has accreted artifacts whose purpose is not
established; the global-settings entries may be old artifacts rather than needed grants. The port
is an **allowlist, not a mirror**: nothing crosses without a reason. See § 2.5, which is new and
replaces the assumption that container settings port wholesale.

**R3 — Dean does the bootstrap copying manually; the entire `plans/` dir can be copied to the new
repo as reference.** This retires **D4** (the author-here-vs-execute-there question) — there is no
boundary problem if the copy is a human action. It also weakens the case for a
`bootstrap-workspace.sh`: a script's value was reviewability across a boundary that no longer
exists. *What remains valuable* is not the script but the **manifest** — the explicit list of what
to copy, what to fix on arrival, and what to leave behind. That is § 2 plus § 2.5, and it is the
concrete deliverable of this doc.

*Note on "copy the entire `plans/` dir as reference":* useful, with one caveat worth stating —
a full copy carries `session/CURRENT.md`, `session/history.md`, the handoff queue and status files,
which are *this* mission's live state. As **reference** that is fine and often exactly what you
want. As a **starting point** it would seed the new workspace with a foreign mission's state, which
is the one thing you said should not migrate (docs don't come over). So: copy it in as reference,
but the new `plans` branch's tracked content should be built from the allowlist, not from the copy.

### Second round of rulings (same day)

**R4 — Effort 2 only. Effort 3 is out of scope.** D1 is therefore **N/A**. Two GitHub repos exist
for certain; *if* the two-project split proceeds, Dean leans shape **(c)** — two repos, two
containers. So the doc no longer plans for a shared container, and any future effort-3 container is
a **second application of this same bootstrap**, which is an argument for capturing the mechanism
(R6) rather than a one-off.

**R5 — `sync-main` must be generalized, not path-fixed.** The § 2.2 fix as written ("derive from
`dirname $0`") is too weak. The real requirement is parameterization over **repo, container, and
branch(es)** — the new repo does not use `main` yet, so a script hardwired to the concept of "main"
is wrong there, not merely mis-pathed. See § 2.2a.

**R6 — Capture the bootstrapping mechanism as we go.** `dean-ai-overlay/` was originally created for
exactly this use case (adding Dean's conventions and tooling to a new repo). It is early-stage,
stale, unstable, untested, unplanned — but the general direction was right. This doc's byproduct
should be the mechanism, not just this one migration. See § 7, new.

**R7 — The container `.claude` must be tracked; plans holds the content, container holds symlinks.**
Confirmed correct, and **already implemented** — see § 2.4, rewritten. Where container and plans
need to differ, both files still live in plans under different names, with a symlink for the
container one. Dean asked what the differences actually are and whether they are needed: answered in
§ 2.4a.

**R8 — `spec-as-code` is wanted, not junk.** It is a separate, parked effort that Dean intends to
return to, and using the existing code as a use-case test was deliberate. He wants the same for the
new repo. § 2.5's junk list is corrected accordingly — the misclassification was mine, from reading
a stale-looking zip filename as abandonment.

### Third round of rulings (same day)

**R9 — `.bob/` and `.revisions/`: see if we can live without them.** Purpose unclear for both, so
neither ports and dropping is the default. **But a separate TODO comes out of it:** Dean wants to use
**Bob as a coder** sometimes, which needs *what the correct Bob settings are under these conventions* —
a rules question that survives dropping the directory. § 2.6a2.

**R10 — Git remotes need full analysis and push protection.** Every remote must reference the new
locations; wrong refs must not be copied; upstream push protection must be added. Several other remotes
are in play (Ofer, Dean's benchmark fork, llm-d-benchmark, llm-d/llm-d, …). **This is the single
highest-risk area of the bootstrap** — a wrong `upstream` is silent until push time, and the failure
mode is pushing to someone else's repo. § 2.7, new, with two concrete hazards found.

**R11 — The memory harvest gets a design doc, owned by the atomic-step Type-2 work, applied in this
migration's context.** Both halves matter: the mechanism is not this doc's to design, and the migration
is what makes it concrete. Verified while folding this in: **the home already exists and the memory pass
is already a deliberately-deferred section of it** — so this is a trigger, not a new artifact. D3.

---

## 1. What is actually being built

Three efforts exist; **this doc covers exactly one of them** (R4).

| # | Effort | Repo | In scope here? |
|---|---|---|---|
| 1 | Existing WVA work (anchor PR-2, benchmark campaign, viz, …) | `llm-d-workload-variant-autoscaler` | no — this workspace, unchanged |
| 2 | **WVA refactor** | **`llm-scaler`** | **yes — the whole of it** |
| 3 | KEDA scaler for llm-d | TBD (own repo if it proceeds) | no — R4 puts it out of scope |

Two GitHub repos exist for certain. If the WVA-into-two-projects split proceeds, Dean leans toward
two repos with two containers, which makes effort 3's eventual workspace **another run of this same
bootstrap** rather than a variation on it. That is the case for R6 (capture the mechanism): the second
consumer is foreseeable, not hypothetical.

The intent: the new workspace follows this environment's construction — bare repo + worktrees +
plans branch + conventions + skills + session protocol. Docs do **not** migrate (the new repo
starts on the new plans tooling only). **Rules, conventions, scripts, skills, and memories do** —
with memories arriving by *harvest into rules*, not by copy (D3).

---

## 2. The hardcoding sweep — findings

Run 2026-08-16 against `plans/scripts/`, `plans/.claude/`, the container `.claude/`,
`~/.claude/settings.json`, and the memory directory. **Grouped by whether the fix is in a file we
control.**

### 2.1 Clean — relocatable as-is

The checkpoint/session scripts resolve their own location and derive everything from it:

- `session-snapshot.sh:44`, `tick-shared-scan.sh:37-38`, `tick-live-index.sh:57-58` all use
  `here="$(cd "$(dirname "$0")" && pwd)"` and `plans_dir="$here/.."`.
- `toc-refresh.sh` takes its target as `$1`.
- The `plans-tooling` tools (`sec.sh`, `conv.sh`, `conv-list.sh`, `conv-new.sh`, `conv-edit.sh`,
  `conv-lint.sh`) are the new-tooling generation and were written against a computed index.

**Implication:** copy these to the new `plans/scripts/` and they work. No edits. This is the
majority of the script surface and it is the good news of the sweep.

### 2.2 Hardcoded in files we control — mechanical fixes

| Site | What | Fix |
|---|---|---|
| `scripts/sync-main-status.sh:12` | `S=/home/dean/code/.../plans/session/status/main.md` | derive from `dirname $0` like its siblings |
| `scripts/sync-main-status.sh:9`, `sync-main-once.sh:12` | absolute path in usage comment | cosmetic, but misleads |
| `scripts/sync-main-session-start.sh:5` | `SYNC_WORKTREE="/home/dean/code/.../plans"` | derive, or parameterize |
| `.claude/skills/s-sync-main/SKILL.md` | **6 sites** — incl. the `allowed-tools:` frontmatter, which is where absolute paths are load-bearing rather than cosmetic | see D5 |
| `.claude/container-settings.json:6,46` | permission + SessionStart hook, both absolute | per-container file; rewrite for the new path |
| `plans/.claude/settings.local.json:16,17,19,23` | Edit/mv/Bash grants pinned to this container | per-container; rewrite |
| `session/CONVENTIONS.md`, `session/CODER-CONVENTIONS.md` | repo name appears in the layout diagram and examples | rewrite as part of the conventions port (which is happening anyway) |

`s-sync-main` is the worst offender by count. It is also the one skill that is genuinely
**container-specific** rather than accidentally so: it fast-forwards `main` from `upstream`, and
"which upstream, which Main worktree" is per-repo by nature.

### 2.2b Bugs found by the sweep — routed to the tooling planner

The sweep was looking for portability blockers and found **actual defects**. All three routed
2026-08-16 to the atomic-step-protocol-brainstorm planner (who owns tooling, per Dean) in
[`plan__tooling-bugs-found-in-portability-sweep.md`](../session/handoffs/plan__tooling-bugs-found-in-portability-sweep.md).
Recorded here only because a portability decision depends on one of them.

**BUG 1 — NEW: `sync-main-status.sh` reports RUNNING for a dead watcher when `last_check` is empty.**
`sync-main-status.sh:20-21` (and the same block duplicated in `sync-main-session-start.sh:19-20`) does
`lc_epoch=$(date -d "$last_check" +%s 2>/dev/null || echo 0)`. **`date -d ""` succeeds with exit 0**,
returning *midnight today* — so the `|| echo 0` fallback is unreachable and `age` becomes
seconds-since-midnight. Since the gate is `age -lt 150`, a **dead watcher reads as RUNNING between
00:00 and 00:02:30**; outside that window it reads STALE with a nonsense age. Verified on this machine
(`date -d "" +%s` → midnight, rc=0; `date -d "garbage"` → fallback works).

> **This is the same class as the tracked `stat -f %m` bug**, not a coincidence: a command that
> **succeeds on bad input**, so `|| echo 0` never fires. Two confirmed instances now
> (`date -d ""`, `stat -f %m`) — worth treating as a pattern to grep for rather than two incidents.

**BUG 2 — `tick-live-index.sh:111` still has `stat -f %m`.** Already tracked in CURRENT.md § Issues to
Open; **confirmed still live 2026-08-16**, and it is the only remaining `stat -f` in `scripts/`.

**BUG 3 — config hazard: two branches carry `remote=upstream`.** Detail in § 2.7c H1.

**Portability consequence of BUG 1, which is why it appears in this doc at all:** it is a second,
independent reason not to port the `sync-main` scripts as-is. § 2.2a's generalization argument was about *what the
scripts assume*; BUG 1 is about *what they report being wrong in the unsafe direction*. Porting a
health-check whose failure mode is "claims healthy" into a fresh container — where `last_check` will be
absent by definition on day one, since no watcher has ever run — would mean the very first status query
in the new workspace hits the buggy path. **So the fix precedes the port**, and that ordering is not
optional.

### 2.2a `sync-main` needs generalizing, not path-fixing (R5)

The table above prescribed "derive from `dirname $0`". That is necessary but **not sufficient**, and
R5 is the correction: the script family is hardwired to more than a path.

Three distinct things are baked in, only one of which is a path:

| Baked-in assumption | Why it breaks on `llm-scaler` |
|---|---|
| **Container path** (`SYNC_WORKTREE=/home/dean/.../plans`, `S=.../session/status/main.md`) | different container — the mechanical fix, and the easy one |
| **Repo identity** — an `upstream` remote distinct from `origin`, i.e. the fork-of-an-upstream topology | `llm-scaler` is Dean's own repo. There may be **no `upstream`** at all, so "fast-forward from upstream" has no referent |
| **Branch identity** — `main` as *the* tracked branch, in name and in concept (`Main/` worktree, `status/main.md`, the skill's whole vocabulary) | **the new repo does not use `main` yet.** So this is not a rename; there is currently no branch for the script to track |

That third row is why this is generalization rather than a path fix. A script parameterized only on
paths would still be asserting that a `main` exists to sync.

**Shape of the generalization** (not a design — the design belongs with the port):

- Parameterize on `(container_root, tracked_branch, upstream_remote)`, resolved from **config, not
  inference**. Config beats auto-detection here for the same reason
  `feedback_tools_take_explicit_paths` gives: the caller knows, the script shouldn't guess.
- Make "no upstream remote" and "no tracked branch" **first-class supported states**, not errors —
  in the new repo, on day one, both are the truth. The script should no-op cleanly and say so, which
  is also what makes it safe to port before the branch topology settles.
- Status file becomes `status/<tracked-branch>.md` rather than `status/main.md`.
- The `Main/` worktree name is a convention, not a requirement — keep it as the default, but the
  script should not assume the directory name equals the branch name.

**Sequencing consequence:** D5 already deferred `s-sync-main` off day one. R5 reinforces that, and
gives a cleaner reason than "it has too many absolute paths" — *there is nothing for it to sync
yet.* Generalize it when the new repo grows a tracked branch, and let this workspace be the second
consumer of the generalized version rather than the reference implementation of the old one.

**➡️ ROUTED (2026-08-16), per Dean:** plan-tools changes belong to the **atomic-step-protocol-brainstorm
planner**, who owns these scripts and has a working coder on them. Requirement handed off in
[`plan__sync-main-generalize-for-second-repo.md`](../session/handoffs/plan__sync-main-generalize-for-second-repo.md),
with Dean's instruction to **fold it into the Type 3 and fix it** stated explicitly. Not this doc's to
implement, and not this doc's to design.

⚠️ **Discovered while routing — the same file already has an in-flight item.**
`plan__sync-main-hook-silent-noop-and-tier1-tier2-boundary.md.WIP` (from sync) reports a *different*
defect in `sync-main-session-start.sh`: line 10's `[ "$cwd" = "$SYNC_WORKTREE" ] || exit 0` **silently
no-ops** when the cwd string-match fails — no log, no stderr, indistinguishable from the hook never
firing (it took a direct question from Dean to notice the watcher was dead after a restart).

**These are one root cause seen from two sides,** which is worth stating because it changes the fix's
shape: that silent failure *is* the hardcoded-single-container assumption. `SYNC_WORKTREE` is a
hardcoded absolute path compared by exact string equality, so the script cannot represent "one of
several valid containers" — the only outcomes are exact match or silent exit. Generalizing the identity
resolution **replaces the very comparison that is failing**, and requirement 2 above (no-op *loudly*,
naming the absent precondition) is the same fix that handoff asks for. The handoff says so; the two
should be designed once, not twice.

### 2.3 Hardcoded *outside* files we control — the real problems

These are the two findings that make this more than a copy job.

**(a) Memories are keyed to the bare-repo path, and do not follow.**

The memory directory is:

```
~/.claude/projects/-home-dean-code-llm-d-llm-d-workload-variant-autoscaler-repo/memory/
```

That slug is the absolute path to `repo/` with `/` → `-`. A new container at a new path gets a
**different project directory**, so none of the ~90 memory files are visible there. Roughly half
are `feedback_*` — the accumulated working rules (handoff protocol, worktree discipline, no-push,
DCO, doc-accuracy, …). Those are exactly what you said must migrate, and they are the largest
single body of it.

Same mechanism, second site: `session-extract.sh:87` computes
`project_dir="$HOME/.claude/projects/$(pwd | sed 's|/|-|g')"`. It is *correct* — that is how Claude
Code keys transcripts — which confirms the keying rather than being a bug to fix.

**Decided (R-D3, see D3 below): harvest first, regenerate one by one, never bulk-copy.** The
path-keying is therefore not a problem to work around — it is a **forcing function**. Because
memories do not follow automatically, the new workspace starts with an empty memory dir, and the only
way content arrives is deliberately. That is the desired behavior: harvest the ~45 `feedback_*` files
into rules, let the new workspace regenerate memories organically as it learns its own, and copy over
only what is genuinely important and left over. Dean marked the harvest a **must-have**.

**(b) Global `~/.claude/settings.json` carries three WVA-path-pinned grants.**

```
Edit(//home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/session/handoffs/**)
Edit(//home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/session/status/**)
Bash(mv /home/dean/code/llm-d/llm-d-workload-variant-autoscaler/plans/session/handoffs/*)
```

Global scope, so they apply to every project — but path-pinned, so in the new workspace they grant
nothing.

**Revised per R2** — the original framing here was "the handoff protocol depends on these, so the
new workspace would silently lack the capability." That overstated it. Two facts narrow it:

- The memory `feedback_shared_session_dirs_writable` records the two `Edit()` entries as **inert**
  (blocked by the isolation guard; `Bash` `cp`/`mv` is what actually works).
- All three are **duplicated** in `plans/.claude/settings.local.json`, which has no git history for
  that file — i.e. accreted, not maintained.

So these are better read as **candidate junk** than as required grants. Only `Bash(mv …/handoffs/*)`
plausibly does work, and § 4 step 5 tests exactly that. Full treatment in § 2.5.

### 2.4 Structural, not textual — **corrected per R7**

⚠️ **The original version of this section was wrong on its central claim.** It said the container
`.claude/settings.json` "lives outside version control," inferred from the container not being a git
repo. That inference was invalid: I read the file's *content* without checking its *type*.

**What is actually there:**

```
container/.claude/settings.json -> ../plans/.claude/container-settings.json    (symlink)
container/.claude/settings.local.json                                          (real file, 1 grant)
container/.claude/skills/*  -> ../../plans/.claude/skills/*                    (13 symlinks)
```

So **R7's model is already implemented**: plans holds the content, the container holds symlinks, and
the differing file lives in plans under a different name (`container-settings.json`) precisely so both
can be tracked. Dean's recollection was right and my § 2.4 was wrong.

**Answering Dean's D2 question — "if going the other way, does git save the contents?"** Yes, and the
current direction is the correct one, for a reason worth writing down because it decides the pattern
for the new repo:

- **Current direction (real file in plans, symlink in container).** Git tracks
  `plans/.claude/container-settings.json` as ordinary file content. The symlink lives *outside* any
  repo, so git never has to represent a link at all. Content is fully versioned. ✅
- **The other direction (real file in container, symlink inside plans).** Git would store the plans-side
  entry as a **symlink object — just the link text**, and the actual content, sitting in the untracked
  container, would be **unversioned**. A clone would restore a dangling link. ❌

That asymmetry is the whole reason the current arrangement is right: *the repo must hold the content,
never the pointer.* Same rule applies to the skills farm, and it is the invariant the new container
should be built to.

Remaining genuinely-structural items:

- **Container `skills/` is 13 relative symlinks** into `../../plans/.claude/skills/` — the walk-up
  reachability mechanism. Recreate rather than copy. Relative, so they survive a container *rename*
  and break on a *restructure*.
- **`container/.claude/settings.local.json` is the one real, untracked file** (one grant:
  `Bash(wc:*)`). Per R7 it *should* be tracked too if it ever holds anything meaningful — same
  different-name-plus-symlink pattern. Today it holds nothing worth tracking, which is the honest
  answer to "what needs tracking": this file, currently, does not.
- **`.vscode/tasks.json` is a symlink** into `../dean-ai-overlay/vscode/tasks.json` — a live
  cross-dependency on the overlay repo, and now a data point for R6/§ 7: the overlay is already wired
  into this container, not merely adjacent to it.
- **`wva.code-workspace`** lists 12 folders (one per active worktree) plus `root`, maintained by hand.
  The new workspace needs its own; expect per-effort churn.

### 2.4a What actually differs between the two settings files, and is it needed? (R7)

Dean asked directly. Diffed 2026-08-16. They are **not two variants of one file** — they are two
different scopes with **zero overlap**:

| | `plans/.claude/settings.json` (plans worktree only) | `plans/.claude/container-settings.json` (symlinked as container-wide) |
|---|---|---|
| **Permissions** | 6 entries, **all plans-local and all stale**: a `mv` grant naming one specific anchor-PR-2 handoff *filename*, two `toc-refresh.sh` grants naming two specific plan docs, `Bash(echo "gofmt exit: $?")`, `Bash(git branch *)`, `mcp__fetch__fetch` | `Skill(keybindings-help)`, `Skill(keybindings-help:*)`, the `sync-main-status.sh` grant |
| **Hooks** | **none** | the three worktree-gate `PreToolUse` hooks (Edit / Write / `git commit` → echo CWD+branch) **plus** the `SessionStart` sync-main hook |

**Is the difference needed? Yes — for the hooks, structurally.** The worktree-gate hooks must fire in
*every* worktree, which is only achievable from the container-level file. That is the whole
justification for having two files, and it is a good one.

**Is the difference needed for the permissions? No.** Four of the six plans-local grants name
specific filenames from completed work — textbook accretion under R2. They should not cross.

**Consequence for the new repo:** create `container-settings.json` (hooks + genuinely global grants)
and let `settings.json` start **empty or absent**, accruing only grants that a session actually hits.
The current plans-local file is a demonstration of what happens without that discipline.

### 2.5 The junk inventory — what must NOT be copied

Per **R2**. Evidence gathered 2026-08-16 by direct inspection. The container `.claude/` turns out to
be mostly accretion, and the settings duplication is a symptom of it.

**Confirmed junk — leave behind:**

| Item | Evidence | Verdict |
|---|---|---|
| `container/.claude/agents/` | **empty directory**, dated May 11 | never used; do not create |
| `container/.claude/worktrees/{engine-multi-analyzer,ta1-rebase}` | two abandoned worktrees dated **May 11**, carrying build artifacts (`bin/controller-gen`, `helm`, `setup-envtest`, `cover.out`) | `EnterWorktree` leftovers from three months ago, unrelated to `.claude/`'s config role. Do not copy. (Cleanup here is separately worthwhile but out of scope.) |
| `container/.claude/settings.local.json` | contains exactly **one** grant: `Bash(wc:*)` | not worth porting; let the new one accrue its own |
| `.devcontainer.OLD`, `hooks.old`, `env1`/`env2`/`env3.sh`, `run_only.sh` at container top level | names self-declare staleness (`.OLD`, `.old`); unversioned; unrelated to the session machinery | do not carry |
| container `requirements.txt` + `.venv` | **246-package flat pip freeze** — `litellm`, `streamlit`, `jupyterlab`, `boto3`, `azure-*`, `openai`… an entire LiteLLM-proxy/notebook environment, not this project's tooling. Pinned to no purpose and referenced by nothing in the session machinery. See § 2.6 for what the *real* requirement is. | do not carry |

**Corrected — not junk (R8):** `spec-as-code-kit-v2.zip` and the `spec-poc/` worktree were in the
original junk list. **Wrong call, mine.** `spec-as-code` is a separate, *parked* effort Dean intends
to return to; using the existing WVA code as a use-case test was deliberate, and he wants the same
arrangement in the new repo. It reads as stale from the outside (a versioned zip, a worktree with no
recent commits) which is exactly how parked-but-wanted work looks — indistinguishable from abandoned
without asking. **Carry it**, and note the general lesson for the port: *staleness is not
abandonment, and only the owner can tell them apart.* That is a reason the allowlist needs Dean's
eyes on it rather than being mechanically derived from file mtimes.

**Duplicated, and duplicating something inert:**

The three path-pinned grants from § 2.3(b) exist in **two** places:

- global `~/.claude/settings.json`
- `plans/.claude/settings.local.json` (tracked, but with **no git history** for that file — so not
  deliberately maintained)

Duplication across a global and a project scope is itself a smell of accretion rather than design.
And per memory `feedback_shared_session_dirs_writable`, the two `Edit()` entries are **inert** — the
isolation guard blocks them; `Bash` `cp`/`mv` is what actually works. So the duplicated thing does
not function.

**Verdict:** do **not** port the `Edit()` grants at all — they are dead in both copies. The
`Bash(mv .../handoffs/*)` grant is the only one of the three that plausibly does work, and whether
it is needed is **cheaply testable in the new workspace** (attempt a handoff rename; add the grant
only if it is actually refused). Porting on faith is what produced the duplication in the first
place.

**Genuinely needed, port deliberately:**

| Item | Why |
|---|---|
| `plans/.claude/skills/` (per D5's classes) | the skill bodies are the real content |
| container `.claude/skills/` symlink farm | the reachability mechanism — recreate, don't copy (relative links) |
| `container-settings.json`'s **worktree-gate `PreToolUse` hooks** | the CWD+branch echo on Edit/Write/`git commit` — cheap, and directly serves the worktree-discipline rules |
| `container-settings.json`'s **SessionStart hook** | only if `s-sync-main` is ported (D5 says defer it), so **not** on day one |
| the Go/test grants in `plans/.claude/settings.local.json` (`make test*`, `go test*`, `go build`, `gofmt -l`, `go vet`, `git commit`) | path-free, genuinely useful, no reason not to |

**Rule for the port, stated once:** an entry crosses only if someone can say what breaks without
it. Anything else stays behind and is re-added when a session actually hits the prompt — which
also documents the reason at the moment it is established.

### 2.6 Gitignored / hidden state, and the Python environment (Dean's two TODOs)

Both inventoried 2026-08-16.

#### (a) Gitignored-but-present, and hidden, in `plans/`

`git status --ignored` — everything ignored is **regenerable machine-local state**, and correctly so:

| Path | Nature | Port? |
|---|---|---|
| `session/status/main.md` | sync-main watcher heartbeat, rewritten every 60 s | **no** — regenerates; and per R5 there is no `main` to watch yet |
| `session/digests/*.raw.md` + `.mark` / `.log` | Tier-1 raw capture ledgers, per-session, uncurated | **no** — regenerable by design; the committed digest is the artifact |
| `.claude/settings.local.json` | one grant (`Bash(wc:*)`) | **no** (§ 2.5) |

The `.gitignore` itself carries a **rationale comment per rule** — that is worth carrying over as a
*pattern*, not as content: the reason each rule exists is written next to it, which is why this
inventory was quick to classify.

**Untracked-but-not-ignored** is the more interesting category: ~50 `session/handoffs/*.DONE` files
plus `session/.tier2-usage.log` and `scratch/` review artifacts. The `.DONE` accumulation is expected
(CONVENTIONS says they accumulate until a sync commit `git rm`s them) — but ~50 of them says the
cleanup half is not happening reliably. **Not a port item; a live hygiene finding in this workspace.**
Worth naming so the new repo's protocol doesn't inherit the drift silently.

Hidden container dirs also present, both tiny and both unclassified: `.bob/` (`custom_modes.yaml`,
`notes/`) and `.revisions/` (`.directives`). Neither is referenced by any script in the sweep.
**Unknown purpose — ask before porting or deleting** (the R8 lesson applies).

#### (a2) `.bob/` and `.revisions/` — unknown, and one of them has a real TODO

**Ruling (Dean):** purpose of both is unclear; **see if we can live without them.** So neither ports
on day one, and dropping them is the default rather than a decision to be made.

But `.bob/` carries a **separate, live requirement** that must not be lost in the "drop it" ruling:

> **TODO — Bob-as-coder settings.** Dean wants to use **Bob as a coder** sometimes. That needs an
> answer to: *what are the correct Bob settings under these conventions?* — i.e. how a Bob session
> gets the coder rulebook (`s-coder` / CODER-CONVENTIONS), respects worktree confinement and the
> pre-action write gate, and participates in the file-based handoff protocol. This is a **conventions
> question, not a file-copy question**, which is why dropping `.bob/` does not dispose of it.

Relevant context from this workspace, since it bears directly on how hard that is:
`feedback_sendmessage_vs_file_handoffs` records that the file-based protocol was chosen over direct
agent-to-agent messaging *specifically because* it works cross-tool — "not for cross-tool (Bob)" is
called out there. So the handoff channel is already the designed integration point for a non-Claude
coder; what is missing is the rulebook-loading half. `.bob/custom_modes.yaml` is presumably where a
role/mode would be declared, but I have not read it and cannot say whether it is current.

**Scope note:** this belongs to the conventions work (R1's gate), not to the container bootstrap. It
lands in the new repo as *rules*, and the new workspace should be built so a Bob coder is a supported
role from the start rather than retrofitted.

#### (b) Python environments — the real requirement is two packages

The headline: **the container `requirements.txt` is not the answer**, and taking it as the answer
would import a 246-package proxy/notebook stack into a fresh repo.

What actually exists:

| Location | State | Real requirement |
|---|---|---|
| `container/.venv` + `requirements.txt` | Python 3.12.3; 246 flat pins incl. `litellm`, `streamlit`, `jupyterlab` | **junk** (§ 2.5) |
| `autoscaling-viz/.venv` | **empty** — no packages installed | the scripts don't use it |
| `benchmark/llm-d-benchmark/` | proper `pyproject.toml` + **`uv.lock`** | upstream's own; comes with the harness, not ours to port |
| `plans/`, `plans-tooling/`, `spec-poc/`, `Main/` | no venv, no requirements | shell + Go only |

**Derived from the imports rather than from any requirements file** — every non-stdlib import across
the viz toolchain:

```
matplotlib, yaml        ← third-party (2)
argparse bisect collections dataclasses datetime glob hashlib heapq json math
os random re statistics subprocess sys time __future__   ← stdlib
```

So the viz toolchain's true dependency set is **`matplotlib` + `pyyaml`**. That the `.venv` beside it
is empty confirms the mechanism: these run via `uv run --with matplotlib --with pyyaml`, matching
`feedback_python_use_uv` (uv 0.9.7 present at `~/.local/bin/uv`).

**Recommendation for the new repo:** no shared venv, no `requirements.txt`. Declare per-script
dependencies at the call site via `uv run --with`, or give each tool a PEP-723 inline script header so
the dependency travels *with the script*. That is strictly better than a container-level freeze —
which is the mechanism that produced the 246-package artifact in the first place. If a pinned set is
ever wanted, `uv.lock` beside a `pyproject.toml` is the form, not a flat freeze.

⚠️ **One caveat I cannot resolve from here:** `system python3` is 3.14 with a broken venv and 3.12
works (per `feedback_python_use_uv`). Whether the *new* container needs its own interpreter pin
depends on tooling that does not exist yet (R1). Flagged, not decided.

### 2.7 Git remotes — the highest-risk part of the bootstrap (Dean's TODO)

Inventoried 2026-08-16. This is the one area where a copy-paste mistake is **silent until push time**,
and where the consequence is pushing to someone else's repo. Dean's instruction: verify every remote
points at the new location, ensure no wrong refs are copied, add upstream push protection, and analyze
the several other remotes in play.

#### (a) What exists today

**Bare repo (`repo/`):**

```
origin    git@github.com:deanlorenz/llm-d-workload-variant-autoscaler.git   (fetch + push)
upstream  https://github.com/llm-d/llm-d-workload-variant-autoscaler.git    (fetch)
upstream  READ-ONLY-UPSTREAM-DO-NOT-PUSH                                    (push)
remote.pushdefault = origin
push.default = simple
```

**Nested repo — `benchmark/llm-d-benchmark/`** (a separate repo inside the benchmark worktree):

```
origin  git@github.com:deanlorenz/llm-d-benchmark.git          (fetch + push)
ofer    https://github.com/biranofer/llm-d-benchmark.git       (fetch)
ofer    READ-ONLY-MIRROR-DO-NOT-PUSH-TO-OFER                   (push)
```

**`dean-ai-overlay/`:** `origin git@github.com:deanlorenz/dean-ai-overlay.git` only. Cross-container by
nature (§ 7) — it should stay a single shared repo, *not* be re-cloned per container, or the "shared
mechanism" idea dies immediately.

Every WVA worktree (`benchmark`, `autoscaling-viz`, `spec-poc`, …) shares the bare repo's remotes, as
expected from the worktree model — there is exactly one remote set to get right per container, not one
per worktree.

#### (b) The push-protection mechanism already in use — carry this over verbatim

The **bogus-pushurl** trick:

```
remote.upstream.pushurl = READ-ONLY-UPSTREAM-DO-NOT-PUSH
remote.ofer.pushurl     = READ-ONLY-MIRROR-DO-NOT-PUSH-TO-OFER
```

It is not a valid URL, so a push fails at transport resolution and **prints the reason in the error
message**. This is mechanical enforcement of the never-push-to-upstream convention rather than
documentation of it, and it is the single best pattern in the current setup for the new repo to
inherit. Combined with `remote.pushdefault = origin`, there are two independent layers.

**Recommendation:** adopt it for *every* read-only remote in the new container, from the moment the
remote is added — not after the first scare. Name the string for the specific remote
(`READ-ONLY-<WHO>-DO-NOT-PUSH`) so the error identifies which one was attempted.

#### (c) Hazards found — two, both concrete

**H1 — two branches track `upstream`, and the safety is layered rather than absolute.**

```
branch.main.remote       = upstream    merge = refs/heads/main
branch.ta-testing.remote = upstream    merge = refs/heads/main
```

`ta-testing` tracking `upstream/main` is fetch-correct (it rebases from upstream) but means the
`remote=upstream` setting is not unique to `main`. Pushes are saved by `remote.pushdefault = origin`
*and* by the bogus pushurl. **The hazard is in the copy:** a bootstrap that reproduces
`branch.*.remote` entries while dropping `pushdefault` re-arms both branches. Since the new repo has no
`main` yet (R5), the correct action is not to copy branch-tracking config **at all** — set it per
branch as branches are created.

**H2 — ~14 sibling llm-d repos live one directory up, several name-adjacent to the new repo.**

`~/code/llm-d/` contains, among others: `llm-d-benchmark`, `dima-llm-d-benchmark`, `inference-perf`,
`llm-d-inference-scheduler`, `llm-d-inference-sim`, `llm-d-infra`, `llm-d-kv-cache-manager`,
`llm-d-model-service`, `llm-d-routing-sidecar`, `llm-d-deployer`, `llm-d-workload-variant-autoscaler`,
**`llm-d-wva`**, **`wva-dean`**.

The last two are the dangerous ones: they are WVA-named, unexplained, and sit adjacent to where a new
`llm-scaler` container would be created. Any bootstrap step that resolves a path by pattern, or copies
a `.env`/`.git/config` from "the WVA repo," can land on the wrong one. **`llm-d/llm-d` itself is not
cloned here** — so the guides-currency-check task in CURRENT.md reads it remotely; that is a *gap to
be aware of*, not a wrong ref.

#### (d) What the new container needs — a checklist, not a copy

**Set explicitly; never inherited from a copied config:**

1. `origin` → `git@github.com:deanlorenz/llm-scaler.git`. Verify with `git remote -v` **and** a
   `git ls-remote origin` that actually reaches the right repo.
2. **`upstream`: decide whether it exists at all.** `llm-scaler` is Dean's own repo. If it has no
   upstream-fork relationship, **do not create an `upstream` remote** — an empty-but-present `upstream`
   is worse than none, because scripts test for its existence (§ 2.2a's R5 point is the same issue
   seen from the script side).
3. If any read-only remote *is* added (Ofer, an llm-d repo, the old WVA for cherry-picking), set its
   `pushurl` to a `READ-ONLY-…-DO-NOT-PUSH` sentinel **in the same command sequence** that adds it.
4. `remote.pushdefault = origin` — cheap, and the layer that saved H1.
5. **Do not copy `branch.*.remote` / `branch.*.merge`.** Set per branch at creation.
6. **Assert, don't assume.** A one-line verifier — every remote's push URL is either `origin` or a
   `READ-ONLY-*` sentinel — is worth having as a script, because it is the kind of check that is
   obvious to run once and never again. Good candidate for the pre-push gate.

**Explicitly out of scope for the new container:** the `benchmark/llm-d-benchmark` fork remotes
(`origin` = Dean's fork, `ofer` = read-only mirror). They come with the harness whenever the benchmark
port happens (D6 puts that last) and should be re-verified *then*, against that repo's own needs — not
pre-created now.

⚠️ **Not verified:** what `llm-d-wva/` and `wva-dean/` are. Named, flagged, not investigated — they
matter here only as collision risks for path resolution.

---

## 3. The open decisions

Ordered by what blocks what. Each has a recommendation.

### D1 — ~~One repo, two projects~~ **N/A per R4**

**Scope is effort 2 only.** Two GitHub repos exist for certain; if the split proceeds Dean leans
**(c)** — two repos, two containers. So there is no shared-container design to make, and the
one-vs-two-plans-branches question dissolves: one repo, one container, one plans branch.

**What this changes downstream:** (c) means a future effort-3 container is *another run of this same
bootstrap*. That is the strongest argument for R6 — capture the mechanism, because it will have at
least two consumers, and the second one is foreseeable rather than hypothetical.

<details>
<summary>Original three-shape analysis (retained — the reasoning may matter if the split is revisited)</summary>

### D1 (original) — One repo, two projects: how do they divide?

Efforts 2 and 3 (WVA refactor, KEDA scaler) are named as possibly-two-projects but one repo was
given. Three shapes:

| | Shape | Consequence |
|---|---|---|
| **a** | One repo, one container, branches divide the efforts | One plans branch, one CURRENT, one convention set. Simplest. Risk: two missions' state in one tracker — the thing CURRENT.md's bounded-shape rules already strain against with *one* mission. |
| **b** | One repo, one container, **two plans branches** (`plans-refactor`, `plans-keda`) | Clean state separation, shared conventions. Cost: two sync sessions, or one sync session with two CURRENTs — the single-writer model is per-file, so this is legal but unexercised. |
| **c** | Two repos, two containers | Maximum isolation, maximum duplication. Contradicts the one-repo premise. |

**Recommendation: (a) to start, with (b) as the known escape hatch.** Reason: the split into two
projects is itself described as tentative ("may be splitting"). Building two-project machinery
before the split is decided is speculative structure. (a) → (b) is a later branch-and-move, not a
rebuild.

**Needs your call.** If the split is firmer than the phrasing suggests, (b) from the start avoids a
migration.

</details>

### D2 — Does `plans` live in its own worktree, or in the container's dot-folder?

You flagged this as previously discussed. Setting out the actual trade, since the sweep gives new
evidence.

**Today:** `plans/` is a top-level worktree on an orphan branch, and the container `.claude/` is
untracked.

**Proposal on the table:** plans content moves under the container's dot-folder (e.g.
`.plans/` or inside `.claude/`).

| | For | Against |
|---|---|---|
| **Own worktree (today)** | Everything under it is version-controlled, including `.claude/skills/`. `EnterWorktree` works. It appears in the workspace folder list, so sessions in it are findable in VSCode history (per `state-commands-design` § 7 — this is *correctness*, not tidiness). Orphan branch keeps it out of every code PR diff. | Occupies a top-level slot. Requires the symlink farm to be reachable from other worktrees. |
| **Container dot-folder** | One less top-level entry; naturally "not part of the code". Skills discoverable without symlinks — a real simplification of §2.4's fragile bit. | **Loses version control unless separately git-init'd** — the container is not a repo, which is exactly why today's `.claude/` is untracked. A dot-folder plans directory inherits that unless deliberately made its own repo, and then you have a second repo to manage. `EnterWorktree` does not apply. Sessions rooted there may not appear in VSCode history. Hidden directories are easy to forget in backups. |

**DECIDED (Dean): keep `plans/` as its own worktree, exactly as today.**

⚠️ **My counter-proposal here was redundant** — I proposed "version-control the container settings
inside `plans/` and symlink outward" as if it were new. **It is already the implementation** (§ 2.4):
`container/.claude/settings.json` is a symlink to `plans/.claude/container-settings.json`. I had
misread the situation by checking the file's content and not its type.

**Dean's follow-up question, answered:** *"'symlink out'? Do you mean files are in plans, and any file
needed in the container is a symlink to a file in plans? If going the other way, does git save the
contents?"* — Yes to the first; and going the other way, **no, git would not save the contents.** Full
reasoning in § 2.4, but the short form is the invariant worth carrying to the new repo:

> **The repo holds the content; the container holds the pointer.** A symlink *inside* a repo is stored
> as link text only, leaving the real content untracked. A symlink *outside* the repo costs git
> nothing, and the target is tracked as ordinary content.

That applies identically to `container-settings.json` and to the 13 skill symlinks. It is the rule the
new container should be built to, and the reason today's arrangement is right rather than incidental.

### D3 — What happens to memories?

The problem from §2.3(a): memories are keyed to the bare-repo path and will not appear in the new
workspace.

Options:

| | Approach | Assessment |
|---|---|---|
| **a** | Copy the `memory/` dir into the new project's slug dir | Direct, works immediately. Creates **two diverging copies** of every `feedback_*` rule. A rule corrected in one workspace stays wrong in the other — and these are behavioral rules, so divergence means the two workspaces behave differently for reasons nobody can see. |
| **b** | Symlink the new project's `memory/` at the existing one | Single source of truth, zero divergence. Both workspaces read and write the same files. Risk: `project_*` memories are WVA-specific and would leak into the new workspace's context as noise; and a new-repo memory would appear in WVA sessions. |
| **c** | **Split by kind**: `feedback_*` (portable working rules) shared via symlink or a shared dir; `project_*` (per-mission state) stays per-workspace | Matches the actual semantics — `feedback_*` is *how Dean wants work done* and is repo-independent; `project_*` is mission state and is not. Cost: needs a mechanism, since Claude Code gives one flat dir per project. |
| **d** | Promote `feedback_*` content into `conventions/` (the new plans tooling) and let memory be per-workspace scratch | The most structural answer: these rules keep being re-learned as memories *because* there was no conventions mechanism. Now there is one (`plans-tooling`, `conv` tools). Cost: the largest up-front effort, and `MEMORY.md`'s index is what's actually auto-loaded, so the loading path differs. |

**DECIDED (Dean): (c) and (d) in substance — but by a different mechanism. Harvest, don't share.**

The ruling, in his sequence:

1. **Harvest the memories for rules first.** The ~45 `feedback_*` files are mined into
   rules/conventions. This is a **must-have**, not a nice-to-have.
2. **Regenerate one by one, as needed.** The new workspace does not receive a memory set. It grows its
   own as it learns them, the same way this one did.
3. **Copy anything important that is left over** — after harvesting, whatever did not become a rule and
   still matters crosses individually.
4. **Re-evaluate and clean up** — this workspace's memory dir gets the same treatment; the harvest is
   an audit of it, not only a source for the new repo.
5. **Global memories should eventually live in `dean-ai-overlay`** (see § 7).

**Why this beats my symlink recommendation, and it isn't close.** I proposed sharing `feedback_*` via
symlink so the new workspace "is not born rule-less." Three things wrong with that:

- It preserves the *memory* form for content that should be *rules*. Memories are recalled
  probabilistically by description-matching; a convention is fetched deterministically by name. For
  content that governs behavior, the second is strictly better — and (d) was already the acknowledged
  right direction, so symlinking would have entrenched the form it was meant to replace.
- Sharing makes both workspaces' memory dirs a shared mutable surface — a write from either changes the
  other's behavior invisibly. The very thing the single-writer model exists to prevent, reintroduced at
  a different layer.
- It relies on an **unverified platform assumption** (that recall follows symlinks). Harvesting needs no
  such assumption, so **the open verification question in the previous revision is now moot** — dropped,
  not carried.

**The path-keying finding inverts.** § 2.3(a) treated "memories don't follow the workspace" as the
problem. Under harvest-and-regenerate it is a **feature**: the new workspace's memory dir starts empty
*by construction*, so nothing arrives by accident and every entry has a reason. The mechanism enforces
the discipline for free.

**One thing to watch, and it is the real risk here:** harvesting ~45 files is the single largest chunk
of judgment work in this whole bootstrap, and it is the step where content loss is both easy and
invisible — the same failure mode `feedback_current_state_preservation` describes. It wants the
verify-or-copy-then-delete discipline applied per file: a `feedback_*` memory is deleted only once its
content demonstrably exists as a rule.

**AGREED (Dean): the harvest gets its own design doc, and it belongs to the atomic-step Type-2 work —
but it must be applied in the context of this migration.**

That dual placement is the substance of the ruling, so stating precisely what it implies:

- **Ownership:** the harvest *mechanism* — how a memory becomes a rule, what the rule format is, how
  loss is prevented, how `MEMORY.md`'s index relates to a fetched convention — is **atomic-step Type-2
  work**, not this doc's. This doc must not design it.
- **The home already exists, and the memory pass is already a named-and-deferred section of it.**
  Verified by reading it (not inferred from CURRENT.md):
  [`planning/harvest-classification.md`](harvest-classification.md), committed `900024f5`, 215 lines, is
  the prerequisite table for `conventions-harvest-spec.md` (Migration 1, M1.2–M1.4). Two things about it
  matter here:
  - Its scope note says the current pass **deliberately covers only the two convention files**, "per
    Dean's request to validate the classification scheme on the largest, clearest source before
    extending it to the ~30 `feedback_*`/`project_*` memories" — that memory pass is explicitly called
    "a separate, messier pass, not done as a full pass here."
  - It already has a **`## From feedback_*/project_* memories — partial, started 2026-08-15`** section,
    holding one memory harvested early at Dean's specific request, with the note "expect this section to
    grow piecemeal, ahead of the full pass."

  So the harvest is **not an unclaimed task and not a new doc** — it is a named, deliberately-deferred
  section of a committed doc, with a classification scheme (`conv:<topic>` / `role:<role>` / `model`)
  already validated on a cleaner source first. The right move is to **trigger that pass**, not to author
  anything parallel to it.

  **➡️ ROUTED (2026-08-16):**
  [`plan__harvest-needs-repo-scope-axis-for-second-repo.md`](../session/handoffs/plan__harvest-needs-repo-scope-axis-for-second-repo.md)
  — sent to the atomic-step-protocol-brainstorm planner, carrying the single requirement below and
  nothing else. Deliberately a *separate* handoff from the `sync-main` one: different doc, different
  owner-step, and it must not be blocked behind a script change.
- **This migration is the forcing application.** A harvest mechanism with no consumer is a design
  exercise; this bootstrap is the concrete consumer that makes it real, and it supplies the one
  requirement a purely-internal harvest would not: the output has to be **portable to a repo that has
  none of this history**. That is a stronger constraint than "tidy up our memories," and it is the
  reason to do the two together rather than sequentially.
- **Practical consequence for sequencing:** the harvest is the pre-gate work item (§ 4), but it is
  *shared* pre-gate work — this doc contributes the migration requirements to it, and the atomic-step
  thread owns the mechanism. Coordination goes through a `plan__` handoff, not through this doc editing
  theirs (the owner may be editing it right now — CONVENTIONS' concurrent-owner rule).
- **The one requirement this doc contributes, stated for that handoff:** classification must include a
  **repo-specific vs global** axis, because D3 point 5 sends globals to `dean-ai-overlay` (§ 7) while
  repo-specific ones stay behind. A harvest that only sorts by *topic* would not produce that split, and
  redoing the classification later over ~45 files is exactly the kind of rework worth one sentence now.

### D4 — ~~Driven from here, or from the new workspace?~~ **RETIRED by R3**

Dean does the bootstrap copying manually, and may copy the whole `plans/` dir over as reference.
There is no cross-container write, so the pre-action-gate collision that made this a real question
does not arise. **No decision needed.**

*What was worth keeping from the analysis:* the case for a `bootstrap-workspace.sh` rested on
reviewability across a boundary that no longer exists — so the script is **not** the deliverable.
The **manifest** is: an explicit list of what crosses, what gets fixed on arrival, and what stays
behind. That is § 2.2 (fix-on-arrival), § 2.5 (leave behind), and D5/D6 (what crosses and in what
order).

*Still worth naming:* the first session launched in the new container has no conventions loaded,
because the conventions arrive as content rather than as a running protocol. Whatever that session
does first should therefore be small and verifiable — § 4 step 5's handoff round-trip is a good
first task precisely because it exercises the protocol without depending on judgment.

### D5 — Which skills port, and how do the path-pinned ones get parameterized?

13 skills exist. They divide by portability:

| Class | Skills | Port |
|---|---|---|
| **Portable, no changes** | `s-note`, `s-plan`, `s-session-name`, `s-session-done`, `s-state-park`, `s-state-sweep`, `s-state-consolidate` | copy as-is |
| **Portable, conventions-dependent** | `s-coder`, `s-design-review`, `s-sync-current`, `s-pre-push` | copy; they reference conventions docs whose content is being ported anyway. `s-pre-push`'s gate list is Go/WVA-shaped and mostly still applies. |
| **Container-pinned** | `s-sync-main` (6 absolute paths incl. `allowed-tools:` frontmatter) | needs rework — see below |
| **Repo-pinned** | `s-pr-triage` (assumes the WVA PR/upstream topology) | copy, then re-point at the new repo |

`s-sync-main`'s frontmatter is the interesting case: `allowed-tools:` grants are matched literally,
so a relative path there does not work — the absolute path is doing real work, not just
documentation. Two ways out: (i) per-container copies of the skill with the paths rewritten, or
(ii) a wrapper script at a fixed relative location, with the grant on the wrapper.

**Recommendation: (ii), a wrapper.** It converts N path-pinned grants into one, and the same
pattern already proved necessary for the checkpoint scripts (launching through an on-disk wrapper
was how the `pgrep` self-match was worked around, per CURRENT's 2026-08-15/16 entry). But this is
rework, not a copy, so it is the one skill that should **not** block the first bootstrap — the new
workspace can live without `main`-syncing on day one.

### D6 — Which WVA and benchmark tooling comes over, and when?

You named this but did not scope it. The candidates I can see, with an opinion on timing:

- **Benchmark harness surface** (`benchmark-*` Makefile targets, the `.env` guard contract,
  `KUBE_CONTEXT` verification, the 10 guarded destructive targets, `benchmark-init`). Substantial
  and cluster-touching. **Later** — it depends on the new repo having something to benchmark.
- **Viz toolchain** (`autoscaling-viz`: `extract_real_trace.py`, `render_real_trace.py`, the
  four-command chain, `COVERAGE-CHECKS.md`). Self-contained, no cluster contact, and would apply
  to a KEDA scaler nearly unchanged. **Good early candidate** — arguably the highest-value port
  after the conventions.
- **Checkpoint loop** (`session-snapshot.sh` + `tick-shared-scan.sh`). Relocatable per §2.1.
  ⚠️ Carries known live state: `tier1-session-start.sh` is committed-but-not-wired and would fail
  its own required-arg validation; the `container-settings.json` SessionStart entry it needs was
  blocked once by `guard-settings-edit.sh` and must not be self-approved. **Port the two working
  scripts; do not port the unwired auto-start** until its owner (the
  atomic-step-protocol-brainstorm planner) finishes it.
- **`plans-tooling` conv tools.** These *are* the new tooling. **First**, not later — they are the
  mechanism the new repo is meant to be configured with.

**DECIDED (Dean): all of them are needed.** Nothing on this list is dropped.

**Clarifying what "order" meant, since it was unclear** — my "conventions → viz → benchmark" was
about **which port is attempted first in time**, not about priority or about anything being optional.
Two separate reasons for wanting *an* order at all, and only the second is load-bearing:

1. *Weak reason — value-per-effort.* Viz is self-contained (2 pip packages, no cluster) so it pays off
   sooner than benchmark, which needs a cluster and something to measure. This is only scheduling
   advice and can be ignored freely.
2. **Strong reason — real dependency.** Two hard constraints, and these are not preferences:
   - **Conventions + conv tools must come first**, because they *are* the thing the new repo is meant
     to be configured with (R1's gate is precisely their completion). Porting other tooling first
     means porting it against conventions that do not exist yet, then reconciling.
   - **Benchmark cannot be meaningfully ported until the new repo has something to benchmark.** Not a
     preference — a dependency on effort 2's own progress. The harness measures a running scaler.

So the honest statement is: **conventions first (hard), benchmark last (hard), viz anywhere in
between (free choice).** Everything else about "order" was scheduling opinion and Dean can disregard
it.

**Still open from this decision:** whether anything is *missing* from the inventory above. Dean said
"need them all" but did not add items, so the list may simply be complete — worth one more pass when
the gate lifts, since the inventory was built from CURRENT.md's view of active work and something
parked (the R8 lesson) could easily be absent.

---

## 4. Sketch sequencing (not a plan) — **gated by R1**

Nothing below starts until the new plans tooling and atomic-step rules are complete (R1). The gate
is real: step 2 *is* those artifacts, so the sequence cannot begin without them.

**Before the gate lifts — what is actionable now.** D1–D6 are settled (§ 6), so this is no longer a
decision list; it is real work that does not wait:

- **Trigger the D3 memory harvest pass** — not author it. `harvest-classification.md`'s memory section
  exists and is deferred by design; this migration is its forcing consumer, and the one requirement to
  contribute is the **repo-specific vs global** classification axis (D3). Goes to that doc's owner via a
  `plan__` handoff, since it is being actively edited.
- **Generalize `sync-main`** per § 2.2a — parameterize on `(container, tracked_branch, upstream_remote)`
  with "neither exists yet" as a supported state. Best done *here*, where there is a real `main` to test
  against, before the new repo needs it.
- **Write the remote-verification assertion** (§ 2.7d item 6) — every remote's push URL is either
  `origin` or a `READ-ONLY-*` sentinel. Useful in *this* container immediately (it would catch H1's
  latent shape), and it is then a ported tool rather than a new one.
- **Keep § 2 current.** If a script gains a hardcoded path between now and then, the sweep is stale and
  the port inherits the bug. Cheap to re-run: the greps in § 8.
- **Answer the § 6 open items** that need no new tooling: the inventory-completeness pass, and the
  Bob-as-coder conventions question (§ 2.6a2).

**After the gate lifts:**

1. **Container + bare repo + first worktrees.** `git clone --bare`, container dir, `Main`, `plans`
   (orphan), `.code-workspace`. Yours, manually (R3).
2. **Port conventions + conv tools** into the new plans branch. This is the "new version only"
   content — authored against the completed new tooling, not copied from `session/CONVENTIONS.md`.
3. **Port skills** per D5's classes, minus `s-sync-main`.
4. **Settings + permissions — allowlist only** (§ 2.5). Worktree-gate hooks and the path-free Go
   grants cross; the `Edit()` grants do not; `Bash(mv …)` waits to be proven needed. Note
   `guard-settings-edit.sh` blocks self-approval of settings edits, so this step needs you by
   design — which is also the safeguard against the allowlist quietly becoming a mirror.
5. **Verify the session protocol end-to-end**: write a handoff, rename `.WIP`, rename `.DONE`, from
   a second worktree. This is both the smoke test and the test of § 2.5's `Bash(mv …)` question —
   if it is refused here, the grant is needed; if not, it was junk. Good first task for a
   conventions-less session (per D4's remnant note).
6. **Memory decision executed** per D3.
7. **Checkpoint loop** started under the new container — the two working scripts only, **not**
   `tier1-session-start.sh` (D6's warning).
8. **Tooling ports** per D6, in the recommended order.

---

## 5. What this doc does not decide

- The actual refactor design for effort 2, or the KEDA scaler design for effort 3. Out of scope —
  this is workspace bootstrap only.
- Whether WVA genuinely splits into two projects. D1 is built to survive either answer.
- Anything requiring a GitHub write (the `llm-scaler` repo's own settings, branch protection,
  remotes beyond `origin`).
- Any cluster or benchmark action.

## 6. Open questions — status after two rounds

**All six original decisions are now settled or retired:**

| | Status |
|---|---|
| **D1** — one repo, two projects | **N/A** (R4 — effort 2 only; two repos if the split proceeds) |
| **D2** — plans worktree vs dot-folder | **DECIDED** — keep the worktree; the "symlink out" pattern was already implemented (§ 2.4) |
| **D3** — memory strategy | **DECIDED** — harvest into rules, regenerate one by one, copy leftovers, then clean up; globals → overlay |
| **D4** — driven from here or there | **RETIRED** (R3 — manual bootstrap, no boundary to cross) |
| **D5** — which skills port | **DECIDED** — per the four classes; `s-sync-main` generalized per R5, off day one |
| **D6** — tooling ports | **DECIDED** — all of them; order is conventions-first / benchmark-last (hard), viz free |

### Still genuinely open

1. **Where the bootstrap mechanism lives** — `dean-ai-overlay` revived, `plans-tooling` extended, or
   both separately (§ 7.2 recommends the third, and recommends *not* deciding until R1's gate lifts,
   since `plans-tooling`'s final scope is unknown).
2. **Is the § 2.5 / D6 inventory complete?** "Need them all" settled the *disposition* of everything
   listed, not whether the list is exhaustive. The R8 miss is the precedent — the inventory was built
   from CURRENT.md's view of *active* work, so parked-but-wanted things are systematically the ones it
   would miss. Worth one deliberate pass by you.
3. **Bob-as-coder settings** (§ 2.6a2) — **new TODO, Dean's ask.** `.bob/` and `.revisions/` themselves
   are settled ("see if we can live without them" → they don't port), but Dean wants Bob usable as a
   coder, which needs a conventions answer: how a Bob session loads the coder rulebook, respects
   worktree confinement and the write gate, and participates in the handoff protocol. Belongs to the
   conventions work, not the container bootstrap. Note `feedback_sendmessage_vs_file_handoffs` already
   records that the file-based protocol was chosen partly *because* it works cross-tool — so the channel
   exists; the rulebook-loading half does not.
4. **Interpreter pin for the new container** (§ 2.6b) — depends on tooling that does not exist yet;
   flagged rather than decided.
5. **What are `llm-d-wva/` and `wva-dean/`?** (§ 2.7c H2) — two WVA-named sibling repos in
   `~/code/llm-d/`, unexplained, sitting adjacent to where the new container would go. They matter only
   as path-collision risks, but that is enough to want them identified before a bootstrap resolves any
   path by pattern.

### Two things I am flagging rather than deciding

- **The D3 harvest wants to be its own task, with its own doc.** It is the largest piece of judgment
  work in the bootstrap (~45 files), the one where loss is invisible, and — unlike everything else
  here — it is **useful before R1's gate lifts**, because the rules are what the new tooling will
  carry. Treating it as one line in a checklist is how it goes wrong.
- **Live hygiene finding in *this* workspace, not a port item:** ~50 `session/handoffs/*.DONE` files
  are sitting untracked. CONVENTIONS says the sync commit `git rm`s them; at fifty, that half is not
  happening reliably. Separately: the container junk from § 2.5 (empty `agents/`, two May-11 abandoned
  worktrees carrying toolchain binaries, `.devcontainer.OLD`, `hooks.old`) is worth cleaning on its
  own merits. I have touched neither. Both get harder to answer with time, for the same reason § 2.5
  gives — nobody can say what it is for.

---

## 7. The bootstrap mechanism itself, and `dean-ai-overlay` (R6)

R6 raises the altitude: **this migration should leave behind a mechanism, not just a migrated
workspace.** Dean names `dean-ai-overlay/` as the thing originally built for exactly this — adding his
conventions and tooling to a new repo — described as early-stage, stale, unstable, untested, unplanned,
but directionally right.

### 7.1 What the overlay actually contains (inspected 2026-08-16)

Dean's recollection was that it "only contains tasks now, and even these are stale." It has more than
that. `dean-ai-overlay/` is **its own git repo** (single commit, `a5cf943` "Initial AI overlay
workflow"):

```
README.md  CONTEXT-CHECKLIST.md  CURRENT.md  PRECEDENCE.md  META.md  zone_files.txt
templates/   pr-plan.md  design-doc.md  adr.md  user-guide.md
roles/       design-facilitator.md  implementer.md  design-scribe.md  reviewer.md
sessions/    DESIGN.md  IMPLEMENTATION.md  REVIEW.md  DOCS.md
scripts/     load-context.sh
vscode/      tasks.json          ← live: symlinked from container/.vscode/tasks.json
```

Two observations that matter more than the file list:

- **The skeleton is the thing being rebuilt.** `roles/`, `sessions/`, `templates/`, `PRECEDENCE.md` map
  almost one-to-one onto what this workspace grew independently: role-scoped write domains, session
  types, doc-type templates, and a precedence order among instruction sources. The overlay guessed the
  right decomposition before the practice existed. What it lacks is everything the practice *taught* —
  the handoff protocol, the single-writer model, the worktree discipline, the checkpoint loop.
- **It is already wired in, not merely adjacent.** `container/.vscode/tasks.json` is a live symlink into
  it. So the overlay is a current dependency of this container, which slightly contradicts "stale" —
  one file of it is in daily use.

### 7.2 Where the mechanism should live — the honest answer is "not yet decided, and that's fine"

Three candidate homes, and the choice interacts with R1:

| | Home | Assessment |
|---|---|---|
| **a** | Revive `dean-ai-overlay` as the mechanism | Matches original intent; already its own repo, so shareable across containers; already symlinked in. But it is unversioned-in-practice (one commit), untested, and its content predates everything learned since. Reviving it means rewriting nearly all of it. |
| **b** | The new plans tooling (`plans-tooling`) becomes the mechanism | It is *already* the generalization effort — `conv.sh`/`sec.sh` and the `conventions/` format are repo-agnostic by construction. R1 gates on it anyway. But it is scoped to conventions, not to containers/worktrees/settings/skills. |
| **c** | Keep them separate: `plans-tooling` = convention mechanics; overlay = **workspace** bootstrap (container layout, symlink farm, settings, skills, venv policy) | Cleanest separation of concerns. The overlay's existing skeleton is closer to (c)'s scope than to (b)'s — `roles/`, `sessions/`, `PRECEDENCE.md` are workspace-shaped, not convention-file-shaped. Cost: two mechanisms to maintain. |

**Recommendation: (c), and don't decide it yet.** Reasoning: the two concerns genuinely differ — a
convention file is *content that gets fetched by name*; a container layout is *structure that gets
created once*. The overlay's own skeleton already sits on the workspace side of that line. But
committing now would be premature, because R1 means `plans-tooling`'s final shape is unknown, and it may
absorb more than conventions. **Revisit when the gate lifts.**

### 7.3 What to capture *while* doing this migration, regardless of where it lands

This is the actionable part of R6, and it is available now:

- **The manifest** (§ 2.2 fix-on-arrival, § 2.5 leave-behind, § 2.6 env policy, D5 skill classes) — this
  doc already *is* the first draft of the mechanism's content. Keeping it accurate is the capture.
- **The invariants**, stated once each, because they are what generalize past this one repo:
  - *The repo holds the content; the container holds the pointer.* (§ 2.4 / D2)
  - *An entry crosses only if someone can say what breaks without it.* (§ 2.5 / R2)
  - *Staleness is not abandonment; only the owner can tell them apart.* (§ 2.5 / R8)
  - *Config over inference for paths and branches.* (§ 2.2a / R5)
  - *Dependencies travel with the script, not with the container.* (§ 2.6)
- **The decision record** — D1–D6 with their retirements and reversals. A second bootstrap will hit the
  same questions; the reasoning is worth more than the answers.
- **Global memories → overlay** (Dean's D3 point 5). This is the one piece of § 7 that is concrete and
  unblocked: `feedback_*` memories that are *not* WVA-specific (American English, no-push, uv, no
  in-place edits, DCO, worktree discipline) belong in a cross-repo home, and the overlay is the only
  candidate that is already cross-repo. **Falls out of the D3 harvest naturally** — the harvest has to
  classify each memory anyway, and repo-specific-vs-global is one of the axes.

### 7.4 What I would *not* do

Reviving the overlay's stale content as a starting point. `PRECEDENCE.md`, `roles/`, `sessions/` predate
the handoff protocol, the single-writer model, the review pipeline, and the atomic-step work — the
skeleton is right and the flesh is superseded. Read it for the decomposition, then write fresh against
what the practice actually taught. Same call as the docs: structure ports, content doesn't.

---

## 8. Sources

Read directly for this doc on 2026-08-16 — not recalled:

- Container: `ls -a`, `.claude/{settings.json,settings.local.json,skills/,agents/,worktrees/}`,
  `.vscode/`, `wva.code-workspace`; confirmed container is not a git repo.
- `plans/`: `scripts/` (all 12), `.claude/`, `session/`, `.gitignore`.
- Greps: `/home/dean` and `llm-d-workload-variant-autoscaler` across `scripts/` + `.claude/` +
  both conventions docs; path-derivation lines in the five checkpoint/toc scripts.
- Global: `~/.claude/settings.json`, `~/.claude/` listing,
  `~/.claude/projects/-home-dean-code-llm-d-llm-d-workload-variant-autoscaler-repo/memory/` listing.
- `plans-tooling`: branch, tree, `conventions/`, `scripts/`, `git log`.
- CURRENT.md and MEMORY.md as loaded context (used for the live-state warnings in D6, e.g. the
  `tier1-session-start.sh` and `guard-settings-edit.sh` hazards).

Second pass, for § 2.5's junk inventory (same day, after R2):

- `container/.claude/agents/` — `ls -la`, confirmed **empty**, dated May 11.
- `container/.claude/worktrees/` — `ls -la`, two directories dated May 11 (`engine-multi-analyzer`,
  `ta1-rebase`), the latter carrying `bin/` toolchain binaries and `cover.out`.
- `container/.claude/settings.local.json` — full read, contains one grant (`Bash(wc:*)`).
- `plans/.claude/settings.local.json` — full read, plus `git log -- <that file>` returning **no
  history**, which is the evidence for "accreted, not maintained."

Third pass, for R4–R8 and Dean's two TODOs (same day):

- **Settings diff:** `diff` of `container/.claude/settings.json` against `plans/.claude/settings.json`;
  full reads of both plus `container-settings.json`. **`ls -la .claude/*.json`** — this is the call that
  corrected § 2.4: it showed `settings.json` is a **symlink**, which the earlier content-only read had
  missed.
- **Gitignore/hidden:** `git status --ignored --short` and `git status --short` in `plans/`;
  `ls -a` on container `.bob/` and `.revisions/`.
- **Python:** container `requirements.txt` (246 lines, read in full), `.venv/bin/python --version`
  (3.12.3), a venv/requirements/lockfile scan across all worktrees, `pip list` inside
  `autoscaling-viz/.venv` (**empty**), an import scan across the viz `*.py` (yielding `matplotlib` +
  `yaml` as the only non-stdlib names), and `uv --version` (0.9.7 at `~/.local/bin/uv`).
- **Overlay:** `find` over `dean-ai-overlay/` and its `git log` (single commit `a5cf943`).

Fourth pass, for R9–R11 (same day):

- **Remotes:** `git -C repo remote -v`; `git -C repo config --get-regexp 'remote\.|push\.|branch\..*remote'`
  (the source for H1's two `remote=upstream` branches and for `remote.pushdefault`); `remote -v` in each
  nested repo (`benchmark/llm-d-benchmark`, `dean-ai-overlay`, and three WVA worktrees to confirm they
  share the bare repo's set); `find -maxdepth 3 -name .git` for the full repo inventory;
  `ls ~/code/llm-d/` for H2's sibling-repo list.
- **Harvest doc:** `planning/harvest-classification.md` read directly — head, `grep -in 'memor'`,
  line count (215), and `git log` (committed `900024f5`). This corrected a claim I had been about to
  make from CURRENT.md alone: the memory pass is not unstarted, it is a **named, deliberately-partial
  section** with one memory already harvested and a validated classification scheme.
- **Not read:** `.bob/custom_modes.yaml` and `.revisions/.directives` — listed only. So the
  Bob-as-coder TODO (§ 2.6a2) is scoped from the conventions side, not from whatever those files say.

**Corrections made to this doc, recorded rather than silently patched:**

1. **§ 2.4 claimed the container `.claude/settings.json` was untracked.** Wrong — it is a symlink into
   the tracked plans file. I inferred "untracked" from the container not being a git repo without
   checking the file type. This mattered: it produced a counter-proposal (D2) for something already
   implemented.
2. **§ 2.5 classified `spec-as-code` as junk.** Wrong — parked-but-wanted (R8).

**Not verified, flagged as such:**

- Whether `Bash(mv …/handoffs/*)` is actually required — § 4 step 5 is designed to answer it.
- The `Edit()` grants' inertness is taken from memory `feedback_shared_session_dirs_writable`, not
  re-tested here. That memory is the reason they are classed as junk, so if the port ever depends on
  the classification being right, re-test rather than trusting this line.
- `.bob/` and `.revisions/` purposes — inspected, not understood.

**No longer relevant:** whether recall follows a symlink inside `memory/`. D3's harvest ruling removed
the need for the assumption, so the question is dropped rather than carried as an open item.
