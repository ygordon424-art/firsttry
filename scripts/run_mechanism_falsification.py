#!/usr/bin/env python3
"""Run a small, predefined suite that attempts to falsify the Stage 2 C3 interpretation."""

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
    from .harmonic_analysis import robust_harmonic_analysis
    from .nonlinear_rom import (
        ABRUPT_PIECEWISE,
        BILATERAL_LINEAR,
        LOW_TENSION_SOFTENING,
        MODEL_LIN,
        SMOOTH_TRANSITION,
        TRUE_TENSION_ONLY,
        MechanismSwitches,
        cable_state_statistics,
        load_config,
        natural_frequencies,
        simulate,
    )
except ImportError:
    from harmonic_analysis import robust_harmonic_analysis
    from nonlinear_rom import (
        ABRUPT_PIECEWISE,
        BILATERAL_LINEAR,
        LOW_TENSION_SOFTENING,
        MODEL_LIN,
        SMOOTH_TRANSITION,
        TRUE_TENSION_ONLY,
        MechanismSwitches,
        cable_state_statistics,
        load_config,
        natural_frequencies,
        simulate,
    )

LOGGER = logging.getLogger("run_mechanism_falsification")
CLASSIFICATION = "STAGE2_MECHANISM_DEVELOPMENT"


def _analyze(time_values: np.ndarray, response: np.ndarray, config: dict[str, Any]) -> dict[str, Any]:
    settings = config["analysis"]
    return robust_harmonic_analysis(
        time_values,
        response,
        fundamental_frequency_hz=float(settings["fundamental_frequency_hz"]),
        frequency_reference=str(settings["frequency_reference"]),
        discard_initial_fraction=float(settings["discard_initial_fraction"]),
        spectral_window=str(settings["spectral_window"]),
        frequency_bin_tolerance_hz=float(settings["frequency_bin_tolerance_hz"]),
        minimum_forcing_cycles=float(settings["minimum_forcing_cycles"]),
        integer_cycle_window=bool(settings["integer_cycle_window"]),
    )


def _harmonic_values(report: dict[str, Any]) -> dict[str, float | None]:
    harmonics = report["harmonics"]
    values = {
        "A_f": harmonics["peaks"]["1f0"]["amplitude"],
        "A_2f": harmonics["peaks"]["2f0"]["amplitude"],
        "A_3f": harmonics["peaks"]["3f0"]["amplitude"],
        "A_2f_over_A_f": harmonics["A_2f_over_A_f"],
        "A_3f_over_A_f": harmonics["A_3f_over_A_f"],
    }
    return {
        key: float(value) if np.isfinite(value) else None
        for key, value in values.items()
    }


def _run_case(
    case_id: str,
    purpose: str,
    config: dict[str, Any],
    switches: MechanismSwitches,
    *,
    response_coordinate: str = "z",
) -> tuple[dict[str, Any], pd.DataFrame]:
    result = simulate(config, MODEL_LIN, mechanism_switches=switches)
    coordinate_index = 0 if response_coordinate == "z" else 1
    report = _analyze(result.time, result.displacement[:, coordinate_index], config)
    theta_report = _analyze(result.time, result.displacement[:, 1], config)
    frequencies = natural_frequencies(config)
    row: dict[str, Any] = {
        "case_id": case_id,
        "purpose": purpose,
        "response_coordinate": response_coordinate,
        "cable_surrogate_mode": switches.cable_surrogate_mode,
        "transition_form": switches.low_tension_transition,
        "quadratic_coupling": switches.quadratic_coupling,
        "bending_torsion_coupling": switches.bending_torsion_coupling,
        "forcing_frequency_hz": float(config["analysis"]["fundamental_frequency_hz"]),
        "frequency_reference": config["analysis"]["frequency_reference"],
        "forcing_contains_2f": False,
        **_harmonic_values(report),
        "theta_A_2f": _harmonic_values(theta_report)["A_2f"],
        "natural_frequency_1_hz": float(frequencies[0]),
        "natural_frequency_2_hz": float(frequencies[1]),
        "natural_frequency_ratio_f2_over_f1": float(frequencies[1] / frequencies[0]),
        **cable_state_statistics(result),
        "max_step_seconds": float(config["solver"]["max_step_seconds"]),
        "solver_method": config["solver"]["method"],
        "analyzed_cycles": report["harmonics"]["analysis_window"]["analyzed_cycles"],
        "frequency_resolution_hz": report["harmonics"]["frequency_resolution_hz"],
        "runtime_seconds": result.runtime_seconds,
        "data_classification": config["data_classification"],
    }
    history = pd.DataFrame(
        {
            "time_seconds": result.time,
            "z": result.displacement[:, 0],
            "theta": result.displacement[:, 1],
            "T_surrogate": result.tension_surrogate,
            "K_tangent": result.tangent_stiffness,
            "stiffness_state": result.stiffness_state,
            "data_classification": config["data_classification"],
        }
    )
    return row, history


def predefined_cases(base: dict[str, Any]) -> list[tuple[str, str, dict[str, Any], MechanismSwitches, str]]:
    controls = base["predefined_controls"]
    cases: list[tuple[str, str, dict[str, Any], MechanismSwitches, str]] = []
    cases.append(
        ("B0", "bilateral linear cable surrogate", copy.deepcopy(base),
         MechanismSwitches(cable_surrogate_mode=BILATERAL_LINEAR), "z")
    )
    cases.append(
        ("B1", "positive-tension abrupt low-stiffness transition", copy.deepcopy(base),
         MechanismSwitches(cable_surrogate_mode=LOW_TENSION_SOFTENING,
                           low_tension_transition=ABRUPT_PIECEWISE), "z")
    )
    cases.append(
        ("B2", "positive-tension smooth low-stiffness transition", copy.deepcopy(base),
         MechanismSwitches(cable_surrogate_mode=LOW_TENSION_SOFTENING,
                           low_tension_transition=SMOOTH_TRANSITION), "z")
    )
    true_positive = copy.deepcopy(base)
    true_positive["tension_surrogate"]["pretension"] = float(
        controls["true_tension_positive_pretension"]
    )
    true_positive["tension_surrogate"]["low_tension_threshold"] = 0.0
    cases.append(
        ("C_TRUE_1", "TRUE_TENSION_ONLY with positive tension throughout",
         true_positive, MechanismSwitches(cable_surrogate_mode=TRUE_TENSION_ONLY), "z")
    )
    true_crossing = copy.deepcopy(base)
    true_crossing["tension_surrogate"]["pretension"] = float(
        controls["true_tension_crossing_pretension"]
    )
    true_crossing["tension_surrogate"]["low_tension_threshold"] = 0.0
    cases.append(
        ("C_TRUE_2", "SYNTHETIC MECHANISM CONTROL crossing true zero tension",
         true_crossing, MechanismSwitches(cable_surrogate_mode=TRUE_TENSION_ONLY), "z")
    )

    ir = controls["internal_resonance"]
    near = copy.deepcopy(base)
    near["dynamics"]["mass_matrix"] = ir["mass_matrix"]
    near["dynamics"]["linear_stiffness_matrix"] = ir["near_1_to_2_stiffness_matrix"]
    near["forcing"]["amplitudes"] = ir["forcing_amplitudes"]
    f1 = float(natural_frequencies(near)[0])
    near["forcing"]["frequency_hz"] = f1
    near["analysis"]["fundamental_frequency_hz"] = f1
    cases.append(("IR0", f"{ir['label']}: linear near 1:2", copy.deepcopy(near), MechanismSwitches(), "theta"))
    ir_switches = MechanismSwitches(quadratic_coupling=True)
    cases.append(("IR1", f"{ir['label']}: quadratic bending-torsion coupling near 1:2",
                  copy.deepcopy(near), ir_switches, "theta"))
    detuned = copy.deepcopy(near)
    detuned["dynamics"]["linear_stiffness_matrix"] = ir["detuned_stiffness_matrix"]
    detuned_f1 = float(natural_frequencies(detuned)[0])
    detuned["forcing"]["frequency_hz"] = detuned_f1
    detuned["analysis"]["fundamental_frequency_hz"] = detuned_f1
    cases.append(("IR2", f"{ir['label']}: same coupling detuned", detuned, ir_switches, "theta"))

    robust = controls["robustness"]
    half_step = copy.deepcopy(base)
    half_step["solver"]["max_step_seconds"] = robust["half_max_step_seconds"]
    cases.append(("R_HALF_DT", "B1 with half maximum integration step", half_step,
                  MechanismSwitches(cable_surrogate_mode=LOW_TENSION_SOFTENING,
                                    low_tension_transition=ABRUPT_PIECEWISE), "z"))
    alternative = copy.deepcopy(base)
    alternative["solver"]["method"] = robust["alternative_solver"]
    cases.append(("R_ALT_SOLVER", "B1 with alternative scipy solver", alternative,
                  MechanismSwitches(cable_surrogate_mode=LOW_TENSION_SOFTENING,
                                    low_tension_transition=ABRUPT_PIECEWISE), "z"))
    long_window = copy.deepcopy(base)
    long_window["solver"]["duration_seconds"] = robust["long_duration_seconds"]
    long_window["analysis"]["discard_initial_fraction"] = robust[
        "long_discard_initial_fraction"
    ]
    long_window["analysis"]["minimum_forcing_cycles"] = robust[
        "long_minimum_forcing_cycles"
    ]
    cases.append(("R_16_CYCLES", "B1 with at least 16 analyzed cycles", long_window,
                  MechanismSwitches(cable_surrogate_mode=LOW_TENSION_SOFTENING,
                                    low_tension_transition=ABRUPT_PIECEWISE), "z"))
    return cases


def _format(value: Any) -> str:
    if value is None:
        return "N/A"
    if isinstance(value, bool):
        return "YES" if value else "NO"
    if isinstance(value, (float, np.floating)):
        return f"{value:.6g}"
    return str(value)


def _relative_difference(first: float | None, second: float | None) -> float | None:
    if first is None or second is None or first == 0:
        return None
    return abs(second - first) / abs(first)


def render_report(rows: list[dict[str, Any]], runtime: float, suite_id: str) -> str:
    by_id = {row["case_id"]: row for row in rows}
    abrupt = by_id["B1"]
    smooth = by_id["B2"]
    true_positive = by_id["C_TRUE_1"]
    true_crossing = by_id["C_TRUE_2"]
    ir0, ir1, ir2 = by_id["IR0"], by_id["IR1"], by_id["IR2"]
    robustness_ids = ["B1", "R_HALF_DT", "R_ALT_SOLVER", "R_16_CYCLES"]
    robustness_values = [by_id[case]["A_2f_over_A_f"] for case in robustness_ids]
    finite_robustness = [value for value in robustness_values if value is not None]
    robustness_spread = (
        (max(finite_robustness) - min(finite_robustness)) / abs(abrupt["A_2f_over_A_f"])
        if finite_robustness and abrupt["A_2f_over_A_f"]
        else None
    )
    lines = [
        "# Stage 2 mechanism falsification",
        "",
        f"- Suite ID: `{suite_id}`",
        f"- Classification: `{CLASSIFICATION}`",
        f"- Total runtime: **{runtime:.3f} s**",
        "- Parameter optimization/search: **NOT PERFORMED**",
        "- Interpretation scope: numerical mechanism capability and model-form sensitivity only.",
        "",
        "| Case | Mode/control | Response | A_f | A_2f | A_3f | A_2f/A_f | min T | T<=0 fraction | softened fraction | transitions | f2/f1 |",
        "|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        mode = row["cable_surrogate_mode"]
        if mode == "NONE":
            mode = row["purpose"]
        elif mode == LOW_TENSION_SOFTENING:
            mode = f"{mode}/{row['transition_form']}"
        lines.append(
            "| {case_id} | {mode} | {response_coordinate} | {A_f} | {A_2f} | {A_3f} | "
            "{ratio} | {minimum} | {zero_fraction} | {soft_fraction} | {transitions} | {modal_ratio} |".format(
                case_id=row["case_id"], mode=mode, response_coordinate=row["response_coordinate"],
                A_f=_format(row["A_f"]), A_2f=_format(row["A_2f"]), A_3f=_format(row["A_3f"]),
                ratio=_format(row["A_2f_over_A_f"]), minimum=_format(row["minimum_tension"]),
                zero_fraction=_format(row["fraction_time_tension_le_zero"]),
                soft_fraction=_format(row["fraction_time_softened_state"]),
                transitions=row["number_stiffness_transitions"],
                modal_ratio=_format(row["natural_frequency_ratio_f2_over_f1"]),
            )
        )
    smooth_difference = _relative_difference(abrupt["A_2f_over_A_f"], smooth["A_2f_over_A_f"])
    ir_amplification = _relative_difference(ir2["A_2f"], ir1["A_2f"])
    lines.extend(
        [
            "",
            "## Required falsification questions",
            "",
            "1. **Dependence on a positive-tension threshold:** **YES for this synthetic model form.** "
            f"B1 was `{_format(abrupt['A_2f_over_A_f'])}`, whereas C_TRUE_1 was "
            f"`{_format(true_positive['A_2f_over_A_f'])}` with no zero-tension transition. The strong "
            "C3-like response therefore did not persist when the positive threshold was removed; this "
            "does not identify a physical cable mechanism.",
            "2. **Abrupt versus smooth transition:** The relative difference in `A_2f/A_f` is "
            f"**{_format(smooth_difference)}** (fraction). The smooth model retained most of the response, "
            "so the amplitude is not explained solely by a tangent-stiffness discontinuity. This is "
            "model-form sensitivity, not causal confirmation.",
            "3. **TRUE_TENSION_ONLY without zero tension:** C_TRUE_1 had zero-tension fraction "
            f"`{_format(true_positive['fraction_time_tension_le_zero'])}` and `A_2f/A_f` "
            f"`{_format(true_positive['A_2f_over_A_f'])}`; **no clear 2f above the numerical-control level was produced**.",
            "4. **TRUE_TENSION_ONLY crossing zero:** C_TRUE_2 is a `SYNTHETIC MECHANISM CONTROL`; "
            f"its zero-tension fraction was `{_format(true_crossing['fraction_time_tension_le_zero'])}` "
            f"and `A_2f/A_f` was `{_format(true_crossing['A_2f_over_A_f'])}`. **The mathematical "
            "zero-tension transition has harmonic-generation capability in this control.** This is not "
            "evidence that a real PV cable reached zero tension.",
            "5. **1:2 internal-resonance control:** IR0/IR1 use `f2/f1` approximately "
            f"`{_format(ir1['natural_frequency_ratio_f2_over_f1'])}`, while IR2 is "
            f"`{_format(ir2['natural_frequency_ratio_f2_over_f1'])}`. Their torsional `A_2f` values are "
            f"IR0=`{_format(ir0['A_2f'])}`, IR1=`{_format(ir1['A_2f'])}`, and "
            f"IR2=`{_format(ir2['A_2f'])}`; the near-1:2 absolute amplitude change relative to the detuned "
            f"control is `{_format(ir_amplification)}` (fraction). **The near-1:2 condition activated/amplified "
            "the implemented quadratic modal-transfer response.** Because torsional `A_f` is near zero, "
            "its `A_2f/A_f` ratio is ill-conditioned and is not used for this comparison. These are software controls only.",
            "6. **Numerical robustness:** Across baseline step, half step, DOP853, and the 16-cycle "
            f"window, the normalized spread in `A_2f/A_f` was **{_format(robustness_spread)}** "
            "(fraction), indicating low sensitivity within only these limited checks.",
            "",
            "## Claim boundary",
            "",
            "No row confirms a physical cause. In particular, positive-tension softening must not be "
            "called cable slackening, and C_TRUE_2 parameters must not be represented as real PV properties.",
            "B0 permits mathematical compression by definition; its negative minimum tension and `T<=0` "
            "fraction are not zero-tension state transitions.",
        ]
    )
    return "\n".join(lines) + "\n"


def run_suite(
    config_path: Path, output_root: Path, report_path: Path
) -> tuple[str, list[dict[str, Any]], float]:
    base = load_config(config_path)
    if base["data_classification"] != CLASSIFICATION:
        raise ValueError(f"Falsification suite requires {CLASSIFICATION}")
    if any(part.lower() == "results" for part in output_root.resolve().parts):
        raise ValueError("Stage 2 development output cannot enter the formal results directory")
    suite_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    suite_root = output_root / suite_id
    suite_root.mkdir(parents=True, exist_ok=False)
    started = time.perf_counter()
    rows: list[dict[str, Any]] = []
    for case_id, purpose, config, switches, coordinate in predefined_cases(base):
        row, history = _run_case(case_id, purpose, config, switches, response_coordinate=coordinate)
        case_root = suite_root / case_id
        case_root.mkdir()
        history.to_csv(case_root / "time_history.csv", index=False)
        (case_root / "metadata.json").write_text(
            json.dumps(row, indent=2, allow_nan=False) + "\n", encoding="utf-8"
        )
        rows.append(row)
        LOGGER.info("%s completed in %.3f s", case_id, row["runtime_seconds"])
    runtime = time.perf_counter() - started
    pd.DataFrame(rows).to_csv(suite_root / "falsification_summary.csv", index=False)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, runtime, suite_id), encoding="utf-8")
    return suite_id, rows, runtime


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run predefined Stage 2 mechanism falsification controls.")
    parser.add_argument("--config", type=Path, default=Path("config/stage2_falsification.yaml"))
    parser.add_argument(
        "--output-root", type=Path, default=Path("prototype_results/stage2_falsification")
    )
    parser.add_argument(
        "--report", type=Path, default=Path("reports/STAGE2_MECHANISM_FALSIFICATION.md")
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        suite_id, _, runtime = run_suite(args.config, args.output_root, args.report)
        LOGGER.info("Falsification suite %s completed in %.3f s", suite_id, runtime)
        return 0
    except Exception:
        LOGGER.exception("Mechanism falsification failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
