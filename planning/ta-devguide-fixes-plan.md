# TA Developer-Guide Fixes — Type 3 Task Plan (PR A, I-21/22/23)

> **Reading protocol:** Read the TOC first. Fetch only the sections you need
> via `Read <file> offset:<start-line> limit:<end-start+1>`. Never read the
> whole file up front.

**Type:** 3 (task plan) · **Branch:** `ta-devguide-fixes` off `main` (`f5b7577c`)
**Size:** doc-only (one dev-guide file) + one optional code-comment fix · **Reviewer session:** light

## TOC {#toc}

- [Overview {#overview}](#overview-overview) L19:38
- [Scope and non-goals {#scope}](#scope-and-non-goals-scope) L39:60
- [Commit 1 — I-21 PromQL groupby labels {#commit-1}](#commit-1--i-21-promql-groupby-labels-commit-1) L61:96
- [Commit 2 — I-22 remove itl_knowledge_store / tier-3 skeleton {#commit-2}](#commit-2--i-22-remove-itlknowledgestore--tier-3-skeleton-commit-2) L97:122
- [Commit 3 — I-23 nKV / ReplicaCount clarification {#commit-3}](#commit-3--i-23-nkv--replicacount-clarification-commit-3) L123:148
- [Pre-push checklist {#prepush}](#pre-push-checklist-prepush) L149:162

## Overview {#overview}

Three documentation-accuracy fixes to `docs/developer-guide/throughput-analyzer.md`,
all catching the doc up to code that already merged. No behavior change, no code logic.
Unblocks operators who copy PromQL from the doc and confuses no reviewer.

- **I-21** — the dev-guide PromQL examples say `by (pod)`, but the registered queries
  already use `by (instance, pod, llm_d_ai_variant)` (verified in
  `internal/collector/registration/throughput_analyzer.go:113,126,141,...`). The doc is
  stale; make it match the registered queries.
- **I-22** — Package Structure lists `itl_knowledge_store.go ... tier-3 skeleton (not
  yet wired)` (throughput-analyzer.md:230) and related "Tier 3 present" language, but the
  file was removed. Remove the stale references.
- **I-23** — Supply Estimation already documents `PendingReplicas` / anticipated supply
  (L520-522). The only residual is clarifying that `ReplicaCount_v` in the supply
  formula is the KV-derived ready count (`nKV`), per commit `34c9be9b`. Verify first;
  drop this commit if the doc already makes that clear.

[↑ TOC](#toc)

## Scope and non-goals {#scope}

**In scope:**
- `docs/developer-guide/throughput-analyzer.md` — the Metrics/PromQL section
  (L96-215), Package Structure (L219-233), ITL Model Calibration Tier-3 mentions
  (~L392+), and Supply Estimation (L427-530).
- *(Optional, Commit 1)* `internal/collector/registration/throughput_analyzer.go:48-50`
  — a stale code comment that still says "max by (pod): deduplication only" while the
  template at L126 uses `max by (instance, pod, llm_d_ai_variant)`. Comment-only fix,
  collision-free with the other 0.9 PRs. Drop it if you want to keep this PR pure-doc.

**Non-goals / coordination:**
- PR `ta-model-level-demand` (PR C) edits the **Demand Estimation** section (L443-501) of
  this same file, in parallel. **Do not edit that section** —
  leave it to PR C. Confine your Supply edits to L427-441 + the formula block. If the
  two PRs land out of order, the second rebases; keeping to disjoint sections makes that
  trivial.
- Do not change any registered PromQL query *string* — those are already correct. You
  are only fixing the doc's *copies* of them (and optionally one stale comment).

[↑ TOC](#toc)

## Commit 1 — I-21 PromQL groupby labels {#commit-1}

**Source of truth:** `internal/collector/registration/throughput_analyzer.go` templates.
Read `Read internal/collector/registration/throughput_analyzer.go offset:105 limit:80`
and use the *actual* `by (...)` clause from each `Template:` line — do not hardcode a
label list from memory, transcribe from the registered query.

**Fix in `docs/developer-guide/throughput-analyzer.md`:** replace `by (pod)` with the
registered groupby (`by (instance, pod, llm_d_ai_variant)`) at:
- L108 (`QueryGenerationTokenRate` example)
- L125 (`QueryKvUsageInstant` example)
- L141, L143 (the "Why `max by (pod)`" prose — update to `max by (instance, pod,
  llm_d_ai_variant)` and keep the dedup explanation accurate)
- L154 (`QueryRequestRate` example)
- L206-213 (the Query Design Decisions table `by (pod)` / `max by (pod)` cells)

Grep the file to be exhaustive: `git -C . grep -n "by (pod)" -- docs/developer-guide/throughput-analyzer.md`
— fix every hit. Keep the surrounding prose (rate windows, instant vs 1m/5m) intact.

**Optional companion (code comment):** in
`internal/collector/registration/throughput_analyzer.go:48-50`, update the
"max by (pod): deduplication only" comment to reference the actual
`max by (instance, pod, llm_d_ai_variant)` clause so the comment matches the template
below it.

**Commit message:**
```
docs(throughput-analyzer): fix stale PromQL groupby labels

The dev-guide query examples used `by (pod)`; the registered queries use
`by (instance, pod, llm_d_ai_variant)`. Sync the doc (and one stale comment)
to the registered templates.
```

[↑ TOC](#toc)

## Commit 2 — I-22 remove itl_knowledge_store / tier-3 skeleton {#commit-2}

The file `itl_knowledge_store.go` was removed but the dev guide still references it.

Fix in `docs/developer-guide/throughput-analyzer.md`:
- L230 — delete the `itl_knowledge_store.go ... tier-3 skeleton (not yet wired)` line
  from the Package Structure block.
- Read the Components (L234+) and ITL Model Calibration (L392+) sections and remove or
  correct any language that describes a Tier-3 knowledge store as present-but-unwired.
  Use "not implemented" phrasing for genuinely-absent behavior (Type 4 rule) rather than
  implying a skeleton exists in the package.

Be exhaustive: `git -C . grep -ni "knowledge store\|itl_knowledge_store\|tier.?3\|not yet wired" -- docs/developer-guide/throughput-analyzer.md`
and resolve every hit.

**Commit message:**
```
docs(throughput-analyzer): drop removed itl_knowledge_store references

The tier-3 knowledge-store file was removed; the Package Structure and
calibration sections still described it as a present-but-unwired skeleton.
Remove the stale references.
```

[↑ TOC](#toc)

## Commit 3 — I-23 nKV / ReplicaCount clarification {#commit-3}

**Verify first — this commit may be a no-op.** Read the Supply Estimation section
(`Read docs/developer-guide/throughput-analyzer.md offset:427 limit:105`). The
`PendingReplicas` / anticipated-supply note is already present (L520-522). The only
possible gap is that `ReplicaCount_v` in the supply formula is not explicitly the
KV-derived ready count (`nKV`) introduced by commit `34c9be9b`.

If the section does not already say so, add one clarifying sentence after the supply
formula block: that `ReplicaCount_v` is the KV-derived ready-replica count (`nKV`) —
the number of replicas actually reporting KV metrics — not a raw spec/status replica
count, and that this mirrors the saturation analyzer's `readyCount`.

If the doc already makes this clear, **skip this commit** and note in your status file
that I-23 was already satisfied.

**Commit message (only if not a no-op):**
```
docs(throughput-analyzer): clarify ReplicaCount is the KV-derived ready count

Note that ReplicaCount_v in the supply formula is nKV (replicas reporting KV
metrics), per 34c9be9b, not a raw replica count.
```

[↑ TOC](#toc)

## Pre-push checklist {#prepush}

Doc-only (plus at most one comment), so the code gates are quick:
1. `git branch --show-current` → `ta-devguide-fixes`.
2. `go build ./...` — clean (relevant only if you took the optional comment fix).
3. `make lint` — clean (comment fix only).
4. DCO sign-off on every commit (`git commit -s`).
5. Render-check the markdown (tables, code fences) — the PromQL table at L202-213 must
   still align after edits.

When done, write `plans/session/handoffs/review__ta-devguide-fixes-ready.md` and stop.
Do not push.

[↑ TOC](#toc)
