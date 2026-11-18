# Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation

Stanford Probability for AI (PAI) Final Project — December 2026

## Research motivation

How do uncertainties in wind speed, air density, and turbine operating parameters
affect the power output, annual energy production (AEP), and energy adequacy of a
2 MW wind turbine? A deterministic calculation returns a single AEP and hides wind
variability and parameter uncertainty. This project quantifies the full predictive
distribution with a Monte Carlo simulation driven by ten years of hourly ERA5
reanalysis data.

## Data source

- **Provider:** Open-Meteo Historical Weather API (backed by ERA5 reanalysis)
- **Endpoint:** https://archive-api.open-meteo.com/v1/archive
- **Documentation:** https://open-meteo.com/en/docs/historical-weather-api
- **Underlying model:** ERA5 (ECMWF/Copernicus Climate Change Service)
- **Site:** Cuxhaven, Germany (latitude 53.86, longitude 8.69); returned ERA5 grid cell
  (53.75, 8.75), elevation 5 m
- **Period:** 2015-01-01 through 2024-12-31
- **Resolution:** Hourly, UTC
- **Variables:** wind_speed_100m (m/s), temperature_2m (°C), surface_pressure (hPa),
  wind_direction_100m (°)
- **Cell selection:** land
- **Retrieved records:** 87,672 (100.0% completeness; 0 duplicates; 0 missing timestamps)
- **Retrieved at:** 2026-11-18T03:44:39 UTC
- **Limitation:** ERA5 is gridded reanalysis, not an on-site turbine measurement.
  The series is a regional estimate.

See `SOURCES.md` for full provenance, licensing, and attribution.

## Installation

```bash
# Create and activate a virtual environment (Python 3.12+ recommended)
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Execution instructions

All research computation is in `src/`; the React-style app restriction from the
course starter bundle does not apply here (no React app in this repository).

```bash
# 1. (Optional) Re-download the raw ERA5 data
python -m src.data_loader --force

# 2. Process the raw data and run the data-quality audit
python -m src.data_processing

# 3. Run the full pipeline: model, simulation, sensitivity, figures, report
python -m src.run_pipeline

# 4. Run the automated test suite
python -m pytest -q tests

# Quick smoke run (1,000 scenarios)
python -m src.run_pipeline --quick
```

The full 10,000-scenario run takes roughly 18 seconds on this hardware and writes
results to `results/`, figures to `results/figures/`, and the report to
`report/`.

## Model equations

All quantities in SI units internally.

**Swept rotor area:**
```
A = pi * R^2          (R = 45 m  ->  A = 6,361.73 m^2)
```

**Air density at hub height (hydrostatic approximation):**
```
T_K   = T_C + 273.15
p_s   = 100 * p_hPa
p_h   = p_s * exp(-g * H_h / (R_air * T_K))
rho   = p_h / (R_air * T_K)
```
with g = 9.80665 m/s^2, R_air = 287.05 J/(kg*K), H_h = 100 m.

Note: 2 m temperature is used as a hub-height temperature proxy and surface pressure
is hydrostatically extrapolated; both are approximations.

**Electrical power:**
```
P_raw = 0.5 * rho * A * V^3 * Cp * eta
P     = 0                          if V < V_ci
P     = min(P_r, P_raw)            if V_ci <= V < V_co
P     = 0                          if V >= V_co
```
with V_ci = 3 m/s, V_rated = 11.5 m/s, V_co = 25 m/s, P_r = 2 MW.

**Annual energy and capacity factor:**
```
AEP = sum_t P_t * Delta t          (Delta t = 1 h, result in MWh)
CF  = AEP / (P_r * 8760)
```

## Simulation methodology

- Primary wind source: empirical distribution of the 87,672-hour ERA5 series.
- **Seasonally stratified block bootstrap:** the series is split by calendar month;
  within each month, contiguous 168-hour (7-day) blocks that lie inside one year
  are resampled with replacement to build a synthetic 8,760-hour year. February 29
  is excluded so every scenario has exactly 8,760 hours. Within-block chronology is
  preserved (short-term dependence survives); dependence is broken at block joins
  and across months — a documented limitation.
- Wind speeds are NOT replaced by independent Weibull draws in the main simulation.
- A Weibull fit (k = 2.298, c = 8.535 m/s) is reported for description only.
- Air density is derived hour by hour from historical temperature and pressure.
- Cp ~ TruncatedNormal(mu=0.359, sigma=0.015), bounded [0.30, 0.50].
- eta ~ TruncatedNormal(mu=0.94, sigma=0.01), bounded [0.88, 0.98].
- Cp and eta are drawn ONCE per annual scenario (turbine-level design parameters).
- 10,000 scenarios, seed 20261118.
- Cp = 0.359 is an initial calibration assumption (reproduces rated power at 11.5
  m/s by construction), not an empirical validation.

## Results (10,000 scenarios, seed 20261118)

| Statistic | Value |
|---|---|
| Mean AEP | 6,523.2 MWh |
| Median AEP | 6,518.3 MWh |
| SD of AEP | 424.9 MWh |
| AEP 5th / 95th percentile | 5,834.5 / 7,234.3 MWh |
| Mean capacity factor | 0.3723 (SD 0.0243) |
| CF 5th / 95th percentile | 0.3330 / 0.4129 |
| Expected power output | 0.745 MW |
| P(CF < 0.25) | 0.0000 (0/10,000; 95% Wilson CI [0.0000, 0.0004]) |
| Deterministic mean AEP (2015-2024) | 6,538.3 MWh |

P(CF < 0.25) is an energy-adequacy indicator, not a mechanical-failure probability.
Zero observed events in 10,000 scenarios is not zero underlying risk.

## Sensitivity analysis

- Spearman (main simulation): scenario mean wind speed is dominant (rho = +0.875
  with AEP), followed by Cp (+0.408), air density (-0.361), eta (+0.102).
- Sobol (separate independent-input experiment): weibull_c dominates (S1 = 0.855,
  ST = 0.862), then Cp (S1 = 0.121, ST = 0.122).

## Limitations

- Reported intervals are Monte Carlo sampling uncertainty; structural model error
  is not quantified numerically.
- Only 10 years of reanalysis: interannual variability sampled from a short record.
- Simplified power curve (constant Cp, eta) — not OEM-certified.
- 2 m temperature / surface-pressure approximations for hub-height density.
- Block joins break cross-block dependence.

## Reproducibility

- Random seed 20261118 is fixed throughout.
- Exact request URLs and per-year API metadata are in `data/raw/*.provenance.json`.
- Software versions are recorded in `results/tables/analysis_manifest.json`.
- Re-run: `python -m src.run_pipeline` then `python -m pytest -q tests`.

## AI usage disclosure

An AI coding agent (OpenCode) generated and executed the data-acquisition,
simulation, statistics, sensitivity, figure, and report code, and drafted the
writeup. The human researcher selected the research question, approved the turbine
specifications and probability model, and is responsible for verifying all
assumptions, numerical results, and claims. See `AI_USAGE.md` and `AI-NOTES.md`.

## Prior hypothesis

No preregistered prior hypothesis was recorded before the simulation results were
inspected. The analysis is exploratory; any hypothesis formulated after seeing the
results is post hoc.
