"""Base classes for Material GUI views."""
from __future__ import annotations

from typing import Protocol

from PySide6.QtWidgets import QWidget

from material_gui.repository import SettingsRepository


class MaterialView(Protocol):
    """Protocol for Material UI views."""

    def widget(self) -> QWidget:  # pragma: no cover - Qt widget access
        ...

    def refresh(self, repository: SettingsRepository) -> None:
        ...


class BaseView(QWidget):
    """Convenience QWidget subclass with refresh hook."""

    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI hook
        del repository
