"""Statistical analysis of the Monte Carlo output.

All reported uncertainty is Monte Carlo sampling uncertainty (variability across
independent simulated annual scenarios) unless explicitly labelled otherwise.  It
does not include structural/model uncertainty from the simplified physics or the
finite 10-year reanalysis record; those are discussed in the writeup.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from . import config as C


# --------------------------------------------------------------------------
# Interval helpers
# --------------------------------------------------------------------------
def wilson_ci(successes: int, n: int, confidence: float = 0.95) -> tuple[float, float]:
    """Wilson score interval for a binomial proportion."""
    if n <= 0:
        raise ValueError("n must be positive")
    z = _norm_ppf(1.0 - (1.0 - confidence) / 2.0)
    p = successes / n
    denom = 1.0 + z**2 / n
    centre = (p + z**2 / (2 * n)) / denom
    half = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / denom
    return float(max(0.0, centre - half)), float(min(1.0, centre + half))


def _norm_ppf(q: float) -> float:
    from scipy import stats

    return float(stats.norm.ppf(q))


def mean_ci(values: np.ndarray, confidence: float = 0.95) -> tuple[float, float, float]:
    """Normal-approximation CI for the mean; returns (mean, lo, hi)."""
    v = np.asarray(values, dtype=float)
    n = v.size
    mean = float(np.mean(v))
    se = float(np.std(v, ddof=1) / np.sqrt(n)) if n > 1 else float("nan")
    z = _norm_ppf(1.0 - (1.0 - confidence) / 2.0)
    return mean, mean - z * se, mean + z * se


# --------------------------------------------------------------------------
# Summary
# --------------------------------------------------------------------------
def summarise(result, threshold: float = C.CF_THRESHOLD) -> dict:
    aep = np.asarray(result.aep_mwh, dtype=float)
    cf = np.asarray(result.cf, dtype=float)
    n = aep.size
    if n < 2:
        raise ValueError("need at least two scenarios for a summary")

    p_cf = float(np.mean(cf < threshold))
    k = int(np.sum(cf < threshold))
    lo, hi = wilson_ci(k, n)

    mean_aep, aep_lo, aep_hi = mean_ci(aep)
    mean_cf, cf_lo, cf_hi = mean_ci(cf)

    q = np.percentile(aep, [5, 25, 50, 75, 95])
    qc = np.percentile(cf, [5, 25, 50, 75, 95])

    return {
        "n_scenarios": n,
        "seed": int(result.seed),
        "aep_mwh": {
            "mean": float(np.mean(aep)),
            "median": float(np.median(aep)),
            "std": float(np.std(aep, ddof=1)),
            "variance": float(np.var(aep, ddof=1)),
            "min": float(np.min(aep)),
            "max": float(np.max(aep)),
            "p05": float(q[0]),
            "p25": float(q[1]),
            "p75": float(q[3]),
            "p95": float(q[4]),
            "iqr": float(q[3] - q[1]),
            "mean_ci95": [aep_lo, aep_hi],
            "mc_standard_error": float(np.std(aep, ddof=1) / np.sqrt(n)),
        },
        "capacity_factor": {
            "mean": float(np.mean(cf)),
            "std": float(np.std(cf, ddof=1)),
            "variance": float(np.var(cf, ddof=1)),
            "p05": float(qc[0]),
            "p25": float(qc[1]),
            "median": float(qc[2]),
            "p75": float(qc[3]),
            "p95": float(qc[4]),
            "mean_ci95": [cf_lo, cf_hi],
        },
        "probability_cf_below_threshold": {
            "threshold": threshold,
            "estimate": p_cf,
            "successes": k,
            "n": n,
            "wilson_ci95": [lo, hi],
            "definition": (
                "P(annual capacity factor < 0.25) across simulated scenarios; "
                "an energy-adequacy indicator, not a mechanical failure probability."
            ),
        },
        "expected_power_output_mw": {
            "mean": float(np.mean(result.mean_power_mw)),
            "std": float(np.std(result.mean_power_mw, ddof=1)),
            "min": float(np.min(result.mean_power_mw)),
            "max": float(np.max(result.mean_power_mw)),
            "definition": "Mean hourly electrical power per annual scenario (AEP / 8760 h).",
        },
        "inputs": {
            "cp": {
                "mean": float(np.mean(result.cp)),
                "std": float(np.std(result.cp, ddof=1)),
                "min": float(np.min(result.cp)),
                "max": float(np.max(result.cp)),
                "bounds": list(C.CP_BOUNDS),
                "betz_limit": C.BETZ_LIMIT,
            },
            "eta": {
                "mean": float(np.mean(result.eta)),
                "std": float(np.std(result.eta, ddof=1)),
                "min": float(np.min(result.eta)),
                "max": float(np.max(result.eta)),
                "bounds": list(C.ETA_BOUNDS),
            },
            "scenario_mean_wind_mps": {
                "mean": float(np.mean(result.mean_wind_mps)),
                "std": float(np.std(result.mean_wind_mps, ddof=1)),
                "min": float(np.min(result.mean_wind_mps)),
                "max": float(np.max(result.mean_wind_mps)),
            },
            "scenario_mean_air_density_kg_m3": {
                "mean": float(np.mean(result.mean_rho_kg_m3)),
                "std": float(np.std(result.mean_rho_kg_m3, ddof=1)),
                "min": float(np.min(result.mean_rho_kg_m3)),
                "max": float(np.max(result.mean_rho_kg_m3)),
            },
        },
        "power_histogram": {
            "bin_edges_mw": result.power_bins.tolist(),
            "counts": result.power_histogram.tolist(),
        },
    }


def summarise_baseline(baseline: pd.DataFrame, threshold: float = C.CF_THRESHOLD) -> dict:
    aep = baseline["aep_mwh"].to_numpy(float)
    cf = baseline["capacity_factor"].to_numpy(float)
    return {
        "years": baseline["year"].astype(int).tolist(),
        "hours": baseline["hours"].astype(int).tolist(),
        "aep_mwh_mean": float(np.mean(aep)),
        "aep_mwh_min": float(np.min(aep)),
        "aep_mwh_max": float(np.max(aep)),
        "aep_mwh_std": float(np.std(aep, ddof=1)),
        "capacity_factor_mean": float(np.mean(cf)),
        "capacity_factor_min": float(np.min(cf)),
        "capacity_factor_max": float(np.max(cf)),
        "probability_cf_below_threshold_empirical": float(np.mean(cf < threshold)),
        "n_years": int(aep.size),
    }


def markdown_summary(summary: dict, baseline: dict | None = None,
                     convergence: pd.DataFrame | None = None) -> str:
    a = summary["aep_mwh"]
    c = summary["capacity_factor"]
    p = summary["probability_cf_below_threshold"]
    pw = summary["expected_power_output_mw"]

    def f(x: float) -> str:
        return f"{x:,.1f}"

    lines = ["# Monte Carlo results", ""]
    lines.append(f"**Scenarios:** {summary['n_scenarios']:,}  ")
    lines.append(f"**Seed:** {summary['seed']}  ")
    lines.append("")
    lines.append("## Annual energy production (MWh)")
    lines.append("")
    lines.append("| Statistic | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Mean | {f(a['mean'])} |")
    lines.append(f"| Median | {f(a['median'])} |")
    lines.append(f"| Standard deviation | {f(a['std'])} |")
    lines.append(f"| Variance (MWh^2) | {a['variance']:,.0f} |")
    lines.append(f"| 5th percentile | {f(a['p05'])} |")
    lines.append(f"| 25th percentile | {f(a['p25'])} |")
    lines.append(f"| 75th percentile | {f(a['p75'])} |")
    lines.append(f"| 95th percentile | {f(a['p95'])} |")
    lines.append(f"| Mean 95% CI (MC) | [{a['mean_ci95'][0]:,.1f}, {a['mean_ci95'][1]:,.1f}] |")
    lines.append("")
    lines.append("## Capacity factor")
    lines.append("")
    lines.append("| Statistic | Value |")
    lines.append("|---|---:|")
    lines.append(f"| Mean | {c['mean']:.4f} |")
    lines.append(f"| Standard deviation | {c['std']:.4f} |")
    lines.append(f"| 5th percentile | {c['p05']:.4f} |")
    lines.append(f"| 25th percentile | {c['p25']:.4f} |")
    lines.append(f"| Median | {c['median']:.4f} |")
    lines.append(f"| 75th percentile | {c['p75']:.4f} |")
    lines.append(f"| 95th percentile | {c['p95']:.4f} |")
    lines.append("")
    lines.append("## Energy adequacy")
    lines.append("")
    lines.append(f"- **P(CF < {p['threshold']:.2f}) = {p['estimate']:.4f}** "
                 f"(95% Wilson CI [{p['wilson_ci95'][0]:.4f}, {p['wilson_ci95'][1]:.4f}], "
                 f"{p['successes']}/{p['n']:,})")
    lines.append(f"- Expected power output: {pw['mean']:.3f} MW ± {pw['std']:.3f} MW (SD across scenarios)")
    lines.append("")
    if baseline:
        lines.append("## Deterministic baseline (nominal Cp=0.359, eta=0.94)")
        lines.append("")
        lines.append("| Statistic | Value |")
        lines.append("|---|---:|")
        lines.append(f"| Mean AEP 2015-2024 | {baseline['aep_mwh_mean']:,.1f} MWh |")
        lines.append(f"| Min / max annual AEP | {baseline['aep_mwh_min']:,.1f} / {baseline['aep_mwh_max']:,.1f} MWh |")
        lines.append(f"| Mean CF | {baseline['capacity_factor_mean']:.4f} |")
        lines.append(f"| Years with CF < {p['threshold']:.2f} | "
                     f"{baseline['probability_cf_below_threshold_empirical'] * baseline['n_years']:.0f} of {baseline['n_years']} |")
        lines.append("")
    if convergence is not None:
        lines.append("## Convergence (nested prefixes of one run)")
        lines.append("")
        lines.append("| N | Mean AEP (MWh) | Median AEP (MWh) | SD AEP (MWh) | P(CF<0.25) | MC SE of mean |")
        lines.append("|---:|---:|---:|---:|---:|---:|")
        for _, r in convergence.iterrows():
            lines.append(
                f"| {int(r['n_scenarios']):,} | {r['mean_aep_mwh']:,.1f} | {r['median_aep_mwh']:,.1f} | "
                f"{r['std_aep_mwh']:,.1f} | {r['p_cf_below_0.25']:.4f} | {r['mc_se_mean_aep_mwh']:,.1f} |"
            )
        lines.append("")
    return "\n".join(lines)