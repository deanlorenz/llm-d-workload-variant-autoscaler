#!/usr/bin/env python3
"""Fetch files that exist on the results PVC but not on the host, size-verified.

Why this exists
---------------
step_09_collect_results.py copies an experiment directory ONCE, and anything
written into that directory afterwards is never fetched. On this PVC that is the
whole `analysis/` subtree (present for all four experiments, absent from every
host copy) plus, for the interrupted probe run, one benchmark_report YAML. Nothing
downstream notices, because "the experiment directory exists locally" reads as
"we have the results" -- the D4 link in
session-notes/issues/llm-d-benchmark-step09-silent-truncation.md.

reset_run.py then offers to `rm -rf` those PVC directories on the strength of the
directory NAME existing on the host, so the gap becomes permanent at that point.
This closes the gap first.

Transport: `kubectl exec -- cat`, not `kubectl cp`. cp is tar-over-exec with no
resume and no verification -- the mechanism that silently truncated 3.4 GB on
2026-08-03. cat into a local file, then compare the byte count to the size the
PVC reported: a short write cannot pass.

Files whose sizes DIFFER are reported and skipped, never overwritten. On this
workspace those are the reports we corrected in place, where the host copy is the
one to keep. Use --overwrite-mismatched only with a reason.

Every kubectl invocation carries an explicit -n <namespace>.

Usage:
  # inside the data-access pod: find /requests -type f -printf '%s %p\n' > listing
  python3 fetch_missing_from_pvc.py -n dhl-wva-209 --listing /tmp/pvc-files.txt \
      --workspace . [--apply]
"""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

DATA_ACCESS_POD = "access-to-harness-data-workload-pvc"
DATA_ACCESS_CONTAINER = "rsync"
PREFIX = "/requests/"


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if abs(n) < 1024 or unit == "GB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return str(n)


def fetch(namespace: str, remote: str, dest: Path, expect: int) -> str | None:
    """cat one file out of the pod into dest. Returns an error string or None."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(dest.suffix + ".partial")
    with tmp.open("wb") as fh:
        proc = subprocess.run(
            ["kubectl", "-n", namespace, "exec", DATA_ACCESS_POD,
             "-c", DATA_ACCESS_CONTAINER, "--", "cat", remote],
            stdout=fh, stderr=subprocess.PIPE, check=False,
        )
    if proc.returncode != 0:
        tmp.unlink(missing_ok=True)
        return (proc.stderr or b"").decode().strip() or f"kubectl exit {proc.returncode}"
    got = tmp.stat().st_size
    if got != expect:
        tmp.unlink(missing_ok=True)
        return f"short read: got {got} B, PVC reports {expect} B"
    tmp.replace(dest)
    return None


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("-n", "--namespace", required=True)
    ap.add_argument("--listing", required=True, help="output of find -printf '%s %p\\n'")
    ap.add_argument("--workspace", default=".")
    ap.add_argument("--apply", action="store_true", help="actually fetch (default: report)")
    ap.add_argument("--overwrite-mismatched", action="store_true")
    args = ap.parse_args()

    ws = Path(args.workspace).resolve()
    host = {p.name: p for p in ws.glob("*/results/*") if p.is_dir()}

    pvc: dict[str, dict[str, int]] = {}
    for line in Path(args.listing).read_text().splitlines():
        if not line.strip():
            continue
        size, path = line.split(None, 1)
        if not path.startswith(PREFIX):
            continue
        exp, _, inner = path[len(PREFIX):].partition("/")
        if inner:
            pvc.setdefault(exp, {})[inner] = int(size)

    mode = "APPLY" if args.apply else "DRY RUN -- nothing will be written"
    print(f"Fill host gaps from the PVC in namespace {args.namespace}   [{mode}]")
    print(f"Workspace: {ws}")

    fetched = failed = skipped = 0
    total = 0
    for exp in sorted(pvc):
        dest_dir = host.get(exp)
        gaps = []
        mismatched = []
        for inner, size in sorted(pvc[exp].items()):
            if dest_dir is None:
                continue
            h = dest_dir / inner
            if not h.exists():
                gaps.append((inner, size))
            elif h.stat().st_size != size:
                mismatched.append((inner, size, h.stat().st_size))
        if dest_dir is None:
            print(f"\n{exp}\n  no host copy -- out of scope here; harvest_run.py fetches whole experiments")
            continue
        if not gaps and not mismatched:
            continue
        print(f"\n{exp}")
        for inner, size, hs in mismatched:
            if args.overwrite_mismatched:
                gaps.append((inner, size))
            else:
                print(f"  keep  {inner} -- host {human(hs)} vs PVC {human(size)}; host copy kept")
                skipped += 1
        for inner, size in gaps:
            remote = f"{PREFIX}{exp}/{inner}"
            dest = dest_dir / inner
            if not args.apply:
                print(f"  WOULD fetch {inner} ({human(size)})")
                total += size
                continue
            err = fetch(args.namespace, remote, dest, size)
            if err:
                print(f"  FAIL  {inner}: {err}")
                failed += 1
            else:
                print(f"  DO    fetch {inner} ({human(size)}) -- size verified")
                fetched += 1
                total += size

    verb = "fetched" if args.apply else "to fetch"
    print(f"\n{fetched if args.apply else '?'} file(s) {verb}, {human(total)}, "
          f"{skipped} kept as-is, {failed} failed")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
