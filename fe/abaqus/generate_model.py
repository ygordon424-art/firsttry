#!/usr/bin/env python3
"""Generate a deterministic, generic bilateral cable–panel Abaqus input deck."""

from __future__ import annotations

import argparse
import json
import os
import shutil
from pathlib import Path
from typing import Any

import yaml

CLASSIFICATION = "GENERIC_FE_PROTOTYPE"
PLACEHOLDER_STATUS = "GENERIC_PLACEHOLDER_PARAMETER"


def detect_abaqus_environment() -> dict[str, Any]:
    candidates = ["abaqus", "abq2025", "abq2024", "abq2023", "abq2022"]
    executable = next((shutil.which(name) for name in candidates if shutil.which(name)), None)
    license_variable_present = any(
        bool(os.environ.get(name)) for name in ("ABAQUSLM_LICENSE_FILE", "LM_LICENSE_FILE")
    )
    return {
        "ABAQUS_AVAILABLE": "YES" if executable else "NO",
        "ABAQUS_EXECUTABLE": executable,
        "PYTHON_INTERFACE": "UNKNOWN" if not executable else "AVAILABLE_THROUGH_ABAQUS_COMMAND",
        "LICENSE_ENVIRONMENT_VARIABLE_PRESENT": license_variable_present,
        "LICENSE_AVAILABLE": "UNKNOWN",
        "SMOKE_TEST": "NOT RUN" if not executable else "REQUIRED BEFORE USE",
        "sensitive_values_reported": False,
    }


def load_and_validate_config(path: Path) -> dict[str, Any]:
    config = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(config, dict):
        raise ValueError("FE configuration must be a YAML mapping")
    validate_config(config)
    return config


def validate_config(config: dict[str, Any]) -> None:
    """Validate an already loaded generic FE configuration."""
    if config.get("data_classification") != CLASSIFICATION:
        raise ValueError(f"data_classification must be {CLASSIFICATION}")
    if config.get("parameter_status") != PLACEHOLDER_STATUS:
        raise ValueError(f"parameter_status must be {PLACEHOLDER_STATUS}")
    required_positive = {
        "geometry.span": config["geometry"]["span"],
        "geometry.panel_width": config["geometry"]["panel_width"],
        "geometry.cable_spacing": config["geometry"]["cable_spacing"],
        "panel.mass": config["panel"]["mass"],
        "panel.rotational_inertia": config["panel"]["rotational_inertia"],
        "cable.area": config["cable"]["area"],
        "cable.youngs_modulus": config["cable"]["youngs_modulus"],
    }
    for name, value in required_positive.items():
        if float(value) <= 0:
            raise ValueError(f"{name} must be positive")
    if float(config["cable"]["pretension"]) < 0:
        raise ValueError("cable.pretension cannot be negative")
    if not -1 <= float(config["load"]["lateral_location_ratio"]) <= 1:
        raise ValueError("load.lateral_location_ratio must be within [-1, 1]")
    if config["support_conditions"]["type"] != "PINNED_TRANSLATIONS":
        raise ValueError("Only PINNED_TRANSLATIONS is implemented in the generic archetype")
    if bool(config["switches"]["tension_only"]):
        raise ValueError(
            "TENSION_ONLY_FE is NOT YET VERIFIED; bilateral T3D2 generation is the only supported baseline"
        )
    if float(config["analysis"]["maximum_runtime_seconds"]) > 300:
        raise ValueError("Current FE runtime limit cannot exceed 300 seconds")


def render_input_deck(config: dict[str, Any]) -> str:
    """Render a tiny two-cable/rigid-panel model without invoking Abaqus."""
    span = float(config["geometry"]["span"])
    spacing = float(config["geometry"]["cable_spacing"])
    area = float(config["cable"]["area"])
    modulus = float(config["cable"]["youngs_modulus"])
    pretension = float(config["cable"]["pretension"])
    mass = float(config["panel"]["mass"])
    inertia = float(config["panel"]["rotational_inertia"])
    force = float(config["load"]["vertical_force"])
    offset = float(config["load"]["lateral_location_ratio"]) * float(
        config["geometry"]["panel_width"]
    ) / 2.0
    moment = force * offset
    nlgeom = "YES" if bool(config["switches"]["nlgeom"]) else "NO"
    lines = [
        "** GENERIC_FE_PROTOTYPE — GENERIC_PLACEHOLDER_PARAMETER",
        "** Minimal bilateral T3D2 cable / rigid panel archetype",
        "** TENSION_ONLY_FE = NOT YET VERIFIED",
        "*HEADING",
        "Stage 2 generic cable-PV structural prototype",
        "*NODE",
        f"1, 0., {-spacing / 2.0:.12g}, 0.",
        f"2, {span / 2.0:.12g}, {-spacing / 2.0:.12g}, 0.",
        f"3, {span:.12g}, {-spacing / 2.0:.12g}, 0.",
        f"4, 0., {spacing / 2.0:.12g}, 0.",
        f"5, {span / 2.0:.12g}, {spacing / 2.0:.12g}, 0.",
        f"6, {span:.12g}, {spacing / 2.0:.12g}, 0.",
        f"7, {span / 2.0:.12g}, 0., 0.",
        "*ELEMENT, TYPE=T3D2, ELSET=CABLES",
        "1, 1, 2",
        "2, 2, 3",
        "3, 4, 5",
        "4, 5, 6",
        "*ELEMENT, TYPE=MASS, ELSET=PANEL_MASS",
        "5, 7",
        "*ELEMENT, TYPE=ROTARYI, ELSET=PANEL_INERTIA",
        "6, 7",
        "*NSET, NSET=SUPPORTS",
        "1, 3, 4, 6",
        "*NSET, NSET=PANEL_ATTACHMENT",
        "2, 5",
        "*NSET, NSET=PANEL_REFERENCE",
        "7",
        "*MATERIAL, NAME=GENERIC_CABLE",
        "*ELASTIC",
        f"{modulus:.12g}, 0.3",
        "*SOLID SECTION, ELSET=CABLES, MATERIAL=GENERIC_CABLE",
        f"{area:.12g}",
        "*MASS, ELSET=PANEL_MASS",
        f"{mass:.12g}",
        "*ROTARY INERTIA, ELSET=PANEL_INERTIA",
        f"{inertia:.12g}, {inertia:.12g}, {inertia:.12g}",
        "*RIGID BODY, REF NODE=7, PIN NSET=PANEL_ATTACHMENT",
        "*BOUNDARY",
        "SUPPORTS, 1, 3, 0.",
        "PANEL_REFERENCE, 1, 2, 0.",
        "PANEL_REFERENCE, 5, 6, 0.",
    ]
    if not bool(config["switches"]["bending_torsion_freedom"]):
        lines.append("PANEL_REFERENCE, 4, 4, 0.")
    if bool(config["switches"]["pretension"]):
        initial_stress = pretension / area
        lines.extend(
            [
                "** Pretension represented as generic initial axial stress; review before research use",
                "*INITIAL CONDITIONS, TYPE=STRESS",
                f"CABLES, {initial_stress:.12g}",
            ]
        )
    lines.extend(
        [
            f"*STEP, NAME=GENERIC_STATIC, NLGEOM={nlgeom}",
            "*STATIC",
            "0.1, 1.0, 1e-06, 0.1",
            "*CLOAD",
            f"7, 3, {force:.12g}",
            f"7, 4, {moment:.12g}",
            "*OUTPUT, FIELD",
            "*NODE OUTPUT",
            "U, UR, RF, RM",
            "*ELEMENT OUTPUT, ELSET=CABLES",
            "S, E",
            "*OUTPUT, HISTORY",
            "*NODE OUTPUT, NSET=PANEL_REFERENCE",
            "U, UR, RF, RM",
            "*END STEP",
            "*STEP, NAME=GENERIC_MODES, PERTURBATION",
            "*FREQUENCY, EIGENSOLVER=LANCZOS",
            f"{int(config['analysis']['eigenmodes'])},",
            "*OUTPUT, FIELD",
            "*NODE OUTPUT",
            "U",
            "*END STEP",
            "",
        ]
    )
    return "\n".join(lines)


def output_plan(config: dict[str, Any]) -> dict[str, Any]:
    return {
        "data_classification": CLASSIFICATION,
        "harmonic_compatibility": "time,z,theta columns are required for harmonic_analysis.py",
        "planned_outputs": {
            "u_z": "PANEL_REFERENCE U3 history",
            "torsional_response": "PANEL_REFERENCE UR1 when available",
            "cable_axial_force": "derive from verified cable stress/section data; do not invent",
            "modal_frequencies": "GENERIC_MODES eigenfrequencies",
            "reaction_forces": "SUPPORTS RF history/field output",
            "internal_force_histories": "verified element output in future dynamic steps",
        },
        "requested_switches": config["switches"],
        "TENSION_ONLY_FE": "NOT YET VERIFIED",
    }


def generate(config_path: Path, output_dir: Path) -> tuple[Path, Path, Path]:
    config = load_and_validate_config(config_path)
    output_dir.mkdir(parents=True, exist_ok=True)
    deck_path = output_dir / "generic_cable_pv.inp"
    manifest_path = output_dir / "generic_cable_pv_manifest.json"
    environment_path = output_dir / "abaqus_environment.json"
    deck_path.write_text(render_input_deck(config), encoding="utf-8", newline="\n")
    manifest = {
        "data_classification": CLASSIFICATION,
        "parameter_status": PLACEHOLDER_STATUS,
        "configuration": config,
        "output_plan": output_plan(config),
        "result_status": "INPUT_GENERATED_NOT_SOLVED",
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    environment_path.write_text(
        json.dumps(detect_abaqus_environment(), indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return deck_path, manifest_path, environment_path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate the generic Stage 2B Abaqus input framework.")
    parser.add_argument("--config", type=Path, default=Path("config/fe_generic.yaml"))
    parser.add_argument("--output-dir", type=Path, default=Path("fe/abaqus/generated"))
    parser.add_argument("--check-environment", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        if args.check_environment:
            print(json.dumps(detect_abaqus_environment(), indent=2))
            return 0
        paths = generate(args.config, args.output_dir)
        print("\n".join(str(path) for path in paths))
        return 0
    except Exception as exc:
        print(f"FE generator failed: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
