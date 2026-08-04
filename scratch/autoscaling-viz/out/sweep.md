# Parameter sweeps — trends & calibration

Metrics per run: `good%` (≤2s, pinned), `failed%` (>60s, pinned), `wait_p90` (s), `rep_max` (peak fleet), `rep·s` (usable replica-seconds), `prov·s` (billed incl. boot/drain), `util` (delivered ÷ usable capacity paid for). `*` = the canonical scenario baseline (setup=90, drain=30).

### setup-lag — setup (boot lag) sweep

Clairvoyant demand-tracking commands landing `setup` s late. Isolates boot lag alone (no backlog term). Context: setup=90 is the real boot time; the point is that it is where quality collapses.

| setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| 30 | 99.6 | 0.0 | 0.0 | 5 | 1709 | 1859 | 0.72 |
| 60 | 58.7 | 0.0 | 9.6 | 5 | 1537 | 1837 | 0.80 |
| 90* | 19.7 | 0.4 | 39.6 | 5 | 1422 | 1872 | 0.86 |

### queue-aware — drain_time aggression curve (setup 60 vs 90)

Reactive backlog-drain sizer, NO upper cap. `drain_time` is the deadline to clear the current queue; shorter → size for more replicas. But it has no dead-time compensation, so replicas ordered still boot `setup` s late — watch whether aggression buys good% or just prov·s (boot-lag waste).

| setup | drain | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 60 | 3 | 64.0 | 0.1 | 13.0 | 5 | 1688 | 2274 | 0.73 |
| 60 | 5 | 53.1 | 0.1 | 20.5 | 5 | 1632 | 2052 | 0.75 |
| 60 | 8 | 49.8 | 0.1 | 20.5 | 5 | 1636 | 1981 | 0.75 |
| 60 | 10 | 49.8 | 0.1 | 20.5 | 5 | 1636 | 1951 | 0.75 |
| 60 | 15 | 38.7 | 0.1 | 27.0 | 5 | 1606 | 1936 | 0.76 |
| 60 | 20 | 38.7 | 0.1 | 27.0 | 5 | 1606 | 1921 | 0.76 |
| 60 | 30* | 32.4 | 0.1 | 27.0 | 5 | 1584 | 1884 | 0.77 |
| 90* | 3 | 50.8 | 1.2 | 29.8 | 6 | 1689 | 3849 | 0.73 |
| 90* | 5 | 27.8 | 1.2 | 30.9 | 5 | 1551 | 3036 | 0.79 |
| 90* | 8 | 36.1 | 1.2 | 35.1 | 5 | 1592 | 2687 | 0.77 |
| 90* | 10 | 26.4 | 1.2 | 35.1 | 5 | 1551 | 2526 | 0.79 |
| 90* | 15 | 34.6 | 1.6 | 45.7 | 5 | 1584 | 2214 | 0.77 |
| 90* | 20 | 34.6 | 1.6 | 45.7 | 5 | 1584 | 2139 | 0.77 |
| 90* | 30* | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |

### qexp — proj_setup dial (sim boots in 90s regardless)

Anticipatory Qexp sizing to the projected backlog peak. `proj_setup` is the boot lead the projection ASSUMES; the sim always applies setup=90. Under-predict (<90) → anticipates less, drifts toward reactive; over-predict (>90) → orders earlier, trades a little cost for tail latency. Stable and self-correcting across the range. `*` = true setup.

| proj_setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| 45 | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |
| 60 | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |
| 75 | 29.8 | 1.2 | 43.4 | 5 | 1568 | 2063 | 0.78 |
| 90* | 34.6 | 1.2 | 43.0 | 5 | 1578 | 2043 | 0.78 |
| 105 | 25.2 | 1.2 | 35.1 | 5 | 1527 | 2157 | 0.80 |
| 120 | 26.8 | 1.2 | 30.7 | 5 | 1543 | 2158 | 0.80 |
| 135 | 28.3 | 1.2 | 25.4 | 5 | 1557 | 2202 | 0.79 |
| 180 | 31.7 | 1.2 | 25.4 | 6 | 1593 | 2313 | 0.77 |

### headroom — static per-replica margin (queue-aware vs Qexp)

Static margin dial (§2.6) at the real 90s boot / 30s drain. More headroom = more replicas = fewer requests per pod = shorter queue = less wait, monotonically, for more prov·s. This is headroom's CAPACITY role; its §2.7 speed role does not appear on the wait metric (see ρ note below). `*` = canonical baseline (1.2).

| sizer | headroom | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| qaware | 1.0 | 22.1 | 3.5 | 56.8 | 5 | 1466 | 1916 | 0.84 |
| qaware | 1.1 | 21.1 | 1.6 | 50.6 | 4 | 1471 | 1981 | 0.83 |
| qaware | 1.2* | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |
| qaware | 1.35 | 38.3 | 1.6 | 45.7 | 5 | 1670 | 2255 | 0.73 |
| qaware | 1.5 | 64.5 | 1.6 | 45.7 | 6 | 1876 | 2461 | 0.65 |
| qaware | 1.75 | 69.8 | 1.6 | 45.7 | 7 | 2122 | 2856 | 0.58 |
| qaware | 2.0 | 75.6 | 1.2 | 43.0 | 7 | 2234 | 3074 | 0.55 |
| qexp | 1.0 | 22.9 | 1.2 | 43.4 | 4 | 1424 | 1784 | 0.86 |
| qexp | 1.1 | 28.7 | 1.2 | 43.0 | 4 | 1515 | 1935 | 0.81 |
| qexp | 1.2* | 34.6 | 1.2 | 43.0 | 5 | 1578 | 2043 | 0.78 |
| qexp | 1.35 | 58.7 | 1.2 | 35.1 | 5 | 1730 | 2255 | 0.71 |
| qexp | 1.5 | 72.8 | 1.2 | 30.7 | 6 | 1870 | 2410 | 0.66 |
| qexp | 1.75 | 78.6 | 1.2 | 25.4 | 7 | 2106 | 2781 | 0.58 |
| qexp | 2.0 | 80.3 | 1.2 | 25.4 | 7 | 2300 | 3050 | 0.53 |

### headroom × drain_time (queue-aware) — static margin vs dynamic aggression

2-D: static per-replica margin (headroom) against the reactive backlog aggression lever (shorter drain_time = order more to clear faster). Where a leaner (low-headroom) line reaches a fatter line's good%, aggression has substituted for static margin — at its own boot-lag cost. setup=90.

| headroom | drain | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 3 | 44.5 | 1.2 | 29.8 | 7 | 1568 | 3802 | 0.78 |
| 1.0 | 5 | 34.5 | 1.2 | 35.1 | 6 | 1536 | 3051 | 0.80 |
| 1.0 | 8 | 23.5 | 1.2 | 43.0 | 6 | 1498 | 2593 | 0.82 |
| 1.0 | 10 | 23.2 | 1.6 | 45.7 | 6 | 1533 | 2568 | 0.80 |
| 1.0 | 15 | 17.3 | 1.6 | 45.7 | 5 | 1475 | 2255 | 0.83 |
| 1.0 | 20 | 22.9 | 1.6 | 50.6 | 4 | 1432 | 1867 | 0.86 |
| 1.0 | 30* | 22.1 | 3.5 | 56.8 | 5 | 1466 | 1916 | 0.84 |
| 1.2* | 3 | 50.8 | 1.2 | 29.8 | 6 | 1689 | 3849 | 0.73 |
| 1.2* | 5 | 27.8 | 1.2 | 30.9 | 5 | 1551 | 3036 | 0.79 |
| 1.2* | 8 | 36.1 | 1.2 | 35.1 | 5 | 1592 | 2687 | 0.77 |
| 1.2* | 10 | 26.4 | 1.2 | 35.1 | 5 | 1551 | 2526 | 0.79 |
| 1.2* | 15 | 34.6 | 1.6 | 45.7 | 5 | 1584 | 2214 | 0.77 |
| 1.2* | 20 | 34.6 | 1.6 | 45.7 | 5 | 1584 | 2139 | 0.77 |
| 1.2* | 30* | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |
| 1.5 | 3 | 66.2 | 1.2 | 19.6 | 6 | 1847 | 3557 | 0.66 |
| 1.5 | 5 | 82.2 | 1.2 | 29.8 | 6 | 1923 | 3183 | 0.64 |
| 1.5 | 8 | 80.1 | 1.2 | 35.1 | 6 | 1922 | 2927 | 0.64 |
| 1.5 | 10 | 78.2 | 1.2 | 35.1 | 6 | 1911 | 2796 | 0.64 |
| 1.5 | 15 | 72.7 | 1.2 | 35.1 | 6 | 1844 | 2580 | 0.67 |
| 1.5 | 20 | 65.7 | 1.6 | 45.7 | 6 | 1862 | 2612 | 0.66 |
| 1.5 | 30* | 64.5 | 1.6 | 45.7 | 6 | 1876 | 2461 | 0.65 |
| 2.0 | 3 | 85.9 | 1.2 | 16.0 | 7 | 2282 | 4517 | 0.54 |
| 2.0 | 5 | 84.6 | 1.2 | 25.4 | 7 | 2352 | 3852 | 0.52 |
| 2.0 | 8 | 80.8 | 1.2 | 29.8 | 7 | 2288 | 3533 | 0.54 |
| 2.0 | 10 | 81.0 | 1.2 | 30.9 | 7 | 2313 | 3483 | 0.53 |
| 2.0 | 15 | 78.5 | 1.2 | 35.1 | 7 | 2254 | 3244 | 0.54 |
| 2.0 | 20 | 76.9 | 1.2 | 35.1 | 7 | 2264 | 3164 | 0.54 |
| 2.0 | 30* | 75.6 | 1.2 | 43.0 | 7 | 2234 | 3074 | 0.55 |

### headroom × proj_setup (Qexp) — static margin vs dynamic anticipation

2-D: static per-replica margin (headroom) against anticipation (assumed boot lead; sim always boots in 90s). More anticipation orders earlier, so a lean fleet can hold a fatter fleet's quality — anticipation substituting for margin. `*` proj_setup = true 90s setup.

| headroom | proj_setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 45 | 22.1 | 3.5 | 56.8 | 5 | 1466 | 1916 | 0.84 |
| 1.0 | 60 | 22.1 | 3.5 | 56.8 | 5 | 1466 | 1916 | 0.84 |
| 1.0 | 75 | 20.0 | 1.6 | 50.6 | 4 | 1434 | 1808 | 0.86 |
| 1.0 | 90* | 22.9 | 1.2 | 43.4 | 4 | 1424 | 1784 | 0.86 |
| 1.0 | 105 | 12.0 | 1.2 | 43.0 | 5 | 1409 | 2024 | 0.87 |
| 1.0 | 120 | 19.7 | 1.2 | 35.5 | 5 | 1446 | 2046 | 0.85 |
| 1.0 | 135 | 21.9 | 1.2 | 32.2 | 5 | 1446 | 2030 | 0.85 |
| 1.0 | 180 | 25.2 | 1.2 | 27.9 | 5 | 1463 | 2168 | 0.84 |
| 1.2* | 45 | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |
| 1.2* | 60 | 28.1 | 1.6 | 50.6 | 5 | 1544 | 2084 | 0.79 |
| 1.2* | 75 | 29.8 | 1.2 | 43.4 | 5 | 1568 | 2063 | 0.78 |
| 1.2* | 90* | 34.6 | 1.2 | 43.0 | 5 | 1578 | 2043 | 0.78 |
| 1.2* | 105 | 25.2 | 1.2 | 35.1 | 5 | 1527 | 2157 | 0.80 |
| 1.2* | 120 | 26.8 | 1.2 | 30.7 | 5 | 1543 | 2158 | 0.80 |
| 1.2* | 135 | 28.3 | 1.2 | 25.4 | 5 | 1557 | 2202 | 0.79 |
| 1.2* | 180 | 31.7 | 1.2 | 25.4 | 6 | 1593 | 2313 | 0.77 |
| 1.5 | 45 | 64.5 | 1.6 | 45.7 | 6 | 1876 | 2461 | 0.65 |
| 1.5 | 60 | 58.7 | 1.2 | 43.0 | 6 | 1831 | 2446 | 0.67 |
| 1.5 | 75 | 58.7 | 1.2 | 43.0 | 6 | 1831 | 2446 | 0.67 |
| 1.5 | 90* | 72.8 | 1.2 | 30.7 | 6 | 1870 | 2410 | 0.66 |
| 1.5 | 105 | 78.6 | 1.2 | 25.4 | 6 | 1887 | 2427 | 0.65 |
| 1.5 | 120 | 80.3 | 1.2 | 25.4 | 6 | 1902 | 2457 | 0.65 |
| 1.5 | 135 | 80.3 | 1.2 | 25.4 | 6 | 1902 | 2472 | 0.65 |
| 1.5 | 180 | 66.2 | 1.2 | 19.6 | 6 | 1869 | 2589 | 0.66 |
| 2.0 | 45 | 75.6 | 1.2 | 43.0 | 7 | 2234 | 3074 | 0.55 |
| 2.0 | 60 | 75.6 | 1.2 | 43.0 | 7 | 2234 | 3074 | 0.55 |
| 2.0 | 75 | 78.5 | 1.2 | 30.7 | 7 | 2256 | 3021 | 0.54 |
| 2.0 | 90* | 80.3 | 1.2 | 25.4 | 7 | 2300 | 3050 | 0.53 |
| 2.0 | 105 | 81.9 | 1.2 | 25.4 | 7 | 2309 | 3074 | 0.53 |
| 2.0 | 120 | 83.0 | 1.2 | 19.6 | 7 | 2229 | 3099 | 0.55 |
| 2.0 | 135 | 84.8 | 1.2 | 15.7 | 7 | 2234 | 3119 | 0.55 |
| 2.0 | 180 | 86.4 | 1.2 | 15.2 | 7 | 2251 | 3166 | 0.55 |

### ρ note — why the §2.7 speed-up does not show in these sweeps

All sweeps run at the canonical `RHO = 2` (empty pods decode ~2× faster than packed ones, §2.7). Yet `good%` / `wait_p90` are **identical** to a `RHO = 1` run at every headroom, and only `prov·s` shifts (a slightly shorter drain tail). The reason is structural: the quality bands key on **waiting time** (arrival→service-start), and whenever a backlog exists the router keeps every pod **packed at `usable_C` (k≈1)**, where `rate = service_rate` — exactly the fixed-rate value. The decode speed-up only fires when a pod is *under-full* (k<1), which is precisely when there is no queue and wait≈0 already. So on the wait metric, headroom buys **capacity/slack**, not speed; the §2.7 speed benefit is a *service-latency* effect (visible in `time/work`, not plotted here). This refines the 7(b) framing — see the design doc §2.7 / §8.1(7b).

