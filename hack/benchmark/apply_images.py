#!/usr/bin/env python3
"""
apply_images.py — bring a STANDING stack's controller image up to the pinned one.

Why this exists
---------------
The WVA controller image pin reaches the cluster only through standup, which
substitutes it as a token into the scenario yaml. That means changing
`WVA_IMAGE_TAG` for an already-running stack does nothing at all: the pin says
one thing and the cluster keeps running another.

That gap makes an A/B across controller images impossible to do cleanly. The
only options were a full re-standup, which changes far more than the controller
and so confounds the comparison, or a hand-patch, which leaves no record of what
was done. This script is the missing third option: change the controller image,
change nothing else, and record it.

Scope: the WVA controller Deployment's container image. Nothing else. It does not
touch the model server, the harness, KEDA, or any cluster-scoped object.

Dry-run by default
------------------
Prints what would change and exits, matching reset_run.py's convention. Pass
--apply to act. This is deliberate for a shared cluster: the read-only form is
useful on its own as a "does the cluster match the pin" check.

Composes with the pre-run restart
---------------------------------
Applying a new image rolls the controller pod, which flushes the in-memory
capacity history -- the same thing benchmark-restart-controller exists to do. So
an image change inherently satisfies the "restart before every run" requirement;
it does not need to be followed by a separate restart.
"""
import argparse
import json
import subprocess
import sys

CONTROLLER_DEPLOYMENT = "workload-variant-autoscaler-controller-manager"
CONTROLLER_CONTAINER = "manager"


def kubectl(namespace: str, *args: str) -> subprocess.CompletedProcess:
    """Run kubectl with an explicit namespace, always. Never raises."""
    return subprocess.run(
        ["kubectl", "-n", namespace, *args],
        capture_output=True, text=True,
    )


def live_images(namespace: str) -> tuple[str | None, str | None]:
    """Return (spec image, running image) for the controller.

    Both, because they can disagree: the spec image is what was requested, the
    running image is what the kubelet actually resolved. A floating tag or a
    stalled rollout is exactly the case where the difference matters, and that is
    the case this script is most often run to diagnose.
    """
    proc = kubectl(namespace, "get", "deploy", CONTROLLER_DEPLOYMENT, "-o", "json")
    if proc.returncode != 0:
        return None, None
    dep = json.loads(proc.stdout)
    spec_image = None
    for c in dep["spec"]["template"]["spec"].get("containers", []):
        if c.get("name") == CONTROLLER_CONTAINER:
            spec_image = c.get("image")

    running = None
    pods = kubectl(namespace, "get", "pods",
                   "-l", "app.kubernetes.io/name=workload-variant-autoscaler",
                   "-o", "json")
    if pods.returncode == 0:
        for pod in json.loads(pods.stdout).get("items", []):
            if (pod.get("status") or {}).get("phase") != "Running":
                continue
            for cs in (pod.get("status") or {}).get("containerStatuses", []) or []:
                if cs.get("name") == CONTROLLER_CONTAINER:
                    running = cs.get("image")
    return spec_image, running


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("-n", "--namespace", required=True)
    ap.add_argument("--wva-image", required=True,
                    help="pinned controller image, repo:tag")
    ap.add_argument("--apply", action="store_true",
                    help="actually patch (default is a dry run)")
    ap.add_argument("--timeout", default="300s",
                    help="rollout wait timeout")
    args = ap.parse_args()

    spec_image, running_image = live_images(args.namespace)
    if spec_image is None:
        print(f"ERROR: deployment {CONTROLLER_DEPLOYMENT} not found in "
              f"namespace {args.namespace}.", file=sys.stderr)
        return 1

    print(f"controller image, namespace {args.namespace}:")
    print(f"  pinned:  {args.wva_image}")
    print(f"  spec:    {spec_image}")
    print(f"  running: {running_image or '(no running pod)'}")

    if spec_image == args.wva_image and running_image == args.wva_image:
        print("Already on the pinned image; nothing to do.")
        return 0

    # Spec matches but the running pod does not: the rollout never completed.
    # Patching again would be a no-op, so say what is actually wrong instead of
    # reporting success.
    if spec_image == args.wva_image and running_image != args.wva_image:
        print(f"\nWARNING: the deployment spec already requests the pinned "
              f"image, but the running pod is on {running_image!r}.")
        print("A previous rollout did not complete. Patching again would be a "
              "no-op -- investigate the pod (ImagePullBackOff, resource "
              "limits, a paused rollout) before running a benchmark on this.")
        return 1

    if not args.apply:
        print(f"\nDRY RUN -- would patch {CONTROLLER_DEPLOYMENT} container "
              f"{CONTROLLER_CONTAINER!r}:")
        print(f"  {spec_image}  ->  {args.wva_image}")
        print("Re-run with BENCHMARK_APPLY=true to act.")
        return 0

    patch = json.dumps({
        "spec": {"template": {"spec": {"containers": [
            {"name": CONTROLLER_CONTAINER, "image": args.wva_image}
        ]}}}
    })
    print(f"\nPatching {CONTROLLER_DEPLOYMENT} -> {args.wva_image}")
    proc = kubectl(args.namespace, "patch", "deploy", CONTROLLER_DEPLOYMENT,
                   "--type", "strategic", "-p", patch)
    if proc.returncode != 0:
        print(f"ERROR: patch failed: {proc.stderr.strip()}", file=sys.stderr)
        return 1
    print(proc.stdout.strip())

    print(f"Waiting for rollout (timeout {args.timeout})...")
    proc = kubectl(args.namespace, "rollout", "status", "deploy",
                   CONTROLLER_DEPLOYMENT, f"--timeout={args.timeout}")
    print(proc.stdout.strip() or proc.stderr.strip())
    if proc.returncode != 0:
        print("ERROR: rollout did not complete. The stack is in a mixed state "
              "-- do NOT start a run until this is resolved.", file=sys.stderr)
        return 1

    # Re-observe rather than trusting the patch: the whole point of this script
    # is that intent and reality can differ.
    spec_image, running_image = live_images(args.namespace)
    print("\nAfter rollout:")
    print(f"  spec:    {spec_image}")
    print(f"  running: {running_image or '(no running pod)'}")
    if running_image != args.wva_image:
        print(f"ERROR: running image is still {running_image!r}, expected "
              f"{args.wva_image!r}.", file=sys.stderr)
        return 1

    print("\nController is on the pinned image. The rollout also flushed the "
          "in-memory capacity history, so a separate restart before the run is "
          "not needed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
