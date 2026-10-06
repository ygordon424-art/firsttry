#!/usr/bin/env python3
"""Analyze a displacement time history and emit traceable signal statistics."""

from __future__ import annotations

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy import signal

try:
    from .experimental_data import identify_time_column, normalized_name, read_tabular_file, time_as_seconds
    from .harmonic_analysis import identify_harmonics, one_sided_fft
except ImportError:
    from experimental_data import identify_time_column, normalized_name, read_tabular_file, time_as_seconds
    from harmonic_analysis import identify_harmonics, one_sided_fft

LOGGER = logging.getLogger("analyze_displacement")
SYNTHETIC_LABEL = "SYNTHETIC_TEST_DATA"


def identify_displacement_column(frame: pd.DataFrame, requested: str | None) -> str:
    if requested:
        if requested not in frame.columns:
            raise KeyError(f"Displacement column not found: {requested}")
        return requested
    names = {"displacement", "disp", "deflection", "displacement_mm", "displacement_m"}
    candidates = [column for column in frame.columns if normalized_name(column) in names]
    if len(candidates) != 1:
        raise ValueError(
            f"Expected one recognizable displacement column, found {candidates}; specify --displacement-column"
        )
    return candidates[0]


def data_classification(frame: pd.DataFrame) -> str:
    if "data_classification" not in frame.columns:
        return "UNSPECIFIED_INPUT_DATA"
    labels = {str(value).strip() for value in frame["data_classification"].dropna().unique()}
    if len(labels) != 1:
        raise ValueError("data_classification must contain one consistent label")
    return labels.pop()


def is_results_path(path: Path) -> bool:
    return any(part.lower() == "results" for part in path.resolve().parts)


def analyze_arrays(
    time: np.ndarray,
    displacement: np.ndarray,
    *,
    fundamental_frequency: float | None = None,
) -> dict[str, Any]:
    time = np.asarray(time, dtype=float)
    displacement = np.asarray(displacement, dtype=float)
    frequencies, fft_amplitude = one_sided_fft(time, displacement)
    dt = float(np.median(np.diff(time)))
    sampling_frequency = 1.0 / dt
    detrended = signal.detrend(displacement, type="linear")
    nperseg = min(1024, displacement.size)
    psd_frequency, psd = signal.welch(
        detrended, fs=sampling_frequency, nperseg=nperseg, detrend=False, scaling="density"
    )
    peak_indices, _ = signal.find_peaks(fft_amplitude[1:])
    peak_indices = peak_indices + 1
    ranked = peak_indices[np.argsort(fft_amplitude[peak_indices])[::-1]][:5]
    dominant = [
        {"frequency_hz": float(frequencies[index]), "amplitude": float(fft_amplitude[index])}
        for index in ranked
    ]
    harmonics = identify_harmonics(
        frequencies, fft_amplitude, fundamental_frequency=fundamental_frequency
    )
    return {
        "statistics": {
            "mean_displacement": float(np.mean(displacement)),
            "rms_displacement": float(np.sqrt(np.mean(np.square(displacement)))),
            "standard_deviation": float(np.std(displacement, ddof=0)),
            "maximum": float(np.max(displacement)),
            "minimum": float(np.min(displacement)),
            "peak_to_peak": float(np.ptp(displacement)),
            "sampling_frequency_hz": sampling_frequency,
            "duration_seconds": float(time[-1] - time[0]),
            "sample_count": int(time.size),
        },
        "time": time,
        "detrended": detrended,
        "fft_frequency": frequencies,
        "fft_amplitude": fft_amplitude,
        "psd_frequency": psd_frequency,
        "psd": psd,
        "dominant_frequencies": dominant,
        "harmonics": harmonics,
    }


def write_outputs(
    analysis: dict[str, Any],
    output_dir: Path,
    *,
    classification: str,
    displacement_unit: str,
) -> None:
    if classification == SYNTHETIC_LABEL and is_results_path(output_dir):
        raise ValueError("SYNTHETIC_TEST_DATA must not be written under a results directory")
    output_dir.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(
        {"time_seconds": analysis["time"], "detrended_displacement": analysis["detrended"]}
    ).to_csv(output_dir / "detrended_signal.csv", index=False)
    pd.DataFrame(
        {"frequency_hz": analysis["fft_frequency"], "amplitude": analysis["fft_amplitude"]}
    ).to_csv(output_dir / "fft_spectrum.csv", index=False)
    pd.DataFrame(
        {"frequency_hz": analysis["psd_frequency"], "psd": analysis["psd"]}
    ).to_csv(output_dir / "welch_psd.csv", index=False)
    pd.DataFrame(analysis["dominant_frequencies"]).to_csv(
        output_dir / "dominant_frequencies.csv", index=False
    )
    statistic_units = {
        "mean_displacement": displacement_unit,
        "rms_displacement": displacement_unit,
        "standard_deviation": displacement_unit,
        "maximum": displacement_unit,
        "minimum": displacement_unit,
        "peak_to_peak": displacement_unit,
        "sampling_frequency_hz": "Hz",
        "duration_seconds": "s",
        "sample_count": "count",
    }
    summary_rows = [
        {"metric": "data_classification", "value": classification, "unit": ""},
        *[
            {"metric": key, "value": value, "unit": statistic_units[key]}
            for key, value in analysis["statistics"].items()
        ],
        {
            "metric": "fundamental_frequency_hz",
            "value": analysis["harmonics"]["fundamental_frequency_hz"],
            "unit": "Hz",
        },
        {"metric": "A_2f_over_A_f", "value": analysis["harmonics"]["A_2f_over_A_f"], "unit": ""},
        {"metric": "A_3f_over_A_f", "value": analysis["harmonics"]["A_3f_over_A_f"], "unit": ""},
    ]
    pd.DataFrame(summary_rows).to_csv(output_dir / "displacement_summary.csv", index=False)
    serializable = {
        "data_classification": classification,
        "statistics": analysis["statistics"],
        "dominant_frequencies": analysis["dominant_frequencies"],
        "harmonics": analysis["harmonics"],
        "interpretation_policy": "Signal features only; no physical mechanism or paper conclusion is inferred.",
    }
    (output_dir / "analysis_summary.json").write_text(
        json.dumps(serializable, indent=2) + "\n", encoding="utf-8"
    )

    fig, ax = plt.subplots(figsize=(9, 4.5))
    ax.plot(analysis["time"], analysis["detrended"], linewidth=0.8)
    ax.set(xlabel="Time (s)", ylabel=f"Detrended displacement ({displacement_unit})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "time_history.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.semilogy(analysis["psd_frequency"], np.maximum(analysis["psd"], np.finfo(float).tiny))
    ax.set(xlabel="Frequency (Hz)", ylabel=f"PSD ({displacement_unit}²/Hz)")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "psd.png", dpi=180)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(8, 4.5))
    ax.plot(analysis["fft_frequency"], analysis["fft_amplitude"], linewidth=0.9)
    ax.set(xlabel="Frequency (Hz)", ylabel=f"Amplitude ({displacement_unit})")
    ax.grid(True, alpha=0.3)
    fig.tight_layout()
    fig.savefig(output_dir / "fft.png", dpi=180)
    plt.close(fig)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze a uniformly sampled displacement CSV.")
    parser.add_argument("input", type=Path)
    parser.add_argument("--time-column")
    parser.add_argument("--displacement-column")
    parser.add_argument("--fundamental-frequency", type=float)
    parser.add_argument("--displacement-unit", default="UNSPECIFIED")
    parser.add_argument("--output-dir", type=Path, default=Path("displacement_analysis"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        frame = read_tabular_file(args.input)
        time_column = identify_time_column(frame, args.time_column)
        if time_column is None:
            raise ValueError("No time column identified; specify --time-column")
        displacement_column = identify_displacement_column(frame, args.displacement_column)
        time = time_as_seconds(frame[time_column])
        displacement = pd.to_numeric(frame[displacement_column], errors="raise").to_numpy(float)
        analysis = analyze_arrays(
            time, displacement, fundamental_frequency=args.fundamental_frequency
        )
        write_outputs(
            analysis,
            args.output_dir,
            classification=data_classification(frame),
            displacement_unit=args.displacement_unit,
        )
        LOGGER.info("Displacement outputs written to %s", args.output_dir)
        return 0
    except Exception:
        LOGGER.exception("Displacement analysis failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
