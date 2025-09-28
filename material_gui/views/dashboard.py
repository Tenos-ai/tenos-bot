"""Dashboard view exposing quick configuration controls."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository
from material_gui.views.base import BaseView


class DashboardView(BaseView):
    """Surface high value controls and status information on launch."""

    def __init__(
        self,
        repository: SettingsRepository,
        *,
        app_base_dir: Path,
        on_open_outputs: Callable[[], None] | None = None,
        status_callback: Callable[[str], None] | None = None,
        start_callback: Callable[[], None] | None = None,
        stop_callback: Callable[[], None] | None = None,
        running_state_provider: Callable[[], bool] | None = None,
    ) -> None:
        super().__init__()
        self._repository = repository
        self._app_base_dir = app_base_dir
        self._open_outputs_callback = on_open_outputs or (lambda: None)
        self._status_callback = status_callback or (lambda _message: None)
        self._start_callback = start_callback
        self._stop_callback = stop_callback
        self._running_state_provider = running_state_provider
        self._loading_models = False

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(24, 24, 24, 24)
        root_layout.setSpacing(18)

        title = QLabel("Dashboard")
        title.setObjectName("MaterialTitle")
        root_layout.addWidget(title)

        description = QLabel(
            "Review key configuration at a glance and adjust the most common bot "
            "settings without digging through separate tabs."
        )
        description.setWordWrap(True)
        description.setObjectName("MaterialCard")
        root_layout.addWidget(description)

        self._summary_label = QLabel()
        self._summary_label.setObjectName("MaterialCard")
        self._summary_label.setWordWrap(True)
        root_layout.addWidget(self._summary_label)

        runtime_box = QGroupBox("Bot Runtime")
        runtime_layout = QVBoxLayout(runtime_box)
        runtime_layout.setSpacing(10)
        runtime_buttons = QHBoxLayout()
        runtime_buttons.setSpacing(12)

        self._runtime_toggle_button = QPushButton("Start Bot")
        self._runtime_toggle_button.clicked.connect(self._handle_toggle_clicked)  # pragma: no cover - Qt binding
        runtime_buttons.addWidget(self._runtime_toggle_button)
        runtime_buttons.addStretch(1)

        runtime_layout.addLayout(runtime_buttons)

        self._runtime_status_label = QLabel("Bot idle.")
        self._runtime_status_label.setObjectName("MaterialCard")
        self._runtime_status_label.setWordWrap(True)
        runtime_layout.addWidget(self._runtime_status_label)

        root_layout.addWidget(runtime_box)

        quick_box = QGroupBox("Quick Settings")
        quick_form = QFormLayout(quick_box)
        quick_form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        quick_form.setFormAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        root_layout.addWidget(quick_box)

        output_row = QHBoxLayout()
        self._output_path_label = QLabel("Not configured")
        self._output_path_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        output_row.addWidget(self._output_path_label, stretch=1)

        change_button = QPushButton("Change…")
        change_button.clicked.connect(self._select_output_folder)  # pragma: no cover - Qt binding
        output_row.addWidget(change_button)

        open_button = QPushButton("Open Folder")
        open_button.clicked.connect(self._open_outputs_callback)  # pragma: no cover - Qt binding
        output_row.addWidget(open_button)
        quick_form.addRow("Generation output", output_row)

        self._flux_combo = self._build_model_combo("Flux")
        quick_form.addRow("Flux default", self._flux_combo)

        self._sdxl_combo = self._build_model_combo("SDXL")
        quick_form.addRow("SDXL default", self._sdxl_combo)

        self._qwen_combo = self._build_model_combo("Qwen")
        quick_form.addRow("Qwen default", self._qwen_combo)

        self._status_label = QLabel()
        self._status_label.setObjectName("MaterialCard")
        self._status_label.setWordWrap(True)
        root_layout.addWidget(self._status_label)

        root_layout.addStretch(1)

        self.refresh(self._repository)

    # ------------------------------------------------------------------
    def _build_model_combo(self, label: str) -> QComboBox:
        combo = QComboBox()
        combo.setObjectName(f"ModelPreference{label}")
        combo.currentIndexChanged.connect(self._handle_model_change)  # pragma: no cover - Qt binding
        return combo

    def _handle_model_change(self) -> None:  # pragma: no cover - Qt binding
        if self._loading_models:
            return
        sender = self.sender()
        if not isinstance(sender, QComboBox):
            return

        key_map = {
            self._flux_combo: ("preferred_model_flux", "Flux"),
            self._sdxl_combo: ("preferred_model_sdxl", "SDXL"),
            self._qwen_combo: ("preferred_model_qwen", "Qwen"),
        }
        if sender not in key_map:
            return
        setting_key, prefix = key_map[sender]
        value = sender.currentData()
        payload = {setting_key: value}
        try:
            self._repository.save_settings(payload)
        except Exception as exc:  # pragma: no cover - user feedback
            self._status_label.setText(f"Unable to save {prefix} preference: {exc}")
            return

        if value:
            self._status_label.setText(f"{prefix} default updated to {sender.currentText()}.")
            self._status_callback(f"{prefix} default saved")
        else:
            self._status_label.setText(f"{prefix} default cleared. Bot will use workflow suggestions.")
            self._status_callback(f"{prefix} default cleared")

        self._update_summary()

    def _select_output_folder(self) -> None:  # pragma: no cover - Qt binding
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            str(self._app_base_dir),
        )
        if not directory:
            return

        path = Path(directory).expanduser().resolve()
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - filesystem issues rare
            self._status_label.setText(f"Unable to prepare output folder: {exc}")
            return

        update_payload = {
            "OUTPUTS": {
                "GENERATIONS": str(path),
                "UPSCALES": str(path),
                "VARIATIONS": str(path),
            }
        }
        try:
            self._repository.save_config(update_payload)
        except Exception as exc:  # pragma: no cover - user feedback
            self._status_label.setText(f"Failed to save output folder: {exc}")
            return

        self._output_path_label.setText(str(path))
        self._status_label.setText(f"Output folder set to {path}.")
        self._status_callback("Output folder updated")
        self._update_summary()

    def _populate_model_combo(self, combo: QComboBox, models: list[str], current_value: str | None) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Use workflow default", None)

        seen: set[str] = set()
        for model in models:
            formatted = self._format_preference(combo, model)
            if formatted in seen:
                continue
            combo.addItem(formatted, formatted)
            seen.add(formatted)

        if current_value and current_value not in seen:
            combo.addItem(current_value, current_value)

        if current_value:
            index = combo.findData(current_value)
            combo.setCurrentIndex(index if index >= 0 else 0)
        else:
            combo.setCurrentIndex(0)
        combo.blockSignals(False)

    def _format_preference(self, combo: QComboBox, value: str) -> str:
        prefix_map = {
            self._flux_combo: "Flux: ",
            self._sdxl_combo: "SDXL: ",
            self._qwen_combo: "Qwen: ",
        }
        prefix = prefix_map.get(combo, "")
        value = value.strip()
        if value.lower().startswith(prefix.strip().lower()):
            return value
        if ":" in value:
            value = value.split(":", 1)[-1].strip()
        return f"{prefix}{value}" if prefix else value

    def _update_summary(self) -> None:
        output_display = self._output_display_value() or "Not configured"

        summary_lines = [
            f"Output folder: {output_display}",
            f"Flux default: {self._flux_combo.currentText()}",
            f"SDXL default: {self._sdxl_combo.currentText()}",
            f"Qwen default: {self._qwen_combo.currentText()}",
        ]
        self._summary_label.setText("\n".join(summary_lines))

    def _handle_toggle_clicked(self) -> None:  # pragma: no cover - Qt binding
        running = self._running_state()
        if running:
            if self._stop_callback is None:
                self._status_label.setText("Stop control unavailable. Open Bot Control to manage runtime.")
                return
            self._status_label.setText("Attempting to stop the bot…")
            self._status_callback("Stopping bot…")
            try:
                self._stop_callback()
            except Exception as exc:  # pragma: no cover - safety net
                self._status_label.setText(f"Unable to stop bot: {exc}")
                self._status_callback("Bot stop failed")
                return
            self._status_label.setText("Stop command sent. The bot will shut down shortly.")
            self._status_callback("Bot stop requested")
        else:
            if self._start_callback is None:
                self._status_label.setText("Start control unavailable. Open Bot Control to manage runtime.")
                return
            self._status_label.setText("Attempting to start the bot…")
            self._status_callback("Launching bot…")
            try:
                self._start_callback()
            except Exception as exc:  # pragma: no cover - safety net
                self._status_label.setText(f"Unable to start bot: {exc}")
                self._status_callback("Bot launch failed")
                return
            self._status_label.setText("Start command sent. Watch Bot Control for logs.")
            self._status_callback("Bot start requested")
        self._update_runtime_controls()

    def _running_state(self) -> bool:
        if self._running_state_provider is None:
            return False
        try:
            return bool(self._running_state_provider())
        except Exception as exc:  # pragma: no cover - defensive guard
            self._status_label.setText(f"Unable to read bot status: {exc}")
            return False

    def _update_runtime_controls(self, *, running: bool | None = None) -> None:
        if running is None:
            running = self._running_state()

        can_toggle = (
            (self._start_callback is not None and not running)
            or (self._stop_callback is not None and running)
        )

        self._runtime_toggle_button.setEnabled(can_toggle)
        self._runtime_toggle_button.setText("Stop Bot" if running else "Start Bot")
        self._runtime_status_label.setText("Bot is running." if running else "Bot idle.")

    def set_runtime_state(self, running: bool) -> None:
        self._update_runtime_controls(running=running)

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def refresh(self, repository: SettingsRepository) -> None:  # pragma: no cover - UI wiring
        self._repository = repository
        display_path = self._output_display_value()
        self._output_path_label.setText(display_path or "Not configured")

        settings = repository.settings
        flux_options = repository.get_available_models("flux")
        sdxl_options = repository.get_available_models("sdxl")
        qwen_options = repository.get_available_models("qwen")

        self._loading_models = True
        try:
            self._populate_model_combo(self._flux_combo, flux_options, self._coerce_setting(settings.get("preferred_model_flux")))
            self._populate_model_combo(self._sdxl_combo, sdxl_options, self._coerce_setting(settings.get("preferred_model_sdxl")))
            self._populate_model_combo(self._qwen_combo, qwen_options, self._coerce_setting(settings.get("preferred_model_qwen")))
        finally:
            self._loading_models = False

        self._status_label.setText("Ready.")
        self._update_summary()
        self._update_runtime_controls()

    def _coerce_setting(self, value: object) -> str | None:
        if not isinstance(value, str):
            return None
        return value.strip() or None

    def _output_display_value(self) -> str:
        config = self._repository.config or {}
        outputs = config.get("OUTPUTS", {}) if isinstance(config, dict) else {}
        generations = outputs.get("GENERATIONS") if isinstance(outputs, dict) else None
        if isinstance(generations, str) and generations.strip():
            path = Path(generations).expanduser()
            if not path.is_absolute():
                path = (self._app_base_dir / path).resolve()
            return str(path)
        return ""


__all__ = ["DashboardView"]
