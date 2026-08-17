# `reset_run.py` — replace the existence check with a completeness check (code spec)

**Status: READY**

**Owner:** benchmark coder (Bob, `coder-auto` mode), worktree `benchmark`, branch `benchmark`.
**Planner:** pokprod-benchmark (`plan (pokprod/benchmark-execution scope)`).
**Ledger:** [[D-74]] (the defect), [[D-77]] (how it was found). Tracked as
[`ta-pokprod-open-scenarios.md`](ta-pokprod-open-scenarios.md) § Priority triage **item 14**.

---

## Reading protocol

Short doc — read it whole. Read `hack/benchmark/reset_run.py` and
`session-notes/scratch/verify_pvc_vs_host.py` in full before writing anything.

## 1. The defect

`reset_pvc_results()` in `hack/benchmark/reset_run.py` (around **lines 270-272**) decides whether it
is safe to `rm -rf` a results directory **on the PVC** by asking whether a directory of the same
**name** exists on the host:

```python
on_host = host_result_dirs(workspace)
for d in ...:
    if d in on_host:
        # ... deletes the PVC copy
```

That is an *existence* check standing in for a *completeness* check. A host directory that exists but
is missing files — or holds truncated ones — reads as "we already have this data," and the PVC copy
(the only complete one) is deleted.

**This is not hypothetical.** A file-by-file comparison run before letting it loose once found **all
four** host copies incomplete; `--apply` would have made the loss permanent:

| experiment | PVC files | missing from host |
|---|---|---|
| `guidellm-…6pckwk_1` | 105 | `analysis/summary.txt` |
| `guidellm-…i6x2vj_1` | 110 | `analysis/summary.txt` |
| `inference-perf-…41gfxn_1` | 424 | `benchmark_report,_stage_4_lifecycle_metrics.json.yaml` |
| `inference-perf-…d5lhav_1` | 260 | 3 × `analysis/*.png` |

Root cause of the *gap itself* is a second, distinct `step_09` defect: the copy runs once and
`analysis/` is written into the experiment directory **afterwards**, so it exists on the PVC but never
on the host. Nothing re-syncs and nothing notices. That upstream defect is **out of scope here** —
captured in `session-notes/issues/llm-d-benchmark-step09-silent-truncation.md` ([[D-76]]).

The mitigation in force today is purely procedural — "remember to run `verify_pvc_vs_host.py` first."
This spec makes it mechanical.

## 2. Scope

**In scope:** make `reset_run.py` refuse to delete a PVC directory unless the host copy is verifiably
complete, reusing the comparison logic that already exists in
`session-notes/scratch/verify_pvc_vs_host.py`.

**Out of scope — do not do these:**
- Fixing `step_09` or anything in the embedded `llm-d-benchmark` clone.
- Any cluster run, any `--apply` against real data, any GPU action.
- Filing upstream issues (Dean's call, no GitHub writes).
- Promoting `verify_pvc_vs_host.py` out of `session-notes/scratch/` — that is a separate parked
  decision (the doc-coverage cleanup, [[D-54]]/[[D-56]]); **borrow its logic, leave the file where it
  is.**

## 3. What "complete" must mean

The check must compare, per experiment directory, at minimum:

1. **File inventory** — every file present on the PVC is present on the host (relative-path set
   comparison, not a count; a count alone can match while contents differ).
2. **Size per file** — byte size equal for every corresponding file.

A count-only comparison is explicitly **not** sufficient — that is the same class of substitution as
the original defect, and `step_09` already shipped one (`file_count > 0` as its only verification).

**One deliberate exception you must preserve, not "fix".** Some host files are *intentionally*
different from the PVC originals: the corrected reports. `benchmark_report_v0.2,_stage_{0,1,2}` differ
because the host copies were corrected in place (`output_len` mean 905.481 → 512.100,
`inter_token_latency` mean 0.008998 → 0.015910, ×1.768, plus an `output_token_correction` provenance
block). **The PVC holds uncorrected originals; the host copy is the one to keep.** A size mismatch on
these must therefore **not** be silently treated as "host is stale, keep the PVC copy" — it must
surface as a mismatch the operator resolves. Report it clearly; do not auto-resolve, and do not
loosen the check to make it pass.

## 4. Required behavior

- **Default (no `--apply`)**: unchanged dry-run reporting, plus the completeness verdict per directory.
- **With `--apply`**: delete a PVC directory **only** when its host copy passes the completeness
  check. On failure, **skip that directory, print a loud explicit reason, and continue** with the
  others; exit non-zero if any directory was skipped, so a caller cannot mistake a partial run for a
  clean one.
- **Never delete on an error path.** If verification itself cannot run (pod gone, exec fails, token
  expired), that is a *refusal to delete*, not a pass. Prior incidents in this exact area include two
  scripts misreporting an expired token as a clean result — do not add a third.
- No new interactive prompts; this runs unattended.

## 5. Verification — behavioral, not by inspection

Per CODER-CONVENTIONS §3, and because this script's whole failure mode is "looks fine, deletes data":

1. **Unit-level, against synthetic fixtures — no cluster.** Build temp dirs standing in for host and
   PVC and prove each case:
   - identical trees → check passes;
   - host missing one file → refuses, names the file;
   - host file truncated (same name, smaller size) → refuses, names the file;
   - host file *larger* (the corrected-report shape) → refuses/flags, does **not** silently delete;
   - verification error (unreadable path) → refuses.
2. **`--apply` must be proven not to delete on a failing check** — assert the directory still exists
   after the call. This is the single most important assertion in this spec.
3. **Do not run `--apply` against the real PVC or a live cluster** to test this. Fixtures only.
4. Record in `./.bob-status.md` exactly which gates you ran. This is a Python-only change, so the Go
   gates (`make test`/`make lint`/`gofmt`/`go build`) do not apply — **note that explicitly** rather
   than skipping silently.

## 6. Commit

One commit is fine if the change is cohesive; split if tests land separately. DCO sign-off required
(`git commit -s`). **Do not push** — the branch is already 35 commits ahead of origin and unpushed;
pushing needs Dean's per-push confirmation, which is not granted by this spec.

Suggested subject:
`fix(benchmark): reset_run.py must verify host completeness before deleting PVC data`

The message must state that the prior check was name-existence-only and name the preserved
corrected-report exception, so a future reader does not "simplify" it back.

## 7. Deletion classification

If you remove any existing helper, classify it **DEPRECATED** or **DEFERRED** per
CONVENTIONS § "Document every deletion" and state it in your handoff. Expected shape here is
*replacement of a predicate*, not removal of functionality — if you find yourself deleting more than
that, stop and ask via a handoff.

## 8. Report back

- Update `./.bob-status.md` at every checkpoint (it is your heartbeat; nobody reads your chat live).
- When done, write `plan__reset-run-completeness-done.md` — what changed, the fixture results per
  case, gates run, deletion classification, anything you found and did **not** fix.
- If the spec is wrong or underspecified, write a `plan__<topic>.md` question and **stop** rather than
  guessing. In particular: if `verify_pvc_vs_host.py`'s logic turns out not to be reusable as-is, say
  so and propose an approach — do not silently reimplement a weaker check.
