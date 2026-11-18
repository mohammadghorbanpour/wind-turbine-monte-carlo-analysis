# References and Verification Notes

## References (in order cited in the technical report)

[1] Open-Meteo. Historical Weather API — documentation.
    https://open-meteo.com/en/docs/historical-weather-api (accessed 2026-11-18).

[2] Open-Meteo. Licence — CC BY 4.0 for Open-Meteo API data.
    https://open-meteo.com/en/licence (accessed 2026-11-18).
    States that API data are offered under Attribution 4.0 International (CC BY 4.0).

[3] Open-Meteo. Terms of Use — non-commercial use; CC BY 4.0 acceptance.
    https://open-meteo.com/en/terms (accessed 2026-11-18).
    Defines public research at public institutions as non-commercial (the free API
    tier used here is therefore applicable). Requires attribution, a link to the
    licence, and indication of changes.

[4] ECMWF / Copernicus Climate Change Service. ERA5 reanalysis — underlying model of
    the Open-Meteo Historical Weather API. ERA5 is a separate Copernicus product
    governed by the Copernicus Licence, **not** by CC BY 4.0.
    **Verification note:** Attempts to retrieve the Copernicus/C3S licence document
    returned HTTP 404 on two occasions, and the Stanford PAI course page
    (https://pai.stanford.edu/pai1/studenthome) returned no usable content.
    Therefore the applicable Copernicus Licence terms were NOT independently
    established in this audit, and no specific licence claim is made for the
    underlying ERA5 reanalysis. ERA5 is attributed to ECMWF / Copernicus Climate
    Change Service as its source; readers are referred to the current Copernicus
    licence terms.

[5] Manwell, J. F., McGowan, J. G., & Rogers, A. L. (2009). Wind Energy Explained,
    2nd ed. John Wiley & Sons. (Power curve and air-density modeling background.)

[6] IEC 61400-1. Wind energy generation systems — Part 1: Design requirements.
    International Electrotechnical Commission. (Turbine design standard context.)

[7] Kassis, T., Agarwal, V., He, Y., Patel, D., & Brueckner, A. M. (2026).
    Scientific Agent Skills: A Library of Procedural Knowledge for Research Agents.
    arXiv:2609.00065. https://doi.org/10.48550/arXiv.2609.00065

## Verification notes

- Open-Meteo API documentation (Historical Weather API, Licence CC BY 4.0, Terms of
  Use) were retrieved directly from open-meteo.com on 2026-11-18 and are verified.
- Underlying ERA5 / Copernicus Licence: NOT independently verified (HTTP 404).
  Distinct from the Open-Meteo API licence; this distinction is maintained
  throughout the report and SOURCES.md.
- Stanford PAI official course page: inaccessible via automated fetch; returned no
  usable content. Official course requirements were not independently verified from
  the live site. Report formats (≤2-page executive summary, 16:9 thumbnail ≥1280×720,
  ≤60 s video script, README, AI_USAGE.md) follow the project brief, which is
  explicitly distinguished from verified official requirements.
- No DOIs or publication details are invented. All numerical results are computed
  from executed code and saved output files (results/tables/, results/figures/).
