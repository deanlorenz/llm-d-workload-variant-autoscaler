from: designer (owner of Type-1 combined-analyzer-optimizer-design.md + Addendum 1)
to: sync
session: type1-addendum-1-approved-rev6

## What changed

**A Type-1 addendum now exists alongside the frozen design, and Dean approved it 2026-08-08.**

- `planning/combined-analyzer-optimizer-design-addendum-1.md` — **Rev 6**, committed **`423eb2a8`** on
  `plans`, **APPROVED by Dean**. It amends the frozen parent (`combined-analyzer-optimizer-design.md`,
  FINAL @ `8c2a9b04`) **without editing it** — the parent stays frozen; all amendments live in the addendum.
  Rulings are labelled `AD1`–`AD8` with a § disposition table, § residual band, § verification checklist
  (written for planner **and** reviewer), and a § withdrawn-framings log.
- Handed off in **`a675602b`** / **`29e3dae1`**: a full planner handoff
  (`plan__ta-anchor-ad8-addendum-1-approved-rev6-final.md`) plus refs-only doorbells to the PR-2 coder and
  the reviewer.
- Cold-resume record: **`session/status/designer-type1-addendum.md`** (new).
- ⚠️ **Note on `a675602b`:** an over-broad `git add -A session/handoffs/` in that commit swept in ~33 other
  sessions' pending handoff files. They are committed **verbatim as found** — nothing edited, renamed, or
  removed, and the `.md`/`.WIP`/`.DONE` machine is unaffected. No sync consequence (sync reads handoffs from
  the filesystem, not git); flagged only so the commit isn't misread as consuming them.

## Update CURRENT.md

### Add to the anchor-refactor mission entry (the PR-2 paragraph)

A **Type-1 addendum** now governs the `AD8` prefill defect: `combined-analyzer-optimizer-design-addendum-1.md`
(**Rev 6, `423eb2a8`, approved by Dean 2026-08-08**). The parent Type 1 remains **FINAL, frozen @ `8c2a9b04`,
and is not edited** — this is the amendment channel.

**Dean's rulings, final:** a **guard** (on a disaggregated model with TA and **no** saturation, do nothing —
it *enforces* `AD2` rather than documenting it); option **(a)** liveness-aware refusal **REJECTED** (*"PD not
SAT — DONT"* — the rule stays keyed on the *enabled* set); option **(b)** the **per-role pricing repair
APPROVED** (three sites: per-role sizing, `CapGPUs`/`Demand` in `rescaleInputsForGroup:540-546`, and
`cost_aware_optimizer.go:350-367` observability); option **(c)** interim documentation **additive, not
alternative**. **`MinReplicas` is not a fourth option** — unset by default, fails correlated with the defect,
cannot reach regime (i) at all, and any variant with `minReplicas > 0` makes `applyScaleToZeroEnforcement`
skip the enforcer **model-wide** (`saturation/engine.go:1362`).

**`AD8` is two regimes from one cause, and must reach the Type 3 / backlog as TWO items, not one** (a fix
verified on one says nothing about the other): **(i) freeze** — decode `RC > 0` ⇒ scale-up arm ⇒ prefill
**freezes at its current count, including 0**, with **no floor of any kind**; **(ii) drain** — decode
`RC == 0` ⇒ scale-down arm ⇒ prefill **drains to 1**. **Sequencing precondition, regime (ii) only:** if
#1237's positional rule is ever tidied, **floor every variant in the role first** (tidy-first re-opens it at
every height on both scale-down paths — measured, prefill → 0).

**Rev 6 lowered severity, and that opened one question.** Rev 6 withdrew this author's own Rev 5 claim that
the `[sat, TA]`-with-saturation-non-live cell is reachable: saturation's capacity store is refilled from the
scale-target objects **every cycle** and kept **7 days**, while TA's persisted `lastPerReplicaSupply` needs an
**observed live replica metric** and expires in **1 hour** — same process, so **TA warm ⟹ saturation warm**.
A cold start leaves both cold; a gap long enough to push saturation past the 90 s liveness window has already
emptied TA. **Unaffected:** `[TA]`-only (needs no saturation death at all — the guard's case, and the
reachable configuration), the two regimes measured at HEAD, the arithmetic, and Dean's decision to repair the
pricing. **Affected:** severity, which he had set on the withdrawn premise.

**⚠️ Open — Dean's call, and the only open ask from this thread: PLACEMENT of the pricing repair.** With
severity lowered, whether the repair belongs **in PR-2** is a live question. The planner has been asked to
bring it to him and told **not** to schedule it on the old severity and **not** to retire it either. Record
it as *open*, not settled either way.

**Not open, for the record:** the `ceil`/`floor` question (Dean: *"we discuss later"*), and document
housekeeping (deferred until PR-2 is done — **his decision is recorded and is not to be re-raised**).

### Correct a stale fact in the PR-2 rows

CURRENT.md and the PR Status row both record PR-2's tip as **`d9f3b97e`**. The branch is actually at
**`a9afb740`**. (Read-only observation from this session; the coder owns the branch.)

### Add to § Issues to Open

- **Align the informativeness predicate with the RC that reaches the optimizer (Type-1 design question,
  later round — not PR-2).** `ResultIsInformative` scans only per-variant `Reason`, while the
  `RequiredCapacity` the optimizer consumes comes from `RoleCapacities` via `applyUniversalThreshold`
  (`saturation/engine_v2.go:476-513`), which never mentions `VariantCapacities` — so a saturation result can
  be non-informative while carrying a positive role RC. **Latent, not live** (Rev 6: the capacity store keeps
  saturation informative in every reachable configuration), which is why it is a design question rather than
  a bug to schedule. Closing it means either having informativeness consider role demand, or having the
  scheduler-queue term mark the variants it speaks for. **This is not a revival of rejected option (a)** —
  different site (the liveness computation, not a second refusal predicate in the optimizer). File at Dean's
  direction.

## Open questions / follow-ups

- The **placement** question above is the one thing awaiting Dean.
- Deferred by Dean until the coder lands, tracked in `session/status/designer-type1-addendum.md`: the `ceil`
  amendment, `multi-analyzer-dataflow-map.md` §9 Case 5's backstop sentence, the one-tier `G2` row, the
  dropped `[TA]`-only caveat, a liveness verdict alongside the consistency verdict, Type 1 `:1524-1526`'s
  `(D-a)` justification, the `N2`/`N7` Disposition sweep, and `T1-1`'s `:1159-1160` divergence.
- Premises now **withdrawn** — if any CURRENT.md text inherited them, drop them: the drain as *"newly
  unmasked by `VG-up`"* (item 6 — base was already `Live`-gated and already read prefill `TotalDemand = 0`
  at `075a208e:rescale.go:545`; reviewer conceded in Finding 67); the cell as reachable by cold start
  (item 7); the cell as reachable by cold start **or** sustained metrics gap (item 8); and review finding
  **V6**'s (b)-fallback domain claim (inverted, superseded by `N1`).
- This session stays live, monitoring inbound handoffs for in-domain PR-2 events until PR-2 is done.
