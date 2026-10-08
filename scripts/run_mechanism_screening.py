#!/usr/bin/env python3
"""Run the frozen, minimal Stage 2 ROM mechanism-screening controls."""

from __future__ import annotations

import argparse
import copy
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .harmonic_analysis import robust_harmonic_analysis, welch_psd
    from .nonlinear_rom import (
        MODEL_LIN,
        MechanismSwitches,
        load_config,
        simulate,
        write_outputs,
    )
except ImportError:
    from harmonic_analysis import robust_harmonic_analysis, welch_psd
    from nonlinear_rom import (
        MODEL_LIN,
        MechanismSwitches,
        load_config,
        simulate,
        write_outputs,
    )

LOGGER = logging.getLogger("run_mechanism_screening")

CASE_MATRIX: tuple[tuple[str, str, MechanismSwitches], ...] = (
    ("C0", "linear negative control", MechanismSwitches()),
    ("C1", "linear + cubic symmetric stiffness", MechanismSwitches(cubic_stiffness=True)),
    ("C2", "linear + quadratic/asymmetric coupling", MechanismSwitches(quadratic_coupling=True)),
    ("C3", "linear + tension-only/piecewise stiffness", MechanismSwitches(tension_only=True)),
    (
        "C4",
        "quadratic/asymmetric coupling + tension-only",
        MechanismSwitches(quadratic_coupling=True, tension_only=True),
    ),
    (
        "C5",
        "bending-torsion nonlinear coupling",
        MechanismSwitches(bending_torsion_coupling=True),
    ),
)


def _analysis_for_result(result: Any, config: dict[str, Any]) -> dict[str, Any]:
    settings = config["analysis"]
    output: dict[str, Any] = {}
    for index, coordinate in enumerate(("z", "theta")):
        robust = robust_harmonic_analysis(
            result.time,
            result.displacement[:, index],
            fundamental_frequency_hz=float(settings["fundamental_frequency_hz"]),
            frequency_reference=str(settings["frequency_reference"]),
            discard_initial_fraction=float(settings["discard_initial_fraction"]),
            spectral_window=str(settings["spectral_window"]),
            frequency_bin_tolerance_hz=float(settings["frequency_bin_tolerance_hz"]),
            minimum_forcing_cycles=float(settings["minimum_forcing_cycles"]),
            integer_cycle_window=bool(settings["integer_cycle_window"]),
        )
        psd_frequency, psd = welch_psd(robust["time"], robust["values"])
        output[coordinate] = {
            "fft_frequency": robust["frequency"],
            "fft_amplitude": robust["amplitude"],
            "psd_frequency": psd_frequency,
            "psd": psd,
            "harmonics": robust["harmonics"],
        }
    return output


def _injected_2f_config(base: dict[str, Any]) -> dict[str, Any]:
    config = copy.deepcopy(base)
    forcing = config["forcing"]
    f0 = float(forcing["frequency_hz"])
    amplitudes = np.asarray(forcing["amplitudes"], dtype=float)
    epsilon = float(forcing["injected_2f_fraction"])
    forcing["type"] = "broadband_synthetic"
    forcing["broadband_components"] = [
        {"frequency_hz": f0, "amplitudes": amplitudes.tolist(), "phases_deg": [0.0, 0.0]},
        {
            "frequency_hz": 2.0 * f0,
            "amplitudes": (epsilon * amplitudes).tolist(),
            "phases_deg": [0.0, 0.0],
        },
    ]
    return config


def _peak_values(harmonics: dict[str, Any]) -> dict[str, float]:
    return {
        "A_f": float(harmonics["peaks"]["1f0"]["amplitude"]),
        "A_2f": float(harmonics["peaks"]["2f0"]["amplitude"]),
        "A_3f": float(harmonics["peaks"]["3f0"]["amplitude"]),
        "A_2f_over_A_f": float(harmonics["A_2f_over_A_f"]),
        "A_3f_over_A_f": float(harmonics["A_3f_over_A_f"]),
    }


def _finite_range(values: np.ndarray) -> tuple[float | None, float | None]:
    finite = values[np.isfinite(values)]
    if not finite.size:
        return None, None
    return float(np.min(finite)), float(np.max(finite))


def _render_report(
    rows: list[dict[str, Any]],
    *,
    suite_id: str,
    runtime_seconds: float,
    output_path: Path,
    config: dict[str, Any],
) -> None:
    lines = [
        "# Stage 2 ROM mechanism screening",
        "",
        f"- Suite ID: `{suite_id}`",
        f"- Classification: `{config['data_classification']}`",
        f"- Runtime: **{runtime_seconds:.3f} s**",
        "- Scope: synthetic mechanism development; not a formal paper result.",
        "- Automatic causal interpretation: **DISABLED**",
        "",
        "Every C0–C5 mechanism case used a single-frequency external input with no 2f component. "
        "PC1 is an input-detection software control and is not mechanism evidence.",
        "",
        "## Spectral robustness record",
        "",
        f"- Frequency resolution: **{rows[0]['frequency_resolution_hz']:.6g} Hz**",
        f"- Analysis window: **{rows[0]['analysis_window']['analysis_start_seconds']:.6g}–{rows[0]['analysis_window']['analysis_end_seconds']:.6g} s**",
        f"- Analysis duration: **{rows[0]['analysis_window']['analysis_duration_seconds']:.6g} s**",
        f"- Analyzed forcing cycles: **{rows[0]['analysis_window']['analyzed_cycles']:.6g}**",
        "- Spectral window: **Hann**",
        "- Nearest-bin errors for C0: "
        f"f={rows[0]['nearest_bin_error_hz']['1f0']:.6g} Hz, "
        f"2f={rows[0]['nearest_bin_error_hz']['2f0']:.6g} Hz, "
        f"3f={rows[0]['nearest_bin_error_hz']['3f0']:.6g} Hz",
        "",
        "| Case | Purpose / switches | f (Hz) | frequency reference | forcing has 2f | A_f | A_2f | A_3f | A_2f/A_f | A_3f/A_f | stiffness transition | T_min | T_max |",
        "|---|---|---:|---|---|---:|---:|---:|---:|---:|---|---:|---:|",
    ]
    for row in rows:
        switches = ", ".join(
            name
            for name, enabled in row["mechanism_switches"].items()
            if enabled is True
            or (name == "cable_surrogate_mode" and enabled not in {"NONE", ""})
        )
        display = {
            **row,
            "switches": switches,
            "minimum_surrogate_tension_display": (
                "N/A"
                if row["minimum_surrogate_tension"] is None
                else f"{row['minimum_surrogate_tension']:.6g}"
            ),
            "maximum_surrogate_tension_display": (
                "N/A"
                if row["maximum_surrogate_tension"] is None
                else f"{row['maximum_surrogate_tension']:.6g}"
            ),
            "forcing_contains_2f_display": "TRUE" if row["forcing_contains_2f"] else "FALSE",
        }
        lines.append(
            "| {case_id} | {purpose}; {switches} | {forcing_frequency_hz:.4g} | "
            "{frequency_reference} | {forcing_contains_2f_display} | {A_f:.6g} | {A_2f:.6g} | "
            "{A_3f:.6g} | {A_2f_over_A_f:.6g} | {A_3f_over_A_f:.6g} | "
            "{stiffness_state_transition} | {minimum_surrogate_tension_display} | "
            "{maximum_surrogate_tension_display} |".format(**display)
        )
    c0 = next(row for row in rows if row["case_id"] == "C0")
    pc1 = next(row for row in rows if row["case_id"] == "PC1")
    negative_passed = c0["A_2f_over_A_f"] <= float(
        config["analysis"]["negative_control_max_A_2f_over_A_f"]
    )
    positive_passed = pc1["A_2f_over_A_f"] >= float(
        config["analysis"]["injected_2f_min_A_2f_over_A_f"]
    )
    lines.extend(
        [
            "",
            "## Controls",
            "",
            f"- Linear single-frequency negative control passed: **{'YES' if negative_passed else 'NO'}**",
            f"- Injected-input-2f detection control passed: **{'YES' if positive_passed else 'NO'}**",
            "",
            "## Reporting boundary",
            "",
            "Rows report signal features only. A larger second-harmonic amplitude than C0 is not "
            "automatically assigned to cable slackening, aeroelastic feedback, or any unique physical cause.",
        ]
    )
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def run_screening(
    config_path: Path,
    output_root: Path,
    report_path: Path,
    repository_root: Path,
) -> tuple[str, list[dict[str, Any]], float]:
    config = load_config(config_path)
    if config["data_classification"] != "STAGE2_MECHANISM_DEVELOPMENT":
        raise ValueError("Stage 2 screening requires STAGE2_MECHANISM_DEVELOPMENT classification")
    suite_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    cases = list(CASE_MATRIX) + [("PC1", "INPUT_2F_DETECTION", MechanismSwitches())]
    for case_id, purpose, switches in cases:
        case_config = _injected_2f_config(config) if case_id == "PC1" else copy.deepcopy(config)
        forcing_contains_2f = case_id == "PC1"
        result = simulate(
            case_config,
            MODEL_LIN,
            tension_only=switches.tension_only,
            mechanism_switches=switches,
        )
        analysis = _analysis_for_result(result, case_config)
        run_id = f"{suite_id}-{case_id.lower()}"
        case_output = output_root / suite_id / case_id
        write_outputs(
            result,
            analysis,
            case_config,
            case_output,
            run_id=run_id,
            repository_root=repository_root,
        )
        primary = str(case_config["analysis"]["response_coordinate"])
        harmonics = analysis[primary]["harmonics"]
        tension_minimum, tension_maximum = _finite_range(result.tension_surrogate)
        states = {state for state in result.stiffness_state if state != "NOT_APPLICABLE"}
        row = {
            "case_id": case_id,
            "purpose": purpose,
            "mechanism_switches": switches.as_dict(),
            "forcing_frequency_hz": float(case_config["analysis"]["fundamental_frequency_hz"]),
            "frequency_reference": str(case_config["analysis"]["frequency_reference"]),
            "forcing_contains_2f": forcing_contains_2f,
            **_peak_values(harmonics),
            "stiffness_state_transition": len(states) > 1,
            "stiffness_states": sorted(states),
            "minimum_surrogate_tension": tension_minimum,
            "maximum_surrogate_tension": tension_maximum,
            "frequency_resolution_hz": harmonics["frequency_resolution_hz"],
            "analysis_window": harmonics["analysis_window"],
            "nearest_bin_error_hz": harmonics["nearest_bin_error_hz"],
            "forcing_contains_2f_statement": "FALSE" if not forcing_contains_2f else "TRUE",
            "data_classification": case_config["data_classification"],
        }
        (case_output / "stage2_case_metadata.json").write_text(
            json.dumps(row, indent=2) + "\n", encoding="utf-8"
        )
        rows.append(row)
        LOGGER.info("%s completed in %.3f s", case_id, result.runtime_seconds)
    runtime = time.perf_counter() - started
    summary_path = output_root / suite_id / "mechanism_screening_summary.csv"
    pd.DataFrame(
        [{**row, "mechanism_switches": json.dumps(row["mechanism_switches"])} for row in rows]
    ).to_csv(summary_path, index=False)
    _render_report(
        rows,
        suite_id=suite_id,
        runtime_seconds=runtime,
        output_path=report_path,
        config=config,
    )
    return suite_id, rows, runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the minimal frozen Stage 2 ROM controls.")
    parser.add_argument("--config", type=Path, default=Path("config/stage2_mechanism.yaml"))
    parser.add_argument(
        "--output-root", type=Path, default=Path("prototype_results/stage2_mechanism")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/STAGE2_ROM_MECHANISM_SCREENING.md")
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        suite_id, _, runtime = run_screening(
            args.config, args.output_root, args.report, args.repository_root
        )
        LOGGER.info("Suite %s completed in %.3f s", suite_id, runtime)
        return 0
    except Exception:
        LOGGER.exception("Stage 2 mechanism screening failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
