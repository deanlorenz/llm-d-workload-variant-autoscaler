# Campaign scripts

Drivers for running a **set** of benchmark cells and capturing what makes each one
interpretable afterwards. The `make benchmark-*` targets run one thing; these sequence many
and record the context around each.

Run them from the repo root, not from this directory.

| Script | What it does |
|---|---|
| `run_cell.sh <env-name>` | One cell end to end: apply the pinned image, set analyzers, reset per-run state, record live config, run, **save the raw controller log**, analyse. |
| `run_all.sh` | Runs the cell list in order, then frees the GPUs. Aborts on the first cell that produces no results. |
| `watch_scaling.sh` | Samples replica target/current/ready during a run, one line per change. |
| `wait_ready.sh` | Blocks until the decode pod is ready. |
| `sanity.sh` | One in-cluster completion request: proves gateway → EPP → vLLM before spending a run. |

## Why the step order in `run_cell.sh` is what it is

**Set analyzers before the run, and let it restart the controller.** The controller holds
in-memory capacity history. Carried across cells, it makes cell N's decisions a function of
cell N-1's load, and two cells that differ only in leftover state are not a comparison.

**Save the raw controller log *before* analysis, every time.** Two independent things
destroy it otherwise: rotation (`kubectl` only serves what the buffer holds) and log-format
drift (a parser cannot read lines whose shape changed). A saved log survives both and can be
re-parsed offline; a lost window cannot be recovered at all. This is not belt-and-braces —
it is the lesson from a run whose analysis silently produced 41 rows with every analysis
field null.

**Record the live analyzer config and images into the run directory.** The pin says what was
asked for; the cluster says what ran. Only the second is evidence.

## Freeing the GPUs

`run_all.sh` releases them from an `EXIT INT TERM` trap, so it happens on success, on
failure, and on interruption — verified under a real interrupt. Leaving H100s held on a
shared cluster is the one outcome worth protecting unconditionally, which is why the release
is not merely the last line of the script.

The release is: annotate the ScaledObject `paused-replicas=0`, **then** scale the deployment
to 0. Order matters — pausing is what stops KEDA from immediately scaling it back up.

⚠️ **A paused autoscaler produces a flat replica trace that reads exactly like a legitimate
"no scaling was needed" result.** Whatever pauses it must un-pause it before the next run.
