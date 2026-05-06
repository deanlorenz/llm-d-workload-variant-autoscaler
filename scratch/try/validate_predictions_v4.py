#!/usr/bin/env python3
"""
Validation Script v4: Adjustable Saturation Thresholds

Key improvements:
1. Separate KV% and KVMax% saturation detection
2. Adjustable thresholds for both metrics
3. Compare predictions across different threshold values
4. Show accuracy for each threshold configuration
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class AdjustableSaturationPredictor:
    """Predicts saturation with adjustable thresholds for KV% and KVMax%."""
    
    def __init__(self, csv_path: str):
        """Load and prepare the data."""
        self.df = pd.read_csv(csv_path)
        self.df.columns = self.df.columns.str.strip().str.replace('\ufeff', '')
        
        self.df.rename(columns={
            'In-Tok': 'IL',
            'Out-Tok': 'OL',
            'test-name': 'test_name'
        }, inplace=True)
        
        numeric_cols = ['IL', 'OL', 'RPS', 'TTFT', 'ITL', 'E2E', 'Kvcache', 'MaxKvcache']
        for col in numeric_cols:
            self.df[col] = pd.to_numeric(self.df[col], errors='coerce')
        
        self.df = self.df.dropna(subset=['IL', 'OL', 'RPS', 'TTFT', 'ITL', 'E2E', 'Kvcache'])
        
        # Compute derived metrics
        self.df['phi'] = self.df['E2E'] / (self.df['OL'] * self.df['ITL'])
        self.df['rho'] = self.df['TTFT'] / self.df['ITL']
        self.df['T_prefill'] = self.df['TTFT'] - self.df['ITL']
        self.df['N_concurrent'] = self.df['RPS'] * self.df['E2E']
        self.df['sqrt_OL'] = np.sqrt(self.df['OL'])
        self.df['rho_ratio'] = self.df['rho'] / self.df['sqrt_OL']
        
        print(f"Loaded {len(self.df)} data points")
    
    def mark_saturation(self, kv_threshold: float = 0.8, kvmax_threshold: float = 0.95,
                       saturation_type: str = 'both') -> pd.DataFrame:
        """
        Mark saturated points based on thresholds.
        
        Args:
            kv_threshold: Threshold for Kvcache (e.g., 0.8 = 80%)
            kvmax_threshold: Threshold for MaxKvcache (e.g., 0.95 = 95%)
            saturation_type: 'kv', 'kvmax', or 'both'
        
        Returns:
            DataFrame with 'is_saturated' column
        """
        df = self.df.copy()
        
        if saturation_type == 'kv':
            df['is_saturated'] = df['Kvcache'] > kv_threshold
        elif saturation_type == 'kvmax':
            df['is_saturated'] = df['MaxKvcache'] > kvmax_threshold
        elif saturation_type == 'both':
            df['is_saturated'] = (df['Kvcache'] > kv_threshold) | (df['MaxKvcache'] > kvmax_threshold)
        else:
            raise ValueError(f"Unknown saturation_type: {saturation_type}")
        
        return df
    
    def classify_experiment_type(self, exp_data: pd.DataFrame) -> Dict:
        """Determine which parameter varies in this experiment."""
        il_std = exp_data['IL'].std()
        ol_std = exp_data['OL'].std()
        rps_std = exp_data['RPS'].std()
        
        il_range = exp_data['IL'].max() - exp_data['IL'].min()
        ol_range = exp_data['OL'].max() - exp_data['OL'].min()
        rps_range = exp_data['RPS'].max() - exp_data['RPS'].min()
        
        if rps_range > 0.5 and rps_std / exp_data['RPS'].mean() > 0.1:
            exp_type = 'vary_rps'
            varying_param = 'RPS'
            base_il = exp_data['IL'].iloc[0]
            base_ol = exp_data['OL'].iloc[0]
            base_rps = exp_data['RPS'].mean()
        elif il_range > 500 and il_std / exp_data['IL'].mean() > 0.1:
            exp_type = 'vary_il'
            varying_param = 'IL'
            base_il = exp_data['IL'].mean()
            base_ol = exp_data['OL'].iloc[0]
            base_rps = exp_data['RPS'].iloc[0]
        elif ol_range > 50 and ol_std / exp_data['OL'].mean() > 0.1:
            exp_type = 'vary_ol'
            varying_param = 'OL'
            base_il = exp_data['IL'].iloc[0]
            base_ol = exp_data['OL'].mean()
            base_rps = exp_data['RPS'].iloc[0]
        else:
            exp_type = 'unknown'
            varying_param = 'unknown'
            base_il = exp_data['IL'].mean()
            base_ol = exp_data['OL'].mean()
            base_rps = exp_data['RPS'].mean()
        
        return {
            'type': exp_type,
            'varying_param': varying_param,
            'base_il': base_il,
            'base_ol': base_ol,
            'base_rps': base_rps
        }
    
    def estimate_kv_capacity(self, non_sat_data: pd.DataFrame) -> float:
        """Estimate KV cache capacity from non-saturated data."""
        kv_estimates = []
        for _, row in non_sat_data.iterrows():
            n = row['N_concurrent']
            il = row['IL']
            ol = row['OL']
            k = row['Kvcache']
            
            if k > 0.01:
                tokens_in_cache = n * (il + ol / 2)
                kv_total_est = tokens_in_cache / k
                kv_estimates.append(kv_total_est)
        
        return np.median(kv_estimates) if len(kv_estimates) > 0 else np.nan
    
    def predict_max_rps(self, non_sat_data: pd.DataFrame, 
                        target_il: float, target_ol: float,
                        kv_capacity: float, target_k: float) -> Dict:
        """Predict maximum RPS for given IL/OL at target k threshold."""
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        
        if len(k_vals) >= 2:
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_target = coeffs[0] + coeffs[1] * target_k
        else:
            itl_at_target = float(np.mean(itl_vals))
        
        tpref_vals = non_sat_data['T_prefill'].values
        if len(k_vals) >= 2:
            coeffs, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            tpref_at_target = coeffs[0] + coeffs[1] * target_k
        else:
            tpref_at_target = float(np.mean(tpref_vals))
        
        e2e_at_sat = tpref_at_target + target_ol * itl_at_target
        tokens_per_request = target_il + target_ol / 2
        predicted_max_rps = (target_k * kv_capacity) / (e2e_at_sat * tokens_per_request)
        
        return {
            'predicted_value': predicted_max_rps,
            'method': 'KV_ceiling',
            'itl_at_target': itl_at_target,
            'tpref_at_target': tpref_at_target,
            'e2e_at_sat': e2e_at_sat
        }
    
    def predict_max_il(self, non_sat_data: pd.DataFrame,
                       target_ol: float, target_rps: float,
                       kv_capacity: float, target_k: float) -> Dict:
        """Predict maximum IL for given OL/RPS at target k threshold."""
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        
        if len(k_vals) >= 2 and np.std(k_vals) > 0.01:
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_target = coeffs[0] + coeffs[1] * target_k
        else:
            itl_at_target = float(np.mean(itl_vals))
        
        il_vals = non_sat_data['IL'].values
        tpref_vals = non_sat_data['T_prefill'].values
        
        if len(il_vals) >= 2 and np.std(il_vals) > 100:
            A = np.vstack([np.ones(len(il_vals)), il_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            tpref_base, tpref_per_token = coeffs
        else:
            tpref_base = 0
            tpref_per_token = float(np.mean(tpref_vals) / np.mean(il_vals)) if np.mean(il_vals) > 0 else 0.001
        
        il_guess = float(np.mean(il_vals))
        for _ in range(20):
            tpref = tpref_base + tpref_per_token * il_guess
            e2e = tpref + target_ol * itl_at_target
            
            tokens_in_cache = (target_k * kv_capacity) / (target_rps * e2e)
            il_new = tokens_in_cache - target_ol / 2
            
            if abs(il_new - il_guess) < 50:
                break
            il_guess = 0.5 * il_guess + 0.5 * il_new
        
        predicted_il_kv = max(0, il_guess)
        
        batch_size = non_sat_data['N_concurrent'].mean()
        rho_threshold = np.sqrt(target_ol)
        target_tprefill = rho_threshold * itl_at_target
        
        if tpref_per_token > 0:
            predicted_il_prefill = (target_tprefill - tpref_base) / tpref_per_token
        else:
            predicted_il_prefill = float('inf')
        
        predicted_il = min(predicted_il_kv, predicted_il_prefill)
        method = 'KV_ceiling' if predicted_il == predicted_il_kv else 'Prefill_instability'
        
        return {
            'predicted_value': predicted_il,
            'method': method,
            'predicted_il_kv': predicted_il_kv,
            'predicted_il_prefill': predicted_il_prefill,
            'itl_at_target': itl_at_target
        }
    
    def predict_max_ol(self, non_sat_data: pd.DataFrame,
                       target_il: float, target_rps: float,
                       kv_capacity: float, target_k: float) -> Dict:
        """Predict maximum OL for given IL/RPS at target k threshold."""
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        
        if len(k_vals) >= 2 and np.std(k_vals) > 0.01:
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs_itl, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_target = coeffs_itl[0] + coeffs_itl[1] * target_k
            
            tpref_vals = non_sat_data['T_prefill'].values
            tpref_at_target = float(np.mean(tpref_vals))
        else:
            itl_at_target = float(np.mean(itl_vals))
            tpref_at_target = float(np.mean(non_sat_data['T_prefill']))
        
        a = target_rps * itl_at_target / 2
        b = target_rps * (tpref_at_target / 2 + itl_at_target * target_il)
        c = target_rps * tpref_at_target * target_il - target_k * kv_capacity
        
        discriminant = b**2 - 4*a*c
        if discriminant >= 0 and a != 0:
            ol1 = (-b + np.sqrt(discriminant)) / (2*a)
            ol2 = (-b - np.sqrt(discriminant)) / (2*a)
            candidates = [x for x in [ol1, ol2] if x > 0]
            predicted_ol_kv = max(candidates) if candidates else float('inf')
        else:
            predicted_ol_kv = float('inf')
        
        predicted_ol = predicted_ol_kv
        method = 'KV_ceiling'
        
        return {
            'predicted_value': predicted_ol,
            'method': method,
            'predicted_ol_kv': predicted_ol_kv,
            'itl_at_target': itl_at_target,
            'tpref_at_target': tpref_at_target
        }
    
    def validate_experiment(self, test_name: str, df_marked: pd.DataFrame,
                           target_k: float, saturation_type: str) -> Optional[Dict]:
        """Validate predictions for a single experiment with given threshold."""
        exp_data = df_marked[df_marked['test_name'] == test_name].copy()
        
        if len(exp_data) == 0:
            return None
        
        exp_info = self.classify_experiment_type(exp_data)
        
        if exp_info['type'] == 'vary_rps':
            exp_data = exp_data.sort_values('RPS').reset_index(drop=True)
        elif exp_info['type'] == 'vary_il':
            exp_data = exp_data.sort_values('IL').reset_index(drop=True)
        elif exp_info['type'] == 'vary_ol':
            exp_data = exp_data.sort_values('OL').reset_index(drop=True)
        
        non_sat = exp_data[~exp_data['is_saturated']].copy()
        saturated = exp_data[exp_data['is_saturated']].copy()
        
        if len(non_sat) < 2:
            return None
        
        kv_capacity = self.estimate_kv_capacity(non_sat)
        
        if exp_info['type'] == 'vary_rps':
            prediction = self.predict_max_rps(non_sat, exp_info['base_il'], 
                                              exp_info['base_ol'], kv_capacity, target_k)
            actual_max = non_sat['RPS'].max()
            actual_sat = saturated['RPS'].min() if len(saturated) > 0 else None
            param_name = 'RPS'
            
        elif exp_info['type'] == 'vary_il':
            prediction = self.predict_max_il(non_sat, exp_info['base_ol'],
                                            exp_info['base_rps'], kv_capacity, target_k)
            actual_max = non_sat['IL'].max()
            actual_sat = saturated['IL'].min() if len(saturated) > 0 else None
            param_name = 'IL'
            
        elif exp_info['type'] == 'vary_ol':
            prediction = self.predict_max_ol(non_sat, exp_info['base_il'],
                                            exp_info['base_rps'], kv_capacity, target_k)
            actual_max = non_sat['OL'].max()
            actual_sat = saturated['OL'].min() if len(saturated) > 0 else None
            param_name = 'OL'
        else:
            return None
        
        predicted_max = prediction['predicted_value']
        error_pct = abs(predicted_max - actual_max) / actual_max * 100 if actual_max > 0 else np.nan
        
        return {
            'test_name': test_name,
            'exp_type': exp_info['type'],
            'varying_param': param_name,
            'kv_capacity': kv_capacity,
            'prediction_method': prediction['method'],
            'predicted_max': predicted_max,
            'actual_max': actual_max,
            'actual_sat': actual_sat,
            'error_pct': error_pct,
            'non_sat_count': len(non_sat),
            'sat_count': len(saturated),
            'target_k': target_k,
            'saturation_type': saturation_type
        }
    
    def validate_all_with_threshold(self, kv_threshold: float, kvmax_threshold: float,
                                    saturation_type: str) -> pd.DataFrame:
        """Validate all experiments with given thresholds."""
        df_marked = self.mark_saturation(kv_threshold, kvmax_threshold, saturation_type)
        
        target_k = kv_threshold if saturation_type in ['kv', 'both'] else kvmax_threshold
        
        results = []
        for test_name in self.df['test_name'].unique():
            result = self.validate_experiment(test_name, df_marked, target_k, saturation_type)
            if result:
                results.append(result)
        
        if not results:
            return pd.DataFrame()
        
        summary_data = []
        for r in results:
            summary_data.append({
                'test_name': r['test_name'],
                'exp_type': r['exp_type'],
                'varying_param': r['varying_param'],
                'predicted_max': r['predicted_max'],
                'actual_max': r['actual_max'],
                'error_pct': r['error_pct'],
                'non_sat_points': r['non_sat_count'],
                'sat_points': r['sat_count'],
                'target_k': r['target_k'],
                'saturation_type': saturation_type
            })
        
        return pd.DataFrame(summary_data)


def main():
    """Main validation workflow with multiple threshold configurations."""
    print("="*80)
    print("Adjustable Saturation Threshold Validation v4")
    print("="*80)
    
    predictor = AdjustableSaturationPredictor('WVA_data160426_short.csv')
    
    # Test different threshold configurations
    configurations = [
        # (kv_threshold, kvmax_threshold, saturation_type, description)
        (0.7, 0.95, 'kv', 'Conservative KV% (70%)'),
        (0.75, 0.95, 'kv', 'Moderate KV% (75%)'),
        (0.8, 0.95, 'kv', 'Standard KV% (80%)'),
        (0.85, 0.95, 'kv', 'Aggressive KV% (85%)'),
        (0.8, 0.90, 'kvmax', 'Conservative KVMax% (90%)'),
        (0.8, 0.95, 'kvmax', 'Standard KVMax% (95%)'),
        (0.8, 0.98, 'kvmax', 'Aggressive KVMax% (98%)'),
        (0.8, 0.95, 'both', 'Combined (KV%=80% OR KVMax%=95%)'),
    ]
    
    all_results = []
    
    for kv_thresh, kvmax_thresh, sat_type, description in configurations:
        print(f"\n{'='*80}")
        print(f"Configuration: {description}")
        print(f"  KV% threshold: {kv_thresh*100:.0f}%")
        print(f"  KVMax% threshold: {kvmax_thresh*100:.0f}%")
        print(f"  Saturation type: {sat_type}")
        print(f"{'='*80}")
        
        summary_df = predictor.validate_all_with_threshold(kv_thresh, kvmax_thresh, sat_type)
        
        if len(summary_df) > 0:
            # Add configuration info
            summary_df['kv_threshold'] = kv_thresh
            summary_df['kvmax_threshold'] = kvmax_thresh
            summary_df['config_desc'] = description
            
            all_results.append(summary_df)
            
            # Print summary statistics
            valid_errors = summary_df['error_pct'].dropna()
            if len(valid_errors) > 0:
                print(f"\nResults:")
                print(f"  Experiments validated: {len(summary_df)}")
                print(f"  Median error: {valid_errors.median():.1f}%")
                print(f"  Mean error: {valid_errors.mean():.1f}%")
                print(f"  Experiments <10% error: {(valid_errors < 10).sum()}/{len(valid_errors)}")
                print(f"  Experiments <20% error: {(valid_errors < 20).sum()}/{len(valid_errors)}")
    
    # Combine all results
    if all_results:
        combined_df = pd.concat(all_results, ignore_index=True)
        combined_df.to_csv('validation_threshold_comparison.csv', index=False)
        print(f"\n{'='*80}")
        print("Saved: validation_threshold_comparison.csv")
        
        # Summary comparison table
        print(f"\n{'='*80}")
        print("THRESHOLD COMPARISON SUMMARY")
        print("="*80)
        
        comparison_data = []
        for config_desc in combined_df['config_desc'].unique():
            config_data = combined_df[combined_df['config_desc'] == config_desc]
            valid_errors = config_data['error_pct'].dropna()
            
            if len(valid_errors) > 0:
                comparison_data.append({
                    'Configuration': config_desc,
                    'Experiments': len(config_data),
                    'Median Error %': f"{valid_errors.median():.1f}",
                    'Mean Error %': f"{valid_errors.mean():.1f}",
                    '<10% Error': f"{(valid_errors < 10).sum()}/{len(valid_errors)}",
                    '<20% Error': f"{(valid_errors < 20).sum()}/{len(valid_errors)}"
                })
        
        comparison_df = pd.DataFrame(comparison_data)
        print(comparison_df.to_string(index=False))
        
        # Best configuration
        print(f"\n{'='*80}")
        print("BEST CONFIGURATIONS")
        print("="*80)
        
        for metric in ['Median Error %', 'Mean Error %']:
            comparison_df[metric] = comparison_df[metric].astype(float)
        
        best_median = comparison_df.loc[comparison_df['Median Error %'].idxmin()]
        print(f"\nLowest Median Error:")
        print(f"  {best_median['Configuration']}: {best_median['Median Error %']:.1f}%")
        
        best_mean = comparison_df.loc[comparison_df['Mean Error %'].idxmin()]
        print(f"\nLowest Mean Error:")
        print(f"  {best_mean['Configuration']}: {best_mean['Mean Error %']:.1f}%")
    
    print(f"\n{'='*80}")
    print("VALIDATION COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

# Made with Bob
