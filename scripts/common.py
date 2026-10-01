"""Shared configuration, case, and provenance helpers."""

from __future__ import annotations

import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import yaml

CASE_ID_RE = re.compile(r"^(BASE_A\d{3}|OBS_S\d{3}_A\d{3}|GCI_(COARSE|MEDIUM|FINE))$")


def project_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"Configuration file not found: {path}")
    with path.open("r", encoding="utf-8") as stream:
        data = yaml.safe_load(stream)
    if not isinstance(data, dict):
        raise ValueError(f"Expected a YAML mapping in {path}")
    return data


def find_case(cases_config: dict[str, Any], case_id: str) -> dict[str, Any]:
    if not CASE_ID_RE.fullmatch(case_id):
        raise ValueError(f"Invalid case_id naming convention: {case_id}")
    candidates = list(cases_config.get("cases", []))
    candidates.extend(cases_config.get("reserved_cases", {}).get("gci", []))
    for case in candidates:
        if case.get("case_id") == case_id:
            return {**cases_config.get("case_defaults", {}), **case}
    raise KeyError(f"Unknown case_id: {case_id}")


def git_commit_sha(root: Path | None = None) -> str:
    repository = (root or project_root()).resolve()
    try:
        result = subprocess.run(
            ["git", "-c", f"safe.directory={repository.as_posix()}", "rev-parse", "HEAD"],
            cwd=repository,
            check=True,
            capture_output=True,
            text=True,
        )
        return result.stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        return "UNCOMMITTED"


def utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def metadata_template(
    case: dict[str, Any],
    research_config: dict[str, Any],
    *,
    status: str,
) -> dict[str, Any]:
    """Create a complete metadata record without inventing unavailable values."""
    solver = research_config.get("solver", {})
    return {
        "case_id": case["case_id"],
        "git_commit_sha": git_commit_sha(),
        "date_utc": utc_timestamp(),
        "solver_version": None,
        "pyfluent_version": None,
        "mesh_cells": None,
        "mesh_quality": None,
        "physical_parameters": {
            key: research_config.get(key, {})
            for key in ("building", "rooftop_obstacle", "pv", "flow")
        },
        "boundary_conditions": None,
        "turbulence_model": solver.get("turbulence_model"),
        "convergence_criteria": solver.get("convergence_criteria"),
        "actual_iterations": None,
        "wall_clock_runtime_seconds": None,
        "cpu_core_count": None,
        "result_status": status,
        "case_definition": case,
    }


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
