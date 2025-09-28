"""Activity log view that mirrors updater output inside the GUI."""
from __future__ import annotations

from pathlib import Path
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QLabel, QPushButton, QVBoxLayout, QWidget, QPlainTextEdit, QHBoxLayout


class ActivityLogView(QWidget):
    """Display the updater log and streaming status events."""

    def __init__(self, log_path: Path) -> None:
        super().__init__()
        self._log_path = log_path

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 32, 32, 32)
        layout.setSpacing(16)

        title = QLabel("Activity & Update Log")
        title.setObjectName("MaterialSectionTitle")
        layout.addWidget(title)

        subtitle = QLabel(
            "Track updater progress, download attempts, and other important status messages "
            "emitted by the configurator."
        )
        subtitle.setWordWrap(True)
        layout.addWidget(subtitle)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(360)
        layout.addWidget(self._log_view)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        self._refresh_button = QPushButton("Reload Log")
        self._refresh_button.clicked.connect(self.refresh)  # pragma: no cover - Qt signal
        button_row.addWidget(self._refresh_button, alignment=Qt.AlignLeft)

        self._open_button = QPushButton("Open Log Folder")
        self._open_button.clicked.connect(self._open_log_location)  # pragma: no cover - Qt signal
        button_row.addWidget(self._open_button, alignment=Qt.AlignLeft)

        button_row.addStretch()
        layout.addLayout(button_row)

        self.refresh()

    # ------------------------------------------------------------------
    def refresh(self) -> None:
        """Load the current activity log from disk."""

        if not self._log_path.exists():
            self._log_view.setPlainText("No update activity has been recorded yet.")
            return

        try:
            contents = self._log_path.read_text(encoding="utf-8")
        except OSError as exc:  # pragma: no cover - disk errors rare
            self._log_view.setPlainText(f"Unable to read log: {exc}")
            return

        self._log_view.setPlainText(contents.strip() or "Update log is currently empty.")
        self._log_view.verticalScrollBar().setValue(self._log_view.verticalScrollBar().maximum())

    def append_entry(self, channel: str, message: str) -> None:
        """Append a log entry emitted during this runtime."""

        existing = self._log_view.toPlainText().strip()
        new_line = f"[{channel}] {message.strip()}"
        rendered = f"{existing}\n{new_line}" if existing else new_line
        self._log_view.setPlainText(rendered)
        self._log_view.verticalScrollBar().setValue(self._log_view.verticalScrollBar().maximum())

    def _open_log_location(self) -> None:
        """Open the update log in the system file browser."""

        try:
            self._log_path.parent.mkdir(parents=True, exist_ok=True)
            if not self._log_path.exists():
                self._log_path.touch()
        except OSError:  # pragma: no cover - filesystem errors rare
            return

        QDesktopServices.openUrl(QUrl.fromLocalFile(str(self._log_path.parent)))


__all__ = ["ActivityLogView"]
