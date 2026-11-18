# AI and Contribution Notes

This file records AI and human contributions as work proceeds, per the Stanford PAI
project policy. It is updated alongside substantive changes.

## Project timeline (all work 2026-11-18)

### Phase 1 — Workspace and requirements inspection
- **AI:** Inspected workspace, existing files, Python environment; attempted to fetch
  https://pai.stanford.edu/pai1/studenthome (returned no usable content on two
  attempts; course requirements could not be verified from the live site).
- **Human:** Reviewed Phase 1 inspection report; approved decisions A–D (prior
  hypothesis, test-set strategy, low-CF threshold, research outcomes) and mandatory
  investigations.

### Phase 2 — Data acquisition and exploratory analysis
- **AI:** Retrieved 87,672 hourly ERA5 records (2015–2024, Cuxhaven) via the
  Open-Meteo Historical Weather API; wrote provenance record; processed data with
  derived air density; produced data-quality audit (100.0% completeness, 0 missing,
  0 duplicates; no imputation).
- **Human:** Approved data source, location, period, and variables.

### Phase 3 — Mathematical model implementation
- **AI:** Implemented swept area, hydrostatic hub-height density, simplified power
  curve, calibration report, Weibull fit.
- **Human:** Approved turbine specifications as research assumptions.

### Phase 4 — Probability distributions and Monte Carlo simulation
- **AI:** Implemented seasonally stratified 7-day block bootstrap (Feb 29 excluded,
  8,760 h/scenario), Cp/eta drawn once per scenario, 10,000 scenarios, seed
  20261118, deterministic baseline, convergence table.
- **Human:** Approved probability model (Cp/eta truncated normals) and low-CF
  threshold (CF < 0.25).

### Phase 5 — Statistical analysis and sensitivity analysis
- **AI:** Computed AEP/CF summaries, percentiles, Wilson CI, MC standard error;
  Spearman correlation (main simulation) and Sobol indices (independent-input
  experiment).
- **Human:** Reviewed sensitivity results; confirmed Sobol experiment is separate
  from the historical-weather simulation.

### Phase 6 — Validation and convergence tests
- **AI:** Wrote and ran 47 automated tests (all pass); convergence checked at
  100 / 1,000 / 5,000 / 10,000 scenarios.
- **Human:** Confirmed test suite passes.

### Phase 7 — Visualization
- **AI:** Generated 12 PNG figures + 1280×720 16:9 thumbnail; all from computed
  results.
- **Human:** Verified figure count, dimensions, and that values match simulation
  outputs.

### Phase 8 — Final scientific-quality audit and comprehensive report (this session)
- **AI:** Implemented factorial uncertainty decomposition and bootstrap preservation
  check (`src/final_audit.py`); corrected licensing documentation (`SOURCES.md`,
  new `report/REFERENCES.md`); built comprehensive technical report
  (`build_report.py`, `report/technical_report.md`, `report/technical_report.pdf`);
  preserved existing two-page executive summary (`report/final_report.pdf`,
  copied to `report/executive_summary.pdf`); created `AI_USAGE.md` and `AI-NOTES.md`;
  re-ran full pipeline and test suite; compiled `FINAL_SUBMISSION_READINESS.md`.
- **Human:** Approved all decisions; responsible for final verification and
  submission.

## Prior hypothesis

None recorded before results were inspected. The analysis is exploratory. Any
hypothesis formulated after seeing results is post hoc.

## Test-set strategy

No ML-style held-out test set (Monte Carlo uncertainty analysis, not predictive
model). Complete 2015–2024 record retained in primary analysis. A separate
chronological robustness analysis is acceptable but not misrepresented as a
preregistered test set.

## Limitations documented

- ERA5 is gridded reanalysis, not on-site measurement.
- Simplified power curve (constant Cp, eta); not OEM-certified.
- 2 m temperature used as hub-height temperature proxy.
- Surface pressure hydrostatically extrapolated to hub height.
- 10-year record limits interannual variability.
- Block joins break cross-block dependence.
- Structural model uncertainty not quantified numerically.
- Open-Meteo API licence (CC BY 4.0) verified; underlying ERA5 / Copernicus
  Licence terms NOT independently verified (HTTP 404).
- Stanford course page inaccessible; official requirements not verified from live
  site.
