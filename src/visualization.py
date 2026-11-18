"""Publication-quality figures for the wind-turbine uncertainty study.

Every figure is generated from computed results (never from illustrative
numbers), carries a title, axis labels with units, and a legend where more than
one series is shown.  A consistent style is applied through a single rcParams
block so that all panels look like one figure set.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import rcParams

from . import config as C

# --------------------------------------------------------------------------
# Style
# --------------------------------------------------------------------------
INK = "#1a1a1a"
C_MAIN = "#0072B2"      # blue
C_ACCENT = "#D55E00"    # vermillion
C_FILL = "#56B4E9"      # sky blue
C_GREEN = "#009E73"
C_GREY = "#6E6E6E"
C_RED = "#C0392B"

rcParams.update(
    {
        "figure.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": INK,
        "axes.labelcolor": INK,
        "axes.titleweight": "bold",
        "axes.titlesize": 12,
        "axes.labelsize": 10,
        "axes.grid": True,
        "grid.color": "#D9D9D9",
        "grid.linewidth": 0.6,
        "legend.frameon": False,
        "legend.fontsize": 9,
        "xtick.labelsize": 9,
        "ytick.labelsize": 9,
        "xtick.color": INK,
        "ytick.color": INK,
        "text.color": INK,
        "font.family": "DejaVu Sans",
        "savefig.dpi": 200,
        "savefig.bbox": "standard",
        "figure.autolayout": False,
    }
)


def _audit_text_bounds(fig, name: str) -> list[str]:
    """Flag text artists that fall outside the figure canvas.

    This is a programmatic proxy for visual inspection: it catches clipped titles,
    axis labels, tick labels, and legends that extend past the figure edge.
    """
    fig.canvas.draw()
    renderer = fig.canvas.get_renderer()
    width, height = fig.canvas.get_width_height()
    problems: list[str] = []
    for ax in fig.axes:
        objs = list(ax.texts) + [ax.title, ax.xaxis.label, ax.yaxis.label]
        objs += list(ax.get_xticklabels()) + list(ax.get_yticklabels())
        legend = ax.get_legend()
        if legend is not None:
            objs += list(legend.get_texts())
        for t in objs:
            if not t.get_text().strip():
                continue
            bb = t.get_window_extent(renderer=renderer)
            if bb.x0 < -1 or bb.y0 < -1 or bb.x1 > width + 1 or bb.y1 > height + 1:
                problems.append(
                    f"{name}: clipped text {t.get_text()[:38]!r} "
                    f"bbox=({bb.x0:.0f},{bb.y0:.0f},{bb.x1:.0f},{bb.y1:.0f}) "
                    f"canvas=({width},{height})"
                )
    return problems


def _save(fig, path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    for problem in _audit_text_bounds(fig, path.name):
        print(f"      WARNING {problem}")
    fig.savefig(path)
    plt.close(fig)
    return path


def _footer(fig, text: str) -> None:
    fig.text(0.01, 0.005, text, fontsize=6.5, color=C_GREY, ha="left", va="bottom")


# --------------------------------------------------------------------------
# 1. Historical wind-speed time series
# --------------------------------------------------------------------------
def plot_wind_timeseries(df: pd.DataFrame, path: Path) -> Path:
    daily = df.set_index("time")["wind_speed_100m"].resample("D").mean()
    slice_ = df.set_index("time")["wind_speed_100m"].loc["2022-01-01":"2022-01-30"]

    fig, (ax1, ax2) = plt.subplots(
        2, 1, figsize=(10, 6.2), sharex=False,
        gridspec_kw={"height_ratios": [1.15, 1.0], "hspace": 0.55},
    )

    ax1.plot(daily.index, daily.to_numpy(), color=C_MAIN, linewidth=0.7)
    ax1.set_title("Daily-mean wind speed at 100 m, Cuxhaven (ERA5), 2015-2024")
    ax1.set_xlabel("Date (UTC)")
    ax1.set_ylabel("Wind speed (m/s)")
    ax1.axhline(C.TURBINE.rated_speed, color=C_ACCENT, linestyle="--", linewidth=1.0,
                label=f"Rated wind speed ({C.TURBINE.rated_speed} m/s)")
    ax1.legend(loc="upper right", ncol=1)
    ax1.set_xlim(daily.index[0], daily.index[-1])

    ax2.plot(slice_.index, slice_.to_numpy(), color=C_MAIN, linewidth=0.9, drawstyle="default")
    ax2.axhline(C.TURBINE.cut_in_speed, color=C_GREEN, linestyle=":", linewidth=1.0,
                label=f"Cut-in ({C.TURBINE.cut_in_speed} m/s)")
    ax2.axhline(C.TURBINE.rated_speed, color=C_ACCENT, linestyle="--", linewidth=1.0,
                label=f"Rated ({C.TURBINE.rated_speed} m/s)")
    ax2.set_title("January 2022, hourly resolution (example month)")
    ax2.set_xlabel("Date (UTC)")
    ax2.set_ylabel("Wind speed (m/s)")
    ax2.legend(loc="upper right", ncol=2)

    _footer(fig, "Source: Open-Meteo Historical Weather API (ERA5 reanalysis). Regional grid-cell estimate, not on-site measurement.")
    fig.subplots_adjust(left=0.085, right=0.972, top=0.90, bottom=0.12)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 2. Wind-speed histogram
# --------------------------------------------------------------------------
def plot_wind_histogram(df: pd.DataFrame, path: Path) -> Path:
    v = df["wind_speed_100m"].to_numpy(float)
    fig, ax = plt.subplots(figsize=(8, 5.2))
    ax.hist(v, bins=np.arange(0, v.max() + 0.5, 0.5), color=C_FILL,
            edgecolor="white", linewidth=0.4, density=True, label="Hourly ERA5 wind speed")
    mean = float(np.mean(v))
    median = float(np.median(v))
    ax.axvline(mean, color=C_ACCENT, linestyle="-", linewidth=1.6, label=f"Mean = {mean:.2f} m/s")
    ax.axvline(median, color=C_GREEN, linestyle="--", linewidth=1.6, label=f"Median = {median:.2f} m/s")
    ax.set_title("Distribution of hourly wind speed at 100 m, 2015-2024")
    ax.set_xlabel("Wind speed (m/s)")
    ax.set_ylabel("Probability density (s/m)")
    ax.set_xlim(0, v.max() + 0.5)
    ax.legend()
    _footer(fig, f"n = {v.size:,} hourly records (Feb 29 excluded only where noted). ERA5 reanalysis.")
    fig.subplots_adjust(left=0.10, right=0.97, top=0.92, bottom=0.14)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 3. Monthly climatology
# --------------------------------------------------------------------------
def plot_monthly_climatology(df: pd.DataFrame, path: Path) -> Path:
    g = df.groupby("month")["wind_speed_100m"]
    mean = g.mean()
    q25 = g.quantile(0.25)
    q75 = g.quantile(0.75)
    months = [C.MONTH_NAMES[m][:3] for m in mean.index]

    fig, ax = plt.subplots(figsize=(9, 5.2))
    x = np.arange(len(mean))
    ax.fill_between(x, q25, q75, color=C_FILL, alpha=0.45, label="Interquartile range")
    ax.plot(x, mean, color=C_MAIN, marker="o", markersize=4.5, linewidth=1.8, label="Monthly mean")
    ax.axhline(df["wind_speed_100m"].mean(), color=C_GREY, linestyle="--", linewidth=1.0,
               label=f"Overall mean = {df['wind_speed_100m'].mean():.2f} m/s")
    ax.set_xticks(x)
    ax.set_xticklabels(months)
    ax.set_title("Monthly wind-speed climatology at 100 m (2015-2024)")
    ax.set_xlabel("Month (UTC)")
    ax.set_ylabel("Wind speed (m/s)")
    ax.legend(loc="upper left", ncol=2)
    fig.subplots_adjust(left=0.10, right=0.962, top=0.895, bottom=0.145)
    _save(fig, path)
    return path


# --------------------------------------------------------------------------
# 4. Seasonal distributions
# --------------------------------------------------------------------------
def plot_seasonal_distributions(df: pd.DataFrame, path: Path) -> Path:
    seasons = list(C.SEASONS.keys())
    data = [df.loc[df["season"] == s, "wind_speed_100m"].to_numpy(float) for s in seasons]

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10.5, 5.0),
                                   gridspec_kw={"width_ratios": [1, 1.25], "wspace": 0.35})
    bp = ax1.boxplot(data, patch_artist=True, widths=0.55, showfliers=False,
                     medianprops={"color": INK, "linewidth": 1.4})
    for patch, col in zip(bp["boxes"], [C_MAIN, C_GREEN, C_ACCENT, C_GREY]):
        patch.set_facecolor(col)
        patch.set_alpha(0.55)
        patch.set_edgecolor(INK)
    ax1.set_xticks(range(1, len(seasons) + 1))
    ax1.set_xticklabels(seasons)
    ax1.set_title("Seasonal wind-speed distributions")
    ax1.set_xlabel("Season")
    ax1.set_ylabel("Wind speed (m/s)")
    ax1.set_ylabel("Wind speed (m/s)")

    for s, d, col in zip(seasons, data, [C_MAIN, C_GREEN, C_ACCENT, C_GREY]):
        ax2.hist(d, bins=np.arange(0, 16, 0.5), density=True, histtype="step",
                 linewidth=1.8, color=col, label=f"{s} (mean {d.mean():.2f} m/s)")
    ax2.set_title("Seasonal density overlay")
    ax2.set_xlabel("Wind speed (m/s)")
    ax2.set_ylabel("Probability density (s/m)")
    ax2.legend(fontsize=8)
    _footer(fig, "ERA5 reanalysis, 2015-2024. Seasons: DJF, MAM, JJA, SON (meteorological).")
    fig.subplots_adjust(left=0.085, right=0.952, top=0.875, bottom=0.15)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 5. Empirical vs Weibull
# --------------------------------------------------------------------------
def plot_empirical_vs_weibull(df: pd.DataFrame, weibull: dict, path: Path) -> Path:
    from scipy import stats

    v = df["wind_speed_100m"].to_numpy(float)
    k, c = weibull["shape_k"], weibull["scale_c"]
    xs = np.linspace(0.01, max(16.0, v.max()), 500)

    fig, ax = plt.subplots(figsize=(8.6, 5.3))
    ax.hist(v, bins=np.arange(0, 16, 0.5), density=True, color=C_FILL, alpha=0.75,
            edgecolor="white", linewidth=0.4, label="Empirical histogram")
    ax.plot(xs, stats.weibull_min.pdf(xs, k, scale=c), color=C_ACCENT, linewidth=2.2,
            label=f"Weibull fit (k = {k:.2f}, c = {c:.2f} m/s)")
    ax.set_title("Empirical wind-speed distribution vs fitted Weibull")
    ax.set_xlabel("Wind speed (m/s)")
    ax.set_ylabel("Probability density (s/m)")
    ax.set_xlim(0, 16)
    ax.legend()
    ax.text(
        0.97, 0.72,
        f"KS statistic = {weibull['ks_statistic']:.4f}\nKS p-value = {weibull['ks_p_value']:.3g}",
        transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
        bbox={"boxstyle": "round,pad=0.3", "facecolor": "white", "edgecolor": "#CCCCCC"},
    )
    _footer(fig, "Weibull fitted by maximum likelihood with the location fixed at zero; descriptive only.")
    fig.subplots_adjust(left=0.105, right=0.962, top=0.885, bottom=0.15)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 6. Power curve
# --------------------------------------------------------------------------
def plot_power_curve(path: Path, mean_rho: float | None = None) -> Path:
    from .turbine_model import power_curve

    v = np.linspace(0, 30, 1200)
    p_nom = power_curve(v, C.NOMINAL_RHO, C.CP_NOMINAL, C.ETA_NOMINAL)
    rho_used = C.NOMINAL_RHO if mean_rho is None else float(mean_rho)
    p_rho = power_curve(v, rho_used, C.CP_NOMINAL, C.ETA_NOMINAL)

    fig, ax = plt.subplots(figsize=(8.8, 5.3))
    ax.plot(v, p_nom, color=C_MAIN, linewidth=2.2,
            label=f"Simplified model, Cp = {C.CP_NOMINAL}, eta = {C.ETA_NOMINAL}, rho = {C.NOMINAL_RHO} kg/m$^3$")
    if mean_rho is not None:
        ax.plot(v, p_rho, color=C_ACCENT, linewidth=1.4, linestyle="--",
                label=f"Same Cp/eta at simulated mean rho = {rho_used:.3f} kg/m$^3$")
    ax.axhline(C.TURBINE.rated_power_mw, color=C_GREY, linestyle=":", linewidth=1.0)
    for x, lab, col in [
        (C.TURBINE.cut_in_speed, f"Cut-in {C.TURBINE.cut_in_speed:g} m/s", C_GREEN),
        (C.TURBINE.rated_speed, f"Rated {C.TURBINE.rated_speed:g} m/s", C_ACCENT),
        (C.TURBINE.cut_out_speed, f"Cut-out {C.TURBINE.cut_out_speed:g} m/s", C_RED),
    ]:
        ax.axvline(x, color=col, linestyle="--", linewidth=1.0)
        ax.text(x, C.TURBINE.rated_power_mw * 1.03, lab, rotation=90, fontsize=8,
                color=col, ha="right", va="bottom")
    ax.set_title("Simplified turbine power curve (2 MW hypothetical turbine)")
    ax.set_xlabel("Hub-height wind speed (m/s)")
    ax.set_ylabel("Electrical power (MW)")
    ax.set_xlim(0, 30)
    ax.set_ylim(0, C.TURBINE.rated_power_mw * 1.20)
    ax.legend(loc="lower right")
    _footer(fig, "Not an OEM-certified power curve. Constant Cp and eta; no pitch control, turbulence, icing, or losses.")
    fig.subplots_adjust(left=0.10, right=0.958, top=0.875, bottom=0.15)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 7. Simulated hourly power distribution
# --------------------------------------------------------------------------
def plot_mc_power_distribution(result, path: Path) -> Path:
    counts = np.asarray(result.power_histogram, dtype=float)
    edges = np.asarray(result.power_bins, dtype=float)
    total = counts.sum()
    width = np.diff(edges)
    density = counts / (total * width)

    fig, ax = plt.subplots(figsize=(8.8, 5.3))
    centres = 0.5 * (edges[:-1] + edges[1:])
    ax.bar(centres, density, width=width * 0.95, color=C_FILL, edgecolor="white",
           linewidth=0.3, label="Simulated hourly power (all scenarios)")
    mean_p = float(np.mean(result.mean_power_mw))
    ax.axvline(mean_p, color=C_ACCENT, linewidth=1.8,
               label=f"Expected power output = {mean_p:.0f} MW")
    ax.axvline(C.TURBINE.rated_power_mw, color=C_GREY, linestyle=":", linewidth=1.2,
               label=f"Rated power = {C.TURBINE.rated_power_mw:g} MW")
    ax.set_title("Distribution of simulated hourly electrical power")
    ax.set_xlabel("Electrical power (MW)")
    ax.set_ylabel("Probability density (1/MW)")
    ax.set_xlim(0, C.TURBINE.rated_power_mw * 1.05)
    ax.legend()
    _footer(fig, f"Histogram accumulated over {result.n_scenarios:,} simulated years "
                 f"({result.n_scenarios * C.N_HOURS_YEAR:,} hourly values), seed {result.seed}.")
    fig.subplots_adjust(left=0.105, right=0.945, top=0.885, bottom=0.15)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 8. AEP distribution
# --------------------------------------------------------------------------
def plot_aep_distribution(result, summary: dict, baseline: pd.DataFrame, path: Path) -> Path:
    aep = np.asarray(result.aep_mwh, dtype=float)
    s = summary["aep_mwh"]

    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.hist(aep, bins=60, color=C_FILL, edgecolor="white", linewidth=0.4, density=True,
            label="Simulated annual energy production")
    for q, lab, col, ls in [
        (s["p05"], f"5th pct = {s['p05']:,.0f} MWh", C_ACCENT, "--"),
        (s["median"], f"Median = {s['median']:,.0f} MWh", INK, "-"),
        (s["p95"], f"95th pct = {s['p95']:,.0f} MWh", C_ACCENT, "--"),
    ]:
        ax.axvline(q, color=col, linestyle=ls, linewidth=1.5, label=lab)
    det_mean = float(baseline["aep_mwh"].mean())
    ax.axvline(det_mean, color=C_GREEN, linewidth=2.0,
               label=f"Deterministic mean (2015-2024) = {det_mean:,.0f} MWh")
    ax.set_title("Monte Carlo distribution of annual energy production")
    ax.set_xlabel("Annual energy production (MWh)")
    ax.set_ylabel("Probability density (1/MWh)")
    ax.legend(fontsize=8.5, loc="upper right")
    _footer(fig, f"{summary['n_scenarios']:,} scenarios, seasonal block bootstrap, seed {summary['seed']}.")
    fig.subplots_adjust(left=0.105, right=0.942, top=0.878, bottom=0.15)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 9. Capacity-factor distribution
# --------------------------------------------------------------------------
def plot_cf_distribution(result, summary: dict, path: Path) -> Path:
    cf = np.asarray(result.cf, dtype=float)
    c = summary["capacity_factor"]
    p = summary["probability_cf_below_threshold"]
    thresh = p["threshold"]

    fig, ax = plt.subplots(figsize=(9.2, 5.4))
    ax.hist(cf, bins=60, color=C_FILL, edgecolor="white", linewidth=0.4,
            label="Simulated annual capacity factor")
    ax.axvline(thresh, color=C_RED, linewidth=2.2,
               label=f"Low-CF threshold = {thresh:.2f}")
    ax.axvline(c["mean"], color=INK, linewidth=1.6,
               label=f"Mean CF = {c['mean']:.3f}")
    ax.axvspan(0, thresh, color=C_RED, alpha=0.10,
               label=f"P(CF < {thresh:.2f}) = {p['estimate']:.4f}")
    ax.set_title("Distribution of annual capacity factor")
    ax.set_xlabel("Annual capacity factor (dimensionless)")
    ax.set_ylabel("Probability density")
    ax.legend(fontsize=8.5, loc="upper right")
    _footer(fig, f"Blue shaded region = energy-adequacy indicator only; not a mechanical failure probability. Seed {summary['seed']}.")
    fig.subplots_adjust(left=0.155, right=0.955, top=0.885, bottom=0.15)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 10. Sensitivity
# --------------------------------------------------------------------------
def plot_sensitivity(spearman: pd.DataFrame, sobol: dict, oat: pd.DataFrame, path: Path) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12.2, 5.2),
                                   gridspec_kw={"width_ratios": [1.25, 1.0], "wspace": 0.42})

    sp = spearman[spearman["output"] == "aep_mwh"].copy()
    sp["absrho"] = sp["spearman_rho"].abs()
    sp = sp.sort_values("absrho")
    ax1.barh(sp["input"], sp["spearman_rho"],
             color=[C_MAIN if v >= 0 else C_ACCENT for v in sp["spearman_rho"]],
             edgecolor=INK, linewidth=0.5)
    ax1.axvline(0, color=INK, linewidth=0.8)
    ax1.set_title("Spearman rank correlation with AEP")
    ax1.set_xlabel("Spearman rho")
    for y, (v) in enumerate(sp["spearman_rho"]):
        ax1.text(v + (0.02 if v >= 0 else -0.02), y, f"{v:.2f}",
                 va="center", ha="left" if v >= 0 else "right", fontsize=8)

    names = sobol["parameters"]
    y = np.arange(len(names))
    ax2.barh(y - 0.19, sobol["s1"], height=0.36, color=C_FILL, edgecolor=INK,
             linewidth=0.5, label="S1 (first order)")
    ax2.barh(y + 0.19, sobol["st"], height=0.36, color=C_ACCENT, edgecolor=INK,
             linewidth=0.5, xerr=sobol["st_conf"], ecolor=INK, capsize=2.5,
             label="ST (total order, 95% CI)")
    ax2.set_yticks(y)
    ax2.set_yticklabels(names)
    ax2.invert_yaxis()
    ax2.set_xlabel("Sobol index")
    ax2.set_title("Sobol indices (independent inputs)")
    ax2.legend(fontsize=8, loc="lower right")
    _footer(fig, "Left: main historical-weather simulation (dependent inputs). Right: separate independent-input experiment.")
    fig.subplots_adjust(left=0.17, right=0.92, top=0.90, bottom=0.13)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 11. Convergence
# --------------------------------------------------------------------------
def plot_convergence(conv: pd.DataFrame, summary: dict, path: Path) -> Path:
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(11.5, 5.0), gridspec_kw={"wspace": 0.32})

    ax1.plot(conv["n_scenarios"], conv["mean_aep_mwh"], marker="o", color=C_MAIN,
             label="Mean AEP")
    ax1.plot(conv["n_scenarios"], conv["median_aep_mwh"], marker="s", color=C_GREEN,
             label="Median AEP")
    ax1.fill_between(
        conv["n_scenarios"],
        conv["mean_aep_mwh"] - 1.96 * conv["mc_se_mean_aep_mwh"],
        conv["mean_aep_mwh"] + 1.96 * conv["mc_se_mean_aep_mwh"],
        color=C_MAIN, alpha=0.18, label="Mean +/- 95% MC error",
    )
    ax1.set_xscale("log")
    ax1.set_xlabel("Number of scenarios (log scale)")
    ax1.set_ylabel("AEP (MWh)")
    ax1.set_title("Convergence of AEP statistics")
    ax1.legend(fontsize=8)

    ax2.plot(conv["n_scenarios"], conv["p_cf_below_0.25"], marker="o", color=C_ACCENT,
             label="P(CF < 0.25)")
    final = summary["probability_cf_below_threshold"]
    ax2.axhline(final["estimate"], color=C_GREY, linestyle="--", linewidth=1.0,
                label=f"10,000-scenario estimate = {final['estimate']:.4f}")
    ax2.set_xscale("log")
    ax2.set_xlabel("Number of scenarios (log scale)")
    ax2.set_ylabel("P(CF < 0.25)")
    ax2.set_title("Convergence of the low-CF probability")
    ax2.legend(fontsize=8)
    _footer(fig, "Nested prefixes of a single run (seed held fixed); shaded band is the Monte Carlo standard error of the mean.")
    fig.subplots_adjust(left=0.15, right=0.93, top=0.90, bottom=0.14)
    return _save(fig, path)


# --------------------------------------------------------------------------
# 12. Confidence / credible interval visualisation
# --------------------------------------------------------------------------
def plot_ci_visualization(summary: dict, baseline: pd.DataFrame, path: Path) -> Path:
    a = summary["aep_mwh"]
    c = summary["capacity_factor"]
    p = summary["probability_cf_below_threshold"]

    fig, axes = plt.subplots(1, 3, figsize=(13.0, 4.3),
                             gridspec_kw={"width_ratios": [1.15, 1.15, 1.0], "wspace": 0.42})

    # AEP mean with 95% MC CI and P05-P95 spread
    ax = axes[0]
    ax.errorbar([0], [a["mean"]], yerr=[[a["mean"] - a["mean_ci95"][0]], [a["mean_ci95"][1] - a["mean"]]],
                fmt="o", color=C_MAIN, ecolor=C_MAIN, capsize=5, markersize=7,
                label="Mean +/- 95% MC CI")
    ax.plot([1], [a["p05"]], marker="|", color=C_ACCENT, markersize=14, label="5th percentile")
    ax.plot([1], [a["p95"]], marker="|", color=C_ACCENT, markersize=14, label="95th percentile")
    ax.plot([0.5, 1.5], [a["p05"], a["p05"]], color=C_ACCENT, linewidth=0.8)
    ax.plot([0.5, 1.5], [a["p95"], a["p95"]], color=C_ACCENT, linewidth=0.8)
    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Mean\n(95% MC CI)", "Percentiles"])
    ax.set_ylabel("AEP (MWh)")
    ax.set_title("AEP uncertainty")
    ax.legend(fontsize=7.5, loc="lower right")

    # CF with threshold
    ax = axes[1]
    ax.axhspan(0, p["threshold"], color=C_RED, alpha=0.10)
    ax.errorbar([0], [c["mean"]], yerr=[[c["mean"] - c["mean_ci95"][0]], [c["mean_ci95"][1] - c["mean"]]],
                fmt="o", color=C_MAIN, ecolor=C_MAIN, capsize=5, markersize=7, label="Mean CF +/- 95% MC CI")
    ax.axhline(p["threshold"], color=C_RED, linestyle="--", linewidth=1.4,
               label=f"Threshold {p['threshold']:.2f}")
    ax.set_xlim(-0.5, 0.5)
    ax.set_xticks([0])
    ax.set_xticklabels(["All scenarios"])
    ax.set_ylabel("Capacity factor")
    ax.set_title("Capacity-factor uncertainty")
    ax.legend(fontsize=7.5, loc="lower right")

    # Probability with Wilson CI
    ax = axes[2]
    lo, hi = p["wilson_ci95"]
    ax.errorbar([0], [p["estimate"]], yerr=[[p["estimate"] - lo], [hi - p["estimate"]]],
                fmt="o", color=C_ACCENT, ecolor=C_ACCENT, capsize=5, markersize=8,
                label="Estimate +/- 95% Wilson CI")
    ax.set_xlim(-0.5, 0.5)
    ax.set_xticks([0])
    ax.set_xticklabels(["P(CF < 0.25)"])
    ax.set_ylabel("Probability")
    ax.set_title(f"Low-CF probability = {p['estimate']:.4f}")
    ax.legend(fontsize=7.5, loc="upper right")

    _footer(fig, "Vertical bars are Monte Carlo sampling uncertainty across simulated annual scenarios, not measurement error.")
    fig.subplots_adjust(left=0.06, right=0.99, top=0.86, bottom=0.18)
    return _save(fig, path)


# --------------------------------------------------------------------------
# Thumbnail (16:9, 1280 x 720)
# --------------------------------------------------------------------------
def make_thumbnail(summary: dict, aep_path: Path, path: Path) -> Path:
    """16:9 thumbnail at exactly 1280x720 px, built from real results."""
    from matplotlib import gridspec
    import matplotlib.image as mpimg

    fig = plt.figure(figsize=(12.8, 7.2), facecolor="#0B2545")
    gs = gridspec.GridSpec(
        3, 2, figure=fig, width_ratios=[1.0, 1.25],
        left=0.045, right=0.975, top=0.86, bottom=0.05,
        hspace=0.30, wspace=0.14,
    )
    fig.text(0.045, 0.955, "Quantifying Wind Turbine Performance Uncertainty",
             color="white", fontsize=22, fontweight="bold", ha="left", va="top")
    fig.text(0.045, 0.900,
             "Monte Carlo assessment of power, annual energy production, and energy adequacy",
             color="#9DC3E6", fontsize=11.5, ha="left", va="top")

    a = summary["aep_mwh"]
    c = summary["capacity_factor"]
    p = summary["probability_cf_below_threshold"]

    cards = [
        ("Mean annual energy production", f"{a['mean']:,.0f} MWh",
         f"5th-95th: {a['p05']:,.0f} - {a['p95']:,.0f} MWh"),
        ("Mean capacity factor", f"{c['mean']:.3f}", f"SD {c['std']:.3f}"),
        ("P(capacity factor < 0.25)", f"{p['estimate']:.3f}",
         f"95% CI [{p['wilson_ci95'][0]:.3f}, {p['wilson_ci95'][1]:.3f}]"),
    ]
    for row, (lab, val, sub) in enumerate(cards):
        ax = fig.add_subplot(gs[row, 0])
        ax.axis("off")
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.add_patch(plt.Rectangle((0.02, 0.06), 0.96, 0.88, transform=ax.transAxes,
                                   facecolor="#13315C", edgecolor="#4A90C2", linewidth=1.2))
        ax.text(0.07, 0.74, lab, color="#9DC3E6", fontsize=9.5, transform=ax.transAxes)
        ax.text(0.07, 0.44, val, color="white", fontsize=24, fontweight="bold",
                transform=ax.transAxes)
        ax.text(0.07, 0.17, sub, color="#C9D6E3", fontsize=8.8, transform=ax.transAxes)

    ax = fig.add_subplot(gs[0:2, 1])
    img = mpimg.imread(aep_path)
    ax.imshow(img)
    ax.axis("off")

    ax = fig.add_subplot(gs[2, 1])
    ax.axis("off")
    ax.text(0.0, 0.92,
            "Data: Open-Meteo Historical Weather API (ERA5 reanalysis), Cuxhaven, Germany, "
            "2015-2024, hourly, UTC.\n"
            f"{summary['n_scenarios']:,} Monte Carlo scenarios | seed {summary['seed']} | "
            "seasonally stratified 7-day block bootstrap.\n"
            "Hypothetical 2 MW turbine (not an OEM power curve). Stanford PAI final project.",
            color="#C9D6E3", fontsize=8.6, va="top", ha="left", linespacing=1.5)

    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=100, facecolor=fig.get_facecolor())
    plt.close(fig)
    return path


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def make_all(df, result, summary, baseline, baseline_summary, convergence,
             spearman, sobol, oat, weibull, figures_dir: Path = C.FIGURES_DIR,
             thumbnail_path: Path | None = None) -> dict:
    out: dict = {}
    mean_rho = float(np.mean(result.mean_rho_kg_m3))
    out["01_wind_timeseries"] = plot_wind_timeseries(df, figures_dir / "fig01_wind_timeseries.png")
    out["02_wind_histogram"] = plot_wind_histogram(df, figures_dir / "fig02_wind_histogram.png")
    out["03_monthly_mean_wind"] = plot_monthly_climatology(df, figures_dir / "fig03_monthly_mean_wind.png")
    out["04_seasonal_distributions"] = plot_seasonal_distributions(df, figures_dir / "fig04_seasonal_distributions.png")
    out["05_empirical_vs_weibull"] = plot_empirical_vs_weibull(df, weibull, figures_dir / "fig05_empirical_vs_weibull.png")
    out["06_power_curve"] = plot_power_curve(figures_dir / "fig06_power_curve.png", mean_rho=mean_rho)
    out["07_mc_power_distribution"] = plot_mc_power_distribution(result, figures_dir / "fig07_mc_power_distribution.png")
    out["08_aep_distribution"] = plot_aep_distribution(result, summary, baseline, figures_dir / "fig08_aep_distribution.png")
    out["09_cf_distribution"] = plot_cf_distribution(result, summary, figures_dir / "fig09_cf_distribution.png")
    out["10_sensitivity"] = plot_sensitivity(spearman, sobol, oat, figures_dir / "fig10_sensitivity.png")
    out["11_convergence"] = plot_convergence(convergence, summary, figures_dir / "fig11_convergence.png")
    out["12_ci_visualization"] = plot_ci_visualization(summary, baseline, figures_dir / "fig12_confidence_intervals.png")
    if thumbnail_path is not None:
        out["thumbnail"] = make_thumbnail(summary, out["08_aep_distribution"], thumbnail_path)
    return out