#!/usr/bin/env python3
"""
Validation Script: Test Saturation Prediction Accuracy

This script validates the prediction methodology by:
1. Using ONLY non-saturated data to build models
2. Predicting saturation thresholds (max RPS, max IL, max OL)
3. Comparing predictions to actual observed saturation
4. Computing prediction accuracy metrics
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple
import warnings
warnings.filterwarnings('ignore')


class SaturationPredictor:
    """Predicts saturation thresholds using only non-saturated data."""
    
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
        
        # Mark saturation (ground truth)
        self.df['kv_saturated'] = (self.df['Kvcache'] > 0.8) | (self.df['MaxKvcache'] > 0.95)
        self.df['is_saturated'] = self.df['kv_saturated']  # Simplified for validation
        
        print(f"Loaded {len(self.df)} data points")
        print(f"Saturated points: {self.df['is_saturated'].sum()}")
    
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
    
    def predict_max_rps_at_config(self, non_sat_data: pd.DataFrame, 
                                   target_il: float, target_ol: float,
                                   kv_capacity: float) -> Dict:
        """
        Predict maximum RPS for a given IL/OL configuration.
        
        Method:
        1. Estimate ITL(k) and T_prefill(k) from non-saturated data
        2. Use KV capacity constraint: k = (N × (IL + OL/2)) / KV_capacity
        3. Solve for max RPS when k = 0.8 (saturation threshold)
        
        At saturation: k = 0.8
        N = RPS × E2E
        E2E ≈ T_prefill + OL × ITL  (simplified, ignoring queueing)
        
        Therefore:
        0.8 = (RPS × E2E × (IL + OL/2)) / KV_capacity
        
        Solving for RPS:
        RPS = (0.8 × KV_capacity) / (E2E × (IL + OL/2))
        """
        # Estimate ITL at k=0.8
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        
        if len(k_vals) >= 2:
            # Linear fit: ITL = a + b*k
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            a, b = coeffs
            itl_at_80 = a + b * 0.8
        else:
            itl_at_80 = np.mean(itl_vals)
        
        # Estimate T_prefill at k=0.8
        tpref_vals = non_sat_data['T_prefill'].values
        if len(k_vals) >= 2:
            coeffs, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            a, b = coeffs
            tpref_at_80 = a + b * 0.8
        else:
            tpref_at_80 = np.mean(tpref_vals)
        
        # Estimate E2E at saturation
        e2e_at_sat = tpref_at_80 + target_ol * itl_at_80
        
        # Predict max RPS using KV capacity constraint
        # k = 0.8 = (RPS × E2E × (IL + OL/2)) / KV_capacity
        # RPS = (0.8 × KV_capacity) / (E2E × (IL + OL/2))
        
        tokens_per_request = target_il + target_ol / 2
        predicted_max_rps = (0.8 * kv_capacity) / (e2e_at_sat * tokens_per_request)
        
        return {
            'predicted_max_rps': predicted_max_rps,
            'itl_at_80': itl_at_80,
            'tpref_at_80': tpref_at_80,
            'e2e_at_sat': e2e_at_sat,
            'tokens_per_request': tokens_per_request
        }
    
    def predict_max_il_at_config(self, non_sat_data: pd.DataFrame,
                                  target_ol: float, target_rps: float,
                                  kv_capacity: float) -> Dict:
        """
        Predict maximum IL for a given OL/RPS configuration.
        
        Using: k = 0.8 = (RPS × E2E × (IL + OL/2)) / KV_capacity
        
        Solving for IL:
        IL = (0.8 × KV_capacity) / (RPS × E2E) - OL/2
        """
        # Estimate ITL and T_prefill (assume they don't change much with IL)
        itl_mean = non_sat_data['ITL'].mean()
        
        # T_prefill scales with IL, estimate slope
        il_vals = non_sat_data['IL'].values
        tpref_vals = non_sat_data['T_prefill'].values
        
        if len(il_vals) >= 2 and np.std(il_vals) > 0:
            # Linear fit: T_prefill = a + b*IL
            A = np.vstack([np.ones(len(il_vals)), il_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            a, b = coeffs
            tpref_per_token = b
        else:
            # Fallback: assume proportional
            tpref_per_token = np.mean(tpref_vals) / np.mean(il_vals) if np.mean(il_vals) > 0 else 0.0001
        
        # Iterative solution (since E2E depends on IL through T_prefill)
        il_guess = 5000  # Initial guess
        for _ in range(10):  # Iterate to converge
            tpref_guess = a + b * il_guess if len(il_vals) >= 2 else tpref_per_token * il_guess
            e2e_guess = tpref_guess + target_ol * itl_mean
            
            # Solve for IL
            tokens_available = (0.8 * kv_capacity) / (target_rps * e2e_guess)
            il_new = tokens_available - target_ol / 2
            
            if abs(il_new - il_guess) < 10:  # Converged
                break
            il_guess = il_new
        
        predicted_max_il = max(0, il_guess)
        
        return {
            'predicted_max_il': predicted_max_il,
            'itl_mean': itl_mean,
            'tpref_per_token': tpref_per_token,
            'e2e_at_sat': e2e_guess
        }
    
    def predict_max_ol_at_config(self, non_sat_data: pd.DataFrame,
                                  target_il: float, target_rps: float,
                                  kv_capacity: float) -> Dict:
        """
        Predict maximum OL for a given IL/RPS configuration.
        
        Using: k = 0.8 = (RPS × E2E × (IL + OL/2)) / KV_capacity
        
        E2E = T_prefill + OL × ITL
        
        This is a quadratic equation in OL.
        """
        # Estimate ITL and T_prefill at k=0.8
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        tpref_vals = non_sat_data['T_prefill'].values
        
        if len(k_vals) >= 2:
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs_itl, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_80 = coeffs_itl[0] + coeffs_itl[1] * 0.8
            
            coeffs_tpref, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            tpref_at_80 = coeffs_tpref[0] + coeffs_tpref[1] * 0.8
        else:
            itl_at_80 = np.mean(itl_vals)
            tpref_at_80 = np.mean(tpref_vals)
        
        # Solve quadratic: k = (RPS × (T_prefill + OL × ITL) × (IL + OL/2)) / KV_capacity
        # 0.8 × KV_capacity = RPS × (T_prefill + OL × ITL) × (IL + OL/2)
        # 0.8 × KV_capacity = RPS × (T_prefill × IL + T_prefill × OL/2 + OL × ITL × IL + OL² × ITL/2)
        
        # Rearranging: a×OL² + b×OL + c = 0
        # where:
        a = target_rps * itl_at_80 / 2
        b = target_rps * (tpref_at_80 / 2 + itl_at_80 * target_il)
        c = target_rps * tpref_at_80 * target_il - 0.8 * kv_capacity
        
        # Solve quadratic
        discriminant = b**2 - 4*a*c
        if discriminant >= 0:
            ol1 = (-b + np.sqrt(discriminant)) / (2*a)
            ol2 = (-b - np.sqrt(discriminant)) / (2*a)
            predicted_max_ol = max(ol1, ol2)  # Take positive root
        else:
            predicted_max_ol = np.nan
        
        return {
            'predicted_max_ol': predicted_max_ol,
            'itl_at_80': itl_at_80,
            'tpref_at_80': tpref_at_80,
            'discriminant': discriminant
        }
    
    def validate_experiment(self, test_name: str) -> Dict:
        """
        Validate predictions for a single experiment.
        
        Steps:
        1. Split data into non-saturated (training) and saturated (test)
        2. Use non-saturated data to estimate KV capacity and build models
        3. Predict saturation thresholds
        4. Compare to actual observations
        """
        exp_data = self.df[self.df['test_name'] == test_name].copy()
        exp_data = exp_data.sort_values('RPS').reset_index(drop=True)
        
        if len(exp_data) == 0:
            return None
        
        # Split into non-saturated and saturated
        non_sat = exp_data[~exp_data['is_saturated']].copy()
        saturated = exp_data[exp_data['is_saturated']].copy()
        
        if len(non_sat) < 2:
            print(f"  ⚠️  {test_name}: Not enough non-saturated data ({len(non_sat)} points)")
            return None
        
        print(f"\n{'='*80}")
        print(f"Validating: {test_name}")
        print(f"  Non-saturated: {len(non_sat)} points")
        print(f"  Saturated: {len(saturated)} points")
        
        # Get configuration
        base_il = exp_data['IL'].iloc[0]
        base_ol = exp_data['OL'].iloc[0]
        
        # Estimate KV capacity from non-saturated data only
        kv_capacity = self.estimate_kv_capacity(non_sat)
        print(f"  Estimated KV capacity: {kv_capacity:.0f} tokens")
        
        # Predict max RPS for this configuration
        pred_rps = self.predict_max_rps_at_config(non_sat, base_il, base_ol, kv_capacity)
        predicted_max_rps = pred_rps['predicted_max_rps']
        
        # Find actual max RPS (last non-saturated point)
        if len(saturated) > 0:
            actual_max_rps = non_sat['RPS'].max()
            actual_sat_rps = saturated['RPS'].min()
        else:
            actual_max_rps = exp_data['RPS'].max()
            actual_sat_rps = None
        
        print(f"\n  RPS Prediction:")
        print(f"    Predicted max RPS: {predicted_max_rps:.2f}")
        print(f"    Actual max RPS: {actual_max_rps:.2f}")
        if actual_sat_rps:
            print(f"    Actual saturation RPS: {actual_sat_rps:.2f}")
            rps_error = abs(predicted_max_rps - actual_max_rps) / actual_max_rps * 100
            print(f"    Prediction error: {rps_error:.1f}%")
        
        # Validate saturated points: predict if they should be saturated
        validation_results = []
        
        if len(saturated) > 0:
            print(f"\n  Validating {len(saturated)} saturated points:")
            for idx, row in saturated.iterrows():
                # Predict k for this point
                e2e_pred = pred_rps['tpref_at_80'] + row['OL'] * pred_rps['itl_at_80']
                n_pred = row['RPS'] * e2e_pred
                tokens_pred = n_pred * (row['IL'] + row['OL'] / 2)
                k_pred = tokens_pred / kv_capacity
                
                # Actual values
                k_actual = row['Kvcache']
                
                # Check if prediction matches observation
                pred_saturated = k_pred > 0.8
                actual_saturated = row['is_saturated']
                
                match = pred_saturated == actual_saturated
                
                print(f"    RPS={row['RPS']:.1f}: k_pred={k_pred:.3f}, k_actual={k_actual:.3f}, "
                      f"pred_sat={pred_saturated}, actual_sat={actual_saturated}, match={match}")
                
                validation_results.append({
                    'rps': row['RPS'],
                    'k_predicted': k_pred,
                    'k_actual': k_actual,
                    'predicted_saturated': pred_saturated,
                    'actual_saturated': actual_saturated,
                    'match': match
                })
        
        # Summary
        if len(validation_results) > 0:
            accuracy = sum(r['match'] for r in validation_results) / len(validation_results) * 100
            print(f"\n  Validation accuracy: {accuracy:.1f}% ({sum(r['match'] for r in validation_results)}/{len(validation_results)} correct)")
        
        return {
            'test_name': test_name,
            'base_il': base_il,
            'base_ol': base_ol,
            'kv_capacity': kv_capacity,
            'predicted_max_rps': predicted_max_rps,
            'actual_max_rps': actual_max_rps,
            'actual_sat_rps': actual_sat_rps,
            'rps_error_pct': abs(predicted_max_rps - actual_max_rps) / actual_max_rps * 100 if actual_max_rps > 0 else np.nan,
            'validation_results': validation_results,
            'validation_accuracy': accuracy if len(validation_results) > 0 else np.nan,
            'non_sat_count': len(non_sat),
            'sat_count': len(saturated)
        }
    
    def validate_all_experiments(self) -> pd.DataFrame:
        """Validate predictions for all experiments."""
        results = []
        
        for test_name in self.df['test_name'].unique():
            result = self.validate_experiment(test_name)
            if result:
                results.append(result)
        
        # Create summary DataFrame
        summary_data = []
        for r in results:
            summary_data.append({
                'test_name': r['test_name'],
                'IL': r['base_il'],
                'OL': r['base_ol'],
                'kv_capacity': r['kv_capacity'],
                'predicted_max_rps': r['predicted_max_rps'],
                'actual_max_rps': r['actual_max_rps'],
                'actual_sat_rps': r['actual_sat_rps'],
                'rps_error_pct': r['rps_error_pct'],
                'validation_accuracy': r['validation_accuracy'],
                'non_sat_points': r['non_sat_count'],
                'sat_points': r['sat_count']
            })
        
        return pd.DataFrame(summary_data), results


def main():
    """Main validation workflow."""
    print("="*80)
    print("Saturation Prediction Validation")
    print("="*80)
    
    predictor = SaturationPredictor('WVA_data160426_short.csv')
    
    print("\n" + "="*80)
    print("VALIDATING ALL EXPERIMENTS")
    print("="*80)
    
    summary_df, detailed_results = predictor.validate_all_experiments()
    
    # Save results
    summary_df.to_csv('validation_summary.csv', index=False)
    print(f"\n{'='*80}")
    print("Saved: validation_summary.csv")
    
    # Print overall summary
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY")
    print("="*80)
    print(summary_df[['test_name', 'predicted_max_rps', 'actual_max_rps', 'rps_error_pct', 'validation_accuracy']].to_string(index=False))
    
    # Overall statistics
    print(f"\n{'='*80}")
    print("OVERALL STATISTICS")
    print("="*80)
    
    valid_errors = summary_df['rps_error_pct'].dropna()
    if len(valid_errors) > 0:
        print(f"RPS Prediction Error:")
        print(f"  Mean: {valid_errors.mean():.1f}%")
        print(f"  Median: {valid_errors.median():.1f}%")
        print(f"  Std: {valid_errors.std():.1f}%")
        print(f"  Min: {valid_errors.min():.1f}%")
        print(f"  Max: {valid_errors.max():.1f}%")
    
    valid_acc = summary_df['validation_accuracy'].dropna()
    if len(valid_acc) > 0:
        print(f"\nSaturation Detection Accuracy:")
        print(f"  Mean: {valid_acc.mean():.1f}%")
        print(f"  Median: {valid_acc.median():.1f}%")
        print(f"  Experiments with 100% accuracy: {(valid_acc == 100).sum()}/{len(valid_acc)}")
    
    print(f"\n{'='*80}")
    print("VALIDATION COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

# Made with Bob
