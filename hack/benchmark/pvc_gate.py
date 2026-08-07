#!/usr/bin/env python3
"""
pvc_gate.py — refuse to start a run that the results PVC cannot hold.

Why this is a gate and not a warning
------------------------------------
The per-request file is written at the END of a run. A PVC that fills up
therefore does not fail fast -- it fails after every minute of GPU time has been
spent, and it takes the results with it. The 2026-08-03 staircase wrote 4.0 GB;
the PVC is 20 GiB with 8.9 GB free at the time of writing. An A/B pair would land
within a few hundred MB of the ceiling. That is not a margin, it is a coin flip.

So: estimate, compare against free space plus a margin, and exit non-zero before
anything is deployed. `make benchmark-run` depends on this, so the check cannot
be forgotten -- which is the point. It is a pure read of the cluster; it changes
nothing.

Where the estimate comes from
-----------------------------
Prior runs, not a guess. The largest per-request file previously written to this
PVC is the best available predictor of the next one, and `--per-request-size`
overrides it when a run's shape is changing (more stages, longer holds, more
requests). With no history and no override, the default below is used and is
reported AS a default, so an unpinned estimate never looks like a measurement.

Reclaiming
----------
`--reclaim` deletes per-request files whose experiment directory is already on
the host -- the same interlock reset_run.py uses, for the same reason: after the
delete the host copy is the only copy. Everything not reclaimable is listed with
why, because "could not free enough" and "would not free anything" call for
different responses.

Namespace discipline
--------------------
Every kubectl invocation carries an explicit `-n <namespace>`.

Usage
-----
  # will the next run fit?
  python3 pvc_gate.py -n dhl-wva-209 --workspace .

  # free what is safe to free, then check
  python3 pvc_gate.py -n dhl-wva-209 --workspace . --reclaim --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

DATA_ACCESS_LABEL = "role=llm-d-benchmark-data-access"
DATA_ACCESS_CONTAINER = "rsync"
PVC_RESULTS_PATH = "/requests"
PER_REQUEST_NAME = "per_request_lifecycle_metrics.json"
SIDECAR_NAME = "server_completion_tokens.json"

# Used only when there is no history and no --per-request-size. Deliberately
# above the 4.0 GB measured on 2026-08-03: under-estimating costs a whole run,
# over-estimating costs one early "free some space" message.
DEFAULT_PER_REQUEST_GB = 5.0

# Everything in a run other than the per-request file measured under 1 MB on
# 2026-08-03 (reports, native json, metrics/raw, logs). 512 MB is slack, not an
# estimate.
OVERHEAD_BYTES = 512 << 20

GB = 1 << 30


def kubectl(namespace: str, *args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["kubectl", "-n", namespace, *args],
        capture_output=True, text=True, check=False,
    )


def pod_sh(namespace: str, pod: str, script: str) -> subprocess.CompletedProcess:
    return kubectl(
        namespace, "exec", pod, "-c", DATA_ACCESS_CONTAINER, "--", "sh", "-c", script
    )


def human(n: float) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{int(n)} B"
        n /= 1024.0
    return str(n)


def require_cluster(namespace: str) -> None:
    """Exit with an accurate message if kubectl cannot reach the cluster.

    Must run BEFORE any presence check. An expired token makes `get pods -l ...`
    return an EMPTY LIST with the real error on stderr, so "no pod matched the
    label" and "we are not logged in" are indistinguishable from the result
    alone -- and reporting the former sends the operator hunting for a pod that
    is sitting there healthy. Cost a debugging detour on 2026-08-07.

    Reachability and authorization only; it deliberately does not assert the
    namespace exists (`get pods` in a missing namespace can still exit 0). That
    check belongs to preflight_shared_cluster.py.
    """
    proc = kubectl(namespace, "get", "pods", "-o", "name")
    if proc.returncode == 0:
        return
    err = proc.stderr or ""
    lines = [
        ln.strip() for ln in err.splitlines()
        if ln.strip() and not ln.lstrip().startswith("E0") and "Unhandled Error" not in ln
    ]
    detail = lines[-1] if lines else (err.strip().splitlines()[-1] if err.strip() else "no detail")
    print(f"ERROR: cannot reach namespace {namespace}: {detail}", file=sys.stderr)
    print(
        "       The PVC was NOT checked -- this is not a pass. If this is an\n"
        "       expired session, log in again (`oc login`) and re-run.",
        file=sys.stderr,
    )
    sys.exit(1)


def find_data_access_pod(namespace: str) -> str | None:
    proc = kubectl(
        namespace, "get", "pods", "-l", DATA_ACCESS_LABEL,
        "--field-selector=status.phase=Running",
        "-o", "jsonpath={.items[0].metadata.name}",
    )
    return (proc.stdout or "").strip() or None


def free_bytes(namespace: str, pod: str) -> tuple[int, int, str]:
    """(available, size, raw df line) for the results filesystem, in bytes.

    `df -kP` for POSIX single-line output in fixed 1K units -- `df -h` rounds,
    and rounding a margin check defeats it.
    """
    proc = pod_sh(namespace, pod, f"df -kP {PVC_RESULTS_PATH} | tail -1")
    line = (proc.stdout or "").strip()
    parts = line.split()
    if len(parts) < 4 or not parts[1].isdigit() or not parts[3].isdigit():
        return -1, -1, line
    return int(parts[3]) * 1024, int(parts[1]) * 1024, line


def per_request_files(namespace: str, pod: str) -> list[tuple[str, int, str]]:
    """(path, size, experiment) for every per-request file on the PVC."""
    proc = pod_sh(
        namespace, pod,
        f"find {PVC_RESULTS_PATH} -name {PER_REQUEST_NAME} -type f "
        f"-printf '%s %p\\n' 2>/dev/null",
    )
    out = []
    for line in (proc.stdout or "").splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) != 2 or not parts[0].isdigit():
            continue
        path = parts[1]
        rel = path[len(PVC_RESULTS_PATH) :].lstrip("/")
        out.append((path, int(parts[0]), rel.split("/")[0]))
    return out


def host_experiments(workspace: Path) -> dict[str, Path]:
    return {p.name: p for p in workspace.glob("*/results/*") if p.is_dir()}


def sidecar_bytes_scanned(path: Path) -> int:
    """``bytes_scanned`` recorded by completion_tokens_scan.py, or 0.

    This is the size of the file the vector was scanned FROM, which makes it both
    a size-history record that outlives the file and a check that the vector was
    taken from the whole file rather than a partial copy.
    """
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return 0
    n = doc.get("bytes_scanned")
    return int(n) if isinstance(n, int) and n > 0 else 0


def classify(dest: Path | None, pvc_size: int) -> tuple[bool, str]:
    """Is the PVC copy of this per-request file safe to delete, and why.

    Deleting leaves the host with whatever it already has, so "safe" means the
    host holds either the extracted vector or a byte-complete copy. A host copy
    of the WRONG SIZE is the dangerous case and the reason this is a function:
    the 2026-08-03 probe run left a 3.7 GB local copy of a 7.1 GB file, because
    step_09's `kubectl cp` was interrupted ~9 min in and step_09 verifies only
    that SOME file arrived. An existence-only check calls that reclaimable and
    deletes the only complete copy.
    See session-notes/issues/llm-d-benchmark-step09-silent-truncation.md.
    """
    if dest is None:
        return False, "not on the host; this is the only copy"

    sidecar = dest / SIDECAR_NAME
    raw = dest / PER_REQUEST_NAME

    if sidecar.exists():
        scanned = sidecar_bytes_scanned(sidecar)
        if scanned == pvc_size:
            return True, f"{SIDECAR_NAME} scanned from all {human(pvc_size)}"
        if scanned == 0:
            return False, f"{SIDECAR_NAME} records no bytes_scanned -- cannot verify it"
        return False, (
            f"{SIDECAR_NAME} was scanned from {human(scanned)} but the PVC file is "
            f"{human(pvc_size)} -- the vector is not from this file"
        )

    if raw.exists():
        local = raw.stat().st_size
        if local == pvc_size:
            return True, f"complete local copy ({human(local)})"
        return False, (
            f"local copy is TRUNCATED: {human(local)} of {human(pvc_size)} "
            f"-- the PVC holds the only complete copy"
        )

    return False, f"neither {SIDECAR_NAME} nor the raw file; run harvest_run.py first"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Check the results PVC can hold the next run; optionally "
                    "reclaim prior runs' per-request files first.",
    )
    parser.add_argument("-n", "--namespace", required=True)
    parser.add_argument("--workspace", default=".")
    parser.add_argument(
        "--per-request-size", type=float, default=0.0,
        help="expected per-request file size in GB (default: the largest on this "
             "PVC, else %.1f)" % DEFAULT_PER_REQUEST_GB,
    )
    parser.add_argument(
        "--margin", type=float, default=2.0,
        help="free space to leave above the estimate, in GB (default: 2.0)",
    )
    parser.add_argument(
        "--reclaim", action="store_true",
        help="delete per-request files whose results are already on the host",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="perform the reclaim (default: report only)",
    )
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace {workspace} is not a directory", file=sys.stderr)
        sys.exit(1)

    require_cluster(args.namespace)

    pod = find_data_access_pod(args.namespace)
    if not pod:
        print(
            f"ERROR: no Running pod with label '{DATA_ACCESS_LABEL}' in namespace "
            f"{args.namespace} -- cannot check the results PVC.\n"
            f"       The PVC is checked because a full one fails a run only after "
            f"its GPU time is spent; not checking is not the safe option.",
            file=sys.stderr,
        )
        sys.exit(1)

    print(f"Results PVC check in namespace {args.namespace}")
    print(f"Data-access pod: {pod}")

    avail, total, raw = free_bytes(args.namespace, pod)
    if avail < 0:
        print(f"ERROR: could not parse df output: {raw!r}", file=sys.stderr)
        sys.exit(1)
    print(f"  size      {human(total)}")
    print(f"  available {human(avail)}")

    prs = per_request_files(args.namespace, pod)
    on_host = host_experiments(workspace)

    # Size history, largest wins. Deliberately includes the vectors' recorded
    # bytes_scanned: reclaiming deletes the files the estimate would otherwise be
    # based on, so without this the estimate collapses to the default on exactly
    # the run after a successful reclaim.
    history: list[int] = [size for _, size, _ in prs]
    for dest in host_experiments(workspace).values():
        sc = dest / SIDECAR_NAME
        if sc.exists():
            history.append(sidecar_bytes_scanned(sc))
        rawf = dest / PER_REQUEST_NAME
        if rawf.exists():
            history.append(rawf.stat().st_size)
    history = [h for h in history if h > 0]

    if args.per_request_size > 0:
        need_pr = int(args.per_request_size * GB)
        basis = "--per-request-size"
    elif history:
        need_pr = max(history)
        basis = f"largest of {len(history)} prior run(s), on the PVC or recorded on the host"
    else:
        need_pr = int(DEFAULT_PER_REQUEST_GB * GB)
        basis = f"DEFAULT {DEFAULT_PER_REQUEST_GB} GB -- no history, not a measurement"

    need = need_pr + OVERHEAD_BYTES
    margin = int(args.margin * GB)
    required = need + margin
    print(f"\nNext run needs")
    print(f"  {human(need_pr):>10}  per-request file   ({basis})")
    print(f"  {human(OVERHEAD_BYTES):>10}  everything else    (slack)")
    print(f"  {human(margin):>10}  margin             (--margin)")
    print(f"  {human(required):>10}  total required")

    if prs:
        print(f"\nPer-request files currently on the PVC")
        freeable: list[tuple[str, int, str]] = []
        for path, size, exp in sorted(prs, key=lambda t: -t[1]):
            ok, why = classify(on_host.get(exp), size)
            print(f"  {'FREE' if ok else 'KEEP'}  {human(size):>9}  {exp} -- {why}")
            if ok:
                freeable.append((path, size, exp))
        reclaimable = sum(size for _, size, _ in freeable)

        if args.reclaim and freeable:
            print(f"\nReclaiming ({'APPLY' if args.apply else 'DRY RUN'})")
            for path, size, exp in freeable:
                print(f"  {'DO   ' if args.apply else 'WOULD'} rm {path} ({human(size)})")
                if args.apply:
                    proc = pod_sh(args.namespace, pod, f"rm -f {path}")
                    if proc.returncode != 0:
                        print(f"        FAILED: {(proc.stderr or '').strip()}")
            if args.apply:
                avail, total, raw = free_bytes(args.namespace, pod)
                print(f"\n  available now {human(avail)}")
        elif reclaimable:
            print(
                f"\n  {human(reclaimable)} is reclaimable -- re-run with "
                f"--reclaim --apply to free it"
            )

    print()
    if avail >= required:
        print(f"OK: {human(avail)} available >= {human(required)} required")
        return

    short = required - avail
    print(
        f"BLOCKED: {human(avail)} available, {human(required)} required "
        f"-- short by {human(short)}",
        file=sys.stderr,
    )
    print(
        "         A run started now would fail while writing its results, after\n"
        "         all of its GPU time has been spent. Free space first:\n"
        f"           make benchmark-pvc-gate BENCHMARK_NAMESPACE={args.namespace} "
        f"BENCHMARK_RECLAIM=true\n"
        "         or lower the requirement deliberately with --margin / "
        "--per-request-size.",
        file=sys.stderr,
    )
    sys.exit(1)


if __name__ == "__main__":
    main()
