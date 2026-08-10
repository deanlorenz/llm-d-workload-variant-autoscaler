# Code spec — role kernels and r-* skills

**code spec** · **Status: DRAFT** — awaiting Dean's finalization.

Migration step M1.1 of [`atomic-step-protocol-design.md`](atomic-step-protocol-design.md). Names and roles
come from [`doc-and-session-model.md`](doc-and-session-model.md) § Roles.

---

## Reading Protocol

Read this protocol, `## Intent`, and `## Step index`. Then start at your assigned step and read only that
step's section. No line numbers; do not run `toc-refresh.sh` on it.

---

## Intent

**intent** — Make the taxonomy operational rather than documented: one skill per role, each loading a small
role kernel, reachable from every worktree. Early on purpose — the old convention files stay untouched, so
new sessions can adopt the new mechanism while old ones keep working.

**current call stack** — `plans/CLAUDE.md` imports `session/CONVENTIONS.md` and `session/CURRENT.md`, so
every session pays for both regardless of role. A code worktree has a 33-byte upstream `CLAUDE.md`, so a
coder launched there loads **neither**. Ten `s-*` skills exist: five map cleanly to roles, `s-plan` covers
two roles, `s-design-review` is ambiguous between confirm and verify, and **seven roles have no skill**.

**planned call stack** —

```
Dean types /r-<role> [args]
  → skill loads roles/<role>.md            (small; only what cannot be per-step)
  → skill states worktree, branch, spec, assigned range
  → Dean confirms
  → session proceeds in that role, one role per session
```

**new components** — `roles/*.md` (ten kernels), `.claude/skills/r-*/SKILL.md`, container symlinks, two
stateless hooks (DCO check, push block).

**new conventions** — none created here. Kernel content at this stage is only what is already settled in
the two designs; the harvest (M1.2) is what fills them out. Building thin kernels first is deliberate: a
kernel that waits for the harvest blocks every session from adopting roles at all.

**Dependency note.** `s-coder` already exists and was created by another session. Renaming it to `r-coder`
touches that work, so S3 must check its current content before replacing it rather than assuming.

---

## Prerequisites

New worktree — this is not the tooling codebase:

```
git -C repo worktree add ../plans-roles --orphan plans-roles
```

**Gates** — no Go, no `make test`. Kernels and skills are markdown, so the gates are structural: each
kernel under a line budget, each skill's frontmatter parseable, every referenced path resolving, and — the
one that actually matters — **each skill visibly present in a fresh session's skill listing**. Five of nine
`s-*` skills were once missing from that listing, and a skill that is absent fails silently. **Never push.**

---

## Step index

**S1 — `roles/coder.md`.** The kernel that matters most and the only large one. Its job is
expectation-setting: the coder must expect a convention per step and halt when one is absent. Everything
else that can be per-step is deliberately not here.

**S2 — The other nine kernels.** Thin, from the roles table: what each owns, what it reads, its handoff
token, and its one non-obvious rule. Thin is correct at this stage, not lazy.

**S3 — `r-coder` skill.** Interactive resolution and the confirm-back handshake, which is what turns Dean's
manual ritual into something that cannot be skipped. Must reconcile with the existing `s-coder`.

**S4 — The other nine skills.** Uniform, thin loaders.

**S5 — Container symlinks and listing verification.** Discovery via the directory walk-up. The verification
is the step, not the symlinks.

**S6 — Two stateless hooks.** DCO check and push block — mechanical, catastrophic if missed, not per-step.

**S7 — Documentation.** How to declare a role, what each token is, how the two regimes coexist.

---

<!-- ─────────────── execution detail below ─────────────── -->

## S1 — `roles/coder.md`

**brief** — The coder kernel. Only what cannot live in a step: expectation-setting, standing prohibitions,
the halt protocol, how to record state, and the range-stop rule. Sources are the two frozen designs and the
frozen `session/CODER-CONVENTIONS.md` — read all three; do not compose from memory.

**scope** — `roles/coder.md`

**do**
1. Open with the expectation: **every step carries its own conventions; a step that does not is a halt, not
   a judgment call.**
2. Standing prohibitions: never leave your worktree; never push; never run a GitHub-mutating command;
   never edit session state.
3. The halt protocol, in Dean's words: never presume, never assume, never guess, never make a judgment
   call; follows orders; limited scope; **owns implementation, not intent**; not sure — stop, ask. Route the
   question to the spec owner, never to the coder's own chat.
4. Recording: status file plus append-only step log; never write `state: done`.
5. The range-stop rule: finishing the assigned range means stop, not continue into unassigned steps.
6. Target **under 60 lines**. If it will not fit, that is a finding — say which content resists being
   per-step rather than trimming the meaning.

**conventions** — none (`conventions/` does not exist yet). Inline: quote Dean's wording where the design
quotes it; paraphrase weakens a rule that is deliberately absolute.

**verify** — `wc -l roles/coder.md` under 60; every claim traceable to one of the three sources; no
plans-branch identifiers (`F3`, `AD8`, `C6c`, …).

**done_when** — under budget, every rule sourced, and the five topics above all present.

**on_fail** — halt. Do **not** drop a rule to meet the line budget; report the conflict instead.

**record** — anything from `CODER-CONVENTIONS.md` that would not fit and why, since it becomes harvest
input.

[↑ Step index](#step-index)

## S2 — The other nine kernels

**brief** — `designer`, `epic`, `spec`, `confirm`, `verify`, `pr`, `triage`, `policy-writer`, `sync`. Each
gets what it owns, what it reads, its handoff token, and its one non-obvious rule. Thin is right: content
arrives with the harvest.

**scope** — `roles/*.md`

**do**
1. One file per role, from `doc-and-session-model.md` § Roles. Target **under 30 lines** each.
2. Carry the non-obvious rule where one exists, because these are the ones that get violated:
   - `spec` — also owns landing: push-readiness, the push, the PR, CI watch, immediate corrections
   - `verify` — reads **code first, then the spec**; an anti-anchoring rule, not sequencing
   - `policy-writer` — captures conventions as a standing behaviour, from what Dean said or an incident;
     Dean never edits those files
   - `sync` — the only writer of session state
   - `triage` — opens on first external review, not at PR creation
3. Every kernel states: one session, one role.
4. Do not invent a rule that is not in the model doc. A thin kernel is correct; an invented one is not.

**conventions** — none. Inline: cite the model doc rather than restating it at length.

**verify** — nine files exist, each under 30 lines; every non-obvious rule above appears in its kernel;
`grep` finds no rule absent from the model doc.

**done_when** — all nine present and under budget, with the five named rules in place.

**on_fail** — halt.

**record** — any role whose kernel felt empty; that is a signal the role may not be real yet.

[↑ Step index](#step-index)

## S3 — `r-coder` skill

**brief** — The skill is the role declaration *and* the arming step. Two invocation paths: bare and
interactive for Dean, argumented and deterministic for a machine-launched coder.

**scope** — `.claude/skills/r-coder/SKILL.md`

**do**
1. **First read the existing `../plans/.claude/skills/s-coder/SKILL.md`** and record what it does. It was
   written by another session; anything it handles that this does not is a regression.
2. Frontmatter description naming the trigger explicitly, so a prose role declaration matches it.
3. Bare invocation → interactive resolution: list worktrees, list `planning/*-spec.md`, read the spec's
   `## Step index` and offer **titled** steps. Default offered is *continue from the ledger* — the step log
   already records what is done, so Dean needs no step numbers in the common case.
4. Argumented invocation `\/r-coder <branch> <range>` → deterministic, no prompting.
5. **Mandated first action:** state worktree, branch, spec path, assigned range; then stop for
   confirmation. Not optional, and not satisfiable by a summary — it must be a stop.
6. Instruct loading `roles/coder.md`, and re-loading it after `EnterWorktree`, which re-roots the
   `CLAUDE.md` chain.
7. Schedule the checkpoint tick (`CONVENTIONS.md` § Checkpoint tick).

**conventions** — none. Inline: do not delete `s-coder` in this step; a rename plus a removal in one step
cannot be reverted cleanly. Removal is S7's business once `r-coder` is proven present in a listing.

**verify** — frontmatter parses; every referenced path resolves; the interactive branch is described
concretely enough to follow without inventing anything.

**done_when** — both paths specified, the handshake mandated, and `s-coder`'s behaviour accounted for.

**on_fail** — halt.

**record** — anything `s-coder` did that `r-coder` drops, explicitly.

[↑ Step index](#step-index)

## S4 — The other nine skills

**brief** — Uniform thin loaders: load the kernel, state the role, do the handshake where a target is
involved.

**scope** — `.claude/skills/r-*/SKILL.md`

**do**
1. One skill per remaining role, same shape as `r-coder` minus the step-range picker.
2. Each description begins `Set this session's role:` so roles are distinguishable from `s-*` utilities in
   a listing.
3. `r-spec` also states that it owns landing — push, PR, CI — since that is the role's least obvious duty.
4. `r-policy` carries the standing capture behaviour and the never-freehand rule.
5. `r-sync` states it is the only writer of session state.

**conventions** — none. Inline: uniformity matters more than per-skill cleverness; these are loaders.

**verify** — ten skills total including `r-coder`; every frontmatter parses; every kernel path resolves.

**done_when** — all ten exist, uniform, with the three special duties stated.

**on_fail** — halt.

**record** — the final skill list with each one's kernel path.

[↑ Step index](#step-index)

## S5 — Container symlinks and listing verification

**brief** — Skills are discovered by the directory walk-up from a worktree, which is why the container holds
symlinks. The verification is the real step: an absent skill fails **silently**, and five of nine were once
missing from a session listing.

**scope** — `install-skills.sh` in the worktree; the symlinks themselves are created by whoever installs

**do**
1. Write `install-skills.sh` that creates a symlink per `r-*` skill in the container `.claude/skills/`,
   mirroring the nine that already exist. Idempotent; refuses to clobber a non-symlink.
2. Do **not** run it against the live container — installation is deliberate, and this worktree's content is
   copied over at kickoff rather than installed from here.
3. Write `VERIFY.md`: the exact manual check — start a fresh session in a code worktree, confirm every
   `r-*` skill appears in the listing, and record which do not.
4. State plainly that this check cannot be automated from inside a session and must be done by hand.

**conventions** — none. Inline: idempotent and non-clobbering; a script that silently replaces a real file
is a data-loss bug.

**verify** — run the script against a throwaway directory tree; second run is a no-op; a pre-existing
regular file at a target path causes a refusal.

**done_when** — the script is idempotent and refuses to clobber, and `VERIFY.md` names the manual check.

**on_fail** — halt.

**record** — that the listing check is outstanding and manual; it is a prerequisite for trusting any `r-*`
skill.

[↑ Step index](#step-index)

## S6 — Two stateless hooks

**brief** — DCO check and push block. Mechanical, catastrophic if missed, not per-step — the only two hooks
that clearly earn their complexity. The scope hook is deliberately excluded: it needs the current step's
scope from disk, and the portable `step-check` covers the same ground.

**scope** — `hooks/`, `README.md`

**do**
1. A commit-stage hook rejecting a missing `Signed-off-by` on code lineage and a **present** one on plans
   lineage. Reuse `step-check --lineage` rather than reimplementing — one rule, one place.
2. A hook rejecting `git push` from a coder session, with the reason.
3. Ship as files plus install instructions. Do not install into a live `.git/hooks`.
4. State in the README that these are Claude-Code-local hardening; the portable layer is `step-check`, and
   nothing may depend on the hooks existing.

**conventions** — none. Inline: no rule implemented twice. A second copy drifts and the drift is silent.

**verify** — each hook exercised in a throwaway repo, both directions per lineage.

**done_when** — both hooks work in both directions and neither duplicates `step-check`'s logic.

**on_fail** — halt. If the push hook cannot distinguish a coder session from any other, say so — that is a
real limitation, not something to approximate.

**record** — how a coder session is identified, or that it cannot be.

[↑ Step index](#step-index)

## S7 — Documentation

**brief** — How to declare a role, what the tokens are, how the two regimes coexist while old files stay
frozen.

**scope** — `README.md`

**do**
1. The role table: role, token, kernel path, skill name.
2. How to declare a role, both paths, and that the handshake is mandatory.
3. Coexistence: old sessions load `CONVENTIONS.md` via `plans/CLAUDE.md`; new sessions load a kernel via
   `r-*`. The old files are frozen, not rewritten.
4. State that `s-coder` removal waits until `r-coder` is confirmed present in a live listing (S5).

**conventions** — none. Inline: no plans-branch identifiers.

**verify** — every path in the table resolves; the token list matches the model doc exactly.

**done_when** — the table is complete and matches the model doc, with the coexistence rule stated.

**on_fail** — halt.

**record** — any divergence found between this table and the model doc; the model doc wins and the
divergence is a finding.

[↑ Step index](#step-index)
