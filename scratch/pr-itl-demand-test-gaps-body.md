## What

Adds unit-test coverage for several already-shipped defensive guards in the ThroughputAnalyzer
that were flagged as untested during the #1503 review. **Test-only — no production code changes.**

During the #1503 review, @ev-shindin noted three untested guard branches (and left them as optional
follow-ups). This PR covers those three plus one adjacent supply-path gap found while adding them:

- **`validITLModel` — `Inf B` rejection.** Symmetric with the already-tested `Inf A` case; the
  `math.IsInf(b, 0)` branch was previously uncovered.
- **Tier-2 fit rejection in `resolveITLModel`.** A single below-baseline replica produces a
  negative slope that `validITLModel` rejects, exercising the `n>0 && sumK2>0` fit-then-reject
  path — distinct from the existing "all replicas idle" (`n==0`) test, which never reaches the fit.
- **`computeLocalDemand` skip guards.** Non-positive `TotalKvCapacityTokens`, and a finite (non-NaN)
  negative predicted ITL — distinct from the existing NaN-coefficient case.
- **`computeVariantSupply` direct coverage.** The same non-positive-capacity guard on the supply
  path, previously only exercised indirectly through an `Analyze`-level test. Adds a direct
  aggregate case plus the skip case.

Each new spec was verified to be non-vacuous (it fails if the guard is removed) and to reach its
intended branch by control-flow + arithmetic, not just a green suite. No behavior changed; no new
test failed against current code, so no latent bug was uncovered.

## Testing

- `make test` — PASS (throughput package coverage 93.2% → 93.4%)
- `make lint` — 0 issues
- `go test ./internal/engines/analyzers/throughput/... -race` — PASS
- `go build ./...` — clean · `gofmt` — clean

## Notes

The matching capacity/ITL guards in `checkVariantGPSMismatch` (a diagnostic-only path) remain a
known coverage gap, intentionally left for a separate follow-up.

```release-note
NONE
```
