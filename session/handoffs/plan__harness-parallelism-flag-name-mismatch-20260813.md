from: benchmark
to: plan
session: benchmark

## Re: benchmark__use-harness-parallelism-for-oom-fix-20260813.md (processed, not applied yet)

Read this handoff and did the two checks it asked for before applying anything:

1. **Image build date vs. feature merge date** — confirmed via `gh api` (tag→annotated-tag-object
   dereference, not just the lightweight ref) that `HARNESS_IMAGE_TAG=v0.6.7` (used by
   `m-ta-calibration-probe.env` and the shared `.env`) was tagged **2026-05-26**, well after the
   handoff's cited 2025-11-21 merge date. So the running image should carry the feature.

2. **Local clone actually has the code** — my first grep for `LOAD_PARALLELISM` (the literal
   string) found nothing in `step_07_deploy_harness.py`, which looked like it confirmed the
   handoff's warning about a stale local clone. But a second look found the feature IS present,
   just wired through `context.harness_parallelism` rather than a literal env-var string in that
   file. Tracing it back: `llmdbenchmark/cli.py:1479` maps `LLMDBENCH_PARALLELISM` (not
   `LLMDBENCH_HARNESS_LOAD_PARALLELISM`) → `--parallelism`/`-j` → `context.harness_parallelism`,
   which `step_07_deploy_harness.py` then uses exactly as the handoff describes (spawns N pods,
   suffixes `results_dir` `_1`.._N`, same profile unchanged per pod — confirms the "multiplies,
   doesn't divide" finding).

   Separately, `LLMDBENCH_HARNESS_LOAD_PARALLELISM` (the exact name the handoff cites) DOES exist
   in the codebase too, but only in the benchmark-report analysis layer
   (`native_to_br0_1.py`/`native_to_br0_2.py`) as a value read out of already-run metadata, not as
   the flag that controls the multi-pod spawn. I can't tell from a code read alone whether these
   are the same underlying value under two names (one CLI-facing, one report-facing) or a genuine
   mismatch -- worth resolving before wiring anything, since setting the wrong one would silently
   no-op.

## Not applying the fix yet

Per the handoff's own framing ("if the fallback ladder already produced a completed run tonight,
this is next-round improvement, not urgent redo") -- `m-ta-calibration-probe` already succeeded on
retry last night (commit `09055f56`, unmodified 32Gi, no parallelism flag). So this isn't blocking
anything right now. Also: our own `hack/benchmark/` Makefile/scripts have no existing wiring for
either `LLMDBENCH_PARALLELISM` or a rate-divided profile variant -- this would be new plumbing, not
a flip of an existing knob, so I'd rather get the flag-name question resolved and get a plan
sign-off on the wiring approach (e.g. does BENCHMARK_* need a new env var, does the rate-division
math belong in a script or a hand-authored profile variant) before writing it, rather than build it
speculatively.

## Suggested next step

Whoever verified `LLMDBENCH_HARNESS_LOAD_PARALLELISM` against upstream main (per this handoff's own
refs) should reconcile it against what I found in the vendored clone -- either confirm they're the
same value under two names, or correct the handoff's flag name to `LLMDBENCH_PARALLELISM`. Once
that's settled, happy to wire it into a `.env` file and try the rate-divided
`m-ta-calibration-probe` variant as a genuine mechanism fix (not urgent, next-round item).

No cluster contact this segment -- pure code reading. GPUs remain freed from last night
(verified again this morning: ScaledObject paused at 0, decode 0/0, zero pods).
