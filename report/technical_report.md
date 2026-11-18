# Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation

*A probabilistic assessment of power generation, annual energy production, and energy adequacy. Stanford PAI final project.*

**Analysis site:** Cuxhaven, Germany (53.86° N, 8.69° E; ERA5 grid cell 53.75° N, 8.75° E, elevation 5 m)
**Analysis period:** 2015-01-01 through 2024-12-31, hourly, UTC
**Analysis date:** 2026-11-18
**Author:** Mohammad Ghorbanpour

## Abstract

Wind energy assessment commonly relies on a single deterministic estimate of annual energy production (AEP), which conceals the fact that wind speed is inherently variable and turbine parameters are only approximately known. This study quantifies the full predictive distribution of AEP, capacity factor, and expected power output for a hypothetical 2 MW wind turbine at Cuxhaven, Germany, using ten years (2015–2024) of hourly ERA5 reanalysis data retrieved via the Open-Meteo Historical Weather API. A seasonally stratified 7-day block bootstrap generates 10,000 synthetic annual weather sequences (8,760 hours each), while turbine parameters — power coefficient Cp and system efficiency η — are drawn once per scenario from truncated normal distributions.

The mean AEP is **6,523.2 MWh** (median 6,518.3 MWh; SD 424.9 MWh; 95% MC CI [6,514.9, 6,531.6] MWh). The mean capacity factor is **0.3723** (SD 0.0243; 5th–95th percentile 0.3330–0.4129), corresponding to an expected power output of 0.745 MW. The deterministic baseline (nominal Cp = 0.359, η = 0.94) yields 6,538.3 MWh. No simulated scenario falls below CF = 0.25 (P(CF < 0.25) = 0/10,000; 95% Wilson CI [0.0000, 0.0004]); this is an energy-adequacy indicator, not a mechanical-failure probability, and is not zero underlying risk. Historical weather variability accounts for ~83.1% of AEP variance; turbine-parameter uncertainty ~18.9%; structural model uncertainty is not quantified.

## 1. Introduction

Deterministic energy estimates report a single AEP and hide wind variability and parameter uncertainty. This project quantifies the full predictive distribution with Monte Carlo simulation and reports P(CF < 0.25) as an energy-adequacy indicator. Research question: how do uncertainties in wind speed, air density, and turbine parameters affect power output, AEP, and energy adequacy?

## 2. Data

- Source: Open-Meteo Historical Weather API (ERA5 reanalysis), https://archive-api.open-meteo.com/v1/archive
- Site: Cuxhaven, Germany, 53.86° N, 8.69° E
- Period: 2015-01-01 to 2024-12-31, hourly, UTC
- Model: era5; cell selection: land; returned cell 53.75° N, 8.75° E, elevation 5 m
- Variables: wind_speed_100m, temperature_2m, surface_pressure, wind_direction_100m
- Records: 87,672; completeness 100.0%; 0 duplicates; 0 missing timestamps
- No imputation; raw and processed data stored separately with provenance record
- Limitation: ERA5 is gridded reanalysis, not on-site turbine measurement

## 3. Physical model

- R = 45 m, swept area A = πR² = 6,361.7 m²
- Air density: hydrostatic hub-height estimate from 2 m temperature and surface pressure (g = 9.80665 m/s², R_air = 287.05 J/(kg·K))
- P_raw = ½ρAV³Cpη; P = 0 below cut-in; P = min(P_r, P_raw) between cut-in and cut-out; P = 0 at/above cut-out
- V_ci = 3 m/s, V_rated = 11.5 m/s, V_co = 25 m/s, P_r = 2.0 MW
- Calibration: Cp = 0.359, η = 0.94, ρ = 1.225 kg/m³ → 0.9999 × rated at V_rated (rated power reached by construction); Cp = 60.6% of Betz limit (0.5926)
- Not OEM-certified; constant Cp/η per scenario

## 4. Probabilistic model

- Wind: empirical ERA5 series, block bootstrap resampling
- Air density: derived hourly from temperature and pressure
- Cp ~ TruncatedNormal(0.359, 0.015) on [0.30, 0.50], drawn once/scenario
- η ~ TruncatedNormal(0.94, 0.01) on [0.88, 0.98], drawn once/scenario
- Weibull fit (k = 2.298, c = 8.535 m/s) descriptive only; not used to generate

## 5. Monte Carlo methodology

- Seasonally stratified 168-h block bootstrap within calendar months
- February 29 excluded; every scenario exactly 8,760 h
- 10,000 scenarios, seed 20261118
- Per scenario: resample weather, draw Cp/η, compute hourly power, integrate AEP and CF
- Cp/η shared across all 8,760 hours of a scenario (turbine-level parameters)

## 6. Results

| Statistic | Value |
|---|---|
| Mean AEP | 6,523.2 MWh |
| Median AEP | 6,518.3 MWh |
| SD AEP | 424.9 MWh |
| 5th / 95th percentile AEP | 5,834.5 / 7,234.3 MWh |
| Mean 95% MC CI | [6,514.9, 6,531.6] MWh |
| MC standard error of mean | 4.25 MWh |
| Mean CF | 0.3723 (SD 0.0243) |
| 5th / 95th percentile CF | 0.3330 / 0.4129 |
| Expected power output | 0.745 MW |
| P(CF < 0.25) | 0.0000 (95% Wilson CI [0.0000, 0.0004], 0/10000) |
| Deterministic mean AEP | 6,538.3 MWh |

## 7. Sensitivity analysis

- Spearman (main simulation): mean wind speed +0.875; Cp +0.408; density −0.361; η +0.102
- Sobol (separate independent-input experiment, 12,288 evals): Weibull scale c ST = 0.862; Cp ST = 0.122; η ST = 0.009
- Correlation ≠ causation; Sobol assumes independent inputs, distinct from main sim

## 8. Uncertainty decomposition

- Total AEP variance: 180,558 MWh²
- Weather variability: 149,957 (83.1%)
- Turbine-parameter (Cp, η): 34,043 (18.9%)
- Interaction/residual: -3,442 (-1.9%; approx. zero within MC error)
- MC sampling error: SE of mean AEP = 4.25 MWh
- Structural model uncertainty: NOT quantified (documented limitation)

## 9. Limitations

- 10-year record; ERA5 grid cell (not on-site); simplified power model; air-density approximations; engineering Cp/η assumptions; bootstrap joins break dependence; structural uncertainty unquantified; exploratory (no preregistered hypothesis)

## 10. References

[1] Open-Meteo. Historical Weather API. https://open-meteo.com/en/docs/historical-weather-api
[2] Open-Meteo. Licence (CC BY 4.0). https://open-meteo.com/en/licence
[3] Open-Meteo. Terms of Use. https://open-meteo.com/en/terms
[4] ECMWF/Copernicus Climate Change Service. ERA5 reanalysis (via Open-Meteo; Copernicus Licence terms not independently verified).
[5] Manwell, McGowan, Rogers (2009). Wind Energy Explained, 2nd ed., Wiley.
[6] IEC 61400-1, Wind turbine generator systems.
[7] Kassis et al. (2026). Scientific Agent Skills. arXiv:2609.00065.

## Reproducibility

`python -m src.data_processing`  `python -m src.run_pipeline`  `python -m pytest -q tests`  (seed 20261118; ~18 s for 10,000 scenarios)