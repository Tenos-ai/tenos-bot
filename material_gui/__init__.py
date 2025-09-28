"""Material-themed GUI shell for the Tenos.ai configurator."""

from __future__ import annotations

try:  # pragma: no cover - exercised indirectly via imports
    from .app import launch_material_editor
except ModuleNotFoundError as exc:  # pragma: no cover - executed when PySide6 absent
    if exc.name != "PySide6":
        raise
    def _missing_launch() -> int:
        msg = (
            "The Material configurator requires the 'PySide6' package. "
            "Install it via 'pip install PySide6' to launch the GUI."
        )
        raise RuntimeError(msg) from exc

    launch_material_editor = _missing_launch  # type: ignore[assignment]

__all__ = ["launch_material_editor"]
