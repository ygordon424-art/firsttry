#!/usr/bin/env python3
"""Plan or deliberately execute configured CFD cases."""

from __future__ import annotations

import argparse
import logging
import subprocess
import sys
from pathlib import Path

try:
    from .common import load_yaml, project_root
except ImportError:  # Direct script execution.
    from common import load_yaml, project_root

LOGGER = logging.getLogger("run_batch")


def parse_args() -> argparse.Namespace:
    root = project_root()
    parser = argparse.ArgumentParser(description="List or execute selected CFD cases.")
    parser.add_argument("--cases", type=Path, default=root / "config/cases.yaml")
    parser.add_argument("--case-id", action="append", dest="case_ids", help="Repeat to select cases")
    parser.add_argument("--all", action="store_true", help="Select all 20 production matrix cases")
    parser.add_argument("--execute", action="store_true", help="Actually invoke Fluent case runner")
    parser.add_argument(
        "--confirm-production",
        action="store_true",
        help="Required with --execute as an accidental-run safeguard",
    )
    parser.add_argument("--case-file-root", type=Path, help="Directory containing <case_id>.cas.h5")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.INFO)
    try:
        config = load_yaml(args.cases)
        cases = config.get("cases", [])
        selected = cases if args.all else [c for c in cases if c["case_id"] in (args.case_ids or [])]
        if not selected:
            LOGGER.error("No cases selected. Use --case-id or --all.")
            return 2
        for case in selected:
            print(f"{case['case_id']}: PLANNED (enabled={case.get('enabled', False)})")
        if not args.execute:
            LOGGER.info("Dry plan only; no solver was launched")
            return 0
        if not args.confirm_production:
            LOGGER.error("Execution refused without --confirm-production")
            return 2
        disabled = [case["case_id"] for case in selected if not case.get("enabled", False)]
        if disabled:
            LOGGER.error("Execution refused; cases remain disabled: %s", ", ".join(disabled))
            return 2
        if not args.case_file_root:
            LOGGER.error("Execution requires --case-file-root")
            return 2
        runner = Path(__file__).with_name("run_case.py")
        for case in selected:
            case_file = args.case_file_root / f"{case['case_id']}.cas.h5"
            completed = subprocess.run(
                [sys.executable, str(runner), case["case_id"], "--execute", "--case-file", str(case_file)],
                check=False,
            )
            if completed.returncode:
                LOGGER.error("Batch stopped after failure in %s", case["case_id"])
                return completed.returncode
        return 0
    except Exception:
        LOGGER.exception("Batch planning/execution failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
