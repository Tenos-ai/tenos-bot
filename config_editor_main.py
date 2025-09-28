"""Entry point for the Material-themed configurator."""
from __future__ import annotations

from material_gui import launch_material_editor


def main() -> int:
    """Launch the PySide6 Material configurator shell."""

    return launch_material_editor()


if __name__ == "__main__":
    raise SystemExit(main())
