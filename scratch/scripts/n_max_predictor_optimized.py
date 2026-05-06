"""Auto-generated N_max prediction function - Optimized Model."""
import numpy as np

def predict_n_max_runtime(input_tokens, output_tokens, target_kv_pct=0.75):
    """
    Predict maximum concurrent requests for given workload.
    
    Uses optimized model: N_max = (target_KV% × cache_size) / (IL + α×OL)
    where α = 0.5000
    
    Args:
        input_tokens: Average input tokens per request
        output_tokens: Average output tokens per request
        target_kv_pct: Target KV cache utilization (default: 0.75 for safety)
    
    Returns:
        n_max: Maximum concurrent requests at target utilization
    """
    # Estimated cache size from H100 measurements (non-saturated data)
    CACHE_SIZE = 386783  # tokens
    ALPHA = 0.5000  # Output token weight
    
    # Calculate effective tokens per request
    effective_tokens = input_tokens + ALPHA * output_tokens
    
    # Calculate N_max
    n_max = (target_kv_pct * CACHE_SIZE) / effective_tokens
    
    return int(n_max)


# Example usage:
# For 5000 input, 300 output tokens at 75% target:
# n_max = predict_n_max_runtime(5000, 300, 0.75)
# Result: 56 concurrent requests

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
        return (True, f"KV cache at {current_kv_pct*100:.1f}%", instances_needed)
    
    if current_n >= n_max_75 * 0.85:
        instances_needed = int(np.ceil(current_n / (n_max_75 * 0.70)))
        return (True, f"Concurrency at {current_n}/{n_max_75} ({current_n/n_max_75*100:.1f}%)", instances_needed)
    
    return (False, "Within safe operating range", 1)
