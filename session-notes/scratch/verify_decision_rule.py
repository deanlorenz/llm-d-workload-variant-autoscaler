#!/usr/bin/env python3
"""Reconstruct the emitted scaling decision from the analyzer payloads, and check it.

Purpose: the 2026-08-07 ladder run emitted tgt=1 at 20:51:37 where TA's own
ceil(demand/prc) = 2. Rather than infer the combine logic from a source tree that is
NOT the commit the deployed image was built from, this derives a candidate rule and
tests it against every cycle in the captured log. A rule that reproduces all cycles
is evidence; a rule that reproduces most is a wrong rule with a lucky streak.

Candidate rule (per analyzer, then combined):

    up:    tgt_a = curr + ceil (rc_a / prc_a)      # rc = demand/scaleUpThreshold - supply
    down:  tgt_a = curr - floor(sc_a / prc_a)      # sc = supply - demand/scaleDownBoundary
    tgt    = max over analyzers, clamped to [minReplicas, maxReplicas]

max-over-analyzers is the conservative combine: any analyzer that wants MORE replicas
wins, and an analyzer that wants fewer cannot drag the fleet below one that does not.

Note `supply` is NOT always curr*prc -- the analyzer's replica basis can lag the
observed replica count by a cycle (at 20:51:37 the basis was 3 while curr was 2).
The rule is expressed in terms of the DELTA (rc/sc are already relative to supply),
applied to curr, which is what makes it basis-independent.

Usage:  python3 verify_decision_rule.py [logfile] [--minr N] [--maxr N] [-v]
"""
import json
import math
import re
import sys

TS = re.compile(r"^(?:\S+\s+)?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
PAYLOAD = re.compile(r'\{"modelID".*\}\s*$')


def parse(path):
    cycles = {}
    for line in open(path, errors="replace"):
        mts, mpl = TS.match(line), PAYLOAD.search(line)
        if not (mts and mpl):
            continue
        try:
            d = json.loads(mpl.group(0))
        except json.JSONDecodeError:
            continue
        cyc = cycles.setdefault(mts.group(1), {})
        if "analyzer" in d:
            v = (d.get("variants") or [{}])[0]
            cyc[d["analyzer"]] = {
                "supply": d.get("supply"), "demand": d.get("demand"),
                "util": d.get("util"), "rc": d.get("rc"), "sc": d.get("sc"),
                "prc": v.get("prc"), "reason": v.get("reason"),
            }
        elif "decisions" in d and d["decisions"]:
            x = d["decisions"][0]
            cyc["dec"] = (x["curr"], x["tgt"], x["action"])
    return cycles


def claim(a, curr):
    """Replica target this analyzer's rc/sc implies, relative to curr."""
    prc, rc, sc = a.get("prc"), a.get("rc") or 0.0, a.get("sc") or 0.0
    if not prc:
        return None, ""
    if rc > 0:
        n = math.ceil(rc / prc)
        return curr + n, f"+ceil({rc:.0f}/{prc:.0f})=+{n}"
    if sc > 0:
        n = math.floor(sc / prc)
        return curr - n, f"-floor({sc:.0f}/{prc:.0f})=-{n}"
    return curr, "hold"


def main():
    argv = sys.argv[1:]
    pos = [a for a in argv if not a.startswith("-")]
    path = pos[0] if pos else "session-notes/scratch/ladder-controller.log"

    def opt(name, default):
        return int(argv[argv.index(name) + 1]) if name in argv else default

    minr, maxr = opt("--minr", 1), opt("--maxr", 10)
    verbose = "-v" in argv

    cycles = parse(path)
    ok = bad = skip = 0
    print(f"{'time':<9} {'curr':>4} {'TA':>12} {'SAT':>12} {'pred':>5} {'obs':>4}  verdict")
    for ts in sorted(cycles):
        c = cycles[ts]
        if not c.get("dec"):
            continue
        curr, tgt, _ = c["dec"]
        ta, sat = c.get("throughput") or {}, c.get("saturation") or {}
        if not (ta.get("prc") and sat.get("prc")):
            skip += 1
            continue
        t_ta, e_ta = claim(ta, curr)
        t_sat, e_sat = claim(sat, curr)
        pred = max(x for x in (t_ta, t_sat) if x is not None)
        pred = max(minr, min(maxr, pred))
        good = pred == tgt
        ok, bad = ok + good, bad + (not good)
        if verbose or not good:
            print(f"{ts[11:]:<9} {curr:>4} {e_ta:>12} {e_sat:>12} "
                  f"{pred:>5} {tgt:>4}  {'ok' if good else 'MISMATCH'}")
    print(f"\nmatched {ok}, mismatched {bad}, skipped {skip} "
          f"(cycles lacking a prc from both analyzers)")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
