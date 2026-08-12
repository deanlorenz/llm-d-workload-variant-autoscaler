from: plan
to: benchmark
session: inference-perf OOM — root cause found (item 1), items 2/3 verified absent, item 4 left open

## Item 1 — answered, source-verified, not inferred

Read the actual `inference-perf` source at `/home/dean/code/llm-d/inference-perf` (a real local clone,
current — not vendored into this repo, comes baked into the harness image per
`hack/benchmark/.env:69`). The memory model is exactly what Dean suspected, and it's structural, not a
tuning problem:

**Every request's full JSON body and every response's full text body are held in memory for the
entire run, in one unbounded list, never flushed until the run ends.**

- `inference_perf/client/modelserver/openai_client.py:170,182`: `request_data = json.dumps(payload)`
  (the full request JSON, prompt included) and `response_content = await response.text()` (the full
  response text, completion included) — both captured **per request**, at full size.
- Both go into a `RequestLifecycleMetric` (`apis/base.py:36-44`) as `request_data: str` /
  `response_data: Optional[str]` — the complete text, not a summary or a length.
- `MultiprocessRequestDataCollector.collect_metrics()` (`client/requestdatacollector/multiprocess.py:38-58`)
  drains a shared `mp.JoinableQueue` and does `metrics.append(item)` — **one Python list, one process,
  every metric object for the whole run, held until `queue.put(None)` signals completion** (`main.py`'s
  `start()` context manager). Workers don't each hold a duplicate copy — they push through the queue —
  but the single collector's list is exactly this run's failure mode: nothing is written to disk or
  released mid-run.

**Why this workload specifically triggers it:** ~4096in/~1024out tokens × ramping to 20 req/s over
12 minutes means the accumulated list is holding roughly (5000+ tokens' worth of text, twice — request
and response) **× thousands of requests**, growing monotonically, with no cap and no periodic flush. A
shorter-token or lower-rate profile would hit the same structural limit later, not avoid it. This is
consistent with Dean's read ("inference-perf itself can't handle this workload shape/rate") and is now
source-confirmed rather than symptom-inferred.

**No code change proposed here** — that's upstream `kubernetes-sigs/inference-perf`, not this repo, and
fixing it (streaming metrics to disk instead of accumulating, or bounding the list) is a real design
question for whoever owns that decision, not a quick patch. Flagging as background for whatever mitigation
you choose on the fallback ladder (memory bump is the correct near-term lever given this root cause — it
buys headroom against a growing-but-bounded-by-run-length list, rather than fixing an actual leak).

## Item 2 — confirmed absent, not just "as far as I've seen"

Checked directly: no `kubectl top`, no cAdvisor reference, no `container_memory` query anywhere in
`hack/benchmark/*.sh` or `*.py`. Your read was right — nothing today watches the harness pod's own
resource usage, only vLLM pods. Given item 1's finding (memory grows monotonically with elapsed
run-time × request volume, not with a load spike), a live memory-vs-time correlation would show a
smooth ramp tracking the accumulated list size, not a stage-transition spike — worth setting
expectations before adding the monitoring, since the interesting signal is "did it cross the limit
before the run finished," not "which stage caused a jump."

## Item 3 — searched, not found; flagging the search as inconclusive rather than definitive

Checked `inference_perf/config.py` for a pod-count/replica knob, and grepped `llm-d-benchmark`'s
`setup/run.sh`/`env.sh`/`functions.sh` for anything resembling a multi-harness-pod flag (`num_pods`,
`replicas`, `LLMDBENCH_RUN_EXPERIMENT_*_COUNT`, launcher-count patterns). **Found nothing in either
codebase.** The `LLMDBENCH_RUN_EXPERIMENT_LAUNCHER` var I did find is a boolean per-pod flag, not a
count. Two possibilities, and I can't distinguish them from search alone: (a) Dean is recalling a
pattern that doesn't exist as a first-class flag — running `run.sh` twice by hand against the same
target would produce two independent, uncoordinated harness pods without any dedicated flag — or (b)
it exists somewhere I didn't search (a different version, a doc, a script I didn't check). Worth Dean
confirming from memory where he saw this before spending more search time on it.

## Item 4 — left open, as asked

Not resolved here — a design-direction question, not mine to decide unilaterally. Flagging one thing
item 1 makes relevant to it: if inference-perf's own memory model is what's failing, "generate load
directly instead of through inference-perf" sidesteps this specific failure mode by construction (no
third-party accumulator to work around), which is a real point in favor of the direction, separate from
the request-mix-control motivation already in the handoff.

## Not done, and why

Did not read `inference_perf/loadgen/load_generator.py` or the datagen modules — item 1's answer didn't
need them once the collector's accumulation was confirmed as the mechanism, and reading further would
be answering a question nobody asked. Did not check whether inference-perf has a `--max-metrics` or
similar cap in a newer/different version than what's cloned locally — worth a quick upstream-changelog
check if a mitigation beyond "bump memory" is wanted later.
