
#!/usr/bin/env python3
"""
Build gps_itl_curve.csv and estimate KV tokens from raw run logs exported to CSV/TSV.

Input CSV/TSV must contain (case-insensitive) columns:
  In-Tok, Out-Tok, MaxRun, ITL, Mean GPS, Max Kvcache
Optional: Mean PPS (for later use)

Usage:
  python build_curve_from_runs.py --in runs.csv --out gps_itl_curve.csv --phi 0.5
"""
import argparse
import pandas as pd
import numpy as np

REQ = ['MaxRun','ITL','Mean GPS','In-Tok','Out-Tok','Max Kvcache']

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--in', dest='inp', required=True, help='Input CSV/TSV file of runs')
    ap.add_argument('--out', dest='out', default='gps_itl_curve.csv', help='Output curve CSV (A,GPS,ITL)')
    ap.add_argument('--phi', type=float, default=0.5, help='OL fraction alive in cache (default 0.5)')
    args = ap.parse_args()

    # Let pandas sniff delimiter
    try:
        df = pd.read_csv(args.inp)
    except Exception:
        # Fallback to whitespace-separated values
        df = pd.read_csv(args.inp, sep=r'\s+')

    df.columns = [c.strip() for c in df.columns]

    for c in REQ:
        if c not in df.columns:
            raise SystemExit(f"Missing required column: {c}")

    cur = df.dropna(subset=['MaxRun','Mean GPS','ITL'])
    cur = cur[(cur['MaxRun']>0) & (cur['Mean GPS']>0) & (cur['ITL']>0)]

    # Curve by median per MaxRun
    curve = (cur.groupby('MaxRun', as_index=False)
               .agg(GPS=('Mean GPS','median'), ITL=('ITL','median'), n=('ITL','count')))
    curve = curve.rename(columns={'MaxRun': 'A'})
    curve.sort_values('A').to_csv(args.out, index=False)

    # KV tokens estimation from utilization peak
    phi = args.phi
    k_rows = cur.dropna(subset=['Max Kvcache', 'In-Tok', 'Out-Tok'])
    k_rows = k_rows[k_rows['Max Kvcache']>0.01]
    K_est_each = (k_rows['MaxRun'] * (k_rows['In-Tok'] + phi*k_rows['Out-Tok'])) / k_rows['Max Kvcache']

    if not K_est_each.empty:
        stats = {
            'count': int(K_est_each.shape[0]),
            'median': float(np.median(K_est_each)),
            'p10': float(np.percentile(K_est_each,10)),
            'p90': float(np.percentile(K_est_each,90)),
            'mean': float(np.mean(K_est_each)),
        }
        print("\nEstimated total KV capacity (tokens):")
        for k,v in stats.items():
            print(f"  {k:>6}: {v:,.1f}")
        print("\nSaved decode curve ->", args.out)
    else:
        print("Could not estimate KV capacity (no valid Max Kvcache rows). Saved curve ->", args.out)

if __name__ == '__main__':
    main()
