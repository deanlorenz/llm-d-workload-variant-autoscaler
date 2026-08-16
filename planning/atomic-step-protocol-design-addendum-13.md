# Addendum 13 — designing all 11 roles: inventory, gaps, and a build order

**Status: research complete 2026-08-17; design proposal below; awaiting Dean's review before any
role kernel is written.**

## At a glance

**Mission:** Dean asked to design all 11 roles from `doc-and-session-model.md` — check what already
exists (conventions, memories, skills), his own instruction patterns, and external best practices —
before writing anything.

**Approach:** three parallel research passes (full doc/skill/memory inventory per role; Claude Code's
actual documented best practices; this session's own observed instruction patterns), synthesized here
into a per-role status table, a prioritized build order, and 5 real cross-cutting defects found along
the way that need a decision before or during the build.

**Needs you:**
- Confirm the build order (§ Build order) before any kernel is written.
- Decide the 5 findings in § Findings needing a decision — none are fixed yet.
- Confirm 4 role kernels are actually thin enough to build directly from this doc alone (designer,
  confirm, verify, pr) vs. needing a fuller design pass first.

**Checklist:**
- [ ] Dean reviews this addendum.
- [ ] Decide the 5 findings (§ Findings needing a decision).
- [ ] Confirm or revise the build order (§ Build order).
- [ ] Hand the approved order to `role-skills-spec.md`'s own S1-S7 execution, or a coder, per usual.

---

## Per-role status

| Role | Kernel content exists? | Skill exists? | Coverage |
|---|---|---|---|
| Dean | n/a (human, no kernel expected) | n/a | complete by design |
| designer | none harvested | none | **thinnest — no source material at all** |
| epic | none harvested | `s-plan` (conflated with spec) | thin, and skill doesn't distinguish it from spec |
| spec | none harvested; mechanics live in `conv:pre-push`/`conv:github-actions` (fetched, not standing) | `s-plan` (conflated with epic) | operationally heaviest role, least standing-posture coverage |
| coder | **richest** — CC6/CC15/CC17/CC18/CC19 in `harvest-classification.md`, full §7/§8 may/may-not lists in `CODER-CONVENTIONS.md` | `s-coder` — fullest of all ten skills | high, not total (§ Findings #2) |
| confirm | none harvested | `s-design-review` — **ambiguous**, shared with verify | thin, and skill doesn't cleanly separate from verify |
| verify | none harvested | `s-design-review` — same ambiguous skill, **wrong step order** (§ Findings #1) | thin, and skill actively violates the role's own defining rule |
| pr | none harvested | **none** | **zero coverage** |
| triage | none harvested (role is newly-named, no pre-existing prose to harvest) | `s-pr-triage` — clean 1:1, but wrong output type (§ Findings #4) | mechanically solid, output doesn't match role's own "Owns" |
| policy-writer | none harvested; no upstream source material at all (its own subject matter — the harvest — hasn't run yet) | **none** | **zero coverage, and no input either** |
| sync | second-richest — C26 in `harvest-classification.md`, full apparatus in `CONVENTIONS.md` § Type 5 | `s-sync-current` — actively maintained, closest to production-ready | high, but token usage is 0/302 (§ Findings #3) |

## Findings needing a decision — none fixed yet

1. **`s-design-review`'s step order is backwards for `verify`.** The role's own defining rule is
   "reads code first, then the spec — anti-anchoring, not sequencing" (`doc-and-session-model.md` §
   Roles). The skill's actual steps read design/plan (Step 3) *before* code (Step 4) — the literal
   inverse. If this skill is treated as verify's current implementation, it violates verify's own
   core rule today, live, not just in an unbuilt design.
2. **Coder's C44 classification (never push to `upstream`) is still an open design question, not a
   settled kernel line.** Cross-cutting `role:coder`+`role:planner`, flagged in
   `atomic-step-protocol-design-addendum-4.md` as the concrete example of the still-unresolved
   "posture vs. checklist" question. Do not treat coder's kernel as fully spec'd until this closes.
3. **`sync`'s handoff token has never been used — 0 of 302 handoff files**, despite `s-sync-current`
   being the most production-ready skill of all ten. `plan__` absorbs work that should be `sync__`.
   Worth understanding why before building more sync content — likely naming confusion with `plan`
   (per `doc-and-session-model.md` § Audit evidence), but not confirmed.
4. **`s-pr-triage` produces the wrong output type for `triage`.** The role's "Owns" column says "a
   fixup code spec, or additions to an existing one" — the skill produces a review/summary doc
   (`PR<N>-review.md`) and stops there. Converting that into a code spec is currently a manual step
   with no rule or skill covering it.
5. **Two live discrepancies between frozen docs, neither previously caught:**
   - `CONVENTIONS.md` calls the epic plan "transient — no longer needed after the mission completes";
     `doc-and-session-model.md` calls it "durable, not transient." Direct contradiction.
   - `atomic-step-protocol-design.md`'s "four reviews" table says External review reads "the code
     spec"; `doc-and-session-model.md`'s role table says `pr` reads "the PR." Possibly the same role
     described inconsistently across two frozen docs, possibly two genuinely different things wearing
     similar names — not yet determined which.

## Build order — proposed, not yet approved

Ordered by (a) how much is already usable and (b) how much a build actually closes a real gap found
above, not by role-table order:

1. **`sync`** — richest existing material, closest to a working skill already; building `roles/sync.md`
   + renaming `s-sync-current`→`r-sync` is mostly transcription, and directly gives an opportunity to
   fix Finding #3 (token adoption) while doing it.
2. **`coder`** — second-richest; building `roles/coder.md` is likewise mostly transcription from
   already-harvested content, blocked only on Finding #2 (C44) being resolved first.
3. **`triage`** — clean skill mapping exists; building the kernel is cheap, and Finding #4 (wrong
   output type) is a concrete, scoped fix to make while touching this role anyway.
4. **`confirm` + `verify`** — build together, since separating them *is* the design work: Finding #1
   (step-order defect) must be fixed as part of this, not deferred. Building them separately first and
   fixing the shared skill later would mean writing two kernels against a skill neither actually uses
   correctly yet.
5. **`epic` + `spec`** — same shared-skill situation as confirm/verify (`s-plan` conflates them), lower
   urgency since nothing found here is actively broken the way Finding #1 is. Resolve Finding #5's
   epic-plan transient/durable discrepancy as part of this.
6. **`designer`** — thinnest, but genuinely low-risk to build once the pattern from 1-5 is established;
   no real source material exists beyond `doc-and-session-model.md` itself.
7. **`pr`** — zero coverage, but well-specified in the model doc (explicitly disambiguated from the
   upstream `pr-review` skill); build once the pattern is proven on richer roles.
8. **`policy-writer`** — deliberately last: it is both zero-coverage AND has no input yet (its own
   subject matter, the `feedback_*`/`project_*` harvest, hasn't run). Building this role's kernel
   before the harvest runs risks designing against a guess rather than the real candidate-file/
   consolidation shape from Addendum 12. Do the harvest-adjacent design work (Addendum 12's own
   checklist) before or alongside this role, not after.

## Sources

Full per-role citation detail (file:line/section for every existing rule, memory, and skill mapped to
each of the 11 roles) is in the research transcript, not reproduced here — this addendum is the
synthesis. Ask if a specific role's sourcing needs re-verification before building its kernel.

External research (Claude Code's own documented best practices) found: tool allowlists, conditional
hooks, and task partitioning are real, documented mechanisms this project already uses correctly; no
official Anthropic guidance exists for role-naming conventions, handoff protocol schemas, scope-breadth
heuristics, or always-loaded-vs-lazy-loaded rule kernels — this project's existing design (fetch-by-name
conventions, the `sync__`/`plan__`/trigger handoff split) is a local invention beyond what's officially
documented, not a deviation from it.
