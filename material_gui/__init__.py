"""Material-themed GUI shell for the Tenos.ai configurator."""

from __future__ import annotations

import subprocess
import sys
from importlib import import_module
from typing import Final

_PYSIDE_REQUIREMENT: Final[str] = "PySide6>=6.7"

try:  # pragma: no cover - exercised indirectly via imports
    from .app import launch_material_editor
except ModuleNotFoundError as exc:  # pragma: no cover - executed when PySide6 absent
    if exc.name != "PySide6":
        raise

    def _install_pyside6(requirement: str = _PYSIDE_REQUIREMENT) -> None:
        """Install PySide6 so the configurator can launch."""

        command = [sys.executable, "-m", "pip", "install", "--upgrade", requirement]
        print(
            f"[material_gui] {requirement} not found. Attempting automatic installation...",
            flush=True,
        )
        try:
            subprocess.check_call(command)
        except Exception as install_exc:  # noqa: BLE001 - surface original failure context
            raise RuntimeError(
                f"Automatic installation of {requirement} failed."
            ) from install_exc

    def _missing_launch() -> int:
        msg = (
            "The Material configurator requires the 'PySide6' package. "
            f"Install it via 'pip install {_PYSIDE_REQUIREMENT}' to launch the GUI."
        )

        try:
            _install_pyside6()
        except RuntimeError as install_error:
            raise RuntimeError(msg) from install_error

        try:
            module = import_module("material_gui.app")
        except ModuleNotFoundError as import_exc:  # pragma: no cover - unexpected post-install failure
            if import_exc.name == "PySide6":
                raise RuntimeError(msg) from import_exc
            raise

        launch = module.launch_material_editor
        globals()["launch_material_editor"] = launch
        return launch()

    launch_material_editor = _missing_launch  # type: ignore[assignment]

__all__ = ["launch_material_editor"]
