#!/usr/bin/env python3
"""
write_report.py — build REPORT.md for one run directory.

Wraps postprocess.py's metrics table (the same table `make benchmark-report`
prints to the console) with relative links into that run's own config/ and
viz/, and writes the result to <run-dir>/REPORT.md. Does not compute anything
itself -- postprocess.py remains the single source of the metrics table, this
script only frames it with the links the results-tree design calls for.

Usage:
    python hack/benchmark/campaign/write_report.py <run-dir> [--scenario "..."]

<run-dir> is a runs/<run-id>/ directory (the one containing config/, results/,
viz/ as siblings) -- NOT the harness's own results/<leaf>/ subdirectory.
"""
import argparse
import subprocess
import sys
from pathlib import Path


def find_leaf(run_dir: Path) -> Path | None:
    matches = sorted(run_dir.glob("results/*_1"))
    return matches[0] if matches else None


def relative_links(run_dir: Path, leaf: Path) -> list[str]:
    lines = []
    viz = run_dir / "viz"
    if viz.is_dir():
        for name in ("panels.png", "coverage.json", "bundle.json"):
            if (viz / name).is_file():
                lines.append(f"- [{name}](viz/{name})")
    config = run_dir / "config"
    if config.is_dir():
        for f in sorted(config.iterdir()):
            if f.is_file():
                lines.append(f"- [config/{f.name}](config/{f.name})")
    if leaf is not None:
        lines.append(f"- [raw results]({leaf.relative_to(run_dir)})")
    return lines


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="runs/<run-id>/ directory")
    ap.add_argument("--scenario", default=None)
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: {run_dir} is not a directory", file=sys.stderr)
        return 1

    leaf = find_leaf(run_dir)
    if leaf is None:
        print(f"ERROR: no results/*_1 leaf found under {run_dir}", file=sys.stderr)
        return 1

    postprocess = Path(__file__).resolve().parent.parent / "postprocess.py"
    cmd = [sys.executable, str(postprocess)]
    if args.scenario:
        cmd += ["--scenario", args.scenario]
    cmd.append(str(leaf))
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"ERROR: postprocess.py failed:\n{result.stderr}", file=sys.stderr)
        return 1

    links = relative_links(run_dir, leaf)
    report = [
        f"# {run_dir.name}",
        "",
        result.stdout.rstrip(),
        "",
        "## Artifacts",
        "",
        *links,
        "",
    ]
    out_path = run_dir / "REPORT.md"
    out_path.write_text("\n".join(report))
    print(f"wrote {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
