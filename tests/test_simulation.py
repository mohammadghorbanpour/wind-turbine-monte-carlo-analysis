"""Tests for the simulation pipeline (bootstrap, Monte Carlo, summaries, CIs)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from src import config as C
from src.data_processing import derive
from src.simulation import (
    build_bootstrap_pools,
    convergence_table,
    deterministic_baseline,
    simulate,
)
from src.statistical_analysis import summarise, summarise_baseline, wilson_ci


# --------------------------------------------------------------------------
# Synthetic fixture (clearly labelled as simulated test data)
# --------------------------------------------------------------------------
def make_synthetic_frame(years: int = 2) -> pd.DataFrame:
    """Two years of synthetic hourly weather, generated for tests only."""
    periods = 8760 * years + (8784 - 8760 if years >= 2 else 0)
    idx = pd.date_range("2015-01-01", periods=periods, freq="h", tz="UTC")
    rng = np.random.default_rng(1234)
    doy = idx.dayofyear.to_numpy()
    wind = 7.5 + 2.5 * np.cos(2 * np.pi * (doy - 20) / 365.25) + rng.normal(0.0, 1.4, periods)
    wind = np.clip(wind, 0.2, None)
    temp = 9.0 + 8.0 * np.sin(2 * np.pi * (doy - 100) / 365.25) + rng.normal(0.0, 2.0, periods)
    pres = 1013.0 + rng.normal(0.0, 8.0, periods)
    wdir = rng.uniform(0.0, 360.0, periods)
    raw = pd.DataFrame(
        {
            "time": idx,
            "wind_speed_100m": wind,
            "temperature_2m": temp,
            "surface_pressure": pres,
            "wind_direction_100m": wdir,
        }
    )
    return derive(raw)


@pytest.fixture(scope="module")
def frame():
    return make_synthetic_frame()


# --------------------------------------------------------------------------
# Bootstrap pools
# --------------------------------------------------------------------------
def test_pools_cover_every_month(frame):
    pools = build_bootstrap_pools(frame)
    assert set(pools) == set(range(1, 13))
    for m, starts in pools.items():
        assert starts.size > 0, f"month {m} has no blocks"


def test_pool_blocks_are_contiguous_and_complete(frame):
    pools = build_bootstrap_pools(frame)
    complete = frame["complete_case"].to_numpy(bool)
    for m, starts in pools.items():
        for s in starts[:20]:
            idx = np.arange(s, s + C.BLOCK_HOURS)
            assert complete[idx].all()
            assert frame["month"].to_numpy()[idx[0]] == m


# --------------------------------------------------------------------------
# Simulation
# --------------------------------------------------------------------------
def test_simulate_shapes(frame):
    res = simulate(frame, n_scenarios=50, seed=42)
    assert res.aep_mwh.shape == (50,)
    assert res.cf.shape == (50,)
    assert res.cp.shape == (50,)
    assert res.eta.shape == (50,)


def test_simulate_is_reproducible(frame):
    a = simulate(frame, n_scenarios=40, seed=2026)
    b = simulate(frame, n_scenarios=40, seed=2026)
    assert np.array_equal(a.aep_mwh, b.aep_mwh)
    assert np.array_equal(a.cf, b.cf)


def test_simulate_different_seed_differs(frame):
    a = simulate(frame, n_scenarios=40, seed=1)
    b = simulate(frame, n_scenarios=40, seed=2)
    assert not np.array_equal(a.aep_mwh, b.aep_mwh)


def test_simulate_physical_consistency(frame):
    res = simulate(frame, n_scenarios=80, seed=7)
    assert np.all(res.aep_mwh >= 0.0)
    assert np.all(res.cf >= 0.0) and np.all(res.cf <= 1.0)
    assert np.all(res.mean_power_mw >= 0.0)
    assert np.all(res.mean_power_mw <= C.TURBINE.rated_power_mw + 1e-9)
    assert np.all(res.cp >= C.CP_BOUNDS[0]) and np.all(res.cp <= C.CP_BOUNDS[1])
    assert np.all(res.eta >= C.ETA_BOUNDS[0]) and np.all(res.eta <= C.ETA_BOUNDS[1])
    assert np.all(res.cp <= C.BETZ_LIMIT)


def test_simulate_rejects_zero_scenarios(frame):
    with pytest.raises(ValueError):
        simulate(frame, n_scenarios=0)


def test_aep_matches_cf_identity(frame):
    res = simulate(frame, n_scenarios=30, seed=11)
    expected_cf = res.aep_mwh / (C.TURBINE.rated_power_mw * C.N_HOURS_YEAR)
    assert np.allclose(res.cf, expected_cf)


def test_power_histogram_is_present(frame):
    res = simulate(frame, n_scenarios=20, seed=3)
    assert res.power_histogram.sum() == 20 * C.N_HOURS_YEAR


# --------------------------------------------------------------------------
# Deterministic baseline
# --------------------------------------------------------------------------
def test_deterministic_baseline(frame):
    base = deterministic_baseline(frame)
    assert list(base["year"]) == sorted(frame["year"].unique())
    assert np.all(base["aep_mwh"] > 0)
    assert np.all(base["capacity_factor"] > 0)
    assert np.all(base["capacity_factor"] < 1)


# --------------------------------------------------------------------------
# Convergence
# --------------------------------------------------------------------------
def test_convergence_table(frame):
    res = simulate(frame, n_scenarios=100, seed=5)
    conv = convergence_table(res, sizes=(10, 50, 100))
    assert len(conv) == 3
    assert conv["n_scenarios"].tolist() == [10, 50, 100]
    assert conv["mean_aep_mwh"].iloc[-1] == pytest.approx(res.aep_mwh.mean())
    assert np.all(conv["mc_se_mean_aep_mwh"] > 0)


# --------------------------------------------------------------------------
# Statistics
# --------------------------------------------------------------------------
def test_wilson_ci_bounds():
    lo, hi = wilson_ci(50, 100)
    assert 0.0 <= lo < 0.5 < hi <= 1.0
    assert (lo, hi) == pytest.approx((0.4038, 0.5962), abs=2e-3)


def test_wilson_ci_extremes():
    lo0, hi0 = wilson_ci(0, 100)
    assert lo0 == pytest.approx(0.0, abs=1e-12)
    lo1, hi1 = wilson_ci(100, 100)
    assert hi1 == pytest.approx(1.0, abs=1e-12)


def test_summarise_structure(frame):
    res = simulate(frame, n_scenarios=60, seed=9)
    s = summarise(res)
    a = s["aep_mwh"]
    assert a["mean"] == pytest.approx(res.aep_mwh.mean())
    assert a["median"] == pytest.approx(np.median(res.aep_mwh))
    assert a["std"] == pytest.approx(res.aep_mwh.std(ddof=1))
    assert a["p05"] <= a["p25"] <= a["median"] <= a["p75"] <= a["p95"]
    pr = s["probability_cf_below_threshold"]
    assert pr["successes"] == int(np.sum(res.cf < C.CF_THRESHOLD))
    assert pr["wilson_ci95"][0] <= pr["estimate"] <= pr["wilson_ci95"][1]
    assert s["expected_power_output_mw"]["mean"] > 0


def test_summarise_baseline(frame):
    base = deterministic_baseline(frame)
    b = summarise_baseline(base)
    assert b["n_years"] == len(base)
    assert b["aep_mwh_min"] <= b["aep_mwh_mean"] <= b["aep_mwh_max"]