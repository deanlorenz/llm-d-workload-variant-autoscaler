#!/usr/bin/env python3
"""
Plot GPS ITL curve data showing relationships between:
- A (MaxRun/concurrent requests)
- GPS (Generations Per Second - throughput)
- ITL (Inter-Token Latency)

Generates three plots:
1. GPS vs A (throughput scaling)
2. ITL vs A (latency under load)
3. GPS vs ITL (throughput-latency trade-off)
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
    
    # Add statistics
    max_gps = df['GPS'].max()
    max_gps_a = df.loc[df['GPS'].idxmax(), 'A']
    ax.text(0.02, 0.98, f'Max GPS: {max_gps:.0f} @ A={max_gps_a:.0f}',
            transform=ax.transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))


def plot_itl_vs_a(df, ax):
    """Plot ITL (latency) vs A (concurrent requests)."""
    sizes = 50 + 100 * (df['n'] / df['n'].max())
    ax.scatter(df['A'], df['ITL'], s=sizes, alpha=0.6, c='red', edgecolors='black', linewidth=0.5)
    ax.plot(df['A'], df['ITL'], 'r-', alpha=0.3, linewidth=1)
    ax.set_xlabel('A (Concurrent Requests)', fontsize=11)
    ax.set_ylabel('ITL (Inter-Token Latency, seconds)', fontsize=11)
    ax.set_title('Inter-Token Latency vs Concurrent Requests', fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3)
    
    # Add statistics
    min_itl = df['ITL'].min()
    min_itl_a = df.loc[df['ITL'].idxmin(), 'A']
    ax.text(0.02, 0.98, f'Min ITL: {min_itl:.4f}s @ A={min_itl_a:.0f}',
            transform=ax.transAxes, fontsize=9, verticalalignment='top',
            bbox=dict(boxstyle='round', facecolor='wheat', alpha=0.5))


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
    
    # Add note about point sizes
    ax.text(0.02, 0.02, 'Point size ∝ sample count (n)',
            transform=ax.transAxes, fontsize=8, verticalalignment='bottom',
            bbox=dict(boxstyle='round', facecolor='lightgray', alpha=0.5))


def print_summary_stats(df):
    """Print summary statistics of the data."""
    print("\n" + "="*60)
    print("GPS ITL Curve Summary Statistics")
    print("="*60)
    print(f"\nData points: {len(df)}")
    print(f"Total samples: {df['n'].sum()}")
    print(f"\nConcurrent Requests (A):")
    print(f"  Range: {df['A'].min():.0f} - {df['A'].max():.0f}")
    print(f"  Mean: {df['A'].mean():.1f}")
    print(f"\nGenerations Per Second (GPS):")
    print(f"  Range: {df['GPS'].min():.0f} - {df['GPS'].max():.0f}")
    print(f"  Mean: {df['GPS'].mean():.1f}")
    print(f"  Max: {df['GPS'].max():.0f} @ A={df.loc[df['GPS'].idxmax(), 'A']:.0f}")
    print(f"\nInter-Token Latency (ITL):")
    print(f"  Range: {df['ITL'].min():.4f}s - {df['ITL'].max():.4f}s")
    print(f"  Mean: {df['ITL'].mean():.4f}s")
    print(f"  Min: {df['ITL'].min():.4f}s @ A={df.loc[df['ITL'].idxmin(), 'A']:.0f}")
    print("="*60 + "\n")


def main():
    # Load data
    csv_path = Path(__file__).parent / 'gps_itl_curve.csv'
    if not csv_path.exists():
        print(f"Error: CSV file not found at {csv_path}")
        return
    
    df = load_data(csv_path)
    
    # Sort by A for better line plots
    df = df.sort_values('A')
    
    # Print summary statistics
    print_summary_stats(df)
    
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

# Made with Bob
