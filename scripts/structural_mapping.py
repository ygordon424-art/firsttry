#!/usr/bin/env python3
"""Map real panel loads to a deliberately simple, explicitly configured support model."""

from __future__ import annotations

import argparse
import logging
import math
from pathlib import Path
from typing import Any

import pandas as pd
import yaml

LOGGER = logging.getLogger("structural_mapping")
ALLOWED_FORCE_AXES = {"Fx", "Fy", "Fz"}
ALLOWED_MOMENT_AXES = {"Mx", "My", "Mz"}


def load_model(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as stream:
        model = yaml.safe_load(stream)
    required = {"horizontal_force_axis", "overturning_moment_axis", "load_height", "column_spacing", "brace_angle_degrees"}
    if not isinstance(model, dict) or not required.issubset(model):
        raise ValueError(f"Model must define: {', '.join(sorted(required))}")
    if model["horizontal_force_axis"] not in ALLOWED_FORCE_AXES:
        raise ValueError("horizontal_force_axis must be Fx, Fy, or Fz")
    if model["overturning_moment_axis"] not in ALLOWED_MOMENT_AXES:
        raise ValueError("overturning_moment_axis must be Mx, My, or Mz")
    for key in ("load_height", "column_spacing", "brace_angle_degrees"):
        if isinstance(model[key], str) and model[key].upper() == "TBD":
            raise ValueError(f"{key} is TBD; structural mapping refused")
        model[key] = float(model[key])
    if model["load_height"] < 0 or model["column_spacing"] <= 0:
        raise ValueError("load_height must be nonnegative and column_spacing positive")
    angle = model["brace_angle_degrees"]
    if not 0 < angle < 90:
        raise ValueError("brace_angle_degrees must be between 0 and 90")
    return model


def map_loads(frame: pd.DataFrame, model: dict[str, Any]) -> pd.DataFrame:
    force_axis = model["horizontal_force_axis"]
    moment_axis = model["overturning_moment_axis"]
    missing = [name for name in (force_axis, moment_axis) if name not in frame.columns]
    if missing:
        raise ValueError(f"Input loads missing columns: {', '.join(missing)}")
    output = frame.copy()
    horizontal = pd.to_numeric(output[force_axis], errors="raise")
    moment = pd.to_numeric(output[moment_axis], errors="raise")
    output["M_base"] = moment + horizontal * model["load_height"]
    output["T_anchor"] = output["M_base"].abs() / model["column_spacing"]
    output["N_brace"] = horizontal.abs() / math.cos(math.radians(model["brace_angle_degrees"]))
    return output


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Map CFD loads to a configured simplified support model.")
    parser.add_argument("loads", type=Path, help="forces_by_row.csv")
    parser.add_argument("--model", type=Path, required=True, help="YAML support geometry and axis mapping")
    parser.add_argument("--output", type=Path, default=Path("structural_demands.csv"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        loads = pd.read_csv(args.loads)
        output = map_loads(loads, load_model(args.model))
        output.to_csv(args.output, index=False)
        LOGGER.info("Wrote %d mapped rows to %s", len(output), args.output)
        return 0
    except Exception:
        LOGGER.exception("Structural mapping failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

