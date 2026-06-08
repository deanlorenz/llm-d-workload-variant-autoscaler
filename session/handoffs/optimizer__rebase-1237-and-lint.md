reason: re-read plan
refs:
  - planning/multi-analyzer-optimizer-plan.md
note: REVISED — the resolution principle changed after a design discussion. Do NOT drop #1237's scaleDownVariantSet; REUSE it (generalized) as the shared shedding primitive. Plan § "CURRENT NEXT ACTION" now has the exact target code for scaleDownVariantSet (injected maxRemovable/onRemove, pre-sorted), sortVariantsForScaleDown (Cost-desc → Σ Score_i·PRC_i asc → name), scaleDownRoleIterated (if-gate, single pass), variantsForRole (exact-match, RoleBoth), plus deletions (findCheapestVariant, old sortByCostDesc) and the 3 lint fixes. Follow it literally — it encodes decisions you weren't part of; do not infer scope. No plans/planning writes. No push (PR #1246 open).
