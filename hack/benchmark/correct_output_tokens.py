#!/usr/bin/env python3
"""Correct inference-perf output-token metrics using server-reported usage.

inference-perf computes `output_len = tokenizer.count_tokens(output_text)` by
RE-TOKENIZING the generated text. With `data.type: random` + `ignore_eos: true`
the detokenize->retokenize round-trip does not preserve token count, so the
reported output length (and every output-token throughput derived from it) is
inflated. The vLLM server, however, reports the exact generated token count in
`usage.completion_tokens`, which inference-perf captures per request as
`info.response_info.server_usage.completion_tokens` but does not use for its
report.

This pass reads per_request_lifecycle_metrics.json, takes the true output length
from server usage (falling back to streamed-chunk count, then to the re-tokenized
value with a warning), bins requests into the load stages by arrival time, and
prints a corrected per-stage table alongside inference-perf's reported values.

Usage: uv run python correct_output_tokens.py <run_dir> [stage_seconds]
"""
import glob
import json
import statistics as st
import sys

RUN = sys.argv[1] if len(sys.argv) > 1 else "."
STAGE_SECS = int(sys.argv[2]) if len(sys.argv) > 2 else 360

matches = glob.glob(f"{RUN}/results/inference-perf-*_1")
if not matches:
    sys.exit(f"no results dir under {RUN}/results/")
RES = matches[0]

per = json.load(open(f"{RES}/per_request_lifecycle_metrics.json"))
reqs = per if isinstance(per, list) else per.get("requests", [])


def true_out(r):
    """Exact generated tokens, best source first."""
    ri = (r.get("info") or {}).get("response_info") or {}
    su = ri.get("server_usage") or {}
    if isinstance(su, dict) and su.get("completion_tokens") is not None:
        return su["completion_tokens"], "server_usage"
    rc = ri.get("response_chunks")
    if isinstance(rc, list) and rc:
        return len(rc), "chunks"
    return ri.get("output_tokens"), "retokenized(!)"


def retok_out(r):
    return ((r.get("info") or {}).get("response_info") or {}).get("output_tokens")


ok = [r for r in reqs if not r.get("error")]
if not ok:
    sys.exit("no successful requests")

t0 = min(r["start_time"] for r in ok)
stages = {}
sources = {}
for r in ok:
    idx = int((r["start_time"] - t0) // STAGE_SECS)
    tv, src = true_out(r)
    if tv is None:
        continue
    stages.setdefault(idx, []).append((tv, retok_out(r), r["start_time"], r["end_time"]))
    sources[src] = sources.get(src, 0) + 1

print(f"run: {RES.split('/')[-1]}")
print(f"true-output-token source: {sources}\n")
hdr = f"{'stage':<6}{'n':>6}{'true_out':>10}{'retok_out':>11}{'inflation':>11}{'true_tok/s':>12}{'retok_tok/s':>13}"
print(hdr)
print("-" * len(hdr))
tot_true = tot_retok = 0.0
for idx in sorted(stages):
    rows = stages[idx]
    n = len(rows)
    span = max(e for *_, e in rows) - min(s for *_, s, _ in rows)
    span = span or 1.0
    mt = st.mean(x[0] for x in rows)
    mr = st.mean(x[1] for x in rows if x[1] is not None)
    true_tps = sum(x[0] for x in rows) / span
    retok_tps = sum(x[1] for x in rows if x[1] is not None) / span
    tot_true += sum(x[0] for x in rows)
    tot_retok += sum(x[1] for x in rows if x[1] is not None)
    print(f"{idx:<6}{n:>6}{mt:>10.1f}{mr:>11.1f}{mr/mt:>10.2f}x{true_tps:>12.0f}{retok_tps:>13.0f}")
print("-" * len(hdr))
print(f"\noverall re-tokenization inflation: {tot_retok/tot_true:.2f}x  "
      f"(reported output tok/s are this many times too high)")
