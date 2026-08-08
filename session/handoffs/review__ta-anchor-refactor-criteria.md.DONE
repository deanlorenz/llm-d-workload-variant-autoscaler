reason: code-review-before-push
refs:
  - planning/ta-anchor-refactor-plan.md
  - planning/combined-analyzer-optimizer-design.md
  - planning/ta-anchor-goldens-review.md
  - ta-anchor-refactor/ (worktree — the branch under review)
note: PRE-STAGED PR-1 verification criteria (code not yet written — branch is at the goldens tip a2f49ccf with no PR-1 commits yet). The refactor-specific checklist is §13 of the plan: ship gate green AND compiling (withSatEntry per §11), the (a)/(b)/RC-SC split matching §2's tables, zero combine-arithmetic change, single code path / no name-checks, RC/SC read off the ballot, semantic-pivot grep resolved (§9), no plans-branch identifiers, deletion classification (§12), dev-guide reflects code, commit hygiene, and the standard pre-push gates. The design doc's Bottom-line invariants (esp. #7 byte-identity + its withSatEntry test-scaffolding note) is the authority behind the gate; ta-anchor-goldens-review.md Finding 2 is the withSatEntry compile dependency.
