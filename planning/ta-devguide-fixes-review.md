# ta-devguide-fixes — Internal Review (Type 6)

**Status: FINAL** (Dean's decisions recorded 2026-07-26; see § Decisions)
**Reviewer:** internal reviewer (plan-vs-diff), 2026-07-26
**Branch:** `ta-devguide-fixes` @ `444cd4a3`, off `main@f5b7577c` (clean base, clean tree)
**Plan:** [`planning/ta-devguide-fixes-plan.md`](ta-devguide-fixes-plan.md)
**Scope:** doc-only (I-21/22/23) + one optional code-comment fix

---

## Verdict

**Clean — APPROVE.** All three commits are accurate against the actual code, exhaustive within
their scope, and stay clear of PR C's territory. No blocking findings. One pre-existing,
out-of-scope doc inaccuracy surfaced (NTH-1) — **Dean elected to fold it into this PR.**

## Decisions (Dean, 2026-07-26)

- **I-21** — accepted; all 8 groupby clauses verified against registered templates (full query
  table in this review). ✅
- **I-22** — accepted. Note: the tier-3 knowledge store is intended to **return in a future TA
  step** but is genuinely not implemented now; the "not implemented" rewrite is correct Type 4
  phrasing. (Future-intent captured here so it is not lost — DEFERRED, not DEPRECATED.)
- **I-23** — accepted as-is. Acknowledged as slightly detailed for a dev guide, but accurate;
  leave it.
- **NTH-1** — **FOLD INTO THIS PR.** Coder applies the one-line edit at
  `docs/developer-guide/throughput-analyzer.md:214` (see NTH-1 below). Routed to the coder
  directly via `session/handoffs/ta-devguide-fixes__review-findings.md`; planner sync deferred
  until after the coder applies it. Context: `ArrivalRate` is separately slated to move to
  model-level in PR C (`ta-model-level-demand`), which will likely rewrite this row again — Dean
  accepts the near-term double-touch.

---

## Commits reviewed

| SHA | Subject | Verdict |
|---|---|---|
| `d2d86c0f` | I-21 fix stale PromQL groupby labels | ✅ accurate & exhaustive |
| `570bd528` | I-22 drop removed itl_knowledge_store references | ✅ accurate & exhaustive |
| `444cd4a3` | I-23 clarify ReplicaCount is the KV-derived ready count | ✅ accurate (not a no-op) |

Files touched: `docs/developer-guide/throughput-analyzer.md` (doc) +
`internal/collector/registration/throughput_analyzer.go:48-50` (optional comment fix, taken).

---

## Verification against source of truth

### I-21 — PromQL groupby (`by (pod)` → `by (instance, pod, llm_d_ai_variant)`)

Every changed query verified against its **registered template**, not transcribed from memory:

- **Three direct examples** (`QueryGenerationTokenRate`, `QueryKvUsageInstant`,
  `QueryRequestRate`) match `internal/collector/registration/throughput_analyzer.go:113,126,141`.
- **Four table rows** whose templates live in *other* files (a real trap — the plan pointed
  only at `throughput_analyzer.go`) all verified:
  - `AvgITL` → `queueing_model.go:70` — `max by (instance, pod, llm_d_ai_variant)` ✓
  - `AvgOutputTokens` → `saturation.go:80` — `max by (instance, pod, llm_d_ai_variant)` ✓ (5m)
  - `AvgInputTokens` → `saturation.go:91` — `max by (instance, pod, llm_d_ai_variant)` ✓ (5m)
  - `PrefixCacheHitRate` → `saturation.go:103` — `max by (instance, pod, llm_d_ai_variant)` ✓ (5m)
- **Prose block** ("Why `max by (...)`") updated consistently; dedup explanation preserved.
- **Exhaustive:** `grep 'by (pod)'` on the doc → **zero** remaining hits.
- **Optional comment fix** (`throughput_analyzer.go:48-50`) taken; matches template at L126.
  Comment-only, collision-free with the other 0.9 PRs — build/lint cannot regress from it.
- **Table renders:** consistent 6-pipe columns after edit.

### I-22 — removed `itl_knowledge_store.go` / tier-3 skeleton

- File confirmed **absent** from the branch (`git ls-files` → not present).
- Package-structure line removed. `grep 'knowledge store|itl_knowledge_store|not yet wired'`
  → **zero** hits.
- Tier-3 paragraph reworded from "present-but-unwired skeleton" to **"not implemented"** —
  correct Type 4 phrasing for genuinely-absent behavior, and the rewrite accurately explains
  *why* (the `Analyze()` loop only iterates variants with active replica metrics).

### I-23 — `ReplicaCount_v = nKV` clarification (not skipped)

The plan flagged this as possibly a no-op; the coder added a clarifying sentence, which is
**justified and accurate**:

- `computeVariantSupply` (`analyzer.go:606-622`) counts only replicas with
  `TotalKvCapacityTokens > 0`, returns `perReplica = sum/n`, `nKV = n`. Booting KV=0 replicas
  are `continue`-skipped → matches the doc's "still-booting KV=0 replicas are excluded here."
- `ReplicaCount: nKV` at `analyzer.go:334`; the code comment (`analyzer.go:321-329`) already
  states "count of KV-capable replicas (nKV) … mirrors saturation_v2 (ReplicaCount =
  readyCount, PendingReplicas separate) … avoids double-counting booting replicas." The doc's
  new sentence transcribes this faithfully.

### Scope hygiene

- **No encroachment on PR C's Demand Estimation section** (L443-501). Both doc hunks end at/before
  L441 (supply totals) — disjoint from Demand, as the plan required. Out-of-order landing stays a
  trivial rebase.
- **No plans-branch identifiers** leaked into doc or comment (`grep` for `I-##`/`F#`/`A#`/`planning/`
  on added lines → none). Commit-message reference to code SHA `34c9be9b` is legitimate.

---

## Findings

### NTH-1 (pre-existing, out of scope) — ArrivalRate row omits `port`

The Query Design Decisions table row for `ArrivalRate` reads
`sum by (pod_name, namespace)`, but the registered `QuerySchedulerDispatchRate` template
(`queueing_model.go:43`) is `sum by (pod_name, port, namespace)` — the doc omits `port`.

- **Pre-existing:** the diff leaves this row unchanged; it is not introduced by this PR.
- **Out of I-21 scope:** the plan scoped I-21 to `by (pod)` hits; `by (pod_name, ...)` is not one,
  and the coder's `grep 'by (pod)'` correctly did not match it.
- **Impact:** cosmetic/doc-accuracy only; `port` is a dedup dimension on the primary λ_req query.
- **DECISION (Dean): fold into this PR.** Exact edit — the sole `pod_name` occurrence in the doc:

  ```diff
  - | `ArrivalRate` | `QuerySchedulerDispatchRate` | `sum by (pod_name, namespace)` | 1m rate | λ_req per pod (primary) |
  + | `ArrivalRate` | `QuerySchedulerDispatchRate` | `sum by (pod_name, port, namespace)` | 1m rate | λ_req per pod (primary) |
  ```

  Source of truth: `internal/collector/registration/queueing_model.go:43` —
  `sum by (pod_name, port, namespace)` (two-clause `or` with a `target_model_name=""` fallback;
  the table's single-groupby summary is fine, only `port` was missing). Coder may amend the
  I-21 commit `d2d86c0f` or add a small follow-up commit.

No other findings. No correctness, no doc-gap, no confirmed bugs.

---

## Gates

Coder reported all gates green (trigger note). Doc-only + one comment-only Go edit; `go build`
/ `make lint` cannot regress from a comment change. Not independently re-run by reviewer (heavy,
zero-risk change). Recommend the coder's reported green run stands.
