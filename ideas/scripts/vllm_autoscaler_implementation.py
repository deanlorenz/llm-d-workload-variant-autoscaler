#!/usr/bin/env python3
"""
vLLM Autoscaler Implementation Example

This module demonstrates how to implement autoscaling for vLLM based on
the H100 capacity analysis and runtime monitoring guidelines.
"""

import math
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta


@dataclass
class VLLMMetrics:
    """Current vLLM metrics from Prometheus."""
    kv_cache_usage_perc: float  # 0.0 to 1.0
    num_requests_running: int
    num_requests_waiting: int
    e2e_latency_avg: float  # seconds
    e2e_latency_p50: float
    e2e_latency_p95: float
    rps: float  # requests per second
    prompt_tokens_rate: float  # tokens/sec
    generation_tokens_rate: float  # tokens/sec
    timestamp: datetime


@dataclass
class WorkloadProfile:
    """Workload characteristics."""
    avg_input_tokens: float
    avg_output_tokens: float
    
    @classmethod
    def from_metrics(cls, metrics: VLLMMetrics) -> 'WorkloadProfile':
        """Estimate workload profile from metrics."""
        if metrics.rps > 0:
            avg_input = metrics.prompt_tokens_rate / metrics.rps
            avg_output = metrics.generation_tokens_rate / metrics.rps
        else:
            avg_input = 0
            avg_output = 0
        
        return cls(
            avg_input_tokens=avg_input,
            avg_output_tokens=avg_output
        )


@dataclass
class CapacityEstimate:
    """Estimated capacity for current workload."""
    N_max: float  # Maximum concurrent requests
    E2E_max: float  # E2E latency at max capacity
    RPS_max_theoretical: float
    RPS_max_safe: float  # With 10% safety margin
    headroom_pct: float  # Current headroom percentage


@dataclass
class ScalingDecision:
    """Autoscaling decision."""
    action: str  # 'scale_out', 'scale_in', 'none'
    current_instances: int
    target_instances: int
    instances_to_change: int
    reason: str
    urgency: str  # 'urgent', 'high', 'normal', 'low'
    projected_utilization: Optional[float] = None


class H100CapacityTable:
    """
    Capacity lookup table based on H100 analysis.
    Maps (input_tokens, output_tokens) to (N_max, max_rps) at 80% KV cache.
    """
    
    # Data from h100_capacity_analysis_results.md
    CAPACITY_DATA = {
        (1000, 300): {'N_max': 6, 'max_rps': 2.0, 'kv_pct': 0.02},
        (3000, 300): {'N_max': 64, 'max_rps': 7.0, 'kv_pct': 0.51},
        (5000, 100): {'N_max': 7, 'max_rps': 2.0, 'kv_pct': 0.09},
        (5000, 200): {'N_max': 10, 'max_rps': 2.0, 'kv_pct': 0.13},
        (5000, 300): {'N_max': 49, 'max_rps': 4.0, 'kv_pct': 0.66},
        (5000, 400): {'N_max': 16, 'max_rps': 2.0, 'kv_pct': 0.22},
        (5000, 500): {'N_max': 25, 'max_rps': 2.0, 'kv_pct': 0.35},
        (5000, 600): {'N_max': 26, 'max_rps': 2.0, 'kv_pct': 0.36},
        (5000, 700): {'N_max': 45, 'max_rps': 2.0, 'kv_pct': 0.60},
        (5000, 800): {'N_max': 45, 'max_rps': 2.0, 'kv_pct': 0.60},
        (5000, 900): {'N_max': 45, 'max_rps': 2.0, 'kv_pct': 0.60},
        (5000, 1000): {'N_max': 51, 'max_rps': 2.0, 'kv_pct': 0.70},
        (5000, 1100): {'N_max': 50, 'max_rps': 2.0, 'kv_pct': 0.70},
        (5000, 1200): {'N_max': 58, 'max_rps': 2.0, 'kv_pct': 0.80},
        (7000, 300): {'N_max': 14, 'max_rps': 2.0, 'kv_pct': 0.26},
        (9000, 300): {'N_max': 25, 'max_rps': 2.0, 'kv_pct': 0.60},
    }
    
    @classmethod
    def get_capacity(cls, input_tokens: float, output_tokens: float) -> Dict:
        """
        Get capacity estimate for given workload.
        Uses nearest neighbor if exact match not found.
        """
        # Round to nearest hundred for input, nearest hundred for output
        in_tok = round(input_tokens / 100) * 100
        out_tok = round(output_tokens / 100) * 100
        
        # Try exact match
        key = (in_tok, out_tok)
        if key in cls.CAPACITY_DATA:
            return cls.CAPACITY_DATA[key]
        
        # Find nearest neighbor
        min_distance = float('inf')
        nearest_key = None
        
        for k in cls.CAPACITY_DATA.keys():
            # Weighted distance (input tokens matter more for KV cache)
            distance = abs(k[0] - in_tok) * 2 + abs(k[1] - out_tok)
            if distance < min_distance:
                min_distance = distance
                nearest_key = k
        
        return cls.CAPACITY_DATA[nearest_key]


class CapacityPredictor:
    """Predicts maximum capacity from current metrics."""
    
    @staticmethod
    def predict_max_capacity(
        current_kv_pct: float,
        current_N: int,
        current_E2E: float,
        current_RPS: float,
        saturation_threshold: float = 0.80
    ) -> CapacityEstimate:
        """
        Predict maximum capacity at saturation threshold.
        
        Args:
            current_kv_pct: Current KV cache utilization (0.0-1.0)
            current_N: Current concurrent requests
            current_E2E: Current E2E latency (seconds)
            current_RPS: Current requests per second
            saturation_threshold: Target KV cache threshold (default: 0.80)
        
        Returns:
            CapacityEstimate with predicted values
        """
        if current_kv_pct <= 0:
            current_kv_pct = 0.01  # Avoid division by zero
        
        # Predict N_max (linear extrapolation)
        N_max = current_N * (saturation_threshold / current_kv_pct)
        
        # Predict E2E increase (non-linear model)
        util_ratio = saturation_threshold / current_kv_pct
        
        if util_ratio <= 1.0:
            # Already at or above threshold
            E2E_factor = 1.0
        elif util_ratio < 1.5:
            # Small increase: linear (20% increase per 1.0 ratio)
            E2E_factor = 1.0 + 0.2 * (util_ratio - 1.0)
        else:
            # Large increase: quadratic (more conservative)
            E2E_factor = 1.0 + 0.5 * ((util_ratio - 1.0) ** 1.5)
        
        E2E_max = current_E2E * E2E_factor
        
        # Calculate max RPS
        RPS_max_theoretical = N_max / E2E_max if E2E_max > 0 else 0
        
        # Apply 10% safety margin
        RPS_max_safe = RPS_max_theoretical * 0.9
        
        # Calculate current headroom
        if current_RPS > 0:
            headroom_pct = ((RPS_max_safe / current_RPS) - 1.0) * 100
        else:
            headroom_pct = 100.0
        
        return CapacityEstimate(
            N_max=N_max,
            E2E_max=E2E_max,
            RPS_max_theoretical=RPS_max_theoretical,
            RPS_max_safe=RPS_max_safe,
            headroom_pct=headroom_pct
        )


class VLLMAutoscaler:
    """Main autoscaler implementation."""
    
    def __init__(
        self,
        scale_out_threshold: float = 0.65,
        scale_in_threshold: float = 0.40,
        target_utilization: float = 0.60,
        min_instances: int = 1,
        max_instances: int = 10,
        cooldown_period_seconds: int = 300,
        use_capacity_table: bool = True
    ):
        """
        Initialize autoscaler.
        
        Args:
            scale_out_threshold: KV cache % to trigger scale-out (default: 65%)
            scale_in_threshold: KV cache % to trigger scale-in (default: 40%)
            target_utilization: Target KV cache % after scaling (default: 60%)
            min_instances: Minimum number of instances (default: 1)
            max_instances: Maximum number of instances (default: 10)
            cooldown_period_seconds: Cooldown between scaling actions (default: 300s)
            use_capacity_table: Use H100 capacity table for predictions (default: True)
        """
        self.scale_out_threshold = scale_out_threshold
        self.scale_in_threshold = scale_in_threshold
        self.target_utilization = target_utilization
        self.min_instances = min_instances
        self.max_instances = max_instances
        self.cooldown_period = timedelta(seconds=cooldown_period_seconds)
        self.use_capacity_table = use_capacity_table
        
        self.last_scaling_action: Optional[datetime] = None
        self.capacity_predictor = CapacityPredictor()
    
    def _in_cooldown(self) -> bool:
        """Check if we're in cooldown period."""
        if self.last_scaling_action is None:
            return False
        
        return datetime.now() - self.last_scaling_action < self.cooldown_period
    
    def _check_urgent_conditions(self, metrics: VLLMMetrics) -> Optional[str]:
        """Check for urgent scaling conditions."""
        # High KV cache
        if metrics.kv_cache_usage_perc >= 0.75:
            return f'KV cache at {metrics.kv_cache_usage_perc*100:.1f}%'
        
        # Queue building up
        if metrics.num_requests_waiting > 10:
            return f'Queue depth: {metrics.num_requests_waiting}'
        
        # Severe latency degradation
        if metrics.e2e_latency_p95 > metrics.e2e_latency_p50 * 3.0:
            return f'P95 latency {metrics.e2e_latency_p95:.2f}s >> P50 {metrics.e2e_latency_p50:.2f}s'
        
        return None
    
    def _calculate_scale_out_count(
        self,
        current_kv_pct: float,
        target_kv_pct: Optional[float] = None
    ) -> int:
        """Calculate how many instances to add."""
        if target_kv_pct is None:
            target_kv_pct = self.target_utilization
        
        if current_kv_pct <= target_kv_pct:
            return 0
        
        # Calculate required instances to reach target utilization
        required_instances = math.ceil(current_kv_pct / target_kv_pct)
        instances_to_add = required_instances - 1
        
        return max(1, instances_to_add)
    
    def make_scaling_decision(
        self,
        metrics: VLLMMetrics,
        current_instances: int,
        workload_profile: Optional[WorkloadProfile] = None
    ) -> ScalingDecision:
        """
        Make autoscaling decision based on current metrics.
        
        Args:
            metrics: Current vLLM metrics
            current_instances: Current number of instances
            workload_profile: Optional workload characteristics
        
        Returns:
            ScalingDecision with recommended action
        """
        kv_cache_pct = metrics.kv_cache_usage_perc
        
        # Check for urgent conditions (override cooldown)
        urgent_reason = self._check_urgent_conditions(metrics)
        if urgent_reason:
            instances_to_add = self._calculate_scale_out_count(kv_cache_pct)
            new_total = min(current_instances + instances_to_add, self.max_instances)
            
            self.last_scaling_action = datetime.now()
            
            return ScalingDecision(
                action='scale_out',
                current_instances=current_instances,
                target_instances=new_total,
                instances_to_change=new_total - current_instances,
                reason=urgent_reason,
                urgency='urgent'
            )
        
        # Check cooldown for non-urgent actions
        if self._in_cooldown():
            return ScalingDecision(
                action='none',
                current_instances=current_instances,
                target_instances=current_instances,
                instances_to_change=0,
                reason='In cooldown period',
                urgency='none'
            )
        
        # Scale out decision
        if kv_cache_pct >= self.scale_out_threshold:
            instances_to_add = self._calculate_scale_out_count(kv_cache_pct)
            new_total = min(current_instances + instances_to_add, self.max_instances)
            
            urgency = 'high' if kv_cache_pct >= 0.70 else 'normal'
            
            self.last_scaling_action = datetime.now()
            
            return ScalingDecision(
                action='scale_out',
                current_instances=current_instances,
                target_instances=new_total,
                instances_to_change=new_total - current_instances,
                reason=f'KV cache at {kv_cache_pct*100:.1f}%',
                urgency=urgency
            )
        
        # Scale in decision
        if kv_cache_pct <= self.scale_in_threshold and current_instances > self.min_instances:
            # Conservative: remove 1 instance at a time
            # Check if we can maintain target utilization
            projected_kv = kv_cache_pct * (current_instances / (current_instances - 1))
            
            if projected_kv <= self.target_utilization:
                self.last_scaling_action = datetime.now()
                
                return ScalingDecision(
                    action='scale_in',
                    current_instances=current_instances,
                    target_instances=current_instances - 1,
                    instances_to_change=-1,
                    reason=f'KV cache at {kv_cache_pct*100:.1f}%, projected {projected_kv*100:.1f}%',
                    urgency='low',
                    projected_utilization=projected_kv
                )
        
        # No action needed
        return ScalingDecision(
            action='none',
            current_instances=current_instances,
            target_instances=current_instances,
            instances_to_change=0,
            reason=f'Within target range ({kv_cache_pct*100:.1f}%)',
            urgency='none'
        )
    
    def get_capacity_estimate(
        self,
        metrics: VLLMMetrics,
        workload_profile: Optional[WorkloadProfile] = None
    ) -> CapacityEstimate:
        """
        Get capacity estimate for current workload.
        
        Args:
            metrics: Current vLLM metrics
            workload_profile: Optional workload characteristics
        
        Returns:
            CapacityEstimate
        """
        if self.use_capacity_table and workload_profile:
            # Use capacity table for more accurate prediction
            capacity_data = H100CapacityTable.get_capacity(
                workload_profile.avg_input_tokens,
                workload_profile.avg_output_tokens
            )
            
            # Adjust based on current utilization
            scale_factor = capacity_data['kv_pct'] / metrics.kv_cache_usage_perc if metrics.kv_cache_usage_perc > 0 else 1.0
            
            return CapacityEstimate(
                N_max=capacity_data['N_max'],
                E2E_max=metrics.e2e_latency_avg * (1.0 / scale_factor),
                RPS_max_theoretical=capacity_data['max_rps'],
                RPS_max_safe=capacity_data['max_rps'] * 0.9,
                headroom_pct=((capacity_data['max_rps'] * 0.9 / metrics.rps) - 1.0) * 100 if metrics.rps > 0 else 100.0
            )
        else:
            # Use prediction model
            return self.capacity_predictor.predict_max_capacity(
                metrics.kv_cache_usage_perc,
                metrics.num_requests_running,
                metrics.e2e_latency_avg,
                metrics.rps
            )


def main():
    """Example usage."""
    
    # Example metrics from a running vLLM instance
    metrics = VLLMMetrics(
        kv_cache_usage_perc=0.68,  # 68%
        num_requests_running=35,
        num_requests_waiting=2,
        e2e_latency_avg=6.5,
        e2e_latency_p50=6.0,
        e2e_latency_p95=8.5,
        rps=5.2,
        prompt_tokens_rate=26000,  # 5000 tokens/req * 5.2 req/s
        generation_tokens_rate=1560,  # 300 tokens/req * 5.2 req/s
        timestamp=datetime.now()
    )
    
    # Estimate workload profile
    workload = WorkloadProfile.from_metrics(metrics)
    print(f"Workload Profile:")
    print(f"  Avg Input Tokens: {workload.avg_input_tokens:.0f}")
    print(f"  Avg Output Tokens: {workload.avg_output_tokens:.0f}")
    print()
    
    # Create autoscaler
    autoscaler = VLLMAutoscaler(
        scale_out_threshold=0.65,
        scale_in_threshold=0.40,
        target_utilization=0.60,
        min_instances=1,
        max_instances=10
    )
    
    # Get capacity estimate
    capacity = autoscaler.get_capacity_estimate(metrics, workload)
    print(f"Capacity Estimate:")
    print(f"  N_max: {capacity.N_max:.0f} concurrent requests")
    print(f"  E2E at max: {capacity.E2E_max:.2f}s")
    print(f"  Max RPS (safe): {capacity.RPS_max_safe:.2f}")
    print(f"  Current headroom: {capacity.headroom_pct:.1f}%")
    print()
    
    # Make scaling decision
    current_instances = 1
    decision = autoscaler.make_scaling_decision(metrics, current_instances, workload)
    
    print(f"Scaling Decision:")
    print(f"  Action: {decision.action}")
    print(f"  Current Instances: {decision.current_instances}")
    print(f"  Target Instances: {decision.target_instances}")
    print(f"  Instances to Change: {decision.instances_to_change:+d}")
    print(f"  Reason: {decision.reason}")
    print(f"  Urgency: {decision.urgency}")
    
    if decision.projected_utilization:
        print(f"  Projected Utilization: {decision.projected_utilization*100:.1f}%")


if __name__ == '__main__':
    main()

# Made with Bob
