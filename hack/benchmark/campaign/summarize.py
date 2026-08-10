#!/usr/bin/env python3
"""
summarize.py — compare campaign cells side by side.

Reads each cell's saved artifacts under session-notes/campaign-runs/<cell>/ and the
analyzed timeseries in its results directory, and prints one row per cell.

The column that matters most is `analyzers seen`: it is counted from the cell's own
saved controller log, so it reports which analyzers ACTUALLY reported during that
run rather than which ones the env file asked for. A cell configured
throughput-only whose log still shows saturation lines is telling you the
configured disable did not take effect -- that is the whole point of running the
matrix, and it is why the configured set and the observed set are printed as
separate columns.
"""
import json
import re
import sys
from pathlib import Path

RUNS = Path("session-notes/campaign-runs")


def analyzer_counts(log: Path) -> dict[str, int]:
    if not log.is_file():
        return {}
    counts: dict[str, int] = {}
    pat = re.compile(r'"analyzer":\s*"([a-z]+)"')
    with log.open(errors="replace") as fh:
        for line in fh:
            m = pat.search(line)
            if m:
                counts[m.group(1)] = counts.get(m.group(1), 0) + 1
    return counts


def configured_analyzers(cell: str) -> str:
    env = Path(f"hack/benchmark/{cell}.env")
    if not env.is_file():
        return "?"
    for line in env.read_text().splitlines():
        if line.startswith("WVA_ANALYZERS="):
            return line.split("=", 1)[1].strip()
    return "(none)"


def image_tag(cell: str) -> str:
    env = Path(f"hack/benchmark/{cell}.env")
    if not env.is_file():
        return "?"
    for line in env.read_text().splitlines():
        if line.startswith("WVA_IMAGE_TAG="):
            return line.split("=", 1)[1].strip()
    return "?"


def profile(cell: str) -> str:
    env = Path(f"hack/benchmark/{cell}.env")
    if not env.is_file():
        return "?"
    for line in env.read_text().splitlines():
        if line.startswith("BENCHMARK_PROFILE="):
            return line.split("=", 1)[1].strip().replace(".yaml", "")
    return "?"


def timeseries(cell: str) -> tuple[int, int, list, float | None, list]:
    """(rows, hydrated, replica path, max util, distinct prc)."""
    ref = RUNS / cell / "results-dir.txt"
    if not ref.is_file():
        return 0, 0, [], None, []
    rd = Path(ref.read_text().strip())
    ts = rd / "metrics" / "processed" / "wva_target_timeseries.json"
    if not ts.is_file():
        return 0, 0, [], None, []
    try:
        rows = json.loads(ts.read_text()).get("samples", [])
    except (OSError, json.JSONDecodeError):
        return 0, 0, [], None, []
    hydrated = sum(1 for s in rows if s.get("totalSupply") is not None)
    path, prev = [], None
    for s in rows:
        t = s.get("primary")
        if t is not None and t != prev:
            path.append(t)
            prev = t
    utils = [s["utilization"] for s in rows if s.get("utilization") is not None]
    prcs = sorted({v.get("prc") for s in rows
                   for v in (s.get("variants") or []) if v.get("prc")})
    return len(rows), hydrated, path, (max(utils) if utils else None), prcs


def main() -> int:
    cells = sys.argv[1:] or sorted(p.name for p in RUNS.iterdir() if p.is_dir()) \
        if RUNS.is_dir() else []
    if not cells:
        print(f"no cells found under {RUNS}", file=sys.stderr)
        return 1

    print(f"{'cell':<20} {'image':<28} {'profile':<11} {'configured':<22} "
          f"{'analyzers seen (from log)':<34} {'rows':>5} {'hyd':>4} {'maxutil':>7}  path")
    print("-" * 175)
    for cell in cells:
        seen = analyzer_counts(RUNS / cell / "controller.log")
        seen_s = ", ".join(f"{k}={v}" for k, v in sorted(seen.items())) or "(none)"
        rows, hyd, path, mx, prcs = timeseries(cell)
        mx_s = f"{mx:.3f}" if mx is not None else "-"
        print(f"{cell:<20} {image_tag(cell)[-26:]:<28} {profile(cell):<11} "
              f"{configured_analyzers(cell):<22} {seen_s:<34} {rows:>5} {hyd:>4} "
              f"{mx_s:>7}  {'→'.join(map(str, path))}")
        if len(prcs) > 1:
            print(f"{'':<20} prc varied across the run: {prcs}")

    print()
    print("Reading this table:")
    print("  * 'configured' is what the env file asked for; 'analyzers seen' is what the")
    print("    controller log shows actually reported. If a throughput-only cell still shows")
    print("    saturation lines, the configured disable did not take effect.")
    print("  * hyd < rows means some snapshots carry no analysis fields -- suspect a")
    print("    log-format drift and re-parse the saved controller log.")
    print("  * a single distinct prc means no capacity-history collapse in that run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
