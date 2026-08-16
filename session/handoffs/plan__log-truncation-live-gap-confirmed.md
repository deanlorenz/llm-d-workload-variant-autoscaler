from: benchmark
to: plan (viz-panels scope)
session: benchmark

## Answer: this is a LIVE gap, not something already covered pending verification

Checked directly, not inferred. The gateway-log-follower WAS running during this run (deployment
up since ~2026-08-08, well before dean-20260813-005321-943) and its PVC capture
(/requests/gateway-logs/igw-access.log on the cluster) has the COMPLETE trace -- filtering to the
exact harness_start/stop window gives 21,122 completion requests, matching the profile's expected
21,120 almost exactly. The 1,732-request gap only exists in the HARVESTED copy
(logs/igw_pods.log.gz under the run directory), not in reality.

Root cause, confirmed by reading the harvest code directly: capture_infrastructure_logs /
capture_label_logs in llm-d-benchmark/llmdbenchmark/utilities/kube_helpers.py runs a plain
`kubectl logs -l app.kubernetes.io/component=inference-gateway` -- this reads the gateway pod's
own container stdout, exactly the rotation-vulnerable path the follower exists to bypass. The
follower's durable PVC capture and the post-run harvest are two fully independent paths sourcing
the same access log; nothing wires the harvest to read from (or fall back to) the follower's copy.
T9 landing added a correct second path without connecting it to the one that actually gets used.

## Not fixed -- a real design/wiring decision, yours to scope

Options I can see but haven't picked between: (a) point the harvest at the follower's PVC file
instead of `kubectl logs` on the gateway pod, (b) keep both but fall back to the follower's copy
when the harvest's count doesn't match the harness's own attempted total, (c) something upstream
in kube_helpers.py vs a benchmark-side post-step. Not mine to decide unilaterally mid-
investigation.

## Practical note

The follower's PVC file has the complete trace for dean-20260813-005321-943 right now. If closing
estimate_per_request.py's stage-0 gap matters before the wiring fix lands, a one-off hand-harvest
of that file for this specific run is possible -- not done, flagging as an option, not assuming
you want it.
