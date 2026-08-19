"""Shared paths and subprocess helpers for the test suite."""

from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys


REPO_ROOT = Path(__file__).resolve().parents[1]
SKILL_ROOT = REPO_ROOT / "skills" / "professional-kanban"
SCRIPTS_ROOT = SKILL_ROOT / "scripts"


def import_scripts() -> None:
    """Make the canonical skill scripts importable for unit tests."""
    scripts = str(SCRIPTS_ROOT)
    if scripts not in sys.path:
        sys.path.insert(0, scripts)


def run_cli(script: str, *args: object) -> subprocess.CompletedProcess[str]:
    """Run one bundled CLI without leaving Python cache files in the tree."""
    env = os.environ.copy()
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return subprocess.run(
        [sys.executable, str(SCRIPTS_ROOT / script), *(str(arg) for arg in args)],
        cwd=REPO_ROOT,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
