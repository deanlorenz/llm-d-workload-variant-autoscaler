#!/usr/bin/env python3
"""Show or set the WVA analyzer list in the saturation-scaling ConfigMap.

Why this exists
---------------
`make benchmark-enable-v2-saturation` rewrites the *whole* `default` payload
(analyzers **and** kvCacheThreshold/queueLengthThreshold/kvSpareTrigger/
queueSpareTrigger/enableLimiter). That is fine as a one-shot "put the cluster in
the V2 saturation config" lever, but it is useless for an A/B experiment where
the only thing that may differ between arms is *which analyzers are enabled* --
using it would silently change the thresholds too, and any behavioural delta
could no longer be attributed to the analyzer set.

This helper edits only the `analyzers:` block of the existing `default` payload
and leaves every other line byte-identical, so arm A (saturation+throughput)
and arm B (saturation only) differ by exactly that one block.

It deliberately avoids PyYAML: the other hack/benchmark scripts run under the
system python3, which has no third-party packages. The payload is a flat
mapping with one nested list, so a line-based transform is sufficient and has
the bonus property of preserving comments and key order.

Usage
-----
  # print the live analyzer config
  python3 set_analyzers.py -n dhl-wva-209 --show

  # arm A: saturation + throughput (TA on)
  python3 set_analyzers.py -n dhl-wva-209 --analyzers saturation,throughput

  # arm B: saturation only (TA off)
  python3 set_analyzers.py -n dhl-wva-209 --analyzers saturation

The controller reads this ConfigMap at startup, so a restart is required for a
change to take effect -- `make benchmark-restart-controller` does that and is
invoked by the wrapping Makefile targets.
"""

import argparse
import json
import subprocess
import sys

CM_CANDIDATES = [
    # Kustomize installs use the short name; the controller prefers it when both
    # exist. Helm installs (what the benchmark standup uses) use the long one.
    "wva-saturation-scaling-config",
    "workload-variant-autoscaler-wva-saturation-scaling-config",
]
DATA_KEY = "default"
DEFAULT_SCORE = "1.0"


def run(cmd, check=True):
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if check and proc.returncode != 0:
        sys.exit(f"ERROR: {' '.join(cmd)} failed:\n{proc.stderr.strip()}")
    return proc


def find_configmap(namespace):
    for name in CM_CANDIDATES:
        proc = run(["kubectl", "get", "configmap", name, "-n", namespace, "-o", "name"],
                   check=False)
        if proc.returncode == 0:
            return name
    # Fall back to any ConfigMap whose name mentions saturation-scaling-config.
    proc = run(["kubectl", "get", "configmap", "-n", namespace, "-o", "name"])
    for line in proc.stdout.splitlines():
        name = line.removeprefix("configmap/").strip()
        if "saturation-scaling-config" in name:
            return name
    sys.exit(f"ERROR: no saturation-scaling-config ConfigMap in namespace {namespace}")


def read_payload(namespace, cm):
    proc = run(["kubectl", "get", "configmap", cm, "-n", namespace,
                "-o", f"jsonpath={{.data.{DATA_KEY}}}"])
    return proc.stdout


def strip_analyzers_block(payload):
    """Drop the `analyzers:` key and its indented list, keep all other lines."""
    kept, dropping = [], False
    for line in payload.splitlines():
        if dropping:
            # The block ends at the next line that starts in column 0 with
            # content (a sibling key). Blank lines and indented lines belong to
            # the block being dropped.
            if line.strip() and not line[0].isspace():
                dropping = False
            else:
                continue
        if line.strip().startswith("analyzers:"):
            dropping = True
            continue
        kept.append(line)
    return kept


def build_payload(payload, analyzers, score):
    block = ["analyzers:"]
    for name in analyzers:
        block.append(f"  - name: {name}")
        block.append(f"    score: {score}")
    lines = block + strip_analyzers_block(payload)
    return "\n".join(lines) + "\n"


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("-n", "--namespace", required=True)
    ap.add_argument("--analyzers",
                    help="comma-separated analyzer names, e.g. saturation,throughput")
    ap.add_argument("--score", default=DEFAULT_SCORE,
                    help=f"score applied to every analyzer (default {DEFAULT_SCORE})")
    ap.add_argument("--show", action="store_true",
                    help="print the live payload and exit without changing anything")
    args = ap.parse_args()

    if not args.show and not args.analyzers:
        ap.error("one of --show or --analyzers is required")

    cm = find_configmap(args.namespace)
    payload = read_payload(args.namespace, cm)

    if args.show:
        print(f"# configmap/{cm} -n {args.namespace} data.{DATA_KEY}")
        print(payload, end="" if payload.endswith("\n") else "\n")
        return

    analyzers = [a.strip() for a in args.analyzers.split(",") if a.strip()]
    if not analyzers:
        sys.exit("ERROR: --analyzers produced an empty list")

    new_payload = build_payload(payload, analyzers, args.score)
    if new_payload == payload:
        print(f"Analyzer set already {analyzers} in configmap/{cm}; nothing to do.")
        return

    print(f"configmap/{cm} -n {args.namespace}: setting analyzers to {analyzers}")
    print("--- before ---")
    print(payload, end="" if payload.endswith("\n") else "\n")
    print("--- after ----")
    print(new_payload, end="")

    patch = json.dumps({"data": {DATA_KEY: new_payload}})
    run(["kubectl", "patch", "configmap", cm, "-n", args.namespace,
         "--type=merge", "-p", patch])
    print(f"Patched configmap/{cm}. Restart the controller for it to take effect.")


if __name__ == "__main__":
    main()
