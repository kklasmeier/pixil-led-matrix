"""Shared pytest configuration for the Pixil test suite."""

import sys
from pathlib import Path

import pytest

# Repo root on sys.path so `pixil_utils` imports work like production.
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def pytest_collection_modifyitems(config, items):
    """Skip hardware tests unless rgbmatrix is available."""
    try:
        import rgbmatrix  # noqa: F401
        has_hardware = True
    except ImportError:
        has_hardware = False

    if has_hardware:
        return

    skip_hardware = pytest.mark.skip(
        reason="rgbmatrix not installed (hardware tests skipped)"
    )
    for item in items:
        if "hardware" in item.keywords:
            item.add_marker(skip_hardware)
