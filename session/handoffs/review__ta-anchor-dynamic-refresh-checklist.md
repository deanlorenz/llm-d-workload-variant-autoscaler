to: review
reason: code-review-before-push
refs:
  - planning/ta-anchor-dynamic-refresh-plan.md
  - planning/combined-analyzer-optimizer-design.md
  - planning/multi-analyzer-dataflow-map.md (§9, findings N1–N9)
note: PR-2 plan-vs-diff checklist (C1–C9). PR-2 is stacked/parallel on PR-1 (not merge-gated). HELD (.HOLD suffix) — arm (rename .HOLD→.md) only when the PR-2 coder signals push-ready. PR-2 code does not exist yet; this is the plan-keyed spine, to be reconciled against the actual diff at review time. Review PR-2's diff against PR-1's branch tip (stacked base), not against main.

---

## PR-2 (`ta-anchor-dynamic-refresh`) plan-vs-diff checklist

Keyed to the §1.1 commit map. Each row: what the diff must show + the dataflow-map §9 finding it
closes + the grep the coder should have run (plan §6). Verify **red-before-fix** on every bug commit
(the fixture failed pre-fix, passes after).

1. **C1 — binder tie-break (N2).** `bindingAnchor` no longer returns nil on >1 non-sat binder; instead
   sat-if-present, else lowest analyzer index. Fixture: two-binder tie asserts the deterministic pick,
   NOT a hold. Confirm all callers still nil-check (getter can still return nil on *no* binder / empty
   voting set). Grep: `bindingAnchor` doc-comment + caller comments updated.
2. **C2 — per-iteration refresh (§3).** Getter re-invoked per allocation iteration; the existing
   per-role `sortByCostEfficiencyAsc`-in-closure seam is reused (no NEW loop). Fixture: binding flips
   mid-water-fill → variant choice changes on the flip. `-race` run present.
3. **C3 — bug #2 `roleAggRemaining`.** Max in replica space (`max_i rd_i`), not raw mixed-unit RC.
   Two-vote MAX fixture red-before. Land before C4.
4. **C4 — bug #1 `allocateForModelPaired` decrement.** Per-analyzer `k·PRC_i` (or replica units), not
   `k·PRC_sat` uniformly. Two-vote allocation-count fixture red-before.
5. **C5 — bug #3 rescale + N3.** `roleDemandGPUs` / water-fill weight use combined
   `max_i ceil(demand_i/PRC_i)`; `TotalDemand` kept for observability only. **N3 nil-guard** added to
   `rescaleModelDecisions` (or compute-once-and-pass). Two-vote rescale fixture + nil-anchor path
   exercised.
6. **C6 — bug #5 fair-share, 3 lock-step sites.** `fairShareValue` (anchor combined replica-demand) +
   `fairShareCap` (GPUs→replicas convert) + `sortVariantsForScaleDown` (binding-PRC tie-break) move in
   ONE commit; units must not desync. Coordinate the `sortVariantsForScaleDown` edit with C7's N7.
7. **C7 — liveness (VG-up + N8 + N7).** `votingResults` gate `Enabled` → `Enabled && Live`;
   `bindingAnchor` still reads the **FULL** ballot (NOT `votingResults`). Sizing-fallback **dropped**
   (binder-unknown ⇒ PRC=0 abstain); PR-1 Test 2 rewritten (v2 110→0). N7 role-coverage default
   **abstain**. Confirm the invariant "non-nil anchor ⟹ non-empty voting set" holds and the nil-anchor
   hold path is exercised. Closes N1 + fallback-half of N5, plus the emergent-vs-enforced scale-up gap.
8. **C8 — notation cleanup (§2c).** `grep -rnE "\((a|b)\)" internal/ docs/developer-guide/` → **zero**
   hits in shipped comments/docs. Behavior byte-identical (goldens/tests green unchanged).
9. **C9 — dev-guide + goldens endgame.** Multi-vote dev-guide sections (§5) landed; the #1513 sat-only
   goldens **removed** in an explicit commit once the multi-vote suite covers the `[sat]`-only sub-case
   (Dean's relax/remove decision). Multi-vote goldens validated against hand-worked § anchor/§ bugs
   examples.

**Cross-cutting:** every semantic-pivot grep in plan §6 run and stale hits updated; full pre-push
battery (`make test` / `gofmt` / `make lint` / `go build` / DCO / branch verify) green after **every**
commit in an isolated worktree; no plans-branch tokens (`#1513`, `Nn`, `(a)/(b)`, `Fnn`) in shipped
code/comments/commit-messages (§4a).
