from: wva-saturation-cycle-log
session: r4-empty-reason-guard-done

## What changed

Commit 5acbb1fd on wva-saturation-cycle-log-r1 (wva-log-rewrite). All gates clean.
Tip: 5acbb1fd

## Changes

**Fix 1 — sat_v2 aggregateByVariant: `no-data` else branch**
Added `else { capacityLabel = "no-data" }` for the path where zero ready replicas,
no store record, and no compatible record are found. Previously Reason was silently
empty for newly deployed variants.

**Fix 2 — k2SourceLabel: `error` fallback**
Changed `return ""` to `return "error"` when K2Priority is not in {1,2,3,4}.
Unreachable today (callers always set 1–4) but traps future unlabelled code paths.

**Fix 3 — resolveITLModel failure: `T2-failed`**
Changed `return ITLModel{}, "", false` to `return ITLModel{}, "T2-failed", false`.
Caller does `continue` so this never appears on a VariantCapacity today, but
documents the contract.

**Fix 4 — cycle-log.md**
Added `no-data` and `error` rows to sat_v2 reason table; expanded TA section with
`T1-ols`/`T2-pinned`/`T2-default`/`T2-failed` table.

## Tests added
- sat_v2/analyzer_test.go: Reason=="no-data" when no data at all
- sat_v2/analyzer_test.go: k2SourceLabel returns "error" for K2Priority==0
- sat_v2/analyzer_test.go: k2SourceLabel returns "" for empty slice (invariant)
- throughput/analyzer_test.go: resolveITLModel returns "T2-failed" when all replicas idle

## Update CURRENT.md
Update PR Status row for wva-saturation-cycle-log:
- tip: 5acbb1fd on wva-saturation-cycle-log-r1 (wva-log-rewrite)
- status: awaiting Dean push to origin/wva-saturation-cycle-log
