from pathlib import Path

import numpy as np
import pytest

from scripts.analyze_displacement import SYNTHETIC_LABEL, analyze_arrays, write_outputs


def synthetic_signal():
    # SYNTHETIC_TEST_DATA: created in memory and held only in pytest's temporary directory.
    time = np.arange(0.0, 4.0, 1.0 / 200.0)
    values = np.sin(2 * np.pi * 5.0 * time) + 0.2 * np.sin(2 * np.pi * 10.0 * time)
    return time, values


def test_displacement_outputs_are_created_in_temporary_directory(tmp_path: Path):
    time, values = synthetic_signal()
    analysis = analyze_arrays(time, values, fundamental_frequency=5.0)
    output = tmp_path / "synthetic_outputs"
    write_outputs(
        analysis,
        output,
        classification=SYNTHETIC_LABEL,
        displacement_unit="arbitrary_unit",
    )
    assert analysis["harmonics"]["A_2f_over_A_f"] == pytest.approx(0.2, abs=0.01)
    for name in (
        "displacement_summary.csv",
        "detrended_signal.csv",
        "fft_spectrum.csv",
        "welch_psd.csv",
        "time_history.png",
        "psd.png",
        "fft.png",
    ):
        assert (output / name).is_file()


def test_synthetic_outputs_are_forbidden_under_results(tmp_path: Path):
    time, values = synthetic_signal()
    analysis = analyze_arrays(time, values, fundamental_frequency=5.0)
    with pytest.raises(ValueError, match="must not be written"):
        write_outputs(
            analysis,
            tmp_path / "results" / "bad_destination",
            classification=SYNTHETIC_LABEL,
            displacement_unit="arbitrary_unit",
        )
