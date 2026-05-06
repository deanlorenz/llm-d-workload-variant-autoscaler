#!/usr/bin/env python3
"""
Compute N_max directly from KV cache size, input length, and output length.

The KV cache stores key-value pairs for all tokens (input + output) for all
concurrent requests. The relationship is:

KV_cache_usage = (N × (IL + OL)) / total_cache_size

Therefore:
N_max = (target_KV_pct × total_cache_size) / (IL + OL)

This script:
1. Estimates the total cache size from measurements
2. Builds a predictive model for N_max given IL and OL
3. Validates the model against actual measurements
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys


def estimate_cache_size(df):
    """
    Estimate total KV cache size from measurements.
    
    For each measurement:
    cache_size = (MaxRun × (In-Tok + Out-Tok)) / MaxKvcache
    
    We take the median to get a robust estimate.
    Only use non-saturated measurements (KV cache < 80%) for accurate estimation.
    """
    df = df.copy()
    
    # Calculate implied cache size for each measurement
    df['implied_cache_size'] = (df['MaxRun'] * (df['In-Tok'] + df['Out-Tok'])) / df['MaxKvcache']
    
    # Only use non-saturated measurements (KV cache < 80%)
    # Also require at least 10% utilization for reliability
    reliable_df = df[(df['MaxKvcache'] >= 0.10) & (df['MaxKvcache'] < 0.80)]
    
    if len(reliable_df) == 0:
        print("⚠️  Warning: No non-saturated measurements found, using all data")
        reliable_df = df[df['MaxKvcache'] >= 0.10]
    
    if len(reliable_df) == 0:
        reliable_df = df
    
    # Get statistics
    cache_sizes = reliable_df['implied_cache_size'].dropna()
    
    median_cache = cache_sizes.median()
    mean_cache = cache_sizes.mean()
    std_cache = cache_sizes.std()
    
    print("="*80)
    print("KV CACHE SIZE ESTIMATION")
    print("="*80)
    print(f"\nBased on {len(cache_sizes)} measurements:")
    print(f"  Median cache size: {median_cache:,.0f} tokens")
    print(f"  Mean cache size:   {mean_cache:,.0f} tokens")
    print(f"  Std deviation:     {std_cache:,.0f} tokens")
    print(f"  Min:               {cache_sizes.min():,.0f} tokens")
    print(f"  Max:               {cache_sizes.max():,.0f} tokens")
    
    # Show distribution by KV cache utilization
    print(f"\nCache size by utilization level:")
    for kv_range in [(0.0, 0.3), (0.3, 0.6), (0.6, 0.8), (0.8, 1.0)]:
        subset = reliable_df[
            (reliable_df['MaxKvcache'] >= kv_range[0]) & 
            (reliable_df['MaxKvcache'] < kv_range[1])
        ]
        if len(subset) > 0:
            avg_cache = subset['implied_cache_size'].mean()
            print(f"  {kv_range[0]*100:.0f}-{kv_range[1]*100:.0f}% KV: {avg_cache:,.0f} tokens (n={len(subset)})")
    
    return median_cache


def predict_n_max(input_tokens, output_tokens, cache_size, target_kv_pct=0.80):
    """
    Predict N_max for given input/output lengths.
    
    Formula:
    N_max = (target_KV_pct × cache_size) / (input_tokens + output_tokens)
    
    Args:
        input_tokens: Input length
        output_tokens: Output length
        cache_size: Total KV cache size in tokens
        target_kv_pct: Target KV cache utilization (default: 0.80)
    
    Returns:
        Predicted N_max
    """
    total_tokens_per_request = input_tokens + output_tokens
    n_max = (target_kv_pct * cache_size) / total_tokens_per_request
    return n_max


def validate_model(df, cache_size):
    """
    Validate the N_max prediction model against actual measurements.
    """
    print("\n" + "="*80)
    print("MODEL VALIDATION")
    print("="*80)
    
    df = df.copy()
    
    # Predict N_max for each measurement at its actual KV cache level
    df['predicted_N_max'] = df.apply(
        lambda row: predict_n_max(
            row['In-Tok'], 
            row['Out-Tok'], 
            cache_size, 
            row['MaxKvcache']
        ),
        axis=1
    )
    
    # Calculate error
    df['error'] = df['predicted_N_max'] - df['MaxRun']
    df['error_pct'] = (df['error'] / df['MaxRun']) * 100
    
    # Statistics
    print(f"\nPrediction accuracy:")
    print(f"  Mean absolute error: {df['error'].abs().mean():.2f} requests")
    print(f"  Mean percentage error: {df['error_pct'].abs().mean():.1f}%")
    print(f"  RMSE: {np.sqrt((df['error']**2).mean()):.2f} requests")
    
    # Show some examples
    print(f"\nSample predictions:")
    print(f"{'Input':>8} {'Output':>8} {'KV%':>6} {'Actual':>8} {'Predicted':>10} {'Error':>8}")
    print(f"{'-'*8} {'-'*8} {'-'*6} {'-'*8} {'-'*10} {'-'*8}")
    
    # Sample across different workload types
    samples = df.sample(min(15, len(df))).sort_values(['In-Tok', 'Out-Tok'])
    for _, row in samples.iterrows():
        print(f"{row['In-Tok']:>8.0f} {row['Out-Tok']:>8.0f} {row['MaxKvcache']*100:>5.1f}% "
              f"{row['MaxRun']:>8.0f} {row['predicted_N_max']:>10.1f} {row['error']:>8.1f}")
    
    return df


def build_n_max_table(cache_size, target_kv_pct=0.80):
    """
    Build a lookup table of N_max for common workload types.
    """
    print("\n" + "="*80)
    print(f"N_MAX LOOKUP TABLE (at {target_kv_pct*100:.0f}% KV cache)")
    print("="*80)
    
    # Common input lengths
    input_lengths = [1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000, 10000, 12000, 15000]
    
    # Common output lengths
    output_lengths = [100, 200, 300, 400, 500, 600, 800, 1000, 1200, 1500, 1800, 2000]
    
    print(f"\n{'Input':>8} {'Output':>8} {'N_max':>8} {'Total Tokens':>14} {'Cache Usage':>12}")
    print(f"{'-'*8} {'-'*8} {'-'*8} {'-'*14} {'-'*12}")
    
    results = []
    
    for in_tok in input_lengths:
        for out_tok in output_lengths:
            n_max = predict_n_max(in_tok, out_tok, cache_size, target_kv_pct)
            total_tokens = in_tok + out_tok
            cache_usage = n_max * total_tokens
            
            # Only show reasonable combinations
            if n_max >= 1 and total_tokens <= 20000:
                results.append({
                    'input': in_tok,
                    'output': out_tok,
                    'n_max': int(n_max),
                    'total_tokens': total_tokens,
                    'cache_usage': cache_usage
                })
    
    # Sort by input then output
    results.sort(key=lambda x: (x['input'], x['output']))
    
    # Print selected entries (not all combinations)
    for r in results[::3]:  # Every 3rd entry to keep output manageable
        print(f"{r['input']:>8} {r['output']:>8} {r['n_max']:>8} {r['total_tokens']:>14,} {r['cache_usage']:>12,.0f}")
    
    return results


def generate_prediction_function(cache_size):
    """
    Generate a Python function for runtime N_max prediction.
    """
    print("\n" + "="*80)
    print("RUNTIME PREDICTION FUNCTION")
    print("="*80)
    
    code = f'''
def predict_n_max_runtime(input_tokens, output_tokens, target_kv_pct=0.75):
    """
    Predict maximum concurrent requests for given workload.
    
    Args:
        input_tokens: Average input tokens per request
        output_tokens: Average output tokens per request
        target_kv_pct: Target KV cache utilization (default: 0.75 for safety)
    
    Returns:
        n_max: Maximum concurrent requests at target utilization
    """
    # Estimated cache size from H100 measurements
    CACHE_SIZE = {cache_size:.0f}  # tokens
    
    # Calculate N_max
    total_tokens_per_request = input_tokens + output_tokens
    n_max = (target_kv_pct * CACHE_SIZE) / total_tokens_per_request
    
    return int(n_max)


# Example usage:
# For 5000 input, 300 output tokens at 75% target:
# n_max = predict_n_max_runtime(5000, 300, 0.75)
# Result: {int(predict_n_max(5000, 300, cache_size, 0.75))} concurrent requests

# For autoscaling decision:
def should_scale_out(current_n, input_tokens, output_tokens, current_kv_pct):
    """
    Determine if scale-out is needed.
    
    Args:
        current_n: Current concurrent requests
        input_tokens: Average input tokens
        output_tokens: Average output tokens
        current_kv_pct: Current KV cache utilization (0.0-1.0)
    
    Returns:
        (should_scale, reason, recommended_instances)
    """
    # Get capacity at 75% target
    n_max_75 = predict_n_max_runtime(input_tokens, output_tokens, 0.75)
    
    # Scale out if:
    # 1. Current KV cache >= 70%
    # 2. Current N >= 85% of N_max
    
    if current_kv_pct >= 0.70:
        # Calculate how many instances needed
        instances_needed = int(np.ceil(current_kv_pct / 0.60))  # Target 60% after scaling
        return (True, f"KV cache at {{current_kv_pct*100:.1f}}%", instances_needed)
    
    if current_n >= n_max_75 * 0.85:
        instances_needed = int(np.ceil(current_n / (n_max_75 * 0.70)))
        return (True, f"Concurrency at {{current_n}}/{{n_max_75}} ({{current_n/n_max_75*100:.1f}}%)", instances_needed)
    
    return (False, "Within safe operating range", 1)
'''
    
    print(code)
    
    return code


def main():
    # Get CSV path
    if len(sys.argv) > 1:
        csv_path = Path(__file__).parent / sys.argv[1]
    else:
        csv_path = Path(__file__).parent / 'DTA-AVG-H100_BS-65000__summary_903.csv'
    
    print("="*80)
    print("N_MAX COMPUTATION FROM KV CACHE SIZE")
    print("="*80)
    print(f"Dataset: {csv_path.name}\n")
    
    # Load data
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=['In-Tok', 'Out-Tok', 'MaxRun', 'MaxKvcache'])
    
    print(f"Loaded {len(df)} measurements\n")
    
    # Step 1: Estimate cache size
    cache_size = estimate_cache_size(df)
    
    # Step 2: Validate model
    validated_df = validate_model(df, cache_size)
    
    # Step 3: Build lookup table
    n_max_table = build_n_max_table(cache_size, target_kv_pct=0.80)
    
    # Step 4: Generate prediction function
    prediction_code = generate_prediction_function(cache_size)
    
    # Save prediction function
    output_file = Path(__file__).parent / 'n_max_predictor.py'
    with open(output_file, 'w') as f:
        f.write('"""Auto-generated N_max prediction function."""\n')
        f.write('import numpy as np\n')
        f.write(prediction_code)
    
    print(f"\n✅ Prediction function saved to: {output_file}")
    
    print("\n" + "="*80)
    print("SUMMARY")
    print("="*80)
    print(f"Estimated KV cache size: {cache_size:,.0f} tokens")
    print(f"Model accuracy: ±{validated_df['error'].abs().mean():.1f} requests")
    print(f"Formula: N_max = (target_KV% × {cache_size:.0f}) / (IL + OL)")
    print("\nExample predictions at 80% KV cache:")
    for il, ol in [(5000, 300), (5000, 1000), (8000, 300), (10000, 300)]:
        n = predict_n_max(il, ol, cache_size, 0.80)
        print(f"  {il:>5}in + {ol:>4}out = {n:>5.0f} concurrent requests")


if __name__ == '__main__':
    main()

# Made with Bob
