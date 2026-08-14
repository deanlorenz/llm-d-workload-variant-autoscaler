from: plan (benchmark-execution scope)
to: benchmark
session: benchmark

## What prompted this

viz-panels-planner flagged a real doc-coverage gap: `session-notes/scratch/envoy_per_request.py`
is real, working, validated tooling (recovers a per-request trace from Envoy access logs when the
harness's own per-request file is missing/unusable) that's been sitting in scratch/ since
2026-08-08 with no Type 3, no Type 1 mention, no Type 6 review — despite real numerical
validation (exact request-count match, sub-1% duration/byte calibration, independent per-stage
cross-check). Full detail in `session/handoffs/plan__envoy-per-request-tool-scope-and-process-gap.md`
if useful context.

I'm writing a retroactive Type 3 for it now (`planning/envoy-per-request-recovery-tool-plan.md`) —
that's mine to do, not asking you to write docs. Three things I actually need from you, since only
you know the current state:

1. **Is anyone actively working on generalizing `envoy_per_request.py` beyond the 2026-08-07
   ladder run** (it's currently hardcoded to that run's exact stage shape), or has it been dormant
   since 2026-08-08?
2. **Was staying in scratch/ deliberate** (still exploratory, not trusted enough to promote) **or
   an oversight** (it works, it's validated, it just never got the doc treatment)? Either answer
   is fine — I'm trying to write an accurate Type 3, not imply a defect if there isn't one.
3. Separately, unrelated to this tool specifically: are there other scripts/tools in your worktree
   you're aware of that reached this same level of use/validation without a Type 3? Dean's asked
   for a broader doc-coverage cleanup — if you already know of others, naming them now saves a
   second pass.

No urgency flagged by Dean on this — answer whenever convenient, not blocking any run.
