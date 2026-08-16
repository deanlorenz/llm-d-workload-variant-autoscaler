from: benchmark
to: plan (viz-panels scope)
session: benchmark

## Answer: --enable-per-request-metrics does NOT exist on vLLM v0.20.2 -- flag-not-recognized

Ran the exact test scoped in envoy-per-request-recovery-tool-plan.md's "Fact-finding test
scoped" section. One bare pod, image docker.io/vllm/vllm-openai:v0.20.2, 1 GPU, no gateway/EPP/
harness, --enable-per-request-metrics in its args. Literal result -- the pod never reached
serving, rejected at CLI arg-parse time before any model load:

```
WARNING 08-15 23:23:20 [argparse_utils.py:257] With `vllm serve`, you should provide the model as
a positional argument or in a config file instead of via the `--model` option. The `--model`
option will be removed in a future version.
usage: vllm [-h] [-v]
            {chat,complete,serve,launch,bench,collect-env,run-batch} ...
vllm: error: unrecognized arguments: --enable-per-request-metrics
```

No curl requests were needed -- there was no server to query. This is a definitive, falsifiable
answer per your own answer-format request: v0.20.2 predates this flag. Per-request TTFT/output-
size measurement via this flag is not available on the version this mission actually runs
(confirmed real gap vs the docs, which were checked against latest/v0.27.0, 7 minors newer).

Pod torn down immediately (oc delete), confirmed gone. No GPU held.

## Not tested, out of scope per your own framing

A newer vLLM image -- deferred by design ("if v0.20.2 already works, nothing to gain testing
newer; if it doesn't [it doesn't], that becomes the next real question, not assumed now"). Whether
to now pursue that next question is yours to scope, not mine to assume.
