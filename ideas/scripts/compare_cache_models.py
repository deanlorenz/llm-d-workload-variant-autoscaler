#!/usr/bin/env python3
"""
Compare different KV cache usage models:
1. Model A: cache_usage = N × (IL + OL)
2. Model B: cache_usage = N × (IL + α×OL) where α is fitted
3. Model C: cache_usage = N × (IL + 0.5×OL) as suggested

Determine which model best fits the measurements.
"""

import pandas as pd
import numpy as np
from pathlib import Path
import sys


def load_data(csv_path):
    """Load and filter non-saturated data."""
    df = pd.read_csv(csv_path)
    df = df.dropna(subset=['In-Tok', 'Out-Tok', 'MaxRun', 'MaxKvcache'])
    
    # Only use non-saturated measurements (KV < 80%)
    df = df[(df['MaxKvcache'] >= 0.10) & (df['MaxKvcache'] < 0.80)]
    
    return df


def model_a_cache_size(row):
    """Model A: cache = N × (IL + OL)"""
    return (row['MaxRun'] * (row['In-Tok'] + row['Out-Tok'])) / row['MaxKvcache']


def model_b_cache_size(row, alpha):
    """Model B: cache = N × (IL + α×OL)"""
    return (row['MaxRun'] * (row['In-Tok'] + alpha * row['Out-Tok'])) / row['MaxKvcache']


def model_c_cache_size(row):
    """Model C: cache = N × (IL + 0.5×OL)"""
    return (row['MaxRun'] * (row['In-Tok'] + 0.5 * row['Out-Tok'])) / row['MaxKvcache']


def evaluate_model(df, model_func, alpha=None):
    """Evaluate a model's fit."""
    if alpha is not None:
        cache_sizes = df.apply(lambda row: model_func(row, alpha), axis=1)
    else:
        cache_sizes = df.apply(model_func, axis=1)
    
    median = cache_sizes.median()
    mean = cache_sizes.mean()
    std = cache_sizes.std()
    cv = std / mean  # Coefficient of variation (lower is better)
    
    return {
        'median': median,
        'mean': mean,
        'std': std,
        'cv': cv,
        'cache_sizes': cache_sizes
    }


def find_optimal_alpha(df):
    """Find optimal alpha for Model B using grid search."""
    
    # Grid search from 0 to 1 with 0.01 step
    alphas = np.arange(0.0, 1.01, 0.01)
    best_alpha = 0.5
    best_cv = float('inf')
    
    for alpha in alphas:
        result = evaluate_model(df, model_b_cache_size, alpha)
        if result['cv'] < best_cv:
            best_cv = result['cv']
            best_alpha = alpha
    
    return best_alpha


def predict_n_max(input_tokens, output_tokens, cache_size, alpha, target_kv_pct=0.80):
    """Predict N_max using Model B."""
    effective_tokens = input_tokens + alpha * output_tokens
    n_max = (target_kv_pct * cache_size) / effective_tokens
    return n_max


def validate_predictions(df, cache_size, alpha, model_name):
    """Validate predictions against actual measurements."""
    df = df.copy()
    
    df['predicted_N_max'] = df.apply(
        lambda row: predict_n_max(
            row['In-Tok'],
            row['Out-Tok'],
            cache_size,
            alpha,
            row['MaxKvcache']
        ),
        axis=1
    )
    
    df['error'] = df['predicted_N_max'] - df['MaxRun']
    df['error_pct'] = (df['error'] / df['MaxRun']) * 100
    
    mae = df['error'].abs().mean()
    mape = df['error_pct'].abs().mean()
    rmse = np.sqrt((df['error']**2).mean())
    
    return {
        'model': model_name,
        'mae': mae,
        'mape': mape,
        'rmse': rmse,
        'predictions': df
    }


def main():
    # Get CSV path
    if len(sys.argv) > 1:
        csv_path = Path(__file__).parent / sys.argv[1]
    else:
        csv_path = Path(__file__).parent / 'DTA-AVG-H100_BS-65000__summary_903.csv'
    
    print("="*80)
    print("KV CACHE MODEL COMPARISON")
    print("="*80)
    print(f"Dataset: {csv_path.name}")
    print("Using only non-saturated measurements (KV < 80%)\n")
    
    df = load_data(csv_path)
    print(f"Loaded {len(df)} non-saturated measurements\n")
    
    # Evaluate Model A: IL + OL
    print("="*80)
    print("MODEL A: cache_usage = N × (IL + OL)")
    print("="*80)
    result_a = evaluate_model(df, model_a_cache_size)
    print(f"Estimated cache size: {result_a['median']:,.0f} tokens (median)")
    print(f"Mean: {result_a['mean']:,.0f} tokens")
    print(f"Std deviation: {result_a['std']:,.0f} tokens")
    print(f"Coefficient of variation: {result_a['cv']:.4f}")
    
    # Evaluate Model C: IL + 0.5×OL
    print("\n" + "="*80)
    print("MODEL C: cache_usage = N × (IL + 0.5×OL)")
    print("="*80)
    result_c = evaluate_model(df, model_c_cache_size)
    print(f"Estimated cache size: {result_c['median']:,.0f} tokens (median)")
    print(f"Mean: {result_c['mean']:,.0f} tokens")
    print(f"Std deviation: {result_c['std']:,.0f} tokens")
    print(f"Coefficient of variation: {result_c['cv']:.4f}")
    
    # Find optimal alpha for Model B
    print("\n" + "="*80)
    print("MODEL B: cache_usage = N × (IL + α×OL) - OPTIMIZED")
    print("="*80)
    print("Finding optimal α...")
    optimal_alpha = find_optimal_alpha(df)
    print(f"Optimal α = {optimal_alpha:.4f}")
    
    result_b = evaluate_model(df, model_b_cache_size, optimal_alpha)
    print(f"\nEstimated cache size: {result_b['median']:,.0f} tokens (median)")
    print(f"Mean: {result_b['mean']:,.0f} tokens")
    print(f"Std deviation: {result_b['std']:,.0f} tokens")
    print(f"Coefficient of variation: {result_b['cv']:.4f}")
    
    # Compare models
    print("\n" + "="*80)
    print("MODEL COMPARISON SUMMARY")
    print("="*80)
    print(f"{'Model':<30} {'Cache Size':>15} {'Std Dev':>12} {'CV':>10}")
    print(f"{'-'*30} {'-'*15} {'-'*12} {'-'*10}")
    print(f"{'A: IL + OL':<30} {result_a['median']:>15,.0f} {result_a['std']:>12,.0f} {result_a['cv']:>10.4f}")
    print(f"{'C: IL + 0.5×OL':<30} {result_c['median']:>15,.0f} {result_c['std']:>12,.0f} {result_c['cv']:>10.4f}")
    print(f"{'B: IL + {:.4f}×OL'.format(optimal_alpha):<30} {result_b['median']:>15,.0f} {result_b['std']:>12,.0f} {result_b['cv']:>10.4f}")
    
    # Determine best model
    best_model = min(
        [('A', result_a['cv']), ('C', result_c['cv']), ('B', result_b['cv'])],
        key=lambda x: x[1]
    )
    
    print(f"\n✅ Best model: {best_model[0]} (lowest coefficient of variation)")
    
    # Validate predictions
    print("\n" + "="*80)
    print("PREDICTION ACCURACY VALIDATION")
    print("="*80)
    
    val_a = validate_predictions(df, result_a['median'], 1.0, "Model A")
    val_c = validate_predictions(df, result_c['median'], 0.5, "Model C")
    val_b = validate_predictions(df, result_b['median'], optimal_alpha, "Model B")
    
    print(f"{'Model':<30} {'MAE':>10} {'MAPE':>10} {'RMSE':>10}")
    print(f"{'-'*30} {'-'*10} {'-'*10} {'-'*10}")
    print(f"{val_a['model']:<30} {val_a['mae']:>10.2f} {val_a['mape']:>9.1f}% {val_a['rmse']:>10.2f}")
    print(f"{val_c['model']:<30} {val_c['mae']:>10.2f} {val_c['mape']:>9.1f}% {val_c['rmse']:>10.2f}")
    print(f"{val_b['model']:<30} {val_b['mae']:>10.2f} {val_b['mape']:>9.1f}% {val_b['rmse']:>10.2f}")
    
    best_pred = min([val_a, val_c, val_b], key=lambda x: x['mae'])
    print(f"\n✅ Most accurate predictions: {best_pred['model']}")
    
    # Show example predictions
    print("\n" + "="*80)
    print("EXAMPLE PREDICTIONS AT 80% KV CACHE")
    print("="*80)
    
    examples = [
        (5000, 300),
        (5000, 1000),
        (8000, 300),
        (10000, 300),
        (5000, 1500)
    ]
    
    print(f"\n{'Input':>8} {'Output':>8} {'Model A':>10} {'Model C':>10} {'Model B':>10}")
    print(f"{'-'*8} {'-'*8} {'-'*10} {'-'*10} {'-'*10}")
    
    for in_tok, out_tok in examples:
        n_a = predict_n_max(in_tok, out_tok, result_a['median'], 1.0, 0.80)
        n_c = predict_n_max(in_tok, out_tok, result_c['median'], 0.5, 0.80)
        n_b = predict_n_max(in_tok, out_tok, result_b['median'], optimal_alpha, 0.80)
        print(f"{in_tok:>8} {out_tok:>8} {n_a:>10.0f} {n_c:>10.0f} {n_b:>10.0f}")
    
    # Recommendation
    print("\n" + "="*80)
    print("RECOMMENDATION")
    print("="*80)
    
    if best_model[0] == 'C' or abs(optimal_alpha - 0.5) < 0.1:
        print("✅ Use Model C: N_max = (target_KV% × cache_size) / (IL + 0.5×OL)")
        print(f"   Cache size: {result_c['median']:,.0f} tokens")
        print(f"   Rationale: Output tokens have ~50% weight in KV cache")
        recommended_alpha = 0.5
        recommended_cache = result_c['median']
    elif best_model[0] == 'B':
        print(f"✅ Use Model B: N_max = (target_KV% × cache_size) / (IL + {optimal_alpha:.4f}×OL)")
        print(f"   Cache size: {result_b['median']:,.0f} tokens")
        print(f"   Rationale: Optimized α = {optimal_alpha:.4f} provides best fit")
        recommended_alpha = optimal_alpha
        recommended_cache = result_b['median']
    else:
        print("✅ Use Model A: N_max = (target_KV% × cache_size) / (IL + OL)")
        print(f"   Cache size: {result_a['median']:,.0f} tokens")
        print(f"   Rationale: Simple model with good accuracy")
        recommended_alpha = 1.0
        recommended_cache = result_a['median']
    
    # Generate updated predictor
    print("\n" + "="*80)
    print("GENERATING UPDATED PREDICTOR")
    print("="*80)
    
    predictor_code = f'''"""Auto-generated N_max prediction function - Optimized Model."""
import numpy as np

def predict_n_max_runtime(input_tokens, output_tokens, target_kv_pct=0.75):
    """
    Predict maximum concurrent requests for given workload.
    
    Uses optimized model: N_max = (target_KV% × cache_size) / (IL + α×OL)
    where α = {recommended_alpha:.4f}
    
    Args:
        input_tokens: Average input tokens per request
        output_tokens: Average output tokens per request
        target_kv_pct: Target KV cache utilization (default: 0.75 for safety)
    
    Returns:
        n_max: Maximum concurrent requests at target utilization
    """
    # Estimated cache size from H100 measurements (non-saturated data)
    CACHE_SIZE = {recommended_cache:.0f}  # tokens
    ALPHA = {recommended_alpha:.4f}  # Output token weight
    
    # Calculate effective tokens per request
    effective_tokens = input_tokens + ALPHA * output_tokens
    
    # Calculate N_max
    n_max = (target_kv_pct * CACHE_SIZE) / effective_tokens
    
    return int(n_max)


# Example usage:
# For 5000 input, 300 output tokens at 75% target:
# n_max = predict_n_max_runtime(5000, 300, 0.75)
# Result: {int(predict_n_max(5000, 300, recommended_cache, recommended_alpha, 0.75))} concurrent requests

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
    
    output_file = Path(__file__).parent / 'n_max_predictor_optimized.py'
    with open(output_file, 'w') as f:
        f.write(predictor_code)
    
    print(f"✅ Optimized predictor saved to: {output_file}")
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

# Made with Bob
