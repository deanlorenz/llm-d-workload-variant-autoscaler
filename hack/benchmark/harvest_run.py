#!/usr/bin/env python3
"""
harvest_run.py — bring a run's results home without bringing home the multi-GB
per-request file, and reclaim that file's space on the PVC.

Why this replaces llmdbenchmark's step_09
-----------------------------------------
step_09 does one blanket `kubectl cp` of each experiment directory. That is fine
until the directory contains `per_request_lifecycle_metrics.json`, which on the
2026-08-03 staircase was 4.2 GB out of 4.2 GB -- every other file in the run put
together was under 1 MB. Copying it costs minutes, and *leaving* it costs the
run after it: the workload PVC is fixed-size, the file is written at the END of a
run, and a full PVC destroys a run only after all of its GPU time is spent.

`kubectl cp` cannot exclude a path. It is implemented as tar-over-exec, so this
does that directly and passes `--exclude`.

What the big file is actually for
---------------------------------
Exactly one thing needs it: the output-token correction, which rebuilds the true
output-length distribution from `server_usage.completion_tokens`. That is a flat
list of integers -- 31 KB for a 7919-request run, a 138,000x reduction. So the
file is scanned WHERE IT ALREADY IS (completion_tokens_scan.py, in-pod, stdlib
only) and only the vector crosses the wire, as `server_completion_tokens.json`
next to the reports. `output_token_correction.py` prefers that vector and falls
back to the raw file for runs that predate this, so `make benchmark-analyze`
stays re-runnable forever either way.

Order matters, and it is the safety property
--------------------------------------------
scan -> fetch -> VERIFY -> delete. The PVC copy is not touched until the vector
is on local disk and passes a sanity check, because after the delete it is the
only copy in existence. A failure anywhere before the verify leaves the PVC
exactly as it was, and re-running harvest is safe.

Dry run is the default. Nothing is fetched or deleted without `--apply`.

Namespace discipline
--------------------
Every kubectl invocation carries an explicit `-n <namespace>`, as in
reset_run.py and preflight_shared_cluster.py.

Usage
-----
  # show what would be harvested, change nothing
  python3 harvest_run.py -n dhl-wva-209 --workspace .

  # do it
  python3 harvest_run.py -n dhl-wva-209 --workspace . --apply

  # keep the raw file too (costs PVC space until the next reclaim)
  python3 harvest_run.py -n dhl-wva-209 --workspace . --apply --fetch-per-request
"""

from __future__ import annotations

import argparse
import datetime
import json
import re
import subprocess
import sys
from pathlib import Path

# The data-access pod is found by the label llmdbenchmark's own step_09 uses,
# rather than by name: the name is a scenario value and can differ per stack.
DATA_ACCESS_LABEL = "role=llm-d-benchmark-data-access"
DATA_ACCESS_CONTAINER = "rsync"
PVC_RESULTS_PATH = "/requests"

# The one file worth all of this. Both locations the correction looks in.
PER_REQUEST_NAME = "per_request_lifecycle_metrics.json"

# Where the extracted vector lands, next to the reports it corrects. Must match
# _TOKENS_SIDECAR in llmdbenchmark/analysis/output_token_correction.py -- that is
# the reader, and a rename on one side only would silently stop correcting.
SIDECAR_NAME = "server_completion_tokens.json"

SCANNER = Path(__file__).with_name("completion_tokens_scan.py")

# Experiment directories are named <harness>-<epoch>-<rand>_<n>; the epoch is the
# only link between a directory on the PVC and a run directory on the host.
EXP_EPOCH_RE = re.compile(r"^[a-z0-9-]+?-(\d{10})-[a-z0-9]+_\d+$")

# Run directories: <user>-<YYYYmmdd>-<HHMMSS>-<ms>, e.g. dean-20260803-052634-197.
RUN_DIR_RE = re.compile(r"^.+-(\d{8})-(\d{6})-\d+$")


def kubectl(namespace: str, *args: str, stdin=None, stdout=None) -> subprocess.CompletedProcess:
    """Run kubectl with an explicit namespace. Never raises on non-zero.

    `stdout=None` here means CAPTURE, as text. It must be spelled out because
    subprocess.run's own meaning for stdout=None is "inherit the parent's
    stdout", which makes every read return None while printing the answer to the
    terminal -- a failure that reads as "the resource does not exist".

    A caller that passes a file object gets binary through to it untouched, which
    is what the tar and in-pod-scanner paths need.
    """
    capture = stdout is None
    return subprocess.run(
        ["kubectl", "-n", namespace, *args],
        stdin=stdin,
        stdout=subprocess.PIPE if capture else stdout,
        stderr=subprocess.PIPE,
        text=capture,
        check=False,
    )


def pod_sh(namespace: str, pod: str, script: str) -> subprocess.CompletedProcess:
    """Run a shell snippet in the data-access container. Read-only by convention;
    the two callers that mutate say so at the call site."""
    return kubectl(
        namespace, "exec", pod, "-c", DATA_ACCESS_CONTAINER, "--", "sh", "-c", script
    )


def human(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if abs(n) < 1024 or unit == "TB":
            return f"{n:.1f} {unit}" if unit != "B" else f"{n} B"
        n /= 1024.0
    return str(n)


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------


def require_cluster(namespace: str) -> None:
    """Exit with an accurate message if kubectl cannot reach the cluster.

    Must run BEFORE any presence check. An expired token makes `get pods -l ...`
    return an EMPTY LIST with a separate error on stderr, so "no pod matched the
    label" and "we are not logged in" are indistinguishable from the result
    alone -- and reporting the former sends the operator hunting for a pod that
    is sitting there healthy. That is the same fail-dangerous shape as the
    standup's presence gates, where absence reads as "not installed yet, go
    install it". Cost a debugging detour on 2026-08-07.

    This probes reachability and authorization only. It deliberately does not
    assert the namespace exists -- `get pods` in a missing namespace can still
    exit 0 -- because that check belongs to preflight_shared_cluster.py.
    """
    proc = kubectl(namespace, "get", "pods", "-o", "name")
    if proc.returncode == 0:
        return
    err = proc.stderr or ""
    if isinstance(err, bytes):
        err = err.decode(errors="replace")
    # kubectl prefixes its own retry noise with E<mmdd>; the useful line is the
    # last one that is not part of that.
    lines = [
        ln.strip() for ln in err.splitlines()
        if ln.strip() and not ln.lstrip().startswith("E0") and "Unhandled Error" not in ln
    ]
    detail = lines[-1] if lines else (err.strip().splitlines()[-1] if err.strip() else "no detail")
    print(f"ERROR: cannot reach namespace {namespace}: {detail}", file=sys.stderr)
    print(
        "       Nothing was read and nothing was changed. If this is an expired\n"
        "       session, log in again (`oc login`) and re-run.",
        file=sys.stderr,
    )
    sys.exit(1)


def find_data_access_pod(namespace: str) -> str | None:
    proc = kubectl(
        namespace, "get", "pods", "-l", DATA_ACCESS_LABEL,
        "--field-selector=status.phase=Running",
        "-o", "jsonpath={.items[0].metadata.name}",
    )
    name = (proc.stdout or "").strip()
    return name or None


def pvc_experiments(namespace: str, pod: str) -> list[str]:
    proc = pod_sh(namespace, pod, f"ls -1 {PVC_RESULTS_PATH} 2>/dev/null")
    if proc.returncode != 0:
        return []
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()]


def per_request_paths(namespace: str, pod: str, exp: str) -> list[tuple[str, int]]:
    """(path, size) for every per-request file under one experiment directory.

    Located with `find` rather than assumed: the correction accepts it at the
    directory root or under analysis/, and which one appears depends on the
    harness version.
    """
    proc = pod_sh(
        namespace, pod,
        f"find {PVC_RESULTS_PATH}/{exp} -name {PER_REQUEST_NAME} -type f "
        f"-printf '%s %p\\n' 2>/dev/null",
    )
    out = []
    for line in proc.stdout.splitlines():
        parts = line.strip().split(None, 1)
        if len(parts) == 2 and parts[0].isdigit():
            out.append((parts[1], int(parts[0])))
    return out


def dir_size(namespace: str, pod: str, path: str) -> int:
    proc = pod_sh(namespace, pod, f"du -sb {path} 2>/dev/null | cut -f1")
    txt = (proc.stdout or "").strip()
    return int(txt) if txt.isdigit() else 0


def host_experiments(workspace: Path) -> dict[str, Path]:
    """Every experiment directory already on the host, name -> path."""
    return {p.name: p for p in workspace.glob("*/results/*") if p.is_dir()}


def sidecar_bytes_scanned(path: Path) -> int:
    """``bytes_scanned`` recorded by the scanner, or 0 if unreadable.

    The size of the file the vector came from. Comparing it against the PVC file
    proves the vector covers the whole file and not a partial copy.
    """
    try:
        doc = json.loads(path.read_text())
    except (OSError, ValueError):
        return 0
    n = doc.get("bytes_scanned")
    return int(n) if isinstance(n, int) and n > 0 else 0


def run_dirs(workspace: Path) -> list[Path]:
    """Run directories, newest first.

    Matched on the <user>-<YYYYmmdd>-<HHMMSS>-<ms> name the harness generates,
    which sorts chronologically as a string, so no stat() is needed.
    """
    return sorted(
        (p for p in workspace.iterdir() if p.is_dir() and RUN_DIR_RE.match(p.name)),
        key=lambda p: p.name,
        reverse=True,
    )


def run_dir_for(exp: str, candidates: list[Path]) -> Path | None:
    """The run directory an experiment belongs to, matched on time.

    The experiment id carries the epoch at which the harness started it, and the
    run directory name carries the local time the run began; the experiment is
    always the later of the two. Picking the newest run directory that started
    before this experiment is therefore exact, not a guess -- and it is what
    keeps a stale PVC directory from being filed under the current run.
    """
    m = EXP_EPOCH_RE.match(exp)
    if not m:
        # Unrecognised name: fall back to the newest run, and say so rather than
        # filing it silently.
        print(f"  warn  {exp} carries no epoch -- filing under the newest run")
        return candidates[0] if candidates else None

    exp_dt = datetime.datetime.fromtimestamp(int(m.group(1)))
    for cand in candidates:  # newest first
        rm = RUN_DIR_RE.match(cand.name)
        if not rm:
            continue
        try:
            started = datetime.datetime.strptime(
                rm.group(1) + rm.group(2), "%Y%m%d%H%M%S"
            )
        except ValueError:
            continue
        if started <= exp_dt:
            return cand
    return None


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------


class Harvest:
    def __init__(self, namespace: str, pod: str, apply: bool):
        self.namespace = namespace
        self.pod = pod
        self.apply = apply
        self.done: list[str] = []
        self.skipped: list[str] = []
        self.failed: list[str] = []
        self.reclaimed = 0

    def note(self, msg: str) -> None:
        print(f"  {'DO   ' if self.apply else 'WOULD'} {msg}")

    def skip(self, msg: str) -> None:
        self.skipped.append(msg)
        print(f"  skip  {msg}")

    def fail(self, msg: str) -> None:
        self.failed.append(msg)
        print(f"  FAIL  {msg}")


def scan_vector(h: Harvest, remote_file: str, dest: Path) -> bool:
    """Extract the completion-token vector in-pod; write it next to the reports.

    The scanner is piped in on stdin and its result comes back on stdout, so
    nothing is written inside the pod and nothing is left behind.
    """
    h.note(f"scan {remote_file} in-pod -> {dest.name} ({SCANNER.name} on stdin)")
    if not h.apply:
        return True
    if not SCANNER.exists():
        h.fail(f"scanner not found at {SCANNER}")
        return False

    dest.parent.mkdir(parents=True, exist_ok=True)
    tmp = dest.with_suffix(".partial")
    with open(SCANNER, "rb") as script, open(tmp, "wb") as out:
        proc = kubectl(
            h.namespace, "exec", "-i", h.pod, "-c", DATA_ACCESS_CONTAINER,
            "--", "python3", "-", remote_file,
            stdin=script, stdout=out,
        )
    if proc.returncode != 0:
        err = (proc.stderr or b"")
        err = err.decode(errors="replace") if isinstance(err, bytes) else err
        h.fail(f"scan failed: {err.strip().splitlines()[-1] if err.strip() else 'no output'}")
        tmp.unlink(missing_ok=True)
        return False

    # Validate before renaming into place: a half-written vector that looks like
    # a whole one is the one failure mode that would survive to the delete.
    try:
        doc = json.loads(tmp.read_text())
        vals = doc["completion_tokens"]
        if not isinstance(vals, list) or not vals:
            raise ValueError("empty vector")
    except (OSError, ValueError, KeyError) as exc:
        h.fail(f"scan produced no usable vector: {exc}")
        tmp.unlink(missing_ok=True)
        return False

    tmp.replace(dest)
    print(
        f"        {len(vals)} values, mean {sum(vals) / len(vals):.1f}, "
        f"{human(dest.stat().st_size)} on disk"
    )
    return True


def fetch_dir(h: Harvest, exp: str, dest_parent: Path, exclude: bool) -> bool:
    """Copy one experiment directory to the host, optionally without the big file.

    tar-over-exec rather than `kubectl cp`, which has no exclude mechanism (and
    is itself implemented this way). `tar cf - -C /requests <exp>` emits entries
    prefixed with <exp>, so extracting under results/ reproduces exactly the
    layout step_09 produced.
    """
    what = f"fetch {exp} -> {dest_parent}/{exp}"
    h.note(f"{what}{' (excluding ' + PER_REQUEST_NAME + ')' if exclude else ' (full)'}")
    if not h.apply:
        return True

    dest_parent.mkdir(parents=True, exist_ok=True)
    excl = f"--exclude={PER_REQUEST_NAME} " if exclude else ""
    remote = f"tar cf - -C {PVC_RESULTS_PATH} {excl}{exp}"

    pull = subprocess.Popen(
        ["kubectl", "-n", h.namespace, "exec", h.pod, "-c", DATA_ACCESS_CONTAINER,
         "--", "sh", "-c", remote],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    untar = subprocess.Popen(
        ["tar", "xf", "-", "-C", str(dest_parent)],
        stdin=pull.stdout,
        stderr=subprocess.PIPE,
    )
    pull.stdout.close()  # let pull see SIGPIPE if untar dies
    untar_err = untar.communicate()[1]
    pull_err = pull.stderr.read()
    pull.wait()

    if pull.returncode != 0 or untar.returncode != 0:
        msg = (untar_err or pull_err or b"").decode(errors="replace").strip()
        h.fail(f"{what}: {msg.splitlines()[-1] if msg else 'transfer failed'}")
        return False

    files = sum(1 for f in (dest_parent / exp).rglob("*") if f.is_file())
    size = sum(f.stat().st_size for f in (dest_parent / exp).rglob("*") if f.is_file())
    print(f"        {files} file(s), {human(size)}")
    return True


def host_copy_verified(dest_dir: Path, pvc_size: int) -> bool:
    """True when the host already holds a provably complete copy of this file.

    Size-based, never existence-based -- the same rule reclaim() enforces, and it
    has to be applied BEFORE the scan decision too. A truncated raw copy that
    reads as "verified" suppresses the scan that would make the delete safe, and
    the flow then gets stuck in a shape that looks careful but is not: refusing
    to delete (right) while also refusing to do the one thing that would let it
    (wrong). That is how the 2026-08-03 probe run's 7.1 GB sat unreclaimable
    behind a 3.7 GB local copy.
    """
    sidecar = dest_dir / SIDECAR_NAME
    if sidecar.exists() and sidecar_bytes_scanned(sidecar) == pvc_size:
        return True
    raw = dest_dir / PER_REQUEST_NAME
    return raw.exists() and raw.stat().st_size == pvc_size


def reclaim(h: Harvest, remote_file: str, size: int, sidecar: Path, local_copy: Path | None) -> bool:
    """Delete the per-request file from the PVC. The point of no return.

    Every guard is re-checked here rather than trusted from earlier in the flow,
    and all of them compare SIZES, not existence. A local file of the wrong size
    is the failure that matters: the 2026-08-03 probe run left a 3.7 GB copy of a
    7.1 GB file because its step_09 `kubectl cp` was interrupted ~9 min in, and
    step_09 verifies only that SOME file arrived -- so the truncation was reported
    as a successful collection. An existence-only check calls that safe to delete.
    See session-notes/issues/llm-d-benchmark-step09-silent-truncation.md.
    """
    if local_copy is not None:
        if not local_copy.exists():
            h.skip(f"KEEP {remote_file} -- requested local copy is missing")
            return False
        if local_copy.stat().st_size != size:
            h.skip(
                f"KEEP {remote_file} -- local copy is TRUNCATED: "
                f"{human(local_copy.stat().st_size)} of {human(size)}"
            )
            return False
    else:
        if not sidecar.exists():
            h.skip(f"KEEP {remote_file} -- no {SIDECAR_NAME} on the host")
            return False
        scanned = sidecar_bytes_scanned(sidecar)
        if scanned != size:
            h.skip(
                f"KEEP {remote_file} -- {SIDECAR_NAME} was scanned from "
                f"{human(scanned) if scanned else 'an unrecorded size'}, "
                f"but the PVC file is {human(size)}"
            )
            return False

    h.note(f"delete {remote_file} from the PVC (frees {human(size)})")
    if not h.apply:
        h.reclaimed += size
        return True

    # The only mutating pod_sh call in this script.
    proc = pod_sh(h.namespace, h.pod, f"rm -f {remote_file}")
    if proc.returncode != 0:
        h.fail(f"could not delete {remote_file}: {(proc.stderr or '').strip()}")
        return False
    h.reclaimed += size
    return True


def show_usage(namespace: str, pod: str, label: str) -> None:
    proc = pod_sh(namespace, pod, f"df -h {PVC_RESULTS_PATH}")
    for line in proc.stdout.splitlines()[1:]:
        print(f"  {label}  {line.strip()}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Fetch a run's results without the multi-GB per-request file, "
                    "and reclaim its space on the PVC. Dry run unless --apply.",
    )
    parser.add_argument("-n", "--namespace", required=True)
    parser.add_argument(
        "--workspace", default=".",
        help="directory holding the <user>-<timestamp> run directories",
    )
    parser.add_argument(
        "--experiment", action="append", default=[],
        help="harvest only this experiment id (repeatable; default: everything on "
             "the PVC that is not already on the host)",
    )
    parser.add_argument(
        "--fetch-per-request", action="store_true",
        help="also copy the per-request file home before reclaiming it "
             "(minutes and multiple GB of local disk)",
    )
    parser.add_argument(
        "--no-reclaim", action="store_true",
        help="fetch but leave the PVC untouched",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="actually fetch and reclaim (default: report only)",
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
            f"ERROR: no Running pod with label '{DATA_ACCESS_LABEL}' in "
            f"namespace {args.namespace} -- cannot reach the results PVC",
            file=sys.stderr,
        )
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY RUN -- nothing will be fetched or deleted"
    print(f"Harvest results from namespace {args.namespace}   [{mode}]")
    print(f"Workspace:       {workspace}")
    print(f"Data-access pod: {pod}")
    show_usage(args.namespace, pod, "before")

    on_pvc = pvc_experiments(args.namespace, pod)
    if not on_pvc:
        print(f"\nNothing under {PVC_RESULTS_PATH} -- nothing to harvest.")
        return

    on_host = host_experiments(workspace)
    candidates = run_dirs(workspace)

    if args.experiment:
        missing = [e for e in args.experiment if e not in on_pvc]
        for e in missing:
            print(f"ERROR: experiment {e} is not on the PVC", file=sys.stderr)
        if missing:
            sys.exit(1)
        targets = args.experiment
    else:
        targets = on_pvc

    h = Harvest(args.namespace, pod, args.apply)

    for exp in sorted(targets):
        print(f"\n{exp}")
        remote_dir = f"{PVC_RESULTS_PATH}/{exp}"
        print(f"  size  {human(dir_size(args.namespace, pod, remote_dir))} on the PVC")

        pr_files = per_request_paths(args.namespace, pod, exp)

        already = exp in on_host
        if already and exp not in args.experiment:
            # Already fetched: skip the copy, but the big file may still be on the
            # PVC (an older run, or a fetch that predates this script), and that
            # space is exactly what we are here for.
            dest_dir = on_host[exp]
            print(f"  host  already at {dest_dir} -- fetch skipped")
        else:
            run_dir = run_dir_for(exp, candidates)
            if run_dir is None:
                h.skip(f"{exp} -- no run directory under {workspace} to file it under")
                continue
            dest_dir = run_dir / "results" / exp

            if pr_files and not args.fetch_per_request:
                sidecar_ok = all(
                    scan_vector(h, path, dest_dir / SIDECAR_NAME) for path, _ in pr_files
                )
                if not sidecar_ok:
                    h.skip(f"{exp} -- not fetching or reclaiming after a failed scan")
                    continue

            if not fetch_dir(
                h, exp, run_dir / "results", exclude=not args.fetch_per_request
            ):
                continue
            h.done.append(exp)

        if args.no_reclaim:
            if pr_files:
                h.skip(f"{exp} -- --no-reclaim, {PER_REQUEST_NAME} left on the PVC")
            continue

        if not pr_files:
            print(f"  none  no {PER_REQUEST_NAME} on the PVC -- nothing to reclaim")
            continue

        for path, size in pr_files:
            sidecar = dest_dir / SIDECAR_NAME
            if already and not host_copy_verified(dest_dir, size):
                # Fetched by an older flow that kept no usable copy -- or kept a
                # TRUNCATED one. Extract the vector now, so the reports stay
                # correctable after the delete.
                raw = dest_dir / PER_REQUEST_NAME
                if raw.exists() and raw.stat().st_size != size:
                    print(
                        f"        NOTE local {PER_REQUEST_NAME} is TRUNCATED "
                        f"({human(raw.stat().st_size)} of {human(size)}); scanning "
                        f"the PVC copy, which is complete"
                    )
                if not scan_vector(h, path, sidecar):
                    h.skip(f"{path} -- kept, vector could not be extracted")
                    continue
                if raw.exists() and raw.stat().st_size != size:
                    print(
                        f"        WARN {raw} is a truncated {human(raw.stat().st_size)} "
                        f"fragment and is now superseded by {SIDECAR_NAME}. Left in "
                        f"place -- deleting your local data is your call, not this "
                        f"script's -- but do not compute on it."
                    )
            reclaim(
                h, path, size, sidecar,
                dest_dir / PER_REQUEST_NAME if args.fetch_per_request else None,
            )

    print()
    show_usage(args.namespace, pod, "after " if args.apply else "unchg ")
    print(
        f"\n{len(h.done)} experiment(s) {'fetched' if args.apply else 'to fetch'}, "
        f"{human(h.reclaimed)} {'reclaimed' if args.apply else 'reclaimable'}, "
        f"{len(h.skipped)} skipped, {len(h.failed)} failed"
    )
    if not args.apply:
        print("Re-run with --apply to perform them.")
    if h.failed:
        for f in h.failed:
            print(f"  FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
