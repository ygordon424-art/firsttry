import numpy as np
import pytest

from scripts.analyze_pressure_array import (
    normalized_cross_correlation,
    pressure_to_cp,
    spectral_relationship,
    validate_synchronized_time,
)


def test_pressure_conversion_and_spectral_interfaces():
    # SYNTHETIC_TEST_DATA: interface verification only.
    sampling_frequency = 100.0
    time = np.arange(0.0, 10.0, 1.0 / sampling_frequency)
    first = np.sin(2 * np.pi * 3.0 * time)
    second = np.sin(2 * np.pi * 3.0 * time + np.pi / 4)
    assert validate_synchronized_time(time) == pytest.approx(sampling_frequency)
    assert pressure_to_cp(np.array([100.0, 110.0]), 10.0, reference_pressure=90.0).tolist() == [1.0, 2.0]
    lags, correlation = normalized_cross_correlation(first, second, sampling_frequency)
    assert lags.shape == correlation.shape
    relationship = spectral_relationship(first, second, sampling_frequency, nperseg=500)
    index = int(np.argmin(np.abs(relationship["frequency_hz"] - 3.0)))
    assert relationship["coherence"][index] > 0.99
