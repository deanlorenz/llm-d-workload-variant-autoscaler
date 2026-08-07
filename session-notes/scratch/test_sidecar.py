#!/usr/bin/env python3
"""Exercise every input path of output_token_correction against real 08-03 data.

Validated 9/9 on 2026-08-07 against the fork's modified
llmdbenchmark/analysis/output_token_correction.py (sidecar fallback).

The decisive assertion is case 3's: the 31 KB sidecar vector and the 4.2 GB raw
per-request file must produce IDENTICAL numbers. They do -- per-stage inflation
1.7682 / 1.7815 / 1.7645, mean 1.7714.

VECTOR points at the sidecar filed next to the experiment it was scanned from, so
this test survives a cold resume. It was originally produced by
hack/benchmark/completion_tokens_scan.py running inside the data-access pod; its
recorded bytes_scanned (4,204,290,876) equals the source file's size exactly,
which is what makes it a complete scan rather than a partial one.
"""
import json
import shutil
import sys
from pathlib import Path

REPO = Path("/home/dean/code/llm-d/llm-d-workload-variant-autoscaler/benchmark")
sys.path.insert(0, str(REPO / "llm-d-benchmark"))

import yaml
from llmdbenchmark.analysis.output_token_correction import (
    _MARKER,
    _TOKENS_SIDECAR,
    correct_inference_perf_output_tokens,
)

SRC = REPO / "dean-20260803-052634-197/results/inference-perf-1785724033-d5lhav_1"
RAW = SRC / "per_request_lifecycle_metrics.json"
VECTOR = SRC / "server_completion_tokens.json"
WORK = Path("/tmp/otc-cases")


class Logger:
    def __init__(self):
        self.lines = []

    def log_info(self, msg, emoji=""):
        self.lines.append(f"{emoji} {msg}".strip())


class Ctx:
    def __init__(self):
        self.logger = Logger()


def fixture(name):
    """Genuinely uncorrected v0.2 reports -- no raw file, no sidecar.

    Regenerated from the native stage JSON rather than by stripping the marker
    off the shipped v0.2 files: those were corrected IN PLACE, so a de-markered
    copy still carries the true means and would report inflation 1.0 -- passing
    the test while exercising nothing.
    """
    # Converter chosen exactly as _convert_via_api does in production, so the
    # fixture has the same shape the real reports have (request_performance,
    # not session_performance).
    from llmdbenchmark.analysis import _is_session_lifecycle_file
    from llmdbenchmark.analysis.benchmark_report.native_to_br0_2 import (
        import_inference_perf,
        import_inference_perf_session,
    )

    d = WORK / name
    if d.exists():
        shutil.rmtree(d)
    d.mkdir(parents=True)
    for native in sorted(SRC.glob("stage_*_lifecycle_metrics.json")):
        conv = (
            import_inference_perf_session
            if _is_session_lifecycle_file(native)
            else import_inference_perf
        )
        br = conv(str(native))
        br.export_yaml(str(d / f"benchmark_report_v0.2,_{native.name}.yaml"))
    return d


def summarize(d):
    """(provenance, output_len mean, inflation) per report."""
    out = []
    for rp in sorted(d.glob("benchmark_report_v0.2,_*.yaml")):
        doc = yaml.safe_load(rp.read_text())
        m = doc.get(_MARKER)
        if not m:
            out.append((rp.name.split(",_")[1], None, None, None))
            continue
        ol = doc["results"]["request_performance"]["aggregate"]["requests"]["output_length"]["mean"]
        out.append((rp.name.split(",_")[1], m["extracted_from"], round(ol, 4), m["inflation_factor"]))
    return out


def show(case, err, ctx, d):
    print(f"\n=== {case}")
    print(f"  return: {err!r}")
    for line in ctx.logger.lines:
        print(f"  log:    {line}")
    for stage, prov, mean, infl in summarize(d):
        print(f"  {stage:38s} prov={prov} mean={mean} inflation={infl}")


fails = []


def check(cond, msg):
    print(f"  {'PASS' if cond else 'FAIL'}  {msg}")
    if not cond:
        fails.append(msg)


# ---------------------------------------------------------------- case 1
# Sidecar present, raw file absent -- the normal post-harvest run.
d = fixture("sidecar-only")
shutil.copy(VECTOR, d / _TOKENS_SIDECAR)
ctx = Ctx()
err = correct_inference_perf_output_tokens(d, ctx)
show("1. sidecar only (raw file deleted)", err, ctx, d)
s = summarize(d)
check(err is None, "returns success")
check(all(p and p.startswith("sidecar") for _, p, _, _ in s), "provenance = sidecar")
check(all(m == 512.1003 for _, _, m, _ in s), "output_len mean = 512.1003 (true)")
check(all(i > 1.7 for _, _, _, i in s), "inflation recorded ~1.77x")
audit = json.loads((d / "metrics" / "processed" / "output_token_correction.json").read_text())
check(audit["n_requests"] == 7919, f"audit n_requests = 7919 (got {audit['n_requests']})")
check(audit["reports_request_total"] == 7920,
      f"audit reports_request_total = 7920 (got {audit['reports_request_total']})")
sidecar_result = s

# ---------------------------------------------------------------- case 2
# Idempotence: a second pass must be a no-op.
ctx = Ctx()
err = correct_inference_perf_output_tokens(d, ctx)
print("\n=== 2. re-run over corrected reports")
print(f"  return: {err!r}")
check(err is None and summarize(d) == sidecar_result, "second pass changes nothing")

# ---------------------------------------------------------------- case 3
# No sidecar, raw file present -- the pre-sidecar path, must still work and must
# produce the SAME numbers as case 1.
d3 = fixture("raw-only")
(d3 / RAW.name).symlink_to(RAW)
ctx = Ctx()
err = correct_inference_perf_output_tokens(d3, ctx)
show("3. raw file only (no sidecar)", err, ctx, d3)
s3 = summarize(d3)
check(err is None, "returns success")
check(all(p and p.startswith("per_request") for _, p, _, _ in s3), "provenance = per-request file")
check([(a, c, dd) for a, _, c, dd in s3] == [(a, c, dd) for a, _, c, dd in sidecar_result],
      "numbers identical to the sidecar path")

# ---------------------------------------------------------------- case 4
# Mismatched sidecar + raw file present -- refuse the sidecar, warn, fall back.
d4 = fixture("bad-sidecar-with-raw")
bad = json.loads(VECTOR.read_text())
bad["completion_tokens"] = bad["completion_tokens"] * 2  # 15838 > 7920 requests
(d4 / _TOKENS_SIDECAR).write_text(json.dumps(bad))
(d4 / RAW.name).symlink_to(RAW)
ctx = Ctx()
err = correct_inference_perf_output_tokens(d4, ctx)
show("4. mismatched sidecar, raw file available", err, ctx, d4)
s4 = summarize(d4)
check(err is None, "returns success (raw file rescues it)")
check(any("Ignoring" in ln and "not this run" in ln for ln in ctx.logger.lines), "warns about the refusal")
check(all(p and p.startswith("per_request") for _, p, _, _ in s4), "corrected from the raw file")

# ---------------------------------------------------------------- case 5
# Mismatched sidecar, raw file gone -- must ERROR, not silently pass.
d5 = fixture("bad-sidecar-no-raw")
(d5 / _TOKENS_SIDECAR).write_text(json.dumps(bad))
ctx = Ctx()
err = correct_inference_perf_output_tokens(d5, ctx)
show("5. mismatched sidecar, raw file gone", err, ctx, d5)
check(isinstance(err, str) and "not this run" in err, "returns an error string")
check(all(p is None for _, p, _, _ in summarize(d5)), "reports left uncorrected")

# ---------------------------------------------------------------- case 6
# Truncated sidecar (a partial scan) -- same refusal.
d6 = fixture("truncated-sidecar")
trunc = json.loads(VECTOR.read_text())
trunc["completion_tokens"] = trunc["completion_tokens"][:4000]  # 4000 / 7920 = 50%
(d6 / _TOKENS_SIDECAR).write_text(json.dumps(trunc))
ctx = Ctx()
err = correct_inference_perf_output_tokens(d6, ctx)
show("6. truncated sidecar, raw file gone", err, ctx, d6)
check(isinstance(err, str) and "truncated" in err, "returns a truncation error")

# ---------------------------------------------------------------- case 7
# Neither input -- "nothing to do", not an error.
d7 = fixture("neither")
ctx = Ctx()
err = correct_inference_perf_output_tokens(d7, ctx)
show("7. no usage data at all", err, ctx, d7)
check(err is None, "returns None (nothing to correct, not an error)")
check(all(p is None for _, p, _, _ in summarize(d7)), "reports untouched")

# ---------------------------------------------------------------- case 8
# Corrupt sidecar JSON, raw file gone.
d8 = fixture("corrupt-sidecar")
(d8 / _TOKENS_SIDECAR).write_text("{not json")
ctx = Ctx()
err = correct_inference_perf_output_tokens(d8, ctx)
show("8. corrupt sidecar JSON, raw file gone", err, ctx, d8)
check(isinstance(err, str) and "unreadable" in err, "returns an unreadable error")

# ---------------------------------------------------------------- case 9
# Slightly fewer values than requests (a request without server usage) -- ACCEPT.
d9 = fixture("slightly-short-sidecar")
short = json.loads(VECTOR.read_text())
short["completion_tokens"] = short["completion_tokens"][:7600]  # 96% of 7920
(d9 / _TOKENS_SIDECAR).write_text(json.dumps(short))
ctx = Ctx()
err = correct_inference_perf_output_tokens(d9, ctx)
show("9. sidecar 96% of requests (missing usage is normal)", err, ctx, d9)
check(err is None, "accepted")
check(all(p and p.startswith("sidecar") for _, p, _, _ in summarize(d9)), "used the sidecar")

print(f"\n{'ALL PASS' if not fails else str(len(fails)) + ' FAILURE(S)'}")
for f in fails:
    print(f"  FAILED: {f}")
sys.exit(1 if fails else 0)
