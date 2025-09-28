"""Overview dashboard for the Material Configurator."""
from __future__ import annotations

from PySide6.QtWidgets import QLabel, QTextEdit, QVBoxLayout

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView


class OverviewView(BaseView):
    """Display a summary of active configuration."""

    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__()
        self._repository = repository

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(16)

        title = QLabel("Configurator Overview")
        title.setObjectName("MaterialTitle")
        layout.addWidget(title)

        self.summary_box = QTextEdit()
        self.summary_box.setReadOnly(True)
        self.summary_box.setObjectName("MaterialCard")
        layout.addWidget(self.summary_box)

        self.refresh(repository)

    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        settings = repository.settings
        preferred_flux = settings.get("preferred_model_flux") or "Not configured"
        preferred_sdxl = settings.get("preferred_model_sdxl") or "Not configured"
        preferred_qwen = settings.get("preferred_model_qwen") or "Not configured"
        default_engine = settings.get("default_edit_engine", "kontext")

        lines = [
            "Active defaults:",
            f"• Flux model: {preferred_flux}",
            f"• SDXL model: {preferred_sdxl}",
            f"• Qwen model: {preferred_qwen}",
            f"• Edit engine: {default_engine.capitalize()}",
            "",
            "Tip: Use the navigation to configure Discord behaviour or fine-tune Qwen edit settings.",
        ]
        self.summary_box.setPlainText("\n".join(lines))
