#!/usr/bin/env python3
"""Run a tiny, real Fluent smoke test from a user-supplied, traceable case file."""

from __future__ import annotations

import argparse
import csv
import json
import logging
import re
import time
from pathlib import Path

LOGGER = logging.getLogger("fluent_smoke_test")
RESIDUAL_LINE = re.compile(r"^\s*(\d+)\s+((?:[-+0-9.eE]+\s+){1,12})", re.MULTILINE)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Launch Fluent and run a minimal real smoke test.")
    parser.add_argument("--case-file", required=True, type=Path, help="Small, initialized Fluent case")
    parser.add_argument("--output", type=Path, default=Path("results/stage0_smoke_test"))
    parser.add_argument("--processor-count", type=int, default=2)
    parser.add_argument("--iterations", type=int, default=5)
    return parser.parse_args()


def transcript_to_csv(transcript: Path, output: Path) -> int:
    text = transcript.read_text(encoding="utf-8", errors="replace")
    rows = []
    for match in RESIDUAL_LINE.finditer(text):
        values = match.group(2).split()
        rows.append([int(match.group(1)), *values])
    with output.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.writer(stream)
        max_values = max((len(row) - 1 for row in rows), default=0)
        writer.writerow(["iteration", *[f"reported_value_{i + 1}" for i in range(max_values)]])
        for row in rows:
            writer.writerow(row)
    return len(rows)


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    status = {
        "status": "FAILED",
        "case_file": str(args.case_file),
        "precision": "double",
        "processor_count": args.processor_count,
        "requested_iterations": args.iterations,
        "synthetic_data_created": False,
    }
    args.output.mkdir(parents=True, exist_ok=True)
    session = None
    started = time.perf_counter()
    transcript = args.output / "solver_transcript.txt"
    try:
        if not args.case_file.is_file():
            raise FileNotFoundError(args.case_file)
        if args.processor_count < 1 or args.iterations < 1:
            raise ValueError("processor-count and iterations must be positive")
        import ansys.fluent.core as pyfluent

        session = pyfluent.launch_fluent(
            mode=pyfluent.FluentMode.SOLVER,
            precision=pyfluent.Precision.DOUBLE,
            processor_count=args.processor_count,
            case_file_name=args.case_file.resolve(),
            cwd=args.output.resolve(),
            start_transcript=False,
            cleanup_on_exit=True,
        )
        session.transcript.start(file_name=str(transcript), write_to_stdout=False)
        status["fluent_version"] = str(session.get_fluent_version())
        status["pyfluent_version"] = pyfluent.__version__
        session.settings.solution.initialization.hybrid_initialize()
        session.settings.solution.run_calculation.iterate(iter_count=args.iterations)
        session.transcript.stop()
        row_count = transcript_to_csv(transcript, args.output / "convergence_history.csv")
        status["convergence_rows_exported"] = row_count
        status["actual_iterations"] = args.iterations
        status["status"] = "SUCCESS"
        with (args.output / "smoke_result.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(
                stream,
                fieldnames=[
                    "status",
                    "fluent_version",
                    "pyfluent_version",
                    "precision",
                    "processor_count",
                    "actual_iterations",
                    "convergence_rows_exported",
                ],
            )
            writer.writeheader()
            writer.writerow({name: status.get(name) for name in writer.fieldnames})
        return 0
    except Exception as exc:
        status["error_type"] = type(exc).__name__
        status["error"] = str(exc)
        LOGGER.exception("Real Fluent smoke test failed")
        return 1
    finally:
        status["wall_clock_runtime_seconds"] = round(time.perf_counter() - started, 3)
        if session is not None:
            try:
                session.exit()
            except Exception:
                LOGGER.warning("Fluent session did not close cleanly", exc_info=True)
        (args.output / "smoke_test_status.json").write_text(
            json.dumps(status, indent=2) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    raise SystemExit(main())
