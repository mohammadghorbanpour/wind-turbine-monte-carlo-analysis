"""Sensitivity analysis.

Two complementary analyses are provided.

1. Spearman rank correlation on the MAIN historical-weather simulation.
   Scenario-level uncertain inputs (Cp, eta, mean wind speed, mean air density)
   are correlated with AEP and capacity factor.  This is a *screening* analysis
   on dependent inputs; correlations are monotone associations, not causal
   effects, and the scenario mean wind speed is itself a summary of the
   resampled weather.

2. Sobol variance-based indices on a SEPARATE experiment with independent
   inputs by construction: Weibull (k, c), Cp, eta, and an air-density
   multiplier.  Wind is generated from independent Weibull draws with a fixed
   uniform base sample (common random numbers), which removes temporal
   dependence by design.  This experiment answers "which uncertain parameters
   drive AEP variance under independence?" and must NOT be read as the
   sensitivity of the historical-weather simulation, where weather variability
   dominates and inputs are dependent.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C
from .turbine_model import power_mw, weibull_inverse_cdf


# --------------------------------------------------------------------------
# 1. Spearman rank correlation on the main simulation
# --------------------------------------------------------------------------
def spearman_sensitivity(result) -> pd.DataFrame:
    inputs = {
        "cp": np.asarray(result.cp, dtype=float),
        "eta": np.asarray(result.eta, dtype=float),
        "scenario_mean_wind_speed_mps": np.asarray(result.mean_wind_mps, dtype=float),
        "scenario_mean_air_density_kg_m3": np.asarray(result.mean_rho_kg_m3, dtype=float),
    }
    outputs = {
        "aep_mwh": np.asarray(result.aep_mwh, dtype=float),
        "capacity_factor": np.asarray(result.cf, dtype=float),
    }
    rows = []
    for iname, iv in inputs.items():
        for oname, ov in outputs.items():
            rho, p = stats.spearmanr(iv, ov)
            rows.append(
                {
                    "input": iname,
                    "output": oname,
                    "spearman_rho": float(rho),
                    "p_value": float(p),
                    "n": int(iv.size),
                }
            )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# 2. Sobol experiment with independent inputs
# --------------------------------------------------------------------------
def sobol_problem() -> dict:
    return {
        "num_vars": len(C.SOBOL_NAMES),
        "names": list(C.SOBOL_NAMES),
        "bounds": [list(C.SOBOL_BOUNDS[n]) for n in C.SOBOL_NAMES],
    }


def sobol_model(x: np.ndarray, u_base: np.ndarray,
                turbine: C.TurbineSpec = C.TURBINE) -> float:
    """Independent-input AEP model [MWh].

    x = [weibull_k, weibull_c, cp, eta, rho_factor]
    Wind is generated from a fixed uniform base sample, so all parameter sets
    share the same underlying random draws (common random numbers).
    """
    k, c, cp, eta, rho_factor = (float(v) for v in x)
    wind = weibull_inverse_cdf(u_base, k, c)
    rho = C.NOMINAL_RHO * rho_factor
    p = power_mw(wind, rho, cp, eta, turbine)
    return float(p.sum())


def _sample_saltelli(problem: dict, n: int, seed: int) -> np.ndarray:
    try:
        from SALib.sample import sobol as sobol_sample  # SALib >= 1.5

        return sobol_sample.sample(problem, n, random_seed=seed)
    except Exception:  # noqa: BLE001 - fallback for older SALib
        from SALib.sample import saltelli

        return saltelli.sample(problem, n, calc_second_order=True)


def _sobol_analyze():
    """Return the Sobol analysis callable across SALib layouts."""
    try:
        from SALib.analyze.sobol import analyze as analyze_fn  # SALib >= 1.5

        return analyze_fn
    except ImportError:  # pragma: no cover - older SALib
        from SALib.analyze import sobol as sobol_module

        return getattr(sobol_module, "analyze", sobol_module)


def sobol_analysis(n: int = C.SOBOL_N, seed: int = C.SEED) -> dict:
    sobol_analyze = _sobol_analyze()

    problem = sobol_problem()
    x = _sample_saltelli(problem, n, seed)

    # Fixed uniform base sample -> common random numbers, no temporal dependence.
    base = np.random.Generator(np.random.PCG64(seed + 1)).random(C.N_HOURS_YEAR)

    y = np.array([sobol_model(row, base) for row in x], dtype=float)
    if not np.all(np.isfinite(y)):
        raise RuntimeError("non-finite Sobol model output")

    si = sobol_analyze(
        problem, y, calc_second_order=True, num_resamples=200,
        conf_level=0.95, seed=seed, print_to_console=False,
    )

    total_order = np.asarray(si["ST"], dtype=float)
    first_order = np.asarray(si["S1"], dtype=float)
    total_ci = np.asarray(si["ST_conf"], dtype=float)
    first_ci = np.asarray(si["S1_conf"], dtype=float)

    order = np.argsort(total_order)[::-1]
    table = pd.DataFrame(
        {
            "parameter": [problem["names"][i] for i in order],
            "s1": first_order[order],
            "s1_conf": first_ci[order],
            "st": total_order[order],
            "st_conf": total_ci[order],
            "rank_by_total": np.arange(1, len(order) + 1),
        }
    )

    return {
        "n_base_samples": int(n),
        "n_model_evaluations": int(x.shape[0]),
        "seed": int(seed),
        "hours_per_evaluation": int(C.N_HOURS_YEAR),
        "parameters": problem["names"],
        "bounds": problem["bounds"],
        "s1": first_order.tolist(),
        "s1_conf": first_ci.tolist(),
        "st": total_order.tolist(),
        "st_conf": total_ci.tolist(),
        "sobol_table": table,
        "output_mean_mwh": float(np.mean(y)),
        "output_std_mwh": float(np.std(y, ddof=1)),
        "note": (
            "Independent-input experiment: Weibull wind with common random "
            "numbers, constant Cp/eta/rho per run. Not the historical-weather "
            "simulation."
        ),
    }


# --------------------------------------------------------------------------
# 3. One-at-a-time tornado on the same independent model (supporting view)
# --------------------------------------------------------------------------
def oat_tornado(base: dict | None = None, u_base: np.ndarray | None = None) -> pd.DataFrame:
    """Vary each Sobol input from its lower to upper bound, others at nominal."""
    if u_base is None:
        u_base = np.random.Generator(np.random.PCG64(C.SEED + 1)).random(C.N_HOURS_YEAR)

    nominal = {
        "weibull_k": 2.2,
        "weibull_c": 8.5,
        "cp": C.CP_NOMINAL,
        "eta": C.ETA_NOMINAL,
        "rho_factor": 1.0,
    }
    # AEP at the nominal point
    x0 = [nominal[n] for n in C.SOBOL_NAMES]
    aep0 = sobol_model(np.array(x0), u_base)

    rows = []
    for i, name in enumerate(C.SOBOL_NAMES):
        lo = C.SOBOL_BOUNDS[name][0]
        hi = C.SOBOL_BOUNDS[name][1]
        x_lo = list(x0)
        x_hi = list(x0)
        x_lo[i] = lo
        x_hi[i] = hi
        a_lo = sobol_model(np.array(x_lo), u_base)
        a_hi = sobol_model(np.array(x_hi), u_base)
        rows.append(
            {
                "parameter": name,
                "low_value": lo,
                "high_value": hi,
                "aep_low_mwh": a_lo,
                "aep_high_mwh": a_hi,
                "swing_mwh": abs(a_hi - a_lo),
                "aep_nominal_mwh": aep0,
            }
        )
    df = pd.DataFrame(rows).sort_values("swing_mwh", ascending=False).reset_index(drop=True)
    df["rank_by_swing"] = np.arange(1, len(df) + 1)
    return df


def sensitivity_summary(sobol: dict, spearman: pd.DataFrame, oat: pd.DataFrame) -> str:
    lines = ["# Sensitivity analysis", ""]
    lines.append("## Spearman rank correlation (main simulation)")
    lines.append("")
    lines.append("| Input | Output | Spearman rho | p-value |")
    lines.append("|---|---|---:|---:|")
    for _, r in spearman.iterrows():
        p_txt = "< 1e-12" if r["p_value"] < 1e-12 else f"{r['p_value']:.3g}"
        lines.append(f"| {r['input']} | {r['output']} | {r['spearman_rho']:.3f} | {p_txt} |")
    lines.append("")
    lines.append("## Sobol indices (independent-input experiment)")
    lines.append("")
    lines.append("| Parameter | S1 | ST | ST 95% CI |")
    lines.append("|---|---:|---:|---:|")
    for i, name in enumerate(sobol["parameters"]):
        lines.append(
            f"| {name} | {sobol['s1'][i]:.3f} | {sobol['st'][i]:.3f} | "
            f"+/- {sobol['st_conf'][i]:.3f} |"
        )
    lines.append("")
    lines.append("## One-at-a-time swing (supporting view)")
    lines.append("")
    lines.append("| Parameter | AEP at low | AEP at high | Swing (MWh) |")
    lines.append("|---|---:|---:|---:|")
    for _, r in oat.iterrows():
        lines.append(
            f"| {r['parameter']} | {r['aep_low_mwh']:,.0f} | {r['aep_high_mwh']:,.0f} | {r['swing_mwh']:,.0f} |"
        )
    lines.append("")
    return "\n".join(lines)


if __name__ == "__main__":
    from .data_processing import load_processed
    from .simulation import simulate

    res = simulate(load_processed(), n_scenarios=500)
    print(spearman_sensitivity(res).to_string(index=False))
    print(sobol_analysis(n=64))