"""Central configuration: physical constants, turbine assumptions, random seeds.

Every number that drives the analysis lives here so that the whole study can be
reproduced from a single, documented source.  Values marked as assumptions are
NOT manufacturer specifications; they are explicit engineering modelling
choices for a hypothetical 2 MW turbine.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

# --------------------------------------------------------------------------
# Paths
# --------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
RESULTS_DIR = PROJECT_ROOT / "results"
FIGURES_DIR = RESULTS_DIR / "figures"
TABLES_DIR = RESULTS_DIR / "tables"
REPORT_DIR = PROJECT_ROOT / "report"
VIDEO_DIR = PROJECT_ROOT / "video"

RAW_CSV = RAW_DIR / "openmeteo_era5_cuxhaven_2015_2024.csv"
RAW_PROVENANCE = RAW_DIR / "openmeteo_era5_cuxhaven_2015_2024.provenance.json"
PROCESSED_CSV = PROCESSED_DIR / "cuxhaven_era5_hourly_2015_2024_processed.csv"
QC_JSON = PROCESSED_DIR / "data_quality_report.json"
QC_MD = PROCESSED_DIR / "data_quality_report.md"

# --------------------------------------------------------------------------
# Physical constants (SI)
# --------------------------------------------------------------------------
G = 9.80665          # standard gravity, m s^-2
R_AIR = 287.05       # specific gas constant for dry air, J kg^-1 K^-1
KELVIN_OFFSET = 273.15
NOMINAL_RHO = 1.225  # kg m^-3, ISA sea-level reference used only for calibration

# --------------------------------------------------------------------------
# Site / data request
# --------------------------------------------------------------------------
SITE_NAME = "Cuxhaven, Germany"
LATITUDE = 53.86
LONGITUDE = 8.69
START_DATE = "2015-01-01"
END_DATE = "2024-12-31"
TIMEZONE = "UTC"
MODEL = "era5"
CELL_SELECTION = "land"
WIND_SPEED_UNIT = "ms"
API_ENDPOINT = "https://archive-api.open-meteo.com/v1/archive"
VARIABLES = [
    "wind_speed_100m",
    "temperature_2m",
    "surface_pressure",
    "wind_direction_100m",
]

# --------------------------------------------------------------------------
# Hypothetical turbine (ASSUMPTIONS, not a commercial specification)
# --------------------------------------------------------------------------
@dataclass(frozen=True)
class TurbineSpec:
    """Simplified horizontal-axis turbine used throughout the study."""

    rated_power_mw: float = 2.0
    rotor_radius_m: float = 45.0
    hub_height_m: float = 100.0
    cut_in_speed: float = 3.0
    rated_speed: float = 11.5
    cut_out_speed: float = 25.0

    @property
    def swept_area_m2(self) -> float:
        import math

        return math.pi * self.rotor_radius_m**2

    @property
    def rated_power_w(self) -> float:
        return self.rated_power_mw * 1e6

    def as_dict(self) -> dict:
        return {
            "rated_power_mw": self.rated_power_mw,
            "rotor_radius_m": self.rotor_radius_m,
            "hub_height_m": self.hub_height_m,
            "cut_in_speed_mps": self.cut_in_speed,
            "rated_speed_mps": self.rated_speed,
            "cut_out_speed_mps": self.cut_out_speed,
            "swept_area_m2": self.swept_area_m2,
        }


TURBINE = TurbineSpec()

# --------------------------------------------------------------------------
# Uncertain turbine parameters (engineering assumptions, not measured data)
# --------------------------------------------------------------------------
CP_NOMINAL = 0.359
CP_SD = 0.015
CP_BOUNDS = (0.30, 0.50)
BETZ_LIMIT = 16.0 / 27.0  # 0.592592...

ETA_NOMINAL = 0.94
ETA_SD = 0.01
ETA_BOUNDS = (0.88, 0.98)

# --------------------------------------------------------------------------
# Simulation design
# --------------------------------------------------------------------------
SEED = 20261118
N_SCENARIOS = 10_000
N_HOURS_YEAR = 8760          # canonical non-leap year
BLOCK_HOURS = 168            # 7-day blocks
BLOCK_STRIDE_HOURS = 24      # candidate block starts every 24 h within a month
CHUNK_SCENARIOS = 100        # memory-bounded batch size
CONVERGENCE_SIZES = (100, 1_000, 5_000, 10_000)
CF_THRESHOLD = 0.25          # low-capacity-factor (energy adequacy) threshold

# Canonical non-leap month lengths (hours); February 29 is excluded by design.
MONTH_HOURS = {
    1: 744, 2: 672, 3: 744, 4: 720, 5: 744, 6: 720,
    7: 744, 8: 744, 9: 720, 10: 744, 11: 720, 12: 744,
}
MONTH_NAMES = {
    1: "January", 2: "February", 3: "March", 4: "April", 5: "May",
    6: "June", 7: "July", 8: "August", 9: "September", 10: "October",
    11: "November", 12: "December",
}
SEASONS = {
    "DJF": (12, 1, 2),
    "MAM": (3, 4, 5),
    "JJA": (6, 7, 8),
    "SON": (9, 10, 11),
}

# --------------------------------------------------------------------------
# Weibull wind model (descriptive only; the main simulation uses resampling)
# --------------------------------------------------------------------------
WEIBULL_K_RANGE = (1.8, 2.6)
WEIBULL_C_RANGE = (7.0, 10.0)

# --------------------------------------------------------------------------
# Sobol sensitivity experiment (independent inputs by construction)
# --------------------------------------------------------------------------
SOBOL_N = 1024
SOBOL_BOUNDS = {
    # name: (lower, upper)  -- uniform, independent by design
    "weibull_k": WEIBULL_K_RANGE,
    "weibull_c": WEIBULL_C_RANGE,
    "cp": (0.30, 0.45),
    "eta": (0.88, 0.98),
    "rho_factor": (0.95, 1.05),
}
SOBOL_NAMES = list(SOBOL_BOUNDS.keys())

# --------------------------------------------------------------------------
# Physical plausibility ranges used only for QC flags (never for filtering)
# --------------------------------------------------------------------------
PLAUSIBLE_RANGES = {
    "wind_speed_100m": (0.0, 60.0),        # m/s
    "temperature_2m": (-60.0, 60.0),       # degC
    "surface_pressure": (80_000.0, 110_000.0),  # Pa (hPa converted)
    "wind_direction_100m": (0.0, 360.0),   # degrees
}