# Quantitative uncertainty decomposition

Design: 5,000 scenarios per factorial arm; main simulation 10,000 scenarios; seed 20261118.

| Component | Variance (MWh²) | Share of total |
|---|---:|---:|
| Total AEP variance (main simulation) | 180,558 | 100.0% |
| A. Historical weather variability | 149,957 | 83.1% |
| B. Turbine-parameter uncertainty (Cp, eta), mean over 10 years | 34,043 | 18.9% |
| A×B interaction / residual | -3,442 | -1.9% |

## Monte Carlo sampling error (separate from physical variance)

- MC standard error of the mean AEP: 4.25 MWh
- Variance of the sample mean: 18.1 MWh² (0.0100% of total AEP variance)
- This is the uncertainty of the ESTIMATED MEAN, not a source of AEP variability. It shrinks as 1/sqrt(N); it is not part of the physical variance decomposition.

## Structural model uncertainty

**NOT QUANTIFIED.** No experiment in this analysis varies the physics, data source, or model structure. Comparison against an OEM power curve, hub-height temperature, or measured winds would be required. It remains a documented qualitative limitation only.

## Diagnostics

- MC SE of weather variance estimate: 2,999 MWh²
- MC SE of turbine variance mean: 1,100 MWh²

| Historical year | Fixed-weather AEP mean (MWh) | Turbine-only variance (MWh²) |
|---|---:|---:|
| 2015 | 7,069.2 | 32,024 |
| 2016 | 6,010.4 | 33,817 |
| 2017 | 6,846.1 | 36,182 |
| 2018 | 6,246.6 | 35,134 |
| 2019 | 6,691.6 | 37,325 |
| 2020 | 6,729.0 | 36,955 |
| 2021 | 5,971.5 | 28,516 |
| 2022 | 6,511.3 | 32,496 |
| 2023 | 6,744.0 | 29,150 |
| 2024 | 6,462.2 | 38,829 |

Weather-only variance is estimated from n bootstrap scenarios; turbine-only variance is averaged over 10 fixed historical years because power is nonlinear in wind (V^3 and rated clipping), so the turbine contribution depends on the weather realization.
