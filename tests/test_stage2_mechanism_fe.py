from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from fe.abaqus.generate_model import (
    detect_abaqus_environment,
    generate,
    load_and_validate_config,
    render_input_deck,
    validate_config,
)
from scripts.harmonic_analysis import robust_harmonic_analysis, steady_state_window
from scripts.nonlinear_rom import (
    MODEL_LIN,
    MechanismSwitches,
    internal_force,
    load_config,
    simulate,
)


@pytest.fixture
def stage2_config() -> dict:
    # SYNTHETIC / NON-PHYSICAL DEFAULT: mechanism software verification only.
    return load_config(Path("config/stage2_mechanism.yaml"))


def _robust_report(time: np.ndarray, values: np.ndarray, f0: float) -> dict:
    return robust_harmonic_analysis(
        time,
        values,
        fundamental_frequency_hz=f0,
        frequency_reference="FORCING",
        discard_initial_fraction=0.5,
        spectral_window="hann",
        frequency_bin_tolerance_hz=0.06,
        minimum_forcing_cycles=8,
        integer_cycle_window=True,
    )


def test_rom_linear_single_frequency_negative_control(stage2_config):
    result = simulate(stage2_config, MODEL_LIN, mechanism_switches=MechanismSwitches())
    f0 = stage2_config["analysis"]["fundamental_frequency_hz"]
    report = _robust_report(result.time, result.displacement[:, 0], f0)
    assert report["harmonics"]["A_2f_over_A_f"] < 0.01


def test_injected_input_2f_positive_detection():
    sampling_frequency = 200.0
    time = np.arange(0.0, 20.0 + 1.0 / sampling_frequency, 1.0 / sampling_frequency)
    f0 = 0.8
    # INPUT_2F_DETECTION synthetic software control; not mechanism evidence.
    values = np.sin(2 * np.pi * f0 * time) + 0.05 * np.sin(2 * np.pi * 2 * f0 * time)
    report = _robust_report(time, values, f0)
    assert report["harmonics"]["A_2f_over_A_f"] == pytest.approx(0.05, abs=0.002)


def test_nonlinear_mechanism_switches_are_independent(stage2_config):
    q = np.array([0.08, 0.04])
    base, *_ = internal_force(q, stage2_config, MODEL_LIN, mechanism_switches=MechanismSwitches())
    forces = {}
    for name, switches in {
        "quadratic": MechanismSwitches(quadratic_coupling=True),
        "cubic": MechanismSwitches(cubic_stiffness=True),
        "bending_torsion": MechanismSwitches(bending_torsion_coupling=True),
        "tension_only": MechanismSwitches(tension_only=True),
    }.items():
        forces[name], *_ = internal_force(
            q,
            stage2_config,
            MODEL_LIN,
            tension_only=switches.tension_only,
            mechanism_switches=switches,
        )
        assert not np.allclose(forces[name], base)
    assert len({tuple(np.round(force - base, 10)) for force in forces.values()}) == 4


def test_frequency_reference_is_explicit_and_validated():
    time = np.linspace(0.0, 20.0, 2001)
    values = np.sin(2 * np.pi * 0.8 * time)
    report = _robust_report(time, values, 0.8)
    assert report["harmonics"]["frequency_reference"] == "FORCING"
    with pytest.raises(ValueError, match="frequency_reference"):
        robust_harmonic_analysis(
            time,
            values,
            fundamental_frequency_hz=0.8,
            frequency_reference="AMBIGUOUS",
        )


def test_steady_state_window_reports_cycles():
    time = np.linspace(0.0, 20.0, 2001)
    values = np.sin(2 * np.pi * 0.8 * time)
    selected_time, _, metadata = steady_state_window(
        time,
        values,
        reference_frequency_hz=0.8,
        discard_initial_fraction=0.5,
        minimum_cycles=8,
        integer_cycle_window=True,
    )
    assert selected_time[0] >= 10.0
    assert metadata["analyzed_cycles"] == pytest.approx(8.0)
    assert metadata["analysis_duration_seconds"] == pytest.approx(10.0)


def test_fe_config_validation_rejects_unverified_tension_only():
    config = load_and_validate_config(Path("config/fe_generic.yaml"))
    invalid = deepcopy(config)
    invalid["switches"]["tension_only"] = True
    with pytest.raises(ValueError, match="NOT YET VERIFIED"):
        validate_config(invalid)


def test_fe_generator_is_deterministic(tmp_path):
    config = load_and_validate_config(Path("config/fe_generic.yaml"))
    assert render_input_deck(config) == render_input_deck(config)
    first = tmp_path / "first"
    second = tmp_path / "second"
    first_paths = generate(Path("config/fe_generic.yaml"), first)
    second_paths = generate(Path("config/fe_generic.yaml"), second)
    assert first_paths[0].read_bytes() == second_paths[0].read_bytes()
    assert first_paths[1].read_bytes() == second_paths[1].read_bytes()


def test_abaqus_absence_is_handled_without_fabricated_results(monkeypatch):
    monkeypatch.setattr("fe.abaqus.generate_model.shutil.which", lambda _: None)
    monkeypatch.delenv("ABAQUSLM_LICENSE_FILE", raising=False)
    monkeypatch.delenv("LM_LICENSE_FILE", raising=False)
    report = detect_abaqus_environment()
    assert report["ABAQUS_AVAILABLE"] == "NO"
    assert report["LICENSE_AVAILABLE"] == "UNKNOWN"
    assert report["SMOKE_TEST"] == "NOT RUN"
