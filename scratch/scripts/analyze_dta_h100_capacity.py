#!/usr/bin/env python3
"""
Analyze DTA H100 capacity data and build capacity curves.

This script analyzes the DTA-AVG-H100_BS-65000__summary_903.csv dataset
and generates:
1. Capacity estimates for each workload type
2. Autoscaling recommendations
3. Capacity curves (N_max vs workload characteristics)
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys


def load_data(csv_path):
    """Load and clean the CSV data."""
    df = pd.read_csv(csv_path)
    
    # Remove rows with missing critical data
    required_cols = ['In-Tok', 'Out-Tok', 'RPS', 'E2E', 'MaxKvcache', 'MaxRun']
    df = df.dropna(subset=required_cols)
    
    # Convert KV cache from percentage (0-1) to percentage (0-100)
    df['KV_Cache_Pct'] = df['MaxKvcache'] * 100
    
    return df


def analyze_workload_group(group_df, group_name, variable_param):
    """Analyze a group of workloads with one varying parameter."""
    
    print(f"\n{'='*80}")
    print(f"Analysis: {group_name}")
    print(f"Variable Parameter: {variable_param}")
    print(f"{'='*80}\n")
    
    # Sort by the variable parameter
    if variable_param == 'In-Tok':
        group_df = group_df.sort_values('In-Tok')
    elif variable_param == 'Out-Tok':
        group_df = group_df.sort_values('Out-Tok')
    elif variable_param == 'RPS':
        group_df = group_df.sort_values('RPS')
    
    results = []
    
    for idx, row in group_df.iterrows():
        # Determine status based on KV cache
        if row['KV_Cache_Pct'] >= 95:
            status = '⚠️ Saturated'
        elif row['KV_Cache_Pct'] >= 80:
            status = '⚠️ Near Saturation'
        elif row['KV_Cache_Pct'] >= 60:
            status = '✅ Good Utilization'
        elif row['KV_Cache_Pct'] >= 40:
            status = '✅ Moderate'
        else:
            status = '✅ Low Utilization'
        
        result = {
            'In-Tok': int(row['In-Tok']),
            'Out-Tok': int(row['Out-Tok']),
            'RPS': row['RPS'],
            'N_max': int(row['MaxRun']),
            'KV_Cache_Pct': row['KV_Cache_Pct'],
            'E2E': row['E2E'],
            'TTFT': row['TTFT'],
            'ITL': row['ITL'],
            'Status': status
        }
        results.append(result)
    
    # Print table
    if variable_param == 'In-Tok':
        print(f"{'Input':>8} {'RPS':>5} {'N_max':>7} {'KV%':>6} {'E2E':>8} {'TTFT':>8} {'ITL':>7} {'Status':>20}")
        print(f"{'-'*8} {'-'*5} {'-'*7} {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*20}")
        for r in results:
            print(f"{r['In-Tok']:>8} {r['RPS']:>5.1f} {r['N_max']:>7} {r['KV_Cache_Pct']:>5.1f}% {r['E2E']:>8.3f} {r['TTFT']:>8.3f} {r['ITL']:>7.3f} {r['Status']:>20}")
    
    elif variable_param == 'Out-Tok':
        print(f"{'Output':>8} {'RPS':>5} {'N_max':>7} {'KV%':>6} {'E2E':>8} {'TTFT':>8} {'ITL':>7} {'Status':>20}")
        print(f"{'-'*8} {'-'*5} {'-'*7} {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*20}")
        for r in results:
            print(f"{r['Out-Tok']:>8} {r['RPS']:>5.1f} {r['N_max']:>7} {r['KV_Cache_Pct']:>5.1f}% {r['E2E']:>8.3f} {r['TTFT']:>8.3f} {r['ITL']:>7.3f} {r['Status']:>20}")
    
    elif variable_param == 'RPS':
        print(f"{'RPS':>5} {'N_max':>7} {'KV%':>6} {'E2E':>8} {'TTFT':>8} {'ITL':>7} {'Status':>20}")
        print(f"{'-'*5} {'-'*7} {'-'*6} {'-'*8} {'-'*8} {'-'*7} {'-'*20}")
        for r in results:
            print(f"{r['RPS']:>5.1f} {r['N_max']:>7} {r['KV_Cache_Pct']:>5.1f}% {r['E2E']:>8.3f} {r['TTFT']:>8.3f} {r['ITL']:>7.3f} {r['Status']:>20}")
    
    # Find optimal point (highest N_max below 80% KV cache)
    stable_results = [r for r in results if r['KV_Cache_Pct'] <= 80]
    if stable_results:
        optimal = max(stable_results, key=lambda x: x['N_max'])
        print(f"\n✅ Optimal Point (KV ≤ 80%):")
        print(f"   {variable_param}: {optimal[variable_param]}")
        print(f"   N_max: {optimal['N_max']} concurrent requests")
        print(f"   KV Cache: {optimal['KV_Cache_Pct']:.1f}%")
        print(f"   E2E: {optimal['E2E']:.3f}s")
        print(f"   Max RPS: {optimal['RPS']:.1f} req/s")
    
    # Find saturation point
    saturated_results = [r for r in results if r['KV_Cache_Pct'] >= 95]
    if saturated_results:
        saturated = saturated_results[0]
        print(f"\n⚠️  Saturation Point (KV ≥ 95%):")
        print(f"   {variable_param}: {saturated[variable_param]}")
        print(f"   N_max: {saturated['N_max']} concurrent requests")
        print(f"   KV Cache: {saturated['KV_Cache_Pct']:.1f}%")
        print(f"   E2E: {saturated['E2E']:.3f}s")
    
    return results


def build_capacity_table(df):
    """Build a capacity lookup table."""
    print(f"\n{'='*80}")
    print("CAPACITY LOOKUP TABLE")
    print(f"{'='*80}\n")
    
    # Filter to stable points (KV cache <= 80%)
    stable_df = df[df['KV_Cache_Pct'] <= 80].copy()
    
    # Group by workload type and get max N for each
    capacity_table = {}
    
    for (in_tok, out_tok), group in stable_df.groupby(['In-Tok', 'Out-Tok']):
        # Get the point with highest RPS (most stressed but still stable)
        max_rps_row = group.loc[group['RPS'].idxmax()]
        
        capacity_table[(int(in_tok), int(out_tok))] = {
            'N_max': int(max_rps_row['MaxRun']),
            'max_rps': float(max_rps_row['RPS']),
            'kv_pct': float(max_rps_row['KV_Cache_Pct']),
            'e2e': float(max_rps_row['E2E'])
        }
    
    # Print table
    print(f"{'Input':>8} {'Output':>8} {'N_max':>7} {'Max RPS':>9} {'KV%':>6} {'E2E':>8}")
    print(f"{'-'*8} {'-'*8} {'-'*7} {'-'*9} {'-'*6} {'-'*8}")
    
    for (in_tok, out_tok), cap in sorted(capacity_table.items()):
        print(f"{in_tok:>8} {out_tok:>8} {cap['N_max']:>7} {cap['max_rps']:>9.1f} {cap['kv_pct']:>5.1f}% {cap['e2e']:>8.3f}")
    
    return capacity_table


def generate_autoscaling_recommendations(capacity_table):
    """Generate autoscaling recommendations."""
    print(f"\n{'='*80}")
    print("AUTOSCALING RECOMMENDATIONS")
    print(f"{'='*80}\n")
    
    print("Scale-Out Thresholds:")
    print("  - KV Cache ≥ 70% (proactive)")
    print("  - KV Cache ≥ 75% (urgent)")
    print("  - Queue depth > 5 requests")
    print("  - Concurrent requests > 0.85 × N_max")
    print()
    
    print("Scale-In Thresholds:")
    print("  - KV Cache ≤ 40% for > 5 minutes")
    print("  - Concurrent requests < 0.4 × N_max")
    print("  - Queue depth = 0")
    print()
    
    print("Workload-Specific Recommendations:")
    print()
    
    # Categorize workloads
    short_context = [(k, v) for k, v in capacity_table.items() if k[0] <= 5000 and k[1] <= 500]
    medium_context = [(k, v) for k, v in capacity_table.items() if 5000 < k[0] <= 8000 or 500 < k[1] <= 1000]
    long_context = [(k, v) for k, v in capacity_table.items() if k[0] > 8000 or k[1] > 1000]
    
    if short_context:
        avg_n = np.mean([v['N_max'] for _, v in short_context])
        avg_rps = np.mean([v['max_rps'] for _, v in short_context])
        print(f"Short Context (≤5000 input, ≤500 output):")
        print(f"  - Avg N_max: {avg_n:.0f} concurrent requests")
        print(f"  - Avg Max RPS: {avg_rps:.1f} req/s")
        print(f"  - Scale out at: 70% KV cache or {int(avg_n * 0.85)} concurrent requests")
        print()
    
    if medium_context:
        avg_n = np.mean([v['N_max'] for _, v in medium_context])
        avg_rps = np.mean([v['max_rps'] for _, v in medium_context])
        print(f"Medium Context (5000-8000 input or 500-1000 output):")
        print(f"  - Avg N_max: {avg_n:.0f} concurrent requests")
        print(f"  - Avg Max RPS: {avg_rps:.1f} req/s")
        print(f"  - Scale out at: 65% KV cache or {int(avg_n * 0.85)} concurrent requests")
        print()
    
    if long_context:
        avg_n = np.mean([v['N_max'] for _, v in long_context])
        avg_rps = np.mean([v['max_rps'] for _, v in long_context])
        print(f"Long Context (>8000 input or >1000 output):")
        print(f"  - Avg N_max: {avg_n:.0f} concurrent requests")
        print(f"  - Avg Max RPS: {avg_rps:.1f} req/s")
        print(f"  - Scale out at: 60% KV cache or {int(avg_n * 0.85)} concurrent requests")
        print(f"  - Note: More conservative due to saturation risk")
        print()


def main():
    # Get CSV path from command line or use default
    if len(sys.argv) > 1:
        csv_path = Path(__file__).parent / sys.argv[1]
    else:
        csv_path = Path(__file__).parent / 'DTA-AVG-H100_BS-65000__summary_903.csv'
    
    print("="*80)
    print("H100 vLLM Capacity Analysis - DTA Dataset")
    print("="*80)
    print(f"Dataset: {csv_path.name}")
    print()
    
    df = load_data(csv_path)
    
    print(f"Total measurements: {len(df)}")
    print(f"Workload types: {df.groupby(['In-Tok', 'Out-Tok']).ngroups}")
    print()
    
    # Analysis 1: Fixed output (300), varying input
    fixed_out_300 = df[(df['Out-Tok'] == 300) & (df['RPS'] == 2.0)]
    if len(fixed_out_300) > 0:
        analyze_workload_group(
            fixed_out_300,
            "Fixed Output (300 tokens), Varying Input Length",
            "In-Tok"
        )
    
    # Analysis 2: Fixed input (5000), varying output
    fixed_in_5000 = df[(df['In-Tok'] == 5000) & (df['RPS'] == 2.0)]
    if len(fixed_in_5000) > 0:
        analyze_workload_group(
            fixed_in_5000,
            "Fixed Input (5000 tokens), Varying Output Length",
            "Out-Tok"
        )
    
    # Analysis 3: Fixed workload (5000, 300), varying RPS
    fixed_workload = df[(df['In-Tok'] == 5000) & (df['Out-Tok'] == 300)]
    if len(fixed_workload) > 0:
        analyze_workload_group(
            fixed_workload,
            "Fixed Workload (5000 input, 300 output), Varying RPS",
            "RPS"
        )
    
    # Build capacity table
    capacity_table = build_capacity_table(df)
    
    # Generate autoscaling recommendations
    generate_autoscaling_recommendations(capacity_table)
    
    print(f"\n{'='*80}")
    print("Analysis Complete!")
    print(f"{'='*80}\n")


if __name__ == '__main__':
    main()

# Made with Bob
