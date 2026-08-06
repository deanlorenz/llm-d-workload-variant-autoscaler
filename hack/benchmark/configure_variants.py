#!/usr/bin/env python3
"""
configure_variants.py — Configure a benchmark's WVA variant set from one YAML.

A benchmark deploys exactly one decode Deployment at standup. This script reads
a variant-set config that lists one or more variants of the *same* model and,
for each, ensures a KEDA ScaledObject that WVA discovers (via the
llm-d.ai/managed annotation) and drives. There is no "primary"/"secondary":
every entry is just a variant of the model, distinguished by cost and shape
(tensor-parallelism / GPUs-per-pod). The variants may be brought up in any
order; one of them simply happens to be the one standup already created.

Exactly one entry is marked `deployed: true` — the variant standup created.
Its ScaledObject is attached to the existing Deployment (converting any legacy
direct HPA the harness may have left). Every other entry is materialized as a
new Deployment (cloned from the deployed one with TP / GPU / label overrides)
plus its own ScaledObject.

A single-variant config (one entry, `deployed: true`) therefore just attaches an
autoscaler to the standup Deployment — no extra Deployment is created. A
two-variant config adds one more.

Common per-test setup (run once, independent of variant count):
  - a KEDA TriggerAuthentication (`wva-prometheus-auth`) borrowing the WVA
    controller SA token so Prometheus triggers authenticate to Thanos Querier
    (without it every trigger 401s → falls back to replicas=1 → nothing scales);
  - correcting the deployed Deployment's `llm-d.ai/variant` pod label so WVA's
    collector attributes its metrics/demand correctly.

Implements Topology B: one shared InferencePool/EPP fed by one or more
Deployments, each with its own KEDA ScaledObject at a different
llm-d.ai/variant-cost. With >1 variant, the WVA cost-aware optimizer scales the
most efficient variant (best capacity per unit cost) first and spills to the
others.

Label strategy
--------------
The InferencePool created by standup selects pods by:
  llm-d.ai/inferenceServing: "true"   (camelCase)
  llm-d.ai/model:            <hash>

A created (non-deployed) variant Deployment:
  - KEEPS  llm-d.ai/inferenceServing + llm-d.ai/model  → joins the pool
  - ADDS   wva.llmd.ai/variant: <suffix>                → unique selector
  - ADDS   llm-d.ai/variant:    <variant-name>          → unique selector

The deployed Deployment's selector is whatever standup created (it varies by
deploy path: kustomize, Helm modelservice chart, etc.).  It never claims
created-variant pods at runtime because Kubernetes ownerReferences make each pod
owned by exactly one Deployment's ReplicaSet; a ReplicaSet only adopts orphans.

All ScaledObjects share the same llm-d.ai/model-id annotation so the WVA solver
groups them under one model and applies cost-weighted scaling.

Config schema
-------------
  variants:
    - suffix: tp1              # required, unique; names the variant
      deployed: true           # exactly one entry; attaches SO to the standup Deployment
      variantCost: "10.0"      # default "5.0"
      minReplicas: 1           # default 1
      maxReplicas: 2           # default 10
      parallelism:
        tensor: 1              # rewrites --tensor-parallel-size (created variants only)
      resources:
        nvidia.com/gpu: 1      # limits+requests on GPU containers (created variants only)

For the `deployed: true` entry the parallelism / resources fields are ignored
(its shape is already baked in by standup); only cost / min / max apply.

Usage
-----
  python hack/benchmark/configure_variants.py -n NAMESPACE \\
      --config hack/benchmark/scenarios/guides/variants/<name>.yaml \\
      --prometheus-url https://thanos-querier.openshift-monitoring.svc.cluster.local:9091 \\
      --accelerator-name NVIDIA-H100-80GB-HBM3
"""

import argparse
import copy
import json
import re
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:
    print("ERROR: PyYAML is required. Install with: pip install pyyaml",
          file=sys.stderr)
    sys.exit(1)


# ---------------------------------------------------------------------------
# kubectl helpers
# ---------------------------------------------------------------------------

def kubectl(*args, stdin=None, check=True):
    cmd = ["kubectl"] + list(args)
    result = subprocess.run(cmd, capture_output=True, text=True, input=stdin)
    if check and result.returncode != 0:
        print(f"ERROR: {' '.join(cmd)}\n{result.stderr.strip()}", file=sys.stderr)
        sys.exit(1)
    return result.stdout


def kubectl_apply(obj, dry_run=False):
    payload = json.dumps(obj)
    if dry_run:
        print("---")
        print(json.dumps(obj, indent=2))
        return
    kubectl("apply", "-f", "-", stdin=payload)


def kubectl_delete(kind, name, namespace, dry_run=False):
    if dry_run:
        print(f"[dry-run] kubectl delete {kind} {name} -n {namespace}")
        return
    kubectl("delete", kind, name, "-n", namespace, "--ignore-not-found=true")


def _strip_managed(obj):
    """Remove server-managed fields before re-applying as a new object."""
    meta = obj.setdefault("metadata", {})
    for field in ("resourceVersion", "uid", "generation", "creationTimestamp",
                  "managedFields", "selfLink"):
        meta.pop(field, None)
    ann = meta.get("annotations", {})
    ann.pop("kubectl.kubernetes.io/last-applied-configuration", None)
    if not ann:
        meta.pop("annotations", None)
    obj.pop("status", None)
    tmpl_meta = obj.get("spec", {}).get("template", {}).get("metadata", {})
    tmpl_meta.pop("creationTimestamp", None)
    tmpl_meta.pop("annotations", None)
    return obj


# ---------------------------------------------------------------------------
# Variant config parsing
# ---------------------------------------------------------------------------

VARIANT_DEFAULTS = {
    "variantCost": "5.0",
    "minReplicas": 1,
    "maxReplicas": 10,
    "deployed": False,
}


def _fail(msg):
    print(f"ERROR: {msg}", file=sys.stderr)
    sys.exit(1)


def _validate_variant_entry(entry, path, idx):
    """Validate one variants[] entry in place, applying defaults."""
    if not isinstance(entry, dict):
        _fail(f"{path}: variants[{idx}] must be a mapping, got "
              f"{type(entry).__name__}")
    suffix = entry.get("suffix")
    if not isinstance(suffix, str) or not suffix:
        _fail(f"{path}: variants[{idx}] must set a non-empty 'suffix'")
    for k, v in VARIANT_DEFAULTS.items():
        entry.setdefault(k, v)
    entry["variantCost"] = str(entry["variantCost"])
    entry["minReplicas"] = int(entry["minReplicas"])
    entry["maxReplicas"] = int(entry["maxReplicas"])
    entry["deployed"] = bool(entry["deployed"])
    return entry


def load_variants_config(path):
    """Load a variant-set yaml, validate, apply defaults, return the list.

    The document is a mapping with a non-empty `variants:` list. Each entry is
    validated by _validate_variant_entry. Suffixes must be unique and exactly
    one entry must set `deployed: true` (the variant standup already created).
    """
    p = Path(path)
    if not p.is_file():
        _fail(f"variant config not found: {p}")
    try:
        doc = yaml.safe_load(p.read_text()) or {}
    except yaml.YAMLError as e:
        _fail(f"failed to parse {p}: {e}")
    if not isinstance(doc, dict) or "variants" not in doc:
        _fail(f"variant config {p} must be a mapping with a 'variants:' list")
    variants = doc["variants"]
    if not isinstance(variants, list) or not variants:
        _fail(f"variant config {p}: 'variants' must be a non-empty list")
    seen = set()
    for i, entry in enumerate(variants):
        _validate_variant_entry(entry, p, i)
        if entry["suffix"] in seen:
            _fail(f"variant config {p}: duplicate suffix {entry['suffix']!r}")
        seen.add(entry["suffix"])
    deployed = [e for e in variants if e["deployed"]]
    if len(deployed) != 1:
        _fail(f"variant config {p}: exactly one entry must set 'deployed: true' "
              f"(found {len(deployed)})")
    return variants


# ---------------------------------------------------------------------------
# Resource discovery
# ---------------------------------------------------------------------------

def find_deployed_deployment(namespace):
    """Return the decode Deployment standup created (the one without a
    wva.llmd.ai/variant selector). Created variants carry that selector, so
    they are excluded -- exactly one un-suffixed decode Deployment is expected.
    """
    out = kubectl("get", "deployment", "-n", namespace, "-o", "json")
    items = json.loads(out)["items"]

    def _is_deployed(d):
        sel = d.get("spec", {}).get("selector", {}).get("matchLabels", {})
        if sel.get("llm-d.ai/role") != "decode":
            return False
        if "wva.llmd.ai/variant" in sel:
            return False
        return True

    deployed = [d for d in items if _is_deployed(d)]
    if not deployed:
        print("ERROR: No standup-deployed decode deployment found "
              "(spec.selector must include llm-d.ai/role=decode and must not "
              "include wva.llmd.ai/variant)",
              file=sys.stderr)
        sys.exit(1)
    if len(deployed) > 1:
        names = [d["metadata"]["name"] for d in deployed]
        print(f"ERROR: Multiple un-suffixed decode deployments found: {names}.",
              file=sys.stderr)
        sys.exit(1)
    return deployed[0]


def find_managed_scaledobject(namespace, deployment_name):
    """Return the ScaledObject with llm-d.ai/managed=true targeting deployment_name, or None."""
    out = kubectl("get", "scaledobject", "-n", namespace, "-o", "json",
                  check=False)
    try:
        items = json.loads(out)["items"]
    except (json.JSONDecodeError, KeyError):
        return None
    for so in items:
        ann = so.get("metadata", {}).get("annotations", {})
        if ann.get("llm-d.ai/managed") != "true":
            continue
        if so.get("spec", {}).get("scaleTargetRef", {}).get("name") == deployment_name:
            return so
    return None


def _hpa_scales_on_wva(hpa):
    """True if hpa has an external metric on wva_desired_replicas."""
    for m in hpa.get("spec", {}).get("metrics", []):
        ext = m.get("external") or {}
        if (ext.get("metric") or {}).get("name") == "wva_desired_replicas":
            return True
    return False


def find_managed_hpa(namespace, deployment_name):
    """Return a pre-existing HPA on deployment_name that the KEDA ScaledObject
    replaces, or None.

    KEDA's admission webhook rejects a ScaledObject while any HPA already
    targets the same Deployment. We remove one when it is clearly prior WVA
    scaling wiring -- either llm-d.ai/managed=true, or a direct external-metrics
    HPA scaling on the wva_desired_replicas metric (as the benchmark harness or
    an earlier manual run leaves behind, without the managed annotation). An
    unrelated user-created HPA is left untouched so the conflict surfaces
    instead of being silently deleted.
    """
    out = kubectl("get", "hpa", "-n", namespace, "-o", "json", check=False)
    try:
        hpas = json.loads(out)["items"]
    except (json.JSONDecodeError, KeyError):
        return None
    for hpa in hpas:
        if hpa.get("spec", {}).get("scaleTargetRef", {}).get("name") != deployment_name:
            continue
        ann = hpa.get("metadata", {}).get("annotations", {})
        if ann.get("llm-d.ai/managed") == "true" or _hpa_scales_on_wva(hpa):
            return hpa
    return None


def detect_model_id(primary_deployment):
    """Extract the served model name from the primary deployment's vLLM args or env."""
    containers = (primary_deployment.get("spec", {})
                  .get("template", {}).get("spec", {})
                  .get("containers", []))
    for c in containers:
        # Path 1: --model flag in args
        args = c.get("args") or []
        for i, a in enumerate(args):
            if a == "--model" and i + 1 < len(args):
                return args[i + 1]
            if isinstance(a, str) and a.startswith("--model="):
                return a.split("=", 1)[1]
        # Path 2: VLLM_SERVED_MODEL_NAME or MODEL_NAME env var
        for e in (c.get("env") or []):
            if e.get("name") in ("VLLM_SERVED_MODEL_NAME", "MODEL_NAME", "LLMDBENCH_DEPLOY_CURRENT_MODEL"):
                v = e.get("value", "")
                if v:
                    return v
    return None


# ---------------------------------------------------------------------------
# Container-arg overrides (unchanged from original)
# ---------------------------------------------------------------------------

def _override_tensor_parallel(containers, tp_value):
    flag = "--tensor-parallel-size"
    target = str(tp_value)
    for c in containers:
        args = c.get("args")
        replaced_in_args = False
        if isinstance(args, list):
            new_args = []
            i = 0
            while i < len(args):
                a = args[i]
                if a == flag and i + 1 < len(args):
                    new_args.extend([flag, target])
                    i += 2
                    replaced_in_args = True
                elif isinstance(a, str) and a.startswith(flag + "="):
                    new_args.append(f"{flag}={target}")
                    i += 1
                    replaced_in_args = True
                else:
                    new_args.append(a)
                    i += 1
            c["args"] = new_args
        env = c.setdefault("env", [])
        replaced_in_env = False
        for e in env:
            if e.get("name") == "VLLM_TENSOR_PARALLELISM":
                e["value"] = target
                e.pop("valueFrom", None)
                replaced_in_env = True
                break
        if not replaced_in_env:
            env.append({"name": "VLLM_TENSOR_PARALLELISM", "value": target})
        if not replaced_in_args and not replaced_in_env:
            if not isinstance(args, list):
                args = []
                c["args"] = args
            args.extend([flag, target])


def _override_gpu_resources(containers, gpu_count):
    target = str(gpu_count)
    for c in containers:
        res = c.get("resources") or {}
        limits = res.get("limits") or {}
        requests = res.get("requests") or {}
        if "nvidia.com/gpu" not in limits and "nvidia.com/gpu" not in requests:
            continue
        limits["nvidia.com/gpu"] = target
        requests["nvidia.com/gpu"] = target
        res["limits"] = limits
        res["requests"] = requests
        c["resources"] = res


def _read_tensor_parallel(containers):
    flag = "--tensor-parallel-size"
    for c in containers:
        args = c.get("args") or []
        env = c.get("env") or []
        env_tp = next(
            (e.get("value") for e in env if e.get("name") == "VLLM_TENSOR_PARALLELISM"),
            None,
        )
        for i, a in enumerate(args):
            if a == flag and i + 1 < len(args):
                v = args[i + 1]
                if isinstance(v, str) and v.startswith("$"):
                    return env_tp
                return v
            if isinstance(a, str) and a.startswith(flag + "="):
                v = a.split("=", 1)[1]
                if v.startswith("$"):
                    return env_tp
                return v
        if env_tp is not None:
            return env_tp
    return None


def _read_gpu_per_pod(containers):
    for c in containers:
        res = c.get("resources") or {}
        for bucket in ("limits", "requests"):
            v = (res.get(bucket) or {}).get("nvidia.com/gpu")
            if v is not None:
                return v
    return None


def _all_containers(deployment):
    spec = deployment.get("spec", {}).get("template", {}).get("spec", {})
    return list(spec.get("containers") or []) + list(spec.get("initContainers") or [])


# ---------------------------------------------------------------------------
# Object builders
# ---------------------------------------------------------------------------

def make_variant_deployment(primary, cfg, namespace):
    sec = copy.deepcopy(primary)
    _strip_managed(sec)

    suffix = cfg["suffix"]
    primary_name = primary["metadata"]["name"]
    sec_name = f"{primary_name}-{suffix}"
    sec["metadata"]["name"] = sec_name
    sec["metadata"]["namespace"] = namespace

    spec = sec["spec"]
    spec["replicas"] = 1

    # WVA's collector (buildInstanceKey in internal/collector/replica_metrics.go)
    # trusts this label as the pod's VariantAutoscaling name whenever it's
    # non-empty -- it only falls back to the correct owner-chain lookup when
    # the label is *missing*, not when it's wrong. The tracked VA/ScaledObject
    # is always named "<deployment>-scaler", so the label must match that
    # exactly or every pod's metrics (including the queue-backlog demand term)
    # get silently filed under an unattributed variant and dropped from the
    # analyzer's totalDemand -- root-caused 2026-07-25/26 (see
    # UnattributedReadyPods warnings in the controller log).
    variant_label = f"{sec_name}-scaler"

    tmpl_labels = spec["template"]["metadata"].setdefault("labels", {})
    tmpl_labels["wva.llmd.ai/variant"] = suffix
    tmpl_labels["llm-d.ai/variant"] = variant_label
    # Drop the primary's own discriminator: kept, this label makes the
    # variant's selector a superset of the primary's, which trips the
    # native HPA controller's AmbiguousSelector safety check (both
    # HPAs' derived pod selectors would overlap) and silently blocks
    # scaling on both variants -- root-caused 2026-07-25.
    tmpl_labels.pop("llm-d.ai/inference-serving", None)

    sel = spec["selector"]["matchLabels"]
    sel["wva.llmd.ai/variant"] = suffix
    sel["llm-d.ai/variant"] = variant_label
    sel.pop("llm-d.ai/inference-serving", None)

    pod_spec = spec["template"]["spec"]
    main_containers = pod_spec.setdefault("containers", [])

    tp = (cfg.get("parallelism") or {}).get("tensor")
    if tp is not None:
        _override_tensor_parallel(main_containers, tp)

    gpu = (cfg.get("resources") or {}).get("nvidia.com/gpu")
    if gpu is not None:
        _override_gpu_resources(main_containers, gpu)

    return sec


def make_variant_scaledobject(dep_name, so_name, model_id, cost, min_replicas,
                               max_replicas, namespace, prometheus_url,
                               accelerator_name):
    """Build a KEDA ScaledObject for a WVA variant.

    WVA discovers the ScaledObject via the llm-d.ai/managed annotation and
    emits wva_desired_replicas{variant_name=<so_name>, namespace=<namespace>}.
    KEDA reads that metric and drives the HPA it manages.
    """
    return {
        "apiVersion": "keda.sh/v1alpha1",
        "kind": "ScaledObject",
        "metadata": {
            "name": so_name,
            "namespace": namespace,
            "labels": {
                # Required for namespace-scoped WVA controller-instance filtering.
                "wva.llmd.ai/controller-instance": namespace,
                # Required for WVA to resolve accelerator type for k1/k2 computation.
                # Without this WVA emits with accelerator_type="unresolved" and withholds
                # accelerator-specific saturation metrics.
                "inference.optimization/acceleratorName": accelerator_name,
            },
            "annotations": {
                "llm-d.ai/managed": "true",
                "llm-d.ai/model-id": model_id,
                "llm-d.ai/variant-cost": str(cost),
            },
        },
        "spec": {
            "scaleTargetRef": {
                "apiVersion": "apps/v1",
                "kind": "Deployment",
                "name": dep_name,
            },
            "pollingInterval": 15,
            "cooldownPeriod": 300,
            "minReplicaCount": min_replicas,
            "maxReplicaCount": max_replicas,
            "fallback": {
                "failureThreshold": 3,
                "replicas": 1,
            },
            "advanced": {
                "restoreToOriginalReplicaCount": False,
                "horizontalPodAutoscalerConfig": {
                    "name": f"wva-keda-hpa-{dep_name}",
                    "behavior": {
                        "scaleUp": {
                            "stabilizationWindowSeconds": 0,
                            "policies": [
                                {"type": "Percent", "value": 100, "periodSeconds": 15},
                            ],
                        },
                        "scaleDown": {
                            "stabilizationWindowSeconds": 120,
                            "policies": [
                                {"type": "Percent", "value": 100, "periodSeconds": 15},
                            ],
                        },
                    },
                },
            },
            "triggers": [
                {
                    "type": "prometheus",
                    "name": "wva-desired-replicas",
                    "authenticationRef": {
                        "name": "wva-prometheus-auth",
                        "kind": "TriggerAuthentication",
                    },
                    "metadata": {
                        "serverAddress": prometheus_url,
                        "authModes": "bearer",
                        "query": (
                            f'wva_desired_replicas{{'
                            f'variant_name="{so_name}",'
                            f'namespace="{namespace}"'
                            f'}}'
                        ),
                        "threshold": "1",
                        "activationThreshold": "0",
                        "metricType": "Value",
                    },
                }
            ],
        },
    }


def find_wva_token_secret(namespace):
    """Return the name of the SA token Secret used by the WVA controller.

    Looks for a kubernetes.io/service-account-token Secret whose
    kubernetes.io/service-account.name annotation points at the WVA controller
    manager ServiceAccount.  Works with both the current Kustomize install
    (creates wva-controller-manager-token) and legacy Helm installs (which may
    use a different name prefix).  Falls back to the Kustomize default if no
    matching secret is found.
    """
    out = kubectl("get", "secret", "-n", namespace, "-o", "json", check=False)
    try:
        secrets = json.loads(out)["items"]
    except (json.JSONDecodeError, KeyError):
        secrets = []

    for s in secrets:
        if s.get("type") != "kubernetes.io/service-account-token":
            continue
        ann = s.get("metadata", {}).get("annotations", {})
        sa_name = ann.get("kubernetes.io/service-account.name", "")
        # Match any SA name that ends with "controller-manager" (covers both
        # the Kustomize install "wva-controller-manager" and legacy names).
        if sa_name.endswith("controller-manager"):
            data = s.get("data", {})
            if "token" in data and ("service-ca.crt" in data or "ca.crt" in data):
                return s["metadata"]["name"]

    # Fallback: standard Kustomize install name.
    return "wva-controller-manager-token"


def make_trigger_authentication(namespace, token_secret):
    """Build a KEDA TriggerAuthentication that borrows the WVA controller's SA token.

    The WVA ServiceAccount already holds cluster-monitoring-view, which is what
    Thanos Querier requires.  Without this, KEDA's Prometheus trigger gets 401
    and silently falls back to spec.fallback.replicas (=1), so scaling never fires.
    """
    ca_key = "service-ca.crt"
    # Check whether the secret actually has service-ca.crt; fall back to ca.crt.
    out = kubectl("get", "secret", token_secret, "-n", namespace, "-o", "json", check=False)
    try:
        data = json.loads(out).get("data", {})
        if ca_key not in data:
            ca_key = "ca.crt"
    except (json.JSONDecodeError, KeyError):
        pass

    return {
        "apiVersion": "keda.sh/v1alpha1",
        "kind": "TriggerAuthentication",
        "metadata": {
            "name": "wva-prometheus-auth",
            "namespace": namespace,
        },
        "spec": {
            "secretTargetRef": [
                {
                    "parameter": "bearerToken",
                    "name": token_secret,
                    "key": "token",
                },
                {
                    "parameter": "ca",
                    "name": token_secret,
                    "key": ca_key,
                },
            ],
        },
    }


# ---------------------------------------------------------------------------
# Per-variant configuration
# ---------------------------------------------------------------------------

def resolve_shared_model_id(namespace, dep_name, deployed_dep):
    """Determine the llm-d.ai/model-id every ScaledObject in the set shares.

    Prefer whatever a prior run or the harness already stamped (an existing
    managed ScaledObject, then a legacy managed HPA), then fall back to
    detecting the served model from the deployed Deployment's vLLM args/env,
    then the Deployment name.
    """
    so = find_managed_scaledobject(namespace, dep_name)
    if so is not None:
        mid = so.get("metadata", {}).get("annotations", {}).get("llm-d.ai/model-id")
        if mid:
            return mid
    hpa = find_managed_hpa(namespace, dep_name)
    if hpa is not None:
        mid = hpa.get("metadata", {}).get("annotations", {}).get("llm-d.ai/model-id")
        if mid:
            return mid
    return detect_model_id(deployed_dep) or dep_name


def remove_variantautoscaling_for(ns, dep_name, dry_run=False):
    """Delete the deprecated VariantAutoscaling CR that targets dep_name, if any.

    Annotation-based discovery replaces the CRD path. A lingering VariantAutoscaling
    keeps WVA's own controller-created HPA alive and double-emits
    wva_desired_replicas under the CR's name, so it must go before the annotated
    ScaledObject takes over. Idempotent: does nothing if the CRD or CR is absent.
    """
    out = kubectl("get", "variantautoscaling", "-n", ns, "-o", "json", check=False)
    try:
        items = json.loads(out)["items"]
    except (json.JSONDecodeError, KeyError):
        return
    for va in items:
        name = va.get("metadata", {}).get("name", "")
        target = va.get("spec", {}).get("scaleTargetRef", {}).get("name", "")
        if target == dep_name or name == dep_name:
            print(f"  Deleting deprecated VariantAutoscaling CR: {name}")
            kubectl_delete("variantautoscaling", name, ns, dry_run=dry_run)


def configure_deployed_variant(deployed_dep, cfg, ns, model_id, args):
    """Attach a WVA-managed KEDA ScaledObject to the standup-deployed Deployment.

    Annotation-only discovery: the ScaledObject carries llm-d.ai/managed=true and
    WVA synthesizes an in-memory VariantAutoscaling named after the ScaledObject
    itself (internal/utils/variant_fromannotations.go: va.Name = so.Name), so it
    emits wva_desired_replicas{variant_name=<so_name>, namespace=<ns>}.

    No llm-d.ai/variant pod label is used or required: with the label absent the
    collector's buildInstanceKey (internal/collector/replica_metrics.go) falls to
    the owner-walk and attributes the decode pods to this ScaledObject by name.

    Steps (each deletion idempotent / dry-run-aware):
      - delete the deprecated VariantAutoscaling CR for this Deployment;
      - delete any direct HPA targeting it (KEDA's webhook rejects a ScaledObject
        while an HPA already targets the same scaleTargetRef) -- but never KEDA's
        own wva-keda-hpa-<dep> or a ScaledObject-owned HPA (re-run safety);
      - remove a stale managed ScaledObject under a different name;
      - apply the ScaledObject built from this entry's cost / min / max, so the
        YAML stays the source of truth on re-runs.

    Returns a summary dict for the final table.
    """
    dep_name = deployed_dep["metadata"]["name"]
    so_name = f"{dep_name}-scaler"

    # Deprecated CRD path -> annotation path: remove the CR (and thus the HPA it owns).
    remove_variantautoscaling_for(ns, dep_name, dry_run=args.dry_run)

    # A prior run may have left a managed ScaledObject under a different name.
    existing_so = find_managed_scaledobject(ns, dep_name)
    if existing_so is not None and existing_so["metadata"]["name"] != so_name:
        stale = existing_so["metadata"]["name"]
        print(f"  Removing stale managed ScaledObject: {stale}")
        kubectl_delete("scaledobject", stale, ns, dry_run=args.dry_run)

    # KEDA rejects a ScaledObject while any HPA still targets the Deployment. Skip
    # KEDA's own managed HPA and any ScaledObject-owned HPA so re-runs don't fight KEDA.
    keda_hpa_name = f"wva-keda-hpa-{dep_name}"
    legacy_hpa = find_managed_hpa(ns, dep_name)
    if legacy_hpa is not None:
        hpa_name = legacy_hpa["metadata"]["name"]
        owned_by_so = any(
            o.get("kind") == "ScaledObject"
            for o in legacy_hpa.get("metadata", {}).get("ownerReferences", [])
        )
        if hpa_name != keda_hpa_name and not owned_by_so:
            print(f"  Deleting direct HPA first (KEDA will manage its own): {hpa_name}")
            kubectl_delete("hpa", hpa_name, ns, dry_run=args.dry_run)

    so_obj = make_variant_scaledobject(
        dep_name=dep_name,
        so_name=so_name,
        model_id=model_id,
        cost=cfg["variantCost"],
        min_replicas=cfg["minReplicas"],
        max_replicas=cfg["maxReplicas"],
        namespace=ns,
        prometheus_url=args.prometheus_url,
        accelerator_name=args.accelerator_name,
    )
    print(f"  Applying ScaledObject: {so_name}  "
          f"(cost={cfg['variantCost']}, min={cfg['minReplicas']}, max={cfg['maxReplicas']})")
    kubectl_apply(so_obj, dry_run=args.dry_run)

    containers = _all_containers(deployed_dep)
    return {
        "role": "deployed",
        "suffix": cfg["suffix"],
        "dep_name": dep_name,
        "so_name": so_name,
        "cost": cfg["variantCost"],
        "tp": _read_tensor_parallel(containers) or "1",
        "gpu": _read_gpu_per_pod(containers) or "1",
    }


def create_variant(deployed_dep, cfg, ns, model_id, args):
    """Materialize a new variant Deployment plus its ScaledObject.

    The Deployment is cloned from the deployed one with this entry's TP / GPU /
    label overrides applied. The ScaledObject carries an ownerReference to the
    new Deployment so deleting the Deployment garbage-collects the autoscaler.

    Returns a summary dict for the final table.
    """
    dep_name = deployed_dep["metadata"]["name"]
    suffix = cfg["suffix"]
    var_dep_name = f"{dep_name}-{suffix}"
    var_so_name = f"{var_dep_name}-scaler"

    var_dep = make_variant_deployment(deployed_dep, cfg, ns)
    var_so = make_variant_scaledobject(
        dep_name=var_dep_name,
        so_name=var_so_name,
        model_id=model_id,
        cost=cfg["variantCost"],
        min_replicas=cfg["minReplicas"],
        max_replicas=cfg["maxReplicas"],
        namespace=ns,
        prometheus_url=args.prometheus_url,
        accelerator_name=args.accelerator_name,
    )

    print(f"  Applying Deployment: {var_dep_name}")
    kubectl_apply(var_dep, dry_run=args.dry_run)

    # Owner refs on the ScaledObject point to the variant Deployment so deleting
    # the Deployment also garbage-collects the ScaledObject. The UID is only
    # available after the Deployment is applied.
    if not args.dry_run:
        var_dep_uid = json.loads(kubectl(
            "get", "deployment", var_dep_name, "-n", ns, "-o", "json",
        ))["metadata"]["uid"]
        owner_ref = {
            "apiVersion": "apps/v1",
            "kind": "Deployment",
            "name": var_dep_name,
            "uid": var_dep_uid,
            "blockOwnerDeletion": True,
            "controller": False,
        }
        var_so.setdefault("metadata", {}).setdefault("ownerReferences", []).append(owner_ref)

    print(f"  Applying ScaledObject: {var_so_name}  "
          f"(cost={cfg['variantCost']}, min={cfg['minReplicas']}, max={cfg['maxReplicas']})")
    kubectl_apply(var_so, dry_run=args.dry_run)

    var_containers = _all_containers(var_dep)
    return {
        "role": "created",
        "suffix": suffix,
        "dep_name": var_dep_name,
        "so_name": var_so_name,
        "cost": cfg["variantCost"],
        "tp": _read_tensor_parallel(var_containers) or "1",
        "gpu": _read_gpu_per_pod(var_containers) or "1",
    }


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    ap = argparse.ArgumentParser(
        description="Configure a benchmark's WVA variant set from one YAML "
                    "(no primary/secondary; exactly one entry is the "
                    "standup-deployed variant)."
    )
    ap.add_argument("-n", "--namespace", required=True,
                    help="Kubernetes namespace")
    ap.add_argument("--config", required=True,
                    help="Path to a variant-set yaml (see module docstring)")
    ap.add_argument("--prometheus-url", required=True,
                    help="Prometheus server URL for KEDA triggers")
    ap.add_argument("--accelerator-name", required=True,
                    help="Node GPU accelerator label (inference.optimization/acceleratorName) "
                         "WVA uses to resolve k1/k2 and accelerator-specific saturation metrics")
    ap.add_argument("--dry-run", action="store_true",
                    help="Print manifests as JSON without applying")
    args = ap.parse_args()

    ns = args.namespace
    variants = load_variants_config(args.config)
    created_count = sum(1 for v in variants if not v["deployed"])

    print(f"[1/4] Finding standup-deployed decode Deployment in namespace '{ns}'...")
    deployed_dep = find_deployed_deployment(ns)
    dep_name = deployed_dep["metadata"]["name"]
    model_hash = (deployed_dep.get("spec", {}).get("selector", {})
                  .get("matchLabels", {}).get("llm-d.ai/model", "?"))
    print(f"      {dep_name}  (llm-d.ai/model={model_hash})")

    model_id = resolve_shared_model_id(ns, dep_name, deployed_dep)
    print(f"      Shared model-id: {model_id!r}")

    print("[2/4] Ensuring TriggerAuthentication for Thanos Querier access...")
    token_secret = find_wva_token_secret(ns)
    print(f"      Using SA token secret: {token_secret}")
    trigger_auth = make_trigger_authentication(ns, token_secret)
    kubectl_apply(trigger_auth, dry_run=args.dry_run)

    print(f"[3/4] Configuring {len(variants)} variant(s) "
          f"(1 deployed + {created_count} created)...")
    results = []
    for v in variants:
        label = "deployed" if v["deployed"] else "create"
        print(f"  - variant '{v['suffix']}' [{label}]  cost={v['variantCost']} "
              f"min={v['minReplicas']} max={v['maxReplicas']}")
        if v["deployed"]:
            results.append(configure_deployed_variant(deployed_dep, v, ns, model_id, args))
        else:
            results.append(create_variant(deployed_dep, v, ns, model_id, args))

    print("[4/4] Done.")
    if args.dry_run:
        return

    print()
    print("Variant set configured successfully.")
    for r in results:
        tag = "deployed" if r["role"] == "deployed" else "created "
        print(f"  [{tag}] cost {str(r['cost']):>5}  TP={r['tp']}  "
              f"{r['gpu']} GPU/pod  {r['dep_name']}  (SO {r['so_name']})")
    print()
    print(f"All ScaledObjects share model-id={model_id!r}.")
    if created_count:
        print("WVA scales the most efficient variant first (highest capacity per")
        print("unit cost), spilling to the others once it saturates.")
    else:
        print("Single variant: WVA drives it between min and max replicas as")
        print("saturation rises and falls.")
    print()
    print("Verify:")
    print(f"  kubectl get scaledobject,hpa -n {ns}")
    print(f"  kubectl get pods -n {ns} "
          f"-l 'llm-d.ai/inferenceServing=true,llm-d.ai/model={model_hash}'")


if __name__ == "__main__":
    main()
