# PENDING Type-3 edits — NOT APPLIED, NOT A SPEC

> ⚠️ **This is not a plan document and carries no authority.** It is the planner's manifest of edits
> *proposed* to `ta-anchor-dynamic-refresh-plan.md` and awaiting Dean's single approval. Nothing here
> has been applied to any plan, and no coder should read scope from it — the authoritative Type 3 is
> [`ta-anchor-dynamic-refresh-plan.md`](ta-anchor-dynamic-refresh-plan.md) @ `1a116e7a`, and the Type 1
> [`combined-analyzer-optimizer-design.md`](combined-analyzer-optimizer-design.md) (FINAL, frozen
> @ `8c2a9b04`) governs it on disagreement. Delete this file once the batch lands.

**Why it exists:** the batch grew 17 → ~23 sites across a long session that has compacted twice.
Recording it protects against exactly the silent content loss CONVENTIONS warns about, and lets Dean
review the batch as a list rather than as prose spread over many turns.

**Target file for every row unless stated:** `planning/ta-anchor-dynamic-refresh-plan.md`.
`scripts/toc-refresh.sh` runs **last**, after all rows are applied.

---

## A. Unconditional — apply on batch approval

| # | Site | Change | Origin |
|---|---|---|---|
| A1 | `:288` | C11 ranking claim is **inverted**: `Cost = 0` ⇒ the sentinel sorts **first**, not last | my verification |
| A2 | `:1315-1316` | same inversion | " |
| A3 | `:1324` | same inversion | " |
| A4 | `:1608-1612` | same inversion | " |
| A5 | `:2199-2200` | same inversion | " |
| A6 | `:288` | Cap placement: the one-replica ceiling must sit at the **granting site**, never in the `MaxReplicas` headroom branch. Widened from one site to **three**, all verified at `eb12089a`: `cost_aware_optimizer.go:104-111` (the `return …, math.MaxInt` at `:111` is *outside* the `MaxReplicas != nil` block); `greedy_score_optimizer.go:711-717` (clamp wholly inside the nil-guard); `rescale.go:454-460` (worst — a `for wantGPUs-spent >= g` loop whose **only** exit is a `break` guarded by `MaxReplicas != nil && > 0`, so an unset ceiling means replicas are granted until the GPU budget is exhausted). `MaxReplicas` is `*int` and nil/`0` are treated alike as unbounded, and the sentinel's population is never-seen zero-replica variants — the least likely to be tuned | my verification, then reviewer F42 independently at all 3 sites |
| A20 | A1–A5 addendum | The ranking inversion's **fix is `N5`, not a different sentinel value**: a never-measured variant's `Cost` arrives as `0` from the *same* zero-replica lookup that leaves `AcceleratorName` empty, so the ratio is `0/1` and it sorts first. `PRC = 1` stays the right choice and the property recovers with **no change to C11** once that lookup is fixed. Ties A1–A5 to the `N5` item currently listed as out-of-scope | coder, C11 impl |
| A19 | §C11 | Record the **post-freeze ordering dependency**: C6e's `firstDraw` floor at `greedy_score_optimizer.go:702` *raises* `capN` after `replicasToCover` at `:701` and before both bounds (`:710` pool, `:711-717` headroom). A ceiling placed next to `replicasToCover` — the natural reading of the Type-1 instruction — is therefore overwritten on the first draw. Single-role case is benign (`:702` raises to exactly 1 = the ceiling); the breach needs two roles resolving to the same sentinel variant in one pre-commit window, which **neither the reviewer nor I have established as reachable**. This is why the clamp shape is `min(cap, 1 - targets[v])` and not `min(cap, 1)` | reviewer F43 + my verification |
| A7 | §C6c items 2/3/4 | corrections carried from the currency-pivot read | my verification |
| A8 | §C6d items 1/1b/2 | ditto | " |
| A9 | §4 | Commit-message reword cost is **13**, not nine or ten: 14 commits, 13 token-bearing, 10 token-bearing subjects, `34b18bc5` the only clean one. Supersedes the "9 now vs 16 later" framing | reviewer F-recount |
| A10 | §4a | Code/doc token locations ~**49**, not 32. New load-bearing fact: production `.go` doc comments went **0 → 19** at base `075a208e`, so **PR-2 is the first to reach production prose** (PR-1 leaked into test comments only) | reviewer F-recount |
| A11 | `:1630-1632` | The C6e golden rule ("goldens are expected to move, incl. `[sat]`-only P/D") is **structurally impossible** — with one active model `allocationMean = 0` so `target == claim`, and `claimGPUs` sums role claims, so the entitlement equals combined spend exactly. Sharper replacement: **no single-model golden *can* move**; the entitlement bug needs multi-model contention | coder + reviewer, independently; reviewer retracted his own contrary pre-registration |
| A12 | `:284` | "the pool was enforced, the fair share was not" is **half true** — in `allocateForModelPaired` the pre-C6e code drove the pool to **−5** on a 7-GPU pool, so the pool was not enforced there either | coder item 0 counterfactual |
| A13 | `:1555` | same correction | " |
| A14 | `:1753` | same correction | " |
| A15 | new §-entry | **DEFERRED** classification for the pool double-count (`analyzer_helpers.go:846-857`: `pick()` runs per role against the same un-decremented `available`; decrement only at the commit loop `:903`). Needs: what it did, why deferred, both candidate fix shapes (speculative decrement + rollback vs shrinking copy reconciled at commit). **Live, not latent**, in the pool-bound case | my correction of the coder's framing |
| A16 | §-note | The indivisible-unit floor now exists at **three** landed sites, each citing the others: `greedy_score_optimizer.go:458-460` (`bound = prc`), `:694` (`firstDraw && capN < 1`), `:822` (`math.Ceil` in `replicasToCover`). Any "floor everywhere" mandate applied literally now means reverting three sites, not one expression | my verification |
| A17 | §C9 | **Finding 29** — the new "Fair-share iteration" paragraph says the single-model case "gets `mean == 0`". It is **`allocationMean`** that is zeroed (`:292-297`); `mean` equals that model's own remaining and still governs the `w.remaining > mean` drop check at `:308`. As written it reads as the inverse | reviewer F29 |
| A18 | §C6f or §C11 | Give the unplanned dormant spec `537b0153` (test-only, +88, `PIt`, asserts the honest even split) a **§-home**, or an explicit "unplanned — revert if the claim-pricing disposition rejects it" note. It currently says in its own first line that it is not in the plan | reviewer, endorsing it |

| A21 | §2e.2 `:1169-1170` | The import-cycle clearance is **false**. *"`internal/config` imports no `internal/engines` package"* ignores `internal/config/config_test.go`, which is **`package config`** and imports `throughput` for the drift guard on the duplicated `throughputAnalyzerName` literal (`config.go:338-341`). So `throughput → config` is a **test-binary** cycle: `go build ./...` stays green, `go test ./internal/config/...` fails. The text points away from its own cause. C10 **landed** as `1a50b418`, and the shipped shape is **not** any of Finding 48's four options — it is a fifth: `resolveKSat(cfg domain.AnalyzerConfig)` (`analyzer.go:217-223`) asserts a **self-declared single-method interface** `interface{ KSat() float64 }` against **TA's own already-injected config parameter** — the one TA received and previously ignored. Production `throughput` imports `internal/config` **nowhere** (verified: the only two matches are prose in comments); the sole importer is `k_sat_test.go`, which is in-package `package throughput`, and both test binaries stay acyclic because test files only ever compile into their own package's binary. **Correct transcription for §2e.2** (all three clauses, none of which the current text says): production `throughput` never imports `internal/config`; the accessor is a self-declared single-method interface on the config TA already receives; the duplicated `0.80` is drift-guarded from **both** sides — `config.go:338-341` in one direction and the new `TestFallbackKSatMatchesConfigDefault` (`k_sat_test.go:24-27`) in the other. Still **explicitly rule out deleting the drift guard**: §4b-classifiable, presents as a build fix. **Dean, 2026-08-08 — the layering question ("may an analyzer read another analyzer's config section?") is settled as LEAVE-AS-SHIPPED + record a TODO, not a decision**; the natural host already exists in code (`analyzer.go:214-216`, `TODO: unify with the system-wide k_sat used by the EPP`) and matches the CURRENT Issues-to-Open entry, so no new note is needed — only the plan text | reviewer F48 diagnosis (stands, and deserves the credit); designer retraction of its own option-3 recommendation; shipped shape + acyclicity verified by me at `1a50b418` |
| A21b | §2e.2 — Dean's missing-in-sat question, answered | Record the **degenerate-case table**, because the answer is "0.80 in every case, by two independent routes that cannot silently drift". No sat config at all (nil, or any config type without `KSat()`) → assertion fails → `fallbackKSat` = **0.80**. `saturation: {}` with `kvCacheThreshold` unset → `ApplyDefaults:294-295` writes `DefaultKvCacheThreshold` → **0.80**. Explicit `0` → treated as unset by `ApplyDefaults`, and even if it reached `resolveKSat` the `k > 0` guard rejects it → **0.80**. Negative → `Validate:401-402` rejects the config outright, and `k > 0` is the backstop → **0.80**. **`> 1` → `Validate:401-402` rejects** (*"kvCacheThreshold must be between 0 and 1"*), so the nonsense-fraction path Dean was implicitly worried about cannot reach TA at all; `:418` additionally requires `KvCacheThreshold >= KvSpareTrigger`. So no configuration-hygiene workaround is needed — every degenerate path is closed in code. One honest behavior note for the commit message: the **no-config path changes `0.85 → 0.80`** (TA never read config before, so it was always the old `DefaultKSat`), which is inside the already-recorded sub-1% band, **not** the "~6%" figure | my verification of `resolveKSat`, `constants.go:52-68`, `saturation_scaling.go:294-295,:401-402,:418` |
| A22 | throughout §2/§2d/§2f | Tip + status are stale by nine commits: `d9f3b97e` → **`b6bb525c`**, and *"C6c has zero edits, scoped read-only, held on Dean's call"* → C6c **landed** as `34b18bc5` (GPU-space pivot), then C6d `330fcd26`, C6e `784c2b5c`, C6f `a679f2ad`, C11 `b6bb525c`, C10 in flight. Every *"as of `d9f3b97e`"* line-reference label needs re-verification — the drift is actual, not prospective, and C6c–C6f touched exactly those files | PR-1 reviewer Part 2.1 + my verification |
| A23 | §rebase step | Must specify **`git rebase --onto upstream/main 075a208e`**. PR-1 squash-merged, so PR-2's merge-base is `aadaa596` (pre-PR-1) and a bare `git rebase upstream/main` sees all of PR-1 as added on both sides: **10 conflicts**, incl. `add/add` on `optimizer_combine_characterization_test.go` + `optimizer_scale_from_zero_test.go`. True surface is **2**: `analyzer_helpers.go` (PR-2's new comment vs `main`'s `buildCapacityMap` swap — take both) and `rescale.go` (**duplicate** `if anchor == nil` guard, arrived at independently). Preferred `rescale.go` resolution: take **`main`'s**, which is §4a-clean, so resolving the conflict removes a violation. Also record that local `ta-anchor-refactor-v2@075a208e` is **not** what merged — `a38d7b73`'s four fixes exist only on `origin/` and in `main` | PR-1 reviewer Part 4, measured via `git merge-tree` |
| A24 | §4 / §4a — supersedes A9/A10 | **11 of 17** commit messages carry a token (heading to ~14), in-tree count `1 → 22 → 36` across C6c–C6f. Critically, the plan's *"17 already inherited at `075a208e`, out of scope"* is **1** under a tighter grep: the plan's expression also catches **legitimate code identifiers** — the `T1-ols` reason string, and `V1`/`V2`, which appear ~12× in `internal/config/saturation_scaling.go` alone as saturation **engine-version** names — which must not be renamed. The two figures were never comparable and more of the debt is PR-2's own than credited. **Pin one grep expression in the plan before re-quoting any count** | PR-1 reviewer Part 5 |
| A24b | A24 addendum — the ledger to pin | The reviewer's third recount is the one to adopt as the pinned expression, and it is now **self-corrected twice**: pattern `C<n>[a-f]?` · `PR-1/2` · `W<n>` · `N<n>` · `U<n>` · `D-a/D-b` · `T1.<n>` · `FZ-admission`, text files only (`git grep -I`), over `internal/**` + `docs/**`. Table: `075a208e` **7** inherited · `b6bb525c` **52** / 16-of-18 messages · `1a50b418` **53** / 17-of-19 · `79a590d6` **54** / **18-of-20**. Its own retractions: it had quoted 53 "as of `b6bb525c`" (was 52) and 17-of-19 there (was 16-of-18), and an earlier ~61 included **8 `Binary file … matches` lines from the dev-guide PNGs**. Two reasons to prefer it over my own figures: `-I` kills the PNG class, and I verified its pattern is **clean of the golden-name false positives A24 warns about** — no `C1`/`A1`–`A4` exists anywhere in `internal/**` at this tip, and `V1` is outside the pattern. **But it is not a closed figure either**, and this is what the plan must say: 54 is **token-class only**, under a pattern that excludes both the plans-branch **path/filename** class (the reviewer acknowledges it separately in its own §5 and leaves it unquantified) and bare **"Type-1"** prose — so A28's two surviving violations sit outside all 54, one of them added by C11. Pin the expression *and* state what it does not count | reviewer's C9-sweep handoff §1, verified by me at `79a590d6` |
| A25 | §2f | Steer C11's `Reason` constant spelling away from `a38d7b73`'s new `variant.ReasonOptimizationRefused` / `constants.K8SEventOptimizationRefused` family — different namespace, no technical collision, but two "Reason" families now coexist in-tree and §2f leaves the spelling to the coder. Optionally cite `a38d7b73`'s own `allPicked`-clears-and-breaks explanation as **independent corroboration** in merged code of §2f's ⚠ skip-not-zero-cap requirement | PR-1 reviewer Part 4.3 |
| A26 | §2f `(D-a)` | Population scope is wrong and the fix is free. **Three** populations reach the binder-miss branch, not one: **lapsed** (ran, scaled to zero, TA state deleted after `2*DefaultObservationMaxAge` — TA's own comment concedes *"degrades to the never-seen case"*), **cold-but-priceable** (sibling/deployment estimate), **cold** (`satReasonNoData`). Saturation tiers 1–2 return stored `EffectiveCapacity` *authoritatively* when `LearnedFrom == learnedFromLive`, so a **measured** PRC often exists for exactly that variant. The discriminator is already at the write site — the identity carrier is located **by name with no `Enabled`/`Live` check**, so `a.Reason` is readable in every configuration — and the merge **discards** it (`out.Reason` assigned only inside the `bByName` hit branch). Keep the two narrowings **visibly distinct**: *"admit only when saturation votes"* is dead by reachability (sat's voting predicate is its binding predicate); *"admit only when the carrier has no record"* survives. Splits `(D-a)` into population scope and a separate `N8`/`VG-up` question about sizing from a stale carrier — deferring `(D-a)` does **not** dispose of the latter | designer §1/§2, endorsing + refining review F44 |

| A27 | §verification `:2033-2040` | The C6c gate **fails by design and will trip C9**. It requires that after `grep -rn "ceil(" internal/engines/pipeline/`, *"`fairShareCap`'s must be **gone**, replaced by the whole-replica `floor` fill"* — but `fairShareCap` no longer exists under that name (it is `replicasToCover`) and the tree ships `ceil` there deliberately, with a written rationale. Re-express against the new name whichever way the rounding question is decided. **Note what survives intact:** the gate's own one-sentence rule at `:2039-2040` — *"round up when asking how many replicas a demand needs, round down when asking how many replicas a budget can afford"* — is exactly the two-directional policy the code implements at `:697-700`. So the gate is not wrong in principle, only in its `fairShareCap` clause and its name | designer §1.3, verified |
| A28 | §4a — **corrects B3, does not close it** | Review Finding 33's four cited lines **are** fixed (`4fb49ac6`, *"drop plans-branch paths from shipped comments"*), and a `plan__|review__|sync__` grep across `internal/` is clean at tip. But the designer's conclusion *"Finding 33 is CLOSED — do not route it"* rests on that narrow expression. A broader one finds **two surviving violations, both PR-2's own** (absent at base `075a208e` **and** on `upstream/main`): `analyzer_helpers.go:642` cites **`combined-analyzer-optimizer-design.md § invariants #7`** — a direct plans-branch document reference, the exact class §4a names — added by `8eb6ee2d`/`b106b929`; and `analyzer_helpers.go:88` reads *"Type-1 owner's, not this file's"*, a taxonomy/role token, added by **`b6bb525c`** — the current tip, i.e. **after** the cleanup commit. So the in-tree burden is **not** monotonically self-correcting as claimed; C11 re-added one. This is the fourth mutually-inconsistent §4a count from three sessions, and all four expressions missed both of these lines — which is the argument for A24's "pin one expression" being a plan step, not a preference. (Separately: `internal/collector/locator/locator.go:4` cites `docs/superpowers/specs/…-design.md` — **inherited**, not PR-2's; belongs to the `main`-side backlog in `governance-follow-ups.md`) | my grep + provenance check; supersedes the designer's §3 closure |

| A29 | §C9 test row | **Finding 49** — two one-line §4a token edits, both verified present at `79a590d6`: `k_sat_test.go:163` *"Pre-C10 this priced at k = 0.85"* → "Before this change" (identical meaning); and `rescale_test.go:186` *"The from-zero admission ceiling (C11) is what stops…"* → drop "(C11)", the sentence already names the mechanism. Unlike the commit-message instances these are ordinary edits, not rewords — which is the whole argument for routing them **into C9 rather than after it** | reviewer Finding 49 |
| A30 | §C9 test row | **Finding 50** — `rescale_test.go:239` `max := 3` and `:248` `max := 8` shadow the Go builtin. Verified: these are the **only two** `max :=` declarations in `internal/**` + `cmd/**` at this tip, and the two sites ev-shindin objected to in the #1246 review are **gone** (`analyzer_helpers.go:977` now uses the builtin correctly), so PR-2 is the sole place reintroducing a pattern the codebase has moved off. **`make lint` cannot catch this** — gocritic's builtin-shadow check is off by default, so the coder's green gates are not evidence against it. `maxRep` costs nothing and no competing local idiom exists. A convention regression against a maintainer's stated objection, not a gate failure | reviewer Finding 50 |
| A31 | §C9 dev-guide row | C9 must **not** describe the from-zero ceiling as an active guard. Per Finding 46 nothing writes the tag and `(D-a)` is deferred, so the ceiling is **dormant in production**; a dev-guide sentence implying it currently bounds anything would be wrong on the merged branch. **Correction to the same handoff's §5:** its first item — *"`analyzer_helpers.go:213-216`'s 'Not proactively selectable' comment is now false and needs correcting"* — is **already fixed and needs no C9 row**. The line reference drifted (the comment is at `:178`, C11 having inserted above it) and `b6bb525c` **rewrote that very comment**: the old *"genuine cold-starts fall to the reactive scale-from-zero engine"* is gone, replaced by *"its sizing must not be invented … Proactively admitting the zero-replica case … is deferred; see `ReasonFromZeroAdmission`"*. That text is accurate **and** consistent with Finding 46 — the finding was carried forward without re-verifying against the tip the handoff itself declares it reviewed | reviewer §5 + my verification at `79a590d6` |

| A32 | §4a — **strengthens A24b; the sweep is not mechanical** | **Finding 51** (`analyzer_helpers.go:216-218`) establishes a principle that changes what a §4a step must *say*: the tokens are **load-bearing markers of "written before X landed"**, so some of the 54 locations are stale in **content**, not merely in vocabulary. Its instance: *"once **PR-2** admits multiple non-saturation voters, a later qualifying entry does not overwrite the earlier one"* — future-tense about a condition `votingResults` (`:315-323`) **already satisfies on this branch**. Strip the token mechanically and you get *"once this change admits…"*, which is §4a-clean **and still false** — and a clean sweep is the thing nobody re-reads afterwards. So the plan's §4a step must direct a **prose rewrite where tense or premise moved**, not a token substitution, and must say the residual risk at such sites is *higher* than at the other 46. Reviewer's own framing, and it is right | reviewer Finding 51 |
| A33 | §4a — the tension that will let A28 through | The coder's C9e is scoped *"47 of 54; the 7 inherited at `075a208e` out of scope"*, and the reviewer **endorses that as matching its ledger exactly** (54 − 7 = 47) while, in the same document, listing *"the path/filename class"* among the items that **"remain pending"** for that commit. Both statements are its own and they cannot both be complete: 54 is token-class only. That is the precise mechanism by which A28's two sites — `analyzer_helpers.go:642` (design-doc **filename**) and `:88` (*"Type-1 owner's"*) — pass through a sweep that is simultaneously certified exhaustive. **Re-verified: both still live at `757fc6f5`.** Scoping the sweep to the PR-2 delta is correct on its merits (the 7 inherited belong to the `main`-side governance backlog) — the defect is the *class* boundary, not the delta boundary. The plan step must therefore name **three** classes: tokens (47), plans-branch paths/filenames, and taxonomy prose (`Type-1`, `Type 3`) | my re-verification at `757fc6f5`, against the reviewer's §C9-gap + ledger-delta sections |
| A34 | §C9 — supersedes A31's first clause only | Distinguish two **adjacent but different** comments, because the reviewer's handoff and its review doc point at nearly the same lines for different things. `:213-216` *"Not proactively selectable"* → **already fixed**, no row needed (C11 rewrote it; it now lives at `:178` and is accurate — A31 stands). `:216-218` the **N2 tie-break** comment → **Finding 51, genuinely open** (A32). A31's correction must not be read as dismissing Finding 51. **Now moot as a disagreement — the reviewer has retracted it itself** (C9b pre-registration **P2**, retracting its own C11 checklist items 7 and 13): those items assumed `(D-a)` would ship, and with it deferred the *"not proactively selectable"* claim is **true as written**, so *"correcting" it would replace a true statement with a false one*. It pre-commits to scoring any regression there as **its own** error, not the coder's. So A31/A34 reduce to bookkeeping: apply them as a note, not as a counter-argument | my verification, corroborated by the reviewer's own P2 retraction |
| A38 | §4 rebase step — A36 addendum | The phantom `"both"` bucket has a **second, separable effect** that A36 and both source handoffs missed: **decode demand is understated by exactly 2×.** Verified at `2ae440e3` — `distributeDemandByRole:918-941` builds its role set with `RolePrefill` **excluded**, maps blank → `RoleBoth`, then assigns every role the *same* `share := demand / float64(len(roles))`. Correct P/D gives `roles = {decode}`, `len == 1`, decode gets the full model decode demand; the phantom gives `{decode, both}`, `len == 2`, decode gets **half**. That share flows `aggregateRoleCapacities` → `RoleCapacities[decode].TotalDemand` → the engine post-step that writes per-role RC/SC. **Why it is separable from the break:** RC/SC is computed and published on a path that does not depend on the pick succeeding, so the `break` suppresses *decisions* while telemetry keeps reporting a **halved decode requirement** — which reads as a healthy under-subscribed role, not a stalled one. Same signature class as the `OptimizationReady=True`-with-no-event bug `a38d7b73` also fixes: the cluster stops acting and the telemetry does not say so. It also **survives break→skip**, which would leave the dilution intact while making the symptom less visible. Two consequences: (1) a **fourth argument for shape 1** — `st.role` fixes both effects at the derivation, a one-liner-plus-nothing does not fix the telemetry story, and severity language must name both; (2) **a live hazard for C9c, in flight right now** — if the multi-vote goldens use a P/D fixture with any zero-replica variant, the golden **bakes the halved decode demand into a characterization test**, which is worse than the break because the break is obvious and a wrong frozen number is not. **Attribution (keep this framing):** the construction is byte-identical at `075a208e` and PR-2's 41/12 delta on that file contains **zero** `Role` hunks (verified) — inherited from PR-1, absent only because PR-2 is stacked on the pre-merge tip, **not a PR-2 regression**. Also narrows the designer's §3: `saturation_v2/analyzer.go:136` does populate `RoleCapacities`, so its `else`-branch generalization is a correct conditional over a narrow live surface, and PR-2 adds no `RoleCapacities: nil` producer — **PR-2 does not widen the hole** | reviewer's second-effect handoff §1–§3, every claim re-verified by me; upstream's own replacement comment names both effects |
| A37 | §0 state-of-record + §2e | Three corrections to my own tracking, all verified by `rev-list --count` rather than subject-matching (the shortcut that produced drift in three documents). **`b6bb525c..HEAD` is 4 commits, not 1** — so **C10 has LANDED** as `1a50b418` *"throughput: read k_sat from config instead of hard-coding it"*: §2e stops being pending work and becomes shipped, and any text saying the coder is "now on C10" is wrong — it is past it. Tip is **`2ae440e3`**, with one untracked file (`optimizer_invariant7_test.go`), so C9's test half is mid-flight. **T1-1 (`ceil` vs `floor`) is withdrawn as blocking and as a C6c scheduling constraint** — C6c landed as `34b18bc5` before the instruction was written, and `replicasToCover:834-838`'s `math.Ceil` (the only `Ceil`/`Floor` in non-test `greedy_score_optimizer.go`) carries a written rationale at `:826-836`. It reduces to a **doc-vs-code divergence** — frozen Type 1 mandates `floor`, tree ships `ceil` with justification — still Dean's call, with the safe side already compiled. My narrowing of the non-termination mechanism is adopted by the designer: the hang needs `allocateForModel` to return **true while allocating nothing** (since `!allocated` sets `w.remaining = -1` and terminates), so it is conditional, **not a property of `floor`** | designer's withdrawal handoff §2/§4, re-verified by me |
| A36 | §4 rebase step (**highest-value row in this batch**) | The rebase step must name the four behaviors `a38d7b73` brings and require a post-rebase message-vs-diff check for each, because **PR-2's branch is missing all of them** — verified: `git merge-base --is-ancestor a38d7b73 HEAD` → **absent**, since PR-2 is stacked on PR-1's *pre-merge* tip. One of the four is a **live P/D break already on this branch**, sentinel-independent: the scale-from-zero complement at `throughput/analyzer.go:435-439` emits `VariantCapacity` with **no `Role`** (confirmed at `2ae440e3`); `distributeDemandByRole`/`aggregateRoleCapacities` consume that same slice *before any anchor merge* and canonicalize blank → `RoleBoth`; on a disaggregated model `len(byRole) == 3` so the only-`both` nil guard misses; `initRoleState` unions ballot role keys; `pick("both")` finds no anchor variant (anchor roles come from the saturation (a)-carrier) ⇒ `allPicked = false` ⇒ **`break` on the first iteration ⇒ zero scale-up decisions for the whole model** whenever a previously-measured variant sits at zero. TA need not *bind* — enabled + live is enough, since the union is over the voting set. **Correction to the handoff proposing it:** the fix is **`Role: st.role`** (persisted state, hunk `@@ -408,6 +415,7 @@`), *not* `Role: vs.Role` as written — they are kept in sync by `:253` so behavior likely matches, but "identical text to `main`, a clean no-op at rebase time" is then **false**, which is the entire safety argument for the one-line-now shape. **My routing: shape 1 (rebase), not the one-liner** — the rebase is due anyway, the other three fixes are real and two are operator-visible (`OptimizationRefused` + Warning event; the `wva_desired_replicas=0` KEDA-reads-as-scale-to-zero rescue), and a lone one-liner leaves the branch fixing the *quiet* bug while still carrying the two *loud* ones. Sequencing also argues for it: injecting a source edit mid-C9c muddies the per-commit golden attribution the C6c-first ordering exists to protect. Also record the **CURRENT.md reading trap**: "Finding 12 is FIXED, not deferred" is true of `main` and **false of PR-2's branch** | designer's P/D handoff §1/§2, every step verified by me at `2ae440e3`; `a38d7b73` message derives the same chain independently |
| A35 | §2f `(D-a)` + §12 deletion/deferral ledger | Rewrite the `(D-a)` deferral as a **§4b DEFERRED classification with a mechanism clause**, not a one-line TODO. Three required parts, because a future implementer reading only the frozen Type 1 builds the regression: (1) **what it would do** — proactively admit a never-measured zero-replica variant so the cost/fair-share ranking can pick it; (2) **why it is not shipping** — the frozen mechanism is insufficient, not merely unfinished, and today's behavior is safe without it (anchor PRC 0 ⇒ `cost_aware_optimizer.go:100` passes the variant over ⇒ co-tenant picked normally); (3) **the mechanism the follow-up must carry** — the sentinel is written on **the binding analyzer's own ballot entry**, and the (b) merge carries it to the anchor as a consequence; an anchor-only write ships a regression that takes the **co-tenant's** scale-up down with it via the `demand = 0` → `utilByRole = 1.0` → `!anyPositive` → `break` chain, and in P/D silently commits prefill without decode. This is the one part of the designer's ask that lands in a doc **I own**, and it is independent of Dean's scope call — it is required whether `(D-a)` ships in PR-2 or not (if it ships, the same clause is the spec; if it defers, it is the deferral record) | designer's `(D-a)` handoff § recommended fix + its explicit-choice constraint; §4b |

## B. Conditional — each waits on one decision

| # | Depends on | Change |
|---|---|---|
| B1 | **(vi) claim pricing** | Land the chosen disposition: accept-and-document / headroom partial / **option (d)** (`min(gpusPR / PRC)` over feasible candidates). If (d): record that its neutrality is **contingent** (via `ceil` + a binding bottleneck), *not* structural — golden scenario A has equal `GPUsPerReplica`, unequal PRC, and the reference **flips** `cheap → expensive`, halving the claim `0.5 → 0.25` GPUs. Also record that (d) changes the **ranking key** for any unequal-PRC role, which no golden covers |
| B2 | **(vii) Finding 28** | Add a discriminating spec for `fairShareRolePick`'s per-role budget. Reviewer's table: clamp-only passes **both** shipped specs, so `committed0`, `reserved`, the per-draw holdback and `firstDraw` are pinned by nothing. §C6e asked for "roles that would each individually fit but jointly overrun"; the shipped fixture has both roles individually exceeding `target`, which is what lets clamp-only pass. Technique already established by `34b18bc5` (call the returned pick closure directly). This is **Finding 20's shape recurring** |
| B3 | **(viii) Finding 33** | A step naming the four shipped §4a defects — `greedy_score_optimizer_test.go:1602-1603` (handoff **path**), `:1741-1743` (three handoff filenames, one written today), `:1604` ("open with the Type-1 owner" — a mis-routing I introduced, now in code), `:1736` (`784c2b5c`, a pre-rebase SHA). My recommendation: **not** C9 — the handoff refs are `.DONE`+`git rm`-ed before the PR merges, so they are dead on arrival |
| B4 | **(ii) C6e item 2** | If fixed: a **C6g** row in §0 between C6f and C11, and the git-order line updated. Rationale for a separate commit: it is entitlement accounting, not sentinel ranking, and C11 is already a behavior-change commit whose golden attribution should not absorb a second change |
| B5 | **(i) C6c fork** | Whichever of (a) restore `ceil` / (b) defer-not-evict / (c) `max(1, floor(x))` is chosen, applied as a **three-site** policy per A16 — not a single-expression edit |

| ~~B6~~ | ~~(xii) Finding 47~~ | **CLOSED — no decision needed; the coder landed it voluntarily as `79a590d6`** *"pipeline: test the admission ceiling at fillRole (C11 D-b follow-up)"*, **+73 lines** to `rescale_test.go` (not the ~15 I estimated). So the question this row was waiting on — C11's own row vs a `(D-a)` follow-up — was answered in the tree, as C11's: the message labels it a `D-b` follow-up, which is the shipped half. Nothing to apply. The two §4a/`max`-shadowing items above (A29/A30) are findings **against this same commit**, so it is not defect-free, only complete |
| B8 | **(xiv) `replicasToCover` Σ-overshoot** | The `ceil` ships with a **known, coder-acknowledged consequence recorded only in a test comment**: `greedy_score_optimizer_test.go:1428-1430` — *"without that, Σ_role spend exceeds target by the round-up, which is the **deferred `replicasToCover` item** and not this one"* — and the C6e fixture is built from whole multiples specifically so it cannot trigger. Whatever Dean decides on the rounding, this deferral needs a **plan home and a §4b classification**; right now it exists nowhere but a comment inside a test that is designed not to exercise it. Independently of the rounding decision, this row should land |
| B9 | **(xv) §4a sub-class ruling** | Does §4a cover **bare "the plan"** and **review-finding-number attributions**? `79a590d6`'s message ends *"Raised by the PR-2 internal review as Finding 47."*; C10's has *"the plan has `resolveKSat` type-assert …"* and *"Two deviations from the plan"*. Neither carries a path or filename, so both sit **outside §4a's literal prohibition** — this is a convention extension, not an existing violation. Two reasons it needs deciding rather than drifting: a finding number *reads as a precise citation* yet is unresolvable for anyone reading `main`, arguably worse than the vaguer "the plan"; and the coder is **now doing this regularly**, which is otherwise a good habit worth preserving in some other form. The reviewer's read (which I share): the substance is always already in the message, so dropping the identifier is free. **The answer changes C9's scope from 54 locations to 54 plus a commit-message pass**, which is why it should be settled before C9 rather than after | reviewer §4, explicitly framed as a convention call and not a review finding |
| B7 | **(i) restated — T1-1 / AM-1** | The fork is **already resolved in-tree as (a)**: `replicasToCover:833-838` ships `ceil` with a written rationale at `:824-832`, and there is no `math.Floor` in non-test `greedy_score_optimizer.go`. So the row is no longer "apply one of three" but a **doc-vs-code divergence**: frozen Type 1 `:1159-1160` mandates `floor`, the tree ships `ceil`. Exactly one must move, and if the Type 1 moves this row becomes a no-op |

## C. Not in this batch — other owners

- `sync__` handoff carrying the A9/A10 recount into CURRENT.md (supersedes "all nine (6/9 subjects,
  8/9 bodies)" and "32 code/doc locations"). Blocked on the (vi)/reword-window rulings; I cannot edit
  CURRENT.md.
- Post-freeze Type-1 rationale touches: the claim-pricing rationale at `referenceVariantForRole:829-838`
  and **Finding 27**'s `:1530-1533`. The reviewer recommends deciding them **together**. Dean's, not mine.
- **Post-freeze Type-1 `(D-b)` amendment — the third such item, and the only one that is a *text
  defect* rather than a rationale touch.** `(D-b)` says to fold the one-replica ceiling into the
  per-site `headroom` computation "including its `headroom <= 0 → continue`" / "same clamp, same
  skip" / "add the ceiling to that same `break` condition". Followed literally that nests the
  ceiling inside a nil-guard at all three grant sites (A6), so the ceiling does not exist on an
  untuned variant — which is the sentinel's whole population. Correct shape is an **unconditional
  sibling** clamp, `cap = min(cap, 1 - targets[v])`, with its own `continue`/`break`, placed after
  the pool bound (A19). **Needed whichever way the C11 diff goes.** I am not amending it: Dean
  divided scope so the plan reviewer handles Type 1 and I own the derived Type 3 only, and
  post-freeze Type-1 changes go through Dean. The handoff routes the amendment to me as "Type-1
  owner" — a label the same reviewer declined for himself — so this is a genuine routing conflict
  for Dean to settle, not something to resolve by guessing.
- **`(D-a)` cannot ship as written — a Type-1 *design* defect, the fourth post-freeze item, and the
  only one that is a regression rather than a text or rationale problem.** The sentinel is written onto
  the **anchor**, and the six `PRC <= 0` gates it clears are all selection-side. Sizing is not
  selection-side: `roleBottleneckReplicas:607-616` reads the **ballot** via
  `votesFromPickerState:511-518`, which calls `prcForVariant(e.Result, …)` — the entry's own Result,
  never the anchor — and abstains on `<= 0`. Every voter abstains ⇒ `binder < 0` ⇒ bottleneck `0` ⇒
  `min(0, cap) = 0` ⇒ `deltaUtil = 0` ⇒ the model's loop breaks, taking down **every variant behind the
  admitted one**. Verified by the coder's mutation on a `[sat-not-live] + [TA]` fixture: with the
  sentinel written the *measured* variant stays at 2; with it disabled it scales past 2. The admitted
  variant gains nothing and a working variant loses its scale-up. It is the same `cap = 0` hazard
  `(D-b)`'s own ⚠ describes, arriving through the bottleneck, where the ceiling is structurally
  powerless. Corroboration: Test 10's `revived` scales *because* TA emits a PRC-only row into its own
  ballot entry; `cold` (never seen) stays 0 — sizing has always come from the ballot, and `(D-a)` is
  the only proposed admission that writes the anchor alone. **Coder held it; the tree ships `(D-b)`
  only, gates green, no golden moved.** Three-way fork, explicitly Dean's: (1) binder emits the
  sentinel into its own ballot entry — closest to `revived`, one currency, but makes a synthetic value
  a *vote*, colliding with `N8`; (2) `roleBottleneckReplicas` floors at 1 for a tagged variant —
  localised, but invents a bottleneck that ignores its voters, contradicting the abstain-not-veto
  semantics stated at `:512-517`, and needs its own gate audit; (3) narrow C11 to `(D-b)` and route
  admission to `N5` — which A20 shows the ranking correction **already** depends on. My recommendation
  is **(3)**, and by decision rather than by default: it is the only branch that preserves current
  behavior, and it lands admission and ranking together on one real fix instead of a synthetic value.
  Needs a **DEFERRED** classification with design intent, not a silent narrowing.
  **Reviewer Finding 44 makes the failure the whole reachable domain, not a point in it** (verified at
  `b6bb525c`): `aCarrier := binding; if satNR != nil { aCarrier = satNR }` (`:237-240`) plus `:211-213`
  means that when saturation binds, `binding == satNR == aCarrier` is **one pointer**, so `bByName`
  (`:260-263`) is built from the identical slice the merge iterates (`:265`) and the no-variant `else`
  is unreachable; `:230-232` returns nil when nothing qualifies. The write site is therefore reachable
  **only** with saturation present-but-not-binding and another analyzer binding-and-omitting — and in
  that state all three sub-cases are unsizable: sat `!Enabled` and sat `Enabled && !Live` never enter
  the `Enabled && Live` voting set (`:318`), while sat `Enabled && Live && !Informative` *does* vote but
  carries only NoData/Error rows at PRC 0, so the ballot-side `prc <= 0` gate skips it. `(D-a)` as
  written **cannot scale a variant from zero in any configuration.** Two consequences: (a) there is no
  *"only admit when saturation votes"* narrowing — the natural thing to reach for — because when
  saturation votes it also binds and the branch is unreachable, so that version is a feature that never
  fires and the amendment should say so; (b) **option 2 is out**, not merely weakest: in sub-case 3
  saturation *is* in the voting set pricing nothing usable, so a floor would grant a replica on the
  strength of a no-data ballot, contradicting the abstain-as-a-pricing-rule invariant. **The fork
  therefore collapses from a mechanism question to a scope question:** option 1 is the only mechanism
  that works (same state, one currency, cost = a synthetic value entering the vote — the `N8` question
  proper), and option 3 is "not in PR-2". Reviewer declines to choose between 1 and 3.
- **Mechanism now settled three ways — and the `N8` objection to option 1 is dissolved.** The designer
  (`plan__ta-anchor-da-sentinel-belongs-on-the-ballot`, 2026-08-08) **owns the defect** — *"The defect
  is **mine**. The `FZ-admission` mechanism I froze into the Type 1 at `8c2a9b04` … is insufficient as
  written"* — and independently reaches option 1: **write the `Reason`-tagged `PRC = 1` on the binding
  analyzer's own ballot entry**, letting the (b) merge carry it onto the anchor as a consequence. That
  retires my one reservation. I had scored option 1 as "a synthetic value entering the vote — the `N8`
  question proper"; the Type 1 already answers it at `:1512-1515` — the sentinel is *in the binder's
  own currency*, hence **a declared minimum, not a borrowed measurement**, which is not what `N8`
  prohibits. Anchor-only made that existing sentence false; ballot-side makes it true. So ballot-side
  is **a correction toward the frozen design's stated intent, not a new direction** — one write site,
  eligibility/ranking/bound all unchanged, and sizing works because the binder then casts
  `state[binder][role] / 1`. The arithmetic closes at exactly one replica:
  `n = min(bottleneck, 1) = 1` ⇒ `deltaUtil = 1/demand` ⇒ `k = 1`; next iteration headroom `1-1 = 0`
  ⇒ `continue` ⇒ the co-tenant is picked normally.
- **The blast radius is worse than this section recorded, and I verified every step at `2ae440e3`.**
  Two sharpenings. (1) **It is the default ordering, not an unlucky one:** saturation reports
  `Cost = 0` for a zero-replica variant (`N5`), so `0/1 = 0` sorts the never-measured variant
  **first** in `sortByCostEfficiencyAsc`. (2) **The co-tenant loses its scale-up too**, not just the
  from-zero variant. Verified chain: `PerReplicaCapacity <= 0` at `cost_aware_optimizer.go:100` no
  longer skips it ⇒ `maxTargetReplicas` → `(1, true)`, headroom 1, `allPicked` true ⇒ but
  `votesFromPickerState` (`:522-535`) reads `prcForVariant(e.Result, v)` — **the ballot, not the
  anchor** — so every entry hits `prc <= 0 { continue }` ⇒ `roleBottleneckReplicas` → `n = 0`, and
  `roleAggRemaining` (`:698-704`) abstains ⇒ `demand = 0`. The step that makes this lethal rather than
  inert is `:969-971`: **`if demand <= 0 { utilByRole[role] = 1.0 }`**, so `deltaUtil = 1.0` and the
  `deltaUtil <= 0` guard at `:982` — the guard built for exactly this — **does not fire**. Then `k` is
  computed only `if prc > 0 && demand > 0` ⇒ `k = 0` ⇒ `!anyPositive` ⇒ **`break` at `:1001`** out of
  the whole model's allocation loop. Textual corroboration in-tree: `cost_aware_optimizer.go:104-107`
  already warns that a returned cap of 0 *"would take every variant behind it down with it"* — the
  anchor-only sentinel re-opens that same hazard through the **demand** path instead of the cap path.
- **New failure mode, previously unrecorded: P/D unmatched commit.** If the never-measured variant is
  alone in its role, the *other* role's positive `k` keeps `anyPositive` true, so there is no break —
  instead prefill commits while decode stays at zero, violating the matched-joint-commit that
  `allocateForModelPaired` (`:930`) exists to guarantee. The break is loud; this one is silent.
- **Dean's *"use sat's demand"* option is now closed with a reason, not merely ranked last.** TA binds
  only when saturation fails `Enabled && Live && Informative`, and `votingResults` (`:332-340`) prunes
  on `Enabled && Live`: failed-on-Live ⇒ not in the voting set at all (no donor exists);
  Live-but-not-Informative ⇒ every variant capacity is a no-data/error sentinel ⇒ `prcForVariant <= 0`
  ⇒ abstains. *"There is no saturation demand to borrow at the moment TA binds."* `N8` rules against
  cross-analyzer borrowing independently. Break→skip is also ruled out as the quick fix: *"fixes the
  blast radius but not the feature"*, and it needs a per-iteration exclusion set or the re-pick spins.
- **My scope recommendation is unchanged — defer — but the reason changed and it now carries a
  mandatory rider.** Not "because option 1 collides with `N8`" (dissolved above) but because it is a
  feature addition to a PR sitting on its last commit, and **today is safe**: `V_zero`'s anchor PRC is
  0, so `:100` passes it over and the co-tenant is picked normally — *"there is no live bug to bypass
  today."* The rider is the designer's own, and is the part that must not be dropped: whichever
  disposition Dean picks must be **chosen explicitly**, and *"if it stays deferred, the follow-up must
  carry the ballot-side requirement, not just 'write the sentinel'; otherwise a future implementer
  reads my Type 1 and builds the broken version."* Concretely that makes the deferral a **§4b DEFERRED
  classification with a mechanism clause**, not a one-line TODO — a Type-3 row I own and can apply in
  the batch. **What I am not deciding:** whether anything lands in PR-2 (Dean's), and the Type-1
  amendment itself (the designer's).
- **Designer's queued Type-1 amendments — no action for me, but they change what the Type 3 derives
  from.** `:1524-1526` marks eligibility as "the whole point" (*"the located error: necessary treated
  as sufficient"*); `:1512-1515` gains the ballot-side precondition; the `:2062` roll-up's *"leaving
  nothing open on either"* is wrong; the `FZ-admission` findings row's *"Adopted — folds into PR-2"*
  overstates. Plus one broader than `(D-a)`: **the `N2`/`N7` Disposition cells still read "Open"
  although both are Dean-confirmed RULEs that shipped** — *"the Disposition column needs a sweep
  against the branch, not spot fixes."*
- **Fourth argument for ballot-side, and a P/D correction to the row above.** With `Role` carried
  correctly the ballot-side sentinel needs **no P/D-specific mechanism** — the joint-commit math does
  it: the from-zero variant is picked for its real role, capped at 1 by C11, the binder prices it so
  `demand > 0`, and `deltaUtil = min` over roles propagates the one-replica ceiling **proportionally to
  the partner role**, yielding a matched 1P+1D step. Under the **anchor-only** shape, though, P/D is
  *worse* than the unmatched-step failure recorded above: every ballot entry abstains
  (`votesFromPickerState:522-535` reads `e.Result`, not the anchor) ⇒ `n = 0` for decode ⇒ `k = 0` ⇒
  **decode's `remaining` never decrements** while prefill keeps drawing against zero decode replicas
  until `!anyPositive` breaks. **The roles decouple completely** — correct "unmatched single step" to
  "anchor-only decouples P/D" wherever that framing was recorded, including in the bullet above.
- **Designer's §3 — a broader latent hazard, its finding, not carried by me.** The blank-`Role` bug is
  only one way to trip `initRoleState`. Verified at `:390-397`: the `else` branch synthesizes
  `domain.RoleBoth` into the same `roleSet` for **any** entry with `RoleCapacities == nil`. So the
  invariant is *"on a disaggregated model, any voting entry that does not report per-role
  `RoleCapacities` injects `both` into `roles`, and the first `pick("both")` kills the model's
  allocation."* `roles` is derived from the **ballot**; satisfiability is decided against the
  **anchor**; nothing reconciles them — the same ballot-vs-anchor split as `(D-a)`, but a *key set*
  rather than a value. **`a38d7b73` does not close this** — it fixes the one blank-`Role` source, not
  the derivation — so A36's rebase leaves the general hazard open for any future analyzer. Not
  reachable today (TA and saturation both report `RoleCapacities` on P/D; the QM analyzer is parked).
  The designer notes this is its `N7`, recorded only in the scale-**down** direction, and that the
  scale-**up** direction is strictly worse — *"not a skipped role, a dead model"* — and that the
  `break` must **not** become a skip, since it is load-bearing for joint-commit.
- **Errata, and why it matters more than the two numbers.** A sibling handoff
  (`plan__ta-anchor-da-sentinel-errata-two-line-refs`) corrects two refs the designer could no longer
  edit once I marked the first `.WIP`: `cost_aware_optimizer.go:103-107` → **`:104-108`**, and
  `votingResults` `:315-323` → **`:332-340`**. Drift under the coder's `2ae440e3`; code unchanged in
  both. **My independent read agrees with the corrected refs, not the originals** — that is the check
  that matters, and the substance survives the drift intact. Self-reported cause: citations written
  from an earlier `git show HEAD:` dump but labelled with a stale SHA — *"a dump is only valid for the
  SHA you read it at"* — the same tip-staleness class I had flagged at it in
  `designer__t1-1-not-shipped-and-pending-edits-exists`. Sender rule held correctly: it stopped
  editing at `.WIP` and sent a sibling rather than amending in place.
- **Shipped production-prose defect, same amendment.** `analyzer_helpers.go:185-188`'s premise is false
  (`ResultIsInformative` is any-variant per `:57-62`, so a healthy binder can be informative in
  aggregate yet price nothing for one variant — the expected shape for a never-measured from-zero
  variant), *and* the sentence is incoherent about its subject: "a binder omits a variant only when the
  binder itself is … not-binding". Conclusion holds; re-justify on `:189-192`. Note this is **new PR-2
  prose**, which per A10 is the first production `.go` doc comment surface this mission touches.
- Routing: who owns post-freeze Type-1. The internal code reviewer has declined the "Type-1 owner"
  label I used in two handoffs; that error is also now in shipped code (see B3).

## Provenance

Handoffs feeding this batch, all read at their stated states:
`plan__ta-anchor-c6e-two-adjacent-defects.md.WIP`, `plan__ta-anchor-c6f-w4-no-spend-is-false.md.WIP`,
`plan__ta-anchor-claim-pricing-verdict-and-c6e-gap.md.WIP`,
`plan__ta-anchor-c11-ceiling-nil-maxreplicas-escape.md.WIP` (Findings 42/43, pre-registered at
`470f4b8d` *before* the C11 diff existed); reviewer write-up
`planning/ta-anchor-dynamic-refresh-review.md` @ `ded9dc5f`. Branch tip when the A19/A6-widening rows
were added: `eb12089a`, with **six** source files modified and uncommitted (C11 in flight, touching
all three grant sites).

Later handoffs: `plan__ta-anchor-c10-import-cycle-blocker.md.WIP` (Finding 48) ·
`plan__ta-anchor-ceil-divergence-and-handoff-reconciliation.md.WIP` ·
`plan__ta-anchor-c10-shipped-supersedes-my-layering-rec.md.WIP` ·
`plan__ta-anchor-pr2-c9-sweep-inputs.md.WIP` (Findings 49/50 + the corrected ledger + the §4 ruling
request; review write-up commits `dba35c60`, `34f3feab`, `e498c5d6`). **Branch tip for every row added
from that last handoff: `79a590d6`** — twenty commits on base `075a208e`, C10 landed at `1a50b418`.
A22's tip correction is therefore now **two** commits further stale than A22 itself records
(`d9f3b97e` → `b6bb525c` → `1a50b418` → `79a590d6`); apply A22 against the tip at approval time, not
against any SHA written here.

Designer round on the `(D-a)` sentinel (A35–A37): `plan__ta-anchor-da-sentinel-belongs-on-the-ballot.md.WIP`,
`plan__ta-anchor-da-sentinel-errata-two-line-refs.md.WIP`,
`plan__ta-anchor-pd-fix-is-one-line-already-on-main.md.WIP`,
`plan__ta-anchor-designer-withdraws-t1-1-and-the-coder-accusation.md.WIP`. Reviewer follow-up (A38):
`plan__ta-anchor-pd-phantom-bucket-second-effect.md.WIP` — from **review**, not the designer;
`ask: fyi`, disposition explicitly left to me. Branch tip for A38: **`2ae440e3`** (C9b landed; C9c in
flight as an untracked `optimizer_invariant7_test.go`).

Two claims in this round were verified against the object and **corrected**, both in ways that matter:
the designer's `Role: vs.Role` is actually **`Role: st.role`** (persisted state, not the loop variable
— which voids shape 2's "clean no-op at rebase" safety case, since the text differs), and its "stale by
one" was actually **four** commits, meaning **C10 had already landed** when the plan text and CURRENT.md
still called §2e pending. The reviewer independently confirmed both. Treat every line ref and staleness
count arriving by handoff as a claim to check, not a fact to copy — the substance survived each time,
the coordinates did not.
