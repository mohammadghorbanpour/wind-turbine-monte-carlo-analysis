"""End-to-end orchestration: data -> model -> simulation -> analysis -> figures -> report.

Usage
-----
    python -m src.run_pipeline                     # full run (download if needed)
    python -m src.run_pipeline --quick             # 1,000 scenarios, fast
    python -m src.run_pipeline --scenarios 10000   # explicit scenario count
    python -m src.run_pipeline --reuse-raw         # never re-download
"""

from __future__ import annotations

import argparse
import json
import platform
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import pandas as pd

from . import config as C
from . import data_processing, report, sensitivity, simulation, visualization
from .data_loader import download
from .statistical_analysis import summarise, summarise_baseline, markdown_summary
from .turbine_model import calibration_report, fit_weibull


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=_json_default), encoding="utf-8")


def _json_default(o):
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (np.ndarray,)):
        return o.tolist()
    raise TypeError(f"not JSON serialisable: {type(o)}")


def _run_tests() -> tuple[int, str]:
    """Run the automated test suite and return (n_tests, command)."""
    import re

    cmd = [sys.executable, "-m", "pytest", "-q", "tests"]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(C.PROJECT_ROOT))
    out = (proc.stdout or "") + (proc.stderr or "")
    m = re.search(r"(\d+) passed", out)
    if m is None:
        raise RuntimeError(f"could not parse pytest output:\n{out[-4000:]}")
    n = int(m.group(1))
    if proc.returncode != 0:
        raise RuntimeError(f"test suite failed; see output:\n{out[-4000:]}")
    return n, " ".join(cmd)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--scenarios", type=int, default=C.N_SCENARIOS)
    ap.add_argument("--quick", action="store_true", help="1,000 scenarios for a fast smoke run")
    ap.add_argument("--reuse-raw", action="store_true", help="do not re-download the raw data")
    ap.add_argument("--force-download", action="store_true", help="force a fresh download")
    ap.add_argument("--skip-tests", action="store_true", help="skip the pytest step")
    args = ap.parse_args()

    n_scenarios = 1000 if args.quick else args.scenarios
    t0 = time.time()
    log: list[str] = []

    def note(msg: str) -> None:
        print(msg, flush=True)
        log.append(msg)

    note("=" * 78)
    note("Wind turbine Monte Carlo uncertainty pipeline")
    note("=" * 78)

    # ---------------------------------------------------------------- 1. data
    if args.reuse_raw and C.RAW_CSV.exists():
        note(f"[1/8] reusing raw data: {C.RAW_CSV.name}")
    elif C.RAW_CSV.exists() and not args.force_download:
        note(f"[1/8] raw data present: {C.RAW_CSV.name}")
    else:
        note("[1/8] downloading ERA5 data from Open-Meteo ...")
        download(force=args.force_download)
    provenance = _load_json(C.RAW_PROVENANCE) if C.RAW_PROVENANCE.exists() else {}

    qc = data_processing.process(force=True)
    df = data_processing.load_processed()
    note(f"      processed rows: {len(df):,}; completeness {qc['completeness_pct']:.4f}%")

    # ------------------------------------------------------- 2. model + weibull
    note("[2/8] fitting Weibull and checking calibration ...")
    weibull = fit_weibull(df["wind_speed_100m"].to_numpy(float))
    cal = calibration_report()
    note(f"      Weibull k={weibull['shape_k']:.3f}, c={weibull['scale_c']:.3f} m/s; "
         f"calibration ratio={cal['ratio_raw_over_rated_at_vrated']:.4f}")

    # ----------------------------------------------------------- 3. simulation
    note(f"[3/8] running Monte Carlo simulation ({n_scenarios:,} scenarios) ...")
    t_sim = time.time()
    result = simulation.simulate(df, n_scenarios=n_scenarios, seed=C.SEED)
    note(f"      done in {time.time() - t_sim:.1f} s")

    baseline = simulation.deterministic_baseline(df)
    baseline_summary = summarise_baseline(baseline)
    summary = summarise(result)
    convergence = simulation.convergence_table(result)

    # ----------------------------------------------------------- 4. sensitivity
    note("[4/8] sensitivity analysis (Spearman + Sobol) ...")
    spearman = sensitivity.spearman_sensitivity(result)
    sobol = sensitivity.sobol_analysis(n=C.SOBOL_N)
    oat = sensitivity.oat_tornado()
    note(f"      Sobol: {sobol['n_model_evaluations']:,} independent-input model evaluations")

    # -------------------------------------------------------------- 5. figures
    note("[5/8] generating figures ...")
    C.FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    C.REPORT_DIR.mkdir(parents=True, exist_ok=True)
    thumbnail = C.REPORT_DIR / "thumbnail.png"
    figs = visualization.make_all(
        df, result, summary, baseline, baseline_summary, convergence,
        spearman, sobol, oat, weibull,
        figures_dir=C.FIGURES_DIR, thumbnail_path=thumbnail,
    )
    for name, path in figs.items():
        note(f"      {name}: {Path(path).name}")

    # --------------------------------------------------------------- 6. tests
    if args.skip_tests:
        n_tests, test_cmd = 0, "(skipped)"
        note("[6/8] tests skipped by request")
    else:
        note("[6/8] running automated tests ...")
        n_tests, test_cmd = _run_tests()
        note(f"      {n_tests} tests passed")

    # ---------------------------------------------------------- 7. persist
    note("[7/8] writing result tables ...")
    C.TABLES_DIR.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {
            "scenario": np.arange(1, result.n_scenarios + 1),
            "aep_mwh": result.aep_mwh,
            "capacity_factor": result.cf,
            "mean_power_mw": result.mean_power_mw,
            "cp": result.cp,
            "eta": result.eta,
            "scenario_mean_wind_mps": result.mean_wind_mps,
            "scenario_mean_air_density_kg_m3": result.mean_rho_kg_m3,
        }
    ).to_csv(C.TABLES_DIR / "scenarios.csv", index=False)
    convergence.to_csv(C.TABLES_DIR / "convergence.csv", index=False)
    spearman.to_csv(C.TABLES_DIR / "spearman.csv", index=False)
    sobol["sobol_table"].to_csv(C.TABLES_DIR / "sobol.csv", index=False)
    oat.to_csv(C.TABLES_DIR / "oat_tornado.csv", index=False)
    baseline.to_csv(C.TABLES_DIR / "deterministic_baseline.csv", index=False)

    summary_out = {k: v for k, v in summary.items()}
    _write_json(C.TABLES_DIR / "summary.json", summary_out)
    _write_json(C.TABLES_DIR / "baseline_summary.json", baseline_summary)
    _write_json(C.TABLES_DIR / "weibull_fit.json", weibull)
    _write_json(C.TABLES_DIR / "calibration.json", cal)
    _write_json(
        C.TABLES_DIR / "sobol.json",
        {k: v for k, v in sobol.items() if k != "sobol_table"},
    )
    _write_json(C.TABLES_DIR / "data_quality_summary.json", {
        "records": qc["received_records"],
        "completeness_pct": qc["completeness_pct"],
        "missing_timestamps": qc["missing_timestamps"],
        "duplicate_timestamps": qc["duplicate_timestamps"],
        "complete_case_hours": qc.get("complete_case_hours"),
    })

    (C.TABLES_DIR / "results_summary.md").write_text(
        markdown_summary(summary, baseline_summary, convergence), encoding="utf-8"
    )
    (C.TABLES_DIR / "sensitivity_summary.md").write_text(
        sensitivity.sensitivity_summary(sobol, spearman, oat), encoding="utf-8"
    )

    # ------------------------------------------------------------- 8. report
    note("[8/8] building report ...")
    ctx = {
        "summary": summary,
        "baseline_summary": baseline_summary,
        "weibull": weibull,
        "calibration": cal,
        "spearman": spearman,
        "sobol": sobol,
        "n_records": int(qc["received_records"]),
        "completeness": float(qc["completeness_pct"]),
        "n_missing": int(qc["missing_timestamps"]),
        "n_duplicates": int(qc["duplicate_timestamps"]),
        "n_tests": n_tests,
        "analysis_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "fig_aep": str(figs["08_aep_distribution"]),
        "fig_cf": str(figs["09_cf_distribution"]),
    }
    pdf_path = report.build_pdf(ctx)
    md_path = report.build_markdown(ctx)

    # manifest
    import scipy
    import matplotlib as mpl
    import pytest as _pytest

    manifest = {
        "project": "Quantifying Wind Turbine Performance Uncertainty Using Monte Carlo Simulation",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "seed": C.SEED,
        "n_scenarios": int(result.n_scenarios),
        "n_hours_per_scenario": C.N_HOURS_YEAR,
        "block_hours": C.BLOCK_HOURS,
        "sobol_n_base": C.SOBOL_N,
        "software": {
            "python": platform.python_version(),
            "platform": platform.platform(),
            "numpy": np.__version__,
            "pandas": pd.__version__,
            "scipy": scipy.__version__,
            "matplotlib": mpl.__version__,
            "pytest": _pytest.__version__,
        },
        "commands": {
            "download": "python -m src.data_loader --force",
            "process": "python -m src.data_processing",
            "pipeline": "python -m src.run_pipeline",
            "tests": test_cmd,
        },
        "data_provenance": {
            "raw_csv": C.RAW_CSV.name,
            "processed_csv": C.PROCESSED_CSV.name,
            "provenance_record": C.RAW_PROVENANCE.name,
            "api_response_metadata": provenance.get("per_year_request_metadata", {}),
            "retrieved_at_utc": provenance.get("retrieved_at_utc"),
        },
        "turbine_specification": C.TURBINE.as_dict(),
        "outputs": {
            "figures": [Path(p).name for p in figs.values()],
            "tables": sorted(p.name for p in C.TABLES_DIR.iterdir() if p.is_file()),
            "report_pdf": pdf_path.name,
            "report_markdown": md_path.name,
        },
        "runtime_seconds": round(time.time() - t0, 1),
    }
    _write_json(C.TABLES_DIR / "analysis_manifest.json", manifest)

    # log
    (C.RESULTS_DIR / "pipeline_log.txt").write_text("\n".join(log) + "\n", encoding="utf-8")

    note("")
    note("=" * 78)
    note("KEY RESULTS")
    note("=" * 78)
    a = summary["aep_mwh"]
    c = summary["capacity_factor"]
    pr = summary["probability_cf_below_threshold"]
    note(f"Mean AEP            : {a['mean']:,.1f} MWh")
    note(f"Median AEP          : {a['median']:,.1f} MWh")
    note(f"AEP 5th-95th        : {a['p05']:,.1f} - {a['p95']:,.1f} MWh")
    note(f"Mean CF             : {c['mean']:.4f} (SD {c['std']:.4f})")
    note(f"P(CF < 0.25)        : {pr['estimate']:.4f} "
         f"(95% CI {pr['wilson_ci95'][0]:.4f} - {pr['wilson_ci95'][1]:.4f})")
    note(f"Deterministic AEP   : {baseline_summary['aep_mwh_mean']:,.1f} MWh (2015-2024 mean)")
    note(f"Tests               : {n_tests} passed")
    note(f"Report              : {pdf_path}")
    note(f"Thumbnail           : {thumbnail}")
    note(f"Total runtime       : {time.time() - t0:.1f} s")
    note("=" * 78)


if __name__ == "__main__":
    main()