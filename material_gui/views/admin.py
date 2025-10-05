"""Administrative dashboard combining user management and live runtime info."""
from __future__ import annotations

import json
from pathlib import Path
from typing import Dict, Iterable
from urllib.error import URLError
from urllib.request import Request, urlopen

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView


class AdminView(BaseView):
    """Expose administrative controls and live bot telemetry in one tab."""

    def __init__(self, repository: SettingsRepository, app_base_dir: Path) -> None:
        super().__init__()
        self._repository = repository
        self._app_base_dir = app_base_dir

        self._admin_username: QLineEdit | None = None
        self._admin_id: QLineEdit | None = None
        self._allowed_table: QTableWidget | None = None
        self._allowed_id_input: QLineEdit | None = None
        self._allowed_label_input: QLineEdit | None = None
        self._blocklist_widget: QListWidget | None = None
        self._block_input: QLineEdit | None = None
        self._status_label: QLabel | None = None

        self._api_status: QLabel | None = None
        self._server_list: QListWidget | None = None
        self._member_list: QListWidget | None = None
        self._dm_list: QListWidget | None = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("Administration Console")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        subtitle = QLabel(
            "Manage privileged Discord users, maintain blocklists, and inspect live Tenos.ai "
            "bot activity from a single surface."
        )
        subtitle.setWordWrap(True)
        subtitle.setObjectName("MaterialCard")
        layout.addWidget(subtitle)

        user_group = self._build_user_group()
        layout.addWidget(user_group)

        block_group = self._build_block_group()
        layout.addWidget(block_group)

        live_group = self._build_live_group()
        layout.addWidget(live_group, stretch=1)

        self._status_label = QLabel("Loaded administrator information from config.json.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        layout.addWidget(self._status_label)

        self.refresh(repository)

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------
    def _build_user_group(self) -> QGroupBox:
        group = QGroupBox("User Management")
        group_layout = QVBoxLayout(group)
        group_layout.setSpacing(12)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._admin_username = QLineEdit()
        self._admin_username.setPlaceholderText("Discord username")
        form.addRow("Main Bot Admin", self._admin_username)

        self._admin_id = QLineEdit()
        self._admin_id.setPlaceholderText("Discord user ID")
        form.addRow("Admin Discord ID", self._admin_id)

        group_layout.addLayout(form)

        table = QTableWidget()
        table.setColumnCount(2)
        table.setHorizontalHeaderLabels(["User ID", "Label"])
        table.horizontalHeader().setStretchLastSection(True)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QTableWidget.SelectRows)
        table.setEditTriggers(QTableWidget.NoEditTriggers)
        self._allowed_table = table
        group_layout.addWidget(table)

        add_row = QHBoxLayout()
        self._allowed_id_input = QLineEdit()
        self._allowed_id_input.setPlaceholderText("New Discord user ID")
        add_row.addWidget(self._allowed_id_input)

        self._allowed_label_input = QLineEdit()
        self._allowed_label_input.setPlaceholderText("Friendly name or notes")
        add_row.addWidget(self._allowed_label_input)

        add_button = QPushButton("Add Allowed User")
        add_button.clicked.connect(self._add_allowed_user)  # pragma: no cover - Qt binding
        add_row.addWidget(add_button)
        group_layout.addLayout(add_row)

        action_row = QHBoxLayout()
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_selected_allowed_user)  # pragma: no cover
        action_row.addWidget(remove_button)

        action_row.addStretch()

        save_button = QPushButton("Save User Changes")
        save_button.clicked.connect(self._persist_user_management)  # pragma: no cover
        action_row.addWidget(save_button)
        group_layout.addLayout(action_row)

        return group

    def _build_block_group(self) -> QGroupBox:
        group = QGroupBox("User Blocklist")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        help_label = QLabel(
            "Users listed below will be prevented from interacting with the bot regardless of other "
            "permissions."
        )
        help_label.setWordWrap(True)
        layout.addWidget(help_label)

        self._blocklist_widget = QListWidget()
        layout.addWidget(self._blocklist_widget)

        input_row = QHBoxLayout()
        self._block_input = QLineEdit()
        self._block_input.setPlaceholderText("Discord user ID to block")
        input_row.addWidget(self._block_input)

        add_button = QPushButton("Add to Blocklist")
        add_button.clicked.connect(self._add_blocked_user)  # pragma: no cover
        input_row.addWidget(add_button)
        layout.addLayout(input_row)

        action_row = QHBoxLayout()
        remove_button = QPushButton("Remove Selected")
        remove_button.clicked.connect(self._remove_selected_blocked_user)  # pragma: no cover
        action_row.addWidget(remove_button)

        action_row.addStretch()

        save_button = QPushButton("Save Blocklist")
        save_button.clicked.connect(self._persist_blocklist)  # pragma: no cover
        action_row.addWidget(save_button)
        layout.addLayout(action_row)

        return group

    def _build_live_group(self) -> QGroupBox:
        group = QGroupBox("Live Manager")
        layout = QVBoxLayout(group)
        layout.setSpacing(12)

        self._api_status = QLabel("Runtime telemetry will appear once the bot API responds.")
        self._api_status.setWordWrap(True)
        self._api_status.setObjectName("MaterialCard")
        layout.addWidget(self._api_status)

        list_row = QHBoxLayout()
        list_row.setSpacing(12)

        self._server_list = self._build_live_list("Active Servers")
        list_row.addWidget(self._server_list)

        self._member_list = self._build_live_list("Members in Selection")
        list_row.addWidget(self._member_list)

        self._dm_list = self._build_live_list("Recent Direct Messages")
        list_row.addWidget(self._dm_list)

        layout.addLayout(list_row)

        button_row = QHBoxLayout()
        refresh_button = QPushButton("Refresh Live Data")
        refresh_button.clicked.connect(self._refresh_live_data)  # pragma: no cover
        button_row.addWidget(refresh_button)
        button_row.addStretch()
        layout.addLayout(button_row)

        return group

    def _build_live_list(self, title: str) -> QListWidget:
        widget = QListWidget()
        widget.setObjectName("MaterialCardList")
        widget.setProperty("title", title)
        return widget

    # ------------------------------------------------------------------
    # Refresh hooks
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - Qt wiring
        self._repository = repository
        self._load_admin_fields(repository.config)
        self._load_allowed_users(repository.config)
        self._load_blocklist()
        if self._status_label:
            self._status_label.setText("Administrator settings synced with disk.")

    # ------------------------------------------------------------------
    # Admin helpers
    # ------------------------------------------------------------------
    def _load_admin_fields(self, config: Dict[str, object]) -> None:
        admin = config.get("ADMIN") if isinstance(config, dict) else {}
        if not isinstance(admin, dict):
            admin = {}
        if self._admin_username:
            self._admin_username.setText(str(admin.get("USERNAME", "")))
        if self._admin_id:
            self._admin_id.setText(str(admin.get("ID", "")))

    def _load_allowed_users(self, config: Dict[str, object]) -> None:
        allowed = config.get("ALLOWED_USERS") if isinstance(config, dict) else {}
        if not isinstance(allowed, dict):
            allowed = {}

        if not self._allowed_table:
            return

        table = self._allowed_table
        table.setRowCount(0)
        for row, (user_id, label) in enumerate(sorted(allowed.items())):
            table.insertRow(row)
            table.setItem(row, 0, QTableWidgetItem(str(user_id)))
            table.setItem(row, 1, QTableWidgetItem(str(label)))

    def _add_allowed_user(self) -> None:  # pragma: no cover - Qt binding
        if not (self._allowed_table and self._allowed_id_input and self._allowed_label_input):
            return
        user_id = self._allowed_id_input.text().strip()
        label = self._allowed_label_input.text().strip()
        if not user_id:
            if self._status_label:
                self._status_label.setText("Enter a Discord user ID before adding.")
            return
        table = self._allowed_table
        row = table.rowCount()
        table.insertRow(row)
        table.setItem(row, 0, QTableWidgetItem(user_id))
        table.setItem(row, 1, QTableWidgetItem(label))
        self._allowed_id_input.clear()
        self._allowed_label_input.clear()

    def _remove_selected_allowed_user(self) -> None:  # pragma: no cover - Qt binding
        if not self._allowed_table:
            return
        selected_rows = {index.row() for index in self._allowed_table.selectedIndexes()}
        for row in sorted(selected_rows, reverse=True):
            self._allowed_table.removeRow(row)

    def _persist_user_management(self) -> None:  # pragma: no cover - Qt binding
        if not (self._admin_username and self._admin_id and self._allowed_table):
            return

        admin_payload = {
            "ADMIN": {
                "USERNAME": self._admin_username.text().strip(),
                "ID": self._admin_id.text().strip(),
            }
        }

        allowed_payload: Dict[str, str] = {}
        for row in range(self._allowed_table.rowCount()):
            user_item = self._allowed_table.item(row, 0)
            label_item = self._allowed_table.item(row, 1)
            if not user_item:
                continue
            user_id = user_item.text().strip()
            if not user_id:
                continue
            allowed_payload[user_id] = label_item.text().strip() if label_item else ""

        admin_payload["ALLOWED_USERS"] = allowed_payload

        try:
            self._repository.save_config(admin_payload)
        except Exception as exc:
            if self._status_label:
                self._status_label.setText(f"Failed to save administrator settings: {exc}")
            return

        if self._status_label:
            self._status_label.setText("Administrator and allowed user list saved.")

    # ------------------------------------------------------------------
    # Blocklist helpers
    # ------------------------------------------------------------------
    def _blocklist_path(self) -> Path:
        return self._app_base_dir / "blocklist.json"

    def _load_blocklist(self) -> None:
        if not self._blocklist_widget:
            return
        widget = self._blocklist_widget
        widget.clear()
        path = self._blocklist_path()
        if not path.exists():
            return
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            data = []
        entries: Iterable[str]
        if isinstance(data, dict):
            entries = (str(key) for key, value in data.items() if value)
        elif isinstance(data, list):
            entries = (str(item) for item in data)
        else:
            entries = ()
        for item in entries:
            widget.addItem(item)

    def _add_blocked_user(self) -> None:  # pragma: no cover - Qt binding
        if not (self._blocklist_widget and self._block_input):
            return
        user_id = self._block_input.text().strip()
        if not user_id:
            if self._status_label:
                self._status_label.setText("Enter a user ID to block.")
            return
        if not any(self._blocklist_widget.item(i).text() == user_id for i in range(self._blocklist_widget.count())):
            self._blocklist_widget.addItem(user_id)
        self._block_input.clear()

    def _remove_selected_blocked_user(self) -> None:  # pragma: no cover - Qt binding
        if not self._blocklist_widget:
            return
        for item in self._blocklist_widget.selectedItems():
            row = self._blocklist_widget.row(item)
            self._blocklist_widget.takeItem(row)

    def _persist_blocklist(self) -> None:  # pragma: no cover - Qt binding
        if not self._blocklist_widget:
            return
        entries = [self._blocklist_widget.item(i).text() for i in range(self._blocklist_widget.count())]
        path = self._blocklist_path()
        try:
            path.write_text(json.dumps(entries, indent=2), encoding="utf-8")
        except Exception as exc:
            if self._status_label:
                self._status_label.setText(f"Failed to save blocklist: {exc}")
            return
        if self._status_label:
            self._status_label.setText("Blocklist saved to blocklist.json.")

    # ------------------------------------------------------------------
    # Live manager helpers
    # ------------------------------------------------------------------
    def _refresh_live_data(self) -> None:  # pragma: no cover - Qt binding
        if self._api_status:
            self._api_status.setText("Contacting bot API…")
        self._clear_live_lists()

        config = self._repository.config if isinstance(self._repository.config, dict) else {}
        internal_api = config.get("BOT_INTERNAL_API") if isinstance(config, dict) else {}
        if not isinstance(internal_api, dict):
            internal_api = {}

        host = str(internal_api.get("HOST", "127.0.0.1")).strip() or "127.0.0.1"
        port = internal_api.get("PORT", 8189)
        try:
            port_value = int(port)
        except (TypeError, ValueError):
            port_value = 8189

        url = f"http://{host}:{port_value}/status"

        try:
            request = Request(url, headers={"User-Agent": "TenosAI-Configurator"})
            with urlopen(request, timeout=4.0) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except URLError as exc:
            if self._api_status:
                self._api_status.setText(
                    f"Unable to reach bot API at {url}: {exc.reason if hasattr(exc, 'reason') else exc}"
                )
            return
        except Exception as exc:  # pragma: no cover - defensive guard
            if self._api_status:
                self._api_status.setText(f"Bot API response invalid: {exc}")
            return

        self._render_live_payload(payload)

    def _clear_live_lists(self) -> None:
        for widget in (self._server_list, self._member_list, self._dm_list):
            if widget:
                widget.clear()

    def _render_live_payload(self, payload: Dict[str, object]) -> None:
        if self._api_status:
            state = str(payload.get("status", "online")).title()
            self._api_status.setText(f"Bot API status: {state}")

        servers = payload.get("servers")
        if isinstance(servers, Iterable) and self._server_list:
            for server in servers:
                self._server_list.addItem(QListWidgetItem(str(server)))

        members = payload.get("members")
        if isinstance(members, Iterable) and self._member_list:
            for member in members:
                self._member_list.addItem(QListWidgetItem(str(member)))

        messages = payload.get("recent_direct_messages")
        if isinstance(messages, Iterable) and self._dm_list:
            for message in messages:
                self._dm_list.addItem(QListWidgetItem(str(message)))


__all__ = ["AdminView"]

