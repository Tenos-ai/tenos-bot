"""Start/stop controls for the Tenos.ai bot runtime."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
)

from material_gui.views.base import BaseView


class BotControlView(BaseView):
    """Provide simple lifecycle management for main_bot.py."""

    def __init__(self, app_base_dir: Path) -> None:
        super().__init__()
        self._app_base_dir = app_base_dir
        self._process = QProcess(self)
        self._process.setProcessChannelMode(QProcess.MergedChannels)
        self._process.readyReadStandardOutput.connect(self._handle_output)  # pragma: no cover - Qt binding
        self._process.errorOccurred.connect(self._handle_error)  # pragma: no cover - Qt binding
        self._process.finished.connect(self._handle_finished)  # pragma: no cover - Qt binding

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("Bot Control")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        description = QLabel(
            "Start or stop the Discord bot without leaving the configurator. "
            "Logs stream in real time below."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        controls = QHBoxLayout()
        self._start_button = QPushButton("Start Bot")
        self._start_button.clicked.connect(self._start_bot)  # pragma: no cover - Qt binding
        self._stop_button = QPushButton("Stop Bot")
        self._stop_button.clicked.connect(self._stop_bot)  # pragma: no cover - Qt binding
        controls.addWidget(self._start_button)
        controls.addWidget(self._stop_button)
        root_layout.addLayout(controls)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(280)
        root_layout.addWidget(self._log_view, stretch=1)

        self._status_label = QLabel("Bot idle.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self._stop_button.setEnabled(False)

    # ------------------------------------------------------------------
    # Lifecycle controls
    # ------------------------------------------------------------------
    def _start_bot(self) -> None:  # pragma: no cover - Qt binding
        if self._process.state() != QProcess.NotRunning:
            self._set_status("Bot is already running.")
            return
        entrypoint = self._app_base_dir / "main_bot.py"
        if not entrypoint.exists():
            QMessageBox.critical(self, "Executable Missing", f"Could not find {entrypoint}.")
            return
        self._log_view.clear()
        self._set_status("Launching bot…")
        self._process.setProgram(sys.executable)
        self._process.setArguments([str(entrypoint)])
        self._process.setWorkingDirectory(str(self._app_base_dir))
        self._process.start()
        if not self._process.waitForStarted(3000):
            self._set_status("Failed to start bot process.")
            return
        self._start_button.setEnabled(False)
        self._stop_button.setEnabled(True)
        self._set_status("Bot running.")

    def _stop_bot(self) -> None:  # pragma: no cover - Qt binding
        if self._process.state() == QProcess.NotRunning:
            self._set_status("Bot is not currently running.")
            return
        self._set_status("Stopping bot…")
        self._process.terminate()
        QTimer.singleShot(5000, self._ensure_killed)  # pragma: no cover - Qt binding

    def _ensure_killed(self) -> None:
        if self._process.state() != QProcess.NotRunning:
            self._process.kill()

    # ------------------------------------------------------------------
    # Signal handlers
    # ------------------------------------------------------------------
    def _handle_output(self) -> None:
        data = self._process.readAllStandardOutput().data().decode("utf-8", errors="replace")
        self._log_view.appendPlainText(data.rstrip())
        self._log_view.moveCursor(self._log_view.textCursor().End)

    def _handle_error(self, error: QProcess.ProcessError) -> None:  # pragma: no cover - Qt binding
        self._set_status(f"Process error: {error}")

    def _handle_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:  # pragma: no cover - Qt binding
        self._start_button.setEnabled(True)
        self._stop_button.setEnabled(False)
        self._set_status(f"Bot stopped (exit code {exit_code}).")

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository) -> None:  # pragma: no cover - UI wiring
        del repository
        if self._process.state() == QProcess.NotRunning:
            self._set_status("Bot idle.")


__all__ = ["BotControlView"]
