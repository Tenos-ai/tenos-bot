"""Bot settings editor mirroring the legacy Tkinter configurator options."""
from __future__ import annotations

from typing import Iterable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDoubleSpinBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView
from settings_manager import (
    get_clip_l_choices,
    get_display_prompt_preference_choices,
    get_llm_model_choices,
    get_llm_provider_choices,
    get_model_choices,
    get_style_choices_flux,
    get_style_choices_qwen,
    get_style_choices_sdxl,
    get_t5_clip_choices,
    get_upscale_model_choices,
    get_variation_mode_choices,
    get_vae_choices,
)


class BotSettingsView(BaseView):
    """Provide controls for generation defaults, styles, and LLM behaviour."""

    def __init__(self, repository: SettingsRepository) -> None:
        super().__init__()
        self._repository = repository

        self._model_combo = QComboBox()
        self._flux_combo = QComboBox()
        self._sdxl_combo = QComboBox()
        self._qwen_combo = QComboBox()
        self._t5_combo = QComboBox()
        self._clip_l_combo = QComboBox()
        self._upscale_model_combo = QComboBox()
        self._vae_combo = QComboBox()
        self._flux_style_combo = QComboBox()
        self._sdxl_style_combo = QComboBox()
        self._qwen_style_combo = QComboBox()

        for combo in (
            self._model_combo,
            self._flux_combo,
            self._sdxl_combo,
            self._qwen_combo,
            self._t5_combo,
            self._clip_l_combo,
            self._upscale_model_combo,
            self._vae_combo,
        ):
            combo.setEditable(True)

        self._steps_spin = QSpinBox()
        self._steps_spin.setRange(1, 300)
        self._sdxl_steps_spin = QSpinBox()
        self._sdxl_steps_spin.setRange(1, 300)
        self._guidance_spin = QDoubleSpinBox()
        self._guidance_spin.setRange(0.0, 20.0)
        self._guidance_spin.setSingleStep(0.1)
        self._sdxl_guidance_spin = QDoubleSpinBox()
        self._sdxl_guidance_spin.setRange(0.0, 20.0)
        self._sdxl_guidance_spin.setSingleStep(0.1)
        self._batch_size_spin = QSpinBox()
        self._batch_size_spin.setRange(1, 4)
        self._variation_batch_spin = QSpinBox()
        self._variation_batch_spin.setRange(1, 4)
        self._mp_size_spin = QDoubleSpinBox()
        self._mp_size_spin.setRange(0.1, 5.0)
        self._mp_size_spin.setSingleStep(0.05)
        self._upscale_factor_spin = QDoubleSpinBox()
        self._upscale_factor_spin.setRange(1.0, 6.0)
        self._upscale_factor_spin.setSingleStep(0.05)
        self._kontext_steps_spin = QSpinBox()
        self._kontext_steps_spin.setRange(1, 300)
        self._kontext_guidance_spin = QDoubleSpinBox()
        self._kontext_guidance_spin.setRange(0.0, 20.0)
        self._kontext_guidance_spin.setSingleStep(0.1)
        self._kontext_mp_spin = QDoubleSpinBox()
        self._kontext_mp_spin.setRange(0.1, 5.0)
        self._kontext_mp_spin.setSingleStep(0.05)

        self._variation_mode_combo = QComboBox()
        self._display_pref_combo = QComboBox()
        self._default_engine_combo = QComboBox()
        self._default_engine_combo.addItems(["kontext", "qwen"])

        self._remix_checkbox = QCheckBox("Enable Remix Mode for variation buttons")
        self._llm_checkbox = QCheckBox("Enable LLM Prompt Enhancer")
        self._llm_provider_combo = QComboBox()
        self._llm_model_combo = QComboBox()
        self._llm_model_combo.setEditable(True)

        self._sdxl_negative = QTextEdit()
        self._sdxl_negative.setPlaceholderText("Default negative prompt for SDXL/Qwen generations")
        self._sdxl_negative.setFixedHeight(100)
        self._qwen_negative = QTextEdit()
        self._qwen_negative.setPlaceholderText("Default negative prompt for Qwen edits")
        self._qwen_negative.setFixedHeight(80)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        header = QLabel("Bot Generation Settings")
        header.setObjectName("MaterialTitle")
        root_layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        root_layout.addWidget(scroll, stretch=1)

        content = QWidget()
        scroll.setWidget(content)
        content_layout = QVBoxLayout(content)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(18)

        content_layout.addWidget(self._build_model_group())
        content_layout.addWidget(self._build_generation_group())
        content_layout.addWidget(self._build_variation_group())
        content_layout.addWidget(self._build_kontext_group())
        content_layout.addWidget(self._build_llm_group())
        content_layout.addStretch()

        button_row = QHBoxLayout()
        button_row.addStretch()
        save_button = QPushButton("Save Bot Settings")
        save_button.clicked.connect(self._persist)  # pragma: no cover - Qt binding
        button_row.addWidget(save_button)
        root_layout.addLayout(button_row)

        self._status_label = QLabel("Defaults mirror settings.json and slash command behaviour.")
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        self.refresh(repository)

    # ------------------------------------------------------------------
    # UI construction helpers
    # ------------------------------------------------------------------
    def _build_model_group(self) -> QGroupBox:
        group = QGroupBox("Model & Asset Defaults")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        form.addRow("Global Default Model", self._model_combo)
        form.addRow("Preferred Flux Model", self._flux_combo)
        form.addRow("Preferred SDXL Model", self._sdxl_combo)
        form.addRow("Preferred Qwen Model", self._qwen_combo)
        form.addRow("T5 CLIP", self._t5_combo)
        form.addRow("CLIP-L", self._clip_l_combo)
        form.addRow("Upscale Model", self._upscale_model_combo)
        form.addRow("VAE", self._vae_combo)

        form.addRow("Default Flux Style", self._flux_style_combo)
        form.addRow("Default SDXL Style", self._sdxl_style_combo)
        form.addRow("Default Qwen Style", self._qwen_style_combo)

        return group

    def _build_generation_group(self) -> QGroupBox:
        group = QGroupBox("Generation Defaults")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        form.addRow("Flux Steps", self._steps_spin)
        form.addRow("Flux Guidance", self._guidance_spin)
        form.addRow("SDXL/Qwen Steps", self._sdxl_steps_spin)
        form.addRow("SDXL/Qwen Guidance", self._sdxl_guidance_spin)
        form.addRow("Default Batch Size", self._batch_size_spin)
        form.addRow("Target Megapixels", self._mp_size_spin)
        form.addRow("Upscale Factor", self._upscale_factor_spin)
        form.addRow("Default Edit Engine", self._default_engine_combo)
        form.addRow("SDXL Negative Prompt", self._sdxl_negative)
        form.addRow("Qwen Negative Prompt", self._qwen_negative)

        return group

    def _build_variation_group(self) -> QGroupBox:
        group = QGroupBox("Variation & Discord Display")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        form.addRow("Variation Mode", self._variation_mode_combo)
        form.addRow("Variation Batch Size", self._variation_batch_spin)
        form.addRow("Remix Mode", self._remix_checkbox)
        form.addRow("Prompt Display Preference", self._display_pref_combo)

        return group

    def _build_kontext_group(self) -> QGroupBox:
        group = QGroupBox("Kontext Edit Defaults")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        form.addRow("Kontext Steps", self._kontext_steps_spin)
        form.addRow("Kontext Guidance", self._kontext_guidance_spin)
        form.addRow("Kontext Target MP", self._kontext_mp_spin)

        return group

    def _build_llm_group(self) -> QGroupBox:
        group = QGroupBox("LLM Prompt Enhancer")
        form = QFormLayout(group)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        form.addRow("Status", self._llm_checkbox)
        form.addRow("Provider", self._llm_provider_combo)
        form.addRow("Provider Model", self._llm_model_combo)

        return group

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _populate_combo(self, combo: QComboBox, options: Iterable, current: str | None, *, allow_blank: bool = False) -> None:
        combo.blockSignals(True)
        combo.clear()
        if allow_blank:
            combo.addItem("(None)", "")
        seen_values: set[str] = set()
        for option in options:
            label = getattr(option, "label", None)
            value = getattr(option, "value", None)
            if label is None or value is None:
                continue
            if value in seen_values:
                continue
            combo.addItem(str(label), str(value))
            seen_values.add(str(value))
        if current:
            idx = combo.findData(current)
            if idx == -1:
                combo.addItem(current, current)
                idx = combo.findData(current)
            combo.setCurrentIndex(idx)
        elif combo.count():
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _set_status(self, message: str) -> None:
        self._status_label.setText(message)

    def _current_combo_value(self, combo: QComboBox) -> str | None:
        data = combo.currentData()
        if data in (None, ""):
            text = combo.currentText().strip()
            return text or None
        return str(data)

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------
    def _persist(self) -> None:  # pragma: no cover - Qt binding
        try:
            payload = {
                "selected_model": self._current_combo_value(self._model_combo),
                "preferred_model_flux": self._current_combo_value(self._flux_combo),
                "preferred_model_sdxl": self._current_combo_value(self._sdxl_combo),
                "preferred_model_qwen": self._current_combo_value(self._qwen_combo),
                "selected_t5_clip": self._current_combo_value(self._t5_combo),
                "selected_clip_l": self._current_combo_value(self._clip_l_combo),
                "selected_upscale_model": self._current_combo_value(self._upscale_model_combo),
                "selected_vae": self._current_combo_value(self._vae_combo),
                "default_style_flux": self._flux_style_combo.currentData() or self._flux_style_combo.currentText(),
                "default_style_sdxl": self._sdxl_style_combo.currentData() or self._sdxl_style_combo.currentText(),
                "default_style_qwen": self._qwen_style_combo.currentData() or self._qwen_style_combo.currentText(),
                "steps": self._steps_spin.value(),
                "sdxl_steps": self._sdxl_steps_spin.value(),
                "default_guidance": self._guidance_spin.value(),
                "default_guidance_sdxl": self._sdxl_guidance_spin.value(),
                "default_batch_size": self._batch_size_spin.value(),
                "variation_batch_size": self._variation_batch_spin.value(),
                "default_variation_mode": self._variation_mode_combo.currentData() or self._variation_mode_combo.currentText(),
                "remix_mode": self._remix_checkbox.isChecked(),
                "default_mp_size": self._mp_size_spin.value(),
                "upscale_factor": self._upscale_factor_spin.value(),
                "kontext_steps": self._kontext_steps_spin.value(),
                "kontext_guidance": self._kontext_guidance_spin.value(),
                "kontext_mp_size": self._kontext_mp_spin.value(),
                "display_prompt_preference": self._display_pref_combo.currentData()
                or self._display_pref_combo.currentText(),
                "default_edit_engine": self._default_engine_combo.currentText(),
                "default_sdxl_negative_prompt": self._sdxl_negative.toPlainText().strip(),
                "default_qwen_negative_prompt": self._qwen_negative.toPlainText().strip(),
                "llm_enhancer_enabled": self._llm_checkbox.isChecked(),
                "llm_provider": self._llm_provider_combo.currentData() or self._llm_provider_combo.currentText(),
            }

            provider = payload["llm_provider"] or "gemini"
            model_value = self._llm_model_combo.currentData() or self._llm_model_combo.currentText().strip()
            if provider == "gemini":
                payload["llm_model_gemini"] = model_value or None
            elif provider == "groq":
                payload["llm_model_groq"] = model_value or None
            elif provider == "openai":
                payload["llm_model_openai"] = model_value or None

            self._repository.save_settings(payload)
            self._set_status("Bot defaults saved.")
            self.refresh(self._repository)
        except Exception as exc:  # pragma: no cover - user feedback only
            QMessageBox.critical(self, "Save Failed", str(exc))
            self._set_status("Unable to save bot settings. See details above.")

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        settings = repository.settings

        model_options = get_model_choices(settings)
        self._populate_combo(self._model_combo, model_options, settings.get("selected_model"))
        flux_options = [opt for opt in model_options if str(getattr(opt, 'value', '')).lower().startswith('flux:')]
        sdxl_options = [opt for opt in model_options if str(getattr(opt, 'value', '')).lower().startswith('sdxl:')]
        qwen_options = [opt for opt in model_options if str(getattr(opt, 'value', '')).lower().startswith('qwen:')]
        self._populate_combo(self._flux_combo, flux_options or model_options, settings.get("preferred_model_flux"))
        self._populate_combo(self._sdxl_combo, sdxl_options or model_options, settings.get("preferred_model_sdxl"))
        self._populate_combo(self._qwen_combo, qwen_options or model_options, settings.get("preferred_model_qwen"))
        self._populate_combo(self._t5_combo, get_t5_clip_choices(settings), settings.get("selected_t5_clip"), allow_blank=True)
        self._populate_combo(self._clip_l_combo, get_clip_l_choices(settings), settings.get("selected_clip_l"), allow_blank=True)
        self._populate_combo(
            self._upscale_model_combo,
            get_upscale_model_choices(settings),
            settings.get("selected_upscale_model"),
            allow_blank=True,
        )
        self._populate_combo(
            self._vae_combo,
            get_vae_choices(settings),
            settings.get("selected_vae"),
            allow_blank=True,
        )

        self._populate_combo(self._flux_style_combo, get_style_choices_flux(settings), settings.get("default_style_flux"))
        self._populate_combo(self._sdxl_style_combo, get_style_choices_sdxl(settings), settings.get("default_style_sdxl"))
        self._populate_combo(self._qwen_style_combo, get_style_choices_qwen(settings), settings.get("default_style_qwen"))

        self._steps_spin.setValue(int(settings.get("steps", 32)))
        self._guidance_spin.setValue(float(settings.get("default_guidance", 3.5)))
        self._sdxl_steps_spin.setValue(int(settings.get("sdxl_steps", 40)))
        self._sdxl_guidance_spin.setValue(float(settings.get("default_guidance_sdxl", 7.0)))
        self._batch_size_spin.setValue(int(settings.get("default_batch_size", 1)))
        self._variation_batch_spin.setValue(int(settings.get("variation_batch_size", 1)))
        self._mp_size_spin.setValue(float(settings.get("default_mp_size", 1.0)))
        self._upscale_factor_spin.setValue(float(settings.get("upscale_factor", 1.85)))
        self._kontext_steps_spin.setValue(int(settings.get("kontext_steps", 32)))
        self._kontext_guidance_spin.setValue(float(settings.get("kontext_guidance", 3.0)))
        self._kontext_mp_spin.setValue(float(settings.get("kontext_mp_size", 1.15)))

        self._populate_combo(self._variation_mode_combo, get_variation_mode_choices(settings), settings.get("default_variation_mode"))
        self._populate_combo(
            self._display_pref_combo,
            get_display_prompt_preference_choices(settings),
            settings.get("display_prompt_preference", "enhanced"),
        )

        self._remix_checkbox.setChecked(bool(settings.get("remix_mode", False)))
        self._default_engine_combo.setCurrentText(str(settings.get("default_edit_engine", "kontext")))
        self._sdxl_negative.setPlainText(settings.get("default_sdxl_negative_prompt", ""))
        self._qwen_negative.setPlainText(settings.get("default_qwen_negative_prompt", ""))

        # LLM provider/model options
        self._llm_checkbox.setChecked(bool(settings.get("llm_enhancer_enabled", False)))
        self._populate_combo(
            self._llm_provider_combo,
            get_llm_provider_choices(settings),
            settings.get("llm_provider", "gemini"),
        )
        provider = self._llm_provider_combo.currentData() or self._llm_provider_combo.currentText()
        self._populate_combo(
            self._llm_model_combo,
            get_llm_model_choices(settings, provider=provider),
            settings.get(f"llm_model_{provider}", None),
            allow_blank=True,
        )

        self._set_status("Adjust defaults and save to update settings.json.")


__all__ = ["BotSettingsView"]
