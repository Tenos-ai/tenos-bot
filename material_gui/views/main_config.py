"""Main configuration editor view for the Material configurator."""
from __future__ import annotations

import json
import zipfile
from datetime import datetime
from pathlib import Path
from typing import Dict

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
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
    QTableWidget,
    QTableWidgetItem,
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
        self._clip_field: QLineEdit | None = None
        self._lora_field: QLineEdit | None = None
        self._nodes_field: QLineEdit | None = None
        self._comfy_host: QLineEdit | None = None
        self._comfy_port: QSpinBox | None = None
        self._bot_host: QLineEdit | None = None
        self._bot_port: QSpinBox | None = None
        self._bot_token: QLineEdit | None = None
        self._admin_username: QLineEdit | None = None
        self._admin_id: QLineEdit | None = None
        self._gemini_key: QLineEdit | None = None
        self._groq_key: QLineEdit | None = None
        self._openai_key: QLineEdit | None = None
        self._auto_update_checkbox: QCheckBox | None = None
        self._allowed_table: QTableWidget | None = None
        self._allowed_id_input: QLineEdit | None = None
        self._allowed_label_input: QLineEdit | None = None
        self._status_label: QLabel | None = None

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

        content_layout.addWidget(self._build_output_group())
        content_layout.addWidget(self._build_model_group())
        content_layout.addWidget(self._build_api_group())
        content_layout.addWidget(self._build_bot_group())
        content_layout.addWidget(self._build_allowed_users_group())
        content_layout.addWidget(self._build_llm_group())
        content_layout.addWidget(self._build_app_settings_group())
        content_layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        save_button = QPushButton("Save Main Config")
        save_button.clicked.connect(self._persist)  # pragma: no cover - Qt binding
        button_row.addWidget(save_button)
        root_layout.addLayout(button_row)

        self._status_label = QLabel("Values mirror config.json. Save to apply changes.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self.refresh(repository)

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
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

        self._clip_field = QLineEdit()
        clip_browse = QPushButton("Browse…")
        clip_browse.clicked.connect(lambda _=False: self._browse_directory(self._clip_field))  # pragma: no cover
        clip_row = QHBoxLayout()
        clip_row.addWidget(self._clip_field)
        clip_row.addWidget(clip_browse)
        form.addRow("CLIP Files", clip_row)

        self._lora_field = QLineEdit()
        lora_browse = QPushButton("Browse…")
        lora_browse.clicked.connect(lambda _=False: self._browse_directory(self._lora_field))  # pragma: no cover
        lora_row = QHBoxLayout()
        lora_row.addWidget(self._lora_field)
        lora_row.addWidget(lora_browse)
        form.addRow("LoRA Files", lora_row)

        self._nodes_field = QLineEdit()
        nodes_browse = QPushButton("Browse…")
        nodes_browse.clicked.connect(lambda _=False: self._browse_directory(self._nodes_field))  # pragma: no cover
        nodes_row = QHBoxLayout()
        nodes_row.addWidget(self._nodes_field)
        nodes_row.addWidget(nodes_browse)
        form.addRow("Custom Nodes", nodes_row)

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

        self._bot_host = QLineEdit()
        self._bot_host.setPlaceholderText("127.0.0.1")
        self._bot_port = QSpinBox()
        self._bot_port.setRange(1, 65535)
        bot_row = QHBoxLayout()
        bot_row.addWidget(self._bot_host)
        bot_row.addWidget(self._bot_port)
        form.addRow("Bot Internal API (Host / Port)", bot_row)

        return group

    def _build_bot_group(self) -> QGroupBox:
        group = QGroupBox("Discord Bot Credentials")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._bot_token = QLineEdit()
        self._bot_token.setEchoMode(QLineEdit.Password)
        self._bot_token.setPlaceholderText("Bot token from Discord developer portal")
        form.addRow("Bot Token", self._bot_token)

        self._admin_username = QLineEdit()
        self._admin_username.setPlaceholderText("Admin username (optional)")
        form.addRow("Admin Username", self._admin_username)

        self._admin_id = QLineEdit()
        self._admin_id.setPlaceholderText("Admin Discord user ID")
        form.addRow("Admin User ID", self._admin_id)

        return group

    def _build_allowed_users_group(self) -> QGroupBox:
        group = QGroupBox("Allowed Users")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        instructions = QLabel(
            "Map Discord user IDs to friendly names to grant additional access. "
            "Leave empty to restrict control to the admin."
        )
        instructions.setWordWrap(True)
        layout.addWidget(instructions)

        self._allowed_table = QTableWidget(0, 2)
        self._allowed_table.setHorizontalHeaderLabels(["Discord ID", "Label"])
        self._allowed_table.horizontalHeader().setStretchLastSection(True)
        self._allowed_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._allowed_table.setSelectionMode(QAbstractItemView.SingleSelection)
        layout.addWidget(self._allowed_table)

        form_row = QHBoxLayout()
        self._allowed_id_input = QLineEdit()
        self._allowed_id_input.setPlaceholderText("Discord ID")
        self._allowed_label_input = QLineEdit()
        self._allowed_label_input.setPlaceholderText("Label / Notes")
        add_button = QPushButton("Add")
        add_button.clicked.connect(self._add_allowed_user)  # pragma: no cover - Qt binding
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_allowed_user)  # pragma: no cover - Qt binding
        form_row.addWidget(self._allowed_id_input)
        form_row.addWidget(self._allowed_label_input)
        form_row.addWidget(add_button)
        form_row.addWidget(remove_button)
        layout.addLayout(form_row)

        return group

    def _build_llm_group(self) -> QGroupBox:
        group = QGroupBox("LLM Enhancer API Keys")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._gemini_key = QLineEdit()
        self._gemini_key.setPlaceholderText("Google Gemini API key")
        form.addRow("Gemini", self._gemini_key)

        self._groq_key = QLineEdit()
        self._groq_key.setPlaceholderText("Groq API key")
        form.addRow("Groq", self._groq_key)

        self._openai_key = QLineEdit()
        self._openai_key.setPlaceholderText("OpenAI API key")
        form.addRow("OpenAI", self._openai_key)

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

    def _add_allowed_user(self) -> None:  # pragma: no cover - Qt binding
        if self._allowed_table is None or self._allowed_id_input is None or self._allowed_label_input is None:
            return
        user_id = self._allowed_id_input.text().strip()
        label = self._allowed_label_input.text().strip()
        if not user_id:
            self._set_status("Enter a Discord user ID before adding.")
            return
        # If the ID already exists, update the label instead of duplicating the row.
        for row in range(self._allowed_table.rowCount()):
            existing_item = self._allowed_table.item(row, 0)
            if existing_item and existing_item.text() == user_id:
                self._allowed_table.setItem(row, 1, QTableWidgetItem(label))
                self._allowed_id_input.clear()
                self._allowed_label_input.clear()
                self._set_status("Updated existing allowed user entry.")
                return
        row = self._allowed_table.rowCount()
        self._allowed_table.insertRow(row)
        self._allowed_table.setItem(row, 0, QTableWidgetItem(user_id))
        self._allowed_table.setItem(row, 1, QTableWidgetItem(label))
        self._allowed_id_input.clear()
        self._allowed_label_input.clear()
        self._set_status("Added allowed user entry.")

    def _remove_allowed_user(self) -> None:  # pragma: no cover - Qt binding
        if self._allowed_table is None:
            return
        current = self._allowed_table.currentRow()
        if current < 0:
            self._set_status("Select an entry to remove.")
            return
        self._allowed_table.removeRow(current)
        self._set_status("Allowed user removed.")

    def _persist(self) -> None:  # pragma: no cover - Qt binding
        try:
            payload = {
                "OUTPUTS": {key: field.text().strip() for key, field in self._output_fields.items()},
                "MODELS": {key: field.text().strip() for key, field in self._model_fields.items()},
                "CLIP": {"CLIP_FILES": (self._clip_field.text().strip() if self._clip_field else "")},
                "LORAS": {"LORA_FILES": (self._lora_field.text().strip() if self._lora_field else "")},
                "NODES": {"CUSTOM_NODES": (self._nodes_field.text().strip() if self._nodes_field else "")},
                "COMFYUI_API": {
                    "HOST": self._comfy_host.text().strip() if self._comfy_host else "127.0.0.1",
                    "PORT": int(self._comfy_port.value()) if self._comfy_port else 8188,
                },
                "BOT_INTERNAL_API": {
                    "HOST": self._bot_host.text().strip() if self._bot_host else "127.0.0.1",
                    "PORT": int(self._bot_port.value()) if self._bot_port else 8189,
                },
                "BOT_API": {"KEY": self._bot_token.text().strip() if self._bot_token else ""},
                "ADMIN": {
                    "USERNAME": self._admin_username.text().strip() if self._admin_username else "",
                    "ID": self._admin_id.text().strip() if self._admin_id else "",
                },
                "LLM_ENHANCER": {
                    "GEMINI_API_KEY": self._gemini_key.text().strip() if self._gemini_key else "",
                    "GROQ_API_KEY": self._groq_key.text().strip() if self._groq_key else "",
                    "OPENAI_API_KEY": self._openai_key.text().strip() if self._openai_key else "",
                },
                "APP_SETTINGS": {
                    "AUTO_UPDATE_ON_STARTUP": bool(self._auto_update_checkbox.isChecked())
                    if self._auto_update_checkbox
                    else False
                },
            }

            if self._allowed_table is not None:
                allowed_users: Dict[str, str] = {}
                for row in range(self._allowed_table.rowCount()):
                    id_item = self._allowed_table.item(row, 0)
                    label_item = self._allowed_table.item(row, 1)
                    if id_item is None:
                        continue
                    user_id = id_item.text().strip()
                    if not user_id:
                        continue
                    label = label_item.text().strip() if label_item else ""
                    allowed_users[user_id] = label
                payload["ALLOWED_USERS"] = allowed_users

            self._repository.save_config(payload)
            self._set_status("Configuration saved.")
            self.refresh(self._repository)
        except Exception as exc:  # pragma: no cover - user feedback only
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status("Unable to save configuration. See details above.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        config = repository.config or {}

        outputs = config.get("OUTPUTS", {})
        for key, field in self._output_fields.items():
            field.setText(str(outputs.get(key, "")))

        models = config.get("MODELS", {})
        for key, field in self._model_fields.items():
            field.setText(str(models.get(key, "")))

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

        admin = config.get("ADMIN", {})
        if self._admin_username is not None:
            self._admin_username.setText(str(admin.get("USERNAME", "")))
        if self._admin_id is not None:
            self._admin_id.setText(str(admin.get("ID", "")))

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

        if self._allowed_table is not None:
            self._allowed_table.setRowCount(0)
            allowed_users = config.get("ALLOWED_USERS", {})
            if isinstance(allowed_users, dict):
                for user_id, label in allowed_users.items():
                    row = self._allowed_table.rowCount()
                    self._allowed_table.insertRow(row)
                    self._allowed_table.setItem(row, 0, QTableWidgetItem(str(user_id)))
                    self._allowed_table.setItem(row, 1, QTableWidgetItem(str(label)))

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_status(self, message: str) -> None:
        if self._status_label is not None:
            self._status_label.setText(message)


__all__ = ["MainConfigView"]
