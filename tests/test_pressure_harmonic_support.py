import json

import numpy as np
import pytest

from scripts.generalized_force_spectrum import (
    generalized_force_harmonics,
    synthetic_pressure_controls,
    write_synthetic_controls,
)
from scripts.pressure_harmonic_audit import harmonic_audit


def _single_channel(amplitude_2f: float = 0.0):
    time = np.arange(0.0, 20.0, 0.01)
    pressure = np.sin(2 * np.pi * 3.0 * time) + amplitude_2f * np.sin(2 * np.pi * 6.0 * time)
    return time, pressure[:, None]


def test_no_2f_negative_control_is_near_zero():
    time, pressure = _single_channel()
    summary, _, _ = harmonic_audit(time, pressure, ["P0"], frequency_value_hz=3.0, frequency_reference="TEST_REFERENCE")
    assert summary.loc[0, "A_2f_over_A_f"] < 1e-8


def test_injected_2f_positive_control_is_detected():
    time, pressure = _single_channel(0.15)
    summary, _, _ = harmonic_audit(time, pressure, ["P2"], frequency_value_hz=3.0, frequency_reference="TEST_REFERENCE")
    assert summary.loc[0, "A_2f"] == pytest.approx(0.15, rel=0.02)


def test_cancellation_and_reinforcement_change_generalized_force_2f():
    time, controls, weights = synthetic_pressure_controls()
    _, cancelled, _, _ = generalized_force_harmonics(time, controls["P3"], weights, frequency_value_hz=3.0, frequency_reference="TEST_REFERENCE")
    _, reinforced, _, _ = generalized_force_harmonics(time, controls["P4"], weights, frequency_value_hz=3.0, frequency_reference="TEST_REFERENCE")
    assert reinforced.loc[0, "A_2f"] > 1.5
    assert cancelled.loc[0, "A_2f"] < reinforced.loc[0, "A_2f"] * 1e-6


def test_reference_resolution_and_startup_window_metadata_are_preserved():
    time, pressure = _single_channel(0.1)
    summary, _, metadata = harmonic_audit(time, pressure, ["P"], frequency_value_hz=3.0, frequency_reference="SYNTHETIC_RESPONSE_FREQUENCY", start_time_seconds=2.0, duration_seconds=10.0)
    assert summary.loc[0, "frequency_reference"] == "SYNTHETIC_RESPONSE_FREQUENCY"
    assert metadata["frequency_resolution_hz"] == pytest.approx(0.1)
    assert metadata["analysis_start_time_seconds"] == pytest.approx(2.0)
    assert metadata["analysis_window"] == "hann"


def test_synthetic_outputs_are_labelled_and_cannot_enter_results(tmp_path):
    output_dir = tmp_path / "prototype_results" / "stage2_pressure_support"
    write_synthetic_controls(output_dir)
    expected = {"channel_harmonics.csv", "generalized_force_time_history.csv", "generalized_force_spectrum.csv", "harmonic_summary.csv", "channel_psd_examples.png", "generalized_force_psd.png", "local_vs_generalized_2f.png"}
    assert expected.issubset({path.name for path in output_dir.iterdir()})
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["data_classification"] == "STAGE2_AERODYNAMIC_INPUT_PROTOTYPE"
    assert metadata["research_evidence"] is False
    with pytest.raises(ValueError):
        write_synthetic_controls(tmp_path / "results")
