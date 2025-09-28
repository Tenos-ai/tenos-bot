"""LLM system prompt editor mirroring the legacy configurator."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
    QPlainTextEdit,
    QHBoxLayout,
)

from material_gui.views.base import BaseView

PROMPTS_PATH = Path("llm_prompts.json")


class LlmPromptsView(BaseView):
    """Allow editing of the enhancer system prompts shipped with the bot."""

    def __init__(self) -> None:
        super().__init__()
        self._prompts: dict[str, str] = {}
        self._editors: dict[str, QPlainTextEdit] = {}

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("LLM System Prompts")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        description = QLabel(
            "Fine-tune the prompt engineering instructions used by the enhancer. "
            "Each tab corresponds to a provider or workflow." 
            "Large prompts are saved with JSON formatting preserved."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        self._tabs = QTabWidget()
        root_layout.addWidget(self._tabs, stretch=1)

        button_row = QHBoxLayout()
        button_row.addStretch()
        save_button = QPushButton("Save Prompts")
        save_button.clicked.connect(self._persist)  # pragma: no cover - Qt binding
        button_row.addWidget(save_button)
        root_layout.addLayout(button_row)

        self._status_label = QLabel("Updates are written to llm_prompts.json.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self.refresh(None)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _populate_tabs(self) -> None:
        self._tabs.clear()
        self._editors.clear()
        if not self._prompts:
            note = QLabel("Prompt file missing or empty. Saving will create it with your entries.")
            note.setAlignment(Qt.AlignCenter)
            self._tabs.addTab(note, "No Prompts")
            return
        for key in sorted(self._prompts.keys()):
            editor = QPlainTextEdit()
            editor.setPlainText(str(self._prompts.get(key, "")))
            editor.setLineWrapMode(QPlainTextEdit.WidgetWidth)
            editor.setPlaceholderText("Enter the system prompt text")
            editor.setMinimumHeight(240)
            self._tabs.addTab(editor, key)
            self._editors[key] = editor

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _persist(self) -> None:  # pragma: no cover - Qt binding
        try:
            if not self._editors:
                # No prompts defined; allow creating one blank entry.
                self._prompts = {}
            for key, editor in self._editors.items():
                self._prompts[key] = editor.toPlainText().replace("\r\n", "\n")
            PROMPTS_PATH.write_text(json.dumps(self._prompts, indent=2, ensure_ascii=False))
            self._set_status("Prompts saved.")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status("Unable to save prompts. See details above.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository) -> None:  # pragma: no cover - UI wiring
        del repository
        if PROMPTS_PATH.exists():
            try:
                data = json.loads(PROMPTS_PATH.read_text())
                self._prompts = {k: str(v) for k, v in data.items() if isinstance(k, str)} if isinstance(data, dict) else {}
            except Exception:
                self._prompts = {}
        else:
            self._prompts = {}
        self._populate_tabs()
        self._set_status("Review or edit the prompts and click save to persist.")


__all__ = ["LlmPromptsView"]
