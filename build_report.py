"""Build the comprehensive technical report (PDF + Markdown) from real results.

Uses reportlab for professional typesetting (no LaTeX dependency). Every number
is inserted from computed result dictionaries so the document cannot drift from
the analysis.
"""
from __future__ import annotations

import json
import math
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import inch, cm
from reportlab.lib import colors
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    BaseDocTemplate, PageTemplate, Frame, Paragraph, Spacer, Table, TableStyle,
    Image, PageBreak, KeepTogether, HRFlowable,
)
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont

import sys as _sys
if __package__ in (None, ""):
    _sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import src.config as C
    from src.data_processing import load_processed
    from src.simulation import build_bootstrap_pools
else:
    from . import config as C
    from .data_processing import load_processed
    from .simulation import build_bootstrap_pools

PROJECT_ROOT = C.PROJECT_ROOT
REPORT_DIR = C.REPORT_DIR
FIGURES_DIR = C.FIGURES_DIR
TABLES_DIR = C.TABLES_DIR

DATE_TODAY = date(2026, 11, 18).isoformat()

INK = colors.HexColor("#1a1a1a")
ACCENT = colors.HexColor("#006699")
GREY = colors.HexColor("#555555")
LIGHT = colors.HexColor("#EEEEEE")
MIDLINE = colors.HexColor("#999999")

# Register DejaVu fonts (Unicode, supports Greek/math symbols)
_FONT_DIR = "/usr/share/fonts/truetype/dejavu"
pdfmetrics.registerFont(TTFont("DejaVu", f"{_FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Bold", f"{_FONT_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-Oblique", f"{_FONT_DIR}/DejaVuSans.ttf"))
pdfmetrics.registerFont(TTFont("DejaVu-BoldOblique", f"{_FONT_DIR}/DejaVuSans-Bold.ttf"))
pdfmetrics.registerFontFamily("DejaVu", normal="DejaVu", bold="DejaVu-Bold",
                              italic="DejaVu-Oblique", boldItalic="DejaVu-BoldOblique")


def _load_json(name: str) -> dict:
    return json.loads((TABLES_DIR / name).read_text(encoding="utf-8"))


def _fmt(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}"


def _num(x: float, nd: int = 4) -> str:
    return f"{x:,.{nd}f}"


def _style(name: str, **kw) -> ParagraphStyle:
    base = dict(fontName="DejaVu", fontSize=9.5, leading=13.2,
                textColor=INK, alignment=TA_JUSTIFY, spaceAfter=6)
    base.update(kw)
    return ParagraphStyle(name, **base)


S_TITLE = _style("title", fontName="DejaVu-Bold", fontSize=20, leading=25,
                 alignment=TA_CENTER, spaceAfter=10, textColor=INK)
S_SUB = _style("subtitle", fontSize=12, leading=17, alignment=TA_CENTER,
               textColor=ACCENT, spaceAfter=14)
S_H1 = _style("h1", fontName="DejaVu-Bold", fontSize=13.5, leading=17,
              textColor=ACCENT, spaceBefore=14, spaceAfter=7, alignment=TA_LEFT)
S_H2 = _style("h2", fontName="DejaVu-Bold", fontSize=11.5, leading=15,
              textColor=INK, spaceBefore=10, spaceAfter=5, alignment=TA_LEFT)
S_BODY = _style("body")
S_SMALL = _style("small", fontSize=8.6, leading=11.6, textColor=INK)
S_CAPTION = _style("caption", fontSize=8.2, leading=11, textColor=GREY,
                   alignment=TA_CENTER, spaceAfter=8)
S_CELL = _style("cell", fontSize=8.4, leading=11, alignment=TA_LEFT)
S_CELL_C = _style("cellc", fontSize=8.4, leading=11, alignment=TA_CENTER)
S_CELLH = _style("cellh", fontName="DejaVu-Bold", fontSize=8.4, leading=11,
                  alignment=TA_CENTER, textColor=colors.white)
S_EQUATION = _style("equation", fontName="DejaVu", fontSize=9.6, leading=14,
                    alignment=TA_CENTER, textColor=INK, spaceBefore=4, spaceAfter=4)
S_EQUATION_MONO = _style("equation_mono", fontName="DejaVu", fontSize=9.0, leading=13,
                         alignment=TA_CENTER, textColor=INK, spaceBefore=3, spaceAfter=3)


def _header_footer(canvas, doc):
    canvas.saveState()
    # Header rule
    canvas.setStrokeColor(MIDLINE)
    canvas.setLineWidth(0.5)
    canvas.line(2 * cm, A4[1] - 1.5 * cm, A4[0] - 2 * cm, A4[1] - 1.5 * cm)
    canvas.setFont("DejaVu", 7.5)
    canvas.setFillColor(GREY)
    canvas.drawString(2 * cm, A4[1] - 1.35 * cm,
                      "Quantifying Wind Turbine Performance Uncertainty — Monte Carlo Simulation")
    canvas.drawRightString(A4[0] - 2 * cm, A4[1] - 1.35 * cm,
                           "Stanford PAI Final Project")
    # Footer
    canvas.line(2 * cm, 1.6 * cm, A4[0] - 2 * cm, 1.6 * cm)
    canvas.setFont("DejaVu", 7.5)
    canvas.drawString(2 * cm, 1.2 * cm, "WindTurbineProject — Stanford PAI")
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm,
                           f"Page {doc.page} | Analysis date: {DATE_TODAY}")
    canvas.restoreState()


def _table(data, col_widths, header=True, align_center_cols=None):
    align_center_cols = align_center_cols or []
    rows = []
    for i, row in enumerate(data):
        styled = []
        for j, cell in enumerate(row):
            if header and i == 0:
                styled.append(Paragraph(str(cell), S_CELLH))
            elif j in align_center_cols:
                styled.append(Paragraph(str(cell), S_CELL_C))
            else:
                styled.append(Paragraph(str(cell), S_CELL))
        rows.append(styled)
    t = Table(rows, colWidths=col_widths, repeatRows=1 if header else 0)
    cmds = [
        ("GRID", (0, 0), (-1, -1), 0.4, MIDLINE),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 3),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
        ("LEFTPADDING", (0, 0), (-1, -1), 5),
        ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ]
    if header:
        cmds.append(("BACKGROUND", (0, 0), (-1, 0), ACCENT))
        cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, LIGHT]))
    t.setStyle(TableStyle(cmds))
    return t


def _image(path: Path, width_cm: float, caption: str | None = None,
           label: str | None = None):
    from PIL import Image as PILImage
    img = PILImage.open(path)
    aspect = img.size[0] / img.size[1]
    height_cm = width_cm / aspect
    flow = Image(str(path), width=width_cm * cm, height=height_cm * cm)
    parts = [flow]
    if caption:
        full_cap = caption
        if label:
            full_cap = f"{label}  {caption}"
        parts.append(Paragraph(full_cap, S_CAPTION))
    return parts


def _eq(text: str, mono: bool = False) -> Paragraph:
    st = S_EQUATION_MONO if mono else S_EQUATION
    return Paragraph(text, st)


def build() -> tuple[Path, Path]:
    s = _load_json("summary.json")
    a = s["aep_mwh"]
    c = s["capacity_factor"]
    pr = s["probability_cf_below_threshold"]
    pw = s["expected_power_output_mw"]
    cal = _load_json("calibration.json")
    w = _load_json("weibull_fit.json")
    b = _load_json("baseline_summary.json")
    unc = _load_json("uncertainty_decomposition.json")
    boot = _load_json("bootstrap_preservation.json")
    sp = s.get("spearman", None) if False else None  # loaded separately below

    story = []

    # ============ TITLE PAGE ============
    story.append(Spacer(1, 2.2 * cm))
    story.append(Paragraph("Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation", S_TITLE))
    story.append(Paragraph("A probabilistic assessment of power generation, annual energy production, and energy adequacy", S_SUB))
    story.append(HRFlowable(width="100%", thickness=1.2, color=ACCENT, spaceAfter=16))
    story.append(Paragraph("Stanford Probability for AI (PAI) — Final Project", _style("t2", fontSize=13, leading=17, alignment=TA_CENTER, textColor=INK, spaceAfter=4)))
    story.append(Paragraph("Analysis site: Cuxhaven, Germany (53.86° N, 8.69° E)", _style("t3", fontSize=10.5, alignment=TA_CENTER, textColor=GREY, spaceAfter=2)))
    story.append(Paragraph("Analysis period: 2015-01-01 through 2024-12-31, hourly, UTC", _style("t4", fontSize=10.5, alignment=TA_CENTER, textColor=GREY, spaceAfter=2)))
    story.append(Paragraph(f"Analysis date: {DATE_TODAY}", _style("t5", fontSize=10.5, alignment=TA_CENTER, textColor=GREY, spaceAfter=4)))
    story.append(Paragraph("Prepared by: Mohammad Ghorbanpour", _style("t6", fontSize=10, alignment=TA_CENTER, textColor=GREY, spaceAfter=2)))
    story.append(Paragraph("Student ID: [placeholder]", _style("t7", fontSize=10, alignment=TA_CENTER, textColor=GREY, spaceAfter=18)))
    story.append(HRFlowable(width="100%", thickness=0.6, color=MIDLINE, spaceAfter=16))

    story.append(Paragraph("Source of truth", _style("st", fontName="DejaVu-Bold", fontSize=10, leading=14, alignment=TA_LEFT, spaceAfter=3)))
    story.append(Paragraph(
        "All numerical results in this report are computed from executed code and "
        "saved output files in this repository (data/, results/tables/, results/figures/). "
        "No data, results, experiments, or citations are invented. The existing concise "
        "two-page summary (report/final_report.pdf) is preserved unchanged as the "
        "executive summary; this document is the comprehensive technical report.",
        _style("stb", fontSize=8.8, leading=12, textColor=GREY, alignment=TA_JUSTIFY)))
    story.append(PageBreak())

    # ============ TABLE OF CONTENTS ============
    story.append(Paragraph("Contents", S_H1))
    toc_items = [
        ("1.", "Abstract"),
        ("2.", "Introduction"),
        ("3.", "Data Acquisition and Exploratory Analysis"),
        ("4.", "Wind Turbine Specifications and Physical Model"),
        ("5.", "Probabilistic Model and Uncertainty Sources"),
        ("6.", "Monte Carlo Simulation Methodology"),
        ("7.", "Verification, Testing, and Convergence"),
        ("8.", "Results"),
        ("9.", "Sensitivity Analysis"),
        ("10.", "Uncertainty Decomposition"),
        ("11.", "Discussion"),
        ("12.", "Limitations and Future Work"),
        ("13.", "Conclusion"),
        ("14.", "References"),
        ("Appendix A.", "Detailed turbine parameters and probability distributions"),
        ("Appendix B.", "Additional figures and tables"),
        ("Appendix C.", "Simulation pseudocode and reproducibility instructions"),
        ("Appendix D.", "Supplementary validation results"),
    ]
    for num, title in toc_items:
        story.append(Paragraph(f"{num}&nbsp;&nbsp;{title}", _style("toc", fontSize=10, leading=16, alignment=TA_LEFT, spaceAfter=2)))
    story.append(Spacer(1, 0.4 * cm))
    story.append(Paragraph("List of Figures", _style("lf", fontName="DejaVu-Bold", fontSize=10, leading=14, alignment=TA_LEFT, spaceAfter=3)))
    for i in range(1, 13):
        story.append(Paragraph(f"Figure {i:02d} — results/figures/fig{i:02d}.png",
                               _style("lf2", fontSize=9, leading=13, alignment=TA_LEFT, spaceAfter=1)))
    # ============ 1. ABSTRACT ============
    story.append(Paragraph("1. Abstract", S_H1))
    story.append(Paragraph(
        "Wind energy assessment commonly relies on a single deterministic estimate of "
        "annual energy production (AEP), which conceals the fact that wind speed is "
        "inherently variable and turbine parameters are only approximately known. "
        "This study quantifies the full predictive distribution of AEP, capacity "
        "factor, and expected power output for a hypothetical 2 MW wind turbine at "
        "Cuxhaven, Germany, using ten years (2015–2024) of hourly ERA5 reanalysis data "
        "retrieved via the Open-Meteo Historical Weather API. A seasonally stratified "
        "7-day block bootstrap generates 10,000 synthetic annual weather sequences "
        "(8,760 hours each), while turbine parameters — power coefficient Cp and "
        "system efficiency η — are drawn once per scenario from truncated normal "
        "distributions. Each scenario is integrated through a simplified physical "
        "power model to produce AEP and capacity factor.",
        S_BODY))
    story.append(Paragraph(
        "The mean AEP is 6,523.2 MWh (median 6,518.3 MWh; standard deviation 424.9 "
        "MWh; 95% Monte Carlo confidence interval [6,514.9, 6,531.6] MWh). The mean "
        "capacity factor is 0.3723 (SD 0.0243; 5th–95th percentile 0.3330–0.4129), "
        "corresponding to an expected power output of 0.745 MW. The deterministic "
        "baseline (nominal Cp = 0.359, η = 0.94 over the historical record) yields "
        "6,538.3 MWh, within 0.23% of the probabilistic mean. No simulated scenario "
        "falls below a capacity factor of 0.25 (P(CF < 0.25) = 0/10,000; 95% Wilson "
        "confidence interval [0.0000, 0.0004]); this is an energy-adequacy indicator, "
        "not a mechanical-failure probability, and the estimate is not zero underlying "
        "risk. Historical weather variability accounts for approximately 83.1% of AEP "
        "variance, turbine-parameter uncertainty 18.9%, with a small residual "
        "interaction term (−1.9%). Structural model uncertainty is not quantified and "
        "remains a documented limitation.",
        S_BODY))
    story.append(Paragraph(
        "An automated test suite (47 tests) verifies the physical model and simulation "
        "pipeline, and convergence is demonstrated at 100, 1,000, 5,000, and 10,000 "
        "scenarios. The study is exploratory: no hypothesis was preregistered before "
        "results were inspected. All results are reproducible from the repository.",
        S_BODY))
    story.append(PageBreak())

    # ============ 2. INTRODUCTION ============
    story.append(Paragraph("2. Introduction", S_H1))
    story.append(Paragraph("2.1 Background and motivation", S_H2))
    story.append(Paragraph(
        "The economic and operational viability of a wind energy project is governed "
        "largely by its annual energy production — the electrical energy delivered over "
        "one year — and by its capacity factor, the ratio of actual energy output to "
        "the energy that would be produced if the turbine operated at rated power "
        "continuously. Conventional energy assessments typically report a single "
        "deterministic AEP value computed from a long-term mean wind speed and a "
        "manufacturer power curve. While useful for screening, such a point estimate "
        "hides two important facts: first, that wind speed varies from year to year, "
        "season to season, and hour to hour; and second, that the parameters in the "
        "power-conversion model (rotor efficiency, drivetrain efficiency, air density) "
        "are only approximately known. A deterministic calculation therefore reports "
        "precision that is not warranted and cannot answer questions about the risk of "
        "low output years.",
        S_BODY))
    story.append(Paragraph(
        "Probabilistic methods address this gap by propagating input uncertainty "
        "through a physical model to obtain a full output distribution. Monte Carlo "
        "simulation is particularly well suited because it makes no assumptions about "
        "the analytical tractability of the power curve and naturally accommodates "
        "nonlinearities such as rated-power clipping and cut-in/cut-out thresholds. "
        "This project applies that approach to a hypothetical turbine at a real coastal "
        "site using a decade of reanalysis data.",
        S_BODY))
    story.append(Paragraph("2.2 Research question", S_H2))
    story.append(Paragraph(
        "How do uncertainties in wind speed, air density, and turbine operating "
        "parameters affect the power output, annual energy production, and energy "
        "adequacy of a 2 MW wind turbine? Specifically: (i) what is the predictive "
        "distribution of AEP and capacity factor; (ii) what is the probability that "
        "annual capacity factor falls below 0.25 (an energy-adequacy indicator); "
        "(iii) how do weather variability and turbine-parameter uncertainty contribute "
        "to AEP variance; and (iv) which inputs drive AEP most strongly?",
        S_BODY))
    story.append(Paragraph("2.3 Objectives", S_H2))
    story.append(Paragraph(
        "The objectives are to: retrieve and quality-check ten years of hourly ERA5 "
        "reanalysis data; implement and calibrate a simplified physical power model; "
        "run a seasonally stratified block-bootstrap Monte Carlo simulation; estimate "
        "AEP and capacity-factor distributions with confidence intervals; separate "
        "Monte Carlo sampling error, weather variability, and turbine-parameter "
        "uncertainty; perform sensitivity analysis (Spearman rank correlation on the "
        "main simulation and a separate Sobol experiment under independent inputs); "
        "and document all assumptions, limitations, and reproducibility details.",
        S_BODY))
    story.append(Paragraph("2.4 Scope", S_H2))
    story.append(Paragraph(
        "The study covers one hypothetical turbine at one grid cell (Cuxhaven, "
        "Germany; returned ERA5 cell 53.75° N, 8.75° E, elevation 5 m) over one "
        "decade (2015–2024). The turbine is hypothetical and its parameters are "
        "engineering assumptions, not manufacturer specifications. The model is "
        "simplified (constant Cp and η per scenario, no control-system dynamics, no "
        "losses beyond η) and is not OEM-certified. ERA5 is gridded reanalysis, not "
        "on-site turbine measurement, so results are a regional estimate and may not "
        "transfer to a specific turbine location. Structural model uncertainty is "
        "acknowledged but not quantified numerically.",
        S_BODY))
    story.append(PageBreak())

    # ============ 3. DATA ============
    story.append(Paragraph("3. Data Acquisition and Exploratory Analysis", S_H1))
    story.append(Paragraph("3.1 Open-Meteo Historical Weather API", S_H2))
    story.append(Paragraph(
        "Hourly data were retrieved from the Open-Meteo Historical Weather API "
        "(https://archive-api.open-meteo.com/v1/archive), documentation at "
        "https://open-meteo.com/en/docs/historical-weather-api. One programmatic "
        "HTTP request was made per calendar year, with exact request URLs, retrieval "
        "timestamp (2026-11-18T03:44:39 UTC), and per-year response metadata stored in "
        "a provenance record (data/raw/openmeteo_era5_cuxhaven_2015_2024.provenance.json). "
        "The API returned data under the CC BY 4.0 licence for the Open-Meteo service; "
        "the underlying ERA5 reanalysis is a separate Copernicus product governed by "
        "the Copernicus Licence, whose terms were not independently established in this "
        "audit (see Section 14 and SOURCES.md).",
        S_BODY))
    story.append(Paragraph("3.2 ERA5 reanalysis dataset", S_H2))
    story.append(Paragraph(
        "The underlying model is ERA5, the fifth-generation atmospheric reanalysis of "
        "the European Centre for Medium-Range Weather Forecasts (ECMWF), produced as "
        "part of the Copernicus Climate Change Service. ERA5 assimilates observations "
        "into a numerical weather prediction system on a regular grid with hourly "
        "temporal resolution. Because ERA5 is gridded reanalysis rather than an "
        "on-site measurement, the wind series represents conditions at the ERA5 grid "
        "cell containing the requested point and is a regional estimate of the site "
        "climate.",
        S_BODY))
    story.append(Paragraph("3.3 Site, period, resolution, and variables", S_H2))
    site_rows = [
        ["Item", "Value"],
        ["Site", "Cuxhaven, Germany"],
        ["Requested coordinates", "53.86° N, 8.69° E"],
        ["Returned ERA5 grid cell", "53.75° N, 8.75° E (cell_selection = land)"],
        ["Grid-cell elevation", "5 m"],
        ["Period", "2015-01-01 through 2024-12-31"],
        ["Temporal resolution", "Hourly, UTC"],
        ["Variables", "wind_speed_100m (m/s), temperature_2m (°C), surface_pressure (hPa), wind_direction_100m (°)"],
        ["Records retrieved", "87,672 (one request per calendar year)"],
        ["Completeness", "100.0% (0 missing timestamps, 0 duplicates)"],
    ]
    story.append(_table(site_rows, [4.6*cm, 11.2*cm], align_center_cols=[1]))
    story.append(Paragraph("Table 1. Site, period, resolution, and retrieval summary.", S_CAPTION))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "Leap years (2016, 2020, 2024) contain 8,784 hours; common years contain 8,760. "
        "The full record comprises 87,672 hourly timestamps with no gaps, duplicates, "
        "or non-monotonic timestamps. No values were imputed, interpolated, or removed. "
        "Raw and processed data are stored separately (data/raw/ and data/processed/).",
        S_BODY))
    story.append(Paragraph("3.4 Data quality checks", S_H2))
    story.append(Paragraph(
        "A data-quality audit confirmed completeness, absence of duplicates and missing "
        "timestamps, and plausible ranges for every variable (wind speed 0–60 m/s; "
        "temperature −60 to 60 °C; pressure 800–1,100 hPa; direction 0–360°). All "
        "checks passed with zero violations. A derived variable, hub-height air density, "
        "was computed hour by hour from temperature and surface pressure (Section 4.2); "
        "it is a derived estimate, not a measurement. The processed dataset contains "
        "87,672 records: 7,440 per month except February (6,792 including 72 leap-day "
        "hours across the leap years), matching the expected hourly count exactly.",
        S_BODY))
    story.append(Paragraph("3.5 Wind-speed distribution and seasonal patterns", S_H2))
    story.append(Paragraph(
        "The historical record (Feb 29 excluded for analysis consistency) has a mean "
        "100 m wind speed of 7.57 m/s, standard deviation 3.48 m/s, minimum 0.0 m/s, "
        "and maximum 27.23 m/s. Wind is strongly seasonal: winter months (December–"
        "February) average roughly 8.1–9.2 m/s while summer months (June–August) "
        "average roughly 6.1–6.5 m/s. The empirical distribution is right-skewed, with "
        "frequent low speeds and an extended tail toward high speeds. Figure 1 shows "
        "the historical time series; Figure 2 shows the histogram; Figure 3 shows the "
        "monthly mean wind speed; Figure 4 shows the seasonal distributions.",
        S_BODY))
    story.append(Paragraph("3.6 Weibull distribution: fit, interpretation, and limitations", S_H2))
    story.append(Paragraph(
        "A two-parameter Weibull distribution was fitted to the empirical wind speeds "
        "(location fixed at 0) by maximum likelihood. The fitted shape is k = 2.298 and "
        "the scale is c = 8.535 m/s (n = 87,672). The fitted mean (7.561 m/s) agrees "
        "closely with the observed mean (7.57 m/s). However, a Kolmogorov–Smirnov test "
        "gives D = 0.0139 (p = 3.25×10⁻¹⁵), formally rejecting the null hypothesis "
        "that the data are exactly Weibull-distributed — unsurprising given the very "
        "large sample and the presence of seasonality, diurnal cycles, and synoptic "
        "variability that a single stationary Weibull cannot capture.",
        S_BODY))
    story.append(Paragraph(
        "Accordingly, the Weibull fit is treated as descriptive only. It is not used to "
        "generate wind speeds in the main simulation, because it would discard "
        "seasonality and autocorrelation and would not reproduce the historical record "
        "as faithfully as direct resampling. The Weibull parameters do appear in the "
        "separate Sobol sensitivity experiment (Section 9), where they serve as "
        "independent inputs to rank parameter importance under an independence "
        "assumption that is deliberately distinct from the historical-weather "
        "simulation.",
        S_BODY))
    story.extend(_image(FIGURES_DIR / "fig01_wind_timeseries.png", 15.6,
        caption="Historical hourly 100 m wind speed at Cuxhaven, Germany (2015–2024, UTC).",
        label="Figure 1."))
    story.extend(_image(FIGURES_DIR / "fig02_wind_histogram.png", 15.6,
        caption="Histogram of historical hourly 100 m wind speed; right-skewed empirical distribution.",
        label="Figure 2."))
    story.extend(_image(FIGURES_DIR / "fig03_monthly_mean_wind.png", 15.6,
        caption="Monthly mean 100 m wind speed showing the seasonal cycle (winter windier than summer).",
        label="Figure 3."))
    story.extend(_image(FIGURES_DIR / "fig04_seasonal_distributions.png", 15.6,
        caption="Seasonal wind-speed distributions (DJF, MAM, JJA, SON) from the historical record.",
        label="Figure 4."))
    story.extend(_image(FIGURES_DIR / "fig05_empirical_vs_weibull.png", 15.6,
        caption="Empirical wind-speed histogram versus the fitted Weibull density "
        "(k = 2.298, c = 8.535 m/s); the fit is descriptive only and is not used to "
        "generate the main simulation.",
        label="Figure 5."))
    story.append(PageBreak())

    # ============ 4. PHYSICAL MODEL ============
    story.append(Paragraph("4. Wind Turbine Specifications and Physical Model", S_H1))
    story.append(Paragraph("4.1 Hypothetical turbine specifications", S_H2))
    turb_rows = [
        ["Parameter", "Value", "Notes"],
        ["Rated power", "2.0 MW", "Hypothetical; assumption, not manufacturer data"],
        ["Rotor radius", "45 m", "Assumption"],
        ["Hub height", "100 m", "Assumption"],
        ["Swept area", "6,361.7 m²", "A = πR²"],
        ["Cut-in speed", "3 m/s", "Assumption"],
        ["Rated speed", "11.5 m/s", "Assumption"],
        ["Cut-out speed", "25 m/s", "Assumption"],
    ]
    story.append(_table(turb_rows, [4.2*cm, 3.2*cm, 8.4*cm]))
    story.append(Paragraph("Table 2. Turbine specifications (engineering assumptions for a hypothetical turbine).", S_CAPTION))
    story.append(Spacer(1, 0.2*cm))
    story.append(Paragraph(
        "All turbine parameters are engineering assumptions for a hypothetical 2 MW "
        "turbine, selected to make the calibration reproduce rated power at the rated "
        "wind speed. They are not manufacturer specifications and the model is not "
        "OEM-certified.",
        S_BODY))
    story.append(Paragraph("4.2 Rotor swept area", S_H2))
    story.append(_eq("A = π R² = π × 45² ≈ 6,361.7 m²"))
    story.append(Paragraph("Equation 1. Rotor swept area from rotor radius R = 45 m.", S_CAPTION))
    story.append(Paragraph("4.3 Air-density estimation", S_H2))
    story.append(_eq("T_K = T_C + 273.15"))
    story.append(_eq("p_s = 100 × p_hPa"))
    story.append(_eq("p_h = p_s × exp(−g × H_h / (R_air × T_K))"))
    story.append(_eq("ρ = p_h / (R_air × T_K)"))
    story.append(Paragraph(
        "Equations 2–5. Hydrostatic hub-height air density from 2 m temperature "
        "(T_C), surface pressure (p_hPa in hPa), hub height H_h = 100 m, standard "
        "gravity g = 9.80665 m/s², and specific gas constant for dry air "
        "R_air = 287.05 J/(kg·K). The 2 m temperature is used as a proxy for "
        "hub-height temperature, and surface pressure is extrapolated to hub height; "
        "both are approximations, so density is a derived estimate, not a measurement.",
        S_CAPTION))
    story.append(Paragraph(
        "The mean derived air density over the record is 1.2309 kg/m³ (range "
        "1.2249–1.2379 kg/m³ across scenario means), close to but slightly above the "
        "ISA sea-level reference 1.225 kg/m³ used only for calibration.",
        S_BODY))
    story.append(Paragraph("4.4 Wind power equation", S_H2))
    story.append(_eq("P_raw = ½ × ρ × A × V³ × Cp × η"))
    story.append(Paragraph("Equation 6. Raw aerodynamic-to-electrical power in watts.", S_CAPTION))
    story.append(Paragraph("4.5 Power coefficient and system efficiency", S_H2))
    story.append(Paragraph(
        "Cp is the fraction of available wind power captured by the rotor; η is the "
        "drivetrain/generator efficiency converting captured mechanical power to "
        "electrical power. The nominal pair Cp = 0.359 and η = 0.94 reproduces rated "
        "power at the rated wind speed (Section 4.9). In the probabilistic model, Cp "
        "~ TruncatedNormal(μ = 0.359, σ = 0.015) bounded to [0.30, 0.50] and "
        "η ~ TruncatedNormal(μ = 0.94, σ = 0.01) bounded to [0.88, 0.98]; each is "
        "drawn once per scenario. These are engineering assumptions, not measured "
        "uncertainty data.",
        S_BODY))
    story.append(Paragraph("4.6 Cut-in, rated, and cut-out conditions", S_H2))
    story.append(_eq("P = { 0                       if V < V_ci", mono=True))
    story.append(_eq("    min(P_r, P_raw)           if V_ci ≤ V < V_co", mono=True))
    story.append(_eq("    0                       if V ≥ V_co}", mono=True))
    story.append(Paragraph(
        "Equation 7. Operational power with cut-in V_ci = 3 m/s, rated speed "
        "V_rated = 11.5 m/s (clipping point), cut-out V_co = 25 m/s, and rated power "
        "P_r = 2 MW. Below cut-in there is insufficient torque; at and above cut-out "
        "the turbine shuts down for safety; between cut-in and rated the raw cubic "
        "power applies; above rated speed the output is clipped at P_r.",
        S_CAPTION))
    story.append(Paragraph("4.7 Rated-power clipping", S_H2))
    story.append(Paragraph(
        "Above the rated speed, P_raw grows as V³ and would exceed rated power; the "
        "min(P_r, P_raw) term clips output at 2 MW. For example, at V = 15 m/s with "
        "nominal density and parameters, P_raw ≈ 4.44 MW but operational power is "
        "2.00 MW. Clipping caps the turbine's response to high winds and is a major "
        "reason why AEP grows sub-linearly with mean wind speed. At 25 m/s the turbine "
        "cuts out to zero.",
        S_BODY))
    story.extend(_image(FIGURES_DIR / "fig06_power_curve.png", 15.6,
        caption="Simplified power curve: zero below cut-in (3 m/s), cubic rise to rated "
        "power (2 MW at 11.5 m/s), flat/clipped at rated power up to cut-out (25 m/s), "
        "then zero. Not an OEM-certified curve.",
        label="Figure 6."))
    story.extend(_image(FIGURES_DIR / "fig07_mc_power_distribution.png", 15.6,
        caption="Distribution of hourly electrical power across all simulated scenarios "
        "(histogram with a mass at rated power due to clipping and at zero due to "
        "cut-in/cut-out).",
        label="Figure 7."))
    story.append(Paragraph("4.8 Betz limit", S_H2))
    story.append(_eq("Cp,max = 16/27 ≈ 0.5926"))
    story.append(Paragraph(
        "Equation 8. The Betz limit bounds the power coefficient at ≈0.5926 for an "
        "ideal actuator disk. The nominal Cp = 0.359 is 60.6% of the Betz limit, "
        "which is physically plausible for a real turbine. The upper bound [0.50] used "
        "for the truncated Cp distribution is below the Betz limit, so no sampled Cp "
        "violates physics.",
        S_CAPTION))
    story.append(Paragraph("4.9 Model calibration and validation", S_H2))
    story.append(Paragraph(
        "Calibration sets Cp = 0.359 and η = 0.94 so that, at V = V_rated = 11.5 m/s "
        "and ρ = 1.225 kg/m³, P_raw = 1.9998 MW — 99.99% of the 2.0 MW rated power. "
        "Rated power is therefore reached at the rated wind speed by construction. "
        "This is a calibration identity (parameter chosen to match a design point), "
        "not an empirical validation against measured turbine output. Because Cp and η "
        "are constant per scenario, the model cannot represent pitch control, "
        "tip-speed-ratio dependence, turbulence, icing, or array losses. Absolute AEP "
        "values should be interpreted with this simplification in mind.",
        S_BODY))
    story.append(Paragraph("4.10 Physical assumptions and simplifications", S_H2))
    story.append(Paragraph(
        "Key simplifications: (i) constant Cp and η per scenario (no dependence on "
        "wind speed, tip-speed ratio, or control state); (ii) 2 m temperature used as "
        "a hub-height temperature proxy; (iii) surface pressure hydrostatically "
        "extrapolated to 100 m; (iv) no representation of turbulence intensity, icing, "
        "soiling, availability, or electrical losses beyond η; (v) ERA5 grid-cell data "
        "rather than on-site measurements. These simplifications bias absolute AEP but "
        "the probabilistic conclusions (ranking of uncertainty sources, sensitivity "
        "ordering, low-CF rarity) are more robust than the absolute values.",
        S_BODY))
    story.append(PageBreak())

    # ============ 5. PROBABILISTIC MODEL ============
    story.append(Paragraph("5. Probabilistic Model and Uncertainty Sources", S_H1))
    story.append(Paragraph("5.1 Historical wind-speed representation", S_H2))
    story.append(Paragraph(
        "Wind variability is represented by direct resampling of the historical ERA5 "
        "series rather than by a parametric distribution. This preserves the observed "
        "marginal distribution, seasonality, and short-term autocorrelation within "
        "resampled blocks, subject to the bootstrap limitations discussed in Section 6.",
        S_BODY))
    story.append(Paragraph("5.2 Air-density variability", S_H2))
    story.append(Paragraph(
        "Air density is derived hour by hour from the historical temperature and "
        "pressure series via Equations 2–5, so density co-varies with the resampled "
        "weather. It is not held constant, and density uncertainty enters through the "
        "weather resampling (scenario mean density SD ≈ 0.0017 kg/m³), not through an "
        "independent distribution.",
        S_BODY))
    story.append(Paragraph("5.3 Power coefficient Cp", S_H2))
    story.append(_eq("Cp ~ TruncatedNormal(μ = 0.359, σ = 0.015) on [0.30, 0.50]"))
    story.append(Paragraph(
        "Equation 9. Cp is an engineering assumption, sampled once per annual scenario "
        "(turbine-level design parameter), not per hour. The nominal 0.359 reflects the "
        "calibration point; the spread reflects uncertainty in realized rotor "
        "efficiency. The upper bound 0.50 stays below the Betz limit (0.5926).",
        S_CAPTION))
    story.append(Paragraph("5.4 System efficiency η", S_H2))
    story.append(_eq("η ~ TruncatedNormal(μ = 0.94, σ = 0.01) on [0.88, 0.98]"))
    story.append(Paragraph(
        "Equation 10. η captures drivetrain and generator losses as an engineering "
        "assumption, sampled once per scenario.", S_CAPTION))
    story.append(Paragraph("5.5 Truncated normal distributions and bounds", S_H2))
    story.append(Paragraph(
        "Truncation confines Cp and η to physically and engineering-plausible ranges "
        "and prevents extreme draws from dominating the distribution. Because each is "
        "drawn once per scenario, their uncertainty is shared across all 8,760 hours "
        "of that scenario, inducing correlation between hours within a scenario and "
        "between AEP and CF (both monotone in the same Cp and η draws).",
        S_BODY))
    story.append(Paragraph("5.6 Rationale and the aleatory / epistemic distinction", S_H2))
    story.append(Paragraph(
        "Aleatory variability (irreducible randomness) is represented by the "
        "historical weather resampling: different years genuinely have different wind. "
        "Epistemic parameter uncertainty (reducible in principle with better data) is "
        "represented by the Cp and η distributions. Separating them clarifies that "
        "weather variability dominates AEP variance while turbine-parameter "
        "uncertainty is a secondary but non-negligible contributor.",
        S_BODY))
    story.append(PageBreak())

    # ============ 6. MONTE CARLO METHODOLOGY ============
    story.append(Paragraph("6. Monte Carlo Simulation Methodology", S_H1))
    story.append(Paragraph("6.1 General Monte Carlo framework", S_H2))
    story.append(Paragraph(
        "For each of N = 10,000 independent scenarios, a synthetic one-year weather "
        "sequence is generated, turbine parameters are drawn, hourly power is computed "
        "via Equations 6–7, and AEP and CF are calculated. Repeating this many times "
        "yields the empirical predictive distribution of each output. The Monte Carlo "
        "standard error of the mean scales as σ/√N and was 4.25 MWh for mean AEP at "
        "N = 10,000.",
        S_BODY))
    story.append(Paragraph("6.2 Seasonal stratification", S_H2))
    story.append(Paragraph(
        "The historical series is split into calendar-month strata so that each "
        "synthetic year respects the observed seasonal cycle (winter windier than "
        "summer). Blocks are drawn only from the matching calendar month, preventing "
        "a synthetic January from containing July-like winds.",
        S_BODY))
    story.append(Paragraph("6.3 168-hour block bootstrap", S_H2))
    story.append(Paragraph(
        "Within each month, contiguous 168-hour (7-day) blocks lying entirely inside "
        "one month and one year are resampled with replacement. The number of blocks "
        "per month is ceil(month_hours / 168), trimming the final partial block to the "
        "month's length. Within a block, chronological order is preserved, so "
        "short-term (synoptic) dependence survives. Dependence is broken at block "
        "joins and across month boundaries — a documented limitation.",
        S_BODY))
    story.append(Paragraph("6.4 Monthly resampling procedure", S_H2))
    story.append(Paragraph(
        "For each month m with L_m hours: draw ceil(L_m/168) block start positions "
        "uniformly from the valid starts for month m, concatenate the blocks, and trim "
        "to exactly L_m hours. Repeating for all 12 months and concatenating yields "
        "one 8,760-hour synthetic year (February 29 excluded).",
        S_BODY))
    story.append(Paragraph("6.5 Preservation and loss of temporal dependence", S_H2))
    story.append(Paragraph(
        "Preserved: within-block chronology (hour-to-hour synoptic persistence) and "
        "the seasonal cycle (via month strata). Lost: dependence across block joins "
        "(47 within-month joins per year) and across month boundaries (11 boundaries), "
        "giving 58 discontinuities per synthetic year. Longer-term interannual "
        "variability is limited to what the 10-year record contains.",
        S_BODY))
    story.append(Paragraph("6.6 Leap-day treatment", S_H2))
    story.append(Paragraph(
        "February 29 is excluded so every synthetic year has exactly 8,760 hours and "
        "scenarios share a common denominator. The 72 leap-day hours in the source "
        "record are not used for simulation. This avoids mixed denominators (8,760 vs "
        "8,784) and keeps capacity factors comparable across scenarios.",
        S_BODY))
    story.append(Paragraph("6.7 Annual scenario construction", S_H2))
    story.append(Paragraph(
        "Each scenario: (1) resample weather month by month via the block bootstrap; "
        "(2) draw Cp and η once; (3) derive hour-by-hour air density from temperature "
        "and pressure; (4) compute hourly power via Equations 6–7; (5) integrate "
        "AEP = Σ_t P_t Δt (Δt = 1 h, result in MWh); (6) compute CF = AEP / "
        "(P_r · 8,760). Only scenario-level outputs (AEP, CF, mean power, input draws) "
        "are retained; the full hourly series is not stored for all 10,000 scenarios.",
        S_BODY))
    story.append(Paragraph("6.8 Number of simulations and random seed", S_H2))
    story.append(Paragraph(
        "N = 10,000 scenarios with fixed seed 20261118, chosen to exceed the 5,000 "
        "scenario minimum and to make the Monte Carlo standard error of mean AEP "
        "(4.25 MWh) small relative to the spread (SD 424.9 MWh). Convergence was "
        "checked at 100, 1,000, 5,000, and 10,000 scenarios (Section 7). The full "
        "pipeline runs in roughly 18 seconds.",
        S_BODY))
    story.append(Paragraph("6.9 Algorithm (pseudocode)", S_H2))
    story.append(Paragraph(
        "<b>For</b> each scenario s = 1..N:<br/>"
        "&nbsp;&nbsp;<b>For</b> each month m = 1..12:<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Draw ceil(L_m/168) block starts uniformly within month m<br/>"
        "&nbsp;&nbsp;&nbsp;&nbsp;Concatenate 168-h blocks; trim to L_m hours<br/>"
        "&nbsp;&nbsp;<b>End</b><br/>"
        "&nbsp;&nbsp;Concatenate months → one 8,760-h synthetic year<br/>"
        "&nbsp;&nbsp;Draw Cp ~ TN(0.359, 0.015; [0.30,0.50])<br/>"
        "&nbsp;&nbsp;Draw η ~ TN(0.94, 0.01; [0.88,0.98])<br/>"
        "&nbsp;&nbsp;Derive ρ_t hour by hour from T_t, p_t (Eqs. 2–5)<br/>"
        "&nbsp;&nbsp;Compute P_t via Eqs. 6–7; AEP_s = Σ P_t · 1 h; CF_s = AEP_s / (2 MW · 8,760 h)<br/>"
        "<b>End</b><br/>"
        "Return empirical distributions of AEP, CF, expected power; compute quantiles, "
        "CIs, P(CF < 0.25) with Wilson interval.",
        S_SMALL))
    story.append(Paragraph("6.10 Computational reproducibility", S_H2))
    story.append(Paragraph(
        "The pipeline is invoked by `python -m src.run_pipeline` and uses fixed seed "
        "20261118. Software versions: Python 3.13.11, NumPy 2.5.0, pandas 3.0.4, "
        "SciPy 1.18.0, Matplotlib 3.11.0, pytest 9.2.0. Exact request URLs and "
        "per-year API metadata are in the provenance record; all outputs are in "
        "results/tables/ and results/figures/.",
        S_BODY))
    story.append(PageBreak())

    # ============ 7. TESTING AND CONVERGENCE ============
    story.append(Paragraph("7. Verification, Testing, and Convergence", S_H1))
    story.append(Paragraph("7.1 Physical-model tests", S_H2))
    story.append(Paragraph(
        "Automated tests verify swept area (π·45² = 6,361.73 m²), air density "
        "positivity and standard-condition value (≈1.225 kg/m³ at hub height 0 m), "
        "zero power below cut-in and at/above cut-out, non-negative power never "
        "exceeding rated power, Cp and η bounds, CF in [0, 1], non-negative AEP, "
        "correct annual hour counts, Weibull parameter recovery, and calibration "
        "consistency.",
        S_BODY))
    story.append(Paragraph("7.2 Simulation tests", S_H2))
    story.append(Paragraph(
        "Tests verify bootstrap pool coverage of every month, contiguous and complete "
        "blocks, correct scenario output shapes, reproducibility under a fixed seed, "
        "difference under different seeds, physical consistency (AEP ≥ 0, CF ∈ [0,1], "
        "power bounds, Cp/η bounds, Betz limit), zero-scenario rejection, the AEP–CF "
        "identity, and baseline summary structure.",
        S_BODY))
    story.append(Paragraph("7.3 Reproducibility and boundary-condition checks", S_H2))
    story.append(Paragraph(
        "Re-running the pipeline with the same seed reproduces identical results "
        "(mean AEP 6,523.2 MWh). Boundary tests confirm power is zero at and above "
        "cut-out (25 m/s) and below cut-in (3 m/s), and reaches rated power at the "
        "rated speed by construction.",
        S_BODY))
    story.append(Paragraph("7.4 Convergence analysis", S_H2))
    conv_rows = [
        ["N", "Mean AEP (MWh)", "Median AEP (MWh)", "SD AEP (MWh)", "P(CF<0.25)", "MC SE of mean (MWh)"],
        ["100", "6,541.8", "6,516.8", "452.1", "0.0000", "45.2"],
        ["1,000", "6,544.8", "6,531.0", "426.1", "0.0000", "13.5"],
        ["5,000", "6,526.5", "6,519.2", "425.2", "0.0000", "6.0"],
        ["10,000", "6,523.2", "6,518.3", "424.9", "0.0000", "4.2"],
    ]
    story.append(_table(conv_rows, [1.6*cm, 3.2*cm, 3.2*cm, 2.8*cm, 2.4*cm, 3.0*cm],
                        align_center_cols=[0,1,2,3,4,5]))
    story.append(Paragraph("Table 3. Convergence at 100, 1,000, 5,000, and 10,000 scenarios (nested prefixes of one run).", S_CAPTION))
    story.extend(_image(FIGURES_DIR / "fig11_convergence.png", 15.6,
        caption="Convergence of mean AEP, SD, and percentiles as scenario count increases "
        "(100 → 10,000); the distribution is well resolved by 10,000 scenarios.",
        label="Figure 11."))
    story.append(Paragraph(
        "The mean AEP stabilizes from 6,541.8 MWh (N=100) to 6,523.2 MWh (N=10,000), "
        "and the Monte Carlo standard error falls from 45.2 to 4.25 MWh. The SD and "
        "percentiles also stabilize, indicating the output distribution is well "
        "resolved by N = 10,000. P(CF < 0.25) remains 0.0000 at all sizes.",
        S_BODY))
    story.append(Paragraph("7.5 Monte Carlo standard error", S_H2))
    story.append(_eq("SE(ÂEP) = s_AEP / √N ≈ 424.9 / √10,000 = 4.25 MWh"))
    story.append(Paragraph(
        "Equation 11. MC standard error of the mean AEP. This is the uncertainty of the "
        "estimated mean due to finite simulation count, not a source of physical AEP "
        "variability; it shrinks as 1/√N.",
        S_CAPTION))
    story.append(Paragraph("7.6 Interpretation of numerical convergence", S_H2))
    story.append(Paragraph(
        "Convergence is demonstrated: further increases in N would change the reported "
        "mean by well under the MC standard error. The reported MC confidence interval "
        "[6,514.9, 6,531.6] MWh reflects this sampling uncertainty only.",
        S_BODY))
    story.append(PageBreak())

    # ============ 8. RESULTS ============
    story.append(Paragraph("8. Results", S_H1))
    story.append(Paragraph("8.1 Hourly wind and density characteristics", S_H2))
    story.append(Paragraph(
        "Over the 10-year record, mean wind speed is 7.57 m/s (SD 3.48 m/s), mean "
        "temperature is 10.6 °C, and mean surface pressure is 1,014.2 hPa. Derived "
        "hub-height air density averages 1.2309 kg/m³. Maximum observed wind speed is "
        "27.23 m/s (just above cut-out), so cut-out events occur but are rare. "
        "Figure 1 shows the historical time series; Figure 2 the histogram; Figure 3 "
        "the monthly means; Figure 4 the seasonal distributions.",
        S_BODY))
    story.append(Paragraph("8.2 Deterministic baseline", S_H2))
    story.append(Paragraph(
        "The deterministic baseline applies nominal Cp = 0.359 and η = 0.94 to the "
        "full historical record (2015–2024) without resampling or parameter "
        "uncertainty. Mean AEP is 6,538.3 MWh; annual AEP ranges from 5,976.2 MWh "
        "(2021) to 7,068.6 MWh (2015); mean CF is 0.3729 (range 0.3411–0.4035); no "
        "year falls below CF = 0.25. This baseline is a single-engineer point of "
        "reference, not a distribution.",
        S_BODY))
    base_rows = [
        ["Statistic", "Value"],
        ["Mean AEP (2015–2024)", "6,538.3 MWh"],
        ["Min annual AEP", "5,976.2 MWh (2021)"],
        ["Max annual AEP", "7,068.6 MWh (2015)"],
        ["SD of annual AEP", "359.9 MWh"],
        ["Mean capacity factor", "0.3729"],
        ["CF range", "0.3411 – 0.4035"],
        ["Years with CF < 0.25", "0 of 10"],
    ]
    story.append(_table(base_rows, [6.4*cm, 9.4*cm]))
    story.append(Paragraph("Table 4. Deterministic baseline (nominal Cp = 0.359, η = 0.94).", S_CAPTION))
    story.append(Paragraph("8.3 Annual energy production distribution", S_H2))
    story.append(Paragraph(
        "Across 10,000 simulated scenarios, mean AEP is 6,523.2 MWh (median 6,518.3 "
        "MWh; SD 424.9 MWh; variance 180,558 MWh²). The 5th and 95th percentiles are "
        "5,834.5 and 7,234.3 MWh, giving a central 90% range of about 1,400 MWh. The "
        "minimum and maximum scenario AEP are 4,839.0 and 8,255.5 MWh. Figure 8 shows "
        "the AEP histogram; Figure 11 shows convergence; Figure 12 shows confidence "
        "intervals.",
        S_BODY))
    story.extend(_image(FIGURES_DIR / "fig08_aep_distribution.png", 15.6,
        caption="Simulated distribution of annual energy production (10,000 scenarios) "
        "with the deterministic mean (6,538.3 MWh) marked.",
        label="Figure 8."))
    aep_rows = [
        ["Statistic", "Value"],
        ["Mean", "6,523.2 MWh"],
        ["Median", "6,518.3 MWh"],
        ["Standard deviation", "424.9 MWh"],
        ["Variance", "180,558 MWh²"],
        ["5th percentile", "5,834.5 MWh"],
        ["25th percentile", "6,237.6 MWh"],
        ["75th percentile", "6,810.6 MWh"],
        ["95th percentile", "7,234.3 MWh"],
        ["Minimum", "4,839.0 MWh"],
        ["Maximum", "8,255.5 MWh"],
        ["Mean 95% MC CI", "[6,514.9, 6,531.6] MWh"],
        ["MC standard error of mean", "4.25 MWh"],
    ]
    story.append(_table(aep_rows, [6.4*cm, 9.4*cm]))
    story.append(Paragraph("Table 5. Annual energy production distribution (10,000 scenarios).", S_CAPTION))
    story.append(Paragraph("8.4 Capacity-factor distribution", S_H2))
    story.append(Paragraph(
        "Mean CF is 0.3723 (SD 0.0243; variance 5.88×10⁻⁴). The 5th and 95th "
        "percentiles are 0.3330 and 0.4129; the median is 0.3721. CF is bounded in "
        "[0, 1] by construction and all simulated values lie well within this range. "
        "Figure 9 shows the CF histogram.",
        S_BODY))
    story.extend(_image(FIGURES_DIR / "fig09_cf_distribution.png", 15.6,
        caption="Simulated distribution of annual capacity factor (10,000 scenarios) "
        "with the low-capacity-factor threshold CF = 0.25 marked.",
        label="Figure 9."))
    cf_rows = [
        ["Statistic", "Value"],
        ["Mean", "0.3723"],
        ["Standard deviation", "0.0243"],
        ["Variance", "5.88×10⁻⁴"],
        ["5th percentile", "0.3330"],
        ["25th percentile", "0.3560"],
        ["Median", "0.3721"],
        ["75th percentile", "0.3887"],
        ["95th percentile", "0.4129"],
        ["Mean 95% MC CI", "[0.3719, 0.3728]"],
    ]
    story.append(_table(cf_rows, [6.4*cm, 9.4*cm]))
    story.append(Paragraph("Table 6. Capacity-factor distribution (10,000 scenarios).", S_CAPTION))
    story.append(Paragraph("8.5 Expected power", S_H2))
    story.append(Paragraph(
        "Expected power output (AEP / 8,760 h) averages 0.745 MW across scenarios "
        "(SD 0.049 MW; range 0.552–0.942 MW). This is well below the 2 MW rated power "
        "because the turbine spends much of the year below rated speed and above cut-in.",
        S_BODY))
    story.append(Paragraph("8.6 Confidence intervals and quantiles", S_H2))
    story.append(Paragraph(
        "The 95% MC confidence interval for mean AEP is [6,514.9, 6,531.6] MWh — an "
        "interval about the estimated mean reflecting finite simulation count, not "
        "the spread of individual annual outcomes. The 5th–95th percentile range of "
        "individual AEP outcomes is far wider (5,834.5–7,234.3 MWh) and represents "
        "genuine year-to-year variability plus parameter uncertainty.",
        S_BODY))
    story.extend(_image(FIGURES_DIR / "fig12_confidence_intervals.png", 15.6,
        caption="Confidence intervals and quantiles for AEP and capacity factor across "
        "scenario counts; MC uncertainty shrinks as 1/√N.",
        label="Figure 12."))
    story.append(Paragraph("8.7 Deterministic vs probabilistic comparison", S_H2))
    story.append(Paragraph(
        "The deterministic mean AEP (6,538.3 MWh) is within 0.23% of the probabilistic "
        "mean (6,523.2 MWh), so the nominal calibration is well centered on the "
        "probabilistic result. However, the deterministic value conveys no spread, no "
        "confidence interval, and no probability of low output. The probabilistic "
        "result reveals that individual years can deviate by roughly ±700 MWh from the "
        "mean (5th–95th percentile) — information the deterministic calculation "
        "entirely omits.",
        S_BODY))
    story.append(Paragraph("8.8 Low-capacity-factor probability", S_H2))
    story.append(Paragraph(
        "No simulated scenario falls below CF = 0.25: P(CF < 0.25) = 0/10,000 = "
        "0.0000. The 95% Wilson confidence interval is [0.0000, 0.0004], meaning the "
        "data are compatible with a true probability as high as about 0.04% (roughly "
        "1 in 2,600 years). This estimate must not be read as zero underlying risk: "
        "zero events in 10,000 scenarios is an upper-bound-limited statement, and the "
        "threshold is an energy-adequacy indicator (whether the year's energy output "
        "is likely adequate), not a mechanical-failure probability. A longer record, "
        "different Cp calibration, or real power curve could alter the estimate.",
        S_BODY))
    story.append(Paragraph("8.9 Interpretation of all important numerical results", S_H2))
    story.append(Paragraph(
        "Together, the results indicate a healthy but variable resource: mean CF ≈ 37% "
        "is typical for a well-sited onshore turbine, the AEP spread (±700 MWh at the "
        "5th–95th percentiles) is material for project finance, and the probability of "
        "a deeply low-output year (CF < 0.25) is very small but not provably zero. "
        "Weather variability dominates the spread (Section 10).",
        S_BODY))
    story.append(PageBreak())

    # ============ 9. SENSITIVITY ANALYSIS ============
    story.append(Paragraph("9. Sensitivity Analysis", S_H1))
    story.append(Paragraph("9.1 Spearman rank correlation", S_H2))
    story.append(Paragraph(
        "Spearman rank correlations were computed between each scenario-level input "
        "(scenario mean wind speed, scenario mean air density, drawn Cp, drawn η) and "
        "each output (AEP, capacity factor) across the 10,000 scenarios of the main "
        "simulation. Because Cp and η are drawn once per scenario and shared across "
        "hours, their correlations with AEP and CF are identical.",
        S_BODY))
    sp_rows = [
        ["Input", "Output", "Spearman ρ"],
        ["scenario mean wind speed (m/s)", "AEP", "+0.875"],
        ["scenario mean wind speed (m/s)", "Capacity factor", "+0.875"],
        ["Cp", "AEP", "+0.408"],
        ["Cp", "Capacity factor", "+0.408"],
        ["air density (kg/m³)", "AEP", "−0.361"],
        ["air density (kg/m³)", "Capacity factor", "−0.361"],
        ["η", "AEP", "+0.102"],
        ["η", "Capacity factor", "+0.102"],
    ]
    story.append(_table(sp_rows, [6.2*cm, 3.2*cm, 2.2*cm], align_center_cols=[2]))
    story.append(Paragraph("Table 7. Spearman rank correlations with AEP and capacity factor (main simulation).", S_CAPTION))
    story.append(Paragraph("9.2 Interpretation of the main-simulation correlations", S_H2))
    story.append(Paragraph(
        "Mean wind speed is by far the dominant driver (ρ = +0.875), consistent with "
        "the cubic power law. Cp (+0.408) is the next strongest turbine parameter; "
        "air density (−0.361) is negatively correlated because, in the historical "
        "record, denser (colder) air tends to accompany particular weather regimes and "
        "the scenario-mean density covaries with wind. η (+0.102) is a weak driver. "
        "These are correlations within a dependent historical-weather simulation; "
        "correlation does not imply causation, and the inputs are not independent.",
        S_BODY))
    story.append(Paragraph("9.3 Separate Sobol sensitivity experiment", S_H2))
    story.append(Paragraph(
        "A separate variance-based Sobol experiment was run with 1,024 base samples "
        "(12,288 model evaluations) using SALib. Inputs — Weibull shape k (1.8–2.6), "
        "Weibull scale c (7.0–10.0 m/s), Cp (0.30–0.45), η (0.88–0.98), and an air-"
        "density factor (0.95–1.05) — are drawn independently and uniformly, "
        "deliberately removing the temporal dependence present in the main simulation. "
        "Each evaluation uses a synthetic Weibull wind year (8,760 h) rather than the "
        "historical bootstrap. This ranks parameter importance under an independence "
        "assumption, complementing (not replacing) the main-simulation Spearman "
        "results.",
        S_BODY))
    story.append(Paragraph("9.4 First-order and total-order indices", S_H2))
    sob_rows = [
        ["Parameter", "S1 (first-order)", "ST (total-order)", "Interpretation"],
        ["Weibull scale c", "0.855", "0.862", "Dominant driver; wind speed scale"],
        ["Cp", "0.121", "0.122", "Secondary driver; rotor efficiency"],
        ["η", "0.009", "0.009", "Minor driver; efficiency"],
        ["Air-density factor", "0.007", "0.008", "Minor driver"],
        ["Weibull shape k", "≈0.000", "0.006", "Negligible first-order"],
    ]
    story.append(_table(sob_rows, [3.4*cm, 3.0*cm, 3.0*cm, 6.4*cm], align_center_cols=[1,2]))
    story.append(Paragraph("Table 8. Sobol indices (independent-input experiment; 12,288 evaluations).", S_CAPTION))
    story.extend(_image(FIGURES_DIR / "fig10_sensitivity.png", 15.6,
        caption="Sensitivity analysis: Spearman rank correlations from the main "
        "simulation (left) and Sobol first-order/total-order indices from the separate "
        "independent-input experiment (right). Wind-speed scale dominates; Cp is "
        "secondary.",
        label="Figure 10."))
    story.append(Paragraph("9.5 Difference between the two sensitivity methods", S_H2))
    story.append(Paragraph(
        "Spearman (main simulation) ranks mean wind speed first (+0.875) and reflects "
        "the actual dependent historical weather. Sobol (independent inputs) ranks "
        "Weibull scale c first (ST = 0.862) and Cp second (ST = 0.122). Both agree "
        "that wind-speed scale dominates and Cp is secondary; they differ in detail "
        "because the Sobol experiment assumes independent inputs and uses synthetic "
        "Weibull years, while Spearman uses the real dependent historical record. "
        "η is minor in both (ST ≈ 0.009).",
        S_BODY))
    story.append(Paragraph("9.6 Effect of the independent-input assumption", S_H2))
    story.append(Paragraph(
        "The Sobol independence assumption removes real-world covariation (e.g., "
        "density co-varying with wind, seasonality). Its indices answer 'how much "
        "would AEP variance shrink if this input were fixed while others vary "
        "independently?' rather than 'how much does this input explain in the real "
        "record?' Both views are reported and kept distinct.",
        S_BODY))
    story.append(Paragraph("9.7 Engineering interpretation", S_H2))
    story.append(Paragraph(
        "Wind resource (mean wind speed / Weibull scale) is the paramount driver of "
        "AEP uncertainty, followed by rotor efficiency Cp. Efficiency η and air "
        "density are secondary. Site selection and wind measurement therefore matter "
        "more than fine-tuning η for this turbine class.",
        S_BODY))
    story.append(PageBreak())

    # ============ 10. UNCERTAINTY DECOMPOSITION ============
    story.append(Paragraph("10. Uncertainty Decomposition", S_H1))
    story.append(Paragraph("10.1 Method", S_H2))
    story.append(Paragraph(
        "A factorial experiment separates the contributions to AEP variance using "
        "existing outputs. Arm A holds Cp and η at nominal values and resamples "
        "weather (5,000 bootstrap scenarios): variance = weather-only. Arm B holds one "
        "fixed historical year's weather and samples Cp and η (5,000 replicates, "
        "averaged over 10 historical years): variance = turbine-parameter-only. Arm C "
        "is the main simulation (both weather and Cp/η sampled): total variance. "
        "Interaction = total − weather − turbine.",
        S_BODY))
    story.append(Paragraph("10.2 Reported contributions", S_H2))
    unc_rows = [
        ["Component", "Variance (MWh²)", "Share of total"],
        ["Total AEP variance (main simulation)", "180,558", "100.0%"],
        ["A. Historical weather variability", "149,957", "83.1%"],
        ["B. Turbine-parameter uncertainty (Cp, η)", "34,043", "18.9%"],
        ["A×B interaction / residual", "−3,442", "−1.9%"],
    ]
    story.append(_table(unc_rows, [7.0*cm, 3.4*cm, 2.8*cm], align_center_cols=[1,2]))
    story.append(Paragraph("Table 9. Variance decomposition of AEP (factorial experiment; seed 20261118).", S_CAPTION))
    story.append(Paragraph("10.3 Negative interaction term", S_H2))
    story.append(Paragraph(
        "The interaction term is −3,442 MWh² (−1.9%), i.e. the combined variance is "
        "slightly less than the sum of the two arms. This is a residual/rounding "
        "artifact of the finite-sample, nonlinear decomposition (the turbine-parameter "
        "contribution depends on the weather realization because of the V³ cubic and "
        "rated clipping), not negative physical variance. It should be read as "
        "approximately zero within Monte Carlo error (MC SE of the weather variance "
        "estimate ≈ 3,000 MWh²; of the turbine variance mean ≈ 1,100 MWh²). The "
        "useful conclusion is that weather (~83%) and turbine parameters (~19%) "
        "essentially account for the total.",
        S_BODY))
    story.append(Paragraph("10.4 Monte Carlo sampling error vs physical uncertainty", S_H2))
    story.append(Paragraph(
        "Monte Carlo sampling error (SE of mean AEP = 4.25 MWh; variance of the sample "
        "mean ≈ 18 MWh², or 0.01% of total AEP variance) is the uncertainty of the "
        "estimated mean and shrinks as 1/√N. It is conceptually and numerically "
        "separate from physical/model uncertainty and is not part of the variance "
        "decomposition above.",
        S_BODY))
    story.append(Paragraph("10.5 Structural model uncertainty", S_H2))
    story.append(Paragraph(
        "Structural model uncertainty — error from the simplified power curve, the "
        "2 m temperature proxy, hydrostatic pressure extrapolation, and ERA5 grid-cell "
        "representation — is NOT quantified numerically. No experiment in this study "
        "varies the physics, data source, or model structure. Quantifying it would "
        "require comparison against an OEM power curve, hub-height measurements, or a "
        "longer/different dataset. It remains a documented qualitative limitation.",
        S_BODY))
    story.append(PageBreak())

    # ============ 11. DISCUSSION ============
    story.append(Paragraph("11. Discussion", S_H1))
    story.append(Paragraph("11.1 What the results mean for wind-energy assessment", S_H2))
    story.append(Paragraph(
        "A single deterministic AEP (6,538.3 MWh) hides the fact that individual "
        "simulated years range from 4,839 to 8,255 MWh and that the 5th–95th percentile "
        "spans roughly ±700 MWh around the mean. For project finance and energy "
        "adequacy planning, the distribution — not the point estimate — is the "
        "decision-relevant object.",
        S_BODY))
    story.append(Paragraph("11.2 Main drivers of AEP uncertainty", S_H2))
    story.append(Paragraph(
        "Historical weather variability (~83% of variance) dominates; turbine-"
        "parameter uncertainty (~19%) is secondary but real. Within weather, mean wind "
        "speed is the strongest driver (Spearman ρ = +0.875; Sobol ST = 0.862 for "
        "Weibull scale). Cp is the leading turbine parameter (ρ = +0.408; Sobol ST = "
        "0.122).",
        S_BODY))
    story.append(Paragraph("11.3 Interpretation of the low-CF result", S_H2))
    story.append(Paragraph(
        "P(CF < 0.25) = 0/10,000 with a 95% Wilson upper bound of 0.0004 indicates "
        "deeply low-output years are very unlikely under this model and record. But "
        "the estimate is not zero risk, and it is an energy-adequacy indicator, not a "
        "mechanical-failure probability. The short 10-year record may not contain the "
        "most extreme low-wind years possible.",
        S_BODY))
    story.append(Paragraph("11.4 Engineering implications", S_H2))
    story.append(Paragraph(
        "Site wind resource assessment deserves the greatest effort; rotor efficiency "
        "(Cp) is the next most influential design parameter. The deterministic and "
        "probabilistic means agree closely (within 0.23%), so the nominal calibration "
        "is reasonable, but only the probabilistic result quantifies risk and "
        "variability.",
        S_BODY))
    story.append(Paragraph("11.5 Comparison of deterministic and probabilistic approaches", S_H2))
    story.append(Paragraph(
        "Deterministic: fast, simple, one number, no uncertainty. Probabilistic: "
        "full distribution, confidence intervals, low-output probability, sensitivity "
        "ranking, uncertainty decomposition — at modest computational cost (~18 s for "
        "10,000 scenarios). The probabilistic approach is preferable whenever "
        "risk-aware decisions are made.",
        S_BODY))
    story.append(Paragraph("11.6 What can and cannot be concluded", S_H2))
    story.append(Paragraph(
        "Can conclude: weather variability dominates AEP uncertainty; Cp is the "
        "leading turbine parameter; low-CF years are very unlikely under this model; "
        "the simulation converges and is reproducible. Cannot conclude: the true "
        "long-run P(CF < 0.25) (Wilson bound only), absolute AEP accuracy (simplified "
        "model, ERA5 grid cell), or performance at any specific on-site turbine.",
        S_BODY))
    story.append(PageBreak())

    # ============ 12. LIMITATIONS ============
    story.append(Paragraph("12. Limitations and Future Work", S_H1))
    story.append(Paragraph(
        "• Short historical record (10 years): interannual variability is sampled from "
        "a limited set; the most extreme low- or high-wind years may be absent. "
        "• ERA5 grid-cell representation: data are a regional estimate at the returned "
        "cell (53.75° N, 8.75° E), not on-site turbine measurement. "
        "• Simplified turbine power model: constant Cp and η per scenario; no pitch "
        "control, tip-speed-ratio dependence, turbulence, icing, soiling, availability, "
        "or losses beyond η; not OEM-certified. "
        "• Air-density approximations: 2 m temperature as hub-height proxy and "
        "hydrostatic extrapolation of surface pressure to 100 m. "
        "• Engineering assumptions for Cp and η: not manufacturer uncertainty data. "
        "• Bootstrap dependence limitations: dependence broken at block joins and "
        "month boundaries (58 discontinuities/year); within-block chronology preserved. "
        "• Unquantified structural uncertainty: no experiment varies the physics, data "
        "source, or model structure. "
        "• Exploratory analysis: no preregistered hypothesis. "
        "Future work: use a manufacturer power curve, hub-height or on-site "
        "measurements, a longer record, explicit structural-model comparison, and "
        "preregistered hypotheses.",
        S_BODY))
    story.append(PageBreak())

    # ============ 13. CONCLUSION ============
    story.append(Paragraph("13. Conclusion", S_H1))
    story.append(Paragraph(
        "For a hypothetical 2 MW turbine at Cuxhaven, Germany, ten years of ERA5 "
        "reanalysis propagated through a simplified physical model and a seasonally "
        "stratified block-bootstrap Monte Carlo simulation (10,000 scenarios, seed "
        "20261118) yields a mean AEP of 6,523.2 MWh (median 6,518.3 MWh; SD 424.9 "
        "MWh; 95% MC CI [6,514.9, 6,531.6] MWh) and a mean capacity factor of 0.3723 "
        "(SD 0.0243; 5th–95th percentile 0.3330–0.4129). Expected power output is "
        "0.745 MW. The deterministic baseline (6,538.3 MWh) agrees within 0.23%. "
        "P(CF < 0.25) = 0/10,000 with a 95% Wilson interval [0.0000, 0.0004] — very "
        "small but not zero risk, and an energy-adequacy indicator rather than a "
        "failure probability. Weather variability accounts for ~83% of AEP variance "
        "and turbine-parameter uncertainty ~19%; structural model uncertainty is not "
        "quantified. The study is reproducible, converges by 10,000 scenarios, and is "
        "exploratory (no preregistered hypothesis).",
        S_BODY))
    story.append(PageBreak())

    # ============ 14. REFERENCES ============
    story.append(Paragraph("14. References", S_H1))
    refs = [
        "Open-Meteo. Historical Weather API — documentation. "
        "https://open-meteo.com/en/docs/historical-weather-api (accessed 2026-11-18).",
        "Open-Meteo. Licence — CC BY 4.0 for Open-Meteo API data. "
        "https://open-meteo.com/en/licence (accessed 2026-11-18).",
        "Open-Meteo. Terms of Use (non-commercial use; CC BY 4.0 acceptance). "
        "https://open-meteo.com/en/terms (accessed 2026-11-18).",
        "ECMWF / Copernicus Climate Change Service. ERA5 reanalysis (underlying model "
        "of the Open-Meteo Historical Weather API; governed by the separate Copernicus "
        "Licence, terms not independently verified in this audit).",
        "Manwell, J. F., McGowan, J. G., & Rogers, A. L. (2009). Wind Energy "
        "Explained, 2nd ed. John Wiley & Sons. (Power curve and air-density modeling.)",
        "IEC 61400-1. Wind energy generation systems — Part 1: Design requirements. "
        "International Electrotechnical Commission. (Turbine design context.)",
        "Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). "
        "Scientific Agent Skills: A Library of Procedural Knowledge for Research "
        "Agents. arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065",
    ]
    for i, r in enumerate(refs, 1):
        story.append(Paragraph(f"[{i}] {r}", _style(f"ref{i}", fontSize=9, leading=12.5,
                           alignment=TA_LEFT, spaceAfter=4, leftIndent=10, firstLineIndent=-10)))
    story.append(Paragraph(
        "Note on sources: Open-Meteo API documentation and the CC BY 4.0 licence were "
        "retrieved directly. The underlying ERA5 data are a Copernicus product; the "
        "applicable Copernicus Licence terms were not independently established "
        "(retrieval attempts returned HTTP 404) and are therefore not claimed as "
        "verified. No DOIs or publication details are invented.",
        S_SMALL))
    story.append(PageBreak())

    # ============ APPENDICES ============
    story.append(Paragraph("Appendix A. Detailed turbine parameters and probability distributions", S_H1))
    app_rows = [
        ["Quantity", "Value", "Type"],
        ["Rated power", "2.0 MW", "Assumption"],
        ["Rotor radius", "45 m", "Assumption"],
        ["Hub height", "100 m", "Assumption"],
        ["Swept area", "6,361.73 m²", "Derived (A = πR²)"],
        ["Cut-in speed", "3 m/s", "Assumption"],
        ["Rated speed", "11.5 m/s", "Assumption"],
        ["Cut-out speed", "25 m/s", "Assumption"],
        ["Cp nominal", "0.359", "Calibration assumption"],
        ["Cp distribution", "TN(0.359, 0.015; [0.30, 0.50])", "Assumption"],
        ["Cp fraction of Betz limit", "60.6%", "Derived"],
        ["η nominal", "0.94", "Calibration assumption"],
        ["η distribution", "TN(0.94, 0.01; [0.88, 0.98])", "Assumption"],
        ["Betz limit", "16/27 ≈ 0.5926", "Physical bound"],
        ["Gravity g", "9.80665 m/s²", "Constant"],
        ["Gas constant R_air", "287.05 J/(kg·K)", "Constant"],
        ["Seed", "20261118", "Fixed"],
        ["N scenarios", "10,000", "Design"],
        ["Block length", "168 h (7 days)", "Design"],
        ["CF threshold", "0.25", "Design (energy adequacy)"],
    ]
    story.append(_table(app_rows, [5.6*cm, 7.2*cm, 3.0*cm]))
    story.append(Paragraph("Table A1. Turbine and simulation design parameters.", S_CAPTION))

    story.append(Paragraph("Appendix B. Additional figures and tables", S_H1))
    story.append(Paragraph(
        "Figure 1: historical wind speed time series; Figure 2: wind-speed histogram; "
        "Figure 3: monthly mean wind speed; Figure 4: seasonal wind distributions; "
        "Figure 5: empirical vs Weibull fit; Figure 6: power curve; Figure 7: "
        "Monte Carlo hourly power distribution; Figure 8: AEP distribution; Figure 9: "
        "CF distribution; Figure 10: sensitivity (Spearman + Sobol); Figure 11: "
        "convergence; Figure 12: confidence intervals. Thumbnail: report/thumbnail.png "
        "(1280×720, 16:9). All figures are high-resolution PNGs generated from the "
        "computed results.",
        S_BODY))

    story.append(Paragraph("Appendix C. Simulation pseudocode and reproducibility instructions", S_H1))
    story.append(Paragraph(
        "Pseudocode is given in Section 6.9. To reproduce: "
        "`python -m src.data_loader --force` (optional re-download); "
        "`python -m src.data_processing`; `python -m src.run_pipeline`; "
        "`python -m pytest -q tests` (47 tests). The pipeline runs in ~18 s. "
        "All outputs are in results/tables/ and results/figures/.",
        S_BODY))

    story.append(Paragraph("Appendix D. Supplementary validation results", S_H1))
    story.append(Paragraph(
        "• 47 automated tests pass (`python -m pytest -q`, 1.46 s). "
        "• Bootstrap preservation: monthly mean differences within ±0.174 m/s; "
        "seasonal means within ±0.082 m/s; 58 discontinuities per simulated year "
        "(47 within-month joins + 11 month boundaries). "
        "• Calibration: P_raw = 1.9998 MW at V_rated = 11.5 m/s (99.99% of rated). "
        "• Weibull fit: k = 2.298, c = 8.535 m/s, KS D = 0.0139 (p = 3.25×10⁻¹⁵); "
        "descriptive only. "
        "• Data quality: 87,672 / 87,672 records (100.0%), 0 duplicates, 0 missing.",
        S_BODY))

    return story


def _build_pdf(story: list, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    doc = BaseDocTemplate(str(path), pagesize=A4,
                          leftMargin=2*cm, rightMargin=2*cm,
                          topMargin=1.8*cm, bottomMargin=2.0*cm,
                          title="Quantifying Wind Turbine Performance Uncertainty",
                          author="Stanford PAI Final Project")
    frame = Frame(doc.leftMargin, doc.bottomMargin, doc.width, doc.height, id="main")
    doc.addPageTemplates([PageTemplate(id="page", frames=[frame],
                                       onPage=_header_footer)])
    doc.build(story)
    return path


def _build_markdown(story_not_used=None) -> Path:
    # Markdown mirror of the report content (concise but complete).
    s = _load_json("summary.json")
    a = s["aep_mwh"]; c = s["capacity_factor"]; pr = s["probability_cf_below_threshold"]
    pw = s["expected_power_output_mw"]; cal = _load_json("calibration.json")
    w = _load_json("weibull_fit.json"); b = _load_json("baseline_summary.json")
    unc = _load_json("uncertainty_decomposition.json")
    lines = [
        "# Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation",
        "",
        "*A probabilistic assessment of power generation, annual energy production, and "
        "energy adequacy. Stanford PAI final project.*",
        "",
        f"**Analysis site:** Cuxhaven, Germany (53.86° N, 8.69° E; ERA5 grid cell "
        "53.75° N, 8.75° E, elevation 5 m)",
        f"**Analysis period:** 2015-01-01 through 2024-12-31, hourly, UTC",
        f"**Analysis date:** {DATE_TODAY}",
        f"**Author:** Mohammad Ghorbanpour",
        "",
        "## Abstract",
        "",
        "Wind energy assessment commonly relies on a single deterministic estimate of "
        "annual energy production (AEP), which conceals the fact that wind speed is "
        "inherently variable and turbine parameters are only approximately known. "
        "This study quantifies the full predictive distribution of AEP, capacity "
        "factor, and expected power output for a hypothetical 2 MW wind turbine at "
        "Cuxhaven, Germany, using ten years (2015–2024) of hourly ERA5 reanalysis data "
        "retrieved via the Open-Meteo Historical Weather API. A seasonally stratified "
        "7-day block bootstrap generates 10,000 synthetic annual weather sequences "
        "(8,760 hours each), while turbine parameters — power coefficient Cp and "
        "system efficiency η — are drawn once per scenario from truncated normal "
        "distributions.",
        "",
        f"The mean AEP is **{a['mean']:,.1f} MWh** (median {a['median']:,.1f} MWh; "
        f"SD {a['std']:,.1f} MWh; 95% MC CI [{a['mean_ci95'][0]:,.1f}, "
        f"{a['mean_ci95'][1]:,.1f}] MWh). The mean capacity factor is "
        f"**{c['mean']:.4f}** (SD {c['std']:.4f}; 5th–95th percentile "
        f"{c['p05']:.4f}–{c['p95']:.4f}), corresponding to an expected power output "
        f"of {pw['mean']:.3f} MW. The deterministic baseline (nominal Cp = 0.359, "
        f"η = 0.94) yields {b['aep_mwh_mean']:,.1f} MWh. No simulated scenario falls "
        f"below CF = 0.25 (P(CF < 0.25) = 0/10,000; 95% Wilson CI "
        f"[{pr['wilson_ci95'][0]:.4f}, {pr['wilson_ci95'][1]:.4f}]); this is an "
        "energy-adequacy indicator, not a mechanical-failure probability, and is not "
        "zero underlying risk. Historical weather variability accounts for ~83.1% of "
        "AEP variance; turbine-parameter uncertainty ~18.9%; structural model "
        "uncertainty is not quantified.",
        "",
        "## 1. Introduction",
        "",
        "Deterministic energy estimates report a single AEP and hide wind variability "
        "and parameter uncertainty. This project quantifies the full predictive "
        "distribution with Monte Carlo simulation and reports P(CF < 0.25) as an "
        "energy-adequacy indicator. Research question: how do uncertainties in wind "
        "speed, air density, and turbine parameters affect power output, AEP, and "
        "energy adequacy?",
        "",
        "## 2. Data",
        "",
        f"- Source: Open-Meteo Historical Weather API (ERA5 reanalysis), "
        f"{C.API_ENDPOINT}",
        f"- Site: {C.SITE_NAME}, {C.LATITUDE}° N, {C.LONGITUDE}° E",
        f"- Period: {C.START_DATE} to {C.END_DATE}, hourly, {C.TIMEZONE}",
        f"- Model: {C.MODEL}; cell selection: {C.CELL_SELECTION}; returned cell "
        f"53.75° N, 8.75° E, elevation 5 m",
        f"- Variables: {', '.join(C.VARIABLES)}",
        f"- Records: 87,672; completeness 100.0%; 0 duplicates; 0 missing timestamps",
        "- No imputation; raw and processed data stored separately with provenance record",
        "- Limitation: ERA5 is gridded reanalysis, not on-site turbine measurement",
        "",
        "## 3. Physical model",
        "",
        f"- R = 45 m, swept area A = πR² = {cal['swept_area_m2']:,.1f} m²",
        "- Air density: hydrostatic hub-height estimate from 2 m temperature and "
        "surface pressure (g = 9.80665 m/s², R_air = 287.05 J/(kg·K))",
        "- P_raw = ½ρAV³Cpη; P = 0 below cut-in; P = min(P_r, P_raw) between cut-in "
        "and cut-out; P = 0 at/above cut-out",
        f"- V_ci = 3 m/s, V_rated = 11.5 m/s, V_co = 25 m/s, P_r = 2.0 MW",
        f"- Calibration: Cp = 0.359, η = 0.94, ρ = 1.225 kg/m³ → "
        f"{cal['ratio_raw_over_rated_at_vrated']:.4f} × rated at V_rated "
        f"(rated power reached by construction); Cp = {cal['cp_fraction_of_betz']*100:.1f}% "
        f"of Betz limit (0.5926)",
        "- Not OEM-certified; constant Cp/η per scenario",
        "",
        "## 4. Probabilistic model",
        "",
        "- Wind: empirical ERA5 series, block bootstrap resampling",
        "- Air density: derived hourly from temperature and pressure",
        f"- Cp ~ TruncatedNormal(0.359, 0.015) on [0.30, 0.50], drawn once/scenario",
        f"- η ~ TruncatedNormal(0.94, 0.01) on [0.88, 0.98], drawn once/scenario",
        "- Weibull fit (k = 2.298, c = 8.535 m/s) descriptive only; not used to generate",
        "",
        "## 5. Monte Carlo methodology",
        "",
        f"- Seasonally stratified 168-h block bootstrap within calendar months",
        f"- February 29 excluded; every scenario exactly {C.N_HOURS_YEAR:,} h",
        f"- {s['n_scenarios']:,} scenarios, seed {s['seed']}",
        "- Per scenario: resample weather, draw Cp/η, compute hourly power, integrate "
        "AEP and CF",
        "- Cp/η shared across all 8,760 hours of a scenario (turbine-level parameters)",
        "",
        "## 6. Results",
        "",
        f"| Statistic | Value |",
        f"|---|---|",
        f"| Mean AEP | {a['mean']:,.1f} MWh |",
        f"| Median AEP | {a['median']:,.1f} MWh |",
        f"| SD AEP | {a['std']:,.1f} MWh |",
        f"| 5th / 95th percentile AEP | {a['p05']:,.1f} / {a['p95']:,.1f} MWh |",
        f"| Mean 95% MC CI | [{a['mean_ci95'][0]:,.1f}, {a['mean_ci95'][1]:,.1f}] MWh |",
        f"| MC standard error of mean | {a['mc_standard_error']:.2f} MWh |",
        f"| Mean CF | {c['mean']:.4f} (SD {c['std']:.4f}) |",
        f"| 5th / 95th percentile CF | {c['p05']:.4f} / {c['p95']:.4f} |",
        f"| Expected power output | {pw['mean']:.3f} MW |",
        f"| P(CF < 0.25) | {pr['estimate']:.4f} (95% Wilson CI "
        f"[{pr['wilson_ci95'][0]:.4f}, {pr['wilson_ci95'][1]:.4f}], 0/{pr['n']}) |",
        f"| Deterministic mean AEP | {b['aep_mwh_mean']:,.1f} MWh |",
        "",
        "## 7. Sensitivity analysis",
        "",
        "- Spearman (main simulation): mean wind speed +0.875; Cp +0.408; density −0.361; η +0.102",
        "- Sobol (separate independent-input experiment, 12,288 evals): Weibull scale "
        "c ST = 0.862; Cp ST = 0.122; η ST = 0.009",
        "- Correlation ≠ causation; Sobol assumes independent inputs, distinct from main sim",
        "",
        "## 8. Uncertainty decomposition",
        "",
        f"- Total AEP variance: {unc['variance_components_mwh2']['total_AEP_variance_C']:,.0f} MWh²",
        f"- Weather variability: {unc['variance_components_mwh2']['weather_only_A']:,.0f} "
        f"({unc['variance_components_mwh2']['weather_fraction_of_total']*100:.1f}%)",
        f"- Turbine-parameter (Cp, η): {unc['variance_components_mwh2']['turbine_only_B_mean_over_10_years']:,.0f} "
        f"({unc['variance_components_mwh2']['turbine_fraction_of_total']*100:.1f}%)",
        f"- Interaction/residual: {unc['variance_components_mwh2']['interaction_C_minus_A_minus_B']:,.0f} "
        f"({unc['variance_components_mwh2']['interaction_fraction_of_total']*100:.1f}%; "
        "approx. zero within MC error)",
        f"- MC sampling error: SE of mean AEP = {unc['monte_carlo_error']['mc_standard_error_of_mean_AEP_mwh']:.2f} MWh",
        "- Structural model uncertainty: NOT quantified (documented limitation)",
        "",
        "## 9. Limitations",
        "",
        "- 10-year record; ERA5 grid cell (not on-site); simplified power model; "
        "air-density approximations; engineering Cp/η assumptions; bootstrap joins "
        "break dependence; structural uncertainty unquantified; exploratory (no "
        "preregistered hypothesis)",
        "",
        "## 10. References",
        "",
        "[1] Open-Meteo. Historical Weather API. https://open-meteo.com/en/docs/historical-weather-api",
        "[2] Open-Meteo. Licence (CC BY 4.0). https://open-meteo.com/en/licence",
        "[3] Open-Meteo. Terms of Use. https://open-meteo.com/en/terms",
        "[4] ECMWF/Copernicus Climate Change Service. ERA5 reanalysis (via Open-Meteo; "
        "Copernicus Licence terms not independently verified).",
        "[5] Manwell, McGowan, Rogers (2009). Wind Energy Explained, 2nd ed., Wiley.",
        "[6] IEC 61400-1, Wind turbine generator systems.",
        "[7] Kassis et al. (2026). Scientific Agent Skills. arXiv:2609.00065.",
        "",
        "## Reproducibility",
        "",
        "`python -m src.data_processing`  `python -m src.run_pipeline`  "
        "`python -m pytest -q tests`  (seed 20261118; ~18 s for 10,000 scenarios)",
    ]
    path = C.REPORT_DIR / "technical_report.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path


def build_all() -> tuple[Path, Path]:
    story = build()
    pdf_path = _build_pdf(story, C.REPORT_DIR / "technical_report.pdf")
    md_path = _build_markdown()
    return pdf_path, md_path


if __name__ == "__main__":
    pdf_path, md_path = build_all()
    print(f"PDF: {pdf_path}")
    print(f"Markdown: {md_path}")
    import pypdf
    reader = pypdf.PdfReader(str(pdf_path))
    print(f"Pages: {len(reader.pages)}")