"""Appearance customisation view for the Material configurator."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository
from material_gui.theme import CUSTOM_PALETTE_KEY, PALETTES
from material_gui.views.base import BaseView

_HEX_PATTERN = re.compile(r"^#?[0-9A-Fa-f]{6}$")


class AppearanceSettingsView(BaseView):
    """Allow users to tailor the configurator colour palette and mode."""

    def __init__(
        self,
        repository: SettingsRepository,
        *,
        on_palette_change,
        on_mode_change,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._on_palette_change = on_palette_change
        self._on_mode_change = on_mode_change

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Appearance Settings")
        title.setObjectName("MaterialTitle")
        layout.addWidget(title)

        description = QLabel(
            "Choose from curated Material palettes or build a custom scheme."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addLayout(form)

        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Dark", "dark")
        self.mode_combo.addItem("Light", "light")
        self.mode_combo.currentIndexChanged.connect(self._handle_mode_changed)  # pragma: no cover - Qt binding
        form.addRow("Theme Mode", self.mode_combo)

        self.palette_combo = QComboBox()
        for key, palette in PALETTES.items():
            self.palette_combo.addItem(palette.display_name, key)
        self.palette_combo.addItem("Custom (Material guided)", CUSTOM_PALETTE_KEY)
        self.palette_combo.currentIndexChanged.connect(self._update_custom_fields_visibility)  # pragma: no cover - Qt binding
        form.addRow("Palette", self.palette_combo)

        self.custom_widget = QWidget()
        custom_layout = QVBoxLayout(self.custom_widget)
        custom_layout.setContentsMargins(0, 0, 0, 0)
        custom_layout.setSpacing(8)
        custom_label = QLabel(
            "Custom palettes are guided to remain legible. Enter #RRGGBB colours."
        )
        custom_label.setWordWrap(True)
        custom_layout.addWidget(custom_label)

        custom_form = QFormLayout()
        custom_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.custom_primary_input = QLineEdit()
        self.custom_surface_input = QLineEdit()
        self.custom_text_input = QLineEdit()
        custom_form.addRow("Accent", self.custom_primary_input)
        custom_form.addRow("Surface", self.custom_surface_input)
        custom_form.addRow("Text", self.custom_text_input)
        custom_layout.addLayout(custom_form)
        layout.addWidget(self.custom_widget)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.save_button = QPushButton("Save Appearance Settings")
        self.save_button.clicked.connect(self._persist)  # pragma: no cover - Qt binding
        button_row.addWidget(self.save_button)
        layout.addLayout(button_row)

        self.status_label = QLabel("Select a palette and click save to apply.")
        self.status_label.setObjectName("MaterialCard")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.refresh(repository)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _is_valid_hex(self, value: str) -> bool:
        return bool(_HEX_PATTERN.fullmatch(value or ""))

    def _normalise_hex(self, value: str) -> str:
        value = value.strip()
        if not value:
            return value
        if len(value) == 6 and not value.startswith("#"):
            value = f"#{value}"
        return value.upper()

    def _update_custom_fields_visibility(self) -> None:
        is_custom = self.palette_combo.currentData() == CUSTOM_PALETTE_KEY
        self.custom_widget.setVisible(is_custom)

    def _handle_mode_changed(self) -> None:  # pragma: no cover - Qt binding
        mode_value = self.mode_combo.currentData()
        if callable(self._on_mode_change):
            self._on_mode_change(mode_value)

    def _persist(self) -> None:  # pragma: no cover - Qt binding
        mode_value = self.mode_combo.currentData()
        palette_key = self.palette_combo.currentData()

        primary = self._normalise_hex(self.custom_primary_input.text())
        surface = self._normalise_hex(self.custom_surface_input.text())
        text_color = self._normalise_hex(self.custom_text_input.text())

        if palette_key == CUSTOM_PALETTE_KEY:
            if not self._is_valid_hex(primary):
                self.status_label.setText("Enter a valid hex colour for the accent.")
                return
            if not self._is_valid_hex(surface):
                self.status_label.setText("Enter a valid hex colour for the surface.")
                return
            if not self._is_valid_hex(text_color):
                self.status_label.setText("Enter a valid hex colour for the text.")
                return
        else:
            current = self._repository.get_theme_preferences()
            primary = current.get("custom_primary", "#2563EB")
            surface = current.get("custom_surface", "#0F172A")
            text_color = current.get("custom_text", "#F1F5F9")

        self._repository.save_theme_preferences(
            mode=mode_value,
            palette=palette_key,
            custom_primary=primary,
            custom_surface=surface,
            custom_text=text_color,
        )

        if callable(self._on_mode_change):
            self._on_mode_change(mode_value)
        if callable(self._on_palette_change):
            self._on_palette_change(palette_key, primary, surface, text_color)

        self.status_label.setText("Appearance preferences saved.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        prefs = repository.get_theme_preferences()
        mode = prefs.get("mode", "dark").lower()
        palette = prefs.get("palette", "oceanic").lower()
        primary = prefs.get("custom_primary", "#2563EB")
        surface = prefs.get("custom_surface", "#0F172A")
        text_color = prefs.get("custom_text", "#F1F5F9")

        self.mode_combo.blockSignals(True)
        mode_index = self.mode_combo.findData("light" if mode == "light" else "dark")
        self.mode_combo.setCurrentIndex(max(0, mode_index))
        self.mode_combo.blockSignals(False)

        self.palette_combo.blockSignals(True)
        palette_index = self.palette_combo.findData(palette)
        if palette_index == -1:
            palette_index = self.palette_combo.findData("oceanic")
        self.palette_combo.setCurrentIndex(max(0, palette_index))
        self.palette_combo.blockSignals(False)

        self.custom_primary_input.setText(self._normalise_hex(primary))
        self.custom_surface_input.setText(self._normalise_hex(surface))
        self.custom_text_input.setText(self._normalise_hex(text_color))
        self._update_custom_fields_visibility()
        self.status_label.setText("Adjust the appearance settings and click save to apply.")


__all__ = ["AppearanceSettingsView"]
