# inference-perf: reported output-token metrics are inflated because `output_len` re-tokenizes generated text

**Status:** draft, not filed. Target: `kubernetes-sigs/inference-perf`.
Separate defect from [`llm-d-benchmark-step09-silent-truncation.md`](llm-d-benchmark-step09-silent-truncation.md),
which is an llm-d-benchmark bug found in the same investigation. Do not conflate them.
**Evidence version:** inference-perf `e250731ce8944f8ab76ece860e0960c6fa39b606`
(recorded as `harness_version` in the run metadata — this is the exact build that produced the numbers below).
**Evidence run:** `dean-20260803-052634-197` / `inference-perf-1785724033-d5lhav_1`, 7919 requests,
vLLM `v0.20.2`, `unsloth/Meta-Llama-3.1-8B-Instruct`, H100-80GB-HBM3.

---

## One-sentence version

inference-perf asks the server for token usage, receives it, stores it, compares it against its own
re-tokenized count, finds a disagreement on **100% of requests**, publishes the disagreement count —
and then reports every output-token-derived metric from the re-tokenized count anyway.

## Root cause

`output_len` is derived by **detokenize → re-tokenize round-trip** rather than taken from the server:

`inference_perf/apis/completion.py` (same in `chat.py`), both the streaming and non-streaming paths:

```python
output_len = tokenizer.count_tokens(output_text)
```

For most workloads the round-trip is lossless and this is harmless. It is **not** lossless for
`data.type: random` with `ignore_eos: true`: the generated text is random-token soup, and detokenizing
then re-encoding it fragments tokens, so `count_tokens(output_text) > true generated tokens`.

The server's exact count is already in hand. inference-perf explicitly requests it —

```python
**({"stream_options": {"include_usage": True}} if streaming else {}),
```

— unpacks it, and stores it on the response info:

```python
output_text, chunk_times, raw_content, response_chunks, server_usage = await parse_sse_stream(...)
...
server_usage=server_usage,
```

`inference_perf/reportgen/base.py` then *reads* it, but only to count disagreements:

```python
expected_output_tokens = (
    m.info.response_info.server_usage.get("completion_tokens")
    if m.info.response_info.server_usage else None
)
...
if expected_output_tokens is not None and accumulated_tokens != expected_output_tokens:
    mismatched_requests += 1
...
"token_count_mismatches": mismatched_requests,
```

Every reported metric is still computed from `response_info.output_tokens` (the re-tokenized value).
So the ground truth is fetched, compared, found wrong, counted, published — and discarded.

**The mismatch counter fired on every single request:** `"token_count_mismatches": 7919` out of 7919
successes (`summary_lifecycle_metrics.json`). inference-perf already knows its own numbers are wrong.

## Exact measured behavior

Run-wide, n=7919: reported mean output length **905.481** vs server-reported mean **512.100** →
**inflation 1.7714×**. Per-stage: 1.7682 / 1.7815 / 1.7645.

Per request, the three counts inference-perf has simultaneously in hand (first 12 records):

| `server_usage.completion_tokens` | `output_tokens` | `len(output_token_times)` |
|---|---|---|
| 516 | 1018 | 1018 |
| 481 | 733  | 733  |
| 503 | 755  | 755  |
| 510 | 1019 | 1019 |
| 515 | 1030 | 1030 |
| 529 | 1057 | 1057 |
| 517 | 1034 | 1034 |
| 495 | 968  | 968  |
| 497 | 987  | 987  |
| 512 | 855  | 855  |
| 481 | 953  | 953  |
| 499 | 998  | 998  |

Two facts worth separating, because they have different consequences:

1. `output_tokens != completion_tokens` on every request — the count is inflated (~1.88× over these 12).
2. **`len(output_token_times) == output_tokens` on every request, exactly.** The per-token *timeline* is
   generated from the re-tokenization too, so it has one entry per *re-tokenized* token rather than per
   *generated* token. The timeline is over-sampled in lockstep with the count.

Fact 2 is the non-obvious one: it means the latency timeline is not an independent, still-correct
measurement that could be used to recover the truth. It is inflated the same way.

## Impact on reported metrics

Let `f = true_mean / reported_mean` (= 0.5646 for this run).

| Metric | Direction | Why |
|---|---|---|
| `output_len` summary | inflated ×1/f | computed from `output_tokens` |
| `output_tokens_per_sec` | inflated ×1/f | numerator is `output_tokens` |
| `total_tokens_per_sec` | inflated (output portion only) | input portion is correct |
| `normalized_time_per_output_token` | **deflated ×f** | `(end - start) / output_tokens`, inflated denominator |
| `time_per_output_token` | **deflated ×f** | `duration / (output_tokens - 1)` |
| `inter_token_latency` | **deflated ×f** | pairwise deltas over an over-sampled timeline |

Unaffected and trustworthy: request rate, input length, request latency, TTFT
(`output_token_times[0] - start_time` — the first entry's timestamp is real regardless of how many
entries follow).

Note the signs are opposite: throughput reads ~1.77× too good while per-token latency reads ~1.77× too
good as well (smaller = better). Both errors flatter the system under test, which is the worst
direction for a benchmark.

## Reproduction

Any `data.type: random` + `ignore_eos: true` profile against a vLLM endpoint. Then compare, in the
per-request output, `info.response_info.output_tokens` against
`info.response_info.server_usage.completion_tokens`. Or just read `token_count_mismatches` in the
summary — if it equals the success count, every metric in the table above is wrong.

## Suggested fix

Prefer the server's count when present, fall back to re-tokenization when absent:

1. Set `response_info.output_tokens` from `server_usage.completion_tokens` when it is available, and
   keep `count_tokens(output_text)` only as the fallback. This alone fixes the count, the rates, and
   NTPOT/TPOT.
2. `inter_token_latency` needs more than a count fix, because the timeline itself has the wrong
   cardinality. Emitting one timestamp per SSE chunk as actually received — rather than one per
   re-tokenized token — makes the timeline match the generated tokens and fixes ITL at the source.
3. The non-streaming path never captures `server_usage` at all (only the streaming branch does), so a
   complete fix should capture usage there too.
4. Consider promoting `token_count_mismatches > 0` from a silent field to a warning. It is currently
   the only published signal that the report is wrong, and it is easy to miss.

Backwards compatibility: this changes reported numbers for affected workloads. That is the point, but
it is worth calling out in a release note, since it will look like a performance regression in
`output_tokens_per_sec` when it is actually the removal of an inflation.

## What we did downstream in the meantime

`llm-d-benchmark` fork (`deanlorenz/llm-d-benchmark`, branch `wva-ta-benchmark`) carries
`llmdbenchmark/analysis/output_token_correction.py`, which recomputes the true output-length
distribution from `server_usage.completion_tokens` and rescales the affected fields in the generated
Benchmark Report v0.2 YAMLs (BR0.2 names them `output_token_rate` / `total_token_rate`). It is a
post-hoc repair of the report, not a fix — it cannot recover a correct ITL *distribution*, only rescale
the aggregate, because the underlying timeline resolution is already lost.

This is why the upstream fix matters: item 2 above is not something a downstream consumer can do.
