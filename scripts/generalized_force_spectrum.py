#!/usr/bin/env python3
"""Synthetic-only generalized-force harmonic controls.

DEMONSTRATION ONLY.  These weights are synthetic and are neither a PV model
nor a substitute for tributary areas, mode shapes, or measured mapping.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

try:
    from scripts.pressure_harmonic_audit import harmonic_audit
except ModuleNotFoundError:  # Supports direct script execution.
    from pressure_harmonic_audit import harmonic_audit

DATA_CLASSIFICATION = "STAGE2_AERODYNAMIC_INPUT_PROTOTYPE"
RESEARCH_EVIDENCE = False
FREQUENCY_REFERENCE = "SYNTHETIC_RESPONSE_FREQUENCY"


def generalized_force(pressures: np.ndarray, weights: np.ndarray) -> np.ndarray:
    values, mapping = np.asarray(pressures, dtype=float), np.asarray(weights, dtype=float)
    if values.ndim != 2 or values.shape[1] != mapping.size or not 1 <= mapping.size <= 12:
        raise ValueError("pressure channels and weights must match and contain 1--12 channels")
    return values @ mapping


def synthetic_pressure_controls(*, sampling_frequency_hz: float = 100.0, duration_seconds: float = 20.0) -> tuple[np.ndarray, dict[str, np.ndarray], np.ndarray]:
    """Return P0--P4 small controls; P3 cancels and P4 reinforces 2f in Q."""
    time = np.arange(0.0, duration_seconds, 1.0 / sampling_frequency_hz)
    fundamental = np.sin(2 * np.pi * 3.0 * time)
    harmonic = np.sin(2 * np.pi * 6.0 * time)
    count = 8
    phase = np.linspace(0.0, np.pi / 3, count)
    partial = np.vstack([np.sin(2 * np.pi * 3.0 * time + offset) for offset in phase]).T
    coherent = np.tile(fundamental[:, None], (1, count))
    weak = coherent + 0.08 * np.tile(harmonic[:, None], (1, count))
    cancellation = coherent + 0.25 * harmonic[:, None] * np.array([1, -1] * 4)[None, :]
    reinforcement = coherent + 0.25 * np.tile(harmonic[:, None], (1, count))
    return time, {"P0": coherent, "P1": partial, "P2": weak, "P3": cancellation, "P4": reinforcement}, np.ones(count)


def generalized_force_harmonics(time: np.ndarray, pressures: np.ndarray, weights: np.ndarray, *, frequency_value_hz: float, frequency_reference: str) -> tuple[np.ndarray, pd.DataFrame, pd.DataFrame, dict[str, object]]:
    """Map pressures to Q(t) then reuse the channel harmonic audit for Q."""
    force = generalized_force(pressures, weights)
    summary, spectrum, metadata = harmonic_audit(time, force[:, None], ["Q"], frequency_value_hz=frequency_value_hz, frequency_reference=frequency_reference)
    return force, summary, spectrum, metadata


def _safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved.name != "stage2_pressure_support" or resolved.parent.name != "prototype_results":
        raise ValueError("Outputs are restricted to prototype_results/stage2_pressure_support")
    return resolved


def write_synthetic_controls(output_dir: Path) -> Path:
    """Write all requested small synthetic controls and explanatory metadata."""
    output_dir = _safe_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    time, controls, weights = synthetic_pressure_controls()
    channel_ids = [f"synthetic_{index + 1}" for index in range(weights.size)]
    channel_rows, force_rows, spectrum_rows, summary_rows = [], [], [], []
    for case_id, pressures in controls.items():
        local, local_spectrum, metadata = harmonic_audit(time, pressures, channel_ids, frequency_value_hz=3.0, frequency_reference=FREQUENCY_REFERENCE, start_time_seconds=1.0)
        force, force_summary, force_spectrum, _ = generalized_force_harmonics(time, pressures, weights, frequency_value_hz=3.0, frequency_reference=FREQUENCY_REFERENCE)
        local.insert(0, "case_id", case_id)
        channel_rows.append(local)
        force_rows.append(pd.DataFrame({"case_id": case_id, "time_seconds": time, "generalized_force_Q": force}))
        force_spectrum.insert(0, "case_id", case_id)
        spectrum_rows.append(force_spectrum.rename(columns={"psd": "PSD_Q", "fft_amplitude": "FFT_amplitude_Q"}))
        summary_rows.append({"case_id": case_id, "mean_local_A_2f": float(local["A_2f"].mean()), "generalized_A_f": float(force_summary.loc[0, "A_f"]), "generalized_A_2f": float(force_summary.loc[0, "A_2f"]), "generalized_A_3f": float(force_summary.loc[0, "A_3f"]), "generalized_A_2f_over_A_f": float(force_summary.loc[0, "A_2f_over_A_f"]), "frequency_reference": FREQUENCY_REFERENCE, "frequency_resolution_hz": metadata["frequency_resolution_hz"]})
    channels = pd.concat(channel_rows, ignore_index=True)
    forces = pd.concat(force_rows, ignore_index=True)
    spectra = pd.concat(spectrum_rows, ignore_index=True)
    summary = pd.DataFrame(summary_rows)
    channels.to_csv(output_dir / "channel_harmonics.csv", index=False)
    forces.to_csv(output_dir / "generalized_force_time_history.csv", index=False)
    spectra.to_csv(output_dir / "generalized_force_spectrum.csv", index=False)
    summary.to_csv(output_dir / "harmonic_summary.csv", index=False)
    (output_dir / "metadata.json").write_text(json.dumps({"data_classification": DATA_CLASSIFICATION, "research_evidence": RESEARCH_EVIDENCE, "frequency_reference": FREQUENCY_REFERENCE, "weights": "SYNTHETIC", "channel_count": int(weights.size), "scope": "DEMONSTRATION ONLY; NOT A PV AERODYNAMIC CONCLUSION"}, indent=2) + "\n", encoding="utf-8")
    fig, axis = plt.subplots(figsize=(6, 4))
    for channel in channel_ids[:2]:
        subset = local_spectrum[local_spectrum["channel_id"] == channel]
        axis.plot(subset["frequency_hz"], subset["psd"], label=channel)
    axis.set(xlim=(0, 12), title="Synthetic channel PSD examples", xlabel="frequency (Hz)", ylabel="PSD")
    axis.legend(); fig.tight_layout(); fig.savefig(output_dir / "channel_psd_examples.png", dpi=160); plt.close(fig)
    fig, axis = plt.subplots(figsize=(6, 4))
    for case_id in ("P3", "P4"):
        subset = spectra[spectra["case_id"] == case_id]
        axis.plot(subset["frequency_hz"], subset["PSD_Q"], label=case_id)
    axis.set(xlim=(0, 12), title="Generalized-force PSD", xlabel="frequency (Hz)", ylabel="PSD_Q")
    axis.legend(); fig.tight_layout(); fig.savefig(output_dir / "generalized_force_psd.png", dpi=160); plt.close(fig)
    fig, axis = plt.subplots(figsize=(6, 4))
    axis.bar(summary["case_id"], summary["mean_local_A_2f"], label="mean local A_2f")
    axis.plot(summary["case_id"], summary["generalized_A_2f"], "o-", color="black", label="generalized A_2f")
    axis.set(title="Local versus generalized 2f", ylabel="amplitude")
    axis.legend(); fig.tight_layout(); fig.savefig(output_dir / "local_vs_generalized_2f.png", dpi=160); plt.close(fig)
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="Synthetic generalized-force harmonic controls only.")
    parser.add_argument("--output-dir", type=Path, default=Path("prototype_results/stage2_pressure_support"))
    args = parser.parse_args()
    write_synthetic_controls(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
