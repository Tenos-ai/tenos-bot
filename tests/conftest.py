"""Pytest configuration for Tenos.ai project tests."""
from __future__ import annotations

import os
import sys
from pathlib import Path


def pytest_configure():
    """Ensure the project root is on ``sys.path`` for package imports."""
    repo_root = Path(__file__).resolve().parent.parent
    root_str = str(repo_root)
    if root_str not in sys.path:
        sys.path.insert(0, root_str)
    os.environ.setdefault("TENOS_TESTING", "1")
