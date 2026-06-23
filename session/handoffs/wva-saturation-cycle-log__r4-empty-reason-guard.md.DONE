from: planner
session: wva-saturation-cycle-log R4 — eliminate empty Reason from sat_v2 and TA

## Your worktree

`/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/wva-log-rewrite`
branch: `wva-saturation-cycle-log-r1`
current tip: `cc3d069f` (R3 complete; rebased on upstream/main@2b736049)

## Context

Audit of TA and sat_v2 found paths that can produce `Reason == ""`. Fix each
source directly with a meaningful label — do NOT add a blanket
`if capacityLabel == "" { capacityLabel = "..." }` guard. Each condition has
its own distinct meaning.

TA: only one empty path, at `resolveITLModel` failure (fix below).
Sat_v2: two gaps — Branch 4 (live) and `k2SourceLabel` fallback (latent).

## Fixes — one commit

### Fix 1 — `aggregateByVariant` Branch 4 (sat_v2 — live gap)

File: `internal/engines/analyzers/saturation_v2/analyzer.go`

When a variant has zero ready replicas AND no capacity store entry AND no
compatible cross-variant record, all three branches are skipped and
`capacityLabel` remains `""`. The entry is still appended with
`PerReplicaCapacity: 0`, and `Reason` is silently absent from the log
(`json:"reason,omitempty"`).

This is a normal operational state: e.g. a newly deployed variant with no
traffic history and no peers. Label it `"no-data"`.

Add an explicit else clause to the three-branch block:

```go
if len(replicas) > 0 {
    ...
    capacityLabel = k2SourceLabel(replicas)
} else if rec := a.capacityStore.Get(...); rec != nil && rec.EffectiveCapacity > 0 {
    ...
    capacityLabel = "P0-store"
} else if rec := a.lookupCompatibleCapacity(...); rec != nil {
    ...
    capacityLabel = "P0-store"
} else {
    capacityLabel = "no-data"   // ADD THIS ELSE BRANCH
}
```

### Fix 2 — `k2SourceLabel` fallback (sat_v2 — latent gap)

File: `internal/engines/analyzers/saturation_v2/analyzer.go`, `k2SourceLabel`

The final `return ""` fires when K2Priority is not in {1,2,3,4}. This is
unreachable today (all callers set 1–4), but the `int` zero-value (0) is not
in the map — a future `ReplicaCapacity` built without setting `K2Priority`
would silently omit the field.

Change the final return to `"error"` — this is an unreachable code path whose
only trigger is a programming mistake:

```go
// BEFORE
return ""

// AFTER
return "error"
```

### Fix 3 — `resolveITLModel` failure return (TA — line 513)

File: `internal/engines/analyzers/throughput/analyzer.go`

The failure return `(ITLModel{}, "", false)` is reached when both tiers fail
(Tier 1 failed or wasn't ready, AND Tier 2 failed). The caller does `continue`
so this label never reaches a `VariantCapacity` append today — but `""` is a
weak contract. Since the failure is always at Tier 2, label it explicitly:

```go
// BEFORE
return ITLModel{}, "", false

// AFTER
return ITLModel{}, "T2-failed", false
```

### Fix 4 — Update `docs/developer-guide/cycle-log.md` reason-values section

**Sat_v2 table** — add two rows:
```
| `no-data`  | No ready replicas, no stored record, no compatible variant — capacity is 0 this cycle (normal for newly deployed variants) |
| `error`    | K2 priority not in known set — indicates an unlabelled code path; should not occur in normal operation |
```

**TA table** — add one row:
```
| `T2-failed` | Both tiers failed — all replicas idle or no usable ITL signal; variant skipped this cycle |
```

Note on `T2-failed`: `resolveITLModel` returns this when `ok=false`; the caller
does `continue` so it never appears on an appended `VariantCapacity` today.
Documented for contract completeness.

## Tests

- Sat_v2 Branch 4: assert that a variant with zero replicas, no store record,
  and no compatible record produces `Reason == "no-data"`.
- `k2SourceLabel`: assert `k2SourceLabel([]ReplicaCapacity{{K2Priority: 0}})` →
  `"error"`.
- TA: assert `resolveITLModel` returns `(_, "T2-failed", false)` when all
  replicas are idle (`KvUsageInstant == 0` for all).

## Commit

```
git commit -s -m "sat_v2/throughput: eliminate empty Reason — no-data/error/T2-failed labels"
```

## After

1. Run gates: `gofmt -l internal/`, `make test`, `make lint`, `go build ./...`
2. Write `plans/session/handoffs/plan__wva-log-r4-done.md`
3. Mark this handoff done:
   `mv plans/session/handoffs/wva-saturation-cycle-log__r4-empty-reason-guard.md \
       plans/session/handoffs/wva-saturation-cycle-log__r4-empty-reason-guard.md.DONE`
4. Do NOT push.
