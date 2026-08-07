#!/usr/bin/env python3
"""Per-cycle TA/SAT decision timeline from a captured WVA controller log.

Companion to replica_timeline.py, which recovers only the OBSERVED replica count.
This one lines up, for each 60 s control cycle, the two analyzers' internal view
(demand, per-replica capacity, utilisation, replica claim) against the decision the
engine actually emitted -- because on the 2026-08-07 ladder run the emitted decision
and the actual replica count diverged, and conflating them produces wrong conclusions:

    emitted decision                      = 2
    actual replicas (HPA stabilisation)   = 3

DO NOT model the emitted decision as ceil(demand/prc). That formula is wrong; it was
used in early analysis of this run and produced two bogus findings (a phantom third
"internal target" level, and a phantom one-step-per-cycle limit). The engine computes a
DELTA against the watermark-relative capacity gap:

    rc = demand/0.85 - supply    if rc > 0:  tgt = curr + ceil (rc/prc)
    sc = supply - demand/0.70    if sc > 0:  tgt = curr - floor(sc/prc)
                                 else:       tgt = curr             (hold)
    combined: max over analyzers, clamped to [minReplicas, maxReplicas]

See verify_decision_rule.py, which reproduces every cycle of the run under this rule.
Note the emitted change is NOT bounded to one replica: 4 -> 1 was emitted at 21:18:40.

`prc` is still the number to watch. It is TA's estimate of one replica's token capacity,
derived from observed throughput and unsmoothed, so at load onset -- before any replica
has demonstrated its capacity -- it reads several times too low and the fleet
overprovisions.

Usage:
    python3 decision_timeline.py [logfile] [--csv]

Reads session-notes/scratch/ladder-controller.log by default. `kubectl logs
--timestamps` prefixes its own RFC3339 stamp, so the zap timestamp is the second
field; a plain `kubectl logs` leaves it first. Both are accepted -- anchoring to the
double-stamp form silently yields zero rows on hand-captured logs, which is exactly
the bug that made the Arm A timeline look empty.
"""
import json
import re
import sys

TS = re.compile(r"^(?:\S+\s+)?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")
PAYLOAD = re.compile(r'\{"modelID".*\}\s*$')


def parse(path):
    cycles = {}
    for line in open(path, errors="replace"):
        mts = TS.match(line)
        mpl = PAYLOAD.search(line)
        if not (mts and mpl):
            continue
        try:
            d = json.loads(mpl.group(0))
        except json.JSONDecodeError:
            continue
        cyc = cycles.setdefault(mts.group(1), {})
        if "analyzer" in d:
            variant = (d.get("variants") or [{}])[0]
            cyc[d["analyzer"]] = {
                "demand": d.get("demand"),
                "prc": variant.get("prc"),
                "util": d.get("util"),
                "rc": d.get("rc"),
                "reason": variant.get("reason"),
            }
        elif "decisions" in d and d["decisions"]:
            dec = d["decisions"][0]
            cyc["dec"] = (dec["curr"], dec["tgt"], dec["action"])
    return cycles


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    path = args[0] if args else "session-notes/scratch/ladder-controller.log"
    as_csv = "--csv" in sys.argv
    cycles = parse(path)

    # Cycles before the first traffic carry no prc at all (TA emits nothing until
    # there is throughput to measure); they are pure idle and only pad the table.
    active = {t: c for t, c in cycles.items() if (c.get("throughput") or {}).get("prc")}
    if not active:
        print(f"no cycles with a throughput prc found in {path}", file=sys.stderr)
        return 1

    if as_csv:
        print("time,ta_prc,ta_demand,ta_util,ta_rc,sat_util,sat_demand,curr,tgt,action")
    else:
        print(f"{'time':<9} {'TA prc':>9} {'TA dem':>8} {'TA util':>8} {'TA rc':>7} "
              f"{'SAT util':>9} | decision")

    prev_prc = None
    for ts in sorted(active):
        c = active[ts]
        ta = c.get("throughput") or {}
        sat = c.get("saturation") or {}
        dec = c.get("dec")
        prc = ta.get("prc")
        curr, tgt, action = dec if dec else ("", "", "")

        if as_csv:
            print(f"{ts},{prc},{ta.get('demand')},{ta.get('util')},{ta.get('rc')},"
                  f"{sat.get('util')},{sat.get('demand')},{curr},{tgt},{action}")
            continue

        # Flag the cycle-over-cycle prc ratio: this is the estimator noise that the
        # replica target inherits, and it is the headline measurement of the run.
        jump = ""
        if prev_prc:
            r = prc / prev_prc
            if r >= 1.5 or r <= 1 / 1.5:
                jump = f"  prc x{r:.2f}"
        prev_prc = prc
        mark = "  <<<" if action and action != "no-change" else ""
        print(f"{ts[11:]:<9} {prc:>9.1f} {ta.get('demand', 0):>8.0f} "
              f"{ta.get('util', 0):>8.3f} {ta.get('rc', 0):>7.0f} "
              f"{sat.get('util', 0):>9.4f} | {curr}->{tgt} {action}{mark}{jump}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
