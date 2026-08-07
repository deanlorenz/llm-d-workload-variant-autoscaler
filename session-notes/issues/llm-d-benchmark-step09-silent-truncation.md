# llm-d-benchmark step_09: an interrupted `kubectl cp` leaves a silently truncated results file that a retry will not repair

**Status:** draft, not filed. Target: `llm-d/llm-d-benchmark` — **not** inference-perf.
This is a separate defect from
[`inference-perf-output-token-inflation.md`](inference-perf-output-token-inflation.md); they surfaced
in the same investigation and must not be conflated.

**Source:** `llmdbenchmark/run/steps/step_09_collect_results.py`
**Evidence run:** `dean-20260803-042120-916` / experiment `inference-perf-1785720119-41gfxn_1`,
namespace `dhl-wva-209`.

---

## One-sentence version

step_09 copies multi-GB results with `kubectl cp`, verifies only that *at least one file* arrived,
swallows the exit status, and then refuses to run again because the destination is non-empty — so an
interrupted copy becomes a permanently truncated local file that looks complete to every downstream
consumer.

## What actually happened

| Copy | Bytes on PVC | Bytes on host | |
|---|---|---|---|
| `inference-perf-1785720119-41gfxn_1` | 7,570,490,291 | 3,967,763,968 | **truncated, 52.4%** |
| `inference-perf-1785724033-d5lhav_1` | 4,204,290,876 | 4,204,290,876 | byte-exact |

Same code path, same cluster, consecutive runs. The second one is the control: when the copy is allowed
to finish it is exact, so this is not a systematic corruption — it is an unguarded interruption.

Timeline from `ta-probe-run.log` and the on-disk mtimes:

```
04:56:03  [08] All pods completed successfully          <- harness finished CLEANLY
04:56:03  [08] Completed: wait_completion
04:56:07  [09] Collecting results for 1 dir(s): inference-perf-1785720119-41gfxn_1
04:56:10  ...  every small file lands (reports, native json, logs, config)
04:56:15  ...  last small file lands
          ---- 9 minutes 33 seconds of no output at all ----
05:05:48  per_request_lifecycle_metrics.json mtime, 3,967,763,968 bytes
          make: *** [Makefile:504: benchmark-run] Terminated
```

The truncated size is an exact multiple of 512 (7,749,539 blocks) — the signature of an interrupted tar
stream, which is what `kubectl cp` is.

**Correction to an earlier hypothesis of mine:** I initially assumed `step_08_wait_completion` had
failed to observe a clean finish and step_09 raced the still-writing harness. The log disproves it —
step_08 logged `All pods completed successfully` and the harness was done. The file was complete on the
PVC and the truncation happened entirely on the *read* side.

## Root cause chain

Four things have to line up, and all four are in step_09:

**D1 — the copy is silent, so it reads as a hang.** step_09 logs `Collecting results: <exp_id>...` and
then produces no output until the copy returns. On a 7 GB file over a cluster link that is ~10 minutes
of apparent deadlock, immediately after a step that just printed a success. An operator watching this
has no signal distinguishing "copying 7 GB" from "wedged", and the natural response is to kill it. The
interruption here was a SIGTERM to `make`; a pod eviction, an idle-timeout on the API connection, or a
laptop suspend would produce the identical outcome.

**D2 — success is a file *count*, not an integrity check.** The only verification is:

```python
result = cmd.kube("cp", remote_path, str(local_path), namespace=harness_ns, check=False)
if result.success:
    files = list(local_path.rglob("*"))
    file_count = sum(1 for f in files if f.is_file())
    if file_count > 0:
        total_collected += file_count
```

`check=False` means a non-zero `kubectl cp` exit does not raise, and `file_count > 0` is satisfied by the
27 small files that copied fine. No byte count is ever compared against the source. A half-copied 7 GB
file is reported as a successful collection.

**D3 — the partial state is sticky; a retry cannot repair it.**

```python
def should_skip(self, context: ExecutionContext) -> bool:
    """Skip if step 06 already collected results locally."""
    results_dir = context.run_results_dir()
    if results_dir.exists() and any(results_dir.iterdir()):
        return True
    return False
```

Re-running the step over a partially-populated results dir short-circuits to skip. The truncation is
therefore permanent from the harness's point of view: the one operation that could fix it declines to
run *because* it half-ran. Recovering requires knowing to delete the destination first, which requires
knowing the file is truncated, which is exactly what D2 prevents.

**D4 — downstream, "the file exists locally" reads as "we have the data".** This is the part that turns
a lost file into lost *results*. A truncated `per_request_lifecycle_metrics.json` is valid-looking JSON
text up to the cut; anything that streams it computes over ~52% of the requests and reports a number.
And any retention policy phrased as "delete from the PVC once it is on the host" will delete the only
complete copy. That is not hypothetical: our own PVC reclaim gate had exactly this bug, said `FREE` for
this experiment, and would have destroyed the remaining 3.6 GB. It was caught only because a size
discrepancy in unrelated output was chased down.

## Second finding: files written into the experiment directory after the copy are never fetched

Found 2026-08-07 while checking whether it was safe to delete the PVC copies. This is a separate defect
from the truncation, in the same step, sharing the D4 link ("exists locally" reads as "we have the data").

`step_09` copies each experiment directory **once**. Anything written into that directory afterwards is
never collected, and no later step re-syncs. On our PVC that is the entire `analysis/` subtree: it is
present for **all four** experiments and absent from **every** host copy. Comparing names and sizes
file-by-file:

| experiment | files on PVC | present on host | missing |
|---|---|---|---|
| `guidellm-1785445833-6pckwk_1` | 105 | 104 | `analysis/summary.txt` |
| `guidellm-1785447061-i6x2vj_1` | 110 | 109 | `analysis/summary.txt` |
| `inference-perf-1785720119-41gfxn_1` | 424 | 423 | `benchmark_report,_stage_4_lifecycle_metrics.json.yaml` |
| `inference-perf-1785724033-d5lhav_1` | 260 | 254 | 3 × `analysis/*.png` |

Small in bytes (265 KB total) and therefore easy to dismiss — but these are results, and nothing reports
them as absent. The failure is silent in both directions: the copy does not know the files will appear,
and no consumer knows to look for them.

It compounds with the truncation because a *reclaim* step downstream then asks only whether the host has
a directory of the same name before deleting the PVC copy. That turns "we quietly lack some results" into
"those results no longer exist". Fix 1 below (compare sizes) does not cover this case — a size comparison
taken at copy time cannot see a file written later. What covers it is re-listing and re-syncing before
anything deletes the source, which is the guard we added downstream.

## Why the consequences are worse than they look

The per-request file is written at the *end* of the run and copied at the *very end* of the pipeline, so
every failure in this area lands after all the GPU time has been spent. There is no cheap retry: the
data either comes off the PVC intact or the run is repeated. For a staircase run that is over an hour of
H100 time.

## Suggested fixes

Roughly in value order:

1. **Compare sizes after the copy.** The source sizes are one `kubectl exec -- find -printf '%s %p\n'`
   away, and the check is a few lines. Treat any mismatch as a step failure with the two byte counts in
   the message. This alone converts silent permanent loss into a loud, recoverable error.
2. **Make `should_skip` mean "already collected *completely*"** rather than "destination is non-empty" —
   or drop the shortcut and let the copy be idempotent. As written, D3 makes every other failure mode in
   this step unrecoverable-by-retry.
3. **Don't discard the exit status.** If `check=False` is deliberate so one experiment's failure doesn't
   abort the others, still surface a non-zero exit per experiment instead of gating everything behind
   `result.success` and a file count.
4. **Emit progress on large copies** — even just logging each file's size before copying it, so a
   ten-minute silence is attributable. Cheap, and it removes the incentive to kill the run.
5. **Consider not putting a multi-GB file through `kubectl cp` at all.** `kubectl cp` is tar-over-exec
   with no resume and no verification; it is the wrong tool for gigabytes. Extracting what is needed
   pod-side and copying the result is both faster and safer (see below).

6. **Re-list the source before declaring collection complete** (for the second finding). A final
   `find`-and-compare pass, or simply collecting after everything that writes into the experiment
   directory has finished, would fetch `analysis/`. A size check at copy time cannot see a file written
   after the copy.

Fixes 1–3 are small and independent. Fix 1 is the one that matters.

## What we do downstream in the meantime

Two guards in this repo, both of which exist because of this incident:

- `hack/benchmark/harvest_run.py` replaces step_09 for the large file. Its stage order **is** the safety
  property: **scan pod-side → fetch → verify → only then delete**. It extracts the ~31 KB completion-token
  vector inside the pod (`completion_tokens_scan.py`, recording `bytes_scanned` = the size of the file it
  read) and never moves the gigabytes at all unless explicitly asked.
- `hack/benchmark/pvc_gate.py::classify()` will only call a PVC file reclaimable if the host holds either
  a **byte-identical** copy or a vector whose recorded `bytes_scanned` equals the PVC file's current size.
  Existence is not evidence. Its docstring names this incident so the check does not get "simplified"
  back into an existence test.
