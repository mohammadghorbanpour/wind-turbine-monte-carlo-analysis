"""Physical model: geometry, air density, and the simplified turbine power curve.

Model
-----
Swept rotor area
    A = pi R^2

Air density from 2 m temperature and surface pressure
    T_K  = T_C + 273.15
    p_s  = 100 * p_hPa                      (hPa -> Pa)
    p_h  = p_s * exp(-g H_h / (R_air T_K))  (hydrostatic to hub height)
    rho  = p_h / (R_air T_K)

Electrical power before clipping
    P_raw = 0.5 * rho * A * V^3 * Cp * eta

Operational power
    P = 0                            V < V_ci
    P = min(P_r, P_raw)              V_ci <= V < V_co
    P = 0                            V >= V_co

The model is intentionally simplified: Cp and eta are constants per scenario,
there is no pitch/tip-speed-ratio control, no turbulence, no icing, and no
wake or array losses.  It is NOT an OEM-certified power curve.
"""

from __future__ import annotations

import numpy as np

from . import config as C


# --------------------------------------------------------------------------
# Geometry
# --------------------------------------------------------------------------
def rotor_swept_area(radius_m: float) -> float:
    """Swept rotor area A = pi R^2 [m^2]."""
    radius_m = float(radius_m)
    if not np.isfinite(radius_m) or radius_m <= 0.0:
        raise ValueError(f"rotor radius must be a positive finite number, got {radius_m!r}")
    return float(np.pi * radius_m**2)


# --------------------------------------------------------------------------
# Air density
# --------------------------------------------------------------------------
def air_density_from_surface(
    temperature_c,
    surface_pressure_hpa,
    hub_height_m: float = C.TURBINE.hub_height_m,
    g: float = C.G,
    r_air: float = C.R_AIR,
):
    """Derive air density [kg m^-3] at hub height.

    Parameters
    ----------
    temperature_c : 2 m air temperature [degC] (used as a hub-height proxy)
    surface_pressure_hpa : surface pressure [hPa]
    hub_height_m : hub height [m]

    Notes
    -----
    ``temperature_2m`` is NOT the hub-height temperature and ``surface_pressure``
    is NOT the hub-height pressure.  The hydrostatic correction below is a
    first-order approximation; the resulting density is a derived estimate, not a
    measurement.
    """
    temp_c = np.asarray(temperature_c, dtype=float)
    p_hpa = np.asarray(surface_pressure_hpa, dtype=float)

    with np.errstate(invalid="ignore"):
        temp_k = temp_c + C.KELVIN_OFFSET
        p_s = 100.0 * p_hpa
        p_h = p_s * np.exp(-g * hub_height_m / (r_air * temp_k))
        rho = p_h / (r_air * temp_k)

    invalid = ~np.isfinite(rho) | (temp_k <= 0.0) | (p_hpa <= 0.0)
    if np.any(invalid):
        raise ValueError(
            f"air density is non-finite or non-physical for {int(np.sum(invalid))} "
            "input(s); check temperature (K) and pressure (hPa) ranges"
        )
    if np.any(rho <= 0.0):
        raise ValueError("air density must be strictly positive")
    return rho


# --------------------------------------------------------------------------
# Power curve
# --------------------------------------------------------------------------
def _check_cp_eta(cp, eta):
    """Validate Cp and eta (scalars or broadcastable arrays) and return arrays."""
    cp_a = np.asarray(cp, dtype=float)
    eta_a = np.asarray(eta, dtype=float)
    if not np.all(np.isfinite(cp_a)) or np.any(cp_a <= 0.0) or np.any(cp_a > C.BETZ_LIMIT):
        raise ValueError(
            f"all Cp values must lie in (0, {C.BETZ_LIMIT:.4f}] (Betz limit); got {cp!r}"
        )
    if not np.all(np.isfinite(eta_a)) or np.any(eta_a <= 0.0) or np.any(eta_a > 1.0):
        raise ValueError(f"all eta values must lie in (0, 1]; got {eta!r}")
    return cp_a, eta_a


def raw_power_w(wind_speed, air_density, cp: float, eta: float,
                turbine: C.TurbineSpec = C.TURBINE):
    """Electrical power before rated-power clipping and cut-out logic [W]."""
    cp, eta = _check_cp_eta(cp, eta)
    v = np.asarray(wind_speed, dtype=float)
    rho = np.asarray(air_density, dtype=float)
    if np.any(rho <= 0.0):
        raise ValueError("air density must be strictly positive")
    return 0.5 * rho * turbine.swept_area_m2 * np.power(v, 3) * cp * eta


def power_mw(wind_speed, air_density, cp: float, eta: float,
             turbine: C.TurbineSpec = C.TURBINE):
    """Operational electrical power [MW] with cut-in/rated/cut-out logic.

    Vectorised over ``wind_speed`` and ``air_density`` (which must broadcast).
    """
    cp, eta = _check_cp_eta(cp, eta)
    v = np.asarray(wind_speed, dtype=float)
    rho = np.asarray(air_density, dtype=float)
    if np.any(rho <= 0.0):
        raise ValueError("air density must be strictly positive")

    p_raw_w = raw_power_w(v, rho, cp, eta, turbine)
    p_raw_mw = p_raw_w / 1e6

    operating = (v >= turbine.cut_in_speed) & (v < turbine.cut_out_speed)
    p = np.where(operating, np.minimum(turbine.rated_power_mw, p_raw_mw), 0.0)
    return p


def power_curve(wind_speeds, air_density: float, cp: float, eta: float,
                turbine: C.TurbineSpec = C.TURBINE):
    """Convenience wrapper for plotting a 1-D power curve."""
    v = np.asarray(wind_speeds, dtype=float)
    rho = np.full_like(v, float(air_density), dtype=float)
    return power_mw(v, rho, cp, eta, turbine)


def implied_rated_power_mw(wind_speed: float, air_density: float, cp: float,
                           eta: float, turbine: C.TurbineSpec = C.TURBINE) -> float:
    """Raw (unclipped) power [MW] at a single wind speed - used for calibration."""
    return float(raw_power_w(wind_speed, air_density, cp, eta, turbine) / 1e6)


# --------------------------------------------------------------------------
# Calibration check
# --------------------------------------------------------------------------
def calibration_report(turbine: C.TurbineSpec = C.TURBINE) -> dict:
    """Verify that the nominal Cp/eta reproduce rated power at rated wind speed."""
    p_at_rated = implied_rated_power_mw(
        turbine.rated_speed, C.NOMINAL_RHO, C.CP_NOMINAL, C.ETA_NOMINAL, turbine
    )
    p_at_cut_in = implied_rated_power_mw(
        turbine.cut_in_speed, C.NOMINAL_RHO, C.CP_NOMINAL, C.ETA_NOMINAL, turbine
    )
    return {
        "swept_area_m2": turbine.swept_area_m2,
        "nominal_cp": C.CP_NOMINAL,
        "nominal_eta": C.ETA_NOMINAL,
        "betz_limit": C.BETZ_LIMIT,
        "cp_fraction_of_betz": C.CP_NOMINAL / C.BETZ_LIMIT,
        "nominal_air_density_kg_m3": C.NOMINAL_RHO,
        "raw_power_at_rated_speed_mw": p_at_rated,
        "rated_power_mw": turbine.rated_power_mw,
        "ratio_raw_over_rated_at_vrated": p_at_rated / turbine.rated_power_mw,
        "raw_power_at_cut_in_mw": p_at_cut_in,
        "note": (
            "Nominal Cp=0.359 with eta=0.94 and rho=1.225 kg/m3 reproduces "
            "rated power at the rated wind speed by construction; this is a "
            "calibration identity, not an empirical validation."
        ),
    }


# --------------------------------------------------------------------------
# Weibull descriptive model
# --------------------------------------------------------------------------
def fit_weibull(wind_speed) -> dict:
    """Fit a two-parameter Weibull (k shape, c scale) by maximum likelihood.

    Returns the parameters plus a Kolmogorov-Smirnov goodness-of-fit statistic
    against the fitted distribution.  This is a *descriptive* model only: it does
    not reproduce autocorrelation, seasonality, or the exact tail behaviour, so
    the main simulation uses block resampling of the observed series instead.
    """
    from scipy import stats

    v = np.asarray(wind_speed, dtype=float)
    v = v[np.isfinite(v)]
    if v.size < 10:
        raise ValueError("need at least 10 finite wind speeds to fit a Weibull")

    k, loc, c = stats.weibull_min.fit(v, floc=0.0)
    ks_stat, ks_p = stats.kstest(v, "weibull_min", args=(k, loc, c))
    return {
        "shape_k": float(k),
        "scale_c": float(c),
        "location": float(loc),
        "n": int(v.size),
        "ks_statistic": float(ks_stat),
        "ks_p_value": float(ks_p),
        "mean_observed": float(np.mean(v)),
        "mean_fitted": float(c * _gamma(1.0 + 1.0 / k)),
    }


def _gamma(x: float) -> float:
    """Gamma function via math.gamma (kept local to avoid a scipy import cycle)."""
    import math

    return math.gamma(x)


def weibull_inverse_cdf(u, shape_k: float, scale_c: float):
    """Closed-form Weibull quantile function (inverse CDF).

    Used by the Sobol experiment so that wind speeds can be generated from
    independent uniform draws without importing scipy inside the inner loop.
    """
    u = np.asarray(u, dtype=float)
    if np.any((u < 0.0) | (u > 1.0)):
        raise ValueError("u must lie in [0, 1]")
    if shape_k <= 0.0 or scale_c <= 0.0:
        raise ValueError("shape and scale must be positive")
    with np.errstate(divide="ignore"):
        return scale_c * np.power(-np.log1p(-u), 1.0 / shape_k)


def capacity_factor(aep_mwh, rated_power_mw: float = C.TURBINE.rated_power_mw,
                    hours: int = C.N_HOURS_YEAR):
    """Capacity factor = AEP / (P_rated * hours), dimensionless in [0, 1]."""
    aep = np.asarray(aep_mwh, dtype=float)
    if hours <= 0:
        raise ValueError("hours must be positive")
    return aep / (rated_power_mw * hours)