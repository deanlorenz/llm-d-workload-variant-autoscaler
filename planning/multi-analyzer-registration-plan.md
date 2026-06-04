# Multi-Analyzer Registration — Plan

> **Status: ACTIVE** — PR [#1225](https://github.com/llm-d/llm-d-workload-variant-autoscaler/pull/1225)
> open, ev-shindin assigned. 5 commits on `main`@`eb327cc2`; tip `6339e495`. Awaiting CI
> + reviewer feedback.
>
> **Cross-cutting design context:** see [`multi-analyzer-design.md`](multi-analyzer-design.md)
> (overview, mission, architectural decisions, alternatives considered for the
> multi-analyzer pipeline as a whole).

---

## Scope

Item 3 of the design split (see `multi-analyzer-design.md` § Tasks): **race-safe
analyzer registry on the engine**. Concretely:

- Engine carries a registration-ordered list of analyzers; `NewEngine`
  pre-registers saturation V2 at slot 0; external analyzers register via a public
  `RegisterAnalyzer` method.
- `StartOptimizeLoop` snapshots the registry to an immutable slice before launching
  the optimize goroutine; subsequent `RegisterAnalyzer` calls fail (per-misuse
  rejection) so the "before Start" contract is enforced rather than only documented.
- Each cycle the engine iterates the snapshot and invokes `Analyze` on every
  registered non-saturation analyzer; results are calibrated with a per-analyzer
  threshold post-step (delegated to PR #1228) and discarded on this branch
  (consumed by the multi-analyzer-optimizer PR).
- Registered analyzers run in isolation — errors and panics are recovered per
  call so a faulty plugin can't bring down the optimize goroutine.

Out of scope on this branch (delegated to siblings): combine deletion + per-analyzer
slice → optimizers (Item 1, multi-analyzer-optimizer); universal threshold post-step
applied to every analyzer's result (Item 2, PR #1228).

---

## Branch state

- **Branch:** `multi-analyzer-registration` in worktree `multi-analyzer-registration/`.
- **Base:** `main`@`eb327cc2`.
- **Tip:** `6339e495` (5 commits).
- **Origin:** pushed to `deanlorenz:multi-analyzer-registration`; PR #1225 OPEN
  upstream against `llm-d/llm-d-workload-variant-autoscaler:main`.

---

## Commits landed

1. **`3a0dff86`** — `engines/saturation: multi-analyzer registration plumbing`
   - `analyzerEntry { name, analyzer }` type; `analyzers []analyzerEntry`
     field on `Engine`; `NewEngine` pre-registers saturation V2 at slot 0.
   - Original `RegisterAnalyzer(name, a)` (panic-on-misuse) — superseded by
     commits 4–5 (see API evolution below).
   - `runAnalyzersAndScore` builds `AnalyzerInput` and iterates the registry
     post-saturation; calls `Analyze` on each non-saturation entry; logs and
     recovers errors/panics per call; results discarded.
   - Tests T1, T2, T3, T6, T7, T8 in new `engine_register_test.go`.

2. **`6b4f2b8f`** — `docs: document analyzer registration mechanism`
   - Adds "V2 Analyzer Parameters" + "Multi-Analyzer Registration" sections to
     `docs/developer-guide/saturation-scaling-config.md`.
   - `docs/user-guide/saturation-analyzer.md` is N/A on current main (entire
     `user-guide/` directory removed upstream — flagged in commit body).

3. **`66001d47`** — `engines/saturation: race-safe analyzer registration via snapshot`
   - Adds `analyzersSnapshot []analyzerEntry` and `started bool` fields on `Engine`.
   - `StartOptimizeLoop` copies registry to snapshot and flips `started` BEFORE
     `recordActiveOptimizer()` / `SetConfigOptimizationInterval` /
     `executor.Start(ctx)` sequence.
   - `runRegisteredAnalyzers` iteration source switches from `e.analyzers` to
     `e.analyzersSnapshot`.
   - Tests T4, T5, T9 added; T6/T7/T8 updated to populate `analyzersSnapshot`
     directly so they exercise the new read path.

4. **`dd9834d2`** — `engines/saturation: address ev-shindin review — rename + log level`
   - Reviewer (ev-shindin) asked for `Must`-prefix per Go convention for
     panic-on-misuse. Renamed `RegisterAnalyzer` → `MustRegisterAnalyzer`.
   - Downgraded plugin-failure logging in `runRegisteredAnalyzer` from `Error`
     to `V(DEBUG).Info`: a persistently failing/panicking plugin is non-fatal,
     and Error-logging every cycle (default 30 s) would spam operator logs.
   - Inline comment added in `runAnalyzersAndScore` noting that non-saturation
     analyzers receive the saturation-adjusted config (threshold-overrides
     leak); harmless on this branch, tracked for cleanup on PR #1228.

5. **`6339e495`** — `engines/saturation: RegisterAnalyzer returns error instead of panic`
   - Per reviewer preference (continued thread): replace both panic conditions
     with error returns. Reverts the `Must`-prefix rename from commit 4.
   - Final API: `func (e *Engine) RegisterAnalyzer(name string, a interfaces.Analyzer) error`
     returning a clear message on misuse (post-Start, duplicate name).

### API evolution summary

| Commit | API shape | Misuse semantics |
|---|---|---|
| 3a0dff86 | `RegisterAnalyzer(name, a)` | panic on duplicate name |
| 66001d47 | `RegisterAnalyzer(name, a)` | + panic if `started` (post-StartOptimizeLoop) |
| dd9834d2 | `MustRegisterAnalyzer(name, a)` | rename per `Must`-prefix convention |
| **6339e495** (current) | `RegisterAnalyzer(name, a) error` | error-return, no panic |

---

## Test plan T1–T10

| # | Test | Layer | Status |
|---|---|---|---|
| T1 | `NewEngine` pre-registers saturation at slot 0 under `interfaces.SaturationAnalyzerName` | construction | ✓ ([engine_register_test.go](internal/engines/saturation/engine_register_test.go)) |
| T2 | `RegisterAnalyzer` appends in registration order | registry | ✓ |
| T3 | `RegisterAnalyzer` with duplicate name returns error (was: panics) | registry | ✓ — semantics updated to error-return in `6339e495` |
| T4 | `RegisterAnalyzer` after `StartOptimizeLoop` returns error (was: panics with `"RegisterAnalyzer called after StartOptimizeLoop"`) | registry | ✓ — semantics updated |
| T5 | `StartOptimizeLoop` builds `analyzersSnapshot` matching `analyzers` and flips `started` | snapshot | ✓ |
| T6 | One cycle calls `Analyze` on every registered NON-saturation analyzer exactly once, in registration order | loop | ✓ |
| T7 | A registered analyzer that returns an error does not abort the cycle | loop | ✓ |
| T8 | A registered analyzer that panics — engine recovers, logs at `V(DEBUG).Info`, continues | loop | ✓ |
| T9 | `go test -race` clean: snapshot reader doesn't race with concurrent post-Start `RegisterAnalyzer` attempts | race | ✓ |
| T10 | Saturation result flows to optimizer regardless of what other analyzers return | wiring | Verified by code inspection (saturation runs via `runV2AnalysisOnly` outside the registered-analyzer loop; non-saturation results discarded). Easy to add as a follow-up test if a reviewer asks. |

---

## Verified

- `gofmt -l ./internal/... ./pkg/... ./cmd/...` — empty output.
- `go vet ./...` — clean.
- `go build ./...` — clean.
- `make test` — all packages pass.
- `go test -race ./internal/engines/saturation/...` — clean (~7 s).
- DCO sign-off on all 5 commits.

---

## Coordination

- **Base for downstream PRs.** PR #1228 (`multi-analyzer-threshold`) is stacked on
  this branch; the optimizer branch (`multi-analyzer-optimizer`) cross-rebases
  onto threshold's tip. Force-push of this branch shifts both downstream branches'
  rebase targets.
- **Stacked PR diff.** PR #1228's diff against `main` includes this PR's 5 commits
  + threshold's commits until #1225 merges and #1228 rebases onto main.
- **PR #1113 (engine-multi-analyzer)** is **superseded** by this PR. To be closed
  by Dean after coordinating with ev-shindin.
- **TA PR-5 (TA3 wiring)** uses `engine.RegisterAnalyzer(...)`. After `6339e495`'s
  API shift to error-return, TA3's call site must be updated to handle the
  returned error (a one-line change in `cmd/main.go`). Tracked on TA-PR5-plan.md.

---

## Open items

- **Late-register message + snapshot mechanism in dev-guide** (deferred from
  initial review). The dev-guide explains the must-call-before-`StartOptimizeLoop`
  contract but doesn't surface the exact error string (`"RegisterAnalyzer:
  called after StartOptimizeLoop"`) or the `analyzersSnapshot` mechanism that
  enforces it. Skipped initially to avoid burning CI on a doc-only change while
  the PR was in review; fold into whichever reviewer-feedback edit lands first.
- **API change call-site in TA3** (`cmd/main.go`): TA3's wiring needs to handle
  the error return from `RegisterAnalyzer`. Tracked on TA-PR5-plan.md.

---

## References

- [`multi-analyzer-design.md`](multi-analyzer-design.md) — cross-cutting design,
  mission, architecture, alternatives considered, future direction.
- [`multi-analyzer-coder-rules.md`](multi-analyzer-coder-rules.md) — coder agent
  rules governing the three multi-analyzer branches.
- [`PR1113-review.md`](PR1113-review.md) — historical review of the original
  PR #1113 that decided the 3-PR split. PR #1113 itself is superseded; this
  PR (#1225) implements the **Item 3** subset.
- [`ENGINE-multi-analyzer-plan.md`](ENGINE-multi-analyzer-plan.md) — SUPERSEDED
  predecessor plan (single-PR scope before the split). Carries the original
  formal design including the rejected combine algorithm.
