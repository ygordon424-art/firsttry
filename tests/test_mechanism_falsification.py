from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from scripts.nonlinear_rom import (
    ABRUPT_PIECEWISE,
    BILATERAL_LINEAR,
    LOW_TENSION_SOFTENING,
    SMOOTH_TRANSITION,
    TRUE_TENSION_ONLY,
    cable_surrogate,
    load_config,
    natural_frequencies,
)
from scripts.run_mechanism_falsification import predefined_cases, run_suite


@pytest.fixture
def config() -> dict:
    # SYNTHETIC mechanism-control parameters only.
    return load_config(Path("config/stage2_falsification.yaml"))


def test_true_tension_only_stays_taut_when_predicted_tension_is_positive(config):
    controlled = deepcopy(config)
    controlled["tension_surrogate"]["low_tension_threshold"] = 0.0
    _, tension, tangent, state = cable_surrogate(
        np.array([0.0, 0.0]), controlled, mode=TRUE_TENSION_ONLY
    )
    assert tension > 0
    assert tangent == pytest.approx(controlled["tension_surrogate"]["stiffness"])
    assert state == "TAUT"


def test_true_tension_only_clips_predicted_compression_to_zero(config):
    controlled = deepcopy(config)
    controlled["tension_surrogate"]["low_tension_threshold"] = 0.0
    _, tension, tangent, state = cable_surrogate(
        np.array([-0.02, 0.0]), controlled, mode=TRUE_TENSION_ONLY
    )
    assert tension == 0.0
    assert tangent == 0.0
    assert state == "ZERO_TENSION"


def test_true_tension_only_rejects_positive_threshold(config):
    with pytest.raises(ValueError, match="requires low_tension_threshold = 0"):
        cable_surrogate(np.zeros(2), config, mode=TRUE_TENSION_ONLY)


def test_smooth_transition_is_continuous(config):
    parameters = config["tension_surrogate"]
    transition_extension = (
        parameters["low_tension_threshold"] - parameters["pretension"]
    ) / parameters["stiffness"]
    epsilon = 1e-9
    below = cable_surrogate(
        np.array([transition_extension - epsilon, 0.0]),
        config,
        mode=LOW_TENSION_SOFTENING,
        transition_form=SMOOTH_TRANSITION,
    )
    above = cable_surrogate(
        np.array([transition_extension + epsilon, 0.0]),
        config,
        mode=LOW_TENSION_SOFTENING,
        transition_form=SMOOTH_TRANSITION,
    )
    assert abs(above[1] - below[1]) < 1e-6
    assert abs(above[2] - below[2]) < 1e-4


def test_abrupt_and_smooth_modes_are_independently_selectable(config):
    q = np.array([-0.004, 0.0])
    abrupt = cable_surrogate(
        q,
        config,
        mode=LOW_TENSION_SOFTENING,
        transition_form=ABRUPT_PIECEWISE,
    )
    smooth = cable_surrogate(
        q,
        config,
        mode=LOW_TENSION_SOFTENING,
        transition_form=SMOOTH_TRANSITION,
    )
    bilateral = cable_surrogate(q, config, mode=BILATERAL_LINEAR)
    assert abrupt[2] == pytest.approx(
        config["tension_surrogate"]["stiffness"]
        * config["tension_surrogate"]["low_tension_stiffness_ratio"]
    )
    assert abrupt[2] < smooth[2] < bilateral[2]


def test_internal_resonance_controls_have_verified_frequency_ratios(config):
    cases = {case_id: case_config for case_id, _, case_config, _, _ in predefined_cases(config)}
    near_ratio = natural_frequencies(cases["IR1"])[1] / natural_frequencies(cases["IR1"])[0]
    detuned_ratio = natural_frequencies(cases["IR2"])[1] / natural_frequencies(cases["IR2"])[0]
    assert near_ratio == pytest.approx(2.0, rel=1e-12)
    assert detuned_ratio == pytest.approx(1.6, rel=1e-12)


def test_falsification_outputs_cannot_enter_formal_results(config, tmp_path):
    with pytest.raises(ValueError, match="formal results"):
        run_suite(
            Path("config/stage2_falsification.yaml"),
            tmp_path / "results" / "forbidden",
            tmp_path / "report.md",
        )
