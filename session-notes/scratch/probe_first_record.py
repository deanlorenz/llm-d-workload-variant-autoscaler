#!/usr/bin/env python3
"""Compare, per request, the three token counts inference-perf has in hand:
  server_usage.completion_tokens  (vLLM ground truth)
  output_tokens                   (re-tokenized whole text -- what metrics use)
  len(output_token_times)         (one timestamp per streamed SSE chunk)

Decides whether inter_token_latency is affected by the re-tokenization bug.
Streams a bounded prefix; never loads the 4.2 GB file.

This is the evidence behind the key claim in
session-notes/issues/inference-perf-output-token-inflation.md: it disproved the
hypothesis that the per-token TIMELINE was still correct and only the COUNT was
inflated. len(output_token_times) == output_tokens exactly for all 12 records, so
the timeline is over-sampled in lockstep and ITL cannot be repaired downstream.

Usage:
  python3 probe_first_record.py <path-to-per_request_lifecycle_metrics.json> [bytes]
"""
import json
import re
import sys

path = sys.argv[1]
limit = int(sys.argv[2]) if len(sys.argv) > 2 else 40 << 20  # 40 MiB prefix

buf = open(path, "rb").read(limit).decode("utf-8", errors="replace")

# Records are objects in a top-level array; find balanced objects that contain
# server_usage, decoding each one individually.
rows = []
dec = json.JSONDecoder()
i = 0
while len(rows) < 12:
    j = buf.find('{"info"', i)
    if j < 0:
        j = buf.find("{", i)
        if j < 0:
            break
    try:
        obj, end = dec.raw_decode(buf, j)
    except ValueError:
        i = j + 1
        continue
    i = end
    info = obj.get("info") or {}
    ri = info.get("response_info") or {}
    su = ri.get("server_usage") or {}
    ott = ri.get("output_token_times") or []
    if su or ott:
        rows.append({
            "completion_tokens": su.get("completion_tokens"),
            "output_tokens": ri.get("output_tokens"),
            "len_output_token_times": len(ott),
        })

if not rows:
    print("no records decoded from the prefix", file=sys.stderr)
    sys.exit(1)

print(f"{'completion_tokens':>18} {'output_tokens':>14} {'len(times)':>11}")
for r in rows:
    print(f"{str(r['completion_tokens']):>18} {str(r['output_tokens']):>14} {r['len_output_token_times']:>11}")

ct = [r["completion_tokens"] for r in rows if isinstance(r["completion_tokens"], int)]
ot = [r["output_tokens"] for r in rows if isinstance(r["output_tokens"], int)]
lt = [r["len_output_token_times"] for r in rows]
print()
if ct and lt:
    print(f"len(output_token_times) == completion_tokens ?  {all(a == b for a, b in zip(lt, ct))}")
if ct and ot:
    print(f"output_tokens           == completion_tokens ?  {all(a == b for a, b in zip(ot, ct))}")
    print(f"mean inflation output_tokens/completion_tokens: {sum(ot)/sum(ct):.4f}")
if lt and ot:
    print(f"len(output_token_times) == output_tokens     ?  {all(a == b for a, b in zip(lt, ot))}")
