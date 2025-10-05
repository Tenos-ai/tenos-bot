"""Appearance customisation view for the Material configurator."""
from __future__ import annotations

import re

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QColorDialog,
    QComboBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QFrame,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository
from material_gui.theme import CUSTOM_PALETTE_KEY, PALETTES
from material_gui.views.base import BaseView

_HEX_PATTERN = re.compile(r"^#?[0-9A-Fa-f]{6}$")


def _is_valid_hex(value: str) -> bool:
    return bool(_HEX_PATTERN.fullmatch(value or ""))


def _normalise_hex(value: str) -> str:
    value = (value or "").strip()
    if not value:
        return value
    if len(value) == 6 and not value.startswith("#"):
        value = f"#{value}"
    return value.upper()


class _ColorPickerField(QWidget):
    """Compact colour selector with swatch preview and dialog launcher."""

    color_changed = Signal(str)

    def __init__(self, *, initial: str) -> None:
        super().__init__()
        self._color = ""

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self._preview = QFrame()
        self._preview.setFixedSize(28, 28)
        self._preview.setFrameShape(QFrame.StyledPanel)
        self._preview.setFrameShadow(QFrame.Sunken)
        layout.addWidget(self._preview)

        self._button = QPushButton("Select colour…")
        self._button.clicked.connect(self._choose_color)  # pragma: no cover - Qt binding
        layout.addWidget(self._button, stretch=1)

        self.set_color(initial, emit=False)

    def color(self) -> str:
        return self._color

    def set_color(self, value: str, *, emit: bool = False) -> None:
        normalised = _normalise_hex(value)
        if normalised and not _is_valid_hex(normalised):
            return
        if normalised == self._color:
            return
        self._color = normalised
        self._update_visuals()
        if emit:
            self.color_changed.emit(self._color)

    def _choose_color(self) -> None:  # pragma: no cover - Qt binding
        current = QColor(self._color or "#2563EB")
        color = QColorDialog.getColor(current, self, "Choose colour")
        if not color.isValid():
            return
        self.set_color(color.name().upper(), emit=True)

    def _update_visuals(self) -> None:
        color = QColor(self._color or "#000000")
        if not color.isValid():
            color = QColor("#000000")
        self._preview.setStyleSheet(
            "QFrame {"
            f"background-color: {color.name()};"
            "border-radius: 6px;"
            "border: 1px solid rgba(15, 23, 42, 0.35);"
            "}"
        )
        label = self._color or "#000000"
        self._button.setText(label)
        self._button.setToolTip(f"Current colour: {label}")


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
            "Custom palettes stay legible. Use the pickers or enter precise #RRGGBB values."
        )
        custom_label.setWordWrap(True)
        custom_layout.addWidget(custom_label)

        custom_form = QFormLayout()
        custom_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        self.custom_primary_picker = _ColorPickerField(initial="#2563EB")
        self.custom_surface_picker = _ColorPickerField(initial="#0F172A")
        self.custom_text_picker = _ColorPickerField(initial="#F1F5F9")
        custom_form.addRow("Accent", self.custom_primary_picker)
        custom_form.addRow("Surface", self.custom_surface_picker)
        custom_form.addRow("Text", self.custom_text_picker)
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

        primary = self.custom_primary_picker.color()
        surface = self.custom_surface_picker.color()
        text_color = self.custom_text_picker.color()

        if palette_key == CUSTOM_PALETTE_KEY:
            if not _is_valid_hex(primary):
                self.status_label.setText("Enter a valid hex colour for the accent.")
                return
            if not _is_valid_hex(surface):
                self.status_label.setText("Enter a valid hex colour for the surface.")
                return
            if not _is_valid_hex(text_color):
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

        self.custom_primary_picker.set_color(_normalise_hex(primary) or "#2563EB")
        self.custom_surface_picker.set_color(_normalise_hex(surface) or "#0F172A")
        self.custom_text_picker.set_color(_normalise_hex(text_color) or "#F1F5F9")
        self._update_custom_fields_visibility()
        self.status_label.setText("Adjust the appearance settings and click save to apply.")


__all__ = ["AppearanceSettingsView"]
