#!/usr/bin/env python3
"""
env_wizard.py — create a named benchmark env file, interactively.

Why this exists
---------------
A user arriving at a cluster with no env file for it should be helped to make
one, not handed a rule. The env file is the reproducible record of a run, so
getting one written correctly is the precondition for everything else -- and the
values that matter most (which controller image, which namespace) are exactly the
ones a newcomer has no way to guess.

What it produces
----------------
`hack/benchmark/<name>.env`, starting from `.env.sample`'s values as defaults,
with the live kube context recorded inside it as `KUBE_CONTEXT` so env_guard.py
can verify it later.

Design commitments
------------------
* **Everything explicit.** The file it writes is complete: reading it tells you
  what a run will do. No value is left to be supplied on a command line.
* **Never silently overwrite.** An existing env file is a record of runs that
  already happened.
* **Say what the dangerous steps imply.** The wizard is where a user is told, in
  plain terms, that cluster-level and namespace-level setup and llm-d standup
  change shared state -- before they are in a position to run them.
* **Read-only against the cluster.** It reads the context and available
  namespaces; it creates nothing.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

# Prompted in this order, with a one-line explanation each. Ordered so the
# identity of the run (where, what code) comes before its shape.
PROMPTS = (
    ("BENCHMARK_NAMESPACE", "Your namespace. Every action is scoped to it."),
    ("WVA_IMAGE_REPO", "Controller image repo (the code under test)."),
    ("WVA_IMAGE_TAG", "Controller image tag. This IS the experiment variable."),
    ("BENCHMARK_MODEL_ID", "Model to serve. Must be chat-template-bearing."),
    ("BENCHMARK_MODEL_SHORTNAME", "Short form used in resource names."),
    ("ACCELERATOR_NAME", "GPU model, must match your nodes."),
    ("VLLM_IMAGE_REPO", "vLLM image repo."),
    ("VLLM_IMAGE_TAG", "vLLM tag. Older images omit the KV-cache metric."),
    ("BENCHMARK_SPEC", "Scenario. Declares its own harness -- they are linked."),
    ("PROMETHEUS_URL", "Metrics source. Derived from the cluster; keep default."),
)

IMPLICATIONS = """
Before you use this file, know what the destructive targets do
-------------------------------------------------------------
These change shared state. On a shared cluster they affect other people, so they
are approve-by-default and never run as a side effect of anything else:

  * cluster-level setup  -- installs cluster-scoped objects (CRDs, SCCs,
                            APIServices). Rarely needed; can break other users'
                            workloads if it claims something already owned.
  * namespace-level setup -- shapes your namespace. Run once, deliberately.
  * llm-d standup         -- deploys the serving stack (gateway, EPP, model
                            servers). Consumes real GPUs.
  * teardown              -- destroys the above. Not reversible.

Only the WVA tests that run *on top* of a standing stack are automated.

Two things that have silently ruined runs, worth knowing now:

  * A PAUSED autoscaler produces a flat replica trace that reads exactly like a
    legitimate "no scaling needed" result.
  * The controller keeps in-memory capacity history between runs, so run 2 can be
    a function of run 1's load unless it is restarted first.
"""


def sample_defaults(sample: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    if not sample.is_file():
        return out
    for raw in sample.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        line = re.sub(r"^export\s+", "", line)
        k, _, v = line.partition("=")
        out[k.strip()] = v.split(" #", 1)[0].strip()
    return out


def current_context() -> str:
    proc = subprocess.run(["kubectl", "config", "current-context"],
                          capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else ""


def ask(label: str, why: str, default: str) -> str:
    print(f"\n{label}")
    print(f"  {why}")
    suffix = f" [{default}]" if default else " (required)"
    while True:
        try:
            val = input(f"  {label}{suffix}: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted; nothing written.", file=sys.stderr)
            sys.exit(1)
        val = val or default
        if val:
            return val
        print("  This value is required.")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--name", default="", help="env file name (X -> X.env)")
    ap.add_argument("--env-dir", default=None)
    args = ap.parse_args()

    env_dir = Path(args.env_dir) if args.env_dir else \
        Path(__file__).resolve().parent

    if not sys.stdin.isatty():
        print("env-wizard: needs a terminal (it asks questions and explains "
              "what the destructive steps imply). Run it interactively, or copy "
              f"{env_dir}/.env.sample to <name>.env by hand.", file=sys.stderr)
        return 1

    ctx = current_context()
    if not ctx:
        print("env-wizard: cannot read the current kube context. Log in and "
              "select a context first -- the env file records which cluster it "
              "is for, and that cannot be guessed.", file=sys.stderr)
        return 1

    print("=" * 72)
    print("Benchmark env wizard")
    print("=" * 72)
    print(f"\nCluster context (recorded in the file, verified on every run):\n"
          f"  {ctx}")

    name = args.name
    while not name:
        try:
            name = input("\nName for this env file (e.g. armA): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nAborted; nothing written.", file=sys.stderr)
            return 1
    if not re.fullmatch(r"[A-Za-z0-9._-]+", name):
        print(f"env-wizard: {name!r} is not a usable file name.",
              file=sys.stderr)
        return 1

    out_path = env_dir / f"{name}.env"
    if out_path.exists():
        # An existing env file is the record of runs that already happened.
        print(f"\nenv-wizard: {out_path} already exists. Refusing to overwrite "
              f"it -- it is the record of whatever has already run under that "
              f"name. Edit it directly, or choose another name.",
              file=sys.stderr)
        return 1

    defaults = sample_defaults(env_dir / ".env.sample")
    print("\nDefaults come from .env.sample. Press Enter to accept each one.")

    values: dict[str, str] = {}
    for key, why in PROMPTS:
        values[key] = ask(key, why, defaults.get(key, ""))

    # Carry through every remaining sample key so the file is complete: a value
    # the user was not asked about must still be recorded, or the file is not a
    # full description of the run.
    carried = {k: v for k, v in defaults.items()
               if k not in values and k != "KUBE_CONTEXT"}

    lines = [
        f"# {name} — benchmark env, created by env_wizard.py",
        "#",
        "# This file is the reproducible record of what a run used. Everything a",
        "# run depends on is stated here; nothing is left to a command-line",
        "# override. If you do override something, env-guard reports it loudly and",
        "# this file stops being a complete record.",
        "",
        "# Cluster this file is for. A run refuses to start if the live context is",
        "# not this one -- that is what stops a stale context from writing into the",
        "# wrong cluster.",
        f"KUBE_CONTEXT={ctx}",
        "",
        "# ── Answered in the wizard ────────────────────────────────────────────",
    ]
    lines += [f"{k}={values[k]}" for k, _ in PROMPTS]
    if carried:
        lines += [
            "",
            "# ── Carried from .env.sample (not prompted; edit if needed) ───────────",
        ]
        lines += [f"{k}={v}" for k, v in sorted(carried.items())]
    lines.append("")

    out_path.write_text("\n".join(lines))
    print(f"\nWrote {out_path}")
    print(IMPLICATIONS)
    print(f"Use it with:  make <target> BENCHMARK_ENV={name}")
    print(f"Review it first:  {out_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
