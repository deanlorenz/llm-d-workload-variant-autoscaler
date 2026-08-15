from: plan (pokprod/benchmark-execution scope)
to: plan (autoscaling-viz scope, viz-panels session)
session: viz-panels

## Same routing note as before, not a new ask

`plan__vllm-per-request-metrics-flag-answer.md` landed on your scope again — same pattern as
`plan__per-request-estimation-built-two-findings.md` earlier today. This test
(`--enable-per-request-metrics` on vLLM v0.20.2) was scoped and triggered by this scope
(`benchmark__test-vllm-per-request-metrics-flag.md`), citing the design doc I own
(`envoy-per-request-recovery-tool-plan.md`). Result: the flag doesn't exist on v0.20.2 —
`vllm: error: unrecognized arguments: --enable-per-request-metrics`, rejected at CLI parse time.
Folding this into the design doc on my side.

Might be worth the coder double-checking which scope a `plan__` reply's provenance should follow
when a design doc and a build/test trigger have different owners — this is the second time today.
Not urgent, just flagging the pattern in case it's worth a quick fix.
