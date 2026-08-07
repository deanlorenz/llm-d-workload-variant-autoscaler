#!/usr/bin/env python3
"""
record_images.py — record the container images a benchmark run ACTUALLY used.

Why this exists
---------------
Image pins in hack/benchmark/.env express a *minimum* version, not an exact one:
they exist so a run cannot land on something older than what we have validated.
They are deliberately not a cross-run comparison mechanism, and a mismatch is
therefore not a reason to refuse a run.

What does matter is that each run records the images it actually ran on. Until
this script existed, it did not:

  * `plan/*/helm/modelservice.yaml` records the *rendered* (desired) images --
    what was asked for, which is not evidence of what ran.
  * `environment/context.ctx` is only the kubeconfig.
  * The WVA controller image -- the subject of the whole benchmark -- appeared
    nowhere at all, because this repo's Makefile deploys it rather than
    llmdbenchmark.

So a run's results could not be attributed to a controller build after the fact.
This script observes the live cluster and writes the answer into the run
artifacts.

It is read-only with respect to the cluster: it performs no writes of any kind.
Its only output is a file under the run directory (and a summary on stdout).

Exit status is 0 even when images differ from their pins -- drift is reported,
never enforced. `--strict` is available for a caller that does want a gate, but
no Makefile target uses it.

Namespace discipline
--------------------
Every kubectl invocation carries an explicit `-n <namespace>`, matching
preflight_shared_cluster.py. See that script's header for why this is done even
for resources where kubectl ignores the flag.

Usage
-----
  # flag drift before spending GPU time, write nothing
  python3 record_images.py -n dhl-wva-209 --wva-image repo:tag --vllm-image repo:tag

  # record what ran, into the run's own artifacts
  python3 record_images.py -n dhl-wva-209 --wva-image repo:tag \
      --out <run-dir>/environment/images.yaml
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Container-name -> role. Roles are keyed off the container name rather than the
# image string so a run using a mirror or a private rebuild is still classified.
ROLE_BY_CONTAINER = {
    "manager": "wva-controller",
    "vllm": "vllm",
    "epp": "epp",
    # All three run images.benchmark. The harness pod itself is per-run, but the
    # download job and the data-access pod persist between runs, so the harness
    # pin stays checkable when no run is in flight.
    "harness": "harness",
    "downloader": "harness",
    "rsync": "harness",
}

# Roles we pin but deliberately do not treat as comparable-by-version, because
# their tags are build labels rather than semantic versions.
NON_SEMVER_ROLES = {"wva-controller"}

SEMVER_RE = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)")


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


def split_image(image: str) -> tuple[str, str]:
    """Split repo:tag, being careful about a registry port (host:5000/x:tag)."""
    if "@" in image:  # digest-pinned: repo@sha256:...
        repo, _, digest = image.partition("@")
        return repo, digest
    head, sep, tail = image.rpartition(":")
    if sep and "/" not in tail:
        return head, tail
    return image, ""


def semver(tag: str) -> tuple[int, int, int] | None:
    m = SEMVER_RE.match(tag)
    return (int(m.group(1)), int(m.group(2)), int(m.group(3))) if m else None


def compare(actual: str, pin: str, role: str) -> tuple[str, str]:
    """Return (status, note) for an observed image against its pin.

    Pins are MINIMUM versions, so a newer actual is fine and must not be noise.
    """
    if not pin:
        return "unpinned", "no pin configured"
    if actual == pin:
        return "match", ""

    a_repo, a_tag = split_image(actual)
    p_repo, p_tag = split_image(pin)

    if a_repo != p_repo:
        return "differs", f"different repository (pinned {p_repo})"

    if role in NON_SEMVER_ROLES:
        return "differs", f"tag {a_tag!r} != pinned {p_tag!r} (build label, not a version)"

    a_ver, p_ver = semver(a_tag), semver(p_tag)
    if a_ver is None or p_ver is None:
        return "differs", f"tag {a_tag!r} != pinned {p_tag!r} (not version-comparable)"
    if a_ver >= p_ver:
        return "ok-newer", f"{a_tag} >= pinned minimum {p_tag}"
    return "below-pin", f"{a_tag} is OLDER than the pinned minimum {p_tag}"


def observe(namespace: str) -> list[dict]:
    """Every container image running in the namespace, with where it came from.

    Pods are the source of truth -- a Deployment spec is intent, a running pod is
    fact. Deployments are consulted only to attribute a pod to a workload.
    """
    found: list[dict] = []
    pods = get_json(namespace, "get", "pods")
    if not pods:
        return found

    for pod in pods.get("items", []):
        meta = pod.get("metadata", {})
        pod_name = meta.get("name", "?")
        phase = (pod.get("status") or {}).get("phase", "?")
        spec = pod.get("spec") or {}
        statuses = {
            cs.get("name"): cs
            for cs in (pod.get("status") or {}).get("containerStatuses", []) or []
        }
        for container in spec.get("containers", []) or []:
            cname = container.get("name", "?")
            cstatus = statuses.get(cname) or {}
            found.append(
                {
                    "role": ROLE_BY_CONTAINER.get(cname, cname),
                    "container": cname,
                    "pod": pod_name,
                    "phase": phase,
                    # spec.image is the request; status.image/imageID is what the
                    # kubelet actually resolved and ran. Record both -- a floating
                    # tag makes them disagree, and the digest is the only durable
                    # identity.
                    "image": container.get("image", ""),
                    "running_image": cstatus.get("image", ""),
                    "image_id": cstatus.get("imageID", ""),
                }
            )
    return found


def build_record(namespace: str, observed: list[dict], pins: dict[str, str]) -> dict:
    entries = []
    flags = []
    seen_roles = set()

    for item in sorted(observed, key=lambda i: (i["role"], i["pod"])):
        role = item["role"]
        seen_roles.add(role)
        pin = pins.get(role, "")
        actual = item["running_image"] or item["image"]
        status, note = compare(actual, pin, role)
        entry = dict(item)
        entry["pin"] = pin
        entry["status"] = status
        if note:
            entry["note"] = note
        entries.append(entry)

        if status in ("below-pin", "differs"):
            flags.append(f"{role}: {actual} -- {note}")

    for role, pin in pins.items():
        if pin and role not in seen_roles:
            flags.append(f"{role}: pinned {pin} but no running container found")

    return {
        "recorded_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "namespace": namespace,
        "pins_are_minimums": True,
        "containers": entries,
        "flags": flags,
    }


def to_yaml(record: dict) -> str:
    """Emit YAML without requiring PyYAML -- the shape here is fully known."""
    lines = [
        "# Container images ACTUALLY observed running, recorded by",
        "# hack/benchmark/record_images.py. Pins are MINIMUM versions from",
        "# hack/benchmark/.env; a newer image is expected, not an error.",
        f"recorded_at: {record['recorded_at']}",
        f"namespace: {record['namespace']}",
        "pins_are_minimums: true",
        "containers:",
    ]
    for e in record["containers"]:
        lines.append(f"  - role: {e['role']}")
        for key in ("container", "pod", "phase", "image", "running_image",
                    "image_id", "pin", "status", "note"):
            value = e.get(key)
            if value:
                lines.append(f"    {key}: {json.dumps(value)}")
    lines.append("flags:")
    if record["flags"]:
        lines.extend(f"  - {json.dumps(f)}" for f in record["flags"])
    else:
        lines.append("  []")
    return "\n".join(lines) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--namespace", required=True)
    ap.add_argument("--wva-image", default="", help="pinned WVA controller image")
    ap.add_argument("--vllm-image", default="", help="pinned vLLM image")
    ap.add_argument("--harness-image", default="", help="pinned harness image")
    ap.add_argument("--out", type=Path, default=None,
                    help="write the record here (parent dirs created)")
    ap.add_argument("--strict", action="store_true",
                    help="exit 1 if anything is flagged (no Makefile target uses this)")
    args = ap.parse_args()

    pins = {
        "wva-controller": args.wva_image,
        "vllm": args.vllm_image,
        "harness": args.harness_image,
    }

    observed = observe(args.namespace)
    if not observed:
        print(f"WARNING: no pods observed in namespace {args.namespace} — "
              f"nothing to record.", file=sys.stderr)

    record = build_record(args.namespace, observed, pins)

    print(f"Images observed in {args.namespace}:")
    for e in record["containers"]:
        actual = e.get("running_image") or e.get("image")
        marker = {"match": "  ", "ok-newer": "  ", "unpinned": "  "}.get(e["status"], "! ")
        # Show a non-Running phase: a Succeeded job pod's image is still evidence,
        # but it is not the currently-serving stack and must not read as if it were.
        phase = "" if e.get("phase") == "Running" else f"  ({e.get('phase')})"
        print(f"  {marker}{e['role']:<16} {actual}  [{e['status']}]{phase}")

    if record["flags"]:
        print("")
        print("FLAGS (reported, not enforced — pins are minimum versions):")
        for f in record["flags"]:
            print(f"  ! {f}")

    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(to_yaml(record))
        print(f"\nRecorded to: {args.out}")

    raise SystemExit(1 if (args.strict and record["flags"]) else 0)


if __name__ == "__main__":
    main()
