from copy import deepcopy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from scripts.nonlinear_rom import (
    CLASSIFICATION,
    MODEL_GEO,
    MODEL_LIN,
    MODEL_TENSION_ONLY,
    analyze_response,
    internal_force,
    linear_energy,
    load_config,
    natural_frequencies,
    simulate,
    write_outputs,
)


@pytest.fixture
def synthetic_config() -> dict:
    # SYNTHETIC / NON-PHYSICAL DEFAULT: software verification only.
    config = load_config(Path("config/rom_config.yaml"))
    config["solver"]["duration_seconds"] = 2.0
    config["solver"]["max_step_seconds"] = 0.01
    return config


def test_linear_two_dof_natural_frequencies_match_theory(synthetic_config):
    config = deepcopy(synthetic_config)
    config["dynamics"] = {
        "mass_matrix": [[2.0, 0.0], [0.0, 1.0]],
        "linear_stiffness_matrix": [[200.0, 0.0], [0.0, 225.0]],
        "damping_matrix": [[0.0, 0.0], [0.0, 0.0]],
    }
    expected = np.array([10.0, 15.0]) / (2.0 * np.pi)
    assert natural_frequencies(config) == pytest.approx(expected, rel=1e-10)


def test_zero_force_damped_linear_energy_decays(synthetic_config):
    config = deepcopy(synthetic_config)
    config["dynamics"]["damping_matrix"] = [[0.5, 0.0], [0.0, 0.2]]
    config["dynamics"].pop("damping_ratio")
    config["forcing"]["amplitudes"] = [0.0, 0.0]
    config["initial_conditions"]["displacement"] = [0.1, 0.03]
    result = simulate(config, MODEL_LIN)
    energy = linear_energy(result, config)
    assert energy[-1] < energy[0]
    assert np.max(np.diff(energy)) < 1e-7


def test_geometric_nonlinear_switch_changes_internal_force(synthetic_config):
    q = np.array([0.08, 0.04])
    linear_force, *_ = internal_force(q, synthetic_config, MODEL_LIN)
    geometric_force, *_ = internal_force(q, synthetic_config, MODEL_GEO)
    assert not np.allclose(geometric_force, linear_force)
    assert np.isfinite(geometric_force).all()


def test_tension_only_false_never_uses_piecewise_branch(synthetic_config):
    result = simulate(synthetic_config, MODEL_TENSION_ONLY, tension_only=False)
    assert set(result.stiffness_state) == {"BIDIRECTIONAL_LINEAR"}
    expected = synthetic_config["tension_surrogate"]["stiffness"]
    assert result.tangent_stiffness == pytest.approx(expected)


def test_tension_only_true_records_stiffness_transition(synthetic_config):
    result = simulate(synthetic_config, MODEL_TENSION_ONLY, tension_only=True)
    assert "TAUT" in result.stiffness_state
    assert "LOW_TENSION" in result.stiffness_state
    assert np.unique(result.tangent_stiffness).size >= 2


def test_harmonic_analysis_output_format(synthetic_config, tmp_path):
    result = simulate(synthetic_config, MODEL_LIN)
    fundamental = synthetic_config["analysis"]["fundamental_frequency_hz"]
    analysis = analyze_response(result, fundamental)
    output = tmp_path / "prototype_results" / "direction1_rom" / "test" / MODEL_LIN
    write_outputs(
        result,
        analysis,
        synthetic_config,
        output,
        run_id="SYNTHETIC_TEST_RUN",
        repository_root=Path.cwd(),
    )
    summary = pd.read_csv(output / "summary.csv")
    spectrum = pd.read_csv(output / "spectrum.csv")
    assert set(summary["signal"]) == {"z", "theta"}
    assert {"f0_hz", "A_2f_over_A_f", "A_3f_over_A_f"} <= set(summary.columns)
    assert set(spectrum["spectrum_type"]) == {"FFT_AMPLITUDE", "WELCH_PSD"}
    assert set(summary["data_classification"]) == {CLASSIFICATION}


def test_mechanism_prototype_cannot_write_to_formal_results(synthetic_config, tmp_path):
    result = simulate(synthetic_config, MODEL_LIN)
    analysis = analyze_response(result, synthetic_config["analysis"]["fundamental_frequency_hz"])
    with pytest.raises(ValueError, match="formal results"):
        write_outputs(
            result,
            analysis,
            synthetic_config,
            tmp_path / "results" / "forbidden",
            run_id="SYNTHETIC_TEST_RUN",
            repository_root=Path.cwd(),
        )
