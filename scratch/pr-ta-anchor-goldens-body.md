## What

Adds a **characterization ("golden") test suite** that freezes the current scaling decisions of the
optimizer for the **saturation-analyzer-only** configuration — the shipped default, where saturation
is the sole active analyzer. It is a **test-only change**: one new file
(`internal/engines/pipeline/optimizer_characterization_test.go`), **zero production-code changes**.

The suite runs a matrix of hand-built, deterministic `ModelScalingRequest` fixtures through **both**
optimizers — `CostAwareOptimizer` and `GreedyByScoreOptimizer` — and asserts the resulting decision
**set** (keyed by variant name, order-insensitive) against literal expected values captured from
current `main` behavior:

- aggregated (role `both`) scale-up on demand-over-capacity, scale-down with cheapest-at-one
  protection, exact no-op, and a multi-variant cost tie-break;
- disaggregated prefill/decode paired scale-up and role-scoped scale-down;
- a namespace-quota-constrained scale-up (GreedyByScore only — `CostAwareOptimizer` documents that it
  ignores `ResourceConstraints`).

Each expected value carries an inline comment showing the arithmetic it was captured from (e.g.
`ceil(15000/10000)=2 additional → 4`), so the fixture is self-documenting and hand-checkable.

## Why

An upcoming refactor of the analyzer/optimizer pipeline will make the saturation analyzer cleanly
**disable-able** and allow a second (throughput) analyzer to participate in the vote. That refactor
restructures how per-variant capacity/sizing flows from the analyzers into the optimizer. Before
touching that plumbing, this suite pins the **current** single-analyzer decisions so the refactor can
prove — mechanically, in CI — that it does **not** change any decision on the default path.

This is intentionally a **characterization / freeze** test, not an assertion of desired behavior: the
expected values are literals captured from `main`, with **no auto-regenerate step**. A red test means
"a previously-frozen saturation-only decision moved." During the refactor that red is exactly the
alarm we want. A *deliberate* future change to optimizer behavior will also turn it red and requires
updating the affected literal by hand (re-capture + re-verify the arithmetic) — this is by design.

## Scope

- **Additive, test-only** — merges safely on its own; changes no runtime behavior.
- The suite is scoped to the pipeline refactor it guards. Once that refactor lands and broader
  multi-analyzer goldens exist, this saturation-only subset can be folded into them or relaxed; it is
  not intended as a permanent behavioral contract for the optimizer.
- Fixtures are synthetic and deterministic (no live metrics, no cluster access); every optimizer call
  is fed a freshly-built request set to avoid in-place result mutation between calls.

## Testing

- `go test ./internal/engines/pipeline/... -race -count=1` — PASS (green by construction against
  `main`); full package suite repeated 5× — stable, no map-iteration / unstable-sort flakiness.
- `gofmt -l`, `go build ./...`, `make lint` — clean.

```release-note
NONE
```
