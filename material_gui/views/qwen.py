"""Qwen-specific settings view for the Material Configurator."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from settings_manager import load_styles_config


class QwenSettingsView(BaseView):
    """Allow users to tune Qwen defaults and edit parameters."""

    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__()
        self._repository = repository
        self._loading = False

        self._save_timer = QTimer(self)
        self._save_timer.setInterval(300)
        self._save_timer.setSingleShot(True)
        self._save_timer.timeout.connect(self._persist_changes)  # pragma: no cover - Qt binding

        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        layout.setSpacing(18)

        header = QLabel("Qwen Image Defaults")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        form = QFormLayout()
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        form.setFormAlignment(Qt.AlignTop)
        form.setVerticalSpacing(12)
        layout.addLayout(form)

        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["kontext", "qwen"])
        form.addRow("Default Edit Engine", self.engine_combo)

        self.model_combo = QComboBox()
        form.addRow("Preferred Qwen Model", self.model_combo)

        self.style_combo = QComboBox()
        form.addRow("Default Style", self.style_combo)

        self.negative_prompt = QTextEdit()
        self.negative_prompt.setPlaceholderText("Default negative prompt for Qwen runs")
        self.negative_prompt.setFixedHeight(80)
        form.addRow("Negative Prompt", self.negative_prompt)

        self.steps_spin = QSpinBox()
        self.steps_spin.setRange(1, 200)
        form.addRow("Edit Steps", self.steps_spin)

        self.guidance_spin = QDoubleSpinBox()
        self.guidance_spin.setRange(0.5, 20.0)
        self.guidance_spin.setSingleStep(0.1)
        form.addRow("Edit Guidance", self.guidance_spin)

        self.denoise_spin = QDoubleSpinBox()
        self.denoise_spin.setRange(0.0, 1.0)
        self.denoise_spin.setSingleStep(0.01)
        form.addRow("Edit Denoise", self.denoise_spin)

        self.engine_combo.currentIndexChanged.connect(self._queue_save)  # pragma: no cover - Qt binding
        self.model_combo.currentIndexChanged.connect(self._queue_save)  # pragma: no cover - Qt binding
        self.style_combo.currentIndexChanged.connect(self._queue_save)  # pragma: no cover - Qt binding
        self.negative_prompt.textChanged.connect(self._queue_save)  # pragma: no cover - Qt binding
        self.steps_spin.valueChanged.connect(self._queue_save)  # pragma: no cover - Qt binding
        self.guidance_spin.valueChanged.connect(self._queue_save)  # pragma: no cover - Qt binding
        self.denoise_spin.valueChanged.connect(self._queue_save)  # pragma: no cover - Qt binding

        self.refresh(repository)

    # ------------------------------------------------------------------
    # Qt helpers
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        self._loading = True
        self._save_timer.stop()
        data = repository.settings
        styles = load_styles_config() or {}
        qwen_styles = ["off"]
        for name, meta in styles.items():
            if not isinstance(meta, dict):
                continue
            model_type = str(meta.get("model_type", "all")).lower()
            if model_type in {"all", "qwen", ""}:
                qwen_styles.append(name)
        qwen_styles = sorted(dict.fromkeys(qwen_styles))

        current_models = repository.get_available_models("qwen")
        self.model_combo.clear()
        self.model_combo.addItem("(None)")
        for item in current_models:
            self.model_combo.addItem(item)

        self.style_combo.clear()
        for style in qwen_styles:
            self.style_combo.addItem(style)

        self.engine_combo.setCurrentText(str(data.get("default_edit_engine", "kontext")).lower())
        preferred_model = data.get("preferred_model_qwen")
        if isinstance(preferred_model, str) and ":" in preferred_model:
            preferred_model = preferred_model.split(":", 1)[-1].strip()
        if preferred_model:
            idx = self.model_combo.findText(preferred_model)
            if idx != -1:
                self.model_combo.setCurrentIndex(idx)

        style_value = data.get("default_style_qwen", "off")
        style_idx = self.style_combo.findText(style_value)
        if style_idx != -1:
            self.style_combo.setCurrentIndex(style_idx)

        self.negative_prompt.setPlainText(data.get("default_qwen_negative_prompt", ""))
        self.steps_spin.setValue(int(data.get("qwen_edit_steps", 30)))
        self.guidance_spin.setValue(float(data.get("qwen_edit_guidance", 6.0)))
        self.denoise_spin.setValue(float(data.get("qwen_edit_denoise", 0.65)))
        self._loading = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _queue_save(self) -> None:  # pragma: no cover - Qt binding
        if self._loading:
            return
        self._save_timer.start()

    def _persist_changes(self) -> None:  # pragma: no cover - Qt binding
        if self._loading:
            return
        model = self.model_combo.currentText()
        model_pref = f"Qwen: {model}" if model and model != "(None)" else None
        payload = {
            "default_edit_engine": self.engine_combo.currentText(),
            "preferred_model_qwen": model_pref,
            "default_style_qwen": self.style_combo.currentText(),
            "default_qwen_negative_prompt": self.negative_prompt.toPlainText().strip(),
            "qwen_edit_steps": self.steps_spin.value(),
            "qwen_edit_guidance": self.guidance_spin.value(),
            "qwen_edit_denoise": self.denoise_spin.value(),
        }
        self._repository.save_settings(payload)
