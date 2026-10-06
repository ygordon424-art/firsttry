import numpy as np
import pytest

from scripts.harmonic_analysis import analyze_signal


def test_synthetic_fundamental_and_second_harmonic():
    # SYNTHETIC_TEST_DATA: software verification only, never an experimental result.
    sampling_frequency = 200.0
    time = np.arange(0.0, 4.0, 1.0 / sampling_frequency)
    fundamental = 5.0
    values = np.sin(2 * np.pi * fundamental * time) + 0.2 * np.sin(
        2 * np.pi * 2 * fundamental * time
    )
    report = analyze_signal(time, values, fundamental_frequency=fundamental)
    assert report["peaks"]["1f0"]["detected_frequency_hz"] == pytest.approx(5.0)
    assert report["peaks"]["2f0"]["detected_frequency_hz"] == pytest.approx(10.0)
    assert report["A_2f_over_A_f"] == pytest.approx(0.2, abs=0.01)
    assert "no nonlinear mechanism" in report["interpretation"]


def test_candidate_fundamental_is_labeled_candidate():
    # SYNTHETIC_TEST_DATA
    time = np.arange(0.0, 2.0, 0.002)
    values = np.sin(2 * np.pi * 7.0 * time)
    report = analyze_signal(time, values)
    assert report["fundamental_frequency_hz"] == pytest.approx(7.0, abs=0.01)
    assert report["fundamental_source"] == "candidate_from_largest_fft_peak"
