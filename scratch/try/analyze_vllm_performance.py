#!/usr/bin/env python3
"""
vLLM Performance Analysis Script

Based on the discussion in chatgpt-current-1776362574645.md, this script:
1. Estimates max λ (RPS) for each experiment configuration
2. Calculates the number of vLLM instances needed to support future loads

Key concepts from the discussion:
- ITL(k) ≈ X + Y*k (Inter-Token Latency as function of KV cache utilization)
- TTFT(k) ≈ Z*IL*k (Time To First Token as function of KV cache utilization)
- System becomes unstable when TTFT(k)/ITL(k) ≈ √OL (prefill-dominated regime)
- λ_max is determined by the k* where this crossover occurs
"""

import pandas as pd
import numpy as np
from scipy import stats
from scipy.optimize import fsolve
import matplotlib.pyplot as plt
from typing import Dict, Tuple, List
import warnings
warnings.filterwarnings('ignore')


class VLLMPerformanceAnalyzer:
    """Analyzes vLLM performance data to estimate max RPS and instance requirements."""
    
    def __init__(self, csv_path: str, kv_max: float = 1.0):
        """
        Initialize the analyzer.
        
        Args:
            csv_path: Path to the CSV data file
            kv_max: Maximum KV cache utilization (default 1.0 = 100%)
        """
        self.df = pd.read_csv(csv_path)
        self.kv_max = kv_max
        self._clean_data()
        
    def _clean_data(self):
        """Clean and prepare the data."""
        # Remove leading/trailing spaces from column names
        self.df.columns = self.df.columns.str.strip()
        
        # Rename columns for easier access
        column_mapping = {
            'In-Tok': 'IL',
            'Out-Tok': 'OL', 
            'RPS': 'RPS',
            'test-name': 'experiment',
            'TTFT': 'TTFT',
            'Prefill': 'Prefill',
            'ITL': 'ITL',
            'E2E': 'E2E',
            'Run': 'N',
            'MaxRun': 'MaxN',
            'Kvcache': 'k',
            'MaxKvcache': 'MaxK'
        }
        
        for old_name, new_name in column_mapping.items():
            if old_name in self.df.columns:
                self.df[new_name] = self.df[old_name]
        
        # Convert to numeric, handling any errors
        numeric_cols = ['IL', 'OL', 'RPS', 'TTFT', 'Prefill', 'ITL', 'E2E', 'N', 'MaxN', 'k', 'MaxK']
        for col in numeric_cols:
            if col in self.df.columns:
                self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Filter out saturated/unstable data (where k > 0.85 or E2E is very high)
        self.df['is_stable'] = (self.df['k'] < 0.85) & (self.df['E2E'] < self.df['E2E'].quantile(0.9))
        
    def get_experiments(self) -> List[str]:
        """Get list of unique experiments."""
        return sorted(self.df['experiment'].unique())
    
    def get_experiment_data(self, experiment: str, stable_only: bool = True) -> pd.DataFrame:
        """Get data for a specific experiment."""
        exp_data = self.df[self.df['experiment'] == experiment].copy()
        if stable_only:
            exp_data = exp_data[exp_data['is_stable']]
        return exp_data.sort_values('RPS')
    
    def fit_itl_model(self, data: pd.DataFrame) -> Tuple[float, float, float]:
        """
        Fit ITL(k) ≈ X + Y*k model.
        
        Returns:
            (X, Y, r_squared): Intercept, slope, and R² of the fit
        """
        if len(data) < 3:
            return np.nan, np.nan, np.nan
        
        valid_data = data[['k', 'ITL']].dropna()
        if len(valid_data) < 3:
            return np.nan, np.nan, np.nan
        
        slope, intercept, r_value, _, _ = stats.linregress(valid_data['k'], valid_data['ITL'])
        return intercept, slope, r_value**2
    
    def fit_ttft_model(self, data: pd.DataFrame) -> Tuple[float, float]:
        """
        Fit TTFT(k) ≈ Z*IL*k model.
        
        Returns:
            (Z, r_squared): Coefficient and R² of the fit
        """
        if len(data) < 3:
            return np.nan, np.nan
        
        valid_data = data[['k', 'TTFT', 'IL']].dropna()
        if len(valid_data) < 3:
            return np.nan, np.nan
        
        # TTFT = Z * IL * k, so Z = TTFT / (IL * k)
        valid_data = valid_data[valid_data['k'] > 0.01]  # Avoid division by zero
        valid_data['Z_estimate'] = valid_data['TTFT'] / (valid_data['IL'] * valid_data['k'])
        
        Z = valid_data['Z_estimate'].median()
        
        # Calculate R² for the fit
        predicted = Z * valid_data['IL'] * valid_data['k']
        ss_res = np.sum((valid_data['TTFT'] - predicted)**2)
        ss_tot = np.sum((valid_data['TTFT'] - valid_data['TTFT'].mean())**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return Z, r_squared
    
    def estimate_lambda_max(self, experiment: str, target_k: float = 0.8) -> Dict:
        """
        Estimate maximum sustainable RPS (λ_max) for an experiment.
        
        Strategy:
        1. Fit ITL(k) and TTFT(k) from unsaturated data
        2. Find k* where TTFT(k)/ITL(k) ≈ √OL (prefill instability threshold)
        3. Calculate λ(k*) using Little's Law and KV constraints
        
        Args:
            experiment: Experiment name
            target_k: Target KV utilization for capacity planning (default 0.8)
            
        Returns:
            Dictionary with analysis results
        """
        data = self.get_experiment_data(experiment, stable_only=True)
        
        if len(data) == 0:
            return {'error': 'No stable data available'}
        
        # Get experiment parameters
        IL = data['IL'].iloc[0]
        OL = data['OL'].iloc[0]
        
        # Fit models
        X, Y, itl_r2 = self.fit_itl_model(data)
        Z, ttft_r2 = self.fit_ttft_model(data)
        
        if np.isnan(X) or np.isnan(Y) or np.isnan(Z):
            return {'error': 'Insufficient data for model fitting'}
        
        # Calculate the prefill instability threshold
        sqrt_OL = np.sqrt(OL)
        
        # Find k* where TTFT(k)/ITL(k) ≈ √OL
        # TTFT(k) = Z*IL*k
        # ITL(k) = X + Y*k
        # Solve: (Z*IL*k) / (X + Y*k) = √OL
        
        def ratio_equation(k):
            ttft = Z * IL * k
            itl = X + Y * k
            return (ttft / itl) - sqrt_OL if itl > 0 else np.inf
        
        # Try to find k* in range [0.1, 0.95]
        try:
            k_star = fsolve(ratio_equation, 0.5)[0]
            k_star = np.clip(k_star, 0.1, 0.95)
        except:
            k_star = target_k
        
        # Calculate λ at k*
        # From Little's Law: N ≈ λ * OL * ITL(k)
        # From KV constraint: k ≈ N * (IL + 0.5*OL) / KV_max
        # Combining: λ(k) = k * KV_max / (OL * (IL + 0.5*OL) * ITL(k))
        
        ITL_at_k_star = X + Y * k_star
        lambda_max_theory = (k_star * self.kv_max) / (OL * (IL + 0.5 * OL) * ITL_at_k_star)
        
        # Also calculate λ at target_k for comparison
        ITL_at_target = X + Y * target_k
        lambda_at_target = (target_k * self.kv_max) / (OL * (IL + 0.5 * OL) * ITL_at_target)
        
        # Get observed max RPS from data
        observed_max_rps = data['RPS'].max()
        
        # Calculate the ratio at different k values to understand the regime
        data_with_ratio = data.copy()
        data_with_ratio['ratio'] = data_with_ratio['TTFT'] / data_with_ratio['ITL']
        
        # Determine regime
        avg_ratio = data_with_ratio['ratio'].mean()
        if avg_ratio < sqrt_OL * 0.5:
            regime = 'decode-dominated'
        elif avg_ratio < sqrt_OL * 1.5:
            regime = 'crossover'
        else:
            regime = 'prefill-dominated'
        
        return {
            'experiment': experiment,
            'IL': IL,
            'OL': OL,
            'sqrt_OL': sqrt_OL,
            'ITL_model': {'X': X, 'Y': Y, 'r_squared': itl_r2},
            'TTFT_model': {'Z': Z, 'r_squared': ttft_r2},
            'k_star': k_star,
            'ITL_at_k_star': ITL_at_k_star,
            'lambda_max_theory': lambda_max_theory,
            'lambda_at_target_k': lambda_at_target,
            'target_k': target_k,
            'observed_max_rps': observed_max_rps,
            'regime': regime,
            'avg_ratio': avg_ratio,
            'n_stable_points': len(data)
        }
    
    def estimate_instances_needed(self, experiment: str, target_IL: float, 
                                  target_OL: float, target_RPS: float,
                                  safety_factor: float = 1.2) -> Dict:
        """
        Estimate number of vLLM instances needed for a target workload.
        
        Args:
            experiment: Base experiment to use for estimation
            target_IL: Target input length
            target_OL: Target output length
            target_RPS: Target requests per second
            safety_factor: Safety margin (default 1.2 = 20% overhead)
            
        Returns:
            Dictionary with instance count and analysis
        """
        # Get lambda_max for the base experiment
        analysis = self.estimate_lambda_max(experiment)
        
        if 'error' in analysis:
            return analysis
        
        base_IL = analysis['IL']
        base_OL = analysis['OL']
        base_lambda_max = analysis['lambda_max_theory']
        
        # Adjust lambda_max for different IL/OL
        # From the model: λ_max ∝ 1/(OL * (IL + 0.5*OL))
        # And ITL depends on k, which depends on (IL + 0.5*OL)
        
        # Simplified scaling (assumes similar k regime)
        workload_factor = (base_OL * (base_IL + 0.5 * base_OL)) / \
                         (target_OL * (target_IL + 0.5 * target_OL))
        
        adjusted_lambda_max = base_lambda_max * workload_factor
        
        # Calculate instances needed
        instances_needed = np.ceil(target_RPS / adjusted_lambda_max * safety_factor)
        
        # Calculate per-instance load
        rps_per_instance = target_RPS / instances_needed
        utilization = rps_per_instance / adjusted_lambda_max
        
        return {
            'experiment': experiment,
            'base_IL': base_IL,
            'base_OL': base_OL,
            'base_lambda_max': base_lambda_max,
            'target_IL': target_IL,
            'target_OL': target_OL,
            'target_RPS': target_RPS,
            'adjusted_lambda_max': adjusted_lambda_max,
            'safety_factor': safety_factor,
            'instances_needed': int(instances_needed),
            'rps_per_instance': rps_per_instance,
            'utilization': utilization,
            'headroom': 1 - utilization
        }
    
    def analyze_all_experiments(self) -> pd.DataFrame:
        """Analyze all experiments and return summary DataFrame."""
        results = []
        
        for exp in self.get_experiments():
            analysis = self.estimate_lambda_max(exp)
            if 'error' not in analysis:
                results.append(analysis)
        
        return pd.DataFrame(results)
    
    def plot_experiment_analysis(self, experiment: str, save_path: str = None):
        """Create visualization of experiment analysis."""
        data = self.get_experiment_data(experiment, stable_only=False)
        stable_data = data[data['is_stable']]
        analysis = self.estimate_lambda_max(experiment)
        
        if 'error' in analysis:
            print(f"Cannot plot {experiment}: {analysis['error']}")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        fig.suptitle(f'vLLM Performance Analysis: {experiment}', fontsize=16)
        
        # Plot 1: ITL vs k
        ax = axes[0, 0]
        ax.scatter(stable_data['k'], stable_data['ITL'], alpha=0.6, label='Stable data')
        ax.scatter(data[~data['is_stable']]['k'], data[~data['is_stable']]['ITL'], 
                  alpha=0.3, color='red', label='Unstable data')
        
        X, Y = analysis['ITL_model']['X'], analysis['ITL_model']['Y']
        k_range = np.linspace(0, 1, 100)
        ax.plot(k_range, X + Y * k_range, 'g--', label=f'Fit: ITL = {X:.4f} + {Y:.4f}*k')
        ax.axvline(analysis['k_star'], color='orange', linestyle=':', label=f'k* = {analysis["k_star"]:.3f}')
        ax.set_xlabel('KV Cache Utilization (k)')
        ax.set_ylabel('ITL (seconds)')
        ax.set_title('Inter-Token Latency vs KV Utilization')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Plot 2: TTFT vs k
        ax = axes[0, 1]
        ax.scatter(stable_data['k'], stable_data['TTFT'], alpha=0.6, label='Stable data')
        ax.scatter(data[~data['is_stable']]['k'], data[~data['is_stable']]['TTFT'],
                  alpha=0.3, color='red', label='Unstable data')
        
        Z = analysis['TTFT_model']['Z']
        IL = analysis['IL']
        ax.plot(k_range, Z * IL * k_range, 'g--', label=f'Fit: TTFT = {Z:.6f}*IL*k')
        ax.axvline(analysis['k_star'], color='orange', linestyle=':', label=f'k* = {analysis["k_star"]:.3f}')
        ax.set_xlabel('KV Cache Utilization (k)')
        ax.set_ylabel('TTFT (seconds)')
        ax.set_title('Time To First Token vs KV Utilization')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Plot 3: TTFT/ITL ratio vs k
        ax = axes[1, 0]
        stable_data_copy = stable_data.copy()
        stable_data_copy['ratio'] = stable_data_copy['TTFT'] / stable_data_copy['ITL']
        ax.scatter(stable_data_copy['k'], stable_data_copy['ratio'], alpha=0.6, label='Observed ratio')
        
        ratio_fit = (Z * IL * k_range) / (X + Y * k_range)
        ax.plot(k_range, ratio_fit, 'g--', label='Model ratio')
        ax.axhline(analysis['sqrt_OL'], color='red', linestyle='--', label=f'√OL = {analysis["sqrt_OL"]:.2f}')
        ax.axvline(analysis['k_star'], color='orange', linestyle=':', label=f'k* = {analysis["k_star"]:.3f}')
        ax.set_xlabel('KV Cache Utilization (k)')
        ax.set_ylabel('TTFT / ITL')
        ax.set_title(f'Prefill/Decode Ratio (Regime: {analysis["regime"]})')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        # Plot 4: RPS vs k
        ax = axes[1, 1]
        ax.scatter(stable_data['k'], stable_data['RPS'], alpha=0.6, label='Stable data')
        ax.scatter(data[~data['is_stable']]['k'], data[~data['is_stable']]['RPS'],
                  alpha=0.3, color='red', label='Unstable data')
        ax.axvline(analysis['k_star'], color='orange', linestyle=':', label=f'k* = {analysis["k_star"]:.3f}')
        ax.axhline(analysis['lambda_max_theory'], color='green', linestyle='--', 
                  label=f'λ_max (theory) = {analysis["lambda_max_theory"]:.2f}')
        ax.axhline(analysis['observed_max_rps'], color='blue', linestyle=':', 
                  label=f'Observed max = {analysis["observed_max_rps"]:.2f}')
        ax.set_xlabel('KV Cache Utilization (k)')
        ax.set_ylabel('RPS')
        ax.set_title('Request Rate vs KV Utilization')
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"Plot saved to {save_path}")
        else:
            plt.show()


def main():
    """Main analysis function."""
    print("=" * 80)
    print("vLLM Performance Analysis")
    print("=" * 80)
    
    # Initialize analyzer
    analyzer = VLLMPerformanceAnalyzer('WVA_data160426_short.csv')
    
    print(f"\nLoaded {len(analyzer.df)} data points")
    print(f"Found {len(analyzer.get_experiments())} unique experiments")
    
    # Analyze all experiments
    print("\n" + "=" * 80)
    print("ANALYSIS: Maximum Sustainable RPS (λ_max) per Experiment")
    print("=" * 80)
    
    results_df = analyzer.analyze_all_experiments()
    
    # Display summary
    summary_cols = ['experiment', 'IL', 'OL', 'sqrt_OL', 'k_star', 
                   'lambda_max_theory', 'observed_max_rps', 'regime', 'n_stable_points']
    
    print("\nSummary Table:")
    print(results_df[summary_cols].to_string(index=False))
    
    # Save detailed results
    results_df.to_csv('vllm_analysis_results.csv', index=False)
    print("\nDetailed results saved to: vllm_analysis_results.csv")
    
    # Example: Estimate instances needed for specific workloads
    print("\n" + "=" * 80)
    print("EXAMPLE: Instance Count Estimation")
    print("=" * 80)
    
    # Example 1: Scale up from 5K_500 experiment
    example_exp = '5K_500'
    if example_exp in analyzer.get_experiments():
        print(f"\nBase experiment: {example_exp}")
        
        scenarios = [
            {'IL': 5000, 'OL': 500, 'RPS': 5.0, 'desc': 'Same as base'},
            {'IL': 5000, 'OL': 1000, 'RPS': 5.0, 'desc': 'Double output length'},
            {'IL': 10000, 'OL': 500, 'RPS': 5.0, 'desc': 'Double input length'},
            {'IL': 5000, 'OL': 500, 'RPS': 10.0, 'desc': 'Double RPS'},
        ]
        
        for scenario in scenarios:
            result = analyzer.estimate_instances_needed(
                example_exp, 
                scenario['IL'], 
                scenario['OL'], 
                scenario['RPS']
            )
            
            if 'error' not in result:
                print(f"\nScenario: {scenario['desc']}")
                print(f"  Target: IL={scenario['IL']}, OL={scenario['OL']}, RPS={scenario['RPS']}")
                print(f"  Instances needed: {result['instances_needed']}")
                print(f"  RPS per instance: {result['rps_per_instance']:.2f}")
                print(f"  Utilization: {result['utilization']:.1%}")
                print(f"  Headroom: {result['headroom']:.1%}")
    
    # Generate plots for a few key experiments
    print("\n" + "=" * 80)
    print("Generating visualizations...")
    print("=" * 80)
    
    key_experiments = ['5K_500', '5K_200', '6K_100']
    for exp in key_experiments:
        if exp in analyzer.get_experiments():
            print(f"\nGenerating plot for {exp}...")
            analyzer.plot_experiment_analysis(exp, save_path=f'analysis_{exp}.png')
    
    print("\n" + "=" * 80)
    print("Analysis complete!")
    print("=" * 80)


if __name__ == '__main__':
    main()

# Made with Bob
