from pathlib import Path

import pandas as pd
import pytest

from scripts.audit_experimental_data import audit_frame
from scripts.experimental_data import read_tabular_file


def test_audit_reports_sampling_and_quality_flags(tmp_path: Path):
    source = tmp_path / "SYNTHETIC_TEST_DATA.csv"
    frame = pd.DataFrame(
        {
            "time": [0.0, 0.01, 0.02, 0.031, 0.031],
            "displacement": [0.0, 1.0, None, 1.0, 100.0],
            "data_classification": ["SYNTHETIC_TEST_DATA"] * 5,
        }
    )
    frame.to_csv(source, index=False)
    loaded = read_tabular_file(source)
    report = audit_frame(loaded, source=source)
    assert report["rows"] == 5
    assert report["time_column"] == "time"
    assert report["missing_values"]["displacement"] == 1
    assert report["sampling"]["duplicate_timestamps"] == 1
    assert report["sampling"]["nonuniform_sampling"] is True
    assert report["source_modified"] is False


def test_unknown_format_is_rejected(tmp_path: Path):
    source = tmp_path / "SYNTHETIC_TEST_DATA.bin"
    source.write_bytes(b"not a recognized table")
    with pytest.raises(ValueError, match="Unsupported format"):
        read_tabular_file(source)


def test_excel_reader_when_engine_available(tmp_path: Path):
    pytest.importorskip("openpyxl")
    source = tmp_path / "SYNTHETIC_TEST_DATA.xlsx"
    pd.DataFrame({"time": [0.0, 0.1], "value": [1.0, 2.0]}).to_excel(source, index=False)
    loaded = read_tabular_file(source)
    assert list(loaded.columns) == ["time", "value"]
