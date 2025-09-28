"""Maintenance utilities surfaced from the legacy configurator."""
from __future__ import annotations

import subprocess
from pathlib import Path

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


class ToolsView(BaseView):
    """Expose maintenance helpers for admins."""

    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__()
        self._repository = repository

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

        install_button = QPushButton("Install / Update Custom Nodes")
        install_button.clicked.connect(self._install_custom_nodes)  # pragma: no cover - Qt binding
        button_column.addWidget(install_button)

        flux_button = QPushButton("Rescan Flux Models")
        flux_button.clicked.connect(self._rescan_flux_models)  # pragma: no cover - Qt binding
        button_column.addWidget(flux_button)

        sdxl_button = QPushButton("Rescan Checkpoints (SDXL/Qwen)")
        sdxl_button.clicked.connect(self._rescan_checkpoints)  # pragma: no cover - Qt binding
        button_column.addWidget(sdxl_button)

        clip_button = QPushButton("Rescan CLIP Models")
        clip_button.clicked.connect(self._rescan_clips)  # pragma: no cover - Qt binding
        button_column.addWidget(clip_button)

        combo_row = QHBoxLayout()
        combo_row.addStretch()
        combo_button = QPushButton("Run All Scans")
        combo_button.clicked.connect(self._run_all_scans)  # pragma: no cover - Qt binding
        combo_row.addWidget(combo_button)
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
        target_dir.mkdir(parents=True, exist_ok=True)
        self._set_status("Updating custom nodes…")
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
                self._append_log(f"{action} {repo}")
                result = subprocess.run(command, capture_output=True, text=True)
                if result.returncode != 0:
                    raise RuntimeError(result.stderr.strip() or result.stdout.strip() or "git command failed")
            except Exception as exc:
                self._append_log(f"❌ {repo}: {exc}")
            else:
                self._append_log(f"✅ {repo}")
        self._set_status("Custom nodes check complete. Review log for details.")

    def _rescan_flux_models(self) -> None:  # pragma: no cover - Qt binding
        self._set_status("Scanning Flux models…")
        update_models_list("config.json", "modelslist.json")
        self._append_log("Flux models list updated.")
        self._set_status("Flux scan complete.")

    def _rescan_checkpoints(self) -> None:  # pragma: no cover - Qt binding
        self._set_status("Scanning checkpoints…")
        update_checkpoints_list("config.json", "checkpointslist.json")
        self._append_log("Checkpoint list updated.")
        self._set_status("Checkpoint scan complete.")

    def _rescan_clips(self) -> None:  # pragma: no cover - Qt binding
        self._set_status("Scanning CLIP models…")
        scan_clip_files("config.json", "cliplist.json")
        self._append_log("CLIP list updated.")
        self._set_status("CLIP scan complete.")

    def _run_all_scans(self) -> None:  # pragma: no cover - Qt binding
        self._set_status("Running all scans…")
        self._rescan_flux_models()
        self._rescan_checkpoints()
        self._rescan_clips()
        self._set_status("All scans complete.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        self._repository = repository
        self._set_status("Ready.")


__all__ = ["ToolsView"]
