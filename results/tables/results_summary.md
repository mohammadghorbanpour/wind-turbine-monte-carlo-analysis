# Monte Carlo results

**Scenarios:** 10,000  
**Seed:** 20261118  

## Annual energy production (MWh)

| Statistic | Value |
|---|---:|
| Mean | 6,523.2 |
| Median | 6,518.3 |
| Standard deviation | 424.9 |
| Variance (MWh^2) | 180,558 |
| 5th percentile | 5,834.5 |
| 25th percentile | 6,237.6 |
| 75th percentile | 6,810.6 |
| 95th percentile | 7,234.3 |
| Mean 95% CI (MC) | [6,514.9, 6,531.6] |

## Capacity factor

| Statistic | Value |
|---|---:|
| Mean | 0.3723 |
| Standard deviation | 0.0243 |
| 5th percentile | 0.3330 |
| 25th percentile | 0.3560 |
| Median | 0.3721 |
| 75th percentile | 0.3887 |
| 95th percentile | 0.4129 |

## Energy adequacy

- **P(CF < 0.25) = 0.0000** (95% Wilson CI [0.0000, 0.0004], 0/10,000)
- Expected power output: 0.745 MW ± 0.049 MW (SD across scenarios)

## Deterministic baseline (nominal Cp=0.359, eta=0.94)

| Statistic | Value |
|---|---:|
| Mean AEP 2015-2024 | 6,538.3 MWh |
| Min / max annual AEP | 5,976.2 / 7,068.6 MWh |
| Mean CF | 0.3729 |
| Years with CF < 0.25 | 0 of 10 |

## Convergence (nested prefixes of one run)

| N | Mean AEP (MWh) | Median AEP (MWh) | SD AEP (MWh) | P(CF<0.25) | MC SE of mean |
|---:|---:|---:|---:|---:|---:|
| 100 | 6,541.8 | 6,516.8 | 452.1 | 0.0000 | 45.2 |
| 1,000 | 6,544.8 | 6,531.0 | 426.1 | 0.0000 | 13.5 |
| 5,000 | 6,526.5 | 6,519.2 | 425.2 | 0.0000 | 6.0 |
| 10,000 | 6,523.2 | 6,518.3 | 424.9 | 0.0000 | 4.2 |
