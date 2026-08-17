# Harvest classification table — feedback_*/project_* memories + governance-follow-ups.md

**Step 2b of `micro-rules-migration-plan.md`.** Same method as `harvest-classification.md` (the
convention-files table): a placement decision, not a correctness gate, all relocations (no new
policy — every row already exists as written memory content). Scope per Dean's own framing in
`harvest-classification.md` ("a separate, messier pass... the ~30 feedback_*/project_* memories and
governance-follow-ups.md incidents") — extended here to the full ~78-memory set actually on disk
(more accumulated since that line was written).

**Repo-scope axis (global vs. repo-specific) is explicitly OUT OF SCOPE for this pass** — per
`harvest-classification.md`'s own "Repo-scope axis... designed 2026-08-16, not yet applied (harvest
pass itself stays deferred)" section: design now, run later, not tonight. This table records `dest`
only, the same single axis the convention-files table used.

Column `dest` uses the same three values as the convention-files table: `conv:<topic>` (existing or
new — marked **NEW** where it doesn't already exist in `conventions/`), `role:<role>`, `model`
(→ `doc-and-session-model.md`). A fourth value, `SKIP (stale)`, is added for this table only — a
memory whose own content or a successor memory marks it superseded/historical with no standing rule
left to harvest. `SKIP (stale)` is not a placement error; it means there is nothing left to move.

Existing `conventions/` topics (20, from Step 2a): checkpoint-capture, code-deletion,
current-md-format, dev-guide-updates, doc-ownership-boundary, git-remotes, github-actions,
go-test-gates, handoffs, plan-authoring, plans-refs-in-code, pre-push, rebase-integrity,
review-pipeline, semantic-pivot-grep, session-start, skills-layout, status-files, triggers,
worktree-scope.

---

## From `feedback_*` memories

| # | Source | dest | Why |
|---|---|---|---|
| FM1 | feedback_american_english.md | `conv:doc-ownership-boundary` **NEW row, existing file** — actually its own small convention, see note | American spelling in docs/comments/prose; never mis-attribute an unrequested spellcheck normalization as something Dean asked for. Doesn't fit any existing topic's trigger — closest is a new tiny `conv:writing-style` topic (see below) rather than forcing it into doc-ownership-boundary. **Correction: give it its own file, `conv:writing-style` (NEW).** |
| FM2 | feedback_chat_file_links_full_path.md | `conv:chat-links` (**NEW**) | VSCode webview link rules: .md links must be workspace-root-relative to open; images never open via link, always inline via Read. Situational (only fires when recommending a file/image in chat) — its own small topic, no existing file fits (not a doc-authoring rule, not worktree-scope). |
| FM3 | feedback_check_handoffs_between_commits.md | `conv:handoffs` | Poll `session/handoffs/` between every commit and when idle; re-read the plan's own current TOC ranges, not stale trigger ranges. Same artifact/topic as the handoffs family. |
| FM4 | feedback_code_review_internal.md | `conv:review-pipeline` | "Code review before push" = internal plan-vs-diff read, never the `/code-review` skill (which writes to GitHub/tree). Same trigger as the review-pipeline convention. |
| FM5 | feedback_coder_no_current_edit.md | `role:coder` | Absolute boundary (never edit CURRENT.md or anything outside two sanctioned paths) — same character as CC6/CC15/CC17-19, a standing permission-boundary fact for the role, not a situational lookup. |
| FM6 | feedback_coder_no_unauthorized_subagents.md | `role:coder` | Never spawn a subagent without asking, even if a plan mentions it — absolute, always-true permission boundary for the coder role. |
| FM7 | feedback_coder_worktree_discipline.md | `conv:worktree-scope` | The two mandatory CWD/branch verification gates (before edit, before commit) — mechanically the same family as C14-C19/CC1-CC4. |
| FM8 | feedback_current_md_per_task.md | `conv:current-md-format` | CURRENT.md's per-task section structure; never overwrite a sibling task's state. Same convention as C8/C13. |
| FM9 | feedback_current_state_preservation.md | `conv:current-md-format` | Never remove CURRENT.md state without verifying it's captured elsewhere first. Same topic/trigger as FM8 — both fire "when editing CURRENT.md." |
| FM10 | feedback_dco_signoff.md | `conv:pre-push` | DCO verification before every push, especially post-rebase. Same checklist item family as C37/C41 (already itemized there as step 5) — this memory adds the post-rebase-drops-signoff detail and the pre-push-hook fact as an addition to the existing pre-push-checklist entry, not a new file. |
| FM11 | feedback_deletion_documentation.md | `conv:code-deletion` | DEPRECATED/DEFERRED classification + named dev-guide sections. Same convention as C36/CC10 — this is the fuller statement of the same rule (the existing harvested entry may be thinner; check for a merge-in, not a duplicate). |
| FM12 | feedback_doc_accuracy_discipline.md | `conv:doc-ownership-boundary` | Design decisions belong to Dean, elevate forks early, structured review summaries, precise handoffs, coders write Type 4 against finished code. Core doc-ownership-boundary material — same trigger as C20/C33. |
| FM13 | feedback_doc_housekeeping_after_pr2.md | `SKIP (stale)` | Scoped/expired standing decision tied to "until PR-2 lands" — PR-2 (#1523) is now OPEN/green per CURRENT.md; the deferral condition has resolved either way, and re-raising or not is a live judgment call, not a standing rule to harvest. |
| FM14 | feedback_doc_names_not_numbers.md | `conv:doc-ownership-boundary` **or NEW `conv:doc-taxonomy`?** — placed at `model` | This is really "how to talk about the taxonomy," directly the model doc's own subject matter (same class as C6/C11) rather than a per-step convention — no situational trigger fires it, it's a standing fact about vocabulary. → `model`. |
| FM15 | feedback_force_push_owner_is_planner.md | `conv:pre-push` | Planner (not coder, not Dean personally) force-pushes PR branches. Same topic as the force-push-explain entry (C41) — an ownership clarification on the same checklist item. |
| FM16 | feedback_gh_pr_edit_workaround.md | `conv:github-actions` | `gh pr edit` bug workaround (use `gh api -X PATCH` instead). Same trigger as C40 — fires whenever a GitHub-writing action is contemplated, this is a specific tool substitution within that same convention. |
| FM17 | feedback_git_archive_alias.md | `conv:git-remotes` | Never delete branches, use `git boidem`. Same topic as C43/C45 — a git-branch-lifecycle fact. |
| FM18 | feedback_git_commit_identity.md | `conv:pre-push` **or NEW?** — placed `conv:pre-push` | Never pass `-c user.name/email`; use defaults + `-s`. Fires at the same moment as the DCO checklist item (FM10) — folds into the same pre-push entry rather than a separate file. |
| FM19 | feedback_git_remote_rules.md | `conv:git-remotes` | Never push upstream, mirror-remotes are read-only, every code branch needs a matching origin branch. Same topic as C43/C44/C45 — this is the fuller, generalized statement (third-party remotes beyond just upstream) of the same rule family; check for overlap/merge with the existing entries, not duplication. |
| FM20 | feedback_handoff_own_reply_never_marked_done.md | `conv:handoffs` | Never mark your own outgoing handoff `.DONE`. Already identified as M1 in the memory-partial table in `harvest-classification.md` — same placement, already decided, just needs actually copying in. |
| FM21 | feedback_handoff_wip_state.md | `conv:handoffs` | Three-state machine, CURRENT.md editing lock, 2026-08-16 gitignore-of-new-handoffs correction. Same topic as C24/C27/C28/C30/C31/CC13 — check the gitignore detail is genuinely new content vs. already captured. |
| FM22 | feedback_handoff_workflow.md | `conv:handoffs` | Three-channel model overview + the (now-superseded) Write/Edit-blocked claim. **Caution: this memory's own Write/Edit-blocked claim is itself stale** (corrected by FM23/project_coder_write_confinement.md) — harvest only the parts still true (channel taxonomy, naming, addressing-by-real-branch-name), explicitly drop or footnote the superseded cp-workaround detail rather than copying it verbatim as current. |
| FM23 | feedback_handoffs_can_be_superseded.md | `conv:handoffs` | A handoff is true as-of-authoring only; check `git log` for newer commits before folding. Same topic — a verification-discipline addition. |
| FM24 | feedback_large_change_approval.md | `SKIP (stale)` — duplicates global CLAUDE.md | Already stated in the user's global `~/.claude/CLAUDE.md` (auto-loaded every session, every project) — harvesting into a project-scoped convention would be a pure duplicate of a rule that's already always-loaded from a different, higher-priority source. Not a placement; a genuine no-op. |
| FM25 | feedback_no_cd_sibling.md | `conv:worktree-scope` | Never `cd` into a sibling worktree; the one plan-agent cd+spawn exception. Same convention as C16/C17 — this is the sharper, repeat-incident-informed statement of the same rule (4+ recurrences noted). |
| FM26 | feedback_no_inplace_edits.md | `SKIP (stale)` — duplicates global CLAUDE.md | Same reasoning as FM24 — already in the always-loaded global CLAUDE.md. |
| FM27 | feedback_no_push_without_confirmation.md | `conv:pre-push` | Never push without Dean's explicit per-push confirmation, never chain commit+push. Same convention as C38 — this is a sharper/fuller statement (never chain) of the same entry; merge, don't duplicate. |
| FM28 | feedback_no_rebase_live_pr_branches.md | `conv:rebase-integrity` | Never rebase a live-PR branch without consulting Dean; merge un-rebased branches into a throwaway integration branch instead. Same topic as C42 — an important addition (the live-PR-branch exception) to the existing rebase-integrity entry. |
| FM29 | feedback_plan_doc_no_other_role_actions.md | `conv:plan-authoring` | Plans must never contain imperative verbs aimed at another role; scan every sentence + trigger `note:` fields. Same convention as C10/C35 — plan-authoring completeness requirement. |
| FM30 | feedback_pr_creation_checklist.md | `conv:pre-push` **or NEW `conv:pr-lifecycle`?** — placed `conv:github-actions` | Always ask who to assign a new PR to. Fires at PR-creation time, a GitHub-writing action — same trigger class as C40/FM16, folds into `github-actions` rather than inventing a fourth PR-specific file for one rule. |
| FM31 | feedback_pr_workflow_not_dispatching_check_mergeable.md | `conv:github-actions` | Check `gh pr view --json mergeable` before assuming a dropped webhook. Diagnostic procedure fired during a GitHub-PR-CI investigation — same file as FM16/FM30, all "things to know before/about a GitHub PR action." |
| FM32 | feedback_push_scope_narrow_to_named_artifact.md | `conv:pre-push` | "Push your X" scopes to X, not the whole branch tip; on `plans` specifically, Dean pushes the shared branch, planner never blanket-pushes. Same convention as C38 — a scope-precision addition to the no-push-without-confirmation entry. |
| FM33 | feedback_python_use_uv.md | `SKIP (stale)` — narrow, no existing topic fits, low standing-rule value | A tool preference for ad hoc Python scratch work, not tied to any per-step convention or role boundary — arguably belongs in a generic "tooling preferences" grab-bag that doesn't exist yet. Flagging rather than forcing: **candidate NEW `conv:tooling-preferences`** if Dean wants a home for this class of fact; otherwise leave in memory only. |
| FM34 | feedback_rebase_target_is_tip_not_sha.md | `conv:rebase-integrity` | Rebase targets the moving ref, never a pinned SHA; any SHA in a doc is informational-as-of-authoring. Same topic as C42/FM28. |
| FM35 | feedback_relative_links_within_docs.md | `conv:doc-ownership-boundary` **or model?** — placed `conv:plan-authoring` | Relative links can't cross a worktree boundary; ask rather than assume. This is a doc-authoring correctness fact (what a doc's own links must satisfy), same trigger as C10/C35/FM29 — fires when authoring/linking within a plan or reference doc. |
| FM36 | feedback_reviewer_writes_in_coder_tree.md | `conv:worktree-scope` | Review agents are strictly read-only outside their own worktree for git write-verbs, zero exceptions. Same convention as C18 — the reviewer-specific instance of the same write-verb boundary, with the concrete incident detail. |
| FM37 | feedback_semantic_pivot_grep.md | `conv:semantic-pivot-grep` | Already an exact 1:1 — this memory IS the named source for C7/CC8's entry. Confirm the existing harvested entry already captures this memory's content in full (it should, they're the same rule); if the existing entry is thinner, enrich it from this memory rather than creating a duplicate file. |
| FM38 | feedback_sendmessage_vs_file_handoffs.md | `conv:handoffs` | SendMessage unproven/unreliable for this project, file-based handoffs remain the channel. Same topic — a tooling-caution addition. |
| FM39 | feedback_session_title_convention.md | `conv:session-start` | Session title format (`[icon] subject Role`). Fires at session start, same trigger as C12 — a naming-convention addition to the session-start entry. |
| FM40 | feedback_shared_git_index_pathspec_commits.md | `conv:worktree-scope` | **This is the exact table gap the Step 2a coder flagged as unclassified** — CODER-CONVENTIONS.md §1's pathspec-commit paragraph. Confirmed: this memory is that rule, already written down, just never given a `harvest-classification.md` row. Placement: same family as C14-C19 (a concrete write-boundary mechanic for the shared `plans` worktree) — `conv:worktree-scope`, as a new entry within that existing file. **Resolves the open question this session's own status file recorded.** |
| FM41 | feedback_shared_session_dirs_writable.md | `conv:worktree-scope` | The two sanctioned shared paths ARE writable via Bash cp/mv despite Write/Edit being blocked there; corrects an earlier over-broad claim. Same topic as CC5's "single sanctioned write exception" detail already in the existing entry — enrich, don't duplicate. Note the further correction in FM42 below. |
| FM42 | feedback_subagent_cwd_pattern.md | `conv:worktree-scope` | The plan-agent-only cd+spawn pattern, `claude -p --allowed-tools` alternative, why EnterWorktree fails inside subagents from plans/. Same convention as FM25/C17 — the mechanics of the specific documented exception. |
| FM43 | feedback_sync_consumes_only_current_updates.md | `conv:handoffs` | sync consumes only explicit CURRENT-update handoffs, never every `plan__`. Same topic as C25/CC13 — the sync-side addressing rule, already substantially captured; check for completeness. |
| FM44 | feedback_sync_single_writer_model.md | `role:sync` | Single-writer model itself — this is standing behavioral posture specific to the sync role's own execution loop (who alone may write CURRENT.md/run /sync-current), matching C26's existing placement rationale exactly. Enrich `roles/sync.md`, don't duplicate into a convention. |
| FM45 | feedback_ta3_coder_role.md | `SKIP (stale)` | Memory's own content and the MEMORY.md index both flag this as a stale pointer describing an outdated role-assignment mechanism. Nothing standing left to harvest. |
| FM46 | feedback_tools_take_explicit_paths.md | `conv:doc-ownership-boundary` **or NEW?** — placed **NEW `conv:tool-authoring`** | Explicit --in/--out paths, no path discovery, one invocation per unit of work, output next to the data it describes. This is a coding/tool-design convention distinct from every existing topic (not doc-authoring, not worktree-scope, not a checklist) — fires when writing any analysis/driver script. New small topic file. |
| FM47 | feedback_trigger_doorbell_only.md | `conv:triggers` | Trigger `note:` field content restrictions + the "read as the recipient" sanity check. Same convention as C29/CC14 — already substantially captured; this adds the concrete sanity-check heuristic. |
| FM48 | feedback_unreachable_code_review.md | `conv:review-pipeline` | Verify why a path is unreachable before calling it benign during review. Same trigger as C9/CC16 — a specific review-technique addition. |
| FM49 | feedback_viz_render_symlinks.md | `SKIP (stale, mission-narrow)` | A single-mission (`autoscaling-viz`) UI workaround tied to one specific webview quirk and one worktree's renders — not a cross-cutting convention any other role/mission would fetch. Candidate for staying in that mission's own status file rather than the shared harvest, unless Dean wants a `conv:chat-links` addition (pairs naturally with FM2's image-link finding — same webview-quirk family). Flagging the option rather than deciding it. |
| FM50 | feedback_worktree_default_locality.md | `conv:worktree-scope` | Default to your own worktree; `-C`/`cd` to a sibling is a deliberate, stated exception, never a reflex. Same convention as C14-C19/FM25 — the general framing statement the more specific entries (FM25, FM36, FM40, FM42) all sit under. |

## From `project_*` memories

Most `project_*` memories are mission-state, not standing rules — the classification table's own
`dest` scheme only has room for `conv:`/`role:`/`model`, so a mission-state memory that carries no
generalizable rule is `SKIP (stale or mission-local)`: its content belongs in that mission's own
Type-1/Type-3 doc or CURRENT.md, not in the rules mechanism this migration is building. Only rows
below with a real standing-rule or taxonomy content get a `conv:`/`role:`/`model` dest; everything
else is explicitly `SKIP`, not silently dropped.

| # | Source | dest | Why |
|---|---|---|---|
| PM1 | project_analyzer_dynamic_registration.md | `SKIP (stale, mission-local)` | Superseded plan-status fact (CURRENT.md has the current status); no standing rule. |
| PM2 | project_autoscaling_viz_armb_findings.md | `SKIP (mission-local)` | Measured findings belong in that mission's own FINDINGS.md (already do) — not a rule. |
| PM3 | project_autoscaling_viz_multishape.md | `SKIP (mission-local)` | Open mission-state, not a rule. |
| PM4 | project_autoscaling_viz_real_trace.md | `SKIP (mission-local)` | Mission/branch-migration state, not a rule. |
| PM5 | project_autoscaling_viz_sim_from_benchmark.md | `SKIP (mission-local)` | Mission state (gate criteria, tolerances) — belongs in that mission's own plan doc. |
| PM6 | project_benchmark_harness_end_goal.md | `model` | This is genuinely a standing architectural decision about the benchmark harness's target shape (source-of-truth rule, invasiveness tiers) — the same class as C6/C11 (design/taxonomy prose describing how a subsystem is meant to work), not a per-step action. Candidate for a `benchmark`-scoped section of `doc-and-session-model.md`, or its own small `model`-class doc if that file shouldn't absorb mission-specific architecture — flagging the sub-placement, not just the top-level `dest`. |
| PM7 | project_benchmark_makefile_two_variant_todo.md | `SKIP (stale)` | Own header says SUPERSEDED; pure pointer. |
| PM8 | project_benchmark_observability_direction.md | `SKIP (mission-local)` | Benchmark-specific design decisions, not a cross-cutting rule — belongs in that mission's design doc (already does). |
| PM9 | project_claude_p_allowed_tools_pattern.md | `conv:worktree-scope` | This is a genuinely reusable procedural pattern (not mission-specific) — same family as FM42/C19, the concrete recipe for permission-scoped subagent work from `plans/`. Fold into the existing entry rather than treat as mission-local. |
| PM10 | project_coder_autonomy_direction.md | `SKIP (not-yet-designed direction)` | Explicitly a captured-for-later brainstorm, not an applied rule — nothing to harvest until it's designed. |
| PM11 | project_coder_enforcement_direction.md | `SKIP (not-yet-designed direction, partially superseded)` | Same as PM10; also partly superseded by this very migration (the `plans/rules/` direction it names is what `conventions/` now is). |
| PM12 | project_coder_write_confinement.md | `conv:worktree-scope` | **High-value, cross-cutting, currently missing from the harvest.** How write-confinement actually works mechanically (launch-time boundary, webview vs. terminal-launch difference, bypassPermissions hole, the coder-loads-no-conventions gap and its s-coder-skill fix) — this is exactly the kind of concrete mechanism fact `conv:worktree-scope` exists to hold, and it's more precise/currently-true than some of what's already in that file. Should be folded in as a distinct entry, not merged silently into an existing one (it corrects/refines them). |
| PM13 | project_context_cost_reduction.md | `SKIP (mission-local, done)` | Completed effort summary — the *rules it produced* are already captured elsewhere (the 5 CONVENTIONS additions are already in C1-C45; the .DONE-handoff `git rm` fix is in C26/`role:sync`). This memory itself is a project retrospective, not an independent source of new rule content. |
| PM14 | project_eval_framework_discussion.md | `SKIP (mission-local)` | Open design discussion for a specific framework, not a rule. |
| PM15 | project_handoff_protocol_redesign.md | `SKIP (stale, historical)` | Superseded by the current protocol (already fully captured in `conv:handoffs`/`conv:triggers`/`conv:status-files`). |
| PM16 | project_llm_scaler_workspace_bootstrap.md | `model` | This directly documents the repo-scope axis and the second-workspace bootstrap design — the same subject `harvest-classification.md`'s own "Repo-scope axis" section already discusses. Belongs as taxonomy/design prose in `doc-and-session-model.md`, not a per-step convention — but note the repo-scope axis itself is explicitly out of scope for this pass; only the *fact that this bootstrap effort exists and is gated* is being placed here, not the axis's classification work. |
| PM17 | project_plans_branch_purpose.md | `model` | Structural/taxonomy fact about what the `plans` branch is for (no DCO, promotion is deliberate) — same class as C3/C5 (workspace structure description), not a per-step rule. |
| PM18 | project_pokprod_shared_cluster_safety.md | `SKIP (mission-local)` | Pokprod-cluster-specific safety invariants — real and important, but scoped to one cluster/mission, not a cross-cutting convention every role fetches. Stays in that mission's own docs. |
| PM19 | project_pr1092_analysis.md | `SKIP (mission-local)` | PR-specific analysis, not a rule. |
| PM20 | project_pr1260_review_a2.md | `SKIP (stale, mission-local)` | PR-specific status, not a rule. |
| PM21 | project_pr1277_design_redesign.md | `SKIP (stale, mission-local)` | PR-specific design discussion, not a rule. |
| PM22 | project_role_specific_conventions.md | `SKIP (stale, outcome-superseded)` | The direction it describes has already happened (CODER-CONVENTIONS.md + s-coder skill exist) — this migration is itself the next iteration of exactly this direction. Historical only. |
| PM23 | project_session_naming_mechanism.md | `conv:session-start` **candidate, mechanism-level** | This is a genuine mechanism fact (how session titles persist, the rename-must-be-last-action timing constraint, the LiteLLM-gateway auto-naming failure) that a session needs to know to rename itself correctly — same trigger class as C12/FM39 (session-start-adjacent). Could also stay `SKIP` as an implementation detail rather than a rule a role "follows" — flagging as a genuine borderline case rather than picking silently. |
| PM24 | project_spec_poc_rev_coding.md | `SKIP (mission-local)` | Mission status (paused pending format redesign), not a rule. |
| PM25 | project_sync_role_origin.md | `role:sync` **as rationale, not a rule** | This explains *why* the sync role exists (historical cause) — useful context for `roles/sync.md` but not itself an actionable rule the way C26/FM44 are. Candidate for a short "why this role exists" note in `roles/sync.md` rather than a `### convention:` entry (nothing here is fetched-on-demand at a step; it's background). |
| PM26 | project_ta3_benchmark_pokprod.md | `SKIP (mission-local, stale-by-successor)` | Mission findings, own successor memory says so. |
| PM27 | project_ta3_benchmark_pokprod_current.md | `SKIP (mission-local)` | Mission state. |
| PM28 | project_ta_09_plans.md | `SKIP (stale, mission-local)` | Superseded mission status. |
| PM29 | project_ta_anchor_live_flag_gap.md | `SKIP (stale, mission-local)` | Superseded mission status. |
| PM30 | project_ta_anchor_pr1_reviewer_checklist.md | `SKIP (stale, mission-local)` | Superseded, historical only. |
| PM31 | project_ta_anchor_pr2_plan_ready.md | `SKIP (stale, mission-local)` | Superseded mission status. |
| PM32 | project_ta_anchor_v2_coding_progress.md | `SKIP (stale, mission-local)` | Superseded, historical only. |
| PM33 | project_ta_anchor_v2_voting_liveness_design_q.md | `SKIP (stale, mission-local)` | Resolved, historical only. |
| PM34 | project_workflow_architecture_directions.md | `SKIP (not-yet-designed direction)` | Explicitly discussion-stage, reopen-only-if-revisited. |
| PM35 | project_wsl_vscode_latency_triage.md | `SKIP (mission-local, environment-specific)` | A specific infrastructure diagnosis (this Dean+LiteLLM setup), not a rule any role follows — stays as environment troubleshooting history. |
| PM36 | project_wva_threshold_vs_ksat.md | `SKIP (mission-local, WVA-domain)` | WVA product-domain fact (analyzer constants), not a process/convention rule — belongs in a Type 1/4 doc about the analyzers, not the rules mechanism. |

---

## From `governance-follow-ups.md`

This doc is itself a **living backlog of incidents and undesigned candidate directions**, not
already-decided rules like the two convention files were — several of its items are explicitly
"not yet designed" per its own text. Only items with an already-resolved, already-stated rule are
harvestable now; undesigned candidate directions (its own § Candidate directions list) are `SKIP`,
matching the same test PM10/PM11/PM34 above already used.

| # | Source | dest | Why |
|---|---|---|---|
| GF1 | § Repeat scope-boundary incidents — 2026-07-14 reviewer-worktree | `conv:worktree-scope` | Already fully captured by FM36 (feedback_reviewer_writes_in_coder_tree.md is literally this incident's own resulting memory) — no separate harvest needed, cross-reference only. |
| GF2 | § 2026-07-26 PR C unauthorized subagent | `role:coder` | Already fully captured by FM6 — same incident, same memory, no separate harvest needed. |
| GF3 | § 2026-07-27 formula-semantics fork | `conv:doc-ownership-boundary` **NEW entry within existing file** | Not yet in any memory as a standalone rule — the general principle ("elevate design forks early") is in `feedback_doc_accuracy_discipline.md`/FM12, but the *specific* corollary ("a bug fix silently changing a plan-specified formula's output for an uncovered input class must be flagged as its own decision point") is only stated here, in the incident record, and candidate direction (6) below says it's still not folded in. Genuinely new content to add to `doc-ownership-boundary`, not a duplicate. |
| GF4 | § 2026-07-29 §4a leaks — the mechanical grep gate | `conv:semantic-pivot-grep` **or NEW `conv:doc-hygiene-grep`?** | The concrete grep pattern (`decision #|review finding|\bF[0-9]\b|plan §|...`) for catching plans-branch identifiers leaking into code comments — related to but distinct from semantic-pivot-grep (that's about behavioral-contract renames; this is about doc-reference leakage). Candidate direction (7) below says this still isn't added to either checklist. Best placement: a new entry within `conv:plans-refs-in-code` (CC11's existing file — this is the mechanical detection half of exactly that rule) rather than a new file. |
| GF5 | § Pre-existing main-side §4a leaks / broken doc links | `SKIP (mission-local backlog, not a rule)` | Concrete cleanup TODOs (specific file:line locations), not a rule — stays as backlog. |
| GF6 | § CODER-CONVENTIONS self-contradiction (a) — §0 cd/cp footgun | `conv:worktree-scope` | Already fixed in the source doc per this section's own text ("Fixed — §0 now points to cp/mv..."); the *lesson* (a doc's own early shorthand can contradict its later correct instruction) is worth a one-line note in worktree-scope's own entry, not a new rule — the fix itself already exists in what Step 2a harvested. |
| GF7 | § CODER-CONVENTIONS self-contradiction (b) — §5.2 split-before-naming | `conv:handoffs` | Same reasoning as GF6 — already fixed in source, already implicitly part of what C25/CC13/FM43 cover ("split before naming" is the mechanism, already stated). Confirm the harvested `handoffs.md` entry states this explicitly; add a line if not. |
| GF8 | § Handoff-routing misroute (2026-08-13) — role+task addressing direction | `SKIP (not-yet-designed direction)` | Dean's own "stated fix direction... not yet designed" — the identity-block partial fix is already captured (status-files.md should have it via C23), but the full role+task addressing redesign is explicitly future work, not a rule to harvest yet. |
| GF9 | § Reviewer-highlight default (2026-07-29) | `SKIP (not-yet-designed — no REVIEWER-CONVENTIONS.md exists)` | A requirement for a document that doesn't exist yet (`REVIEWER-CONVENTIONS.md`, candidate direction 2) — nothing to harvest into until that doc is created; this is itself backlog content for that future doc, not a rule with a home today. |
| GF10 | § Plan-authoring process note — widen semantic-pivot-grep to `grep -rl` across all `_test.go` | `conv:semantic-pivot-grep` **addition** | A concrete, already-decided widening of the existing grep scope for behavioral-contract-change plans — real content to add to the existing entry, not a duplicate (the existing entry doesn't yet say "search broadly, not just declared files"). |
| GF11 | § Candidate directions 1-8 | `SKIP (not-yet-designed, all 8)` | Explicitly "not yet designed" per the doc's own section header — no standing rule exists yet for any of these 8 items (mechanical hooks, REVIEWER-CONVENTIONS.md, CONVENTIONS.md ownership, subagent-rule wording, historical-revision pattern naming, formula-fork mirroring, §4a grep gate wiring, reviewer-highlight wiring). Direction 5 ("safe pattern for running code at a historical revision") is worth flagging separately — FM36/feedback_reviewer_writes_in_coder_tree.md already names the answer ("isolated temp worktree/clone") informally; that answer could be pulled into `worktree-scope` now even though the "name it as a pattern" framing stays undesigned. |
| GF12 | § Retrospective open question (F merged) | `SKIP (undecided question, not a rule)` | A still-open judgment question, not a resolved rule. |

---

## Summary

- **feedback_\* : 50 rows.** ~38 map into existing `conventions/` topics as additions (mostly
  worktree-scope, handoffs, pre-push, git-remotes, github-actions — the same handful of files absorb
  most of the volume, consistent with Step 2a's own pattern). 4 genuinely new topic files
  (`conv:chat-links`, `conv:tool-authoring`, and 2 flagged candidates: `conv:writing-style`,
  `conv:tooling-preferences`). 6 `SKIP` (2 duplicate the global CLAUDE.md, 4 are stale/mission-narrow).
- **project_\* : 36 rows.** Overwhelmingly `SKIP (mission-local)` — 27 rows — since most `project_*`
  memories are mission state, not standing rules, and mission state's permanent home is that
  mission's own Type-1/Type-3 doc or CURRENT.md, not the rules mechanism. 4 rows → `model`
  (benchmark-harness-end-goal, llm-scaler-workspace-bootstrap, plans-branch-purpose — taxonomy/
  architecture prose). 3 rows → existing conventions as genuine additions (`claude-p-allowed-tools`
  and, most valuably, **`project_coder_write_confinement.md`'s mechanism content**, which is more
  precise than some of what Step 2a already harvested into `worktree-scope.md` and should be folded
  in). 2 borderline/flagged (`session-naming-mechanism`, `sync-role-origin` — context/rationale, not
  action rules).
- **governance-follow-ups.md : 12 items.** Only 4 have genuinely new, already-resolved content to
  add (GF3 formula-fork corollary, GF4 §4a grep gate, GF10 widened grep scope, GF6/GF7 as
  already-fixed lessons worth a one-line note). The other 8 are `SKIP` — either already captured by
  an existing feedback memory (GF1/GF2), or explicitly not-yet-designed backlog (GF8/GF9/GF11/GF12).

**Net new work for the coder dispatch:** roughly 4 new topic files, ~15-20 additions to existing
topic files (mostly enrichment, not brand-new entries), and 3 `model`-doc additions. Substantially
smaller than Step 2a's 45-entry build, consistent with most of the volume here being restatement/
reinforcement of what the two convention files already said, which is exactly what "the totals list
will not change... it grows as more incidents happen" (Addendum 15) predicts — most memories exist
*because* an incident reinforced a rule CONVENTIONS.md already had, not because it's a genuinely new
rule.

**Flagged for Dean, not decided here (same discipline as harvest-classification.md's own flags):**
- FM1/FM33/FM46/FM49: whether `conv:writing-style`, `conv:tooling-preferences`, and a `chat-links`
  fold-in for FM49 are worth creating as topics, vs. leaving those few memories un-harvested.
- PM6/PM16/PM17: whether mission-specific architecture facts (benchmark harness, the second-workspace
  bootstrap, the plans-branch-purpose fact) belong in the shared `doc-and-session-model.md` at all, or
  should stay in their own mission docs — `model` was picked by analogy to C3/C5/C6/C11, not verified
  against Dean's actual intent for what that file should hold.
- PM23/PM25: session-naming-mechanism and sync-role-origin as borderline rule-vs-context cases.
- FM40 resolves the open question the Step 2a coder's status file recorded (the unclassified
  pathspec-commit paragraph) — confirmed here as `conv:worktree-scope`, sourced from
  `feedback_shared_git_index_pathspec_commits.md`.
