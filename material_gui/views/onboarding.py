"""First-run onboarding dialog for the Material Configurator."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from material_gui.repository import SettingsRepository


class FirstRunSetupDialog(QDialog):
    """Interactive wizard that captures the minimum configuration required to run."""

    def __init__(self, repository: SettingsRepository, app_base_dir: Path, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Welcome to Tenos.ai Configurator")
        self.setModal(True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.resize(720, 500)

        self._repository = repository
        self._app_base_dir = app_base_dir
        self._skipped = False

        self._output_field = QLineEdit()
        self._token_field = QLineEdit()
        self._flux_combo = QComboBox()
        self._sdxl_combo = QComboBox()
        self._qwen_combo = QComboBox()
        self._summary_label = QLabel()

        self._token_field.setEchoMode(QLineEdit.Password)
        for combo in (self._flux_combo, self._sdxl_combo, self._qwen_combo):
            combo.setEditable(False)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 28, 32, 28)
        layout.setSpacing(18)

        header = QLabel("First-Time Setup")
        header.setObjectName("MaterialTitle")
        layout.addWidget(header)

        self._step_indicator = QLabel()
        self._step_indicator.setObjectName("MaterialSubtitle")
        layout.addWidget(self._step_indicator)

        self._stack = QStackedWidget()
        layout.addWidget(self._stack, stretch=1)

        self._stack.addWidget(self._build_welcome_page())
        self._stack.addWidget(self._build_output_page())
        self._stack.addWidget(self._build_discord_page())
        self._stack.addWidget(self._build_models_page())
        self._stack.addWidget(self._build_summary_page())

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._skip_button = QPushButton("Skip setup")
        self._skip_button.clicked.connect(self._handle_skip)  # pragma: no cover - UI binding
        controls.addWidget(self._skip_button)

        controls.addStretch()

        self._back_button = QPushButton("Back")
        self._back_button.clicked.connect(self._go_back)  # pragma: no cover - UI binding
        controls.addWidget(self._back_button)

        self._next_button = QPushButton("Next")
        self._next_button.setDefault(True)
        self._next_button.clicked.connect(self._go_forward)  # pragma: no cover - UI binding
        controls.addWidget(self._next_button)

        layout.addLayout(controls)

        self._prefill_fields()
        self._update_step_labels()

    # ------------------------------------------------------------------
    # Qt helpers
    # ------------------------------------------------------------------
    def was_skipped(self) -> bool:
        return self._skipped

    def reject(self) -> None:  # pragma: no cover - UI behaviour
        self._skipped = True
        super().reject()

    # ------------------------------------------------------------------
    # Page builders
    # ------------------------------------------------------------------
    def _build_welcome_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        title = QLabel("Let's get you ready")
        title.setObjectName("MaterialSubtitle")
        layout.addWidget(title)

        body = QLabel(
            "This short setup captures your preferred output folder, Discord bot token, "
            "and default model selections so Tenos.ai can start generating immediately."
        )
        body.setWordWrap(True)
        body.setObjectName("MaterialCard")
        layout.addWidget(body)

        tips = QLabel(
            "You can revisit any setting later via the Main Config or Bot Settings tabs."
        )
        tips.setWordWrap(True)
        layout.addWidget(tips)

        layout.addStretch(1)
        return page

    def _build_output_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._output_field.setPlaceholderText("Choose where images should be saved")
        browse_button = QPushButton("Browse…")
        browse_button.clicked.connect(self._browse_output_folder)  # pragma: no cover - UI binding
        row = QHBoxLayout()
        row.addWidget(self._output_field)
        row.addWidget(browse_button)
        form.addRow("Generation output", row)

        hint = QLabel(
            "Tip: The same folder will be used for generations, upscales, and variations."
        )
        hint.setWordWrap(True)
        form.addRow("", hint)
        return page

    def _build_discord_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        self._token_field.setPlaceholderText("Bot token from Discord developer portal")
        form.addRow("Discord bot token", self._token_field)

        notice = QLabel(
            "Your token is stored locally in config.json. Keep it secret to protect your bot."
        )
        notice.setWordWrap(True)
        form.addRow("", notice)
        return page

    def _build_models_page(self) -> QWidget:
        page = QWidget()
        form = QFormLayout(page)
        form.setLabelAlignment(Qt.AlignLeft | Qt.AlignVCenter)

        for combo, prefix in (
            (self._flux_combo, "Flux"),
            (self._sdxl_combo, "SDXL"),
            (self._qwen_combo, "Qwen"),
        ):
            combo.addItem("Use workflow default", None)
            combo.setObjectName(f"FirstRun{prefix}Model")

        form.addRow("Flux default", self._flux_combo)
        form.addRow("SDXL default", self._sdxl_combo)
        form.addRow("Qwen default", self._qwen_combo)

        helper = QLabel(
            "Set optional preferred checkpoints for quick access. You can adjust them later in Bot Settings."
        )
        helper.setWordWrap(True)
        form.addRow("", helper)
        return page

    def _build_summary_page(self) -> QWidget:
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setSpacing(12)

        title = QLabel("Review & Finish")
        title.setObjectName("MaterialSubtitle")
        layout.addWidget(title)

        self._summary_label.setWordWrap(True)
        self._summary_label.setObjectName("MaterialCard")
        layout.addWidget(self._summary_label)

        reminder = QLabel(
            "Click Finish to save these values. You can make changes at any time from the configuration tabs."
        )
        reminder.setWordWrap(True)
        layout.addWidget(reminder)

        layout.addStretch(1)
        return page

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _browse_output_folder(self) -> None:  # pragma: no cover - UI binding
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select output folder",
            str(self._app_base_dir),
        )
        if directory:
            self._output_field.setText(directory)

    def _go_forward(self) -> None:  # pragma: no cover - UI behaviour
        current = self._stack.currentIndex()
        if current >= self._stack.count() - 1:
            if self._apply_changes():
                self.accept()
            return
        self._stack.setCurrentIndex(current + 1)
        self._update_step_labels()
        self._update_summary_page()

    def _go_back(self) -> None:  # pragma: no cover - UI behaviour
        current = self._stack.currentIndex()
        if current <= 0:
            return
        self._stack.setCurrentIndex(current - 1)
        self._update_step_labels()
        self._update_summary_page()

    def _handle_skip(self) -> None:  # pragma: no cover - UI behaviour
        self._skipped = True
        super().reject()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _prefill_fields(self) -> None:
        config = self._repository.config or {}
        outputs = config.get("OUTPUTS", {}) if isinstance(config, dict) else {}
        generations = outputs.get("GENERATIONS") if isinstance(outputs, dict) else ""
        if isinstance(generations, str):
            self._output_field.setText(generations)

        bot_api = config.get("BOT_API", {}) if isinstance(config, dict) else {}
        token = bot_api.get("KEY") if isinstance(bot_api, dict) else ""
        if isinstance(token, str):
            self._token_field.setText(token)

        settings = self._repository.settings
        flux_options = self._repository.get_available_models("flux")
        sdxl_options = self._repository.get_available_models("sdxl")
        qwen_options = self._repository.get_available_models("qwen")

        self._populate_model_combo(self._flux_combo, flux_options, settings.get("preferred_model_flux"))
        self._populate_model_combo(self._sdxl_combo, sdxl_options, settings.get("preferred_model_sdxl"))
        self._populate_model_combo(self._qwen_combo, qwen_options, settings.get("preferred_model_qwen"))
        self._update_summary_page()

    def _populate_model_combo(self, combo: QComboBox, options: list[str], current: object) -> None:
        combo.blockSignals(True)
        combo.clear()
        combo.addItem("Use workflow default", None)

        seen: set[str] = set()
        for item in options:
            formatted = self._format_preference(combo, item)
            if formatted in seen:
                continue
            combo.addItem(formatted, formatted)
            seen.add(formatted)

        current_value = current if isinstance(current, str) and current.strip() else None
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

    def _update_step_labels(self) -> None:
        current = self._stack.currentIndex()
        total = self._stack.count()
        self._step_indicator.setText(f"Step {current + 1} of {total}")
        self._back_button.setEnabled(current > 0)
        self._next_button.setText("Finish" if current == total - 1 else "Next")

    def _update_summary_page(self) -> None:
        if self._stack.currentIndex() != self._stack.count() - 1:
            return
        output_path = self._output_field.text().strip() or "Not configured"
        flux = self._flux_combo.currentText()
        sdxl = self._sdxl_combo.currentText()
        qwen = self._qwen_combo.currentText()
        token_status = "Provided" if self._token_field.text().strip() else "Missing"
        lines = [
            f"Output folder: {output_path}",
            f"Flux default: {flux}",
            f"SDXL default: {sdxl}",
            f"Qwen default: {qwen}",
            f"Discord token: {token_status}",
        ]
        self._summary_label.setText("\n".join(lines))

    def _apply_changes(self) -> bool:
        output_path = self._output_field.text().strip()
        if not output_path:
            QMessageBox.warning(self, "Output Folder Required", "Choose where images should be saved.")
            self._stack.setCurrentIndex(1)
            self._update_step_labels()
            return False

        token_value = self._token_field.text().strip()
        if not token_value:
            QMessageBox.warning(self, "Bot Token Required", "Enter your Discord bot token to continue.")
            self._stack.setCurrentIndex(2)
            self._update_step_labels()
            return False

        try:
            path_obj = Path(output_path).expanduser().resolve()
            path_obj.mkdir(parents=True, exist_ok=True)
        except Exception as exc:  # pragma: no cover - filesystem guard
            QMessageBox.critical(self, "Folder Error", f"Unable to prepare output folder: {exc}")
            self._stack.setCurrentIndex(1)
            self._update_step_labels()
            return False

        config_payload = {
            "OUTPUTS": {
                "GENERATIONS": str(path_obj),
                "UPSCALES": str(path_obj),
                "VARIATIONS": str(path_obj),
            },
            "BOT_API": {"KEY": token_value},
        }
        try:
            self._repository.save_config(config_payload)
        except Exception as exc:  # pragma: no cover - disk guard
            QMessageBox.critical(self, "Save Failed", f"Unable to save configuration: {exc}")
            return False

        settings_payload = {
            "preferred_model_flux": self._flux_combo.currentData(),
            "preferred_model_sdxl": self._sdxl_combo.currentData(),
            "preferred_model_qwen": self._qwen_combo.currentData(),
        }
        try:
            self._repository.save_settings(settings_payload)
        except Exception as exc:  # pragma: no cover - disk guard
            QMessageBox.critical(self, "Save Failed", f"Unable to save settings: {exc}")
            return False

        return True


__all__ = ["FirstRunSetupDialog"]
