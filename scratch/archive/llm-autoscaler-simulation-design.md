
# LLM Autoscaler Simulation Environment - Design Document

## 1. Executive Summary

This document describes the design of a discrete-event simulation environment for testing and validating autoscaling algorithms for LLM inference workloads. The simulation models vLLM behavior with high fidelity while running 10-60x faster than real-time, enabling rapid iteration on autoscaling strategies.

### Key Design Principles

1. **High-fidelity vLLM modeling**: Capture prefill/decode dynamics, KV cache constraints, and interference effects
2. **Time acceleration**: Run simulations 10-60x faster than real-time for rapid experimentation
3. **K8s integration**: Reuse real HPA controllers and metrics APIs where possible
4. **Pluggable autoscalers**: Easy to test different scaling algorithms and compare results
5. **Configurable workloads**: Support diverse IL/OL distributions and arrival patterns
6. **Comprehensive metrics**: Track SLOs (TTFT, TPOT), utilization, and stability indicators

### Target Use Cases

- **Algorithm comparison**: Test reactive vs proactive scaling, different utilization thresholds
- **Stability validation**: Identify oscillation conditions and feedback loop instabilities
- **Workload benchmarking**: Evaluate performance across diverse request patterns
- **Parameter tuning**: Optimize scaling thresholds, smoothing factors, and control gains

---

## 2. Requirements and Constraints

### 2.1 Functional Requirements

**FR1: vLLM Replica Simulation**
- Model prefill phase: time = f(input_tokens, cache_hits, concurrency)
- Model decode phase: time = f(output_tokens, active_sequences, KV_utilization)
- Model KV cache: hard memory limit, eviction policies
- Model prefill/decode interference: chunked scheduling, preemption
- Model continuous batching: dynamic request admission and scheduling

**FR2: Workload Generation**
- Configurable arrival process: Poisson, bursty, periodic patterns
- Configurable IL distribution: uniform, normal, long-tail, bimodal
- Configurable OL distribution: uniform, normal, long-tail, bimodal
- Configurable shared prefix patterns: simulate prompt caching benefits
- Support workload transitions: sudden load changes, diurnal patterns

**FR3: Autoscaler Testing Framework**
- Plugin architecture for different scaling algorithms
- Support for both reactive (utilization-based) and proactive (rate-based) strategies
- Configurable scaling parameters: thresholds, smoothing, delays
- Support for multi-dimensional scaling (prefill + decode channels)

**FR4: Metrics and Observability**
- Per-request metrics: TTFT, TPOT, queue time, total latency
- Per-replica metrics: KV utilization, active sequences, prefill/decode load
- Aggregate metrics: P50/P95/P99 latencies, throughput, SLO violations
- Autoscaler metrics: scaling decisions, replica count over time, utilization

**FR5: K8s Integration**
- Mock K8s API server for HPA interaction
- Support real HPA controller with simulated metrics
- Simulate pod lifecycle: startup time, readiness, termination grace period
- Simulate metric collection delays and staleness

**FR6: Time Acceleration**
- Configurable speedup factor (10-60x)
- Discrete-event simulation for accurate timing
- Proper handling of concurrent events and causality
- Reproducible results with fixed random seeds

### 2.2 Non-Functional Requirements

**NFR1: Performance**
- Simulate 1 hour of workload in 1-6 minutes (10-60x speedup)
- Support 100+ concurrent replicas in simulation
- Handle 1000+ requests/second arrival rate (simulated time)

**NFR2: Accuracy**
- vLLM timing models within 20% of real system behavior
- Capture key nonlinear effects: saturation, interference, queueing
- Validate against production traces where available

**NFR3: Usability**
- Simple YAML configuration for experiments
- Clear output format for analysis (CSV, JSON, Parquet)
- Built-in visualization for common metrics
- Comprehensive logging for debugging

**NFR4: Extensibility**
- Easy to add new autoscaling algorithms
- Easy to modify vLLM behavior models
- Easy to add new workload patterns
- Modular architecture for component replacement

### 2.3 Constraints and Simplifications

**Simplification 1: No Load Balancing**
- Assume requests are uniformly distributed across replicas
- No need to model routing algorithms or connection pooling
- Focus on per-replica behavior and aggregate capacity

**Simplification 2: No Network Modeling**
- Ignore network latency and bandwidth constraints
- Assume instant communication between components
- Focus on compute and memory bottlenecks

**Simplification 3: Homogeneous Replicas**
- All replicas have identical hardware characteristics
- No GPU heterogeneity (can be added later if needed)
- Simplifies capacity calculations

**Simplification 4: Perfect Observability**
- Metrics are instantly available (with configurable delay)
- No metric collection failures or gaps
- Focus on control algorithm behavior

---

## 3. Architecture Overview

### 3.1 Component Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Simulation Environment                       │
│                                                                   │
│  ┌────────────────┐         ┌──────────────────┐                │
│  │   Workload     │────────▶│  Request Queue   │                │
│  │   Generator    │         └──────────────────┘                │
│  └────────────────┘                  │                           │
│                                      │                           │
│                                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐        │
│  │            vLLM Replica Pool                        │        │
│  │  ┌──────────┐  ┌──────────┐  ┌──────────┐         │        │
│  │  │ Replica 1│  │ Replica 2│  │ Replica N│  ...    │        │
│  │  │          │  │          │  │          │         │        │
│  │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │         │        │
│  │  │ │Prefill│ │  │ │Prefill│ │  │ │Prefill│ │         │        │
│  │  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │         │        │
│  │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │         │        │
│  │  │ │Decode │ │  │ │Decode │ │  │ │Decode │ │         │        │
│  │  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │         │        │
│  │  │ ┌──────┐ │  │ ┌──────┐ │  │ ┌──────┐ │         │        │
│  │  │ │KV Mem│ │  │ │KV Mem│ │  │ │KV Mem│ │         │        │
│  │  │ └──────┘ │  │ └──────┘ │  │ └──────┘ │         │        │
│  │  └──────────┘  └──────────┘  └──────────┘         │        │
│  └─────────────────────────────────────────────────────┘        │
│                                      │                           │
│                                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐        │
│  │            Metrics Collector                        │        │
│  │  - Per-request: TTFT, TPOT, latency                │        │
│  │  - Per-replica: KV util, active seqs, load         │        │
│  │  - Aggregate: throughput, SLO violations           │        │
│  └─────────────────────────────────────────────────────┘        │
│                                      │                           │
│                                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐        │
│  │         Mock K8s Metrics API                        │        │
│  │  - Exposes metrics in K8s format                    │        │
│  │  - Simulates metric staleness/delay                │        │
│  └─────────────────────────────────────────────────────┘        │
│                                      │                           │
│                                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐        │
│  │            Autoscaler Plugin                        │        │
│  │  - Reads metrics from K8s API                       │        │
│  │  - Computes desired replica count                  │        │
│  │  - Issues scale commands                            │        │
│  └─────────────────────────────────────────────────────┘        │
│                                      │                           │
│                                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐        │
│  │         Replica Lifecycle Manager                   │        │
│  │  - Handles pod creation/deletion                    │        │
│  │  - Simulates startup/shutdown delays                │        │
│  │  - Manages replica pool                             │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
│  ┌─────────────────────────────────────────────────────┐        │
│  │         Discrete Event Scheduler                    │        │
│  │  - Manages simulation time                          │        │
│  │  - Schedules and dispatches events                  │        │
│  │  - Handles time acceleration                        │        │
│  └─────────────────────────────────────────────────────┘        │
│                                                                   │
└─────────────────────────────────────────────────────────────────┘
                                 │
                                 ▼
                    ┌────────────────────────┐
                    │   Analysis & Viz       │
                    │  - Time series plots   │
                    │  - SLO dashboards      │
                    │  - Comparison reports  │
                    └────────────────────────┘
```

### 3.2 Technology Stack

**Core Simulation**
- **SimPy**: Discrete-event simulation framework
- **Python 3.11+**: Main implementation language
- **NumPy/SciPy**: Statistical distributions and numerical operations

**K8s Integration**
- **kubernetes-client**: Python K8s API client
- **Custom mock server**: Lightweight K8s API simulator for metrics

**Data & Analysis**
- **Pandas**: Data manipulation and analysis
- **Polars**: High-performance alternative for large datasets
- **Matplotlib/Plotly**: Visualization
- **Parquet**: Efficient storage for time-series data

**Configuration & Testing**
- **Pydantic**: Configuration validation and type safety
- **PyYAML**: Configuration file parsing
- **pytest**: Unit and integration testing
- **hypothesis**: Property-based testing for edge cases

---

## 4. Core Components Design

### 4.1 Discrete Event Scheduler

The scheduler is the heart of the simulation, managing virtual time and event dispatch.

**Key Responsibilities:**
- Maintain simulation clock (virtual time)
- Schedule events with precise timestamps
- Dispatch events in chronological order
- Handle concurrent events at same timestamp
- Support time acceleration (speedup factor)

**Implementation Approach:**
```python
class SimulationScheduler:
    def __init__(self, speedup_factor: float = 1.0):
        self.env = simpy.Environment()
        self.speedup_factor = speedup_factor
        self.start_real_time = None
        self.start_sim_time = 0
        
    def now(self) -> float:
        """Current simulation time in seconds"""
        return self.env.now
        
    def schedule(self, delay: float, callback: Callable):
        """Schedule callback after delay (sim seconds)"""
        self.env.process(self._delayed_callback(delay, callback))
        
    def run(self, until: float):
        """Run simulation until specified time"""
        self.start_real_time = time.time()
        self.start_sim_time = self.env.now
        self.env.run(until=until)
        
    def real_time_elapsed(self) -> float:
        """Actual wall-clock time elapsed"""
        return time.time() - self.start_real_time
        
    def sim_time_elapsed(self) -> float:
        """Simulated time elapsed"""
        return self.env.now - self.start_sim_time
```

**Time Acceleration:**
- SimPy naturally runs as fast as possible (event-driven)
- No artificial delays between events
- Speedup factor used for:
  - Reporting progress in real-time
  - Throttling metric collection if needed
  - Synchronizing with external systems (optional)

---

## 5. vLLM Replica Behavior Model

This is the most critical component - it must accurately capture the nonlinear dynamics described in [`chatAS.md`](chatAS.md).

### 5.1 Model Parameters

**Hardware Characteristics:**
```python
@dataclass
class GPUConfig:
    # Prefill capacity
    prefill_tokens_per_sec: float = 10000  # tokens/sec at low load
    prefill_batch_size: int = 256  # max tokens in prefill batch
    
    # Decode capacity  
    decode_tokens_per_sec: float = 2000  # tokens/sec per sequence
    max_sequences: int = 128  # hardware limit
    
    # Memory
    kv_cache_size_gb: float = 80  # total KV cache memory
    bytes_per_token: int = 128  # KV cache per token
    
    # Timing
    context_switch_overhead_ms: float = 1.0
    preemption_overhead_ms: float = 2.0
```

**Behavioral Parameters:**
```python
@dataclass
class VLLMConfig:
    # Scheduling
    max_batch_size: int = 256
    max_num_seqs: int = 128
    chunked_prefill_size: int = 512  # tokens per chunk
    
    # Cache
    enable_prefix_caching: bool = True
    cache_hit_rate: float = 0.3  # for shared prefixes
    
    # Performance
    prefill_decode_interference: float = 0.2  # decode slowdown during prefill
    load_dependent_slowdown: bool = True  # model saturation effects
```

### 5.2 Prefill Phase Model

**Basic Model:**
```
prefill_time = input_tokens / prefill_throughput
```

**With Chunking:**
```python
def compute_prefill_time(
    input_tokens: int,
    cache_hits: int,
    current_load: float,
    config: GPUConfig
) -> float:
    # Effective tokens after cache hits
    effective_tokens = input_tokens - cache_hits
    
    # Chunk the prefill
    num_chunks = math.ceil(effective_tokens / config.chunked_prefill_size)
    
    # Base throughput
    base_throughput = config.prefill_tokens_per_sec
    
    # Load-dependent slowdown (saturation effect)
    if current_load > 0.7:
        # Nonlinear slowdown near saturation
        slowdown = 1.0 + 2.0 * (current_load - 0.7) ** 2
        base_throughput /= slowdown
    
    # Time per chunk
    chunk_time = config.chunked_prefill_size / base_throughput
    
    # Total time with context switch overhead
    total_time = (num_chunks * chunk_time + 
                  (num_chunks - 1) * config.context_switch_overhead_ms / 1000)
    
    return total_time
```

**Cache Hit Modeling:**
```python
def compute_cache_hits(
    request: Request,
    cache_state: CacheState,
    config: VLLMConfig
) -> int:
    if not config.enable_prefix_caching:
        return 0
    
    # Simple model: check for common prefixes
    for prefix_len in cache_state.common_prefixes:
        if request.prompt.startswith(cache_state.get_prefix(prefix_len)):
            return prefix_len
    
    # Probabilistic model for general case
    if random.random() < config.cache_hit_rate:
        return int(request.input_tokens * 0.5)  # 50% hit
    
    return 0
```

### 5.3 Decode Phase Model

**Basic Model:**
```
decode_time_per_token = 1 / (decode_throughput / num_active_sequences)
total_decode_time = output_tokens * decode_time_per_token
```

**With Load Effects:**
```python
def compute_decode_time(
    output_tokens: int,
    active_sequences: int,
    kv_utilization: float,
    config: GPUConfig
) -> float:
    # Base throughput per sequence
    base_tpot = config.decode_tokens_per_sec / active_sequences
    
    # Memory pressure slowdown
    if kv_utilization > 0.8:
        memory_slowdown = 1.0 + 3.0 * (kv_utilization - 0.8) ** 2
        base_tpot /= memory_slowdown
    
    # Concurrency slowdown (attention computation scales)
    if active_sequences > config.max_sequences * 0.7:
        concurrency_factor = active_sequences / (config.max_sequences * 0.7)
        base_tpot /= concurrency_factor ** 0.5
    
    # Time per token
    time_per_token = 1.0 / base_tpot
    
    # Total decode time
    return output_tokens * time_per_token
```

### 5.4 Prefill/Decode Interference

**Model:**
```python
def apply_interference(
    decode_tpot: float,
    prefill_active: bool,
    config: VLLMConfig
) -> float:
    """Decode slows down when prefill is running"""
    if prefill_active:
        return decode_tpot * (1.0 + config.prefill_decode_interference)
    return decode_tpot
```

### 5.5 KV Cache Management

**Memory Tracking:**
```python
class KVCacheManager:
    def __init__(self, config: GPUConfig):
        self.total_capacity = config.kv_cache_size_gb * 1e9
        self.bytes_per_token = config.bytes_per_token
        self.active_sequences: Dict[str, Sequence] = {}
        
    def can_admit(self, input_tokens: int, output_tokens: int) -> bool:
        """Check if request can be admitted"""
        required_bytes = (input_tokens + output_tokens) * self.bytes_per_token
        return self.used_bytes() + required_bytes <= self.total_capacity
        
    def utilization(self) -> float:
        """Current KV cache utilization [0, 1]"""
        return self.used_bytes() / self.total_capacity
        
    def used_bytes(self) -> int:
        """Total bytes used by active sequences"""
        return sum(
            (seq.input_tokens + seq.generated_tokens) * self.bytes_per_token
            for seq in self.active_sequences.values()
        )
        
    def admit_sequence(self, seq: Sequence):
        """Add sequence to cache"""
        self.active_sequences[seq.id] = seq
        
    def remove_sequence(self, seq_id: str):
        """Remove completed sequence"""
        del self.active_sequences[seq_id]
```

### 5.6 Continuous Batching Scheduler

**Request Admission:**
```python
class ContinuousBatchScheduler:
    def __init__(self, config: VLLMConfig, gpu_config: GPUConfig):
        self.config = config
        self.gpu_config = gpu_config
        self.kv_cache = KVCacheManager(gpu_config)
        self.waiting_queue: List[Request] = []
        self.running_sequences: List[Sequence] = []
        
    def try_admit_requests(self) -> List[Request]:
        """Try to admit waiting requests"""
        admitted = []
        
        for req in self.waiting_queue[:]:
            # Check sequence limit
            if len(self.running_sequences) >= self.config.max_num_seqs:
                break
                
            # Check KV cache capacity
            if not self.kv_cache.can_admit(req.input_tokens, req.output_tokens):
                break
                
            # Admit request
            self.waiting_queue.remove(req)
            admitted.append(req)
            
        return admitted
        
    def schedule_iteration(self) -> ScheduleDecision:
        """Decide what to run in next iteration"""
        # Try to admit new requests
        newly_admitted = self.try_admit_requests()
        
        # Decide between prefill and decode
        if newly_admitted and len(self.running_sequences) < self.config.max_num_seqs:
            # Run prefill for new requests
            return ScheduleDecision(
                action="prefill",
                requests=newly_admitted[:self.config.max_batch_size]
            )
        elif self.running_sequences:
            # Run decode for active sequences
            return ScheduleDecision(
                action="decode",
                sequences=self.running_sequences
            )
        else:
            # Idle
            return ScheduleDecision(action="idle")
```

---

## 6. Workload Generator Design

### 6.1 Arrival Process

**Poisson Process (baseline):**
```python
class PoissonArrivalProcess:
    def __init__(self, rate: float):
        self.rate = rate  # requests per second
        
    def generate_arrivals(self, duration: float) -> List[float]:
        """Generate arrival times for duration"""
        num_arrivals = np.random.poisson(self.rate * duration)
        return sorted(np.random.uniform(0, duration, num_arrivals))
```

**Bursty Traffic:**
```python
class BurstyArrivalProcess:
    def __init__(self, base_rate: float, burst_rate: float, 
                 burst_duration: float, burst_interval: float):
        self.base_rate = base_rate
        self.burst_rate = burst_rate
        self.burst_duration = burst_duration
        self.burst_interval = burst_interval
        
    def generate_arrivals(self, duration: float) -> List[float]:
        arrivals = []
        t = 0
        
        while t < duration:
            # Normal period
            normal_duration = self.burst_interval - self.burst_duration
            arrivals.extend(
                t + np.random.exponential(1/self.base_rate, 
                    int(self.base_rate * normal_duration))
            )
            t += normal_duration
            
            # Burst period
            if t < duration:
                arrivals.extend(
                    t + np.random.exponential(1/self.burst_rate,
                        int(self.burst_rate * self.burst_duration))
                )
                t += self.burst_duration
                
        return sorted([a for a in arrivals if a < duration])
```

**Diurnal Pattern:**
```python
class DiurnalArrivalProcess:
    def __init__(self, peak_rate: float, trough_rate: float, period: float = 86400):
        self.peak_rate = peak_rate
        self.trough_rate = trough_rate
        self.period = period
        
    def rate_at_time(self, t: float) -> float:
        """Rate varies sinusoidally"""
        phase = 2 * np.pi * t / self.period
        amplitude = (self.peak_rate - self.trough_rate) / 2
        midpoint = (self.peak_rate + self.trough_rate) / 2
        return midpoint + amplitude * np.sin(phase)
        
    def generate_arrivals(self, duration: float) -> List[float]:
        """Non-homogeneous Poisson process"""
        # Use thinning algorithm
        max_rate = self.peak_rate
        candidate_arrivals = np.random.exponential(1/max_rate, 
                                                   int(max_rate * duration * 1.5))
        candidate_times = np.cumsum(candidate_arrivals)
        
        # Accept with probability rate(t) / max_rate
        arrivals = []
        for t in candidate_times:
            if t >= duration:
                break
            if np.random.random() < self.rate_at_time(t) / max_rate:
                arrivals.append(t)
                
        return arrivals
```

### 6.2 Request Characteristics

**Token Length Distributions:**
```python
class TokenDistribution:
    @staticmethod
    def uniform(min_tokens: int, max_tokens: int) -> int:
        return np.random.randint(min_tokens, max_tokens + 1)
        
    @staticmethod
    def normal(mean: float, std: float, min_tokens: int = 1) -> int:
        return max(min_tokens, int(np.random.normal(mean, std)))
        
    @staticmethod
    def lognormal(mean: float, sigma: float) -> int:
        return int(np.random.lognormal(mean, sigma))
        
    @staticmethod
    def bimodal(mode1_mean: float, mode1_std: float, mode1_weight: float,
                mode2_mean: float, mode2_std: float) -> int:
        if np.random.random() < mode1_weight:
            return int(np.random.normal(mode1_mean, mode1_std))
        else:
            return int(np.random.normal(mode2_mean, mode2_std))
```

**Shared Prefix Modeling:**
```python
class SharedPrefixGenerator:
    def __init__(self, num_common_prefixes: int = 10, 
                 prefix_length_range: Tuple[int, int] = (100, 500),
                 prefix_probability: float = 0.3):
        self.num_prefixes = num_common_prefixes
        self.prefix_length_range = prefix_length_range
        self.prefix_prob = prefix_probability
        
        # Generate common prefixes
        self.prefixes = [
            self._generate_prefix() 
            for _ in range(num_common_prefixes)
        ]
        
    def _generate_prefix(self) -> str:
        length = np.random.randint(*self.prefix_length_range)
        return f"prefix_{length}_" + "x" * length
        
    def generate_prompt(self, total_tokens: int) -> Tuple[str, int]:
        """Returns (prompt, cache_hits)"""
        # Decide if using common prefix
        if np.random.random() < self.prefix_prob:
            prefix = np.random.choice(self.prefixes)
            prefix_len = len(prefix.split("_")[1])
            remaining = total_tokens - prefix_len
            suffix = "y" * max(0, remaining)
            return prefix + suffix, prefix_len
        else:
            return "z" * total_tokens, 0
```

**Request Generator:**
```python
class WorkloadGenerator:
    def __init__(self, config: WorkloadConfig):
        self.arrival_process = self._create_arrival_process(config)
        self.il_dist = config.input_length_distribution
        self.ol_dist = config.output_length_distribution
        self.prefix_gen = SharedPrefixGenerator(**config.prefix_config)
        
    def generate_workload(self, duration: float) -> List[Request]:
        """Generate complete workload for simulation"""
        arrival_times = self.arrival_process.generate_arrivals(duration)
        
        requests = []
        for i, arrival_time in enumerate(arrival_times):
            il = self.il_dist.sample()
            ol = self.ol_dist.sample()
            prompt, cache_hits = self.prefix_gen.generate_prompt(il)
            
            requests.append(Request(
                id=f"req_{i}",
                arrival_time=arrival_time,
                input_tokens=il,
                output_tokens=ol,
                prompt=prompt,
                expected_cache_hits=cache_hits
            ))
            
        return requests
```

### 6.3 Workload Configuration

```yaml
workload:
  duration: 3600  # 1 hour simulation
  
  arrival:
    type: "poisson"  # poisson | bursty | diurnal
    rate: 10  # requests/sec
    
    # For bursty
    burst_rate: 50
    burst_duration: 60
    burst_interval: 300
    
    # For diurnal
    peak_rate: 20
    trough_rate: 5
    period: 3600
    
  input_length:
    type: "normal"  # uniform | normal | lognormal | bimodal
    mean: 1000
    std: 300
    min: 100
    max: 8000
    
  output_length:
    type: "lognormal"
    mean: 5.5  # ln(mean)
    sigma: 0.8
    min: 50
    max: 2000
    
  shared_prefixes:
    enabled: true
    num_prefixes: 10
    prefix_length_min: 100
    prefix_length_max: 500
    probability: 0.3
```

---

## 7. Metrics Collection System

### 7.1 Metric Types

**Per-Request Metrics:**
```python
@dataclass
class RequestMetrics:
    request_id: str
    arrival_time: float
    queue_time: float  # time in queue before prefill
    prefill_time: float  # TTFT
    decode_time: float  # total decode time
    total_time: float  # end-to-end latency
    input_tokens: int
    output_tokens: int
    cache_hits: int
    replica_id: str
    
    @property
    def ttft(self) -> float:
        return self.queue_time + self.prefill_time
        
    @property
    def tpot(self) -> float:
        """Tokens per output token time"""
        return self.decode_time / self.output_tokens if self.output_tokens > 0 else 0
```

**Per-Replica Metrics:**
```python
@dataclass
class ReplicaMetrics:
    replica_id: str
    timestamp: float
    
    # Utilization
    kv_cache_utilization: float  # [0, 1]
    active_sequences: int
    waiting_requests: int
    
    # Load
    prefill_load: float  # tokens/sec being processed
    decode_load: float  # sequences being decoded
    
    # Throughput
    prefill_throughput: float  # actual tokens/sec
    decode_throughput: float  # actual tokens/sec
    
    # Timing
    avg_ttft: float  # recent average
    avg_tpot: float  # recent average
    avg_itl: float  # inter-token latency
```

**Aggregate Metrics:**
```python
@dataclass
class AggregateMetrics:
    timestamp: float
    
    # Throughput
    total_requests_completed: int
    requests_per_second: float
    tokens_per_second: float
    
    # Latency (percentiles)
    ttft_p50: float
    ttft_p95: float
    ttft_p99: float
    tpot_p50: float
    tpot_p95: float
    tpot_p99: float
    
    # SLO violations
    ttft_violations: int  # count above threshold
    tpot_violations: int
    
    # Capacity
    total_replicas: int
    avg_kv_utilization: float
    avg_active_sequences: float
    
    # Queue
    queue_depth: int
    avg_queue_time: float
```

### 7.2 Metrics Collector

```python
class MetricsCollector:
    def __init__(self, collection_interval: float = 1.0):
        self.collection_interval = collection_interval
        self.request_metrics: List[RequestMetrics] = []
        self.replica_metrics: List[ReplicaMetrics] = []
        self.aggregate_metrics: List[AggregateMetrics] = []
        
    def record_request(self, metrics: RequestMetrics):
        """Record completed request metrics"""
        self.request_metrics.append(metrics)
        
    def collect_replica_metrics(self, replicas: List[VLLMReplica], timestamp: float):
        """Collect current state from all replicas"""
        for replica in replicas:
            self.replica_metrics.append(ReplicaMetrics(
                replica_id=replica.id,
                timestamp=timestamp,
                kv_cache_utilization=replica.kv_cache.utilization(),
                active_sequences=len(replica.scheduler.running_sequences),
                waiting_requests=len(replica.scheduler.waiting_queue),
                prefill_load=replica.compute_prefill_load(),
                decode_load=replica.compute_decode_load(),
                prefill_throughput=replica.get_prefill_throughput(),
                decode_throughput=replica.get_decode_throughput(),
                avg_ttft=replica.get_recent_ttft(),
                avg_tpot=replica.get_recent_tpot(),
                avg_itl=replica.get_recent_itl()
            ))
            
    def compute_aggregate_metrics(self, timestamp: float, 
                                  window: float = 60.0) -> AggregateMetrics:
        """Compute aggregate metrics over recent window"""
        recent_requests = [
            m for m in self.request_metrics
            if timestamp - m.arrival_time <= window
        ]
        
        if not recent_requests:
            return AggregateMetrics(timestamp=timestamp, ...)
            
        # Compute percentiles
        ttfts = [m.ttft for m in recent_requests]
        tpots = [m.tpot for m in recent_requests]
        
        return AggregateMetrics(
            timestamp=timestamp,
            total_requests_completed=len(recent_requests),
            requests_per_second=len(recent_requests) / window,
            tokens_per_second=sum(m.output_tokens for m in recent_requests) / window,
            ttft_p50=np.percentile(ttfts, 50),
            ttft_p95=np.percentile(ttfts, 95),
            ttft_p99=np.percentile(ttfts, 99),
            tpot_p50=np.percentile(tpots, 50),
            tpot_p95=np.percentile(tpots, 95),
            tpot_p99=np.percentile(tpots, 99),
            # ... other fields
        )
        
    def export_to_dataframe(self) -> Dict[str, pd.DataFrame]:
        """Export all metrics to pandas DataFrames"""
        return {
            "requests": pd.DataFrame([asdict(m) for m in self.request_metrics]),
            "replicas": pd.DataFrame([asdict(m) for m in self.replica_metrics]),
            "aggregate": pd.DataFrame([asdict(m) for m in self.aggregate_metrics])
        }
```

---

## 8. Autoscaler Plugin Architecture

### 8.1 Base Interface

```python
class AutoscalerPlugin(ABC):
    """Base class for all autoscaling algorithms"""
    
    @abstractmethod
    def compute_desired_replicas(
        self,
        current_replicas: int,
        metrics: Dict[str, Any],
        config: Dict[str, Any]
    ) -> int:
        """
        Compute desired replica count based on current state.
        
        Args:
            current_replicas: Current number of replicas
            metrics: Dictionary of current metrics
            config: Algorithm-specific configuration
            
        Returns:
            Desired number of replicas
        """
        pass
        
    @abstractmethod
    def get_config_schema(self) -> Dict[str, Any]:
        """Return JSON schema for configuration validation"""
        pass
        
    def on_scale_event(self, old_count: int, new_count: int):
        """Optional callback when scaling occurs"""
        pass
```

### 8.2 Example Implementations

**Reactive Utilization-Based:**
```python
class UtilizationAutoscaler(AutoscalerPlugin):
    def compute_desired_replicas(self, current_replicas, metrics, config):
        # Get average KV utilization across replicas
        avg_kv_util = metrics["avg_kv_utilization"]
        
        # Target utilization
        target_util = config.get("target_utilization", 0.7)
        
        # Simple proportional scaling
        if avg_kv_util > target_util:
            scale_factor = avg_kv_util / target_util
            desired = math.ceil(current_replicas * scale_factor)
        elif avg_kv_util < target_util * 0.5:
            # Scale down if well below target
            scale_factor = avg_kv_util / (target_util * 0.5)
            desired = max(1, math.floor(current_replicas * scale_factor))
        else:
            desired = current_replicas
            
        return desired
        
    def get_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "target_utilization": {"type": "number", "minimum": 0, "maximum": 1}
            }
        }
```

**Proactive Rate-Based (from throughput-analyzer-design.md):**
```python
class RateBasedAutoscaler(AutoscalerPlugin):
    def __init__(self):
        self.prefill_ema = None
        self.decode_ema = None
        self.alpha = 0.3  # EMA smoothing factor
        
    def compute_desired_replicas(self, current_replicas, metrics, config):
        # Extract rate metrics
        prefill_demand = metrics["prefill_demand_rate"]  # tokens/sec
        decode_demand = metrics["decode_demand_rate"]  # sequences/sec
        
        prefill_supply_per_replica = config["prefill_capacity"]  # tokens/sec
        decode_supply_per_replica = config["decode_capacity"]  # sequences
        
        # Smooth demand with EMA
        if self.prefill_ema is None:
            self.prefill_ema = prefill_demand
            self.decode_ema = decode_demand
        else:
            self.prefill_ema = self.alpha * prefill_demand + (1 - self.alpha) * self.prefill_ema
            self.decode_ema = self.alpha * decode_demand + (1 - self.alpha) * self.decode_ema
            
        # Compute required replicas for each channel
        target_util = config.get("target_utilization", 0.7)
        
        prefill_replicas = math.ceil(
            self.prefill_ema / (prefill_supply_per_replica * target_util)
        )
        decode_replicas = math.ceil(
            self.decode_ema / (decode_supply_per_replica * target_util)
        )
        
        # Take max (both constraints must be satisfied)
        desired = max(prefill_replicas, decode_replicas, 1)
        
        return desired
        
    def get_config_schema(self):
        return {
            "type": "object",
            "properties": {
                "prefill_capacity": {"type": "number"},
                "decode_capacity": {"type": "number"},
                "target_utilization": {"type": "number"},
                "ema_alpha": {"type": "number"}
            },
            "required": ["prefill_capacity", "decode_capacity"]
        }
```

**Hybrid Approach:**
```python
class HybridAutoscaler(AutoscalerPlugin):
    """Combines rate-based (scale-up) with utilization-based (scale-down)"""
    
    def __init__(self):
        self.rate_scaler = RateBasedAutoscaler()
        self.util_scaler = UtilizationAutoscaler()
        
    def compute_desired_replicas(self, current_replicas, metrics, config):
        # Use rate-based for scale-up decisions
        rate_desired = self.rate_scaler.compute_desired_replicas(
            current_replicas, metrics, config["rate_config"]
        )
        
        # Use utilization for scale-down decisions
        util_desired = self.util_scaler.compute_desired_replicas(
            current_replicas, metrics, config["util_config"]
        )
        
        # OR for scale-up, AND for scale-down
        if rate_desired > current_replicas:
            return rate_desired
        elif util_desired < current_replicas:
            return util_desired
        else:
            return current_replicas
```

### 8.3 Autoscaler Manager

```python
class AutoscalerManager:
    def __init__(self, plugin: AutoscalerPlugin, config: Dict[str, Any],
                 scheduler: SimulationScheduler):
        self.plugin = plugin
        self.config = config
        self.scheduler = scheduler
        self.evaluation_interval = config.get("evaluation_interval", 10.0)
        self.scale_up_delay = config.get("scale_up_delay", 0.0)
        self.scale_down_delay = config.get("scale_down_delay", 30.0)
        self.last_scale_time = 0
        
    def start(self, replica_manager: ReplicaLifecycleManager,
              metrics_collector: MetricsCollector):
        """Start autoscaling loop"""
        self.scheduler.env.process(
            self._autoscaling_loop(replica_manager, metrics_collector)
        )
        
    def _autoscaling_loop(self, replica_manager, metrics_collector):
        """Main autoscaling control loop"""
        while True:
            # Wait for next evaluation
            yield self.scheduler.env.timeout(self.evaluation_interval)
            
            # Collect current metrics
            current_replicas = replica_manager.get_replica_count()
            metrics = metrics_collector.get_latest_metrics()
            
            # Compute desired replicas
            desired_replicas = self.plugin.compute_desired_replicas(
                current_replicas, metrics, self.config
            )
            
            # Apply scaling decision with delays
            if desired_replicas > current_replicas:
                # Scale up
                if self.scheduler.now() - self.last_scale_time >= self.scale_up_delay:
                    replica_manager.scale_to(desired_replicas)
                    self.last_scale_time = self.scheduler.now()
                    self.plugin.on_scale_event(current_replicas, desired_replicas)
                    
            elif desired_replicas < current_replicas:
                # Scale down
                if self.scheduler.now() - self.last_scale_time >= self.scale_down_delay:
                    replica_manager.scale_to(desired_replicas)
                    self.last_scale_time = self.scheduler.now()
                    self.plugin.on_scale_event(current_replicas, desired_replicas)
```

---

## 9. K8s Integration Design

### 9.1 Mock Metrics API Server

```python
class MockK8sMetricsServer:
    """Simulates K8s metrics API for HPA integration"""
    
    def __init__(self, metrics_collector: MetricsCollector,
                 staleness_delay: float = 5.0):
        self.metrics_collector = metrics_collector
        self.staleness_delay = staleness_delay
        self.custom_metrics: Dict[str, Any] = {}
        
    def get_pod_metrics(self, namespace: str, pod_name: str) -> Dict[str, Any]:
        """Return metrics for a specific pod (replica)"""
        # Simulate metric staleness
        current_time = self.metrics_collector.current_time
        stale_time = current_time - self.staleness_delay
        
        # Get replica metrics at stale time
        replica_metrics = self.metrics_collector.get_replica_metrics_at_time(
            pod_name, stale_time
        )
        
        # Convert to K8s format
        return {
            "metadata": {"name": pod_name, "namespace": namespace},
            "timestamp": stale_time,
            "window": "15s",
            "containers": [{
                "name": "vllm",
                "usage": {
                    "cpu": f"{replica_metrics.cpu_usage}m",
                    "memory": f"{replica_metrics.memory_usage}Mi"
                }
            }]
        }
        
    def get_custom_metrics(self, namespace: str, metric_name: str) -> List[Dict]:
        """Return custom metrics (e.g., KV utilization, queue depth)"""
        current_time = self.metrics_collector.current_time
        stale_time = current_time - self.staleness_delay
        
        # Get aggregate metrics
        agg_metrics = self.metrics_collector.get_aggregate_metrics_at_time(stale_time)
        
        # Map to K8s custom metrics format
        if metric_name == "kv_cache_utilization":
            value = agg_metrics.avg_kv_utilization
        elif metric_name == "queue_depth":
            value = agg_metrics.queue_depth
        elif metric_name == "prefill_load":
            value = agg_metrics.prefill_demand_rate
        else:
            value = 0
            
        return [{
            "describedObject": {
                "kind": "Deployment",
                "name": "vllm-deployment",
                "namespace": namespace
            },
            "metricName": metric_name,
            "timestamp": stale_time,
            "value": str(value)
        }]
        
    def register_custom_metric(self, name: str, value_func: Callable):
        """Register a custom metric computation"""
        self.custom_metrics[name] = value_func
```

### 9.2 HPA Controller Integration
**Option 1: Use Real HPA Controller (Recommended)**

Run an actual K8s HPA controller in a separate process, pointing it at the mock metrics server. This provides the most realistic behavior.

```python
class RealHPAIntegration:
    """Integration with real K8s HPA controller"""
    
    def __init__(self, metrics_server: MockK8sMetricsServer,
                 hpa_config: Dict[str, Any]):
        self.metrics_server = metrics_server
        self.hpa_config = hpa_config
        self.hpa_process = None
        
    def start_hpa_controller(self):
        """Start HPA controller in separate process"""
        # Create HPA manifest
        hpa_manifest = {
            "apiVersion": "autoscaling/v2",
            "kind": "HorizontalPodAutoscaler",
            "metadata": {"name": "vllm-hpa"},
            "spec": {
                "scaleTargetRef": {
                    "apiVersion": "apps/v1",
                    "kind": "Deployment",
                    "name": "vllm-deployment"
                },
                "minReplicas": self.hpa_config["min_replicas"],
                "maxReplicas": self.hpa_config["max_replicas"],
                "metrics": self._build_metrics_spec(),
                "behavior": self._build_behavior_spec()
            }
        }
        
        # Start mock API server
        self.metrics_server.start_server(port=8080)
        
        # Start HPA controller pointing to mock server
        # (This would use kubectl or K8s client library)
        
    def _build_metrics_spec(self) -> List[Dict]:
        """Build HPA metrics specification"""
        metrics = []
        
        if "kv_utilization" in self.hpa_config["metrics"]:
            metrics.append({
                "type": "Object",
                "object": {
                    "metric": {"name": "kv_cache_utilization"},
                    "target": {
                        "type": "Value",
                        "value": str(self.hpa_config["metrics"]["kv_utilization"]["target"])
                    }
                }
            })
            
        return metrics
        
    def _build_behavior_spec(self) -> Dict:
        """Build HPA scaling behavior"""
        return {
            "scaleUp": {
                "stabilizationWindowSeconds": 0,
                "policies": [{
                    "type": "Percent",
                    "value": 100,
                    "periodSeconds": 15
                }]
            },
            "scaleDown": {
                "stabilizationWindowSeconds": 300,
                "policies": [{
                    "type": "Percent",
                    "value": 10,
                    "periodSeconds": 60
                }]
            }
        }
```

**Option 2: Simulate HPA Logic**

Implement HPA algorithm directly in Python for simpler setup.

```python
class SimulatedHPA(AutoscalerPlugin):
    """Simulates K8s HPA v2 algorithm"""
    
    def __init__(self):
        self.stabilization_window = 300  # seconds
        self.recent_recommendations: List[Tuple[float, int]] = []
        
    def compute_desired_replicas(self, current_replicas, metrics, config):
        # HPA algorithm: desired = ceil(current * (current_metric / target_metric))
        
        metric_name = config["metric_name"]
        target_value = config["target_value"]
        current_value = metrics[metric_name]
        
        # Compute raw desired replicas
        if target_value > 0:
            ratio = current_value / target_value
            raw_desired = math.ceil(current_replicas * ratio)
        else:
            raw_desired = current_replicas
            
        # Apply min/max bounds
        desired = max(config["min_replicas"], 
                     min(config["max_replicas"], raw_desired))
        
        # Apply stabilization window for scale-down
        now = metrics["timestamp"]
        self.recent_recommendations.append((now, desired))
        
        # Remove old recommendations
        self.recent_recommendations = [
            (t, r) for t, r in self.recent_recommendations
            if now - t <= self.stabilization_window
        ]
        
        # For scale-down, use max of recent recommendations
        if desired < current_replicas:
            desired = max(r for _, r in self.recent_recommendations)
            
        return desired
```

### 9.3 Replica Lifecycle Manager

```python
class ReplicaLifecycleManager:
    """Manages replica creation, deletion, and lifecycle"""
    
    def __init__(self, scheduler: SimulationScheduler,
                 gpu_config: GPUConfig,
                 vllm_config: VLLMConfig):
        self.scheduler = scheduler
        self.gpu_config = gpu_config
        self.vllm_config = vllm_config
        self.replicas: Dict[str, VLLMReplica] = {}
        self.next_replica_id = 0
        
        # Lifecycle timing
        self.startup_time = 30.0  # seconds to start pod
        self.readiness_delay = 10.0  # seconds until ready
        self.termination_grace = 30.0  # seconds for graceful shutdown
        
    def scale_to(self, desired_count: int):
        """Scale to desired replica count"""
        current_count = len(self.replicas)
        
        if desired_count > current_count:
            # Scale up
            for _ in range(desired_count - current_count):
                self._create_replica()
        elif desired_count < current_count:
            # Scale down
            replicas_to_remove = current_count - desired_count
            self._remove_replicas(replicas_to_remove)
            
    def _create_replica(self):
        """Create a new replica with startup delay"""
        replica_id = f"replica-{self.next_replica_id}"
        self.next_replica_id += 1
        
        # Schedule replica to become ready after startup time
        self.scheduler.schedule(
            self.startup_time + self.readiness_delay,
            lambda: self._activate_replica(replica_id)
        )
        
    def _activate_replica(self, replica_id: str):
        """Activate replica after startup"""
        replica = VLLMReplica(
            id=replica_id,
            gpu_config=self.gpu_config,
            vllm_config=self.vllm_config,
            scheduler=self.scheduler
        )
        self.replicas[replica_id] = replica
        replica.start()
        
    def _remove_replicas(self, count: int):
        """Remove replicas with graceful shutdown"""
        # Select replicas to remove (e.g., least loaded)
        sorted_replicas = sorted(
            self.replicas.items(),
            key=lambda x: x[1].get_load()
        )
        
        for replica_id, replica in sorted_replicas[:count]:
            # Mark for termination
            replica.mark_for_termination()
            
            # Schedule removal after grace period
            self.scheduler.schedule(
                self.termination_grace,
                lambda rid=replica_id: self._terminate_replica(rid)
            )
            
    def _terminate_replica(self, replica_id: str):
        """Terminate replica after grace period"""
        if replica_id in self.replicas:
            replica = self.replicas[replica_id]
            replica.stop()
            del self.replicas[replica_id]
            
    def get_active_replicas(self) -> List[VLLMReplica]:
        """Get list of active replicas"""
        return [r for r in self.replicas.values() if r.is_ready()]
        
    def get_replica_count(self) -> int:
        """Get current replica count"""
        return len(self.get_active_replicas())
```

---

## 10. Simulation Configuration

### 10.1 Configuration Schema

```yaml
simulation:
  name: "baseline-poisson-workload"
  duration: 3600  # seconds
  speedup_factor: 30  # 30x real-time
  random_seed: 42
  
gpu:
  prefill_tokens_per_sec: 10000
  prefill_batch_size: 256
  decode_tokens_per_sec: 2000
  max_sequences: 128
  kv_cache_size_gb: 80
  bytes_per_token: 128
  context_switch_overhead_ms: 1.0
  preemption_overhead_ms: 2.0
  
vllm:
  max_batch_size: 256
  max_num_seqs: 128
  chunked_prefill_size: 512
  enable_prefix_caching: true
  cache_hit_rate: 0.3
  prefill_decode_interference: 0.2
  load_dependent_slowdown: true
  
workload:
  duration: 3600
  
  arrival:
    type: "poisson"
    rate: 10
    
  input_length:
    type: "normal"
    mean: 1000
    std: 300
    min: 100
    max: 8000
    
  output_length:
    type: "lognormal"
    mean: 5.5
    sigma: 0.8
    min: 50
    max: 2000
    
  shared_prefixes:
    enabled: true
    num_prefixes: 10
    prefix_length_min: 100
    prefix_length_max: 500
    probability: 0.3
    
autoscaler:
  plugin: "rate_based"  # rate_based | utilization | hybrid | hpa
  evaluation_interval: 10.0
  scale_up_delay: 0.0
  scale_down_delay: 30.0
  
  config:
    prefill_capacity: 8000  # tokens/sec per replica
    decode_capacity: 100  # sequences per replica
    target_utilization: 0.7
    ema_alpha: 0.3
    
  min_replicas: 1
  max_replicas: 20
  
replica_lifecycle:
  startup_time: 30.0
  readiness_delay: 10.0
  termination_grace: 30.0
  
metrics:
  collection_interval: 1.0
  staleness_delay: 5.0
  aggregation_window: 60.0
  
slo:
  ttft_target_ms: 500
  tpot_target_ms: 50
  
output:
  directory: "./results"
  formats: ["parquet", "csv", "json"]
  plots: true
  dashboard: true
```

### 10.2 Configuration Validation

```python
from pydantic import BaseModel, Field, validator
from typing import Literal, Optional

class GPUConfigModel(BaseModel):
    prefill_tokens_per_sec: float = Field(gt=0)
    prefill_batch_size: int = Field(gt=0)
    decode_tokens_per_sec: float = Field(gt=0)
    max_sequences: int = Field(gt=0)
    kv_cache_size_gb: float = Field(gt=0)
    bytes_per_token: int = Field(gt=0)
    context_switch_overhead_ms: float = Field(ge=0)
    preemption_overhead_ms: float = Field(ge=0)

class ArrivalConfigModel(BaseModel):
    type: Literal["poisson", "bursty", "diurnal"]
    rate: float = Field(gt=0)
    burst_rate: Optional[float] = None
    burst_duration: Optional[float] = None
    burst_interval: Optional[float] = None
    peak_rate: Optional[float] = None
    trough_rate: Optional[float] = None
    period: Optional[float] = None
    
    @validator('burst_rate')
    def validate_bursty_config(cls, v, values):
        if values.get('type') == 'bursty' and v is None:
            raise ValueError("burst_rate required for bursty arrival")
        return v

class SimulationConfigModel(BaseModel):
    name: str
    duration: float = Field(gt=0)
    speedup_factor: float = Field(gt=0, le=1000)
    random_seed: Optional[int] = None
    
    gpu: GPUConfigModel
    vllm: dict
    workload: dict
    autoscaler: dict
    replica_lifecycle: dict
    metrics: dict
    slo: dict
    output: dict
    
    @classmethod
    def from_yaml(cls, path: str) -> "SimulationConfigModel":
        with open(path) as f:
            config_dict = yaml.safe_load(f)
        return cls(**config_dict)
```

---

## 11. Output Analysis and Visualization

### 11.1 Analysis Framework

```python
class SimulationAnalyzer:
    """Analyze simulation results and generate reports"""
    
    def __init__(self, results_dir: str):
        self.results_dir = Path(results_dir)
        self.request_df = pd.read_parquet(self.results_dir / "requests.parquet")
        self.replica_df = pd.read_parquet(self.results_dir / "replicas.parquet")
        self.aggregate_df = pd.read_parquet(self.results_dir / "aggregate.parquet")
        
    def compute_slo_compliance(self, ttft_target: float, tpot_target: float) -> Dict:
        """Compute SLO compliance metrics"""
        ttft_violations = (self.request_df["ttft"] > ttft_target).sum()
        tpot_violations = (self.request_df["tpot"] > tpot_target).sum()
        total_requests = len(self.request_df)
        
        return {
            "ttft_compliance": 1.0 - (ttft_violations / total_requests),
            "tpot_compliance": 1.0 - (tpot_violations / total_requests),
            "overall_compliance": 1.0 - ((ttft_violations + tpot_violations) / (2 * total_requests)),
            "ttft_violations": ttft_violations,
            "tpot_violations": tpot_violations
        }
        
    def compute_latency_percentiles(self) -> Dict:
        """Compute latency percentiles"""
        return {
            "ttft": {
                "p50": self.request_df["ttft"].quantile(0.50),
                "p95": self.request_df["ttft"].quantile(0.95),
                "p99": self.request_df["ttft"].quantile(0.99),
                "max": self.request_df["ttft"].max()
            },
            "tpot": {
                "p50": self.request_df["tpot"].quantile(0.50),
                "p95": self.request_df["tpot"].quantile(0.95),
                "p99": self.request_df["tpot"].quantile(0.99),
                "max": self.request_df["tpot"].max()
            },
            "total_latency": {
                "p50": self.request_df["total_time"].quantile(0.50),
                "p95": self.request_df["total_time"].quantile(0.95),
                "p99": self.request_df["total_time"].quantile(0.99),
                "max": self.request_df["total_time"].max()
            }
        }
        
    def compute_throughput_stats(self) -> Dict:
        """Compute throughput statistics"""
        duration = self.request_df["arrival_time"].max()
        total_requests = len(self.request_df)
        total_tokens = self.request_df["output_tokens"].sum()
        
        return {
            "requests_per_second": total_requests / duration,
            "tokens_per_second": total_tokens / duration,
            "avg_request_size": self.request_df["output_tokens"].mean(),
            "total_requests": total_requests,
            "total_tokens": total_tokens
        }
        
    def compute_scaling_stats(self) -> Dict:
        """Compute autoscaling statistics"""
        # Get replica count over time from aggregate metrics
        replica_counts = self.aggregate_df["total_replicas"]
        
        # Count scaling events
        scaling_events = (replica_counts.diff() != 0).sum()
        scale_ups = (replica_counts.diff() > 0).sum()
        scale_downs = (replica_counts.diff() < 0).sum()
        
        return {
            "avg_replicas": replica_counts.mean(),
            "min_replicas": replica_counts.min(),
            "max_replicas": replica_counts.max(),
            "scaling_events": scaling_events,
            "scale_ups": scale_ups,
            "scale_downs": scale_downs,
            "avg_kv_utilization": self.aggregate_df["avg_kv_utilization"].mean(),
            "max_kv_utilization": self.aggregate_df["avg_kv_utilization"].max()
        }
        
    def detect_oscillations(self, window: int = 10) -> Dict:
        """Detect scaling oscillations"""
        replica_counts = self.aggregate_df["total_replicas"]
        
        # Count direction changes in sliding window
        direction_changes = []
        for i in range(len(replica_counts) - window):
            window_data = replica_counts.iloc[i:i+window]
            changes = (window_data.diff().fillna(0) != 0).sum()
            direction_changes.append(changes)
            
        return {
            "max_changes_in_window": max(direction_changes) if direction_changes else 0,
            "avg_changes_in_window": np.mean(direction_changes) if direction_changes else 0,
            "oscillation_detected": max(direction_changes) > window * 0.5 if direction_changes else False
        }
        
    def generate_report(self, output_path: str):
        """Generate comprehensive analysis report"""
        report = {
            "slo_compliance": self.compute_slo_compliance(500, 50),
            "latency_percentiles": self.compute_latency_percentiles(),
            "throughput": self.compute_throughput_stats(),
            "scaling": self.compute_scaling_stats(),
            "oscillations": self.detect_oscillations()
        }
        
        with open(output_path, 'w') as f:
            json.dump(report, f, indent=2)
            
        return report
```

### 11.2 Visualization

```python
class SimulationVisualizer:
    """Generate plots and dashboards"""
    
    def __init__(self, analyzer: SimulationAnalyzer):
        self.analyzer = analyzer
        
    def plot_latency_over_time(self, output_path: str):
        """Plot TTFT and TPOT over time"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        # TTFT over time
        df = self.analyzer.request_df.sort_values("arrival_time")
        ax1.scatter(df["arrival_time"], df["ttft"], alpha=0.3, s=1)
        ax1.axhline(y=500, color='r', linestyle='--', label='SLO Target')
        ax1.set_ylabel("TTFT (ms)")
        ax1.set_title("Time to First Token")
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # TPOT over time
        ax2.scatter(df["arrival_time"], df["tpot"], alpha=0.3, s=1)
        ax2.axhline(y=50, color='r', linestyle='--', label='SLO Target')
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("TPOT (ms)")
        ax2.set_title("Time Per Output Token")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        
    def plot_replica_count(self, output_path: str):
        """Plot replica count and utilization over time"""
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(12, 8))
        
        df = self.analyzer.aggregate_df
        
        # Replica count
        ax1.plot(df["timestamp"], df["total_replicas"], linewidth=2)
        ax1.set_ylabel("Replica Count")
        ax1.set_title("Autoscaling Behavior")
        ax1.grid(True, alpha=0.3)
        
        # KV utilization
        ax2.plot(df["timestamp"], df["avg_kv_utilization"], linewidth=2)
        ax2.axhline(y=0.7, color='r', linestyle='--', label='Target')
        ax2.set_xlabel("Time (s)")
        ax2.set_ylabel("KV Utilization")
        ax2.set_title("Average KV Cache Utilization")
        ax2.legend()
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        
    def plot_throughput(self, output_path: str):
        """Plot throughput over time"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        df = self.analyzer.aggregate_df
        ax.plot(df["timestamp"], df["requests_per_second"], label="Requests/sec")
        ax.plot(df["timestamp"], df["tokens_per_second"] / 100, label="Tokens/sec (÷100)")
        
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Throughput")
        ax.set_title("System Throughput")
        ax.legend()
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        
    def plot_queue_depth(self, output_path: str):
        """Plot queue depth over time"""
        fig, ax = plt.subplots(figsize=(12, 6))
        
        df = self.analyzer.aggregate_df
        ax.plot(df["timestamp"], df["queue_depth"], linewidth=2)
        
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Queue Depth")
        ax.set_title("Request Queue Depth")
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
        
    def create_dashboard(self, output_dir: str):
        """Create complete dashboard"""
        output_dir = Path(output_dir)
        output_dir.mkdir(exist_ok=True)
        
        self.plot_latency_over_time(output_dir / "latency.png")
        self.plot_replica_count(output_dir / "replicas.png")
        self.plot_throughput(output_dir / "throughput.png")
        self.plot_queue_depth(output_dir / "queue.png")
        
        # Generate HTML dashboard
        html = f"""
        <html>
        <head><title>Simulation Results</title></head>
        <body>
            <h1>LLM Autoscaler Simulation Results</h1>
            <h2>Latency Metrics</h2>
            <img src="latency.png" width="100%">
            <h2>Autoscaling Behavior</h2>
            <img src="replicas.png" width="100%">
            <h2>Throughput</h2>
            <img src="throughput.png" width="100%">
            <h2>Queue Depth</h2>
            <img src="queue.png" width="100%">
        </body>
        </html>
        """
        
        with open(output_dir / "dashboard.html", 'w') as f:
            f.write(html)
```

### 11.3 Comparison Framework

```python
class SimulationComparator:
    """Compare multiple simulation runs"""
    
    def __init__(self, result_dirs: List[str], labels: List[str]):
        self.analyzers = [SimulationAnalyzer(d) for d in result_dirs]
        self.labels = labels
        
    def compare_slo_compliance(self) -> pd.DataFrame:
        """Compare SLO compliance across runs"""
        results = []
        for analyzer, label in zip(self.analyzers, self.labels):
            compliance = analyzer.compute_slo_compliance(500, 50)
            results.append({
                "run": label,
                "ttft_compliance": compliance["ttft_compliance"],
                "tpot_compliance": compliance["tpot_compliance"],
                "overall_compliance": compliance["overall_compliance"]
            })
        return pd.DataFrame(results)
        
    def compare_latency_percentiles(self) -> pd.DataFrame:
        """Compare latency percentiles across runs"""
        results = []
        for analyzer, label in zip(self.analyzers, self.labels):
            percentiles = analyzer.compute_latency_percentiles()
            results.append({
                "run": label,
                "ttft_p50": percentiles["ttft"]["p50"],
                "ttft_p95": percentiles["ttft"]["p95"],
                "ttft_p99": percentiles["ttft"]["p99"],
                "tpot_p50": percentiles["tpot"]["p50"],
                "tpot_p95": percentiles["tpot"]["p95"],
                "tpot_p99": percentiles["tpot"]["p99"]
            })
        return pd.DataFrame(results)
        
    def compare_resource_efficiency(self) -> pd.DataFrame:
        """Compare resource efficiency across runs"""
        results = []
        for analyzer, label in zip(self.analyzers, self.labels):
            scaling = analyzer.compute_scaling_stats()
            throughput = analyzer.compute_throughput_stats()
            
            # Compute efficiency: throughput per replica
            efficiency = throughput["tokens_per_second"] / scaling["avg_replicas"]
            
            results.append({
                "run": label,
                "avg_replicas": scaling["avg_replicas"],
                "tokens_per_second": throughput["tokens_per_second"],
                "tokens_per_replica": efficiency,
                "avg_kv_utilization": scaling["avg_kv_utilization"],
                "scaling_events": scaling["scaling_events"]
            })
        return pd.DataFrame(results)
        
    def plot_comparison(self, output_path: str):
        """Create comparison plots"""
        fig, axes = plt.subplots(2, 2, figsize=(15, 12))
        
        # SLO compliance
        compliance_df = self.compare_slo_compliance()
        axes[0, 0].bar(compliance_df["run"], compliance_df["overall_compliance"])
        axes[0, 0].set_ylabel("Compliance Rate")
        axes[0, 0].set_title("SLO Compliance")
        axes[0, 0].set_ylim([0, 1])
        
        # Latency percentiles
        latency_df = self.compare_latency_percentiles()
        x = np.arange(len(self.labels))
        width = 0.35
        axes[0, 1].bar(x - width/2, latency_df["ttft_p95"], width, label='TTFT P95')
        axes[0, 1].bar(x + width/2, latency_df["tpot_p95"], width, label='TPOT P95')
        axes[0, 1].set_ylabel("Latency (ms)")
        axes[0, 1].set_title("P95 Latencies")
        axes[0, 1].set_xticks(x)
        axes[0, 1].set_xticklabels(self.labels)
        axes[0, 1].legend()
        
        # Resource efficiency
        efficiency_df = self.compare_resource_efficiency()
        axes[1, 0].bar(efficiency_df["run"], efficiency_df["tokens_per_replica"])
        axes[1, 0].set_ylabel("Tokens/sec per Replica")
        axes[1, 0].set_title("Resource Efficiency")
        
        # Scaling stability
        axes[1, 1].bar(efficiency_df["run"], efficiency_df["scaling_events"])
        axes[1, 1].set_ylabel("Scaling Events")
        axes[1, 1].set_title("Scaling Stability (fewer is better)")
        
        plt.tight_layout()
        plt.savefig(output_path, dpi=150)
        plt.close()
```

---

## 12. Validation Strategy

### 12.1 Unit Testing

```python
class TestVLLMReplica:
    """Unit tests for vLLM replica behavior"""
    
    def test_prefill_time_linear_at_low_load(self):
        """Prefill time should be linear at low load"""
        replica = VLLMReplica(...)
        
        time_1000 = replica.compute_prefill_time(1000, 0, 0.3)
        time_2000 = replica.compute_prefill_time(2000, 0, 0.3)
        
        assert abs(time_2000 / time_1000 - 2.0) < 0.1
        
    def test_prefill_time_nonlinear_at_high_load(self):
        """Prefill time should slow down at high load"""
        replica = VLLMReplica(...)
        
        time_low = replica.compute_prefill_time(1000, 0, 0.5)
        time_high = replica.compute_prefill_time(1000, 0, 0.9)
        
        assert time_high > time_low * 1.5
        
    def test_kv_cache_admission_control(self):
        """KV cache should reject requests when full"""
        replica = VLLMReplica(...)
        
        # Fill cache
        for i in range(100):
            replica.admit_request(Request(input_tokens=1000, output_tokens=1000))
            
        # Should reject next request
        assert not replica.can_admit(Request(input_tokens=1000, output_tokens=1000))
        
    def test_decode_time_scales_with_concurrency(self):
        """Decode time should increase with active sequences"""
        replica = VLLMReplica(...)
        
        time_1_seq = replica.compute_decode_time(100, 1, 0.5)
        time_10_seq = replica.compute_decode_time(100, 10, 0.5)
        
        assert time_10_seq > time_1_seq * 5
```

### 12.2 Integration Testing

```python
class TestAutoscalerIntegration:
    """Integration tests for autoscaler"""
    
    def test_scale_up_on_high_load(self):
        """Autoscaler should scale up when load increases"""
        sim = Simulation(config)
        
        # Start with low load
        sim.run(duration=100)
        initial_replicas = sim.get_replica_count()
        
        # Increase load
        sim.workload_generator.set_rate(50)
        sim.run(duration=100)
        final_replicas = sim.get_replica_count()
        
        assert final_replicas > initial_replicas
        
    def test_scale_down_on_low_load(self):
        """Autoscaler should scale down when load decreases"""
        sim = Simulation(config)
        
        # Start with high load
        sim.workload_generator.set_rate(50)
        sim.run(duration=100)
        initial_replicas = sim.get_replica_count()
        
        # Decrease load
        sim.workload_generator.set_rate(5)
        sim.run(duration=200)  # Wait for scale-down delay
        final_replicas = sim.get_replica_count()
        
        assert final_replicas < initial_replicas
        
    def test_slo_maintained_under_load(self):
        """SLOs should be maintained under varying load"""
        sim = Simulation(config)
        sim.run(duration=3600)
        
        analyzer = SimulationAnalyzer(sim.results_dir)
        compliance = analyzer.compute_slo_compliance(500, 50)
        
        assert compliance["overall_compliance"] > 0.95
```

### 12.3 Validation Against Production Data

```python
class ProductionValidator:
    """Validate simulation against production traces"""
    
    def __init__(self, production_trace_path: str):
        self.prod_df = pd.read_parquet(production_trace_path)
        
    def extract_workload_characteristics(self) -> Dict:
        """Extract workload parameters from production"""
        return {
            "arrival_rate": len(self.prod_df) / self.prod_df["timestamp"].max(),
            "il_mean": self.prod_df["input_tokens"].mean(),
            "il_std": self.prod_df["input_tokens"].std(),
            "ol_mean": self.prod_df["output_tokens"].mean(),
            "ol_std": self.prod_df["output_tokens"].std()
        }
        
    def run_matching_simulation(self, config_template: str) -> SimulationAnalyzer:
        """Run simulation matching production workload"""
        workload_params = self.extract_workload_characteristics()
        
        # Update config with production parameters
        config = SimulationConfigModel.from_yaml(config_template)
        config.workload.arrival.rate = workload_params["arrival_rate"]
        config.workload.input_length.mean = workload_params["il_mean"]
        config.workload.input_length.std = workload_params["il_std"]
        # ... etc
        
        # Run simulation
        sim = Simulation(config)
        sim.run()
        
        return SimulationAnalyzer(sim.results_dir)
        
    def compare_latency_distributions(self, sim_analyzer: SimulationAnalyzer) -> Dict:
        """Compare latency distributions"""
        prod_ttft = self.prod_df["ttft"]
        sim_ttft = sim_analyzer.request_df["ttft"]
        
        # KS test
        from scipy.stats import ks_2samp
        ks_stat, p_value = ks_2samp(prod_ttft, sim_ttft)
        
        return {
            "ks_statistic": ks_stat,
            "p_value": p_value,
            "prod_p50": prod_ttft.quantile(0.5),
            "sim_p50": sim_ttft.quantile(0.5),
            "prod_p95": prod_ttft.quantile(0.95),
            "sim_p95": sim_ttft.quantile(0.95)
        }
```

---

## 13. Implementation Roadmap

### Phase 1: Core Simulation (Weeks 1-2)
- [ ] Implement discrete event scheduler
- [ ] Implement basic vLLM replica model (linear timing)
- [ ] Implement simple workload generator (Poisson arrivals)
- [ ] Implement metrics collector
- [ ] Basic end-to-end test

### Phase 2: High-Fidelity Modeling (Weeks 3-4)
- [ ] Add KV cache management
- [ ] Add prefill/decode interference
- [ ] Add load-dependent timing
- [ ] Add continuous batching scheduler
- [ ] Validate against production traces

### Phase 3: Autoscaler Framework (Week 5)
- [ ] Implement autoscaler plugin interface
- [ ] Implement utilization-based autoscaler
- [ ] Implement rate-based autoscaler
- [ ] Implement replica lifecycle manager
- [ ] Add scaling delay simulation

### Phase 4: K8s Integration (Week 6)
- [ ] Implement mock metrics API server
- [ ] Integrate with real HPA controller
- [ ] Test HPA configurations
- [ ] Validate metric staleness effects

### Phase 5: Analysis & Visualization (Week 7)
- [ ] Implement analysis framework
- [ ] Create visualization tools
- [ ] Build comparison framework
- [ ] Generate example dashboards

### Phase 6: Validation & Documentation (Week 8)
- [ ] Comprehensive unit tests
- [ ] Integration tests
- [ ] Production validation
- [ ] User documentation
- [ ] Example configurations

---

## 14. Example Usage

```python
# Load configuration
config = SimulationConfigModel.from_yaml("configs/baseline.yaml")

# Create simulation
sim = Simulation(config)

# Run simulation
print(f"Running simulation: {config.name}")
print(f"Duration: {config.duration}s (simulated)")
print(f"Speedup: {config.speedup_factor}x")

start_time = time.time()
sim.run()
elapsed = time.time() - start_time

print(f"Completed in {elapsed:.1f}s (wall-clock)")
print(f"Speedup achieved: {config.duration / elapsed:.1f}x")

# Analyze results
analyzer = SimulationAnalyzer(sim.results_dir)
report = analyzer.generate_report(sim.results_dir / "report.json")

print("\nResults:")
print(f"SLO Compliance: {report['slo_compliance']['overall_compliance']:.1%}")
print(f"TTFT P95: {report['latency_percentiles']['ttft']['p95']:.1f}ms")
print(f"TPOT P95: {report['latency_percentiles']['tpot']['p95']:.1f}ms")
print(f"Avg Replicas: {report['scaling']['avg_replicas']:.1f}")
print(f"Scaling Events: {report['scaling']['scaling_events']}")

# Generate visualizations
visualizer = SimulationVisualizer(analyzer)
visualizer.create_dashboard(sim.results_dir / "dashboard")

print(f"\nDashboard: {sim.results_dir / 'dashboard' / 'dashboard.html'}")
```

**Comparing Multiple Algorithms:**

```python
# Run multiple configurations
configs = [
    "configs/utilization_based.yaml",
    "configs/rate_based.yaml",
    "configs/hybrid.yaml"
]

result_dirs = []
for config_path in configs:
    config = SimulationConfigModel.from_yaml(config_path)
    sim = Simulation(config)
    sim.run()
    result_dirs.append(sim.results_dir)

# Compare results
comparator = SimulationComparator(
    result_dirs,
    labels=["Utilization", "Rate-Based", "Hybrid"]
)

comparison_df = comparator.compare_slo_compliance()
print(comparison_df)

comparator.plot_comparison("comparison.png")
```

---

## 15. Summary

This design provides a comprehensive simulation environment for testing LLM autoscaling algorithms with the following key features:

**High-Fidelity Modeling:**
- Accurate vLLM behavior including prefill/decode dynamics
- KV cache constraints and memory management
- Prefill/decode interference effects
- Load-dependent performance degradation

**Flexible Testing:**
- Pluggable autoscaler architecture
- Configurable workload patterns
- Support for various scaling algorithms
- K8s HPA integration

**Fast Iteration:**
- 10-60x time acceleration
- Discrete-event simulation for efficiency
- Reproducible results with random seeds

**Comprehensive Analysis:**
- SLO compliance tracking
- Latency percentiles
- Resource efficiency metrics
- Oscillation detection
- Comparison framework

**Production Validation:**
- Validation against production traces
- Statistical comparison tools
- Configurable fidelity levels

The simulation enables rapid experimentation with autoscaling strategies while maintaining high fidelity to production behavior, supporting the goals outlined in [`chatAS.md`](chatAS.md).

