"""Final scientific-quality audit analyses.

This module does NOT modify any of the working research pipeline. It adds two
standalone, reproducible analyses requested in the final audit:

1. A factorial uncertainty decomposition that separates
   - historical weather variability (weather resampled, Cp/eta fixed),
   - turbine-parameter uncertainty (weather fixed, Cp/eta resampled),
   - their interaction, and the Monte Carlo sampling error.
   Structural model uncertainty is NOT quantified: no experiment here varies
   the physics itself, so it remains a documented qualitative limitation.

2. A bootstrap preservation check comparing historical and simulated monthly
   and seasonal wind-speed means, standard deviations, quantiles, and KS
   statistics, plus a count of block-join discontinuities.

Outputs are written to results/tables/ (new files only; existing outputs untouched).
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C
from .data_processing import load_processed
from .simulation import build_bootstrap_pools, _simulate_chunk, sample_turbine_params
from .turbine_model import power_mw

QUANTILES = (0.05, 0.25, 0.50, 0.75, 0.95)
Q_LABELS = ("p05", "p25", "median", "p75", "p95")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, np.ndarray):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=_json_default), encoding="utf-8")


# ---------------------------------------------------------------------------
# 1. Factorial uncertainty decomposition
# ---------------------------------------------------------------------------
def uncertainty_decomposition(n: int = 5000, seed: int = C.SEED) -> dict:
    """Separate weather, turbine-parameter, interaction and MC variance."""
    df = load_processed()
    pools = build_bootstrap_pools(df)
    wind = df["wind_speed_100m"].to_numpy(float)
    temp = df["temperature_2m"].to_numpy(float)
    pres = df["surface_pressure"].to_numpy(float)
    rng = np.random.default_rng(seed)

    # --- A. Weather-only: bootstrap weather, Cp/eta fixed at nominal -----------
    cp_fixed = np.full(n, C.CP_NOMINAL)
    eta_fixed = np.full(n, C.ETA_NOMINAL)
    out_w = _simulate_chunk(rng, pools, wind, temp, pres, cp_fixed, eta_fixed)
    aep_w = out_w["aep_mwh"]
    var_w = float(aep_w.var(ddof=1))

    # --- B. Turbine-only: observed weather fixed, Cp/eta sampled --------------
    # One fixed historical year per replicate; power is nonlinear in wind, so the
    # turbine variance is reported across all 10 historical years (excluding Feb 29).
    per_year: dict[int, dict] = {}
    for year in sorted(df["year"].unique()):
        sub = df[(df["year"] == year) & (~df["is_leap_day"])]
        w = sub["wind_speed_100m"].to_numpy(float)
        rho = sub["air_density_kg_m3"].to_numpy(float)
        if w.size != C.N_HOURS_YEAR:
            continue
        cp_s, eta_s = sample_turbine_params(rng, n)
        p = power_mw(w[None, :], rho[None, :], cp_s[:, None], eta_s[:, None])
        aep_t = p.sum(axis=1)
        per_year[int(year)] = {
            "mean_aep_mwh": float(aep_t.mean()),
            "variance_aep_mwh2": float(aep_t.var(ddof=1)),
            "sd_aep_mwh": float(aep_t.std(ddof=1)),
        }
    var_t_values = [v["variance_aep_mwh2"] for v in per_year.values()]
    var_t_mean = float(np.mean(var_t_values))

    # --- C. Combined: main simulation output ----------------------------------
    scen = pd.read_csv(C.TABLES_DIR / "scenarios.csv")
    aep_comb = scen["aep_mwh"].to_numpy(float)
    var_total = float(aep_comb.var(ddof=1))
    n_main = int(aep_comb.size)
    mc_se_mean = float(aep_comb.std(ddof=1) / np.sqrt(n_main))
    var_mc_mean = mc_se_mean**2  # variance of the *sample mean*, not of AEP

    interaction = float(var_total - var_w - var_t_mean)

    # Diagnostics: MC sampling error of each variance estimate (normal approx.)
    se_var_w = float(var_w * np.sqrt(2.0 / (n - 1)))
    se_var_t = float(np.std(var_t_values, ddof=1) / np.sqrt(len(var_t_values)))

    result = {
        "design": {
            "n_per_experiment": int(n),
            "main_scenarios": n_main,
            "seed": int(seed),
            "factorial": {
                "A_weather_only": "bootstrap weather; Cp=0.359, eta=0.94 fixed",
                "B_turbine_only": "observed historical year fixed; Cp/eta sampled once per replicate",
                "C_combined": "main simulation: both weather and Cp/eta sampled (existing 10,000 scenarios)",
            },
        },
        "variance_components_mwh2": {
            "total_AEP_variance_C": var_total,
            "weather_only_A": var_w,
            "turbine_only_B_mean_over_10_years": var_t_mean,
            "interaction_C_minus_A_minus_B": interaction,
            "weather_fraction_of_total": var_w / var_total,
            "turbine_fraction_of_total": var_t_mean / var_total,
            "interaction_fraction_of_total": interaction / var_total,
        },
        "monte_carlo_error": {
            "mc_standard_error_of_mean_AEP_mwh": mc_se_mean,
            "variance_of_sample_mean_mwh2": var_mc_mean,
            "fraction_of_total_variance": var_mc_mean / var_total,
            "note": (
                "This is the uncertainty of the ESTIMATED MEAN, not a source of "
                "AEP variability. It shrinks as 1/sqrt(N); it is not part of the "
                "physical variance decomposition."
            ),
        },
        "diagnostics": {
            "mc_se_of_weather_variance_estimate_mwh2": se_var_w,
            "mc_se_of_turbine_variance_mean_mwh2": se_var_t,
            "turbine_variance_by_historical_year": per_year,
            "note": (
                "Weather-only variance is estimated from n bootstrap scenarios; "
                "turbine-only variance is averaged over 10 fixed historical years "
                "because power is nonlinear in wind (V^3 and rated clipping), so "
                "the turbine contribution depends on the weather realization."
            ),
        },
        "structural_model_uncertainty": {
            "quantified": False,
            "reason": (
                "No experiment in this analysis varies the physics, data source, "
                "or model structure. Comparison against an OEM power curve, "
                "hub-height temperature, or measured winds would be required. "
                "It remains a documented qualitative limitation only."
            ),
        },
    }
    return result


# ---------------------------------------------------------------------------
# 2. Bootstrap preservation
# ---------------------------------------------------------------------------
def _describe(hist: np.ndarray, sim: np.ndarray) -> dict:
    ks, ks_p = stats.ks_2samp(hist, sim)
    qh = np.quantile(hist, QUANTILES)
    qs = np.quantile(sim, QUANTILES)
    return {
        "n_historical": int(hist.size),
        "n_simulated": int(sim.size),
        "historical": {
            "mean_mps": float(np.mean(hist)),
            "std_mps": float(np.std(hist, ddof=1)),
            **{f"q_{lab}_mps": float(q) for lab, q in zip(Q_LABELS, qh)},
        },
        "simulated": {
            "mean_mps": float(np.mean(sim)),
            "std_mps": float(np.std(sim, ddof=1)),
            **{f"q_{lab}_mps": float(q) for lab, q in zip(Q_LABELS, qs)},
        },
        "absolute_difference": {
            "mean_mps": float(np.mean(sim) - np.mean(hist)),
            "std_mps": float(np.std(sim, ddof=1) - np.std(hist, ddof=1)),
            **{f"q_{lab}_mps": float(s - h) for lab, s, h in zip(Q_LABELS, qs, qh)},
        },
        "ks_statistic": float(ks),
        "ks_p_value": float(ks_p),
    }


def bootstrap_preservation(n_years: int = 500, seed: int = C.SEED + 7) -> dict:
    """Compare historical vs simulated monthly/seasonal wind distributions."""
    df = load_processed()
    pools = build_bootstrap_pools(df)
    wind = df["wind_speed_100m"].to_numpy(float)
    rng = np.random.default_rng(seed)
    block = C.BLOCK_HOURS

    # Historical values, excluding leap day to match the simulated year structure.
    hist_df = df[~df["is_leap_day"]]

    # Draw n_years synthetic years and collect all simulated hourly wind values
    # by calendar month (block order preserved within each block).
    sim_by_month: dict[int, np.ndarray] = {}
    join_counts: dict[int, int] = {}
    for m in range(1, 13):
        length = C.MONTH_HOURS[m]
        n_blocks = -(-length // block)  # ceil
        join_counts[m] = n_blocks - 1
        starts = pools[m][rng.integers(0, pools[m].size, size=(n_years, n_blocks))]
        idx = (starts[:, :, None] + np.arange(block)[None, None, :]).reshape(
            n_years, n_blocks * block
        )[:, :length]
        sim_by_month[m] = wind[idx].ravel()

    monthly = {}
    for m in range(1, 13):
        hist = hist_df.loc[hist_df["month"] == m, "wind_speed_100m"].to_numpy(float)
        monthly[C.MONTH_NAMES[m]] = _describe(hist, sim_by_month[m])

    seasonal = {}
    for season, months in C.SEASONS.items():
        hist = hist_df.loc[hist_df["month"].isin(months), "wind_speed_100m"].to_numpy(float)
        sim = np.concatenate([sim_by_month[m] for m in months])
        seasonal[season] = _describe(hist, sim)

    joins_within_months = int(sum(join_counts.values()))
    inter_month_joins = 11
    return {
        "design": {
            "n_simulated_years": int(n_years),
            "seed": int(seed),
            "block_hours": int(block),
            "blocks_per_month": {C.MONTH_NAMES[m]: int(-(-C.MONTH_HOURS[m] // block)) for m in range(1, 13)},
            "within_month_block_joins_per_year": join_counts,
            "total_within_month_joins_per_year": joins_within_months,
            "inter_month_boundaries_per_year": inter_month_joins,
            "total_discontinuities_per_year": joins_within_months + inter_month_joins,
        },
        "monthly": monthly,
        "seasonal": seasonal,
        "interpretation": (
            "The bootstrap resamples contiguous 7-day blocks from the historical "
            "series within each calendar month, so each month's marginal distribution "
            "is preserved up to Monte Carlo resampling error. Differences in means, "
            "SDs and quantiles should be small. KS p-values can be tiny with very "
            "large simulated n even for negligible differences, so effect sizes "
            "(mean/SD/quantile differences) are the primary criterion. Block joins "
            "break temporal dependence at a limited number of points per year and "
            "across month boundaries; within-block chronology is preserved."
        ),
    }


# ---------------------------------------------------------------------------
# Markdown rendering
# ---------------------------------------------------------------------------
def render_uncertainty_md(r: dict) -> str:
    v = r["variance_components_mwh2"]
    mc = r["monte_carlo_error"]
    lines = [
        "# Quantitative uncertainty decomposition", "",
        f"Design: {r['design']['n_per_experiment']:,} scenarios per factorial arm; "
        f"main simulation {r['design']['main_scenarios']:,} scenarios; seed {r['design']['seed']}.", "",
        "| Component | Variance (MWh²) | Share of total |", "|---|---:|---:|",
        f"| Total AEP variance (main simulation) | {v['total_AEP_variance_C']:,.0f} | 100.0% |",
        f"| A. Historical weather variability | {v['weather_only_A']:,.0f} | {v['weather_fraction_of_total']*100:.1f}% |",
        f"| B. Turbine-parameter uncertainty (Cp, eta), mean over 10 years | {v['turbine_only_B_mean_over_10_years']:,.0f} | {v['turbine_fraction_of_total']*100:.1f}% |",
        f"| A×B interaction / residual | {v['interaction_C_minus_A_minus_B']:,.0f} | {v['interaction_fraction_of_total']*100:.1f}% |",
        "", "## Monte Carlo sampling error (separate from physical variance)", "",
        f"- MC standard error of the mean AEP: {mc['mc_standard_error_of_mean_AEP_mwh']:.2f} MWh",
        f"- Variance of the sample mean: {mc['variance_of_sample_mean_mwh2']:.1f} MWh² "
        f"({mc['fraction_of_total_variance']*100:.4f}% of total AEP variance)",
        f"- {mc['note']}", "",
        "## Structural model uncertainty", "",
        f"**NOT QUANTIFIED.** {r['structural_model_uncertainty']['reason']}", "",
        "## Diagnostics", "",
        f"- MC SE of weather variance estimate: {r['diagnostics']['mc_se_of_weather_variance_estimate_mwh2']:,.0f} MWh²",
        f"- MC SE of turbine variance mean: {r['diagnostics']['mc_se_of_turbine_variance_mean_mwh2']:,.0f} MWh²",
        "", "| Historical year | Fixed-weather AEP mean (MWh) | Turbine-only variance (MWh²) |",
        "|---|---:|---:|",
    ]
    for y, d in r["diagnostics"]["turbine_variance_by_historical_year"].items():
        lines.append(f"| {y} | {d['mean_aep_mwh']:,.1f} | {d['variance_aep_mwh2']:,.0f} |")
    lines += ["", r["diagnostics"]["note"], ""]
    return "\n".join(lines)


def render_preservation_md(r: dict) -> str:
    d = r["design"]
    lines = [
        "# Bootstrap preservation check", "",
        f"Simulated years: {d['n_simulated_years']:,}; block length {d['block_hours']} h; "
        f"seed {r['design']['seed']}.",
        "",
        f"Discontinuities per simulated year: {d['total_within_month_joins_per_year']} within-month "
        f"block joins + {d['inter_month_boundaries_per_year']} month boundaries = "
        f"{d['total_discontinuities_per_year']} total.", "",
        "## Monthly mean and SD (m/s)", "",
        "| Month | Hist mean | Sim mean | Δ mean | Hist SD | Sim SD | Δ SD | KS stat | KS p |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for m, e in r["monthly"].items():
        lines.append(
            f"| {m} | {e['historical']['mean_mps']:.3f} | {e['simulated']['mean_mps']:.3f} | "
            f"{e['absolute_difference']['mean_mps']:+.3f} | {e['historical']['std_mps']:.3f} | "
            f"{e['simulated']['std_mps']:.3f} | {e['absolute_difference']['std_mps']:+.3f} | "
            f"{e['ks_statistic']:.4f} | {e['ks_p_value']:.3g} |"
        )
    lines += ["", "## Monthly wind-speed quantiles (m/s): historical vs simulated difference", "",
              "| Month | Δ p05 | Δ p25 | Δ median | Δ p75 | Δ p95 |", "|---|---:|---:|---:|---:|---:|"]
    for m, e in r["monthly"].items():
        ad = e["absolute_difference"]
        lines.append(
            f"| {m} | {ad['q_p05_mps']:+.3f} | {ad['q_p25_mps']:+.3f} | {ad['q_median_mps']:+.3f} | "
            f"{ad['q_p75_mps']:+.3f} | {ad['q_p95_mps']:+.3f} |"
        )
    lines += ["", "## Seasonal distributions", "",
              "| Season | Hist mean | Sim mean | Δ mean | Hist SD | Sim SD | Δ SD | KS stat | KS p |",
              "|---|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for s, e in r["seasonal"].items():
        lines.append(
            f"| {s} | {e['historical']['mean_mps']:.3f} | {e['simulated']['mean_mps']:.3f} | "
            f"{e['absolute_difference']['mean_mps']:+.3f} | {e['historical']['std_mps']:.3f} | "
            f"{e['simulated']['std_mps']:.3f} | {e['absolute_difference']['std_mps']:+.3f} | "
            f"{e['ks_statistic']:.4f} | {e['ks_p_value']:.3g} |"
        )
    lines += ["", "## Seasonal quantiles (m/s): historical vs simulated difference", "",
              "| Season | Δ p05 | Δ p25 | Δ median | Δ p75 | Δ p95 |", "|---|---:|---:|---:|---:|---:|"]
    for s, e in r["seasonal"].items():
        ad = e["absolute_difference"]
        lines.append(
            f"| {s} | {ad['q_p05_mps']:+.3f} | {ad['q_p25_mps']:+.3f} | {ad['q_median_mps']:+.3f} | "
            f"{ad['q_p75_mps']:+.3f} | {ad['q_p95_mps']:+.3f} |"
        )
    lines += ["", r["interpretation"], ""]
    return "\n".join(lines)


def main() -> None:
    print("Running factorial uncertainty decomposition ...")
    unc = uncertainty_decomposition()
    _write_json(C.TABLES_DIR / "uncertainty_decomposition.json", unc)
    (C.TABLES_DIR / "uncertainty_decomposition.md").write_text(
        render_uncertainty_md(unc), encoding="utf-8"
    )
    v = unc["variance_components_mwh2"]
    print(f"  total variance {v['total_AEP_variance_C']:,.0f} MWh^2")
    print(f"  weather {v['weather_only_A']:,.0f} ({v['weather_fraction_of_total']*100:.1f}%)")
    print(f"  turbine {v['turbine_only_B_mean_over_10_years']:,.0f} ({v['turbine_fraction_of_total']*100:.1f}%)")
    print(f"  interaction {v['interaction_C_minus_A_minus_B']:,.0f} ({v['interaction_fraction_of_total']*100:.1f}%)")
    print(f"  MC SE of mean {unc['monte_carlo_error']['mc_standard_error_of_mean_AEP_mwh']:.2f} MWh")
    print("  structural uncertainty: NOT QUANTIFIED")
    print("Running bootstrap preservation check ...")
    boot = bootstrap_preservation()
    _write_json(C.TABLES_DIR / "bootstrap_preservation.json", boot)
    (C.TABLES_DIR / "bootstrap_preservation.md").write_text(
        render_preservation_md(boot), encoding="utf-8"
    )
    print(f"  simulated years: {boot['design']['n_simulated_years']:,}")
    print(f"  discontinuities per year: {boot['design']['total_discontinuities_per_year']}")
    for m, e in boot["monthly"].items():
        print(f"    {m:9s} d_mean={e['absolute_difference']['mean_mps']:+.3f} m/s  d_sd={e['absolute_difference']['std_mps']:+.3f} m/s")
    for s, e in boot["seasonal"].items():
        print(f"    {s} d_mean={e['absolute_difference']['mean_mps']:+.3f} m/s  d_sd={e['absolute_difference']['std_mps']:+.3f} m/s")


if __name__ == "__main__":
    main()
