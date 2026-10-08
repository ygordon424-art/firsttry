#!/usr/bin/env python3
"""Future Abaqus ODB extraction gate; never fabricates missing FE results."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def extraction_schema() -> dict[str, object]:
    return {
        "data_classification": "GENERIC_FE_PROTOTYPE",
        "required_time_history_columns": ["time", "z", "theta"],
        "optional_time_history_columns": ["cable_axial_force", "reaction_force"],
        "modal_output_columns": ["mode", "frequency_hz"],
        "harmonic_analysis_compatible": True,
        "status": "INTERFACE_ONLY_NO_VALUES_GENERATED",
    }


def require_abaqus_odb_interface(odb_path: Path) -> None:
    if not odb_path.is_file():
        raise FileNotFoundError(f"ODB file does not exist: {odb_path}")
    try:
        __import__("odbAccess")
    except ImportError as exc:
        raise RuntimeError("Abaqus odbAccess is unavailable; no output was extracted") from exc


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate access for future generic ODB extraction.")
    parser.add_argument("--odb", type=Path)
    parser.add_argument("--schema-output", type=Path, default=Path("fe_output_schema.json"))
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    args.schema_output.write_text(json.dumps(extraction_schema(), indent=2) + "\n", encoding="utf-8")
    if args.odb is None:
        return 0
    try:
        require_abaqus_odb_interface(args.odb)
        return 0
    except Exception as exc:
        print(f"ODB extraction not run: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
