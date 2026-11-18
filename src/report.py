"""Build the two-page PDF writeup and a full Markdown report from real results.

The PDF is laid out deterministically with matplotlib (no external template, no
network access).  Every number in it is inserted from the computed results
dictionaries, so the document cannot drift from the analysis.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib.backends.backend_pdf import PdfPages

from . import config as C

INK = "#1a1a1a"
ACCENT = "#0072B2"
GREY = "#555555"

PAGE_W, PAGE_H = 8.27, 11.69  # A4, inches
MARGIN = 0.62
TEXT_W = PAGE_W - 2 * MARGIN


def _wrap(text: str, width_chars: int) -> list[str]:
    out = []
    for para in text.split("\n"):
        if not para.strip():
            out.append("")
            continue
        out.extend(textwrap.wrap(para, width=width_chars) or [""])
    return out


def _chars_for(fontsize: float, width_in: float) -> int:
    # DejaVu Sans averages ~0.52 em per character.
    char_w_in = 0.52 * fontsize / 72.0
    return max(20, int(width_in / char_w_in * 0.97))


class Page:
    _counter = 0

    def __init__(self, pdf: PdfPages, preview_dir: Path | None = None):
        self.fig = plt.figure(figsize=(PAGE_W, PAGE_H))
        self.fig.patch.set_facecolor("white")
        self.y = PAGE_H - MARGIN
        Page._counter += 1
        self.preview_path = (
            Path(preview_dir) / f"page{Page._counter}.png" if preview_dir else None
        )

    def heading(self, text: str, size: float = 10.5, space_before: float = 4.0):
        self.y -= space_before / 72.0
        for line in _wrap(text, _chars_for(size, TEXT_W)):
            self.fig.text(MARGIN / PAGE_W, self.y / PAGE_H, line, fontsize=size,
                          fontweight="bold", color=ACCENT, ha="left", va="top")
            self.y -= (size * 1.28) / 72.0

    def para(self, text: str, size: float = 8.0, leading: float = 1.30,
             color: str = INK, space_before: float = 2.0, indent: float = 0.0):
        self.y -= space_before / 72.0
        width_in = TEXT_W - indent
        for line in _wrap(text, _chars_for(size, width_in)):
            self.fig.text((MARGIN + indent) / PAGE_W, self.y / PAGE_H, line,
                          fontsize=size, color=color, ha="left", va="top")
            self.y -= (size * leading) / 72.0

    def bullet(self, text: str, size: float = 8.0, indent: float = 0.16):
        self.y -= 1.0 / 72.0
        for i, line in enumerate(_wrap(text, _chars_for(size, TEXT_W - indent))):
            prefix = "\u2022 " if i == 0 else "  "
            self.fig.text((MARGIN + indent) / PAGE_W, self.y / PAGE_H, prefix + line,
                          fontsize=size, color=INK, ha="left", va="top")
            self.y -= (size * 1.28) / 72.0

    def rule(self, space: float = 3.0):
        self.y -= space / 72.0
        self.fig.add_artist(
            plt.Line2D([MARGIN / PAGE_W, (PAGE_W - MARGIN) / PAGE_W],
                       [self.y / PAGE_H, self.y / PAGE_H],
                       color="#BBBBBB", linewidth=0.6, transform=self.fig.transFigure)
        )

    def image(self, path: Path, width_in: float, caption: str | None = None,
              space_before: float = 4.0):
        import matplotlib.image as mpimg

        self.y -= space_before / 72.0
        img = mpimg.imread(path)
        h_in = width_in * img.shape[0] / img.shape[1]
        left = (PAGE_W - width_in) / 2 / PAGE_W
        bottom = (self.y - h_in) / PAGE_H
        ax = self.fig.add_axes([left, bottom, width_in / PAGE_W, h_in / PAGE_H])
        ax.imshow(img)
        ax.axis("off")
        self.y -= h_in
        if caption:
            self.para(caption, size=7.0, color=GREY, space_before=2.0)

    def finish(self, pdf: PdfPages):
        if self.y < 0.25:
            print(
                f"      WARNING page content reaches y={self.y:.2f} in "
                f"(page height {PAGE_H} in); check for overflow"
            )
        if self.preview_path is not None:
            self.preview_path.parent.mkdir(parents=True, exist_ok=True)
            self.fig.savefig(self.preview_path, dpi=110)
        pdf.savefig(self.fig)
        plt.close(self.fig)


def _fmt(x: float, nd: int = 0) -> str:
    return f"{x:,.{nd}f}"


# --------------------------------------------------------------------------
# Page 1
# --------------------------------------------------------------------------
def _page_one(pdf: PdfPages, ctx: dict, preview_dir: Path | None = None):
    p = Page(pdf, preview_dir=preview_dir)
    s = ctx["summary"]
    w = ctx["weibull"]
    cal = ctx["calibration"]

    p.para("Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation",
           size=15.5, leading=1.18, color=INK, space_before=0)
    p.para("A probabilistic assessment of power generation, annual energy production, "
           "and energy adequacy", size=9.6, leading=1.25, color=ACCENT, space_before=2)
    p.para(f"Stanford Probability for AI (PAI) Final Project  |  Analysis date: "
           f"{ctx['analysis_date']}  |  Code and data: see accompanying repository",
           size=7.6, color=GREY, space_before=2)
    p.rule()

    p.heading("1. Research question and motivation")
    p.para(
        "How do uncertainties in wind speed, air density, and turbine operating "
        "parameters affect the power output, annual energy production (AEP), and energy "
        "adequacy of a 2 MW wind turbine? A deterministic calculation returns a single "
        "AEP number and hides the fact that wind is variable and turbine parameters are "
        "only approximately known. We quantify the full predictive distribution with a "
        "Monte Carlo simulation driven by ten years of hourly reanalysis data, and we "
        "report the probability that annual capacity factor falls below 0.25."
    )

    p.heading("2. Data source and collection method")
    p.para(
        f"Hourly ERA5 reanalysis data were retrieved from the Open-Meteo Historical "
        f"Weather API (endpoint {C.API_ENDPOINT}) for {C.SITE_NAME} "
        f"(latitude {C.LATITUDE}, longitude {C.LONGITUDE}), {C.START_DATE} to "
        f"{C.END_DATE}, timezone {C.TIMEZONE}, model '{C.MODEL}', cell selection "
        f"'{C.CELL_SELECTION}'. Variables: 100 m wind speed (m/s), 2 m temperature "
        f"(degC), surface pressure (hPa), and 100 m wind direction (deg). "
        f"Retrieval was programmatic (one HTTP request per calendar year, "
        f"{ctx['n_records']:,} hourly records), and the exact request URLs, retrieval "
        f"timestamp, and per-year response metadata are stored in a provenance record. "
        f"Data completeness was {ctx['completeness']:.4f}% with "
        f"{ctx['n_duplicates']} duplicate timestamps and {ctx['n_missing']} missing "
        f"timestamps. No values were imputed or removed. ERA5 is gridded reanalysis, "
        f"not an on-site turbine measurement, so the series is a regional estimate."
    )

    p.heading("3. Mathematical model")
    p.para("Swept rotor area, air density, and electrical power are computed in SI units:")
    p.para("\u2022  A = \u03c0 R\u00b2,  with R = 45 m  \u2192  "
           f"A = {cal['swept_area_m2']:,.1f} m\u00b2", size=8.2, indent=0.1)
    p.para("\u2022  T_K = T_C + 273.15;   p_s = 100 p_hPa;   "
           "p_h = p_s exp(\u2212g H_h / (R_air T_K));   \u03c1 = p_h / (R_air T_K)",
           size=8.2, indent=0.1)
    p.para("\u2022  P_raw = \u00bd \u03c1 A V\u00b3 Cp \u03b7", size=8.2, indent=0.1)
    p.para("\u2022  P = 0 for V < V_ci;   P = min(P_r, P_raw) for V_ci \u2264 V < V_co;   "
           "P = 0 for V \u2265 V_co", size=8.2, indent=0.1)
    p.para(
        f"with g = {C.G} m/s\u00b2, R_air = {C.R_AIR} J/(kg\u00b7K), "
        f"V_ci = {C.TURBINE.cut_in_speed:g} m/s, V_rated = {C.TURBINE.rated_speed:g} m/s, "
        f"V_co = {C.TURBINE.cut_out_speed:g} m/s, P_r = {C.TURBINE.rated_power_mw:g} MW. "
        f"The 2 m temperature is used as a proxy for the 100 m hub-height temperature and "
        f"surface pressure is hydrostatically extrapolated to hub height; both are "
        f"approximations, and the resulting density is a derived estimate rather than a "
        f"measurement. The nominal pair Cp = {C.CP_NOMINAL}, \u03b7 = {C.ETA_NOMINAL} "
        f"reproduces {cal['ratio_raw_over_rated_at_vrated']:.4f} times rated power at "
        f"V_rated with \u03c1 = {C.NOMINAL_RHO} kg/m\u00b3, i.e. rated power is reached "
        f"at the rated wind speed by construction. Cp = {C.CP_NOMINAL} is "
        f"{cal['cp_fraction_of_betz']*100:.1f}% of the Betz limit "
        f"({C.BETZ_LIMIT:.4f}). This is a simplified model, not an OEM-certified power "
        f"curve: Cp and \u03b7 are constant per scenario, and pitch control, tip-speed "
        f"ratio, turbulence, icing, and losses are not represented."
    )

    p.heading("4. Probability distributions and assumptions")
    p.bullet(
        f"Wind speed: empirical distribution of the {ctx['n_records']:,}-hour ERA5 series, "
        f"resampled chronologically. A Weibull fit (k = {w['shape_k']:.3f}, "
        f"c = {w['scale_c']:.3f} m/s) is reported for description only (KS = "
        f"{w['ks_statistic']:.4f}, p = {w['ks_p_value']:.3g}); it does not capture "
        f"seasonality or autocorrelation and is not used to generate the main simulation."
    )
    p.bullet("Air density: derived hour by hour from the historical temperature and "
             "pressure series, not held constant.")
    p.bullet(f"Power coefficient: Cp ~ TruncatedNormal(\u03bc = {C.CP_NOMINAL}, "
             f"\u03c3 = {C.CP_SD}), bounded to [{C.CP_BOUNDS[0]:.2f}, {C.CP_BOUNDS[1]:.2f}].")
    p.bullet(f"System efficiency: \u03b7 ~ TruncatedNormal(\u03bc = {C.ETA_NOMINAL}, "
             f"\u03c3 = {C.ETA_SD}), bounded to [{C.ETA_BOUNDS[0]:.2f}, {C.ETA_BOUNDS[1]:.2f}].")
    p.bullet("These turbine distributions are engineering assumptions, not manufacturer "
             "uncertainty data; their influence is tested in the sensitivity analysis.")

    p.heading("5. Monte Carlo methodology")
    p.para(
        f"We use a seasonally stratified block bootstrap. The historical series is split "
        f"by calendar month; within each month, contiguous {C.BLOCK_HOURS}-hour (7-day) "
        f"blocks that lie inside one year are resampled with replacement to build a "
        f"synthetic {C.N_HOURS_YEAR:,}-hour year (February 29 excluded so every scenario "
        f"has exactly 8,760 h). Within-block chronology is preserved, so short-term "
        f"dependence survives, but dependence is broken at block joins and across months. "
        f"Each scenario draws Cp and \u03b7 once (turbine-level design parameters), "
        f"computes hourly power, and integrates AEP = \u03a3_t P_t \u0394t with "
        f"\u0394t = 1 h, then CF = AEP / (P_r \u00b7 8,760). We ran "
        f"{s['n_scenarios']:,} scenarios with seed {s['seed']}."
    )
    p.para(
        "The low-capacity-factor event CF < 0.25 is an energy-adequacy indicator for this "
        "hypothetical turbine. It is not a probability of mechanical failure.",
        size=7.8, color=GREY
    )
    p.finish(pdf)


# --------------------------------------------------------------------------
# Page 2
# --------------------------------------------------------------------------
def _page_two(pdf: PdfPages, ctx: dict, preview_dir: Path | None = None):
    p = Page(pdf, preview_dir=preview_dir)
    s = ctx["summary"]
    a = s["aep_mwh"]
    c = s["capacity_factor"]
    pr = s["probability_cf_below_threshold"]
    pw = s["expected_power_output_mw"]
    b = ctx["baseline_summary"]

    p.heading("6. Testing and validation")
    p.para(
        f"Automated tests cover the physical model and simulation pipeline: swept area, "
        f"air density positivity, zero power below cut-in and at/above cut-out, "
        f"non-negative power never exceeding rated power, Cp and efficiency bounds, "
        f"CF in [0, 1], non-negative AEP, correct annual hour counts, and reproducibility "
        f"under a fixed seed. All {ctx['n_tests']} tests pass "
        f"(`python -m pytest -q`). Convergence uses nested prefixes (100, 1,000, "
        f"5,000, 10,000 scenarios); mean AEP standard error at "
        f"{s['n_scenarios']:,} scenarios is {a['mc_standard_error']:.1f} MWh."
    )

    p.heading("7. Main results")
    rows = [
        ("Mean AEP", f"{_fmt(a['mean'])} MWh"),
        ("Median AEP", f"{_fmt(a['median'])} MWh"),
        ("SD of AEP", f"{_fmt(a['std'])} MWh"),
        ("5th / 25th percentile", f"{_fmt(a['p05'])} / {_fmt(a['p25'])} MWh"),
        ("75th / 95th percentile", f"{_fmt(a['p75'])} / {_fmt(a['p95'])} MWh"),
        ("Mean capacity factor", f"{c['mean']:.4f}  (SD {c['std']:.4f})"),
        ("5th / 95th percentile CF", f"{c['p05']:.4f} / {c['p95']:.4f}"),
        ("Expected power output", f"{pw['mean']:.3f} MW"),
        ("P(CF < 0.25)", f"{pr['estimate']:.4f}  (95% CI {pr['wilson_ci95'][0]:.4f} - {pr['wilson_ci95'][1]:.4f})"),
        ("Deterministic mean AEP (2015-2024)", f"{_fmt(b['aep_mwh_mean'])} MWh"),
        ("Deterministic CF range", f"{b['capacity_factor_min']:.4f} - {b['capacity_factor_max']:.4f}"),
    ]
    p.para("Statistic | Value", size=7.6, color=GREY, space_before=1)
    for k, v in rows:
        p.para(f"{k}: {v}", size=7.9, leading=1.22, space_before=0.6, indent=0.08)

    p.heading("Sensitivity analysis")
    sp = ctx["spearman"]
    top = sp[sp["output"] == "aep_mwh"].assign(a=lambda d: d["spearman_rho"].abs()).sort_values("a", ascending=False)
    lead = ", ".join(f"{r.input} ({r.spearman_rho:+.2f})" for r in top.head(3).itertuples())
    sob = ctx["sobol"]
    top_st = sorted(zip(sob["parameters"], sob["st"]), key=lambda t: -t[1])[:2]
    p.para(
        f"Spearman rank correlations with AEP are strongest for {lead}. In the separate "
        f"independent-input Sobol experiment ({sob['n_model_evaluations']:,} model "
        f"evaluations), the largest total-order indices are "
        + ", ".join(f"{n} (ST = {v:.3f})" for n, v in top_st) +
        ". Correlation is not causation, and the Sobol experiment deliberately removes "
        "temporal dependence, so it ranks parameter importance under independence rather "
        "than in the historical-weather simulation."
    )

    p.heading("8. Uncertainty and limitations")
    p.bullet("Reported intervals are Monte Carlo sampling uncertainty across simulated "
             "annual scenarios; they do not include structural model error.")
    p.bullet("Evaluated with only ten years of reanalysis: interannual variability is "
             "sampled from a short record, and block joins break dependence.")
    p.bullet("The simplified power curve (constant Cp and \u03b7, no control or losses) "
             "and the 2 m temperature / surface-pressure approximations bias the "
             "absolute AEP; the probabilistic conclusions are more robust than the "
             "absolute values.")
    p.bullet("A different Cp calibration, a real manufacturer power curve, or a "
             "longer record could change the AEP mean and the P(CF < 0.25) estimate.")

    p.heading("9. AI usage disclosure")
    p.para(
        "An AI coding agent (OpenCode) generated and executed the data-acquisition, "
        "simulation, statistics, sensitivity, figure, and report code, and drafted this "
        "writeup. The human researcher selected the research question, approved the "
        "turbine specifications and probability model, and is responsible for verifying "
        "all assumptions, numerical results, and claims. Full disclosure is in "
        "AI_USAGE.md and AI-NOTES.md in the repository.", size=7.6
    )

    p.heading("10. Sources")
    p.para(
        "Open-Meteo. Historical Weather API (ERA5 reanalysis). "
        "https://open-meteo.com/en/docs/historical-weather-api (accessed "
        f"{ctx['analysis_date']}). ECMWF/Copernicus ERA5 reanalysis via Open-Meteo, "
        "CC BY 4.0 attribution. Manwell, J.F., McGowan, J.G., Rogers, A.L. (2009). "
        "Wind Energy Explained, 2nd ed., Wiley. IEC 61400-1 (wind turbine generator "
        "systems). Kassis, T., Agarwal, V., He, Y., Patel, D., Brueckner, A.M. (2026). "
        "Scientific Agent Skills. arXiv:2609.00065.", size=7.0
    )

    if ctx.get("fig_aep") and ctx.get("fig_cf"):
        p.heading("Figures")
        p.image(Path(ctx["fig_aep"]), width_in=3.0,
                caption="Figure 1. Simulated distribution of annual energy production "
                        f"({s['n_scenarios']:,} scenarios) with the deterministic mean "
                        f"({_fmt(b['aep_mwh_mean'])} MWh).")
        p.image(Path(ctx["fig_cf"]), width_in=3.0,
                caption=f"Figure 2. Simulated distribution of annual capacity factor with "
                        f"the P(CF < {pr['threshold']:.2f}) threshold.")
    p.finish(pdf)


# --------------------------------------------------------------------------
# Public API
# --------------------------------------------------------------------------
def build_pdf(ctx: dict, path: Path = C.REPORT_DIR / "final_report.pdf",
              preview_dir: Path | None = None) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    Page._counter = 0
    with PdfPages(path) as pdf:
        _page_one(pdf, ctx, preview_dir=preview_dir)
        _page_two(pdf, ctx, preview_dir=preview_dir)
    return path


def build_markdown(ctx: dict, path: Path = C.REPORT_DIR / "final_report.md") -> Path:
    s = ctx["summary"]
    a, c, pr, pw = s["aep_mwh"], s["capacity_factor"], s["probability_cf_below_threshold"], s["expected_power_output_mw"]
    b = ctx["baseline_summary"]
    w = ctx["weibull"]

    lines = [
        "# Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation",
        "",
        "*A probabilistic assessment of power generation, annual energy production, and "
        "energy adequacy. Stanford PAI final project.*",
        "",
        "## 1. Research question and motivation",
        "",
        "How do uncertainties in wind speed, air density, and turbine operating parameters "
        "affect power output, annual energy production (AEP), and energy adequacy of a 2 MW "
        "wind turbine? A deterministic calculation returns a single AEP and hides wind "
        "variability and parameter uncertainty. We quantify the full predictive distribution "
        "with a Monte Carlo simulation driven by ten years of hourly reanalysis data.",
        "",
        "## 2. Data source and collection method",
        "",
        f"- Source: Open-Meteo Historical Weather API (ERA5 reanalysis), endpoint "
        f"`{C.API_ENDPOINT}`",
        f"- Site: {C.SITE_NAME}, latitude {C.LATITUDE}, longitude {C.LONGITUDE}",
        f"- Period: {C.START_DATE} to {C.END_DATE}, hourly, {C.TIMEZONE}, model "
        f"`{C.MODEL}`, cell selection `{C.CELL_SELECTION}`",
        f"- Variables: {', '.join(C.VARIABLES)}",
        f"- Retrieved records: {ctx['n_records']:,}; completeness "
        f"{ctx['completeness']:.4f}%; duplicates {ctx['n_duplicates']}; missing "
        f"timestamps {ctx['n_missing']}",
        "- No values imputed, interpolated, or removed. Raw and processed data are stored "
        "separately, with a provenance record of exact request URLs and retrieval metadata.",
        "- Limitation: ERA5 is gridded reanalysis, not an on-site turbine measurement.",
        "",
        "## 3. Mathematical model",
        "",
        "```",
        "A     = pi R^2",
        "T_K   = T_C + 273.15",
        "p_s   = 100 p_hPa",
        "p_h   = p_s exp(-g H_h / (R_air T_K))",
        "rho   = p_h / (R_air T_K)",
        "P_raw = 0.5 rho A V^3 Cp eta",
        "P     = 0                    V < V_ci",
        "P     = min(P_r, P_raw)      V_ci <= V < V_co",
        "P     = 0                    V >= V_co",
        "AEP   = sum_t P_t * 1 h",
        "CF    = AEP / (P_r * 8760)",
        "```",
        "",
        f"R = 45 m (A = {ctx['calibration']['swept_area_m2']:,.1f} m^2), V_ci = 3 m/s, "
        f"V_rated = 11.5 m/s, V_co = 25 m/s, P_r = 2 MW, g = {C.G} m/s^2, "
        f"R_air = {C.R_AIR} J/(kg K).",
        "",
        f"Calibration: Cp = {C.CP_NOMINAL}, eta = {C.ETA_NOMINAL}, "
        f"rho = {C.NOMINAL_RHO} kg/m^3 gives {ctx['calibration']['ratio_raw_over_rated_at_vrated']:.4f} "
        "times rated power at V_rated (rated power reached at the rated wind speed by "
        "construction). Cp is "
        f"{ctx['calibration']['cp_fraction_of_betz']*100:.1f}% of the Betz limit "
        f"({C.BETZ_LIMIT:.4f}). Not an OEM-certified power curve.",
        "",
        "## 4. Probability distributions and assumptions",
        "",
        f"- Wind: empirical distribution of {ctx['n_records']:,}-hour ERA5 series, "
        "resampled chronologically in 7-day blocks within calendar month.",
        f"- Weibull descriptive fit: k = {w['shape_k']:.3f}, c = {w['scale_c']:.3f} m/s, "
        f"KS = {w['ks_statistic']:.4f} (p = {w['ks_p_value']:.3g}); not used for generation.",
        "- Air density: derived hourly from historical temperature and pressure.",
        f"- Cp ~ TruncatedNormal(mu = {C.CP_NOMINAL}, sigma = {C.CP_SD}), bounds "
        f"[{C.CP_BOUNDS[0]}, {C.CP_BOUNDS[1]}]; sampled once per scenario.",
        f"- eta ~ TruncatedNormal(mu = {C.ETA_NOMINAL}, sigma = {C.ETA_SD}), bounds "
        f"[{C.ETA_BOUNDS[0]}, {C.ETA_BOUNDS[1]}]; sampled once per scenario.",
        "- These turbine distributions are engineering assumptions, not manufacturer data.",
        "",
        "## 5. Monte Carlo methodology",
        "",
        f"- Seasonally stratified block bootstrap; blocks of {C.BLOCK_HOURS} h, month "
        "strata, February 29 excluded.",
        f"- {s['n_scenarios']:,} scenarios, seed {s['seed']}, "
        f"{ctx['n_records']:,}-hour source record.",
        "- Per scenario: resample weather, draw Cp and eta, derive air density, compute "
        "hourly power, integrate AEP and CF.",
        "",
        "## 6. Testing and validation",
        "",
        f"- {ctx['n_tests']} automated tests pass (`python -m pytest -q`), covering the "
        "physical model, boundary conditions, bounds, and reproducibility.",
        f"- Convergence checked at 100 / 1,000 / 5,000 / 10,000 scenarios (nested "
        f"prefixes); MC standard error of the mean AEP at {s['n_scenarios']:,} is "
        f"{a['mc_standard_error']:.1f} MWh.",
        "",
        "## 7. Main results",
        "",
        "| Statistic | Value |",
        "|---|---:|",
        f"| Mean AEP | {a['mean']:,.1f} MWh |",
        f"| Median AEP | {a['median']:,.1f} MWh |",
        f"| SD of AEP | {a['std']:,.1f} MWh |",
        f"| 5th / 25th percentile AEP | {a['p05']:,.1f} / {a['p25']:,.1f} MWh |",
        f"| 75th / 95th percentile AEP | {a['p75']:,.1f} / {a['p95']:,.1f} MWh |",
        f"| Mean capacity factor | {c['mean']:.4f} (SD {c['std']:.4f}) |",
        f"| 5th / 95th percentile CF | {c['p05']:.4f} / {c['p95']:.4f} |",
        f"| Expected power output | {pw['mean']:.3f} MW |",
        f"| P(CF < 0.25) | {pr['estimate']:.4f} (95% Wilson CI {pr['wilson_ci95'][0]:.4f} - {pr['wilson_ci95'][1]:.4f}) |",
        f"| Deterministic mean AEP (2015-2024) | {b['aep_mwh_mean']:,.1f} MWh |",
        "",
        "## 8. Sensitivity analysis",
        "",
        "| Input | Output | Spearman rho |",
        "|---|---|---:|",
    ]
    for r in ctx["spearman"].itertuples():
        lines.append(f"| {r.input} | {r.output} | {r.spearman_rho:+.3f} |")
    lines += [
        "",
        "| Sobol parameter | S1 | ST |",
        "|---|---:|---:|",
    ]
    for n, s1, st in zip(ctx["sobol"]["parameters"], ctx["sobol"]["s1"], ctx["sobol"]["st"]):
        lines.append(f"| {n} | {s1:.3f} | {st:.3f} |")
    lines += [
        "",
        "## 9. Uncertainty and limitations",
        "",
        "- Reported intervals are Monte Carlo sampling uncertainty; they exclude structural "
        "model error.",
        "- Only ten years of reanalysis: interannual variability is sampled from a short "
        "record; block joins break dependence.",
        "- The simplified power curve and the 2 m temperature / surface-pressure "
        "approximations bias the absolute AEP; probabilistic conclusions are more robust "
        "than absolute values.",
        "- A different Cp calibration, a real manufacturer power curve, or a longer record "
        "could change the AEP mean and P(CF < 0.25).",
        "",
        "## 10. AI usage disclosure",
        "",
        "An AI coding agent generated and executed the analysis code and drafted this "
        "report; the human researcher selected the research question, approved the turbine "
        "specifications and probability model, and is responsible for verifying all "
        "assumptions, numerical results, and claims. See AI_USAGE.md and AI-NOTES.md.",
        "",
        "## 11. Sources",
        "",
        "- Open-Meteo. Historical Weather API (ERA5 reanalysis). "
        "https://open-meteo.com/en/docs/historical-weather-api",
        "- ECMWF/Copernicus Climate Change Service. ERA5 reanalysis (via Open-Meteo).",
        "- Manwell, J.F., McGowan, J.G., Rogers, A.L. (2009). Wind Energy Explained, 2nd ed., Wiley.",
        "- IEC 61400-1, Wind turbine generator systems.",
        "- Kassis, T., Agarwal, V., He, Y., Patel, D., Brueckner, A.M. (2026). Scientific "
        "Agent Skills. arXiv:2609.00065.",
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    return path