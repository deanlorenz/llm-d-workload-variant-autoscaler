#!/usr/bin/env python3
"""
reset_run.py — return the namespace to a clean pre-run state, and nothing more.

Why this exists
---------------
Two arms of an A/B experiment must not inherit each other's state. Three kinds of
carry-over are real, and all three are invisible in the results:

  * **Analyzer memory.** The WVA controller accumulates per-analyzer history
    (throughput OLS samples, saturation k2 history). Arm B starting with arm A's
    accumulators is not arm B.
  * **vLLM prefix cache.** With the same prompt seed in both arms, arm B would
    serve from a cache arm A warmed, and report better TTFT for no reason
    attributable to the controller.
  * **Leftover harness objects.** llmdbenchmark deletes its own harness pod and
    per-run ConfigMaps in run step_11 -- but that step is skipped in debug mode
    and never reached if a run fails earlier. A stranded harness pod holds its
    memory request and can collide with the next run.

And one kind of carry-over is fatal rather than merely confounding: the workload
PVC. Each staircase run writes a multi-GB per-request file, the PVC is fixed-size,
and the file is written at the *end* of a run -- so exhausting it destroys a run
after all of its GPU time has been spent. Reclaiming that space is the load-bearing
part of a reset, not a nicety.

Scope: this is the LOWEST rung
------------------------------
This script resets a *run*. It deliberately does not rebuild the stack, does not
touch the namespace's shape, and cannot touch anything cluster-scoped. Everything
it skips is listed on stdout under "not touched", so the boundary is visible at
the point of use rather than only in this comment.

Two specific non-actions are worth stating, because both look like omissions:

  * **KEDA pause state is reported, never changed.** A ScaledObject left at
    `paused-replicas: 0` means the next run traces flat at zero replicas, which
    looks like an autoscaling result and is not one. Un-pausing is a decision
    about starting a run, and belongs to whoever starts it.
  * **The model PVC, the download Job, and the data-access pod stay.** Deleting
    them forces a fresh multi-GB model download. They are not per-run state.

Dry run is the default. Nothing is written to the cluster or the PVC without
`--apply`.

Namespace discipline
--------------------
Every kubectl invocation carries an explicit `-n <namespace>`, matching
preflight_shared_cluster.py and record_images.py. See the former's header for why
this is done even where kubectl ignores the flag.

Usage
-----
  # show exactly what would be reset, change nothing
  python3 reset_run.py -n dhl-wva-209 --workspace .

  # do it
  python3 reset_run.py -n dhl-wva-209 --workspace . --apply
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

# Harness pods carry this label (20_harness_pod.yaml.j2 -> harness.podLabel),
# and it is the selector llmdbenchmark's own step_11 cleanup uses.
HARNESS_POD_LABEL = "app=llmdbench-harness-launcher"

# Per-run ConfigMaps, recreated by run steps 05/06 on every run.
# <harness>-profiles is named after the harness, so it is resolved at runtime.
HARNESS_SCRIPTS_CONFIGMAP = "llmdbench-harness-scripts"

# The data-access pod and the container in it that has the workload PVC mounted.
DATA_ACCESS_POD = "access-to-harness-data-workload-pvc"
DATA_ACCESS_CONTAINER = "rsync"
PVC_RESULTS_PATH = "/requests"


def kubectl(namespace: str, *args: str) -> subprocess.CompletedProcess:
    """Run kubectl with an explicit namespace. Never raises on non-zero."""
    return subprocess.run(
        ["kubectl", "-n", namespace, *args],
        capture_output=True,
        text=True,
        check=False,
    )


def get_json(namespace: str, *args: str) -> dict | None:
    proc = kubectl(namespace, *args, "-o", "json")
    if proc.returncode != 0:
        return None
    try:
        return json.loads(proc.stdout)
    except json.JSONDecodeError:
        return None


class Reset:
    """Collects planned actions, then either prints or performs them."""

    def __init__(self, namespace: str, apply: bool):
        self.namespace = namespace
        self.apply = apply
        self.planned: list[str] = []
        self.skipped: list[str] = []
        self.failed: list[str] = []

    def plan(self, description: str) -> None:
        self.planned.append(description)
        print(f"  {'DO  ' if self.apply else 'WOULD'} {description}")

    def skip(self, description: str) -> None:
        self.skipped.append(description)
        print(f"  skip  {description}")

    def run(self, description: str, *args: str) -> bool:
        """Perform one kubectl action if applying. Returns False on failure."""
        self.plan(description)
        if not self.apply:
            return True
        proc = kubectl(self.namespace, *args)
        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout).strip().splitlines()
            print(f"        FAILED: {err[0] if err else 'unknown error'}")
            self.failed.append(description)
            return False
        return True


# --------------------------------------------------------------------------
# discovery
# --------------------------------------------------------------------------


def find_controller_deployment(namespace: str) -> str | None:
    """The WVA controller, by label rather than by name.

    Kustomize and Helm installs name it differently (wva-controller-manager vs
    workload-variant-autoscaler-controller-manager); the label is stable across
    both, so this matches what `make benchmark-restart-controller` does.
    """
    data = get_json(
        namespace, "get", "deploy",
        "-l", "app.kubernetes.io/name=workload-variant-autoscaler",
    )
    items = (data or {}).get("items") or []
    return items[0]["metadata"]["name"] if items else None


def find_scaled_deployments(namespace: str) -> list[tuple[str, str, str | None]]:
    """Deployments under KEDA control, from each ScaledObject's scaleTargetRef.

    Discovered rather than derived from the model name: the decode Deployment's
    name is a hash of the model ID, and the ScaledObject is the object that
    actually declares which workload WVA scales. Returns
    (scaledobject, deployment, paused-replicas annotation or None).
    """
    data = get_json(namespace, "get", "scaledobject")
    out = []
    for item in (data or {}).get("items") or []:
        target = (item.get("spec") or {}).get("scaleTargetRef") or {}
        name = target.get("name")
        if not name:
            continue
        paused = (item["metadata"].get("annotations") or {}).get(
            "autoscaling.keda.sh/paused-replicas"
        )
        out.append((item["metadata"]["name"], name, paused))
    return out


def find_harness_pods(namespace: str) -> list[str]:
    data = get_json(namespace, "get", "pods", "-l", HARNESS_POD_LABEL)
    return [i["metadata"]["name"] for i in (data or {}).get("items") or []]


def find_harness_configmaps(namespace: str) -> list[str]:
    """Per-run ConfigMaps: llmdbench-harness-scripts and <harness>-profiles.

    Both are regenerated per run, so their names are matched rather than
    configured -- a reset should clear a stale profiles ConfigMap left by any
    harness, not only the one the next run happens to use.
    """
    data = get_json(namespace, "get", "configmap")
    found = []
    for item in (data or {}).get("items") or []:
        name = item["metadata"]["name"]
        if name == HARNESS_SCRIPTS_CONFIGMAP or name.endswith("-profiles"):
            found.append(name)
    return found


def find_pvc_results(namespace: str) -> tuple[list[str], str | None]:
    """Result directories on the workload PVC, read through the data-access pod.

    Returns (directories, error). An error is not fatal: with no data-access pod
    the PVC simply cannot be inspected from here, which is a reason to say so
    and carry on, not to refuse the rest of the reset.
    """
    proc = kubectl(
        namespace, "exec", DATA_ACCESS_POD, "-c", DATA_ACCESS_CONTAINER,
        "--", "ls", "-1", PVC_RESULTS_PATH,
    )
    if proc.returncode != 0:
        err = (proc.stderr or "").strip().splitlines()
        return [], err[0] if err else "could not exec into the data-access pod"
    return [ln.strip() for ln in proc.stdout.splitlines() if ln.strip()], None


def host_result_dirs(workspace: Path) -> set[str]:
    """Basenames of every run result directory already copied back to the host.

    This is the safety interlock for deleting anything off the PVC: a directory
    is reclaimable only if its copy is here. The names are identical on both
    sides (the harness names the directory, and step_09 rsyncs it verbatim), so
    the comparison is exact rather than heuristic.
    """
    return {p.name for p in workspace.glob("*/results/*") if p.is_dir()}


# --------------------------------------------------------------------------
# actions
# --------------------------------------------------------------------------


def reset_harness_objects(r: Reset) -> None:
    print("\nLeftover harness objects (llmdbenchmark step_11 normally removes these)")
    pods = find_harness_pods(r.namespace)
    if pods:
        for pod in pods:
            r.run(f"delete pod/{pod}", "delete", "pod", pod, "--ignore-not-found")
    else:
        r.skip("no harness pod present")

    cms = find_harness_configmaps(r.namespace)
    if cms:
        for cm in cms:
            r.run(
                f"delete configmap/{cm}",
                "delete", "configmap", cm, "--ignore-not-found",
            )
    else:
        r.skip("no per-run ConfigMaps present")


def reset_pvc_results(r: Reset, workspace: Path) -> None:
    print(f"\nWorkload PVC results ({PVC_RESULTS_PATH}, reclaim only what is already on the host)")

    usage = kubectl(
        r.namespace, "exec", DATA_ACCESS_POD, "-c", DATA_ACCESS_CONTAINER,
        "--", "df", "-h", PVC_RESULTS_PATH,
    )
    if usage.returncode == 0:
        for line in usage.stdout.splitlines()[1:]:
            print(f"  usage  {line.strip()}")

    dirs, err = find_pvc_results(r.namespace)
    if err:
        r.skip(f"PVC not inspectable: {err}")
        return
    if not dirs:
        r.skip("PVC has no result directories")
        return

    on_host = host_result_dirs(workspace)
    for d in sorted(dirs):
        if d in on_host:
            r.run(
                f"delete {PVC_RESULTS_PATH}/{d} (copy present on host)",
                "exec", DATA_ACCESS_POD, "-c", DATA_ACCESS_CONTAINER,
                "--", "rm", "-rf", f"{PVC_RESULTS_PATH}/{d}",
            )
        else:
            # Not an error: an interrupted run leaves results here and nowhere
            # else, and those are the only copy in existence.
            r.skip(f"KEEP {PVC_RESULTS_PATH}/{d} -- no copy under {workspace}/*/results/")


def reset_controller(r: Reset, timeout: str) -> None:
    print("\nWVA controller (flush analyzer in-memory state)")
    deploy = find_controller_deployment(r.namespace)
    if not deploy:
        r.skip("no WVA controller deployment found in this namespace")
        return
    if not r.run(f"rollout restart deploy/{deploy}", "rollout", "restart", f"deploy/{deploy}"):
        return
    if r.apply:
        proc = kubectl(
            r.namespace, "rollout", "status", f"deploy/{deploy}", f"--timeout={timeout}",
        )
        print(f"        {proc.stdout.strip() or proc.stderr.strip()}")
        if proc.returncode != 0:
            r.failed.append(f"deploy/{deploy} did not become ready within {timeout}")


def reset_decode(r: Reset, timeout: str) -> None:
    print("\nDecode pods (flush the vLLM prefix cache)")
    targets = find_scaled_deployments(r.namespace)
    if not targets:
        r.skip("no ScaledObject in this namespace -- nothing identified as decode")
        return

    for so, deploy, paused in targets:
        if paused is not None:
            # A rollout restart at zero replicas is a no-op, so say why rather
            # than reporting a restart that did nothing.
            r.skip(
                f"deploy/{deploy} -- scaledobject/{so} is paused at "
                f"{paused} replica(s); nothing running to restart"
            )
            continue
        if not r.run(
            f"rollout restart deploy/{deploy} (via scaledobject/{so})",
            "rollout", "restart", f"deploy/{deploy}",
        ):
            continue
        if r.apply:
            # Model load dominates this: allow it well past the controller's.
            proc = kubectl(
                r.namespace, "rollout", "status", f"deploy/{deploy}",
                f"--timeout={timeout}",
            )
            print(f"        {proc.stdout.strip() or proc.stderr.strip()}")
            if proc.returncode != 0:
                r.failed.append(f"deploy/{deploy} did not become ready within {timeout}")


def report_untouched(r: Reset) -> None:
    print("\nNot touched (raise the scope deliberately if you need any of these)")
    for line in [
        "ScaledObjects / KEDA-generated HPAs -- including their pause state",
        "Deployments, Services, InferencePool, gateway -- the stack's shape",
        "model PVC, download-model Job, data-access pod -- avoids a model re-download",
        "local run directories under the workspace -- those are the results",
        "anything cluster-scoped -- out of reach at this scope by design",
    ]:
        print(f"  keep  {line}")

    for so, deploy, paused in find_scaled_deployments(r.namespace):
        if paused is not None:
            print(
                f"\nNOTE: scaledobject/{so} is PAUSED at {paused} replica(s).\n"
                f"      deploy/{deploy} will not scale, and a run started now\n"
                f"      would trace flat -- which reads as an autoscaling result.\n"
                f"      Un-pause with:\n"
                f"        kubectl annotate scaledobject/{so} -n {r.namespace} \\\n"
                f"          autoscaling.keda.sh/paused-replicas-"
            )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Reset per-run state in one namespace. Dry run unless --apply.",
    )
    parser.add_argument("-n", "--namespace", required=True)
    parser.add_argument(
        "--workspace", default=".",
        help="directory holding the <user>-<timestamp> run directories; used to "
             "verify a PVC result set was copied back before reclaiming it",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="actually perform the reset (default: report only)",
    )
    parser.add_argument("--skip-pvc", action="store_true", help="leave the workload PVC alone")
    parser.add_argument("--skip-restart", action="store_true", help="do not restart any pods")
    parser.add_argument("--controller-timeout", default="120s")
    parser.add_argument("--decode-timeout", default="600s")
    args = parser.parse_args()

    workspace = Path(args.workspace).resolve()
    if not workspace.is_dir():
        print(f"ERROR: workspace {workspace} is not a directory", file=sys.stderr)
        sys.exit(1)

    probe = kubectl(args.namespace, "get", "namespace", args.namespace, "-o", "name")
    if probe.returncode != 0:
        print(
            f"ERROR: namespace {args.namespace} not reachable: "
            f"{(probe.stderr or '').strip()}",
            file=sys.stderr,
        )
        sys.exit(1)

    mode = "APPLY" if args.apply else "DRY RUN -- nothing will be changed"
    print(f"Reset run state in namespace {args.namespace}   [{mode}]")
    print(f"Workspace: {workspace}")

    r = Reset(args.namespace, args.apply)
    reset_harness_objects(r)
    if args.skip_pvc:
        print("\nWorkload PVC results")
        r.skip("--skip-pvc")
    else:
        reset_pvc_results(r, workspace)
    if args.skip_restart:
        print("\nPod restarts")
        r.skip("--skip-restart")
    else:
        reset_controller(r, args.controller_timeout)
        reset_decode(r, args.decode_timeout)
    report_untouched(r)

    print(
        f"\n{len(r.planned)} action(s) {'performed' if args.apply else 'planned'}, "
        f"{len(r.skipped)} skipped, {len(r.failed)} failed"
    )
    if not args.apply and r.planned:
        print("Re-run with --apply to perform them.")
    if r.failed:
        for f in r.failed:
            print(f"  FAILED: {f}")
        sys.exit(1)


if __name__ == "__main__":
    main()
