# Pokprod scratch-tools doc-coverage cleanup (Type 3, draft)

**Status:** DRAFT — Dean asked for this cleanup plan (D-51); not yet approved, nothing executed.
**Correction 2026-08-15: the original count was wrong.** D-51 named 5 tools from the coder's own
§16.5 list; a full directory listing of `benchmark/session-notes/scratch/` this session found
**19 scripts total**, not 7 (5 + the already-documented envoy pair). 12 were never named anywhere
in D-51 or this doc's first draft. Verified none belong to Ofer's code (checked directly — the
`two_variant_v2_full_pipeline.png` figure Dean asked about comes from tracked
`hack/benchmark/plot_two_variant_pipeline.py`, unrelated to this directory).

**Companion docs:** [`envoy-per-request-recovery-tool-plan.md`](envoy-per-request-recovery-tool-plan.md)
(the pattern this follows; the 2 tools already covered) · [`ta-pokprod-history.md`](ta-pokprod-history.md)
(D-51, D-54, D-56 — this correction).

---

## Full inventory, read in full 2026-08-15 (not from recollection or the coder's §16.5 list alone)

19 scripts, 3 real categories — not the 2-category split the first draft used:

**Already documented (2):** `envoy_per_request.py`, `serving_replicas.py` — see the companion doc.

**Ladder-run-specific analysis tools (8) — same hard limit: hardcoded to the 2026-08-07 ladder
run's shape, none generalizes without rework, none was written to.**

| Tool | What it answers |
|---|---|
| `verify_decision_rule.py` | Does a candidate max-over-analyzers combine rule reproduce every emitted scaling decision? |
| `server_token_truth.py` | Ground-truth token counts from vLLM's own `/metrics` counters (inference-perf's re-tokenization was wrong on 100% of requests) |
| `stage_table.py` | Per-stage latency + bounds the output-token defect's dispersion per stage |
| `stage_vs_replicas.py` | Joins per-stage latency to actual serving replica count (imports directly from `envoy_per_request`/`serving_replicas`) |
| `analyzer_presence.py` | Per-cycle census: were both analyzers actually decision-capable, or riding along silently with no `prc`? |
| `decision_timeline.py` | Per-cycle TA/SAT internal view vs. the emitted decision, with the correct delta-based combine formula documented in its own docstring (guards against two specific wrong formulas used in earlier analysis) |
| `kv_per_rung.py` | Real vLLM KV-cache utilization per workload rung, because the analyzer's own `util` field is NOT kv-cache utilization (0.9987 real vs 0.360 reported on this run) |
| `replica_timeline.py` | When each replica became ready, not just run-wide aggregate counts |

**Run-collection / operational tools (9) — mostly reusable as written, not ladder-run-specific in
the same way.**

| Tool | What it does | Reusable as-is? |
|---|---|---|
| `watch_pvc_space.sh` | Standing PVC-space watchdog, silent unless free space drops below a floor | Yes — NS/pod hardcoded *on purpose* ("never point it at another namespace") |
| `watch_decode_replicas.sh` | Emits one line per change in decode replica count (the harness's own stdout is silent for the whole load window) | Yes, generic |
| `wait_harness_done.sh` | Single-notification watch: emits when the harness pod leaves Running, before teardown makes its terminal phase unreadable | Yes, generic |
| `wait_pid_exit.sh` | Single-notification watch on a PID exiting (the harness's own completion signal returns *before* post-collection steps finish) | Yes, generic |
| `verify_pvc_vs_host.py` | Byte-for-byte completeness check between PVC and host — catches the same silent-truncation bug `reset_run.py`'s existence-only check misses | Yes, generic — real bug-catcher, cites a real prior incident |
| `fetch_missing_from_pvc.py` | Fetches files that exist on the PVC but never got copied to host (because the harness's own collection step copies once, missing anything written after) | Yes, generic |
| `sample_report.py` | Prints a compact cross-stage comparison from the harness's nested YAML reports, dependency-free | Yes, generic |
| `probe_first_record.py` | Compares 3 token-count sources per request to isolate a re-tokenization bug; streams a bounded prefix of a 4.2GB file rather than loading it | Ladder-run-specific input path, but the streaming technique generalizes |
| `test_sidecar.py` | Validates a specific correction module (`output_token_correction.py`) 9/9 against real data | Ladder-run-specific validation data, general test structure |

## Recommended classification (Dean's call, not decided here)

- **The 8 ladder-run analysis tools:** recommend **DEFERRED, not DEPRECATED** — each embodies a
  reusable diagnostic *technique* (verify a decision rule against raw logs; recover ground truth
  from server-side counters; distinguish "logged a payload" from "was decision-capable"; join
  latency to actual-not-nominal replica count; measure the real metric instead of a proxy field
  that looks like it but isn't) even though the hardcoded constants aren't reusable directly.
  Promoting as-is would be misleading; the value is as a worked pattern for the next time this
  failure-mode class recurs.
- **The 7 generic operational/run-collection tools** (`watch_pvc_space.sh`,
  `watch_decode_replicas.sh`, `wait_harness_done.sh`, `wait_pid_exit.sh`,
  `verify_pvc_vs_host.py`, `fetch_missing_from_pvc.py`, `sample_report.py`): recommend
  **promote as-is or close to it** — genuinely reusable, several catch real bugs
  (`verify_pvc_vs_host.py` in particular guards against a specific documented incident). Main
  open question, same as before: hardcoded NS/pod as a deliberate guard vs. a required flag —
  Dean's call, may differ per tool.
- **`probe_first_record.py`, `test_sidecar.py`:** recommend **DEFERRED** for the same reason as
  the analysis-tool group — general technique (bounded streaming of a huge file; validating a
  correction module against real data), ladder-run-specific inputs.

## What this doc does NOT do

- Does not promote anything — gated on Dean's classification call above.
- Does not re-validate any tool's numeric claims independently — validation is internal to each
  tool's own docstring and the investigation that produced it.
- Does not open a WVA issue for anything — none of these touch WVA code.

## Open question for Dean

Classification above is a recommendation, not a decision, and the count itself just changed from
5 to 17 (excluding the already-documented pair) — worth confirming the scope is right before
Dean spends review time on it. If agreed: write a DEFERRED note into each deferred tool's own
docstring pointing at this doc, and scope promotion Type 3s for whichever of the 7 operational
tools get the promote-as-is call. Neither executed here.
