# Sources and Attribution

## Primary dataset

- **Name:** Open-Meteo Historical Weather API (ERA5 reanalysis)
- **Provider:** Open-Meteo
- **Endpoint:** https://archive-api.open-meteo.com/v1/archive
- **Documentation:** https://open-meteo.com/en/docs/historical-weather-api
- **Underlying reanalysis model:** ERA5 — ECMWF / Copernicus Climate Change Service
- **Access date:** 2026-11-18
- **Site:** Cuxhaven, Germany (requested 53.86 N, 8.69 E); returned ERA5 grid cell
  (53.75 N, 8.75 E), elevation 5 m
- **Period:** 2015-01-01 through 2024-12-31
- **Resolution:** Hourly, UTC
- **Variables:** wind_speed_100m (m/s), temperature_2m (°C), surface_pressure (hPa),
  wind_direction_100m (°)
- **Cell selection:** land
- **Records retrieved:** 87,672 hourly records (one HTTP request per calendar year)
- **Completeness:** 100.0% (0 missing timestamps, 0 duplicates)
- **Retrieval timestamp:** 2026-11-18T03:44:39 UTC
- **Raw file:** data/raw/openmeteo_era5_cuxhaven_2015_2024.csv
- **Provenance record:** data/raw/openmeteo_era5_cuxhaven_2015_2024.provenance.json

## License and attribution

**Verified from the provider's own documentation (accessed 2026-11-18):**

1. **Open-Meteo API data — CC BY 4.0.** The Open-Meteo [Licence page]
   (https://open-meteo.com/en/licence) states: "API data are offered under
   Attribution 4.0 International (CC BY 4.0)". The [Terms of Use]
   (https://open-meteo.com/en/terms) require acceptance of CC BY 4.0 for both
   free and subscription API use, and define public research conducted at public
   institutions as **non-commercial** (so the free API tier used here is the
   applicable one). Attribution requires giving credit, linking the licence, and
   indicating changes.

2. **Required Open-Meteo attribution.** The Licence page requires a visible link
   where data are displayed, e.g. "Weather data by Open-Meteo.com" linking to
   https://open-meteo.com/. Recommended citation: Zippenfenig, P. (2023).
   *Open-Meteo.com Weather API* [Computer software]. Zenodo.
   https://doi.org/10.5281/ZENODO.7970649

3. **Underlying ERA5 — separate Copernicus Licence, NOT verified in detail.**
   Open-Meteo's Licence page lists reanalysis data from the Copernicus Climate
   Change Service (C3S) under a distinct "Copernicus Licence" (a separate licence
   document linked from that page), not under CC BY 4.0. **The applicable
   Copernicus Licence terms were NOT independently established in this audit:**
   attempts to retrieve the Copernicus/C3S licence document returned HTTP 404.
   Therefore no specific licence claim is made for the underlying ERA5 reanalysis.
   The data are attributed to ECMWF / Copernicus Climate Change Service as their
   source, and the reader is referred to the current Copernicus licence terms.

**Corrected attribution statement:** Weather data by Open-Meteo.com (CC BY 4.0).
Contains ERA5 reanalysis data produced by ECMWF as part of the Copernicus Climate
Change Service; the Copernicus Licence applies to the underlying reanalysis (terms
not independently verified here). Data were accessed via the Open-Meteo Historical
Weather API on 2026-11-18. Neither Open-Meteo nor ECMWF endorses this analysis.

**Previous inconsistency resolved:** An earlier version of this file stated that
"ERA5 data are generally distributed under the Copernicus licence (CC BY 4.0)".
That conflated the Open-Meteo API licence (CC BY 4.0, verified) with the separate
Copernicus Licence governing the underlying ERA5 product (terms not verified).
This distinction is now explicit.

## Secondary references (consulted for methodology)

- Manwell, J. F., McGowan, J. G., & Rogers, A. L. (2009). *Wind Energy Explained*,
  2nd ed. Wiley. (Power curve and air-density modeling background.)
- IEC 61400-1, *Wind turbine generator systems — Part 1: Design requirements.*
  (Turbine design standard context.)
- Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026). Scientific
  Agent Skills: A Library of Procedural Knowledge for Research Agents. arXiv:2609.00065.
  https://doi.org/10.48550/arXiv.2609.00065

## Dataset limitations (stated limitations)

- ERA5 is gridded reanalysis, not an on-site turbine measurement.
- The returned grid cell is a regional estimate; it does not represent exact
  conditions at a specific turbine.
- 10-year record limits the range of interannual variability sampled.
