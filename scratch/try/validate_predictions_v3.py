#!/usr/bin/env python3
"""
Validation Script v3: Complete Prediction Validation for All Experiment Types

Handles three types of experiments:
1. Vary RPS (IL, OL constant) - predict max RPS
2. Vary IL (OL, RPS constant) - predict max IL  
3. Vary OL (IL, RPS constant) - predict max OL

Uses only non-saturated data to build models and predict saturation thresholds.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
import warnings
warnings.filterwarnings('ignore')


class ComprehensiveSaturationPredictor:
    """Predicts saturation thresholds for all experiment types."""
    
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
        
        # Mark saturation
        self.df['kv_saturated'] = (self.df['Kvcache'] > 0.8) | (self.df['MaxKvcache'] > 0.95)
        self.df['is_saturated'] = self.df['kv_saturated']
        
        print(f"Loaded {len(self.df)} data points")
        print(f"Saturated points: {self.df['is_saturated'].sum()}")
    
    def classify_experiment_type(self, exp_data: pd.DataFrame) -> Dict:
        """
        Determine which parameter varies in this experiment.
        
        Returns dict with:
        - type: 'vary_rps', 'vary_il', or 'vary_ol'
        - base_il, base_ol, base_rps: typical values
        - varying_param: name of varying parameter
        """
        il_std = exp_data['IL'].std()
        ol_std = exp_data['OL'].std()
        rps_std = exp_data['RPS'].std()
        
        il_range = exp_data['IL'].max() - exp_data['IL'].min()
        ol_range = exp_data['OL'].max() - exp_data['OL'].min()
        rps_range = exp_data['RPS'].max() - exp_data['RPS'].min()
        
        # Determine which parameter has significant variation
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
            'base_rps': base_rps,
            'il_range': il_range,
            'ol_range': ol_range,
            'rps_range': rps_range
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
                        kv_capacity: float) -> Dict:
        """
        Predict maximum RPS for given IL/OL (Type 1: vary RPS experiments).
        
        Uses KV capacity constraint: k = (N × (IL + OL/2)) / KV_capacity
        At saturation: k = 0.8
        """
        # Estimate ITL at k=0.8
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        
        if len(k_vals) >= 2:
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_80 = coeffs[0] + coeffs[1] * 0.8
        else:
            itl_at_80 = np.mean(itl_vals)
        
        # Estimate T_prefill at k=0.8
        tpref_vals = non_sat_data['T_prefill'].values
        if len(k_vals) >= 2:
            coeffs, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            tpref_at_80 = coeffs[0] + coeffs[1] * 0.8
        else:
            tpref_at_80 = np.mean(tpref_vals)
        
        # Estimate E2E at saturation
        e2e_at_sat = tpref_at_80 + target_ol * itl_at_80
        
        # Predict max RPS using KV capacity constraint
        tokens_per_request = target_il + target_ol / 2
        predicted_max_rps = (0.8 * kv_capacity) / (e2e_at_sat * tokens_per_request)
        
        return {
            'predicted_value': predicted_max_rps,
            'method': 'KV_ceiling',
            'itl_at_80': itl_at_80,
            'tpref_at_80': tpref_at_80,
            'e2e_at_sat': e2e_at_sat
        }
    
    def predict_max_il(self, non_sat_data: pd.DataFrame,
                       target_ol: float, target_rps: float,
                       kv_capacity: float) -> Dict:
        """
        Predict maximum IL for given OL/RPS (Type 2: vary IL experiments).
        
        Key insight: As IL increases, T_prefill increases, causing ρ = TTFT/ITL to grow.
        System saturates when prefill pressure becomes too high OR KV cache fills.
        """
        # Estimate ITL at k=0.8 (relatively constant with IL)
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        
        if len(k_vals) >= 2 and np.std(k_vals) > 0.01:
            # Linear fit: ITL = a + b*k
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_80 = coeffs[0] + coeffs[1] * 0.8
        else:
            itl_at_80 = np.mean(itl_vals)
        
        # Method 1: KV ceiling
        # At saturation: k = 0.8 = (RPS × E2E × (IL + OL/2)) / KV_capacity
        # E2E = T_prefill(IL) + OL × ITL
        # T_prefill scales roughly linearly with IL
        
        # Estimate T_prefill per input token
        il_vals = non_sat_data['IL'].values
        tpref_vals = non_sat_data['T_prefill'].values
        
        if len(il_vals) >= 2 and np.std(il_vals) > 100:
            # T_prefill = a + b*IL (b is time per input token)
            A = np.vstack([np.ones(len(il_vals)), il_vals]).T
            coeffs, _, _, _ = np.linalg.lstsq(A, tpref_vals, rcond=None)
            tpref_base, tpref_per_token = coeffs
        else:
            tpref_base = 0
            tpref_per_token = np.mean(tpref_vals) / np.mean(il_vals) if np.mean(il_vals) > 0 else 0.001
        
        # Solve for IL iteratively
        il_guess = np.mean(il_vals)
        for _ in range(20):
            tpref = tpref_base + tpref_per_token * il_guess
            e2e = tpref + target_ol * itl_at_80
            
            # From KV constraint: IL = (0.8 * KV / (RPS * E2E)) - OL/2
            tokens_in_cache = (0.8 * kv_capacity) / (target_rps * e2e)
            il_new = tokens_in_cache - target_ol / 2
            
            if abs(il_new - il_guess) < 50:
                break
            il_guess = 0.5 * il_guess + 0.5 * il_new  # Damping for stability
        
        predicted_il_kv = max(0, il_guess)
        
        # Method 2: Prefill instability (√OL scaling)
        # From discussion: λ_max ∝ B / (√OL × T_prefill)
        # For vary-IL: IL_max is where T_prefill causes instability
        # Heuristic: ρ = TTFT/ITL should stay below √OL
        
        # Estimate average batch size
        batch_size = non_sat_data['N_concurrent'].mean()
        
        # Critical ρ threshold (from √OL scaling)
        rho_threshold = np.sqrt(target_ol)
        
        # Predict IL where ρ would reach threshold
        # ρ = TTFT/ITL = (T_prefill + ITL) / ITL ≈ T_prefill/ITL (when T_prefill >> ITL)
        # So: T_prefill ≈ ρ_threshold × ITL
        target_tprefill = rho_threshold * itl_at_80
        
        # IL where T_prefill reaches target
        if tpref_per_token > 0:
            predicted_il_prefill = (target_tprefill - tpref_base) / tpref_per_token
        else:
            predicted_il_prefill = np.inf
        
        # Take minimum of both mechanisms
        predicted_il = min(predicted_il_kv, predicted_il_prefill)
        
        if predicted_il == predicted_il_kv:
            method = 'KV_ceiling'
        else:
            method = 'Prefill_instability'
        
        return {
            'predicted_value': predicted_il,
            'method': method,
            'predicted_il_kv': predicted_il_kv,
            'predicted_il_prefill': predicted_il_prefill,
            'itl_at_80': itl_at_80,
            'tpref_per_token': tpref_per_token,
            'rho_threshold': rho_threshold
        }
    
    def predict_max_ol(self, non_sat_data: pd.DataFrame,
                       target_il: float, target_rps: float,
                       kv_capacity: float) -> Dict:
        """
        Predict maximum OL for given IL/RPS (Type 3: vary OL experiments).
        
        Key observation: In vary-OL experiments, ρ stays relatively constant
        until KV cache fills. The √OL scaling helps the system handle larger OL,
        so saturation is primarily driven by KV ceiling, not prefill instability.
        """
        # Estimate ITL and T_prefill at k=0.8
        k_vals = non_sat_data['Kvcache'].values
        itl_vals = non_sat_data['ITL'].values
        tpref_vals = non_sat_data['T_prefill'].values
        
        if len(k_vals) >= 2 and np.std(k_vals) > 0.01:
            # Linear fit: ITL(k) = a + b*k
            A = np.vstack([np.ones(len(k_vals)), k_vals]).T
            coeffs_itl, _, _, _ = np.linalg.lstsq(A, itl_vals, rcond=None)
            itl_at_80 = coeffs_itl[0] + coeffs_itl[1] * 0.8
            
            # T_prefill is relatively constant with OL
            tpref_at_80 = float(np.mean(tpref_vals))
        else:
            itl_at_80 = float(np.mean(itl_vals))
            tpref_at_80 = float(np.mean(tpref_vals))
        
        # Primary method: KV ceiling (quadratic equation)
        # At saturation: k = 0.8 = (RPS × E2E × (IL + OL/2)) / KV_capacity
        # E2E = T_prefill + OL × ITL
        # Expanding: 0.8 × KV = RPS × (T_pref + OL × ITL) × (IL + OL/2)
        # = RPS × (T_pref × IL + T_pref × OL/2 + OL × ITL × IL + OL² × ITL/2)
        # Rearranging: (RPS × ITL/2) × OL² + (RPS × (T_pref/2 + ITL × IL)) × OL + (RPS × T_pref × IL - 0.8 × KV) = 0
        
        a = target_rps * itl_at_80 / 2
        b = target_rps * (tpref_at_80 / 2 + itl_at_80 * target_il)
        c = target_rps * tpref_at_80 * target_il - 0.8 * kv_capacity
        
        # Solve quadratic
        discriminant = b**2 - 4*a*c
        if discriminant >= 0 and a != 0:
            ol1 = (-b + np.sqrt(discriminant)) / (2*a)
            ol2 = (-b - np.sqrt(discriminant)) / (2*a)
            # Take the larger positive solution (we want max OL)
            candidates = [x for x in [ol1, ol2] if x > 0]
            predicted_ol_kv = max(candidates) if candidates else float('inf')
        else:
            predicted_ol_kv = float('inf')
        
        # Secondary check: Detect if ρ starts accelerating
        # In non-saturated region, ρ should be relatively stable
        # At saturation, ρ explodes
        ol_vals = non_sat_data['OL'].values
        rho_vals = non_sat_data['rho'].values
        
        if len(ol_vals) >= 3:
            # Sort by OL
            sorted_idx = np.argsort(ol_vals)
            ol_sorted = ol_vals[sorted_idx]
            rho_sorted = rho_vals[sorted_idx]
            
            # Compute rate of change of ρ
            drho_dol = np.gradient(rho_sorted, ol_sorted)
            
            # Find where ρ starts increasing significantly
            # In stable region, dρ/dOL should be near zero or slightly negative
            # At saturation onset, it becomes positive and large
            rho_stable_mean = np.mean(rho_sorted[:len(rho_sorted)//2])  # Use first half
            
            # Predict OL where ρ would double from stable value
            # This is a heuristic for "ρ explosion"
            rho_threshold = 2 * rho_stable_mean
            
            # Extrapolate: assume ρ stays stable until KV ceiling
            predicted_ol_rho = float('inf')  # Default: no ρ-based limit
            
        else:
            predicted_ol_rho = float('inf')
        
        # For vary-OL experiments, KV ceiling is the primary mechanism
        predicted_ol = predicted_ol_kv
        method = 'KV_ceiling'
        
        return {
            'predicted_value': predicted_ol,
            'method': method,
            'predicted_ol_kv': predicted_ol_kv,
            'predicted_ol_rho': predicted_ol_rho,
            'itl_at_80': itl_at_80,
            'tpref_at_80': tpref_at_80,
            'a': a,
            'b': b,
            'c': c,
            'discriminant': discriminant
        }
    
    def validate_experiment(self, test_name: str) -> Dict:
        """
        Validate predictions for a single experiment.
        Automatically detects experiment type and uses appropriate prediction method.
        """
        exp_data = self.df[self.df['test_name'] == test_name].copy()
        
        if len(exp_data) == 0:
            return None
        
        # Classify experiment type
        exp_info = self.classify_experiment_type(exp_data)
        
        print(f"\n{'='*80}")
        print(f"Validating: {test_name}")
        print(f"  Type: {exp_info['type']} (varying {exp_info['varying_param']})")
        print(f"  Base config: IL={exp_info['base_il']:.0f}, OL={exp_info['base_ol']:.0f}, RPS={exp_info['base_rps']:.1f}")
        
        # Sort by the varying parameter
        if exp_info['type'] == 'vary_rps':
            exp_data = exp_data.sort_values('RPS').reset_index(drop=True)
        elif exp_info['type'] == 'vary_il':
            exp_data = exp_data.sort_values('IL').reset_index(drop=True)
        elif exp_info['type'] == 'vary_ol':
            exp_data = exp_data.sort_values('OL').reset_index(drop=True)
        
        # Split into non-saturated and saturated
        non_sat = exp_data[~exp_data['is_saturated']].copy()
        saturated = exp_data[exp_data['is_saturated']].copy()
        
        if len(non_sat) < 2:
            print(f"  ⚠️  Not enough non-saturated data ({len(non_sat)} points)")
            return None
        
        print(f"  Non-saturated: {len(non_sat)} points")
        print(f"  Saturated: {len(saturated)} points")
        
        # Estimate KV capacity
        kv_capacity = self.estimate_kv_capacity(non_sat)
        print(f"  Estimated KV capacity: {kv_capacity:.0f} tokens")
        
        # Predict based on experiment type
        if exp_info['type'] == 'vary_rps':
            prediction = self.predict_max_rps(non_sat, exp_info['base_il'], 
                                              exp_info['base_ol'], kv_capacity)
            actual_max = non_sat['RPS'].max()
            actual_sat = saturated['RPS'].min() if len(saturated) > 0 else None
            param_name = 'RPS'
            
        elif exp_info['type'] == 'vary_il':
            prediction = self.predict_max_il(non_sat, exp_info['base_ol'],
                                            exp_info['base_rps'], kv_capacity)
            actual_max = non_sat['IL'].max()
            actual_sat = saturated['IL'].min() if len(saturated) > 0 else None
            param_name = 'IL'
            
        elif exp_info['type'] == 'vary_ol':
            prediction = self.predict_max_ol(non_sat, exp_info['base_il'],
                                            exp_info['base_rps'], kv_capacity)
            actual_max = non_sat['OL'].max()
            actual_sat = saturated['OL'].min() if len(saturated) > 0 else None
            param_name = 'OL'
        else:
            print(f"  ⚠️  Unknown experiment type")
            return None
        
        predicted_max = prediction['predicted_value']
        
        print(f"\n  {param_name} Prediction:")
        print(f"    Method: {prediction['method']}")
        print(f"    Predicted max {param_name}: {predicted_max:.2f}")
        print(f"    Actual max {param_name}: {actual_max:.2f}")
        if actual_sat:
            print(f"    Actual saturation {param_name}: {actual_sat:.2f}")
            error_pct = abs(predicted_max - actual_max) / actual_max * 100
            print(f"    Prediction error: {error_pct:.1f}%")
        else:
            error_pct = np.nan
        
        return {
            'test_name': test_name,
            'exp_type': exp_info['type'],
            'varying_param': param_name,
            'base_il': exp_info['base_il'],
            'base_ol': exp_info['base_ol'],
            'base_rps': exp_info['base_rps'],
            'kv_capacity': kv_capacity,
            'prediction_method': prediction['method'],
            'predicted_max': predicted_max,
            'actual_max': actual_max,
            'actual_sat': actual_sat,
            'error_pct': error_pct,
            'non_sat_count': len(non_sat),
            'sat_count': len(saturated),
            'prediction_details': prediction
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
                'exp_type': r['exp_type'],
                'varying_param': r['varying_param'],
                'IL': r['base_il'],
                'OL': r['base_ol'],
                'RPS': r['base_rps'],
                'kv_capacity': r['kv_capacity'],
                'method': r['prediction_method'],
                'predicted_max': r['predicted_max'],
                'actual_max': r['actual_max'],
                'actual_sat': r['actual_sat'],
                'error_pct': r['error_pct'],
                'non_sat_points': r['non_sat_count'],
                'sat_points': r['sat_count']
            })
        
        return pd.DataFrame(summary_data)


def main():
    """Main validation workflow."""
    print("="*80)
    print("Comprehensive Saturation Prediction Validation v3")
    print("="*80)
    
    predictor = ComprehensiveSaturationPredictor('WVA_data160426_short.csv')
    
    print("\n" + "="*80)
    print("VALIDATING ALL EXPERIMENTS")
    print("="*80)
    
    summary_df = predictor.validate_all_experiments()
    
    # Save results
    summary_df.to_csv('validation_summary_v3.csv', index=False)
    print(f"\n{'='*80}")
    print("Saved: validation_summary_v3.csv")
    
    # Print summary by experiment type
    print(f"\n{'='*80}")
    print("VALIDATION SUMMARY BY EXPERIMENT TYPE")
    print("="*80)
    
    for exp_type in ['vary_rps', 'vary_il', 'vary_ol']:
        type_data = summary_df[summary_df['exp_type'] == exp_type]
        if len(type_data) > 0:
            print(f"\n{exp_type.upper()} Experiments ({len(type_data)}):")
            print(type_data[['test_name', 'varying_param', 'predicted_max', 'actual_max', 'error_pct']].to_string(index=False))
            
            valid_errors = type_data['error_pct'].dropna()
            if len(valid_errors) > 0:
                print(f"  Mean error: {valid_errors.mean():.1f}%")
                print(f"  Median error: {valid_errors.median():.1f}%")
    
    # Overall statistics
    print(f"\n{'='*80}")
    print("OVERALL STATISTICS")
    print("="*80)
    
    valid_errors = summary_df['error_pct'].dropna()
    if len(valid_errors) > 0:
        print(f"Prediction Error Across All Types:")
        print(f"  Mean: {valid_errors.mean():.1f}%")
        print(f"  Median: {valid_errors.median():.1f}%")
        print(f"  Std: {valid_errors.std():.1f}%")
        print(f"  Min: {valid_errors.min():.1f}%")
        print(f"  Max: {valid_errors.max():.1f}%")
        print(f"  Experiments with <20% error: {(valid_errors < 20).sum()}/{len(valid_errors)}")
        print(f"  Experiments with <10% error: {(valid_errors < 10).sum()}/{len(valid_errors)}")
    
    print(f"\n{'='*80}")
    print("VALIDATION COMPLETE")
    print("="*80)


if __name__ == '__main__':
    main()

# Made with Bob
