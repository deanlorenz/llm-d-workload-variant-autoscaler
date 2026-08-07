#!/usr/bin/env python3
"""Sync workload profiles from this repo into the llm-d-benchmark clone.

This repo is the source of truth for workload profiles; the llm-d-benchmark
clone is cache. A profile that exists only inside the clone makes a run
unreproducible from a fresh checkout, so this script both copies ours in and
refuses to proceed when the scenario names a profile that nothing but the clone's
working tree provides.

Two modes:

    sync_workloads.py --scenario PATH --print-harness
        Print the harness name the scenario declares. Exit 1 if the scenario
        does not declare one (or its stacks disagree), so a caller can fall
        back to its own default.

    sync_workloads.py --scenario PATH --workloads-dir DIR --repo-dir DIR
        Copy every <workloads-dir>/<harness>/*.yaml.in into
        <repo-dir>/workload/profiles/<harness>/, then assert the profile each
        stack names actually resolves there.

Only ``*.yaml.in`` templates are copied. ``llmdbenchmark``'s step_05 prefers a
plain ``<name>.yaml`` over ``<name>.yaml.in`` when both are present, so a stale
rendered sibling left by an earlier run would silently shadow an edited
template; any such untracked sibling is removed.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
from pathlib import Path

try:
    import yaml
except ImportError:  # pragma: no cover - reported, not crashed on
    yaml = None

# llmdbenchmark's own fallbacks (run/steps/step_05_render_profiles.py). Mirrored
# here only so messages can say what the harness would do, never to substitute
# for an explicit declaration.
UPSTREAM_DEFAULT_HARNESS = "inference-perf"
UPSTREAM_DEFAULT_PROFILE = "sanity_random.yaml"


def die(msg: str) -> None:
    print(f"ERROR: {msg}", file=sys.stderr)
    raise SystemExit(1)


def load_scenario(path: Path) -> dict:
    if yaml is None:
        die("PyYAML is not available to this interpreter; cannot read the scenario.")
    if not path.is_file():
        die(f"scenario not found: {path}")
    try:
        doc = yaml.safe_load(path.read_text())
    except yaml.YAMLError as exc:
        die(f"scenario is not valid YAML ({path}): {exc}")
    if not isinstance(doc, dict):
        die(f"scenario does not parse to a mapping: {path}")
    return doc


def stack_harnesses(doc: dict) -> list[dict]:
    """Resolve the effective `harness` block for each stack.

    `render_plans.py` deep-merges the scenario-wide `shared:` block into every
    stack, so a per-stack `harness:` overrides `shared.harness` key by key.
    """
    shared = (doc.get("shared") or {}).get("harness") or {}
    stacks = doc.get("scenario") or []
    if not isinstance(stacks, list) or not stacks:
        return [dict(shared)]
    resolved = []
    for stack in stacks:
        merged = dict(shared)
        if isinstance(stack, dict):
            merged.update(stack.get("harness") or {})
        resolved.append(merged)
    return resolved


def profile_of(harness: dict) -> str | None:
    """experimentProfile, then profile -- step_05's own fallback chain."""
    for key in ("experimentProfile", "profile"):
        value = harness.get(key)
        if value:
            return str(value)
    return None


def git_tracked(repo_dir: Path, path: Path) -> bool:
    """True if `path` is tracked in the clone's git index."""
    try:
        rel = path.relative_to(repo_dir)
    except ValueError:
        return False
    proc = subprocess.run(
        ["git", "-C", str(repo_dir), "ls-files", "--error-unmatch", str(rel)],
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.returncode == 0


def do_print_harness(doc: dict) -> None:
    names = {h.get("name") for h in stack_harnesses(doc) if h.get("name")}
    if len(names) != 1:
        # Undeclared, or a multi-harness scenario that a single -l cannot express.
        raise SystemExit(1)
    print(names.pop())


def sync(doc: dict, workloads_dir: Path, repo_dir: Path, cli_harness: str | None) -> None:
    harnesses = stack_harnesses(doc)
    declared = {h.get("name") for h in harnesses if h.get("name")}

    if cli_harness and declared and cli_harness not in declared:
        die(
            f"harness mismatch: the run will pass -l {cli_harness}, which overrides the "
            f"scenario's harness.name ({', '.join(sorted(declared))}).\n"
            f"       The scenario is where the harness belongs -- either drop the override "
            f"or fix harness.name."
        )

    # Which harness directories to sync: whatever the scenario declares, plus an
    # explicit override so `-l <other>` still gets its profiles.
    targets = set(declared)
    if cli_harness:
        targets.add(cli_harness)
    if not targets:
        targets.add(UPSTREAM_DEFAULT_HARNESS)

    synced: dict[str, set[str]] = {}
    for harness in sorted(targets):
        src = workloads_dir / harness
        dest = repo_dir / "workload" / "profiles" / harness
        synced[harness] = set()
        if not src.is_dir():
            continue
        templates = sorted(src.glob("*.yaml.in"))
        if not templates:
            continue
        dest.mkdir(parents=True, exist_ok=True)
        for template in templates:
            shutil.copy2(template, dest / template.name)
            synced[harness].add(template.name)
            print(f"Synced workload profile: {harness}/{template.name}")
            # step_05 prefers <name>.yaml over <name>.yaml.in; drop an untracked
            # rendered leftover so the template we just copied stays authoritative.
            stale = dest / template.name[: -len(".in")]
            if stale.exists():
                if git_tracked(repo_dir, stale):
                    print(
                        f"WARNING: {harness}/{stale.name} is tracked in the clone and "
                        f"will shadow {template.name} -- leaving it alone.",
                        file=sys.stderr,
                    )
                else:
                    stale.unlink()
                    print(f"  removed stale rendered sibling: {harness}/{stale.name}")

    # Every profile the scenario names must resolve to something reproducible.
    for harness in harnesses:
        # step_05's precedence: the -l flag overrides harness.name, which
        # overrides llmdbenchmark's own default.
        name = cli_harness or harness.get("name") or UPSTREAM_DEFAULT_HARNESS
        profile = profile_of(harness)
        if not profile:
            print(
                f"NOTE: no harness.experimentProfile declared; llmdbenchmark will fall "
                f"back to {UPSTREAM_DEFAULT_PROFILE}."
            )
            continue
        dest = repo_dir / "workload" / "profiles" / name
        candidates = [dest / profile, dest / f"{profile}.in"]
        ours = synced.get(name, set())
        if profile in ours or f"{profile}.in" in ours:
            continue
        found = next((c for c in candidates if c.is_file()), None)
        if found is None:
            die(
                f"harness.experimentProfile={profile} does not exist for harness "
                f"'{name}'.\n"
                f"       Add {profile}.in under {workloads_dir / name}/ -- this repo is "
                f"the source of truth for workload profiles."
            )
        if not git_tracked(repo_dir, found):
            die(
                f"harness.experimentProfile={profile} exists only as untracked cache in "
                f"the clone:\n"
                f"       {found}\n"
                f"       A run depending on it is not reproducible from a fresh checkout. "
                f"Move it to {workloads_dir / name}/{profile}.in."
            )
        print(f"Profile {name}/{profile}: provided by the llm-d-benchmark clone (tracked).")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenario", required=True, type=Path,
                    help="path to the scenario YAML in THIS repo")
    ap.add_argument("--print-harness", action="store_true",
                    help="print the harness the scenario declares, then exit")
    ap.add_argument("--workloads-dir", type=Path,
                    help="this repo's workload profile root (hack/benchmark/workloads)")
    ap.add_argument("--repo-dir", type=Path,
                    help="the llm-d-benchmark clone directory")
    ap.add_argument("--harness", default=None,
                    help="harness the run will pass via -l, for cross-checking")
    args = ap.parse_args()

    doc = load_scenario(args.scenario)

    if args.print_harness:
        do_print_harness(doc)
        return

    if not args.workloads_dir or not args.repo_dir:
        die("--workloads-dir and --repo-dir are required unless --print-harness is set.")
    if not args.repo_dir.is_dir():
        die(f"llm-d-benchmark clone not found: {args.repo_dir}")

    sync(doc, args.workloads_dir, args.repo_dir, args.harness or None)


if __name__ == "__main__":
    main()
