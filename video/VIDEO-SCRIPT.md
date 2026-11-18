# Video Script — Wind Turbine Performance Uncertainty

**Target duration:** 60 seconds maximum  
**Format:** Spoken narration with visual scene directions  
**Topic:** Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation

---

[0:00–0:08] Scene 1 — Title / motivation  
Visual: Title card: "Quantifying Wind Turbine Performance Uncertainty"  
Subtitle: A Monte Carlo assessment of power, annual energy, and energy adequacy  
Narration:  
"A wind turbine's annual energy output is never a single number. Wind varies, air
density changes, and turbine performance is only approximately known. How do these
uncertainties affect energy production — and the risk of low output?"

[0:08–0:18] Scene 2 — The data  
Visual: Map pin on Cuxhaven, Germany; timeline bar 2015–2024  
Narration:  
"We used ten years of hourly ERA5 reanalysis data from Cuxhaven, Germany — nearly
88,000 hours of wind speed, temperature, and pressure at 100 metres. ERA5 is a
regional reanalysis estimate, not on-site turbine measurement."

[0:18–0:30] Scene 3 — The model  
Visual: Simple turbine diagram; equation P = 0.5 × rho × A × V^3 × Cp × eta  
Narration:  
"For a hypothetical 2 megawatt turbine with a 45-metre rotor, we convert wind
speed and air density into hourly power using a simplified physical model. The
power coefficient Cp and efficiency eta are uncertain — we model them with
truncated normal distributions, drawn once per simulated year."

[0:30–0:42] Scene 4 — The simulation  
Visual: Histogram of annual energy production building up; 10,000 scenarios  
Narration:  
"We built 10,000 synthetic one-year weather sequences using a seven-day block
bootstrap that preserves seasonal structure, then simulated each year. The mean
annual energy production is about 6,523 megawatt-hours, with a 5th to 95th
percentile range of roughly 5,835 to 7,234 megawatt-hours."

[0:42–0:52] Scene 5 — The headline result  
Visual: Capacity factor distribution; threshold marker at 0.25  
Narration:  
"The mean capacity factor is 37.2%. The probability that annual capacity factor
falls below 25 percent — an energy-adequacy indicator, not a failure probability —
was zero in 10,000 simulated years. That does not mean zero risk; the 95 percent
confidence interval allows up to about 0.04 percent."

[0:52–0:60] Scene 6 — Takeaway  
Visual: Deterministic vs probabilistic comparison; limitations note  
Narration:  
"A deterministic calculation gives one AEP. The probabilistic result gives a full
distribution, with uncertainty intervals and sensitivity rankings. The simplified
model and ten-year record are limitations — but the method shows how uncertainty
propagates from wind and turbine parameters to energy production."

---

**Word count:** ~330 words  
**Estimated speaking time:** ~55–60 seconds at a measured pace  
**Key probability concept:** Monte Carlo simulation propagates input uncertainty
into an output distribution rather than a single point estimate.  
**Main result:** Mean AEP ≈ 6,523 MWh; mean CF ≈ 0.372; P(CF < 0.25) = 0.0000
(95% Wilson CI [0.0000, 0.0004]).
