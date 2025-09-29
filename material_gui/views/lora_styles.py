"""LoRA style preset editor for the Material configurator."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import Qt, QTimer
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
    QSizePolicy,
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
        self._loading = False
        self._known_loras: set[str] = {"NONE.safetensors"}

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

        self._status_label = QLabel("Select a style to edit its LoRA slots. Changes save automatically.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._persist_styles)

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
        header_layout.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.addLayout(header_layout)

        self._favorite_checkbox = QCheckBox("Mark as favourite in menus")
        self._favorite_checkbox.toggled.connect(self._handle_form_changed)  # pragma: no cover - Qt binding
        header_layout.addRow("Favourite", self._favorite_checkbox)

        self._model_type_combo = QComboBox()
        self._model_type_combo.addItems(["all", "flux", "sdxl", "qwen"])
        self._model_type_combo.currentIndexChanged.connect(self._handle_form_changed)  # pragma: no cover - Qt binding
        header_layout.addRow("Model Family", self._model_type_combo)

        slots_group = QGroupBox("LoRA Slots")
        slots_form = QFormLayout(slots_group)
        slots_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        slots_form.setFieldGrowthPolicy(QFormLayout.AllNonFixedFieldsGrow)
        layout.addWidget(slots_group)

        self._slot_controls.clear()
        for index in range(1, 6):
            toggle = QCheckBox("Enabled")
            name_combo = QComboBox()
            name_combo.setEditable(False)
            name_combo.setInsertPolicy(QComboBox.NoInsert)
            name_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
            name_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
            strength = QDoubleSpinBox()
            strength.setRange(0.0, 2.0)
            strength.setSingleStep(0.05)
            strength.setDecimals(2)

            toggle.toggled.connect(self._handle_form_changed)  # pragma: no cover - Qt binding
            name_combo.currentIndexChanged.connect(self._handle_lora_selection_changed)  # pragma: no cover - Qt binding
            strength.valueChanged.connect(self._handle_form_changed)  # pragma: no cover - Qt binding

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
        self._rebuild_known_loras()
        self._repopulate_lora_combos()
        self._refresh_style_list(select=style_name)
        self._set_status(f"Style '{style_name}' created. Configure the slots; changes save automatically.")
        self._schedule_save()

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
        self._rebuild_known_loras()
        self._repopulate_lora_combos()
        self._refresh_style_list(select=new_name)
        self._set_status(f"Duplicated '{base_name}' → '{new_name}'.")
        self._schedule_save()

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
        self._rebuild_known_loras()
        self._repopulate_lora_combos()
        self._refresh_style_list(select=candidate)
        self._set_status(f"Renamed style to '{candidate}'.")
        self._schedule_save()

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
        self._rebuild_known_loras()
        self._repopulate_lora_combos()
        self._refresh_style_list()
        self._clear_form()
        self._set_status("Style removed.")
        self._schedule_save()

    def _persist_styles(self) -> None:
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
        previous = self._current_style
        self._update_style_from_form()
        if previous and not self._loading:
            self._schedule_save()
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
        self._set_status(f"Editing '{style_name}'. Changes save automatically.")

    def _populate_form(self, data: dict) -> None:
        self._loading = True
        self._favorite_checkbox.setChecked(bool(data.get("favorite", False)))
        model_type = str(data.get("model_type", "all")).lower()
        index = self._model_type_combo.findText(model_type)
        if index == -1:
            self._model_type_combo.addItem(model_type)
            index = self._model_type_combo.findText(model_type)
        self._model_type_combo.setCurrentIndex(index if index != -1 else 0)

        self._rebuild_known_loras()
        selections: list[str] = []
        for idx, controls in enumerate(self._slot_controls, start=1):
            slot_data = data.get(f"lora_{idx}", {})
            if not isinstance(slot_data, dict):
                slot_data = {}
            controls.toggle.blockSignals(True)
            controls.toggle.setChecked(bool(slot_data.get("on", False)))
            controls.toggle.blockSignals(False)

            name_value = str(slot_data.get("lora", "NONE.safetensors")) or "NONE.safetensors"
            selections.append(name_value)

            strength_value = float(slot_data.get("strength", 0.0))
            controls.strength.blockSignals(True)
            controls.strength.setValue(strength_value)
            controls.strength.blockSignals(False)
        self._repopulate_lora_combos(selections)
        self._loading = False

    def _clear_form(self) -> None:
        self._loading = True
        self._favorite_checkbox.setChecked(False)
        self._model_type_combo.setCurrentIndex(0)
        for controls in self._slot_controls:
            controls.toggle.blockSignals(True)
            controls.toggle.setChecked(False)
            controls.toggle.blockSignals(False)
            controls.name.blockSignals(True)
            controls.name.clear()
            controls.name.blockSignals(False)
            controls.strength.blockSignals(True)
            controls.strength.setValue(0.0)
            controls.strength.blockSignals(False)
        self._repopulate_lora_combos(["NONE.safetensors"] * len(self._slot_controls))
        self._loading = False

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
            selected_value = controls.name.currentData()
            if selected_value in (None, "", "__custom__"):
                selected_value = "NONE.safetensors"
            slot_payload["lora"] = str(selected_value)
            slot_payload["strength"] = controls.strength.value()
            style[slot_key] = slot_payload
        self._styles[self._current_style] = style
        self._rebuild_known_loras()
        self._repopulate_lora_combos()
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

    def _handle_form_changed(self) -> None:  # pragma: no cover - Qt binding
        if self._loading:
            return
        self._update_style_from_form()
        self._schedule_save()

    def _schedule_save(self) -> None:
        if self._loading:
            return
        self._status_label.setText("Saving styles…")
        self._save_timer.start()

    def _handle_lora_selection_changed(self) -> None:  # pragma: no cover - Qt binding
        if self._loading:
            return
        combo = self.sender()
        if not isinstance(combo, QComboBox):
            return
        data = combo.currentData()
        if data == "__custom__":
            new_value = self._prompt_custom_lora_name()
            if new_value:
                self._known_loras.add(new_value)
                selections: list[str] = []
                for controls in self._slot_controls:
                    current = controls.name.currentData()
                    if controls.name is combo:
                        selections.append(new_value)
                    else:
                        if current in (None, "", "__custom__"):
                            current = "NONE.safetensors"
                        selections.append(str(current))
                self._repopulate_lora_combos(selections)
            else:
                self._repopulate_lora_combos()
            self._handle_form_changed()
            return
        self._handle_form_changed()

    def _prompt_custom_lora_name(self) -> str | None:
        name, ok = QInputDialog.getText(self, "Custom LoRA", "LoRA filename:")
        if not ok:
            return None
        candidate = name.strip()
        if not candidate:
            return None
        return candidate

    def _rebuild_known_loras(self) -> None:
        names = {"NONE.safetensors"}
        for style in self._styles.values():
            if not isinstance(style, dict):
                continue
            for idx in range(1, 6):
                slot = style.get(f"lora_{idx}")
                if not isinstance(slot, dict):
                    continue
                value = slot.get("lora")
                if isinstance(value, str) and value.strip():
                    names.add(value.strip())
        self._known_loras = names

    def _base_lora_options(self) -> list[tuple[str, str]]:
        extras = sorted(
            (name for name in self._known_loras if name and name.lower() != "none.safetensors"),
            key=str.lower,
        )
        options: list[tuple[str, str]] = [("None (disable slot)", "NONE.safetensors")]
        options.extend((name, name) for name in extras)
        return options

    def _repopulate_lora_combos(self, selections: list[str | None] | None = None) -> None:
        if not self._slot_controls:
            return
        base_options = self._base_lora_options()
        base_values = [value for _, value in base_options]
        if selections is None:
            selections = []
            for controls in self._slot_controls:
                current = controls.name.currentData()
                if current in (None, "", "__custom__"):
                    current = "NONE.safetensors"
                selections.append(str(current))
        self._loading = True
        try:
            for controls, selected in zip(self._slot_controls, selections):
                choice = (selected or "NONE.safetensors").strip()
                combo = controls.name
                combo.blockSignals(True)
                combo.clear()
                for label, value in base_options:
                    combo.addItem(label, value)
                if choice not in base_values:
                    insert_at = 1 if len(base_options) else 0
                    combo.insertItem(insert_at, choice, choice)
                combo.addItem("Add custom LoRA…", "__custom__")
                index = combo.findData(choice)
                if index == -1:
                    index = combo.findData("NONE.safetensors")
                combo.setCurrentIndex(index if index != -1 else 0)
                combo.blockSignals(False)
        finally:
            self._loading = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository) -> None:  # pragma: no cover - UI wiring
        del repository
        self._loading = True
        try:
            self._styles = load_styles_config() or {}
        except Exception:
            self._styles = {"off": self._default_style_payload()}
        if "off" not in self._styles:
            self._styles["off"] = self._default_style_payload()
        self._rebuild_known_loras()
        self._refresh_style_list()
        if self._style_list.count():
            self._style_list.setCurrentRow(0)
        self._loading = False


__all__ = ["LoraStylesView"]
