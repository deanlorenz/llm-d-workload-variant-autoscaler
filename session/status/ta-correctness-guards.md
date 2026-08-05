last_update: 2026-07-30T00:00:00
state: in-progress
current_step: all 7 commits landed, all gates green; awaiting internal code review before push

## Branch
ta-correctness-guards at ta-correctness-guards/ ; tip 8bdd8b37 ; base main@f5261c8e (moving ref, not stacked on PR C #1480 — still OPEN as of every check this session)

## Recent commits
- 101e64ae — fix(throughput): reject NaN k in ObservationWindow.Add (I-3)
- 3b0b5cdf — fix(collector): wire real per-replica metric freshness (I-6)
- b9670047 — refactor(throughput): share one ITL-model validator across both fit tiers (I-2)
- d2618824 — fix(throughput): reject NaN/out-of-range KV usage in computeLocalDemand (I-4)
- b326000b — docs(throughput): document the shared ITL validator, freshness wiring, and local-demand guard
- ffcdae2f — fix(saturation): harden the liveness engine against a zero interval and zero AnalyzedAt (Commit 5: DR-1/DR-2/DR-3)
- 8bdd8b37 — docs(saturation): document the liveness engine's interval and AnalyzedAt fail-safes

Note: this branch's history was reworded twice via non-interactive `git reset --soft` + recommit
(never `rebase -i`, never `--amend` on a non-tip commit) — both times to fix a self-caught §4a
plans-branch-identifier leak in a commit message ("DR-1/DR-2/DR-3" then, separately, "I-2/I-4/I-6").
Each rework was confirmed tree-identical via `git diff <old-tip> <new-tip>` before and after. The
first rework was done after asking Dean for explicit go-ahead (AskUserQuestion); the second was
the same class of fix so I applied it directly per that same standing approval — flagging here in
case that inference should have been re-confirmed.

## Tests added
- observation_window_test.go: "rejects NaN k" (I-3)
- replica_metrics_test.go: TestCollectReplicaMetrics_Freshness (stale/fresh subtests) (I-6)
- itl_model_test.go: Describe("validITLModel") — accept + 5 reject-branch cases (I-2)
- analyzer_test.go: Describe("computeLocalDemand") — NaN KvUsageInstant, KvUsageInstant > 1, NaN-producing model (I-4)
- engine_v2_liveness_test.go: 3 new specs — zero-interval fallback (DR-1), zero-AnalyzedAt fail-safe on an informative result (DR-2), zero-AnalyzedAt on a non-informative result stays excluded (DR-2 contrast)

## Verified (final, post-rework)
- make test — PASS (full repo)
- gofmt -l internal cmd — clean
- make lint — 0 issues
- go build ./... — clean
- DCO — 7/7 commits signed
- §4a scan — widened beyond the plan's own pattern (added `\bDR-[0-9]\b`, `\bI-[0-9]\b`, `\bA[0-9]\b`, `\bB[0-9]\b`, `\bT[0-9]\b`) after catching two misses with the plan's original pattern; final scan clean across .go diff, .md diff, and all 7 commit messages

## Developer guide
- docs/developer-guide/throughput-analyzer.md — Tier 1/Tier 2 sections describe validITLModel; k*-based local demand section describes the NaN/out-of-range skip; new "Note on metric freshness" describing the collector-derived per-replica freshness rollup (detection-only).
- docs/developer-guide/multi-analyzer-pipeline.md — Liveness section now notes the 30s interval fallback (DR-1) and the zero-AnalyzedAt fail-safe (DR-2). Checked the existing "Demand-liveness telemetry (warn-only)" section per the plan's ev-shindin-note instruction — it was already correctly framed as observability-only, no correction needed.

## Judgment calls made (raised per the plan's explicit invitation, not silently chosen)
- I-4 k*>1 handling: skip (plan's recommended default), not clamp-to-1.
- I-6 freshness rollup basis: same 9 tracked timestamps as the existing trackMetricFreshness — verified first that all 9 corresponding queries are unconditionally issued for every model (not gated behind an optional feature), so "missing" is a genuine signal.
- I-2 Tier-2 test: did not add the plan's optional "resolveITLModel Tier-2 now rejects a previously-accepted degenerate A" case — confirmed algebraically infeasible (Tier-2 only accepts A>0 with both possible B sources always positive, so A*DefaultKSat+B>0 always holds).
- Commit 5 / DR-1 test: the plan's literal scenario ("a present Config returning 0 from OptimizationInterval()") is not constructible via config.NewTestConfig() (no setter, private field) and not reachable via config.Load() either (sanitizeOptimizationInterval always clamps below-minimum values up to the 15s default) — added config.SetOptimizationIntervalForTest in internal/config/config.go, following the existing SetLimiterForTest pattern, to make the test possible. This touches a file outside the plan's declared Commit-5 file scope (internal/engines/saturation/engine_v2.go only) — flagging since it's a plan/anchor gap, not a silent scope expansion.
- §4a self-correction (two rounds): my own commit messages used "DR-1/DR-2/DR-3" and, separately, "I-2/I-4/I-6" — plans-branch shorthand the plan's own grep pattern doesn't cover (it's shaped for F-numbers/plan-§ references, not issue-ID shorthand). Caught both on my own re-scan before declaring push-ready. Asked Dean before the first history rework (AskUserQuestion; approved "non-interactive rebase to fix it now"); applied the second occurrence directly under that same approval since it was the identical fix pattern — see the branch note above.

## Not done / known limitations
- No cross-package collector→sanity end-to-end test for I-6 (used the plan's own stated fallback "collector-level test suffices").
- PR C (#1480) still OPEN at every check during this session (checked before Commit 3, before Commit 4, and again at the very end) — no rebase was ever needed.

## Notes
review__ta-correctness-guards-ready.md is filed and open (corrected in place to reflect the final
7-commit state, since it hadn't been picked up yet). An earlier, premature plan__*.md handoff
(sent before I discovered the plan had grown a Commit 5) was already consumed by the sync session
before I could correct it — a follow-up plan__*.md handoff has been sent with the corrected final
state.

## Pre-rebase plan (2026-07-30, rebase onto upstream/main per review recommendation #1)

**Trigger:** internal review (`planning/ta-correctness-guards-review.md`) found PR C (#1480)
merged to upstream/main as `f9f04d81` during this session; branch is stale on `main@f5261c8e`.
Dean confirmed: rebase onto upstream/main.

**Scope correction vs. the plan's own C-overlap analysis:** the plan said "C never touches
`computeLocalDemand`/`resolveITLModel` bodies... conflict surface is small." True for those two
function *bodies*, but C's actual merged diff touches 8 files I also touched (not the ~2 the plan
anticipated) — `git show --stat f9f04d81` lists 15 files; 8 overlap with mine, including
`engine_v2.go`/`engine_v2_liveness_test.go` (the plan explicitly said C "never touches the
saturation engine" — no longer true; C's PR needed a same-repo conflict-resolution commit against
D's already-merged liveness work).

**Per-commit behavior-to-preserve + expected conflict:**
1. `101e64ae` (I-3, observation_window.go/_test.go) — no overlap with C. Expect clean.
2. `3b0b5cdf` (I-6, replica_metrics.go/_test.go) — preserve `classifyTimestamp`/`worstFreshnessStatus`
   helpers + assembly-site wiring + `TestCollectReplicaMetrics_Freshness`. `replica_metrics.go`:
   C only adds a new func at ~L1091+ (well after my ~L426-506/~L1023-1050) → expect clean.
   `replica_metrics_test.go`: C inserts a new test (`TestCollectReplicaMetrics_ArrivalRatePerPodRetained`)
   at the **same anchor** (right after `ThroughputKeyMerge`) where I inserted mine → **expect a real
   conflict**; resolve by keeping both new test functions intact.
3. `b9670047` (I-2, itl_model.go/_test.go clean + analyzer.go's `resolveITLModel` Tier-2 edit) —
   C's only analyzer.go hunk near `resolveITLModel` is actually inside `computeDemand`'s doc-comment
   (a different function) → expect clean.
4. `d2618824` (I-4, analyzer.go's `computeLocalDemand` guard) — C never touches this function's
   body/signature → expect clean in the .go file.
5. `b326000b` (docs, throughput-analyzer.md) — 3 edits: (a) freshness note ~L200, (b) Tier1/Tier2
   notes ~L402/416 — both clean, before C's first hunk at L448. (c) k*-local-demand skip note,
   appended after the old verbose "3. k*-based local" paragraph (~L486) — **C's rewrite deletes
   that whole paragraph**, renames the section, replaces it with a condensed one-liner → **expect a
   real conflict**; resolve by re-attaching my one-sentence skip-note to C's new condensed bullet
   under its new section name ("Per-Variant Demand (Introspection Only)").
6. `ffcdae2f` (Commit 5 code: engine_v2.go clean + engine_v2_liveness_test.go + config.go clean) —
   my 3 new `It(...)` specs are appended after C's 6 edited call sites → **likely no textual
   conflict**, but a **silent compile-break**: C added a trailing `arrivalRate float64` param to
   `runAnalyzersAndScore` and fixed its own 6 existing calls to pass `, 0`; my 3 new calls were
   written against the old 9-arg signature and will fail to compile until the same `, 0` is added.
7. `8bdd8b37` (docs, multi-analyzer-pipeline.md Liveness-section edit ~L250+) — C only touches the
   field table at L190 → expect clean.

**Post-rebase verification checklist:**
1. Per-file diff inventory: confirm every guard/helper is still present and semantically intact in
   each of the 7 commits' final diffs (not just "no conflict marker left behind").
2. Re-read each commit's post-rebase diff against its own message.
3. Manually fix the `engine_v2_liveness_test.go` compile-break (append `, 0` to my 3 new calls) —
   git will not flag this as a conflict.
4. Re-attach the k*-local-demand dev-guide note to C's renamed/condensed section.
5. Full gate re-run: gofmt, go build, make test, make lint, DCO, widened §4a scan.
6. Confirm both new collector tests (mine + C's) exist and pass; confirm all 3 new liveness specs
   compile and pass with corrected call arity.

## Rebase onto upstream/main — COMPLETE (2026-07-30)

Rebased onto `upstream/main` (`f9f04d81`, PR C #1480's merge) per the internal review's
recommendation #1. New tip: `abeb048f`. Old tip `8bdd8b37` is superseded.

**Conflicts resolved (both predicted in the pre-rebase plan above):**
1. `internal/collector/replica_metrics_test.go` — C and I both inserted a new test function at the
   same anchor (right after `ThroughputKeyMerge`). Kept both functions intact:
   `TestCollectReplicaMetrics_ArrivalRatePerPodRetained` (C) followed by
   `TestCollectReplicaMetrics_Freshness` (mine). Both pass.
2. `docs/developer-guide/throughput-analyzer.md` — C rewrote the "Demand Estimation" section
   (renamed "Priority Chain" → "Per-Variant Demand (Introspection Only)", condensed the k*-local
   bullet, deleting the paragraph my dev-guide note was attached to). Re-attached my one-sentence
   skip-note to C's new condensed "3. k\*-based local" bullet. My other two dev-guide edits
   (freshness note, Tier1/Tier2 validITLModel note) were in untouched regions — applied cleanly.

**Silent compile-break found and fixed (no textual conflict, so git didn't flag it):** C added a
trailing `arrivalRate float64` parameter to `runAnalyzersAndScore` and fixed its own 6 pre-existing
call sites in `engine_v2_liveness_test.go` (passing `0`). My 3 new specs (added in Commit 5) called
the function with the old 9-arg signature — this doesn't produce a merge conflict since my specs
are appended after C's edited lines, but `go vet`/`go test` fail to compile. Caught by running
`go vet ./...` immediately after the rebase completed (predicted in the pre-rebase plan; would not
have been caught by relying on "no conflict markers" alone). Fixed by appending `, 0` to all 3
calls, mirroring C's own fix. Folded into the rebased Commit 5 (`667c8b4a`) via the same
non-interactive `reset --soft` + recommit pattern used for the earlier §4a message fixes — same
standing approval, same class of fix (local-only, unpushed, no behavior change to the fix's own
target — it makes an already-intended call correct, doesn't add new coverage).

**Post-rebase verification (all re-run against the new base, matching the plan's checklist):**
- Per-file diff inventory: grepped every one of the 7 guards/helpers (I-3 NaN-k, I-6
  worstFreshnessStatus/classifyTimestamp, I-2 validITLModel call sites, I-4 NaN/>1 guard, DR-1
  interval clamp, DR-2 zero-AnalyzedAt fail-safe, DR-3 comment) — all present, unchanged.
- Semantic-pivot greps re-run against the new base (FreshnessStatus consumers, ITL validator
  stray-check scan, AnalyzedAt comment accuracy) — same clean results as before the rebase.
- gofmt clean, go build clean, go vet clean, `make test` full-repo PASS (targeted re-run of every
  touched suite individually also confirmed: collector 27/27, throughput 163/163, saturation
  93/93, config 98/98 — all including the newly-coexisting C+mine test pairs), `make lint` 0
  issues, DCO 7/7, widened §4a scan clean against the new base.

Branch is no longer stale. Ready for re-review (filed a fresh `review__ta-correctness-guards-ready.md`
trigger — the previous one was already consumed by the review that found the staleness in the
first place, and this rebase did real conflict resolution, not just a mechanical gate re-run, so
treating it as warranting re-review rather than assuming the "routine rebase-only push" exemption).

## Second rebase onto upstream/main — COMPLETE (2026-07-30)

Branch had been opened as **PR #1503** (reviewer+assignee ev-shindin) after the first rebase, then
went `CONFLICTING`/`DIRTY` when upstream merged **#1486** (ScalingPolicy Phase 1, `da58c0e0`).
Rebased again per the plan's new Pre-push step 0 (triggered by the `ta-correctness-guards__rebase-1486.md`
handoff). New tip: **`021b6f8d`**. Old tip `abeb048f` superseded. This is a **live, open PR
branch** — did not push; per the plan's own step 0, signalling review-ready only, planner
force-pushes #1503 with Dean's confirmation.

**One real conflict, exactly as the plan flagged:** `internal/config/config.go` — #1486 removed
`SetLimiterForTest`/`ReloadQuotaForTest` entirely (superseded by the new ConfigMap-driven,
`EffectiveLimiterMode()`-based limiter selection; confirmed zero remaining callers anywhere in the
new tree). My `SetOptimizationIntervalForTest` (added for the DR-1 test, unrelated to the limiter
schema) sat textually adjacent to those two functions. Resolved by keeping only
`SetOptimizationIntervalForTest` and dropping the other two — not a deletion I'm introducing, just
correctly not resurrecting code upstream had already removed for unrelated reasons. Trimmed the
function's doc comment's dangling "for the same reason as SetLimiterForTest" reference since that
function no longer exists.

**`engine_v2.go` — clean, as predicted from a pre-check:** #1486's only change there
(`aw.Name ==` → `aw.EffectiveType() ==` in `scoreForAnalyzer`/`resolveThresholds`/`effectiveEnabled`)
is in functions this branch never touches (this branch's Commit 5 only touches
`updateLivenessAndSetLive` and `pruneLastGoodAnalysis`). Auto-merged with no conflict. Verified none
of this branch's own code does an `aw.Name ==` comparison needing the same `EffectiveType()` fix
(the plan's explicit sanity-check item) — confirmed clean, N/A.

**Note on IDE diagnostics during resolution:** mid-rebase, the IDE's live gopls diagnostics flagged
many unrelated files (`main.go`, `limiter_factory.go`, `inventory_gate.go`, `validation.go`,
`loader.go` — none touched by this branch) with `undefined: cfg.LimiterMode` etc. `git status`
showed only `config.go` as unmerged at the time; a fresh `go build ./...` and `go vet ./...`
immediately after `git rebase --continue` both came back clean — the diagnostics were stale gopls
cache lagging behind the large rebase, not real errors. Treated `go build`/`go vet` as the
authoritative signal rather than the IDE panel, per usual practice, but noting this explicitly
since it looked alarming for a moment.

**Post-rebase verification (full checklist re-run against the new base):**
- Per-file diff inventory: all 7 guards/helpers + `SetOptimizationIntervalForTest` confirmed
  present and unchanged via grep.
- Semantic-pivot greps (FreshnessStatus consumers, ITL validator stray-check scan) re-run clean.
- gofmt clean, `go build`/`go vet` clean, `make test` full-repo PASS, `make lint` 0 issues, DCO 7/7,
  widened §4a scan clean against the new base.

Filed a fresh `review__ta-correctness-guards-ready.md` (this rebase also did real conflict
resolution, not a mechanical replay) and a `plan__*.md` handoff. Marked the
`ta-correctness-guards__rebase-1486.md` trigger `.DONE`.
