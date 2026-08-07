#!/usr/bin/env python3
"""Is every file in a PVC experiment directory also on the host, byte-for-byte?

reset_run.py's PVC reclaim asks only `if d in on_host` -- the DIRECTORY NAME
exists under <workspace>/*/results/. That is an existence check standing in for a
completeness check, the same substitution that cost the 2026-08-03 probe run its
per-request file (see session-notes/issues/llm-d-benchmark-step09-silent-truncation.md).
A step_09 interrupted early enough leaves a host directory holding SOME of the
small report files, and an existence check calls that reclaimable.

This is the check that should gate the delete: compare names and sizes.

Feed it the output of, inside the data-access pod:
  find /requests -type f -printf '%s %p\n'

Usage:
  python3 verify_pvc_vs_host.py <pvc-file-list> [workspace]
"""
import sys
from pathlib import Path

listing = Path(sys.argv[1])
ws = Path(sys.argv[2] if len(sys.argv) > 2 else ".").resolve()
PREFIX = "/requests/"

host = {p.name: p for p in ws.glob("*/results/*") if p.is_dir()}

pvc: dict[str, dict[str, int]] = {}
for line in listing.read_text().splitlines():
    if not line.strip():
        continue
    size, path = line.split(None, 1)
    if not path.startswith(PREFIX):
        continue
    exp, _, inner = path[len(PREFIX):].partition("/")
    if inner:
        pvc.setdefault(exp, {})[inner] = int(size)

unsafe = 0
for exp in sorted(pvc):
    files = pvc[exp]
    dest = host.get(exp)
    print(f"\n{exp}   ({len(files)} files on PVC)")
    if dest is None:
        print("  NO HOST COPY -- the PVC holds the only copy")
        print("  VERDICT: NOT SAFE")
        unsafe += 1
        continue
    print(f"  host {dest}")
    missing, mismatch, ok = [], [], 0
    for inner, size in sorted(files.items()):
        h = dest / inner
        if not h.exists():
            missing.append((inner, size))
        elif h.stat().st_size != size:
            mismatch.append((inner, size, h.stat().st_size))
        else:
            ok += 1
    print(f"  byte-identical: {ok}/{len(files)}")
    for inner, size in missing:
        print(f"  MISSING on host: {inner} ({size} B)")
    for inner, size, hs in mismatch:
        print(f"  SIZE DIFFERS:    {inner} pvc={size} host={hs}")
    extra = sum(
        1 for p in dest.rglob("*")
        if p.is_file() and str(p.relative_to(dest)) not in files
    )
    print(f"  host-only files (fine -- e.g. the extracted vector): {extra}")
    safe = not missing and not mismatch
    print(f"  VERDICT: {'SAFE to delete the PVC dir' if safe else 'NOT SAFE'}")
    if not safe:
        unsafe += 1

print(f"\n{len(pvc)} experiment(s) on the PVC, {unsafe} NOT safe to delete")
sys.exit(1 if unsafe else 0)
