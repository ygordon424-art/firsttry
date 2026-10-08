import json

import numpy as np
import pytest

from scripts.analyze_pressure_array import spectral_relationship
from scripts.coherence_prototype import (
    analyse_spatial_coherence,
    make_synthetic_signals,
    pair_distance,
    synthetic_coordinates,
    write_outputs,
)
from scripts.coherence_response_demo import modal_response_demo, write_outputs as write_response_outputs


def test_identical_and_independent_synthetic_signal_coherence():
    # SYNTHETIC_TEST_DATA: test the reused pairwise interface, not wind data.
    rng = np.random.default_rng(14)
    time = np.arange(0.0, 20.0, 0.01)
    identical = np.sin(2 * np.pi * 3.0 * time)
    independent = rng.normal(size=time.size)
    same = spectral_relationship(identical, identical, 100.0, nperseg=500)
    separate = spectral_relationship(identical, independent, 100.0, nperseg=500)
    index = int(np.argmin(np.abs(same["frequency_hz"] - 3.0)))
    assert same["coherence"][index] > 0.99
    assert np.mean(separate["coherence"][(separate["frequency_hz"] > 1.0) & (separate["frequency_hz"] < 12.0)]) < 0.35


def test_known_phase_lag_is_identified():
    time = np.arange(0.0, 20.0, 0.01)
    phase_offset = np.pi / 3
    first = np.sin(2 * np.pi * 3.0 * time)
    second = np.sin(2 * np.pi * 3.0 * time + phase_offset)
    relationship = spectral_relationship(first, second, 100.0, nperseg=500)
    index = int(np.argmin(np.abs(relationship["frequency_hz"] - 3.0)))
    assert relationship["phase_radians"][index] == pytest.approx(phase_offset, abs=0.08)


def test_distance_and_multichannel_matrices_are_correct():
    coordinates = synthetic_coordinates(8)
    assert pair_distance(coordinates, 0, 1) == pytest.approx(np.linalg.norm(coordinates[0] - coordinates[1]))
    _, signals, _ = make_synthetic_signals()
    correlation, coherence, phase, distance_table = analyse_spatial_coherence(signals, coordinates, 100.0)
    assert correlation.shape == coherence.shape == phase.shape == (8, 8)
    assert len(distance_table) == 28
    assert coherence.iloc[0, 1] > 0.99


def test_prototype_outputs_are_synthetic_and_not_formal_results(tmp_path):
    output_dir = tmp_path / "prototype_results" / "direction2_coherence"
    write_outputs(output_dir)
    write_response_outputs(output_dir)
    expected = {"coherence_matrix.csv", "correlation_matrix.csv", "phase_matrix.csv", "distance_coherence.csv", "coherence_matrix.png", "coherence_decay.png", "phase_lag.png", "generalized_force_psd.csv", "response_psd.csv", "response_rms_comparison.csv"}
    assert expected.issubset({path.name for path in output_dir.iterdir()})
    metadata = json.loads((output_dir / "metadata.json").read_text(encoding="utf-8"))
    assert metadata["data_classification"] == "SYNTHETIC_TEST_DATA"
    assert metadata["research_evidence"] is False
    with pytest.raises(ValueError):
        write_outputs(tmp_path / "results")


def test_fully_coherent_and_partial_response_cases_differ():
    force, response, comparison = modal_response_demo()
    assert not force.empty and not response.empty
    coherent = comparison.loc[comparison["case"] == "fully_coherent", "response_rms"].iloc[0]
    partial = comparison.loc[comparison["case"] == "partially_coherent", "response_rms"].iloc[0]
    assert coherent > partial > 0.0
    assert comparison["research_evidence"].eq(False).all()
