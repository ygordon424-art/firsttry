#!/usr/bin/env python3
"""Preparatory interfaces for synchronized multi-point pressure signals."""

from __future__ import annotations

import argparse
import json
import logging
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import signal

try:
    from .experimental_data import identify_numeric_columns, identify_time_column, read_tabular_file, time_as_seconds
except ImportError:
    from experimental_data import identify_numeric_columns, identify_time_column, read_tabular_file, time_as_seconds

LOGGER = logging.getLogger("analyze_pressure_array")


@dataclass(frozen=True)
class PressureArrayMetadata:
    time_column: str
    pressure_channels: tuple[str, ...]
    sampling_frequency_hz: float
    pressure_unit: str
    dynamic_pressure: float | None = None
    reference_pressure: float | None = None


def validate_synchronized_time(time: np.ndarray, tolerance: float = 0.01) -> float:
    time = np.asarray(time, dtype=float)
    if time.ndim != 1 or time.size < 8 or not np.isfinite(time).all():
        raise ValueError("At least eight finite time samples are required")
    intervals = np.diff(time)
    if np.any(intervals <= 0):
        raise ValueError("Time values must be strictly increasing and unique")
    median_interval = float(np.median(intervals))
    if np.max(np.abs(intervals - median_interval)) / median_interval > tolerance:
        raise ValueError("Pressure-array spectral analysis requires synchronized uniform sampling")
    return 1.0 / median_interval


def pressure_to_cp(
    pressure: np.ndarray,
    dynamic_pressure: float,
    *,
    reference_pressure: float = 0.0,
) -> np.ndarray:
    if not np.isfinite(dynamic_pressure) or dynamic_pressure <= 0:
        raise ValueError("dynamic_pressure must be a positive finite value")
    return (np.asarray(pressure, dtype=float) - reference_pressure) / dynamic_pressure


def normalized_cross_correlation(
    first: np.ndarray, second: np.ndarray, sampling_frequency_hz: float
) -> tuple[np.ndarray, np.ndarray]:
    first = signal.detrend(np.asarray(first, dtype=float))
    second = signal.detrend(np.asarray(second, dtype=float))
    if first.shape != second.shape or first.ndim != 1:
        raise ValueError("Pressure channels must be equal-length vectors")
    if sampling_frequency_hz <= 0:
        raise ValueError("sampling_frequency_hz must be positive")
    denominator = np.linalg.norm(first) * np.linalg.norm(second)
    if denominator == 0:
        raise ValueError("Cross-correlation is undefined for a constant channel")
    correlation = signal.correlate(second, first, mode="full") / denominator
    lags = signal.correlation_lags(second.size, first.size, mode="full") / sampling_frequency_hz
    return lags, correlation


def spectral_relationship(
    first: np.ndarray,
    second: np.ndarray,
    sampling_frequency_hz: float,
    *,
    nperseg: int | None = None,
) -> dict[str, np.ndarray]:
    first = np.asarray(first, dtype=float)
    second = np.asarray(second, dtype=float)
    if first.shape != second.shape or first.ndim != 1:
        raise ValueError("Pressure channels must be equal-length vectors")
    segment = min(nperseg or 1024, first.size)
    frequencies, cross_spectrum = signal.csd(
        first, second, fs=sampling_frequency_hz, nperseg=segment
    )
    coherence_frequency, coherence = signal.coherence(
        first, second, fs=sampling_frequency_hz, nperseg=segment
    )
    if not np.allclose(frequencies, coherence_frequency):
        raise RuntimeError("Cross-spectrum and coherence frequency grids differ")
    phase_radians = np.angle(cross_spectrum)
    phase_lag_seconds = np.full_like(frequencies, np.nan, dtype=float)
    positive = frequencies > 0
    phase_lag_seconds[positive] = phase_radians[positive] / (2 * np.pi * frequencies[positive])
    return {
        "frequency_hz": frequencies,
        "cross_spectrum_real": np.real(cross_spectrum),
        "cross_spectrum_imag": np.imag(cross_spectrum),
        "coherence": coherence,
        "phase_radians": phase_radians,
        "phase_lag_seconds": phase_lag_seconds,
    }


def load_pressure_array(
    path: Path,
    *,
    time_column: str | None = None,
    channels: list[str] | None = None,
    pressure_unit: str = "UNSPECIFIED",
) -> tuple[np.ndarray, pd.DataFrame, PressureArrayMetadata]:
    frame = read_tabular_file(path)
    detected_time = identify_time_column(frame, time_column)
    if detected_time is None:
        raise ValueError("No time column identified; specify --time-column")
    selected = channels or [
        column for column in identify_numeric_columns(frame) if column != detected_time
    ]
    if not selected:
        raise ValueError("No pressure channels selected or identified")
    missing = [column for column in selected if column not in frame.columns]
    if missing:
        raise KeyError(f"Pressure channels not found: {missing}")
    pressure = frame[selected].apply(pd.to_numeric, errors="raise")
    if pressure.isna().any().any():
        raise ValueError("Pressure channels contain missing values")
    time = time_as_seconds(frame[detected_time])
    sampling_frequency = validate_synchronized_time(time)
    metadata = PressureArrayMetadata(
        time_column=detected_time,
        pressure_channels=tuple(selected),
        sampling_frequency_hz=sampling_frequency,
        pressure_unit=pressure_unit,
    )
    return time, pressure, metadata


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare and validate multi-channel pressure inputs.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--time-column")
    parser.add_argument("--channel", action="append", dest="channels")
    parser.add_argument("--pressure-unit", default="UNSPECIFIED")
    parser.add_argument("--dynamic-pressure", type=float)
    parser.add_argument("--reference-pressure", type=float, default=0.0)
    parser.add_argument("--reference-channel")
    parser.add_argument("--comparison-channel")
    parser.add_argument("--output-dir", type=Path, default=Path("pressure_interface_output"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        time, pressure, metadata = load_pressure_array(
            args.input,
            time_column=args.time_column,
            channels=args.channels,
            pressure_unit=args.pressure_unit,
        )
        args.output_dir.mkdir(parents=True, exist_ok=True)
        payload: dict[str, Any] = {
            "status": "PREPARATORY_INTERFACE_ONLY",
            "source": str(args.input.resolve()),
            "sample_count": int(time.size),
            "metadata": asdict(metadata),
            "available_operations": [
                "Cp conversion",
                "cross-correlation",
                "cross-spectrum",
                "coherence",
                "phase lag",
            ],
            "interpretation_policy": "No formal paper conclusion is produced by this interface.",
        }
        if args.dynamic_pressure is not None:
            cp = pd.DataFrame(
                {
                    column: pressure_to_cp(
                        pressure[column].to_numpy(),
                        args.dynamic_pressure,
                        reference_pressure=args.reference_pressure,
                    )
                    for column in pressure.columns
                }
            )
            cp.insert(0, "time_seconds", time)
            cp.to_csv(args.output_dir / "cp_channels.csv", index=False)
            payload["cp_exported"] = True
        if bool(args.reference_channel) != bool(args.comparison_channel):
            raise ValueError("Specify both --reference-channel and --comparison-channel")
        if args.reference_channel and args.comparison_channel:
            for channel in (args.reference_channel, args.comparison_channel):
                if channel not in pressure.columns:
                    raise KeyError(f"Selected channel not found: {channel}")
            first = pressure[args.reference_channel].to_numpy()
            second = pressure[args.comparison_channel].to_numpy()
            lags, correlation = normalized_cross_correlation(
                first, second, metadata.sampling_frequency_hz
            )
            pd.DataFrame({"lag_seconds": lags, "correlation": correlation}).to_csv(
                args.output_dir / "cross_correlation.csv", index=False
            )
            spectral = spectral_relationship(first, second, metadata.sampling_frequency_hz)
            pd.DataFrame(spectral).to_csv(args.output_dir / "spectral_relationship.csv", index=False)
            payload["channel_pair_exported"] = [
                args.reference_channel,
                args.comparison_channel,
            ]
        (args.output_dir / "pressure_interface_summary.json").write_text(
            json.dumps(payload, indent=2) + "\n", encoding="utf-8"
        )
        LOGGER.info("Pressure interface outputs written to %s", args.output_dir)
        return 0
    except Exception:
        LOGGER.exception("Pressure-array preparation failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
