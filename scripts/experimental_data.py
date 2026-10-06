"""Shared, read-only loaders and signal-column helpers for experimental data."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SUPPORTED_EXTENSIONS = {".csv", ".txt", ".dat", ".xls", ".xlsx", ".xlsm"}
TIME_NAMES = {
    "t",
    "time",
    "times",
    "time_s",
    "time_sec",
    "time_seconds",
    "timestamp",
    "elapsed_time",
}


def normalized_name(value: object) -> str:
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def read_tabular_file(path: Path, *, sheet: str | int | None = None) -> pd.DataFrame:
    """Read a supported table without writing to or modifying the source file."""
    path = path.expanduser().resolve()
    if not path.is_file():
        raise FileNotFoundError(f"Input file not found: {path}")
    suffix = path.suffix.lower()
    if suffix not in SUPPORTED_EXTENSIONS:
        raise ValueError(
            f"Unsupported format {suffix or '<none>'}. Supported: "
            + ", ".join(sorted(SUPPORTED_EXTENSIONS))
        )
    try:
        if suffix in {".xls", ".xlsx", ".xlsm"}:
            selected_sheet = 0 if sheet is None else sheet
            frame = pd.read_excel(path, sheet_name=selected_sheet)
        else:
            frame = pd.read_csv(path, sep=None, engine="python", comment="#")
            if frame.shape[1] == 1 and suffix in {".txt", ".dat"}:
                whitespace_frame = pd.read_csv(path, sep=r"\s+", engine="python", comment="#")
                if whitespace_frame.shape[1] > 1:
                    frame = whitespace_frame
    except ImportError as exc:
        raise RuntimeError(
            "Excel support requires an engine such as openpyxl; install requirements-stage1.txt"
        ) from exc
    except (pd.errors.ParserError, UnicodeDecodeError, ValueError) as exc:
        raise ValueError(f"Could not parse {path.name} as a supported tabular format: {exc}") from exc
    if frame.empty:
        raise ValueError(f"Input table is empty: {path}")
    if frame.columns.empty or any(str(column).startswith("Unnamed:") for column in frame.columns):
        raise ValueError("Column names are missing or ambiguous; provide a file with an explicit header")
    frame.columns = [str(column).strip() for column in frame.columns]
    if len(set(frame.columns)) != len(frame.columns):
        raise ValueError("Duplicate column names are not supported")
    return frame


def identify_numeric_columns(frame: pd.DataFrame) -> list[str]:
    """Return columns whose non-missing values are entirely numeric."""
    columns: list[str] = []
    for column in frame.columns:
        series = frame[column]
        nonmissing = series.dropna()
        if nonmissing.empty:
            continue
        converted = pd.to_numeric(nonmissing, errors="coerce")
        if converted.notna().all():
            columns.append(column)
    return columns


def identify_time_column(frame: pd.DataFrame, requested: str | None = None) -> str | None:
    if requested:
        if requested not in frame.columns:
            raise KeyError(f"Requested time column not found: {requested}")
        return requested
    exact = [column for column in frame.columns if normalized_name(column) in TIME_NAMES]
    if len(exact) == 1:
        return exact[0]
    if len(exact) > 1:
        raise ValueError(f"Multiple possible time columns found: {exact}; specify --time-column")
    candidates = [
        column
        for column in frame.columns
        if normalized_name(column).startswith("time_") or normalized_name(column).endswith("_time")
    ]
    if len(candidates) == 1:
        return candidates[0]
    if len(candidates) > 1:
        raise ValueError(f"Multiple possible time columns found: {candidates}; specify --time-column")
    return None


def time_as_seconds(series: pd.Series) -> np.ndarray:
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.notna().sum() == series.notna().sum() and numeric.notna().any():
        return numeric.to_numpy(dtype=float)
    parsed = pd.to_datetime(series, errors="coerce", utc=True)
    if parsed.notna().sum() != series.notna().sum() or not parsed.notna().any():
        raise ValueError("Time column is neither numeric nor consistently parseable as timestamps")
    origin = parsed.dropna().iloc[0]
    return (parsed - origin).dt.total_seconds().to_numpy(dtype=float)


def sampling_metrics(series: pd.Series, tolerance: float = 0.01) -> dict[str, Any]:
    times = time_as_seconds(series)
    finite = times[np.isfinite(times)]
    if finite.size < 2:
        raise ValueError("At least two finite time values are required")
    differences = np.diff(finite)
    positive = differences[differences > 0]
    duplicate_count = int(pd.Series(finite).duplicated().sum())
    if positive.size == 0:
        raise ValueError("No positive time interval was found")
    median_dt = float(np.median(positive))
    relative = np.abs(positive - median_dt) / median_dt
    return {
        "sampling_frequency_hz": 1.0 / median_dt,
        "median_interval_seconds": median_dt,
        "duration_seconds": float(np.max(finite) - np.min(finite)),
        "duplicate_timestamps": duplicate_count,
        "nonpositive_intervals": int(np.count_nonzero(differences <= 0)),
        "nonuniform_sampling": bool(np.any(relative > tolerance)),
        "interval_tolerance_fraction": tolerance,
        "max_relative_interval_deviation": float(np.max(relative)),
    }


def iqr_outlier_counts(frame: pd.DataFrame, numeric_columns: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for column in numeric_columns:
        values = pd.to_numeric(frame[column], errors="coerce")
        finite = values[np.isfinite(values)]
        if finite.empty:
            counts[column] = 0
            continue
        q1, q3 = np.percentile(finite, [25, 75])
        iqr = q3 - q1
        if iqr == 0:
            counts[column] = 0
        else:
            lower, upper = q1 - 1.5 * iqr, q3 + 1.5 * iqr
            counts[column] = int(((finite < lower) | (finite > upper)).sum())
    return counts
