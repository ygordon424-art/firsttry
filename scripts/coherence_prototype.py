#!/usr/bin/env python3
"""SYNTHETIC_TEST_DATA-only spatial coherence prototype.

This small demonstrator reuses the Stage 1 pressure-array pair interfaces.  It
is deliberately limited to eight synthetic channels and is not a source of
formal research evidence.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scripts.analyze_pressure_array import normalized_cross_correlation, spectral_relationship
except ModuleNotFoundError:  # Supports direct: python scripts/coherence_prototype.py
    from analyze_pressure_array import normalized_cross_correlation, spectral_relationship

DATA_CLASSIFICATION = "SYNTHETIC_TEST_DATA"
RESEARCH_EVIDENCE = False


def synthetic_coordinates(channel_count: int = 8) -> np.ndarray:
    """Return small, artificial x/y/z coordinates in metres."""
    if not 2 <= channel_count <= 12:
        raise ValueError("Synthetic prototype supports 2--12 channels only")
    x = np.arange(channel_count, dtype=float) * 0.25
    return np.column_stack((x, np.zeros(channel_count), 0.03 * (x % 2)))


def make_synthetic_signals(
    *, sampling_frequency_hz: float = 100.0, duration_seconds: float = 20.0, seed: int = 7
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """Create eight labelled signals: coherent, partial, lagged, and weak."""
    rng = np.random.default_rng(seed)
    time = np.arange(0.0, duration_seconds, 1.0 / sampling_frequency_hz)
    base = np.sin(2 * np.pi * 3.0 * time) + 0.35 * np.sin(2 * np.pi * 7.0 * time)
    independent = rng.normal(size=(4, time.size))
    signals = np.vstack(
        (
            base,
            base,  # fully coherent pair
            0.80 * base + 0.60 * independent[0],
            0.60 * base + 0.80 * independent[1],  # partially coherent pair
            np.sin(2 * np.pi * 3.0 * time + np.pi / 3) + 0.35 * np.sin(2 * np.pi * 7.0 * time + np.pi / 3),
            np.sin(2 * np.pi * 3.0 * time - np.pi / 4) + 0.35 * np.sin(2 * np.pi * 7.0 * time - np.pi / 4),
            independent[2],
            independent[3],  # weakly coherent pair
        )
    )
    names = ["coherent_0", "coherent_1", "partial_0", "partial_1", "lagged_plus", "lagged_minus", "weak_0", "weak_1"]
    return time, signals, names


def pair_distance(coordinates: np.ndarray, first: int, second: int) -> float:
    return float(np.linalg.norm(np.asarray(coordinates)[first] - np.asarray(coordinates)[second]))


def analyse_spatial_coherence(
    signals: np.ndarray, coordinates: np.ndarray, sampling_frequency_hz: float, *, nperseg: int = 512
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Return correlation, band-mean coherence, phase, and pair-distance tables."""
    values = np.asarray(signals, dtype=float)
    count = values.shape[0]
    if values.ndim != 2 or not 2 <= count <= 12:
        raise ValueError("signals must contain 2--12 channels")
    if np.asarray(coordinates).shape != (count, 3):
        raise ValueError("coordinates must have shape (channel_count, 3)")
    correlation = np.eye(count)
    coherence = np.eye(count)
    phase = np.zeros((count, count))
    pair_rows: list[dict[str, float | int]] = []
    for first in range(count):
        for second in range(first + 1, count):
            _, cross_correlation = normalized_cross_correlation(values[first], values[second], sampling_frequency_hz)
            spectral = spectral_relationship(values[first], values[second], sampling_frequency_hz, nperseg=nperseg)
            frequency = spectral["frequency_hz"]
            usable = (frequency >= 1.0) & (frequency <= 12.0)
            mean_coherence = float(np.mean(spectral["coherence"][usable]))
            dominant = int(np.argmax(np.abs(spectral["cross_spectrum_real"] + 1j * spectral["cross_spectrum_imag"])))
            phase_value = float(spectral["phase_radians"][dominant])
            peak_correlation = float(np.max(np.abs(cross_correlation)))
            correlation[first, second] = correlation[second, first] = peak_correlation
            coherence[first, second] = coherence[second, first] = mean_coherence
            phase[first, second] = phase_value
            phase[second, first] = -phase_value
            pair_rows.append({"channel_i": first, "channel_j": second, "distance_m": pair_distance(coordinates, first, second), "mean_coherence_1_to_12_hz": mean_coherence})
    labels = [f"channel_{index}" for index in range(count)]
    return (pd.DataFrame(correlation, index=labels, columns=labels), pd.DataFrame(coherence, index=labels, columns=labels), pd.DataFrame(phase, index=labels, columns=labels), pd.DataFrame(pair_rows))


def _safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved.name != "direction2_coherence" or resolved.parent.name != "prototype_results":
        raise ValueError("Outputs are restricted to prototype_results/direction2_coherence")
    return resolved


def write_outputs(output_dir: Path) -> Path:
    """Run the tiny synthetic prototype and write its explicitly labelled outputs."""
    output_dir = _safe_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    time, signals, names = make_synthetic_signals()
    coordinates = synthetic_coordinates(signals.shape[0])
    correlation, coherence, phase, distance_table = analyse_spatial_coherence(signals, coordinates, 100.0)
    correlation.to_csv(output_dir / "correlation_matrix.csv")
    coherence.to_csv(output_dir / "coherence_matrix.csv")
    phase.to_csv(output_dir / "phase_matrix.csv")
    distance_table.to_csv(output_dir / "distance_coherence.csv", index=False)
    (output_dir / "metadata.json").write_text(json.dumps({"data_classification": DATA_CLASSIFICATION, "research_evidence": RESEARCH_EVIDENCE, "channel_names": names, "coordinates_m": coordinates.tolist(), "sample_count": int(time.size)}, indent=2) + "\n", encoding="utf-8")
    fig, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(coherence.to_numpy(), vmin=0, vmax=1, cmap="viridis")
    axis.set(title="Synthetic magnitude-squared coherence", xlabel="channel", ylabel="channel")
    fig.colorbar(image, ax=axis, label="mean coherence (1--12 Hz)")
    fig.tight_layout(); fig.savefig(output_dir / "coherence_matrix.png", dpi=160); plt.close(fig)
    fig, axis = plt.subplots(figsize=(6, 4))
    axis.scatter(distance_table["distance_m"], distance_table["mean_coherence_1_to_12_hz"])
    axis.set(title="Synthetic coherence versus distance", xlabel="distance (m)", ylabel="mean coherence (1--12 Hz)", ylim=(-0.05, 1.05))
    fig.tight_layout(); fig.savefig(output_dir / "coherence_decay.png", dpi=160); plt.close(fig)
    fig, axis = plt.subplots(figsize=(6, 5))
    image = axis.imshow(phase.to_numpy(), vmin=-np.pi, vmax=np.pi, cmap="twilight")
    axis.set(title="Synthetic phase lag", xlabel="channel", ylabel="channel")
    fig.colorbar(image, ax=axis, label="phase (rad)")
    fig.tight_layout(); fig.savefig(output_dir / "phase_lag.png", dpi=160); plt.close(fig)
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="SYNTHETIC_TEST_DATA spatial-coherence prototype only.")
    parser.add_argument("--output-dir", type=Path, default=Path("prototype_results/direction2_coherence"))
    args = parser.parse_args()
    write_outputs(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
