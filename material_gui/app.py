"""Material-themed Configurator shell built with PySide6."""
from __future__ import annotations

from dataclasses import dataclass
import os
import subprocess
import sys
import webbrowser
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Callable, Optional

from PySide6.QtCore import Qt, QTimer, QPoint, QEvent, QSize
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFrame,
    QGraphicsDropShadowEffect,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QStyle,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from comfyui_api import ConnectionRefusedError, queue_prompt as comfy_queue_prompt
from controllers import UpdateCoordinator
from material_gui.animations import AnimatedStackedWidget, StatusPulseAnimator
from material_gui.repository import SettingsRepository
from material_gui.theme import (
    CUSTOM_PALETTE_KEY,
    PALETTES,
    build_stylesheet,
    resolve_theme_variant,
)
from material_gui.views import (
    ActivityLogView,
    AppearanceSettingsView,
    DiscordSettingsView,
    NetworkMonitorView,
    OverviewView,
    QwenSettingsView,
    SystemStatusView,
    WorkflowsView,
    MainConfigView,
    BotSettingsView,
    LoraStylesView,
    FavoritesView,
    LlmPromptsView,
    BotControlView,
    ToolsView,
)
from material_gui.views.onboarding import FirstRunTutorialDialog
from services import (
    WorkflowLibraryService,
    collect_system_diagnostics,
    collect_usage_analytics,
)
from services.system_diagnostics import DiagnosticsReport
from version_info import APP_VERSION


@dataclass(slots=True)
class NavigationEntry:
    """Describes a navigation destination inside the configurator."""

    title: str
    slug: str
    view: QWidget
    on_selected: Optional[Callable[[], None]] = None


class MaterialConfigWindow(QMainWindow):
    """Modernised configurator shell using Material-inspired widgets."""

    def __init__(self, repository: SettingsRepository, app_base_dir: Path) -> None:
        super().__init__()
        self._repository = repository
        self._app_base_dir = app_base_dir
        worker_count = max(2, min(4, os.cpu_count() or 2))
        self._executor = ThreadPoolExecutor(max_workers=worker_count, thread_name_prefix="config-worker")
        self._workflow_service = WorkflowLibraryService()
        self._pending_status_message: Optional[str] = None
        self._coordinator = UpdateCoordinator(
            repo_owner="Tenos-ai",
            repo_name="Tenos-Bot",
            current_version=APP_VERSION,
            app_base_dir=str(self._app_base_dir),
            log_callback=self._handle_update_log,
        )
        self._update_in_progress = False

        theme_preferences = self._repository.get_theme_preferences()
        mode = str(theme_preferences.get("mode", "dark")).strip().lower()
        palette = str(theme_preferences.get("palette", "oceanic")).strip().lower()
        valid_palettes = set(PALETTES.keys()) | {CUSTOM_PALETTE_KEY}
        self._theme_mode = mode if mode in {"light", "dark"} else "dark"
        self._theme_palette = palette if palette in valid_palettes else "oceanic"
        self._theme_custom_primary = str(theme_preferences.get("custom_primary", "#2563EB"))
        self._theme_custom_surface = str(theme_preferences.get("custom_surface", "#0F172A"))
        self._theme_custom_text = str(theme_preferences.get("custom_text", "#F1F5F9"))
        self._current_variant = None

        self.setWindowTitle("Tenos.ai Configurator – Material Edition")
        self.resize(1320, 860)
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowMinMaxButtonsHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        self._drag_active = False
        self._drag_offset = QPoint()

        central = QWidget()
        outer_layout = QVBoxLayout(central)
        outer_layout.setContentsMargins(28, 28, 28, 28)
        outer_layout.setSpacing(0)

        self._surface = QFrame()
        self._surface.setObjectName("MaterialSurface")
        surface_shadow = QGraphicsDropShadowEffect(self._surface)
        surface_shadow.setBlurRadius(48)
        surface_shadow.setColor(QColor(15, 23, 42, 140))
        surface_shadow.setOffset(0, 18)
        self._surface.setGraphicsEffect(surface_shadow)

        surface_layout = QVBoxLayout(self._surface)
        surface_layout.setContentsMargins(0, 0, 0, 0)
        surface_layout.setSpacing(0)

        outer_layout.addWidget(self._surface)

        self._build_top_bar(surface_layout)
        self._build_body(surface_layout)

        self.setCentralWidget(central)
        self._apply_material_theme()

        self._run_diagnostics()  # prime diagnostics on launch
        self._set_status("Ready")
        QTimer.singleShot(250, self._maybe_run_auto_update)  # pragma: no cover - startup hook
        QTimer.singleShot(400, self._maybe_show_first_run_tutorial)  # pragma: no cover - startup hook

    # ------------------------------------------------------------------
    # Qt construction helpers
    # ------------------------------------------------------------------
    def _build_top_bar(self, parent_layout: QVBoxLayout) -> None:
        self._title_bar = QWidget()
        self._title_bar.setObjectName("MaterialTitleBar")
        self._title_bar.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        bar_layout = QHBoxLayout(self._title_bar)
        bar_layout.setContentsMargins(32, 22, 24, 16)
        bar_layout.setSpacing(18)

        title_container = QVBoxLayout()
        title_container.setSpacing(2)
        title = QLabel("Tenos.ai Configurator")
        title.setObjectName("MaterialAppTitle")
        subtitle = QLabel(f"Material Interface • v{APP_VERSION}")
        subtitle.setObjectName("MaterialSubtitle")
        title_container.addWidget(title)
        title_container.addWidget(subtitle)
        bar_layout.addLayout(title_container)

        bar_layout.addStretch(1)

        self.status_chip = QLabel("Ready")
        self.status_chip.setObjectName("StatusChip")
        self.status_chip.setAlignment(Qt.AlignCenter)
        bar_layout.addWidget(self.status_chip)
        if self._pending_status_message:
            self.status_chip.setText(self._pending_status_message)
            self._pending_status_message = None
        self._status_pulse = StatusPulseAnimator(self.status_chip)

        quick_actions = QWidget()
        quick_actions.setObjectName("QuickActions")
        quick_actions.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        quick_layout = QHBoxLayout(quick_actions)
        quick_layout.setContentsMargins(14, 6, 14, 6)
        quick_layout.setSpacing(8)

        self.refresh_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_BrowserReload),
            "Refresh configuration from disk",
            self._handle_refresh,
        )
        quick_layout.addWidget(self.refresh_button)

        self.update_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_ArrowUp),
            "Check for Tenos.ai bot updates",
            self._handle_update,
        )
        quick_layout.addWidget(self.update_button)

        self.diagnostics_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_MessageBoxInformation),
            "Run diagnostics",
            self._run_diagnostics,
        )
        quick_layout.addWidget(self.diagnostics_button)

        self.outputs_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_DirOpenIcon),
            "Open generation outputs",
            self._open_outputs,
        )
        quick_layout.addWidget(self.outputs_button)

        self.config_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_DirHomeIcon),
            "Open application directory",
            self._open_config_dir,
        )
        quick_layout.addWidget(self.config_button)

        self.logs_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_FileDialogDetailedView),
            "View latest logs",
            self._open_logs_dir,
        )
        quick_layout.addWidget(self.logs_button)

        self.docs_button = self._create_icon_button(
            self.style().standardIcon(QStyle.SP_DialogHelpButton),
            "Open Qwen workflow guide",
            self._open_qwen_docs,
        )
        quick_layout.addWidget(self.docs_button)

        bar_layout.addWidget(quick_actions)

        bar_layout.addSpacing(12)

        window_controls = QHBoxLayout()
        window_controls.setContentsMargins(0, 0, 0, 0)
        window_controls.setSpacing(4)

        self._minimize_button = self._create_window_control(QStyle.SP_TitleBarMinButton, self.showMinimized)
        window_controls.addWidget(self._minimize_button)

        self._maximize_button = self._create_window_control(QStyle.SP_TitleBarMaxButton, self._toggle_maximize_state)
        window_controls.addWidget(self._maximize_button)

        self._close_button = self._create_window_control(QStyle.SP_TitleBarCloseButton, self.close)
        window_controls.addWidget(self._close_button)

        bar_layout.addLayout(window_controls)

        parent_layout.addWidget(self._title_bar)
        self._title_bar.installEventFilter(self)

    def _build_body(self, parent_layout: QVBoxLayout) -> None:
        body = QHBoxLayout()
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)

        nav_container = QFrame()
        nav_container.setObjectName("NavigationRail")
        nav_container.setFixedWidth(268)
        nav_container.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        nav_layout = QVBoxLayout(nav_container)
        nav_layout.setContentsMargins(22, 28, 22, 28)
        nav_layout.setSpacing(18)

        nav_header = QLabel("Workspace")
        nav_header.setObjectName("NavigationHeading")
        nav_layout.addWidget(nav_header)

        self.nav_list = QListWidget()
        self.nav_list.setObjectName("MaterialNav")
        self.nav_list.setVerticalScrollMode(QListWidget.ScrollPerPixel)
        self.nav_list.setFocusPolicy(Qt.NoFocus)
        self.nav_list.setIconSize(QSize(18, 18))
        nav_layout.addWidget(self.nav_list, stretch=1)

        nav_footer = QWidget()
        nav_footer.setObjectName("NavigationFooter")
        footer_layout = QHBoxLayout(nav_footer)
        footer_layout.setContentsMargins(12, 10, 12, 10)
        footer_layout.setSpacing(12)

        self.theme_toggle = QToolButton()
        self.theme_toggle.setObjectName("ThemeToggle")
        self.theme_toggle.setCheckable(True)
        self.theme_toggle.toggled.connect(self._toggle_theme)  # pragma: no cover - Qt binding
        self.theme_toggle.setToolButtonStyle(Qt.ToolButtonTextOnly)
        self.theme_toggle.setCursor(Qt.PointingHandCursor)
        footer_layout.addWidget(self.theme_toggle)

        version_label = QLabel(f"v{APP_VERSION}")
        version_label.setObjectName("NavVersion")
        footer_layout.addWidget(version_label)
        footer_layout.addStretch(1)

        nav_layout.addWidget(nav_footer)

        body.addWidget(nav_container)

        self.stack = AnimatedStackedWidget()
        body.addWidget(self.stack)

        parent_layout.addLayout(body)

        # Instantiate views
        self.overview_view = OverviewView(self._repository)
        self.discord_view = DiscordSettingsView(self._repository)
        self.appearance_view = AppearanceSettingsView(
            self._repository,
            on_palette_change=self._handle_theme_palette_update,
            on_mode_change=self._handle_theme_mode_update,
        )
        self.qwen_view = QwenSettingsView(self._repository)
        self.system_view = SystemStatusView()
        self.activity_view = ActivityLogView(self._app_base_dir / "update_log.txt")
        self.analytics_view = NetworkMonitorView()
        self.workflows_view = WorkflowsView(
            service=self._workflow_service,
            repository=self._repository,
            app_base_dir=self._app_base_dir,
            queue_callback=self._queue_workflow,
            export_callback=self._export_workflow,
            export_all_callback=self._export_all_workflows,
        )
        self.main_config_view = MainConfigView(self._repository, self._app_base_dir)
        self.bot_settings_view = BotSettingsView(self._repository)
        self.lora_styles_view = LoraStylesView()
        self.favorites_view = FavoritesView()
        self.llm_prompts_view = LlmPromptsView()
        self.bot_control_view = BotControlView(self._app_base_dir)
        self.tools_view = ToolsView(self._repository)


        icon_map = {
            "overview": QStyle.SP_ComputerIcon,
            "main-config": QStyle.SP_FileIcon,
            "bot-settings": QStyle.SP_DialogApplyButton,
            "lora-styles": QStyle.SP_FileDialogListView,
            "favorites": QStyle.SP_DialogYesButton,
            "llm-prompts": QStyle.SP_FileDialogContentsView,
            "qwen": QStyle.SP_DialogOpenButton,
            "discord": QStyle.SP_DialogOkButton,
            "appearance": QStyle.SP_DialogResetButton,
            "system": QStyle.SP_DesktopIcon,
            "activity": QStyle.SP_FileDialogDetailedView,
            "admin": QStyle.SP_BrowserStop,
            "workflows": QStyle.SP_DialogSaveButton,
            "tools": QStyle.SP_TrashIcon,
            "bot-control": QStyle.SP_MediaPlay,
        }

        self._nav_entries = [
            NavigationEntry(
                "Overview",
                "overview",
                self.overview_view,
                lambda: self.overview_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Main Config",
                "main-config",
                self.main_config_view,
                lambda: self.main_config_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Bot Settings",
                "bot-settings",
                self.bot_settings_view,
                lambda: self.bot_settings_view.refresh(self._repository),
            ),
            NavigationEntry(
                "LoRA Styles",
                "lora-styles",
                self.lora_styles_view,
                lambda: self.lora_styles_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Favorites",
                "favorites",
                self.favorites_view,
                lambda: self.favorites_view.refresh(self._repository),
            ),
            NavigationEntry(
                "LLM Prompts",
                "llm-prompts",
                self.llm_prompts_view,
                lambda: self.llm_prompts_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Qwen",
                "qwen",
                self.qwen_view,
                lambda: self.qwen_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Discord",
                "discord",
                self.discord_view,
                lambda: self.discord_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Appearance",
                "appearance",
                self.appearance_view,
                lambda: self.appearance_view.refresh(self._repository),
            ),
            NavigationEntry("System", "system", self.system_view, None),
            NavigationEntry(
                "Activity",
                "activity",
                self.activity_view,
                self.activity_view.refresh,
            ),
            NavigationEntry("Admin", "admin", self.analytics_view, None),
            NavigationEntry(
                "Workflows",
                "workflows",
                self.workflows_view,
                lambda: self.workflows_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Tools",
                "tools",
                self.tools_view,
                lambda: self.tools_view.refresh(self._repository),
            ),
            NavigationEntry(
                "Bot Control",
                "bot-control",
                self.bot_control_view,
                lambda: self.bot_control_view.refresh(self._repository),
            ),
        ]

        for entry in self._nav_entries:
            item = QListWidgetItem(entry.title)
            item.setData(Qt.UserRole, entry.slug)
            icon_role = icon_map.get(entry.slug)
            if icon_role is not None:
                item.setIcon(self.style().standardIcon(icon_role))
            self.nav_list.addItem(item)
            self.stack.addWidget(entry.view)

        self.nav_list.currentRowChanged.connect(self._handle_nav_change)  # pragma: no cover - Qt binding
        self.nav_list.setCurrentRow(0)

        self._update_maximize_button_icon()

    def _create_icon_button(self, icon, tooltip: str, callback: Callable[[], None]) -> QToolButton:
        button = QToolButton()
        button.setObjectName("IconButton")
        button.setToolTip(tooltip)
        button.setIcon(icon)
        button.setIconSize(QSize(22, 22))
        button.setCursor(Qt.PointingHandCursor)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.clicked.connect(callback)  # pragma: no cover - Qt binding
        return button

    def _create_window_control(self, standard_icon: QStyle.StandardPixmap, callback: Callable[[], None]) -> QToolButton:
        button = QToolButton()
        button.setObjectName("WindowControl")
        button.setIcon(self.style().standardIcon(standard_icon))
        button.setIconSize(QSize(16, 16))
        button.setCursor(Qt.PointingHandCursor)
        button.setToolButtonStyle(Qt.ToolButtonIconOnly)
        button.clicked.connect(callback)  # pragma: no cover - Qt binding
        return button

    def _toggle_maximize_state(self) -> None:  # pragma: no cover - Qt binding
        if self.isMaximized():
            self.showNormal()
        else:
            self.showMaximized()
        self._update_maximize_button_icon()

    def _update_maximize_button_icon(self) -> None:
        if not hasattr(self, "_maximize_button"):
            return
        icon_role = QStyle.SP_TitleBarNormalButton if self.isMaximized() else QStyle.SP_TitleBarMaxButton
        self._maximize_button.setIcon(self.style().standardIcon(icon_role))

    def _update_theme_toggle_icon(self) -> None:
        if not hasattr(self, "theme_toggle"):
            return
        is_light = self._theme_mode == "light"
        self.theme_toggle.setText("☀" if is_light else "🌙")
        self.theme_toggle.setToolTip("Switch to dark mode" if is_light else "Switch to light mode")
        self.theme_toggle.setProperty("mode", "light" if is_light else "dark")
        self.theme_toggle.style().unpolish(self.theme_toggle)
        self.theme_toggle.style().polish(self.theme_toggle)
        self.theme_toggle.update()

    def eventFilter(self, obj, event):
        if obj is getattr(self, "_title_bar", None):
            if event.type() == QEvent.MouseButtonDblClick and event.button() == Qt.LeftButton:
                child = obj.childAt(int(event.position().x()), int(event.position().y()))
                if isinstance(child, (QToolButton, QPushButton)):
                    return False
                self._toggle_maximize_state()
                return True
            if event.type() == QEvent.MouseButtonPress and event.button() == Qt.LeftButton:
                child = obj.childAt(int(event.position().x()), int(event.position().y()))
                if isinstance(child, (QToolButton, QPushButton)) or self.isMaximized():
                    return False
                self._drag_active = True
                self._drag_offset = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
                return True
            if event.type() == QEvent.MouseMove and self._drag_active:
                if not self.isMaximized():
                    self.move(event.globalPosition().toPoint() - self._drag_offset)
                return True
            if event.type() == QEvent.MouseButtonRelease and event.button() == Qt.LeftButton:
                self._drag_active = False
                return True
        return super().eventFilter(obj, event)

    def changeEvent(self, event):  # pragma: no cover - Qt lifecycle
        if event.type() == QEvent.WindowStateChange:
            QTimer.singleShot(0, self._update_maximize_button_icon)
        super().changeEvent(event)

    # ------------------------------------------------------------------
    # Event handlers
    # ------------------------------------------------------------------
    def _handle_refresh(self) -> None:  # pragma: no cover - Qt binding
        self._set_status("Refreshing configuration…")

        def task() -> None:
            self._repository.refresh()

        def on_success(_result: None) -> None:
            for entry in self._nav_entries:
                if entry.on_selected is not None:
                    entry.on_selected()
            current_item = self.nav_list.currentItem()
            if current_item and current_item.data(Qt.UserRole) == "admin":
                self._run_usage_analytics()
            self._set_status("Configuration refreshed")

        self._run_async(task, on_success, self._handle_task_error)

    def _handle_nav_change(self, index: int) -> None:  # pragma: no cover - Qt binding
        if index >= 0:
            self.stack.setCurrentIndex(index)
            entry = self._nav_entries[index]
            if entry.on_selected is not None:
                entry.on_selected()
            if entry.slug == "admin":
                self._run_usage_analytics()

    def _handle_update(self) -> None:  # pragma: no cover - Qt binding
        self._begin_update(status_message="Checking for updates…", initiated_by_auto=False)

    def _maybe_show_first_run_tutorial(self) -> None:  # pragma: no cover - UI hook
        if self._repository.has_completed_onboarding():
            return

        dialog = FirstRunTutorialDialog(self)
        dialog.exec()
        self._repository.mark_onboarding_completed()

        if dialog.was_skipped():
            self._set_status("Tutorial skipped")
        else:
            self._set_status("Walkthrough complete")

        QTimer.singleShot(2000, lambda: self._set_status("Ready"))

    def _maybe_run_auto_update(self) -> None:
        config_data = self._repository.config
        config = config_data if isinstance(config_data, dict) else {}
        auto_flag = bool(config.get("AUTO_UPDATE_ON_STARTUP"))
        if not self._coordinator.should_run_auto_update(auto_flag):
            return
        self._begin_update(status_message="Auto-checking for updates…", initiated_by_auto=True)

    def _begin_update(self, *, status_message: str, initiated_by_auto: bool) -> None:
        if self._update_in_progress:
            if not initiated_by_auto:
                self._show_error("Update In Progress", "An update check is already running.")
            return

        self._update_in_progress = True
        self._set_status(status_message)

        def task():
            return self._coordinator.download_latest_release()

        def on_success(result) -> None:
            self._update_in_progress = False
            if result.message:
                self._set_status(result.message)
            if result.requires_restart and result.update_info:
                self._handoff_update(result.update_info)

        def on_error(error: Exception) -> None:
            self._update_in_progress = False
            self._handle_task_error(error)

        self._run_async(task, on_success, on_error)

    # ------------------------------------------------------------------
    # Backend integrations
    # ------------------------------------------------------------------
    def _run_diagnostics(self) -> None:  # pragma: no cover - Qt binding
        self.system_view.show_loading()
        self._set_status("Collecting diagnostics…")

        def task() -> DiagnosticsReport:
            return collect_system_diagnostics(
                app_base_dir=str(self._app_base_dir),
                settings=self._repository.settings,
                workflow_service=self._workflow_service,
            )

        def on_success(report: DiagnosticsReport) -> None:
            self.system_view.show_report(report)
            self._set_status("Diagnostics updated")

        self._run_async(task, on_success, self._handle_task_error)

    def _queue_workflow(self, slug: str) -> None:
        descriptor = self._workflow_service.get_workflow(slug)
        if descriptor is None:
            self.workflows_view.set_status("Select a workflow to queue.")
            return

        self.workflows_view.set_status("Queueing workflow in ComfyUI…")
        self._set_status("Queueing curated workflow…")

        def task() -> Optional[str]:
            return comfy_queue_prompt(descriptor.build_template())

        def on_success(prompt_id: Optional[str]) -> None:
            if prompt_id:
                self.workflows_view.set_status(f"Workflow queued (Prompt ID: {prompt_id})")
                self._set_status(f"Workflow queued – prompt {prompt_id}")
            else:
                self.workflows_view.set_status("Workflow queued, awaiting ComfyUI response…")
                self._set_status("Workflow queued")

        def on_error(exc: Exception) -> None:
            if isinstance(exc, ConnectionRefusedError):
                message = "Unable to reach ComfyUI. Ensure it is running and the API port is correct."
            else:
                message = str(exc)
            self.workflows_view.set_status(f"Queue failed: {message}")
            self._show_error("Queue Failed", message)
            self._set_status("Action failed")

        self._run_async(task, on_success, on_error)

    def _run_usage_analytics(self) -> None:
        self.analytics_view.show_loading()
        self._set_status("Collecting network analytics…")

        def task():
            return collect_usage_analytics(log_dir=self._app_base_dir / "logs")

        def on_success(report) -> None:
            self.analytics_view.show_report(report)
            self._set_status("Network analytics updated")

        def on_error(exc: Exception) -> None:
            message = str(exc)
            self.analytics_view.show_error(message)
            self._show_error("Analytics Failed", message)
            self._set_status("Action failed")

        self._run_async(task, on_success, on_error)

    def _export_workflow(self, slug: str) -> None:
        descriptor = self._workflow_service.get_workflow(slug)
        if descriptor is None:
            self.workflows_view.set_status("Select a workflow to export.")
            return

        default_dir = self._app_base_dir / "exported_workflows"
        default_dir.mkdir(exist_ok=True)
        default_path = default_dir / f"{descriptor.slug}.json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Workflow",
            str(default_path),
            "JSON Files (*.json)",
        )
        if not file_path:
            self.workflows_view.set_status("Export cancelled.")
            return

        self.workflows_view.set_status("Exporting workflow…")
        self._set_status("Exporting workflow…")

        def task() -> str:
            self._workflow_service.export_to_file(file_path, slug)
            return file_path

        def on_success(path: str) -> None:
            self.workflows_view.set_status(f"Exported to {path}")
            self._set_status("Workflow exported")

        def on_error(exc: Exception) -> None:
            message = str(exc)
            self.workflows_view.set_status(f"Export failed: {message}")
            self._show_error("Export Failed", message)
            self._set_status("Action failed")

        self._run_async(task, on_success, on_error)

    def _export_all_workflows(self, group_key: str | None = None) -> None:
        default_dir = self._app_base_dir / "exported_workflows"
        default_dir.mkdir(exist_ok=True)

        directory = QFileDialog.getExistingDirectory(
            self,
            "Export Workflow Library",
            str(default_dir),
        )
        if not directory:
            self.workflows_view.set_status("Bulk export cancelled.")
            return

        target_dir = Path(directory)
        self.workflows_view.set_status("Exporting curated workflows…")
        self._set_status("Exporting curated workflows…")

        def task() -> int:
            summary = self._workflow_service.export_all(str(target_dir), group_key=group_key)
            return len(summary.written_files)

        def on_success(count: int) -> None:
            plural = "s" if count != 1 else ""
            if group_key:
                label = group_key.replace("_", " ").title()
                self.workflows_view.set_status(
                    f"Exported {count} {label} workflow{plural} to {target_dir}"
                )
            else:
                self.workflows_view.set_status(f"Exported {count} workflow{plural} to {target_dir}")
            self._set_status("Workflow library exported")

        def on_error(exc: Exception) -> None:
            message = str(exc)
            self.workflows_view.set_status(f"Bulk export failed: {message}")
            self._show_error("Export Failed", message)
            self._set_status("Action failed")

        self._run_async(task, on_success, on_error)

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------
    def _run_async(self, task: Callable[[], object], on_success: Callable[[object], None], on_error: Callable[[Exception], None]) -> None:
        def job():
            try:
                return True, task()
            except Exception as exc:  # pragma: no cover - defensive guard
                return False, exc

        future = self._executor.submit(job)

        def deliver(future_result) -> None:
            ok, payload = future_result.result()

            def dispatch() -> None:
                if ok:
                    on_success(payload)
                else:
                    on_error(payload)  # type: ignore[arg-type]

            QTimer.singleShot(0, dispatch)

        future.add_done_callback(deliver)

    def _handle_task_error(self, error: Exception) -> None:
        message = str(error)
        self._set_status("Action failed")
        self._show_error("Operation Failed", message)

    def _show_error(self, title: str, message: str) -> None:
        QMessageBox.critical(self, title, message)

    def _set_status(self, message: str) -> None:
        if hasattr(self, "status_chip") and self.status_chip is not None:
            self.status_chip.setText(message)
        else:
            self._pending_status_message = message

    def _open_outputs(self) -> None:  # pragma: no cover - Qt binding
        outputs_config = self._repository.config.get("OUTPUTS", {}) if isinstance(self._repository.config, dict) else {}
        configured = outputs_config.get("GENERATIONS")
        if isinstance(configured, str) and configured.strip():
            path = Path(configured.strip())
            if not path.is_absolute():
                path = (self._app_base_dir / path).resolve()
        else:
            path = self._app_base_dir / "output"
        self._open_folder(path, label="outputs")

    def _open_config_dir(self) -> None:  # pragma: no cover - Qt binding
        self._open_folder(self._app_base_dir, label="app directory")

    def _open_logs_dir(self) -> None:  # pragma: no cover - Qt binding
        self._open_folder(self._app_base_dir / "logs", label="logs")

    def _open_folder(self, path: Path, *, label: str) -> None:
        try:
            path.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            self._show_error("Open Folder Failed", f"Unable to prepare {label}: {exc}")
            self._set_status("Action failed")
            return

        try:
            if sys.platform.startswith("win") and hasattr(os, "startfile"):
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
            self._set_status(f"Opened {label} at {path}")
        except Exception as exc:
            self._show_error("Open Folder Failed", str(exc))
            self._set_status("Action failed")

    def _open_qwen_docs(self) -> None:  # pragma: no cover - Qt binding
        webbrowser.open("https://docs.comfy.org/tutorials/image/qwen/qwen-image", new=2)
        self._set_status("Opened Qwen workflow guide")

    def _handle_update_log(self, channel: str, message: str) -> None:
        # Surface important update messages in the status chip while still logging to stdout.
        trimmed = message.strip()
        print(f"[{channel}] {trimmed}")
        if hasattr(self, "activity_view") and self.activity_view is not None:
            self.activity_view.append_entry(channel, trimmed)
        if channel in {"info", "worker"}:
            self._set_status(trimmed)

    def _handoff_update(self, update_info: dict[str, str]) -> None:
        updater_path = self._app_base_dir / "updater.py"
        if not updater_path.exists():
            self._show_error("Updater Missing", f"Could not locate updater script at {updater_path}.")
            self._coordinator.clear_pending_update()
            return

        temp_dir = update_info.get("temp_dir")
        dest_dir = update_info.get("dest_dir", str(self._app_base_dir))
        target_tag = update_info.get("target_tag")
        if not temp_dir:
            self._show_error("Update Failed", "Update metadata missing temporary directory.")
            self._coordinator.clear_pending_update()
            return

        args = [
            sys.executable,
            str(updater_path),
            str(os.getpid()),
            temp_dir,
            dest_dir,
        ]
        if target_tag:
            args.append(target_tag)

        try:
            subprocess.Popen(args, cwd=str(self._app_base_dir))
        except Exception as exc:
            self._show_error("Update Failed", f"Unable to launch updater: {exc}")
            self._coordinator.clear_pending_update()
            return

        self._executor.shutdown(wait=False)
        QApplication.instance().quit()

    def closeEvent(self, event) -> None:  # pragma: no cover - Qt lifecycle
        self._executor.shutdown(wait=False)
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Styling helpers
    # ------------------------------------------------------------------
    def _apply_material_theme(self) -> None:
        self._current_variant = resolve_theme_variant(
            mode=self._theme_mode,
            palette_key=self._theme_palette,
            custom_primary=self._theme_custom_primary,
            custom_surface=self._theme_custom_surface,
            custom_text=self._theme_custom_text,
        )
        stylesheet = build_stylesheet(
            mode=self._theme_mode,
            palette_key=self._theme_palette,
            custom_primary=self._theme_custom_primary,
            custom_surface=self._theme_custom_surface,
            custom_text=self._theme_custom_text,
        )
        self.setStyleSheet(stylesheet)
        self._sync_theme_toggle()
        if hasattr(self, "_status_pulse") and self._status_pulse is not None:
            self._status_pulse.refresh()

    def _sync_theme_toggle(self) -> None:
        if not hasattr(self, "theme_toggle"):
            return
        is_light = self._theme_mode == "light"
        self.theme_toggle.blockSignals(True)
        self.theme_toggle.setChecked(is_light)
        self._update_theme_toggle_icon()
        self.theme_toggle.blockSignals(False)

    def _persist_theme_preferences(self) -> None:
        self._repository.save_theme_preferences(
            mode=self._theme_mode,
            palette=self._theme_palette,
            custom_primary=self._theme_custom_primary,
            custom_surface=self._theme_custom_surface,
            custom_text=self._theme_custom_text,
        )

    def _handle_theme_palette_update(
        self,
        palette: str,
        custom_primary: str,
        custom_surface: str,
        custom_text: str,
    ) -> None:
        palette_key = palette.strip().lower()
        valid_palettes = set(PALETTES.keys()) | {CUSTOM_PALETTE_KEY}
        self._theme_palette = palette_key if palette_key in valid_palettes else "oceanic"
        self._theme_custom_primary = custom_primary
        self._theme_custom_surface = custom_surface
        self._theme_custom_text = custom_text
        self._apply_material_theme()
        self._persist_theme_preferences()
        self._set_status("Theme palette updated")

    def _handle_theme_mode_update(self, mode: str) -> None:
        next_mode = "light" if mode.strip().lower() == "light" else "dark"
        if next_mode == self._theme_mode:
            self._sync_theme_toggle()
            return
        self._theme_mode = next_mode
        self._apply_material_theme()
        self._persist_theme_preferences()
        self._set_status(f"{next_mode.capitalize()} theme applied")

    def _toggle_theme(self, checked: bool) -> None:  # pragma: no cover - Qt binding
        self._handle_theme_mode_update("light" if checked else "dark")


def launch_material_editor() -> int:
    """Launch the Material Configurator window."""

    app = QApplication.instance() or QApplication(sys.argv)
    repository = SettingsRepository()
    app_base_dir = Path(__file__).resolve().parent.parent
    window = MaterialConfigWindow(repository, app_base_dir)
    window.show()
    return app.exec()


__all__ = ["launch_material_editor", "MaterialConfigWindow"]
