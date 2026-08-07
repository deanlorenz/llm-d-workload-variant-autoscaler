"""Print a compact cross-stage sample of the corrected benchmark reports.

The v0.2 reports are ~20 KB of nested YAML each; dumping them is unreadable and
dumping one stage's head hides the thing you actually want, which is how the
numbers move across stages. This pulls the handful of scalars that matter and
lays the three stages side by side.

Deliberately dependency-free (no PyYAML): it walks indentation, because the
reports are machine-generated with stable two-space nesting and the alternative
is making a results *sample* depend on a package install.

Usage:
  python3 sample_report.py <results-dir>
"""

import sys
from pathlib import Path

# (label, dotted path into the report) -- dotted path is matched as an ordered
# sequence of keys by indentation depth, so sibling keys with the same leaf name
# under different parents don't collide.
WANTED = [
    ("KV util (mean)", "results.observability.epp_pool_avg_kv_cache_utilization.aggregated.mean"),
    ("KV util (p99)", "results.observability.epp_pool_avg_kv_cache_utilization.aggregated.p99"),
    ("ready pods (mean)", "results.observability.epp_pool_ready_pods.aggregated.mean"),
    ("running reqs (mean)", "results.observability.epp_pool_avg_running_requests.aggregated.mean"),
    ("queue size (mean)", "results.observability.epp_pool_avg_queue_size.aggregated.mean"),
    ("requests total", "results.request_performance.aggregate.requests.total"),
    ("failures", "results.request_performance.aggregate.requests.failures"),
    ("output_len (mean)", "results.request_performance.aggregate.requests.output_length.mean"),
    ("req latency (mean)", "results.request_performance.aggregate.latency.request_latency.mean"),
    ("req latency (p95)", "results.request_performance.aggregate.latency.request_latency.p95"),
    ("TTFT (mean)", "results.request_performance.aggregate.latency.time_to_first_token.mean"),
    ("TTFT (p95)", "results.request_performance.aggregate.latency.time_to_first_token.p95"),
    ("TPOT (mean)", "results.request_performance.aggregate.latency.time_per_output_token.mean"),
    ("request rate", "results.request_performance.aggregate.throughput.request_rate.mean"),
    ("output tok/s", "results.request_performance.aggregate.throughput.output_token_rate.mean"),
    ("total tok/s", "results.request_performance.aggregate.throughput.total_token_rate.mean"),
]


def flatten(path: Path) -> dict[str, str]:
    """Map dotted key path -> scalar value, by tracking the indent stack."""
    out: dict[str, str] = {}
    stack: list[tuple[int, str]] = []
    for raw in path.read_text().splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip())
        line = raw.strip()
        if line.startswith("- ") or ":" not in line:
            continue  # list items: the aggregated/* block already has what we need
        key, _, val = line.partition(":")
        key, val = key.strip(), val.strip()
        while stack and stack[-1][0] >= indent:
            stack.pop()
        dotted = ".".join([k for _, k in stack] + [key])
        if val:
            out[dotted] = val
        stack.append((indent, key))
    return out


def fmt(v: str | None) -> str:
    if v is None:
        return "--"
    try:
        f = float(v)
    except ValueError:
        return v
    if f == int(f) and abs(f) < 1e6:
        return str(int(f))
    return f"{f:.4g}"


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    rdir = Path(sys.argv[1])
    reports = sorted(rdir.glob("benchmark_report_v0.2,_stage_*_lifecycle_metrics.json.yaml"))
    if not reports:
        print(f"no v0.2 stage reports under {rdir}")
        return 1

    stages = [(r.name.split("stage_")[1].split("_")[0], flatten(r)) for r in reports]

    w = max(len(lbl) for lbl, _ in WANTED) + 2
    hdr = "".join(f"{'stage ' + s:>16}" for s, _ in stages)
    print(f"{'metric':<{w}}{hdr}")
    print("-" * (w + 16 * len(stages)))
    for label, dotted in WANTED:
        row = "".join(f"{fmt(d.get(dotted)):>16}" for _, d in stages)
        print(f"{label:<{w}}{row}")

    # The token correction is the reason these reports exist in v0.2 form at all,
    # so surface its provenance rather than leaving it buried at the file tail.
    print()
    for key in ("true_output_len_mean", "reported_output_len_mean", "inflation_factor",
                "n_requests", "source", "extracted_from"):
        vals = {d.get(f"output_token_correction.{key}", d.get(key)) for _, d in stages}
        print(f"  correction.{key:<26} {' / '.join(fmt(v) for v in sorted(vals, key=str))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
