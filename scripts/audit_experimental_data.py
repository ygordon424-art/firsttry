#!/usr/bin/env python3
"""Audit an experimental data table without modifying the source."""

from __future__ import annotations

import argparse
import hashlib
import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

try:
    from .experimental_data import (
        identify_numeric_columns,
        identify_time_column,
        iqr_outlier_counts,
        read_tabular_file,
        sampling_metrics,
    )
except ImportError:
    from experimental_data import (
        identify_numeric_columns,
        identify_time_column,
        iqr_outlier_counts,
        read_tabular_file,
        sampling_metrics,
    )

LOGGER = logging.getLogger("audit_experimental_data")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_frame(
    frame: pd.DataFrame,
    *,
    source: Path,
    time_column: str | None = None,
    interval_tolerance: float = 0.01,
) -> dict[str, Any]:
    numeric_columns = identify_numeric_columns(frame)
    detected_time = identify_time_column(frame, time_column)
    missing = {column: int(frame[column].isna().sum()) for column in frame.columns}
    infinite = {
        column: int(np.isinf(pd.to_numeric(frame[column], errors="coerce")).sum())
        for column in numeric_columns
    }
    report: dict[str, Any] = {
        "report_type": "EXPERIMENTAL_DATA_AUDIT",
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source_file": str(source.resolve()),
        "source_sha256": sha256_file(source),
        "source_size_bytes": source.stat().st_size,
        "source_modified": False,
        "rows": int(frame.shape[0]),
        "columns": int(frame.shape[1]),
        "column_names": list(frame.columns),
        "column_dtypes": {column: str(frame[column].dtype) for column in frame.columns},
        "numeric_columns": numeric_columns,
        "missing_values": missing,
        "total_missing_values": int(sum(missing.values())),
        "infinite_values": infinite,
        "duplicate_rows": int(frame.duplicated().sum()),
        "iqr_outlier_counts": iqr_outlier_counts(frame, numeric_columns),
        "time_column": detected_time,
        "sampling": None,
        "warnings": [],
    }
    if detected_time is None:
        report["warnings"].append("No unambiguous time column was identified.")
    else:
        try:
            report["sampling"] = sampling_metrics(
                frame[detected_time], tolerance=interval_tolerance
            )
        except ValueError as exc:
            report["warnings"].append(f"Time analysis failed: {exc}")
    if report["total_missing_values"]:
        report["warnings"].append("Missing values are present.")
    if any(infinite.values()):
        report["warnings"].append("Infinite numeric values are present.")
    if any(report["iqr_outlier_counts"].values()):
        report["warnings"].append(
            "Potential outliers were flagged by the 1.5×IQR rule; this is a signal-quality flag, not a physical conclusion."
        )
    return report


def render_markdown(report: dict[str, Any]) -> str:
    sampling = report["sampling"]
    sampling_lines = (
        [
            f"- Estimated sampling frequency: {sampling['sampling_frequency_hz']:.9g} Hz",
            f"- Median interval: {sampling['median_interval_seconds']:.9g} s",
            f"- Duration: {sampling['duration_seconds']:.9g} s",
            f"- Duplicate timestamps: {sampling['duplicate_timestamps']}",
            f"- Nonpositive intervals: {sampling['nonpositive_intervals']}",
            f"- Nonuniform sampling: {'YES' if sampling['nonuniform_sampling'] else 'NO'}",
        ]
        if sampling
        else ["- Sampling metrics unavailable."]
    )
    missing_lines = [f"- `{column}`: {count}" for column, count in report["missing_values"].items()]
    outlier_lines = [
        f"- `{column}`: {count}" for column, count in report["iqr_outlier_counts"].items()
    ] or ["- No numeric columns identified."]
    warning_lines = [f"- {warning}" for warning in report["warnings"]] or ["- None."]
    return "\n".join(
        [
            "# Experimental data audit",
            "",
            f"- Source: `{report['source_file']}`",
            f"- Source SHA-256: `{report['source_sha256']}`",
            f"- Source modified: {str(report['source_modified']).upper()}",
            f"- Rows: {report['rows']}",
            f"- Columns: {report['columns']}",
            f"- Time column: {report['time_column'] or 'NOT IDENTIFIED'}",
            f"- Numeric columns: {', '.join(report['numeric_columns']) or 'None'}",
            "",
            "## Missing values",
            "",
            *missing_lines,
            "",
            "## Sampling",
            "",
            *sampling_lines,
            "",
            "## Potential outliers (1.5×IQR)",
            "",
            *outlier_lines,
            "",
            "## Warnings",
            "",
            *warning_lines,
            "",
            "Potential outliers and sampling warnings are data-quality indicators only; they are not experimental or physical conclusions.",
            "",
        ]
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only audit of experimental tabular data.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--sheet", help="Excel sheet name or zero-based index")
    parser.add_argument("--time-column")
    parser.add_argument("--interval-tolerance", type=float, default=0.01)
    parser.add_argument("--output-dir", type=Path, default=Path("audit_output"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        if not 0 <= args.interval_tolerance < 1:
            raise ValueError("--interval-tolerance must be in [0, 1)")
        sheet: str | int | None = args.sheet
        if isinstance(sheet, str) and sheet.isdigit():
            sheet = int(sheet)
        frame = read_tabular_file(args.input, sheet=sheet)
        report = audit_frame(
            frame,
            source=args.input,
            time_column=args.time_column,
            interval_tolerance=args.interval_tolerance,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        (args.output_dir / "audit_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        (args.output_dir / "audit_report.md").write_text(
            render_markdown(report), encoding="utf-8"
        )
        LOGGER.info("Audit reports written to %s", args.output_dir)
        return 0
    except Exception:
        LOGGER.exception("Experimental data audit failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
