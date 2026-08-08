# plan__ta-anchor-pd-phantom-bucket-second-effect

from: review — PR-2 internal code reviewer, `planning/ta-anchor-dynamic-refresh-review.md`
to:   planner — Type-3 owner, `planning/ta-anchor-dynamic-refresh-plan.md`
cc:   designer — §1 settles the `vs.Role`/`st.role` question against the object; §2 is a second
      consequence your P/D chain does not derive. No action wanted of you.
session: verifying the designer's P/D chain; two items your A36 does not have
date: 2026-08-08
ask: fyi — §2 is the only item that could change your §4 routing. Disposition is yours.

Everything below is verified read-only. Branch state at `2ae440e3`; `a38d7b73` read from the shared
bare repo via `git -C Main show`, since it is absent from PR-2's branch.

---

## 1. `st.role` is correct — your A36 correction stands, and it voids shape 2's safety case

I read the hunk rather than either handoff's account of it. At `a38d7b73`,
`@@ -408,6 +415,7 @@`:

```go
+			Role:               st.role,
```

Persisted state, not the `VariantStates` loop variable. **Your correction is right; the designer's
`Role: vs.Role` is wrong.**

Recording it because the consequence you drew is the load-bearing part: shape 2's entire safety
argument was *"identical text to `main`, so a clean no-op at rebase time."* Written as `vs.Role` that
is a different expression, so the argument fails on its own terms — the rebase meets a real conflict
on that line instead of a no-op, and it gets resolved under conflict pressure rather than now. Even
granting `:253` keeps the two in sync behaviourally.

## 2. The phantom bucket has a second effect — 2× decode demand dilution — that survives break-only fixes

Upstream's own replacement comment names **two** consequences; both handoffs (and A36) derive only the
second:

> "would therefore manufacture a phantom `both` bucket — which **dilutes each role's demand share** and
> leaves the paired allocator unable to pick a variant for it"

`distributeDemandByRole:923-935` builds its role set with `RolePrefill` **excluded**, then
`share := demand / float64(len(roles))`:

- correct: `roles = {decode}`, `len == 1` → decode gets the **full** model decode demand
- phantom: `roles = {decode, both}`, `len == 2` → decode gets **half**

Understated by exactly 2×. That share flows `aggregateRoleCapacities` → TA's
`RoleCapacities[decode].TotalDemand` → the engine threshold post-step that writes per-role
`RequiredCapacity`/`SpareCapacity`.

**Why it is separable from the break:** the `break` suppresses scale-up *decisions*, but this RC/SC is
computed and published on a path that does not depend on the pick succeeding. So an operator watching
per-role required-capacity sees a **halved decode requirement** — which reads as a healthy
under-subscribed role, not a stalled one. Same failure-signature class as the
`OptimizationReady=True`-with-no-event bug `a38d7b73` also fixes: the cluster stops acting and the
telemetry does not say so.

It also survives *"turn the `break` into a skip"* — that shape would leave the dilution fully intact
while making the symptom less visible. Not an argument against your shape-1 routing; if anything a
fourth one for it, since `st.role` fixes both effects at the derivation.

## 3. Attribution, since it bears on severity language

Verified, and I have recorded it in the review doc: the blank-`Role` construction is **byte-identical at
`075a208e`** and PR-2's diff on that file carries **zero** `Role` hunks. So this is inherited from PR-1
and absent only because PR-2 is stacked on the pre-merge tip — **not a PR-2 regression**, and it should
not be scored as one. Your A36 phrasing ("PR-2 is *missing* `a38d7b73`") already has this right; flagging
only so the framing survives into the plan text.

Two further checks, in case they save you a pass: `saturation_v2/analyzer.go:136` **does** populate
`RoleCapacities`, so the designer's §3 generalization ("any voting entry without per-role
`RoleCapacities`") is a correct conditional but a narrow live surface — saturation never takes
`initRoleState`'s `else` branch on a P/D model. And PR-2 adds **no** `RoleCapacities: nil` producer: its
`analyzer_helpers.go` delta only reads the map, and its new abstention paths key on
`PerReplicaCapacity <= 0`, a value test downstream of the key set. So PR-2 does not widen the hole.

## 4. Scope

No Type-1, Type-3, code, or CURRENT.md edit. My review doc (`386e6477`, `5d0470da`) and this file are
the only writes.
