#!/usr/bin/env python3
"""
vLLM Performance Analysis: Saturation Detection and Instance Estimation

This script analyzes vLLM performance data to:
1. Detect saturation points per experiment
2. Estimate maximum sustainable RPS
3. Calculate required vLLM instances for future loads

Based on the methodology from the technical discussion about vLLM performance bottlenecks.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class VLLMSaturationAnalyzer:
    """Analyzes vLLM performance data to detect saturation and estimate capacity."""
    
    def __init__(self, csv_path: str):
        """Load and prepare the data."""
        self.df = pd.read_csv(csv_path)
        # Clean column names (remove BOM and extra spaces)
        self.df.columns = self.df.columns.str.strip().str.replace('\ufeff', '')
        
        # Rename columns for easier access
        self.df.rename(columns={
            'In-Tok': 'IL',
            'Out-Tok': 'OL',
            'test-name': 'test_name'
        }, inplace=True)
        
        # Convert numeric columns
        numeric_cols = ['IL', 'OL', 'RPS', 'TTFT', 'ITL', 'E2E', 'Kvcache']
        for col in numeric_cols:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        # Remove rows with missing critical data
        self.df = self.df.dropna(subset=['IL', 'OL', 'RPS', 'TTFT', 'ITL', 'E2E', 'Kvcache'])
        
        print(f"Loaded {len(self.df)} valid data points")
        print(f"Experiments: {self.df['test_name'].unique()}")
    
    def compute_derived_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute derived metrics for analysis:
        - φ (phi): E2E / (OL × ITL) - queueing indicator
        - ρ (rho): TTFT / ITL - prefill pressure indicator
        - T_prefill: TTFT - ITL - actual prefill time
        """
        df = df.copy()
        
        # Compute phi: queueing indicator
        df['phi'] = df['E2E'] / (df['OL'] * df['ITL'])
        
        # Compute rho: prefill pressure indicator
        df['rho'] = df['TTFT'] / df['ITL']
        
        # Compute T_prefill
        df['T_prefill'] = df['TTFT'] - df['ITL']
        
        return df
    
    def estimate_ITL_at_k(self, df: pd.DataFrame, target_k: float = 0.8) -> Tuple[float, float]:
        """
        Estimate ITL(k) using linear extrapolation from non-saturated measurements.
        
        Returns: (estimated_ITL, confidence_score)
        """
        # Use only non-saturated points (phi < 1.1 as initial filter)
        non_sat = df[df['phi'] < 1.1].copy()
        
        if len(non_sat) < 2:
            # Not enough data, use all available
            non_sat = df.copy()
        
        # Fit linear model: ITL = a + b*k
        k = non_sat['Kvcache'].values
        itl = non_sat['ITL'].values
        
        if len(k) < 2:
            return itl[0] if len(itl) > 0 else np.nan, 0.0
        
        # Linear regression
        A = np.vstack([np.ones(len(k)), k]).T
        coeffs, residuals, rank, s = np.linalg.lstsq(A, itl, rcond=None)
        a, b = coeffs
        
        # Estimate at target k
        estimated_ITL = a + b * target_k
        
        # Confidence based on R²
        ss_res = np.sum((itl - (a + b*k))**2)
        ss_tot = np.sum((itl - np.mean(itl))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return estimated_ITL, r_squared
    
    def estimate_Tprefill_at_k(self, df: pd.DataFrame, target_k: float = 0.8) -> Tuple[float, float]:
        """
        Estimate T_prefill(k) using extrapolation from non-saturated measurements.
        
        Returns: (estimated_T_prefill, confidence_score)
        """
        # Use only non-saturated points
        non_sat = df[df['phi'] < 1.1].copy()
        
        if len(non_sat) < 2:
            non_sat = df.copy()
        
        # Fit linear model: T_prefill = a + b*k
        k = non_sat['Kvcache'].values
        t_pref = non_sat['T_prefill'].values
        
        if len(k) < 2:
            return t_pref[0] if len(t_pref) > 0 else np.nan, 0.0
        
        # Linear regression
        A = np.vstack([np.ones(len(k)), k]).T
        coeffs, residuals, rank, s = np.linalg.lstsq(A, t_pref, rcond=None)
        a, b = coeffs
        
        # Estimate at target k
        estimated_T_prefill = a + b * target_k
        
        # Confidence based on R²
        ss_res = np.sum((t_pref - (a + b*k))**2)
        ss_tot = np.sum((t_pref - np.mean(t_pref))**2)
        r_squared = 1 - (ss_res / ss_tot) if ss_tot > 0 else 0
        
        return estimated_T_prefill, r_squared
    
    def compute_derivatives(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Compute derivatives g = d(ITL)/dλ and h = dρ/dλ.
        Uses centered differences for interior points.
        """
        df = df.copy()
        df = df.sort_values('RPS').reset_index(drop=True)
        
        rps = df['RPS'].values
        itl = df['ITL'].values
        rho = df['rho'].values
        
        # Initialize with NaN
        g = np.full(len(df), np.nan)
        h = np.full(len(df), np.nan)
        
        # Compute derivatives using centered differences
        for i in range(len(df)):
            if i == 0:
                # Forward difference
                if len(df) > 1:
                    g[i] = (itl[i+1] - itl[i]) / (rps[i+1] - rps[i]) if rps[i+1] != rps[i] else 0
                    h[i] = (rho[i+1] - rho[i]) / (rps[i+1] - rps[i]) if rps[i+1] != rps[i] else 0
            elif i == len(df) - 1:
                # Backward difference
                g[i] = (itl[i] - itl[i-1]) / (rps[i] - rps[i-1]) if rps[i] != rps[i-1] else 0
                h[i] = (rho[i] - rho[i-1]) / (rps[i] - rps[i-1]) if rps[i] != rps[i-1] else 0
            else:
                # Centered difference
                g[i] = (itl[i+1] - itl[i-1]) / (rps[i+1] - rps[i-1]) if rps[i+1] != rps[i-1] else 0
                h[i] = (rho[i+1] - rho[i-1]) / (rps[i+1] - rps[i-1]) if rps[i+1] != rps[i-1] else 0
        
        df['g_dITL_dRPS'] = g
        df['h_drho_dRPS'] = h
        
        return df
    
    def detect_saturation(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Detect saturation using three conditions:
        1. Service degradation: g increases sharply (ITL convexity)
        2. Prefill interference: h > 0 and accelerating
        3. Queueing onset: φ > 1.1
        """
        df = df.copy()
        df = df.sort_values('RPS').reset_index(drop=True)
        
        # Compute second derivative of ITL (acceleration)
        g = df['g_dITL_dRPS'].values
        g_accel = np.full(len(df), np.nan)
        for i in range(1, len(df)):
            if not np.isnan(g[i]) and not np.isnan(g[i-1]):
                g_accel[i] = g[i] - g[i-1]
        df['g_acceleration'] = g_accel
        
        # Condition 1: ITL convexity (g increasing)
        df['cond1_service_degradation'] = (df['g_dITL_dRPS'] > 0) & (df['g_acceleration'] > 0)
        
        # Condition 2: Prefill interference (h > 0 and accelerating)
        h = df['h_drho_dRPS'].values
        h_accel = np.full(len(df), np.nan)
        for i in range(1, len(df)):
            if not np.isnan(h[i]) and not np.isnan(h[i-1]):
                h_accel[i] = h[i] - h[i-1]
        df['h_acceleration'] = h_accel
        df['cond2_prefill_interference'] = (df['h_drho_dRPS'] > 0) & (df['h_acceleration'] > 0)
        
        # Condition 3: Queueing onset
        df['cond3_queueing'] = df['phi'] > 1.1
        
        # Overall saturation: all three conditions met
        df['is_saturated'] = (
            df['cond1_service_degradation'] & 
            df['cond2_prefill_interference'] & 
            df['cond3_queueing']
        )
        
        return df
    
    def classify_regime(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Classify performance regime based on ρ and √OL:
        - Decode-limited: ρ << √OL (long output, high k)
        - Prefill-limited: ρ >> √OL (large input)
        - Scheduler/churn-limited: ρ ≈ √OL (short output, transition)
        """
        df = df.copy()
        
        df['sqrt_OL'] = np.sqrt(df['OL'])
        df['rho_ratio'] = df['rho'] / df['sqrt_OL']
        
        # Classification thresholds
        regime = []
        for _, row in df.iterrows():
            ratio = row['rho_ratio']
            if ratio < 0.5:
                regime.append('decode-limited')
            elif ratio > 2.0:
                regime.append('prefill-limited')
            else:
                regime.append('scheduler-limited')
        
        df['regime'] = regime
        
        return df
    
    def find_max_sustainable_rps(self, df: pd.DataFrame) -> Dict:
        """
        Find the maximum sustainable RPS before saturation.
        Returns detailed analysis including the saturation point.
        """
        df = df.sort_values('RPS').reset_index(drop=True)
        
        # Find first saturation point
        saturated = df[df['is_saturated'] == True]
        
        if len(saturated) > 0:
            sat_idx = saturated.index[0]
            if sat_idx > 0:
                # Last non-saturated point
                max_rps = df.loc[sat_idx - 1, 'RPS']
                max_rps_data = df.loc[sat_idx - 1].to_dict()
                sat_rps = df.loc[sat_idx, 'RPS']
                sat_data = df.loc[sat_idx].to_dict()
            else:
                # Saturated from the start
                max_rps = df.loc[0, 'RPS'] * 0.5  # Conservative estimate
                max_rps_data = df.loc[0].to_dict()
                sat_rps = df.loc[0, 'RPS']
                sat_data = df.loc[0].to_dict()
        else:
            # No saturation detected, use highest RPS
            max_rps = df['RPS'].max()
            max_rps_data = df.loc[df['RPS'].idxmax()].to_dict()
            sat_rps = None
            sat_data = None
        
        return {
            'max_sustainable_rps': max_rps,
            'max_rps_metrics': max_rps_data,
            'saturation_rps': sat_rps,
            'saturation_metrics': sat_data,
            'saturated_count': len(saturated),
            'total_points': len(df)
        }
    
    def estimate_instances_needed(self, experiment_data: pd.DataFrame, 
                                  target_il: int, target_ol: int, 
                                  target_rps: float) -> Dict:
        """
        Estimate number of vLLM instances needed for a target load.
        
        Uses the max sustainable RPS from the experiment and scales linearly.
        """
        # Get max sustainable RPS for this experiment
        max_info = self.find_max_sustainable_rps(experiment_data)
        max_rps = max_info['max_sustainable_rps']
        
        # Calculate instances needed
        if max_rps > 0:
            instances_needed = np.ceil(target_rps / max_rps)
        else:
            instances_needed = np.inf
        
        # Get the configuration from experiment
        exp_il = experiment_data['IL'].iloc[0]
        exp_ol = experiment_data['OL'].iloc[0]
        
        return {
            'target_IL': target_il,
            'target_OL': target_ol,
            'target_RPS': target_rps,
            'experiment_IL': exp_il,
            'experiment_OL': exp_ol,
            'max_sustainable_rps': max_rps,
            'instances_needed': int(instances_needed) if instances_needed != np.inf else 'N/A',
            'capacity_per_instance': max_rps,
            'total_capacity': instances_needed * max_rps if instances_needed != np.inf else 'N/A'
        }
    
    def analyze_experiment(self, test_name: str) -> Tuple[pd.DataFrame, Dict]:
        """
        Complete analysis for a single experiment.
        """
        # Filter data for this experiment
        exp_data = self.df[self.df['test_name'] == test_name].copy()
        
        if len(exp_data) == 0:
            return None, None
        
        print(f"\n{'='*80}")
        print(f"Analyzing experiment: {test_name}")
        print(f"Configuration: IL={exp_data['IL'].iloc[0]}, OL={exp_data['OL'].iloc[0]}")
        print(f"Data points: {len(exp_data)}")
        
        # Step 1: Compute derived metrics
        exp_data = self.compute_derived_metrics(exp_data)
        
        # Step 2: Estimate ITL(k=0.8) and T_prefill(k=0.8)
        itl_80, itl_conf = self.estimate_ITL_at_k(exp_data, 0.8)
        tpref_80, tpref_conf = self.estimate_Tprefill_at_k(exp_data, 0.8)
        
        print(f"Estimated ITL(k=0.8): {itl_80:.6f} (R²={itl_conf:.3f})")
        print(f"Estimated T_prefill(k=0.8): {tpref_80:.6f} (R²={tpref_conf:.3f})")
        
        # Step 3: Compute derivatives
        exp_data = self.compute_derivatives(exp_data)
        
        # Step 4: Detect saturation
        exp_data = self.detect_saturation(exp_data)
        
        # Step 5: Classify regime
        exp_data = self.classify_regime(exp_data)
        
        # Step 6: Find max sustainable RPS
        max_info = self.find_max_sustainable_rps(exp_data)
        
        print(f"\nMax sustainable RPS: {max_info['max_sustainable_rps']:.2f}")
        if max_info['saturation_rps']:
            print(f"Saturation begins at RPS: {max_info['saturation_rps']:.2f}")
        else:
            print("No saturation detected in data range")
        
        # Summary statistics
        summary = {
            'test_name': test_name,
            'IL': exp_data['IL'].iloc[0],
            'OL': exp_data['OL'].iloc[0],
            'data_points': len(exp_data),
            'rps_range': (exp_data['RPS'].min(), exp_data['RPS'].max()),
            'max_sustainable_rps': max_info['max_sustainable_rps'],
            'saturation_rps': max_info['saturation_rps'],
            'estimated_ITL_at_80': itl_80,
            'estimated_Tprefill_at_80': tpref_80,
            'itl_confidence': itl_conf,
            'tprefill_confidence': tpref_conf,
            'regime_distribution': exp_data['regime'].value_counts().to_dict(),
            'saturated_points': max_info['saturated_count']
        }
        
        return exp_data, summary
    
    def analyze_all_experiments(self) -> Tuple[Dict[str, pd.DataFrame], pd.DataFrame]:
        """
        Analyze all experiments in the dataset.
        """
        all_results = {}
        all_summaries = []
        
        for test_name in self.df['test_name'].unique():
            exp_data, summary = self.analyze_experiment(test_name)
            if exp_data is not None:
                all_results[test_name] = exp_data
                all_summaries.append(summary)
        
        summary_df = pd.DataFrame(all_summaries)
        
        return all_results, summary_df
    
    def generate_instance_estimates(self, experiment_results: Dict[str, pd.DataFrame]) -> pd.DataFrame:
        """
        Generate instance estimates for various future load scenarios.
        For each experiment, vary one parameter (IL, OL, or RPS) while keeping others constant.
        """
        estimates = []
        
        for test_name, exp_data in experiment_results.items():
            base_il = exp_data['IL'].iloc[0]
            base_ol = exp_data['OL'].iloc[0]
            max_info = self.find_max_sustainable_rps(exp_data)
            max_rps = max_info['max_sustainable_rps']
            
            # Scenario 1: Vary RPS (keeping IL, OL constant)
            for target_rps in [max_rps * 0.5, max_rps, max_rps * 1.5, max_rps * 2, max_rps * 3]:
                est = self.estimate_instances_needed(exp_data, base_il, base_ol, target_rps)
                est['test_name'] = test_name
                est['scenario'] = 'vary_RPS'
                estimates.append(est)
            
            # Scenario 2: Vary OL (keeping IL, RPS constant at max)
            for ol_multiplier in [0.5, 1.0, 1.5, 2.0]:
                target_ol = int(base_ol * ol_multiplier)
                est = self.estimate_instances_needed(exp_data, base_il, target_ol, max_rps)
                est['test_name'] = test_name
                est['scenario'] = 'vary_OL'
                estimates.append(est)
            
            # Scenario 3: Vary IL (keeping OL, RPS constant at max)
            for il_multiplier in [0.5, 1.0, 1.5, 2.0]:
                target_il = int(base_il * il_multiplier)
                est = self.estimate_instances_needed(exp_data, target_il, base_ol, max_rps)
                est['test_name'] = test_name
                est['scenario'] = 'vary_IL'
                estimates.append(est)
        
        return pd.DataFrame(estimates)


def main():
    """Main analysis workflow."""
    print("="*80)
    print("vLLM Performance Analysis: Saturation Detection & Instance Estimation")
    print("="*80)
    
    # Initialize analyzer
    analyzer = VLLMSaturationAnalyzer('WVA_data160426_short.csv')
    
    # Analyze all experiments
    print("\n" + "="*80)
    print("ANALYZING ALL EXPERIMENTS")
    print("="*80)
    
    experiment_results, summary_df = analyzer.analyze_all_experiments()
    
    # Save detailed results for each experiment
    print("\n" + "="*80)
    print("SAVING DETAILED RESULTS")
    print("="*80)
    
    for test_name, exp_data in experiment_results.items():
        filename = f"analysis_{test_name.replace('/', '_')}.csv"
        exp_data.to_csv(filename, index=False)
        print(f"Saved: {filename}")
    
    # Save summary
    summary_df.to_csv('analysis_summary.csv', index=False)
    print(f"Saved: analysis_summary.csv")
    
    # Generate instance estimates
    print("\n" + "="*80)
    print("GENERATING INSTANCE ESTIMATES")
    print("="*80)
    
    instance_estimates = analyzer.generate_instance_estimates(experiment_results)
    instance_estimates.to_csv('instance_estimates.csv', index=False)
    print(f"Saved: instance_estimates.csv")
    
    # Print summary table
    print("\n" + "="*80)
    print("SUMMARY: MAX SUSTAINABLE RPS PER EXPERIMENT")
    print("="*80)
    print(summary_df[['test_name', 'IL', 'OL', 'max_sustainable_rps', 'saturation_rps', 'saturated_points']].to_string(index=False))
    
    print("\n" + "="*80)
    print("ANALYSIS COMPLETE")
    print("="*80)
    print("\nGenerated files:")
    print("  - analysis_summary.csv: Summary of all experiments")
    print("  - analysis_<test_name>.csv: Detailed metrics for each experiment")
    print("  - instance_estimates.csv: Instance requirements for various scenarios")


if __name__ == '__main__':
    main()

# Made with Bob
