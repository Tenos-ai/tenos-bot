"""Workflow override management view."""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Tuple

from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QVBoxLayout,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from workflows import WORKFLOW_OVERRIDE_SLOTS


class CustomWorkflowSettingsView(BaseView):
    """Allow users to assign custom ComfyUI workflows per engine/command."""

    def __init__(self, *, repository: SettingsRepository, app_base_dir: Path) -> None:
        super().__init__()
        self._repository = repository
        self._app_base_dir = app_base_dir
        self._storage_dir = (self._app_base_dir / "user_workflows").resolve()
        self._storage_dir.mkdir(exist_ok=True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        title = QLabel("Workflow Overrides")
        title.setObjectName("MaterialTitle")
        layout.addWidget(title)

        description = QLabel(
            "Upload custom ComfyUI JSON workflows and assign them to specific engines or commands."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self.workflow_list = QListWidget()
        self.workflow_list.currentItemChanged.connect(self._handle_selection_changed)  # pragma: no cover - Qt binding
        layout.addWidget(self.workflow_list)

        detail_layout = QVBoxLayout()
        self.current_path_label = QLabel("Select a workflow slot to view details.")
        self.current_path_label.setObjectName("MaterialCard")
        self.current_path_label.setWordWrap(True)
        detail_layout.addWidget(self.current_path_label)

        button_row = QHBoxLayout()
        button_row.addStretch()
        self.import_button = QPushButton("Import Workflow")
        self.import_button.clicked.connect(self._import_workflow)  # pragma: no cover - Qt binding
        button_row.addWidget(self.import_button)

        self.clear_button = QPushButton("Clear Override")
        self.clear_button.clicked.connect(self._clear_override)  # pragma: no cover - Qt binding
        button_row.addWidget(self.clear_button)

        self.open_button = QPushButton("Open File")
        self.open_button.clicked.connect(self._open_override_file)  # pragma: no cover - Qt binding
        button_row.addWidget(self.open_button)

        detail_layout.addLayout(button_row)
        layout.addLayout(detail_layout)

        self.status_label = QLabel("Custom overrides are optional. Defaults will be used when no override is set.")
        self.status_label.setObjectName("MaterialCard")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.refresh(repository)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _selected_slot(self) -> Tuple[str, str] | None:
        item = self.workflow_list.currentItem()
        if item is None:
            return None
        data = item.data(Qt.UserRole)
        if isinstance(data, tuple) and len(data) == 2:
            return data[0], data[1]
        return None

    def _populate_list(self, overrides: dict[str, dict[str, object]]) -> None:
        self.workflow_list.blockSignals(True)
        self.workflow_list.clear()
        for engine, slots in WORKFLOW_OVERRIDE_SLOTS.items():
            engine_overrides = overrides.get(engine, {}) if isinstance(overrides.get(engine), dict) else {}
            for slot_key, label in slots.items():
                override_path = engine_overrides.get(slot_key)
                status = "Custom" if isinstance(override_path, str) and override_path else "Default"
                item = QListWidgetItem(f"{label} — {status}")
                item.setData(Qt.UserRole, (engine, slot_key))
                if isinstance(override_path, str) and override_path:
                    item.setToolTip(override_path)
                self.workflow_list.addItem(item)
        self.workflow_list.blockSignals(False)
        if self.workflow_list.count():
            self.workflow_list.setCurrentRow(0)
        else:
            self.current_path_label.setText("No workflow slots available.")

    def _handle_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.current_path_label.setText("Select a workflow slot to manage its override.")
            return
        engine, slot = current.data(Qt.UserRole)
        overrides = self._repository.get_custom_workflows()
        path = overrides.get(engine, {}).get(slot) if isinstance(overrides.get(engine), dict) else None
        if isinstance(path, str) and path:
            self.current_path_label.setText(f"Override: {path}")
            self.open_button.setEnabled(True)
            self.clear_button.setEnabled(True)
        else:
            self.current_path_label.setText("Using bundled workflow template.")
            self.open_button.setEnabled(False)
            self.clear_button.setEnabled(False)

    def _import_workflow(self) -> None:  # pragma: no cover - Qt binding
        selection = self._selected_slot()
        if selection is None:
            self._set_status("Select a workflow slot before importing.")
            return
        engine, slot = selection
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select ComfyUI Workflow",
            str(self._storage_dir),
            "Workflow JSON (*.json)",
        )
        if not file_path:
            return

        try:
            source = Path(file_path)
            if not source.exists():
                raise FileNotFoundError("Selected workflow file no longer exists.")
            target_name = f"{engine}_{slot}_{int(time.time())}.json"
            destination = self._storage_dir / target_name
            shutil.copy2(source, destination)
            self._repository.set_custom_workflow(engine, slot, str(destination))
            self._set_status(f"Custom workflow applied to {engine.upper()} · {slot.replace('_', ' ')}.")
            self.refresh(self._repository)
        except Exception as exc:  # pragma: no cover - user feedback only
            self._set_status(f"Failed to import workflow: {exc}")

    def _clear_override(self) -> None:  # pragma: no cover - Qt binding
        selection = self._selected_slot()
        if selection is None:
            self._set_status("Select a workflow slot to clear.")
            return
        engine, slot = selection
        self._repository.set_custom_workflow(engine, slot, None)
        self._set_status(f"Override cleared for {engine.upper()} · {slot.replace('_', ' ')}.")
        self.refresh(self._repository)

    def _open_override_file(self) -> None:  # pragma: no cover - Qt binding
        selection = self._selected_slot()
        if selection is None:
            return
        engine, slot = selection
        overrides = self._repository.get_custom_workflows()
        path = overrides.get(engine, {}).get(slot) if isinstance(overrides.get(engine), dict) else None
        if isinstance(path, str) and path:
            destination = Path(path)
            if destination.exists():
                QDesktopServices.openUrl(QUrl.fromLocalFile(str(destination)))
            else:
                self._set_status("Stored override file could not be found on disk.")

    def _set_status(self, message: str) -> None:
        self.status_label.setText(message)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        overrides = repository.get_custom_workflows()
        self._populate_list(overrides)
        self._set_status("Select a workflow slot to review or customise the override.")


__all__ = ["CustomWorkflowSettingsView"]
