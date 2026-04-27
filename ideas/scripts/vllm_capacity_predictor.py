
#!/usr/bin/env python3
"""
LLM vLLM Capacity Predictor
---------------------------

Purpose
=======
Estimate per-instance sustainable RPS and the number of vLLM instances needed for a target
RPS given:
  * Fixed request shape (IL = input tokens, OL = output tokens)
  * KV-cache capacity (in tokens) and a utilization cap (e.g., 0.8)
  * A small empirical curve of decode performance measured at a few decode-concurrency
    levels A: CSV with columns A,GPS,ITL (ITL optional)

Model
=====
We use the following relations (see vLLM docs & standard LLM benchmarking definitions):
  * Cache-constrained concurrency: A_cache = u * K / (IL + phi * OL)
  * Decode sharing relation: ITL(A) ~ A_dec / GPS(A)
  * Latency model: E2E(A) ~ (IL / PPS_eff) + OL * ITL(A)
  * Per-instance sustainable RPS:
        lambda_token(A) = GPS(A) / OL
        lambda_conc(A)  = A / E2E(A)
        lambda_inst(A)  = min(lambda_token(A), lambda_conc(A))
    We evaluate at A_eff = min(A_cache, max(A in CSV)) and clip within measured range.

Notes
=====
- If ITL is missing in the CSV, we derive it by ITL(A) = A / (GPS(A) * eta), with eta≈1.0
  (eta parameterizes deviations when total running requests include some in prefill).
- If PPS is unknown, we set prefill time to 0 by default (IL/PPS_eff -> 0). You can
  provide --pps to incorporate prefill.
- CSV format:
      A,GPS,ITL
      4,5500,0.0007
      8,3500,0.0018
      12,2500,0.0030
  ITL column can be omitted; in that case, pass --derive-itl-eta (default=1.0).

CLI Examples
============
# Basic: ignore prefill term, 80% KV utilization, phi=0.5
python vllm_capacity_predictor.py \
  --curve gps_itl_curve.csv --il 5000 --ol 800 \
  --kv-tokens 3200000 --util 0.8 --phi 0.5 \
  --target-rps 30

# Include PPS for prefill
python vllm_capacity_predictor.py \
  --curve gps_itl_curve.csv --il 5000 --ol 800 \
  --kv-tokens 3.2e6 --util 0.8 --phi 0.5 --pps 12000 \
  --target-rps 30

# Print a sweep table for RPS targets (optional)
python vllm_capacity_predictor.py \
  --curve gps_itl_curve.csv --il 2000 --ol 256 \
  --kv-tokens 2.0e6 --util 0.8 --pps 18000 \
  --rps-sweep 10 100 10

"""

import argparse
import csv
import math
from typing import List, Tuple, Optional

# ---------- Utilities ----------

def lin_interp(xq: float, xs: List[float], ys: List[float]) -> float:
    """Simple 1D linear interpolation with clipping to endpoints."""
    if not xs:
        raise ValueError("Empty xs")
    if len(xs) != len(ys):
        raise ValueError("xs and ys must have the same length")
    # If only one point, return its y
    if len(xs) == 1:
        return ys[0]
    # Ensure ascending by xs; if not sorted, sort pairs
    pairs = sorted(zip(xs, ys), key=lambda p: p[0])
    xs_sorted = [p[0] for p in pairs]
    ys_sorted = [p[1] for p in pairs]
    # Clip
    if xq <= xs_sorted[0]:
        return ys_sorted[0]
    if xq >= xs_sorted[-1]:
        return ys_sorted[-1]
    # Find segment
    for i in range(1, len(xs_sorted)):
        if xq <= xs_sorted[i]:
            x0, y0 = xs_sorted[i-1], ys_sorted[i-1]
            x1, y1 = xs_sorted[i],   ys_sorted[i]
            t = (xq - x0) / (x1 - x0)
            return y0 + t * (y1 - y0)
    # Fallback (shouldn't reach)
    return ys_sorted[-1]

# ---------- Core computations ----------

def compute_cache_concurrency(il: float, ol: float, kv_tokens: float, util: float, phi: float) -> float:
    denom = il + phi * ol
    if denom <= 0:
        raise ValueError("IL + phi*OL must be positive")
    return util * kv_tokens / denom


def predict_for_A(
    A: float,
    il: float,
    ol: float,
    pps: Optional[float],
    xs_A: List[float], ys_GPS: List[float], ys_ITL: Optional[List[float]],
    derive_itl_eta: float = 1.0,
) -> Tuple[float, float, float, float, float]:
    """
    Predict (gpsA, itlA, t_prefill, E2E, lambda_inst) at a given concurrency A.

    Returns (gpsA, itlA, t_prefill, E2E, lambda_inst)
    """
    gpsA = lin_interp(A, xs_A, ys_GPS)
    if ys_ITL is not None:
        itlA = lin_interp(A, xs_A, ys_ITL)
    else:
        # Derive ITL ≈ A / (GPS * eta). Units: (dimensionless)/(tok/s) = s/tok
        if gpsA <= 0:
            raise ValueError("GPS at A is non-positive; cannot derive ITL")
        itlA = (A / gpsA) / derive_itl_eta

    t_prefill = 0.0 if (pps is None or pps <= 0) else (il / pps)
    E2E = t_prefill + ol * itlA

    # Two constraints
    lambda_token = gpsA / ol if ol > 0 else float('inf')
    lambda_conc  = A / E2E if E2E > 0 else float('inf')
    lambda_inst  = min(lambda_token, lambda_conc)

    return gpsA, itlA, t_prefill, E2E, lambda_inst


def load_curve(csv_path: str) -> Tuple[List[float], List[float], Optional[List[float]]]:
    xs_A: List[float] = []
    ys_GPS: List[float] = []
    ys_ITL: Optional[List[float]] = None
    maybe_itl: List[float] = []
    with open(csv_path, 'r', newline='') as f:
        reader = csv.DictReader(f)
        header = [h.strip().lower() for h in reader.fieldnames or []]
        has_itl = ('itl' in header) or ('inter_token_latency' in header) or ('intertokenlatency' in header)
        for row in reader:
            A = float(row.get('A') or row.get('a'))
            GPS = float(row.get('GPS') or row.get('gps'))
            xs_A.append(A)
            ys_GPS.append(GPS)
            if has_itl:
                val = row.get('ITL') or row.get('inter_token_latency') or row.get('intertokenlatency')
                maybe_itl.append(float(val))
    if maybe_itl:
        ys_ITL = maybe_itl
    return xs_A, ys_GPS, ys_ITL


# ---------- CLI ----------

def main():
    ap = argparse.ArgumentParser(description="vLLM capacity predictor (decode-curve based)")
    ap.add_argument('--curve', required=True, help='CSV file with columns A,GPS[,ITL]')
    ap.add_argument('--il', type=float, required=True, help='Input tokens per request (IL)')
    ap.add_argument('--ol', type=float, required=True, help='Output tokens per request (OL)')
    ap.add_argument('--kv-tokens', type=float, required=True, help='Total KV-cache capacity in tokens (across blocks)')
    ap.add_argument('--util', type=float, default=0.8, help='Allowed average KV-cache utilization (0..1), default 0.8')
    ap.add_argument('--phi', type=float, default=0.5, help='Average fraction of OL alive in cache, default 0.5')
    ap.add_argument('--pps', type=float, default=None, help='Effective PPS for prefill term (optional)')
    ap.add_argument('--derive-itl-eta', type=float, default=1.0, help='Eta for deriving ITL when ITL not in CSV (default 1.0)')
    ap.add_argument('--target-rps', type=float, default=None, help='Cluster target RPS; if provided, prints instances needed')
    ap.add_argument('--rps-sweep', nargs=3, type=float, help='Optional: start stop step for RPS sweep table')

    args = ap.parse_args()

    xs_A, ys_GPS, ys_ITL = load_curve(args.curve)
    if not xs_A:
        raise SystemExit("Curve CSV appears empty or missing columns A,GPS")

    # Compute cache-limited concurrency
    A_cache = compute_cache_concurrency(args.il, args.ol, args.kv_tokens, args.util, args.phi)

    A_min, A_max = min(xs_A), max(xs_A)
    # Choose effective A within measured range (clip)
    A_eff = max(A_min, min(A_cache, A_max))

    gpsA, itlA, t_prefill, E2E, lambda_inst = predict_for_A(
        A=A_eff,
        il=args.il,
        ol=args.ol,
        pps=args.pps,
        xs_A=xs_A, ys_GPS=ys_GPS, ys_ITL=ys_ITL,
        derive_itl_eta=args.derive_itl_eta,
    )

    print("\n=== vLLM Capacity Prediction (Per Instance) ===")
    print(f"Measured curve range A in [{A_min:.2f}, {A_max:.2f}]  |  A_cache={A_cache:.3f}  ->  A_eff={A_eff:.3f}")
    print(f"IL={args.il:.1f}  OL={args.ol:.1f}  phi={args.phi:.2f}  util={args.util:.2f}")
    print(f"KV tokens={args.kv_tokens:.0f}  PPS={'(not used)' if not args.pps else args.pps}")
    print(f"gps(A_eff)={gpsA:.3f} tok/s   itl(A_eff)={itlA*1000:.3f} ms/tok")
    print(f"prefill={t_prefill:.6f} s   E2E={E2E:.6f} s  |  per-inst RPS cap={lambda_inst:.6f} req/s")

    if args.target_rps is not None:
        N = math.ceil(args.target_rps / lambda_inst) if lambda_inst > 0 else math.inf
        print(f"\nTarget cluster RPS={args.target_rps:.3f}  ->  required instances N={N}")

    if args.rps_sweep is not None:
        start, stop, step = args.rps_sweep
        print("\nRPS  |  N instances  |  concurrency per inst (A_eff)  |  token bound GPS/OL  |  conc bound A_eff/E2E")
        r = start
        while r <= stop + 1e-9:
            N = math.ceil(r / lambda_inst) if lambda_inst > 0 else math.inf
            token_bound = gpsA / args.ol if args.ol > 0 else float('inf')
            conc_bound  = A_eff / E2E if E2E > 0 else float('inf')
            print(f"{r:6.1f}  |  {N:11d}  |  {A_eff:23.2f}  |  {token_bound:17.3f}  |  {conc_bound:17.3f}")
            r += step

if __name__ == '__main__':
    main()
