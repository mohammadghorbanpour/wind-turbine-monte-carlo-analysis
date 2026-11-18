# Bootstrap preservation check

Simulated years: 500; block length 168 h; seed 20261125.

Discontinuities per simulated year: 47 within-month block joins + 11 month boundaries = 58 total.

## Monthly mean and SD (m/s)

| Month | Hist mean | Sim mean | Δ mean | Hist SD | Sim SD | Δ SD | KS stat | KS p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| January | 9.246 | 9.021 | -0.226 | 4.017 | 3.982 | -0.036 | 0.0259 | 0.000114 |
| February | 9.086 | 9.201 | +0.115 | 4.001 | 3.999 | -0.003 | 0.0161 | 0.0642 |
| March | 7.910 | 7.978 | +0.068 | 3.467 | 3.438 | -0.029 | 0.0147 | 0.0844 |
| April | 7.282 | 7.456 | +0.174 | 3.012 | 3.045 | +0.033 | 0.0284 | 2.18e-05 |
| May | 6.827 | 6.835 | +0.008 | 2.924 | 2.907 | -0.017 | 0.0090 | 0.597 |
| June | 6.140 | 6.169 | +0.028 | 2.686 | 2.707 | +0.021 | 0.0063 | 0.939 |
| July | 6.495 | 6.365 | -0.130 | 2.994 | 2.906 | -0.089 | 0.0222 | 0.00147 |
| August | 6.117 | 6.216 | +0.099 | 2.701 | 2.778 | +0.077 | 0.0178 | 0.0196 |
| September | 6.713 | 6.731 | +0.018 | 3.143 | 3.184 | +0.041 | 0.0062 | 0.945 |
| October | 7.932 | 7.888 | -0.044 | 3.196 | 3.169 | -0.027 | 0.0073 | 0.826 |
| November | 8.213 | 8.279 | +0.067 | 3.475 | 3.442 | -0.033 | 0.0114 | 0.313 |
| December | 8.909 | 8.808 | -0.101 | 3.701 | 3.655 | -0.046 | 0.0165 | 0.0369 |

## Monthly wind-speed quantiles (m/s): historical vs simulated difference

| Month | Δ p05 | Δ p25 | Δ median | Δ p75 | Δ p95 |
|---|---:|---:|---:|---:|---:|
| January | -0.060 | -0.230 | -0.210 | -0.260 | -0.210 |
| February | +0.110 | +0.180 | +0.095 | +0.078 | +0.080 |
| March | +0.110 | +0.080 | +0.130 | +0.060 | +0.000 |
| April | +0.110 | +0.140 | +0.190 | +0.250 | +0.240 |
| May | -0.010 | +0.070 | +0.010 | -0.022 | +0.010 |
| June | +0.020 | -0.010 | +0.045 | +0.030 | +0.140 |
| July | +0.000 | -0.040 | -0.150 | -0.230 | -0.280 |
| August | +0.000 | +0.022 | +0.060 | +0.160 | +0.240 |
| September | -0.030 | -0.010 | +0.020 | +0.030 | +0.030 |
| October | -0.020 | -0.010 | -0.020 | -0.072 | -0.050 |
| November | +0.190 | +0.090 | +0.015 | +0.030 | +0.010 |
| December | +0.060 | -0.100 | -0.130 | -0.180 | -0.151 |

## Seasonal distributions

| Season | Hist mean | Sim mean | Δ mean | Hist SD | Sim SD | Δ SD | KS stat | KS p |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| DJF | 9.080 | 9.003 | -0.077 | 3.908 | 3.881 | -0.027 | 0.0118 | 0.00531 |
| MAM | 7.340 | 7.423 | +0.082 | 3.176 | 3.174 | -0.002 | 0.0136 | 0.000639 |
| JJA | 6.252 | 6.251 | -0.001 | 2.804 | 2.800 | -0.004 | 0.0017 | 1 |
| SON | 7.623 | 7.636 | +0.013 | 3.337 | 3.331 | -0.006 | 0.0049 | 0.686 |

## Seasonal quantiles (m/s): historical vs simulated difference

| Season | Δ p05 | Δ p25 | Δ median | Δ p75 | Δ p95 |
|---|---:|---:|---:|---:|---:|
| DJF | +0.030 | -0.070 | -0.080 | -0.133 | -0.070 |
| MAM | +0.040 | +0.090 | +0.100 | +0.080 | +0.100 |
| JJA | +0.000 | +0.000 | -0.010 | -0.002 | -0.020 |
| SON | +0.010 | +0.040 | +0.020 | -0.002 | +0.020 |

The bootstrap resamples contiguous 7-day blocks from the historical series within each calendar month, so each month's marginal distribution is preserved up to Monte Carlo resampling error. Differences in means, SDs and quantiles should be small. KS p-values can be tiny with very large simulated n even for negligible differences, so effect sizes (mean/SD/quantile differences) are the primary criterion. Block joins break temporal dependence at a limited number of points per year and across month boundaries; within-block chronology is preserved.
