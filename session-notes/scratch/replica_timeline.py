"""Observed-replica timeline from a WVA controller log.

The reports only expose ready-replica counts as run-wide aggregates, so they
cannot say WHEN a replica became ready -- and that is the quantity that decides
whether an early scale-up actually bought any serving capacity before the load
step. The controller logs `curr` (observed replicas) every reconcile, so the
timeline is recoverable from the log even though the reports lost it.

Prints one row per change in (curr, tgt), plus dwell time at each curr value.

Usage:
  python3 replica_timeline.py <controller.log> [load_start_utc] [load_end_utc]
"""

import re
import sys
from datetime import datetime, timezone

DEC = re.compile(r'"curr":(\d+),"tgt":(\d+),"action":"([^"]+)"')
# Two capture formats in play: `kubectl logs --timestamps` prefixes an RFC3339
# stamp of its own, so the zap timestamp is the SECOND field; a plain
# `kubectl logs` leaves it first. Match either -- anchoring to the prefix
# silently yields zero rows on hand-captured logs.
TS = re.compile(r"^(?:\S+\s+)?(\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2})")


def parse(path):
    rows = []
    for line in open(path):
        if "scaling-decision" not in line:
            continue
        mt, md = TS.match(line), DEC.search(line)
        if not (mt and md):
            continue
        t = datetime.strptime(mt.group(1), "%Y-%m-%dT%H:%M:%S").replace(tzinfo=timezone.utc)
        rows.append((t, int(md.group(1)), int(md.group(2)), md.group(3)))
    return rows


def main():
    rows = parse(sys.argv[1])
    if not rows:
        return "no scaling-decision lines found"
    lo = sys.argv[2] if len(sys.argv) > 2 else None
    hi = sys.argv[3] if len(sys.argv) > 3 else None

    def clip(s):
        return datetime.strptime(s, "%H:%M:%S").time() if s else None

    print(f"{len(rows)} decision cycles, {rows[0][0]:%H:%M:%S}Z .. {rows[-1][0]:%H:%M:%S}Z\n")
    print(f"{'time':<10}{'curr':>5}{'tgt':>5}  action")
    print("-" * 44)
    prev = None
    for t, curr, tgt, act in rows:
        if (curr, tgt) != prev:
            mark = ""
            if lo and hi:
                inwin = clip(lo) <= t.time() <= clip(hi)
                mark = "  <= in load window" if inwin else ""
            print(f"{t:%H:%M:%S}Z{curr:>5}{tgt:>5}  {act}{mark}")
            prev = (curr, tgt)

    # Dwell: how long was each observed replica count actually in effect?
    print("\ndwell at each observed replica count (between first and last cycle):")
    dwell = {}
    for i, (t, curr, _, _) in enumerate(rows):
        end = rows[i + 1][0] if i + 1 < len(rows) else t
        dwell[curr] = dwell.get(curr, 0) + (end - t).total_seconds()
    total = sum(dwell.values()) or 1
    for k in sorted(dwell):
        print(f"  curr={k}: {dwell[k]/60:6.1f} min  ({100*dwell[k]/total:5.1f}%)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
