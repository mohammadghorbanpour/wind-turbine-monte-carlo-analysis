"""Monte Carlo simulation with a seasonally stratified block bootstrap.

Design
------
* The observed hourly ERA5 series (2015-2024) is the primary source of wind
  variability.  Wind speeds are NOT replaced by independent Weibull draws in the
  main simulation.
* For each calendar month, contiguous 168 h (7-day) blocks that lie entirely
  inside one month and one year are resampled with replacement.  Within a block
  the chronological order is preserved, so short-term (synoptic) dependence
  survives; dependence is broken at block joins and across months.  This is a
  documented limitation, not a claim of full dependence preservation.
* February 29 is excluded so every synthetic year is exactly 8,760 h.
* ``Cp`` and ``eta`` are drawn ONCE per annual scenario (turbine-level design
  parameters), not per hour.
* Scenarios are processed in memory-bounded chunks; only scenario-level outputs
  and a binned hourly-power histogram are retained.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Iterable

import numpy as np
import pandas as pd
from scipy import stats

from . import config as C
from .turbine_model import air_density_from_surface, capacity_factor, power_mw

MONTH_OFFSET = {}
_acc = 0
for _m in range(1, 13):
    MONTH_OFFSET[_m] = _acc
    _acc += C.MONTH_HOURS[_m]
assert _acc == C.N_HOURS_YEAR


# --------------------------------------------------------------------------
# Bootstrap pools
# --------------------------------------------------------------------------
def _block_starts(run_start: int, run_end: int, block: int, stride: int) -> list[int]:
    if run_end - run_start + 1 < block:
        return []
    return list(range(run_start, run_end - block + 2, stride))


def build_bootstrap_pools(
    df: pd.DataFrame,
    block_hours: int = C.BLOCK_HOURS,
    stride: int = C.BLOCK_STRIDE_HOURS,
) -> dict[int, np.ndarray]:
    """Map each calendar month to the array of valid block start positions.

    A block is valid only if all of its hours are complete cases and it lies
    within a single month and year.
    """
    complete = df["complete_case"].to_numpy(dtype=bool)
    month = df["month"].to_numpy(dtype=int)
    year = df["year"].to_numpy(dtype=int)
    n = len(df)
    pos = np.arange(n)

    pools: dict[int, list[int]] = {m: [] for m in range(1, 13)}
    for m in range(1, 13):
        for y in np.unique(year):
            seg = pos[(month == m) & (year == y)]
            if seg.size == 0:
                continue
            run_start: int | None = None
            prev: int | None = None
            for p in seg:
                p = int(p)
                if not complete[p]:
                    if run_start is not None:
                        pools[m].extend(_block_starts(run_start, prev, block_hours, stride))
                        run_start, prev = None, None
                    continue
                if run_start is None:
                    run_start = p
                elif p != prev + 1:
                    pools[m].extend(_block_starts(run_start, prev, block_hours, stride))
                    run_start = p
                prev = p
            if run_start is not None:
                pools[m].extend(_block_starts(run_start, prev, block_hours, stride))

    out = {m: np.asarray(sorted(v), dtype=np.int64) for m, v in pools.items()}
    empty = [m for m, v in out.items() if v.size == 0]
    if empty:
        raise RuntimeError(f"no valid bootstrap blocks for month(s) {empty}")
    return out


def pool_summary(pools: dict[int, np.ndarray]) -> dict:
    return {
        C.MONTH_NAMES[m]: {
            "candidate_blocks": int(pools[m].size),
            "hours_represented": int(pools[m].size * C.BLOCK_HOURS),
        }
        for m in range(1, 13)
    }


# --------------------------------------------------------------------------
# Truncated turbine parameters
# --------------------------------------------------------------------------
def sample_turbine_params(rng: np.random.Generator, n: int) -> tuple[np.ndarray, np.ndarray]:
    """Sample Cp and eta once per scenario from truncated normals."""
    a_cp, b_cp = (C.CP_BOUNDS[0] - C.CP_NOMINAL) / C.CP_SD, (C.CP_BOUNDS[1] - C.CP_NOMINAL) / C.CP_SD
    a_eta, b_eta = (C.ETA_BOUNDS[0] - C.ETA_NOMINAL) / C.ETA_SD, (C.ETA_BOUNDS[1] - C.ETA_NOMINAL) / C.ETA_SD
    cp = stats.truncnorm.rvs(a_cp, b_cp, loc=C.CP_NOMINAL, scale=C.CP_SD, size=n, random_state=rng)
    eta = stats.truncnorm.rvs(a_eta, b_eta, loc=C.ETA_NOMINAL, scale=C.ETA_SD, size=n, random_state=rng)
    return cp, eta


# --------------------------------------------------------------------------
# One chunk of scenarios
# --------------------------------------------------------------------------
def _simulate_chunk(
    rng: np.random.Generator,
    pools: dict[int, np.ndarray],
    wind_global: np.ndarray,
    temp_global: np.ndarray,
    pres_global: np.ndarray,
    cp: np.ndarray,
    eta: np.ndarray,
    power_bins: np.ndarray | None = None,
) -> dict:
    s = cp.size
    wind = np.empty((s, C.N_HOURS_YEAR), dtype=np.float64)
    temp = np.empty((s, C.N_HOURS_YEAR), dtype=np.float64)
    pres = np.empty((s, C.N_HOURS_YEAR), dtype=np.float64)

    block = C.BLOCK_HOURS
    for m in range(1, 13):
        length = C.MONTH_HOURS[m]
        n_blocks = -(-length // block)  # ceil division
        starts_pool = pools[m]
        starts = starts_pool[rng.integers(0, starts_pool.size, size=(s, n_blocks))]
        idx = (starts[:, :, None] + np.arange(block, dtype=np.int64)[None, None, :]).reshape(s, n_blocks * block)[:, :length]
        off = MONTH_OFFSET[m]
        wind[:, off : off + length] = wind_global[idx]
        temp[:, off : off + length] = temp_global[idx]
        pres[:, off : off + length] = pres_global[idx]

    rho = air_density_from_surface(temp, pres)
    p_mw = power_mw(wind, rho, cp[:, None], eta[:, None])

    aep = p_mw.sum(axis=1)  # MW * 1 h -> MWh
    hist = None
    if power_bins is not None:
        hist = np.zeros(power_bins.size - 1, dtype=np.int64)
        for row in p_mw:
            hist += np.histogram(row, bins=power_bins)[0]

    return {
        "aep_mwh": aep,
        "mean_power_mw": aep / C.N_HOURS_YEAR,
        "mean_wind_mps": wind.mean(axis=1),
        "mean_rho_kg_m3": rho.mean(axis=1),
        "power_histogram": hist,
        "cp": cp,
        "eta": eta,
    }


# --------------------------------------------------------------------------
# Full simulation
# --------------------------------------------------------------------------
@dataclass
class SimulationResult:
    aep_mwh: np.ndarray
    cf: np.ndarray
    mean_power_mw: np.ndarray
    mean_wind_mps: np.ndarray
    mean_rho_kg_m3: np.ndarray
    cp: np.ndarray
    eta: np.ndarray
    power_histogram: np.ndarray
    power_bins: np.ndarray
    seed: int
    n_scenarios: int
    pools: dict = field(default_factory=dict)

    def summary(self) -> dict:
        from .statistical_analysis import summarise

        return summarise(self)


def simulate(
    df: pd.DataFrame,
    n_scenarios: int = C.N_SCENARIOS,
    seed: int = C.SEED,
    chunk: int = C.CHUNK_SCENARIOS,
    collect_histogram: bool = True,
) -> SimulationResult:
    """Run the seasonal block-bootstrap Monte Carlo simulation."""
    if n_scenarios <= 0:
        raise ValueError("n_scenarios must be positive")

    wind_global = df["wind_speed_100m"].to_numpy(dtype=float)
    temp_global = df["temperature_2m"].to_numpy(dtype=float)
    pres_global = df["surface_pressure"].to_numpy(dtype=float)
    pools = build_bootstrap_pools(df)

    power_bins = np.linspace(0.0, C.TURBINE.rated_power_mw * 1.025, 104)
    hist_total = np.zeros(power_bins.size - 1, dtype=np.int64)

    rng = np.random.Generator(np.random.PCG64(seed))
    aep_chunks, mean_p_chunks, mean_w_chunks, mean_rho_chunks, cp_chunks, eta_chunks = [], [], [], [], [], []

    for start in range(0, n_scenarios, chunk):
        n = min(chunk, n_scenarios - start)
        cp, eta = sample_turbine_params(rng, n)
        out = _simulate_chunk(
            rng, pools, wind_global, temp_global, pres_global, cp, eta,
            power_bins=power_bins if collect_histogram else None,
        )
        aep_chunks.append(out["aep_mwh"])
        mean_p_chunks.append(out["mean_power_mw"])
        mean_w_chunks.append(out["mean_wind_mps"])
        mean_rho_chunks.append(out["mean_rho_kg_m3"])
        cp_chunks.append(out["cp"])
        eta_chunks.append(out["eta"])
        if collect_histogram:
            hist_total += out["power_histogram"]

    aep = np.concatenate(aep_chunks)
    result = SimulationResult(
        aep_mwh=aep,
        cf=capacity_factor(aep),
        mean_power_mw=np.concatenate(mean_p_chunks),
        mean_wind_mps=np.concatenate(mean_w_chunks),
        mean_rho_kg_m3=np.concatenate(mean_rho_chunks),
        cp=np.concatenate(cp_chunks),
        eta=np.concatenate(eta_chunks),
        power_histogram=hist_total,
        power_bins=power_bins,
        seed=seed,
        n_scenarios=n_scenarios,
        pools={C.MONTH_NAMES[m]: int(pools[m].size) for m in range(1, 13)},
    )
    _validate_result(result)
    return result


def _validate_result(result: SimulationResult) -> None:
    """Physical-consistency checks on the scenario-level output."""
    if not np.all(np.isfinite(result.aep_mwh)):
        raise AssertionError("non-finite AEP encountered")
    if np.any(result.aep_mwh < 0.0):
        raise AssertionError("negative AEP encountered")
    if np.any(result.cf < 0.0) or np.any(result.cf > 1.0):
        raise AssertionError("capacity factor outside [0, 1]")
    if np.any(result.mean_power_mw < 0.0) or np.any(result.mean_power_mw > C.TURBINE.rated_power_mw + 1e-9):
        raise AssertionError("mean power outside [0, P_rated]")
    if np.any(result.cp < C.CP_BOUNDS[0]) or np.any(result.cp > C.CP_BOUNDS[1]):
        raise AssertionError("Cp outside approved bounds")
    if np.any(result.eta < C.ETA_BOUNDS[0]) or np.any(result.eta > C.ETA_BOUNDS[1]):
        raise AssertionError("eta outside approved bounds")
    if np.any(result.cp > C.BETZ_LIMIT):
        raise AssertionError("Cp exceeds the Betz limit")


# --------------------------------------------------------------------------
# Deterministic baseline
# --------------------------------------------------------------------------
def deterministic_baseline(df: pd.DataFrame, turbine: C.TurbineSpec = C.TURBINE) -> pd.DataFrame:
    """Nominal-parameter (Cp=0.359, eta=0.94) AEP for each observed year."""
    rows = []
    for year, g in df.groupby("year"):
        p = power_mw(
            g["wind_speed_100m"].to_numpy(float),
            g["air_density_kg_m3"].to_numpy(float),
            C.CP_NOMINAL,
            C.ETA_NOMINAL,
            turbine,
        )
        hours = len(g)
        aep = float(p.sum())
        rows.append(
            {
                "year": int(year),
                "hours": int(hours),
                "aep_mwh": aep,
                "capacity_factor": aep / (turbine.rated_power_mw * hours),
                "mean_power_mw": aep / hours,
                "mean_wind_mps": float(g["wind_speed_100m"].mean()),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------
# Convergence (nested prefixes of one run)
# --------------------------------------------------------------------------
def convergence_table(result: SimulationResult, sizes: Iterable[int] = C.CONVERGENCE_SIZES) -> pd.DataFrame:
    """Metrics computed on nested prefixes of the same run.

    Because every prefix comes from one simulation with a single RNG stream, the
    comparison is a genuine nested-convergence check rather than a comparison of
    independent runs.
    """
    sizes = sorted({int(s) for s in sizes if 0 < int(s) <= result.n_scenarios})
    rows = []
    for n in sizes:
        aep = result.aep_mwh[:n]
        cf = result.cf[:n]
        rows.append(
            {
                "n_scenarios": n,
                "mean_aep_mwh": float(np.mean(aep)),
                "median_aep_mwh": float(np.median(aep)),
                "std_aep_mwh": float(np.std(aep, ddof=1)) if n > 1 else float("nan"),
                "p05_aep_mwh": float(np.percentile(aep, 5)),
                "p95_aep_mwh": float(np.percentile(aep, 95)),
                "mean_cf": float(np.mean(cf)),
                "p_cf_below_0.25": float(np.mean(cf < C.CF_THRESHOLD)),
                "mc_se_mean_aep_mwh": float(np.std(aep, ddof=1) / np.sqrt(n)) if n > 1 else float("nan"),
            }
        )
    return pd.DataFrame(rows)


if __name__ == "__main__":
    from .data_processing import load_processed

    res = simulate(load_processed(), n_scenarios=1000)
    print(res.summary())