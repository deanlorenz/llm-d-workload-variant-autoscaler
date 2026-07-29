# 0.9 Epics & Issue Bookkeeping (DRAFT)

**Type:** planning artifact (issue/epic drafts) · **Status:** DRAFT — for discussion, NOT posted to GitHub
**Author:** planner · **Date:** 2026-07-29 · **Companion:** [`ta-0.9-release-notes.md`](ta-0.9-release-notes.md)

> **No GitHub actions.** Every epic/issue below is a *draft* for a maintainer to file, label, and
> milestone. Nothing here is posted, labeled, milestoned, reopened, or assigned on GitHub by the
> assistant.
>
> **Dedup rule (Dean, 2026-07-29):** *any PR that is already linked to an issue keeps that issue —
> no duplicate is filed.* The "Issue" column below records the existing issue where one exists
> (verified via each PR's closing-issue reference on 2026-07-29); only rows marked **NEW** lack a
> tracker.
>
> **Other-author work:** PRs/issues by other contributors are listed for the map only. The
> assistant does not edit, retitle, or relabel them. Where an other-author PR has **no** existing
> issue, filing a fresh tracker for it is flagged as a **decision for Dean** (§ Issue ledger) rather
> than prescribed — arguably the PR author or a maintainer owns that, not us.
>
> **Other-author merged bug fixes are excluded (Dean, 2026-07-29):** minor, already merged, and not
> ours to track — so they are **not** listed as epic children here. Excluded: #1470, #1469, #1392
> (Epic C) and #1368, #1393, #1147, #1144, #1334 (Epic D). They **remain in the release Highlights**
> (companion doc, Part B) so the release still credits them. Substantive other-author *features* and
> *breaking changes* (#1442, #1237, #1036, #994, #1328, #1190) are kept.

---

## Purpose

Bookkeeping so the community can see the full body of analyzer / optimizer / observability work,
**0.8 (retroactive) and 0.9**, organized under four epics. Each child row carries its implementing
PR, its existing issue (if any), author, and merge status.

Per Dean (2026-07-29):
1. **Epic D (observability)** — file a **new** observability epic. **Do not assign shuynh2017.**
2. **Epics A and C** — file as **new, separate** epics.
3. **Epic B (TA)** — adopt the **existing** epic **#1005**; add children.
4. **0.8-era work** — represent as a **summary** folded into 0.9. No need to retro-milestone each
   minor closed 0.8 issue to the v0.9.0 milestone (#7).
5. **Add release notes to all of Dean's PRs**; add the issues and reference the PRs; **no duplicate
   issue** for a PR already tracked.

---

## Labeling conventions (from the live repo taxonomy)

Verified against `gh label list` on 2026-07-29. Use these exact labels — do **not** invent
`kind/epic`, `area/analyzer`, or `area/optimizer` (they don't exist).

- **Epic issue:** `epic` + `enhancement` + `triage/accepted` + one `area/*` (+ `release/v0.9`).
  Mirrors existing epics #1005 / #911 / #1000 (`enhancement, epic, triage/accepted`).
- **Feature:** `enhancement` + `area/*` (+ `release/v0.9`).
- **Bug:** `bug` + `area/*` (+ `release/v0.9`).
- **Docs:** `documentation` + `area/*`.
- **Area labels that exist:** `area/engine`, `area/observability`, `area/collector`, `area/api`,
  `area/config`, `area/coordinator`, `area/inventory`, `area/installation`, `area/ci`,
  `area/benchmark`. **Analyzer + optimizer work → `area/engine`.** Observability → `area/observability`.
- **0.9 tracking:** label **`release/v0.9`** *and* the v0.9.0 milestone (#7) are both live. Apply
  the label to 0.9-scope issues; milestone is optional per decision 4.
- **Triage:** `labeler.yaml` auto-adds **`needs-triage`** to every new issue; a maintainer swaps it
  for `triage/accepted`. New drafts therefore *start* `needs-triage` — that's expected.
- **Priority (optional):** only `priority/medium` / `priority/low` exist (no `priority/high`).

**Author key:** 🟢 = deanlorenz (yours), ⚪ = other author (reference only — do not edit their PR/issue).

**Issue-column key:** `#NNNN(state)` = existing tracker → link, no new · **NEW** = no tracker, file
one · **NEW?** = other-author PR with no tracker → decision for Dean · `→#NNNN` = tracked by that
epic/tracking issue.

---

## Epic map at a glance

| Epic | GitHub | Area | 0.8 foundation | 0.9 deltas | Backlog |
|---|---|---|---|---|---|
| **A** Multi-analyzer pipeline & lifecycle | **new** (ancestor #408 closed) | engine | #1225 #1228 #1246 #1266 | #1479 #1481 #1442 (+PR E) | #1261 #1455/#1444 |
| **B** ThroughputAnalyzer | **#1005** (open; add children) | engine | #1051 #1052 #1250 | #1480 #1478 | gauges, supply models, #901 #1202 #1475 |
| **C** Optimizer & P/D allocation math | **new** | engine | #1237 #1036 #994 #1246 | *(others' merged bug fixes excluded)* | #1476 #1454 #1325 #1352 #1256 #1251 #426 |
| **D** Observability | **new** (successor to closed #911) | observability | — | #1318 #1328 #1190 | #1466 #1272 #1273 #1459 #1484 |

Cross-cutting / owned by other epics (cross-reference, don't absorb): rescale #1452 → issue **#1447**;
quota limiter #1129 → epic **#1000** (via issue #1002); rebalancer → epic **#1348**.

---

## Epic A — Multi-analyzer pipeline & analyzer lifecycle  *(NEW epic — **FILED [#1492](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1492)**, 2026-07-29)*

**Suggested title:** `[Epic] Multi-analyzer pipeline: pluggable analyzers feeding one optimizer`
**Labels:** `epic`, `enhancement`, `area/engine`, `triage/accepted`, `release/v0.9`
**Ancestor:** #408 "Pluggable Analyzer Architecture for Optimization Loop" (CLOSED) — link as prior art.

**Body (draft):**
> WVA's optimization loop runs a pluggable set of analyzers behind a single optimizer. Each analyzer
> publishes its own supply/demand estimate; the engine applies a universal threshold post-step and
> combines decisions safely: scale **up** if *any* analyzer wants more (OR), scale **down** only if
> *all* agree there is spare (AND). This epic covers the pipeline framework (race-safe registry,
> engine-owned RC/SC post-step, per-analyzer slice to the optimizer) and the analyzer **lifecycle**
> (opt-in participation, liveness-gated veto, and the future per-analyzer status contract). The
> ThroughputAnalyzer is the first non-saturation consumer; the saturation analyzer runs on the same rails.

| ID | Child (suggested title) | Class | Status | PR | Author | Issue | Labels |
|---|---|---|---|---|---|---|---|
| A1 | engine: race-safe analyzer registry | infra | SHIPPED v0.8.0 | #1225 | 🟢 | **NEW** | enhancement, area/engine |
| A2 | engine: universal threshold post-step + aggregation helpers | infra | SHIPPED v0.8.0 | #1228 | 🟢 | **NEW** | enhancement, area/engine |
| A3 | engine: per-analyzer result slice to optimizer; remove combine | infra | SHIPPED v0.8.0 | #1246 | 🟢 | **NEW** | enhancement, area/engine |
| A4 | saturation: multi-analyzer addendum — disabled-analyzer fix + dev guide | infra | SHIPPED v0.8.0 | #1266 | 🟢 | **NEW** | enhancement, area/engine |
| A5 | engine: analyzer participation opt-in + non-registration startup log | infra | MERGED 0.9 | #1479 | 🟢 | **[#1495](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1495)** ✅ | bug, area/engine, release/v0.9 |
| A6 | engine: gate the scale-down veto on per-analyzer liveness | infra | OPEN 0.9 | #1481 | 🟢 | **[#1496](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1496)** ✅ | bug, area/engine, release/v0.9 |
| A7 | saturation: default to V2 (token/capacity) analyzer *(breaking)* | infra | MERGED 0.9 | #1442 | ⚪ | **NOT FILED** (other author — Dean alerts directly) | enhancement, area/engine, release/v0.9 |
| A8 | engine: warn when runtime ConfigMap analyzer-enable needs a restart | infra | PLANNED 0.9 | PR E | 🟢 | **[#1497](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1497)** ✅ | bug, area/engine, area/observability |
| A9 | analyzer: per-analyzer status return (SuppressSC/SuppressRC) | infra | BACKLOG | — | 🟢 | **#1261(OPEN)** | enhancement, area/engine |
| A10 | analyzer: metric-based (demand, target) interface | infra | BACKLOG (proposal #1444 merged) | #1444 | 🟢 | **#1455(OPEN)** | enhancement, area/engine |

*Notes.* A5 = config-absence half of internal I-16/I-5; A8 = runtime-edit half (new PR, decision 3).
A7 is ⚪ other-author with no tracker → **NEW?** decision. A9/A10 already have homes (#1261/#1455).

---

## Epic B — ThroughputAnalyzer  *(EXISTING epic #1005 — add children)*

**GitHub:** [#1005](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1005) (OPEN;
`enhancement, epic, triage/accepted`). Adopt as-is; add `release/v0.9`; add the children below.

> The ThroughputAnalyzer is a proactive, model-driven scaling signal. It estimates sustainable
> decode-token supply from a fitted ITL(k)=A·k+B latency model and measured KV capacity, compares it
> to decode-token demand, and raises scale-up *before* saturation is observed. Opt-in; plugs into the
> multi-analyzer pipeline (epic A).

| ID | Child (suggested title) | Class | Status | PR | Author | Issue | Labels |
|---|---|---|---|---|---|---|---|
| B1 | collector: register ThroughputAnalyzer PromQL queries | TA | SHIPPED (pre-0.8) | #1051 | 🟢 | **NEW** | enhancement, area/collector |
| B2 | throughput: workload-shape tracking, ITL window, sanity checks | TA | SHIPPED (pre-0.8) | #1052 | 🟢 | **NEW** | enhancement, area/engine |
| B3–B6 | throughput: ITL(k) calibration + decode supply/demand + GPS verify + engine wiring | TA | SHIPPED v0.8.0 | #1250 | 🟢 | **NEW** (or checklist under #1005) | enhancement, area/engine |
| B7 | throughput: compute decode demand from model-level arrival rate | TA | OPEN 0.9 | #1480 | 🟢 | **NEW** | bug, area/engine, release/v0.9 |
| B8 | docs(throughput-analyzer): sync developer guide to merged code | TA | MERGED 0.9 | #1478 | 🟢 | **NEW** | documentation, area/engine, release/v0.9 |
| B9 | throughput: Prometheus gauges for ITL calibration state | TA | BACKLOG | — | 🟢 | **NEW** (internal I-8) | enhancement, area/observability |
| B10 | throughput: persistent ITL knowledge store + RPS/prefill supply models | TA | BACKLOG | — | 🟢 | **NEW** (internal I-18/19/20) | enhancement, area/engine |

*Related existing open issues to link under #1005 (do not re-file):* #901 (vLLM experiments &
metrics for TA), #1202 (router EPP metrics-rename impact), #1475 (pending-replica capacity topology).

*Note.* B3–B6 all shipped inside the single squash-merge #1250 — either one closed child issue with a
four-item checklist, or four closed children, all referencing #1250. Legibility only.

---

## Epic C — Optimizer & P/D allocation math  *(NEW epic — **FILED [#1493](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1493)**, 2026-07-29)*

**Suggested title:** `[Epic] P/D-aware optimizer: role capacity aggregation & paired allocation`
**Labels:** `epic`, `enhancement`, `area/engine`, `triage/accepted`, `release/v0.9`

> For disaggregated (prefill/decode) serving, the optimizer reasons per **role** rather than as one
> pool: aggregates capacity per role (`RoleCapacities`), allocates jointly via min-over-role
> utilization, distributes queue demand across roles, and counts DP-rank instances rather than pods.
> General disaggregated-serving infrastructure; TA and the saturation analyzer both feed it.

| ID | Child (suggested title) | Class | Status | PR | Author | Issue | Labels |
|---|---|---|---|---|---|---|---|
| C1 | optimizer: role-aware scale-down for disaggregated models | infra | SHIPPED v0.8.0 | #1237 | ⚪ | **NEW?** | enhancement, area/engine |
| C2 | saturation(v1): P/D role-aware grouping path | infra | SHIPPED (pre-0.8) | #1036 | ⚪ | **#1031(CLOSED)** | enhancement, area/engine |
| C3 | saturation(v1): default thresholds + partial override | infra | SHIPPED (pre-0.8) | #994 | ⚪ | **#993(CLOSED)** | enhancement, area/engine |
| C4 | optimizer: per-role capacity aggregation + joint paired allocation | infra | SHIPPED v0.8.0 | #1246 | 🟢 | **NEW** (shares PR with A3) | enhancement, area/engine |

*Excluded (Dean 2026-07-29):* other-author merged bug fixes #1470 (→#1456), #1469 (→#1467), #1392 —
credited in release Highlights, not tracked here.

*Cross-reference (owned elsewhere — link, don't absorb):* priority-weighted rescale #1452 → issue
**#1447**; quota-based limiter #1129 → epic **#1000** (via #1002).

*Backlog / open math issues to link:* #1476, #1454, #1325, #1352, #1256, #1251, #1213/#1212/#1211,
#426. Most are ⚪ other-author — reference only.

---

## Epic D — Observability  *(NEW epic; successor to closed #911 — **FILED [#1494](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1494)**, 2026-07-29)*

**Suggested title:** `[Epic] WVA observability: scaling-decision visibility (metrics, logs, alerts)`
**Labels:** `epic`, `enhancement`, `area/observability`, `triage/accepted`, `release/v0.9`
**Assignee:** *leave unassigned / TBD* — **do not assign shuynh2017** (per Dean).
**Predecessor:** #911 "Improve WVA Observability" (CLOSED) — link as the completed prior epic.

> Make WVA's scaling decisions observable end-to-end: structured per-cycle logs naming the analyzer
> and reason behind each decision, decision/capacity metrics, freshness and config gauges, and
> alerting rules. 0.9 successor to the closed observability epic #911.

| ID | Child (suggested title) | Class | Status | PR | Author | Issue | Labels |
|---|---|---|---|---|---|---|---|
| D1 | engine: structured per-cycle log lines (analyzer-result, scaling-decision) | obs | MERGED 0.9 | #1318 | 🟢 | **#1317(OPEN)** | enhancement, area/observability, release/v0.9 |
| D2 | observability: PrometheusRule alerting rules | obs | MERGED 0.9 | #1328 | ⚪ | **NEW?** | enhancement, area/observability, release/v0.9 |
| D3 | observability: wva_saturation_metrics_up freshness gauge | obs | MERGED 0.9 | #1190 | ⚪ | **#1082(CLOSED)** | enhancement, area/observability, release/v0.9 |

*Excluded (Dean 2026-07-29):* other-author merged bug fixes #1368, #1393, #1147, #1144, #1334
(→#962) — credited in release Highlights, not tracked here.

*Backlog / open observability issues to link (do not re-file):* #1466, #1272, #1273, #1459, #1484.
Most are ⚪ other-author.

---

## Issue ledger — consolidated (the actionable list)

### (1) Existing issues → LINK to epic, no new issue

| Issue | State | PR | Author | Epic child |
|---|---|---|---|---|
| #1005 | OPEN (epic) | — | 🟢 | **Epic B parent** — adopt, add children |
| #1261 | OPEN | — | 🟢 | A9 |
| #1455 | OPEN | #1444 | 🟢 | A10 (proposal merged) |
| #1317 | OPEN | #1318 | 🟢 | D1 |
| #1031 | CLOSED | #1036 | ⚪ | C2 |
| #993 | CLOSED | #994 | ⚪ | C3 |
| #1082 | CLOSED | #1190 | ⚪ | D3 |
| #1002 | CLOSED | #1129 | ⚪ | cross-ref → epic #1000 |
| #1447 | OPEN | #1452 | ⚪ | cross-ref (rescale) |

### (2) NEW issues to FILE — Dean's PRs (unambiguous; yours to author)

| Proposed child | Epic | PR | Status | Labels |
|---|---|---|---|---|
| race-safe analyzer registry | A1 | #1225 | closed-ref v0.8 | enhancement, area/engine |
| universal threshold post-step | A2 | #1228 | closed-ref v0.8 | enhancement, area/engine |
| per-analyzer slice to optimizer | A3 | #1246 | closed-ref v0.8 | enhancement, area/engine |
| multi-analyzer addendum (disabled-analyzer fix) | A4 | #1266 | closed-ref v0.8 | enhancement, area/engine |
| analyzer opt-in + non-registration log | A5 | #1479 | MERGED 0.9 | bug, area/engine, release/v0.9 |
| scale-down veto liveness gate | A6 | #1481 | OPEN 0.9 | bug, area/engine, release/v0.9 |
| runtime-enable restart warning | A8 | PR E | planned | bug, area/engine, area/observability |
| TA collector queries | B1 | #1051 | closed-ref pre-0.8 | enhancement, area/collector |
| TA state management | B2 | #1052 | closed-ref pre-0.8 | enhancement, area/engine |
| TA foundation (ITL/supply/demand/GPS/wiring) | B3–B6 | #1250 | closed-ref v0.8 | enhancement, area/engine |
| TA model-level demand | B7 | #1480 | OPEN 0.9 | bug, area/engine, release/v0.9 |
| TA dev-guide sync | B8 | #1478 | MERGED 0.9 | documentation, area/engine, release/v0.9 |
| per-role capacity aggregation / paired alloc | C4 | #1246 | closed-ref v0.8 | enhancement, area/engine |

> 0.8/pre-0.8 rows can be filed **closed** referencing the merged PR (legibility only), or folded
> into the epic body as a summary per decision 4. Only #1479/#1481/#1480/#1478 (+ PR E) are live 0.9.

### (3) Other-author PRs with NO existing issue — **decision for Dean**

These merged PRs have no tracker. Filing a new tracking issue would reference another contributor's
work; per your standing rule we don't edit their PRs, and a fresh issue is arguably theirs/a
maintainer's to open. **Default: leave as a bare PR-reference under the epic (no new issue).**
Confirm if you'd rather file trackers for epic completeness.

| PR | Author | Epic child | Note |
|---|---|---|---|
| #1442 | ev-shindin | A7 (V2 default, breaking) | high-visibility; may warrant a tracker |
| #1237 | ev-shindin | C1 (role-aware scale-down) | v0.8 foundation |
| #1328 | shuynh2017 | D2 (PrometheusRule alerts) | feature |

*(Other-author merged **bug fixes** — #1392, #1368, #1393, #1147, #1144, #1334 — removed per Dean
2026-07-29; they are not tracked here but remain in the release Highlights.)*

---

## Ready-to-file skeletons — Dean's work, **new epics only** (A, C, D)

> ✅ **FILED 2026-07-29.** Epics: A=[#1492](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1492),
> C=[#1493](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1493),
> D=[#1494](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1494). Child issues:
> A5=[#1495](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1495),
> A6=[#1496](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1496),
> A8=[#1497](https://github.com/llm-d/llm-d-workload-variant-autoscaler/issues/1497). All labeled
> `triage/accepted` + `release/v0.9`; children assigned to deanlorenz; shipped-0.8 children folded as
> epic-body checklists (not filed separately). No trackers filed for any other-author work. The text
> below is retained as the source of what was filed.

> **Scope (Dean, 2026-07-29):** file the missing trackers **only for Dean's own work under the new
> epics**. **No trackers for anything not Dean's** — the ⚪ other-author children (A7 #1442, C1 #1237,
> D2 #1328, and the excluded bug fixes) get **no issue from us**; Dean alerts those authors directly.
> Epic **B is existing #1005**, not new, so its children (B7 #1480, B8 #1478) are **out of scope for
> this pass** — not filed here. Skeletons are short by design; author-alert lines apply only where a
> referenced item is still **open** (here that's only A6 #1481, and its author is Dean → no external
> ping needed).

### The three new epic issues

Bodies are drafted above (§ Epic A, § Epic C, § Epic D). File each with its suggested title + labels,
and paste this **children checklist** into the epic body. Shipped-0.8 children are recorded as a
**done checklist inside the epic** rather than as separate retro trackers (decision 4 — no
retro-filing per minor issue); only live/planned 0.9 work gets its own child issue (below).

**Epic A children checklist (paste into epic body):**
```
- [x] Race-safe analyzer registry — #1225 (v0.8.0)
- [x] Universal threshold post-step + aggregation helpers — #1228 (v0.8.0)
- [x] Per-analyzer result slice to optimizer; remove combine — #1246 (v0.8.0)
- [x] Multi-analyzer addendum: disabled-analyzer fix + dev guide — #1266 (v0.8.0)
- [x] Analyzer participation opt-in + non-registration startup log — #1479  ← child issue A5
- [ ] Gate scale-down veto on per-analyzer liveness — #1481  ← child issue A6
- [ ] Warn on runtime ConfigMap analyzer-enable needing restart — PR E  ← child issue A8
- [ ] (backlog) Per-analyzer status return — #1261
- [ ] (backlog) Metric-based (demand, target) interface — #1455 / proposal #1444
```

**Epic C children checklist (paste into epic body):**
```
- [x] Per-role capacity aggregation + joint paired allocation — #1246 (v0.8.0)
- [x] Role-aware scale-down for disaggregated models — #1237 (v0.8.0, other author — link only)
- [x] Saturation v1 P/D role-aware grouping — #1036 / #1031 (other author — link only)
- [x] Saturation v1 default thresholds + partial override — #994 / #993 (other author — link only)
```
*(Epic C needs no new Dean child issue — C4's work shipped inside #1246, tracked as the checklist item.)*

**Epic D children checklist (paste into epic body):**
```
- [x] Structured per-cycle log lines — #1318 (tracked by #1317)
- [x] PrometheusRule alerting rules — #1328 (other author — link only)
- [x] Saturation freshness gauge — #1190 / #1082 (other author — link only)
```
*(Epic D needs no new Dean child issue — D1 already tracked by #1317; D2/D3 are other-author.)*

### Standalone child skeletons (live/planned 0.9, Dean-owned, no existing tracker)

**A5 — analyzer participation is opt-in**  · labels: `bug`, `area/engine`, `release/v0.9` · parent: Epic A
```
An absent analyzer config entry previously defaulted to enabled, so an analyzer could run without
being explicitly configured. Make participation opt-in; add a startup log line reporting when the
ThroughputAnalyzer is not registered.

Fixed by #1479 (merged). Retroactive tracker — open and close, or record as the Epic A checklist item.
```

**A6 — gate scale-down veto on per-analyzer liveness**  · labels: `bug`, `area/engine`, `release/v0.9` · parent: Epic A
```
A stalled, errored, or never-reporting analyzer could silently veto scale-down. Gate the veto on
per-analyzer liveness: an analyzer with no recent informative result cannot block scale-down, and if
no analyzer is live for a model, scale-down is withheld (safety floor).

Tracked by #1481 (open); closes on merge.
```

**A8 — warn when runtime ConfigMap analyzer-enable needs a controller restart**  · labels: `bug`, `area/engine`, `area/observability` (+ `release/v0.9` if it makes the cut) · parent: Epic A
```
Enabling an analyzer by editing the saturation ConfigMap at runtime is silently ignored until the
controller restarts. Emit a warning (log + Kubernetes Event) so the operator knows a restart is
required to pick up the change.

No PR yet (planned — "PR E"). This is the missing tracker for future work; file it now to hold scope.
```

---

## Filing checklist (for the maintainer — nothing done by the assistant)

1. File epics **A, C, D** (new), each with its children checklist pasted in; adopt **B = #1005**.
2. File the **3 standalone child skeletons** (A5, A6, A8) — Dean's work only. **File none** for
   ⚪ other-author children (Dean alerts those authors directly). B children not filed this pass
   (new epics only).
3. **Link** everything in ledger (1) — no duplicates. **File** ledger (2) — Dean's PRs.
   Ledger (3) other-author features: **no tracker** (Dean's call to alert authors directly).
4. Apply labels per the conventions block; expect `needs-triage` auto-added → set `triage/accepted`.
5. Tag 0.9-scope issues `release/v0.9` (± milestone #7). Leave 0.8-only closed items unmilestoned
   (decision 4) — represented via epic child-checklists + the Highlights summary.
6. **Do not assign D to shuynh2017.** **Do not edit/retitle/relabel ⚪ other-author PRs or issues.**

---

## Maintainer summary (draft notification — NOT posted)

> Draft only. Fill in `@<main-maintainer>` and send by hand (Slack/comment) when you're ready.

> **0.9 issue/epic cleanup.** I've organized the 0.9 (and carried-forward 0.8)
> analyzer/optimizer/observability work into four epics so the release tracks cleanly:
> - **Epic A — Multi-analyzer pipeline & analyzer lifecycle** (#1492, new) — pluggable analyzers
>   behind one optimizer; opt-in participation, liveness-gated scale-down veto.
> - **Epic B — ThroughputAnalyzer** — adopting existing epic **#1005**, adding 0.9 children.
> - **Epic C — Optimizer & P/D allocation math** (#1493, new) — role-aware capacity aggregation +
>   paired allocation for disaggregated serving.
> - **Epic D — Observability** (#1494, new; successor to closed #911) — per-cycle decision logs,
>   metrics, alerts.
>
> I filed the three new epics plus short trackers for my own untracked 0.9 items — opt-in
> participation (#1495), veto liveness (#1496), and the planned runtime-ConfigMap-restart warning
> (#1497). Existing issues are linked, not duplicated. I did **not** create trackers for other
> contributors' PRs — I'll ping those authors directly. Other-author work is still credited in the
> 0.9 release Highlights.
>
> Flag if you'd rather assign/label any of these differently.
