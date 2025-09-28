"""Main configuration editor view for the Material configurator."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView


class MainConfigView(BaseView):
    """Expose config.json editing in a structured Material-inspired layout."""

    def __init__(self, repository: SettingsRepository, app_base_dir: Path) -> None:
        super().__init__()
        self._repository = repository
        self._app_base_dir = app_base_dir

        self._output_fields: Dict[str, QLineEdit] = {}
        self._model_fields: Dict[str, QLineEdit] = {}
        self._field_map: Dict[QLineEdit, tuple[str, str]] = {}
        self._clip_field: QLineEdit | None = None
        self._lora_field: QLineEdit | None = None
        self._nodes_field: QLineEdit | None = None
        self._qwen_model_field: QLineEdit | None = None
        self._qwen_clip_field: QLineEdit | None = None
        self._comfy_host: QLineEdit | None = None
        self._comfy_port: QSpinBox | None = None
        self._bot_host: QLineEdit | None = None
        self._bot_port: QSpinBox | None = None
        self._bot_token: QLineEdit | None = None
        self._gemini_key: QLineEdit | None = None
        self._groq_key: QLineEdit | None = None
        self._openai_key: QLineEdit | None = None
        self._auto_update_checkbox: QCheckBox | None = None
        self._status_label: QLabel | None = None
        self._loading = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("Main Configuration")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        description = QLabel(
            "Update critical paths, Discord credentials, API hosts, and whitelisted users. "
            "Changes are written to <code>config.json</code>."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll, stretch=1)

        content = QWidget()
        scroll.setWidget(content)

        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        tabs = QTabWidget()
        tabs.addTab(self._build_paths_tab(), "File Paths")
        tabs.addTab(self._build_endpoints_tab(), "Endpoint URLs")
        tabs.addTab(self._build_api_keys_tab(), "API Keys")
        tabs.addTab(self._build_app_settings_tab(), "App Settings")
        content_layout.addWidget(tabs)
        content_layout.addStretch()

        self._status_label = QLabel("Changes are saved automatically.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self.refresh(repository)

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _build_paths_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self._build_output_group())
        layout.addWidget(self._build_model_group())
        layout.addStretch(1)
        return page

    def _build_endpoints_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self._build_api_group())
        layout.addStretch(1)
        return page

    def _build_api_keys_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self._build_bot_credentials_group())
        layout.addWidget(self._build_llm_group())
        layout.addStretch(1)
        return page

    def _build_app_settings_tab(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(12)
        layout.addWidget(self._build_app_settings_group())
        layout.addStretch(1)
        return page

    def _build_output_group(self) -> QGroupBox:
        group = QGroupBox("Output Directories")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for key, label in (
            ("GENERATIONS", "Generations"),
            ("UPSCALES", "Upscales"),
            ("VARIATIONS", "Variations"),
        ):
            field = QLineEdit()
            field.setPlaceholderText("Path to folder")
            browse = QPushButton("Browse…")
            browse.clicked.connect(lambda _=False, k=key: self._browse_directory(self._output_fields[k]))  # pragma: no cover
            row = QHBoxLayout()
            row.addWidget(field)
            row.addWidget(browse)
            form.addRow(label, row)
            self._output_fields[key] = field
            self._field_map[field] = ("OUTPUTS", key)
            field.editingFinished.connect(
                lambda key=key, f=field: self._persist_path("OUTPUTS", key, f.text().strip())
            )  # pragma: no cover

        return group

    def _build_model_group(self) -> QGroupBox:
        group = QGroupBox("Model & Asset Paths")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for key, label in (
            ("MODEL_FILES", "Flux Models"),
            ("CHECKPOINTS_FOLDER", "SDXL / Qwen Checkpoints"),
            ("UPSCALE_MODELS", "Upscale Models"),
            ("VAE_MODELS", "VAE Models"),
        ):
            field = QLineEdit()
            field.setPlaceholderText("Path to folder")
            browse = QPushButton("Browse…")
            browse.clicked.connect(lambda _=False, f=field: self._browse_directory(f))  # pragma: no cover
            row = QHBoxLayout()
            row.addWidget(field)
            row.addWidget(browse)
            form.addRow(label, row)
            self._model_fields[key] = field
            self._field_map[field] = ("MODELS", key)
            field.editingFinished.connect(lambda key=key, f=field: self._persist_path("MODELS", key, f.text().strip()))  # pragma: no cover

        self._clip_field = QLineEdit()
        clip_browse = QPushButton("Browse…")
        clip_browse.clicked.connect(lambda _=False: self._browse_directory(self._clip_field))  # pragma: no cover
        clip_row = QHBoxLayout()
        clip_row.addWidget(self._clip_field)
        clip_row.addWidget(clip_browse)
        form.addRow("CLIP Files", clip_row)
        self._field_map[self._clip_field] = ("CLIP", "CLIP_FILES")
        self._clip_field.editingFinished.connect(
            lambda: self._persist_path("CLIP", "CLIP_FILES", self._clip_field.text().strip())
        )  # pragma: no cover

        self._lora_field = QLineEdit()
        lora_browse = QPushButton("Browse…")
        lora_browse.clicked.connect(lambda _=False: self._browse_directory(self._lora_field))  # pragma: no cover
        lora_row = QHBoxLayout()
        lora_row.addWidget(self._lora_field)
        lora_row.addWidget(lora_browse)
        form.addRow("LoRA Files", lora_row)
        self._field_map[self._lora_field] = ("LORAS", "LORA_FILES")
        self._lora_field.editingFinished.connect(
            lambda: self._persist_path("LORAS", "LORA_FILES", self._lora_field.text().strip())
        )  # pragma: no cover

        self._nodes_field = QLineEdit()
        nodes_browse = QPushButton("Browse…")
        nodes_browse.clicked.connect(lambda _=False: self._browse_directory(self._nodes_field))  # pragma: no cover
        nodes_row = QHBoxLayout()
        nodes_row.addWidget(self._nodes_field)
        nodes_row.addWidget(nodes_browse)
        form.addRow("Custom Nodes", nodes_row)
        self._field_map[self._nodes_field] = ("NODES", "CUSTOM_NODES")
        self._nodes_field.editingFinished.connect(
            lambda: self._persist_path("NODES", "CUSTOM_NODES", self._nodes_field.text().strip())
        )  # pragma: no cover

        self._qwen_model_field = QLineEdit()
        qwen_model_browse = QPushButton("Browse…")
        qwen_model_browse.clicked.connect(lambda _=False: self._browse_directory(self._qwen_model_field))  # pragma: no cover
        qwen_model_row = QHBoxLayout()
        qwen_model_row.addWidget(self._qwen_model_field)
        qwen_model_row.addWidget(qwen_model_browse)
        form.addRow("Qwen Models", qwen_model_row)
        self._field_map[self._qwen_model_field] = ("QWEN", "MODEL_FILES")
        self._qwen_model_field.editingFinished.connect(
            lambda: self._persist_path("QWEN", "MODEL_FILES", self._qwen_model_field.text().strip())
        )  # pragma: no cover

        self._qwen_clip_field = QLineEdit()
        qwen_clip_browse = QPushButton("Browse…")
        qwen_clip_browse.clicked.connect(lambda _=False: self._browse_directory(self._qwen_clip_field))  # pragma: no cover
        qwen_clip_row = QHBoxLayout()
        qwen_clip_row.addWidget(self._qwen_clip_field)
        qwen_clip_row.addWidget(qwen_clip_browse)
        form.addRow("Qwen CLIP", qwen_clip_row)
        self._field_map[self._qwen_clip_field] = ("QWEN", "CLIP_FILES")
        self._qwen_clip_field.editingFinished.connect(
            lambda: self._persist_path("QWEN", "CLIP_FILES", self._qwen_clip_field.text().strip())
        )  # pragma: no cover

        return group

    def _build_api_group(self) -> QGroupBox:
        group = QGroupBox("Service Endpoints")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._comfy_host = QLineEdit()
        self._comfy_host.setPlaceholderText("127.0.0.1")
        self._comfy_port = QSpinBox()
        self._comfy_port.setRange(1, 65535)
        comfy_row = QHBoxLayout()
        comfy_row.addWidget(self._comfy_host)
        comfy_row.addWidget(self._comfy_port)
        form.addRow("ComfyUI API (Host / Port)", comfy_row)
        self._comfy_host.editingFinished.connect(
            lambda: self._persist_path("COMFYUI_API", "HOST", self._comfy_host.text().strip())
        )  # pragma: no cover
        self._comfy_port.valueChanged.connect(
            lambda value: self._persist_path("COMFYUI_API", "PORT", int(value))
        )  # pragma: no cover

        self._bot_host = QLineEdit()
        self._bot_host.setPlaceholderText("127.0.0.1")
        self._bot_port = QSpinBox()
        self._bot_port.setRange(1, 65535)
        bot_row = QHBoxLayout()
        bot_row.addWidget(self._bot_host)
        bot_row.addWidget(self._bot_port)
        form.addRow("Bot Internal API (Host / Port)", bot_row)
        self._bot_host.editingFinished.connect(
            lambda: self._persist_path("BOT_INTERNAL_API", "HOST", self._bot_host.text().strip())
        )  # pragma: no cover
        self._bot_port.valueChanged.connect(
            lambda value: self._persist_path("BOT_INTERNAL_API", "PORT", int(value))
        )  # pragma: no cover

        return group

    def _build_bot_credentials_group(self) -> QGroupBox:
        group = QGroupBox("Discord Bot Credentials")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._bot_token = QLineEdit()
        self._bot_token.setEchoMode(QLineEdit.Password)
        self._bot_token.setPlaceholderText("Bot token from Discord developer portal")
        form.addRow("Bot Token", self._bot_token)
        self._bot_token.editingFinished.connect(
            lambda: self._persist_path("BOT_API", "KEY", self._bot_token.text().strip())
        )  # pragma: no cover

        return group

    def _build_llm_group(self) -> QGroupBox:
        group = QGroupBox("LLM Enhancer API Keys")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._gemini_key = QLineEdit()
        self._gemini_key.setPlaceholderText("Google Gemini API key")
        form.addRow("Gemini", self._gemini_key)
        self._gemini_key.editingFinished.connect(
            lambda: self._persist_path("LLM_ENHANCER", "GEMINI_API_KEY", self._gemini_key.text().strip())
        )  # pragma: no cover

        self._groq_key = QLineEdit()
        self._groq_key.setPlaceholderText("Groq API key")
        form.addRow("Groq", self._groq_key)
        self._groq_key.editingFinished.connect(
            lambda: self._persist_path("LLM_ENHANCER", "GROQ_API_KEY", self._groq_key.text().strip())
        )  # pragma: no cover

        self._openai_key = QLineEdit()
        self._openai_key.setPlaceholderText("OpenAI API key")
        form.addRow("OpenAI", self._openai_key)
        self._openai_key.editingFinished.connect(
            lambda: self._persist_path("LLM_ENHANCER", "OPENAI_API_KEY", self._openai_key.text().strip())
        )  # pragma: no cover

        return group

    def _build_app_settings_group(self) -> QGroupBox:
        group = QGroupBox("Configurator Behaviour")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        info = QLabel(
            "Bundle or restore <code>config.json</code> and <code>settings.json</code> without leaving "
            "the configurator."
        )
        info.setObjectName("MaterialCard")
        info.setWordWrap(True)
        layout.addWidget(info)

        self._auto_update_checkbox = QCheckBox("Automatically check for updates on launch")
        self._auto_update_checkbox.stateChanged.connect(
            lambda state: self._persist_path("APP_SETTINGS", "AUTO_UPDATE_ON_STARTUP", bool(state))
        )  # pragma: no cover
        layout.addWidget(self._auto_update_checkbox)

        button_row = QHBoxLayout()
        button_row.setSpacing(12)

        import_button = QPushButton("Import Config & Settings")
        import_button.clicked.connect(self._import_bundle)  # pragma: no cover - Qt binding
        button_row.addWidget(import_button)

        export_button = QPushButton("Export Config & Settings")
        export_button.clicked.connect(self._export_bundle)  # pragma: no cover - Qt binding
        button_row.addWidget(export_button)

        button_row.addStretch(1)
        layout.addLayout(button_row)

        return group

    def _import_bundle(self) -> None:
        start_dir = str(self._app_base_dir)
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Config & Settings",
            start_dir,
            "Zip Archives (*.zip)",
        )
        if not file_path:
            return
        try:
            imported = 0
            with zipfile.ZipFile(file_path, "r") as archive:
                for name in ("config.json", "settings.json"):
                    if name not in archive.namelist():
                        continue
                    raw = archive.read(name).decode("utf-8")
                    json.loads(raw)  # validate JSON before writing
                    target_path = self._app_base_dir / name
                    target_path.write_text(raw, encoding="utf-8")
                    imported += 1
            if imported == 0:
                raise ValueError("Archive did not contain config.json or settings.json")
            self._repository.refresh()
            self.refresh(self._repository)
            self._set_status("Imported configuration bundle.")
        except Exception as exc:  # pragma: no cover - user feedback only
            QMessageBox.critical(self, "Import Failed", str(exc))
            self._set_status("Import failed. See message above.")

    def _export_bundle(self) -> None:
        default_name = f"tenosai-config-{datetime.now():%Y%m%d-%H%M%S}.zip"
        target_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Config & Settings",
            str(self._app_base_dir / default_name),
            "Zip Archives (*.zip)",
        )
        if not target_path:
            return
        try:
            written = 0
            with zipfile.ZipFile(target_path, "w", compression=zipfile.ZIP_DEFLATED) as archive:
                for name in ("config.json", "settings.json"):
                    path = self._app_base_dir / name
                    if path.exists():
                        archive.write(path, arcname=name)
                        written += 1
            if written == 0:
                raise FileNotFoundError("No configuration files found to export.")
            self._set_status(f"Exported configuration bundle to {target_path}")
        except Exception as exc:  # pragma: no cover - user feedback only
            QMessageBox.critical(self, "Export Failed", str(exc))
            self._set_status("Export failed. See message above.")

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _browse_directory(self, field: QLineEdit | None) -> None:  # pragma: no cover - Qt binding
        if field is None:
            return
        start_dir = field.text().strip() or str(self._app_base_dir)
        directory = QFileDialog.getExistingDirectory(self, "Select Directory", start_dir)
        if directory:
            field.setText(directory)
            mapping = self._field_map.get(field)
            if mapping:
                section, key = mapping
                self._persist_path(section, key, field.text().strip())

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        self._loading = True
        config = repository.config or {}

        outputs = config.get("OUTPUTS", {})
        for key, field in self._output_fields.items():
            field.setText(str(outputs.get(key, "")))

        models = config.get("MODELS", {})
        for key, field in self._model_fields.items():
            field.setText(str(models.get(key, "")))

        qwen = config.get("QWEN", {})
        if self._qwen_model_field is not None:
            self._qwen_model_field.setText(str(qwen.get("MODEL_FILES", "")))
        if self._qwen_clip_field is not None:
            self._qwen_clip_field.setText(str(qwen.get("CLIP_FILES", "")))

        if self._clip_field is not None:
            self._clip_field.setText(str(config.get("CLIP", {}).get("CLIP_FILES", "")))
        if self._lora_field is not None:
            self._lora_field.setText(str(config.get("LORAS", {}).get("LORA_FILES", "")))
        if self._nodes_field is not None:
            self._nodes_field.setText(str(config.get("NODES", {}).get("CUSTOM_NODES", "")))

        comfy = config.get("COMFYUI_API", {})
        if self._comfy_host is not None:
            self._comfy_host.setText(str(comfy.get("HOST", "127.0.0.1")))
        if self._comfy_port is not None:
            self._comfy_port.setValue(int(comfy.get("PORT", 8188)))

        bot_api = config.get("BOT_INTERNAL_API", {})
        if self._bot_host is not None:
            self._bot_host.setText(str(bot_api.get("HOST", "127.0.0.1")))
        if self._bot_port is not None:
            self._bot_port.setValue(int(bot_api.get("PORT", 8189)))

        bot_credentials = config.get("BOT_API", {})
        if self._bot_token is not None:
            self._bot_token.setText(str(bot_credentials.get("KEY", "")))

        llm = config.get("LLM_ENHANCER", {})
        if self._gemini_key is not None:
            self._gemini_key.setText(str(llm.get("GEMINI_API_KEY", "")))
        if self._groq_key is not None:
            self._groq_key.setText(str(llm.get("GROQ_API_KEY", "")))
        if self._openai_key is not None:
            self._openai_key.setText(str(llm.get("OPENAI_API_KEY", "")))

        app_settings = config.get("APP_SETTINGS", {})
        if self._auto_update_checkbox is not None:
            self._auto_update_checkbox.setChecked(bool(app_settings.get("AUTO_UPDATE_ON_STARTUP", False)))

        self._loading = False

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_status(self, message: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(message)

    def _persist_path(self, section: str, key: str | None, value: object) -> None:
        if self._loading or key is None:
            return
        try:
            self._repository.save_config({section: {key: value}})
            self._set_status("Configuration saved.")
        except Exception as exc:  # pragma: no cover - user feedback only
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status("Unable to save configuration. See details above.")


__all__ = ["MainConfigView"]
