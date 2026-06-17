from: collector-va-attribution
session: R1 fixup applied (error & log handling)

## What changed
Processed trigger `collector-va-attribution__plan-revised.md` (plan gained R1 section).
Applied all R1 changes in commit `85bd65de` (fixup on `7157c7d2`).

Changes:
- attribution.go: BuildLabelAttributor returns (Attributor, error); partial success
  on list failure; errors.Join; removed ctrl+logging imports, added errors+fmt.
- engine.go: error return handled in prepareModelData; logger.Error once per cycle;
  proceeds with partial attributor.
- replica_metrics.go: empty-vaName skip demoted Info → DEBUG; reworded.
- attribution_test.go: updated call sites; added TestBuildLabelAttributor_ListError
  (single-ns fail + partial multi-ns); uses interceptor.Funcs.
- build_instance_key_test.go: attributorWithPods helper updated for 2-value return.

All gates green (gofmt/test/lint/build).

## Update CURRENT.md
- Update the collector-va-attribution entry: 2 commits on branch (7157c7d2 + 85bd65de);
  R1 fixup applied; all gates green; still "in review" / WIP.
- The review trigger review__collector-va-attribution-ready.md is still active;
  the fixup is now part of the review scope.
