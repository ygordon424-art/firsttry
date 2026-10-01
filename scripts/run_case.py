#!/usr/bin/env python3
"""Prepare or execute one traceable Fluent case."""

from __future__ import annotations

import argparse
import logging
import os
import time
from pathlib import Path
from typing import Any

try:
    from .common import find_case, load_yaml, metadata_template, project_root, write_json
except ImportError:  # Direct script execution.
    from common import find_case, load_yaml, metadata_template, project_root, write_json

LOGGER = logging.getLogger("run_case")


def contains_tbd(value: Any) -> bool:
    if isinstance(value, dict):
        return any(contains_tbd(item) for item in value.values())
    if isinstance(value, list):
        return any(contains_tbd(item) for item in value)
    return isinstance(value, str) and value.strip().upper() == "TBD"


def execute_case(
    case_file: Path,
    run_dir: Path,
    processor_count: int,
    iterations: int,
    metadata: dict[str, Any],
) -> None:
    """Launch real Fluent. This function never substitutes synthetic data."""
    try:
        import ansys.fluent.core as pyfluent
    except ImportError as exc:
        raise RuntimeError("PyFluent is not installed") from exc

    transcript_path = run_dir / "solver_transcript.txt"
    session = None
    started = time.perf_counter()
    try:
        session = pyfluent.launch_fluent(
            mode=pyfluent.FluentMode.SOLVER,
            precision=pyfluent.Precision.DOUBLE,
            processor_count=processor_count,
            case_file_name=case_file.resolve(),
            cwd=run_dir.resolve(),
            start_transcript=False,
            cleanup_on_exit=True,
        )
        session.transcript.start(file_name=str(transcript_path), write_to_stdout=False)
        metadata["solver_version"] = str(session.get_fluent_version())
        metadata["pyfluent_version"] = pyfluent.__version__
        metadata["cpu_core_count"] = processor_count
        session.settings.solution.initialization.hybrid_initialize()
        session.settings.solution.run_calculation.iterate(iter_count=iterations)
        metadata["actual_iterations"] = iterations
        metadata["result_status"] = "COMPLETED"
    except Exception:
        metadata["result_status"] = "FAILED"
        raise
    finally:
        metadata["wall_clock_runtime_seconds"] = round(time.perf_counter() - started, 3)
        if session is not None:
            try:
                session.transcript.stop()
            except Exception:
                LOGGER.warning("Could not stop transcript cleanly", exc_info=True)
            try:
                session.exit()
            except Exception:
                LOGGER.warning("Could not close Fluent cleanly", exc_info=True)
        write_json(run_dir / "metadata.json", metadata)


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="Prepare or run one configured CFD case.")
    parser.add_argument("case_id", help="Case ID from config/cases.yaml")
    parser.add_argument("--config", type=Path, default=root / "config/research_config.yaml")
    parser.add_argument("--cases", type=Path, default=root / "config/cases.yaml")
    parser.add_argument("--output-root", type=Path, default=root / "results/runs")
    parser.add_argument("--case-file", type=Path, help="Prepared Fluent .cas/.cas.h5 file")
    parser.add_argument("--processor-count", type=int, help="Override configured core count")
    parser.add_argument("--iterations", type=int, help="Override configured iteration count")
    parser.add_argument(
        "--execute", action="store_true", help="Launch Fluent; otherwise only prepare metadata"
    )
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    try:
        research = load_yaml(args.config)
        case = find_case(load_yaml(args.cases), args.case_id)
        run_id = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        run_dir = args.output_root / args.case_id / run_id
        metadata = metadata_template(case, research, status="PREPARED")
        metadata["run_id"] = run_id
        write_json(run_dir / "metadata.json", metadata)
        if not args.execute:
            LOGGER.info("Prepared %s at %s; Fluent was not launched", args.case_id, run_dir)
            return 0
        if not case.get("enabled", False):
            raise ValueError(f"{args.case_id} is disabled in config/cases.yaml; execution refused")
        if contains_tbd(research):
            raise ValueError("Research configuration still contains TBD values; execution refused")
        if not args.case_file or not args.case_file.is_file():
            raise FileNotFoundError("--case-file must identify a prepared Fluent case")
        solver = research.get("solver", {})
        processors = args.processor_count or solver.get("processor_count")
        iterations = args.iterations or solver.get("max_iterations")
        if not isinstance(processors, int) or processors < 1:
            raise ValueError("processor_count must be a positive integer")
        if not isinstance(iterations, int) or iterations < 1:
            raise ValueError("iterations must be a positive integer")
        execute_case(args.case_file, run_dir, processors, iterations, metadata)
        LOGGER.info("Completed %s", args.case_id)
        return 0
    except Exception:
        LOGGER.exception("Case failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
