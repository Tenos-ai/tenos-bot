"""LoRA style preset editor for the Material configurator."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from material_gui.views.base import BaseView
from settings_manager import load_styles_config

STYLE_CONFIG_PATH = Path("styles_config.json")


@dataclass
class LoraSlotControls:
    toggle: QCheckBox
    name: QComboBox
    strength: QDoubleSpinBox


class LoraStylesView(BaseView):
    """Manage reusable LoRA style presets including favourites and weights."""

    def __init__(self) -> None:
        super().__init__()
        self._styles: Dict[str, dict] = {}
        self._current_style: Optional[str] = None
        self._slot_controls: list[LoraSlotControls] = []

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("LoRA Styles")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        description = QLabel(
            "Create named style presets that bundle LoRA toggles and strengths. "
            "These presets surface in /settings, /gen, and /edit commands."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        body = QHBoxLayout()
        body.setSpacing(18)
        root_layout.addLayout(body, stretch=1)

        self._style_list = QListWidget()
        self._style_list.currentItemChanged.connect(self._handle_selection_changed)  # pragma: no cover - Qt binding
        body.addWidget(self._style_list, stretch=1)

        detail_container = QVBoxLayout()
        detail_container.setSpacing(12)
        body.addLayout(detail_container, stretch=2)

        detail_container.addWidget(self._build_detail_group())

        button_row = QHBoxLayout()
        add_button = QPushButton("Add Style")
        add_button.clicked.connect(self._add_style)  # pragma: no cover - Qt binding
        duplicate_button = QPushButton("Duplicate")
        duplicate_button.clicked.connect(self._duplicate_style)  # pragma: no cover - Qt binding
        rename_button = QPushButton("Rename")
        rename_button.clicked.connect(self._rename_style)  # pragma: no cover - Qt binding
        delete_button = QPushButton("Delete")
        delete_button.clicked.connect(self._delete_style)  # pragma: no cover - Qt binding
        button_row.addWidget(add_button)
        button_row.addWidget(duplicate_button)
        button_row.addWidget(rename_button)
        button_row.addWidget(delete_button)
        detail_container.addLayout(button_row)

        action_row = QHBoxLayout()
        action_row.addStretch()
        save_button = QPushButton("Save Styles")
        save_button.clicked.connect(self._persist_styles)  # pragma: no cover - Qt binding
        action_row.addWidget(save_button)
        detail_container.addLayout(action_row)

        self._status_label = QLabel("Select a style to edit its LoRA slots.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self.refresh(None)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_detail_group(self) -> QGroupBox:
        group = QGroupBox("Style Details")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        header_layout = QFormLayout()
        header_layout.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addLayout(header_layout)

        self._favorite_checkbox = QCheckBox("Mark as favourite in menus")
        header_layout.addRow("Favourite", self._favorite_checkbox)

        self._model_type_combo = QComboBox()
        self._model_type_combo.addItems(["all", "flux", "sdxl", "qwen"])
        header_layout.addRow("Model Family", self._model_type_combo)

        slots_group = QGroupBox("LoRA Slots")
        slots_form = QFormLayout(slots_group)
        slots_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        layout.addWidget(slots_group)

        self._slot_controls.clear()
        for index in range(1, 6):
            toggle = QCheckBox("Enabled")
            name_combo = QComboBox()
            name_combo.setEditable(True)
            name_combo.setPlaceholderText("Filename")
            strength = QDoubleSpinBox()
            strength.setRange(0.0, 2.0)
            strength.setSingleStep(0.05)
            strength.setDecimals(2)

            row_layout = QHBoxLayout()
            row_layout.addWidget(toggle)
            row_layout.addWidget(name_combo, stretch=1)
            row_layout.addWidget(strength)

            slots_form.addRow(f"LoRA {index}", row_layout)
            self._slot_controls.append(LoraSlotControls(toggle, name_combo, strength))

        return group

    # ------------------------------------------------------------------
    # Button handlers
    # ------------------------------------------------------------------
    def _add_style(self) -> None:  # pragma: no cover - Qt binding
        name, ok = QInputDialog.getText(self, "New Style", "Style name:")
        if not ok or not name.strip():
            return
        style_name = name.strip()
        if style_name.lower() == "off":
            QMessageBox.warning(self, "Invalid Name", "'off' is reserved for disabling styles.")
            return
        if style_name in self._styles:
            QMessageBox.warning(self, "Duplicate Style", "A style with that name already exists.")
            return
        self._styles[style_name] = self._default_style_payload()
        self._refresh_style_list(select=style_name)
        self._set_status(f"Style '{style_name}' created. Configure the slots then save.")

    def _duplicate_style(self) -> None:  # pragma: no cover - Qt binding
        if not self._current_style:
            self._set_status("Select a style to duplicate.")
            return
        base_name = self._current_style
        suffix = 1
        while f"{base_name}_copy{suffix}" in self._styles:
            suffix += 1
        new_name = f"{base_name}_copy{suffix}"
        self._update_style_from_form()
        self._styles[new_name] = json.loads(json.dumps(self._styles.get(base_name, {})))
        self._styles[new_name]["favorite"] = False
        self._refresh_style_list(select=new_name)
        self._set_status(f"Duplicated '{base_name}' → '{new_name}'.")

    def _rename_style(self) -> None:  # pragma: no cover - Qt binding
        if not self._current_style or self._current_style == "off":
            self._set_status("The 'off' style cannot be renamed.")
            return
        new_name, ok = QInputDialog.getText(self, "Rename Style", "New name:", text=self._current_style)
        if not ok or not new_name.strip():
            return
        candidate = new_name.strip()
        if candidate in self._styles and candidate != self._current_style:
            QMessageBox.warning(self, "Duplicate Style", "Another style already uses that name.")
            return
        if candidate.lower() == "off":
            QMessageBox.warning(self, "Invalid Name", "'off' is reserved for disabling styles.")
            return
        self._update_style_from_form()
        self._styles[candidate] = self._styles.pop(self._current_style)
        self._refresh_style_list(select=candidate)
        self._set_status(f"Renamed style to '{candidate}'.")

    def _delete_style(self) -> None:  # pragma: no cover - Qt binding
        if not self._current_style:
            self._set_status("Select a style to delete.")
            return
        if self._current_style == "off":
            QMessageBox.warning(self, "Protected Style", "The 'off' style cannot be removed.")
            return
        confirm = QMessageBox.question(
            self,
            "Delete Style",
            f"Remove style '{self._current_style}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if confirm != QMessageBox.Yes:
            return
        del self._styles[self._current_style]
        self._current_style = None
        self._refresh_style_list()
        self._clear_form()
        self._set_status("Style removed. Save to persist changes.")

    def _persist_styles(self) -> None:  # pragma: no cover - Qt binding
        try:
            self._update_style_from_form()
            data = dict(self._styles)
            STYLE_CONFIG_PATH.write_text(json.dumps(data, indent=2))
            self._set_status("Styles saved to styles_config.json.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status("Unable to save styles. See details above.")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _default_style_payload(self) -> dict:
        payload = {
            "favorite": False,
            "model_type": "all",
        }
        for index in range(1, 6):
            payload[f"lora_{index}"] = {
                "on": False,
                "lora": "NONE.safetensors",
                "strength": 0.0,
            }
        return payload

    def _handle_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        self._update_style_from_form()
        if current is None:
            self._current_style = None
            self._clear_form()
            return
        style_name = current.data(Qt.UserRole)
        if not isinstance(style_name, str):
            self._clear_form()
            self._current_style = None
            return
        self._current_style = style_name
        self._populate_form(self._styles.get(style_name, {}))
        self._set_status(f"Editing '{style_name}'. Remember to save after making changes.")

    def _populate_form(self, data: dict) -> None:
        self._favorite_checkbox.setChecked(bool(data.get("favorite", False)))
        model_type = str(data.get("model_type", "all")).lower()
        index = self._model_type_combo.findText(model_type)
        if index == -1:
            self._model_type_combo.addItem(model_type)
            index = self._model_type_combo.findText(model_type)
        self._model_type_combo.setCurrentIndex(index if index != -1 else 0)

        for idx, controls in enumerate(self._slot_controls, start=1):
            slot_data = data.get(f"lora_{idx}", {})
            if not isinstance(slot_data, dict):
                slot_data = {}
            controls.toggle.setChecked(bool(slot_data.get("on", False)))
            name_value = str(slot_data.get("lora", "NONE.safetensors"))
            controls.name.blockSignals(True)
            controls.name.clear()
            controls.name.addItem(name_value)
            controls.name.setCurrentIndex(0)
            controls.name.blockSignals(False)
            controls.name.setEditText(name_value)
            strength_value = float(slot_data.get("strength", 0.0))
            controls.strength.setValue(strength_value)

    def _clear_form(self) -> None:
        self._favorite_checkbox.setChecked(False)
        self._model_type_combo.setCurrentIndex(0)
        for controls in self._slot_controls:
            controls.toggle.setChecked(False)
            controls.name.clear()
            controls.name.setEditText("")
            controls.strength.setValue(0.0)

    def _update_style_from_form(self) -> None:
        if not self._current_style or self._current_style not in self._styles:
            return
        style = dict(self._styles[self._current_style])
        if self._current_style == "off":
            style["favorite"] = False
        else:
            style["favorite"] = self._favorite_checkbox.isChecked()
        style["model_type"] = self._model_type_combo.currentText().strip().lower() or "all"
        for idx, controls in enumerate(self._slot_controls, start=1):
            slot_key = f"lora_{idx}"
            slot_payload = style.get(slot_key)
            if not isinstance(slot_payload, dict):
                slot_payload = {}
            slot_payload["on"] = controls.toggle.isChecked()
            slot_payload["lora"] = controls.name.currentText().strip() or "NONE.safetensors"
            slot_payload["strength"] = controls.strength.value()
            style[slot_key] = slot_payload
        self._styles[self._current_style] = style
        self._refresh_style_list(select=self._current_style, preserve_position=True)

    def _refresh_style_list(self, *, select: str | None = None, preserve_position: bool = False) -> None:
        current_name = select or (self._style_list.currentItem().data(Qt.UserRole) if self._style_list.currentItem() else None)
        self._style_list.blockSignals(True)
        self._style_list.clear()
        for style_name in sorted(self._styles.keys(), key=lambda n: (n != "off", n.lower())):
            display = style_name
            style_data = self._styles.get(style_name, {})
            if style_name == "off":
                display = "off (disable styles)"
            elif style_data.get("favorite"):
                display = "⭐ " + style_name
            item = QListWidgetItem(display)
            item.setData(Qt.UserRole, style_name)
            self._style_list.addItem(item)
        self._style_list.blockSignals(False)
        target = select or current_name
        if target:
            for index in range(self._style_list.count()):
                item = self._style_list.item(index)
                if item.data(Qt.UserRole) == target:
                    self._style_list.setCurrentItem(item)
                    if preserve_position:
                        self._style_list.scrollToItem(item)
                    break
        elif self._style_list.count():
            self._style_list.setCurrentRow(0)

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository) -> None:  # pragma: no cover - UI wiring
        del repository
        try:
            self._styles = load_styles_config() or {}
        except Exception:
            self._styles = {"off": self._default_style_payload()}
        if "off" not in self._styles:
            self._styles["off"] = self._default_style_payload()
        self._refresh_style_list()
        if self._style_list.count():
            self._style_list.setCurrentRow(0)


__all__ = ["LoraStylesView"]
