# ta-registration-safety — Review

**Status:** FINAL — no blocking findings; 2 follow-ups (F1, F2) assigned to coder via planner handoff
**Scope:** `75f529b9`, `30bca98e`, `44af05c6` on branch `ta-registration-safety` (off
`main@f5b7577c`). Reviewed against
[`planning/ta-registration-safety-plan.md`](ta-registration-safety-plan.md). All commits match
the plan's declared commit boundaries (1 = veto fix, 2 = startup log, 3 = dev-guide doc).

**Gates:** coder's trigger (`review__ta-registration-safety-ready.md`) reports `make test`,
`gofmt`, `make lint`, `go build ./...` all green. Independently spot-checked before this doc was
written: `gofmt -l` clean, `go build ./...` clean, `go test ./internal/engines/saturation/...
./cmd/...` passes. DCO — all 3 commits carry `Signed-off-by: Dean H Lorenz <dean@il.ibm.com>`.
Did not re-run `make lint` or the full suite (coder already confirmed; not re-verified here per
Dean's direction not to duplicate that work).

---

## Verified correct

1. **Saturation exemption invariant holds.** `runAnalyzersAndScore` (engine_v2.go:127-156)
   appends the saturation result unconditionally before the loop, and the loop's first check is
   `if entry.name == domain.SaturationAnalyzerName { continue }` — this `continue` is reached
   before `effectiveEnabled` is ever called for saturation. The opt-in flip cannot gate saturation
   off, matching the plan's explicit safety requirement and the coder's own verification note in
   the handoff.

2. **`effectiveEnabled` opt-in fix is exactly the plan's diff.** Fall-through changed from
   `return true` to `return false`; three explicit-entry branches (`Enabled` nil/true/false)
   unchanged. Doc comment restates the new contract accurately.

3. **Test-fixture collateral fix (item 2 in the coder's handoff) is correct and minimal.** The
   call-ordering test in `engine_v2_test.go` now opts in `throughput` and `slo` via explicit
   `Analyzers` entries — restoring the test's original intent (exercise call-count/order) rather
   than accidentally re-testing the opt-in gate. Same pattern in the two `engine_v2_population_test.go`
   fixtures (`spy` given an explicit unscored entry). No test was weakened to pass; each fix adds
   exactly the config entry the changed default now requires.

4. **`cmd/main.go` commit is doc/log-only, no logic change.** `throughputAnalyzerEnabled` itself
   is untouched — confirmed by reading the function; only the doc comment and the new `else`
   branch changed. The new `TestThroughputAnalyzerEnabled` table test (5 cases: absent, absent-
   with-other-analyzers, enabled-explicit, enabled-nil-default, disabled-explicit) covers this
   function's existing behavior; it was not previously tested (I-12), so this is a net-new
   coverage win independent of the opt-in fix.

5. **Semantic-pivot grep step was executed correctly and completely.** Re-ran the same grep
   (`effectiveEnabled|opt-in|defaults to enabled|absent.*enabled|unconfigured analyzer` over
   `internal/engines/saturation/`, `docs/developer-guide/`, `cmd/`). Every hit inside this PR's
   write scope reads correctly as opt-in. The one hit that still says the old thing —
   `docs/developer-guide/throughput-analyzer.md:28` — is the exact hit the coder already flagged
   as out-of-scope in the handoff (item 1). No missed hits.

6. **Dev-guide addition (`multi-analyzer-pipeline.md`) matches the plan's required content**:
   states the opt-in rule, the veto hazard it prevents, and the saturation exemption, without any
   forward-looking references to `wva-analyzer-lifecycle` (Type 4 rule respected).

---

## Findings

None blocking. Two items worth a note, both already surfaced by the coder — this review just
confirms them independently rather than adding new scope.

### F1 — `throughput-analyzer.md` stale note (coder's item 1) — confirmed real, correctly deferred

Lines 27-29 of `docs/developer-guide/throughput-analyzer.md` still say the startup gate is "a
stopgap" pending "the per-cycle consumption gate (effectiveEnabled opt-in fix)," and that landing
it "will remove the need for a restart." Both claims are now wrong: the opt-in fix landed on this
branch, and it does not touch registration-freeze/restart behavior at all — that's
`wva-analyzer-lifecycle` scope, a non-goal here. The coder's call to leave this alone (plan names
only `multi-analyzer-pipeline.md` for dev-guide changes; grep-step instructions say hand
out-of-scope hits back rather than edit across scope) is the correct read of this PR's stated
scope. Recommend Dean pick one of: fold a 4th small commit into this PR (cheap — it's a 3-line
edit), or track as a follow-up. Either way it should land before/alongside this PR's merge, since
after merge the doc is *actively* wrong rather than merely dated.

### F2 — missing test case for `effectiveEnabled`: other analyzers configured, target absent — ACTION: add test

The plan's Commit 1 section (`ta-registration-safety-plan.md:117`) says line 76 of
`engine_v2_population_test.go` has an assertion for "some other analyzer present, throughput
absent → BeTrue()" that needs flipping. That exact spec is not present in the file, on `main` or
on this branch — the `effectiveEnabled` `Describe` block has only 4 specs (absent-from-empty-
config, nil-default, explicit-false, explicit-true). The coder correctly did not fabricate a spec
to match the plan's stale description, and the fall-through path itself is already exercised by
the empty-config spec (same `return false` line, whether the loop runs zero iterations or several
non-matching ones).

That said, the *scenario* — `Analyzers` non-empty but containing no entry for the analyzer under
test — is a real, currently-untested path for `effectiveEnabled` specifically (as opposed to
`cmd/main.go`'s `throughputAnalyzerEnabled`, which the coder's new `TestThroughputAnalyzerEnabled`
table already covers for exactly this scenario). Dean's call: any untested path should be tested.
**Action for planner → coder:** add one spec to `engine_v2_population_test.go`'s `effectiveEnabled`
`Describe` block — `Analyzers: []config.AnalyzerScoreConfig{{Name: "other"}}`, expect
`effectiveEnabled("throughput", cfg)` to be `BeFalse()`. Small, additive, no risk to existing
specs; re-run `go test ./internal/engines/saturation/...` after adding.

### F3 — deferred coverage gap (coder's item 3) — accept as documented, no action

No natural fixture in `internal/engines/saturation/` exercises `needsScaleDownForRole`
end-to-end (it lives in `internal/engines/pipeline/`), so the "unconfigured analyzer doesn't veto
scale-down" claim is only covered indirectly (via `effectiveEnabled` unit tests + the
config-bridge tests confirming exclusion from the result slice). The plan explicitly allowed
documenting this gap rather than forcing a cross-package fixture. Accepted — matches PR D
(`ta-veto-liveness`) scope more naturally than this one; no new coverage requested here.

---

## Verdict

**No blocking findings.** The implementation matches the plan's stated commit boundaries exactly,
the one behavioral-contract change (`effectiveEnabled` fall-through) is verified safe against the
saturation exemption, collateral test fixes are minimal and correct, and the semantic-pivot grep
was run and fully accounted for. Dean confirmed 2026-07-26: code is OK to proceed once two
coder-actionable follow-ups land — **F1** (fold or track the `throughput-analyzer.md` stale-note
fix) and **F2** (add the missing "other analyzers present, target absent" spec to
`effectiveEnabled`'s test block). Both handed to the planner via
`plan__ta-registration-safety-review-outcome.md` for routing to the coder. F3 remains accepted
as documented, no action.

## Update — F1 and F2 landed, both confirmed correct

Two follow-up commits added on top of the previously-reviewed three (tip now `7374be55`):

- **`7b69a561`** (F2) — adds exactly the proposed spec to `effectiveEnabled`'s `Describe` block:
  `Analyzers: [{Name: "other"}]` → `effectiveEnabled("throughput", cfg)` is `BeFalse()`. Matches
  the review's proposed fix verbatim; no existing specs touched.
- **`7374be55`** (F1) — rewrites the `throughput-analyzer.md` restart-requirement note to
  describe the startup registration gate and the per-cycle `effectiveEnabled` gate as
  independent, with no forward-looking claim about either changing (Type 4 rule respected), and
  cross-links to `multi-analyzer-pipeline.md`. Re-ran the stale-wording grep
  (`stopgap|will remove the need for a restart`) across `docs/`, `internal/`, `cmd/` — zero hits;
  the note is fully corrected with no other latent references.

Both commits are DCO-signed. Coder's trigger reports all gates re-verified green (`make test`,
`gofmt`, `make lint`, `go build ./...`); not independently re-run here (Dean's direction: don't
duplicate gate runs already confirmed by the coder for a small, additive diff).

**Final verdict: ready to push.** No outstanding findings — F1 and F2 closed, F3 remains an
accepted, documented gap (not this PR's scope).
