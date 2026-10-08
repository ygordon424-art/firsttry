#!/usr/bin/env python3
"""Harmonic audit for synchronized pressure channels.

This preparatory utility requires an explicit frequency reference.  It does
not infer whether that reference is structural, modal, or experimental.
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import signal

try:
    from scripts.analyze_pressure_array import load_pressure_array, validate_synchronized_time
except ModuleNotFoundError:  # Supports direct script execution.
    from analyze_pressure_array import load_pressure_array, validate_synchronized_time


def _window_values(name: str, size: int) -> np.ndarray:
    if name != "hann":
        raise ValueError("Only the documented hann window is supported")
    return signal.windows.hann(size, sym=False)


def _analysis_slice(time: np.ndarray, start_time_seconds: float, duration_seconds: float | None) -> np.ndarray:
    if start_time_seconds < time[0]:
        raise ValueError("start_time_seconds cannot precede the first sample")
    mask = time >= start_time_seconds
    if duration_seconds is not None:
        if duration_seconds <= 0:
            raise ValueError("duration_seconds must be positive")
        mask &= time < start_time_seconds + duration_seconds
    if int(mask.sum()) < 8:
        raise ValueError("Analysis window must contain at least eight samples")
    return mask


def harmonic_audit(
    time: np.ndarray,
    channels: np.ndarray,
    channel_ids: list[str],
    *,
    frequency_value_hz: float,
    frequency_reference: str,
    start_time_seconds: float = 0.0,
    duration_seconds: float | None = None,
    window: str = "hann",
) -> tuple[pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Return channel harmonic metrics, PSD/FFT spectra, and window metadata."""
    time = np.asarray(time, dtype=float)
    values = np.asarray(channels, dtype=float)
    if values.ndim != 2 or values.shape[0] != time.size or values.shape[1] != len(channel_ids):
        raise ValueError("channels must have shape (time_samples, channel_ids)")
    if not 0 < values.shape[1] <= 12 or not np.isfinite(values).all():
        raise ValueError("Use 1--12 finite synchronized pressure channels")
    if frequency_value_hz <= 0 or not frequency_reference.strip():
        raise ValueError("frequency_value_hz and frequency_reference are required")
    sampling_frequency = validate_synchronized_time(time)
    selected = _analysis_slice(time, start_time_seconds, duration_seconds)
    selected_time = time[selected]
    selected_values = values[selected]
    count = selected_time.size
    frequency_resolution = sampling_frequency / count
    weights = _window_values(window, count)
    coherent_gain = float(np.sum(weights))
    frequencies = np.fft.rfftfreq(count, d=1.0 / sampling_frequency)
    rows: list[dict[str, float | str]] = []
    spectrum_rows: list[pd.DataFrame] = []
    targets = {"A_f": frequency_value_hz, "A_2f": 2 * frequency_value_hz, "A_3f": 3 * frequency_value_hz}
    for index, channel_id in enumerate(channel_ids):
        demeaned = signal.detrend(selected_values[:, index])
        fft = np.fft.rfft(demeaned * weights)
        amplitude = 2.0 * np.abs(fft) / coherent_gain
        amplitude[0] /= 2.0
        _, psd = signal.periodogram(demeaned, fs=sampling_frequency, window=weights, scaling="density")
        metric: dict[str, float | str] = {"channel_id": channel_id}
        for label, target in targets.items():
            bin_index = int(np.argmin(np.abs(frequencies - target)))
            metric[f"{label}_frequency_hz"] = float(frequencies[bin_index])
            metric[label] = float(amplitude[bin_index])
        metric["A_2f_over_A_f"] = float(metric["A_2f"] / metric["A_f"]) if metric["A_f"] else np.nan
        metric["A_3f_over_A_f"] = float(metric["A_3f"] / metric["A_f"]) if metric["A_f"] else np.nan
        metric["frequency_reference"] = frequency_reference
        metric["frequency_resolution_hz"] = frequency_resolution
        rows.append(metric)
        spectrum_rows.append(pd.DataFrame({"channel_id": channel_id, "frequency_hz": frequencies, "psd": psd, "fft_amplitude": amplitude}))
    metadata: dict[str, object] = {
        "frequency_value_hz": frequency_value_hz,
        "frequency_reference": frequency_reference,
        "sampling_frequency_hz": sampling_frequency,
        "frequency_resolution_hz": frequency_resolution,
        "analysis_window": window,
        "analysis_start_time_seconds": float(selected_time[0]),
        "analysis_duration_seconds": float(selected_time[-1] - selected_time[0] + 1.0 / sampling_frequency),
        "sample_count": int(count),
    }
    return pd.DataFrame(rows), pd.concat(spectrum_rows, ignore_index=True), metadata


def main() -> int:
    parser = argparse.ArgumentParser(description="Preparatory pressure harmonic audit; physical meaning is user-supplied.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--frequency-value-hz", type=float, required=True)
    parser.add_argument("--frequency-reference", required=True)
    parser.add_argument("--time-column")
    parser.add_argument("--channel", action="append", dest="channels")
    parser.add_argument("--pressure-unit", default="UNSPECIFIED")
    parser.add_argument("--start-time-seconds", type=float, default=0.0)
    parser.add_argument("--duration-seconds", type=float)
    parser.add_argument("--output-dir", type=Path, default=Path("pressure_harmonic_audit_output"))
    args = parser.parse_args()
    time, pressure, _ = load_pressure_array(args.input, time_column=args.time_column, channels=args.channels, pressure_unit=args.pressure_unit)
    metrics, spectra, metadata = harmonic_audit(time, pressure.to_numpy(), list(pressure.columns), frequency_value_hz=args.frequency_value_hz, frequency_reference=args.frequency_reference, start_time_seconds=args.start_time_seconds, duration_seconds=args.duration_seconds)
    args.output_dir.mkdir(parents=True, exist_ok=True)
    metrics.to_csv(args.output_dir / "channel_harmonics.csv", index=False)
    spectra.to_csv(args.output_dir / "channel_spectra.csv", index=False)
    pd.Series(metadata).to_json(args.output_dir / "analysis_metadata.json", indent=2)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
