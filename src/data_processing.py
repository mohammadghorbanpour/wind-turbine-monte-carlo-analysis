"""Load, validate, and enrich the raw ERA5 series; write a data-quality report.

Nothing is silently dropped, imputed, or replaced.  Missing and implausible
values are counted and reported; the simulation draws only from complete,
physically plausible hours and the number of excluded hours is stated in the QC
report and in the final writeup.
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from .turbine_model import air_density_from_surface

RAW_DTYPES = {
    "time": "string",
    "wind_speed_100m": "float64",
    "temperature_2m": "float64",
    "surface_pressure": "float64",
    "wind_direction_100m": "float64",
}


# --------------------------------------------------------------------------
# Loading
# --------------------------------------------------------------------------
def load_raw(path: Path = C.RAW_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(
            f"{path} not found. Run 'python -m src.data_loader' first."
        )
    df = pd.read_csv(path)
    missing_cols = [c for c in RAW_DTYPES if c not in df.columns]
    if missing_cols:
        raise ValueError(f"raw file is missing required columns: {missing_cols}")

    df["time"] = pd.to_datetime(df["time"], utc=False, errors="coerce")
    for col in ["wind_speed_100m", "temperature_2m", "surface_pressure", "wind_direction_100m"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")

    if df["time"].isna().any():
        raise ValueError(f"{int(df['time'].isna().sum())} timestamps could not be parsed")
    df = df.sort_values("time").reset_index(drop=True)
    return df


# --------------------------------------------------------------------------
# Derivation
# --------------------------------------------------------------------------
def derive(df: pd.DataFrame) -> pd.DataFrame:
    """Add physical and calendar columns; never modifies the raw values in place."""
    out = df.copy()

    out["surface_pressure_pa"] = out["surface_pressure"] * 100.0
    out["temperature_k"] = out["temperature_2m"] + C.KELVIN_OFFSET
    out["air_density_kg_m3"] = air_density_from_surface(
        out["temperature_2m"].to_numpy(),
        out["surface_pressure"].to_numpy(),
        hub_height_m=C.TURBINE.hub_height_m,
    )

    out["year"] = out["time"].dt.year
    out["month"] = out["time"].dt.month
    out["day"] = out["time"].dt.day
    out["hour"] = out["time"].dt.hour
    out["month_name"] = out["month"].map(C.MONTH_NAMES)
    out["season"] = out["month"].map(
        lambda m: next(name for name, months in C.SEASONS.items() if m in months)
    )
    out["is_leap_day"] = (out["month"] == 2) & (out["day"] == 29)

    required = ["wind_speed_100m", "temperature_2m", "surface_pressure"]
    out["complete_case"] = (
        np.isfinite(out[required].to_numpy(dtype=float)).all(axis=1)
        & np.isfinite(out["air_density_kg_m3"].to_numpy(dtype=float))
    )
    return out


# --------------------------------------------------------------------------
# QC audit
# --------------------------------------------------------------------------
def qc_audit(df: pd.DataFrame) -> dict:
    """Bounded, aggregate-only data-quality audit."""
    n_rows = int(len(df))
    start = pd.Timestamp(C.START_DATE)
    stop = pd.Timestamp(C.END_DATE) + pd.Timedelta(days=1)
    expected = pd.date_range(start, stop, freq="h", inclusive="left")
    expected_hours = int(len(expected))
    actual = pd.DatetimeIndex(df["time"])
    if actual.tz is not None:
        actual = actual.tz_convert("UTC").tz_localize(None)
    missing_idx = expected.difference(actual)
    dup_count = int(actual.duplicated().sum())

    report: dict = {
        "site": C.SITE_NAME,
        "period": {"start": C.START_DATE, "end": C.END_DATE, "timezone": C.TIMEZONE},
        "expected_hourly_records": expected_hours,
        "received_records": n_rows,
        "record_count_difference": n_rows - expected_hours,
        "completeness_pct": 100.0 * n_rows / expected_hours if expected_hours else float("nan"),
        "duplicate_timestamps": dup_count,
        "missing_timestamps": int(len(missing_idx)),
        "non_monotonic_timestamps": int((np.diff(actual.view("int64")) <= 0).sum())
        if n_rows > 1
        else 0,
        "duplicate_rows_full": int(df.duplicated().sum()),
        "columns": {},
        "per_year_records": {},
        "per_month_records": {},
        "leap_day_records": int(df["is_leap_day"].sum()) if "is_leap_day" in df else None,
    }

    if len(missing_idx):
        gaps = []
        if len(missing_idx):
            start = prev = missing_idx[0]
            for ts in missing_idx[1:]:
                if ts - prev == pd.Timedelta(hours=1):
                    prev = ts
                    continue
                gaps.append({"start": str(start), "end": str(prev), "hours": int((prev - start) / pd.Timedelta(hours=1)) + 1})
                start = prev = ts
            gaps.append({"start": str(start), "end": str(prev), "hours": int((prev - start) / pd.Timedelta(hours=1)) + 1})
        report["missing_timestamp_gaps"] = gaps[:20]
        report["missing_timestamp_gap_count"] = len(gaps)

    for col in ["wind_speed_100m", "temperature_2m", "surface_pressure", "wind_direction_100m"]:
        series = pd.to_numeric(df[col], errors="coerce")
        finite = np.isfinite(series.to_numpy(dtype=float))
        entry = {
            "missing_or_non_numeric": int((~finite).sum()),
            "non_finite": int((~finite).sum()),
        }
        lo, hi = C.PLAUSIBLE_RANGES[col]
        if col == "surface_pressure":
            # raw values are hPa
            lo, hi = 800.0, 1100.0
        vals = series.to_numpy(dtype=float)
        below = int(np.sum(finite & (vals < lo)))
        above = int(np.sum(finite & (vals > hi)))
        entry.update(
            {
                "plausible_range_used": [lo, hi],
                "below_range": below,
                "above_range": above,
                "min": float(np.nanmin(vals)) if finite.any() else None,
                "max": float(np.nanmax(vals)) if finite.any() else None,
                "mean": float(np.nanmean(vals)) if finite.any() else None,
                "std": float(np.nanstd(vals, ddof=1)) if finite.sum() > 1 else None,
            }
        )
        report["columns"][col] = entry

    if "air_density_kg_m3" in df:
        rho = df["air_density_kg_m3"].to_numpy(dtype=float)
        report["columns"]["air_density_kg_m3"] = {
            "min": float(np.nanmin(rho)),
            "max": float(np.nanmax(rho)),
            "mean": float(np.nanmean(rho)),
            "std": float(np.nanstd(rho, ddof=1)),
            "non_finite": int((~np.isfinite(rho)).sum()),
        }

    if "complete_case" in df:
        report["complete_case_hours"] = int(df["complete_case"].sum())
        report["excluded_incomplete_hours"] = int((~df["complete_case"]).sum())

    if "year" in df:
        counts = df.groupby("year").size().to_dict()
        report["per_year_records"] = {str(k): int(v) for k, v in counts.items()}
    if "month" in df:
        counts = df.groupby("month").size().to_dict()
        report["per_month_records"] = {str(k): int(v) for k, v in counts.items()}

    return report


def render_qc_markdown(report: dict) -> str:
    lines = ["# Data Quality Report", ""]
    lines.append(f"**Site:** {report['site']}  ")
    lines.append(
        f"**Period:** {report['period']['start']} to {report['period']['end']} "
        f"({report['period']['timezone']})  "
    )
    lines.append(f"**Expected hourly records:** {report['expected_hourly_records']:,}  ")
    lines.append(f"**Received records:** {report['received_records']:,}  ")
    lines.append(f"**Completeness:** {report['completeness_pct']:.4f}%  ")
    lines.append(f"**Duplicate timestamps:** {report['duplicate_timestamps']}  ")
    lines.append(f"**Missing timestamps:** {report['missing_timestamps']}  ")
    lines.append(f"**Non-monotonic timestamps:** {report['non_monotonic_timestamps']}  ")
    lines.append("")
    lines.append(
        "No values are imputed, interpolated, or removed. "
        "`complete_case` marks hours usable for simulation; excluded hours are counted."
    )
    lines.append("")
    lines.append("## Per-variable summary")
    lines.append("")
    lines.append("| Variable | Missing / non-finite | Below range | Above range | Min | Max | Mean |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|")
    for col, e in report["columns"].items():
        if col == "air_density_kg_m3":
            continue
        lines.append(
            f"| {col} | {e['missing_or_non_numeric']} | {e['below_range']} | "
            f"{e['above_range']} | {e['min']:.3g} | {e['max']:.3g} | {e['mean']:.3g} |"
        )
    if "air_density_kg_m3" in report["columns"]:
        e = report["columns"]["air_density_kg_m3"]
        lines.append(
            f"| air_density_kg_m3 (derived) | {e['non_finite']} | - | - | "
            f"{e['min']:.4f} | {e['max']:.4f} | {e['mean']:.4f} |"
        )
    lines.append("")
    lines.append("## Records per year")
    lines.append("")
    lines.append("| Year | Records |")
    lines.append("|---|---:|")
    for y in sorted(report["per_year_records"], key=int):
        lines.append(f"| {y} | {report['per_year_records'][y]:,} |")
    lines.append("")
    lines.append("## Records per calendar month")
    lines.append("")
    lines.append("| Month | Records |")
    lines.append("|---|---:|")
    for m in sorted(report["per_month_records"], key=int):
        lines.append(f"| {m} | {report['per_month_records'][m]:,} |")
    lines.append("")
    if report.get("missing_timestamp_gaps"):
        lines.append("## Missing-timestamp gaps (first 20)")
        lines.append("")
        for g in report["missing_timestamp_gaps"]:
            lines.append(f"- {g['start']} to {g['end']} ({g['hours']} h)")
        lines.append("")
    lines.append(f"**Leap-day (29 Feb) records:** {report.get('leap_day_records')}")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Orchestration
# --------------------------------------------------------------------------
def process(force: bool = False) -> dict:
    df_raw = load_raw()
    df = derive(df_raw)

    report = qc_audit(df)

    C.PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    if C.PROCESSED_CSV.exists() and not force:
        # overwrite is intentional here: the processed file is a derived artefact
        pass
    out_cols = [
        "time", "year", "month", "month_name", "day", "hour", "season",
        "is_leap_day", "wind_speed_100m", "temperature_2m", "surface_pressure",
        "wind_direction_100m", "surface_pressure_pa", "temperature_k",
        "air_density_kg_m3", "complete_case",
    ]
    df[out_cols].to_csv(C.PROCESSED_CSV, index=False)
    C.QC_JSON.write_text(json.dumps(report, indent=2), encoding="utf-8")
    C.QC_MD.write_text(render_qc_markdown(report), encoding="utf-8")

    print(f"processed rows: {len(df):,} -> {C.PROCESSED_CSV}")
    print(f"completeness: {report['completeness_pct']:.4f}%")
    print(f"complete-case hours: {report.get('complete_case_hours'):,}")
    print(f"wrote {C.QC_JSON.name} and {C.QC_MD.name}")
    return report


def load_processed(path: Path = C.PROCESSED_CSV) -> pd.DataFrame:
    if not path.exists():
        raise FileNotFoundError(f"{path} not found. Run 'python -m src.data_processing' first.")
    df = pd.read_csv(path, parse_dates=["time"])
    return df


def main() -> None:
    process(force=True)


if __name__ == "__main__":
    main()