# Pokprod scratch-tools doc-coverage cleanup (Type 3, draft)

**Status:** DRAFT — Dean asked for this cleanup plan (D-51); not yet approved, nothing executed.
Covers the 5 tools named in D-51 that were flagged (coder's own §16.5, 2026-08-07) as
never-promoted, distinct from `envoy_per_request.py`/`serving_replicas.py`, which already have a
retroactive Type 3 (`envoy-per-request-recovery-tool-plan.md`).

**Companion docs:** [`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md)
(the pattern this follows) · [`ta-pokprod-history.md`](ta-pokprod-history.md) (D-51).

---

## What was actually found, read directly (not from recollection)

All 5 read in full 2026-08-15. They split into two real categories, not one:

**Ladder-run-specific analysis tools (4) — same shape as the already-documented pair, same hard
limit.** All four are one-off diagnostic scripts built to answer specific questions about the
2026-08-07 ladder run's OOM/output-token-defect/replica-lag investigation. None generalizes to a
different workload shape without rework; none was written to.

| Tool | What it answers | Depends on |
|---|---|---|
| `verify_decision_rule.py` | Does a candidate max-over-analyzers combine rule reproduce every emitted scaling decision in the controller log? (Built because the deployed image's source tree didn't match what was on disk — verify from behavior, not source.) | Controller log JSON payloads only; self-contained |
| `server_token_truth.py` | Recovers ground-truth token counts from vLLM's own `/metrics` counters, since inference-perf's re-tokenization was wrong on 100% of requests this run | `metrics/raw/*decode*_metrics.log` scrapes only; self-contained |
| `stage_table.py` | Per-stage latency + quantifies the output-token defect's dispersion per stage (bounds it via the workload's known true output-length band) | Hardcoded `RATES`/`DIR` for the ladder run; hardcoded `TRUE_LO/HI/MEAN` for this workload's profile |
| `stage_vs_replicas.py` | Joins per-stage latency to the *actual* serving replica count (not the controller's lagging `curr`), explaining the ladder run's non-monotonic latency-vs-RPS curve | Imports `envoy_per_request.assign_stages`/`serving_replicas.weighted` directly — inherits their ladder-run-specific `STAGES` |

**Operational guard (1) — different category, genuinely reusable, deliberately narrow-scoped.**

`watch_pvc_space.sh` — a standing PVC-space watchdog (silent unless free space drops below a
floor), because inference-perf writes its per-request report directly to the workload PVC with no
buffer in front of it, and a full PVC silently truncates/loses a run's results with no way to
regenerate short of a full rerun. **Not workload-specific** — it watches disk space, not run
content — but its namespace and pod name are hardcoded *on purpose* ("this is a blast-radius
guard, not a knob. Never point it at another namespace"). This one is close to promotion-ready as
written; the other four are not.

## Recommended classification (Dean's call, not decided here)

Per the deletion/deprecation-documentation convention (`session/CONVENTIONS.md`), every one of
these needs a DEPRECATED-or-DEFERRED call if it stays in scratch/ rather than being promoted:

- **The 4 ladder-run analysis tools:** recommend **DEFERRED, not DEPRECATED** — the diagnostic
  *technique* each embodies (verify a decision rule against raw logs; recover ground truth from
  server-side counters when the client-side trace is lost; bound a known defect's dispersion
  rather than assume a scalar correction; join latency to actual-not-nominal replica count) is
  reusable even though the specific hardcoded constants are not. Promoting them as-is to
  `hack/benchmark/` would be misleading (they'd look general-purpose and aren't); the actual
  future value is as a worked pattern to lift from when the same failure mode recurs on a
  different run, not a tool to invoke unchanged.
- **`watch_pvc_space.sh`:** recommend **promote as-is**, or close to it — genuinely reusable,
  narrow by design, low risk. The main open question is whether the hardcoded NS/pod should become
  a required `--namespace`/`--pod` flag (matching the `.env`-per-namespace discipline elsewhere in
  this scope) or stay a deliberate blast-radius guard exactly as written. Both are defensible;
  Dean's call.

## What this doc does NOT do

- Does not promote anything — that's a separate action, gated on Dean's classification call above.
- Does not re-validate any of the 4 analysis tools' numeric claims independently (unlike the
  envoy-tool Type 3, which had an independent cross-check to cite) — their validation is
  internal to their own docstrings and the ladder-run investigation that produced them.
- Does not open a WVA issue for anything — none of these touch WVA code; they're all
  benchmark-side analysis/ops tooling.

## Open question for Dean

Classification above (4 deferred-as-pattern, 1 promote-as-is) is a recommendation, not a decision.
If agreed, next step is: write the DEFERRED note into each of the 4 tools' own docstring header
(one line pointing at this doc) and open a small Type 3 for `watch_pvc_space.sh`'s promotion if
that's the chosen path — neither executed here.
