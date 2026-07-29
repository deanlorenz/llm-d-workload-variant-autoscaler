# WVA 0.9 Release Notes (DRAFT)

**Type:** planning artifact (release-note drafts) · **Status:** DRAFT — for discussion, NOT posted
**Author:** planner · **Date:** 2026-07-29 · **Companion:** [`ta-0.9-epic-issues.md`](ta-0.9-epic-issues.md)

> **No GitHub actions.** All text below is a *draft*. The assistant does not edit any PR body, does
> not create the GitHub Release, and posts nothing. A maintainer applies these. **Nothing authored
> by another contributor is edited** — other-author work is *described* in the Highlights (Part B)
> for completeness, but Part A drafts blocks **only for Dean's own PRs**.

---

## How release notes are actually produced in this repo (corrected)

I verified the mechanism directly. The earlier assumption that a PR's ` ```release-note ``` ` block
is "picked up automatically" is **false** — worth stating plainly so effort goes to the channel
that actually reaches users:

1. **There is no `.github/release.yml`** and no workflow/script that harvests `release-note`
   fenced blocks. Editing that block — on an **open** PR or a **merged** one — has **zero** effect
   on the generated notes. It is prose for human reviewers only.
2. **GitHub's auto-generated "What's Changed"** list is built from **PR _titles_** in the tag range
   (`v0.8.0..v0.9.0`). It is flat and uncategorized. → The only lever here is **PR title quality**
   (Part C), and titles are only worth touching on *your own* PRs.
3. **The curated `## Highlights`** section is **hand-written** by the release manager and
   *prepended* to the auto list at release time (v0.8.0 house style: Highlights → Key Features /
   Notable Bug Fixes, then Upgrade Steps & Deprecations, then Known Issues). **This is the only
   channel that carries a narrative, groups by theme, or surfaces 0.8 carry-forward work.**

**Consequences:**
- Retroactive 0.8 work will **not** reappear in the 0.9 auto-list (it's outside the tag range). It
  only surfaces via the hand-written Highlights (Part B). This is exactly why Dean wants the 0.8-era
  summary folded into 0.9.
- Keeping a clean `release-note` block in your own PRs is still worthwhile — it's the raw material
  the release manager pastes from, and it documents user impact on the PR itself — but treat it as
  **source material for Part B**, not as an auto-publish path.
- Part B below is therefore written **as if every note were picked up** — a complete, drop-in
  Highlights block the release manager can use verbatim.

---

## Part A — clean `release-note` blocks for **all of Dean's PRs**

Per decision: a clean `release-note` block for **every** Dean-authored PR in scope. **No
other-author PR appears here.** Reminder from the mechanism section — these blocks are *not*
auto-harvested; they are (a) accurate documentation on the PR body and (b) raw material for the
Part B Highlights. Open PRs (#1480, #1481) are the only ones where editing the block is a normal
pre-merge step; everything merged is optional back-fill that changes nothing downstream.

Where a change has genuinely no operator-visible effect, the honest block is `NONE` (k8s
convention) — noted as such rather than manufacturing a note.

### 0.9 — live / recently merged

**#1480 — TA model-level decode demand (OPEN)** — *keep / minor refine*
```release-note
The Throughput Analyzer now derives decode demand from the model-level request arrival rate
(arrival rate × average output length) instead of summing per-instance arrival rates. This fixes
cases where the analyzer was enabled and running but never triggered scale-up because per-pod
arrival rate failed to attribute to the model.
```

**#1481 — scale-down veto liveness gate (OPEN)** — *keep / minor refine*
```release-note
Scale-down decisions now ignore analyzers that have not produced a recent, informative result
(never reported, errored, or stale) — such an analyzer can no longer silently veto scale-down.
As a safety measure, if no analyzer is currently live for a model, scale-down is withheld.
```

**#1479 — analyzer participation opt-in (MERGED)** — *block already accurate; no edit needed*
```release-note
Analyzer participation is now opt-in: an analyzer runs only when explicitly enabled in its
configuration. An absent config entry no longer defaults to enabled. A startup log line now
reports when the ThroughputAnalyzer is not registered.
```

**#1478 — TA developer-guide fixes (MERGED, docs-only)** — *optional back-fill*
```release-note
Developer-guide corrections for the Throughput Analyzer: the example PromQL queries now use the
correct grouping labels, and stale references to removed internal components were removed. No
behavior change.
```

**#1318 — structured per-cycle log lines (MERGED)** — *optional back-fill*
```release-note
Scaling cycles now emit structured `analyzer-result` and `scaling-decision` log lines with a
per-decision reason, making it easier to trace which analyzer drove a scaling decision.
```

**PR E — gate observability (PLANNED, no PR yet)** — *draft for when you open it*
```release-note
When an analyzer is enabled by editing the saturation ConfigMap at runtime, the controller now
warns (log + Kubernetes Event) that the change takes effect only after a controller restart,
instead of silently ignoring it.
```

### 0.8 / pre-0.8 — foundation PRs (blocks for completeness; shipped in earlier releases)

These already shipped (v0.8.0 or earlier), so they are outside the 0.9 tag range and do not appear
in 0.9 auto-notes. Blocks are provided for PR-body hygiene and as source for the Part B
carry-forward summary — not for the 0.9 auto-list.

**#1250 — ThroughputAnalyzer (MERGED v0.8.0)** — the headline TA feature
```release-note
Adds the Throughput Analyzer: a proactive, model-driven scaling signal that estimates sustainable
decode-token supply from a fitted per-token latency model and measured KV capacity, and raises
scale-up before saturation is observed. Opt-in via the analyzer configuration.
```

**#1266 — multi-analyzer addendum (MERGED v0.8.0)** — small user-visible fix + docs
```release-note
Fixes a case where a saturation analyzer disabled in configuration could still influence scaling
decisions. No action required.
```

**#1225 — analyzer registry (MERGED v0.8.0)**
```release-note
NONE
```
<!-- internal: race-safe analyzer registration framework; no operator-visible behavior on its own -->

**#1228 — universal threshold post-step (MERGED v0.8.0)**
```release-note
NONE
```
<!-- internal: engine-owned threshold/aggregation post-step; no operator-visible behavior on its own -->

**#1246 — per-analyzer slice to optimizer + role/paired allocation (MERGED v0.8.0)**
```release-note
NONE
```
<!-- internal: pipeline plumbing + per-role capacity aggregation; visible behavior lands via the analyzers that use it -->

**#1051 — TA collector queries (MERGED pre-0.8)**
```release-note
NONE
```
<!-- internal: registers the PromQL queries the Throughput Analyzer consumes -->

**#1052 — TA state management (MERGED pre-0.8)**
```release-note
NONE
```
<!-- internal: workload-shape tracking / ITL observation window / sanity checks for the Throughput Analyzer -->

**#1444 — metric-based analyzer interface proposal (MERGED)** — proposal doc only
```release-note
NONE
```
<!-- docs/proposal only; no shipped behavior. Implementation tracked in #1455 -->

> **Other-author 0.9 PRs** (#1442, #1470, #1469, #1392, #1393, #1368, #1334, #1328, #1190, #1147,
> #1144, #1452, #1129): **not drafted here** — their authors own their PR bodies and titles. Their
> user-visible impact is captured in Part B for the release manager.

---

## Part B — comprehensive 0.9 Highlights (hand-written, all authors, drop-in)

*Written as a suggested **prepend** to the main 0.9 GitHub Release text, in the v0.8.0 house style.
Covers all contributors and folds the 0.8-era foundation forward (decision 4). Assumes #1480 and
#1481 merge into 0.9 — if either slips the cut, drop its line. Verify PR numbers/authors against the
final tag range before publishing.*

> **Disposition (Dean, 2026-07-29):** this Highlights block stays a **local draft** for now — **no
> in-repo doc yet**. Hold until code freeze; Dean will send it (e.g. via Slack to the release
> manager) at that point. Do not create `docs/CHANGELOG-v0.9.0.md`.

---

## Highlights

WVA 0.9 focuses on **making autoscaling decisions correct, safe, and observable** for disaggregated
(prefill/decode) serving. The multi-analyzer engine and the Throughput Analyzer introduced across
the 0.8 line are hardened for production, the P/D-aware optimizer gets several correctness fixes,
the default saturation analyzer moves to the token/capacity-based V2 model, and a broad set of new
metrics, logs, and alerts make scaling behavior visible.

### Key Features

- **Multi-analyzer scaling pipeline, matured.** WVA runs a pluggable set of analyzers behind one
  optimizer — scale **up** if any analyzer needs capacity, scale **down** only when all agree
  there's spare. The framework landed across 0.8 (race-safe analyzer registry, universal threshold
  post-step, per-analyzer results to the optimizer). 0.9 hardens the **analyzer lifecycle**:
  participation is now **opt-in** (an absent config entry no longer silently enables an analyzer),
  and scale-down is **liveness-gated** so a stalled, errored, or never-reporting analyzer can't veto
  it. *(0.8: #1225, #1228, #1246, #1266 · 0.9: #1479, #1481)*

- **Throughput Analyzer, production-hardened.** The Throughput Analyzer is a proactive scaling
  signal: it estimates sustainable decode-token supply from a fitted per-token latency model and
  measured KV capacity, and scales **before** saturation is observed. Introduced in 0.8, it now
  derives decode demand from the **model-level** arrival rate (arrival × average output length)
  rather than per-instance summation — fixing cases where it ran but never triggered scale-up — and
  its developer guide is brought in sync with the code. *(0.8: #1250 · 0.9: #1480, #1478)*

- **P/D role-aware optimizer.** For disaggregated serving, the optimizer aggregates capacity per
  role and allocates prefill/decode jointly (min-over-role utilization), rather than treating a
  model as one pool. The role-aware core landed in 0.8; 0.9 adds correctness fixes: waiting
  local-queue requests are charged by role, and instances are counted by DP-rank rather than raw
  pods. *(0.8: #1237, #1036, #994, #1246 · 0.9: #1470, #1469, #1392)*

- **V2 saturation analyzer is now the default** — a token/capacity-based model replacing the older
  percentage-based V1. See **Upgrade Steps** for the action required. *(#1442)*

- **Priority-weighted GPU rescale under contention** (Alpha, opt-in, off by default): when demand
  exceeds capacity, GPU budget is redistributed across a competition group by model priority and
  demand, never exceeding physical or quota limits. *(#1452)*

- **Observability across the scaling loop.** Structured per-cycle `analyzer-result` /
  `scaling-decision` log lines with a per-decision reason; new metrics for available GPUs,
  config-info, per-model metric freshness, and V2 saturation decisions; and shipped PrometheusRule
  alerting. *(#1318, #1147, #1144, #1190, #1368, #1393, #1328, #1334)*

### Notable Bug Fixes

- Throughput Analyzer never triggered scale-up when per-pod arrival rate didn't attribute to the
  model — now uses model-level demand. *(#1480)*
- A stalled / errored / stale analyzer could silently veto scale-down — now liveness-gated, with a
  no-live-analyzer safety floor that withholds scale-down. *(#1481)*
- Saturation V2 under-counted demand for long-generation workloads by not charging output tokens for
  waiting requests by P/D role. *(#1470)*
- Saturation V2 mis-scaled models with data-parallelism by counting pods instead of DP-rank
  instances. *(#1469)*
- Saturation V1 computed a missing utilization metric incorrectly. *(#1392)*
- Metrics fixes: pods-with-metrics gauge recorded incorrectly *(#1393)*; available-GPUs metric
  *(#1147)*; V2 saturation decision metrics not populated *(#1368)*; analyzer mode logged as a
  hardcoded value instead of the actual mode *(#1334)*.

### Upgrade Steps & Deprecations

- **⚠️ action required — default saturation analyzer is now V2 (#1442).** V2 is token/capacity-based
  and may produce different scaling decisions than V1 for the same workload. Review your dashboards
  and alert thresholds after upgrading. **To stay on V1**, remove the `analyzers:` section (and the
  V2-only `scaleUpThreshold` / `scaleDownBoundary` fields) from the `default` entry of the
  saturation ConfigMap.
- **Behavioral default change — analyzer participation is opt-in (#1479).** An absent config entry
  no longer enables an analyzer. Confirm your `analyzers:` configuration explicitly lists every
  analyzer you expect to run; check for the startup log line reporting whether the Throughput
  Analyzer is registered.
- **Saturation V2 demand accounting changed (#1470).** Output tokens are now charged for waiting
  requests; saturation-utilization values (and any alerts baselined on them) may shift for
  long-generation workloads — re-baseline if needed.

### Known Issues

- Enabling an analyzer by editing the saturation ConfigMap at runtime requires a controller restart
  to take effect; today this is silent. A warning (log + Kubernetes Event) is planned (PR E) but may
  not land in 0.9.
- Analyzers cannot yet return a per-analyzer status to suppress only spare-capacity or only
  required-capacity decisions; the pipeline currently combines binary up/down signals. Tracked in
  #1261.

---

## Part C — PR-title review (advisory; your own titles only)

The auto-generated "What's Changed" keys off **PR titles**, so a clear title is the one free win in
the flat list. **This is advisory and applies only to Dean's own PRs** — other-author titles are not
touched. Quick pass over the 0.9 Dean-authored PRs:

| PR | Current-title concern | Fine as-is? |
|---|---|---|
| #1480 | should read as user-facing ("Throughput Analyzer: …model-level demand") | verify before merge |
| #1481 | should read as user-facing ("…liveness-gate scale-down veto") | verify before merge |
| #1478 | docs-only; a `docs:` prefix reads well in the flat list | optional |
| #1479 | already user-facing (opt-in participation) | likely fine |

*No title is edited here. Confirm the two open PRs' titles read well to an operator before merge.*

---

## Part D — epic → PR → Highlights mapping

Epic IDs are from the companion bookkeeping doc.

| Epic child | PR | Author | 0.9? | Highlights home | Part A block? |
|---|---|---|---|---|---|
| A5 opt-in participation | #1479 | 🟢 | merged | Key Features + Upgrade Steps | yes (verbatim) |
| A6 veto liveness | #1481 | 🟢 | open | Key Features + Bug Fixes | yes |
| A7 V2 default | #1442 | ⚪ | merged | Key Features + Upgrade Steps ⚠️ | no (other author) |
| B7 model-level demand | #1480 | 🟢 | open | Key Features + Bug Fixes | yes |
| B8 dev-guide fixes | #1478 | 🟢 | merged | Key Features (TA line) | yes (optional) |
| — Highlights-only (sat-v2 waiting demand) | #1470 | ⚪ | merged | Bug Fixes + Upgrade Steps | no |
| — Highlights-only (DP-rank counting) | #1469 | ⚪ | merged | Bug Fixes | no |
| — Highlights-only (V1 util calc) | #1392 | ⚪ | merged | Bug Fixes | no |
| D1 structured logs | #1318 | 🟢 | merged | Key Features (observability) | yes (optional) |
| D2 alerting rules | #1328 | ⚪ | merged | Key Features (observability) | no |
| D3 freshness gauge | #1190 | ⚪ | merged | Key Features (observability) | no |
| — Highlights-only (V2 decision metrics) | #1368 | ⚪ | merged | Bug Fixes | no |
| — Highlights-only (pods-with-metrics) | #1393 | ⚪ | merged | Bug Fixes | no |
| — Highlights-only (available-GPUs) | #1147 | ⚪ | merged | Bug Fixes | no |
| — Highlights-only (config-info metrics) | #1144 | ⚪ | merged | Key Features (observability) | no |
| — Highlights-only (log actual mode) | #1334 | ⚪ | merged | Bug Fixes | no |
| A8 gate observability | PR E | 🟢 | planned | Known Issues | draft ready |
| (adjacent) priority rescale | #1452 | ⚪ | merged | Key Features (Alpha) | no |
| TA foundation | #1250 | 🟢 | **v0.8** | Key Features (carry-forward) | — |

---

## Resolved decisions (Dean, 2026-07-29)

1. **#1480 / #1481 → 0.9** — agreed. Their Highlights lines stand; drop only if a PR slips the cut.
2. **PR E (gate observability)** — scope confirmed **when it lands**; it will be **coded as a new
   PR** (A8). For now it stays under "Known Issues"; promote to a Bug Fix line once merged.
3. **Merged-PR back-fill blocks (#1478, #1479, #1318, and the 0.8 foundation PRs)** — Part A now
   carries a block for every Dean PR. Applying them to merged bodies is optional hygiene (changes
   nothing downstream); no PR-body edit is made without your explicit go-ahead.
4. **Highlights (Part B)** — **no in-repo doc.** Held as a local draft until code freeze; Dean will
   send it via Slack to the release manager. Do **not** create `docs/CHANGELOG-v0.9.0.md`.
