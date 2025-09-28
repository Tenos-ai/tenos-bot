"""Curated Qwen workflow explorer for the Material configurator."""
from __future__ import annotations

from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTextEdit,
    QVBoxLayout,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from services.qwen_workflow_service import QwenWorkflowService
from workflows.qwen_image_library import WorkflowDescriptor


class WorkflowsView(BaseView):
    """Display and action curated Qwen Image workflows."""

    def __init__(
        self,
        *,
        service: QwenWorkflowService,
        queue_callback: Callable[[str], None],
        export_callback: Callable[[str], None],
        export_all_callback: Callable[[], None],
    ) -> None:
        super().__init__()
        self._service = service
        self._queue_callback = queue_callback
        self._export_callback = export_callback
        self._export_all_callback = export_all_callback

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("Qwen Workflow Library")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search workflows…")
        self.search_box.textChanged.connect(self._handle_search)  # pragma: no cover - Qt binding
        layout.addWidget(self.search_box)

        self.description_box = QTextEdit()
        self.description_box.setObjectName("MaterialCard")
        self.description_box.setReadOnly(True)
        self.description_box.setFixedHeight(160)

        self.workflow_list = QListWidget()
        self.workflow_list.setSelectionMode(QAbstractItemView.SingleSelection)
        self.workflow_list.currentItemChanged.connect(self._handle_selection_changed)  # pragma: no cover - Qt binding

        list_container = QHBoxLayout()
        list_container.addWidget(self.workflow_list, 2)
        list_container.addWidget(self.description_box, 3)
        layout.addLayout(list_container)

        button_row = QHBoxLayout()
        button_row.addStretch()

        self.queue_button = QPushButton("Queue in ComfyUI")
        self.queue_button.clicked.connect(self._handle_queue)  # pragma: no cover - Qt binding
        button_row.addWidget(self.queue_button)

        self.export_button = QPushButton("Export Selected")
        self.export_button.clicked.connect(self._handle_export)  # pragma: no cover - Qt binding
        button_row.addWidget(self.export_button)

        self.export_all_button = QPushButton("Export All")
        self.export_all_button.clicked.connect(self._export_all_callback)  # pragma: no cover - Qt binding
        button_row.addWidget(self.export_all_button)

        layout.addLayout(button_row)

        self.status_label = QLabel("Select a workflow to begin.")
        self.status_label.setObjectName("MaterialCard")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.refresh(None)

    def refresh(self, repository: SettingsRepository | None) -> None:  # pragma: no cover - UI wiring
        del repository
        self._populate_workflows()

    def set_status(self, message: str) -> None:
        self.status_label.setText(message)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _populate_workflows(self) -> None:
        filter_text = self.search_box.text() if hasattr(self, "search_box") else ""

        descriptors = self._service.search_workflows(filter_text)

        self.workflow_list.blockSignals(True)
        self.workflow_list.clear()

        for descriptor in descriptors:
            item = QListWidgetItem(descriptor.title)
            item.setData(Qt.UserRole, descriptor.slug)
            item.setToolTip(descriptor.description)
            self.workflow_list.addItem(item)

        self.workflow_list.blockSignals(False)
        if descriptors:
            self.workflow_list.setCurrentRow(0)
            self._update_description(descriptors[0])
            summary = (
                f"{len(descriptors)} workflows match '{filter_text}'"
                if filter_text
                else f"{len(descriptors)} workflows available"
            )
        else:
            self.description_box.setPlainText("No workflows available.")
            summary = "No workflows match your filter." if filter_text else "No workflows available."

        self.status_label.setText(summary)

    def _handle_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.description_box.clear()
            return

        slug = current.data(Qt.UserRole)
        descriptor = self._service.get_workflow(slug)
        self._update_description(descriptor)

    def _handle_queue(self) -> None:
        item = self.workflow_list.currentItem()
        if not item:
            self.set_status("Select a workflow to queue.")
            return
        slug = item.data(Qt.UserRole)
        self._queue_callback(slug)

    def _handle_export(self) -> None:
        item = self.workflow_list.currentItem()
        if not item:
            self.set_status("Select a workflow to export.")
            return
        slug = item.data(Qt.UserRole)
        self._export_callback(slug)

    def _handle_search(self, _text: str) -> None:  # pragma: no cover - Qt binding
        self._populate_workflows()

    def _update_description(self, descriptor: WorkflowDescriptor | None) -> None:
        if descriptor is None:
            self.description_box.clear()
            return

        lines = [descriptor.description]
        if descriptor.use_cases:
            lines.append("")
            lines.append("Use cases:")
            for use_case in descriptor.use_cases:
                lines.append(f"• {use_case}")
        if descriptor.documentation_url:
            lines.append("")
            lines.append(f"Docs: {descriptor.documentation_url}")

        self.description_box.setPlainText("\n".join(lines))


__all__ = ["WorkflowsView"]
