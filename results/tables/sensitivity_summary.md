# Sensitivity analysis

## Spearman rank correlation (main simulation)

| Input | Output | Spearman rho | p-value |
|---|---|---:|---:|
| cp | aep_mwh | 0.408 | < 1e-12 |
| cp | capacity_factor | 0.408 | < 1e-12 |
| eta | aep_mwh | 0.102 | < 1e-12 |
| eta | capacity_factor | 0.102 | < 1e-12 |
| scenario_mean_wind_speed_mps | aep_mwh | 0.875 | < 1e-12 |
| scenario_mean_wind_speed_mps | capacity_factor | 0.875 | < 1e-12 |
| scenario_mean_air_density_kg_m3 | aep_mwh | -0.361 | < 1e-12 |
| scenario_mean_air_density_kg_m3 | capacity_factor | -0.361 | < 1e-12 |

## Sobol indices (independent-input experiment)

| Parameter | S1 | ST | ST 95% CI |
|---|---:|---:|---:|
| weibull_k | -0.000 | 0.006 | +/- 0.001 |
| weibull_c | 0.855 | 0.862 | +/- 0.063 |
| cp | 0.121 | 0.122 | +/- 0.011 |
| eta | 0.009 | 0.009 | +/- 0.001 |
| rho_factor | 0.007 | 0.008 | +/- 0.001 |

## One-at-a-time swing (supporting view)

| Parameter | AEP at low | AEP at high | Swing (MWh) |
|---|---:|---:|---:|
| weibull_c | 4,249 | 8,444 | 4,195 |
| cp | 5,739 | 7,366 | 1,627 |
| eta | 6,187 | 6,618 | 431 |
| rho_factor | 6,246 | 6,647 | 401 |
| weibull_k | 6,434 | 6,425 | 9 |
