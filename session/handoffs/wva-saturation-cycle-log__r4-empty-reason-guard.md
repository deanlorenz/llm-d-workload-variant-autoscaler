from: planner
session: wva-saturation-cycle-log R4 — empty-reason guards in sat_v2

## Your worktree

`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/wva-log-rewrite`
branch: `wva-saturation-cycle-log-r1`
current tip: `cc3d069f` (R3 complete; rebased on upstream/main@2b736049)

## Context

Audit of TA and sat_v2 found two paths where `Reason` can be `""` in sat_v2.
TA is clean — no empty reason is possible on any appended VariantCapacity.

## Two fixes, one commit

### Fix 1 — `aggregateByVariant` Branch 4 (live gap)

File: `internal/engines/analyzers/saturation_v2/analyzer.go`

When a variant has zero replicas AND no capacity store entry AND no compatible
cross-variant record, all three capacity branches are skipped. `capacityLabel`
remains `""` and the `VariantCapacity` is still appended unconditionally.
Because `Reason` uses `json:"reason,omitempty"`, the field is silently absent.

After the three-branch if/else-if/else-if block (after computing
`capacityLabel`), add before building `vc`:

```go
if capacityLabel == "" {
    capacityLabel = "unknown"
}
```

### Fix 2 — `k2SourceLabel` fallback (latent gap)

File: `internal/engines/analyzers/saturation_v2/analyzer.go`, `k2SourceLabel`

The function ends with `return ""` when the K2Priority is not in the label map.
K2Priority outside {1,2,3,4} is unreachable today, but the zero-value `int` (0)
is not in the map — any future `ReplicaCapacity` built without setting
`K2Priority` would silently omit the field.

Change the final return:

```go
// BEFORE
return ""

// AFTER
return "unknown"
```

### Fix 3 — `resolveITLModel` failure return (`throughput/analyzer.go` line 513)

The function currently returns `(ITLModel{}, "", false)` when both tiers fail.
The caller does `continue` so this label never reaches a `VariantCapacity` append
today — but the empty string is a weak contract. Since the failure is always at
Tier 2 (Tier 1 either failed or wasn't ready, Tier 2 failed), label it explicitly:

```go
// BEFORE
return ITLModel{}, "", false

// AFTER
return ITLModel{}, "T2-failed", false
```

### Tests

- Add a test asserting that a `VariantCapacity` produced by Branch 4 (zero
  replicas, no store, no compatible record) has `Reason == "unknown"`.
- Add a test asserting `k2SourceLabel([]ReplicaCapacity{{K2Priority: 0}})` →
  `"unknown"` (verifies the fallback fires for unmapped priorities).
- Add a test asserting `resolveITLModel` returns `"T2-failed"` when all
  replicas are idle (all `KvUsageInstant == 0`).

### Fix 4 — Update `docs/developer-guide/cycle-log.md` TA reason table

Add `T2-failed` to the throughput analyzer reason values table:

```
| `T2-failed`  | Both tiers failed — all replicas idle or no usable ITL signal; variant skipped this cycle |
```

Note: `T2-failed` is returned by `resolveITLModel` on failure, but the caller
currently skips the variant (`continue`) so this label never appears on an
appended `VariantCapacity`. Document it anyway so operators know the value is
possible if code paths change, and to make `resolveITLModel`'s contract explicit.

### Commit

```
git commit -s -m "sat_v2/throughput: eliminate empty Reason — unknown fallback, T2-failed on tier exhaustion"
```

### After

1. Run gates: `gofmt -l internal/`, `make test`, `make lint`, `go build ./...`
2. Write `plans/session/handoffs/plan__wva-log-r4-done.md`
3. Mark this handoff done:
   `mv plans/session/handoffs/wva-saturation-cycle-log__r4-empty-reason-guard.md \
       plans/session/handoffs/wva-saturation-cycle-log__r4-empty-reason-guard.md.DONE`
4. Do NOT push.
