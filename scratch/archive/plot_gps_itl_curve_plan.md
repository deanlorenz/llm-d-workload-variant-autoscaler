# GPS ITL Curve Plotting Plan

## Overview
Create visualizations for the GPS (Generations Per Second) vs ITL (Inter-Token Latency) curve data from [`gps_itl_curve.csv`](gps_itl_curve.csv).

## Data Structure
The CSV contains:
- **A**: MaxRun (concurrent requests/batch size)
- **GPS**: Generations Per Second (throughput metric)
- **ITL**: Inter-Token Latency (seconds per token)
- **n**: Number of samples aggregated for this data point

## Visualization Requirements

### Plot 1: GPS vs A (Throughput Scaling)
- **X-axis**: A (concurrent requests)
- **Y-axis**: GPS (Generations Per Second)
- **Purpose**: Show how throughput scales with concurrency
- **Features**:
  - Scatter plot with line connecting points
  - Point size proportional to `n` (sample count)
  - Grid for readability
  - Title: "Throughput vs Concurrent Requests"

### Plot 2: ITL vs A (Latency Under Load)
- **X-axis**: A (concurrent requests)
- **Y-axis**: ITL (Inter-Token Latency in seconds)
- **Purpose**: Show how latency changes with load
- **Features**:
  - Scatter plot with line connecting points
  - Point size proportional to `n` (sample count)
  - Grid for readability
  - Title: "Inter-Token Latency vs Concurrent Requests"

### Plot 3: GPS vs ITL (Throughput-Latency Trade-off)
- **X-axis**: ITL (Inter-Token Latency)
- **Y-axis**: GPS (Generations Per Second)
- **Color**: A (concurrent requests) - using colormap
- **Size**: Proportional to `n` (sample count)
- **Purpose**: Show the fundamental trade-off between throughput and latency
- **Features**:
  - Scatter plot with colorbar
  - Colormap showing A values
  - Size legend for sample counts
  - Grid for readability
  - Title: "Throughput vs Latency Trade-off"

## Implementation Details

### Script: `plot_gps_itl_curve.py`

```python
#!/usr/bin/env python3
"""
Plot GPS ITL curve data showing relationships between:
- A (MaxRun/concurrent requests)
- GPS (Generations Per Second - throughput)
- ITL (Inter-Token Latency)
"""

import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path

def load_data(csv_path):
    """Load and validate the GPS ITL curve data."""
    df = pd.read_csv(csv_path)
    required_cols = ['A', 'GPS', 'ITL', 'n']
    for col in required_cols:
        if col not in df.columns:
            raise ValueError(f"Missing required column: {col}")
    return df

def plot_gps_vs_a(df, ax):
    """Plot GPS (throughput) vs A (concurrent requests)."""
    sizes = 50 + 100 * (df['n'] / df['n'].max())
    ax.scatter(df['A'], df['GPS'], s=sizes, alpha=0.6, c='blue', edgecolors='black', linewidth=0.5)
    ax.plot(df['A'], df['GPS'], 'b-', alpha=0.3, linewidth=1)
    ax.set_xlabel('A (Concurrent Requests)', fontsize=11)
    ax.set_ylabel('GPS (Generations/Second)', fontsize=11)
    ax.set_title('Throughput vs Concurrent Requests', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

def plot_itl_vs_a(df, ax):
    """Plot ITL (latency) vs A (concurrent requests)."""
    sizes = 50 + 100 * (df['n'] / df['n'].max())
    ax.scatter(df['A'], df['ITL'], s=sizes, alpha=0.6, c='red', edgecolors='black', linewidth=0.5)
    ax.plot(df['A'], df['ITL'], 'r-', alpha=0.3, linewidth=1)
    ax.set_xlabel('A (Concurrent Requests)', fontsize=11)
    ax.set_ylabel('ITL (Inter-Token Latency, seconds)', fontsize=11)
    ax.set_title('Inter-Token Latency vs Concurrent Requests', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

def plot_gps_vs_itl(df, ax):
    """Plot GPS vs ITL with A as color."""
    sizes = 50 + 150 * (df['n'] / df['n'].max())
    scatter = ax.scatter(df['ITL'], df['GPS'], c=df['A'], s=sizes, 
                        cmap='viridis', alpha=0.7, edgecolors='black', linewidth=0.5)
    cbar = plt.colorbar(scatter, ax=ax)
    cbar.set_label('A (Concurrent Requests)', fontsize=10)
    ax.set_xlabel('ITL (Inter-Token Latency, seconds)', fontsize=11)
    ax.set_ylabel('GPS (Generations/Second)', fontsize=11)
    ax.set_title('Throughput vs Latency Trade-off', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)

def main():
    # Load data
    csv_path = Path(__file__).parent / 'gps_itl_curve.csv'
    df = load_data(csv_path)
    
    # Sort by A for better line plots
    df = df.sort_values('A')
    
    # Create figure with 3 subplots
    fig, axes = plt.subplots(1, 3, figsize=(18, 5))
    fig.suptitle('GPS ITL Curve Analysis', fontsize=14, fontweight='bold', y=1.02)
    
    # Generate plots
    plot_gps_vs_a(df, axes[0])
    plot_itl_vs_a(df, axes[1])
    plot_gps_vs_itl(df, axes[2])
    
    # Adjust layout
    plt.tight_layout()
    
    # Save figure
    output_path = Path(__file__).parent / 'gps_itl_curve_plots.png'
    plt.savefig(output_path, dpi=300, bbox_inches='tight')
    print(f"Plots saved to: {output_path}")
    
    # Show plots
    plt.show()

if __name__ == '__main__':
    main()
```

## Key Insights to Look For

1. **Throughput Scaling**: Does GPS increase linearly with A, or does it plateau?
2. **Latency Behavior**: How does ITL change as concurrency increases?
3. **Optimal Operating Point**: Where is the best balance between throughput and latency?
4. **Saturation Point**: At what A value does the system become saturated?

## Next Steps

1. Switch to Code mode to implement the plotting script
2. Run the script to generate visualizations
3. Analyze the results and document findings
4. Consider additional analyses if patterns emerge