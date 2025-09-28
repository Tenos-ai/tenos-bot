"""Favorites manager for models, CLIPs, and styles."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, List

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QVBoxLayout,
    QWidget,
)

from material_gui.views.base import BaseView
from settings_manager import load_styles_config

MODELS_PATH = Path("modelslist.json")
CHECKPOINTS_PATH = Path("checkpointslist.json")
CLIP_PATH = Path("cliplist.json")
STYLES_PATH = Path("styles_config.json")


class FavoritesView(BaseView):
    """Restore the legacy configurator favourites editing experience."""

    def __init__(self) -> None:
        super().__init__()
        self._models_data: Dict = {}
        self._checkpoints_data: Dict = {}
        self._clips_data: Dict = {}
        self._styles_data: Dict = {}
        self._loading = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("Favorites")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        description = QLabel(
            "Select favourite models, checkpoints, CLIPs, and style presets. "
            "Favourites float to the top of slash-command menus."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        grid = QHBoxLayout()
        grid.setSpacing(18)
        root_layout.addLayout(grid, stretch=1)

        column_left = QVBoxLayout()
        column_right = QVBoxLayout()
        grid.addLayout(column_left, stretch=1)
        grid.addLayout(column_right, stretch=1)

        self._flux_list = self._build_list_group("Flux Models", column_left)
        self._sdxl_list = self._build_list_group("SDXL Models", column_left)
        self._qwen_list = self._build_list_group("Qwen Models", column_left)

        clip_group = QGroupBox("CLIP Models")
        clip_layout = QHBoxLayout(clip_group)
        clip_layout.setSpacing(12)
        column_right.addWidget(clip_group)
        self._clip_t5_list = QListWidget()
        self._clip_clip_l_list = QListWidget()
        clip_layout.addWidget(self._clip_t5_list)
        clip_layout.addWidget(self._clip_clip_l_list)
        for widget, label in ((self._clip_t5_list, "T5"), (self._clip_clip_l_list, "CLIP-L")):
            widget.setAlternatingRowColors(True)
            widget.setProperty("heading", label)
            widget.itemChanged.connect(self._handle_item_changed)  # pragma: no cover - Qt binding

        styles_group = QGroupBox("Styles")
        styles_layout = QVBoxLayout(styles_group)
        self._styles_list = QListWidget()
        styles_layout.addWidget(self._styles_list)
        self._styles_list.itemChanged.connect(self._handle_item_changed)  # pragma: no cover - Qt binding
        column_right.addWidget(styles_group)

        self._status_label = QLabel("Tick entries to mark them as favourites. Changes save automatically.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self._save_timer = QTimer(self)
        self._save_timer.setSingleShot(True)
        self._save_timer.setInterval(600)
        self._save_timer.timeout.connect(self._persist)

        self.refresh(None)

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def _build_list_group(self, title: str, parent: QVBoxLayout) -> QListWidget:
        group = QGroupBox(title)
        layout = QVBoxLayout(group)
        list_widget = QListWidget()
        list_widget.setAlternatingRowColors(True)
        layout.addWidget(list_widget)
        parent.addWidget(group)
        list_widget.itemChanged.connect(self._handle_item_changed)  # pragma: no cover - Qt binding
        return list_widget

    def _add_checkable_item(self, widget: QListWidget, label: str, data: str, checked: bool) -> None:
        item = QListWidgetItem(label)
        item.setData(Qt.UserRole, data)
        item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
        item.setCheckState(Qt.Checked if checked else Qt.Unchecked)
        widget.addItem(item)

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _handle_item_changed(self, _item: QListWidgetItem) -> None:  # pragma: no cover - Qt binding
        if self._loading:
            return
        self._set_status("Saving favourites…")
        self._save_timer.start()

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _persist(self) -> None:  # pragma: no cover - Qt binding
        try:
            self._collect_models()
            self._collect_checkpoints()
            self._collect_clips()
            self._collect_styles()
            self._set_status("Favorites updated.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status("Unable to save favourites. See details above.")

    def _collect_models(self) -> None:
        if not self._models_data:
            return
        favorites: List[str] = []
        for index in range(self._flux_list.count()):
            item = self._flux_list.item(index)
            if item.checkState() == Qt.Checked:
                favorites.append(str(item.data(Qt.UserRole)))
        self._models_data["favorites"] = favorites
        MODELS_PATH.write_text(json.dumps(self._models_data, indent=2))

    def _collect_checkpoints(self) -> None:
        if not self._checkpoints_data:
            return
        favorites: List[str] = []
        for widget in (self._sdxl_list, self._qwen_list):
            for index in range(widget.count()):
                item = widget.item(index)
                if item.checkState() == Qt.Checked:
                    favorites.append(str(item.data(Qt.UserRole)))
        self._checkpoints_data["favorites"] = favorites
        CHECKPOINTS_PATH.write_text(json.dumps(self._checkpoints_data, indent=2))

    def _collect_clips(self) -> None:
        if not self._clips_data:
            return
        favorites = {"t5": [], "clip_L": []}
        for widget, key in ((self._clip_t5_list, "t5"), (self._clip_clip_l_list, "clip_L")):
            for index in range(widget.count()):
                item = widget.item(index)
                if item.checkState() == Qt.Checked:
                    favorites[key].append(str(item.data(Qt.UserRole)))
        self._clips_data.setdefault("favorites", {})
        self._clips_data["favorites"].update(favorites)
        CLIP_PATH.write_text(json.dumps(self._clips_data, indent=2))

    def _collect_styles(self) -> None:
        if not self._styles_data:
            return
        for index in range(self._styles_list.count()):
            item = self._styles_list.item(index)
            style_name = str(item.data(Qt.UserRole))
            if style_name not in self._styles_data:
                continue
            entry = self._styles_data[style_name]
            if style_name == "off":
                entry["favorite"] = False
                item.setCheckState(Qt.Unchecked)
            else:
                entry["favorite"] = item.checkState() == Qt.Checked
        STYLES_PATH.write_text(json.dumps(self._styles_data, indent=2))

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository) -> None:  # pragma: no cover - UI wiring
        del repository
        self._loading = True
        self._models_data = self._load_json(MODELS_PATH)
        self._checkpoints_data = self._load_json(CHECKPOINTS_PATH)
        self._clips_data = self._load_json(CLIP_PATH)
        try:
            self._styles_data = load_styles_config() or {}
        except Exception:
            self._styles_data = {}

        self._populate_models()
        self._populate_checkpoints()
        self._populate_clips()
        self._populate_styles()
        self._loading = False

    # ------------------------------------------------------------------
    # Population helpers
    # ------------------------------------------------------------------
    def _load_json(self, path: Path) -> Dict:
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except Exception:
            return {}

    def _populate_models(self) -> None:
        self._flux_list.clear()
        favorites = set(self._models_data.get("favorites", []))
        entries: List[str] = []
        for key in ("safetensors", "sft", "gguf"):
            values = self._models_data.get(key, [])
            if isinstance(values, list):
                entries.extend(str(v) for v in values if isinstance(v, str))
        for model in sorted(dict.fromkeys(entries)):
            self._add_checkable_item(self._flux_list, model, model, model in favorites)

    def _populate_checkpoints(self) -> None:
        self._sdxl_list.clear()
        self._qwen_list.clear()
        favorites = set(self._checkpoints_data.get("favorites", []))
        entries: List[str] = []
        if isinstance(self._checkpoints_data.get("checkpoints"), list):
            entries.extend(self._checkpoints_data.get("checkpoints", []))
        else:
            for key, value in self._checkpoints_data.items():
                if key == "favorites":
                    continue
                if isinstance(value, list):
                    entries.extend(value)
        seen = set()
        for entry in sorted(str(item).strip() for item in entries if isinstance(item, str)):
            if not entry or entry in seen:
                continue
            seen.add(entry)
            target = self._qwen_list if "qwen" in entry.lower() else self._sdxl_list
            self._add_checkable_item(target, entry, entry, entry in favorites)

    def _populate_clips(self) -> None:
        self._clip_t5_list.clear()
        self._clip_clip_l_list.clear()
        favorites = self._clips_data.get("favorites", {}) if isinstance(self._clips_data.get("favorites"), dict) else {}
        t5_favs = set(favorites.get("t5", []))
        clip_l_favs = set(favorites.get("clip_L", []))
        for item in sorted(str(v) for v in self._clips_data.get("t5", []) if isinstance(v, str)):
            self._add_checkable_item(self._clip_t5_list, item, item, item in t5_favs)
        for item in sorted(str(v) for v in self._clips_data.get("clip_L", []) if isinstance(v, str)):
            self._add_checkable_item(self._clip_clip_l_list, item, item, item in clip_l_favs)

    def _populate_styles(self) -> None:
        self._styles_list.clear()
        if not isinstance(self._styles_data, dict):
            return
        for style_name in sorted(self._styles_data.keys(), key=lambda n: (n != "off", n.lower())):
            entry = self._styles_data.get(style_name, {})
            favorite = bool(entry.get("favorite")) if isinstance(entry, dict) else False
            item = QListWidgetItem(style_name)
            item.setData(Qt.UserRole, style_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if style_name == "off":
                item.setFlags(item.flags() & ~Qt.ItemIsEnabled)
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked if favorite else Qt.Unchecked)
            self._styles_list.addItem(item)


__all__ = ["FavoritesView"]
