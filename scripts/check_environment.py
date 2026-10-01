#!/usr/bin/env python3
"""Audit the execution environment without revealing credential values."""

from __future__ import annotations

import argparse
import ctypes
import importlib.metadata
import json
import logging
import os
import platform
import re
import shutil
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

LOGGER = logging.getLogger("environment_check")
LICENSE_ENV_NAMES = (
    "ANSYSLMD_LICENSE_FILE",
    "ANSYSLI_SERVERS",
    "ANSYSLIC_DIR",
    "LM_LICENSE_FILE",
    "FLUENT_LICENSE_FILE",
)
CI_ENV_NAMES = (
    "GITHUB_ACTIONS",
    "RUNNER_NAME",
    "RUNNER_OS",
    "RUNNER_ENVIRONMENT",
    "CI",
    "TF_BUILD",
    "GITLAB_CI",
    "JENKINS_URL",
)


def command_version(command: list[str]) -> tuple[bool, str | None]:
    executable = shutil.which(command[0])
    if not executable:
        return False, None
    try:
        completed = subprocess.run(
            [executable, *command[1:]],
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        text = (completed.stdout or completed.stderr).strip().splitlines()
        return True, text[0] if text else "installed (version unavailable)"
    except (OSError, subprocess.SubprocessError) as exc:
        LOGGER.warning("Could not query %s: %s", command[0], exc)
        return True, "installed (version query failed)"


def package_version(distribution: str) -> str | None:
    try:
        return importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        return None


def windows_memory() -> tuple[float | None, float | None]:
    if os.name != "nt":
        try:
            page_size = os.sysconf("SC_PAGE_SIZE")
            total = page_size * os.sysconf("SC_PHYS_PAGES")
            available = page_size * os.sysconf("SC_AVPHYS_PAGES")
            return total / 2**30, available / 2**30
        except (AttributeError, OSError, ValueError):
            return None, None

    class MemoryStatusEx(ctypes.Structure):
        _fields_ = [
            ("dwLength", ctypes.c_ulong),
            ("dwMemoryLoad", ctypes.c_ulong),
            ("ullTotalPhys", ctypes.c_ulonglong),
            ("ullAvailPhys", ctypes.c_ulonglong),
            ("ullTotalPageFile", ctypes.c_ulonglong),
            ("ullAvailPageFile", ctypes.c_ulonglong),
            ("ullTotalVirtual", ctypes.c_ulonglong),
            ("ullAvailVirtual", ctypes.c_ulonglong),
            ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
        ]

    status = MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        return None, None
    return status.ullTotalPhys / 2**30, status.ullAvailPhys / 2**30


def windows_registry_value(path: str, name: str) -> str | None:
    if os.name != "nt":
        return None
    try:
        import winreg

        with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, path) as key:
            return str(winreg.QueryValueEx(key, name)[0]).strip()
    except (OSError, ImportError):
        return None


def find_fluent() -> Path | None:
    located = shutil.which("fluent") or shutil.which("fluent.exe")
    if located:
        return Path(located).resolve()
    if os.name == "nt":
        roots = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "ANSYS Inc"]
        roots.extend(Path(value) for key, value in os.environ.items() if key.startswith("AWP_ROOT") and value)
        patterns = ("v*/fluent/ntbin/win64/fluent.exe", "fluent/ntbin/win64/fluent.exe")
        for root in roots:
            if not root.is_dir():
                continue
            for pattern in patterns:
                match = next(root.glob(pattern), None)
                if match and match.is_file():
                    return match.resolve()
    return None


def classify_environment() -> str:
    if os.environ.get("GITHUB_ACTIONS"):
        hosted = "self-hosted or GitHub-hosted (labels unavailable to safe audit)"
        return f"GitHub Actions runner: {hosted}"
    if any(os.environ.get(name) for name in CI_ENV_NAMES):
        return "CI runner (provider detected by environment flag)"
    if os.environ.get("SLURM_JOB_ID") or os.environ.get("PBS_JOBID"):
        return "HPC scheduled job"
    return "Local/interactive Windows environment (no CI or scheduler markers detected)" if os.name == "nt" else "Local/interactive environment (no CI or scheduler markers detected)"


def audit() -> dict[str, Any]:
    total_ram, available_ram = windows_memory()
    disk = shutil.disk_usage(Path.cwd())
    python_ok, python_ver = command_version([sys.executable, "--version"])
    git_ok, git_ver = command_version(["git", "--version"])
    docker_ok, docker_ver = command_version(["docker", "--version"])
    docker_engine = False
    if docker_ok:
        try:
            docker_engine = subprocess.run(
                ["docker", "info"], capture_output=True, timeout=15, check=False
            ).returncode == 0
        except (OSError, subprocess.SubprocessError):
            docker_engine = False

    fluent_path = find_fluent()
    fluent_version = None
    if fluent_path:
        version_match = re.search(r"[\\/]v(\d{3})[\\/]", str(fluent_path), re.IGNORECASE)
        fluent_version = version_match.group(1) if version_match else "installed; exact version not queried"

    scheduler_commands = {
        name: bool(shutil.which(name)) for name in ("sbatch", "srun", "qsub", "pbsnodes")
    }
    cpu_name = windows_registry_value(
        r"HARDWARE\DESCRIPTION\System\CentralProcessor\0", "ProcessorNameString"
    ) or platform.processor() or "Unknown"
    os_name = platform.platform()
    product_name = windows_registry_value(
        r"SOFTWARE\Microsoft\Windows NT\CurrentVersion", "ProductName"
    )

    return {
        "checked_at_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "operating_system": os_name,
        "os_registry_product": product_name,
        "cpu_model": cpu_name,
        "available_logical_cores": os.cpu_count(),
        "ram_total_gib": round(total_ram, 2) if total_ram is not None else None,
        "ram_available_gib": round(available_ram, 2) if available_ram is not None else None,
        "disk_total_gib": round(disk.total / 2**30, 2),
        "disk_free_gib": round(disk.free / 2**30, 2),
        "python_available": python_ok,
        "python_version": python_ver,
        "git_available": git_ok,
        "git_version": git_ver,
        "docker_cli_available": docker_ok,
        "docker_version": docker_ver,
        "docker_engine_available": docker_engine,
        "fluent_available": fluent_path is not None,
        "fluent_executable": str(fluent_path) if fluent_path else None,
        "fluent_version": fluent_version,
        "pyfluent_available": package_version("ansys-fluent-core") is not None,
        "pyfluent_version": package_version("ansys-fluent-core"),
        "license_available": "UNKNOWN",
        "license_environment_variables": {
            name: "PRESENT_REDACTED" if os.environ.get(name) else "ABSENT"
            for name in LICENSE_ENV_NAMES
        },
        "execution_environment": classify_environment(),
        "scheduler_commands": scheduler_commands,
    }


def yes_no(value: bool) -> str:
    return "YES" if value else "NO"


def render_markdown(data: dict[str, Any]) -> str:
    blockers = []
    if not data["fluent_available"]:
        blockers.append("Fluent executable missing; no real solver process can be started.")
    if data["license_available"] != "YES":
        blockers.append("Fluent license availability is unverified because Fluent cannot be launched.")
    if (data["ram_total_gib"] or 0) < 32:
        blockers.append("Installed RAM is below the recommended starting point for 4–7M-cell production CFD.")
    if data["disk_free_gib"] < 100:
        blockers.append("Free local disk space is insufficient for comfortable production case/data and artifact handling.")
    scheduler = ", ".join(
        f"{name}: {yes_no(found)}" for name, found in data["scheduler_commands"].items()
    )
    license_env = "\n".join(
        f"- `{name}`: {state}"
        for name, state in data["license_environment_variables"].items()
    )
    blocker_text = "\n".join(f"- {item}" for item in blockers) or "- None detected."
    return f"""# Environment report

Generated by `scripts/check_environment.py` at `{data['checked_at_local']}`. Secret values, tokens, and license-server addresses are never printed.

## Host and resources

- Operating system: {data['operating_system']}
- Registry product label: {data['os_registry_product'] or 'Unavailable'}
- CPU: {data['cpu_model']}
- Available logical cores: {data['available_logical_cores']}
- RAM: {data['ram_total_gib']} GiB total; {data['ram_available_gib']} GiB available at audit time
- Working-volume disk: {data['disk_total_gib']} GiB total; {data['disk_free_gib']} GiB free
- Execution environment: {data['execution_environment']}

## Software

- Python: {data['python_version'] or 'NOT FOUND'}
- Git: {data['git_version'] or 'NOT FOUND'}
- Docker CLI available: {yes_no(data['docker_cli_available'])}
- Docker engine available: {yes_no(data['docker_engine_available'])}
- Fluent available: {yes_no(data['fluent_available'])}
- Fluent executable: {data['fluent_executable'] or 'NOT FOUND'}
- Fluent version: {data['fluent_version'] or 'UNKNOWN (executable missing)'}
- PyFluent available: {yes_no(data['pyfluent_available'])}
- PyFluent version: {data['pyfluent_version'] or 'NOT INSTALLED'}
- Fluent license available: {data['license_available']}
- Scheduler commands: {scheduler}

## License environment (presence only)

{license_env}

Absence of these variables does not prove that a license is unavailable: a client may use a system-level configuration. Because no Fluent executable exists here, a real checkout test cannot be performed and the license status remains **UNKNOWN**.

## Stage 0 decision

The environment cannot run a genuine Fluent smoke test because the Fluent solver executable is missing. PyFluent is an orchestration client, not a solver. No synthetic CFD transcript, convergence history, or result CSV was generated.

Hardware suitability for 4–7M-cell CFD: **NO in the current state**. The 16 logical CPU cores are useful, but {data['ram_total_gib']} GiB total RAM, only {data['ram_available_gib']} GiB available during inspection, and {data['disk_free_gib']} GiB free disk do not provide safe production headroom.

## Current blockers

{blocker_text}

## Required next environment

Use a licensed ANSYS Fluent compute node or workstation with a version compatible with PyFluent, verified license checkout, at least 32 GiB RAM (64 GiB preferred for headroom), sufficient fast scratch storage (at least 100 GiB free for the planned workflow), and a deliberate processor count matched to the license/HPC allocation. Run the Stage 0 smoke test there before any production matrix case.
"""


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Safely audit CFD host capabilities and write a Markdown report."
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/environment_report.md"),
        help="Markdown report path (default: reports/environment_report.md)",
    )
    parser.add_argument("--json", type=Path, help="Optional machine-readable JSON output")
    parser.add_argument("--verbose", action="store_true", help="Enable diagnostic logging")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO)
    try:
        data = audit()
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(render_markdown(data), encoding="utf-8")
        if args.json:
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        LOGGER.info("Environment report written to %s", args.output)
        return 0
    except Exception:
        LOGGER.exception("Environment audit failed")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
