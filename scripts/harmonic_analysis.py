#!/usr/bin/env python3
"""Identify spectral features near f0, 2f0, and 3f0 without physical interpretation."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np
from scipy import signal

try:
    from .experimental_data import identify_time_column, read_tabular_file, time_as_seconds
except ImportError:
    from experimental_data import identify_time_column, read_tabular_file, time_as_seconds

LOGGER = logging.getLogger("harmonic_analysis")


def one_sided_fft(time: np.ndarray, values: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    time = np.asarray(time, dtype=float)
    values = np.asarray(values, dtype=float)
    if time.ndim != 1 or values.ndim != 1 or time.size != values.size:
        raise ValueError("time and values must be equal-length one-dimensional arrays")
    if time.size < 8 or not np.isfinite(time).all() or not np.isfinite(values).all():
        raise ValueError("At least eight finite samples are required")
    dt = np.diff(time)
    if np.any(dt <= 0):
        raise ValueError("Time values must be strictly increasing")
    median_dt = float(np.median(dt))
    if np.max(np.abs(dt - median_dt)) / median_dt > 0.01:
        raise ValueError("FFT requires uniformly sampled data (interval deviation exceeds 1%)")
    detrended = signal.detrend(values, type="linear")
    spectrum = np.fft.rfft(detrended)
    amplitudes = 2.0 * np.abs(spectrum) / values.size
    if amplitudes.size:
        amplitudes[0] /= 2.0
        if values.size % 2 == 0:
            amplitudes[-1] /= 2.0
    frequencies = np.fft.rfftfreq(values.size, d=median_dt)
    return frequencies, amplitudes


def welch_psd(
    time: np.ndarray, values: np.ndarray, *, max_segment_samples: int = 1024
) -> tuple[np.ndarray, np.ndarray]:
    """Return a Welch PSD after applying the same sampling checks used by the FFT."""
    time = np.asarray(time, dtype=float)
    values = np.asarray(values, dtype=float)
    if time.ndim != 1 or values.ndim != 1 or time.size != values.size:
        raise ValueError("time and values must be equal-length one-dimensional arrays")
    if time.size < 8 or not np.isfinite(time).all() or not np.isfinite(values).all():
        raise ValueError("At least eight finite samples are required")
    intervals = np.diff(time)
    if np.any(intervals <= 0):
        raise ValueError("Time values must be strictly increasing")
    median_dt = float(np.median(intervals))
    if np.max(np.abs(intervals - median_dt)) / median_dt > 0.01:
        raise ValueError("Welch PSD requires uniformly sampled data (interval deviation exceeds 1%)")
    detrended = signal.detrend(values, type="linear")
    return signal.welch(
        detrended,
        fs=1.0 / median_dt,
        nperseg=min(max_segment_samples, values.size),
        detrend=False,
        scaling="density",
    )


def steady_state_window(
    time: np.ndarray,
    values: np.ndarray,
    *,
    reference_frequency_hz: float,
    discard_initial_fraction: float = 0.0,
    minimum_cycles: float = 1.0,
    integer_cycle_window: bool = True,
) -> tuple[np.ndarray, np.ndarray, dict[str, float | bool]]:
    """Select a post-transient analysis window and report its cycle coverage."""
    time = np.asarray(time, dtype=float)
    values = np.asarray(values, dtype=float)
    if time.ndim != 1 or values.ndim != 1 or time.size != values.size or time.size < 8:
        raise ValueError("time and values must be equal-length vectors with at least eight samples")
    if not 0 <= discard_initial_fraction < 1:
        raise ValueError("discard_initial_fraction must be in [0, 1)")
    if reference_frequency_hz <= 0 or minimum_cycles <= 0:
        raise ValueError("reference frequency and minimum cycles must be positive")
    if np.any(np.diff(time) <= 0):
        raise ValueError("Time values must be strictly increasing")
    requested_start = float(time[0] + discard_initial_fraction * (time[-1] - time[0]))
    available_duration = float(time[-1] - requested_start)
    complete_cycles = int(np.floor(available_duration * reference_frequency_hz + 1e-12))
    if integer_cycle_window:
        if complete_cycles < minimum_cycles:
            raise ValueError(
                f"Only {complete_cycles} complete cycles remain; minimum is {minimum_cycles:g}"
            )
        requested_start = float(time[-1] - complete_cycles / reference_frequency_hz)
    start_index = int(np.searchsorted(time, requested_start, side="left"))
    selected_time = time[start_index:]
    selected_values = values[start_index:]
    analyzed_duration = float(selected_time[-1] - selected_time[0])
    analyzed_cycles = analyzed_duration * reference_frequency_hz
    if analyzed_cycles + 1e-9 < minimum_cycles:
        raise ValueError(
            f"Analysis window contains {analyzed_cycles:.3f} cycles; minimum is {minimum_cycles:g}"
        )
    metadata: dict[str, float | bool] = {
        "discard_initial_fraction": float(discard_initial_fraction),
        "integer_cycle_window": bool(integer_cycle_window),
        "analysis_start_seconds": float(selected_time[0]),
        "analysis_end_seconds": float(selected_time[-1]),
        "analysis_duration_seconds": analyzed_duration,
        "analyzed_cycles": float(analyzed_cycles),
    }
    return selected_time, selected_values, metadata


def windowed_fft(
    time: np.ndarray, values: np.ndarray, *, window: str = "hann"
) -> tuple[np.ndarray, np.ndarray]:
    """Return a coherent-gain-corrected, one-sided windowed amplitude spectrum."""
    time = np.asarray(time, dtype=float)
    values = np.asarray(values, dtype=float)
    # Reuse the established validation, including the uniform-sampling check.
    one_sided_fft(time, values)
    detrended = signal.detrend(values, type="linear")
    if window.lower() == "hann":
        weights = signal.windows.hann(values.size, sym=False)
    elif window.lower() in {"boxcar", "rectangular", "none"}:
        weights = np.ones(values.size)
    else:
        raise ValueError(f"Unsupported spectral window: {window}")
    coherent_sum = float(np.sum(weights))
    if coherent_sum <= 0:
        raise ValueError("Spectral window has zero coherent gain")
    spectrum = np.fft.rfft(detrended * weights)
    amplitudes = 2.0 * np.abs(spectrum) / coherent_sum
    amplitudes[0] /= 2.0
    if values.size % 2 == 0:
        amplitudes[-1] /= 2.0
    dt = float(np.median(np.diff(time)))
    return np.fft.rfftfreq(values.size, d=dt), amplitudes


def robust_harmonic_analysis(
    time: np.ndarray,
    values: np.ndarray,
    *,
    fundamental_frequency_hz: float,
    frequency_reference: str,
    discard_initial_fraction: float = 0.0,
    spectral_window: str = "hann",
    frequency_bin_tolerance_hz: float | None = None,
    minimum_forcing_cycles: float = 1.0,
    integer_cycle_window: bool = True,
) -> dict[str, Any]:
    """Analyze harmonics with explicit frequency semantics and transient/leakage controls."""
    allowed_references = {"FORCING", "MODE", "RESPONSE_PEAK", "EXPERIMENT_DEFINED"}
    if frequency_reference not in allowed_references:
        raise ValueError(f"frequency_reference must be one of {sorted(allowed_references)}")
    selected_time, selected_values, window_metadata = steady_state_window(
        time,
        values,
        reference_frequency_hz=fundamental_frequency_hz,
        discard_initial_fraction=discard_initial_fraction,
        minimum_cycles=minimum_forcing_cycles,
        integer_cycle_window=integer_cycle_window,
    )
    frequencies, amplitudes = windowed_fft(
        selected_time, selected_values, window=spectral_window
    )
    harmonics = identify_harmonics(
        frequencies,
        amplitudes,
        fundamental_frequency=fundamental_frequency_hz,
        tolerance_hz=frequency_bin_tolerance_hz,
    )
    harmonics.update(
        {
            "frequency_reference": frequency_reference,
            "spectral_window": spectral_window,
            "analysis_window": window_metadata,
            "nearest_bin_error_hz": {
                name: details["offset_hz"] for name, details in harmonics["peaks"].items()
            },
        }
    )
    return {
        "time": selected_time,
        "values": selected_values,
        "frequency": frequencies,
        "amplitude": amplitudes,
        "harmonics": harmonics,
    }


def candidate_fundamental(frequencies: np.ndarray, amplitudes: np.ndarray) -> float:
    if frequencies.size < 2:
        raise ValueError("Spectrum does not contain a positive-frequency bin")
    positive = frequencies > 0
    if not positive.any() or np.max(amplitudes[positive]) <= 0:
        raise ValueError("No non-zero spectral peak is available")
    positive_indices = np.flatnonzero(positive)
    return float(frequencies[positive_indices[np.argmax(amplitudes[positive])]])


def identify_harmonics(
    frequencies: np.ndarray,
    amplitudes: np.ndarray,
    fundamental_frequency: float | None = None,
    *,
    tolerance_hz: float | None = None,
) -> dict[str, Any]:
    frequencies = np.asarray(frequencies, dtype=float)
    amplitudes = np.asarray(amplitudes, dtype=float)
    if frequencies.shape != amplitudes.shape or frequencies.ndim != 1:
        raise ValueError("frequencies and amplitudes must be equal-length vectors")
    if fundamental_frequency is None:
        f0 = candidate_fundamental(frequencies, amplitudes)
        source = "candidate_from_largest_fft_peak"
    else:
        f0 = float(fundamental_frequency)
        source = "user_specified"
    if f0 <= 0:
        raise ValueError("Fundamental frequency must be positive")
    resolution = float(np.median(np.diff(frequencies))) if frequencies.size > 1 else 0.0
    tolerance = tolerance_hz if tolerance_hz is not None else max(1.5 * resolution, 1e-12)
    peaks: dict[str, dict[str, float | bool]] = {}
    harmonic_amplitudes: list[float] = []
    for order in (1, 2, 3):
        target = order * f0
        index = int(np.argmin(np.abs(frequencies - target)))
        offset = abs(float(frequencies[index]) - target)
        found = offset <= tolerance
        amplitude = float(amplitudes[index]) if found else float("nan")
        harmonic_amplitudes.append(amplitude)
        peaks[f"{order}f0"] = {
            "target_frequency_hz": target,
            "detected_frequency_hz": float(frequencies[index]),
            "amplitude": amplitude,
            "within_tolerance": found,
            "offset_hz": offset,
        }
    fundamental_amplitude = harmonic_amplitudes[0]
    ratio_2 = (
        harmonic_amplitudes[1] / fundamental_amplitude
        if fundamental_amplitude > 0 and np.isfinite(harmonic_amplitudes[1])
        else float("nan")
    )
    ratio_3 = (
        harmonic_amplitudes[2] / fundamental_amplitude
        if fundamental_amplitude > 0 and np.isfinite(harmonic_amplitudes[2])
        else float("nan")
    )
    return {
        "fundamental_frequency_hz": f0,
        "fundamental_source": source,
        "frequency_resolution_hz": resolution,
        "tolerance_hz": tolerance,
        "peaks": peaks,
        "A_2f_over_A_f": float(ratio_2),
        "A_3f_over_A_f": float(ratio_3),
        "interpretation": "Signal features only; no nonlinear mechanism is inferred.",
    }


def analyze_signal(
    time: np.ndarray, values: np.ndarray, fundamental_frequency: float | None = None
) -> dict[str, Any]:
    frequencies, amplitudes = one_sided_fft(time, values)
    return identify_harmonics(frequencies, amplitudes, fundamental_frequency)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Report f0/2f0/3f0 spectral features.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--time-column")
    parser.add_argument("--signal-column", required=True)
    parser.add_argument("--fundamental-frequency", type=float)
    parser.add_argument("--output", type=Path, default=Path("harmonic_report.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        frame = read_tabular_file(args.input)
        time_column = identify_time_column(frame, args.time_column)
        if time_column is None:
            raise ValueError("No time column identified; specify --time-column")
        if args.signal_column not in frame.columns:
            raise KeyError(f"Signal column not found: {args.signal_column}")
        time = time_as_seconds(frame[time_column])
        values = np.asarray(frame[args.signal_column], dtype=float)
        report = analyze_signal(time, values, args.fundamental_frequency)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        LOGGER.info("Harmonic feature report written to %s", args.output)
        return 0
    except Exception:
        LOGGER.exception("Harmonic analysis failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
