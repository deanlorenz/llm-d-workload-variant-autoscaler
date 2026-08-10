# ta-anchor-refactor-v2 — Coder quick-checklist (TOC-indexed)

**Type:** 3 companion (verification aid) · **For:** the `ta-anchor-refactor-v2` coder
**Plan:** [`ta-anchor-refactor-v2-plan.md`](ta-anchor-refactor-v2-plan.md) (Status: FINAL)

Purpose: verify the load-bearing gates **without re-reading the whole plan**. Each item cites the
plan section + line range — pull just that span with
`Read planning/ta-anchor-refactor-v2-plan.md offset:<start> limit:<end−start+1>`. This adds no new
scope: everything here is already in the FINAL plan; the checklist only indexes it.

---

- [ ] **1. Ship gate — goldens green after EVERY commit** (decision-SET identity, keyed by `VariantName`).
  → §4 · `offset:283 limit:16`
- [ ] **2. Commit 1** — every ballot entry tagged `Enabled` (alongside existing `Live`); uniform
  generation loop; **QM untouched in C1**.
  → §5 · `offset:299 limit:80`
- [ ] **3. Commit 2** — `bindingAnchor` derives a **fresh** anchor by per-`VariantName` merge:
  **(a) identity from sat, (b) sizing from the binding analyzer**.
  → §6·2a `offset:389 limit:42` + §2 merge `offset:187 limit:39`
- [ ] **4. (b)-fallback is ENABLEMENT-GATED** — sat's (b) only when `satNR.Enabled`; under
  `[TA]`-only a missing/never-seen variant gets **PRC = 0**, *not* sat's (b).
  → §2 table `offset:187 limit:39` + §6 step 3 (within §6·2a `offset:389 limit:42`)
- [ ] **5. Fresh literals only** — never mutate `satNR.Result` / `binding.Result` or their slices
  (test 3); fallback fires **before** the prune; `votingResults` is a **separate** slice.
  → §2 ordering `offset:187 limit:39` + §6·2b `offset:431 limit:18`
- [ ] **6. Repoint sites correctly** — SELECTION → `anchor`; COMBINE-BALLOT →
  `votingResults(req.AnalyzerResults)`.
  → §6·2c `offset:449 limit:20` + §6·2d `offset:469 limit:14` (inventory §10 `offset:878 limit:89`)
- [ ] **7. Commit 3** — QM → **explicit error** (`refuseQueueingModel`) at the dispatch **case body**,
  **not** gated on the `analyzers:` list; liveness = **do-nothing**.
  → §7·7a `offset:547 limit:40` + §7·7b `offset:587 limit:16`
- [ ] **8. Commit 4** — TA emits **PRC-only** (reuse `lastPerReplicaSupply`; no `lastCost`/sentinel);
  emit only for **previously-live-now-zero**; **never-seen → emit nothing**.
  → §7b `offset:618 limit:125`
- [ ] **9. Tests** — Test 9 fixture **all-live** (`[sat,TA]` bit-identity); Test 7 = **throughput
  analyzer** layer; Test 10 = **pipeline cost-picker** layer.
  → §6·2f `offset:503 limit:38` + §7b tests `offset:717 limit:26`
- [ ] **10. Wrap-up gates** — §9 **semantic-pivot grep (MANDATORY)**: `saturationEntry`→`bindingAnchor`
  rename + stale dev-guide strings; C5 dev-guide **named passages**; §12 deferrals **classified**
  (QM = DEFERRED).
  → §9 `offset:851 limit:27` + §8 `offset:808 limit:43` + §12 `offset:1000 limit:47`

---

*Standard gates still apply (not repeated here): `make test`, `gofmt -l`, `make lint`, `go build ./...`,
DCO sign-off, CWD+branch re-verify before every commit — per CODER-CONVENTIONS §0/§3.*
