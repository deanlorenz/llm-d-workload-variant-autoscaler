#!/usr/bin/env python3
"""
Analyze H100 vLLM capacity data to estimate maximal concurrency and RPS.

Based on KV cache utilization and other measured parameters, this script:
1. Estimates the maximal concurrency (N_max) for each workload type
2. Estimates the maximal RPS for each request type

Saturation is considered at >80% KV cache utilization.
"""

import pandas as pd
import numpy as np
from pathlib import Path

def load_data(csv_path):
    """Load and clean the CSV data."""
    df = pd.read_csv(csv_path)
    
    # Handle different column names in different datasets
    kv_col = 'MaxKvcache' if 'MaxKvcache' in df.columns else 'Max Kvcache'
    
    # Remove rows with missing critical data
    required_cols = ['In-Tok', 'Out-Tok', 'RPS', 'E2E', kv_col, 'MaxRun']
    df = df.dropna(subset=required_cols)
    
    # Convert KV cache from percentage (0-1) to percentage (0-100) for clarity
    df['KV_Cache_Pct'] = df[kv_col] * 100
    
    return df

def estimate_n_from_metrics(row):
    """
    Estimate N (concurrent requests) from metrics.
    Formula: N ≈ GPS * ITL + Prefill / ITL
    """
    # Handle different column names
    gps = row.get('Mean GPS', row.get('GPS', np.nan))
    itl = row.get('ITL', np.nan)
    prefill = row.get('Prefill', np.nan)
    
    if pd.isna(gps) or pd.isna(itl) or itl == 0:
        return np.nan
    
    # GPS * ITL gives tokens being generated
    # Prefill / ITL gives requests in prefill phase
    n_estimate = gps * itl + (prefill / itl if not pd.isna(prefill) else 0)
    return n_estimate

def analyze_workload_type(group_df, workload_name):
    """Analyze a specific workload type to find N_max and max RPS."""
    
    print(f"\n{'='*80}")
    print(f"Workload Type: {workload_name}")
    print(f"{'='*80}")
    
    # Sort by KV cache utilization
    group_df = group_df.sort_values('KV_Cache_Pct')
    
    # Find the point near saturation (70-85% KV cache)
    # We want stable operation, so prefer lower end of saturation range
    stable_df = group_df[group_df['KV_Cache_Pct'] <= 80]
    
    if len(stable_df) == 0:
        print(f"⚠️  No stable measurements found (all above 80% KV cache)")
        stable_df = group_df[group_df['KV_Cache_Pct'] <= 85]
        if len(stable_df) == 0:
            print(f"⚠️  Using all data points")
            stable_df = group_df
    
    # Get the highest RPS point that's still stable
    max_stable_row = stable_df.loc[stable_df['RPS'].idxmax()]
    
    # N_max is the MaxRun at this point
    n_max = max_stable_row['MaxRun']
    e2e_at_n_max = max_stable_row['E2E']
    kv_cache_at_n_max = max_stable_row['KV_Cache_Pct']
    
    # Estimate N from metrics for validation
    n_estimate = estimate_n_from_metrics(max_stable_row)
    
    # Max RPS = N_max / E2E(N_max)
    # This is the theoretical max throughput at this concurrency
    max_rps_theoretical = n_max / e2e_at_n_max
    
    # Actual max RPS observed
    max_rps_observed = max_stable_row['RPS']
    
    print(f"\nStable Operation Point (KV Cache ≤ 80%):")
    print(f"  RPS: {max_rps_observed:.2f}")
    print(f"  KV Cache Utilization: {kv_cache_at_n_max:.1f}%")
    print(f"  E2E Latency: {e2e_at_n_max:.3f}s")
    print(f"  MaxRun (N_max): {n_max:.0f}")
    print(f"  Estimated N from metrics: {n_estimate:.1f}" if not pd.isna(n_estimate) else "  Estimated N: N/A")
    
    print(f"\nCapacity Estimates:")
    print(f"  Max Concurrency (N_max): {n_max:.0f} concurrent requests")
    print(f"  Theoretical Max RPS: {max_rps_theoretical:.2f} req/s")
    print(f"  Observed Max RPS: {max_rps_observed:.2f} req/s")
    
    # Show what happens at saturation
    saturated_df = group_df[group_df['KV_Cache_Pct'] >= 95]
    if len(saturated_df) > 0:
        sat_row = saturated_df.iloc[0]
        print(f"\nAt Saturation (KV Cache ≥ 95%):")
        print(f"  RPS: {sat_row['RPS']:.2f}")
        print(f"  KV Cache: {sat_row['KV_Cache_Pct']:.1f}%")
        print(f"  E2E Latency: {sat_row['E2E']:.3f}s (vs {e2e_at_n_max:.3f}s stable)")
        print(f"  MaxRun: {sat_row['MaxRun']:.0f} (vs {n_max:.0f} stable)")
    
    return {
        'workload': workload_name,
        'n_max': n_max,
        'max_rps_theoretical': max_rps_theoretical,
        'max_rps_observed': max_rps_observed,
        'e2e_at_n_max': e2e_at_n_max,
        'kv_cache_at_n_max': kv_cache_at_n_max,
        'n_estimate': n_estimate
    }

def main():
    import sys
    
    # Get CSV path from command line or use default
    if len(sys.argv) > 1:
        csv_path = Path(__file__).parent / sys.argv[1]
    else:
        csv_path = Path(__file__).parent / 'TA-H100_BS-65000__summary-W.csv'
    
    print("H100 vLLM Capacity Analysis")
    print("="*80)
    print(f"Analyzing: {csv_path.name}")
    print("Analyzing workload capacity based on KV cache utilization")
    print("Saturation threshold: >80% KV cache utilization")
    print()
    
    df = load_data(csv_path)
    
    # Group by workload type (In-Tok, Out-Tok combination)
    df['Workload'] = df['In-Tok'].astype(int).astype(str) + 'in_' + df['Out-Tok'].astype(int).astype(str) + 'out'
    
    results = []
    
    # Analyze each unique workload type
    workload_groups = df.groupby(['In-Tok', 'Out-Tok'])
    
    for (in_tok, out_tok), group in workload_groups:
        if len(group) < 2:
            continue  # Skip if not enough data points
        
        workload_name = f"{int(in_tok)} input tokens, {int(out_tok)} output tokens"
        result = analyze_workload_type(group, workload_name)
        results.append(result)
    
    # Summary table
    print(f"\n{'='*80}")
    print("SUMMARY: Maximal Capacity by Workload Type")
    print(f"{'='*80}")
    print(f"{'Workload':<40} {'N_max':>8} {'Max RPS':>10} {'E2E@N_max':>12} {'KV%@N_max':>10}")
    print(f"{'-'*40} {'-'*8} {'-'*10} {'-'*12} {'-'*10}")
    
    for r in results:
        print(f"{r['workload']:<40} {r['n_max']:>8.0f} {r['max_rps_observed']:>10.2f} {r['e2e_at_n_max']:>12.3f}s {r['kv_cache_at_n_max']:>9.1f}%")
    
    print(f"\n{'='*80}")
    print("Key Insights:")
    print(f"{'='*80}")
    
    # Find patterns
    results_df = pd.DataFrame(results)
    
    print(f"\n1. Workload with highest concurrency capacity:")
    max_n = results_df.loc[results_df['n_max'].idxmax()]
    print(f"   {max_n['workload']}: N_max = {max_n['n_max']:.0f}")
    
    print(f"\n2. Workload with highest throughput capacity:")
    max_rps = results_df.loc[results_df['max_rps_observed'].idxmax()]
    print(f"   {max_rps['workload']}: Max RPS = {max_rps['max_rps_observed']:.2f}")
    
    print(f"\n3. Relationship between token counts and capacity:")
    print(f"   - Longer outputs generally reduce max concurrency")
    print(f"   - Longer inputs increase prefill time but may allow higher concurrency")
    print(f"   - KV cache is the primary bottleneck at saturation")

if __name__ == '__main__':
    main()

# Made with Bob
