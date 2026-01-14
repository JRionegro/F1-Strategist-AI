"""Lint test to prevent accidental F541 f-strings.

Project instruction: avoid generating f-strings without placeholders.
This test enforces that rule for the new predictive package.
"""

from __future__ import annotations

import subprocess
import sys


def test_flake8_no_f541_in_predictive_package() -> None:
    """Verify there are no F541 errors in src/predictive."""
    result = subprocess.run(
        [sys.executable, "-m", "flake8", "--select=F541", "src/predictive"],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, (
        "F541 errors found in src/predictive:\n"
        f"{result.stdout}{result.stderr}"
    )
