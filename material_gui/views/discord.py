"""Discord-related preferences view."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QFileDialog,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView


class DiscordSettingsView(BaseView):
    """Surface Discord-centric toggles in a Material layout."""

    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__()
        self._repository = repository

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Discord Enhancer Settings")
        title.setObjectName("MaterialTitle")
        layout.addWidget(title)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addLayout(form)

        self.enhancer_checkbox = QCheckBox("Enable prompt enhancer for slash commands")
        form.addRow("LLM Enhancer", self.enhancer_checkbox)

        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["gemini", "groq", "openai"])
        form.addRow("Provider", self.provider_combo)

        self.bot_name_input = QLineEdit()
        form.addRow("Bot Display Name", self.bot_name_input)

        avatar_row = QHBoxLayout()
        self.avatar_path_input = QLineEdit()
        self.avatar_browse_button = QPushButton("Browse…")
        self.avatar_browse_button.clicked.connect(self._browse_avatar)  # pragma: no cover
        avatar_row.addWidget(self.avatar_path_input)
        avatar_row.addWidget(self.avatar_browse_button)
        form.addRow("Bot Avatar", avatar_row)

        self.save_button = QPushButton("Save Discord Settings")
        self.save_button.clicked.connect(self._persist)  # pragma: no cover
        layout.addWidget(self.save_button)

        self.refresh(repository)

    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        data = repository.settings
        self.enhancer_checkbox.setChecked(bool(data.get("llm_enhancer_enabled", False)))
        provider = str(data.get("llm_provider", "gemini")).lower()
        idx = self.provider_combo.findText(provider)
        if idx != -1:
            self.provider_combo.setCurrentIndex(idx)
        self.bot_name_input.setText(str(data.get("discord_display_name", "")))
        self.avatar_path_input.setText(str(data.get("discord_avatar_path", "")))

    def _browse_avatar(self) -> None:  # pragma: no cover - Qt binding
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Bot Avatar",
            str(Path.home()),
            "Image Files (*.png *.jpg *.jpeg *.gif)",
        )
        if file_path:
            self.avatar_path_input.setText(file_path)

    def _persist(self) -> None:  # pragma: no cover - Qt binding
        payload = {
            "llm_enhancer_enabled": self.enhancer_checkbox.isChecked(),
            "llm_provider": self.provider_combo.currentText(),
            "discord_display_name": self.bot_name_input.text().strip(),
            "discord_avatar_path": self.avatar_path_input.text().strip(),
        }
        self._repository.save_settings(payload)
