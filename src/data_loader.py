"""Reproducible data acquisition from the Open-Meteo Historical Weather API.

The API is backed by the ERA5 reanalysis.  We request one calendar year per HTTP
call (10 calls) so that partial failures can be retried and audited.  The
untouched JSON response is not kept; instead the returned CSV plus a provenance
record (exact URL, parameters, retrieval timestamp, response metadata) is saved.

Run:
    python -m src.data_loader                # download if missing
    python -m src.data_loader --force        # re-download
    python -m src.data_loader --reuse        # build raw CSV from saved JSON-free cache
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

from . import config as C

TIMEOUT_S = 90
RETRIES = 4
RETRY_BACKOFF_S = 3.0


def build_params(year: int) -> dict:
    """Exact query parameters for one calendar year (UTC, ERA5, land cell)."""
    return {
        "latitude": C.LATITUDE,
        "longitude": C.LONGITUDE,
        "start_date": f"{year}-01-01",
        "end_date": f"{year}-12-31",
        "hourly": C.VARIABLES,
        "timezone": C.TIMEZONE,
        "models": C.MODEL,
        "cell_selection": C.CELL_SELECTION,
        "wind_speed_unit": C.WIND_SPEED_UNIT,
    }


def build_url(params: dict, endpoint: str = C.API_ENDPOINT) -> str:
    """Human-readable request URL (also recorded in the provenance file)."""
    q = "&".join(f"{k}={v}" for k, v in params.items())
    return f"{endpoint}?{q}"


def _fetch_year(session: requests.Session, year: int) -> dict:
    params = build_params(year)
    url = build_url(params)
    last_error: Exception | None = None
    for attempt in range(1, RETRIES + 1):
        try:
            resp = session.get(C.API_ENDPOINT, params=params, timeout=TIMEOUT_S)
            resp.raise_for_status()
            payload = resp.json()
            if "hourly" not in payload:
                raise ValueError(f"unexpected API payload for {year}: keys={list(payload)[:6]}")
            return payload
        except Exception as exc:  # noqa: BLE001 - recorded and re-raised
            last_error = exc
            if attempt < RETRIES:
                time.sleep(RETRY_BACKOFF_S * attempt)
    raise RuntimeError(f"failed to retrieve ERA5 data for {year} after {RETRIES} attempts: {last_error}")


def download(force: bool = False) -> dict:
    """Download 2015-2024 hourly ERA5 data and write the raw CSV + provenance."""
    C.RAW_DIR.mkdir(parents=True, exist_ok=True)
    if C.RAW_CSV.exists() and not force:
        raise FileExistsError(
            f"{C.RAW_CSV.name} already exists; pass --force to re-download"
        )

    session = requests.Session()
    frames = []
    per_year_meta = {}
    for year in range(2015, 2025):
        payload = _fetch_year(session, year)
        hourly = payload["hourly"]
        columns = {k: hourly[k] for k in ["time"] + C.VARIABLES if k in hourly}
        import pandas as pd

        frames.append(pd.DataFrame(columns))
        per_year_meta[str(year)] = {
            "latitude": payload.get("latitude"),
            "longitude": payload.get("longitude"),
            "elevation": payload.get("elevation"),
            "utc_offset_seconds": payload.get("utc_offset_seconds"),
            "timezone": payload.get("timezone"),
            "timezone_abbreviation": payload.get("timezone_abbreviation"),
            "records": len(hourly["time"]),
        }
        print(f"  retrieved {year}: {len(hourly['time'])} hourly records")

    import pandas as pd

    raw = pd.concat(frames, ignore_index=True)
    raw.to_csv(C.RAW_CSV, index=False)

    provenance = {
        "dataset": "Open-Meteo Historical Weather API (ERA5 reanalysis)",
        "provider": "Open-Meteo",
        "source_url": C.API_ENDPOINT,
        "documentation": "https://open-meteo.com/en/docs/historical-weather-api",
        "underlying_model": C.MODEL,
        "cell_selection": C.CELL_SELECTION,
        "site": {
            "name": C.SITE_NAME,
            "latitude_requested": C.LATITUDE,
            "longitude_requested": C.LONGITUDE,
        },
        "period": {"start": C.START_DATE, "end": C.END_DATE},
        "timezone": C.TIMEZONE,
        "wind_speed_unit": C.WIND_SPEED_UNIT,
        "variables": C.VARIABLES,
        "retrieved_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "retrieval_method": "python-requests, one HTTP request per calendar year",
        "per_year_request_metadata": per_year_meta,
        "requests": [
            {"year": y, "url": build_url(build_params(y))} for y in range(2015, 2025)
        ],
        "notes": (
            "ERA5 is gridded reanalysis, not on-site turbine measurement. The "
            "returned grid cell is the ERA5 cell containing the requested point, "
            "so the series is a regional estimate."
        ),
    }
    C.RAW_PROVENANCE.write_text(json.dumps(provenance, indent=2), encoding="utf-8")
    print(f"wrote {C.RAW_CSV} ({len(raw)} rows)")
    print(f"wrote {C.RAW_PROVENANCE}")
    return provenance


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--force", action="store_true", help="re-download even if the raw CSV exists")
    args = ap.parse_args()
    download(force=args.force)


if __name__ == "__main__":
    main()