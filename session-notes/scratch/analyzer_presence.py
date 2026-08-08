#!/usr/bin/env python3
"""Per-cycle census of which analyzers spoke, and whether each was decision-capable.

Answers a narrow question Dean asked of the 2026-08-07 ladder run: were BOTH the
saturation and throughput analyzers actually enabled and actually logging scaling
decisions, or did one of them ride along silently?

"Logged a payload" is weaker than "was decision-capable". An analyzer that emits a
payload with no `prc` cannot produce a replica claim, so it cannot influence the
max-over-analyzers combine even though it is plainly enabled and running. This
distinguishes the two, and splits the run into the load window and the idle tail,
because a silent analyzer at idle means something different from a silent one under
load.

What this tool does NOT establish is the CONFIGURED set -- it observes behaviour, and an
analyzer could in principle be running for a reason other than being asked for. That half
comes from the controller's own startup gate, which is a single grep and worth pairing with
every run of this tool:

    grep "ThroughputAnalyzer" <logfile>

`cmd/main.go:throughputAnalyzerEnabled` registers the throughput analyzer only if a
saturation-config entry names it with `enabled != false`, and it logs one of two distinct
messages -- "ThroughputAnalyzer registered (enabled in saturation config)" or
"ThroughputAnalyzer NOT registered -- no saturation config entry enables 'throughput'".
Seeing the positive line is a positive identification rather than an absence of evidence, so
check that the negative one is absent too. Saturation needs no such line: it is intrinsic to
saturation.NewEngine and exempt from the gate, so a running engine is a running saturation
analyzer.

Usage:  python3 analyzer_presence.py [logfile]
"""
import json
import re
import sys

TS = re.compile(r"^(?:\S+\s+)?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
PAYLOAD = re.compile(r'\{"modelID".*\}\s*$')

# The load window, from the gateway trace (envoy_per_request.py): first arrival to last.
LOAD_LO, LOAD_HI = "20:41:44", "21:22:46"

NAMES = ("saturation", "throughput")


def parse(path, collect_all=False):
    """ts -> {analyzer: {"prc": float|None, "variants": int}, "dec": (curr, tgt, action)}

    An analyzer can emit MORE THAN ONE payload inside the same one-second timestamp: the
    throughput analyzer does so in 21 of this run's cycles. Keying by (ts, analyzer) and
    assigning therefore silently keeps whichever arrived last, which is how a census can
    look clean and be wrong. With collect_all, every payload is retained under
    ``all[(ts, analyzer)]`` so the duplicates can be compared rather than assumed benign.
    """
    cycles, dupes = {}, {}
    for line in open(path, errors="replace"):
        mts, mpl = TS.match(line), PAYLOAD.search(line)
        if not (mts and mpl):
            continue
        try:
            d = json.loads(mpl.group(0))
        except json.JSONDecodeError:
            continue
        ts = mts.group(1)
        cyc = cycles.setdefault(ts, {})
        if "analyzer" in d:
            vs = d.get("variants") or []
            rec = {
                "prc": (vs[0].get("prc") if vs else None),
                "variants": len(vs),
                "util": d.get("util"),
            }
            if collect_all:
                dupes.setdefault((ts, d["analyzer"]), []).append(rec)
            # Prefer a decision-capable payload over a prc-less one, rather than letting
            # arrival order decide. Without this, a variants:[] payload can mask a real one.
            prev = cyc.get(d["analyzer"])
            if not (prev and prev["prc"] and not rec["prc"]):
                cyc[d["analyzer"]] = rec
        elif "decisions" in d and d["decisions"]:
            x = d["decisions"][0]
            cyc["dec"] = (x["curr"], x["tgt"], x["action"])
    return (cycles, dupes) if collect_all else cycles


def audit_dupes(dupes):
    """Report cycles where one analyzer emitted several payloads, and whether they agree."""
    multi = {k: v for k, v in dupes.items() if len(v) > 1}
    print(f"\n{len(multi)} (cycle, analyzer) pairs emitted more than one payload")
    if not multi:
        return
    shapes = {}
    for (ts, name), recs in sorted(multi.items()):
        sig = (name, len(recs),
               tuple(r["variants"] for r in recs),
               tuple(r["prc"] is not None for r in recs))
        shapes.setdefault(sig, []).append(ts[11:])
    print(f"  {'analyzer':<12} {'n':>2} {'variants':<12} {'has prc':<14} "
          f"{'cycles':>6}  first -> last")
    for (name, n, vs, has), times in sorted(shapes.items()):
        print(f"  {name:<12} {n:>2} {str(vs):<12} {str(has):<14} "
              f"{len(times):>6}  {times[0]} -> {times[-1]}")
    print("  A (0,) variants payload alongside a real one is the known idle-TA behaviour:\n"
          "  with no traffic there is no throughput observation to build a prc from.")


def main():
    argv = [a for a in sys.argv[1:] if not a.startswith("-")]
    path = argv[0] if argv else "session-notes/scratch/ladder-controller.log"
    cycles, dupes = parse(path, collect_all=True)

    tally = {}
    for ts in sorted(cycles):
        c = cycles[ts]
        hhmmss = ts[11:]
        window = "load" if LOAD_LO <= hhmmss <= LOAD_HI else "idle"
        key = (window,
               tuple(n for n in NAMES if n in c),
               tuple(n for n in NAMES if (c.get(n) or {}).get("prc")),
               bool(c.get("dec")))
        tally.setdefault(key, []).append(hhmmss)

    print(f"{len(cycles)} cycles in {path}\n")
    print(f"{'window':<6} {'payload from':<24} {'prc from':<24} {'dec':>4} "
          f"{'n':>4}  first -> last")
    for (window, spoke, capable, dec), times in sorted(tally.items()):
        print(f"{window:<6} {'+'.join(spoke) or '-':<24} "
              f"{'+'.join(capable) or '-':<24} {'yes' if dec else 'no':>4} "
              f"{len(times):>4}  {times[0]} -> {times[-1]}")

    # Totals, so "both were enabled" is a count and not an impression.
    print()
    for n in NAMES:
        spoke = [t for t in cycles if n in cycles[t]]
        capable = [t for t in spoke if (cycles[t][n] or {}).get("prc")]
        load = [t for t in capable if LOAD_LO <= t[11:] <= LOAD_HI]
        print(f"  {n:<12} payloads {len(spoke):>4}   with prc {len(capable):>4}   "
              f"of those in load window {len(load):>4}")
    both = [t for t in cycles
            if all((cycles[t].get(n) or {}).get("prc") for n in NAMES)]
    print(f"  {'BOTH':<12} decision-capable in the same cycle {len(both):>4}")
    audit_dupes(dupes)
    return 0


if __name__ == "__main__":
    sys.exit(main())
