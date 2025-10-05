"""Maintenance utilities surfaced from the legacy configurator."""
from __future__ import annotations

import subprocess
from pathlib import Path

from PySide6.QtCore import QObject, QThread, Signal, Slot
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QHBoxLayout,
    QPlainTextEdit,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from model_scanner import update_models_list, update_checkpoints_list, scan_clip_files

CUSTOM_NODE_REPOS = [
    "https://github.com/rgthree/rgthree-comfy.git",
    "https://github.com/ssitu/ComfyUI_UltimateSDUpscale.git",
    "https://github.com/jamesWalker55/comfyui-various.git",
    "https://github.com/city96/ComfyUI-GGUF.git",
    "https://github.com/tsogzark/ComfyUI-load-image-from-url.git",
    "https://github.com/BobsBlazed/Bobs_Latent_Optimizer.git",
    "https://github.com/Tenos-ai/Tenos-Resize-to-1-M-Pixels.git",
]


class ToolsWorker(QObject):
    """Background worker that performs maintenance tasks without freezing the UI."""

    log_emitted = Signal(str)
    status_changed = Signal(str)
    finished = Signal()

    def __init__(self, job: str, *, custom_nodes_dir: Path | None = None) -> None:
        super().__init__()
        self._job = job
        self._custom_nodes_dir = custom_nodes_dir

    @Slot()
    def run(self) -> None:
        try:
            if self._job == "install":
                self._run_install()
            elif self._job == "flux":
                self._run_flux_scan()
            elif self._job == "checkpoints":
                self._run_checkpoint_scan()
            elif self._job == "clips":
                self._run_clip_scan()
            elif self._job == "all":
                self._run_all_scans()
        finally:
            self.finished.emit()

    # ------------------------------------------------------------------
    # Scan helpers
    # ------------------------------------------------------------------
    def _run_install(self) -> None:
        target_dir = self._custom_nodes_dir
        if target_dir is None:
            self.status_changed.emit("Custom nodes directory not configured.")
            self.log_emitted.emit("⚠️ Custom nodes directory not configured. Set it in Main Config first.")
            return

        try:
            target_dir.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - filesystem safeguards
            self.status_changed.emit("Unable to prepare custom nodes directory.")
            self.log_emitted.emit(f"❌ Failed to create directory {target_dir}: {exc}")
            return

        self.status_changed.emit("Updating custom nodes…")
        for repo in CUSTOM_NODE_REPOS:
            name = repo.rstrip("/").split("/")[-1]
            if name.endswith(".git"):
                name = name[:-4]
            destination = target_dir / name
            try:
                if destination.exists():
                    command = ["git", "-C", str(destination), "pull", "--ff-only"]
                    action = "Pull"
                else:
                    command = ["git", "clone", repo, str(destination)]
                    action = "Clone"
                self.log_emitted.emit(f"{action} {repo}")
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode != 0:
                    stderr = result.stderr.strip()
                    stdout = result.stdout.strip()
                    details = stderr or stdout or "git command failed"
                    raise RuntimeError(details)
            except Exception as exc:  # pragma: no cover - subprocess safeguards
                self.log_emitted.emit(f"❌ {repo}: {exc}")
            else:
                self.log_emitted.emit(f"✅ {repo}")

        self.status_changed.emit("Custom nodes check complete. Review log for details.")

    def _scan_flux(self) -> bool:
        self.status_changed.emit("Scanning Flux models…")
        try:
            update_models_list("config.json", "modelslist.json")
        except Exception as exc:  # pragma: no cover - subprocess safeguards
            self.log_emitted.emit(f"❌ Flux scan failed: {exc}")
            return False
        else:
            self.log_emitted.emit("Flux models list updated.")
            return True

    def _scan_checkpoints(self) -> bool:
        self.status_changed.emit("Scanning checkpoints…")
        try:
            update_checkpoints_list("config.json", "checkpointslist.json")
        except Exception as exc:  # pragma: no cover - subprocess safeguards
            self.log_emitted.emit(f"❌ Checkpoint scan failed: {exc}")
            return False
        else:
            self.log_emitted.emit("Checkpoint list updated.")
            return True

    def _scan_clips(self) -> bool:
        self.status_changed.emit("Scanning CLIP models…")
        try:
            scan_clip_files("config.json", "cliplist.json")
        except Exception as exc:  # pragma: no cover - subprocess safeguards
            self.log_emitted.emit(f"❌ CLIP scan failed: {exc}")
            return False
        else:
            self.log_emitted.emit("CLIP list updated.")
            return True

    def _run_flux_scan(self) -> None:
        success = self._scan_flux()
        if success:
            self.status_changed.emit("Flux scan complete.")
        else:
            self.status_changed.emit("Flux scan failed. Review log.")

    def _run_checkpoint_scan(self) -> None:
        success = self._scan_checkpoints()
        if success:
            self.status_changed.emit("Checkpoint scan complete.")
        else:
            self.status_changed.emit("Checkpoint scan failed. Review log.")

    def _run_clip_scan(self) -> None:
        success = self._scan_clips()
        if success:
            self.status_changed.emit("CLIP scan complete.")
        else:
            self.status_changed.emit("CLIP scan failed. Review log.")

    def _run_all_scans(self) -> None:
        flux_ok = self._scan_flux()
        checkpoints_ok = self._scan_checkpoints()
        clips_ok = self._scan_clips()

        if flux_ok and checkpoints_ok and clips_ok:
            self.log_emitted.emit("✅ All scans completed successfully.")
            self.status_changed.emit("All scans complete.")
        else:
            self.log_emitted.emit("⚠️ All scans finished with errors. Review log entries above.")
            self.status_changed.emit("All scans finished with errors. Review log.")


class ToolsView(BaseView):
    """Expose maintenance helpers for admins."""

    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__()
        self._repository = repository
        self._active_thread: QThread | None = None

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("Tools")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        description = QLabel(
            "Install required custom nodes and rescan resource catalogues used by the bot."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        button_column = QVBoxLayout()
        button_column.setSpacing(12)
        root_layout.addLayout(button_column)

        self._install_button = QPushButton("Install / Update Custom Nodes")
        self._install_button.clicked.connect(self._install_custom_nodes)  # pragma: no cover - Qt binding
        button_column.addWidget(self._install_button)

        self._flux_button = QPushButton("Rescan Flux Models")
        self._flux_button.clicked.connect(self._rescan_flux_models)  # pragma: no cover - Qt binding
        button_column.addWidget(self._flux_button)

        self._checkpoint_button = QPushButton("Rescan Base Checkpoints")
        self._checkpoint_button.clicked.connect(self._rescan_checkpoints)  # pragma: no cover - Qt binding
        button_column.addWidget(self._checkpoint_button)

        self._clip_button = QPushButton("Rescan CLIP Models")
        self._clip_button.clicked.connect(self._rescan_clips)  # pragma: no cover - Qt binding
        button_column.addWidget(self._clip_button)

        combo_row = QHBoxLayout()
        combo_row.addStretch()
        self._combo_button = QPushButton("Run All Scans")
        self._combo_button.clicked.connect(self._run_all_scans)  # pragma: no cover - Qt binding
        combo_row.addWidget(self._combo_button)
        root_layout.addLayout(combo_row)

        self._log = QPlainTextEdit()
        self._log.setReadOnly(True)
        self._log.setMinimumHeight(240)
        root_layout.addWidget(self._log)

        self._status_label = QLabel("Ready.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

    # ------------------------------------------------------------------
    # Helper methods
    # ------------------------------------------------------------------
    def _append_log(self, message: str) -> None:
        self._log.appendPlainText(message)
        self._log.moveCursor(self._log.textCursor().End)

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _set_buttons_enabled(self, enabled: bool) -> None:
        for button in (
            self._install_button,
            self._flux_button,
            self._checkpoint_button,
            self._clip_button,
            self._combo_button,
        ):
            button.setEnabled(enabled)

    def _start_worker(self, job: str, *, custom_nodes_dir: Path | None = None) -> None:
        if self._active_thread is not None and self._active_thread.isRunning():
            QMessageBox.information(
                self,
                "Task Running",
                "Please wait for the current maintenance task to finish before starting a new one.",
            )
            return

        worker = ToolsWorker(job, custom_nodes_dir=custom_nodes_dir)
        thread = QThread(self)
        worker.moveToThread(thread)
        worker.log_emitted.connect(self._append_log)
        worker.status_changed.connect(self._set_status)
        worker.finished.connect(lambda: self._on_worker_finished(thread, worker))
        thread.started.connect(worker.run)

        self._active_thread = thread
        self._set_buttons_enabled(False)
        thread.start()

    def _on_worker_finished(self, thread: QThread, worker: ToolsWorker) -> None:
        thread.quit()
        thread.wait()
        worker.deleteLater()
        thread.deleteLater()
        self._active_thread = None
        self._set_buttons_enabled(True)

    def _custom_nodes_path(self) -> Path | None:
        config = self._repository.config or {}
        nodes_config = config.get("NODES", {})
        if not isinstance(nodes_config, dict):
            return None
        path_value = nodes_config.get("CUSTOM_NODES")
        if not isinstance(path_value, str) or not path_value.strip():
            return None
        return Path(path_value.strip()).expanduser()

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _install_custom_nodes(self) -> None:  # pragma: no cover - Qt binding
        target_dir = self._custom_nodes_path()
        if target_dir is None:
            QMessageBox.warning(
                self,
                "Path Required",
                "Set the Custom Nodes directory in Main Config before installing.",
            )
            return
        self._start_worker("install", custom_nodes_dir=target_dir)

    def _rescan_flux_models(self) -> None:  # pragma: no cover - Qt binding
        self._start_worker("flux")

    def _rescan_checkpoints(self) -> None:  # pragma: no cover - Qt binding
        self._start_worker("checkpoints")

    def _rescan_clips(self) -> None:  # pragma: no cover - Qt binding
        self._start_worker("clips")

    def _run_all_scans(self) -> None:  # pragma: no cover - Qt binding
        self._start_worker("all")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        self._repository = repository
        self._set_status("Ready.")


__all__ = ["ToolsView"]
