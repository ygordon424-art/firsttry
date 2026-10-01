#!/usr/bin/env python3
"""Compute three-grid Grid Convergence Index (GCI) from real scalar results."""

from __future__ import annotations

import argparse
import json
import logging
import math
from pathlib import Path

LOGGER = logging.getLogger("compute_gci")


def apparent_order(phi1: float, phi2: float, phi3: float, r21: float, r32: float) -> float:
    """Solve the generalized apparent-order equation by fixed-point iteration."""
    e21, e32 = phi2 - phi1, phi3 - phi2
    if e21 == 0 or e32 == 0:
        raise ValueError("Successive solution differences must be non-zero")
    s = 1.0 if e32 / e21 > 0 else -1.0
    p = abs(math.log(abs(e32 / e21)) / math.log(r21))
    for _ in range(100):
        numerator = r21**p - s
        denominator = r32**p - s
        if numerator <= 0 or denominator <= 0:
            raise ValueError("Cannot determine apparent order for supplied values")
        updated = abs(math.log(abs(e32 / e21)) + math.log(numerator / denominator)) / math.log(r21)
        if abs(updated - p) < 1e-10:
            return updated
        p = updated
    raise RuntimeError("Apparent-order iteration did not converge")


def compute(phi1: float, phi2: float, phi3: float, h1: float, h2: float, h3: float) -> dict[str, float]:
    if not (0 < h1 < h2 < h3):
        raise ValueError("Require 0 < h_fine < h_medium < h_coarse")
    r21, r32 = h2 / h1, h3 / h2
    if r21 <= 1 or r32 <= 1:
        raise ValueError("Refinement ratios must exceed one")
    p = apparent_order(phi1, phi2, phi3, r21, r32)
    extrapolated = (r21**p * phi1 - phi2) / (r21**p - 1)
    denom = max(abs(phi1), 1e-30)
    approximate_error = abs((phi1 - phi2) / denom)
    gci_fine = 1.25 * approximate_error / (r21**p - 1)
    return {
        "apparent_order": p,
        "refinement_ratio_21": r21,
        "refinement_ratio_32": r32,
        "extrapolated_value": extrapolated,
        "gci_fine_fraction": gci_fine,
        "gci_fine_percent": 100 * gci_fine,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compute a three-grid GCI for one scalar quantity.")
    parser.add_argument("--fine", type=float, required=True, help="Fine-grid solution phi1")
    parser.add_argument("--medium", type=float, required=True, help="Medium-grid solution phi2")
    parser.add_argument("--coarse", type=float, required=True, help="Coarse-grid solution phi3")
    parser.add_argument("--h-fine", type=float, required=True)
    parser.add_argument("--h-medium", type=float, required=True)
    parser.add_argument("--h-coarse", type=float, required=True)
    parser.add_argument("--output", type=Path, default=Path("gci_result.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        result = compute(args.fine, args.medium, args.coarse, args.h_fine, args.h_medium, args.h_coarse)
        args.output.write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
        LOGGER.info("GCI result written to %s", args.output)
        return 0
    except Exception:
        LOGGER.exception("GCI calculation failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

