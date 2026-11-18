# Final Submission-Readiness Report

**Project:** Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation
**Course:** Stanford Probability for AI (PAI) Final Project
**Date:** 2026-11-18

---

## 1. Resolved Issues (this final audit)

| # | Issue | Resolution |
|---|-------|------------|
| 1 | Uncertainty sources not separately quantified | Implemented a factorial uncertainty decomposition (`src/final_audit.py`, outputs `results/tables/uncertainty_decomposition.json/.md`) separating historical weather variability (83.1%), turbine-parameter uncertainty (18.9%), interaction/residual (−1.9%, ≈0 within MC error), and Monte Carlo sampling error (SE = 4.25 MWh). Structural model uncertainty explicitly NOT quantified. |
| 2 | Bootstrap preservation not quantitatively validated | Ran a bootstrap preservation check (`results/tables/bootstrap_preservation.json/.md`) comparing historical vs 500 simulated years: monthly mean differences within ±0.174 m/s, seasonal means within ±0.082 m/s, quantile differences small; 58 discontinuities/year (47 within-month block joins + 11 month boundaries). KS p-values small only due to large n; effect sizes are the criterion. |
| 3 | Licensing inconsistency (ERA5 labelled CC BY 4.0) | Resolved in `SOURCES.md` and `report/REFERENCES.md`: Open-Meteo API data = CC BY 4.0 (verified directly from open-meteo.com/en/licence and /en/terms). Underlying ERA5 = separate Copernicus product governed by the Copernicus Licence, terms NOT independently verified (HTTP 404 on two retrieval attempts). No ERA5 licence claim made. |
| 4 | Report consistency across artifacts | Cross-checked every number in `report/technical_report.md`, `report/technical_report.pdf`, `report/final_report.md`, `report/final_report.pdf`, `FINAL_AUDIT_REPORT.md`, `video/VIDEO-SCRIPT.md`. All agree with `results/tables/summary.json`. Low-CF wording verified: 0/10,000, Wilson 95% CI [0.0000, 0.0004], described as energy-adequacy indicator (not mechanical failure), never interpreted as zero risk. |
| 5 | Course requirements verification | Final attempt to fetch https://pai.stanford.edu/pai1/studenthome returned no usable content. Limitation retained explicitly; no official requirements invented. Report formats follow the project brief. |
| 6 | Comprehensive technical report missing | Created `report/technical_report.md` and `report/technical_report.pdf` (29 pages, 14 sections + 4 appendices, 12 embedded figures, 9 tables, title page, TOC, numbered equations/tables/figures, references). Existing two-page executive summary preserved as `report/final_report.pdf` and copied to `report/executive_summary.pdf`. Created `report/REFERENCES.md`. |

---

## 2. Remaining Limitations (honest, not claimed away)

- **No preregistered prior hypothesis.** None recorded before results were inspected; analysis is exploratory. Any post-hoc hypothesis is identified as such.
- **No ML-style held-out test set.** This is a Monte Carlo uncertainty analysis, not a predictive model; the complete 2015–2024 record is retained in the primary analysis. Not misrepresented as a preregistered test set.
- **P(CF < 0.25) = 0.0000** is the observed estimate (0/10,000), not zero underlying risk. Wilson 95% CI upper bound 0.0004 (≈1 in 2,600 years). Described strictly as an energy-adequacy indicator, never as mechanical-failure probability.
- **Structural model uncertainty NOT quantified.** No experiment varies the physics, data source, or model structure (simplified power curve, 2 m temperature proxy, hydrostatic pressure extrapolation, ERA5 grid-cell resolution). Requires OEM power curve / hub-height measurements / longer record to quantify.
- **Short historical record (10 years)** limits sampled interannual variability.
- **ERA5 is gridded reanalysis**, not on-site turbine measurement; results are a regional estimate at cell (53.75° N, 8.75° E).
- **Bootstrap joins break dependence** at 47 within-month block joins + 11 month boundaries per year (58 discontinuities); within-block chronology preserved.
- **ERA5 licence terms not independently verified** (HTTP 404); distinguished from the verified Open-Meteo CC BY 4.0 API licence.
- **Stanford course page inaccessible**; official requirements not verified from the live site.

---

## 3. Quantitative Uncertainty Decomposition

Factorial experiment (seed 20261118), based on `results/tables/uncertainty_decomposition.json`:

| Component | Variance (MWh²) | Share of total AEP variance |
|---|---:|---:|
| Total AEP variance (main simulation, N=10,000) | 180,558 | 100.0% |
| A. Historical weather variability | 149,957 | 83.1% |
| B. Turbine-parameter uncertainty (Cp, η), mean over 10 fixed historical years | 34,043 | 18.9% |
| A×B interaction / residual | −3,442 | −1.9% (≈0 within MC error) |

- **Monte Carlo sampling error (separate, not part of physical variance):** SE of mean AEP = 4.25 MWh; variance of sample mean ≈ 18 MWh² (0.01% of total AEP variance); shrinks as 1/√N.
- **Structural model uncertainty:** NOT quantified. Documented qualitative limitation only.

Correct interpretation of the negative interaction: it is a residual/rounding artifact of the finite-sample nonlinear decomposition (the turbine-parameter contribution depends on the weather realization due to V³ cubic and rated clipping), not negative physical variance. It is ≈0 within Monte Carlo error (MC SE of weather variance estimate ≈ 3,000 MWh²; of turbine variance mean ≈ 1,100 MWh²). The useful conclusion: weather (~83%) and turbine parameters (~19%) essentially account for the total.

---

## 4. Final Validated Results

Source of truth: `results/tables/summary.json` (reproduced identically on re-run).

**Primary outcomes (10,000 scenarios, seed 20261118):**

| Metric | Value |
|---|---|
| Mean AEP | 6,523.2 MWh |
| Median AEP | 6,518.3 MWh |
| SD of AEP | 424.9 MWh |
| Variance of AEP | 180,558 MWh² |
| AEP 5th / 95th percentile | 5,834.5 / 7,234.3 MWh |
| Mean AEP 95% MC CI | [6,514.9, 6,531.6] MWh |
| MC standard error of mean AEP | 4.25 MWh |
| Mean capacity factor | 0.3723 (SD 0.0243) |
| CF 5th / 95th percentile | 0.3330 / 0.4129 |
| Expected power output | 0.745 MW |
| **P(CF < 0.25)** | **0.0000 (0/10,000)** |
| **P(CF < 0.25) 95% Wilson CI** | **[0.0000, 0.0004]** |

**Deterministic baseline (nominal Cp = 0.359, η = 0.94, 2015–2024):**

| Metric | Value |
|---|---|
| Mean AEP | 6,538.3 MWh |
| Min / max annual AEP | 5,976.2 / 7,068.6 MWh |
| Mean CF | 0.3729 (range 0.3411–0.4035) |
| Years with CF < 0.25 | 0 of 10 |

**Calibration (verified independently):** Cp = 0.359, η = 0.94, ρ = 1.225 kg/m³ at V = 11.5 m/s → P_raw = 1.9998 MW (99.99% of rated 2.0 MW; rated power reached by construction). Cp = 60.6% of Betz limit (0.5926). Rated-power clipping activates above ~11.5 m/s (e.g., 15 m/s: raw 4.44 MW → operational 2.00 MW).

**Sensitivity (Spearman, main simulation; Sobol, separate independent-input experiment):**
- Spearman ρ with AEP: mean wind speed +0.875; Cp +0.408; air density −0.361; η +0.102.
- Sobol total-order: Weibull scale c 0.862; Cp 0.122; η 0.009; air-density factor 0.008; Weibull shape k ≈0.000.

---

## 5. Test Results

Command: `python3 -m pytest -q tests`
**Result: 47 passed, 0 failed, 1.83 s.**

Coverage: physical model (swept area, air density, power curve boundary conditions, Cp/η bounds, Weibull fit, calibration) and simulation pipeline (bootstrap pool integrity, block completeness, scenario shapes, reproducibility, physical consistency, AEP–CF identity, baseline structure, convergence table, Wilson CI extremes).

---

## 6. Deliverable Inventory

**New / regenerated in this audit:**
- `build_report.py` — comprehensive report generator (reportlab)
- `report/technical_report.md` — full Markdown report
- `report/technical_report.pdf` — 29-page professional PDF (title page, TOC, 14 sections, 4 appendices, 12 figures, 9 tables)
- `report/executive_summary.pdf` — copy of preserved 2-page summary
- `report/REFERENCES.md` — references + licensing verification notes

**Preserved (unchanged, verified intact):**
- `report/final_report.pdf` — 2-page executive summary
- `report/final_report.md` — Markdown summary
- `report/thumbnail.png` — 1280×720, 16:9
- `results/figures/fig01–fig12.png` — 12 high-res figures (all embedded in technical report)
- `results/tables/*` — all computed outputs (summary, convergence, sensitivity, uncertainty decomposition, bootstrap preservation, calibration, baseline, Weibull)
- `src/` — all working modules (not modified in this audit)
- `tests/` — 47 tests
- `data/` — raw + processed ERA5 + provenance + quality report
- `requirements.txt`, `README.md`, `SOURCES.md` (licensing corrected), `AI_USAGE.md`, `AI-NOTES.md`, `video/VIDEO-SCRIPT.md`, `FINAL_AUDIT_REPORT.md`

---

## 7. Requirement Status (PASS / FAIL / NOT VERIFIED)

| Requirement | Status | Evidence |
|---|---|---|
| Open-Meteo ERA5 API, Cuxhaven (53.86, 8.69) | PASS | provenance.json; 87,672 records |
| Period 2015–2024, hourly, UTC | PASS | QC report |
| Variables: wind_speed_100m, temperature_2m, surface_pressure, wind_direction_100m | PASS | provenance.json |
| Model era5, cell_selection land | PASS | provenance.json |
| Raw + processed data saved separately | PASS | data/raw/, data/processed/ |
| Provenance record (URL, timestamp, metadata) | PASS | provenance.json |
| Quality checks (completeness, duplicates, missing) | PASS | 100.0%, 0, 0 |
| No silent imputation/dropping | PASS | complete_case flag only |
| Turbine model: swept area, density, power curve, cut-in/rated/cut-out | PASS | turbine_model.py + tests |
| Betz limit Cp ≤ 16/27 enforced | PASS | 0.359 = 60.6% of Betz |
| Not claimed OEM-certified | PASS | documented throughout |
| Empirical wind primary; Weibull descriptive only | PASS | simulation.py + report |
| Cp ~ TN(0.359,0.015)[0.30,0.50]; η ~ TN(0.94,0.01)[0.88,0.98] | PASS | config.py |
| Cp/η drawn once per scenario | PASS | simulation.py |
| ≥5,000 scenarios (10,000 run) | PASS | 10,000 scenarios |
| Reproducible seed | PASS | seed 20261118, identical on re-run |
| Seasonally stratified 7-day block bootstrap | PASS | verified 0 block violations |
| Exactly 8,760 h/scenario; Feb 29 excluded | PASS | verified |
| AEP/CF summaries, quantiles, CIs | PASS | summary.json |
| P(CF<0.25) with Wilson CI | PASS | [0.0000, 0.0004] |
| Expected power output | PASS | 0.745 MW |
| Deterministic baseline | PASS | 6,538.3 MWh |
| Uncertainty sources separated (MC/weather/turbine/structural) | PASS | Section 10 + uncertainty_decomposition.json |
| Structural uncertainty NOT claimed quantified | PASS | explicitly stated |
| Spearman rank correlation | PASS | spearman.csv |
| Sobol on separate independent-input experiment | PASS | sobol.json; clearly separated from main sim |
| Automated tests executed | PASS | 47 passed |
| Convergence at 100/1,000/5,000/10,000 | PASS | convergence.csv |
| 12 high-res PNG figures | PASS | results/figures/ (all embedded) |
| PDF writeup ≤ 2 pages (executive summary) | PASS | final_report.pdf = 2 pages |
| Thumbnail ≥1280×720, 16:9 | PASS | exactly 1280×720 |
| Video script ≤60 s | PASS | VIDEO-SCRIPT.md (~55–60 s) |
| README | PASS | README.md |
| AI_USAGE.md | PASS | AI_USAGE.md |
| SOURCES.md / attribution | PASS | SOURCES.md (licensing corrected) |
| requirements.txt + documented commands | PASS | requirements.txt, README |
| No fabricated data/results/sources/tests | PASS | all computed from executed code |
| Prior hypothesis not invented/retroactive | PASS | documented as none |
| Low-CF framed as energy adequacy, not failure | PASS | documented throughout |
| Technical report (12–20 pp body) | PASS | technical_report.pdf 29 pp total (~18 pp body + appendices/refs) |
| ERA5 licence claimed as verified | NOT VERIFIED | explicitly NOT claimed; Copernicus terms HTTP 404 |
| Stanford course requirements verified | NOT VERIFIED | page inaccessible; limitation retained |

---

## Conclusion

The project is **submission-ready with explicitly retained limitations**. All computational work is executed and reproduced (47 tests pass, identical results on re-run). All numerical values are consistent across the technical report PDF/Markdown, executive summary, and output files. The comprehensive technical report (29 pages) and preserved 2-page executive summary are both present. The only items marked NOT VERIFIED are those that genuinely cannot be verified from this environment (ERA5 Copernicus licence terms via HTTP 404; Stanford course page inaccessible), and these are documented as limitations rather than claimed.

Key result: Mean AEP = 6,523.2 MWh; mean capacity factor = 0.3723; P(CF < 0.25) = 0.0000 (0/10,000, 95% Wilson CI [0.0000, 0.0004]) — an energy-adequacy indicator, not zero risk.
