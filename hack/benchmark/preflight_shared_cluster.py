#!/usr/bin/env python3
"""
preflight_shared_cluster.py — abort before a standup can damage a shared cluster.

Why this exists
---------------
Our shared-cluster safety net has three levels:

  L1  operator discipline (explicit -n on every call, read-only until approved)
  L2  this repo's Makefile/scripts (namespace required, step_02 excluded, the
      fork clone never force-synced)
  L3  our llm-d-benchmark FORK, which presence-gates every cluster-scoped
      operation the upstream standup would otherwise perform

L3 is the layer that actually blocks writes, and it has a structural weakness:
every gate is a *presence* gate. It skips the dangerous operation **because the
shared object already exists**. That is fail-safe while the object is there and
fail-DANGEROUS the moment it is not, because absence reads as "not installed
yet, go install it".

The worst case is prometheus-adapter. Our clone skips installing it only because
the cluster-scoped ClusterRole `prometheus-adapter-resource-reader` exists — and
on pokprod that ClusterRole is a hand-made stub with no real helm release behind
it. Delete the stub and the standup performs a genuine
`helm install prometheus-adapter`, which registers the
`v1beta1.external.metrics.k8s.io` APIService. That APIService is a cluster-wide
singleton currently owned by KEDA (openshift-keda/keda-metrics-apiserver), so
taking it over would break every KEDA-driven autoscaler on the cluster —
other tenants' included.

Nothing asserted those preconditions before a run. This script does: it turns
"silently take the destructive path" into "refuse to start".

It is read-only. It performs no writes of any kind.

Namespace discipline
--------------------
Every kubectl invocation carries an explicit `-n <namespace>`, including the
ones querying cluster-scoped resources where kubectl accepts and ignores it.
That is deliberate: it removes this script's own scope classification from the
loop, so a resource misjudged as cluster-scoped cannot silently fall through to
whatever the current context's default namespace happens to be.

Note the flag is a net against misclassification, NOT a scope restriction --
kubectl ignores it for genuinely cluster-scoped resources, so `-n` alone would
not make a ClusterRole/SCC/APIService *write* namespace-scoped. Those still
depend on the L3 gates this script verifies.

Usage
-----
  python3 preflight_shared_cluster.py -n dhl-wva-209 \
      --repo-dir /path/to/llm-d-benchmark --expect-ref wva-ta-benchmark

  # look without gating (always exits 0)
  python3 preflight_shared_cluster.py -n dhl-wva-209 --report-only

Exit status: 0 if every gating check passed, 1 otherwise.
"""

import argparse
import json
import subprocess
import sys
from pathlib import Path

# The APIService that a real prometheus-adapter install would claim, and who is
# expected to own it on this cluster. If ownership has already moved, we must not
# run a standup until a human has looked at why.
EXTERNAL_METRICS_APISERVICE = "v1beta1.external.metrics.k8s.io"
EXPECTED_METRICS_OWNER = "openshift-keda/keda-metrics-apiserver"

# SCCs that step_09 grants to the model ServiceAccount. It must do so with the
# namespace-scoped `-z <sa> -n <ns>` form, which creates a RoleBinding to
# system:openshift:scc:<scc>. The cluster-wide form would instead append our SA
# to the shared SCC object's .users list -- a mutation of cluster-global state.
SCCS_GRANTED_BY_STANDUP = ["anyuid", "privileged"]

# Guard functions that MUST be present in the clone. Their absence means the
# clone is upstream code, not our fork, and the standup would run unguarded.
REQUIRED_FORK_GUARDS = [
    (
        "llmdbenchmark/standup/steps/step_03_workload_monitoring.py",
        "_uwm_enabled",
        "blocks wholesale overwrite of cluster-monitoring-config in openshift-monitoring",
    ),
    (
        "llmdbenchmark/standup/steps/step_07_deploy_setup.py",
        "_gateway_provider_present",
        "blocks re-applying istio-base/istiod into the shared istio-system",
    ),
    (
        "llmdbenchmark/standup/wva.py",
        "_find_existing_prometheus_adapter_release",
        "blocks helm install prometheus-adapter (would claim the metrics APIService)",
    ),
    (
        "llmdbenchmark/standup/wva.py",
        "_cluster_roles_present",
        "blocks overwriting the allow-thanos-querier-api-access ClusterRole",
    ),
]


class Report:
    """Collects check outcomes and renders them as an aligned table."""

    def __init__(self):
        self.rows = []
        self.failed = 0

    def add(self, gating, ok, check, detail):
        if ok:
            status = "PASS"
        elif gating:
            status = "FAIL"
            self.failed += 1
        else:
            status = "WARN"
        self.rows.append((status, check, detail))

    def render(self):
        width = max((len(c) for _, c, _ in self.rows), default=0)
        for status, check, detail in self.rows:
            marker = {"PASS": "  ok  ", "FAIL": " FAIL ", "WARN": " warn "}[status]
            print(f"[{marker}] {check.ljust(width)}  {detail}")


def kubectl(namespace, *args):
    """Run a read-only kubectl command, always with an explicit -n.

    Returns (ok, stdout). Never raises on a non-zero exit -- a missing object is
    a legitimate result that the caller interprets.
    """
    cmd = ["kubectl", *args, "-n", namespace]
    proc = subprocess.run(cmd, capture_output=True, text=True, check=False)
    return proc.returncode == 0, proc.stdout.strip()


def get_json(namespace, *args):
    ok, out = kubectl(namespace, *args, "-o", "json")
    if not ok or not out:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return None


def check_namespace_exists(rep, ns):
    ok, out = kubectl(ns, "get", "namespace", ns, "--ignore-not-found", "-o", "name")
    rep.add(
        True,
        bool(ok and out),
        f"target namespace {ns} exists",
        out or "NOT FOUND -- wrong cluster, or the namespace was removed",
    )


def check_uwm_namespace(rep, ns):
    """Precondition for step_03's _uwm_enabled gate."""
    target = "openshift-user-workload-monitoring"
    ok, out = kubectl(ns, "get", "namespace", target, "--ignore-not-found", "-o", "name")
    present = bool(ok and out)
    rep.add(
        True,
        present,
        "L3 gate: cluster-monitoring-config",
        f"ns/{target} present -- step_03 will SKIP the overwrite"
        if present
        else f"ns/{target} MISSING -- step_03 would OVERWRITE the shared "
        "cluster-monitoring-config in openshift-monitoring",
    )


def check_istio_crd(rep, ns):
    """Precondition for step_07's _gateway_provider_present gate."""
    crd = "gateways.networking.istio.io"
    ok, out = kubectl(ns, "get", "crd", crd, "--ignore-not-found", "-o", "name")
    present = bool(ok and out)
    rep.add(
        True,
        present,
        "L3 gate: istio control plane",
        f"crd/{crd} present -- step_07 will SKIP the cluster-scoped helmfile"
        if present
        else f"crd/{crd} MISSING -- step_07 would install istio-base/istiod "
        "into the shared istio-system",
    )


def check_prometheus_adapter_stub(rep, ns):
    """Precondition for wva.py's _find_existing_prometheus_adapter_release gate.

    The gate reads this ClusterRole's helm ownership annotations, so the object
    existing is not enough -- both annotations must be readable or the probe
    returns "not installed" and the install proceeds.
    """
    name = "prometheus-adapter-resource-reader"
    obj = get_json(ns, "get", "clusterrole", name, "--ignore-not-found")
    annotations = (obj or {}).get("metadata", {}).get("annotations", {}) or {}
    release = annotations.get("meta.helm.sh/release-name")
    release_ns = annotations.get("meta.helm.sh/release-namespace")
    ok = bool(release and release_ns)
    rep.add(
        True,
        ok,
        "L3 gate: prometheus-adapter install",
        f"clusterrole/{name} owned by release {release!r} in {release_ns!r} "
        "-- wva.py will REUSE, not install"
        if ok
        else f"clusterrole/{name} missing or unannotated -- wva.py would run a "
        "real `helm install prometheus-adapter` and claim "
        f"{EXTERNAL_METRICS_APISERVICE}",
    )


def check_thanos_clusterrole(rep, ns):
    """Precondition for wva.py's _cluster_roles_present gate."""
    name = "allow-thanos-querier-api-access"
    ok, out = kubectl(ns, "get", "clusterrole", name, "--ignore-not-found", "-o", "name")
    present = bool(ok and out)
    rep.add(
        True,
        present,
        "L3 gate: thanos-querier ClusterRole",
        f"clusterrole/{name} present -- 22_prometheus-rbac apply will be SKIPPED"
        if present
        else f"clusterrole/{name} MISSING -- the standup would apply "
        "22_prometheus-rbac and overwrite its rules",
    )


def check_metrics_apiservice_owner(rep, ns):
    """The blast radius itself: who currently serves external metrics."""
    obj = get_json(ns, "get", "apiservice", EXTERNAL_METRICS_APISERVICE,
                   "--ignore-not-found")
    if obj is None:
        rep.add(
            True,
            False,
            "shared invariant: external metrics owner",
            f"apiservice/{EXTERNAL_METRICS_APISERVICE} NOT FOUND -- expected "
            f"{EXPECTED_METRICS_OWNER}; do not run a standup until this is understood",
        )
        return
    svc = obj.get("spec", {}).get("service", {}) or {}
    owner = f"{svc.get('namespace')}/{svc.get('name')}"
    ok = owner == EXPECTED_METRICS_OWNER
    rep.add(
        True,
        ok,
        "shared invariant: external metrics owner",
        f"{EXTERNAL_METRICS_APISERVICE} -> {owner} (as expected)"
        if ok
        else f"{EXTERNAL_METRICS_APISERVICE} -> {owner}, expected "
        f"{EXPECTED_METRICS_OWNER} -- ownership already moved; a standup could "
        "compound the damage",
    )


def check_scc_users_clean(rep, ns):
    """Assert prior runs used the namespace-scoped SCC form.

    If our service accounts have leaked into a cluster-global SCC's .users list,
    something used `oc adm policy add-scc-to-user` without -n and mutated shared
    state. That is a regression we want to catch before adding more.
    """
    prefix = f"system:serviceaccount:{ns}:"
    for scc in SCCS_GRANTED_BY_STANDUP:
        obj = get_json(ns, "get", "scc", scc, "--ignore-not-found")
        if obj is None:
            rep.add(False, False, f"shared invariant: scc/{scc} .users",
                    "could not read the SCC (insufficient rights?) -- not gating")
            continue
        leaked = [u for u in (obj.get("users") or []) if u.startswith(prefix)]
        rep.add(
            True,
            not leaked,
            f"shared invariant: scc/{scc} .users",
            f"{ns} absent -- grants are namespace-scoped RoleBindings"
            if not leaked
            else f"LEAKED into cluster-global SCC: {leaked}",
        )


def check_fork_clone(rep, repo_dir, expect_ref):
    """Confirm the clone that will run is our fork, on the expected branch."""
    repo = Path(repo_dir)
    if not (repo / ".git").exists():
        rep.add(True, False, "L3: fork clone present",
                f"{repo} is not a git checkout -- cannot verify which code runs")
        return

    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-parse", "--abbrev-ref", "HEAD"],
        capture_output=True, text=True, check=False,
    )
    branch = proc.stdout.strip()
    if expect_ref:
        rep.add(
            True,
            branch == expect_ref,
            "L3: fork clone branch",
            f"{branch} (as expected)"
            if branch == expect_ref
            else f"clone is on {branch!r}, expected {expect_ref!r} -- a different "
            "branch may not carry the safety patches",
        )
    else:
        rep.add(False, True, "L3: fork clone branch", f"{branch} (no --expect-ref given)")

    # Warn (do not gate) when the clone has work origin does not have: the run
    # is then not reproducible from origin alone.
    proc = subprocess.run(
        ["git", "-C", str(repo), "rev-list", "--count", f"origin/{branch}..HEAD"],
        capture_output=True, text=True, check=False,
    )
    ahead = proc.stdout.strip() or "?"
    proc = subprocess.run(
        ["git", "-C", str(repo), "status", "--porcelain"],
        capture_output=True, text=True, check=False,
    )
    dirty = len([l for l in proc.stdout.splitlines() if l.strip()])
    clean = ahead == "0" and dirty == 0
    rep.add(
        False,
        clean,
        "L3: fork clone vs origin",
        "in sync with origin"
        if clean
        else f"ahead {ahead} commit(s), {dirty} modified/untracked path(s) -- "
        "push before relying on this run being reproducible",
    )


def check_fork_guards(rep, repo_dir):
    """Confirm each safety patch is actually in the source that will execute."""
    repo = Path(repo_dir)
    for rel_path, symbol, purpose in REQUIRED_FORK_GUARDS:
        path = repo / rel_path
        try:
            present = symbol in path.read_text(encoding="utf-8")
        except OSError:
            present = False
        rep.add(
            True,
            present,
            f"L3 patch: {symbol}",
            purpose
            if present
            else f"NOT FOUND in {rel_path} -- clone looks like unguarded upstream code",
        )


def check_scc_call_form(rep, repo_dir):
    """Confirm step_09 still grants SCCs with the namespace-scoped form."""
    path = Path(repo_dir) / "llmdbenchmark/standup/steps/step_09_deploy_modelservice.py"
    try:
        src = path.read_text(encoding="utf-8")
    except OSError:
        rep.add(True, False, "L3: SCC grant form", f"could not read {path}")
        return
    if "add-scc-to-user" not in src:
        rep.add(False, True, "L3: SCC grant form", "step_09 grants no SCCs")
        return
    scoped = '"-z"' in src and '"-n"' in src
    rep.add(
        True,
        scoped,
        "L3: SCC grant form",
        "namespace-scoped (-z SA -n NS) -- creates a RoleBinding, not an SCC .users edit"
        if scoped
        else "cluster-wide form -- would append our SA to the shared SCC's .users list",
    )


def main():
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("-n", "--namespace", required=True,
                    help="the ONLY namespace this test may touch")
    ap.add_argument("--repo-dir",
                    help="path to the llm-d-benchmark fork clone (skips L3 source checks if omitted)")
    ap.add_argument("--expect-ref",
                    help="branch the fork clone must be on, e.g. wva-ta-benchmark")
    ap.add_argument("--report-only", action="store_true",
                    help="print the report but always exit 0")
    args = ap.parse_args()

    ns = args.namespace
    print(f"Shared-cluster pre-flight -- namespace {ns} (read-only, no writes)\n")

    rep = Report()
    check_namespace_exists(rep, ns)
    check_uwm_namespace(rep, ns)
    check_istio_crd(rep, ns)
    check_prometheus_adapter_stub(rep, ns)
    check_thanos_clusterrole(rep, ns)
    check_metrics_apiservice_owner(rep, ns)
    check_scc_users_clean(rep, ns)
    if args.repo_dir:
        check_fork_clone(rep, args.repo_dir, args.expect_ref)
        check_fork_guards(rep, args.repo_dir)
        check_scc_call_form(rep, args.repo_dir)
    else:
        rep.add(False, True, "L3 source checks",
                "skipped (--repo-dir not given)")

    rep.render()

    if rep.failed:
        print(f"\n{rep.failed} gating check(s) FAILED.")
        print("Do NOT run the standup: at least one cluster-scoped operation that "
              "our fork normally skips would now execute for real.")
        if args.report_only:
            print("(--report-only: exiting 0 anyway)")
            return 0
        return 1

    print("\nAll gating checks passed -- the fork's presence-gates will hold.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
