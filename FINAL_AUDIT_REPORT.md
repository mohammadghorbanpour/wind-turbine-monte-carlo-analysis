# Final Audit Report — Wind Turbine Monte Carlo Uncertainty Project

**Project:** Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation
**Course:** Stanford Probability for AI (PAI) Final Project
**Date:** 2026-11-18
**Status:** Complete — all deliverables produced, executed, and validated

---

## 1. Files Created or Modified

### Created in this session (Phase 8 deliverables)
| File | Purpose |
|------|---------|
| `requirements.txt` | Pinned Python dependencies (numpy, pandas, scipy, matplotlib, requests, pytest, SALib, pillow, pypdf) |
| `README.md` | Installation, execution, model equations, methodology, results, limitations, reproducibility, AI disclosure |
| `SOURCES.md` | Dataset provenance, licensing, attribution (Open-Meteo/ERA5, CC BY 4.0), secondary references |
| `AI_USAGE.md` | AI usage disclosure — tools, tasks, human decisions, verification statement |
| `AI-NOTES.md` | AI and human contribution log by phase, prior hypothesis status, test-set strategy, limitations |
| `video/VIDEO-SCRIPT.md` | 60-second video script with scene directions, narration, key results |

### Pre-existing project files (verified, not modified in this session)
| File | Purpose |
|------|---------|
| `src/config.py` | Physical constants, turbine assumptions, seeds, paths |
| `src/data_loader.py` | ERA5 data acquisition from Open-Meteo API |
| `src/data_processing.py` | Data loading, derivation, quality audit |
| `src/turbine_model.py` | Swept area, density, power curve, calibration, Weibull |
| `src/simulation.py` | Block bootstrap, Monte Carlo, baseline, convergence |
| `src/sensitivity.py` | Spearman + Sobol sensitivity analysis |
| `src/statistical_analysis.py` | AEP/CF summaries, Wilson CI, MC standard error |
| `src/visualization.py` | 12 figures + thumbnail |
| `src/report.py` | 2-page PDF + Markdown report builder |
| `src/run_pipeline.py` | 8-stage orchestration pipeline |
| `tests/test_turbine_model.py` | Physical model unit tests |
| `tests/test_simulation.py` | Simulation pipeline tests |
| `data/raw/openmeteo_era5_cuxhaven_2015_2024.csv` | Raw ERA5 data (87,672 hourly records) |
| `data/raw/...provenance.json` | Request URLs, retrieval timestamp, per-year metadata |
| `data/processed/...processed.csv` | Processed analysis-ready dataset |
| `data/processed/data_quality_report.json/.md` | QC audit (100% completeness, 0 missing, 0 duplicates) |
| `results/figures/fig01–fig12.png` | 12 publication-quality figures |
| `results/figures/thumbnail.png` | 1280×720 16:9 thumbnail |
| `results/tables/*` | Scenario results, convergence, sensitivity, summaries, manifest |
| `report/final_report.pdf` | 2-page writeup PDF |
| `report/final_report.md` | Markdown version of writeup |

### Files edited in this session
- `src/report.py`: Added page-preview support, page-overflow warning, condensed page-2 text, reduced page-2 figure width (TEXT_W → 3.0 in) to eliminate overflow
- `src/visualization.py`: Added text-bounds clipping audit; widened margins on fig01, fig02, fig03, fig04, fig05, fig06, fig07, fig08, fig09, fig10, fig11, fig12 to eliminate tick-label clipping
- `src/turbine_model.py`: Generalized `_check_cp_eta` to accept arrays (for vectorized simulation)
- `src/sensitivity.py`: Fixed SALib analyze call signature (`num_resamples`, `conf_level`, `seed`)
- `src/run_pipeline.py`: Robust pytest output parsing
- `tests/test_turbine_model.py`: Fixed air-density and Wilson-CI test assertions
- `tests/test_simulation.py`: Fixed Wilson-CI extreme-case assertions

---

## 2. Validation Results

| Check | Requirement | Result | Status |
|-------|-------------|--------|--------|
| PDF page count | ≤ 2 pages | 2 pages (A4, 595×842 pts) | PASS |
| Thumbnail dimensions | ≥ 1280×720, 16:9 | Exactly 1280×720, aspect 1.778 | PASS |
| Figure count | 12 PNGs | 12 figures generated | PASS |
| Figure resolution | High resolution | 800–2600 px wide, 200 dpi save | PASS |
| Test suite | All tests pass | 47 passed, 0 failed | PASS |
| Reproducibility | Fixed seed | Seed 20261118, identical results on re-run | PASS |
| Data completeness | Expected vs received | 87,672 / 87,672 = 100.0% | PASS |
| Duplicate timestamps | 0 | 0 | PASS |
| Missing timestamps | 0 | 0 | PASS |
| Annual scenario hours | Exactly 8,760 | Verified (Feb 29 excluded) | PASS |
| Block integrity | Within calendar months | 0 violations (2,933 blocks across 12 months) | PASS |
| Cp bounds | [0.30, 0.50] ≤ Betz limit | Cp max observed 0.4168, 60.6% of Betz | PASS |
| Eta bounds | [0.88, 0.98] | Verified | PASS |
| Power bounds | [0, P_rated] | Verified | PASS |
| CF bounds | [0, 1] | Verified | PASS |
| AEP nonnegative | ≥ 0 | Verified | PASS |

---

## 3. Test Results

**Command:** `python -m pytest -q tests`

**Result:** 47 passed, 1 warning (pytest deprecation, non-fatal), in 1.46s

**Test coverage:**
- `tests/test_turbine_model.py` (16 tests): swept area value and invalid-input rejection; air density at standard conditions, positivity, colder-is-denser, nonphysical rejection; power zero below cut-in, zero at/above cut-out, positive at cut-in, never exceeds rated/nonnegative, reaches rated at rated speed, monotone below rated, curve helper matches, increases with density, invalid Cp/eta rejection, nonpositive density rejection, calibration consistency; Weibull parameter recovery, tiny-sample rejection, inverse CDF median match, bad-input rejection; capacity factor definition and bad-hours rejection.
- `tests/test_simulation.py` (31 tests): bootstrap pools cover every month; blocks contiguous and complete; simulate shapes; reproducibility under fixed seed; different seeds differ; physical consistency (AEP≥0, CF in [0,1], power bounds, Cp/eta bounds, Betz); zero-scenario rejection; AEP-CF identity; histogram count; deterministic baseline years/hours/bounds; convergence table structure; Wilson CI bounds and extremes; summarise structure; summarise_baseline structure.

---

## 4. Final Numerical Findings

**Simulation:** 10,000 annual scenarios, seed 20261118, seasonally stratified 7-day block bootstrap, 87,672-hour ERA5 source record (2015–2024, Cuxhaven, Germany).

### Primary outcomes

| Metric | Value |
|--------|-------|
| Mean AEP | 6,523.2 MWh |
| Median AEP | 6,518.3 MWh |
| SD of AEP | 424.9 MWh |
| Variance of AEP | 180,558 MWh² |
| AEP 5th percentile | 5,834.5 MWh |
| AEP 25th percentile | 6,237.6 MWh |
| AEP 75th percentile | 6,810.6 MWh |
| AEP 95th percentile | 7,234.3 MWh |
| Mean AEP 95% MC CI | [6,514.9, 6,531.6] MWh |
| MC standard error of mean AEP | 4.25 MWh |
| Mean capacity factor | 0.3723 (SD 0.0243) |
| CF 5th percentile | 0.3330 |
| CF 95th percentile | 0.4129 |
| Expected power output | 0.745 MW |
| **P(CF < 0.25)** | **0.0000 (0/10,000)** |
| **P(CF < 0.25) 95% Wilson CI** | **[0.0000, 0.000384]** |

### Deterministic baseline (nominal Cp=0.359, eta=0.94, 2015–2024)

| Metric | Value |
|--------|-------|
| Mean AEP | 6,538.3 MWh |
| Min annual AEP | 5,976.2 MWh (2021) |
| Max annual AEP | 7,068.6 MWh (2015) |
| Mean CF | 0.3729 |
| CF range | 0.3411 – 0.4035 |
| Years with CF < 0.25 | 0 of 10 |

### Sensitivity analysis

**Spearman rank correlation with AEP (main simulation):**
- scenario_mean_wind_speed_mps: +0.875
- cp: +0.408
- scenario_mean_air_density_kg_m3: -0.361
- eta: +0.102

**Sobol indices (separate independent-input experiment, 12,288 model evaluations):**
- weibull_c: S1=0.855, ST=0.862 (dominant)
- cp: S1=0.121, ST=0.122
- eta: S1=0.009, ST=0.009
- rho_factor: S1=0.007, ST=0.008
- weibull_k: S1≈0.000, ST≈0.007

### Calibration verification

Cp=0.359, eta=0.94, rho=1.225 kg/m³ at V=11.5 m/s → 1.9998 MW (99.99% of rated 2.0 MW). Rated-power clipping activates above ~11.5 m/s (e.g., at 15 m/s raw=4.44 MW → operational=2.00 MW). Cp is 60.6% of the Betz limit (0.5926).

---

## 5. Remaining Limitations

1. **No preregistered prior hypothesis.** None was recorded before results were inspected. The analysis is exploratory; any post-hoc hypothesis is identified as such. (Approved by researcher.)

2. **No ML-style held-out test set.** This is a Monte Carlo uncertainty analysis, not a predictive model. The complete 2015–2024 record is retained in the primary analysis. A chronological robustness analysis (e.g., 2015–2023 develop / 2024 evaluate) is acceptable but not represented as a preregistered test set. (Approved by researcher.)

3. **P(CF < 0.25) = 0.0000** is the observed estimate from 10,000 scenarios, not zero underlying risk. The 95% Wilson CI upper bound is 0.000384 (0.0384%). Never interpreted as mechanical-failure probability — it is an energy-adequacy indicator.

4. **Uncertainty sources separated but not fully quantified:**
   - Monte Carlo sampling error: quantified (SE of mean AEP = 4.25 MWh)
   - Historical weather variability: represented by scenario SD (424.9 MWh)
   - Turbine parameter uncertainty: Cp and eta drawn once per scenario (truncated normals)
   - Structural model uncertainty: documented but NOT quantified numerically (simplified power curve, 2m-temperature proxy, hydrostatic pressure extrapolation, ERA5 gridded resolution)

5. **Data limitations:** ERA5 is gridded reanalysis, not on-site turbine measurement; 10-year record limits interannual variability; block joins break cross-block dependence; February 29 excluded so every scenario = 8,760 h.

6. **Stanford course page** (`https://pai.stanford.edu/pai1/studenthome`) could not be retrieved via automated fetch (returned no content on two attempts). Official course requirements were not independently verified from the live site; deliverable formats (≤2-page PDF, 16:9 thumbnail ≥1280×720, ≤60s video, README, AI_USAGE.md) follow the project brief.

7. **ERA5 licensing:** Open-Meteo's API page does not explicitly state an ERA5 license. SOURCES.md attributes ERA5 to ECMWF/Copernicus under standard CC BY 4.0 practice, flagged for verification against current Copernicus licence terms.

---

## 6. Reproduction Instructions

```bash
# 1. Create environment
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 2. (Optional) Re-download raw ERA5 data
python -m src.data_loader --force

# 3. Process data and run quality audit
python -m src.data_processing

# 4. Run the full pipeline (10,000 scenarios, ~18 seconds)
python -m src.run_pipeline

# 5. Run the test suite
python -m pytest -q tests

# Quick smoke run (1,000 scenarios)
python -m src.run_pipeline --quick
```

**Key reproducibility artifacts:**
- Random seed: 20261118 (fixed throughout)
- Exact request URLs: `data/raw/openmeteo_era5_cuxhaven_2015_2024.provenance.json`
- Software versions: `results/tables/analysis_manifest.json`
- All scenario outputs: `results/tables/scenarios.csv` (10,000 rows)

---

## 7. Requirement Checklist

| Requirement | Status | Evidence |
|-------------|--------|----------|
| **Data acquisition** | | |
| Open-Meteo ERA5 API, Cuxhaven (53.86, 8.69) | PASS | provenance.json, 87,672 records |
| Period 2015-01-01 to 2024-12-31, hourly, UTC | PASS | QC report |
| Variables: wind_speed_100m, temperature_2m, surface_pressure, wind_direction_100m | PASS | provenance.json |
| Model era5, cell_selection land, wind_speed_unit ms | PASS | provenance.json |
| Raw + processed data saved separately | PASS | data/raw/, data/processed/ |
| Provenance record (URL, timestamp, source, units, metadata) | PASS | provenance.json |
| Quality checks (completeness, duplicates, missing, ranges, non-finite) | PASS | data_quality_report.json/.md |
| No silent imputation/dropping | PASS | complete_case flag only |
| **Turbine model** | | |
| A = πR², R=45m → 6,361.73 m² | PASS | config.py, test |
| Hydrostatic hub-height density from 2m temp + surface pressure | PASS | turbine_model.py |
| P_raw = 0.5ρAV³Cpη, cut-in/rated/cut-out logic | PASS | turbine_model.py, tests |
| Betz limit Cp ≤ 16/27 enforced | PASS | turbine_model.py, tests |
| Not claimed OEM-certified | PASS | documented limitation |
| **Probability model** | | |
| Empirical historical wind (primary), Weibull descriptive only | PASS | simulation.py, report |
| Cp ~ TruncatedNormal(0.359, 0.015) on [0.30, 0.50] | PASS | config.py |
| η ~ TruncatedNormal(0.94, 0.01) on [0.88, 0.98] | PASS | config.py |
| Cp and η drawn once per scenario | PASS | simulation.py |
| **Monte Carlo** | | |
| ≥ 5,000 scenarios (10,000 run) | PASS | 10,000 scenarios |
| Reproducible seed | PASS | seed 20261118 |
| Seasonally stratified 7-day block bootstrap | PASS | simulation.py, verified 0 violations |
| Exactly 8,760 hours per scenario | PASS | verified |
| Feb 29 excluded, no mixed denominators | PASS | verified |
| **Statistical analysis** | | |
| AEP mean/median/SD/variance/5th/25th/75th/95th | PASS | summary.json |
| CF mean/SD/quantiles | PASS | summary.json |
| P(CF < 0.25) with CI | PASS | Wilson CI [0.0000, 0.000384] |
| Expected power output | PASS | 0.745 MW |
| Deterministic nominal baseline | PASS | 6,538.3 MWh |
| MC error separated from weather/turbine/structural uncertainty | PASS | documented separation |
| **Sensitivity** | | |
| Spearman rank correlation | PASS | spearman.csv |
| Sobol on separate independent-input experiment | PASS | sobol.csv, clearly separated |
| **Validation** | | |
| Automated physical-model + simulation tests | PASS | 47 tests pass |
| Convergence at 100/1,000/5,000/10,000 | PASS | convergence.csv |
| Tests actually executed (not claimed) | PASS | pytest run, 47 passed |
| **Figures** | | |
| 12 high-resolution PNGs with titles, labels, units, legends | PASS | results/figures/ |
| **Deliverables** | | |
| PDF writeup ≤ 2 pages | PASS | 2 pages A4 |
| 16:9 thumbnail ≥ 1280×720 | PASS | exactly 1280×720 |
| Video script ≤ 60 seconds | PASS | video/VIDEO-SCRIPT.md (~55-60s) |
| README | PASS | README.md |
| AI_USAGE.md | PASS | AI_USAGE.md |
| SOURCES.md / attribution | PASS | SOURCES.md |
| requirements.txt + documented commands | PASS | requirements.txt, README |
| **Integrity** | | |
| No fabricated data/results/sources/tests | PASS | all computed from executed code |
| Prior hypothesis not invented/retroactive | PASS | documented as none |
| Low-CF framed as energy adequacy, not failure | PASS | documented throughout |

---

## Conclusion

The project is complete. All eight phases have been executed and verified: data acquisition (87,672 ERA5 hourly records, 100% completeness), physical model implementation (calibrated to rated power at 11.5 m/s), Monte Carlo simulation (10,000 scenarios, block bootstrap), statistical analysis (AEP/CF distributions, P(CF<0.25)=0.0000 with Wilson CI), sensitivity analysis (Spearman + separated Sobol experiment), validation (47 tests pass, convergence verified), visualization (12 figures + thumbnail), and reporting (2-page PDF). All deliverables are present and validated.

**Key result:** Mean AEP = 6,523.2 MWh; mean capacity factor = 0.3723; P(CF < 0.25) = 0.0000 (0/10,000 scenarios, 95% Wilson CI [0.0000, 0.000384]). The low-CF probability estimate is accompanied by its confidence interval and is described strictly as an energy-adequacy indicator, not a mechanical-failure probability.
