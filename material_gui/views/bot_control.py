"""Start/stop controls for the Tenos.ai bot runtime."""
from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtCore import QProcess, QTimer, Signal
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView


class BotControlView(BaseView):
    """Provide lifecycle management and health context for ``main_bot.py``."""

    runtime_state_changed = Signal(bool)

    def __init__(
        self,
        app_base_dir: Path,
        repository: SettingsRepository,
    ) -> None:
        super().__init__()
        self._app_base_dir = app_base_dir
        self._repository = repository
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
            "Launch or stop the Discord bot without leaving the configurator. "
            "Runtime logs and maintenance updates appear below alongside system health summaries."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        self._runtime_card = QLabel()
        self._runtime_card.setObjectName("MaterialCard")
        self._runtime_card.setWordWrap(True)
        root_layout.addWidget(self._runtime_card)

        controls = QHBoxLayout()
        self._toggle_button = QPushButton("Start Bot")
        self._toggle_button.clicked.connect(self._toggle_runtime)  # pragma: no cover - Qt binding
        controls.addWidget(self._toggle_button)
        root_layout.addLayout(controls)

        action_row = QHBoxLayout()
        self._clear_log_button = QPushButton("Clear Console")
        self._clear_log_button.clicked.connect(self._clear_log)  # pragma: no cover - Qt binding
        action_row.addWidget(self._clear_log_button)

        self._copy_log_button = QPushButton("Copy Console")
        self._copy_log_button.clicked.connect(self._copy_log)  # pragma: no cover - Qt binding
        action_row.addWidget(self._copy_log_button)

        action_row.addStretch()
        root_layout.addLayout(action_row)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        self._log_view.setMinimumHeight(280)
        root_layout.addWidget(self._log_view, stretch=1)

        self._status_label = QLabel("Bot idle.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self._render_runtime_card()

    # ------------------------------------------------------------------
    # Lifecycle controls
    # ------------------------------------------------------------------
    def _start_bot(self) -> None:  # pragma: no cover - Qt binding
        if self._process.state() != QProcess.NotRunning:
            self._set_status("Bot is already running.")
            return

        if not self._ensure_output_folder():
            return

        entrypoint = self._locate_entrypoint()
        if entrypoint is None:
            expected = ", ".join(candidate.name for candidate in self._entrypoint_candidates())
            QMessageBox.critical(
                self,
                "Executable Missing",
                f"Could not find a bot entrypoint in {self._app_base_dir}. Looked for: {expected}",
            )
            return

        self._log_view.clear()
        self._append_log("[CONTROL] Launching bot…")
        self._set_status("Launching bot…")
        self._toggle_button.setEnabled(False)
        self._process.setProgram(sys.executable)
        self._process.setArguments([str(entrypoint)])
        self._process.setWorkingDirectory(str(self._app_base_dir))
        self._process.start()
        if not self._process.waitForStarted(3000):
            self._set_status("Failed to start bot process.")
            self._append_log("[ERROR] Bot failed to start within timeout.")
            return
        self._toggle_button.setEnabled(True)
        self._set_status("Bot running.")
        self.runtime_state_changed.emit(True)

    def _stop_bot(self) -> None:  # pragma: no cover - Qt binding
        if self._process.state() == QProcess.NotRunning:
            self._set_status("Bot is not currently running.")
            return
        self._append_log("[CONTROL] Stopping bot…")
        self._set_status("Stopping bot…")
        self._toggle_button.setEnabled(False)
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
        self.append_runtime_log(data.rstrip())

    def _handle_error(self, error: QProcess.ProcessError) -> None:  # pragma: no cover - Qt binding
        self._append_log(f"[ERROR] Process error: {error}")
        self._set_status(f"Process error: {error}")
        self.runtime_state_changed.emit(False)

    def _handle_finished(self, exit_code: int, _status: QProcess.ExitStatus) -> None:  # pragma: no cover - Qt binding
        self._toggle_button.setEnabled(True)
        self._append_log(f"[CONTROL] Bot stopped (exit code {exit_code}).")
        self._set_status(f"Bot stopped (exit code {exit_code}).")
        self.runtime_state_changed.emit(False)

    # ------------------------------------------------------------------
    # External hooks
    # ------------------------------------------------------------------
    def append_runtime_log(self, message: str) -> None:
        if not message:
            return
        for line in message.splitlines():
            trimmed = line.strip("\n")
            if not trimmed:
                continue
            self._append_log(f"[BOT] {trimmed}")

    def append_system_log(self, channel: str, message: str) -> None:
        channel_label = channel.upper() if channel else "INFO"
        self._append_log(f"[{channel_label}] {message}")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _append_log(self, message: str) -> None:
        self._log_view.appendPlainText(message)
        self._log_view.moveCursor(self._log_view.textCursor().End)

    def _clear_log(self) -> None:  # pragma: no cover - Qt binding
        self._log_view.clear()

    def _copy_log(self) -> None:  # pragma: no cover - Qt binding
        clipboard = QGuiApplication.clipboard()
        clipboard.setText(self._log_view.toPlainText())
        self._set_status("Console copied to clipboard.")

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)
        self._render_runtime_card()

    def _render_runtime_card(self) -> None:
        state = "Running" if self._process.state() != QProcess.NotRunning else "Stopped"
        config = self._repository.config or {}
        outputs = config.get("OUTPUTS", {}) if isinstance(config, dict) else {}
        generations = outputs.get("GENERATIONS") if isinstance(outputs, dict) else None
        if isinstance(generations, str) and generations.strip():
            path = Path(generations).expanduser()
            if not path.is_absolute():
                path = (self._app_base_dir / path).resolve()
            output_display = str(path)
        else:
            output_display = "Not configured"
        self._runtime_card.setText(
            "\n".join(
                [
                    f"Runtime state: {state}",
                    f"Output folder: {output_display}",
                ]
            )
        )

        self._toggle_button.setText("Stop Bot" if state == "Running" else "Start Bot")
        self._toggle_button.setEnabled(True)

    def _toggle_runtime(self) -> None:  # pragma: no cover - Qt binding
        if self._process.state() == QProcess.NotRunning:
            self._start_bot()
        else:
            self._stop_bot()

    def _ensure_output_folder(self) -> bool:
        config = self._repository.config or {}
        outputs = config.get("OUTPUTS", {}) if isinstance(config, dict) else {}
        configured_path = outputs.get("GENERATIONS") if isinstance(outputs, dict) else None
        if isinstance(configured_path, str) and configured_path.strip():
            path = Path(configured_path).expanduser()
            if not path.is_absolute():
                path = (self._app_base_dir / path).resolve()
        else:
            QMessageBox.information(
                self,
                "Output Folder Needed",
                "Select where generated images should be saved before starting the bot.",
            )
            directory = QFileDialog.getExistingDirectory(
                self,
                "Select output folder",
                str(self._app_base_dir),
            )
            if not directory:
                self._set_status("Select an output folder from Main Config before starting the bot.")
                return False
            path = Path(directory).expanduser()
            if not path.is_absolute():
                path = path.resolve()
            try:
                path.mkdir(parents=True, exist_ok=True)
            except Exception as exc:
                QMessageBox.critical(self, "Folder Error", f"Unable to prepare output folder: {exc}")
                self._set_status("Unable to prepare output folder.")
                return False
            try:
                self._repository.save_config(
                    {
                        "OUTPUTS": {
                            "GENERATIONS": str(path),
                            "UPSCALES": str(path),
                            "VARIATIONS": str(path),
                        }
                    }
                )
            except Exception as exc:
                QMessageBox.critical(self, "Save Failed", f"Failed to persist output folder: {exc}")
                self._set_status("Failed to save output folder.")
                return False

        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            QMessageBox.critical(self, "Folder Error", f"Unable to prepare output folder: {exc}")
            self._set_status("Unable to prepare output folder.")
            return False

        self._render_runtime_card()
        return True

    def _entrypoint_candidates(self) -> list[Path]:
        return [
            self._app_base_dir / "main_bot.py",
            self._app_base_dir / "main.py",
        ]

    def _locate_entrypoint(self) -> Path | None:
        for candidate in self._entrypoint_candidates():
            if candidate.exists():
                return candidate
        return None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        self._repository = repository
        if self._process.state() == QProcess.NotRunning:
            self._set_status("Bot idle.")
        else:
            self._set_status("Bot running.")

    def start_runtime(self) -> None:
        self._start_bot()

    def stop_runtime(self) -> None:
        self._stop_bot()

    def is_running(self) -> bool:
        return self._process.state() != QProcess.NotRunning


__all__ = ["BotControlView"]
