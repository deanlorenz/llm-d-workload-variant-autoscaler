#!/usr/bin/env python3
"""Extract WVA controller decisions and V2 saturation analysis numbers from
the controller logs within a given results dir's run window. Output:

  metrics/processed/wva_target_timeseries.json

Captured per reconcile timestamp:
  - per-variant `target` (from "Applied saturation decision via shared cache")
  - model-level totalSupply / totalDemand / utilization / requiredCapacity /
    spareCapacity, plus the two decision thresholds and per-variant
    per-replica-capacity (from the saturation analyzer's "analyzer-result")

Both lines fire at the same reconcile, so we group by integer timestamp.

Note on the analyzer-result line: it fires once per registered analyzer at the
same wall-clock second (saturation and throughput), and the throughput analyzer
reports zeros until it has fitted a model. We therefore accept only the
saturation analyzer's line -- taking whichever arrives last would silently zero
out the real numbers.

Older controller builds emitted these fields on a "V2 saturation analysis
completed" line with different key names; that form is still parsed as a
fallback so previously-captured logs remain readable.

Usage
-----
  python hack/benchmark/dump_wva_target_timeseries.py \
      <results>/<treatment>_<i> -n NAMESPACE

  # Offline: parse a saved controller log instead of querying the cluster.
  python hack/benchmark/dump_wva_target_timeseries.py \
      <results>/<treatment>_<i> --log-file controller.log --no-window
"""
import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML required. pip install pyyaml", file=sys.stderr)
    sys.exit(1)


DECISION_PAT = re.compile(
    r'^(?P<ts>\S+)\t\S+\tsaturation/engine\.go:\d+\t'
    r'Applied saturation decision via shared cache\t'
    r'(?P<json>\{.*\})$'
)
ANALYZER_RESULT_PAT = re.compile(
    r'^(?P<ts>\S+)\t\S+\tsaturation/engine_v2\.go:\d+\t'
    r'analyzer-result\t'
    r'(?P<json>\{.*\})$'
)
# Legacy form, kept so logs from older controller builds still parse.
LEGACY_ANALYSIS_PAT = re.compile(
    r'^(?P<ts>\S+)\t\S+\tsaturation/engine_v2\.go:\d+\t'
    r'V2 saturation analysis completed\t'
    r'(?P<json>\{.*\})$'
)

# analyzer-result key -> output key. The controller shortened these names; the
# output schema keeps the long form so downstream consumers do not change.
ANALYSIS_KEYMAP = {
    "supply": "totalSupply",
    "demand": "totalDemand",
    "util": "utilization",
    "rc": "requiredCapacity",
    "sc": "spareCapacity",
}
# Fields that make a sample useful for analysis. A row carrying none of these is
# a bare target with no analysis attached -- see the hydration guard in main().
ANALYSIS_FIELDS = tuple(ANALYSIS_KEYMAP.values())


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("results_dir", help="Path to .../results/<treatment>_<i>")
    ap.add_argument("-n", "--namespace",
                    help="Namespace to query controller logs from. "
                         "Required unless --log-file is given.")
    ap.add_argument("--log-file",
                    help="Parse this saved controller log instead of querying "
                         "the cluster. Lets a run be re-analyzed offline with no "
                         "dependence on the log buffer still holding the window.")
    ap.add_argument("--no-window", action="store_true",
                    help="Skip the run-window timestamp filter. Use with "
                         "--log-file when the log was captured for this run and "
                         "is already scoped to it.")
    args = ap.parse_args()
    if not args.log_file and not args.namespace:
        ap.error("-n/--namespace is required unless --log-file is given")

    rd = Path(args.results_dir).resolve()
    meta_path = rd / "run_metadata.yaml"
    if not meta_path.is_file():
        print(f"ERROR: run_metadata.yaml not found in {rd}", file=sys.stderr)
        sys.exit(1)
    meta = yaml.safe_load(meta_path.read_text())

    def parse_iso(s):
        return datetime.fromisoformat(s.replace("Z", "+00:00"))

    meta_start = parse_iso(meta["harness_start"])
    meta_stop = parse_iso(meta["harness_stop"])

    # When inference-perf runs multiple iterations, run_metadata.yaml records
    # only the last iteration's start/stop. Use the raw metric scrape file
    # timestamps (which span the entire collection window across all iterations)
    # to widen the filter when they cover a longer range.
    raw_dir = rd / "metrics" / "raw"
    scrape_ts = []
    fname_pat = re.compile(r"_(\d{10})_metrics\.log$")
    if raw_dir.is_dir():
        for f in raw_dir.iterdir():
            m = fname_pat.search(f.name)
            if m:
                scrape_ts.append(int(m.group(1)))
    if scrape_ts:
        raw_start = datetime.fromtimestamp(min(scrape_ts), tz=timezone.utc)
        raw_stop = datetime.fromtimestamp(max(scrape_ts), tz=timezone.utc)
        start = min(meta_start, raw_start)
        stop = max(meta_stop, raw_stop)
    else:
        start = meta_start
        stop = meta_stop

    # Pull WVA logs covering the run window. We query "since" relative to now
    # plus a small buffer to ensure we capture the harness-start tick.
    now = datetime.now(timezone.utc)
    since_seconds = int((now - start).total_seconds()) + 90

    if args.log_file:
        logs = Path(args.log_file).read_text()
    else:
        logs = subprocess.run(
            ["kubectl", "logs", "-n", args.namespace,
             "-l", "app.kubernetes.io/name=workload-variant-autoscaler",
             f"--since={since_seconds}s", "--tail=200000"],
            capture_output=True, text=True,
        ).stdout

    if args.no_window:
        start = datetime.min.replace(tzinfo=timezone.utc)
        stop = datetime.max.replace(tzinfo=timezone.utc)

    samples_by_ts = {}
    n_analysis = 0  # saturation analyzer-result lines accepted, for the guard below

    # Bucket reconciles by integer timestamp. Some reconciles fire both
    # "V2 saturation analysis" and per-variant "Applied decision" lines at the
    # same wall-clock second; we want them merged into one sample.
    def bucket(ts_dt):
        return samples_by_ts.setdefault(int(ts_dt.timestamp()), {})

    for line in logs.splitlines():
        m = DECISION_PAT.match(line)
        if m:
            try:
                ts_dt = parse_iso(m.group("ts"))
                if ts_dt < start or ts_dt > stop:
                    continue
                d = json.loads(m.group("json"))
            except (ValueError, json.JSONDecodeError):
                continue
            variant = d.get("variant", "")
            target = d.get("target")
            if target is None:
                continue
            # KEDA ScaledObject names end in "-v2-scaler"; check for "-v2" anywhere
            # after the deployment-name prefix, not just as a suffix.
            tag = "v2" if ("-v2-" in variant or variant.endswith("-v2")) else "primary"
            bucket(ts_dt)[tag] = int(target)
            continue

        m = ANALYZER_RESULT_PAT.match(line)
        if m:
            try:
                ts_dt = parse_iso(m.group("ts"))
                if ts_dt < start or ts_dt > stop:
                    continue
                d = json.loads(m.group("json"))
            except (ValueError, json.JSONDecodeError):
                continue
            # One line per analyzer per tick. Only saturation carries the
            # capacity numbers; throughput reports zeros until it has fitted a
            # model, and would otherwise overwrite them at the same timestamp.
            if d.get("analyzer") != "saturation":
                continue
            n_analysis += 1
            b = bucket(ts_dt)
            for src, dst in ANALYSIS_KEYMAP.items():
                if src in d:
                    b[dst] = d[src]
            for k in ("scaleUpThreshold", "scaleDownBoundary"):
                if k in d:
                    b[k] = d[k]
            # Per-variant per-replica capacity. This is the field that shows the
            # capacity-history collapse behind the observed limit cycle, so it is
            # worth carrying even though it is not model-level.
            variants = d.get("variants")
            if isinstance(variants, list) and variants:
                b["variants"] = [
                    {"name": v.get("name"), "prc": v.get("prc"),
                     "role": v.get("role"), "reason": v.get("reason")}
                    for v in variants if isinstance(v, dict)
                ]
            continue

        m = LEGACY_ANALYSIS_PAT.match(line)
        if m:
            try:
                ts_dt = parse_iso(m.group("ts"))
                if ts_dt < start or ts_dt > stop:
                    continue
                d = json.loads(m.group("json"))
            except (ValueError, json.JSONDecodeError):
                continue
            n_analysis += 1
            b = bucket(ts_dt)
            for k in ANALYSIS_FIELDS:
                if k in d:
                    b[k] = d[k]

    samples = []
    for ts, b in sorted(samples_by_ts.items()):
        row = {
            "timestamp": ts,
            "primary":         b.get("primary"),
            "v2":              b.get("v2"),
            "totalSupply":     b.get("totalSupply"),
            "totalDemand":     b.get("totalDemand"),
            "utilization":     b.get("utilization"),
            "requiredCapacity": b.get("requiredCapacity"),
            "spareCapacity":   b.get("spareCapacity"),
            "scaleUpThreshold":  b.get("scaleUpThreshold"),
            "scaleDownBoundary": b.get("scaleDownBoundary"),
        }
        if "variants" in b:
            row["variants"] = b["variants"]
        samples.append(row)

    # A row is "hydrated" if it carries any analysis field. Counting these
    # separately is what distinguishes a healthy parse from a log-format drift:
    # target lines and analysis lines match independently, so the analysis
    # pattern can go stale while targets still populate, yielding rows that look
    # like data but are all-null where it matters.
    hydrated = sum(
        1 for s in samples if any(s.get(k) is not None for k in ANALYSIS_FIELDS)
    )

    out = rd / "metrics" / "processed" / "wva_target_timeseries.json"
    out.parent.mkdir(parents=True, exist_ok=True)

    # Don't clobber an existing useful file with a useless new one. Two ways the
    # new parse can be useless: no samples at all (the controller log buffer
    # rotated past the run window), or samples with no analysis fields attached
    # (the analysis log format drifted). The original guard only checked the
    # first, which let an all-null parse overwrite good data.
    if not samples or not hydrated:
        existing = []
        if out.is_file():
            try:
                existing = json.loads(out.read_text()).get("samples", [])
            except (OSError, json.JSONDecodeError):
                existing = []
        existing_hydrated = sum(
            1 for s in existing
            if any(s.get(k) is not None for k in ANALYSIS_FIELDS)
        )
        if existing_hydrated:
            print(f"Skipped overwriting {out}: new parse has {len(samples)} "
                  f"snapshots / {hydrated} with analysis data, existing file has "
                  f"{len(existing)} / {existing_hydrated}.", file=sys.stderr)
            return 1

    out.write_text(json.dumps({"samples": samples}, indent=2))
    print(f"Wrote {out} ({len(samples)} snapshots, {hydrated} with analysis data, "
          f"window {start.isoformat()} -> {stop.isoformat()})")

    # Surface a partial parse loudly. Previously this exact condition -- rows
    # present, analysis fields all null -- printed a healthy-looking success
    # line, and the resulting file was taken at face value.
    if samples and not hydrated:
        print(f"WARNING: {len(samples)} snapshots parsed but NONE carry supply/"
              f"demand/utilization/capacity. The analysis log format has probably "
              f"drifted again -- check what the controller now logs at "
              f"saturation/engine_v2.go and update ANALYZER_RESULT_PAT / "
              f"ANALYSIS_KEYMAP.", file=sys.stderr)
        return 1
    if n_analysis and not hydrated:
        print(f"WARNING: matched {n_analysis} analysis lines but extracted no "
              f"fields from them -- ANALYSIS_KEYMAP is probably stale.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main() or 0)
