"""Backward-compatible shim for the new material_gui.model_scanner module."""
from __future__ import annotations

from material_gui.model_scanner import *  # noqa: F401,F403

# The configurator historically imported ``model_scanner`` from the project
# root.  The module now lives within :mod:`material_gui` so that PyInstaller
# can reliably bundle it alongside the GUI.  Re-exporting everything keeps
# existing imports working without requiring immediate upstream changes.
