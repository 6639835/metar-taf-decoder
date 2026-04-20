"""CLI smoke tests for installed and no-install execution paths."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def run_module_command(*args: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(PROJECT_ROOT / "src")
    return subprocess.run(
        [sys.executable, "-m", "weather_decoder", *args],
        cwd=PROJECT_ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )


def test_python_module_metar_subcommand_smoke():
    result = run_module_command(
        "metar",
        "METAR KJFK 061751Z 28008KT 10SM FEW250 22/18 A2992",
    )

    assert result.returncode == 0
    assert "KJFK" in result.stdout


def test_python_module_taf_subcommand_smoke():
    result = run_module_command(
        "taf",
        "TAF KJFK 061730Z 0618/0724 28008KT 9999 FEW250",
    )

    assert result.returncode == 0
    assert "KJFK" in result.stdout
