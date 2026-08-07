#!/usr/bin/env python3
"""Per-stage client-side results for the 2026-08-07 ladder run, with the harness's
output-token defect quantified per stage rather than assumed uniform.

Why this exists: the per-request trace was lost to an OOM, so the usual per-request
output-token correction cannot run. The per-STAGE aggregates survived, and they are
enough to (a) report latency per load level and (b) bound the harness defect, because
the scenario pins the true output length to a narrow band.

The profile requests output lengths ~N(512, 20) truncated to [480, 550]. So ANY
reported output_len outside [480, 550] is a harness artifact, not workload variation.
That turns `output_len`'s own min/max into a direct measurement of the defect's
dispersion -- which is the thing that decides whether a single scalar correction factor
is legitimate. It is not: see the inflation column against the min/max columns.

Latency columns are wall-clock and therefore UNAFFECTED by the token miscount.
Per-token columns (tpot, itl, ntpot) divide by the wrong denominator and are reported
here only to show they must not be used.

Usage: python3 stage_table.py [--csv]
"""
import json
import sys

RATES = [2, 5, 8, 10, 12, 15, 20, 2]  # from ta_autoscale_ladder.yaml load.stages
TRUE_LO, TRUE_HI, TRUE_MEAN = 480.0, 550.0, 512.0
DIR = "session-notes/scratch/ladder-run"


def main():
    as_csv = "--csv" in sys.argv
    rows = []
    for i, rate in enumerate(RATES):
        d = json.load(open(f"{DIR}/stage_{i}.json"))
        s, load = d["successes"], d["load_summary"]
        lat, thr, olen = s["latency"], s["throughput"], s["output_len"]
        rows.append({
            "stage": i,
            "rate": rate,
            "achieved": load["achieved_rate"],
            "n": s["count"],
            "fail": d["failures"]["count"],
            "lat_mean": lat["request_latency"]["mean"],
            "lat_p95": lat["request_latency"]["p95"],
            "lat_max": lat["request_latency"]["max"],
            "ttft_mean": lat["time_to_first_token"]["mean"],
            "ttft_p95": lat["time_to_first_token"]["p95"],
            "olen_mean": olen["mean"],
            "olen_min": olen["min"],
            "olen_max": olen["max"],
            "in_tps": thr["input_tokens_per_sec"],
            "out_tps": thr["output_tokens_per_sec"],
            "secs": d["benchmark_time_seconds"],
        })

    if as_csv:
        keys = list(rows[0])
        print(",".join(keys))
        for r in rows:
            print(",".join(str(r[k]) for k in keys))
        return 0

    print("LATENCY (wall-clock; unaffected by the token miscount)")
    print(f"{'stg':>3} {'RPS':>4} {'achv':>6} {'n':>5} {'fail':>4} "
          f"{'lat_mean':>9} {'lat_p95':>8} {'lat_max':>8} {'ttft_mean':>10} {'ttft_p95':>9}")
    for r in rows:
        print(f"{r['stage']:>3} {r['rate']:>4} {r['achieved']:>6.2f} {r['n']:>5} "
              f"{r['fail']:>4} {r['lat_mean']:>9.3f} {r['lat_p95']:>8.3f} "
              f"{r['lat_max']:>8.3f} {r['ttft_mean']:>10.4f} {r['ttft_p95']:>9.4f}")

    print(f"\nHARNESS OUTPUT-TOKEN DEFECT (truth is bounded to "
          f"[{TRUE_LO:.0f}, {TRUE_HI:.0f}], mean {TRUE_MEAN:.0f})")
    print(f"{'stg':>3} {'RPS':>4} {'olen_mean':>10} {'infl':>6} {'olen_min':>9} "
          f"{'olen_max':>9}  verdict")
    for r in rows:
        out_of_band = r["olen_min"] < TRUE_LO or r["olen_max"] > TRUE_HI
        v = "min/max OUTSIDE true band -> per-request error" if out_of_band else "in band"
        print(f"{r['stage']:>3} {r['rate']:>4} {r['olen_mean']:>10.1f} "
              f"{r['olen_mean'] / TRUE_MEAN:>6.3f} {r['olen_min']:>9.0f} "
              f"{r['olen_max']:>9.0f}  {v}")

    print("\nTHROUGHPUT: input is trustworthy, output is inflated by the same defect")
    print(f"{'stg':>3} {'RPS':>4} {'in_tok/s':>9} {'out_tok/s(rep)':>15} "
          f"{'out_tok/s(true)':>16} {'secs':>7}")
    for r in rows:
        true_out = r["n"] * TRUE_MEAN / r["secs"]
        print(f"{r['stage']:>3} {r['rate']:>4} {r['in_tps']:>9.1f} "
              f"{r['out_tps']:>15.1f} {true_out:>16.1f} {r['secs']:>7.1f}")

    # Aggregate ITL derived WITHOUT any per-request division: wall-clock decode window
    # over the KNOWN true token count. This is the only per-token figure from this run
    # that is defensible, and it is a mean only -- no percentile version exists.
    print("\nDEFENSIBLE per-token figure (aggregate, no per-request denominator):")
    print(f"{'stg':>3} {'RPS':>4} {'decode_s':>9} {'itl_true_ms':>12} {'itl_reported_ms':>16}")
    for r in rows:
        d = json.load(open(f"{DIR}/stage_{r['stage']}.json"))
        rep = d["successes"]["latency"]["inter_token_latency"]["mean"]
        decode = r["lat_mean"] - r["ttft_mean"]
        print(f"{r['stage']:>3} {r['rate']:>4} {decode:>9.3f} "
              f"{1000 * decode / TRUE_MEAN:>12.2f} {1000 * rep:>16.2f}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
