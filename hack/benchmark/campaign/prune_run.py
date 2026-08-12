#!/usr/bin/env python3
"""
prune_run.py — discard genuinely redundant harness output from one run directory.

Conservative by design: only removes a file when it is BYTE-IDENTICAL to
another file already preserved under the run's results/*/logs/ (the
pod-log followers copy their raw kubectl-logs output into
setup/commands/*_stdout.log, then again into results/<leaf>/logs/ -- this
prunes the setup/ copy, keeping the results/ one). Never touches
config/, viz/, REPORT.md, or anything under results/ or logs/ -- those are
either the reproducible/curated set or the substrate for signal not yet
mined (see session/status/benchmark.md §20.24). Never touches metrics/raw/.

Usage:
    python hack/benchmark/campaign/prune_run.py <run-dir> [--apply]

Without --apply, prints what would be removed and the total size, without
deleting anything.
"""
import argparse
import hashlib
import sys
from pathlib import Path


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def find_duplicates(run_dir: Path) -> list[tuple[Path, Path, int]]:
    """Return (candidate, kept_original, size) for each setup/commands/*_stdout.log
    that is byte-identical to some file under results/*/logs/."""
    candidates = sorted(run_dir.glob("setup/commands/*_stdout.log"))
    kept_logs = sorted(run_dir.glob("results/*/logs/*"))
    if not candidates or not kept_logs:
        return []

    kept_by_size: dict[int, list[Path]] = {}
    for f in kept_logs:
        if f.is_file():
            kept_by_size.setdefault(f.stat().st_size, []).append(f)

    dupes = []
    for c in candidates:
        size = c.stat().st_size
        same_size = kept_by_size.get(size, [])
        if not same_size:
            continue
        c_hash = sha256(c)
        for k in same_size:
            if sha256(k) == c_hash:
                dupes.append((c, k, size))
                break
    return dupes


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("run_dir", help="runs/<run-id>/ directory")
    ap.add_argument("--apply", action="store_true",
                     help="actually delete; default is dry-run")
    args = ap.parse_args()

    run_dir = Path(args.run_dir)
    if not run_dir.is_dir():
        print(f"ERROR: {run_dir} is not a directory", file=sys.stderr)
        return 1

    dupes = find_duplicates(run_dir)
    if not dupes:
        print("nothing to prune (no byte-identical setup/commands/*_stdout.log found)")
        return 0

    total = 0
    for candidate, original, size in dupes:
        total += size
        verb = "removing" if args.apply else "would remove"
        print(f"{verb}: {candidate} ({size / 1e6:.1f} MB, duplicate of {original})")
        if args.apply:
            candidate.unlink()

    print(f"\n{'freed' if args.apply else 'would free'}: {total / 1e6:.1f} MB "
          f"across {len(dupes)} file(s)")
    if not args.apply:
        print("(dry run -- pass --apply to actually delete)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
