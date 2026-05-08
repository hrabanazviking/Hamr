"""
Blender Bridge — Headless subprocess runner for Hamr.

Runs Blender in background mode, executes Python scripts,
captures stdout/stderr, and returns structured results.

The bridge never opens a GUI. It speaks to Blender through
the command line, like a völva speaking to the beyond.
"""

from __future__ import annotations

import json
import logging
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

logger = logging.getLogger("hamr.blender_bridge.runner")

# Blender executable — prefer BLENDER_PATH env, then system blender
BLENDER_EXE = "blender"

# ARM64 Linux needs this flag
BLENDER_EXTRA_ARGS = ["--python-use-system-env"]


class BlenderResult:
    """Structured result from a Blender subprocess run."""

    def __init__(
        self,
        exit_code: int,
        stdout: str,
        stderr: str,
        elapsed: float,
        output_files: list[str] | None = None,
    ) -> None:
        self.exit_code = exit_code
        self.stdout = stdout
        self.stderr = stderr
        self.elapsed = elapsed
        self.output_files = output_files or []

    @property
    def success(self) -> bool:
        return self.exit_code == 0

    def __repr__(self) -> str:
        status = "✓" if self.success else "✗"
        return f"BlenderResult({status} exit={self.exit_code} time={self.elapsed:.1f}s)"


def run_blender_script(
    script_path: str | Path,
    script_args: list[str] | None = None,
    blender_args: list[str] | None = None,
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> BlenderResult:
    """
    Run a Python script inside headless Blender.

    Args:
        script_path: Path to the Python script to run inside Blender.
        script_args: Arguments to pass to the script (after --).
        blender_args: Additional Blender arguments (e.g., --addons).
        timeout: Maximum seconds to wait. Default 600 (10 minutes).
        env: Extra environment variables.

    Returns:
        BlenderResult with exit code, output, and timing.
    """
    script_path = Path(script_path)
    if not script_path.exists():
        raise FileNotFoundError(f"Blender script not found: {script_path}")

    # Build command
    cmd = [
        BLENDER_EXE,
        "--background",          # No GUI
        "--python-use-system-env",  # ARM64 Linux fix
    ]

    if blender_args:
        cmd.extend(blender_args)

    cmd.extend([
        "--python", str(script_path),
    ])

    if script_args:
        cmd.append("--")
        cmd.extend(script_args)

    # Environment
    import os
    run_env = os.environ.copy()
    run_env["BLENDER_VRM_AUTOMATIC_LICENSE_CONFIRMATION"] = "true"
    if env:
        run_env.update(env)

    logger.info(f"Running Blender: {' '.join(cmd)}")
    start = time.time()

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=timeout,
            env=run_env,
        )
        elapsed = time.time() - start
        return BlenderResult(
            exit_code=result.returncode,
            stdout=result.stdout,
            stderr=result.stderr,
            elapsed=elapsed,
        )
    except subprocess.TimeoutExpired:
        elapsed = time.time() - start
        logger.error(f"Blender timed out after {elapsed:.1f}s")
        return BlenderResult(
            exit_code=-1,
            stdout="",
            stderr=f"Process timed out after {timeout}s",
            elapsed=elapsed,
        )
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Blender process failed: {e}")
        return BlenderResult(
            exit_code=-2,
            stdout="",
            stderr=str(e),
            elapsed=elapsed,
        )


def run_inline_script(
    python_code: str,
    timeout: int = 600,
    env: dict[str, str] | None = None,
) -> BlenderResult:
    """
    Run inline Python code inside headless Blender.

    Writes the code to a temporary file and runs it.
    Useful for quick operations that don't warrant a full script file.
    """
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".py", delete=False, prefix="hamr_"
    ) as f:
        f.write(python_code)
        temp_path = f.name

    try:
        result = run_blender_script(temp_path, timeout=timeout, env=env)
        return result
    finally:
        Path(temp_path).unlink(missing_ok=True)


def check_blender_available() -> bool:
    """Check if Blender is installed and accessible."""
    try:
        result = subprocess.run(
            [BLENDER_EXE, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def get_blender_version() -> str | None:
    """Get the Blender version string."""
    try:
        result = subprocess.run(
            [BLENDER_EXE, "--version"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode == 0:
            first_line = result.stdout.strip().split("\n")[0]
            # "Blender 3.4.1" → "3.4.1"
            return first_line.split()[-1] if first_line else None
        return None
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None