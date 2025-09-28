"""Workflow management hub combining overrides and curated libraries."""
from __future__ import annotations

from pathlib import Path
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
    QTabWidget,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from material_gui.views.custom_workflows import CustomWorkflowSettingsView
from services.workflow_library_service import WorkflowLibraryService
from workflows import WorkflowDescriptor, WorkflowGroup


class WorkflowsView(BaseView):
    """Display curated workflows by engine and manage override slots."""

    def __init__(
        self,
        *,
        service: WorkflowLibraryService,
        repository: SettingsRepository,
        app_base_dir: Path,
        queue_callback: Callable[[str], None],
        export_callback: Callable[[str], None],
        export_all_callback: Callable[[str | None], None],
    ) -> None:
        super().__init__()
        self._service = service
        self._repository = repository
        self._app_base_dir = app_base_dir
        self._queue_callback = queue_callback
        self._export_callback = export_callback
        self._export_all_callback = export_all_callback
        self._library_tabs: dict[str, _WorkflowLibraryTab] = {}

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("Workflow Studio")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        description = QLabel(
            "Browse curated ComfyUI templates across every supported engine,"
            " or assign custom overrides for the Tenos.ai slash commands."
        )
        description.setWordWrap(True)
        layout.addWidget(description)

        self._section_tabs = QTabWidget()
        layout.addWidget(self._section_tabs, stretch=1)

        # -- Library tab -------------------------------------------------
        library_container = QWidget()
        library_layout = QVBoxLayout(library_container)
        library_layout.setContentsMargins(0, 0, 0, 0)
        library_layout.setSpacing(12)

        self._group_description = QLabel()
        self._group_description.setWordWrap(True)
        self._group_description.setObjectName("MaterialCard")
        library_layout.addWidget(self._group_description)

        self._library_tab_widget = QTabWidget()
        library_layout.addWidget(self._library_tab_widget, stretch=1)

        for group in self._service.list_groups():
            tab = _WorkflowLibraryTab(
                group=group,
                service=self._service,
                status_callback=self.set_status,
                queue_callback=lambda slug, g=group.key: self._handle_queue_request(g, slug),
                export_callback=lambda slug, g=group.key: self._handle_export_request(g, slug),
                export_all_callback=lambda g=group.key: self._handle_export_group_request(g),
            )
            self._library_tabs[group.key] = tab
            self._library_tab_widget.addTab(tab, group.title)

        self._library_tab_widget.currentChanged.connect(self._handle_group_changed)  # pragma: no cover - Qt binding

        global_actions = QHBoxLayout()
        global_actions.addStretch()
        export_all_button = QPushButton("Export Entire Library")
        export_all_button.clicked.connect(lambda: self._handle_export_group_request(None))  # pragma: no cover - Qt binding
        global_actions.addWidget(export_all_button)
        library_layout.addLayout(global_actions)
        self._section_tabs.addTab(library_container, "Workflow Library")

        # -- Overrides tab -----------------------------------------------
        overrides_view = CustomWorkflowSettingsView(repository=self._repository, app_base_dir=self._app_base_dir)
        self._overrides_view = overrides_view
        self._section_tabs.addTab(overrides_view, "Workflow Overrides")

        self._status_label = QLabel("Select a workflow to preview.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self._handle_group_changed(self._library_tab_widget.currentIndex())

    # ------------------------------------------------------------------
    # Status utilities
    # ------------------------------------------------------------------
    def set_status(self, message: str) -> None:  # type: ignore[override]
        self._status_label.setText(message)

    # ------------------------------------------------------------------
    # Action handlers
    # ------------------------------------------------------------------
    def _handle_group_changed(self, index: int) -> None:  # pragma: no cover - Qt binding
        groups = self._service.list_groups()
        group = groups[index] if 0 <= index < len(groups) else None
        if group is None:
            self._group_description.setText("Curated workflows will appear here once available.")
        else:
            self._group_description.setText(group.description)

    def _handle_queue_request(self, group_key: str, slug: str | None) -> None:
        if not slug:
            self.set_status("Select a workflow to queue.")
            return
        self.set_status(f"Queueing {group_key.replace('_', ' ').title()} workflow…")
        self._queue_callback(slug)

    def _handle_export_request(self, group_key: str, slug: str | None) -> None:
        if not slug:
            self.set_status("Select a workflow to export.")
            return
        self.set_status(f"Preparing {group_key.replace('_', ' ').title()} export…")
        self._export_callback(slug)

    def _handle_export_group_request(self, group_key: str | None) -> None:
        if group_key:
            label = group_key.replace("_", " ").title()
            self.set_status(f"Exporting {label} library…")
        else:
            self.set_status("Exporting full workflow library…")
        self._export_all_callback(group_key)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository | None) -> None:  # pragma: no cover - UI wiring
        source_repository = repository or self._repository
        if source_repository is not None:
            self._overrides_view.refresh(source_repository)
        for tab in self._library_tabs.values():
            tab.refresh()
        self.set_status("Select a workflow to preview.")


class _WorkflowLibraryTab(QWidget):
    """Isolated workflow browser for a specific engine group."""

    def __init__(
        self,
        *,
        group: WorkflowGroup,
        service: WorkflowLibraryService,
        status_callback: Callable[[str], None],
        queue_callback: Callable[[str | None], None],
        export_callback: Callable[[str | None], None],
        export_all_callback: Callable[[], None],
    ) -> None:
        super().__init__()
        self._group = group
        self._service = service
        self._status_callback = status_callback
        self._queue_callback = queue_callback
        self._export_callback = export_callback
        self._export_all_callback = export_all_callback
        self._descriptors: tuple[WorkflowDescriptor, ...] = ()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText(f"Search {group.title} workflows…")
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
        self.queue_button.clicked.connect(self._queue_workflow)  # pragma: no cover - Qt binding
        button_row.addWidget(self.queue_button)

        self.export_button = QPushButton("Export Selected")
        self.export_button.clicked.connect(self._export_selected)  # pragma: no cover - Qt binding
        button_row.addWidget(self.export_button)

        self.export_all_button = QPushButton("Export Group")
        self.export_all_button.clicked.connect(self._export_all)  # pragma: no cover - Qt binding
        button_row.addWidget(self.export_all_button)

        layout.addLayout(button_row)

        self.status_label = QLabel("Select a workflow to begin.")
        self.status_label.setObjectName("MaterialCard")
        self.status_label.setWordWrap(True)
        layout.addWidget(self.status_label)

        self.refresh()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def refresh(self) -> None:
        filter_text = self.search_box.text() if hasattr(self, "search_box") else ""
        self._descriptors = tuple(self._service.search_workflows(filter_text, group_key=self._group.key))

        self.workflow_list.blockSignals(True)
        self.workflow_list.clear()
        for descriptor in self._descriptors:
            item = QListWidgetItem(descriptor.title)
            item.setData(Qt.UserRole, descriptor.slug)
            item.setToolTip(descriptor.description)
            self.workflow_list.addItem(item)
        self.workflow_list.blockSignals(False)

        if self._descriptors:
            self.workflow_list.setCurrentRow(0)
            self._update_description(self._descriptors[0])
            summary = (
                f"{len(self._descriptors)} workflows match '{filter_text}'"
                if filter_text
                else f"{len(self._descriptors)} workflows available"
            )
        else:
            self.description_box.setPlainText("No workflows available.")
            summary = "No workflows match your filter." if filter_text else "No workflows available."

        self.status_label.setText(summary)

    def _current_slug(self) -> str | None:
        item = self.workflow_list.currentItem()
        return item.data(Qt.UserRole) if item is not None else None

    def _handle_selection_changed(self, current: QListWidgetItem | None, _previous: QListWidgetItem | None) -> None:
        if current is None:
            self.description_box.clear()
            return

        slug = current.data(Qt.UserRole)
        descriptor = next((wf for wf in self._descriptors if wf.slug == slug), None)
        self._update_description(descriptor)

    def _handle_search(self, _text: str) -> None:  # pragma: no cover - Qt binding
        self.refresh()

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

    def _queue_workflow(self) -> None:
        slug = self._current_slug()
        if not slug:
            self._status_callback("Select a workflow to queue.")
            return
        self._status_callback(f"Queueing {self._group.title} workflow…")
        self._queue_callback(slug)

    def _export_selected(self) -> None:
        slug = self._current_slug()
        if not slug:
            self._status_callback("Select a workflow to export.")
            return
        self._status_callback(f"Exporting {self._group.title} workflow…")
        self._export_callback(slug)

    def _export_all(self) -> None:
        self._status_callback(f"Exporting {self._group.title} library…")
        self._export_all_callback()


__all__ = ["WorkflowsView"]
