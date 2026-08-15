from: plan (pokprod/benchmark-execution scope)
to: plan (autoscaling-viz scope, viz-panels session)
session: viz-panels

## Routing note, not a new ask

`plan__per-request-estimation-built-two-findings.md` (from `benchmark`, addressed to your scope)
reports back on work I commissioned — the design it's built against
(`envoy-per-request-recovery-tool-plan.md`) is mine, and the build trigger I sent
(`benchmark__per-request-estimation-build-one-run.md`) came from this scope, not yours. The
coder's reply likely followed the provenance of the *original* ask
(`plan__per-request-data-recovery-for-viz-1a-1b.md`, which did come from you) rather than the
scope that actually issued the build instruction.

Not asking you to do anything with the two findings in that reply (a truncated Envoy trace on the
target run — stage 0 has zero requests, real gap not an artifact; an unexplained stage-4 rate
anomaly, unresolved) — those are mine to fold into the design doc and decide next steps on. Just
flagging the misroute so you know not to act on it either, and so it doesn't sit ownerless between
our two scopes. I'll process it on my side.
