#!/usr/bin/env python3
"""
env_guard.py — assert that a benchmark run is reproducible from a named env file.

Why this exists
---------------
A benchmark result is only usable as data if you can say what produced it. Three
things previously made that impossible to guarantee:

  * `make VAR=...` overrides won over `hack/benchmark/.env`, so reading the env
    file did not tell you what ran.
  * `BENCHMARK_NAMESPACE ?=` meant an unset namespace became the empty string
    rather than an error.
  * Nothing checked that the current kube context was the cluster the configured
    namespace lives on. On a shared cluster, a stale context plus a
    valid-looking env file is a write into the wrong cluster.

What this guards -- and what it deliberately does not
----------------------------------------------------
This runs before the **destructive** operations only: cluster-level and
NS-level setup, llm-d standup, teardown, anything that mutates the running stack
(image apply, analyzer change, controller restart, per-run reset), and starting a
run (it consumes real GPUs on a shared cluster).

It is NOT wired into read-only or local-only targets -- `benchmark-preflight`
(itself a gate), `benchmark-record-images`, `benchmark-show-analyzers`,
`benchmark-report`, `benchmark-analyze`, `benchmark-plot-*`, `benchmark-install`.
Gating those would add friction with nothing to protect: they cannot change the
cluster, so a wrong env file cannot do damage through them.

The contract this enforces
--------------------------
The env file is the reproducible record. Overrides remain possible -- this is a
Makefile and a determined user can always bypass it -- but an override is never
silent: it is reported, loudly, so it appears in the run's console log next to
the results it produced.

Named env files, not context-named files
----------------------------------------
Selection is `BENCHMARK_ENV=<name>` -> `hack/benchmark/<name>.env`. The name
describes the campaign (`armA`, `pr2-ab`), and the kube context is declared
*inside* the file as `KUBE_CONTEXT`, then verified against the live one. A
filename cannot be verified; a declared value can. This also lets several env
files target one context (two arms of an A/B) without contorting their names.

Refusal vs complaint
--------------------
Refusals are the checks where proceeding could touch the wrong cluster or
produce unattributable data: no env file, no declared context, context mismatch,
missing required keys. Everything else complains and proceeds.

UNSAFE has levels, because "bypass the guard" is not one decision
----------------------------------------------------------------
  UNSAFE=confirm  (or `true`)  ask per bypassed guard, interactively
  UNSAFE=once                  ask once, covering every bypassed guard
  UNSAFE=silent                bypass with no prompt; still logged

`confirm` is the default meaning of a bare `UNSAFE=true`: if a user is
overriding a safety check on a shared cluster, the safe default is to make them
look at each one. `silent` exists for automation, where no one is watching a
prompt -- it is the most dangerous setting and says so.

Every level logs what it bypassed. The difference is only how much friction
precedes it, never whether it is recorded.

Read-only: this script never writes to the cluster or to the env file.
"""
import argparse
import os
import re
import subprocess
import sys
from pathlib import Path

# UNSAFE levels, least to most dangerous.
UNSAFE_LEVELS = ("confirm", "once", "silent")

# Keys that must be present for a run to be attributable after the fact. A run
# missing any of these produces results nobody can reconstruct.
REQUIRED_KEYS = (
    "KUBE_CONTEXT",
    "BENCHMARK_NAMESPACE",
    "WVA_IMAGE_REPO",
    "WVA_IMAGE_TAG",
    "VLLM_IMAGE_REPO",
    "VLLM_IMAGE_TAG",
    "ACCELERATOR_NAME",
    "BENCHMARK_MODEL_ID",
)

# The scenario declares its own harness (see the Makefile note on
# BENCHMARK_HARNESS: it "belongs to the spec of a run, not to this Makefile").
# They therefore travel together -- overriding one without the other is the
# inconsistent state worth catching.
LINKED_PAIRS = (("BENCHMARK_SPEC", "BENCHMARK_HARNESS"),)

# Derived rather than configured: the collection target is a property of the
# cluster, not a preference. A wrong value yields plausible numbers from the
# wrong place, which is worse than an error.
THANOS_URL = (
    "https://thanos-querier.openshift-monitoring.svc.cluster.local:9091"
)


class Findings:
    """Collects refusals and complaints so all are reported in one pass.

    Reporting every problem at once matters here: these checks run before a
    cluster run, and discovering missing keys one per invocation wastes the
    operator's time.
    """

    def __init__(self, unsafe: str | None, interactive: bool = True):
        self.unsafe = unsafe          # None, or one of UNSAFE_LEVELS
        self.interactive = interactive
        self.refusals: list[str] = []
        self.complaints: list[str] = []

    def refuse(self, msg: str) -> None:
        self.refusals.append(msg)

    def complain(self, msg: str) -> None:
        self.complaints.append(msg)

    def _ask(self, prompt: str) -> bool:
        """Prompt, treating anything other than an explicit yes as no.

        A non-tty (CI, a pipe) cannot answer, so it declines rather than
        proceeding on a default -- silence must not read as consent when the
        subject is bypassing a safety check.
        """
        if not self.interactive or not sys.stdin.isatty():
            print("  (not a terminal -- cannot confirm; treating as NO)",
                  file=sys.stderr)
            return False
        try:
            answer = input(f"{prompt} [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return False
        return answer in ("y", "yes")

    def _how_to_override(self) -> None:
        """Always tell the user the way forward, not just that they are blocked."""
        print(
            "\n  To proceed anyway, pick how much confirmation you want:\n"
            "    UNSAFE=confirm   ask me about each bypassed guard (safest)\n"
            "    UNSAFE=once      ask me once, for all of them\n"
            "    UNSAFE=silent    no prompt at all (for automation; riskiest)\n"
            "  e.g.  make <target> BENCHMARK_ENV=<name> UNSAFE=confirm\n"
            "  Prefer fixing the env file where you can -- an override means the\n"
            "  env file no longer records what actually ran.",
            file=sys.stderr,
        )

    def report(self) -> int:
        for c in self.complaints:
            print(f"  [override] {c}", file=sys.stderr)
        if not self.refusals:
            if self.complaints:
                print(
                    f"env-guard: {len(self.complaints)} override(s) in effect -- "
                    f"the env file is NOT a complete record of this run.",
                    file=sys.stderr,
                )
            return 0

        for r in self.refusals:
            print(f"  [REFUSE] {r}", file=sys.stderr)

        n = len(self.refusals)
        if self.unsafe is None:
            print(f"env-guard: refusing to proceed ({n} guard(s) failed).",
                  file=sys.stderr)
            self._how_to_override()
            return 1

        if self.unsafe == "silent":
            print(f"env-guard: UNSAFE=silent -- {n} guard(s) BYPASSED with no "
                  f"confirmation. You own the consequences.", file=sys.stderr)
            return 0

        if self.unsafe == "once":
            print(f"\nenv-guard: UNSAFE=once -- about to bypass {n} guard(s) "
                  f"listed above.", file=sys.stderr)
            if not self._ask("Bypass all of them and proceed?"):
                print("env-guard: declined; nothing was done.", file=sys.stderr)
                return 1
            print(f"env-guard: {n} guard(s) BYPASSED by confirmation.",
                  file=sys.stderr)
            return 0

        # confirm: one prompt per guard, so each is considered on its own.
        print(f"\nenv-guard: UNSAFE=confirm -- confirming {n} guard(s) "
              f"individually.", file=sys.stderr)
        for i, r in enumerate(self.refusals, 1):
            first = r.splitlines()[0]
            if not self._ask(f"  ({i}/{n}) Bypass: {first}"):
                print("env-guard: declined; nothing was done.", file=sys.stderr)
                return 1
        print(f"env-guard: {n} guard(s) BYPASSED by confirmation.",
              file=sys.stderr)
        return 0


def parse_env_file(path: Path) -> dict[str, str]:
    """Parse a shell-style KEY=VALUE env file.

    Deliberately simple: this must agree with how `make -include` reads the same
    file, so it handles comments, blank lines, optional `export`, and quotes --
    and nothing else. Anything fancier would let the two readers disagree, which
    is the exact class of bug this script exists to prevent.
    """
    out: dict[str, str] = {}
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        line = re.sub(r"^export\s+", "", line)
        if "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.split(" #", 1)[0].strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "\"'":
            val = val[1:-1]
        out[key] = val
    return out


def current_context() -> str | None:
    proc = subprocess.run(
        ["kubectl", "config", "current-context"],
        capture_output=True, text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else None


def check_prometheus(env: dict[str, str], effective: dict[str, str],
                     f: Findings) -> None:
    """Verify the collection target rather than merely defaulting it.

    An override is allowed, but it is checked for correctness: a wrong
    collection target produces plausible-looking numbers read from the wrong
    place, and that failure is invisible in the results.
    """
    configured = effective.get("PROMETHEUS_URL", "").strip()
    if not configured:
        f.complain(
            f"PROMETHEUS_URL unset; derived from cluster -> {THANOS_URL}"
        )
        return
    if configured == THANOS_URL:
        return

    f.complain(
        f"PROMETHEUS_URL overrides the cluster-derived value.\n"
        f"      configured: {configured}\n"
        f"      derived:    {THANOS_URL}"
    )
    # Correctness check, not just a warning: confirm the host it points at is a
    # service that actually exists.
    m = re.match(r"https?://([^:/]+)", configured)
    if not m:
        f.complain(f"PROMETHEUS_URL is not a parseable URL: {configured}")
        return
    host = m.group(1)
    svc = host.split(".")[0]
    ns = host.split(".")[1] if "." in host and len(host.split(".")) > 1 else ""
    if not ns:
        f.complain(
            f"PROMETHEUS_URL host {host!r} is not a cluster-internal service "
            f"name; cannot verify it resolves."
        )
        return
    proc = subprocess.run(
        ["kubectl", "get", "svc", "-n", ns, svc, "-o", "name"],
        capture_output=True, text=True,
    )
    if proc.returncode != 0:
        f.complain(
            f"PROMETHEUS_URL points at service {svc!r} in namespace {ns!r}, "
            f"which does not exist in this cluster. Metrics collection will "
            f"silently return nothing."
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--env-name", default=os.environ.get("BENCHMARK_ENV", ""),
                    help="name X selecting hack/benchmark/X.env")
    ap.add_argument("--env-dir", default=None,
                    help="directory holding the named env files")
    ap.add_argument("--unsafe", default=os.environ.get("UNSAFE", ""),
                    help="confirm | once | silent (true == confirm)")
    ap.add_argument("--no-input", action="store_true",
                    help="never prompt; a guard needing confirmation fails")
    ap.add_argument("--effective", default="",
                    help="KEY=VALUE pairs make will actually use, "
                         "comma-separated; used to detect overrides")
    ap.add_argument("--skip-context-check", action="store_true",
                    help="skip the live-context comparison (offline use)")
    args = ap.parse_args()

    # Normalize the UNSAFE level. A bare `true` means `confirm`: if someone is
    # overriding a safety check, the safe default is to make them look at each
    # one rather than to wave them all through.
    unsafe_raw = (args.unsafe or "").strip().lower()
    if unsafe_raw in ("", "false", "0", "no"):
        unsafe = None
    elif unsafe_raw in ("true", "1", "yes", "confirm"):
        unsafe = "confirm"
    elif unsafe_raw in UNSAFE_LEVELS:
        unsafe = unsafe_raw
    else:
        print(f"env-guard: UNSAFE={args.unsafe!r} is not a known level. "
              f"Use one of: {', '.join(UNSAFE_LEVELS)} (or true == confirm).",
              file=sys.stderr)
        return 1

    f = Findings(unsafe=unsafe, interactive=not args.no_input)

    env_dir = Path(args.env_dir) if args.env_dir else \
        Path(__file__).resolve().parent

    def available() -> list[str]:
        """Named env files only.

        `.env` is the legacy unnamed file and `.env.sample` is a template;
        neither is selectable by name. Note `Path(".env").stem` is `".env"`, not
        the empty string, so these must be excluded explicitly rather than by
        truthiness.
        """
        return sorted(
            p.stem for p in env_dir.glob("*.env")
            if p.name not in (".env", ".env.sample")
        )

    def offer_wizard(reason: str) -> int:
        """No usable env file: offer to create one rather than just refusing.

        A missing env file is the one guard failure where the fix is mechanical,
        so the useful response is to run the wizard, not to print a rule. The
        wizard is interactive by design -- it is where the user is told what the
        destructive steps imply -- so a non-tty declines instead of guessing.
        """
        print(f"env-guard: {reason}", file=sys.stderr)
        found = available()
        if found:
            print("  Existing env files: " + ", ".join(found), file=sys.stderr)
        print(
            "  A run must name the env file that records it, so the result can "
            "be reproduced:\n"
            "    make <target> BENCHMARK_ENV=<name>"
            "   # -> hack/benchmark/<name>.env",
            file=sys.stderr,
        )
        wizard = Path(__file__).resolve().parent / "env_wizard.py"
        if not wizard.is_file():
            print(f"  To create one: cp {env_dir}/.env.sample "
                  f"{env_dir}/<name>.env and edit it.", file=sys.stderr)
            return 1
        print("\n  No env file for this context yet? The wizard can create one:"
              "\n    make benchmark-init BENCHMARK_ENV=<name>", file=sys.stderr)
        if args.no_input or not sys.stdin.isatty():
            return 1
        try:
            answer = input("  Run the wizard now? [y/N] ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print(file=sys.stderr)
            return 1
        if answer not in ("y", "yes"):
            return 1
        cmd = [sys.executable, str(wizard), "--env-dir", str(env_dir)]
        if args.env_name:
            cmd += ["--name", args.env_name]
        return subprocess.run(cmd).returncode or 1

    if not args.env_name:
        return offer_wizard("BENCHMARK_ENV is not set.")

    env_path = env_dir / f"{args.env_name}.env"
    if not env_path.is_file():
        return offer_wizard(f"{env_path} does not exist.")

    env = parse_env_file(env_path)

    effective = dict(env)
    for pair in args.effective.split(","):
        if "=" in pair:
            k, _, v = pair.partition("=")
            effective[k.strip()] = v.strip()

    print(f"env-guard: {env_path.name} "
          f"(namespace {env.get('BENCHMARK_NAMESPACE', '?')})",
          file=sys.stderr)

    missing = [k for k in REQUIRED_KEYS if not env.get(k, "").strip()]
    if missing:
        f.refuse(
            "env file is missing required key(s): " + ", ".join(missing) +
            "\n      Without these a run cannot be attributed after the fact."
        )

    declared = env.get("KUBE_CONTEXT", "").strip()
    if declared and not args.skip_context_check:
        live = current_context()
        if live is None:
            f.refuse("cannot read the current kube context (is kubectl "
                     "configured?)")
        elif live != declared:
            f.refuse(
                f"kube context mismatch -- this env file is for a different "
                f"cluster.\n"
                f"      env file declares: {declared}\n"
                f"      current context:   {live}\n"
                f"      Switch context, or select the env file for this one."
            )

    # Overrides: report, do not block. The env file stops being a complete
    # record the moment one is in effect, which is the thing worth saying out
    # loud rather than the thing worth preventing.
    #
    # Only keys the file actually sets can be "overridden". A key the file omits
    # is being *derived* -- BENCHMARK_HARNESS, for instance, is read from the
    # scenario yaml when unset, because the scenario is authoritative for it.
    # Treating a derived default as an override would cry wolf on every run.
    def overridden(key: str) -> bool:
        return key in env and effective.get(key, env[key]) != env[key]

    for key in sorted(env):
        if overridden(key):
            f.complain(
                f"{key} overridden on the command line.\n"
                f"      env file: {env[key] or '(empty)'}\n"
                f"      in use:   {effective.get(key) or '(empty)'}"
            )

    for a, b in LINKED_PAIRS:
        a_over = overridden(a)
        b_over = overridden(b)
        if a_over != b_over:
            overridden, other = (a, b) if a_over else (b, a)
            f.complain(
                f"{overridden} was overridden but {other} was not. These are "
                f"linked -- the scenario declares its own harness, so changing "
                f"one without the other can run a scenario under a harness it "
                f"did not specify. Prefer a separate env file."
            )

    check_prometheus(env, effective, f)

    rc = f.report()
    # Only claim a clean bill of health when there is one. A bypassed guard
    # (UNSAFE) still returns 0, so returncode alone must not be read as "clean".
    if rc == 0 and not f.complaints and not f.refusals:
        print("env-guard: OK -- run is fully described by the env file.",
              file=sys.stderr)
    return rc


if __name__ == "__main__":
    sys.exit(main())
