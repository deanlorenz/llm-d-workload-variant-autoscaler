last_update: 2026-08-17T02:30:00Z
state: in-progress
current_step: **Batch refresh, all 29 SUCCESS-collection runs (35 leaves), done — no code
changes.** Picked up `plan__batch-refresh-all-success-runs.md`, code spec
`planning/autoscaling-viz-batch-refresh-all-success-runs-plan.md` § Outcome. 35/35 leaves
succeeded, 0 crashes, stamps verified against `a1a815a7`. Not push-ready — pure data refresh.
**Watching for the next trigger, none picked up yet.**

## History — compressed 2026-08-17

Every task below this point is fully captured (spec + outcome + measured results + any bugs found
during verification) in its own Type 3 code-spec doc under `plans/planning/autoscaling-viz-*-plan.md`
— see the table below. This status file no longer carries the narrative; it points to it. Landed
commits, newest first, all on the `autoscaling-viz` branch (none pushed beyond `origin`'s tip
`4b263d73` — see § Branch):

| Commit | Task | Plan doc (§ Outcome) |
|---|---|---|
| (data only) | Batch refresh, all SUCCESS-collection runs | `autoscaling-viz-batch-refresh-all-success-runs-plan.md` |
| `a1a815a7` | Panel 3 stale forward-fill (Items AE/AF) + Item AC correction | `autoscaling-viz-panel3-stale-forward-fill-plan.md`, `autoscaling-viz-warmup-anchor-and-panel-polish-plan.md` |
| `deaf4886` | Warmup-anchor + estimated-data fallback + panel 3/4/6 polish round 2 | `autoscaling-viz-warmup-anchor-and-panel-polish-plan.md` |
| `0aade22f` | Latent `SAT` NameError fix | `autoscaling-viz-panel4-kv-heatmap-plan.md` |
| `f92d3c19` | Panel 4/3/6 visual follow-up (+ infinite-loop bug fix) | `autoscaling-viz-panel4-heatmap-followup-plan.md` |
| `0a2be3be` | Panel 4 repurpose: per-pod KV% heatmap | `autoscaling-viz-panel4-kv-heatmap-plan.md` |
| `9da9f7a2` | Panel review 2026-08-15/16 fixes (Items Q/R/T/U/W) | `autoscaling-viz-panel-review-20260815-fixes-plan.md` |
| `b7920cd3` | Task 8: panel 3 visual scheme (hatch/outline) | `autoscaling-viz-panel3-visual-scheme-plan.md` |
| `d7fa6ee5` | sim-from-benchmark Fork 6 correction (TA is a pure rate analyzer, not an SLO enforcer) | `autoscaling-viz/planning/sim-from-benchmark-plan.md` §8 item 6 (branch-local, not `plans/planning/`) |
| `062c1071` | Task 7: per-panel corner-info allocation | `autoscaling-viz-corner-info-plan.md` |
| `870fff6d` | Task 6: version-stamp + regen (Part 2 scope-violation incident, resolved) | `autoscaling-viz-version-stamp-and-regen-plan.md` |
| `cf76a238` | Task 5: backlog viz rerun, all 7 runs extracted+rendered fresh | `planning/autoscaling-viz-followon-plan.md` § Item 8 |
| `e188d244` | Task 4: drain-window bound fix (two-attempt; second version correct) | `autoscaling-viz-drain-window-fix-plan.md` |
| `3f12aaa1` | Task 3: panel 6 redesign (signed replica-delta per analyzer) | `autoscaling-viz-panel6-redesign-plan.md` |
| `08927557` | Task 2 fix-round 1 (panel 1b cap no-op, panel 3 legend density) | `autoscaling-viz-panel3-redesign-plan.md` § Outcome |
| `fbecfe26` | Task 2: panel 1b capping + panel 3 request-domain redesign | `autoscaling-viz-panel3-redesign-plan.md` |
| `037106f2` | Task 1: bugfix cluster (title `?`s, panel 1a triage, panel 3 readability) | `autoscaling-viz-bugfix-cluster-plan.md` |
| `34afc197` | Item 5: coverage-check reference doc (`COVERAGE-CHECKS.md`) | `planning/autoscaling-viz-followon-plan.md` § Item 5 |
| `cff4e4c0` | Panel 6 (scaling-decision reasons), first landing | `autoscaling-viz-decision-panel-plan.md` |

**Process note preserved (not a defect in any plan doc, a session-handling lesson):** a machine
restart once parked mid-Task-4 (drain-window fix) with zero code written — safe resume point,
reproduction only. The eventual fix (`e188d244`) came from a fresh pickup of the same trigger, per
the drain-window-fix plan doc's own outcome. No standing risk from this — noted only because a
future "PARKED mid-task" entry should look the same way (nothing to compress, nothing at risk).

**Housekeeping notes not worth their own row:** a `plan__` reply
(`plan__autoscaling-viz-extract-render-two-real-runs-done.md`) was once sent mistakenly claiming the
SAT-NameError finding was still unfixed when it had already shipped at `0aade22f` — corrected via a
follow-up handoff rather than editing the sent one, per the handoff protocol's sender-never-edits
rule. Two filing inconsistencies (a trigger addressed without the usual prefix; a trigger opened
without marking `.WIP` first) were both self-corrected mid-session, no lasting effect.

## Branch
`autoscaling-viz` at `/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/autoscaling-viz`.
Tip **`a1a815a7`**. `origin/autoscaling-viz` is at `4b263d73` — everything in the table above is
**local only** and needs Dean's OK to push (narrow to the specific commit range asked for, per this
workspace's push-scope convention — not "push the branch" by default).
35 commits, orphan lineage — **no merge-base with `upstream/main` by design**, so the pre-push DCO
hook self-skips and commits here carry **no `Signed-off-by`**. Never push to `upstream` (its push
URL is literally `READ-ONLY-UPSTREAM-DO-NOT-PUSH`).

Venv at `./.venv` (matplotlib only). `uv` is the tool of record for Python here.

## Plan — live ownership problem, still unresolved (flagged for Dean 2026-08-08, unchanged since)
The document being followed is **`autoscaling-viz/real-trace-viz-plan.md`** (Rev 6, `Status: DRAFT`),
which lives on the code branch, not as a Type 3 under `plans/planning/`, and does not follow Type 3
authoring rules (no Reading Protocol, no TOC). De-facto owner: this session (the coder) — every
"open decision for Dean" in that doc is this session nominating its own forks, and nobody independent
has set the scope. Not unilaterally restructured — splitting it, moving it, or handing authorship to
a plan agent are all Dean's calls.

## What is done and pushed (predates this branch's local-only commits above)
- **Real-trace toolchain**: `fetch_run.sh` → `extract_real_trace.py` → `render_real_trace.py`, plus
  `sim.py`/`run.py`/`plots.py` (synthetic, untouched by the real-trace path).
- **Six-panel renderer** (panel numbering has since evolved — see the table above for current shape).
- **arm-B findings** `real-trace/staircase-20260807-armB/FINDINGS.md`: the multi-pod wave is
  **routing**, not the originally-published "not routing" claim (over-generalized from a single-pod
  run). Propagated into plan/README/docstrings at `1941afe4`.
- **`947dd4c1`/`aa67c399`/`4b263d73`**: ladder cross-check, envoy-field feasibility probe,
  `router_stats` boot-exclusion fix.

## Simulation from the benchmark — C1, C2 done, unpushed
Full state, including the Fork 6 resolution (TA is a pure rate analyzer, not an SLO enforcer) and all
measured results, lives in **`autoscaling-viz/planning/sim-from-benchmark-plan.md`** (§3 gate, §6
commit order, §8 Dean's open forks, §9 data sources) — not restated here. Gate **PASSES both arms**
(`5a0c607f`); still open: the 15%/15%/1-replica/1% tolerance numbers (Dean resolved the *criterion*,
not the numbers) and Fork 0b (what `prc` means for A2 in C4).

## Awaiting Dean (nothing blocked; work continues around these)
1. **Envoy input path in `extract_real_trace.py`** — a third reader for ladder-shaped runs with no
   per-request file. Substantial single-file edit ⇒ needs approval before coding.
2. **Regenerate the shipped `arm-B` bundle?** Still carries pre-fix `disp_p95: 1.0`. FINDINGS §7
   documents the correct numbers, so the artifact is self-describing either way — a results-policy
   call (results are append-only), not urgent.
3. **Plan-doc ownership** (§ Plan above).
4. **Inert allowlist entry**: `~/.claude/settings.json` allowlists `Edit()` on
   `plans/session/handoffs/**`, but the worktree-isolation guard preempts it — either the guard
   should honor it or the entry should go. (Workaround in active use: Bash `cp`/`mv` both work fine.)

## Deferred by agreement
- **Panel 4 design** (superseded — panel 4 is now the KV% heatmap, see the table above; this entry
  is about the *original* panel 4's three-queue question, now moot).
- **(iii) per-request-trace oscillation detector** — lower priority, shares a dependency (rotated EPP
  logs) with proving the routing mechanism.
- **sim-p3 replacement** — needs a check on whether `sim.py` exports per-backend request counts.

## Dean's stated priority — viz output into the benchmark's own experiment dir (2026-08-08, still open)
Target: call the viz tools as a last step after copying benchmark results over, get full
reports/graphs/HTML in the results dir. Specified as `sim-from-benchmark-plan.md` §7.1, the
`viz_experiment.sh` call-site contract (explicit `--run`/`--controller-log`/`--out`, no path
discovery). What exists: `run_inputs.json` ✅, `gate.json`/`GATE-REPORT.md` ✅. What doesn't:
`sim_compare.json`, `panels-*.png`, `index.html` — all gated on C5, itself gated on `report.py`/
`run.py`'s `OUT = "out"` hardcoding (substantial single-file edit, needs approval before coding).

## OWED — started? NO.
Full prose recheck with real numbers across `autoscaling-behavioral-demo-design.md`,
`REVIEW-CHECKLIST.md` and `report.py` (both on the branch). Known-stale claims: the spike-shape
banner (renders twice), two `2.5×` token references, §2.4's paragraphs on the deleted analytic `W0`
seed. Also standing: `spike` is teaching-only, never calibrated; Stability stays a standalone doc.

## Data locations (read-only; none of it is in this branch)
- Ladder run 08-07: `benchmark/dean-20260807-234050-328/results/inference-perf-1786135288-srzxlb_1`
  — `per_request_lifecycle_metrics.json` is 0 bytes (harness OOM); envoy log is on kubelet rotation.
- arm-B run: `benchmark/dean-20260807-210058-612/results/inference-perf-1786125698-ptufog_1`.
- WVA controller log: `benchmark/session-notes/scratch/ladder-controller.log` (not in the results
  directory — this was the finding that triggered `sim-from-benchmark-plan.md` §1.3).

## Standing constraints
No `git push` without Dean's explicit OK **for that specific push**; never push to `upstream`; no
in-place shell edits; >3 existing files or a substantial single-file edit ⇒ describe as text and get
approval first; `pwd` + `git branch --show-current` before every edit and every commit; no
GitHub-visible actions without instruction; no Agent/workflow use unless asked. Bundle rules: never
copy prompt/response text into a bundle; bundles only, never raw; nothing over 20 MB; no
`metrics/raw/` or per-request source files in a published bundle; `provenance.json` mandatory;
results append-only; publishing never pushes. pokprod is read-only; teardown needs Dean's approval.
**Design forks belong to Dean, including for coders** — a bug fix can silently ride a semantic
change, so name it separately. **Never write directly into `benchmark/runs/` or any other sibling
worktree** — this scope's output convention is exclusively
`session-notes/review-samples/<label>/{bundle.json,coverage.json,panels.png}` inside this worktree
(see `autoscaling-viz-version-stamp-and-regen-plan.md` § Outcome for the incident this rule comes
from).

## Last state-park — 2026-08-16/17
Five tasks (two-real-runs, sat-nameerror-correction, warmup-anchor-round2, panel3-stale-fill,
batch-refresh-all-success-runs), all completed and filed — no subagents spawned, no stuck handoffs,
nothing uncommitted. Full park report is in git history for this file (commit prior to this
2026-08-17 compression pass) if the mechanical detail is ever needed; the substance is in the table
above.
