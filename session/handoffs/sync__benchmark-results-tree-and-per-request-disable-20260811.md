from: benchmark
to: sync
session: benchmark-results-tree-and-per-request-disable-20260811

## What changed

Seven local commits on `benchmark` across two sessions (2026-08-11 night, 2026-08-12 resume), all
DCO-signed, nothing pushed (branch now 23 commits ahead of `origin/benchmark`). Full results-tree
build is now complete except live-run verification. Read in order — the third supersedes the
second's approach:

1. **`500b675f`** — disables `report.request_lifecycle.per_request` (true → false) in 4 of 5
   `inference-perf` workload templates (`ta_autoscale_dwell.yaml.in`, `ta_autoscale_staircase.yaml.in`,
   `ta_autoscale_ladder.yaml.in`, `ta_calibration_probe.yaml.in`), per Dean's decision recorded in
   `planning/ta-pokprod-campaign-20260810-results.md` § *Per-request data*. Deliberate, documented
   exception: `ta_prefill_knee.yaml.in` keeps `per_request: true` — its own docstring says per-request
   ITL is the actual measurement for that probe, and its sizing math shows a comfortable margin
   (~9.0 GB worst case over ~17 min against a reclaimed 20Gi PVC) unlike the dwell profile that
   OOM'd at ~11.3 GB against an ~11.9 GB boundary.
2. **`334012c4`** (superseded by `8f55cbfa` — left in git history, not amended) — originally
   relocated each run's results via `mv` from the repo-root `dean-<ts>-<pid>/` into
   `runs/<run-id>/{config,raw,viz}`.
3. **`8f55cbfa`** — the corrected approach. `Makefile`'s `BENCHMARK_WORKSPACE` now defaults to
   `$(CURDIR)/runs` instead of `$(CURDIR)`, so the harness writes its own `$USER-<ts>-<pid>/`
   directory **natively** under `runs/` — no copy, no move. Also fixes a real bug: the old
   `dean-*/` gitignore glob only matched Dean's own username. `.gitignore` allowlists `config/`,
   `viz/`, `REPORT.md` per run directory rather than carving out a `raw/` subfolder.
4. **`75dde31a`** — `benchmark/tools/` symlink to `hack/benchmark` (relative path, not `../hack/benchmark`
   — caught a broken first attempt before committing).
5. **`955291a7`** — new `write_report.py`: wraps `postprocess.py`'s existing metrics table with
   relative links into a run's `config/`/`viz/`/raw results, writing `runs/<run-id>/REPORT.md`.
   Same commit fixes a real path bug in `run_cell.sh` (`cut -d/ -f1` → `-f1-2`) that would have
   silently broken the config-copy on every future run — caught before any live run hit it.
6. **`6a3dc448`** — stopped duplicating `analyzer-config.txt`/`images.txt`/`scaledobject.yaml` into
   `session-notes/campaign-runs/<cell>/`; now `mv`, not `cp`, into `runs/<id>/config/` once the run
   directory is known. `campaign-runs/<cell>/` keeps only genuinely campaign-scoped bookkeeping
   (`results-dir.txt`, `run.log`, `controller.log`).
7. **`df320c94`** — new `prune_run.py`: conservative, SHA-256-based pruning of
   `setup/commands/*_stdout.log` files confirmed byte-identical to a file already preserved under
   `results/*/logs/` (the pod-log follower's raw output gets captured twice by the harness's own
   pipeline). Dry-run by default; `--apply` to delete. Verified on real 2026-08-10 data: 5 files,
   51.2 MB, all genuine duplicates.

Preceding all seven, a read-only per-request discovery task (no commits) corrected two claims in the
results doc: (1) `logs/igw_pods.log` DOES carry per-request Envoy access-log data (the "just Istio
noise" claim was a sampling error, and this was actually already validated on this branch back in
commit `2e7cbf4a`); (2) EPP's `kv-cache-utilization-scorer`/`prefix-cache-scorer` "Calculated score"
lines do NOT carry raw pod state — that's on a different event, `"Before running filter plugins"`.
Also confirmed `vllm:time_to_first_token_seconds`/`vllm:inter_token_latency_seconds` histograms are
already scraped into `metrics/raw/*`, no new collection needed for TTFT/ITL distributions.

Full detail: `session/status/benchmark.md` §20.24 (discovery write-up), §20.25 (original relocation
— superseded), §20.26 (corrected relocation), §20.27 (the four remaining Part-B items — read this
one for the fullest picture). Handoff `benchmark__viz-model-review-and-per-request-discovery.md` is
`.DONE`.

## Verification done / not done

Every change this session was verified against a scratch copy of real 2026-08-10 campaign data, or a
scratch git tree for the `.gitignore` allowlist — never against the live campaign directories
themselves. `prune_run.py` additionally cross-checked with independent `md5sum` spot-checks before
trusting `sha256sum` inside the script. `bash -n`/`py_compile` clean on all edited/new scripts. No Go
code touched; `gofmt`/`go build` clean; `make test`/`make lint` not re-run.

**Not yet exercised against a live `make benchmark-run`** — no cluster access either session, and
Dean explicitly held off any cluster run both nights. This is the one real gap before trusting the
whole tree (workspace relocation, config handoff, REPORT.md generation, pruning) on the next actual
campaign.

## Update CURRENT.md

Under the benchmark entry in § Recent activity: the full results-tree build from the campaign
results doc's Folder Structure section is now code-complete — `BENCHMARK_WORKSPACE=runs/`,
`tools/` symlink, per-run `config/`+`viz/`+`REPORT.md`, per-request collection disabled (one
deliberate exception), a conservative pruning script, and the `campaign-runs/` duplication removed.
**Live-run verification is the one remaining gap** — nothing has touched a real cluster or a live
harness run; everything is scratch-tree/dry-run verified. Seven commits:
`500b675f`, `334012c4` (superseded), `8f55cbfa`, `75dde31a`, `955291a7`, `6a3dc448`, `df320c94`.
Nothing pushed.

## Open questions / follow-ups

- Migrating the 7 pre-existing 2026-08-10 campaign directories from the repo root into `runs/` (or
  deciding to leave them permanently) — not decided.
- Next live campaign run is the natural point to verify the whole tree end-to-end: workspace
  relocation, the config handoff (including the path-bug fix), REPORT.md rendering with real data,
  and the pruning script against a genuinely fresh run (not a scratch copy of an old one).
