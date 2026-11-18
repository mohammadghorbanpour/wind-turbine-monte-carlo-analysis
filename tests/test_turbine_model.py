"""Tests for the physical model (rotor area, air density, power curve, Weibull)."""

from __future__ import annotations

import numpy as np
import pytest

from src import config as C
from src.turbine_model import (
    air_density_from_surface,
    calibration_report,
    capacity_factor,
    fit_weibull,
    implied_rated_power_mw,
    power_curve,
    power_mw,
    rotor_swept_area,
    weibull_inverse_cdf,
)


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def test_swept_area_value():
    assert rotor_swept_area(45.0) == pytest.approx(np.pi * 45.0**2, rel=1e-12)
    assert rotor_swept_area(45.0) == pytest.approx(6361.725123519330, rel=1e-9)


@pytest.mark.parametrize("bad", [0.0, -1.0, np.nan, np.inf])
def test_swept_area_rejects_invalid(bad):
    with pytest.raises(ValueError):
        rotor_swept_area(bad)


# --------------------------------------------------------------------------
# Air density
# --------------------------------------------------------------------------
def test_air_density_at_standard_conditions():
    # With the hydrostatic correction to hub height this is slightly below the
    # sea-level value; at hub height 0 it must reduce exactly to p/(R T).
    rho_hub = float(air_density_from_surface(15.0, 1013.25))
    expected = 101325.0 * np.exp(-C.G * C.TURBINE.hub_height_m / (C.R_AIR * 288.15)) / (
        C.R_AIR * 288.15
    )
    assert rho_hub == pytest.approx(expected, rel=1e-9)
    assert rho_hub == pytest.approx(1.2106, rel=1e-3)
    rho_0 = float(air_density_from_surface(15.0, 1013.25, hub_height_m=0.0))
    assert rho_0 == pytest.approx(1.2250, rel=1e-4)


def test_air_density_positive_and_finite_over_range():
    temp = np.linspace(-40.0, 45.0, 50)
    pres = np.linspace(950.0, 1040.0, 50)
    rho = air_density_from_surface(temp, pres)
    assert np.all(np.isfinite(rho))
    assert np.all(rho > 0.0)
    assert np.all(rho < 1.6)


def test_air_density_colder_is_denser():
    rho_cold = air_density_from_surface(-10.0, 1013.25)
    rho_warm = air_density_from_surface(30.0, 1013.25)
    assert rho_cold > rho_warm


def test_air_density_rejects_nonphysical_temperature():
    with pytest.raises(ValueError):
        air_density_from_surface(-300.0, 1013.25)


# --------------------------------------------------------------------------
# Power curve
# --------------------------------------------------------------------------
def test_power_zero_below_cut_in():
    v = np.array([0.0, 1.0, 2.999])
    p = power_mw(v, 1.225, C.CP_NOMINAL, C.ETA_NOMINAL)
    assert np.all(p == 0.0)


def test_power_zero_at_and_above_cut_out():
    v = np.array([C.TURBINE.cut_out_speed, 25.5, 30.0, 40.0])
    p = power_mw(v, 1.225, C.CP_NOMINAL, C.ETA_NOMINAL)
    assert np.all(p == 0.0)


def test_power_positive_at_cut_in():
    p = power_mw(np.array([C.TURBINE.cut_in_speed]), 1.225, C.CP_NOMINAL, C.ETA_NOMINAL)
    assert p[0] > 0.0


def test_power_never_exceeds_rated_and_is_nonnegative():
    v = np.linspace(0.0, 35.0, 500)
    p = power_mw(v, 1.225, C.CP_NOMINAL, C.ETA_NOMINAL)
    assert np.all(p >= 0.0)
    assert np.all(p <= C.TURBINE.rated_power_mw + 1e-12)


def test_power_reaches_rated_at_rated_speed():
    p = implied_rated_power_mw(C.TURBINE.rated_speed, C.NOMINAL_RHO,
                               C.CP_NOMINAL, C.ETA_NOMINAL)
    assert p == pytest.approx(C.TURBINE.rated_power_mw, rel=5e-3)


def test_power_is_monotone_in_wind_speed_below_rated():
    v = np.linspace(C.TURBINE.cut_in_speed, C.TURBINE.rated_speed, 200)
    p = power_mw(v, 1.225, C.CP_NOMINAL, C.ETA_NOMINAL)
    assert np.all(np.diff(p) >= -1e-12)


def test_power_curve_helper_matches_power_mw():
    v = np.array([4.0, 8.0, 12.0])
    p1 = power_curve(v, 1.225, C.CP_NOMINAL, C.ETA_NOMINAL)
    p2 = power_mw(v, np.full_like(v, 1.225), C.CP_NOMINAL, C.ETA_NOMINAL)
    assert np.allclose(p1, p2)


def test_power_increases_with_air_density():
    v = np.array([9.0])
    lo = power_mw(v, 1.20, C.CP_NOMINAL, C.ETA_NOMINAL)
    hi = power_mw(v, 1.30, C.CP_NOMINAL, C.ETA_NOMINAL)
    assert hi[0] > lo[0]


@pytest.mark.parametrize("cp", [0.0, -0.1, C.BETZ_LIMIT + 0.01, 0.9])
def test_power_rejects_invalid_cp(cp):
    with pytest.raises(ValueError):
        power_mw(np.array([10.0]), 1.225, cp, C.ETA_NOMINAL)


@pytest.mark.parametrize("eta", [0.0, -0.1, 1.01])
def test_power_rejects_invalid_eta(eta):
    with pytest.raises(ValueError):
        power_mw(np.array([10.0]), 1.225, C.CP_NOMINAL, eta)


def test_power_rejects_nonpositive_density():
    with pytest.raises(ValueError):
        power_mw(np.array([10.0]), 0.0, C.CP_NOMINAL, C.ETA_NOMINAL)


# --------------------------------------------------------------------------
# Calibration
# --------------------------------------------------------------------------
def test_calibration_is_consistent():
    cal = calibration_report()
    assert cal["ratio_raw_over_rated_at_vrated"] == pytest.approx(1.0, rel=5e-3)
    assert cal["cp_fraction_of_betz"] < 1.0
    assert cal["swept_area_m2"] == pytest.approx(rotor_swept_area(45.0))


# --------------------------------------------------------------------------
# Weibull
# --------------------------------------------------------------------------
def test_weibull_fit_recovers_parameters():
    rng = np.random.default_rng(7)
    sample = rng.weibull(2.0, size=200_000) * 9.0
    fit = fit_weibull(sample)
    assert fit["shape_k"] == pytest.approx(2.0, rel=0.02)
    assert fit["scale_c"] == pytest.approx(9.0, rel=0.02)
    assert fit["ks_statistic"] < 0.01


def test_weibull_fit_rejects_tiny_sample():
    with pytest.raises(ValueError):
        fit_weibull(np.array([1.0, 2.0, 3.0]))


def test_weibull_inverse_cdf_matches_median():
    k, c = 2.2, 8.5
    q = weibull_inverse_cdf(0.5, k, c)
    expected = c * np.log(2.0) ** (1.0 / k)
    assert q == pytest.approx(expected, rel=1e-12)


def test_weibull_inverse_cdf_rejects_bad_input():
    with pytest.raises(ValueError):
        weibull_inverse_cdf(1.5, 2.0, 8.0)
    with pytest.raises(ValueError):
        weibull_inverse_cdf(0.5, 0.0, 8.0)


# --------------------------------------------------------------------------
# Capacity factor
# --------------------------------------------------------------------------
def test_capacity_factor_definition():
    aep = C.TURBINE.rated_power_mw * C.N_HOURS_YEAR  # full power all year
    assert capacity_factor(aep) == pytest.approx(1.0)
    assert capacity_factor(0.0) == 0.0


def test_capacity_factor_rejects_bad_hours():
    with pytest.raises(ValueError):
        capacity_factor(1000.0, hours=0)