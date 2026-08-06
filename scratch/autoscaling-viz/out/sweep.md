# Parameter sweeps — trends & calibration

Metrics per run: `good%` (≤2s, pinned), `failed%` (>60s, pinned), `wait_p90` (s), `rep_max` (peak fleet), `rep·s` (usable replica-seconds), `prov·s` (billed incl. boot/drain), `util` (delivered ÷ usable capacity paid for). `*` = each section's own canonical baseline (setup=90; drain=20 for BOTH Q sizers — a standing rule so they compare on a level field; headroom=1.3; sat_frac=0.85).

### setup-lag — setup (boot lag) sweep

Clairvoyant demand-tracking commands landing `setup` s late. Isolates boot lag alone (no backlog term). Context: setup=90 is the real boot time; the point is that it is where quality collapses.

| setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| 30 | 99.6 | 0.0 | 0.0 | 5 | 1566 | 1716 | 0.65 |
| 60 | 90.2 | 0.0 | 1.7 | 4 | 1430 | 1716 | 0.71 |
| 90* | 36.2 | 0.4 | 31.7 | 4 | 1309 | 1714 | 0.77 |

### queue-aware — drain_time aggression curve (setup 60 vs 90)

Reactive backlog-drain sizer, NO upper cap. `drain_time` is the deadline to clear the current queue; shorter → size for more replicas. But it has no dead-time compensation, so replicas ordered still boot `setup` s late — watch whether aggression buys good% or just prov·s (boot-lag waste).

| setup | drain | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 60 | 3 | 86.5 | 0.1 | 3.1 | 4 | 1438 | 1783 | 0.70 |
| 60 | 5 | 86.5 | 0.1 | 3.1 | 4 | 1438 | 1753 | 0.70 |
| 60 | 8 | 86.5 | 0.1 | 3.1 | 4 | 1438 | 1738 | 0.70 |
| 60 | 10 | 62.5 | 0.1 | 10.2 | 4 | 1436 | 1721 | 0.70 |
| 60 | 15 | 62.5 | 0.1 | 10.2 | 4 | 1436 | 1721 | 0.70 |
| 60 | 20* | 62.5 | 0.1 | 10.2 | 4 | 1436 | 1721 | 0.70 |
| 60 | 30 | 41.6 | 0.1 | 22.3 | 4 | 1392 | 1692 | 0.73 |
| 90* | 3 | 78.9 | 1.1 | 22.7 | 4 | 1458 | 2598 | 0.69 |
| 90* | 5 | 77.1 | 1.1 | 30.7 | 4 | 1470 | 2310 | 0.69 |
| 90* | 8 | 70.7 | 1.1 | 30.7 | 4 | 1411 | 2056 | 0.72 |
| 90* | 10 | 69.0 | 1.1 | 40.2 | 4 | 1429 | 2074 | 0.71 |
| 90* | 15 | 69.4 | 1.1 | 40.2 | 4 | 1438 | 1978 | 0.70 |
| 90* | 20* | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1872 | 0.73 |
| 90* | 30 | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1826 | 0.73 |

### qexp — proj_setup dial (sim boots in 90s regardless)

Anticipatory Qexp sizing to the projected backlog peak. `proj_setup` is the boot lead the projection ASSUMES; the sim always applies setup=90. Under-predict (<90) → anticipates less, drifts toward reactive; over-predict (>90) → orders earlier, trades a little cost for tail latency. Stable and self-correcting across the range. `*` = true setup.

| proj_setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| 45 | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1872 | 0.73 |
| 60 | 36.2 | 1.1 | 32.6 | 4 | 1389 | 1854 | 0.73 |
| 75 | 36.2 | 1.1 | 32.6 | 4 | 1389 | 1854 | 0.73 |
| 90* | 70.7 | 1.1 | 30.7 | 4 | 1411 | 1861 | 0.72 |
| 105 | 74.5 | 1.1 | 24.9 | 4 | 1427 | 1877 | 0.71 |
| 120 | 78.0 | 1.1 | 17.6 | 4 | 1440 | 1920 | 0.70 |
| 135 | 78.0 | 1.1 | 17.6 | 4 | 1440 | 1920 | 0.70 |
| 180 | 35.4 | 1.1 | 16.8 | 4 | 1400 | 2120 | 0.72 |

### headroom — static per-replica margin (queue-aware vs Qexp)

Static margin dial (§2.6) at the real 90s boot (both Q sizers at the shared drain=20). More headroom = more replicas = fewer requests per pod = shorter queue = less wait, monotonically, for more prov·s. This is headroom's CAPACITY role; its §2.7 speed role does not appear on the wait metric (see ρ note below). `*` = canonical baseline (1.3). The pick is the steepest part of the curve — max marginal quality per unit margin.

| sizer | headroom | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| qaware | 1.0 | 17.1 | 1.1 | 46.7 | 3 | 1170 | 1576 | 0.86 |
| qaware | 1.1 | 27.6 | 1.1 | 40.2 | 4 | 1272 | 1677 | 0.79 |
| qaware | 1.2 | 29.5 | 1.1 | 40.2 | 4 | 1306 | 1742 | 0.77 |
| qaware | 1.3* | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1872 | 0.73 |
| qaware | 1.5 | 74.2 | 1.1 | 40.2 | 5 | 1554 | 2139 | 0.65 |
| qaware | 1.75 | 75.3 | 1.1 | 40.2 | 6 | 1745 | 2375 | 0.58 |
| qaware | 2.0 | 78.7 | 1.1 | 32.6 | 6 | 1920 | 2625 | 0.53 |
| qexp | 1.0 | 28.4 | 1.1 | 38.3 | 5 | 1268 | 1898 | 0.80 |
| qexp | 1.1 | 46.6 | 1.1 | 32.6 | 4 | 1303 | 1663 | 0.78 |
| qexp | 1.2 | 66.2 | 1.1 | 30.7 | 4 | 1365 | 1770 | 0.74 |
| qexp | 1.3* | 70.7 | 1.1 | 30.7 | 4 | 1411 | 1861 | 0.72 |
| qexp | 1.5 | 79.1 | 1.1 | 24.9 | 5 | 1542 | 2052 | 0.66 |
| qexp | 1.75 | 82.7 | 1.1 | 17.6 | 6 | 1734 | 2379 | 0.58 |
| qexp | 2.0 | 85.0 | 1.1 | 17.6 | 6 | 1980 | 2640 | 0.51 |

### headroom × drain_time (queue-aware) — static margin vs dynamic aggression

2-D: static per-replica margin (headroom) against the reactive backlog aggression lever (shorter drain_time = order more to clear faster). Where a leaner (low-headroom) line reaches a fatter line's good%, aggression has substituted for static margin — at its own boot-lag cost. setup=90.

| headroom | drain | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 3 | 34.3 | 1.1 | 31.4 | 7 | 1352 | 3646 | 0.75 |
| 1.0 | 5 | 30.6 | 1.1 | 38.1 | 7 | 1330 | 2845 | 0.76 |
| 1.0 | 8 | 26.2 | 1.1 | 41.1 | 6 | 1297 | 2467 | 0.78 |
| 1.0 | 10 | 26.5 | 1.1 | 41.1 | 6 | 1308 | 2328 | 0.77 |
| 1.0 | 15 | 19.8 | 1.1 | 40.2 | 3 | 1178 | 1598 | 0.86 |
| 1.0 | 20* | 17.1 | 1.1 | 46.7 | 3 | 1170 | 1576 | 0.86 |
| 1.0 | 30 | 16.8 | 1.1 | 46.7 | 4 | 1211 | 1646 | 0.83 |
| 1.3* | 3 | 78.9 | 1.1 | 22.7 | 4 | 1458 | 2598 | 0.69 |
| 1.3* | 5 | 77.1 | 1.1 | 30.7 | 4 | 1470 | 2310 | 0.69 |
| 1.3* | 8 | 70.7 | 1.1 | 30.7 | 4 | 1411 | 2056 | 0.72 |
| 1.3* | 10 | 69.0 | 1.1 | 40.2 | 4 | 1429 | 2074 | 0.71 |
| 1.3* | 15 | 69.4 | 1.1 | 40.2 | 4 | 1438 | 1978 | 0.70 |
| 1.3* | 20* | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1872 | 0.73 |
| 1.3* | 30 | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1826 | 0.73 |
| 1.5 | 3 | 83.4 | 1.1 | 22.7 | 5 | 1581 | 2901 | 0.64 |
| 1.5 | 5 | 81.7 | 1.1 | 30.7 | 5 | 1564 | 2569 | 0.65 |
| 1.5 | 8 | 75.3 | 1.1 | 30.7 | 5 | 1528 | 2308 | 0.66 |
| 1.5 | 10 | 75.3 | 1.1 | 30.7 | 5 | 1528 | 2218 | 0.66 |
| 1.5 | 15 | 74.2 | 1.1 | 40.2 | 5 | 1554 | 2199 | 0.65 |
| 1.5 | 20* | 74.2 | 1.1 | 40.2 | 5 | 1554 | 2139 | 0.65 |
| 1.5 | 30 | 62.8 | 1.1 | 40.2 | 5 | 1554 | 2004 | 0.65 |
| 2.0 | 3 | 86.3 | 1.1 | 15.7 | 6 | 2016 | 3606 | 0.50 |
| 2.0 | 5 | 84.8 | 1.1 | 22.7 | 6 | 2024 | 3254 | 0.50 |
| 2.0 | 8 | 81.8 | 1.1 | 30.7 | 6 | 1956 | 2961 | 0.52 |
| 2.0 | 10 | 80.2 | 1.1 | 30.7 | 6 | 1959 | 2859 | 0.52 |
| 2.0 | 15 | 80.2 | 1.1 | 30.7 | 6 | 1959 | 2724 | 0.52 |
| 2.0 | 20* | 78.7 | 1.1 | 32.6 | 6 | 1920 | 2625 | 0.53 |
| 2.0 | 30 | 75.3 | 1.1 | 40.2 | 6 | 1902 | 2592 | 0.53 |

### headroom × proj_setup (Qexp) — static margin vs dynamic anticipation

2-D: static per-replica margin (headroom) against anticipation (assumed boot lead; sim always boots in 90s). More anticipation orders earlier, so a lean fleet can hold a fatter fleet's quality — anticipation substituting for margin. `*` proj_setup = true 90s setup.

| headroom | proj_setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 45 | 17.1 | 1.1 | 46.7 | 3 | 1170 | 1576 | 0.86 |
| 1.0 | 60 | 17.1 | 1.1 | 46.7 | 3 | 1170 | 1576 | 0.86 |
| 1.0 | 75 | 28.6 | 1.1 | 38.1 | 5 | 1272 | 1887 | 0.79 |
| 1.0 | 90* | 28.4 | 1.1 | 38.3 | 5 | 1268 | 1898 | 0.80 |
| 1.0 | 105 | 28.6 | 1.1 | 38.1 | 5 | 1275 | 1950 | 0.79 |
| 1.0 | 120 | 28.6 | 1.1 | 40.0 | 6 | 1279 | 2014 | 0.79 |
| 1.0 | 135 | 28.6 | 1.1 | 40.0 | 6 | 1279 | 2029 | 0.79 |
| 1.0 | 180 | 24.9 | 1.1 | 40.0 | 5 | 1254 | 2200 | 0.81 |
| 1.3* | 45 | 32.9 | 1.1 | 40.2 | 4 | 1376 | 1872 | 0.73 |
| 1.3* | 60 | 36.2 | 1.1 | 32.6 | 4 | 1389 | 1854 | 0.73 |
| 1.3* | 75 | 36.2 | 1.1 | 32.6 | 4 | 1389 | 1854 | 0.73 |
| 1.3* | 90* | 70.7 | 1.1 | 30.7 | 4 | 1411 | 1861 | 0.72 |
| 1.3* | 105 | 74.5 | 1.1 | 24.9 | 4 | 1427 | 1877 | 0.71 |
| 1.3* | 120 | 78.0 | 1.1 | 17.6 | 4 | 1440 | 1920 | 0.70 |
| 1.3* | 135 | 78.0 | 1.1 | 17.6 | 4 | 1440 | 1920 | 0.70 |
| 1.3* | 180 | 35.4 | 1.1 | 16.8 | 4 | 1400 | 2120 | 0.72 |
| 1.5 | 45 | 74.2 | 1.1 | 40.2 | 5 | 1554 | 2139 | 0.65 |
| 1.5 | 60 | 60.5 | 1.1 | 32.6 | 5 | 1491 | 2046 | 0.68 |
| 1.5 | 75 | 75.3 | 1.1 | 30.7 | 5 | 1528 | 2068 | 0.66 |
| 1.5 | 90* | 79.1 | 1.1 | 24.9 | 5 | 1542 | 2052 | 0.66 |
| 1.5 | 105 | 82.6 | 1.1 | 17.6 | 5 | 1568 | 2093 | 0.64 |
| 1.5 | 120 | 82.6 | 1.1 | 17.6 | 5 | 1568 | 2108 | 0.64 |
| 1.5 | 135 | 82.6 | 1.1 | 17.6 | 5 | 1568 | 2153 | 0.64 |
| 1.5 | 180 | 87.6 | 1.1 | 7.8 | 5 | 1575 | 2220 | 0.64 |
| 2.0 | 45 | 78.7 | 1.1 | 32.6 | 6 | 1920 | 2625 | 0.53 |
| 2.0 | 60 | 80.3 | 1.1 | 24.9 | 6 | 1964 | 2608 | 0.51 |
| 2.0 | 75 | 82.7 | 1.1 | 17.6 | 6 | 1992 | 2636 | 0.51 |
| 2.0 | 90* | 85.0 | 1.1 | 17.6 | 6 | 1980 | 2640 | 0.51 |
| 2.0 | 105 | 86.3 | 1.1 | 15.7 | 6 | 2016 | 2706 | 0.50 |
| 2.0 | 120 | 85.9 | 1.1 | 12.4 | 6 | 1920 | 2714 | 0.53 |
| 2.0 | 135 | 87.7 | 1.1 | 7.8 | 6 | 1923 | 2748 | 0.53 |
| 2.0 | 180 | 89.9 | 1.1 | 2.3 | 6 | 1948 | 2878 | 0.52 |

### ρ note — why the §2.7 speed-up does not show in these sweeps

All sweeps run at the canonical `RHO = 2` (empty pods decode ~2× faster than packed ones, §2.7). Yet `good%` / `wait_p90` are **identical** to a `RHO = 1` run at every headroom, and only `prov·s` shifts (a slightly shorter drain tail). The reason is structural: the quality bands key on **waiting time** (arrival→service-start), and whenever a backlog exists the router keeps every pod **packed at `usable_C` (k≈1)**, where `rate = service_rate` — exactly the fixed-rate value. The decode speed-up only fires when a pod is *under-full* (k<1), which is precisely when there is no queue and wait≈0 already. So on the wait metric, headroom buys **capacity/slack**, not speed; the §2.7 speed benefit is a *service-latency* effect (visible in `time/work`, not plotted here). This refines the 7(b) framing — see the design doc §2.7 / §8.1(7b).

## Cap sweep — actuation ceiling (max_replicas) as the swept axis

The seven scenarios pin `max_replicas` at the KEDA guide's 10. Here it is swept per sustained shape. **This is not the same knob as HPA-queue's `q_target`** (the per-replica queue-depth target that sets aggression — swept in `stability.md`, held ≤10 there): raising the *cap* lets a policy provision *more*; raising `q_target` makes HPA-queue want *fewer* replicas. So Dean's "a less aggressive HPA doesn't grow cost as fast" is about `q_target` (`stability.md`), not the cap — along *this* axis HPA-queue's cost grows fast.

Reading the cost column: `hpa-queue` and `static` rise **∝ cap** — HPA's raw desired (`ceil` of the whole backlog) runs far above any sane cap, so it pins to the ceiling, just as `static`'s fleet *is* the ceiling; both hit ~2.5× ideal at cap 10 and climb to 7–9× by cap 30. The work-rate Q sizers (`queue-aware`, `qexp`) behave completely differently: their **usable** fleet peaks low (6–15 replicas on these shapes — see `rep_max`), well under every swept cap, so a looser ceiling can't be filled with useful work. Their cost still creeps up a little past that peak (speculative boot orders the backlog term issues and then cancels before they become usable — pure boot-lag waste) and then **flattens** by cap ≈15–20, staying ~1.4–2.1× ideal. Crucially that creep buys **zero** extra quality: `served ≤15s` is flat across the cap once it clears the usable peak. `ideal` is flat throughout (usable peak ~5, cap never binds).

One caution on `hpa-queue`'s quality column: it is **non-monotone in the cap** (e.g. trapezoid dips at cap 15, stepup dips at cap 8) — the same deterministic dead-time / mistimed-scale-down fragility the `q_target` sweep shows in `stability.md`, not a smooth cap response. Cross-ref: for the *aggression* axis at a fixed cap, see that HPA-queue `q_target` sweep.

### cap sweep (trapezoid) — cost: provisioned·seconds (×ideal)

Billed fleet-seconds per policy as the cap rises; `(N×)` = multiple of `ideal` at the same cap. `hpa-queue`/`static` track the cap; the Q sizers plateau once the cap clears their natural peak.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 2359 | 2428 (1.0×) | 2550 (1.1×) | 2619 (1.1×) | 3001 (1.3×) |
| 8 | 2359 | 2911 (1.2×) | 2982 (1.3×) | 4695 (2.0×) | 4802 (2.0×) |
| 10* | 2359 | 3100 (1.3×) | 3182 (1.3×) | 5865 (2.5×) | 6002 (2.5×) |
| 12 | 2359 | 3250 (1.4×) | 3332 (1.4×) | 7035 (3.0×) | 7203 (3.1×) |
| 15 | 2359 | 3400 (1.4×) | 3437 (1.5×) | 8512 (3.6×) | 9004 (3.8×) |
| 20 | 2359 | 3400 (1.4×) | 3452 (1.5×) | 11715 (5.0×) | 12005 (5.1×) |
| 30 | 2359 | 3400 (1.4×) | 3452 (1.5×) | 17565 (7.4×) | 18007 (7.6×) |

### cap sweep (trapezoid) — quality: served ≤15s %

Share served within 15s (the "works" bar). More ceiling buys the Q sizers headroom to clear the backlog; past their peak it stops mattering.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 100.0 | 52.5 | 67.3 | 74.7 | 100.0 |
| 8 | 100.0 | 67.8 | 79.2 | 85.4 | 100.0 |
| 10* | 100.0 | 69.0 | 80.3 | 86.5 | 100.0 |
| 12 | 100.0 | 69.0 | 80.3 | 87.4 | 100.0 |
| 15 | 100.0 | 69.0 | 80.3 | 68.3 | 100.0 |
| 20 | 100.0 | 69.0 | 80.3 | 87.8 | 100.0 |
| 30 | 100.0 | 69.0 | 80.3 | 87.8 | 100.0 |

### cap sweep (stepup) — cost: provisioned·seconds (×ideal)

Billed fleet-seconds per policy as the cap rises; `(N×)` = multiple of `ideal` at the same cap. `hpa-queue`/`static` track the cap; the Q sizers plateau once the cap clears their natural peak.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 2227 | 2475 (1.1×) | 2591 (1.2×) | 2940 (1.3×) | 3001 (1.3×) |
| 8 | 2227 | 2917 (1.3×) | 3158 (1.4×) | 4372 (2.0×) | 4802 (2.2×) |
| 10* | 2227 | 3007 (1.4×) | 3354 (1.5×) | 5865 (2.6×) | 6002 (2.7×) |
| 12 | 2227 | 3007 (1.4×) | 3458 (1.6×) | 7035 (3.2×) | 7203 (3.2×) |
| 15 | 2227 | 3007 (1.4×) | 3518 (1.6×) | 8790 (3.9×) | 9004 (4.0×) |
| 20 | 2227 | 3007 (1.4×) | 3518 (1.6×) | 11715 (5.3×) | 12005 (5.4×) |
| 30 | 2227 | 3007 (1.4×) | 3518 (1.6×) | 17565 (7.9×) | 18008 (8.1×) |

### cap sweep (stepup) — quality: served ≤15s %

Share served within 15s (the "works" bar). More ceiling buys the Q sizers headroom to clear the backlog; past their peak it stops mattering.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 100.0 | 61.6 | 69.3 | 92.7 | 100.0 |
| 8 | 100.0 | 63.6 | 72.4 | 54.3 | 100.0 |
| 10* | 100.0 | 63.6 | 72.4 | 93.1 | 100.0 |
| 12 | 100.0 | 63.6 | 72.4 | 93.1 | 100.0 |
| 15 | 100.0 | 63.6 | 72.4 | 93.1 | 100.0 |
| 20 | 100.0 | 63.6 | 72.4 | 93.1 | 100.0 |
| 30 | 100.0 | 63.6 | 72.4 | 93.1 | 100.0 |

### cap sweep (stepdown) — cost: provisioned·seconds (×ideal)

Billed fleet-seconds per policy as the cap rises; `(N×)` = multiple of `ideal` at the same cap. `hpa-queue`/`static` track the cap; the Q sizers plateau once the cap clears their natural peak.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 1976 | 2031 (1.0×) | 2049 (1.0×) | 2404 (1.2×) | 3001 (1.5×) |
| 8 | 1976 | 2493 (1.3×) | 2543 (1.3×) | 4695 (2.4×) | 4802 (2.4×) |
| 10* | 1976 | 2740 (1.4×) | 2824 (1.4×) | 4368 (2.2×) | 6002 (3.0×) |
| 12 | 1976 | 3019 (1.5×) | 3084 (1.6×) | 7035 (3.6×) | 7203 (3.6×) |
| 15 | 1976 | 3259 (1.6×) | 3460 (1.8×) | 8790 (4.4×) | 9004 (4.6×) |
| 20 | 1976 | 3559 (1.8×) | 3850 (1.9×) | 11715 (5.9×) | 12005 (6.1×) |
| 30 | 1976 | 3604 (1.8×) | 4180 (2.1×) | 17565 (8.9×) | 18007 (9.1×) |

### cap sweep (stepdown) — quality: served ≤15s %

Share served within 15s (the "works" bar). More ceiling buys the Q sizers headroom to clear the backlog; past their peak it stops mattering.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 100.0 | 31.7 | 32.9 | 33.9 | 100.0 |
| 8 | 100.0 | 50.6 | 62.1 | 63.0 | 100.0 |
| 10* | 100.0 | 55.4 | 65.7 | 67.7 | 100.0 |
| 12 | 100.0 | 57.0 | 67.8 | 70.0 | 100.0 |
| 15 | 100.0 | 57.0 | 69.5 | 72.3 | 100.0 |
| 20 | 100.0 | 57.0 | 69.5 | 74.3 | 100.0 |
| 30 | 100.0 | 57.0 | 69.5 | 75.1 | 100.0 |

**bump / spike are cap-inert for the Q sizers** and so are omitted from the per-shape switcher: their offered load needs only ≈4–6 replicas at the peak, well under every swept cap, so `queue-aware`/`qexp`/`ideal` never touch the ceiling there (only `hpa-queue`/`static`, which pin to the cap on any shape, would still scale with it).

