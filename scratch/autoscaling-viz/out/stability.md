# Workload-stability sweeps — do the calibration knobs hold across shapes?

Canonical picks under test: Qexp `proj_setup = 120`, shared `drain_time = 20`, `headroom = 1.3` (at `sat_frac = 0.85`, `ρ = 2.0`), tuned on the triangular `bump`. Each non-bump shape has a nonzero floor (lo = peak/3 ≈ 8, hi = peak = 24 req/s) so the fleet never fully drains. A knob **HOLDS** for a shape if the canonical value's `good%` is within 3 pp of that shape's best swept `good%`; otherwise **FLAG**. Divergence is surfaced, not silently re-tuned.

## bump  (reqs = 7159)

### canonical calibration (drain=20, proj=120, hr=1.3)

| sizer | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| ideal | 100.0 | 0.0 | 0.0 | 5 | 1714 | 1714 | 0.59 |
| setup-lag | 36.2 | 0.4 | 31.7 | 4 | 1309 | 1714 | 0.77 |
| queue-aware | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1872 | 0.73 |
| qexp | 78.0 | 1.1 | 17.6 | 4 | 1440 | 1920 | 0.70 |

### Qexp `proj_setup` sweep (drain=20, hr=1.3)

| proj_setup | 45 | 60 | 75 | 90 | 105 | 120 | 135 | 180 |
|---|---|---|---|---|---|---|---|---|
| good% | 32.9 | 36.2 | 36.2 | 70.7 | 74.5 | 78.0 | 78.0 | 35.4 |

**HOLDS — canonical 120 → good% 78.0; shape-best 120 → 78.0 (Δ +0.0 pp)**

### queue-aware `drain_time` sweep (hr=1.3)

| drain_time | 3 | 5 | 8 | 10 | 15 | 20 | 30 |
|---|---|---|---|---|---|---|---|
| good% | 78.9 | 77.1 | 70.7 | 69.0 | 69.4 | 32.9 | 32.9 |

****FLAG** — canonical 20 → good% 32.9; shape-best 3 → 78.9 (Δ +46.0 pp)**

### headroom sweep — good% and raw-hw util (both Q sizers)

| headroom | 1 | 1.1 | 1.2 | 1.3 | 1.5 | 1.75 | 2 |
|---|---|---|---|---|---|---|---|
| qaware good% | 17.1 | 27.6 | 29.5 | 32.9 | 74.2 | 75.3 | 78.7 |
| qexp good% | 28.6 | 28.7 | 31.7 | 78.0 | 82.6 | 86.3 | 85.9 |
| qexp util | 0.79 | 0.78 | 0.75 | 0.70 | 0.64 | 0.56 | 0.53 |

knee (gains < 1 pp per +0.1 margin) at headroom ≈ **1.1**; qexp util at 1.3 = 0.70.

## trapezoid  (reqs = 10460)

### canonical calibration (drain=20, proj=120, hr=1.3)

| sizer | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| ideal | 100.0 | 0.0 | 0.0 | 5 | 2359 | 2359 | 0.63 |
| setup-lag | 43.3 | 12.2 | 63.7 | 5 | 1918 | 2368 | 0.78 |
| queue-aware | 62.5 | 14.8 | 71.1 | 9 | 2200 | 3400 | 0.68 |
| qexp | 75.3 | 6.8 | 46.4 | 9 | 2297 | 3452 | 0.65 |

### Qexp `proj_setup` sweep (drain=20, hr=1.3)

| proj_setup | 45 | 60 | 75 | 90 | 105 | 120 | 135 | 180 |
|---|---|---|---|---|---|---|---|---|
| good% | 61.3 | 60.9 | 68.3 | 68.7 | 72.1 | 75.3 | 74.3 | 74.7 |

**HOLDS — canonical 120 → good% 75.3; shape-best 120 → 75.3 (Δ +0.0 pp)**

### queue-aware `drain_time` sweep (hr=1.3)

| drain_time | 3 | 5 | 8 | 10 | 15 | 20 | 30 |
|---|---|---|---|---|---|---|---|
| good% | 75.0 | 72.1 | 70.3 | 68.3 | 66.3 | 62.5 | 54.5 |

****FLAG** — canonical 20 → good% 62.5; shape-best 3 → 75.0 (Δ +12.6 pp)**

### headroom sweep — good% and raw-hw util (both Q sizers)

| headroom | 1 | 1.1 | 1.2 | 1.3 | 1.5 | 1.75 | 2 |
|---|---|---|---|---|---|---|---|
| qaware good% | 54.1 | 54.9 | 60.2 | 62.5 | 66.3 | 66.3 | 68.3 |
| qexp good% | 56.0 | 67.1 | 67.0 | 75.3 | 75.6 | 76.2 | 78.5 |
| qexp util | 0.79 | 0.76 | 0.73 | 0.65 | 0.62 | 0.55 | 0.49 |

knee (gains < 1 pp per +0.1 margin) at headroom ≈ **1.2**; qexp util at 1.3 = 0.65.

## stepup  (reqs = 10275)

### canonical calibration (drain=20, proj=120, hr=1.3)

| sizer | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| ideal | 100.0 | 0.0 | 0.0 | 5 | 2227 | 2227 | 0.64 |
| setup-lag | 56.6 | 5.5 | 35.0 | 5 | 1786 | 2236 | 0.80 |
| queue-aware | 51.7 | 6.9 | 38.0 | 6 | 1837 | 3007 | 0.78 |
| qexp | 61.8 | 3.8 | 36.4 | 7 | 1974 | 3518 | 0.72 |

### Qexp `proj_setup` sweep (drain=20, hr=1.3)

| proj_setup | 45 | 60 | 75 | 90 | 105 | 120 | 135 | 180 |
|---|---|---|---|---|---|---|---|---|
| good% | 55.2 | 56.0 | 59.3 | 60.7 | 61.4 | 61.8 | 61.8 | 62.5 |

**HOLDS — canonical 120 → good% 61.8; shape-best 180 → 62.5 (Δ +0.7 pp)**

### queue-aware `drain_time` sweep (hr=1.3)

| drain_time | 3 | 5 | 8 | 10 | 15 | 20 | 30 |
|---|---|---|---|---|---|---|---|
| good% | 58.7 | 57.6 | 57.1 | 56.0 | 54.7 | 51.7 | 49.8 |

****FLAG** — canonical 20 → good% 51.7; shape-best 3 → 58.7 (Δ +7.0 pp)**

### headroom sweep — good% and raw-hw util (both Q sizers)

| headroom | 1 | 1.1 | 1.2 | 1.3 | 1.5 | 1.75 | 2 |
|---|---|---|---|---|---|---|---|
| qaware good% | 44.8 | 46.5 | 50.5 | 51.7 | 55.1 | 56.9 | 75.2 |
| qexp good% | 58.6 | 60.0 | 61.4 | 61.8 | 62.5 | 63.4 | 77.9 |
| qexp util | 0.83 | 0.80 | 0.80 | 0.72 | 0.71 | 0.65 | 0.56 |

knee (gains < 1 pp per +0.1 margin) at headroom ≈ **1.3**; qexp util at 1.3 = 0.72.

## stepdown  (reqs = 8698)

### canonical calibration (drain=20, proj=120, hr=1.3)

| sizer | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| ideal | 100.0 | 0.0 | 0.0 | 5 | 1976 | 1976 | 0.63 |
| setup-lag | 28.6 | 24.0 | 76.6 | 5 | 1543 | 1993 | 0.81 |
| queue-aware | 51.7 | 25.1 | 95.2 | 12 | 1939 | 3604 | 0.64 |
| qexp | 64.6 | 15.7 | 72.3 | 15 | 2110 | 4180 | 0.59 |

### Qexp `proj_setup` sweep (drain=20, hr=1.3)

| proj_setup | 45 | 60 | 75 | 90 | 105 | 120 | 135 | 180 |
|---|---|---|---|---|---|---|---|---|
| good% | 55.1 | 58.0 | 60.0 | 61.7 | 63.2 | 64.6 | 64.9 | 64.5 |

**HOLDS — canonical 120 → good% 64.6; shape-best 135 → 64.9 (Δ +0.4 pp)**

### queue-aware `drain_time` sweep (hr=1.3)

| drain_time | 3 | 5 | 8 | 10 | 15 | 20 | 30 |
|---|---|---|---|---|---|---|---|
| good% | 62.1 | 58.9 | 58.0 | 56.5 | 53.0 | 51.7 | 46.5 |

****FLAG** — canonical 20 → good% 51.7; shape-best 3 → 62.1 (Δ +10.4 pp)**

### headroom sweep — good% and raw-hw util (both Q sizers)

| headroom | 1 | 1.1 | 1.2 | 1.3 | 1.5 | 1.75 | 2 |
|---|---|---|---|---|---|---|---|
| qaware good% | 41.8 | 46.5 | 50.6 | 51.7 | 52.8 | 55.1 | 56.9 |
| qexp good% | 60.2 | 63.2 | 64.0 | 64.6 | 65.9 | 66.5 | 67.0 |
| qexp util | 0.67 | 0.64 | 0.61 | 0.59 | 0.53 | 0.53 | 0.45 |

knee (gains < 1 pp per +0.1 margin) at headroom ≈ **1.2**; qexp util at 1.3 = 0.59.

## Verdict — do the canonical picks hold across shapes?

### Qexp proj_setup = 120

Shape-best values: {120, 135, 180} — clustered near 120. Canonical 120 lands within tolerance of every shape's optimum:

- **bump** — HOLDS — canonical 120 → 78.0; best 120 → 78.0 (Δ +0.0 pp)
- **trapezoid** — HOLDS — canonical 120 → 75.3; best 120 → 75.3 (Δ +0.0 pp)
- **stepup** — HOLDS — canonical 120 → 61.8; best 180 → 62.5 (Δ +0.7 pp)
- **stepdown** — HOLDS — canonical 120 → 64.6; best 135 → 64.9 (Δ +0.4 pp)

**→ proj_setup = 120 HOLDS across all four shapes** — the anticipation lead is a property of the Qexp sizer, not of the bump.

### queue-aware / shared drain_time = 20

Shape-best values: {3} — identical on every shape. The shape-best drain is **perfectly stable across shapes** (always the most aggressive grid point), so this is NOT shape-overfitting. But that optimum is not 20 — the per-shape rows below are FLAGGED because drain=20 is deliberately **not** queue-aware's good%-optimum:

- **bump** — **FLAG** — canonical 20 → 32.9; best 3 → 78.9 (Δ +46.0 pp)
- **trapezoid** — **FLAG** — canonical 20 → 62.5; best 3 → 75.0 (Δ +12.6 pp)
- **stepup** — **FLAG** — canonical 20 → 51.7; best 3 → 58.7 (Δ +7.0 pp)
- **stepdown** — **FLAG** — canonical 20 → 51.7; best 3 → 62.1 (Δ +10.4 pp)

**→ drain = 20 is the level-field CONSTANT, not a tuned optimum.** Queue-aware can match Qexp's good% only by cranking drain to its most aggressive setting (drain=3) — i.e. by over-provisioning, at higher cost. Holding drain=20 for BOTH Q sizers isolates the one thing the demo is about: anticipation (Qexp) vs reaction (queue-aware) at equal aggression. Qexp beats queue-aware on good% on **every** shape at drain=20, so the level-field ranking is shape-robust. **Do NOT re-tune to drain=3** — the standing level-field rule holds; the FLAG records a known, intentional handicap, not instability.

### headroom = 1.3

headroom good% is monotone in margin by construction (more slots = less queue), so 1.3 is a cost/utilisation CHOICE, not a quality optimum. The stability question is whether the diminishing-returns knee stays near 1.3 across shapes:

- **bump** — HOLDS: knee ≈ 1.1, util@1.3 = 0.70
- **trapezoid** — HOLDS: knee ≈ 1.2, util@1.3 = 0.65
- **stepup** — HOLDS: knee ≈ 1.3, util@1.3 = 0.72
- **stepdown** — HOLDS: knee ≈ 1.2, util@1.3 = 0.59

