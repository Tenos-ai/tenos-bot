"""System diagnostics view for the Material configurator."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor
from PySide6.QtWidgets import QLabel, QListWidget, QListWidgetItem, QVBoxLayout

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from services.system_diagnostics import DiagnosticsReport


class SystemStatusView(BaseView):
    """Render ComfyUI and workflow health diagnostics."""

    def __init__(self) -> None:
        super().__init__()

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("System Health Snapshot")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        self.summary_label = QLabel("Collecting diagnostics…")
        self.summary_label.setObjectName("MaterialCard")
        self.summary_label.setWordWrap(True)
        layout.addWidget(self.summary_label)

        self.issue_list = QListWidget()
        self.issue_list.setObjectName("MaterialCardList")
        layout.addWidget(self.issue_list)

    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        del repository

    def show_loading(self) -> None:
        self.summary_label.setText("Collecting diagnostics…")
        self.issue_list.clear()

    def show_report(self, report: DiagnosticsReport) -> None:
        summary_lines = [
            f"ComfyUI connected: {'Yes' if report.comfy_connected else 'No'}",
            f"Qwen ready: {'Yes' if report.qwen_ready else 'No'}",
            f"Curated Qwen workflows: {report.qwen_workflow_count}",
            f"Style presets available: {report.style_count}",
        ]
        self.summary_label.setText("\n".join(summary_lines))

        self.issue_list.clear()
        if not report.issues:
            ok_item = QListWidgetItem("All systems operational")
            ok_item.setForeground(QColor("#34D399"))
            self.issue_list.addItem(ok_item)
            return

        severity_colors = {
            "ok": QColor("#38BDF8"),
            "info": QColor("#93C5FD"),
            "warning": QColor("#FBBF24"),
            "error": QColor("#F87171"),
        }
        for issue in report.issues:
            text = f"{issue.label}: {issue.message}"
            if issue.detail:
                text += f" — {issue.detail}"
            item = QListWidgetItem(text)
            item.setForeground(severity_colors.get(issue.severity, QColor("#E2E8F0")))
            self.issue_list.addItem(item)


__all__ = ["SystemStatusView"]
