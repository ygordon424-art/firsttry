#!/usr/bin/env python3
"""Two-DOF bending-torsion mechanism-screening ROM using synthetic defaults only."""

from __future__ import annotations

import argparse
import json
import logging
import subprocess
import time as wall_time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import yaml
from scipy.integrate import solve_ivp
from scipy.linalg import eigh

try:
    from .harmonic_analysis import identify_harmonics, one_sided_fft, welch_psd
except ImportError:
    from harmonic_analysis import identify_harmonics, one_sided_fft, welch_psd

LOGGER = logging.getLogger("nonlinear_rom")
MODEL_LIN = "MODEL_LIN"
MODEL_GEO = "MODEL_GEO"
MODEL_TENSION_ONLY = "MODEL_TENSION_ONLY"
MODEL_TYPES = (MODEL_LIN, MODEL_GEO, MODEL_TENSION_ONLY)
CLASSIFICATION = "MECHANISM_PROTOTYPE"
STAGE2_CLASSIFICATION = "STAGE2_MECHANISM_DEVELOPMENT"
ALLOWED_CLASSIFICATIONS = {CLASSIFICATION, STAGE2_CLASSIFICATION}


@dataclass(frozen=True)
class MechanismSwitches:
    """Independent nonlinear terms; the base linear M/C/K system is always present."""

    quadratic_coupling: bool = False
    cubic_stiffness: bool = False
    bending_torsion_coupling: bool = False
    tension_only: bool = False

    def as_dict(self) -> dict[str, bool]:
        return {
            "linear": True,
            "quadratic_coupling": self.quadratic_coupling,
            "cubic_stiffness": self.cubic_stiffness,
            "bending_torsion_coupling": self.bending_torsion_coupling,
            "tension_only": self.tension_only,
        }


@dataclass(frozen=True)
class RomResult:
    time: np.ndarray
    displacement: np.ndarray
    velocity: np.ndarray
    force: np.ndarray
    tension_surrogate: np.ndarray
    tangent_stiffness: np.ndarray
    stiffness_state: tuple[str, ...]
    model_type: str
    tension_only: bool
    natural_frequencies_hz: np.ndarray
    runtime_seconds: float
    solver_message: str
    mechanism_switches: MechanismSwitches


def load_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("ROM configuration must be a YAML mapping")
    if config.get("data_classification") not in ALLOWED_CLASSIFICATIONS:
        raise ValueError(f"data_classification must be one of {sorted(ALLOWED_CLASSIFICATIONS)}")
    if "SYNTHETIC" not in str(config.get("parameter_status", "")).upper():
        raise ValueError("ROM defaults must be explicitly marked SYNTHETIC")
    return config


def _matrix(config: dict[str, Any], name: str) -> np.ndarray:
    value = np.asarray(config["dynamics"][name], dtype=float)
    if value.shape != (2, 2) or not np.isfinite(value).all():
        raise ValueError(f"{name} must be a finite 2x2 matrix")
    if not np.allclose(value, value.T):
        raise ValueError(f"{name} must be symmetric")
    return value


def natural_frequencies(config: dict[str, Any]) -> np.ndarray:
    mass = _matrix(config, "mass_matrix")
    stiffness = _matrix(config, "linear_stiffness_matrix")
    eigenvalues = eigh(stiffness, mass, eigvals_only=True)
    if np.any(eigenvalues <= 0):
        raise ValueError("Mass and stiffness matrices must define positive natural frequencies")
    return np.sqrt(eigenvalues) / (2.0 * np.pi)


def damping_matrix(config: dict[str, Any]) -> np.ndarray:
    dynamics = config["dynamics"]
    if "damping_matrix" in dynamics:
        damping = np.asarray(dynamics["damping_matrix"], dtype=float)
        if damping.shape != (2, 2) or not np.isfinite(damping).all():
            raise ValueError("damping_matrix must be a finite 2x2 matrix")
        return damping
    ratio = float(dynamics["damping_ratio"])
    if ratio < 0:
        raise ValueError("damping_ratio cannot be negative")
    omega = 2.0 * np.pi * natural_frequencies(config)
    coefficients = np.linalg.solve(
        np.array([[1.0 / (2.0 * omega[0]), omega[0] / 2.0],
                  [1.0 / (2.0 * omega[1]), omega[1] / 2.0]]),
        np.array([ratio, ratio]),
    )
    return coefficients[0] * _matrix(config, "mass_matrix") + coefficients[1] * _matrix(
        config, "linear_stiffness_matrix"
    )


def forcing_function(config: dict[str, Any]) -> Callable[[float], np.ndarray]:
    forcing = config["forcing"]
    forcing_type = str(forcing["type"])
    if forcing_type == "harmonic":
        amplitudes = np.asarray(forcing["amplitudes"], dtype=float)
        phases = np.deg2rad(np.asarray(forcing.get("phases_deg", [0.0, 0.0]), dtype=float))
        frequency = float(forcing["frequency_hz"])
        if amplitudes.shape != (2,) or phases.shape != (2,) or frequency <= 0:
            raise ValueError("Harmonic forcing needs two amplitudes/phases and positive frequency")
        return lambda t: amplitudes * np.sin(2.0 * np.pi * frequency * t + phases)
    if forcing_type == "broadband_synthetic":
        components = forcing.get("broadband_components", [])
        if not components:
            raise ValueError("broadband_synthetic forcing needs at least one component")
        parsed: list[tuple[float, np.ndarray, np.ndarray]] = []
        for component in components:
            frequency = float(component["frequency_hz"])
            amplitudes = np.asarray(component["amplitudes"], dtype=float)
            phases = np.deg2rad(np.asarray(component.get("phases_deg", [0.0, 0.0]), dtype=float))
            if frequency <= 0 or amplitudes.shape != (2,) or phases.shape != (2,):
                raise ValueError("Each broadband component needs positive frequency and two components")
            parsed.append((frequency, amplitudes, phases))

        def broadband(t: float) -> np.ndarray:
            return sum(
                (amplitude * np.sin(2.0 * np.pi * frequency * t + phase)
                 for frequency, amplitude, phase in parsed),
                start=np.zeros(2),
            )

        return broadband
    raise ValueError(f"Unknown forcing type: {forcing_type}")


def tension_element(
    q: np.ndarray, config: dict[str, Any], *, tension_only: bool
) -> tuple[np.ndarray, float, float, str]:
    parameters = config["tension_surrogate"]
    direction = np.asarray(parameters["direction"], dtype=float)
    if direction.shape != (2,) or np.linalg.norm(direction) == 0:
        raise ValueError("tension surrogate direction must be a non-zero two-component vector")
    stiffness = float(parameters["stiffness"])
    pretension = float(parameters["pretension"])
    threshold = float(parameters["low_tension_threshold"])
    ratio = float(parameters["low_tension_stiffness_ratio"])
    if stiffness <= 0 or not 0 <= ratio <= 1 or threshold < 0 or pretension < threshold:
        raise ValueError("Invalid tension surrogate stiffness, ratio, threshold, or pretension")
    extension = float(direction @ q)
    raw_tension = pretension + stiffness * extension
    if not tension_only:
        return direction * stiffness * extension, raw_tension, stiffness, "BIDIRECTIONAL_LINEAR"
    transition_extension = (threshold - pretension) / stiffness
    if raw_tension > threshold:
        tension = raw_tension
        tangent = stiffness
        state = "TAUT"
    else:
        tangent = stiffness * ratio
        tension = threshold + tangent * (extension - transition_extension)
        if tension <= 0:
            tension = 0.0
            tangent = 0.0
            state = "ZERO_TENSION"
        else:
            state = "LOW_TENSION"
    return direction * (tension - pretension), tension, tangent, state


def internal_force(
    q: np.ndarray,
    config: dict[str, Any],
    model_type: str,
    *,
    tension_only: bool = False,
    mechanism_switches: MechanismSwitches | None = None,
) -> tuple[np.ndarray, float, float, str]:
    if model_type not in MODEL_TYPES:
        raise ValueError(f"Unknown model type: {model_type}")
    q = np.asarray(q, dtype=float)
    linear = _matrix(config, "linear_stiffness_matrix") @ q
    if mechanism_switches is None:
        if model_type == MODEL_LIN:
            mechanism_switches = MechanismSwitches()
        elif model_type == MODEL_GEO:
            # Backward-compatible Stage 1 aggregate model. Stage 2 uses explicit switches.
            mechanism_switches = MechanismSwitches(True, True, True, False)
        else:
            mechanism_switches = MechanismSwitches(tension_only=True)
    z, theta = q
    coefficients = config["geometric_nonlinearity"]
    nonlinear = np.zeros(2)
    if mechanism_switches.quadratic_coupling:
        gamma = float(coefficients["quadratic_coupling"])
        nonlinear += np.array([gamma * z * theta, 0.5 * gamma * z**2])
    if mechanism_switches.cubic_stiffness:
        az = float(coefficients["cubic_z"])
        at = float(coefficients["cubic_theta"])
        nonlinear += np.array([az * z**3, at * theta**3])
    if mechanism_switches.bending_torsion_coupling:
        beta = float(coefficients["cubic_coupling"])
        nonlinear += np.array([beta * z * theta**2, beta * theta * z**2])
    if not mechanism_switches.tension_only:
        return linear + nonlinear, float("nan"), float("nan"), "NOT_APPLICABLE"
    element_force, tension, tangent, state = tension_element(
        q, config, tension_only=tension_only
    )
    return linear + nonlinear + element_force, tension, tangent, state


def simulate(
    config: dict[str, Any],
    model_type: str,
    *,
    tension_only: bool | None = None,
    mechanism_switches: MechanismSwitches | None = None,
) -> RomResult:
    mass = _matrix(config, "mass_matrix")
    damping = damping_matrix(config)
    forcing = forcing_function(config)
    settings = config["solver"]
    duration = float(settings["duration_seconds"])
    sampling_frequency = float(settings["sampling_frequency_hz"])
    max_runtime = float(settings.get("max_runtime_seconds", 300.0))
    if duration <= 0 or sampling_frequency <= 0 or max_runtime <= 0 or max_runtime > 300:
        raise ValueError("Duration/frequency must be positive and runtime limit cannot exceed 300 s")
    sample_count = int(round(duration * sampling_frequency)) + 1
    evaluation_times = np.linspace(0.0, duration, sample_count)
    initial = config["initial_conditions"]
    y0 = np.concatenate(
        [np.asarray(initial["displacement"], dtype=float),
         np.asarray(initial["velocity"], dtype=float)]
    )
    if y0.shape != (4,):
        raise ValueError("Initial displacement and velocity must each have two components")
    active_tension_only = (
        bool(config["tension_surrogate"]["tension_only"])
        if tension_only is None and model_type == MODEL_TENSION_ONLY
        else bool(tension_only)
    )
    active_switches = mechanism_switches
    if active_switches is None:
        if model_type == MODEL_LIN:
            active_switches = MechanismSwitches()
        elif model_type == MODEL_GEO:
            active_switches = MechanismSwitches(True, True, True, False)
        else:
            active_switches = MechanismSwitches(tension_only=True)
    started = wall_time.perf_counter()

    def derivative(t: float, state: np.ndarray) -> np.ndarray:
        if wall_time.perf_counter() - started > max_runtime:
            raise TimeoutError(f"ROM solve exceeded the {max_runtime:g} s runtime limit")
        q = state[:2]
        velocity = state[2:]
        restoring, _, _, _ = internal_force(
            q,
            config,
            model_type,
            tension_only=active_tension_only,
            mechanism_switches=active_switches,
        )
        acceleration = np.linalg.solve(mass, forcing(t) - damping @ velocity - restoring)
        return np.concatenate([velocity, acceleration])

    solution = solve_ivp(
        derivative,
        (0.0, duration),
        y0,
        t_eval=evaluation_times,
        method=str(settings.get("method", "RK45")),
        max_step=float(settings["max_step_seconds"]),
        rtol=float(settings["relative_tolerance"]),
        atol=float(settings["absolute_tolerance"]),
    )
    runtime = wall_time.perf_counter() - started
    if not solution.success:
        raise RuntimeError(f"ROM integration failed: {solution.message}")
    applied_force = np.column_stack([forcing(t) for t in solution.t]).T
    tensions: list[float] = []
    tangents: list[float] = []
    states: list[str] = []
    for q in solution.y[:2].T:
        _, tension, tangent, state = internal_force(
            q,
            config,
            model_type,
            tension_only=active_tension_only,
            mechanism_switches=active_switches,
        )
        tensions.append(tension)
        tangents.append(tangent)
        states.append(state)
    return RomResult(
        time=solution.t,
        displacement=solution.y[:2].T,
        velocity=solution.y[2:].T,
        force=applied_force,
        tension_surrogate=np.asarray(tensions),
        tangent_stiffness=np.asarray(tangents),
        stiffness_state=tuple(states),
        model_type=model_type,
        tension_only=active_tension_only,
        natural_frequencies_hz=natural_frequencies(config),
        runtime_seconds=runtime,
        solver_message=str(solution.message),
        mechanism_switches=active_switches,
    )


def linear_energy(result: RomResult, config: dict[str, Any]) -> np.ndarray:
    mass = _matrix(config, "mass_matrix")
    stiffness = _matrix(config, "linear_stiffness_matrix")
    kinetic = 0.5 * np.einsum("ni,ij,nj->n", result.velocity, mass, result.velocity)
    potential = 0.5 * np.einsum(
        "ni,ij,nj->n", result.displacement, stiffness, result.displacement
    )
    return kinetic + potential


def analyze_response(result: RomResult, fundamental_frequency: float) -> dict[str, Any]:
    analysis: dict[str, Any] = {}
    for index, name in enumerate(("z", "theta")):
        fft_frequency, fft_amplitude = one_sided_fft(result.time, result.displacement[:, index])
        psd_frequency, psd = welch_psd(result.time, result.displacement[:, index])
        analysis[name] = {
            "fft_frequency": fft_frequency,
            "fft_amplitude": fft_amplitude,
            "psd_frequency": psd_frequency,
            "psd": psd,
            "harmonics": identify_harmonics(
                fft_frequency, fft_amplitude, fundamental_frequency=fundamental_frequency
            ),
        }
    return analysis


def _git_sha(repository_root: Path) -> str:
    commands = [
        ["git", "rev-parse", "HEAD"],
        ["git", "--git-dir=work/git-meta", "--work-tree=.", "rev-parse", "HEAD"],
    ]
    for command in commands:
        completed = subprocess.run(
            command, cwd=repository_root, capture_output=True, text=True, check=False
        )
        if completed.returncode == 0:
            return completed.stdout.strip()
    return "UNKNOWN"


def _save_plot(
    path: Path,
    x: np.ndarray,
    y: np.ndarray,
    xlabel: str,
    ylabel: str,
    *,
    classification: str = CLASSIFICATION,
) -> None:
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.plot(x, y, linewidth=0.9)
    axis.set(xlabel=xlabel, ylabel=ylabel, title=f"{classification} — SYNTHETIC")
    axis.grid(True, alpha=0.3)
    figure.tight_layout()
    figure.savefig(path, dpi=160)
    plt.close(figure)


def write_outputs(
    result: RomResult,
    analysis: dict[str, Any],
    config: dict[str, Any],
    output_dir: Path,
    *,
    run_id: str,
    repository_root: Path,
) -> None:
    if any(part.lower() == "results" for part in output_dir.resolve().parts):
        raise ValueError("Mechanism prototype output is forbidden under the formal results directory")
    output_dir.mkdir(parents=True, exist_ok=False)
    classification = str(config["data_classification"])
    pd.DataFrame(
        {
            "time_seconds": result.time,
            "z": result.displacement[:, 0],
            "theta": result.displacement[:, 1],
            "z_velocity": result.velocity[:, 0],
            "theta_velocity": result.velocity[:, 1],
            "force_z": result.force[:, 0],
            "force_theta": result.force[:, 1],
            "T_surrogate": result.tension_surrogate,
            "K_tangent": result.tangent_stiffness,
            "stiffness_state": result.stiffness_state,
            "data_classification": classification,
        }
    ).to_csv(output_dir / "time_history.csv", index=False)
    spectrum_rows: list[dict[str, Any]] = []
    for signal_name in ("z", "theta"):
        for spectrum_type, frequency_key, value_key in (
            ("FFT_AMPLITUDE", "fft_frequency", "fft_amplitude"),
            ("WELCH_PSD", "psd_frequency", "psd"),
        ):
            spectrum_rows.extend(
                {
                    "signal": signal_name,
                    "spectrum_type": spectrum_type,
                    "frequency_hz": frequency,
                    "value": value,
                    "data_classification": classification,
                }
                for frequency, value in zip(
                    analysis[signal_name][frequency_key], analysis[signal_name][value_key]
                )
            )
    pd.DataFrame(spectrum_rows).to_csv(output_dir / "spectrum.csv", index=False)
    summary_rows = []
    for signal_name in ("z", "theta"):
        harmonic = analysis[signal_name]["harmonics"]
        summary_rows.append(
            {
                "run_id": run_id,
                "model_type": result.model_type,
                "tension_only": result.tension_only,
                "signal": signal_name,
                "f0_hz": harmonic["fundamental_frequency_hz"],
                "A_2f_over_A_f": harmonic["A_2f_over_A_f"],
                "A_3f_over_A_f": harmonic["A_3f_over_A_f"],
                "data_classification": classification,
                "interpretation": "Signal feature only; no physical mechanism is inferred.",
            }
        )
    pd.DataFrame(summary_rows).to_csv(output_dir / "summary.csv", index=False)
    metadata = {
        "run_id": run_id,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "git_commit": _git_sha(repository_root),
        "model_type": result.model_type,
        "tension_only": result.tension_only,
        "mechanism_switches": result.mechanism_switches.as_dict(),
        "parameter_set": config,
        "solver": {
            "name": "scipy.integrate.solve_ivp",
            "method": config["solver"].get("method", "RK45"),
            "message": result.solver_message,
        },
        "dt_seconds": 1.0 / float(config["solver"]["sampling_frequency_hz"]),
        "duration_seconds": float(config["solver"]["duration_seconds"]),
        "forcing": config["forcing"],
        "runtime_seconds": result.runtime_seconds,
        "natural_frequencies_hz": result.natural_frequencies_hz.tolist(),
        "observed_stiffness_states": sorted(set(result.stiffness_state)),
        "data_classification": classification,
        "claim_limit": "MECHANISM_PROTOTYPE only; not validated and not a research conclusion.",
    }
    (output_dir / "metadata.json").write_text(
        json.dumps(metadata, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    _save_plot(
        output_dir / "z_time_history.png",
        result.time,
        result.displacement[:, 0],
        "Time (s)",
        "z",
        classification=classification,
    )
    _save_plot(
        output_dir / "theta_time_history.png",
        result.time,
        result.displacement[:, 1],
        "Time (s)",
        "theta",
        classification=classification,
    )
    for signal_name in ("z", "theta"):
        figure, axis = plt.subplots(figsize=(8, 4.5))
        axis.semilogy(
            analysis[signal_name]["psd_frequency"],
            np.maximum(analysis[signal_name]["psd"], np.finfo(float).tiny),
        )
        axis.set(
            xlabel="Frequency (Hz)",
            ylabel=f"{signal_name} PSD",
            title=f"{classification} — SYNTHETIC",
        )
        axis.grid(True, alpha=0.3)
        figure.tight_layout()
        figure.savefig(output_dir / f"{signal_name}_psd.png", dpi=160)
        plt.close(figure)
    ratio_labels = ["z: 2f/f", "z: 3f/f", "theta: 2f/f", "theta: 3f/f"]
    ratios = [
        analysis["z"]["harmonics"]["A_2f_over_A_f"],
        analysis["z"]["harmonics"]["A_3f_over_A_f"],
        analysis["theta"]["harmonics"]["A_2f_over_A_f"],
        analysis["theta"]["harmonics"]["A_3f_over_A_f"],
    ]
    figure, axis = plt.subplots(figsize=(8, 4.5))
    axis.bar(ratio_labels, ratios)
    axis.set(ylabel="Amplitude ratio", title=f"{classification} — signal features only")
    axis.tick_params(axis="x", rotation=20)
    figure.tight_layout()
    figure.savefig(output_dir / "harmonic_ratio.png", dpi=160)
    plt.close(figure)
    if np.isfinite(result.tension_surrogate).any():
        _save_plot(
            output_dir / "tension_surrogate.png",
            result.time,
            result.tension_surrogate,
            "Time (s)",
            "T_surrogate",
            classification=classification,
        )
        _save_plot(
            output_dir / "tangent_stiffness.png",
            result.time,
            result.tangent_stiffness,
            "Time (s)",
            "K_tangent",
            classification=classification,
        )
    else:
        for filename, label in (
            ("tension_surrogate.png", "T_surrogate: not applicable"),
            ("tangent_stiffness.png", "K_tangent: not applicable"),
        ):
            figure, axis = plt.subplots(figsize=(8, 4.5))
            axis.text(0.5, 0.5, label, ha="center", va="center", transform=axis.transAxes)
            axis.set(title=f"{classification} — {result.model_type}")
            axis.set_axis_off()
            figure.tight_layout()
            figure.savefig(output_dir / filename, dpi=160)
            plt.close(figure)


def run_suite(config_path: Path, output_root: Path, repository_root: Path) -> tuple[str, list[Path]]:
    config = load_config(config_path)
    suite_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    suite_root = output_root / suite_id
    paths: list[Path] = []
    fundamental = float(config["analysis"]["fundamental_frequency_hz"])
    for model_type in MODEL_TYPES:
        run_id = f"{suite_id}-{model_type.lower()}"
        result = simulate(
            config,
            model_type,
            tension_only=(model_type == MODEL_TENSION_ONLY),
        )
        analysis = analyze_response(result, fundamental)
        case_path = suite_root / model_type
        write_outputs(
            result,
            analysis,
            config,
            case_path,
            run_id=run_id,
            repository_root=repository_root,
        )
        paths.append(case_path)
        LOGGER.info("Completed %s in %.3f s", model_type, result.runtime_seconds)
    return suite_id, paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the synthetic two-DOF Direction 1 mechanism-screening ROM."
    )
    parser.add_argument("--config", type=Path, default=Path("config/rom_config.yaml"))
    parser.add_argument(
        "--output-root", type=Path, default=Path("prototype_results/direction1_rom")
    )
    parser.add_argument("--repository-root", type=Path, default=Path.cwd())
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    try:
        run_id, paths = run_suite(args.config, args.output_root, args.repository_root)
        LOGGER.info("Synthetic mechanism suite %s written to %s", run_id, paths[0].parent)
        return 0
    except Exception:
        LOGGER.exception("ROM mechanism prototype failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
