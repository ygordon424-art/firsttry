#!/usr/bin/env python3
"""Normalize solver-exported per-row PV loads and calculate interference metrics."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

import pandas as pd

LOGGER = logging.getLogger("postprocess")
REQUIRED = [
    "case_id",
    "wind_angle",
    "spacing_ratio",
    "row_id",
    "Cd",
    "Cl",
    "Cm",
    "Fx",
    "Fy",
    "Fz",
    "Mx",
    "My",
    "Mz",
]
OPTIONAL = ["Cp", "net_pressure", "Mbase"]


def validate_frame(frame: pd.DataFrame, source: Path) -> None:
    missing = [column for column in REQUIRED if column not in frame.columns]
    if missing:
        raise ValueError(f"{source} is missing columns: {', '.join(missing)}")
    if frame.empty:
        raise ValueError(f"{source} contains no rows")
    numeric = [column for column in REQUIRED if column not in ("case_id", "row_id")]
    for column in numeric:
        if column == "spacing_ratio":
            continue
        converted = pd.to_numeric(frame[column], errors="coerce")
        if converted.isna().any():
            raise ValueError(f"{source}: {column} contains non-numeric values")


def add_interference_metrics(frame: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    keys = ["wind_angle", "row_id"]
    baseline_columns = keys + ["Cm"] + (["Mbase"] if "Mbase" in baseline.columns else [])
    reference = baseline[baseline_columns].rename(
        columns={"Cm": "Cm_baseline", "Mbase": "Mbase_baseline"}
    )
    merged = frame.merge(reference, on=keys, how="left", validate="many_to_one")
    if merged["Cm_baseline"].isna().any():
        raise ValueError("Baseline does not cover every wind_angle/row_id pair")
    if (merged["Cm_baseline"] == 0).any():
        raise ZeroDivisionError("Cannot compute IF_M where baseline Cm is zero")
    merged["IF_M"] = merged["Cm"] / merged["Cm_baseline"]
    if "Mbase" in merged.columns and "Mbase_baseline" in merged.columns:
        if (merged["Mbase_baseline"] == 0).any():
            raise ZeroDivisionError("Cannot compute K_M where baseline Mbase is zero")
        merged["K_M"] = merged["Mbase"] / merged["Mbase_baseline"]
    return merged


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Normalize real CFD row-load exports.")
    parser.add_argument("input", type=Path, help="Solver-exported row-load CSV")
    parser.add_argument("--baseline", type=Path, help="Baseline CSV for IF_M and K_M")
    parser.add_argument("--output", type=Path, default=Path("forces_by_row.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        frame = pd.read_csv(args.input)
        validate_frame(frame, args.input)
        if args.baseline:
            baseline = pd.read_csv(args.baseline)
            validate_frame(baseline, args.baseline)
            frame = add_interference_metrics(frame, baseline)
        ordered = REQUIRED + [c for c in OPTIONAL if c in frame.columns]
        ordered += [c for c in ("IF_M", "K_M") if c in frame.columns]
        frame[ordered].to_csv(args.output, index=False)
        LOGGER.info("Wrote %d rows to %s", len(frame), args.output)
        return 0
    except Exception:
        LOGGER.exception("Postprocessing failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

