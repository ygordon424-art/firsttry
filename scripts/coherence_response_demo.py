#!/usr/bin/env python3
"""DEMONSTRATION ONLY: coherence to one-modal-DOF response chain.

NOT A PV STRUCTURAL MODEL.  This tests the future computational connection
between pressure spatial coherence, generalised force, and modal response.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd

DATA_CLASSIFICATION = "SYNTHETIC_TEST_DATA"
RESEARCH_EVIDENCE = False


def modal_response_demo() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    """Calculate a one-DOF oscillator response for two artificial coherence cases."""
    frequency = np.linspace(0.05, 20.0, 800)
    single_point_psd = 1.0 / (1.0 + (frequency / 4.0) ** 2)  # same in both cases
    weights = np.array([1.0, 0.8, 0.7, 0.6])
    modal_frequency_hz, damping_ratio = 4.0, 0.04
    omega = 2 * np.pi * frequency
    omega_n = 2 * np.pi * modal_frequency_hz
    transfer_squared = 1.0 / ((omega_n**2 - omega**2) ** 2 + (2 * damping_ratio * omega_n * omega) ** 2)
    cases = {"fully_coherent": 1.0, "partially_coherent": 0.25}
    force_output: dict[str, np.ndarray] = {"frequency_hz": frequency, "single_point_psd": single_point_psd}
    response_output: dict[str, np.ndarray] = {"frequency_hz": frequency}
    rms_rows = []
    for name, off_diagonal_coherence in cases.items():
        coherence_matrix = np.full((weights.size, weights.size), off_diagonal_coherence)
        np.fill_diagonal(coherence_matrix, 1.0)
        force_psd = single_point_psd * float(weights @ coherence_matrix @ weights)
        response_psd = force_psd * transfer_squared
        force_output[f"generalized_force_psd_{name}"] = force_psd
        response_output[f"response_psd_{name}"] = response_psd
        rms_rows.append({"case": name, "response_rms": float(np.sqrt(np.trapezoid(response_psd, frequency)),), "data_classification": DATA_CLASSIFICATION, "research_evidence": RESEARCH_EVIDENCE})
    return pd.DataFrame(force_output), pd.DataFrame(response_output), pd.DataFrame(rms_rows)


def _safe_output_dir(output_dir: Path) -> Path:
    resolved = output_dir.resolve()
    if resolved.name != "direction2_coherence" or resolved.parent.name != "prototype_results":
        raise ValueError("Outputs are restricted to prototype_results/direction2_coherence")
    return resolved


def write_outputs(output_dir: Path) -> Path:
    output_dir = _safe_output_dir(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    force, response, rms = modal_response_demo()
    force.to_csv(output_dir / "generalized_force_psd.csv", index=False)
    response.to_csv(output_dir / "response_psd.csv", index=False)
    rms.to_csv(output_dir / "response_rms_comparison.csv", index=False)
    (output_dir / "response_demo_metadata.json").write_text(json.dumps({"data_classification": DATA_CLASSIFICATION, "research_evidence": RESEARCH_EVIDENCE, "scope": "DEMONSTRATION ONLY; NOT A PV STRUCTURAL MODEL", "modal_dof": 1}, indent=2) + "\n", encoding="utf-8")
    return output_dir


def main() -> int:
    parser = argparse.ArgumentParser(description="DEMONSTRATION ONLY; NOT A PV STRUCTURAL MODEL.")
    parser.add_argument("--output-dir", type=Path, default=Path("prototype_results/direction2_coherence"))
    args = parser.parse_args()
    write_outputs(args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
