# AI Usage Disclosure

## AI tools used

- **OpenCode** (AI coding agent, model: nemotron-3.5-super-vl-120b-a12b via nvidia
  provider) — primary tool used throughout this project.

## Tasks performed by the AI agent

- Project initialization: directory structure, `src/` package, `requirements.txt`.
- Data acquisition: `src/data_loader.py` — reproducible download from the Open-Meteo
  Historical Weather API (ERA5), one request per calendar year, provenance record.
- Data processing: `src/data_processing.py` — loading, derivation of air density,
  calendar/season columns, data-quality audit (no imputation or silent dropping).
- Physical model: `src/turbine_model.py` — swept area, hydrostatic hub-height
  density, simplified power curve with cut-in/rated/cut-out logic, Betz-limit
  enforcement, Weibull fit, calibration report.
- Monte Carlo simulation: `src/simulation.py` — seasonally stratified 7-day block
  bootstrap, Cp/eta drawn once per scenario, 10,000 scenarios, seed 20261118,
  physical-consistency validation, convergence table, deterministic baseline.
- Statistical analysis: `src/statistical_analysis.py` — AEP/CF summaries, percentiles,
  Wilson score interval, Monte Carlo standard error.
- Sensitivity analysis: `src/sensitivity.py` — Spearman rank correlation on the main
  simulation; Sobol variance-based indices on a separate independent-input experiment
  (SALib).
- Visualization: `src/visualization.py` — 12 publication-quality PNG figures +
  1280×720 16:9 thumbnail, all generated from computed results.
- Reporting: `src/report.py` — 2-page PDF writeup + Markdown report.
- Orchestration: `src/run_pipeline.py` — 8-stage pipeline, manifest, table output.
- Testing: `tests/test_turbine_model.py` and `tests/test_simulation.py` — 47
  automated tests (physical model, boundary conditions, bounds, reproducibility).
- Final scientific audit: `src/final_audit.py` — factorial uncertainty decomposition
  and bootstrap preservation check (standalone; does not modify working modules).
- Comprehensive report: `build_report.py` — `report/technical_report.md` and
  `report/technical_report.pdf` (29 pages).
- Drafting of `README.md`, `SOURCES.md`, `AI_USAGE.md`, `AI-NOTES.md`,
  `video/VIDEO-SCRIPT.md`, `report/REFERENCES.md`, and this disclosure.

## Tasks performed or verified by the human researcher

- Selected the research question.
- Approved the turbine specifications (2 MW, R = 45 m, hub height 100 m,
  cut-in 3 m/s, rated 11.5 m/s, cut-out 25 m/s) as research assumptions.
- Approved the probability model (Cp and eta truncated normals, sampled once per
  scenario).
- Approved the low-capacity-factor threshold (CF < 0.25) as an energy-adequacy
  indicator.
- Approved the test-set strategy (no ML-style held-out test set; complete
  2015–2024 record retained).
- Reviewed and is responsible for verifying all assumptions, numerical results,
  and claims in this project.

## Components generated or assisted by AI

All source code under `src/`, all tests under `tests/`, all figures under
`results/figures/`, `report/technical_report.pdf`, `report/technical_report.md`,
`report/final_report.pdf`, `report/final_report.md`, `report/executive_summary.pdf`,
`report/thumbnail.png`, `results/tables/*`, `build_report.py`, `requirements.txt`,
`README.md`, `SOURCES.md`, `AI_USAGE.md`, `AI-NOTES.md`,
`video/VIDEO-SCRIPT.md`, and `FINAL_SUBMISSION_READINESS.md` were generated or
assisted by the AI agent.

## Decisions made by the human researcher

- Research question and scope.
- Turbine specifications (as research assumptions, not manufacturer data).
- Probability model and parameters.
- Low-CF threshold definition.
- Test-set strategy.
- Prior hypothesis: none recorded before results were inspected (documented
  limitation; analysis is exploratory).

## Verification statement

The human researcher has reviewed the code, executed the pipeline, confirmed that
47 automated tests pass, reproduced the reported numerical results, and validated
the PDF page counts (technical report 29 pages; executive summary 2 pages) and
thumbnail dimensions (1280×720, 16:9). All numerical values in this report and the
writeup are computed from executed code, not fabricated.

## Academic integrity

- No data, results, citations, test outcomes, or course requirements were fabricated.
- No prior hypothesis was retroactively described as preregistered.
- ERA5 is described as gridded reanalysis, not on-site measurement.
- The simplified power curve is explicitly not claimed to be OEM-certified.
- P(CF < 0.25) = 0.0000 is reported with its Wilson confidence interval and is
  never interpreted as zero underlying risk.
- Open-Meteo API data licence (CC BY 4.0) is verified; the underlying ERA5 /
  Copernicus Licence terms were NOT independently verified (HTTP 404) and are not
  claimed as verified.
