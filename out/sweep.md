# Parameter sweeps — trends & calibration

**Demand shape:** every knob sweep below runs on the **bump** reference shape (the smooth triangular calibration demand) — only the knob varies, the demand does not. The one exception is the **Cap sweep** at the very end, which is run per sustained shape (trapezoid / step-up / step-down) and labels each explicitly.

Metrics per run: `good%` (≤2s, pinned), `failed%` (>60s, pinned), `wait_p90` (s), `rep_max` (peak fleet), `rep·s` (usable replica-seconds), `prov·s` (billed incl. boot/drain), `util` (delivered ÷ usable capacity paid for). `*` = each section's own canonical baseline (setup=90; drain=20 for BOTH Q sizers — a standing rule so they compare on a level field; headroom=1.3; sat_frac=0.85).

### setup-lag — setup (boot lag) sweep

Clairvoyant demand-tracking commands landing `setup` s late. Isolates boot lag alone (no backlog term). Context: setup=90 is the real boot time; the point is that it is where quality collapses.

| setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| 30 | 99.5 | 0.0 | 0.0 | 5 | 1586 | 1736 | 0.65 |
| 60 | 87.1 | 0.0 | 4.7 | 5 | 1477 | 1777 | 0.70 |
| 90* | 31.0 | 0.5 | 34.7 | 4 | 1306 | 1741 | 0.79 |

### queue-aware — drain_time aggression curve (setup 60 vs 90)

Reactive backlog-drain sizer, NO upper cap. `drain_time` is the deadline to clear the current queue; shorter → size for more replicas. But it has no dead-time compensation, so replicas ordered still boot `setup` s late — watch whether aggression buys good% or just prov·s (boot-lag waste).

| setup | drain | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 60 | 3 | 73.6 | 0.2 | 4.1 | 5 | 1482 | 1872 | 0.69 |
| 60 | 5 | 65.8 | 0.2 | 6.6 | 5 | 1502 | 1832 | 0.68 |
| 60 | 8 | 65.8 | 0.2 | 6.6 | 5 | 1502 | 1817 | 0.68 |
| 60 | 10 | 65.8 | 0.2 | 6.6 | 5 | 1502 | 1802 | 0.68 |
| 60 | 15 | 48.4 | 0.2 | 12.7 | 5 | 1487 | 1787 | 0.69 |
| 60 | 20* | 48.4 | 0.2 | 12.7 | 5 | 1487 | 1787 | 0.69 |
| 60 | 30 | 48.4 | 0.2 | 12.7 | 5 | 1487 | 1787 | 0.69 |
| 90* | 3 | 36.1 | 1.2 | 21.0 | 6 | 1488 | 3108 | 0.69 |
| 90* | 5 | 71.9 | 1.2 | 33.7 | 4 | 1458 | 2433 | 0.70 |
| 90* | 8 | 64.8 | 1.2 | 33.7 | 4 | 1406 | 2142 | 0.73 |
| 90* | 10 | 69.1 | 1.2 | 35.4 | 4 | 1447 | 2092 | 0.71 |
| 90* | 15 | 64.2 | 1.2 | 42.7 | 4 | 1435 | 2035 | 0.72 |
| 90* | 20* | 33.6 | 1.2 | 42.7 | 4 | 1373 | 1928 | 0.75 |
| 90* | 30 | 31.0 | 1.2 | 42.7 | 4 | 1370 | 1865 | 0.75 |

### qexp — proj_setup dial (sim boots in 90s regardless)

Anticipatory Qexp sizing to the projected backlog peak. `proj_setup` is the boot lead the projection ASSUMES; the sim always applies setup=90. Under-predict (<90) → anticipates less, drifts toward reactive; over-predict (>90) → orders earlier, trades a little cost for tail latency. Stable and self-correcting across the range. `*` = true setup.

| proj_setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|
| 45 | 33.6 | 1.2 | 42.7 | 4 | 1373 | 1928 | 0.75 |
| 60 | 50.3 | 1.2 | 35.4 | 4 | 1400 | 1910 | 0.73 |
| 75 | 50.3 | 1.2 | 35.4 | 4 | 1400 | 1910 | 0.73 |
| 90* | 69.8 | 1.2 | 27.8 | 4 | 1420 | 1885 | 0.72 |
| 105 | 36.3 | 1.2 | 21.0 | 5 | 1447 | 2032 | 0.71 |
| 120 | 38.3 | 1.2 | 21.0 | 5 | 1461 | 2091 | 0.70 |
| 135 | 38.3 | 1.2 | 21.0 | 5 | 1461 | 2106 | 0.70 |
| 180 | 48.7 | 1.2 | 15.2 | 5 | 1502 | 2267 | 0.68 |

### headroom — static per-replica margin (queue-aware vs Qexp)

Static margin dial (§2.6) at the real 90s boot (both Q sizers at the shared drain=20). More headroom = more replicas = fewer requests per pod = shorter queue = less wait, monotonically, for more prov·s. This is headroom's CAPACITY role; its §2.7 speed role does not appear on the wait metric (see ρ note below). `*` = canonical baseline (1.3). The pick is the steepest part of the curve — max marginal quality per unit margin.

| sizer | headroom | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| qaware | 1.0 | 21.7 | 1.2 | 42.7 | 4 | 1254 | 1659 | 0.82 |
| qaware | 1.1 | 23.6 | 1.2 | 42.7 | 4 | 1285 | 1750 | 0.80 |
| qaware | 1.2 | 31.0 | 1.2 | 42.7 | 4 | 1356 | 1821 | 0.76 |
| qaware | 1.3* | 33.6 | 1.2 | 42.7 | 4 | 1373 | 1928 | 0.75 |
| qaware | 1.5 | 73.0 | 1.2 | 42.7 | 5 | 1598 | 2184 | 0.64 |
| qaware | 1.75 | 77.7 | 1.2 | 35.4 | 6 | 1792 | 2436 | 0.57 |
| qaware | 2.0 | 80.6 | 1.2 | 33.7 | 6 | 1982 | 2716 | 0.52 |
| qexp | 1.0 | 20.5 | 1.2 | 38.6 | 5 | 1280 | 1956 | 0.80 |
| qexp | 1.1 | 42.2 | 1.2 | 35.4 | 4 | 1318 | 1768 | 0.78 |
| qexp | 1.2 | 34.3 | 1.2 | 27.8 | 5 | 1421 | 2021 | 0.72 |
| qexp | 1.3* | 69.8 | 1.2 | 27.8 | 4 | 1420 | 1885 | 0.72 |
| qexp | 1.5 | 81.8 | 1.2 | 21.0 | 5 | 1595 | 2120 | 0.64 |
| qexp | 1.75 | 83.4 | 1.2 | 21.0 | 6 | 1741 | 2416 | 0.59 |
| qexp | 2.0 | 84.8 | 1.2 | 21.0 | 6 | 2020 | 2725 | 0.51 |

### headroom × drain_time (queue-aware) — static margin vs dynamic aggression

2-D: static per-replica margin (headroom) against the reactive backlog aggression lever (shorter drain_time = order more to clear faster). Where a leaner (low-headroom) line reaches a fatter line's good%, aggression has substituted for static margin — at its own boot-lag cost. setup=90.

| headroom | drain | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 3 | 42.5 | 1.2 | 29.9 | 8 | 1421 | 3806 | 0.72 |
| 1.0 | 5 | 26.9 | 1.2 | 39.8 | 6 | 1352 | 2972 | 0.76 |
| 1.0 | 8 | 26.5 | 1.2 | 42.7 | 6 | 1332 | 2547 | 0.77 |
| 1.0 | 10 | 26.5 | 1.2 | 42.7 | 6 | 1332 | 2352 | 0.77 |
| 1.0 | 15 | 21.7 | 1.2 | 42.7 | 4 | 1254 | 1689 | 0.82 |
| 1.0 | 20* | 21.7 | 1.2 | 42.7 | 4 | 1254 | 1659 | 0.82 |
| 1.0 | 30 | 13.4 | 1.2 | 49.7 | 4 | 1194 | 1629 | 0.86 |
| 1.3* | 3 | 36.1 | 1.2 | 21.0 | 6 | 1488 | 3108 | 0.69 |
| 1.3* | 5 | 71.9 | 1.2 | 33.7 | 4 | 1458 | 2433 | 0.70 |
| 1.3* | 8 | 64.8 | 1.2 | 33.7 | 4 | 1406 | 2142 | 0.73 |
| 1.3* | 10 | 69.1 | 1.2 | 35.4 | 4 | 1447 | 2092 | 0.71 |
| 1.3* | 15 | 64.2 | 1.2 | 42.7 | 4 | 1435 | 2035 | 0.72 |
| 1.3* | 20* | 33.6 | 1.2 | 42.7 | 4 | 1373 | 1928 | 0.75 |
| 1.3* | 30 | 31.0 | 1.2 | 42.7 | 4 | 1370 | 1865 | 0.75 |
| 1.5 | 3 | 84.6 | 1.2 | 18.7 | 5 | 1618 | 2908 | 0.64 |
| 1.5 | 5 | 82.1 | 1.2 | 26.2 | 5 | 1632 | 2636 | 0.63 |
| 1.5 | 8 | 73.5 | 1.2 | 33.7 | 5 | 1579 | 2389 | 0.65 |
| 1.5 | 10 | 73.5 | 1.2 | 33.7 | 5 | 1579 | 2299 | 0.65 |
| 1.5 | 15 | 59.0 | 1.2 | 35.4 | 5 | 1542 | 2172 | 0.67 |
| 1.5 | 20* | 73.0 | 1.2 | 42.7 | 5 | 1598 | 2184 | 0.64 |
| 1.5 | 30 | 68.2 | 1.2 | 42.7 | 5 | 1620 | 2100 | 0.63 |
| 2.0 | 3 | 87.0 | 1.2 | 18.7 | 6 | 2074 | 3784 | 0.50 |
| 2.0 | 5 | 84.8 | 1.2 | 21.0 | 6 | 2020 | 3250 | 0.51 |
| 2.0 | 8 | 82.2 | 1.2 | 33.7 | 6 | 1976 | 3042 | 0.52 |
| 2.0 | 10 | 82.2 | 1.2 | 33.7 | 6 | 1976 | 2922 | 0.52 |
| 2.0 | 15 | 80.6 | 1.2 | 33.7 | 6 | 1982 | 2776 | 0.52 |
| 2.0 | 20* | 80.6 | 1.2 | 33.7 | 6 | 1982 | 2716 | 0.52 |
| 2.0 | 30 | 77.7 | 1.2 | 35.4 | 6 | 1942 | 2617 | 0.53 |

### headroom × proj_setup (Qexp) — static margin vs dynamic anticipation

2-D: static per-replica margin (headroom) against anticipation (assumed boot lead; sim always boots in 90s). More anticipation orders earlier, so a lean fleet can hold a fatter fleet's quality — anticipation substituting for margin. `*` proj_setup = true 90s setup.

| headroom | proj_setup | good% | failed% | wait_p90 | rep_max | rep·s | prov·s | util |
|---|---|---|---|---|---|---|---|---|
| 1.0 | 45 | 21.7 | 1.2 | 42.7 | 4 | 1254 | 1659 | 0.82 |
| 1.0 | 60 | 21.7 | 1.2 | 42.7 | 4 | 1254 | 1659 | 0.82 |
| 1.0 | 75 | 22.6 | 1.2 | 38.4 | 5 | 1284 | 1914 | 0.80 |
| 1.0 | 90* | 20.5 | 1.2 | 38.6 | 5 | 1280 | 1956 | 0.80 |
| 1.0 | 105 | 18.6 | 1.2 | 41.6 | 5 | 1270 | 1960 | 0.81 |
| 1.0 | 120 | 22.1 | 1.2 | 41.6 | 6 | 1290 | 2024 | 0.80 |
| 1.0 | 135 | 32.8 | 1.2 | 33.0 | 5 | 1325 | 2075 | 0.78 |
| 1.0 | 180 | 32.8 | 1.2 | 33.0 | 5 | 1325 | 2240 | 0.78 |
| 1.3* | 45 | 33.6 | 1.2 | 42.7 | 4 | 1373 | 1928 | 0.75 |
| 1.3* | 60 | 50.3 | 1.2 | 35.4 | 4 | 1400 | 1910 | 0.73 |
| 1.3* | 75 | 50.3 | 1.2 | 35.4 | 4 | 1400 | 1910 | 0.73 |
| 1.3* | 90* | 69.8 | 1.2 | 27.8 | 4 | 1420 | 1885 | 0.72 |
| 1.3* | 105 | 36.3 | 1.2 | 21.0 | 5 | 1447 | 2032 | 0.71 |
| 1.3* | 120 | 38.3 | 1.2 | 21.0 | 5 | 1461 | 2091 | 0.70 |
| 1.3* | 135 | 38.3 | 1.2 | 21.0 | 5 | 1461 | 2106 | 0.70 |
| 1.3* | 180 | 48.7 | 1.2 | 15.2 | 5 | 1502 | 2267 | 0.68 |
| 1.5 | 45 | 73.0 | 1.2 | 42.7 | 5 | 1598 | 2184 | 0.64 |
| 1.5 | 60 | 59.0 | 1.2 | 35.4 | 5 | 1542 | 2097 | 0.67 |
| 1.5 | 75 | 78.5 | 1.2 | 27.8 | 5 | 1594 | 2104 | 0.64 |
| 1.5 | 90* | 81.8 | 1.2 | 21.0 | 5 | 1595 | 2120 | 0.64 |
| 1.5 | 105 | 81.8 | 1.2 | 21.0 | 5 | 1595 | 2150 | 0.64 |
| 1.5 | 120 | 81.8 | 1.2 | 21.0 | 5 | 1595 | 2165 | 0.64 |
| 1.5 | 135 | 85.5 | 1.2 | 10.8 | 5 | 1603 | 2188 | 0.64 |
| 1.5 | 180 | 85.5 | 1.2 | 10.8 | 5 | 1603 | 2278 | 0.64 |
| 2.0 | 45 | 80.6 | 1.2 | 33.7 | 6 | 1982 | 2716 | 0.52 |
| 2.0 | 60 | 82.1 | 1.2 | 27.8 | 6 | 1980 | 2670 | 0.52 |
| 2.0 | 75 | 83.4 | 1.2 | 21.0 | 6 | 2007 | 2697 | 0.51 |
| 2.0 | 90* | 84.8 | 1.2 | 21.0 | 6 | 2020 | 2725 | 0.51 |
| 2.0 | 105 | 87.1 | 1.2 | 10.8 | 6 | 1960 | 2740 | 0.52 |
| 2.0 | 120 | 87.1 | 1.2 | 10.8 | 6 | 1960 | 2770 | 0.52 |
| 2.0 | 135 | 87.1 | 1.2 | 10.8 | 6 | 1960 | 2800 | 0.52 |
| 2.0 | 180 | 89.1 | 1.2 | 6.1 | 6 | 1996 | 2942 | 0.51 |

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
| 5 | 2331 | 2344 (1.0×) | 2393 (1.0×) | 2775 (1.2×) | 3001 (1.3×) |
| 8 | 2331 | 2624 (1.1×) | 2692 (1.2×) | 4305 (1.8×) | 4802 (2.1×) |
| 10* | 2331 | 2624 (1.1×) | 2737 (1.2×) | 5325 (2.3×) | 6002 (2.6×) |
| 12 | 2331 | 2624 (1.1×) | 2737 (1.2×) | 6345 (2.7×) | 7203 (3.1×) |
| 15 | 2331 | 2624 (1.1×) | 2737 (1.2×) | 7875 (3.4×) | 9004 (3.9×) |
| 20 | 2331 | 2624 (1.1×) | 2737 (1.2×) | 10425 (4.5×) | 12005 (5.2×) |
| 30 | 2331 | 2624 (1.1×) | 2737 (1.2×) | 15435 (6.6×) | 18008 (7.7×) |

### cap sweep (trapezoid) — quality: served ≤15s %

Share served within 15s (the "works" bar). More ceiling buys the Q sizers headroom to clear the backlog; past their peak it stops mattering.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 100.0 | 79.3 | 85.3 | 87.5 | 100.0 |
| 8 | 100.0 | 79.3 | 85.3 | 61.7 | 100.0 |
| 10* | 100.0 | 79.3 | 85.3 | 87.5 | 100.0 |
| 12 | 100.0 | 79.3 | 85.3 | 87.5 | 100.0 |
| 15 | 100.0 | 79.3 | 85.3 | 87.5 | 100.0 |
| 20 | 100.0 | 79.3 | 85.3 | 87.5 | 100.0 |
| 30 | 100.0 | 79.3 | 85.3 | 87.5 | 100.0 |

### cap sweep (stepup) — cost: provisioned·seconds (×ideal)

Billed fleet-seconds per policy as the cap rises; `(N×)` = multiple of `ideal` at the same cap. `hpa-queue`/`static` track the cap; the Q sizers plateau once the cap clears their natural peak.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 2257 | 2166 (1.0×) | 2226 (1.0×) | 2109 (0.9×) | 3001 (1.3×) |
| 8 | 2257 | 2492 (1.1×) | 2622 (1.2×) | 3195 (1.4×) | 4802 (2.1×) |
| 10* | 2257 | 2568 (1.1×) | 2757 (1.2×) | 3201 (1.4×) | 6002 (2.7×) |
| 12 | 2257 | 2568 (1.1×) | 2832 (1.3×) | 4565 (2.0×) | 7203 (3.2×) |
| 15 | 2257 | 2568 (1.1×) | 2832 (1.3×) | 5505 (2.4×) | 9004 (4.0×) |
| 20 | 2257 | 2568 (1.1×) | 2832 (1.3×) | 7155 (3.2×) | 12005 (5.3×) |
| 30 | 2257 | 2568 (1.1×) | 2832 (1.3×) | 10455 (4.6×) | 18008 (8.0×) |

### cap sweep (stepup) — quality: served ≤15s %

Share served within 15s (the "works" bar). More ceiling buys the Q sizers headroom to clear the backlog; past their peak it stops mattering.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 100.0 | 72.2 | 79.7 | 79.7 | 100.0 |
| 8 | 100.0 | 75.2 | 80.7 | 83.9 | 100.0 |
| 10* | 100.0 | 75.2 | 80.7 | 84.0 | 100.0 |
| 12 | 100.0 | 75.2 | 80.7 | 65.5 | 100.0 |
| 15 | 100.0 | 75.2 | 80.7 | 84.0 | 100.0 |
| 20 | 100.0 | 75.2 | 80.7 | 84.0 | 100.0 |
| 30 | 100.0 | 75.2 | 80.7 | 84.0 | 100.0 |

### cap sweep (stepdown) — cost: provisioned·seconds (×ideal)

Billed fleet-seconds per policy as the cap rises; `(N×)` = multiple of `ideal` at the same cap. `hpa-queue`/`static` track the cap; the Q sizers plateau once the cap clears their natural peak.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 3001 (1.5×) |
| 8 | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 4802 (2.4×) |
| 10* | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 6002 (3.0×) |
| 12 | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 7203 (3.6×) |
| 15 | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 9004 (4.5×) |
| 20 | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 12005 (5.9×) |
| 30 | 2018 | 2087 (1.0×) | 2087 (1.0×) | 3000 (1.5×) | 18007 (8.9×) |

### cap sweep (stepdown) — quality: served ≤15s %

Share served within 15s (the "works" bar). More ceiling buys the Q sizers headroom to clear the backlog; past their peak it stops mattering.

| cap | ideal | queue-aware | qexp | hpa-queue | static |
|---|---|---|---|---|---|
| 5 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 8 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 10* | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 12 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 15 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 20 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |
| 30 | 100.0 | 100.0 | 100.0 | 100.0 | 100.0 |

**bump / spike are cap-inert for the Q sizers** and so are omitted from the per-shape switcher: their offered load needs only ≈4–6 replicas at the peak, well under every swept cap, so `queue-aware`/`qexp`/`ideal` never touch the ceiling there (only `hpa-queue`/`static`, which pin to the cap on any shape, would still scale with it).

